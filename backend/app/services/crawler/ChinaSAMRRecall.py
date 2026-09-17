#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国国家市场监督管理总局产品召回信息爬虫
目标网站：https://www.samrdprc.org.cn/
提取字段：产品名称、链接、时间、产品描述
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _normalize_date(date_str):
    """
    标准化中国日期格式
    常见格式: "YYYY-MM-DD", "YYYY/MM/DD", "YYYY.MM.DD"
    转换为: "YYYY-MM-DD"
    """
    if not date_str or not date_str.strip():
        return ""
    
    date_str = date_str.strip()
    
    try:
        # 替换分隔符为标准格式
        date_str = date_str.replace('/', '-').replace('.', '-')
        
        # 验证格式是否正确 YYYY-MM-DD
        import re
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str
        elif re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
            # 补齐月份和日期的前导零
            parts = date_str.split('-')
            year, month, day = parts[0], parts[1].zfill(2), parts[2].zfill(2)
            return f"{year}-{month}-{day}"
            
    except Exception as e:
        logger.warning(f"无法解析日期格式: {date_str}, 错误: {e}")
    
    return date_str  # 如果无法解析，返回原始字符串

def ChinaSAMRRecall(keyword: str, max_pages: int = 1) -> List[Dict[str, Any]]:
    """
    中国国家市场监督管理总局产品召回信息爬虫
    
    Args:
        keyword (str): 搜索关键词
        max_pages (int): 最大爬取页数，默认1页
        
    Returns:
        list: 包含召回信息的字典列表，格式符合数据库写入要求
    """
    if not keyword or not keyword.strip():
        logger.warning("搜索关键词为空")
        return []
    
    logger.info(f"开始爬取中国SAMR产品召回信息，关键词: {keyword}, 页数: {max_pages}")
    
    url = "https://www.samrdprc.org.cn/search/searchlist.jsp"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    }

    results = []
    for page in range(1, max_pages + 1):
        try:
            data = {
                "searchValue": keyword.strip(),
                "pageNo": page
            }
            resp = requests.post(url, headers=headers, data=data, timeout=15)
            resp.encoding = resp.apparent_encoding

            if resp.status_code != 200:
                logger.warning(f"请求失败，页面 {page}：HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # 解析搜索结果
            for li in soup.select("div.boxl_ul ul li"):
                try:
                    a_tag = li.select_one("a")
                    span_tag = li.select_one("span")
                    intro_tag = li.select_one("i.jianjie")

                    title = a_tag.get_text(strip=True) if a_tag else ""
                    link = a_tag["href"] if a_tag and a_tag.has_attr("href") else ""
                    raw_date = span_tag.get_text(strip=True) if span_tag else ""
                    intro = intro_tag.get_text(strip=True) if intro_tag else ""

                    # 确保链接是完整的URL
                    if link and not link.startswith('http'):
                        link = f"https://www.samrdprc.org.cn{link}" if link.startswith('/') else f"https://www.samrdprc.org.cn/{link}"

                    # 标准化日期格式
                    date = _normalize_date(raw_date) if raw_date else ""

                    # 按照recall表写入逻辑的格式返回数据
                    result = {
                        "产品名称": title,
                        "link": link,
                        "时间": date,
                        "生产厂家": "",  # SAMR网站通常不在搜索结果中提供生产厂家信息
                        "产品描述": intro,  # 使用简介作为产品描述
                        "产品缺陷": "",    # 可以后续通过详情页获取
                        "危害": "",        # 可以后续通过详情页获取
                        "bindWith": [keyword],  # 关键词绑定
                        # 保留原始字段用于调试
                        "_original": {
                            "title": title,
                            "link": link, 
                            "date": date,
                            "intro": intro
                        }
                    }
                    
                    if title:  # 只添加有标题的结果
                        results.append(result)
                        
                except Exception as e:
                    logger.warning(f"解析单个结果失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"爬取页面 {page} 失败: {e}")
            continue

    logger.info(f"爬取完成，获取到 {len(results)} 条数据")
    return results


if __name__ == "__main__":
    # 测试代码
    test_keywords = ["玩具", "儿童用品", "电动车"]
    
    for test_keyword in test_keywords:
        print(f"\n=== 测试关键词: '{test_keyword}' ===")
        records = ChinaSAMRRecall(test_keyword, max_pages=1)
        for record in records[:3]:  # 只显示前3条结果
            print(f"产品名称: {record['产品名称']}")
            print(f"链接: {record['link']}")
            print(f"时间: {record['时间']}")
            print(f"产品描述: {record['产品描述'] or '未提供'}")
            print("-" * 50)
        print(f"✅ 抓取完成，已获取 {len(records)} 条数据")
