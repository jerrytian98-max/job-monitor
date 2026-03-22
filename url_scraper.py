"""
URL抓取器 - 从用户提供的具体URL抓取职位信息
支持BOSS直聘、拉勾网、猎聘网的具体职位页面
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class URLScraper:
    """从具体URL抓取职位信息"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def scrape_from_url(self, url: str) -> Dict:
        """
        从单个URL抓取职位信息

        Args:
            url: 职位页面URL

        Returns:
            职位信息字典
        """
        try:
            logger.info(f"正在抓取URL: {url}")

            # 随机延迟
            delay = random.uniform(2, 5)
            time.sleep(delay)

            # 发送请求
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                logger.error(f"请求失败，状态码: {response.status_code}")
                return None

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 根据域名选择解析方式
            if 'zhipin.com' in url:
                return self._parse_zhipin_page(soup, url)
            elif 'lagou.com' in url:
                return self._parse_lagou_page(soup, url)
            elif 'liepin.com' in url:
                return self._parse_liepin_page(soup, url)
            else:
                logger.warning(f"不支持的网站: {url}")
                return None

        except Exception as e:
            logger.error(f"抓取URL失败: {e}")
            return None

    def scrape_from_urls(self, urls: List[str]) -> List[Dict]:
        """
        从多个URL批量抓取职位信息

        Args:
            urls: URL列表

        Returns:
            职位信息列表
        """
        jobs = []
        for url in urls:
            job = self.scrape_from_url(url)
            if job:
                jobs.append(job)

        return jobs

    def _parse_zhipin_page(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析BOSS直聘职位页面"""
        try:
            # 职位标题
            title_elem = soup.find('span', class_='name')
            title = title_elem.text.strip() if title_elem else '未知职位'

            # 薪资
            salary_elem = soup.find('span', class_='salary')
            salary = salary_elem.text.strip() if salary_elem else '面议'

            # 公司名称
            company_elem = soup.find('a', class_='company-name')
            company = company_elem.text.strip() if company_elem else '未知公司'

            # 城市位置
            location_elem = soup.find('span', class_='location-address')
            city = location_elem.text.strip() if location_elem else '未知'

            # 职位描述
            desc_elem = soup.find('div', class_='job-sec-text')
            description = desc_elem.text.strip() if desc_elem else ''

            # 发布时间
            time_elem = soup.find('span', class_='time-ago')
            publish_time = time_elem.text.strip() if time_elem else time.strftime('%Y-%m-%d')

            return {
                'title': title,
                'company': company,
                'salary': salary,
                'city': city,
                'url': url,
                'description': description[:200] if description else '职位详情',
                'publish_time': publish_time,
                'source_site': 'BOSS直聘'
            }

        except Exception as e:
            logger.error(f"解析BOSS直聘页面失败: {e}")
            return None

    def _parse_lagou_page(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析拉勾网职位页面"""
        try:
            # 拉勾网使用JavaScript渲染，直接解析HTML可能获取不到完整内容
            # 这里提供基本信息
            title_elem = soup.find('span', class_='position-title')
            title = title_elem.text.strip() if title_elem else '未知职位'

            salary_elem = soup.find('span', class_='salary')
            salary = salary_elem.text.strip() if salary_elem else '面议'

            company_elem = soup.find('a', class_='company-name')
            company = company_elem.text.strip() if company_elem else '未知公司'

            return {
                'title': title,
                'company': company,
                'salary': salary,
                'city': '未知',
                'url': url,
                'description': '拉勾网职位详情请查看原始页面',
                'publish_time': time.strftime('%Y-%m-%d'),
                'source_site': '拉勾网'
            }

        except Exception as e:
            logger.error(f"解析拉勾网页面失败: {e}")
            return None

    def _parse_liepin_page(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析猎聘网职位页面"""
        try:
            title_elem = soup.find('h1', class_='title-info')
            title = title_elem.text.strip() if title_elem else '未知职位'

            salary_elem = soup.find('span', class_='text-warning')
            salary = salary_elem.text.strip() if salary_elem else '面议'

            company_elem = soup.find('a', class_='company-name')
            company = company_elem.text.strip() if company_elem else '未知公司'

            # 城市
            city_elem = soup.find('span', class_='area')
            city = city_elem.text.strip() if city_elem else '未知'

            return {
                'title': title,
                'company': company,
                'salary': salary,
                'city': city,
                'url': url,
                'description': '猎聘网职位详情请查看原始页面',
                'publish_time': time.strftime('%Y-%m-%d'),
                'source_site': '猎聘网'
            }

        except Exception as e:
            logger.error(f"解析猎聘网页面失败: {e}")
            return None


def scrape_jobs_from_urls(urls: List[str]) -> List[Dict]:
    """
    从URL列表抓取职位信息（便捷函数）

    Args:
        urls: URL列表

    Returns:
        职位信息列表
    """
    scraper = URLScraper()
    return scraper.scrape_from_urls(urls)
