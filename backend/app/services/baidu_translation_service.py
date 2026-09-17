"""
Baidu Translation Service
Provides translation functionality using Baidu Translate API with caching support.
"""

import hashlib
import random
import time
import os
import ssl
from typing import List, Dict, Optional
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from app import db
from app.models import TranslationCache
from sqlalchemy.exc import IntegrityError

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建自定义的 SSL 上下文适配器
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


class BaiduTranslationService:
    """
    Baidu Translation Service with caching and batch translation support.
    
    Features:
    - Batch translation support
    - Database caching to reduce API calls
    - Error handling and retry mechanism
    - Language code mapping
    """
    
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        """
        Initialize Baidu Translation Service.
        
        Args:
            app_id: Baidu API App ID (defaults to environment variable)
            app_key: Baidu API App Key (defaults to environment variable)
        """
        self.app_id = app_id or os.getenv("BAIDU_APPID", "20250918002457415")
        self.app_key = app_key or os.getenv("BAIDU_KEY", "_q0pbtFzJk9E_7NqAj1j")
        self.base_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        self.timeout = 10
        self.max_text_length = 6000
        
        # Language code mapping for Baidu API
        self.lang_map = {
            "zh-CN": "zh",
            "zh": "zh",
            "en": "en",
            "it": "it",
            "ja": "jp",
            "ko": "kor",
            "auto": "auto"
        }
    
    def _map_language_code(self, code: str) -> str:
        """
        Map language code to Baidu API format.
        
        Args:
            code: Language code (e.g., 'zh-CN', 'en')
            
        Returns:
            Mapped language code for Baidu API
        """
        return self.lang_map.get(code, code)
    
    def _generate_sign(self, query: str, salt: str) -> str:
        """
        Generate signature for Baidu API authentication.
        
        Args:
            query: Text to translate
            salt: Random salt string
            
        Returns:
            MD5 signature string
        """
        raw = f"{self.app_id}{query}{salt}{self.app_key}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
    
    def _translate_single(self, text: str, src: str = 'auto', tgt: str = 'zh-CN') -> str:
        """
        Translate a single text using Baidu API.
        
        Args:
            text: Text to translate
            src: Source language code
            tgt: Target language code
            
        Returns:
            Translated text (returns original text on error)
        """
        if not text or not text.strip():
            return text
        
        # Truncate text if too long
        query = text.strip()
        if len(query) > self.max_text_length:
            query = query[:self.max_text_length]
        
        # Generate authentication parameters
        salt = str(random.randint(100000, 999999))
        sign = self._generate_sign(query, salt)
        
        params = {
            "q": query,
            "from": self._map_language_code(src),
            "to": self._map_language_code(tgt),
            "appid": self.app_id,
            "salt": salt,
            "sign": sign
        }
        
        # 尝试多次请求，处理 SSL 错误
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 创建一个更宽松的 session
                session = requests.Session()
                session.verify = False
                
                # 使用自定义的 SSL 适配器
                ssl_adapter = SSLAdapter()
                session.mount("https://", ssl_adapter)
                
                response = session.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Connection': 'keep-alive'
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for successful translation
                if "trans_result" in data and data["trans_result"]:
                    return data["trans_result"][0]["dst"]
                elif "error_code" in data:
                    print(f"[Baidu Translation] Error {data['error_code']}: {data.get('error_msg', 'unknown')}")
                    return text
                else:
                    print(f"[Baidu Translation] Unknown response: {data}")
                    return text
                    
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                print(f"[Baidu Translation] SSL/Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # 递增延迟
                    continue
                else:
                    print(f"[Baidu Translation] All SSL retry attempts failed, trying fallback method...")
                    # 尝试最后一次使用最基本的请求
                    try:
                        response = requests.get(
                            self.base_url,
                            params=params,
                            timeout=30,
                            verify=False,
                            headers={'User-Agent': 'python-requests/2.28.1'}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if "trans_result" in data and data["trans_result"]:
                                return data["trans_result"][0]["dst"]
                    except Exception:
                        pass
                    print(f"[Baidu Translation] All attempts failed, returning original text")
                    return text
                    
            except requests.exceptions.RequestException as e:
                print(f"[Baidu Translation] Request failed: {e}")
                return text
            except Exception as e:
                print(f"[Baidu Translation] Unexpected error: {e}")
                return text
    
    def translate_batch(self, texts: List[str], src: str = 'auto', tgt: str = 'zh-CN') -> List[str]:
        """
        Translate multiple texts using Baidu API.
        
        Args:
            texts: List of texts to translate
            src: Source language code
            tgt: Target language code
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        results = []
        for text in texts:
            if not text:
                results.append(text)
                continue
            
            translated = self._translate_single(text, src, tgt)
            results.append(translated)
            
            # Add delay to avoid rate limiting
            time.sleep(0.1)
        
        return results
    
    def _get_cached_translations(self, texts: List[str], src: str, tgt: str) -> Dict[str, str]:
        """
        Retrieve cached translations from database.
        
        Args:
            texts: List of texts to look up
            src: Source language code
            tgt: Target language code
            
        Returns:
            Dictionary mapping source text to translated text
        """
        if not texts:
            return {}
        
        # Remove duplicates while preserving order
        unique_texts = list(dict.fromkeys([t for t in texts if t]))
        if not unique_texts:
            return {}
        
        try:
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
        except Exception as e:
            print(f"[Baidu Translation] Cache lookup failed: {e}")
            return {}
    
    def _save_to_cache(self, translations: Dict[str, str], src: str, tgt: str) -> None:
        """
        Save translations to database cache.
        
        Args:
            translations: Dictionary mapping source text to translated text
            src: Source language code
            tgt: Target language code
        """
        if not translations:
            return
        
        cache_entries = []
        for src_text, result_text in translations.items():
            cache_entries.append(TranslationCache(
                src_text=src_text,
                src_lang=src,
                tgt_lang=tgt,
                result_text=result_text
            ))
        
        try:
            db.session.add_all(cache_entries)
            db.session.commit()
        except IntegrityError:
            # Handle duplicate key conflicts (concurrent writes)
            db.session.rollback()
        except Exception as e:
            print(f"[Baidu Translation] Cache save failed: {e}")
            db.session.rollback()
    
    def translate_with_cache(self, texts: List[str], src: str = 'auto', tgt: str = 'zh-CN') -> List[str]:
        """
        Translate texts with caching support.
        
        This method first checks the cache for existing translations,
        then translates only the missing texts and saves them to cache.
        
        Args:
            texts: List of texts to translate
            src: Source language code
            tgt: Target language code
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        # Normalize empty texts
        normalized = [t or '' for t in texts]
        
        # Get cached translations
        cache_map = self._get_cached_translations(normalized, src, tgt)
        
        # Identify texts that need translation
        results = []
        missing_texts = []
        missing_indices = []
        
        for idx, text in enumerate(normalized):
            if text in cache_map:
                # Cache hit
                results.append(cache_map[text])
            else:
                # Cache miss
                results.append('')  # Placeholder
                if text and text not in missing_texts:
                    missing_texts.append(text)
                missing_indices.append(idx)
        
        # Translate missing texts
        if missing_texts:
            print(f"[Baidu Translation] Translating {len(missing_texts)} texts (cache miss)")
            translated = self.translate_batch(missing_texts, src, tgt)
            
            # Build translation map
            translate_map = dict(zip(missing_texts, translated))
            
            # Fill in results
            for idx in missing_indices:
                original_text = normalized[idx]
                translated_text = translate_map.get(original_text, original_text)
                results[idx] = translated_text
            
            # Save to cache
            self._save_to_cache(translate_map, src, tgt)
        
        return results
    
    def translate_to_chinese(self, texts: List[str]) -> List[str]:
        """
        Translate texts to Chinese (Simplified).
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts in Chinese
        """
        return self.translate_with_cache(texts, 'auto', 'zh-CN')
    
    def translate_to_english(self, texts: List[str]) -> List[str]:
        """
        Translate texts to English.
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts in English
        """
        return self.translate_with_cache(texts, 'auto', 'en')
