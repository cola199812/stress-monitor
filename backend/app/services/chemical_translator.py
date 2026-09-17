#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
化学物质专业翻译服务
提供准确的化学物质中英文对照翻译
"""

from typing import Dict, List, Optional
import re
from .translator import translate_to_en
from app import db  # type: ignore
from app.models import TranslationCache  # type: ignore
from sqlalchemy.exc import IntegrityError  # type: ignore


# 化学物质专业术语词典 - 中文到英文
CHEMICAL_DICTIONARY = {
    # 杀虫剂/驱虫剂
    '避蚊胺': 'DEET',
    'DEET': 'DEET',
    'deet': 'DEET',
    '驱蚊胺': 'DEET',
    'N,N-二乙基-3-甲基苯甲酰胺': 'DEET',
    '二乙基甲苯甲酰胺': 'DEET',
    
    # 常见杀虫剂
    '敌敌畏': 'DDVP',
    '有机磷': 'organophosphorus',
    '拟除虫菊酯': 'pyrethroid',
    '氯氰菊酯': 'cypermethrin',
    '溴氰菊酯': 'deltamethrin',
    '氯菊酯': 'permethrin',
    '胺菊酯': 'tetramethrin',
    
    # 防腐剂/添加剂
    '苯甲酸': 'benzoic acid',
    '山梨酸': 'sorbic acid',
    '丙酸': 'propionic acid',
    '二氧化硫': 'sulfur dioxide',
    '亚硝酸钠': 'sodium nitrite',
    '硝酸钠': 'sodium nitrate',
    
    # 重金属
    '汞': 'mercury',
    '铅': 'lead', 
    '镉': 'cadmium',
    '砷': 'arsenic',
    '铬': 'chromium',
    '镍': 'nickel',
    '锌': 'zinc',
    '铜': 'copper',
    
    # 塑化剂
    '邻苯二甲酸': 'phthalic acid',
    '邻苯二甲酸酯': 'phthalate',
    'DEHP': 'DEHP',
    'DBP': 'DBP',
    'BBP': 'BBP',
    'DINP': 'DINP',
    'DIDP': 'DIDP',
    
    # 常见化学物质
    '甲醛': 'formaldehyde',
    '苯': 'benzene',
    '甲苯': 'toluene',
    '二甲苯': 'xylene',
    '苯乙烯': 'styrene',
    '氨': 'ammonia',
    '氯气': 'chlorine',
    '一氧化碳': 'carbon monoxide',
    '二氧化碳': 'carbon dioxide',
    '硫化氢': 'hydrogen sulfide',
    
    # 农药
    '草甘膦': 'glyphosate',
    '阿特拉津': 'atrazine',
    '毒死蜱': 'chlorpyrifos',
    '乐果': 'dimethoate',
    '马拉硫磷': 'malathion',
    
    # 药物
    '阿司匹林': 'aspirin',
    '对乙酰氨基酚': 'acetaminophen',
    '布洛芬': 'ibuprofen',
    '青霉素': 'penicillin',
    
    # 食品添加剂
    '柠檬酸': 'citric acid',
    '抗坏血酸': 'ascorbic acid',
    '维生素C': 'vitamin C',
    '维生素E': 'vitamin E',
    'BHT': 'BHT',
    'BHA': 'BHA',
    
    # 其他常见物质
    '乙醇': 'ethanol',
    '甲醇': 'methanol',
    '丙酮': 'acetone',
    '乙酸': 'acetic acid',
    '盐酸': 'hydrochloric acid',
    '硫酸': 'sulfuric acid',
    '硝酸': 'nitric acid',
    '氢氧化钠': 'sodium hydroxide',
    '碳酸钠': 'sodium carbonate',
    '氯化钠': 'sodium chloride',
}

# 化学物质类别词典
CHEMICAL_CATEGORIES = {
    '杀虫剂': 'insecticide',
    '除草剂': 'herbicide',
    '杀菌剂': 'fungicide',
    '驱虫剂': 'repellent',
    '防腐剂': 'preservative',
    '抗氧化剂': 'antioxidant',
    '增稠剂': 'thickener',
    '乳化剂': 'emulsifier',
    '稳定剂': 'stabilizer',
    '着色剂': 'coloring agent',
    '香料': 'fragrance',
    '溶剂': 'solvent',
    '催化剂': 'catalyst',
    '表面活性剂': 'surfactant',
}

# 英文到中文的专业术语翻译词典
ENGLISH_TO_CHINESE_TERMS = {
    # 化合物类型
    'Drug': '药物',
    'Human': '人体相关',
    'Chemical': '化学品',
    'Pesticide': '农药',
    'Industrial': '工业化学品',
    'Food Additive': '食品添加剂',
    'Cosmetic': '化妆品',
    'Pharmaceutical': '医药品',
    
    # 实验类型
    'TDLo - Lowest published toxic dose': '最低毒性剂量',
    'LD50 - Lethal dose, 50 percent kill': '半数致死量',
    'LC50 - Lethal concentration, 50 percent kill': '半数致死浓度',
    'LDLo - Lowest published lethal dose': '最低致死剂量',
    'TCLo - Lowest published toxic concentration': '最低毒性浓度',
    'TDLo': '最低毒性剂量',
    'LD50': '半数致死量',
    'LC50': '半数致死浓度',
    'LDLo': '最低致死剂量',
    'TCLo': '最低毒性浓度',
    
    # 暴露途径
    'Oral': '口服',
    'Intravenous': '静脉注射',
    'Intraperitoneal': '腹腔注射',
    'Subcutaneous': '皮下注射',
    'Intramuscular': '肌肉注射',
    'Dermal': '皮肤接触',
    'Inhalation': '吸入',
    'Ocular': '眼部接触',
    'Rectal': '直肠给药',
    'Topical': '外用',
    
    # 观察物种
    'Human': '人类',
    'Rodent - mouse': '小鼠',
    'Rodent - rat': '大鼠',
    'Rodent - guinea pig': '豚鼠',
    'Rodent - hamster': '仓鼠',
    'Rodent - rabbit': '兔子',
    'Mammal - dog': '狗',
    'Mammal - cat': '猫',
    'Mammal - monkey': '猴子',
    'Bird - chicken': '鸡',
    'Fish': '鱼类',
    'Mouse': '小鼠',
    'Rat': '大鼠',
    'Guinea pig': '豚鼠',
    'Hamster': '仓鼠',
    'Rabbit': '兔子',
    'Dog': '狗',
    'Cat': '猫',
    'Monkey': '猴子',
    'Chicken': '鸡',
    
    # 毒性效应关键词
    'Behavioral': '行为影响',
    'Neurological': '神经系统',
    'Cardiovascular': '心血管系统',
    'Respiratory': '呼吸系统',
    'Gastrointestinal': '消化系统',
    'Hepatic': '肝脏',
    'Renal': '肾脏',
    'Dermatological': '皮肤',
    'Ocular': '眼部',
    'Reproductive': '生殖系统',
    'Developmental': '发育',
    'Carcinogenic': '致癌',
    'Mutagenic': '致突变',
    'Teratogenic': '致畸',
    'lethal dose': '致死剂量',
    'toxic effects': '毒性效应',
    'hallucinations': '幻觉',
    'distorted perceptions': '感知扭曲',
    'convulsions': '抽搐',
    'tremor': '震颤',
    'paralysis': '麻痹',
    'coma': '昏迷',
    'death': '死亡',
}


def _normalize_chemical_name(name: str) -> str:
    """标准化化学物质名称"""
    if not name:
        return name
    
    # 转换为小写并去除空格
    normalized = name.strip().lower()
    
    # 移除常见的化学物质后缀/前缀描述
    patterns_to_remove = [
        r'[（(].*?[）)]',  # 括号内容
        r'[【\[].*?[】\]]',  # 方括号内容
        r'含量.*',  # 含量描述
        r'浓度.*',  # 浓度描述
        r'纯度.*',  # 纯度描述
        r'工业级',
        r'食品级',
        r'医药级',
        r'化学纯',
        r'分析纯',
    ]
    
    for pattern in patterns_to_remove:
        normalized = re.sub(pattern, '', normalized)
    
    return normalized.strip()


def translate_chemical_name(chinese_name: str, use_cache: bool = True) -> str:
    """
    翻译化学物质名称
    优先使用专业词典，回退到通用翻译，支持缓存
    """
    if not chinese_name:
        return chinese_name
    
    # 标准化输入
    normalized = _normalize_chemical_name(chinese_name)
    original = chinese_name.strip()
    
    # 0. 检查翻译缓存（化学专业翻译缓存）
    if use_cache:
        try:
            cached = TranslationCache.query.filter_by(
                src_text=original,
                src_lang='zh-CN',
                tgt_lang='en-chemical'  # 使用特殊标识区分化学专业翻译
            ).first()
            if cached and cached.result_text:
                print(f"从化学翻译缓存获取: {original} → {cached.result_text}")
                return cached.result_text
        except Exception as e:
            print(f"查询翻译缓存失败: {e}")
    
    # 1. 直接匹配专业词典
    result = None
    if original in CHEMICAL_DICTIONARY:
        result = CHEMICAL_DICTIONARY[original]
        print(f"专业词典直接匹配: {original} → {result}")
    elif normalized in CHEMICAL_DICTIONARY:
        result = CHEMICAL_DICTIONARY[normalized]
        print(f"专业词典标准化匹配: {original} → {result}")
    else:
        # 2. 部分匹配专业词典（包含关键词）
        for chinese_key, english_value in CHEMICAL_DICTIONARY.items():
            if chinese_key in original or chinese_key in normalized:
                result = english_value
                print(f"专业词典部分匹配: {original} → {result} (通过关键词: {chinese_key})")
                break
    
    # 辅助：安全写缓存（若已存在则跳过，若内容不同则更新）
    def _upsert_cache(src: str, result: str):
        try:
            exist = TranslationCache.query.filter_by(
                src_text=src,
                src_lang='zh-CN',
                tgt_lang='en-chemical',
            ).first()
            if exist:
                if exist.result_text != result:
                    exist.result_text = result
                    db.session.commit()
                return
            cache_entry = TranslationCache(
                src_text=src,
                src_lang='zh-CN',
                tgt_lang='en-chemical',
                result_text=result
            )
            db.session.add(cache_entry)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        except Exception as e:
            print(f"保存翻译缓存失败: {e}")
            db.session.rollback()

    # 如果专业词典匹配成功，保存到缓存并返回
    if result:
        if use_cache:
            _upsert_cache(original, result)
        return result
    
    # 3. 检查是否已经是英文（包含英文字母）
    if re.search(r'[a-zA-Z]', original):
        # 如果包含英文，可能已经是英文名称或混合名称
        # 提取英文部分
        english_parts = re.findall(r'[a-zA-Z][a-zA-Z0-9\-]*', original)
        if english_parts:
            # 返回最长的英文部分
            longest_part = max(english_parts, key=len)
            if len(longest_part) >= 3:  # 至少3个字符的英文才认为是有效的化学名称
                result = longest_part.upper()
                print(f"提取英文部分: {original} → {result}")
                
                # 保存到缓存
                if use_cache:
                    _upsert_cache(original, result)
                
                return result
    
    # 4. 使用通用翻译作为回退
    try:
        translated = translate_to_en([normalized])
        if translated and translated[0] and translated[0] != normalized:
            result = translated[0]
            print(f"通用翻译回退: {original} → {result}")
            
            # 保存到缓存
            if use_cache:
                _upsert_cache(original, result)
            
            return result
    except Exception as e:
        print(f"通用翻译失败: {e}")
    
    # 5. 最终回退：返回原始名称
    print(f"翻译失败，返回原始名称: {original}")
    
    # 即使是原始名称也保存到缓存，避免重复处理
    if use_cache:
        _upsert_cache(original, original)
    
    return original


def translate_chemical_names(chinese_names: List[str]) -> List[str]:
    """批量翻译化学物质名称"""
    return [translate_chemical_name(name) for name in chinese_names]


def translate_english_term_to_chinese(english_term: str) -> str:
    """
    将英文专业术语翻译为中文
    优先使用专业术语词典
    """
    if not english_term:
        return english_term
    
    original = english_term.strip()
    
    # 1. 直接匹配专业词典
    if original in ENGLISH_TO_CHINESE_TERMS:
        return ENGLISH_TO_CHINESE_TERMS[original]
    
    # 2. 部分匹配（包含关键词）
    for english_key, chinese_value in ENGLISH_TO_CHINESE_TERMS.items():
        if english_key.lower() in original.lower():
            return chinese_value
    
    # 3. 使用通用翻译作为回退（非阻塞：优先缓存命中，缺失项后台翻译）
    try:
        from .translator import ensure_async_translations_and_get_cached
        translated = ensure_async_translations_and_get_cached([original], 'auto', 'zh-CN')
        if translated and translated[0] and translated[0] != original:
            return translated[0]
    except Exception as e:
        print(f"通用翻译失败: {e}")
    
    # 4. 返回原始英文
    return original


def translate_english_terms_to_chinese(english_terms: List[str]) -> List[str]:
    """批量翻译英文专业术语为中文"""
    return [translate_english_term_to_chinese(term) for term in english_terms]


def add_chemical_translation(chinese_name: str, english_name: str):
    """动态添加化学物质翻译对照"""
    CHEMICAL_DICTIONARY[chinese_name.strip()] = english_name.strip()


def get_chemical_dictionary() -> Dict[str, str]:
    """获取完整的化学物质词典"""
    return CHEMICAL_DICTIONARY.copy()


def get_chemical_translation_cache() -> List[Dict[str, str]]:
    """获取化学翻译缓存"""
    try:
        cache_entries = TranslationCache.query.filter_by(
            src_lang='zh-CN',
            tgt_lang='en-chemical'
        ).all()
        
        return [
            {
                'chinese': entry.src_text,
                'english': entry.result_text,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            }
            for entry in cache_entries
        ]
    except Exception as e:
        print(f"获取化学翻译缓存失败: {e}")
        return []


def clear_chemical_translation_cache():
    """清空化学翻译缓存"""
    try:
        deleted_count = TranslationCache.query.filter_by(
            src_lang='zh-CN',
            tgt_lang='en-chemical'
        ).delete()
        db.session.commit()
        print(f"已清空 {deleted_count} 条化学翻译缓存")
        return deleted_count
    except Exception as e:
        print(f"清空化学翻译缓存失败: {e}")
        db.session.rollback()
        return 0


def main():
    """测试函数"""
    test_names = [
        '避蚊胺(DEET)',
        '避蚊胺',
        'DEET',
        '驱蚊液',
        '杀虫剂',
        '甲醛',
        '苯甲酸钠',
        '未知化学物质',
        '维生素C',
        'BHT抗氧化剂',
    ]
    
    print("化学物质翻译测试:")
    for name in test_names:
        translated = translate_chemical_name(name)
        print(f"{name} → {translated}")


if __name__ == '__main__':
    main()
