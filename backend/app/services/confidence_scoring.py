"""
事件信号计算服务
基于PRR（比例报告比）和卡方值计算产品-症状关联的事件信号强度
"""

import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import Product, Symptom2, ProductSymptom

logger = logging.getLogger(__name__)


class EventSignalCalculator:
    """事件信号计算器 - 基于PRR和卡方值"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def _build_contingency_table(self, product_id: int, symptom_id: int) -> Dict:
        """
        构建2×2列联表
        
        基于ProductSymptomNews和ProductSymptomComp中的佐证记录统计：
        A: 同时包含目标产品p和目标不良反应a的事件数
        B: 包含目标产品p但不包含目标不良反应a的事件数
        C: 不包含目标产品p但包含目标不良反应a的事件数
        D: 既不包含目标产品p也不包含目标不良反应a的事件数
        """
        from ..models import ProductSymptomNews, ProductSymptomComp
        
        # 统计新闻佐证记录数
        news_counts = self.db.query(
            ProductSymptom.product_id,
            ProductSymptom.symptom_id,
            func.count(ProductSymptomNews.id).label('cnt')
        ).join(
            ProductSymptomNews, ProductSymptom.id == ProductSymptomNews.product_symptom_id
        ).filter(
            ProductSymptomNews.news_id.isnot(None)
        ).group_by(
            ProductSymptom.product_id,
            ProductSymptom.symptom_id
        ).all()
        
        # 统计投诉佐证记录数
        comp_counts = self.db.query(
            ProductSymptom.product_id,
            ProductSymptom.symptom_id,
            func.count(ProductSymptomComp.id).label('cnt')
        ).join(
            ProductSymptomComp, ProductSymptom.id == ProductSymptomComp.product_symptom_id
        ).filter(
            ProductSymptomComp.complaints_id.isnot(None)
        ).group_by(
            ProductSymptom.product_id,
            ProductSymptom.symptom_id
        ).all()
        
        # 合并新闻和投诉的事件计数
        pair_counts = {}
        for pid, sid, cnt in news_counts:
            pair_counts[(pid, sid)] = pair_counts.get((pid, sid), 0) + cnt
        for pid, sid, cnt in comp_counts:
            pair_counts[(pid, sid)] = pair_counts.get((pid, sid), 0) + cnt
        
        # 构建列联表
        A = pair_counts.get((product_id, symptom_id), 0)
        B = sum(cnt for (pid, sid), cnt in pair_counts.items() 
                if pid == product_id and sid != symptom_id)
        C = sum(cnt for (pid, sid), cnt in pair_counts.items() 
                if pid != product_id and sid == symptom_id)
        D = sum(cnt for (pid, sid), cnt in pair_counts.items() 
                if pid != product_id and sid != symptom_id)
        N = A + B + C + D
        
        return {'A': A, 'B': B, 'C': C, 'D': D, 'N': N}
    
    def calculate_prr(self, A: int, B: int, C: int, D: int) -> Optional[float]:
        """
        计算比例报告比 PRR = (A/(A+B)) / (C/(C+D))
        """
        if (A + B) == 0 or (C + D) == 0 or C == 0:
            return None
        return (A / (A + B)) / (C / (C + D))
    
    def calculate_chi_square(self, A: int, B: int, C: int, D: int, N: int) -> float:
        """
        计算卡方值 χ² = N(AD-BC)² / ((A+B)(C+D)(A+C)(B+D))
        """
        denominator = (A + B) * (C + D) * (A + C) * (B + D)
        if denominator == 0:
            return 0.0
        return N * ((A * D - B * C) ** 2) / denominator
    
    def get_signal_level(self, A: int, prr: Optional[float], chi2: float) -> Dict:
        """
        根据PRR和卡方值判定事件信号等级
        
        强事件信号（3分）：A≥3、PRR≥2 且 χ²≥4
        中等事件信号（2分）：A≥3、1≤PRR<2 且 χ²≥4
        弱事件信号（1分）：其余情况
        """
        if A >= 3 and prr is not None and prr >= 2 and chi2 >= 4:
            return {'score': 3, 'label': '强事件信号'}
        elif A >= 3 and prr is not None and prr >= 1 and chi2 >= 4:
            return {'score': 2, 'label': '中等事件信号'}
        else:
            return {'score': 1, 'label': '弱事件信号'}
    
    def calculate_event_signal(self, product_id: int, symptom_id: int) -> Dict:
        """
        计算产品-症状组合的事件信号
        
        Returns:
            包含PRR、卡方值、信号等级等信息的字典
        """
        try:
            product = self.db.get(Product, product_id)
            symptom = self.db.get(Symptom2, symptom_id)
            
            if not product or not symptom:
                logger.warning(f"产品或症状不存在: product_id={product_id}, symptom_id={symptom_id}")
                return self._empty_result()
            
            # 构建列联表
            table = self._build_contingency_table(product_id, symptom_id)
            A, B, C, D, N = table['A'], table['B'], table['C'], table['D'], table['N']
            
            # 计算PRR和卡方值
            prr = self.calculate_prr(A, B, C, D)
            chi2 = self.calculate_chi_square(A, B, C, D, N)
            
            # 判定信号等级
            signal = self.get_signal_level(A, prr, chi2)
            
            result = {
                'PRR': round(prr, 4) if prr is not None else None,
                'chi_square': round(chi2, 4),
                'signal_score': signal['score'],
                'signal_label': signal['label'],
                'contingency_table': {'A': A, 'B': B, 'C': C, 'D': D, 'N': N}
            }
            
            logger.info(
                f"事件信号计算: 产品={product.name}, "
                f"症状={getattr(symptom, 'symptom_name', getattr(symptom, 'name', '未知'))}, "
                f"A={A}, B={B}, C={C}, D={D}, N={N}, "
                f"PRR={result['PRR']}, χ²={result['chi_square']}, "
                f"信号={signal['label']}({signal['score']}分)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"计算事件信号失败: {e}")
            return self._empty_result(error=str(e))
    
    def _empty_result(self, error: str = None) -> Dict:
        result = {
            'PRR': None,
            'chi_square': 0.0,
            'signal_score': 1,
            'signal_label': '弱事件信号',
            'contingency_table': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'N': 0}
        }
        if error:
            result['error'] = error
        return result


def calculate_product_symptom_signal(db_session: Session, product_id: int,
                                    symptom_id: int) -> Dict:
    """
    便捷函数：计算单个产品-症状关联的事件信号（PRR和卡方值）
    """
    calculator = EventSignalCalculator(db_session)
    return calculator.calculate_event_signal(product_id, symptom_id)
