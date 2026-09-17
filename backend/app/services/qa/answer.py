from __future__ import annotations

import logging
import re
from typing import Dict, Any, List

from app.services.qa.context import update_session
from app.services.model.nlp import get_vector_database

logger = logging.getLogger(__name__)


def _keyword_search_literature(question: str, limit: int = 5) -> List[Dict[str, str]]:
    """向量库不可用或无结果时的降级检索：在 literature 表按关键词匹配。

    中文问题先按标点/空白切词，过滤过短片段，再对标题/摘要/关键词做 ILIKE 匹配。
    返回 [{content, title, link}]，link 为文献原文链接，供前端「参考资料」跳转。
    """
    from sqlalchemy import or_
    from app.models import Literature

    # 提取候选词：按中英文标点与空白切分
    raw_tokens = [t for t in re.split(r'[\s,，。；;、.!?！？:：()（）\[\]【】"\'“”‘’\-—]+', question) if t]

    stopwords = {'什么', '哪些', '怎么', '如何', '为什么', '是什么', '有没有', '是否',
                 '请问', '一下', '这个', '那个', '以及', '或者', '还有', '请', '的', '吗', '呢',
                 'what', 'is', 'are', 'the', 'of', 'and', 'a', 'an', 'in', 'on', 'to', 'for', 'about'}

    terms = []
    seen = set()

    def add(t: str):
        t = t.strip().lower()
        if len(t) < 2 or t in stopwords or t in seen:
            return
        seen.add(t)
        terms.append(t)

    for t in raw_tokens:
        add(t)
        # 中文长串：补充 2-gram 提升召回（例如「花生过敏」→「花生」「生过」「过敏」）
        if re.search(r'[一-鿿]', t) and len(t) >= 3:
            for i in range(len(t) - 1):
                add(t[i:i + 2])

    if not terms:
        terms = [question]
    terms = terms[:20]

    conds = []
    for t in terms:
        like = f'%{t}%'
        conds.append(Literature.title.ilike(like))
        conds.append(Literature.abstract.ilike(like))
        conds.append(Literature.keywords.ilike(like))

    q = Literature.query
    if conds:
        q = q.filter(or_(*conds))

    docs = []
    for r in q.limit(limit).all():
        text = ' '.join(p for p in (r.title or '', r.abstract or '') if p)
        if text:
            docs.append({'content': text, 'title': r.title or '', 'link': r.link or ''})
    return docs


def build_qa_answer(question: str, session_id: str | None = None) -> Dict[str, Any]:
    q = (question or '').strip()
    if not q:
        return { 'answer': '请提供问题。', 'refs': [] }

    logger.info("开始处理问题: %s", q)

    vector_db = get_vector_database()

    documents: List[Dict[str, str]] = []
    source = 'fallback'

    # 1) 向量库语义检索（可用时优先）
    try:
        if vector_db.is_available():
            docs = vector_db.query_documents(q, n_results=3)
            documents = [{'content': d, 'title': '', 'link': ''} for d in docs]
            if documents:
                source = 'vector_qa'
    except Exception as e:
        logger.warning("向量库检索失败，降级为关键词检索: %s", e)

    # 2) 向量库不可用或无结果时，降级为数据库关键词检索
    if not documents:
        try:
            documents = _keyword_search_literature(q)
            source = 'keyword_qa'
        except Exception as e:
            logger.error("关键词检索失败: %s", e)

    # 3) 生成答案（DeepSeek，仅依赖 LLM，不依赖向量库）
    try:
        context_texts = [d['content'] for d in documents]
        answer = vector_db.generate_answer(q, context_texts)
    except Exception as e:
        logger.error("答案生成异常: %s", e)
        answer = None

    if not answer:
        return {
            'answer': 'AI 模型暂时无法回答此问题，请稍后再试。',
            'refs': [],
            'source': source,
            'confidence': 0.0
        }

    refs = []
    for i, doc in enumerate(documents[:3]):
        content = doc.get('content') or ''
        refs.append({
            'title': doc.get('title') or f'相关文献 {i+1}',
            'url': doc.get('link') or '',
            'content': content[:200] + '...' if len(content) > 200 else content
        })

    update_session(session_id, subject=None, intent='vector_qa', candidates=[])
    return {
        'answer': answer,
        'refs': refs,
        'source': source,
        'confidence': 0.8 if documents else 0.5,
        'context_documents': documents
    }
