from __future__ import annotations

import hashlib
import threading
import queue
import time
import os
import random
import json
from typing import List, Dict, Tuple, Optional
import requests

from app import db  # type: ignore
from app.models import TranslationCache  # type: ignore
from sqlalchemy.exc import IntegrityError  # type: ignore


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode('utf-8')).hexdigest()


def translate_google_free(texts: List[str], src: str = 'auto', tgt: str = 'zh-CN') -> List[str]:
    """
    使用 Google translate 免费接口（translate.googleapis.com）进行翻译。
    支持批量翻译：每个文本通过多个 q 参数传递。
    """
    if not texts:
        return []
    
    try:
        session = requests.Session()
        # 添加用户代理，避免被识别为机器人
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        url = 'https://translate.googleapis.com/translate_a/single'

        # 构造多个 q 参数
        params = [
            ('client', 'gtx'),
            ('sl', src),
            ('tl', tgt),
            ('dt', 't'),
        ]
        for t in texts:
            params.append(('q', t))

        # 禁用SSL验证以避免连接问题
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = session.get(url, params=params, timeout=15, verify=False)
        r.raise_for_status()
        data = r.json()

        # data 结构: [ [ [translated, original, ...], ... ], ... ]
        out: List[str] = []
        if isinstance(data, list) and data:
            parts = data[0]
            for p in parts:
                if isinstance(p, list) and p:
                    out.append(str(p[0]))
        return out
    except Exception as e:
        print(f"Google翻译异常: {e}")
        # 如果失败，返回原文
        return texts


# ====== 国内翻译引擎配置 ======
# 百度翻译配置
BAIDU_APPID = os.getenv("BAIDU_APPID", "20250918002457415")
BAIDU_KEY = os.getenv("BAIDU_KEY", "_q0pbtFzJk9E_7NqAj1j")

# 有道翻译配置
YOUDAO_APP_KEY = os.getenv("YOUDAO_APP_KEY", "4c541793fc5cb7a6")
YOUDAO_APP_SECRET = os.getenv("YOUDAO_APP_SECRET", "9fo9HsHkMLZYIeSljOTXoqkghvbTC7Vm")

# 通用配置
TIMEOUT = 10


# ====== 语言代码映射 ======
def _map_lang_baidu(code: str) -> str:
    """百度翻译语言代码映射"""
    mapping = {
        "zh-CN": "zh", "zh": "zh", "en": "en", "it": "it", 
        "ja": "jp", "ko": "kor", "auto": "auto"
    }
    return mapping.get(code, code)


def _map_lang_youdao(code: str) -> str:
    """有道翻译语言代码映射"""
    mapping = {
        "zh-CN": "zh-CHS", "zh": "zh-CHS", "en": "en", 
        "ja": "ja", "ko": "ko", "auto": "auto"
    }
    return mapping.get(code, code)


# ====== 百度翻译 ======
def _baidu_sign(q: str, appid: str, key: str, salt: str) -> str:
    """百度翻译签名生成"""
    raw = appid + q + salt + key
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def translate_baidu(texts: List[str], src: str = 'auto', tgt: str = 'zh-CN') -> Optional[List[str]]:
    """
    百度翻译API
    """
    if not BAIDU_APPID or not BAIDU_KEY or not texts:
        print("百度翻译配置缺失，跳过")
        return None
    
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    results = []
    
    for text in texts:
        if not text:
            results.append(text)
            continue
            
        q = text.strip()
        # 限制文本长度
        if len(q) > 6000:
            q = q[:6000]
            
        salt = str(random.randint(100000, 999999))
        sign = _baidu_sign(q, BAIDU_APPID, BAIDU_KEY, salt)
        
        params = {
            "q": q,
            "from": _map_lang_baidu(src),
            "to": _map_lang_baidu(tgt),
            "appid": BAIDU_APPID,
            "salt": salt,
            "sign": sign
        }
        
        try:
            # 禁用SSL验证以避免连接问题，同时禁用警告
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, params=params, timeout=TIMEOUT, verify=False)
            response.raise_for_status()
            data = response.json()
            
            if "trans_result" in data and data["trans_result"]:
                results.append(data["trans_result"][0]["dst"])
            elif "error_code" in data:
                print(f"百度翻译错误 {data['error_code']}: {data.get('error_msg', 'unknown')}")
                results.append(text)
            else:
                print(f"百度翻译未知响应: {data}")
                results.append(text)
                
        except Exception as e:
            print(f"百度翻译失败: {e}")
            results.append(text)
    
    return results


