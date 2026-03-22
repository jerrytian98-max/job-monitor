"""
招聘监测系统 - Flask Web应用
提供Web界面管理监测配置和查看监测状态
"""

from flask import Flask, render_template, jsonify, request, Response
import yaml

import os
PROFILE = os.environ.get('JOB_PROFILE', '')
PROFILE_SUFFIX = f'_{PROFILE}' if PROFILE else ''
CONFIG_FILE = f'config{PROFILE_SUFFIX}.yaml'
LOG_FILE = f'app{PROFILE_SUFFIX}.log'

import subprocess
import threading
from datetime import datetime
from main import JobMonitor
from database import db
import logging
import queue
import json
from scraper_with_callback import get_scraper_with_callback
from notifier import EmailNotifier

# 配置日志 - 同时输出到文件和控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__,
           template_folder='templates',
           static_folder='static')

# 全局变量
monitor = None
monitor_thread = None
is_monitoring = False
monitor_status = {
    'status': 'stopped',
    'last_check': None,
    'total_jobs_found': 0,
    'new_jobs_today': 0,
    'running_time': None
}

# 分页设置
JOBS_PER_PAGE = 10

# 事件队列（用于实时推送）
event_queue = queue.Queue()


def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return {}


def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return False


def send_event(event_type: str, data: dict):
    """发送事件到队列"""
    event = {
        'type': event_type,
        'data': data,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    try:
        event_queue.put_nowait(event)
    except queue.Full:
        pass  # 队列满时忽略


# 全局回调函数
def status_callback(message: str, status_type: str):
    """状态更新回调"""
    send_event('status', {'message': message, 'type': status_type})


def job_callback(job: dict):
    """职位发现回调"""
    send_event('job_found', job)


class WebJobMonitor(JobMonitor):
    """
    Web环境下的监测器，支持回调
    """
    def __init__(self, config_file: str = CONFIG_FILE, test_mode: bool = False):
        super().__init__(config_file, test_mode)
        self.status_callback = status_callback
        self.job_callback = job_callback

    def _scrape_all_sites(self) -> list:
        """重写：使用带回调的爬虫"""
        all_jobs = []
        
        keywords = self.config.get('job_keywords', [])
        cities = self.config.get('cities', [])
        job_sites = self.config.get('job_sites', [])
        
        for site_url in job_sites:
            # 使用带回调的爬虫工厂函数
            scraper = get_scraper_with_callback(site_url, self.status_callback, self.job_callback)
            if scraper:
                try:
                    logger.info(f"开始抓取目标网址: {site_url}")
                    self.status_callback(f"开始抓取目标网址: {site_url}", "info")
                    
                    # 抓取并解析该 URL
                    jobs = scraper.scrape_jobs(site_url, keywords, cities)
                    all_jobs.extend(jobs)
                    logger.info(f"从 {site_url} 抓取到 {len(jobs)} 个匹配职位")
                
                except Exception as e:
                    logger.error(f"抓取目标网址 {site_url} 时出错: {e}")
                    self.status_callback(f"抓取目标网址 {site_url} 时出错: {e}", "error")
        
        return all_jobs


def run_monitor():
    """在后台运行监测"""
    global is_monitoring, monitor_status
    
    try:
        is_monitoring = True
        monitor_status['status'] = 'running'
        monitor_status['running_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 使用 WebJobMonitor
        monitor = WebJobMonitor(CONFIG_FILE, test_mode=False)
        monitor.run_forever()
        
    except Exception as e:
        logger.error(f"监测出错: {e}")
        status_callback(f"监测出错: {e}", "error")
    finally:
        is_monitoring = False
        monitor_status['status'] = 'stopped'


# 路由

@app.route('/')
def index():
    """主页"""
    config = load_config()
    return render_template('index.html', config=config, status=monitor_status)


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = load_config()
    return jsonify({'success': True, 'data': config})


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        config = request.json
        
        # 验证必要字段
        required_fields = ['job_keywords', 'cities', 'job_sites', 'email', 'check_interval']
        for field in required_fields:
            if field not in config:
                return jsonify({'success': False, 'message': f'缺少字段: {field}'})
        
        # 保存配置
        if save_config(config):
            logger.info("配置已更新")
            # 同步到云端
            try:
                subprocess.run(['git', 'add', CONFIG_FILE], cwd=os.path.dirname(os.path.abspath(__file__)), check=True)
                subprocess.run(['git', 'commit', '-m', 'Update config via Web UI'], cwd=os.path.dirname(os.path.abspath(__file__)))
                subprocess.run(['git', 'push', 'origin', 'main'], cwd=os.path.dirname(os.path.abspath(__file__)), check=True)
                logger.info('配置已同步到GitHub云端')
            except Exception as e:
                logger.error(f'配置同步云端失败: {e}')
            return jsonify({'success': True, 'message': '配置保存成功'})
        else:
            return jsonify({'success': False, 'message': '保存配置失败'})
            
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/monitor/start', methods=['POST'])
def start_monitor():
    """启动监测"""
    global monitor_thread, is_monitoring
    
    if is_monitoring:
        return jsonify({'success': False, 'message': '监测已在运行中'})
    
    try:
        # 在新线程中启动监测
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        
        logger.info("监测已启动")
        return jsonify({'success': True, 'message': '监测已启动'})
        
    except Exception as e:
        logger.error(f"启动监测失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitor():
    """停止监测"""
    global is_monitoring
    
    if not is_monitoring:
        return jsonify({'success': False, 'message': '监测未运行'})
    
    try:
        is_monitoring = False
        monitor_status['status'] = 'stopped'
        
        logger.info("监测已停止")
        return jsonify({'success': True, 'message': '监测已停止'})
        
    except Exception as e:
        logger.error(f"停止监测失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/monitor/status', methods=['GET'])
def get_status():
    """获取监测状态"""
    monitor_status['is_monitoring'] = is_monitoring
    
    # 如果正在监测，更新运行时间
    if is_monitoring and monitor_status['running_time']:
        start_time = datetime.strptime(monitor_status['running_time'], '%Y-%m-%d %H:%M:%S')
        elapsed = datetime.now() - start_time
        hours, remainder = divmod(elapsed.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        monitor_status['elapsed_time'] = f"{hours}小时{minutes}分钟"
    
    return jsonify({'success': True, 'data': monitor_status})


@app.route('/api/test/check', methods=['POST'])
def test_check():
    """测试检查一次"""
    try:
        monitor = WebJobMonitor(CONFIG_FILE, test_mode=True)
        success = monitor.check_jobs()

        if success:
            return jsonify({'success': True, 'message': '测试检查完成'})
        else:
            return jsonify({'success': False, 'message': '测试检查失败'})

    except Exception as e:
        logger.error(f"测试检查失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """获取职位列表"""
    try:
        page = int(request.args.get('page', 1))
        keyword = request.args.get('keyword', '')

        # 搜索或获取全部
        if keyword:
            jobs = db.search_jobs(keyword)
        else:
            offset = (page - 1) * JOBS_PER_PAGE
            jobs = db.get_all_jobs(limit=JOBS_PER_PAGE, offset=offset)

        return jsonify({'success': True, 'data': jobs})

    except Exception as e:
        logger.error(f"获取职位列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/jobs/clear', methods=['POST'])
def clear_jobs():
    """清除职位记录"""
    try:
        # 检查是否是完全清除
        clear_all = request.args.get('all', 'false').lower() == 'true'
        
        if clear_all:
            cleared = db.clear_all_jobs()
            message = f'已清除所有 {cleared} 条职位记录'
        else:
            days = int(request.args.get('days', 30))
            cleared = db.clear_old_jobs(days)
            message = f'已清除 {cleared} 条旧职位记录'

        return jsonify({'success': True, 'message': message})

    except Exception as e:
        logger.error(f"清除职位失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/jobs/scan-url', methods=['POST'])
def scan_job_url():
    """扫描单个职位URL并添加到数据库"""
    try:
        from url_scraper import scrape_jobs_from_urls

        data = request.json
        url = data.get('url', '')

        if not url:
            return jsonify({'success': False, 'message': '请提供职位URL'})

        logger.info(f"正在扫描职位URL: {url}")

        # 扫描URL
        jobs = scrape_jobs_from_urls([url])

        if jobs:
            # 添加到数据库
            added = db.add_jobs_batch(jobs)
            return jsonify({
                'success': True,
                'message': f'成功添加 {added} 个职位',
                'job': jobs[0]
            })
        else:
            return jsonify({'success': False, 'message': '无法从该URL获取职位信息'})

    except Exception as e:
        logger.error(f"扫描URL失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    try:
        stats = db.get_statistics()
        return jsonify({'success': True, 'data': stats})

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/events')
def events():
    """Server-Sent Events - 实时推送工作状态"""
    def generate():
        while True:
            try:
                # 从队列获取事件
                event = event_queue.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # 发送心跳
                yield "data: {\"type\": \"heartbeat\"}\n\n"
            except GeneratorExit:
                break

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/email/test', methods=['POST'])
def test_email():
    """发送测试邮件"""
    try:
        config = load_config()
        email_config = config.get('email', {})
        
        if not email_config:
            return jsonify({'success': False, 'message': '未找到邮件配置，请先保存配置'})
            
        target_email = request.json.get('email') or email_config.get('receiver')
        
        if not target_email:
            return jsonify({'success': False, 'message': '请提供接收邮箱或在配置中设置'})
            
        notifier = EmailNotifier(email_config)
        success = notifier.send_test_email(target_email)
        
        if success:
            return jsonify({'success': True, 'message': f'测试邮件已发送至 {target_email}'})
        else:
            return jsonify({'success': False, 'message': '发送失败，请检查邮箱配置和授权码'})
            
    except Exception as e:
        logger.error(f"测试邮件失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志内容"""
    try:
        lines = int(request.args.get('lines', 100))
        log_file = LOG_FILE
        
        if not os.path.exists(log_file):
            return jsonify({'success': True, 'data': '暂无日志记录'})
            
        with open(log_file, 'r', encoding='utf-8') as f:
            # 读取最后N行
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            content = ''.join(last_lines)
            
        return jsonify({'success': True, 'data': content})
        
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    # 确保必要目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("="*60)
    print("招聘监测系统 Web界面")
    print("="*60)
    print(f"访问地址: http://127.0.0.1:5000")
    print("="*60)
    print()
    
    app.run(host='0.0.0.0', port=int(os.environ.get('FLASK_PORT', 5000)), debug=True)
