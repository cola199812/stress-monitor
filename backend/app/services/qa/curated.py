from __future__ import annotations

from typing import Dict, Tuple, Optional


_CURATED: Dict[str, Dict[str, str]] = {
    # 高频类别示例：驱蚊产品、空气清新剂、修正文具
    '驱蚊产品': {
        'allergens': (
            '驱蚊产品常见成分/可能致敏物包括：避蚊胺（DEET）、派卡瑞丁（Picaridin）、驱蚊酯（IR3535/BAAPE）、'
            '植物精油/香精（如柠檬烯、芳樟醇等）。不同配方差异较大，请以实际标签为准。'
        ),
        'symptoms': (
            '驱蚊产品可能引发的症状（因个体/用量/暴露而异）包括：皮肤刺激、过敏反应、眼鼻喉刺激、头痛/眩晕。'
        ),
        'products': (
            '代表产品可参考：花露水、防蚊喷雾、驱蚊液/贴/手环等（具体品牌视数据而定）。'
        ),
    },
    '空气清新剂': {
        'allergens': (
            '空气清新剂/香薰常见成分：乙醇、柠檬烯等萜类、邻苯二甲酸酯、挥发性有机物（VOCs）、香精等。'
        ),
        'symptoms': (
            '可能的症状：呼吸道刺激、皮肤刺激、头痛、恶心等；敏感人群应谨慎使用并注意通风。'
        ),
    },
    '修正文具': {
        'allergens': (
            '修正液/修正带类常见成分：有机溶剂（依配方而异）、树脂/颜料、香精等；请参考产品MSDS或标签。'
        ),
        'symptoms': (
            '可能的症状：呼吸道刺激、皮肤刺激、头痛、恶心、过敏反应等；建议在通风良好处使用。'
        ),
    },
}


_ALIASES = {
    '驱蚊液': '驱蚊产品',
    '驱蚊剂': '驱蚊产品',
    '防蚊喷雾': '驱蚊产品',
    '防蚊液': '驱蚊产品',
    '驱蚊': '驱蚊产品',
    '防蚊': '驱蚊产品',
    '驱蚊相关': '驱蚊产品',
    '香薰': '空气清新剂',
    '芳香剂': '空气清新剂',
    '修正液': '修正文具',
    '涂改液': '修正文具',
    '修正带': '修正文具',
}


def get_curated_answer(subject: Optional[str], intent: str) -> Tuple[Optional[str], Optional[str]]:
    """返回（匹配到的主类目, 答案文本）。未命中则均为 None。"""
    subj = (subject or '').strip()
    if not subj:
        return (None, None)
    key = _ALIASES.get(subj, subj)
    item = _CURATED.get(key)
    if not item:
        return (None, None)
    text = item.get(intent)
    if not text:
        return (key, None)
    return (key, text)


def canonicalize_subject(subject: Optional[str]) -> Optional[str]:
    s = (subject or '').strip()
    if not s:
        return None
    return _ALIASES.get(s, s if s in _CURATED else None)
