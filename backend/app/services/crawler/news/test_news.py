#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻爬虫全源测试脚本
用于测试所有新闻源的爬虫功能是否正常
支持：新浪、百度、搜狐、网易、中国新闻网
"""

# ==================== 🔧 测试配置参数 ====================
# 测试模式配置
TEST_MODE = "single"  # 可选: "all"(所有源), "single"(单个源), "multiple"(多个源)

# 单个源测试配置 (当TEST_MODE="single"时使用)
SINGLE_SOURCE = "chinanews"  # 可选: sina, baidu, sohu, netease, chinanews

# 多个源测试配置 (当TEST_MODE="multiple"时使用)
MULTIPLE_SOURCES = ["sina", "chinanews"]  # 选择要测试的源

# 测试参数配置
TEST_KEYWORD = "驱蚊手环"  # 搜索关键词
MAX_RESULTS_PER_SOURCE = 20  # 每个源的最大抓取数量
TIME_RANGE_DAYS = 2000  # 时间范围（天数，从今天往前推）

# 显示配置
SHOW_CONTENT_PREVIEW = True  # 是否显示正文预览
MAX_PREVIEW_LENGTH = 200  # 正文预览最大长度
SHOW_MAX_NEWS_PER_SOURCE = 20  # 每个源最多显示几条新闻详情

# ==================== 📦 导入和日志配置 ====================
import logging
from datetime import datetime, timedelta
from BaiduNews import BaiduNewsCrawler
from SohuNews import SohuNewsCrawler
from NeteaseNews import NeteaseNewsCrawler
from ChinaNews import ChinaNewsCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 新闻源配置
NEWS_SOURCES = {
    'baidu': {
        'name': '百度新闻', 
        'crawler_class': BaiduNewsCrawler,
        'emoji': '🔍'
    },
    'sohu': {
        'name': '搜狐新闻',
        'crawler_class': SohuNewsCrawler,
        'emoji': '📡'
    },
    'netease': {
        'name': '网易新闻',
        'crawler_class': NeteaseNewsCrawler,
        'emoji': '🎵'
    },
    'chinanews': {
        'name': '中国新闻网',
        'crawler_class': ChinaNewsCrawler,
        'emoji': '🇨🇳'
    }
}

def test_single_source(source_key: str, test_keyword: str = None, max_results: int = None):
    """测试单个新闻源"""
    
    # 使用配置参数作为默认值
    if test_keyword is None:
        test_keyword = TEST_KEYWORD
    if max_results is None:
        max_results = MAX_RESULTS_PER_SOURCE
    
    if source_key not in NEWS_SOURCES:
        logger.error(f"❌ 不支持的新闻源: {source_key}")
        return False
    
    source_config = NEWS_SOURCES[source_key]
    
    print("=" * 60)
    print(f"{source_config['emoji']} {source_config['name']}爬虫测试")
    print("=" * 60)
    
    # 时间范围：使用配置的天数
    end_date = datetime.now()
    start_date = end_date - timedelta(days=TIME_RANGE_DAYS)
    
    logger.info(f"测试关键词: {test_keyword}")
    logger.info(f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"目标数量: {max_results} 条")
    
    try:
        # 创建爬虫实例并调用crawl方法
        crawler = source_config['crawler_class']()
        
        # 为新浪新闻添加年份分段搜索参数
        if source_key == 'sina':
            results = crawler.crawl(
                keyword=test_keyword,
                max_results=max_results,
                start_date=start_date,
                end_date=end_date,
                use_year_segmentation=True
            )
        else:
            results = crawler.crawl(
                keyword=test_keyword,
                max_results=max_results,
                start_date=start_date,
                end_date=end_date
            )
        
        # 显示结果
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        
        if results:
            logger.info(f"✅ 成功获取 {len(results)} 条新闻")
            
            print(f"\n📄 {source_config['name']}新闻列表:")
            for i, news in enumerate(results[:SHOW_MAX_NEWS_PER_SOURCE], 1):
                print(f"\n{i}. 【{news.get('source', 'N/A')}】")
                print(f"   标题: {news.get('title', 'N/A')[:60]}...")
                print(f"   发布日报: {news.get('source_wz', 'N/A')[:60]}...")
                print(f"   时间: {news.get('time', 'N/A')}")
                print(f"   链接: {news.get('url', 'N/A')[:80]}...")
                
                if SHOW_CONTENT_PREVIEW:
                    content = news.get('content', '')
                    if content:
                        content_preview = content[:MAX_PREVIEW_LENGTH] + "..." if len(content) > MAX_PREVIEW_LENGTH else content
                        print(f"   正文: {content_preview}")
                    else:
                        print("   正文: 未获取到内容")
            
            if len(results) > SHOW_MAX_NEWS_PER_SOURCE:
                print(f"\n   ... 还有 {len(results) - SHOW_MAX_NEWS_PER_SOURCE} 条新闻")
                
        else:
            logger.warning("⚠️  未获取到任何新闻数据")
            print(f"\n可能的原因:")
            print("1. 网络连接问题")
            print(f"2. {source_config['name']}网站结构发生变化")
            print("3. 搜索关键词过于具体")
            print("4. 时间范围内没有相关新闻")
        
        print("\n" + "=" * 60)
        print(f"🏁 {source_config['name']}测试完成")
        print("=" * 60)
        
        return len(results) > 0
        
    except Exception as e:
        logger.error(f"❌ {source_config['name']}测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_all_sources(test_keyword: str = None, max_results: int = None):
    """测试所有新闻源"""
    
    # 使用配置参数作为默认值
    if test_keyword is None:
        test_keyword = TEST_KEYWORD
    if max_results is None:
        max_results = MAX_RESULTS_PER_SOURCE
    
    print("=" * 80)
    print("🚀 新闻爬虫全源测试")
    print("=" * 80)
    
    results_summary = {}
    total_success = 0
    total_sources = len(NEWS_SOURCES)
    
    logger.info(f"开始测试 {total_sources} 个新闻源")
    logger.info(f"测试关键词: {test_keyword}")
    logger.info(f"每源目标数量: {max_results} 条")
    
    for source_key, source_config in NEWS_SOURCES.items():
        print(f"\n{'='*20} {source_config['emoji']} {source_config['name']} {'='*20}")
        
        try:
            success = test_single_source(source_key, test_keyword, max_results)
            results_summary[source_key] = {
                'name': source_config['name'],
                'emoji': source_config['emoji'],
                'success': success
            }
            
            if success:
                total_success += 1
                
        except Exception as e:
            logger.error(f"❌ {source_config['name']}测试异常: {e}")
            results_summary[source_key] = {
                'name': source_config['name'],
                'emoji': source_config['emoji'],
                'success': False
            }
        
        print(f"\n⏱️  等待2秒后继续下一个源...")
        import time
        time.sleep(2)
    
    # 显示总结报告
    print("\n" + "=" * 80)
    print("📋 测试总结报告")
    print("=" * 80)
    
    print(f"\n📊 总体统计:")
    print(f"   测试源数量: {total_sources}")
    print(f"   成功数量: {total_success}")
    print(f"   失败数量: {total_sources - total_success}")
    print(f"   成功率: {(total_success/total_sources)*100:.1f}%")
    
    print(f"\n📝 详细结果:")
    for source_key, result in results_summary.items():
        status = "✅ 成功" if result['success'] else "❌ 失败"
        print(f"   {result['emoji']} {result['name']}: {status}")
    
    print("\n" + "=" * 80)
    if total_success == total_sources:
        print("🎉 所有新闻源测试通过！")
    elif total_success > 0:
        print(f"⚠️  部分新闻源测试通过 ({total_success}/{total_sources})")
    else:
        print("❌ 所有新闻源测试失败")
    print("=" * 80)
    
    return total_success > 0

def test_specific_sources(sources: list = None, test_keyword: str = None, max_results: int = None):
    """测试指定的新闻源"""
    
    # 使用配置参数作为默认值
    if sources is None:
        sources = MULTIPLE_SOURCES
    if test_keyword is None:
        test_keyword = TEST_KEYWORD
    if max_results is None:
        max_results = MAX_RESULTS_PER_SOURCE
    
    print("=" * 80)
    print("🎯 指定新闻源测试")
    print("=" * 80)
    
    valid_sources = [s for s in sources if s in NEWS_SOURCES]
    invalid_sources = [s for s in sources if s not in NEWS_SOURCES]
    
    if invalid_sources:
        logger.warning(f"⚠️  无效的新闻源: {invalid_sources}")
        logger.info(f"📋 支持的新闻源: {list(NEWS_SOURCES.keys())}")
    
    if not valid_sources:
        logger.error("❌ 没有有效的新闻源可测试")
        return False
    
    logger.info(f"测试源: {valid_sources}")
    results_summary = {}
    
    for source_key in valid_sources:
        success = test_single_source(source_key, test_keyword, max_results)
        results_summary[source_key] = success
        
        print(f"\n⏱️  等待2秒后继续...")
        import time
        time.sleep(2)
    
    # 显示结果
    print(f"\n📋 测试结果:")
    success_count = 0
    for source_key, success in results_summary.items():
        source_config = NEWS_SOURCES[source_key]
        status = "✅ 成功" if success else "❌ 失败"
        print(f"   {source_config['emoji']} {source_config['name']}: {status}")
        if success:
            success_count += 1
    
    print(f"\n成功率: {success_count}/{len(valid_sources)} ({(success_count/len(valid_sources))*100:.1f}%)")
    return success_count > 0

if __name__ == '__main__':
    print("🚀 新闻爬虫测试工具")
    print("=" * 50)
    
    # 显示当前配置
    print("📋 当前测试配置:")
    print(f"   测试模式: {TEST_MODE}")
    print(f"   搜索关键词: {TEST_KEYWORD}")
    print(f"   每源数量: {MAX_RESULTS_PER_SOURCE}")
    print(f"   时间范围: 最近 {TIME_RANGE_DAYS} 天")
    
    if TEST_MODE == "single":
        print(f"   测试源: {SINGLE_SOURCE}")
    elif TEST_MODE == "multiple":
        print(f"   测试源: {MULTIPLE_SOURCES}")
    
    print("=" * 50)
    
    # 根据配置执行测试
    if TEST_MODE == "all":
        print("🔍 测试所有新闻源")
        success = test_all_sources()
    elif TEST_MODE == "single":
        if SINGLE_SOURCE not in NEWS_SOURCES:
            logger.error(f"❌ 无效的新闻源: {SINGLE_SOURCE}")
            logger.info(f"📋 支持的新闻源: {list(NEWS_SOURCES.keys())}")
            success = False
        else:
            print(f"🎯 测试单个新闻源: {NEWS_SOURCES[SINGLE_SOURCE]['name']}")
            success = test_single_source(SINGLE_SOURCE)
    elif TEST_MODE == "multiple":
        print(f"🎯 测试指定新闻源: {MULTIPLE_SOURCES}")
        success = test_specific_sources()
    else:
        logger.error(f"❌ 无效的测试模式: {TEST_MODE}")
        logger.info("📋 支持的测试模式: all, single, multiple")
        success = False
    
    # 显示结果和提示
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试完成！")
        print("💡 提示: 测试成功的源可以添加到 crawler_config.py 的 NEWS_SOURCES 列表中")
    else:
        print("⚠️  测试失败")
        print("💡 建议检查网络连接或爬虫代码逻辑")
    print("=" * 50)
