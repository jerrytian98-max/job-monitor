"""
职位数据库管理模块
使用SQLite存储职位信息，实现持久化
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging

import os
PROFILE = os.environ.get('JOB_PROFILE', '')
PROFILE_SUFFIX = f'_{PROFILE}' if PROFILE else ''
DB_FILE = f'jobs{PROFILE_SUFFIX}.db'


logger = logging.getLogger(__name__)


class JobDatabase:
    """职位数据库管理器"""
    
    def __init__(self, db_path: str = DB_FILE):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 创建职位表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    salary TEXT,
                    city TEXT,
                    description TEXT,
                    url TEXT NOT NULL,
                    source_site TEXT,
                    publish_time TEXT,
                    found_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_notified BOOLEAN DEFAULT 0,
                    job_hash TEXT UNIQUE
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_found_time ON jobs(found_time)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_notified ON jobs(is_notified)
            ''')
            
            conn.commit()
            logger.info("数据库初始化成功")
            
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _generate_hash(self, job: Dict) -> str:
        """生成职位的唯一哈希值（主要基于URL和标题，避免因时间等可变因素导致重复）"""
        import hashlib
        # 使用 URL 和 标题 作为唯一标识，比之前加入薪资和城市更稳定
        job_str = f"{job.get('url', '')}_{job.get('title', '')}"
        return hashlib.md5(job_str.encode('utf-8')).hexdigest()
    
    def add_job(self, job: Dict) -> bool:
        """
        添加职位到数据库
        
        Args:
            job: 职位信息字典
        
        Returns:
            True表示添加成功，False表示职位已存在或添加失败
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            job_hash = self._generate_hash(job)
            
            # 检查是否已存在
            cursor.execute('SELECT id FROM jobs WHERE job_hash = ?', (job_hash,))
            if cursor.fetchone():
                return False
            
            # 插入新职位
            cursor.execute('''
                INSERT INTO jobs (
                    title, company, salary, city, description, url,
                    source_site, publish_time, found_time, job_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job.get('title', ''),
                job.get('company', ''),
                job.get('salary', ''),
                job.get('city', ''),
                job.get('description', ''),
                job.get('url', ''),
                job.get('source_site', ''),
                job.get('publish_time', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                job_hash
            ))
            
            conn.commit()
            logger.info(f"职位已添加到数据库: {job['title']} - {job['company']}")
            return True
            
        except Exception as e:
            logger.error(f"添加职位失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def add_jobs_batch(self, jobs: List[Dict]) -> int:
        """
        批量添加职位
        
        Args:
            jobs: 职位列表
        
        Returns:
            实际添加的职位数量
        """
        added_count = 0
        for job in jobs:
            if self.add_job(job):
                added_count += 1
        return added_count
    
    def get_all_jobs(self, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[Dict]:
        """
        获取所有职位
        
        Args:
            limit: 限制数量
            offset: 偏移量
        
        Returns:
            职位列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM jobs ORDER BY found_time DESC'
            if limit:
                query += ' LIMIT ? OFFSET ?'
                cursor.execute(query, (limit, offset))
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取职位失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_new_jobs(self, hours: int = 24) -> List[Dict]:
        """
        获取最近的新职位
        
        Args:
            hours: 最近多少小时内的职位
        
        Returns:
            职位列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE found_time >= datetime('now', '-' || ? || ' hours')
                ORDER BY found_time DESC
            ''', (hours,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取新职位失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_jobs_by_company(self, company: str) -> List[Dict]:
        """
        获取指定公司的职位
        
        Args:
            company: 公司名称
        
        Returns:
            职位列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE company LIKE ?
                ORDER BY found_time DESC
            ''', (f'%{company}%',))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取公司职位失败: {e}")
            return []
        finally:
            conn.close()
    
    def mark_as_notified(self, job_ids: List[int]) -> bool:
        """
        标记职位已通知
        
        Args:
            job_ids: 职位ID列表
        
        Returns:
            True表示成功
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            for job_id in job_ids:
                cursor.execute('UPDATE jobs SET is_notified = 1 WHERE id = ?', (job_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"标记已通知失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 总职位数
            cursor.execute('SELECT COUNT(*) as total FROM jobs')
            total = cursor.fetchone()['total']
            
            # 今日新增
            cursor.execute('''
                SELECT COUNT(*) as today 
                FROM jobs 
                WHERE DATE(found_time) = DATE('now')
            ''')
            today = cursor.fetchone()['today']
            
            # 未通知
            cursor.execute('SELECT COUNT(*) as not_notified FROM jobs WHERE is_notified = 0')
            not_notified = cursor.fetchone()['not_notified']
            
            # 公司分布
            cursor.execute('''
                SELECT company, COUNT(*) as count 
                FROM jobs 
                GROUP BY company 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            top_companies = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_jobs': total,
                'new_jobs_today': today,
                'jobs_not_notified': not_notified,
                'top_companies': top_companies
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
        finally:
            conn.close()
    
    def clear_old_jobs(self, days: int = 30) -> int:
        """
        清除旧职位
        
        Args:
            days: 保留最近多少天的职位
        
        Returns:
            删除的职位数量
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM jobs 
                WHERE found_time < datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"已清除 {deleted_count} 个旧职位")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清除旧职位失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def clear_all_jobs(self) -> int:
        """
        清除所有职位记录
        
        Returns:
            删除的职位数量
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM jobs')
            deleted_count = cursor.rowcount
            
            # 重置自增ID
            cursor.execute('DELETE FROM sqlite_sequence WHERE name="jobs"')
            
            conn.commit()
            logger.info(f"已清除所有 {deleted_count} 个职位记录")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清除所有职位失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def search_jobs(self, keyword: str) -> List[Dict]:
        """
        搜索职位
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的职位列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE title LIKE ? OR company LIKE ? OR description LIKE ?
                ORDER BY found_time DESC
            ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"搜索职位失败: {e}")
            return []
        finally:
            conn.close()


# 全局数据库实例
db = JobDatabase()
