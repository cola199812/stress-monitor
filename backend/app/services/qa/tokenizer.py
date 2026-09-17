from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import time
import re

from app.models import Category, Product
from app import db
from app.services.qa.curated import canonicalize_subject


_CACHE_TTL_SECONDS = 120


class _Lexicon:
    def __init__(self, categories: List[str], products: List[str], keywords: List[str]):
        self.categories = categories
        self.products = products
        self.keywords = keywords


_lexicon_cache: Tuple[float, _Lexicon] | None = None


_PUNCT = ('？', '?', '。', '.', '！', '!', '，', ',', '；', ';', '：', ':', '、')
_TRIM_TOKENS = ('哪些', '什么', '哪一些', '哪类', '哪种', '相关', '有关', '代表', '典型', '主要')


def _normalize_text(s: str) -> str:
    t = (s or '').strip()
    for ch in _PUNCT:
        t = t.replace(ch, '')
    # 清理斜杠组合（如 成分/过敏原）
    t = t.replace('/', '')
    # 去引号
    for q in ('"', '"', '"', "'"):
        t = t.replace(q, '')
    # 去前缀动词
    for pfx in ('询问', '请问', '关于'):
        if t.startswith(pfx):
            t = t[len(pfx):].strip()
    # 去尾部泛指与弱限定
    for suf in _TRIM_TOKENS:
        if t.endswith(suf):
            t = t[: -len(suf)].strip()
    return t


def _load_lexicon() -> _Lexicon:
    cats: List[str] = [c.name.strip() for c in db.session.query(Category).all() if (c.name or '').strip()]
    prods: List[str] = [p.name.strip() for p in db.session.query(Product).filter_by(status=1).all() if (p.name or '').strip()]
    kws: List[str] = [k.keyword.strip() for k in db.session.query(ProductKeyword).all() if (k.keyword or '').strip()]
    # 去重保序
    def _uniq(xs: List[str]) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out
    return _Lexicon(_uniq(cats), _uniq(prods), _uniq(kws))


def get_lexicon() -> _Lexicon:
    global _lexicon_cache
    now = time.time()
    if _lexicon_cache is None or (now - _lexicon_cache[0]) > _CACHE_TTL_SECONDS:
        _lexicon_cache = (now, _load_lexicon())
    return _lexicon_cache[1]


def extract_subject_via_lexicon(question: str, intent: str | None = None) -> Optional[str]:
    """从问题中用词表匹配出最可能的主题词。
    策略：先按类别→产品→关键词顺序进行包含匹配，选取长度最长者；再做别名规范化。
    """
    text = _normalize_text(question or '')
    if not text:
        return None
    lex = get_lexicon()

    def _best_match(candidates: List[str]) -> Optional[str]:
        best: Tuple[int, str] | None = None  # (length, term)
        for term in candidates:
            if not term:
                continue
            if term in text:
                ln = len(term)
                if (best is None) or (ln > best[0]):
                    best = (ln, term)
        return best[1] if best else None

    # 按优先级寻找
    for pool in (lex.categories, lex.products, lex.keywords):
        hit = _best_match(pool)
        if hit:
            cano = canonicalize_subject(hit) or hit
            return cano
    return None
