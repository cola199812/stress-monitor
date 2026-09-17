#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜狐新闻爬虫 - 使用 Selenium 处理 SPA 页面
"""

import re
import time
import html
import logging
import warnings

# 抑制CSS选择器警告
warnings.filterwarnings('ignore', category=FutureWarning, module='soupsieve')
from urllib.parse import quote
from datetime import datetime
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

try:
    from .base import parse_date, normalize_date, REQUEST_DELAY
except ImportError:
    from base import parse_date, normalize_date, REQUEST_DELAY

logger = logging.getLogger(__name__)


class SohuNewsCrawler:
    """搜狐新闻爬虫"""

    SOURCE_NAME = '搜狐新闻'

    def __init__(self):
        self.logger = logger


    def crawl(self, keyword: str, max_results: int = 50,
              start_date: Optional[datetime] = None,
              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """爬取搜狐新闻，使用Selenium处理SPA页面"""
        results = []
        seen_urls: set = set()
        driver = None

        self.logger.info(f"开始爬取搜狐新闻: 关键词={keyword}")

        try:
            # 配置Selenium Chrome选项 - 优化版本，减少错误输出
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1920,1080')
            
            # 减少日志输出
            options.add_argument('--log-level=3')  # 只显示严重错误
            options.add_argument('--silent')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-gpu-logging')
            
            # 禁用不必要的功能以减少错误
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            
            # USB和设备相关错误抑制
            options.add_argument('--disable-usb-keyboard-detect')
            options.add_argument('--disable-device-discovery-notifications')
            
            # 网络相关优化
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-ipc-flooding-protection')
            
            options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 实验性选项 - 抑制更多日志
            options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # 抑制Chrome的日志输出
            prefs = {
                'profile.default_content_setting_values': {
                    'notifications': 2,  # 禁用通知
                }
            }
            options.add_experimental_option('prefs', prefs)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # 搜狐搜索URL（使用传入的完整URL格式）
            search_url = (
                f"https://search.sohu.com/?keyword={quote(keyword)}&type=10002&ie=utf8"
                f"&queryType=default&spm=smpc.channel_258.search-box.1774250205878ktbfoyk_1090"
            )

            self.logger.info(f"访问搜狐搜索页面")
            driver.get(search_url)
            time.sleep(5)  # 等待JS渲染

            # 等待搜索结果加载，增加等待时间
            max_wait = 20
            wait_count = 0
            news_items = []
            
            while wait_count < max_wait:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # 尝试多种选择器策略
                selector_strategies = [
                    # 基于Vue组件的选择器
                    'div[data-v-] a[href*="sohu.com"]',
                    'div.search-page a[href*="sohu.com"]',
                    
                    # 通用新闻链接选择器
                    'a[href*="sohu.com"][title]',
                    'a[href*="www.sohu.com/a/"]',
                    'a[href*="mp.sohu.com"]',
                    
                    # 可能的结果容器
                    'div.result a',
                    'div.item a',
                    'div.news a',
                    'div.list a',
                    
                    # 更宽泛的搜索
                    'a[href*="sohu.com"]'
                ]
                
                for selector in selector_strategies:
                    items = soup.select(selector)
                    if items:
                        self.logger.info(f"使用选择器 '{selector}' 找到 {len(items)} 个链接")
                        # 过滤出真正的新闻链接
                        news_items = [item for item in items if self._is_news_link(item.get('href', ''))]
                        if news_items:
                            self.logger.info(f"过滤后得到 {len(news_items)} 个新闻链接")
                            break
                
                if news_items:
                    break
                    
                wait_count += 1
                self.logger.info(f"等待搜索结果加载... {wait_count}/{max_wait}")
                time.sleep(1.5)
            
            if not news_items:
                self.logger.warning("未找到搜索结果或页面未加载完成")
                # 输出详细的调试信息
                page_content = driver.page_source
                self.logger.info(f"页面内容长度: {len(page_content)}")
                
                # 查找所有链接用于调试
                all_links = soup.select('a[href]')
                self.logger.info(f"页面总链接数: {len(all_links)}")
                
                sohu_links = [a for a in all_links if 'sohu.com' in a.get('href', '')]
                self.logger.info(f"搜狐域名链接数: {len(sohu_links)}")
                
                if sohu_links:
                    self.logger.info("搜狐链接示例:")
                    for i, link in enumerate(sohu_links[:5]):
                        href = link.get('href', '')
                        title = link.get('title', '') or link.get_text(strip=True)
                        self.logger.info(f"  {i+1}. {href} - {title[:50]}")
                
                # 查看页面主要元素
                main_divs = soup.select('div[class], div[id]')[:10]
                self.logger.info("主要div元素:")
                for div in main_divs:
                    classes = div.get('class', [])
                    div_id = div.get('id', '')
                    self.logger.info(f"  <div class='{' '.join(classes)}' id='{div_id}'>")
                
                return results
            
            # 解析新闻条目
            for item in news_items:
                if len(results) >= max_results:
                    break

                try:
                    # 提取标题和链接
                    if item.name == 'a':  # 直接是a标签
                        title = item.get('title', '') or item.get_text(strip=True)
                        link = item.get('href', '')
                    else:  # 包含a标签的元素
                        title_elem = item.select_one('a[title]') or item.select_one('a')
                        if not title_elem:
                            continue
                        title = title_elem.get('title', '') or title_elem.get_text(strip=True)
                        link = title_elem.get('href', '')
                    
                    # 过滤无效数据
                    if not title or not link or 'sohu.com' not in link:
                        continue
                    
                    # 去重
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    # 处理相对链接
                    if link.startswith('//'):
                        link = 'https:' + link
                    elif link.startswith('/'):
                        link = 'https://www.sohu.com' + link
                    elif not link.startswith('http'):
                        continue
                    
                    # 从文章页面获取详细信息（时间、来源、内容）
                    article_info = self._fetch_article_details(driver, link)
                    
                    # 使用文章页面的信息，如果获取不到则使用默认值
                    date_str = article_info.get('publish_time', '')
                    source_wz = article_info.get('source_wz', '')
                    content = article_info.get('content', '')
                    
                    # 时间过滤（如果有时间信息）
                    if date_str:
                        item_dt = parse_date(date_str)
                        if start_date and item_dt and item_dt < start_date:
                            continue
                        if end_date and item_dt and item_dt > end_date:
                            continue
                    
                    results.append({
                        'source': self.SOURCE_NAME,
                        'source_wz': source_wz,
                        'title': title,
                        'content': content,
                        'time': normalize_date(date_str) if date_str else '',
                        'keyword': keyword,
                        'url': link,
                    })
                    
                    self.logger.info(f"添加新闻: {title[:50]}... [时间: {date_str[:10]}] [来源: {source_wz[:10]}]")
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    self.logger.warning(f"解析搜狐新闻条目失败: {e}")
                    continue
            
            self.logger.info(f"搜狐新闻爬取完成，获取 {len(results)} 条")

        except Exception as e:
            self.logger.error(f"搜狐新闻爬取失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()

        return results

    def _fetch_article_details(self, driver, article_url: str) -> Dict[str, str]:
        """获取搜狐文章的详细信息（时间、来源、内容）"""
        details = {
            'publish_time': '',
            'source_wz': '',
            'content': ''
        }
        
        try:
            self.logger.info(f"获取文章详情: {article_url[:60]}...")
            
            # 访问文章页面
            driver.get(article_url)
            time.sleep(3)  # 等待页面加载
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 1. 提取发布时间
            time_selectors = [
                # 搜狐文章页的常见时间选择器
                'span.time',
                'div.time',
                '.article-info .time',
                '.info .time',
                'time[datetime]',
                '[class*="time"]',
                # 从文章信息栏提取
                '.article-info span',
                '.info span',
                '.meta span',
                # 通用时间格式 - 使用find方法避免CSS警告
            ]
            
            for selector in time_selectors:
                time_elem = soup.select_one(selector)
                if time_elem:
                    time_text = time_elem.get_text(strip=True)
                    # 检查是否包含日期格式
                    if re.search(r'20\d{2}[-年]\d{1,2}[-月]\d{1,2}', time_text):
                        details['publish_time'] = time_text
                        self.logger.info(f"提取到发布时间: {time_text}")
                        break
            
            # 2. 提取新闻来源（source_wz）
            # 搜狐文章通常会显示作者/媒体信息
            source_found = False
            
            # 方法1: 查找页面中的媒体/账号名称（搜狐自媒体特征）
            # 搜狐文章页面通常会显示账号名称
            account_selectors = [
                # 自媒体账号选择器
                'a[class*="account"]',
                'span[class*="account"]', 
                'div[class*="account"]',
                # 作者信息
                '.author a',
                '.writer a',
                '.media a',
                # 可能的账号链接
                'a[href*="/u/"]',
                'a[href*="/user/"]',
                # Vue组件数据
                'div[data-v-] a[class*="name"]',
                'span[data-v-][class*="name"]'
            ]
            
            for selector in account_selectors:
                account_elem = soup.select_one(selector)
                if account_elem:
                    account_text = account_elem.get_text(strip=True)
                    if (account_text and 
                        len(account_text) > 2 and len(account_text) < 50 and
                        not re.search(r'20\d{2}[-年]\d{1,2}[-月]\d{1,2}', account_text) and
                        '发布于' not in account_text):
                        details['source_wz'] = account_text
                        source_found = True
                        self.logger.info(f"提取到账号来源: {account_text}")
                        break
            
            # 方法2: 如果方法1没找到，尝试其他选择器
            if not source_found:
                source_selectors = [
                    # 搜狐文章页的来源选择器
                    '.article-info .source',
                    '.info .source',
                    '.meta .source',
                    '.author-name',
                    '.media-name',
                    'a[class*="author"]',
                    'span[class*="author"]',
                    '.source',
                    '[class*="source"]',
                ]
                
                for selector in source_selectors:
                    source_elem = soup.select_one(selector)
                    if source_elem:
                        source_text = source_elem.get_text(strip=True)
                        # 过滤掉时间信息和无效内容
                        if (source_text and 
                            not re.search(r'20\d{2}[-年]\d{1,2}[-月]\d{1,2}', source_text) and
                            '发布于' not in source_text and
                            len(source_text) > 2 and len(source_text) < 50):
                            # 清理来源文本
                            source_text = re.sub(r'来源[：:]?', '', source_text).strip()
                            details['source_wz'] = source_text
                            self.logger.info(f"提取到来源: {source_text}")
                            break
            
            # 方法3: 如果还是没找到，尝试从页面中查找作者或媒体信息
            if not details['source_wz']:
                # 查找所有可能包含作者/媒体信息的元素
                possible_source_elements = soup.select('span, div, a')
                for elem in possible_source_elements:
                    text = elem.get_text(strip=True)
                    # 查找看起来像媒体名称的文本
                    if (text and 
                        len(text) > 2 and len(text) < 30 and
                        not re.search(r'20\d{2}[-年]\d{1,2}[-月]\d{1,2}', text) and
                        not any(word in text for word in ['发布于', '时间', '阅读', '点击', '分享', '评论', '收藏']) and
                        (text.endswith('网') or text.endswith('报') or text.endswith('社') or 
                         text.endswith('台') or text.endswith('界') or '传媒' in text or '新闻' in text)):
                        details['source_wz'] = text
                        self.logger.info(f"智能提取到来源: {text}")
                        break
            
            # 3. 提取文章内容
            content_selectors = [
                # 搜狐文章页的内容选择器
                'article .content',
                '.article-text',
                '.article-content',
                '.content',
                '.article-body',
                'div[data-role="original-content"]',
                # 通用内容选择器
                'div.content',
                'div.text',
                'div.article',
                '.main-content',
            ]
            
            content_text = ''
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 清理无关元素
                    for unwanted in content_elem(['script', 'style', 'iframe', 'nav', 'aside', 'footer']):
                        unwanted.decompose()
                    
                    # 获取文本内容
                    paragraphs = content_elem.select('p')
                    if paragraphs:
                        # 提取段落内容
                        content_parts = []
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 10:  # 过滤过短段落
                                content_parts.append(text)
                        content_text = '\n'.join(content_parts[:10])  # 取前10段
                    else:
                        # 如果没有p标签，直接取文本
                        content_text = content_elem.get_text(separator='\n', strip=True)
                    
                    if content_text and len(content_text) > 100:
                        details['content'] = content_text[:1000]  # 限制内容长度
                        self.logger.info(f"提取到内容: {len(content_text)} 字符")
                        break
            
            # 如果文章页面没有时间信息，尝试从URL中提取
            if not details['publish_time']:
                url_date_match = re.search(r'/a/(\d+)_', article_url)
                if url_date_match:
                    # 搜狐URL中的数字可能包含时间戳信息
                    # 这里可以尝试转换，但不一定准确
                    pass
                    
        except Exception as e:
            self.logger.warning(f"获取文章详情失败 {article_url}: {e}")
        
        return details
    
    def _is_news_link(self, href: str) -> bool:
        """判断是否为新闻链接"""
        if not href or 'sohu.com' not in href:
            return False
        
        # 排除非新闻链接
        exclude_patterns = [
            '/user/', '/profile/', '/login', '/register', 
            '/search', '/channel', '/index', '/home',
            '.js', '.css', '.png', '.jpg', '.gif',
            'passport.sohu.com', 'login.sohu.com'
        ]
        
        for pattern in exclude_patterns:
            if pattern in href.lower():
                return False
        
        # 新闻链接特征
        news_patterns = [
            '/a/',  # 搜狐文章链接通常包含 /a/
            'mp.sohu.com',  # 自媒体文章
            '/news/',  # 新闻分类
            '/article/'  # 文章链接
        ]
        
        return any(pattern in href.lower() for pattern in news_patterns)