# ====== 有道翻译 ======
def _youdao_sign(q: str, app_key: str, app_secret: str, salt: str, curtime: str) -> str:
    """有道翻译签名生成"""
    input_str = app_key + q + salt + curtime + app_secret
    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()


def translate_youdao(texts: List[str], src: str = 'auto', tgt: str = 'zh-CN') -> Optional[List[str]]:
    """
    有道翻译API
    """
    if not YOUDAO_APP_KEY or not YOUDAO_APP_SECRET or not texts:
        return None
    
    url = "https://openapi.youdao.com/api"
    results = []
    
    for text in texts:
        if not text:
            results.append(text)
            continue
            
        q = text.strip()
        # 限制文本长度，有道翻译有字符限制
        if len(q) > 5000:
            q = q[:5000]
            
        salt = str(random.randint(100000, 999999))
        curtime = str(int(time.time()))
        sign = _youdao_sign(q, YOUDAO_APP_KEY, YOUDAO_APP_SECRET, salt, curtime)
        
        data = {
            "q": q,
            "from": _map_lang_youdao(src),
            "to": _map_lang_youdao(tgt),
            "appKey": YOUDAO_APP_KEY,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime
        }
        
        try:
            # 禁用SSL验证以避免连接问题
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.post(url, data=data, timeout=TIMEOUT, verify=False)
            response.raise_for_status()
            result = response.json()
            
            error_code = result.get("errorCode")
            if error_code == "0" and "translation" in result:
                results.append(result["translation"][0])
            elif error_code == "202":
                print(f"有道翻译频率限制，跳过: {q[:50]}...")
                results.append(text)
            else:
                print(f"有道翻译错误 {error_code}: {result.get('errorMsg', 'unknown')}")
                results.append(text)
                
        except Exception as e:
            print(f"有道翻译失败: {e}")
            results.append(text)
    
    return results


def translate_with_fallback(texts: List[str], src: str = 'auto', tgt: str = 'zh-CN') -> List[str]:
    """
    多后端翻译，按优先级尝试不同的翻译服务
    优先级：1. 百度翻译 2. 有道翻译 3. Google API
    """
    if not texts:
        return []
    
    # 1. 优先尝试百度翻译（国内服务，最稳定）
    try:
        print("尝试百度翻译API...")
        result = translate_baidu(texts, src, tgt)
        if result is not None:
            return result
    except Exception as e:
        print(f"百度翻译失败: {e}")
    
    # 2. 尝试有道翻译
    try:
        print("尝试有道翻译API...")
        result = translate_youdao(texts, src, tgt)
        if result is not None:
            return result
    except Exception as e:
        print(f"有道翻译失败: {e}")
    
    # 3. 最后尝试Google免费API（可能被墙）
    try:
        print("尝试Google免费API翻译...")
        return translate_google_free(texts, src, tgt)
    except Exception as e:
        print(f"Google免费API失败: {e}")
    
    # 所有翻译服务都失败，返回原文
    print("所有翻译服务都失败，返回原文")
    return texts


