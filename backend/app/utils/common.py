from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse, urlunparse


def clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    try:
        import html
        import re
        t = html.unescape(s)
        t = re.sub(r"<[^>]+>", "", t)
        t = re.sub(r"[\u200B-\u200D\uFEFF]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    except Exception:
        return s


def normalize_link(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        norm = p._replace(query='', fragment='', scheme=p.scheme.lower(), netloc=p.netloc.lower())
        result = urlunparse(norm)
        if result.endswith('/'):
            result = result[:-1]
        return result
    except Exception:
        return None


def parse_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, str):
            v = value.strip()
            for fmt in [
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M',
                '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    pass
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value))
    except Exception:
        return None
    return None


