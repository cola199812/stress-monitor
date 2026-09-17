#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网易新闻爬虫
"""

import time
import logging
from urllib.parse import quote
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

try:
    from .base import parse_date, normalize_date, fetch_article_content_and_date, COMMON_HEADERS, REQUEST_TIMEOUT
except ImportError:
    from base import parse_date, normalize_date, fetch_article_content_and_date, COMMON_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class NeteaseNewsCrawler:
    """网易新闻爬虫"""

    SOURCE_NAME = '网易新闻'

    def __init__(self):
        self.logger = logger

    def crawl(self, keyword: str, max_results: int = 50,
              start_date: Optional[datetime] = None,
              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """爬取网易新闻"""
        results = []

        try:
            url = (
                f'https://gw.m.163.com/nc/api/v1/pc-wap/search'
                f'?query={quote(keyword)}&size={max_results}&from=wap&needPcUrl=true'
            )
            resp = requests.get(url, headers=COMMON_HEADERS, timeout=REQUEST_TIMEOUT)

            if resp.status_code != 200:
                self.logger.warning(f"网易新闻请求失败: {resp.status_code}")
                return results

            data = resp.json() or {}
            items = (data.get('data') or {}).get('result') or []

            for item in items[:max_results]:
                link = item.get('pcUrl') or item.get('docUrl') or ''
                title = item.get('title') or ''
                date_str = item.get('ptime') or ''

                item_dt = parse_date(date_str)
                if start_date and item_dt and item_dt < start_date:
                    continue
                if end_date and item_dt and item_dt > end_date:
                    continue

                if not title or not link:
                    continue

                content = ''
                try:
                    content, _ = fetch_article_content_and_date(link, 'netease')
                except Exception:
                    pass

                results.append({
                    'source': self.SOURCE_NAME,
                    'title': title,
                    'content': content,
                    'time': normalize_date(date_str),
                    'keyword': keyword,
                    'url': link,
                })
                time.sleep(0.5)

            self.logger.info(f"网易新闻爬取完成，获取 {len(results)} 条")

        except Exception as e:
            self.logger.error(f"网易新闻爬取失败: {e}")

        return results
