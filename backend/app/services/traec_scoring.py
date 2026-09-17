"""
TRAEC 评分计算服务
包含浓度权重 ε_k 计算、单位换算、物种系数等核心计算逻辑
"""

import math
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# 流行病学单位换算到 mg/L 的系数表
EPI_UNIT_TO_MG_L = {
    'mg/L':  1.0,
    'μg/L':  0.001,
    'ng/g':  0.001,      # ng/g ≈ μg/L → 0.001 mg/L
    'mg/g':  1000.0,     # 1 mg/g = 1 mg/mL = 1000 mg/L
    'ppm':   1.0,        # 水中 ppm ≈ mg/L
}

# 体内实验动物物种换算系数（相对于小鼠）
SPECIES_FACTOR = {
    'mice':       1.000,
    'rat':        0.692,
    'cavy':       0.596,
    'rabbit':     0.359,
    'monkey':     0.115,
    'dog':        0.205,
    'zebrafish':  18.315,
}


def epi_concentration_to_mg_l(concentration, unit: str, conversion_factor=None) -> Optional[float]:
    """将流行病学浓度统一换算为 mg/L"""
    if concentration is None:
        return None
    c = float(concentration)
    if conversion_factor:
        c *= float(conversion_factor)
    factor = EPI_UNIT_TO_MG_L.get(unit, 1.0)
    return c * factor


def vivo_dose_to_mg_l(dose, dose_unit: str, species: str, conversion_factors=None) -> Optional[float]:
    """将体内实验剂量统一换算为 mg/L（血液等效浓度）

    单位换算：1000 mg/kg/d = 1 mg/L
    物种换算：乘以对应物种系数（相对于小鼠）
    """
    if dose is None:
        return None
    d = float(dose)
    if dose_unit == 'mg/kg/d':
        d = d / 1000.0
    # mg/L 不需要换算
    species_f = SPECIES_FACTOR.get(species, 1.0)
    d = d * species_f
    if conversion_factors:
        d *= float(conversion_factors)
    return d


def calculate_concentration_weights(concentrations: List[float]) -> List[float]:
    """根据浓度列表计算浓度权重 ε_k

    公式：ε_k = (1/lg(C_k_std)) / Σ(1/lg(C_n_std))
    其中 C_k_std = C_k × (10 / C_min)，保证 C_std >= 10，lg(C_std) >= 1 > 0

    Args:
        concentrations: 已统一单位的浓度值列表（均 > 0）

    Returns:
        对应的权重列表，总和为 1.0
    """
    if not concentrations:
        return []
    try:
        c_min = min(concentrations)
        c_std_list = [c * (10.0 / c_min) for c in concentrations]
        inv_lg_list = [1.0 / math.log10(c_std) for c_std in c_std_list]
        total = sum(inv_lg_list)
        if total == 0:
            return [1.0 / len(concentrations)] * len(concentrations)
        return [v / total for v in inv_lg_list]
    except (ValueError, ZeroDivisionError):
        return [1.0 / len(concentrations)] * len(concentrations)


def recalculate_epi_concentration_weights(relation_id: int, db_session) -> None:
    """重新计算同一关系下所有流行病学文献的浓度权重 ε_k，并写回数据库"""
    from app.models import LiteratureEpiScoring
    scorings = LiteratureEpiScoring.query.filter_by(relation_id=relation_id).all()

    c_values = [
        epi_concentration_to_mg_l(s.concentrations, s.concentration_unit or 'mg/L', s.conversion_factor)
        for s in scorings
    ]

    valid = [(i, c) for i, c in enumerate(c_values) if c and c > 0]
    if not valid:
        return

    valid_concentrations = [c for _, c in valid]
    weights = calculate_concentration_weights(valid_concentrations)

    valid_idx = 0
    for i, s in enumerate(scorings):
        if c_values[i] and c_values[i] > 0:
            s.concentration_weight = round(weights[valid_idx], 6)
            valid_idx += 1
        else:
            s.concentration_weight = None


def recalculate_vivo_concentration_weights(relation_id: int, db_session) -> None:
    """重新计算同一关系下所有体内实验文献的浓度权重 ε_k，并写回数据库"""
    from app.models import LiteratureVivoScoring
    scorings = LiteratureVivoScoring.query.filter_by(relation_id=relation_id).all()

    c_values = [
        vivo_dose_to_mg_l(s.dose, s.dose_unit or 'mg/kg/d', s.type_of_model or 'mice', s.conversion_factors)
        for s in scorings
    ]

    valid = [(i, c) for i, c in enumerate(c_values) if c and c > 0]
    if not valid:
        return

    valid_concentrations = [c for _, c in valid]
    weights = calculate_concentration_weights(valid_concentrations)

    valid_idx = 0
    for i, s in enumerate(scorings):
        if c_values[i] and c_values[i] > 0:
            s.concentration_weight = round(weights[valid_idx], 6)
            valid_idx += 1
        else:
            s.concentration_weight = None


