"""
PubMed Official API Crawler
使用PubMed官方E-utilities API，避免403错误
"""

import requests
import time
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET


def _normalize_query_terms(value) -> List[str]:
    """Normalize a string or sequence of strings into a clean term list."""
    if value is None:
        return []

    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [str(value)]

    terms: List[str] = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        terms.append(text)
    return terms


def _build_title_abstract_group(terms) -> str:
    """Build a PubMed Title/Abstract query group joined by OR."""
    normalized_terms = _normalize_query_terms(terms)
    if not normalized_terms:
        return ""

    clauses = [f'"{term}"[Title/Abstract]' for term in normalized_terms]
    if len(clauses) == 1:
        return f"({clauses[0]})"
    return "(" + " OR ".join(clauses) + ")"


class PubMedAPICrawler:
    """
    使用PubMed官方E-utilities API的爬虫
    文档: https://www.ncbi.nlm.nih.gov/books/NBK25501/
    """
    
    def __init__(self, email: str = "your_email@example.com", tool: str = "literature_crawler"):
        """
        初始化PubMed API爬虫
        
        Args:
            email: 您的邮箱（PubMed要求提供）
            tool: 工具名称
        """
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = email
        self.tool = tool
        self.api_key = None  # 可选：申请API key可以提高请求限制
        
    def search_pubmed(
        self, 
        query: str, 
        max_results: int = 100,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[str]:
        """
        搜索PubMed并返回PMID列表
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            PMID列表
        """
        print(f"[PubMed API] 搜索查询: {query}")
        
        # 构建搜索URL
        search_url = f"{self.base_url}esearch.fcgi"
        
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'email': self.email,
            'tool': self.tool,
        }
        
        # 添加年份过滤
        if start_year and end_year:
            params['mindate'] = f"{start_year}/01/01"
            params['maxdate'] = f"{end_year}/12/31"
            params['datetype'] = 'pdat'
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pmid_list = data.get('esearchresult', {}).get('idlist', [])
            count = data.get('esearchresult', {}).get('count', '0')
            
            print(f"[PubMed API] 找到 {count} 条结果，返回前 {len(pmid_list)} 条")
            
            return pmid_list
            
        except Exception as e:
            print(f"[PubMed API] 搜索失败: {e}")
            return []
    
    def fetch_article_details(
        self, 
        pmid_list: List[str],
        study_type: Optional[str] = None
    ) -> List[Dict]:
        """
        获取文章详细信息
        
        Args:
            pmid_list: PMID列表
            
        Returns:
            文章详情列表
        """
        if not pmid_list:
            return []
        
        print(f"[PubMed API] 获取 {len(pmid_list)} 篇文献详情...")
        
        # 构建fetch URL
        fetch_url = f"{self.base_url}efetch.fcgi"
        
        # 分批处理（每次最多200个）
        batch_size = 200
        all_articles = []
        
        for i in range(0, len(pmid_list), batch_size):
            batch = pmid_list[i:i+batch_size]
            pmids = ','.join(batch)
            
            params = {
                'db': 'pubmed',
                'id': pmids,
                'retmode': 'xml',
                'email': self.email,
                'tool': self.tool,
            }
            
            if self.api_key:
                params['api_key'] = self.api_key
            
            try:
                response = requests.get(fetch_url, params=params, timeout=60)
                response.raise_for_status()
                
                # 解析XML
                articles = self._parse_xml_response(response.text, study_type)
                all_articles.extend(articles)
                
                print(f"[PubMed API] 已获取 {len(all_articles)}/{len(pmid_list)} 篇")
                
                # API限制：每秒最多3个请求（无API key）
                time.sleep(0.4)
                
            except Exception as e:
                print(f"[PubMed API] 获取详情失败: {e}")
                continue
        
        return all_articles
    
    def _parse_xml_response(self, xml_text: str, study_type: Optional[str] = None) -> List[Dict]:
        """
        解析XML响应
        
        Args:
            xml_text: XML文本
            
        Returns:
            文章列表
        """
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            
            for article_elem in root.findall('.//PubmedArticle'):
                try:
                    article_data = self._parse_article(article_elem, study_type)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    print(f"解析文章失败: {e}")
                    continue
            
        except Exception as e:
            print(f"解析XML失败: {e}")
        
        return articles
    
    def _parse_article(self, article_elem, study_type: Optional[str] = None) -> Optional[Dict]:
        """
        解析单篇文章
        
        Args:
            article_elem: XML元素
            
        Returns:
            文章字典
        """
        try:
            # PMID
            pmid_elem = article_elem.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ''
            
            # 标题
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ''
            
            # 摘要
            abstract_parts = []
            for abstract_text in article_elem.findall('.//AbstractText'):
                if abstract_text.text:
                    label = abstract_text.get('Label', '')
                    text = abstract_text.text
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            abstract = '\n'.join(abstract_parts)
            
            # 作者
            authors = []
            for author in article_elem.findall('.//Author'):
                lastname = author.find('LastName')
                forename = author.find('ForeName')
                if lastname is not None and forename is not None:
                    authors.append(f"{forename.text} {lastname.text}")
                elif lastname is not None:
                    authors.append(lastname.text)
            author_str = ', '.join(authors)
            
            # 日期
            pub_date = article_elem.find('.//PubDate')
            year = ''
            date_str = ''
            if pub_date is not None:
                year_elem = pub_date.find('Year')
                month_elem = pub_date.find('Month')
                day_elem = pub_date.find('Day')
                
                if year_elem is not None:
                    year = year_elem.text
                    date_parts = [year]
                    if month_elem is not None:
                        date_parts.append(month_elem.text)
                    if day_elem is not None:
                        date_parts.append(day_elem.text)
                    date_str = ' '.join(date_parts)
            
            # 期刊
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ''
            
            # 关键词
            keywords = []
            for keyword in article_elem.findall('.//Keyword'):
                if keyword.text:
                    keywords.append(keyword.text)
            keywords_str = ', '.join(keywords)
            
            # 文献类型 - 直接根据study_type设置
            if study_type == 'epidemiological':
                literature_type = 'epidemiology'
            elif study_type == 'in_vivo':
                literature_type = 'in-vivo'
            elif study_type == 'in_vitro':
                literature_type = 'in-vitro'
            else:
                literature_type = 'epidemiology'  # 默认为流行病学
            
            # 构建链接
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ''
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'author': author_str,
                'date': date_str,
                'year': int(year) if year.isdigit() else None,
                'journal': journal,
                'literature_type': literature_type,
                'keywords': keywords_str,
                'link': link,
                'source': 'pubmed',
                'has_abstract': bool(abstract and len(abstract) > 10),
                'abstract_length': len(abstract) if abstract else 0,
            }
            
        except Exception as e:
            print(f"解析文章元素失败: {e}")
            return None
    
    def crawl(
        self,
        query: str,
        max_results: int = 100,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        study_type: Optional[str] = None
    ) -> List[Dict]:
        """
        完整的爬取流程
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            文章列表
        """
        # 搜索获取PMID列表
        pmid_list = self.search_pubmed(query, max_results, start_year, end_year)
        
        if not pmid_list:
            print("[PubMed API] 未找到相关文献")
            return []
        
        # 获取文章详情
        articles = self.fetch_article_details(pmid_list, study_type)
        
        print(f"[PubMed API] 爬取完成，共获取 {len(articles)} 篇文献")
        
        return articles