def translate_with_cache(texts: List[str], src: str, tgt: str) -> List[str]:
    """带缓存的翻译逻辑：命中缓存直接返回，缺失时才翻译并写入缓存"""
    if not texts:
        return []
    
    results: List[str] = []
    missing_texts: List[str] = []
    missing_indices: List[int] = []
    normalized = [t or '' for t in texts]

    # 查询现有缓存
    unique_texts = list(dict.fromkeys(normalized))  # 保持顺序去重
    cache_map: Dict[str, str] = {}
    if unique_texts:
        rows = (
            TranslationCache.query
            .filter(TranslationCache.src_lang == src, TranslationCache.tgt_lang == tgt, TranslationCache.src_text.in_(unique_texts))
            .all()
        )
        for row in rows:
            cache_map[row.src_text] = row.result_text

    # 分离缓存命中和缺失的文本
    for idx, t in enumerate(normalized):
        if t in cache_map:
            # 缓存命中，直接使用
            results.append(cache_map[t])
        else:
            # 缓存缺失，标记为需要翻译
            results.append('')  # 占位符
            if t not in missing_texts:  # 避免重复翻译相同文本
                missing_texts.append(t)
            missing_indices.append(idx)

    # 只有缓存缺失时才调用翻译API
    if missing_texts:
        try:
            translated = translate_with_fallback(missing_texts, src, tgt)
            
            # 建立翻译结果映射
            translate_map = {}
            for original, translated_text in zip(missing_texts, translated):
                translate_map[original] = translated_text
            
            # 填充结果并准备写入缓存
            cache_entries = []
            added_cache_keys = set()
            
            for idx in missing_indices:
                original_text = normalized[idx]
                translated_text = translate_map.get(original_text, original_text)
                results[idx] = translated_text
                
                # 准备缓存条目（去重）
                cache_key = (original_text, src, tgt)
                if cache_key not in added_cache_keys:
                    cache_entries.append(TranslationCache(
                        src_text=original_text, 
                        src_lang=src, 
                        tgt_lang=tgt, 
                        result_text=translated_text
                    ))
                    added_cache_keys.add(cache_key)
            
            # 批量写入缓存
            if cache_entries:
                try:
                    db.session.add_all(cache_entries)
                    db.session.commit()
                except IntegrityError:
                    # 如果有重复键冲突，回滚并忽略（可能是并发写入）
                    db.session.rollback()
                except Exception:
                    db.session.rollback()
                    
        except Exception:
            # 翻译失败时，返回原文
            for idx in missing_indices:
                results[idx] = normalized[idx]

    return results


def translate_to_zh(texts: List[str]) -> List[str]:
    """将任意语言翻译为中文（简体）。"""
    return translate_with_cache(texts, 'auto', 'zh-CN')


def translate_to_en(texts: List[str]) -> List[str]:
    """将中文或其他语言翻译为英文。"""
    return translate_with_cache(texts, 'auto', 'en')


def translate_to_ko(texts: List[str]) -> List[str]:
    """将任意语言翻译为韩文。"""
    return translate_with_cache(texts, 'auto', 'ko')


# ------------------------------
# 异步翻译后台与非阻塞API
# ------------------------------

# 轻量后台任务队列：元素为 (text, src, tgt)
_BG_QUEUE: "queue.Queue[Tuple[str, str, str]]" = queue.Queue()
_BG_THREAD: Optional[threading.Thread] = None
_BG_STARTED: bool = False
_BG_APP = None  # 由 start_background_translation(app) 设置

_BATCH_MAX = 50
_BATCH_DELAY_SECONDS = 0.3


def start_background_translation(app) -> None:
    """在应用启动时调用，启动后台翻译线程（只启动一次）。"""
    global _BG_THREAD, _BG_STARTED, _BG_APP
    if _BG_STARTED:
        return
    _BG_APP = app

    def _worker_loop() -> None:
        while True:
            try:
                item = _BG_QUEUE.get(timeout=1)
            except Exception:
                # 空闲等待
                continue

            batch: List[Tuple[str, str, str]] = [item]
            start_ts = time.time()
            while len(batch) < _BATCH_MAX and (time.time() - start_ts) < _BATCH_DELAY_SECONDS:
                try:
                    batch.append(_BG_QUEUE.get_nowait())
                except Exception:
                    break

            # 分组聚合：按 (src, tgt) 分组，并在组内去重
            grouped: Dict[Tuple[str, str], List[str]] = {}
            seen_in_group: Dict[Tuple[str, str], set] = {}
            for text, src, tgt in batch:
                if not text:
                    continue
                key = (src, tgt)
                if key not in grouped:
                    grouped[key] = []
                    seen_in_group[key] = set()
                if text not in seen_in_group[key]:
                    seen_in_group[key].add(text)
                    grouped[key].append(text)

            # 逐组处理：查询缓存 → 调用翻译API → 写入缓存
            if _BG_APP is None:
                continue
            try:
                with _BG_APP.app_context():
                    for (src, tgt), texts in grouped.items():
                        if not texts:
                            continue
                        # 查询已有缓存，过滤已存在的
                        unique_texts = list(dict.fromkeys([t for t in texts if t]))
                        if not unique_texts:
                            continue
                        rows = (
                            TranslationCache.query
                            .filter(
                                TranslationCache.src_lang == src,
                                TranslationCache.tgt_lang == tgt,
                                TranslationCache.src_text.in_(unique_texts)
                            )
                            .all()
                        )
                        cached_set = {r.src_text for r in rows}
                        missing = [t for t in unique_texts if t not in cached_set]
                        if not missing:
                            continue

                        try:
                            translated_list = translate_with_fallback(missing, src, tgt)
                        except Exception:
                            translated_list = []

                        entries = []
                        for orig, zh in zip(missing, translated_list):
                            entries.append(TranslationCache(
                                src_text=orig,
                                src_lang=src,
                                tgt_lang=tgt,
                                result_text=zh or orig,
                            ))

                        if entries:
                            try:
                                db.session.add_all(entries)
                                db.session.commit()
                            except IntegrityError:
                                db.session.rollback()
                            except Exception:
                                db.session.rollback()
            except Exception:
                # 避免线程崩溃
                try:
                    db.session.rollback()
                except Exception:
                    pass

    _BG_THREAD = threading.Thread(target=_worker_loop, name="translator-bg-worker", daemon=True)
    _BG_THREAD.start()
    _BG_STARTED = True


