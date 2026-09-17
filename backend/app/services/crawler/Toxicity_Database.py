import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import re

def sanitize_filename(filename):
    return "".join(c for c in filename if c not in r'\/:*?"<>|')

def save_data(name, data):
    sanitized_name = sanitize_filename(name)
    filename = sanitized_name.replace(',', '_').replace(' ', '') + '.json'
    file_path = os.path.join("./", filename)

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    print(f"保存 {name} 的数据到 {file_path}")
    return file_path

def _build_session() -> requests.Session:
    """构建带有重试的 Session"""
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def fetch_page(url, headers, session: requests.Session | None = None, timeout: int = 15):
    sess = session or _build_session()
    # 避免部分站点的 keep-alive/SSL 问题
    local_headers = dict(headers or {})
    local_headers.setdefault('Connection', 'close')
    try:
        response = sess.get(url, headers=local_headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response
    except requests.exceptions.SSLError as e:
        # 遇到 SSL EOF 等问题时，退化为 verify=False 再试一次
        try:
            response = sess.get(url, headers=local_headers, timeout=timeout, verify=False)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response
        except Exception:
            raise e

def parse_chemical_info(text):
    data = {}

    # 提取基础信息
    data['RTECS编号'] = re.search(r'RTECS NUMBER\s*:\s*(.+)', text).group(1).strip() if re.search(r'RTECS NUMBER\s*:\s*(.+)', text) else '未知'
    data['化学名称'] = re.search(r'CHEMICAL NAME\s*:\s*([\s\S]*?)\n', text).group(1).strip() if re.search(r'CHEMICAL NAME\s*:\s*([\s\S]*?)\n', text) else '未知'
    data['CAS注册号'] = re.search(r'CAS REGISTRY NUMBER\s*:\s*(.+)', text).group(1).strip() if re.search(r'CAS REGISTRY NUMBER\s*:\s*(.+)', text) else '未知'
    data['BEILSTEIN参考号'] = re.search(r'BEILSTEIN REFERENCE NO.\s*:\s*(.+)', text).group(1).strip() if re.search(r'BEILSTEIN REFERENCE NO.\s*:\s*(.+)', text) else '未知'
    data['最后更新'] = re.search(r'LAST UPDATED\s*:\s*(.+)', text).group(1).strip() if re.search(r'LAST UPDATED\s*:\s*(.+)', text) else '未知'
    data['引用数据项'] = re.search(r'DATA ITEMS CITED\s*:\s*(.+)', text).group(1).strip() if re.search(r'DATA ITEMS CITED\s*:\s*(.+)', text) else '未知'
    data['分子式'] = re.search(r'MOLECULAR FORMULA\s*:\s*(.+)', text).group(1).strip() if re.search(r'MOLECULAR FORMULA\s*:\s*(.+)', text) else '未知'
    data['分子量'] = re.search(r'MOLECULAR WEIGHT\s*:\s*(.+)', text).group(1).strip() if re.search(r'MOLECULAR WEIGHT\s*:\s*(.+)', text) else '未知'
    data['WISWESSER线路标记'] = re.search(r'WISWESSER LINE NOTATION\s*:\s*(.+)', text).group(1).strip() if re.search(r'WISWESSER LINE NOTATION\s*:\s*(.+)', text) else '未知'
    data['化合物描述符'] = re.search(r'COMPOUND DESCRIPTOR\s*:\s*(.+)', text).group(1).strip() if re.search(r'COMPOUND DESCRIPTOR\s*:\s*(.+)', text) else '未知'

    # 提取同义词
    synonyms = re.search(r'SYNONYMS/TRADE NAMES\s*:\s*((?:\s*\*.*\n?)+)', text, re.DOTALL)
    if synonyms:
        data['同义词/商标名称'] = [syn.strip().lstrip('* ').strip() for syn in synonyms.group(1).split('\n') if syn.strip().startswith('* ')]
    else:
        data['同义词/商标名称'] = []

    hazard_data = re.search(r'HEALTH HAZARD DATA\s*(.*?)(?:\*\*\* END OF RECORD \*\*\*|\Z)', text, re.DOTALL)
    if hazard_data:
        hazard_text = hazard_data.group(1).strip()
        data['健康危害数据'] = []

        # 使用正则表达式提取每个实验记录
        experiments = re.split(r'\n(?=TYPE OF TEST)', hazard_text)
        for experiment in experiments:
            exp_data = {}
            exp_data['实验类型'] = re.search(r'TYPE OF TEST\s*:\s*(.+)', experiment).group(1).strip() if re.search(r'TYPE OF TEST\s*:\s*(.+)', experiment) else '未知'
            if exp_data['实验类型'] == '未知':
                continue
            exp_data['暴露途径'] = re.search(r'ROUTE OF EXPOSURE\s*:\s*(.+)', experiment).group(1).strip() if re.search(r'ROUTE OF EXPOSURE\s*:\s*(.+)', experiment) else '未知'
            exp_data['观察物种'] = re.search(r'SPECIES OBSERVED\s*:\s*(.+)', experiment).group(1).strip() if re.search(r'SPECIES OBSERVED\s*:\s*(.+)', experiment) else '未知'
            exp_data['duration'] = re.search(r'DOSE/DURATION\s*:\s*(.+)', experiment).group(1).strip() if re.search(r'DOSE/DURATION\s*:\s*(.+)', experiment) else '未知'
            exp_data['毒性效应'] = re.search(r'TOXIC EFFECTS\s*:\s*(.+)', experiment).group(1).strip() if re.search(r'TOXIC EFFECTS\s*:\s*(.+)', experiment) else '未知'
            exp_data['参考文献'] = re.search(r'REFERENCE\s*:\s*([\s\S]+?)(?=\n\s*\n|$)', experiment, re.DOTALL).group(1).replace('\r\n', ' ').strip() if re.search(r'REFERENCE\s*:\s*([\s\S]+?)(?=\n\s*\n|$)', experiment, re.DOTALL) else '未知'
            data['健康危害数据'].append(exp_data)
    else:
        data['健康危害数据'] = []

    return data


def parse_results_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    if "请输入至少4个字符。" in soup.text:
        print(f"警告: 页面包含提示: '请输入至少4个字符。'")
        return data
    for li in soup.find_all('li'):
        a_tag = li.find('a')
        if a_tag:
            href = 'https://www.drugfuture.com/toxic/' + a_tag.get('href')
            name = a_tag.get_text(strip=True)
            data[name] = href
    return data


def process_chemical(name, href, headers, session: requests.Session | None = None):
    try:
        page_response = fetch_page(href, headers, session=session)
        page_soup = BeautifulSoup(page_response.text, 'html.parser')
        pre = page_soup.find('pre')
        if pre is not None:
            text = pre.get_text()
        else:
            # 回退：直接使用全文文本，尽可能解析出信息
            text = page_soup.get_text("\n", strip=True)
        chemical_info = parse_chemical_info(text)
        return {'名称': name, '数据': chemical_info}
    except Exception as e:
        print(f"处理 {name} 时出错: {e}")
        return None


def search_chemical(search_term, type="precise"):
    url = 'https://www.drugfuture.com/toxic/search.aspx'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Referer': 'https://organchem.csdb.cn/scdb/default.htm?nCount=26396773'
    }

    data = {
        'SearchTerm': search_term,
        'Submit': '查询',
        'Restriction': type,  # fuzzy 或者 precise
    }

    session = _build_session()
    default_timeout = int(os.getenv('TOXICITY_REQUEST_TIMEOUT', '15'))
    response = session.post(url, headers=headers, data=data, timeout=default_timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding

    result_data = parse_results_page(response.text)
    data_list = []

    # 限制最大处理条目数，避免占用过多内存/IO
    max_items = int(os.getenv('TOXICITY_MAX_ITEMS', '20'))
    items = list(result_data.items())[:max_items] if result_data else []

    # 使用线程池处理每个链接（适当限制并发）
    max_workers = int(os.getenv('TOXICITY_MAX_WORKERS', '3'))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_chemical, name, href, headers, session) for name, href in items]
        i = 1
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                print(f"获取化学详情时出错: {e}")
                continue
            if not result:
                continue
            # 无论是否包含健康危害数据，均保存基础信息，避免全量丢失
            result["id"] = str(i).zfill(4)
            i += 1
            data_list.append(result)
    return data_list

