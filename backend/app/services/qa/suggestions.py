from __future__ import annotations

from typing import List
from app.services.qa.curated import canonicalize_subject


_TRIM_TOKENS = (
    '哪些', '什么', '哪种', '哪类', '哪一些', '哪些的', '什么的', '代表', '典型', '主要',
)


def _normalize_subject(s: str) -> str:
    if not s:
        return ''
    t = s.strip()
    # 去引号和前缀动词遗留内容
    for ch in ('"', '"', '"', "'"):
        t = t.replace(ch, '')
    for pfx in ('询问', '请问', '关于'):
        if t.startswith(pfx):
            t = t[len(pfx):].strip()
    # 去尾部疑问泛指词
    for tok in _TRIM_TOKENS:
        if t.endswith(tok):
            t = t[: -len(tok)].strip()
    # 去"相关/有关"等弱限定词
    for weak in ('相关', '有关'):
        if t.endswith(weak):
            t = t[: -len(weak)].strip()
    # 归一"的"
    if not t.endswith('的'):
        t = t
    # 规范化到已知主类（确保建议更可达）
    cano = canonicalize_subject(t)
    if cano:
        t = cano
    return t


def build_fallback_suggestions(subject: str | None, intent: str) -> List[str]:
    subj_raw = (subject or '').strip()
    subj = _normalize_subject(subj_raw)
    suggestions: List[str] = []
    if intent == 'symptoms':
        if subj:
            suggestions.append(f"{subj}的常见成分/过敏原有哪些？")
            suggestions.append(f"{subj}的代表产品有哪些？")
            suggestions.append("针对某一具体产品再问：可能引发哪些症状？")
        else:
            suggestions.append("先确认类别名称，例如：驱蚊产品、空气清新剂、修正文具…")
            suggestions.append("该类别的常见成分/过敏原有哪些？")
    elif intent == 'allergens':
        if subj:
            suggestions.append(f"{subj}的代表产品有哪些？")
            suggestions.append("这些成分可能引发哪些症状？")
        else:
            suggestions.append("尝试更具体的类别名称或品牌/型号")
    elif intent == 'products':
        if subj:
            suggestions.append(f"{subj}的常见成分/过敏原有哪些？")
            suggestions.append(f"{subj}可能引发哪些症状？")
        else:
            suggestions.append("先确认类别名称，再询问代表产品")
    else:
        if subj:
            suggestions.append(f"{subj}的常见成分/过敏原有哪些？")
            suggestions.append(f"{subj}可能引发哪些症状？")
        else:
            suggestions.append("先确认类别名称：如 修正文具/空气清新剂/驱蚊产品…")
    return suggestions
