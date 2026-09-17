import requests
from urllib.parse import quote


def sina(keyword: str, pages: int = 1):
    results = []
    # 移动端搜索接口（JSONP 包裹）
    url = f'https://sapi.sina.cn/search/list?newsId=HB-1-snhs%2Findex_v2-search&page=1&newspage=0&keyword={quote(keyword)}&tab=news&sort=0&is_ec=0'
    try:
        resp = requests.get(url, timeout=10)
        text = resp.text or ''
        # 去掉 JSONP 包裹
        start = text.find('(')
        end = text.rfind(')')
        payload = text[start + 1:end] if (start != -1 and end != -1 and end > start) else text
        data = resp.json() if payload == text else __import__('json').loads(payload)
        feed = ((data or {}).get('data') or {}).get('feed') or []
        for item in feed:
            results.append({
                'title': item.get('title') or '',
                'link': item.get('link') or '',
                'date': item.get('showTimeStr') or '',
                'abstract': item.get('source') or '',
            })
    except Exception:
        return []
    return results


def netease(keyword: str, pages: int = 1):
    results = []
    url = f'https://gw.m.163.com/nc/api/v1/pc-wap/search?query={quote(keyword)}&size=20&from=wap&needPcUrl=true'
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json() or {}
        items = (data.get('data') or {}).get('result') or []
        for item in items:
            results.append({
                'title': item.get('title') or '',
                'link': item.get('pcUrl') or item.get('docUrl') or '',
                'date': item.get('ptime') or '',
                'abstract': item.get('source') or '',
            })
    except Exception:
        return []
    return results


