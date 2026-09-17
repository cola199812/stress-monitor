#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度新闻爬虫 - 使用 Selenium + webdriver_manager 自动匹配 chromedriver 版本
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


class BaiduNewsCrawler:
    """百度新闻爬虫"""

    SOURCE_NAME = '百度新闻'

    def __init__(self):
        self.logger = logger

    def crawl(self, keyword: str, max_results: int = 50,
              start_date: Optional[datetime] = None,
              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """爬取百度新闻，按时间从新到旧排序，超出时间范围后提前停止"""
        results = []
        seen_urls: set = set()
        driver = None

        self.logger.info(f"开始爬取百度新闻: 关键词={keyword}")

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
            
            # 网络相关优化 - 减少P2P和STUN服务器错误
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--disable-webrtc')  # 禁用WebRTC，减少STUN服务器连接错误
            options.add_argument('--disable-webrtc-multiple-routes')
            options.add_argument('--disable-webrtc-hw-decoding')
            options.add_argument('--disable-webrtc-hw-encoding')
            
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
                    'media_stream': 2,   # 禁用媒体流（减少P2P连接）
                }
            }
            options.add_experimental_option('prefs', prefs)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # rtt=4 按时间从新到旧排序
            base_url = (
                f"https://www.baidu.com/s?tn=news&rtt=4&bsst=1&cl=2"
                f"&rsv_dl=ns_pc&word={quote(keyword)}"
            )

            page = 1
            consecutive_empty = 0

            while len(results) < max_results and consecutive_empty < 2:
                pn = (page - 1) * 10
                url = base_url if page == 1 else base_url + f"&pn={pn}"

                self.logger.info(f"访问百度新闻第{page}页")
                driver.get(url)
                time.sleep(3)

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                news_items = (
                    soup.select('div.result-op.c-container[tpl="news-normal"]') or
                    soup.select('div[tpl="news-normal"]') or
                    soup.select('div.c-container.xpath-log')
                )

                if not news_items:
                    self.logger.info(f"第{page}页未找到新闻条目")
                    consecutive_empty += 1
                    page += 1
                    continue

                self.logger.info(f"第{page}页找到 {len(news_items)} 个条目")
                page_count = 0
                duplicate_count = 0
                out_of_range_count = 0

                for item in news_items:
                    if len(results) >= max_results:
                        break

                    try:
                        title_elem = (
                            item.select_one('h3 a') or
                            item.select_one('a[data-click]') or
                            item.select_one('a[href^="http"]')
                        )
                        if not title_elem:
                            continue

                        title = html.unescape(title_elem.get_text(strip=True))
                        if not title or len(title) < 5:
                            continue

                        item_tpl = item.get('tpl', '')
                        if item_tpl and item_tpl != 'news-normal':
                            continue

                        link = title_elem.get('href', '')
                        if not link.startswith('http'):
                            continue

                        if link in seen_urls:
                            duplicate_count += 1
                            continue
                        seen_urls.add(link)

                        # 提取时间和来源信息
                        date_str = ''
                        source_wz = ''
                        date_elem = (
                            item.select_one('span.c-color-gray2.c-font-normal') or
                            item.select_one('span.c-color-gray2') or
                            item.select_one('span[class*="c-color-gray"]') or
                            item.select_one('span[class*="time"]')
                        )
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            # 提取日期
                            m = re.search(r'(\d{4}[-年]\d{1,2}[-月]\d{1,2})', date_text)
                            if m:
                                date_str = m.group(1).replace('年', '-').replace('月', '-')
                            
                            # 提取新闻来源（通常在日期前面或后面）
                            # 格式可能是："海报新闻 2024-03-15" 或 "2024-03-15 海报新闻"
                            source_match = re.search(r'([^\d\s]{2,10})\s+\d{4}[-年]\d{1,2}[-月]\d{1,2}', date_text)
                            if source_match:
                                source_wz = source_match.group(1).strip()
                            else:
                                # 尝试另一种格式：日期后面的来源
                                source_match = re.search(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}\s+([^\d\s]{2,10})', date_text)
                                if source_match:
                                    source_wz = source_match.group(1).strip()
                        
                        # 如果没有找到来源，尝试从其他地方提取
                        if not source_wz:
                            # 尝试从标题下方的来源标签提取
                            source_elem = (
                                item.select_one('span.c-color-source') or
                                item.select_one('span[class*="source"]') or
                                item.select_one('a[class*="source"]')
                            )
                            if source_elem:
                                source_wz = source_elem.get_text(strip=True)
                        
                        # 清理来源名称
                        if source_wz:
                            source_wz = re.sub(r'\s+', '', source_wz)  # 移除空格
                            source_wz = source_wz.replace('小时前', '').replace('分钟前', '').replace('刚刚', '')

                        # 时间过滤（rtt=4按时间排序，超出范围则计数）
                        item_dt = parse_date(date_str)
                        if start_date and item_dt and item_dt < start_date:
                            out_of_range_count += 1
                            continue
                        if end_date and item_dt and item_dt > end_date:
                            out_of_range_count += 1
                            continue

                        # 用已打开的driver获取正文，绕过百度安全验证
                        content = self._fetch_article_content(driver, link, date_str)
                        date_str = content[1] if content[1] else date_str
                        content = content[0]

                        results.append({
                            'source': self.SOURCE_NAME,
                            'source_wz': source_wz,
                            'title': title,
                            'content': content,
                            'time': normalize_date(date_str),
                            'keyword': keyword,
                            'url': link,
                        })
                        page_count += 1
                        time.sleep(REQUEST_DELAY)

                    except Exception as e:
                        self.logger.debug(f"解析条目失败: {e}")
                        continue

                self.logger.info(
                    f"第{page}页获取 {page_count} 条（重复 {duplicate_count}），总计: {len(results)}"
                )

                if page_count == 0 and duplicate_count == 0:
                    consecutive_empty += 1
                    self.logger.info(f"连续空页: {consecutive_empty}")
                else:
                    consecutive_empty = 0

                if duplicate_count > 0 and page_count == 0:
                    self.logger.info("大部分数据重复，停止爬取")
                    break

                # 按时间排序：本页所有条目都超出时间范围，提前停止
                if start_date and len(news_items) > 0 and out_of_range_count == len(news_items):
                    self.logger.info(f"第{page}页所有文章均超出时间范围，停止爬取")
                    break

                if len(results) >= max_results:
                    self.logger.info(f"已达目标数量({max_results})，停止爬取")
                    break

                if page >= 10:
                    self.logger.info("已达最大页数(10页)，停止爬取")
                    break

                page += 1
                time.sleep(2)

            self.logger.info(f"百度新闻爬取完成，共获取 {len(results)} 条")

        except Exception as e:
            self.logger.error(f"百度新闻爬取失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return results

    def _fetch_article_content(self, driver, link: str, date_str: str):
        """用Selenium driver获取文章正文和日期，返回 (content, date_str)"""
        content = ''
        try:
            driver.get(link)
            time.sleep(2)
            article_soup = BeautifulSoup(driver.page_source, 'html.parser')

            # 补充日期
            if not date_str:
                for meta_sel in [
                    'meta[property="article:published_time"]',
                    'meta[name="publishdate"]',
                    'meta[name="pubdate"]',
                ]:
                    meta = article_soup.select_one(meta_sel)
                    if meta and meta.get('content'):
                        m = re.search(r'(\d{4}-\d{2}-\d{2})', meta.get('content', ''))
                        if m:
                            date_str = m.group(1)
                            break

            # 优先 baijiahao SSR 容器
            content_elem = (
                article_soup.select_one('div#ssr-content-wrapper') or
                article_soup.select_one('div.index-module_articleWrap__Os-HM') or
                article_soup.select_one('div.bjh-article') or
                article_soup.select_one('article') or
                article_soup.select_one('div.article') or
                article_soup.select_one('div#article-content') or
                article_soup.select_one('div.content')
            )

            if not content_elem:
                candidates = [
                    (d, len(d.get_text(strip=True)))
                    for d in article_soup.select('div')
                    if len(d.get_text(strip=True)) > 200 and d.get('id') not in ('app',)
                ]
                if candidates:
                    content_elem = max(candidates, key=lambda x: x[1])[0]

            if content_elem:
                for tag in content_elem(['script', 'style', 'aside', 'nav', 'header', 'footer']):
                    tag.decompose()
                paragraphs = content_elem.select('p')
                p_content = '\n'.join(
                    p.get_text(strip=True) for p in paragraphs
                    if len(p.get_text(strip=True)) > 5
                )
                if len(p_content) > 100:
                    content = p_content
                else:
                    raw = content_elem.get_text(separator='\n', strip=True)
                    lines = [l.strip() for l in raw.splitlines()]
                    nav_exact = {'百度首页', '登录', '搜索', '复制', '关注', '官方账号', '举报', '分享', '收藏', '点赞'}
                    content_lines = [
                        line for line in lines
                        if len(line) > 10 and line not in nav_exact
                        and not re.match(r'^\d{4}-\d{2}-\d{2}', line)
                        and not re.match(r'^[0-9:. -]+$', line)
                    ]
                    content = '\n'.join(content_lines)
                content = re.sub(r'\n{3,}', '\n\n', content).strip()

        except Exception as e:
            self.logger.debug(f"获取正文失败: {e}")

        return content, date_str
