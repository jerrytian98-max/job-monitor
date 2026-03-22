"""
职位匹配模块
根据配置过滤和匹配符合条件的职位
"""

import hashlib
from typing import List, Dict
import logging
import json
import os
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobMatcher:
    """职位匹配器"""
    
    def __init__(self, config: dict, storage_file: str = 'jobs_cache.json'):
        self.config = config
        self.storage_file = storage_file
        self.known_jobs = self._load_known_jobs()
    
    def _load_known_jobs(self) -> dict:
        """加载已知的职位缓存"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载职位缓存失败: {e}")
                return {}
        return {}
    
    def _save_known_jobs(self):
        """保存已知的职位缓存"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.known_jobs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存职位缓存失败: {e}")
    
    def _generate_job_id(self, job: Dict) -> str:
        """为职位生成唯一ID（基于URL和标题，避免因抓取信息的微小差异导致重复）"""
        job_str = f"{job.get('url', '')}_{job.get('title', '')}"
        return hashlib.md5(job_str.encode('utf-8')).hexdigest()
    
    def is_new_job(self, job: Dict) -> bool:
        """
        判断是否为新职位

        Args:
            job: 职位信息

        Returns:
            True表示新职位，False表示已存在
        """
        # 同时保存到数据库
        is_new = db.add_job(job)

        job_id = self._generate_job_id(job)

        if job_id not in self.known_jobs:
            self.known_jobs[job_id] = {
                'job': job,
                'found_time': None  # 将在添加时设置
            }
            return is_new
        return False
    
    def match_job(self, job: Dict) -> bool:
        """
        判断职位是否匹配配置条件
        
        Args:
            job: 职位信息
        
        Returns:
            True表示匹配，False表示不匹配
        """
        # 移除了目标公司过滤逻辑，因为现在通过目标网址抓取，抓取到的即视为该公司的职位
        
        # 检查城市
        cities = self.config.get('cities', [])
        if cities and job.get('city', '') not in cities and job.get('city', '') != '未知':
            return False
        
        # 检查排除关键词
        exclude_keywords = self.config.get('exclude_keywords', [])
        title = job.get('title', '')
        description = job.get('description', '')
        
        for keyword in exclude_keywords:
            if keyword in title or keyword in description:
                return False
        
        # 检查职位关键词
        job_keywords = self.config.get('job_keywords', [])
        if not job_keywords:
            return True # 如果没有配置关键词，默认全部匹配
            
        for keyword in job_keywords:
            if keyword.lower() in title.lower() or keyword.lower() in description.lower():
                return True
        
        return False
    
    def filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        过滤职位，返回符合条件的新职位
        
        Args:
            jobs: 职位列表
        
        Returns:
            符合条件的新职位列表
        """
        matched_jobs = []
        
        for job in jobs:
            try:
                # 先检查是否匹配条件
                if not self.match_job(job):
                    continue
                
                # 再检查是否为新职位
                if self.is_new_job(job):
                    matched_jobs.append(job)
                    logger.info(f"发现新职位: {job['title']} - {job['company']}")
                
            except Exception as e:
                logger.error(f"过滤职位时出错: {e}")
        
        # 更新缓存
        self._save_known_jobs()
        
        return matched_jobs
    
    def mark_as_notified(self, jobs: List[Dict]):
        """
        标记职位已通知
        
        Args:
            jobs: 职位列表
        """
        for job in jobs:
            job_id = self._generate_job_id(job)
            if job_id in self.known_jobs:
                import time
                self.known_jobs[job_id]['found_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        self._save_known_jobs()
