from __future__ import annotations

import time
from typing import Dict, Any, Optional, Tuple


class SessionContext:
    def __init__(self, ttl_seconds: int = 900, max_size: int = 1024):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.store: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def get(self, session_id: Optional[str]) -> Dict[str, Any]:
        if not session_id:
            return {}
        now = time.time()
        rec = self.store.get(session_id)
        if not rec:
            return {}
        ts, data = rec
        if now - ts > self.ttl:
            self.store.pop(session_id, None)
            return {}
        return data.copy()

    def set(self, session_id: Optional[str], data: Dict[str, Any]) -> None:
        if not session_id:
            return
        # 简单 LRU：超出容量时随机清理一批（轻量实现）
        if len(self.store) >= self.max_size:
            # 删除过期项
            now = time.time()
            for k in list(self.store.keys()):
                ts, _ = self.store[k]
                if now - ts > self.ttl:
                    self.store.pop(k, None)
            # 若仍超限，删前 N 个
            if len(self.store) >= self.max_size:
                for k in list(self.store.keys())[:128]:
                    self.store.pop(k, None)
        self.store[session_id] = (time.time(), data.copy())


_SESSION = SessionContext()


def get_session(session_id: Optional[str]) -> Dict[str, Any]:
    return _SESSION.get(session_id)


def update_session(session_id: Optional[str], *, subject: Optional[str] = None, intent: Optional[str] = None, candidates: Optional[list[str]] = None) -> None:
    if not session_id:
        return
    cur = _SESSION.get(session_id)
    if subject:
        cur['lastSubject'] = subject
    if intent:
        cur['lastIntent'] = intent
    if candidates:
        cur['lastCandidates'] = candidates
    _SESSION.set(session_id, cur)
