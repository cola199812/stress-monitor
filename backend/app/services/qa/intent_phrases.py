from __future__ import annotations

import re
from typing import Literal

Intent = Literal['allergens', 'symptoms', 'products', 'literature', 'news', 'recall', 'generic']


# 规则短语（支持斜杠组合）
ALLERGEN_PATTERNS = [
    r"成分/过敏原",
    r"过敏原/成分",
    r"成分",
    r"过敏原",
    r"致敏物",
    r"配方",
    r"材料",
    r"主要成分",
    r"常见成分",
]

SYMPTOM_PATTERNS = [
    r"症状",
    r"危害",
    r"风险",
    r"不良反应",
    r"副作用",
    r"可能引发",
    r"会引发",
    r"会造成",
    r"可能造成",
]

PRODUCT_PATTERNS = [
    r"代表产品",
    r"相关产品",
    r"有哪些产品",
    r"商品",
    r"品牌",
    r"型号",
]

LITERATURE_PATTERNS = [
    r"文献",
    r"论文",
    r"研究",
    r"相关研究",
    r"学术文献",
    r"科研资料",
    r"参考文献",
    r"佐证文献",
    r"研究报告",
]

NEWS_PATTERNS = [
    r"新闻",
    r"报道",
    r"媒体报道",
    r"相关新闻",
    r"新闻报道",
    r"资讯",
    r"消息",
]

RECALL_PATTERNS = [
    r"召回",
    r"召回信息",
    r"产品召回",
    r"召回通知",
    r"召回公告",
    r"缺陷",
    r"安全隐患",
    r"质量问题",
]


def detect_intent_by_phrases(question: str) -> Intent | None:
    s = (question or '').strip()
    # 按优先级检测意图：过敏原 > 症状 > 文献 > 新闻 > 召回 > 产品
    for p in ALLERGEN_PATTERNS:
        if re.search(p, s):
            return 'allergens'
    for p in SYMPTOM_PATTERNS:
        if re.search(p, s):
            return 'symptoms'
    for p in LITERATURE_PATTERNS:
        if re.search(p, s):
            return 'literature'
    for p in NEWS_PATTERNS:
        if re.search(p, s):
            return 'news'
    for p in RECALL_PATTERNS:
        if re.search(p, s):
            return 'recall'
    for p in PRODUCT_PATTERNS:
        if re.search(p, s):
            return 'products'
    return None
