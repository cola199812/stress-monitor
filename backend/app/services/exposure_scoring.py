from __future__ import annotations

from typing import List, Tuple, Optional

def validate_scoring_details(scoring_details: Dict[str, str]) -> Dict[str, str]:
    """
    验证评分详情的有效性
    
    Args:
        scoring_details: 评分详情
        
    Returns:
        Dict[str, str]: 验证错误信息，如果为空则验证通过
    """
    errors = {}
    
    # 检查是否包含所有必需的维度
    required_dimensions = set(EXPOSURE_SCORING_CONFIG.keys())
    provided_dimensions = set(scoring_details.keys())
    
    missing_dimensions = required_dimensions - provided_dimensions
    if missing_dimensions:
        errors["missing_dimensions"] = f"缺少维度: {', '.join(missing_dimensions)}"
    
    # 检查每个维度的等级是否有效
    for dimension, level in scoring_details.items():
        if dimension not in EXPOSURE_SCORING_CONFIG:
            errors[f"invalid_dimension_{dimension}"] = f"无效的维度: {dimension}"
        elif level not in EXPOSURE_SCORING_CONFIG[dimension]["levels"]:
            errors[f"invalid_level_{dimension}"] = f"维度 {dimension} 的等级 {level} 无效"
    
    return errors


def get_scoring_config() -> Dict:
    """
    获取暴露潜力评分配置
    
    Returns:
        Dict: 评分配置
    """
    return EXPOSURE_SCORING_CONFIG


def format_scoring_details_for_display(scoring_details: Dict[str, str]) -> Dict:
    """
    格式化评分详情用于前端显示
    
    Args:
        scoring_details: 评分详情
        
    Returns:
        Dict: 格式化后的详情，包含分数和描述
    """
    formatted = {}
    
    for dimension, level in scoring_details.items():
        if dimension in EXPOSURE_SCORING_CONFIG:
            config = EXPOSURE_SCORING_CONFIG[dimension]
            if level in config["levels"]:
                level_config = config["levels"][level]
                formatted[dimension] = {
                    "level": level,
                    "score": level_config["score"],
                    "description": level_config["description"]
                }
    
    return formatted


# 测试函数
if __name__ == "__main__":
    # 测试评分计算
    test_scoring = {
        "暴露维度": "4分",
        "年龄": "3分", 
        "产品形态": "2分",
        "含量": "4分",
        "使用频率": "3分",
        "使用时间": "2分"
    }
    
    print("测试评分详情:", test_scoring)
    print("计算总分:", calculate_exposure_score(test_scoring))
    print("验证结果:", validate_scoring_details(test_scoring))
    print("格式化显示:", format_scoring_details_for_display(test_scoring))