def get_cached_translations(texts: List[str], src: str, tgt: str) -> Dict[str, str]:
    """仅从缓存读取翻译结果，不触发外部API调用。"""
    if not texts:
        return {}
    normalized = [t or '' for t in texts]
    unique_texts = list(dict.fromkeys(normalized))
    if not unique_texts:
        return {}
    rows = (
        TranslationCache.query
        .filter(
            TranslationCache.src_lang == src,
            TranslationCache.tgt_lang == tgt,
            TranslationCache.src_text.in_(unique_texts)
        )
        .all()
    )
    return {row.src_text: row.result_text for row in rows}


def schedule_translation(texts: List[str], src: str, tgt: str) -> None:
    """将缺失的翻译任务放入后台队列，快速返回。"""
    if not texts:
        return
    try:
        normalized = [t or '' for t in texts]
        unique_texts = list(dict.fromkeys([t for t in normalized if t]))
        if not unique_texts:
            return
        # 过滤已在缓存中的文本
        rows = (
            TranslationCache.query
            .filter(
                TranslationCache.src_lang == src,
                TranslationCache.tgt_lang == tgt,
                TranslationCache.src_text.in_(unique_texts)
            )
            .all()
        )
        cached_set = {r.src_text for r in rows}
        for t in unique_texts:
            if t not in cached_set:
                try:
                    _BG_QUEUE.put_nowait((t, src, tgt))
                except Exception:
                    # 队列满等异常直接忽略
                    pass
    except Exception:
        # 任何异常都不阻塞主流程
        try:
            db.session.rollback()
        except Exception:
            pass


def ensure_async_translations_and_get_cached(texts: List[str], src: str, tgt: str) -> List[str]:
    """非阻塞翻译：优先返回缓存命中；对缺失项投递后台任务并返回原文。"""
    if not texts:
        return []
    cache_map = get_cached_translations(texts, src, tgt)
    missing = [t for t in texts if (t or '') and (t not in cache_map)]
    if missing:
        schedule_translation(missing, src, tgt)
    return [cache_map.get(t, t) for t in texts]


from app import create_app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 测试缓存逻辑
        print("=== 测试翻译缓存逻辑 ===")
        
        # 第一次翻译（应该调用API并写入缓存）
        print("第一次翻译韩文:")
        result1 = translate_to_zh(['지우개', '음식 모양 지우개'])
        print(f"结果: {result1}")
        
        # 第二次翻译相同内容（应该命中缓存，不调用API）
        print("\n第二次翻译相同韩文（应该命中缓存）:")
        result2 = translate_to_zh(['지우개', '음식 모양 지우개'])
        print(f"结果: {result2}")
        
        # 混合翻译（部分命中缓存，部分需要新翻译）
        print("\n混合翻译（部分缓存命中）:")
        result3 = translate_to_zh(['지우개', '새로운 텍스트', '음식 모양 지우개'])
        print(f"结果: {result3}")
        
        print("\n=== 测试完成 ===")
        print(translate_to_zh(['hello', 'world']))
        print(translate_to_en(['驱蚊扣', '世界']))
