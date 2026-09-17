#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国新闻网爬虫 - 解析 JavaScript 中的 JSON 数据
"""

import re
import time
import html
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

try:
    from .base import parse_date, normalize_date, fetch_article_content_and_date, COMMON_HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY
except ImportError:
    from base import parse_date, normalize_date, fetch_article_content_and_date, COMMON_HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY

logger = logging.getLogger(__name__)


class ChinaNewsCrawler:
    """中国新闻网爬虫"""

    SOURCE_NAME = '中国新闻网'

    def __init__(self):
        self.logger = logger

    def crawl(self, keyword: str, max_results: int = 50,
              start_date: Optional[datetime] = None,
              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """爬取中国新闻网"""
        results = []
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 3
        seen_urls: set = set()
        empty_pages = 0

        self.logger.info(f"开始爬取中国新闻网: 关键词={keyword}")

        try:
            while len(results) < max_results and consecutive_failures < max_consecutive_failures:
                search_url = 'https://sou.chinanews.com/search/news'

                post_data = {
                    'q': keyword,
                    'searchField': 'all',
                    'sortType': 'time',
                    'dateType': 'all',
                    'startDate': start_date.strftime('%Y-%m-%d') if start_date else '',
                    'endDate': end_date.strftime('%Y-%m-%d') if end_date else '',
                    'channel': 'all',
                    'editor': '',
                    'shouQiFlag': '',
                    'pageNum': page,
                }

                self.logger.info(f"访问中新网第{page}页")

                headers = COMMON_HEADERS.copy()
                headers['Referer'] = 'https://sou.chinanews.com/search.do'
                headers['Content-Type'] = 'application/x-www-form-urlencoded'

                resp = requests.post(search_url, data=post_data, headers=headers, timeout=REQUEST_TIMEOUT)

                if resp.status_code != 200:
                    self.logger.warning(f"中新网第{page}页请求失败，状态码: {resp.status_code}")
                    consecutive_failures += 1
                    time.sleep(2)
                    continue

                consecutive_failures = 0

                try:
                    docArr_match = re.search(r'var docArr = (\[.*?\]);', resp.text, re.DOTALL)
                    if not docArr_match:
                        self.logger.warning(f"中新网第{page}页未找到docArr数据")
                        consecutive_failures += 1
                        page += 1
                        continue

                    news_data = json.loads(docArr_match.group(1))

                    if not news_data:
                        empty_pages += 1
                        self.logger.info(f"中新网第{page}页无数据，连续空页: {empty_pages}")
                        if empty_pages >= 2:
                            self.logger.info("中新网连续2页无数据，停止爬取")
                            break
                        page += 1
                        continue

                    empty_pages = 0
                    self.logger.info(f"中新网第{page}页找到 {len(news_data)} 个新闻条目")
                    page_count = 0
                    duplicate_count = 0
                    out_of_date_count = 0

                    for item in news_data:
                        if len(results) >= max_results:
                            break

                        try:
                            title = item.get('title', '').strip()
                            url = item.get('url', '').strip()
                            pubtime = item.get('pubtime', '') or item.get('createtime', '')
                            content_snippet = item.get('content_without_tag', '').strip()

                            title = re.sub(r'<[^>]+>', '', title)
                            title = html.unescape(title).strip()
                            content_snippet = re.sub(r'<[^>]+>', '', content_snippet)
                            content_snippet = html.unescape(content_snippet).strip()

                            if not title or not url or len(title) < 5:
                                continue

                            if not url.startswith('http'):
                                if url.startswith('//'):
                                    url = 'https:' + url
                                elif url.startswith('/'):
                                    url = 'https://www.chinanews.com.cn' + url
                                else:
                                    url = 'https://www.chinanews.com.cn/' + url

                            if url in seen_urls:
                                duplicate_count += 1
                                continue
                            seen_urls.add(url)

                            item_dt = parse_date(pubtime)
                            if start_date and item_dt and item_dt < start_date:
                                out_of_date_count += 1
                                continue
                            if end_date and item_dt and item_dt > end_date:
                                continue

                            full_content = ''
                            try:
                                full_content, detailed_date = fetch_article_content_and_date(url, 'chinanews')
                                if not full_content and content_snippet:
                                    full_content = content_snippet
                                if detailed_date and not pubtime:
                                    pubtime = detailed_date
                            except Exception as e:
                                self.logger.debug(f"获取中新网正文失败: {e}")
                                full_content = content_snippet

                            results.append({
                                'source': self.SOURCE_NAME,
                                'title': title,
                                'content': full_content,
                                'time': normalize_date(pubtime),
                                'keyword': keyword,
                                'url': url,
                            })
                            page_count += 1
                            time.sleep(REQUEST_DELAY)

                        except Exception as e:
                            self.logger.debug(f"解析中新网条目失败: {e}")
                            continue

                    self.logger.info(
                        f"中新网第{page}页获取 {page_count} 条，重复 {duplicate_count} 条，超出时间范围 {out_of_date_count} 条，当前总数: {len(results)}"
                    )

                    if start_date and out_of_date_count >= len(news_data) * 0.8 and len(news_data) >= 5:
                        self.logger.info(f"中新网第{page}页大部分数据({out_of_date_count}/{len(news_data)})早于起始日期，停止爬取")
                        break

                    if duplicate_count > 0 and page_count == 0 and duplicate_count >= len(news_data) * 0.8:
                        self.logger.info(f"中新网第{page}页大部分数据重复，停止爬取")
                        break

                    consecutive_failures = 0

                    if len(news_data) < 10:
                        self.logger.info(f"中新网第{page}页数据量({len(news_data)})少于预期，可能已到最后一页")
                        break

                    if len(results) >= max_results:
                        self.logger.info(f"中新网已达到目标数量({max_results})，停止爬取")
                        break

                except json.JSONDecodeError as e:
                    self.logger.warning(f"中新网第{page}页JSON解析失败: {e}")
                    consecutive_failures += 1
                except Exception as e:
                    self.logger.warning(f"中新网第{page}页处理失败: {e}")
                    consecutive_failures += 1

                page += 1
                time.sleep(2)

                if page > 50:
                    self.logger.warning("中新网达到最大页数限制(50页)")
                    break

            self.logger.info(f"中国新闻网爬取完成，共获取 {len(results)} 条")

        except Exception as e:
            self.logger.error(f"中国新闻网爬取失败: {e}")

        return results
