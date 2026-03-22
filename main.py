"""
招聘监测系统主程序
定时监测招聘网站，发现符合条件的职位时发送邮件通知
"""

import yaml
import time
import logging
import argparse
from typing import List, Dict
from scraper import get_scraper
from matcher import JobMatcher
from notifier import EmailNotifier, ConsoleNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobMonitor:
    """招聘监测器"""
    
    def __init__(self, config_file: str = 'config.yaml', test_mode: bool = False):
        """
        初始化监测器
        
        Args:
            config_file: 配置文件路径
            test_mode: 测试模式（使用控制台输出而非邮件）
        """
        self.config = self._load_config(config_file)
        self.matcher = JobMatcher(self.config)
        
        # 根据模式选择通知方式
        if test_mode:
            self.notifier = ConsoleNotifier()
            logger.info("运行在测试模式，通知将输出到控制台")
        else:
            self.notifier = EmailNotifier(self.config['email'])
            logger.info("运行在正常模式，将通过邮件发送通知")
    
    def _load_config(self, config_file: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"配置文件加载成功: {config_file}")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _scrape_all_sites(self) -> List[Dict]:
        """从所有配置的招聘网站爬取职位"""
        all_jobs = []
        
        companies = self.config.get('target_companies', [])
        keywords = self.config.get('job_keywords', [])
        cities = self.config.get('cities', [])
        job_sites = self.config.get('job_sites', [])
        
        for site_url in job_sites:
            scraper = get_scraper(site_url)
            if scraper:
                try:
                    logger.info(f"开始爬取网站: {site_url}")
                    
                    for company in companies:
                        jobs = scraper.scrape_jobs(company, keywords, cities)
                        all_jobs.extend(jobs)
                        logger.info(f"从 {site_url} 爬取到 {len(jobs)} 个职位（{company}）")
                
                except Exception as e:
                    logger.error(f"爬取网站 {site_url} 时出错: {e}")
        
        return all_jobs
    
    def check_jobs(self) -> bool:
        """
        检查新职位并发送通知
        
        Returns:
            True表示检查成功
        """
        try:
            logger.info("="*60)
            logger.info("开始检查新职位...")
            logger.info("="*60)
            
            # 爬取所有职位
            all_jobs = self._scrape_all_sites()
            logger.info(f"共爬取到 {len(all_jobs)} 个职位")
            
            if not all_jobs:
                logger.info("没有找到任何职位")
                return True
            
            # 过滤符合条件的新职位
            matched_jobs = self.matcher.filter_jobs(all_jobs)
            logger.info(f"找到 {len(matched_jobs)} 个符合条件的新职位")
            
            # 发送通知
            if matched_jobs:
                success = self.notifier.send_notification(matched_jobs)
                if success:
                    # 标记为已通知
                    self.matcher.mark_as_notified(matched_jobs)
                    logger.info("职位检查完成，已发送通知")
                else:
                    logger.error("发送通知失败")
                return success
            else:
                logger.info("没有发现新职位")
                return True
            
        except Exception as e:
            logger.error(f"检查职位时出错: {e}")
            return False
    
    def run_once(self):
        """运行一次检查"""
        self.check_jobs()
    
    def run_forever(self):
        """持续运行监测"""
        check_interval = self.config.get('check_interval', 2) * 3600  # 转换为秒
        
        logger.info(f"监测已启动，每 {check_interval/3600:.1f} 小时检查一次")
        logger.info("按 Ctrl+C 停止监测")
        print()
        
        try:
            while True:
                self.check_jobs()
                
                # 计算下次检查时间
                next_check = time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(time.time() + check_interval))
                logger.info(f"下次检查时间: {next_check}")
                logger.info(f"等待 {check_interval/3600:.1f} 小时后再次检查...")
                print()
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("\n监测已停止")
            print("\n感谢使用招聘监测系统！")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='招聘监测系统')
    parser.add_argument('--config', default='config.yaml', 
                       help='配置文件路径（默认: config.yaml）')
    parser.add_argument('--test', action='store_true',
                       help='测试模式：使用控制台输出而非邮件')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次检查，不循环')
    
    args = parser.parse_args()
    
    try:
        monitor = JobMonitor(args.config, args.test)
        
        if args.once:
            monitor.run_once()
        else:
            monitor.run_forever()
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
