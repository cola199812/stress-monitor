#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻爬虫共享工具函数和配置常量
"""

import re
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup

# ==================== 配置常量 ====================
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 1.0

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> Optional[datetime]:
    """改进的日期解析函数，支持更多格式"""
    if not date_str:
        return None

    date_str = date_str.strip()
    date_str = re.sub(r'\s+', ' ', date_str)

    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d',
        '%Y年%m月%d日 %H:%M:%S',
        '%Y年%m月%d日 %H:%M',
        '%Y年%m月%d日',
        '%m月%d日 %H:%M',
        '%m月%d日',
        '%Y.%m.%d %H:%M:%S',
        '%Y.%m.%d %H:%M',
        '%Y.%m.%d',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y',
        '%Y%m%d %H:%M:%S',
        '%Y%m%d',
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if '%Y' not in fmt:
                parsed = parsed.replace(year=datetime.now().year)
            return parsed
        except ValueError:
            continue

    try:
        if 'T' in date_str:
            date_str_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', date_str)
            date_str_clean = re.sub(r'Z$', '', date_str_clean)
            return datetime.fromisoformat(date_str_clean)
    except Exception:
        pass

    now = datetime.now()
    relative_patterns = [
        (r'(\d+)\s*分钟前', 'minutes'),
        (r'(\d+)\s*小时前', 'hours'),
        (r'(\d+)\s*天前', 'days'),
        (r'(\d+)\s*周前', 'weeks'),
        (r'(\d+)\s*月前', 'months'),
        (r'(\d+)\s*年前', 'years'),
    ]

    for pattern, unit in relative_patterns:
        match = re.search(pattern, date_str)
        if match:
            value = int(match.group(1))
            if unit == 'minutes':
                return now - timedelta(minutes=value)
            elif unit == 'hours':
                return now - timedelta(hours=value)
            elif unit == 'days':
                return now - timedelta(days=value)
            elif unit == 'weeks':
                return now - timedelta(weeks=value)
            elif unit == 'months':
                return now - timedelta(days=value * 30)
            elif unit == 'years':
                return now - timedelta(days=value * 365)

    if '昨天' in date_str:
        time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
        yesterday = now - timedelta(days=1)
        if time_match:
            hour, minute = map(int, time_match.groups())
            return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return yesterday.replace(hour=12, minute=0, second=0, microsecond=0)
    elif '前天' in date_str:
        time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
        day_before = now - timedelta(days=2)
        if time_match:
            hour, minute = map(int, time_match.groups())
            return day_before.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return day_before.replace(hour=12, minute=0, second=0, microsecond=0)
    elif '今天' in date_str:
        time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
        if time_match:
            hour, minute = map(int, time_match.groups())
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return now
    elif '刚刚' in date_str:
        return now

    date_pattern = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', date_str)
    if date_pattern:
        year, month, day = date_pattern.groups()
        try:
            time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', date_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                second = int(time_match.group(3)) if time_match.group(3) else 0
                return datetime(int(year), int(month), int(day), hour, minute, second)
            else:
                return datetime(int(year), int(month), int(day))
        except Exception:
            pass

    return None


def normalize_date(date_str: str) -> str:
    """标准化日期格式 - 只保留年月日"""
    if not date_str:
        return ""
    dt = parse_date(date_str)
    if dt:
        return dt.strftime('%Y-%m-%d')
    return date_str


def fetch_article_content_and_date(url: str, source: str) -> tuple:
    """获取新闻正文内容和日期，适配PC/移动端"""
    content = ''
    page_date = None

    try:
        headers = COMMON_HEADERS.copy()
        headers['Referer'] = 'https://www.sina.com.cn/'

        session = requests.Session()
        session.max_redirects = 5

        resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            return '', None

        if resp.encoding and resp.encoding.upper() not in ('ISO-8859-1', 'WINDOWS-1252'):
            try:
                html_bytes = resp.content
                soup = BeautifulSoup(html_bytes, 'html.parser')
            except Exception:
                soup = BeautifulSoup(resp.text, 'html.parser')
        else:
            html_bytes = resp.content
            meta_charset = None
            charset_match = re.search(
                rb'<meta[^>]+charset[="\s]+([A-Za-z0-9_\-]+)',
                html_bytes[:4096], re.IGNORECASE
            )
            if charset_match:
                meta_charset = charset_match.group(1).decode('ascii', errors='ignore').strip()
            if meta_charset:
                resp.encoding = meta_charset
            else:
                resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

        final_url = resp.url

        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publishdate"]',
            'meta[name="pubdate"]',
            'meta[name="publish_date"]',
            'time[datetime]',
            '.date',
            '.time',
            '.pub-date',
            '.publish-time',
            '#pub_date',
            '.art_time',
            '.news-time',
            '.source-time',
        ]

        for selector in date_selectors:
            elements = soup.select(selector)
            for elem in elements:
                date_value = (elem.get('datetime') or
                              elem.get('content') or
                              elem.get('value') or
                              elem.get_text(strip=True))
                if date_value and re.search(r'\d', date_value):
                    parsed_dt = parse_date(date_value)
                    if parsed_dt:
                        page_date = date_value
                        break
            if page_date:
                break

        if not page_date:
            date_match = re.search(r'/(\d{4})[/-]?(\d{2})[/-]?(\d{2})/', final_url)
            if date_match:
                year, month, day = date_match.groups()
                page_date = f"{year}-{month}-{day}"

        content_selectors = [
            'div.article', 'div#artibody', 'div#article_content',
            'div.rm_txt_con', 'div.box_con',
            'div.left_zw', 'div.content_left',
            'div#content', 'div.content',
            'div.article-body', 'div.news-content',
            'article', 'div.art_content', 'div.text',
            'div.article-text', 'div.article-detail',
            'div.content-article', 'div.main-content',
            'div.post-content', 'div.entry-content',
        ]

        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            max_text_length = 0
            candidate_elem = None
            for div in soup.select('div'):
                text = div.get_text(strip=True)
                if len(text) > max_text_length and len(text) > 200:
                    classes = ' '.join(div.get('class', [])).lower()
                    id_attr = div.get('id', '').lower()
                    if ('comment' not in classes and 'nav' not in classes and
                            'sidebar' not in classes and 'footer' not in classes and
                            'header' not in classes and 'menu' not in classes and
                            'comment' not in id_attr and 'nav' not in id_attr):
                        candidate_elem = div
                        max_text_length = len(text)
            if candidate_elem and max_text_length > 300:
                content_elem = candidate_elem

        if content_elem:
            for element in content_elem(['script', 'style', 'iframe', 'nav', 'aside', 'header', 'footer']):
                element.decompose()
            ad_selectors = ['.ad', '.advertisement', '.ads', '.promotion', '.related',
                            '.recommend', '.share', '.comment', '.hot-news', '.relevant']
            for ad_selector in ad_selectors:
                for ad in content_elem.select(ad_selector):
                    ad.decompose()
            paragraphs = content_elem.select('p')
            if paragraphs:
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 5:
                        if not any(kw in text for kw in ['版权声明', '免责声明', '责任编辑', '来源：']):
                            content_parts.append(text)
                content = '\n'.join(content_parts)
            else:
                content = content_elem.get_text(separator='\n', strip=True)

            content = re.sub(r'\n{3,}', '\n\n', content)
            content = re.sub(r'【.*?】', '', content)
            content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
            content = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]', '', content)
            content = re.sub(r' {2,}', ' ', content)
            content = content.strip()

        return content, page_date

    except Exception as e:
        logger.debug(f"获取正文失败 {url}: {e}")
        return '', None


def clean_text_for_excel(text: str) -> str:
    """清理文本用于Excel导出，移除不可打印字符和控制字符"""
    if not text:
        return ''
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]', '', text)
    text = re.sub(r'[\ufffe\uffff]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()
