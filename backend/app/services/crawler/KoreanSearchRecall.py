import requests
import logging
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import quote

def KoreanSearchRecall(keyword: str, progress: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """
    韩国安全召回信息爬虫
    :param keyword: 搜索关键词（韩文或中文都行）
    :param progress: 可选的进度回调
    :return: 召回信息列表，每个元素是 dict
    """
    safe_kw = quote(keyword)
    base_url = "https://search.safetykorea.kr/sftk/sftktm02.do"
    params = {
        "occTypeName": "리콜정보ID",
        "instanceId": "x24lea0bt7-0",  # 可能会变，需要抓包确认
        "qry": keyword,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Referer": f"https://search.safetykorea.kr/tm/tmsearch.do?qry={safe_kw}",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    if progress:
        try:
            progress(f"[korea_recall] keyword={keyword} start")
        except Exception:
            pass

    resp = requests.get(base_url, params=params, headers=headers, verify=False)
    resp.encoding = "utf-8"

    if resp.status_code != 200:
        logging.warning(f"请求失败: HTTP {resp.status_code}")
        return []

    try:
        data = resp.json()
    except Exception:
        logging.warning("返回结果不是 JSON")
        return []

    results: List[Dict[str, Any]] = []
    for item in data:
        record = {}
        for k in ["UID", "RECALLTYPE", "COMPANYNAME", "PRODUCTNAME", "MODEL", "PUBLISHDATE"]:
            v = item.get(k, "").strip()
            if v:  # 只保留非空字段
                record[k] = v
        if record:
            results.append(record)

    msg = f"[korea_recall] keyword={keyword} done count={len(results)}"
    logging.info(msg)
    if progress:
        try:
            progress(msg)
        except Exception:
            pass

    return results


if __name__ == "__main__":
    res = KoreanSearchRecall("지우개")  # 例：搜索“橡皮擦”
    print(f"抓取到 {len(res)} 条")
    for r in res[:3]:
        print(r)