def calculate_traec_score(relation_id: int, db_session) -> float:
    """计算指定 AllergenSymptom 关系的 TRAEC 评分

    计算步骤：
    1. 查询该关系下所有文献评分数据，按文献类型分组
    2. 对每组文献统一换算浓度单位
    3. 计算浓度权重 ε_k
    4. 单篇得分 = 可靠性 × 相关性 × 风险强度 × ε_k
    5. 各类型求和后取平均作为最终得分

    Returns:
        float: TRAEC 评分
    """
    from app.models import (
        AllergenSymptomSource, Literature,
        LiteratureEpiScoring, LiteratureVivoScoring, LiteratureVitroScoring,
        AllergenSymptom
    )

    try:
        literature_sources = db_session.query(AllergenSymptomSource, Literature).join(
            Literature, AllergenSymptomSource.literature_id == Literature.id
        ).filter(
            AllergenSymptomSource.allergen_symptom_id == relation_id
        ).all()

        if not literature_sources:
            _update_traec_score(relation_id, 0.0, db_session)
            return 0.0

        type_data = {'epidemiology': [], 'in-vivo': [], 'in-vitro': []}

        for source_rel, lit in literature_sources:
            scoring = None
            concentration_value = 0.0

            if lit.literature_type == 'epidemiology':
                scoring = LiteratureEpiScoring.query.filter_by(
                    literature_id=lit.id, relation_id=relation_id
                ).first()
                if scoring:
                    c = epi_concentration_to_mg_l(
                        scoring.concentrations,
                        scoring.concentration_unit or 'mg/L',
                        scoring.conversion_factor
                    )
                    concentration_value = c if c and c > 0 else 0.0

            elif lit.literature_type == 'in-vivo':
                scoring = LiteratureVivoScoring.query.filter_by(
                    literature_id=lit.id, relation_id=relation_id
                ).first()
                if scoring:
                    c = vivo_dose_to_mg_l(
                        scoring.dose,
                        scoring.dose_unit or 'mg/kg/d',
                        scoring.type_of_model or 'mice',
                        scoring.conversion_factors
                    )
                    concentration_value = c if c and c > 0 else 0.0

            elif lit.literature_type == 'in-vitro':
                scoring = LiteratureVitroScoring.query.filter_by(
                    literature_id=lit.id, relation_id=relation_id
                ).first()
                if scoring:
                    concentration_value = float(scoring.dose) if scoring.dose else 0.0

            if scoring and concentration_value > 0:
                type_data[lit.literature_type].append({
                    'scoring_obj': scoring,
                    'reliability': float(scoring.reliability_total_score or 0),
                    'correlation': float(scoring.correlation_score or 0),
                    'risk': float(scoring.risk_intensity_score or 0),
                    'concentration': concentration_value,
                })

        type_totals = []

        for literature_type, literature_list in type_data.items():
            if not literature_list:
                continue

            concentrations = [lit['concentration'] for lit in literature_list]
            weights = calculate_concentration_weights(concentrations)

            literature_scores = []
            for i, lit_data in enumerate(literature_list):
                w = weights[i] if i < len(weights) else 0.0
                try:
                    scoring_obj = lit_data['scoring_obj']
                    if scoring_obj:
                        scoring_obj.concentration_weight = round(w, 6)
                except Exception as update_error:
                    logger.warning(f'更新浓度权重失败: {update_error}')

                score = lit_data['reliability'] * lit_data['correlation'] * lit_data['risk'] * w
                literature_scores.append(score)

            if literature_scores:
                type_totals.append(sum(literature_scores))

        # 提交浓度权重更新
        try:
            db_session.commit()
        except Exception as commit_error:
            logger.error(f'提交浓度权重更新失败: {commit_error}')
            db_session.rollback()

        if type_totals:
            final_score = round(sum(type_totals) / len(type_totals), 2)
            _update_traec_score(relation_id, final_score, db_session)
            return final_score
        else:
            _update_traec_score(relation_id, 0.0, db_session)
            return 0.0

    except Exception as e:
        logger.error(f'计算关系 {relation_id} 的TRAEC评分失败: {e}', exc_info=True)
        return 0.0


def _update_traec_score(relation_id: int, score: float, db_session) -> None:
    """将 TRAEC 评分写回 AllergenSymptom 表"""
    from app.models import AllergenSymptom
    try:
        allergen_symptom = db_session.get(AllergenSymptom, relation_id)
        if allergen_symptom:
            allergen_symptom.traec_score = score
            db_session.commit()
        else:
            logger.warning(f'未找到关系ID {relation_id}，无法更新TRAEC评分')
    except Exception as e:
        logger.error(f'更新关系 {relation_id} 的TRAEC评分失败: {e}')
        db_session.rollback()