def pubmed_api_crawler(
    chemical_source,
    adverse_reaction,
    study_type: Optional[str] = None,
    translator=None,
    max_results: int = 100,
    start_year: int = 2000,
    end_year: Optional[int] = None
) -> List[Dict]:
    """
    使用PubMed API的爬虫主函数
    
    Args:
        chemical_source: 化学物质名称列表（或单个字符串）
        adverse_reaction: 不良反应名称列表（或单个字符串）
        study_type: 研究类型
        translator: 翻译服务
        max_results: 最大结果数
        start_year: 开始年份
        end_year: 结束年份
        
    Returns:
        文章列表
    """
    from datetime import datetime
    
    if end_year is None:
        end_year = datetime.now().year
    
    # 构建三段式查询: chemical AND adverse AND frequency
    chemical_group = _build_title_abstract_group(chemical_source)
    adverse_group = _build_title_abstract_group(adverse_reaction)

    if not chemical_group or not adverse_group:
        raise ValueError("chemical_source and adverse_reaction must contain at least one non-empty keyword")

    query_parts = [chemical_group, adverse_group]
    
    # 添加研究类型
    if study_type == 'epidemiological':
        query_parts.append('(epidemiological[Title/Abstract] OR cohort[Title/Abstract] OR case-control[Title/Abstract])')
    elif study_type == 'in_vivo':
        query_parts.append('(in vivo[Title/Abstract] OR animal[Title/Abstract])')
    elif study_type == 'in_vitro':
        query_parts.append('(in vitro[Title/Abstract] OR cell culture[Title/Abstract])')
    
    # 排除特定类型
    exclusion = "NOT (meta-analysis[pt] OR review[pt] OR congress[pt] OR case reports[pt])"
    query = " AND ".join(query_parts) + f" {exclusion}"
    print(query)

    print(f"[PubMed API] query={query}")
    
    # 创建爬虫实例
    crawler = PubMedAPICrawler()
    
    # 爬取
    articles = crawler.crawl(query, max_results, start_year, end_year, study_type)
    
    # 翻译
    if translator and articles:
        print(f"[PubMed API] 开始翻译 {len(articles)} 篇文献...")
        
        titles = [a['title'] for a in articles]
        abstracts = [a['abstract'] for a in articles]
        
        titles_zh = translator.translate_batch(titles, 'en', 'zh-CN')
        abstracts_zh = translator.translate_batch(abstracts, 'en', 'zh-CN')
        
        for i, article in enumerate(articles):
            article['title_zh'] = titles_zh[i]
            article['abstract_zh'] = abstracts_zh[i]
        
        print(f"[PubMed API] 翻译完成")
    
    return articles
