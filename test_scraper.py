"""
测试真实爬虫功能
"""

from scraper_real import get_scraper

# 测试配置
test_companies = ['腾讯', '阿里巴巴']
test_keywords = ['Python', 'Java']
test_cities = ['深圳', '北京']
test_sites = [
    'https://www.zhipin.com',
    'https://www.lagou.com',
    'https://www.liepin.com'
]

print("="*60)
print("招聘监测系统 - 真实爬虫测试")
print("="*60)
print()

all_jobs = []

for site_url in test_sites:
    print(f"\n{'='*60}")
    print(f"测试网站: {site_url}")
    print(f"{'='*60}")

    scraper = get_scraper(site_url, use_real=True)

    if scraper:
        for company in test_companies[:1]:  # 只测试第一个公司
            for keyword in test_keywords[:1]:  # 只测试第一个关键词
                for city in test_cities[:1]:  # 只测试第一个城市
                    try:
                        print(f"\n正在爬取: {company} - {keyword} - {city}")

                        jobs = scraper.scrape_jobs(company, [keyword], [city])

                        if jobs:
                            print(f"\n成功获取 {len(jobs)} 个职位:")
                            for i, job in enumerate(jobs, 1):
                                print(f"\n{i}. {job['title']}")
                                print(f"   公司: {job['company']}")
                                print(f"   薪资: {job['salary']}")
                                print(f"   城市: {job['city']}")
                                print(f"   来源: {job['source_site']}")
                                print(f"   链接: {job['url']}")

                            all_jobs.extend(jobs)
                        else:
                            print("未获取到职位信息")

                    except Exception as e:
                        print(f"爬取失败: {e}")
    else:
        print(f"不支持的网站: {site_url}")

print(f"\n{'='*60}")
print(f"测试完成！共获取 {len(all_jobs)} 个职位")
print(f"{'='*60}")
