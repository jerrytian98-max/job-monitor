"""
邮件通知模块
当发现符合条件的职位时发送邮件通知
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, config: dict):
        self.sender = config.get('sender', '')
        self.auth_code = config.get('auth_code', '')
        self.receiver = config.get('receiver', '')
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
    
    def _create_email_content(self, jobs: List[Dict]) -> str:
        """
        创建邮件内容
        
        Args:
            jobs: 职位列表
        
        Returns:
            HTML格式的邮件内容
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .job {{ border: 1px solid #ddd; margin: 20px 0; padding: 15px; border-radius: 5px; background-color: #f9f9f9; }}
                .job-title {{ color: #4CAF50; font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                .job-info {{ margin: 5px 0; }}
                .job-link {{ color: #2196F3; text-decoration: none; }}
                .job-link:hover {{ text-decoration: underline; }}
                .footer {{ text-align: center; color: #666; margin-top: 30px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 发现新的招聘信息！</h1>
                    <p>我们为您找到了 {len(jobs)} 个符合条件的职位</p>
                </div>
        """
        
        for i, job in enumerate(jobs, 1):
            html += f"""
                <div class="job">
                    <div class="job-title">{i}. {job.get('title', '职位名称')}</div>
                    <div class="job-info"><strong>公司：</strong>{job.get('company', '')}</div>
                    <div class="job-info"><strong>薪资：</strong>{job.get('salary', '面议')}</div>
                    <div class="job-info"><strong>城市：</strong>{job.get('city', '')}</div>
                    <div class="job-info"><strong>发布时间：</strong>{job.get('publish_time', '')}</div>
                    <div class="job-info"><strong>职位描述：</strong>{job.get('description', '')}</div>
                    <div class="job-info"><strong>链接：</strong><a href="{job.get('url', '')}" class="job-link">点击查看详情</a></div>
                </div>
            """
        
        html += f"""
                <div class="footer">
                    <p>邮件发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>这是自动发送的邮件，请勿直接回复</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_notification(self, jobs: List[Dict]) -> bool:
        """
        发送邮件通知
        
        Args:
            jobs: 职位列表
        
        Returns:
            True表示发送成功，False表示发送失败
        """
        if not jobs:
            logger.info("没有新职位需要发送通知")
            return True
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'招聘监测通知：发现 {len(jobs)} 个新职位'
            msg['From'] = self.sender
            msg['To'] = self.receiver
            
            # 添加HTML内容
            html_content = self._create_email_content(jobs)
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            logger.info(f"正在发送邮件到 {self.receiver}...")
            
            # 根据端口选择不同的连接方式
            if int(self.smtp_port) == 465:
                # 465 端口使用 SSL
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender, self.auth_code)
                    server.send_message(msg)
            else:
                # 其他端口（如 587, 25）使用普通连接后启动 TLS
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()  # 启用TLS加密
                    server.login(self.sender, self.auth_code)
                    server.send_message(msg)
            
            logger.info(f"邮件发送成功！共发送 {len(jobs)} 个职位信息")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False

    def send_test_email(self, target_email: str = None) -> bool:
        """
        发送测试邮件
        
        Args:
            target_email: 目标邮箱地址，如果未提供则使用配置中的接收邮箱
            
        Returns:
            True表示发送成功，False表示发送失败
        """
        receiver = target_email if target_email else self.receiver
        
        if not receiver:
            logger.error("未配置接收邮箱，无法发送测试邮件")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['Subject'] = '招聘监测系统 - 邮件配置测试'
            msg['From'] = self.sender
            msg['To'] = receiver
            
            content = f"""
            您好！
            
            这是一封来自招聘监测系统的测试邮件。
            如果您收到了这封邮件，说明您的邮件配置是正确的！
            
            发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            logger.info(f"正在发送测试邮件到 {receiver}...")
            
            # 根据端口选择不同的连接方式
            if int(self.smtp_port) == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender, self.auth_code)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender, self.auth_code)
                    server.send_message(msg)
                
            logger.info("测试邮件发送成功")
            return True
            
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            return False


class ConsoleNotifier:
    """控制台通知器（用于测试）"""
    
    def send_notification(self, jobs: List[Dict]) -> bool:
        """
        在控制台输出职位信息
        
        Args:
            jobs: 职位列表
        
        Returns:
            True表示输出成功
        """
        if not jobs:
            print("没有发现新职位")
            return True
        
        print("\n" + "="*60)
        print(f"发现 {len(jobs)} 个新职位！")
        print("="*60 + "\n")
        
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.get('title', '')}")
            print(f"   公司: {job.get('company', '')}")
            print(f"   薪资: {job.get('salary', '面议')}")
            print(f"   城市: {job.get('city', '')}")
            print(f"   发布时间: {job.get('publish_time', '')}")
            print(f"   链接: {job.get('url', '')}")
            print("-"*60 + "\n")
        
        return True
