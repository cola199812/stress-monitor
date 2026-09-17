#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度新闻爬虫：抓取百度新闻搜索结果
目标：https://www.baidu.com/s?ie=utf-8&medium=0&rtt=1&bsst=1&rsv_dl=news_t_sk&cl=2&wd=keyword&tn=news
提取字段：标题、链接、发布时间、摘要
"""

import os
import logging
import re
import time
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _normalize_baidu_date(date_str):
    """标准化百度日期格式，返回 YYYY-MM-DD"""
    if not date_str or not date_str.strip():
        return ""
    date_str = date_str.strip()
    current_date = datetime.now()
    try:
        if "小时前" in date_str:
            match = re.search(r'(\d+)小时前', date_str)
            if match:
                hours = int(match.group(1))
                target_date = current_date.replace(hour=current_date.hour - hours)
                return target_date.strftime('%Y-%m-%d')
        if "天前" in date_str:
            match = re.search(r'(\d+)天前', date_str)
            if match:
                days = int(match.group(1))
                target_date = current_date.replace(day=current_date.day - days)
                return target_date.strftime('%Y-%m-%d')
        if "昨天" in date_str:
            target_date = current_date.replace(day=current_date.day - 1)
            return target_date.strftime('%Y-%m-%d')
        if "前天" in date_str:
            target_date = current_date.replace(day=current_date.day - 2)
            return target_date.strftime('%Y-%m-%d')
        if re.match(r'\d{4}年\d{1,2}月\d{1,2}日', date_str):
            match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
            if match:
                year, month, day = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        if re.match(r'\d{1,2}月\d{1,2}日', date_str):
            match = re.match(r'(\d{1,2})月(\d{1,2})日', date_str)
            if match:
                month, day = match.groups()
                year = current_date.year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except Exception as e:
        logger.warning(f"无法解析百度日期格式: {date_str}, 错误: {e}")
    return date_str

def _setup_chrome_driver():
    """设置Chrome驱动器"""
    options = Options()
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36')
    options.add_argument('--headless')
    service = Service()
    return webdriver.Chrome(service=service, options=options)

def fetch_baidu_news(keyword, max_pages=1, max_results=5):
    """获取百度新闻搜索结果"""
    if not keyword or not keyword.strip():
        logger.warning("搜索关键词为空")
        return []
    driver = None
    results = []
    try:
        driver = _setup_chrome_driver()
        search_url = f"https://www.baidu.com/s?&wd={keyword}"
        logger.info(f"开始访问百度搜索: {search_url}")
        driver.get(search_url)
        time.sleep(4)

        page_count = 0
        while len(results) <= max_results:
            page_count += 1
            logger.info(f"正在处理第 {page_count} 页")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            news_items = soup.select('.result-op.c-container.xpath-log.new-pmd') or \
                         soup.select('.result.c-container') or \
                         soup.select('[data-log]')
            if not news_items:
                news_items = soup.select('div[class*="result"]')

            page_results = 0
            for item in news_items:
                try:
                    title_elem = item.select('h3 a') or item.select('a[data-click]') or item.select('h3')
                    if not title_elem:
                        continue
                    title = title_elem[0].get_text(strip=True).replace('\n', ' ')
                    link = title_elem[0].get('href', '') if title_elem[0].name == 'a' else ''
                    date_elem = item.select('.c-color-gray2.c-font-normal.c-gap-right-xsmall') or \
                                item.select('[class*="time"]') or \
                                item.select('[class*="date"]')
                    raw_date = date_elem[0].get_text(strip=True) if date_elem else ''
                    formatted_date = _normalize_baidu_date(raw_date)
                    abstract_elem = item.select('.c-font-normal.c-color-text') or \
                                    item.select('[class*="abstract"]') or \
                                    item.select('p')
                    abstract = abstract_elem[0].get_text(strip=True).replace('\n', ' ') if abstract_elem else ''
                    if title and len(title) > 5:
                        result = {
                            "产品名称": title,
                            "link": link,
                            "时间": formatted_date,
                            "生产厂家": "",
                            "产品描述": abstract[:500] if abstract else "",
                            "产品缺陷": "",
                            "危害": "",
                            "_original": {
                                "title": title,
                                "link": link,
                                "raw_date": raw_date,
                                "formatted_date": formatted_date,
                                "abstract": abstract
                            }
                        }
                        results.append(result)
                        page_results += 1
                        if len(results) >= max_results:
                            break
                except Exception as e:
                    logger.warning(f"解析新闻条目时出错: {e}")
                    continue
            logger.info(f"第 {page_count} 页获取到 {page_results} 条结果")
            if page_results == 0 or len(results) >= max_results:
                break
            try:
                next_buttons = driver.find_elements(By.XPATH, '//a[contains(@class, "n")]')
                if next_buttons:
                    next_buttons[-1].click()
                    time.sleep(4)
                else:
                    logger.info("未找到下一页按钮，停止翻页")
                    break
            except Exception as e:
                logger.warning(f"翻页失败: {e}")
                break

        logger.info(f"百度新闻爬取完成，共获取 {len(results)} 条结果")
        return results
    except Exception as e:
        logger.error(f"百度新闻爬取失败: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def BaiduNewsRecall(keyword):
    """百度新闻召回信息爬虫"""
    if not keyword or not keyword.strip():
        logger.warning("搜索关键词为空")
        return []
    logger.info(f"开始爬取百度信息，关键词: {keyword}")
    max_retries = 2
    for attempt in range(max_retries):
        try:
            results = fetch_baidu_news(keyword.strip(), max_pages=2, max_results=20)
            if results:
                news_list = []
                for i, result in enumerate(results):
                    # 将百度新闻的数据格式转换为与其他爬虫一致的格式
                    item = {
                        'id': str(i+1).zfill(4),
                        'NewsTitle': result.get('_original', {}).get('title', ''),
                        'NewsUrl': result.get('_original', {}).get('link', ''),
                        'PublishTime': result.get('_original', {}).get('formatted_date', ''),
                        'Abstract': result.get('_original', {}).get('abstract', ''),
                        'bindWith': [keyword] if keyword else []
                    }
                    news_list.append(item)
                logger.info(f"爬取完成，获取到 {len(news_list)} 条数据")
                return news_list
            else:
                logger.warning(f"第 {attempt + 1} 次尝试未获取到数据")
        except Exception as e:
            logger.error(f"百度新闻爬取失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logger.error("百度爬取最终失败")
                return []
    return []

if __name__ == '__main__':
    # 测试代码（只跑，不输出）
    test_keywords = ["驱蚊花露水+过敏"]
    for test_keyword in test_keywords:
        BaiduNewsRecall(test_keyword)
