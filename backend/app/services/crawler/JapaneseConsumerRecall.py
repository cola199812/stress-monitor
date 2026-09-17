from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import logging

def JapaneseConsumerRecall(keyword: str) -> List[Dict[str, Any]]:
    url = "https://www.recall.caa.go.jp/result/index.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/119.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.recall.caa.go.jp/result/",
    }
    payload = {
        "search": keyword,
        "viewCount": 15,
        "screenkbn": "01",
        "category": 4,
        "viewCountdden": 15,
        "portarorder": 0,
        "actionorder": 0,
        "pagingHidden": "",
    }

    resp = requests.post(url, headers=headers, data=payload)
    if resp.status_code != 200:
        logging.warning(f"请求失败: HTTP {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    results: List[Dict[str, Any]] = []
    rows = soup.select("div.search_result_main table tr")
    # print(f"DEBUG: 找到 {len(rows)} 行 <tr>")

    for row in rows:
        cols = row.find_all("td")
        if not cols or len(cols) < 5:
            continue  # 跳过表头或不完整的行

        debug_text = [c.get_text(strip=True) for c in cols]
        # print("DEBUG 行内容:", debug_text)

        category = cols[0].get_text(strip=True)

        img_tag = cols[1].select_one("a")
        image_url = (
            "https://www.recall.caa.go.jp" + img_tag["href"] if img_tag else ""
        )

        title_tag = cols[2].select_one("a")
        title = title_tag.get_text(strip=True) if title_tag else ""
        link = (
            "https://www.recall.caa.go.jp" + title_tag["href"] if title_tag else ""
        )

        publish_date = cols[3].get_text(strip=True)
        action_date = cols[4].get_text(strip=True)

        record = {
            "category": category,
            "image": image_url,
            "title": title,
            "link": link,
            "publish_date": publish_date,
            "action_date": action_date,
        }
        results.append(record)

    return results


if __name__ == "__main__":
    res = JapaneseConsumerRecall("Zebra Japan「ライト付きカチューシャ（キッズ用）」")
    # print("最终结果:", res)
