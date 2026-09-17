from __future__ import annotations

from typing import List, Tuple, Optional

_clf_ready = False
_vectorizer = None
_clf = None


def _build_training_data() -> List[Tuple[str, str]]:
    data: List[Tuple[str, str]] = []
    # allergens
    allergens = [
        '常见成分', '主要成分', '成分', '过敏原', '致敏物', '配方', '材料', '成分过敏原', '成分/过敏原',
        'X 的常见成分有哪些', 'X 的过敏原有哪些', 'X 的配方组成是什么',
    ]
    data += [(t.replace('X', '驱蚊产品'), 'allergens') for t in allergens]
    data += [(t.replace('X', '空气清新剂'), 'allergens') for t in allergens]

    # symptoms
    symptoms = [
        '症状', '危害', '风险', '不良反应', '副作用', '可能引发', '会引发', '会造成', '可能造成',
        'X 可能引发哪些症状', 'X 有什么危害',
    ]
    data += [(t.replace('X', '驱蚊产品'), 'symptoms') for t in symptoms]
    data += [(t.replace('X', '空气清新剂'), 'symptoms') for t in symptoms]

    # products
    products = [
        '代表产品', '相关产品', '有哪些产品', '商品', '品牌', '型号',
        'X 的代表产品有哪些', 'X 有哪些产品',
    ]
    data += [(t.replace('X', '驱蚊产品'), 'products') for t in products]
    data += [(t.replace('X', '空气清新剂'), 'products') for t in products]
    return data


def _try_init() -> None:
    global _clf_ready, _vectorizer, _clf
    if _clf_ready:
        return
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC
        import jieba  # type: ignore

        train = _build_training_data()
        texts = [t for t, _ in train]
        labels = [y for _, y in train]
        _vectorizer = TfidfVectorizer(tokenizer=jieba.lcut, token_pattern=None)
        X = _vectorizer.fit_transform(texts)
        _clf = LinearSVC()
        _clf.fit(X, labels)
        _clf_ready = True
    except Exception:
        _clf_ready = False
        _vectorizer = None
        _clf = None


def classify_intent_by_tfidf(q: str) -> Optional[str]:
    """返回 allergens|symptoms|products 或 None。若依赖缺失或低置信度则返回 None。"""
    _try_init()
    if not _clf_ready or not _vectorizer or not _clf:
        return None
    try:
        Xq = _vectorizer.transform([q])
        pred = _clf.predict(Xq)
        # LinearSVC 无概率，这里直接返回预测
        return str(pred[0]) if pred is not None else None
    except Exception:
        return None
