from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, text, and_, or_
from ..models import (
    News, Recall, Literature, News_filter, LiteratureFilter, Recall_filter,
    ProductSymptom, Product, Symptom2, Category, Type, Complaints,
    ProductSymptomNews, ProductSymptomComp,
    Allergen, AllergenProduct, AllergenSymptom, ExposureScoringDetail,
    LiteratureEpiScoring, LiteratureVivoScoring, LiteratureVitroScoring,
    db
)
import logging
import math

logger = logging.getLogger(__name__)

bp = Blueprint('dashboard', __name__)


@bp.get('/trend/daily')
def trend_daily():
    """
    每日采集数据趋势API
    返回文献、新闻、召回三条折线的数据
    参数：
    - from: 起始日期 (格式: YYYY-MM-DD)
    - to: 结束日期 (格式: YYYY-MM-DD)
    默认显示最近3天的数据
    """
    date_from = request.args.get('from')
    date_to = request.args.get('to')

    try:
        dt_from = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
    except Exception:
        dt_from = None
    try:
        dt_to = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
    except Exception:
        dt_to = None

    # 默认显示最近3天的数据
    if dt_from is None or dt_to is None:
        dt_to = dt_to or datetime.utcnow()
        dt_from = dt_from or (dt_to - timedelta(days=3))

    print(f"Debug: trend_daily date range from {dt_from} to {dt_to}")

    # 查询新闻数据（按 updated_at）
    news_rows = (
        News.query.filter(News.updated_at >= dt_from, News.updated_at <= dt_to)
        .with_entities(func.date(News.updated_at), func.count(News.id))
        .group_by(func.date(News.updated_at))
        .all()
    )
    
    # 查询文献数据（按 updated_at）
    literature_rows = (
        Literature.query.filter(Literature.updated_at >= dt_from, Literature.updated_at <= dt_to)
        .with_entities(func.date(Literature.updated_at), func.count(Literature.id))
        .group_by(func.date(Literature.updated_at))
        .all()
    )
    
    # 查询召回数据（按 updated_at）
    recall_rows = (
        Recall.query.filter(Recall.updated_at >= dt_from, Recall.updated_at <= dt_to)
        .with_entities(func.date(Recall.updated_at), func.count(Recall.id))
        .group_by(func.date(Recall.updated_at))
        .all()
    )

    print(f"Debug: news={len(news_rows)}, literature={len(literature_rows)}, recall={len(recall_rows)}")

    # 初始化所有日期的数据结构
    date_keys = {}
    cur = dt_from
    while cur.date() <= dt_to.date():
        k = cur.strftime('%m-%d')
        date_keys[k] = {'新闻': 0, '文献': 0, '召回': 0}
        cur += timedelta(days=1)

    # 填充新闻数据
    for d, n in news_rows:
        if d:
            key = d.strftime('%m-%d')
            if key in date_keys:
                date_keys[key]['新闻'] = int(n or 0)
    
    # 填充文献数据
    for d, n in literature_rows:
        if d:
            key = d.strftime('%m-%d')
            if key in date_keys:
                date_keys[key]['文献'] = int(n or 0)
    
    # 填充召回数据
    for d, n in recall_rows:
        if d:
            key = d.strftime('%m-%d')
            if key in date_keys:
                date_keys[key]['召回'] = int(n or 0)

    # 转换为前端需要的格式
    trend_data = []
    for date_key in sorted(date_keys.keys()):
        trend_data.append({
            'name': date_key,
            '新闻': date_keys[date_key]['新闻'],
            '文献': date_keys[date_key]['文献'],
            '召回': date_keys[date_key]['召回']
        })
    
    print(f"Debug: returning {len(trend_data)} data points")
    return jsonify(trend_data)


# @bp.get('/sources')
# def source_stats():
#     """
#     来源渠道统计API - 预留接口
#     当前前端使用预设数据，此接口为后续真实数据对接预留
#     """
#     # 使用真实的filter表数据
    
#     try:
#         print("Debug: Starting source_stats query...")
        
#         # 测试数据库连接
#         db.session.execute(text("SELECT 1"))
#         print("Debug: Database connection successful")
        
#         # 查询数据
#         news_count = News_filter.query.count()
#         literature_count = LiteratureFilter.query.count()
#         recall_count = Recall_filter.query.count()
        
#         print(f"Debug: news_count={news_count}, literature_count={literature_count}, recall_count={recall_count}")
        
#         items = [
#             { 'name': '新闻', 'count': int(news_count or 0) },
#             { 'name': '文献', 'count': int(literature_count or 0) },
#             { 'name': '召回', 'count': int(recall_count or 0) },
#             { 'name': '毒性数据库', 'count': 50 },
#             { 'name': '医疗信息', 'count': 0 },
#         ]
#         print(f"Debug: returning items={items}")
#         return jsonify({'items': items})
#     except Exception as e:
#         print(f"Error in source_stats: {e}")
#         import traceback
#         traceback.print_exc()
#         # 返回默认数据
#         items = [
#             {'name': '新闻', 'count': 0},
#             {'name': '文献', 'count': 0},
#             {'name': '召回', 'count': 0},
#             {'name': '毒性数据库', 'count': 0},
#             {'name': '医疗信息', 'count': 0},
#         ]
#         return jsonify({'items': items})


# @bp.get('/collection/trend')
# def collection_trend():
#     """
#     采集数据趋势API - 预留接口
#     当前前端使用预设数据，此接口为后续真实数据对接预留
#     """
#     from ..models import News_filter, LiteratureFilter, Recall_filter
#     from sqlalchemy import func
#     from .. import db
    
#     print("Debug: collection_trend API called")
    
#     try:
#         # 测试数据库连接
#         db.session.execute(text("SELECT 1"))
#         print("Debug: Database connection successful")
        
#         date_from = request.args.get('from')
#         date_to = request.args.get('to')
        
#         try:
#             dt_from = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
#         except Exception:
#             dt_from = None
#         try:
#             dt_to = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
#         except Exception:
#             dt_to = None

#         if dt_from is None or dt_to is None:
#             dt_to = dt_to or datetime.utcnow()
#             dt_from = dt_from or (dt_to - timedelta(days=30))  # 默认30天
        
#         print(f"Debug: date range from {dt_from} to {dt_to}")

#         # 获取新闻采集趋势
#         news_rows = (
#             News_filter.query.filter(News_filter.created_at >= dt_from, News_filter.created_at <= dt_to)
#             .with_entities(func.date(News_filter.created_at), func.count(News_filter.id))
#             .group_by(func.date(News_filter.created_at))
#             .all()
#         )
        
#         # 获取文献采集趋势
#         literature_rows = (
#             LiteratureFilter.query.filter(LiteratureFilter.created_at >= dt_from, LiteratureFilter.created_at <= dt_to)
#             .with_entities(func.date(LiteratureFilter.created_at), func.count(LiteratureFilter.id))
#             .group_by(func.date(LiteratureFilter.created_at))
#             .all()
#         )
        
#         # 获取召回采集趋势
#         recall_rows = (
#             Recall_filter.query.filter(Recall_filter.created_at >= dt_from, Recall_filter.created_at <= dt_to)
#             .with_entities(func.date(Recall_filter.created_at), func.count(Recall_filter.id))
#             .group_by(func.date(Recall_filter.created_at))
#             .all()
#         )

#         print(f"Debug: news_rows={len(news_rows)}, literature_rows={len(literature_rows)}, recall_rows={len(recall_rows)}")

#         # 构建日期范围
#         date_keys = {}
#         cur = dt_from
#         while cur.date() <= dt_to.date():
#             k = cur.strftime('%m-%d')
#             date_keys[k] = {'新闻': 0, '文献': 0, '召回': 0}
#             cur += timedelta(days=1)

#         # 填充新闻数据
#         for d, n in news_rows:
#             if d:
#                 key = d.strftime('%m-%d')
#                 if key in date_keys:
#                     date_keys[key]['新闻'] = int(n or 0)
        
#         # 填充文献数据
#         for d, n in literature_rows:
#             if d:
#                 key = d.strftime('%m-%d')
#                 if key in date_keys:
#                     date_keys[key]['文献'] = int(n or 0)
        
#         # 填充召回数据
#         for d, n in recall_rows:
#             if d:
#                 key = d.strftime('%m-%d')
#                 if key in date_keys:
#                     date_keys[key]['召回'] = int(n or 0)

#         # 转换为前端需要的格式
#         trend_data = []
#         for date_key in sorted(date_keys.keys()):
#             trend_data.append({
#                 'name': date_key,
#                 '新闻': date_keys[date_key]['新闻'],
#                 '文献': date_keys[date_key]['文献'],
#                 '召回': date_keys[date_key]['召回']
#             })
        
#         print(f"Debug: returning trend_data with {len(trend_data)} items")
#         return jsonify(trend_data)
        
#     except Exception as e:
#         print(f"Error in collection_trend: {e}")
#         import traceback
#         traceback.print_exc()
#         # 返回空数据
#         return jsonify([])


# @bp.get('/sentiment')
# def sentiment_summary():
#     # 暂时返回模拟数据，后续可以基于实际的情感分析结果
#     # 这里可以根据新闻标题、召回描述等进行简单的情感分析
#     return jsonify({ 
#         'positive': 46, 
#         'neutral': 32, 
#         'negative': 22 
#     })


# @bp.get('/product-symptom/top')
# def product_symptom_top():
#     """
#     产品-不良反应热搜榜 Top5
#     返回半年内（180天）按证据支持分数（confidence）排序的前5个组合
#     """
#     import logging
#     logger = logging.getLogger(__name__)
    
#     try:
#         # 计算半年前的日期
#         dt_to = datetime.utcnow()
#         dt_from = dt_to - timedelta(days=180)
        
#         logger.info(f"Fetching top product-symptom pairs from {dt_from} to {dt_to}")
        
#         # 查询半年内的产品-症状关系，按 confidence 降序排列，取前5条
#         # 注意：这里假设 ProductSymptom 表的 create_at/update_at 字段记录了关系的时间
#         # 如果需要根据证据来源的时间过滤，需要 join ProductSymptomNews 和 ProductSymptomComp 表
#         top_relations = (
#             db.session.query(ProductSymptom)
#             .join(Product, ProductSymptom.product_id == Product.id)
#             .join(Symptom2, ProductSymptom.symptom_id == Symptom2.id)
#             .filter(ProductSymptom.update_at >= dt_from)
#             .filter(ProductSymptom.update_at <= dt_to)
#             .order_by(ProductSymptom.confidence.desc())
#             .limit(5)
#             .all()
#         )
        
#         # 格式化返回数据
#         items = []
#         for idx, relation in enumerate(top_relations, start=1):
#             # 计算证据数量 - 分别统计新闻和投诉数量
#             from ..models import ProductSymptomNews, ProductSymptomComp
            
#             news_count = db.session.query(func.count(ProductSymptomNews.id)).filter(
#                 ProductSymptomNews.product_symptom_id == relation.id
#             ).scalar() or 0
            
#             complaint_count = db.session.query(func.count(ProductSymptomComp.id)).filter(
#                 ProductSymptomComp.product_symptom_id == relation.id
#             ).scalar() or 0
            
#             evidence_count = news_count + complaint_count
            
#             items.append({
#                 'rank': idx,
#                 'id': relation.id,
#                 'product_id': relation.product_id,
#                 'product_name': relation.product.name,
#                 'symptom_id': relation.symptom_id,
#                 'symptom_name': relation.symptom.symptom_name,
#                 'confidence': float(relation.confidence) if relation.confidence else 0.0,
#                 'evidence_count': evidence_count,
#                 'updated_at': relation.update_at.isoformat() if relation.update_at else None
#             })
        
#         logger.info(f"Returning {len(items)} top product-symptom pairs")
        
#         return jsonify({
#             'code': 200,
#             'message': '获取成功',
#             'data': {
#                 'items': items,
#                 'time_range': {
#                     'from': dt_from.strftime('%Y-%m-%d'),
#                     'to': dt_to.strftime('%Y-%m-%d'),
#                     'days': 180
#                 }
#             }
#         }), 200
        
#     except Exception as e:
#         logger.error(f"Error fetching top product-symptom pairs: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({
#             'code': 500,
#             'message': '获取热搜榜失败',
#             'error': str(e)
#         }), 500


# =====================================================
# 新 Dashboard API 端点
# =====================================================

@bp.get('/overview/stats')
def overview_stats():
    """
    总览统计数据API
    返回：系统资料库总数、标准化资料库、伤害事件数、候选化学应激源数
    """
    try:
        # 1. 系统资料库 = 文献 + 新闻 + 投诉 的总数量（所有表的所有数据）
        literature_count = Literature.query.count()
        news_count = News.query.count()
        complaints_count = Complaints.query.count()
        system_library = literature_count + news_count + complaints_count

        # 2. 标准化资料库 = 已处理的数据（state为True/1的文献 + 新闻 + 投诉）
        literature_processed = Literature.query.filter(Literature.state == 1).count()
        news_processed = News.query.filter(News.state == 1).count()
        complaints_processed = Complaints.query.filter(Complaints.state == 1).count()
        standardized_library = literature_processed + news_processed + complaints_processed

        # 3. 伤害事件数 = 已处理的新闻 + 投诉（state为1）
        injury_events = news_processed + complaints_processed

        # 4. 候选化学应激源数 = allergen表中所有数据
        chemical_stressors = Allergen.query.count()

        return jsonify({
            'systemLibrary': system_library,
            'collectionVolume': standardized_library,
            'injuryEvents': injury_events,
            'chemicalStressors': chemical_stressors,
        })
    except Exception as e:
        logger.error(f"Error in overview_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'systemLibrary': 0,
            'collectionVolume': 0,
            'injuryEvents': 0,
            'chemicalStressors': 0,
        })


@bp.get('/overview/category-distribution')
def category_distribution():
    """
    产品类别分布API
    返回product_1表下每个类别包含的product_3数量
    """
    try:
        # 5. 产品类别分布 = product_1表下每个类别包含多少个product_3
        results = (
            db.session.query(
                Category.name,
                func.count(Product.id).label('count')
            )
            .join(Type, Category.id == Type.category_id)
            .join(Product, Type.id == Product.category_id)
            .group_by(Category.name)
            .order_by(func.count(Product.id).desc())
            .all()
        )

        items = [{'name': name, 'value': count} for name, count in results]
        return jsonify({'items': items})
    except Exception as e:
        logger.error(f"Error in category_distribution: {e}")
        return jsonify({'items': []})


@bp.get('/overview/hot-alerts')
def hot_alerts():
    """
    热门预警 Top 5
    返回事件数最多的产品-不良反应组合
    """
    try:
        # 统计每个产品-不良反应组合的事件数（新闻+投诉），取 Top 5
        results = (
            db.session.query(
                ProductSymptom.id,
                Product.name.label('product_name'),
                Symptom2.symptom_name.label('adverse_reaction'),
                func.count(ProductSymptomNews.id).label('news_count'),
            )
            .join(Product, ProductSymptom.product_id == Product.id)
            .join(Symptom2, ProductSymptom.symptom_id == Symptom2.id)
            .outerjoin(ProductSymptomNews, ProductSymptom.id == ProductSymptomNews.product_symptom_id)
            .group_by(ProductSymptom.id, Product.name, Symptom2.symptom_name)
            .order_by(func.count(ProductSymptomNews.id).desc())
            .limit(5)
            .all()
        )

        items = []
        for idx, row in enumerate(results, 1):
            # 也统计投诉数
            comp_count = db.session.query(func.count(ProductSymptomComp.id)).filter(
                ProductSymptomComp.product_symptom_id == row.id
            ).scalar() or 0
            total_events = (row.news_count or 0) + comp_count

            items.append({
                'rank': idx,
                'product': row.product_name,
                'adverseReaction': row.adverse_reaction,
                'eventCount': total_events,
            })

        return jsonify({'items': items})
    except Exception as e:
        logger.error(f"Error in hot_alerts: {e}")
        return jsonify({'items': []})


def _calculate_prr_chi_square(product_id: int, symptom_id: int):
    """
    计算指定产品-不良反应组合的 PRR 和 χ² 值
    基于论文中的2×2列联表方法：
    
    A = 同时包含目标产品p和不良反应a的事件数
    B = 包含产品p但不包含不良反应a的事件数
    C = 不包含产品p但包含不良反应a的事件数
    D = 既不包含产品p也不包含不良反应a的事件数
    N = A+B+C+D
    
    PRR = (A/(A+B)) / (C/(C+D))
    χ² = N(AD-BC)² / ((A+B)(C+D)(A+C)(B+D))
    """
    try:
        # A: 包含产品p AND 不良反应a 的事件数
        A = db.session.query(func.count(ProductSymptomNews.id)).join(
            ProductSymptom, ProductSymptomNews.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id == product_id,
            ProductSymptom.symptom_id == symptom_id
        ).scalar() or 0

        # 加上投诉数
        A_comp = db.session.query(func.count(ProductSymptomComp.id)).join(
            ProductSymptom, ProductSymptomComp.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id == product_id,
            ProductSymptom.symptom_id == symptom_id
        ).scalar() or 0
        A = A + A_comp

        # B: 包含产品p但不包含不良反应a的事件数
        B_news = db.session.query(func.count(ProductSymptomNews.id)).join(
            ProductSymptom, ProductSymptomNews.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id == product_id,
            ProductSymptom.symptom_id != symptom_id
        ).scalar() or 0
        B_comp = db.session.query(func.count(ProductSymptomComp.id)).join(
            ProductSymptom, ProductSymptomComp.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id == product_id,
            ProductSymptom.symptom_id != symptom_id
        ).scalar() or 0
        B = B_news + B_comp

        # C: 不包含产品p但包含不良反应a的事件数
        C_news = db.session.query(func.count(ProductSymptomNews.id)).join(
            ProductSymptom, ProductSymptomNews.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id != product_id,
            ProductSymptom.symptom_id == symptom_id
        ).scalar() or 0
        C_comp = db.session.query(func.count(ProductSymptomComp.id)).join(
            ProductSymptom, ProductSymptomComp.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id != product_id,
            ProductSymptom.symptom_id == symptom_id
        ).scalar() or 0
        C = C_news + C_comp

        # D: 既不包含产品p也不包含不良反应a的事件数
        D_news = db.session.query(func.count(ProductSymptomNews.id)).join(
            ProductSymptom, ProductSymptomNews.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id != product_id,
            ProductSymptom.symptom_id != symptom_id
        ).scalar() or 0
        D_comp = db.session.query(func.count(ProductSymptomComp.id)).join(
            ProductSymptom, ProductSymptomComp.product_symptom_id == ProductSymptom.id
        ).filter(
            ProductSymptom.product_id != product_id,
            ProductSymptom.symptom_id != symptom_id
        ).scalar() or 0
        D = D_news + D_comp

        N = A + B + C + D

        # 计算 PRR
        if (A + B) == 0 or (C + D) == 0 or C == 0:
            prr = 0.0
        else:
            prr = (A / (A + B)) / (C / (C + D))

        # 计算 χ²
        denom = (A + B) * (C + D) * (A + C) * (B + D)
        if denom == 0:
            chi_square = 0.0
        else:
            chi_square = (N * (A * D - B * C) ** 2) / denom

        # 判定信号等级
        if A >= 3 and prr >= 2 and chi_square >= 4:
            signal_level = 'strong'
            signal_score = 3
        elif A >= 3 and 1 <= prr < 2 and chi_square >= 4:
            signal_level = 'medium'
            signal_score = 2
        else:
            signal_level = 'weak'
            signal_score = 1

        return {
            'A': A, 'B': B, 'C': C, 'D': D, 'N': N,
            'prr': round(prr, 2),
            'chiSquare': round(chi_square, 2),
            'signalLevel': signal_level,
            'signalScore': signal_score,
        }
    except Exception as e:
        logger.error(f"Error calculating PRR/chi-square for product={product_id}, symptom={symptom_id}: {e}")
        return {
            'A': 0, 'B': 0, 'C': 0, 'D': 0, 'N': 0,
            'prr': 0.0, 'chiSquare': 0.0,
            'signalLevel': 'weak', 'signalScore': 1,
        }


@bp.get('/injury-events')
def injury_events():
    """
    伤害事件筛查API
    返回所有产品-不良反应组合的PRR、χ²值及信号等级
    支持筛选参数：date_from, date_to, category, adverse_reaction_type
    """
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        category = request.args.get('category')
        adverse_reaction_type = request.args.get('adverse_reaction_type')

        query = (
            db.session.query(ProductSymptom)
            .join(Product, ProductSymptom.product_id == Product.id)
            .join(Symptom2, ProductSymptom.symptom_id == Symptom2.id)
        )

        # 按产品类别筛选
        if category and category != '全部':
            query = query.join(Type, Product.category_id == Type.id).join(
                Category, Type.category_id == Category.id
            ).filter(Category.name == category)

        # 按日期范围筛选
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(ProductSymptom.create_at >= dt_from)
            except ValueError:
                pass
        if date_to:
            try:
                dt_to = datetime.strptime(date_to, '%Y-%m-%d')
                query = query.filter(ProductSymptom.create_at <= dt_to)
            except ValueError:
                pass

        relations = query.all()

        items = []
        for relation in relations:
            # 计算事件数
            news_count = db.session.query(func.count(ProductSymptomNews.id)).filter(
                ProductSymptomNews.product_symptom_id == relation.id
            ).scalar() or 0
            comp_count = db.session.query(func.count(ProductSymptomComp.id)).filter(
                ProductSymptomComp.product_symptom_id == relation.id
            ).scalar() or 0
            event_count = news_count + comp_count

            # 计算 PRR 和 χ²
            prr_data = _calculate_prr_chi_square(relation.product_id, relation.symptom_id)

            # 按不良反应类型筛选
            if adverse_reaction_type and adverse_reaction_type != '全部':
                if relation.symptom.symptom_name != adverse_reaction_type:
                    continue

            # 检查是否有风险评估数据（即是否有关联的allergen数据）
            has_risk_assessment = db.session.query(
                func.count(AllergenProduct.id)
            ).filter(
                AllergenProduct.product_id == relation.product_id
            ).scalar() > 0

            items.append({
                'id': relation.id,
                'productId': relation.product_id,
                'productName': relation.product.name,
                'adverseReactionId': relation.symptom_id,
                'adverseReactionName': relation.symptom.symptom_name,
                'eventCount': event_count,
                'prr': prr_data['prr'],
                'chiSquare': prr_data['chiSquare'],
                'signalLevel': prr_data['signalLevel'],
                'signalScore': prr_data['signalScore'],
                'hasRiskAssessment': has_risk_assessment,
            })

        # 按事件数降序排列
        items.sort(key=lambda x: x['eventCount'], reverse=True)

        return jsonify({'items': items})
    except Exception as e:
        logger.error(f"Error in injury_events: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'items': []})


@bp.get('/injury-events/filters')
def injury_event_filters():
    """
    获取伤害事件筛选选项
    """
    try:
        # 获取所有产品类别
        categories = [row.name for row in Category.query.all()]

        # 获取所有不良反应类型
        adverse_reactions = [row.symptom_name for row in Symptom2.query.all()]

        return jsonify({
            'categories': categories,
            'adverseReactions': adverse_reactions,
        })
    except Exception as e:
        logger.error(f"Error in injury_event_filters: {e}")
        return jsonify({'categories': [], 'adverseReactions': []})


@bp.get('/risk-matrix/<int:product_id>/<int:symptom_id>')
def risk_matrix(product_id, symptom_id):
    """
    风险矩阵结果API
    根据选定的产品-不良反应组合，返回化学应激源的三维风险评分
    X: 暴露潜势 (1-3)
    Y: 伤害风险 (1-3)
    Z: 事件信号 (1-3)
    S = X × Y × Z
    """
    try:
        product = Product.query.get(product_id)
        symptom = Symptom2.query.get(symptom_id)

        if not product or not symptom:
            return jsonify({'error': '产品或不良反应不存在'}), 404

        # 计算事件信号 Z
        prr_data = _calculate_prr_chi_square(product_id, symptom_id)
        z_score = prr_data['signalScore']

        # 查找关联的化学应激源（通过 allergen_product 表，且必须与目标不良反应有关联）
        allergen_products = (
            db.session.query(AllergenProduct, Allergen)
            .join(Allergen, AllergenProduct.allergen_id == Allergen.id)
            .join(AllergenSymptom, AllergenSymptom.allergen_id == Allergen.id)
            .filter(AllergenProduct.product_id == product_id)
            .filter(AllergenSymptom.symptom_id == symptom_id)
            .distinct()
            .all()
        )

        chemical_stressors = []
        for ap, allergen in allergen_products:
            # X: 暴露潜势
            exposure_detail = ExposureScoringDetail.query.filter_by(
                allergen_product_id=ap.id
            ).first()

            if exposure_detail and exposure_detail.total_score:
                raw_exposure = float(exposure_detail.total_score)
                # 原始5-20分 → 三级：(5,9]=1, (10,15]=2, (16,20]=3
                if raw_exposure <= 9:
                    x_score = 1
                elif raw_exposure <= 15:
                    x_score = 2
                else:
                    x_score = 3
                x_raw = raw_exposure
            elif ap.exposure_score:
                raw_exposure = float(ap.exposure_score)
                if raw_exposure <= 9:
                    x_score = 1
                elif raw_exposure <= 15:
                    x_score = 2
                else:
                    x_score = 3
                x_raw = raw_exposure
            else:
                x_score = 1
                x_raw = 0

            # Y: 伤害风险 (TRAEC评分)
            allergen_symptom = AllergenSymptom.query.filter_by(
                allergen_id=allergen.id,
                symptom_id=symptom_id
            ).first()

            y_raw = 0.0
            if allergen_symptom and allergen_symptom.traec_score:
                y_raw = float(allergen_symptom.traec_score)
            else:
                # 尝试从文献评分计算 TRAEC
                if allergen_symptom:
                    from ..services.traec_scoring import calculate_traec_score
                    try:
                        y_raw = calculate_traec_score(allergen_symptom.id, db.session)
                    except Exception:
                        y_raw = 0.0

            # 原始TRAEC 0-10分 → 三级：(0,4]=1, (4,8]=2, (8,10]=3
            if y_raw <= 4:
                y_score = 1
            elif y_raw <= 8:
                y_score = 2
            else:
                y_score = 3

            # 综合得分 S = X × Y × Z
            total_score = x_score * y_score * z_score
            all_score = (x_raw / 20) * (y_raw / 10) * z_score
            
            # 风险等级
            if total_score >= 18:
                risk_level = 'high'
            elif total_score >= 8:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            # 证据充分性评估（基于文献数量）
            evidence_count = 0
            if allergen_symptom:
                epi_count = LiteratureEpiScoring.query.filter_by(relation_id=allergen_symptom.id).count()
                vivo_count = LiteratureVivoScoring.query.filter_by(relation_id=allergen_symptom.id).count()
                vitro_count = LiteratureVitroScoring.query.filter_by(relation_id=allergen_symptom.id).count()
                evidence_count = epi_count + vivo_count + vitro_count

            if evidence_count >= 5:
                evidence_sufficiency = 5
            elif evidence_count >= 3:
                evidence_sufficiency = 4
            elif evidence_count >= 2:
                evidence_sufficiency = 3
            elif evidence_count >= 1:
                evidence_sufficiency = 2
            else:
                evidence_sufficiency = 1

            chemical_stressors.append({
                'id': allergen.id,
                'nameCn': allergen.name,
                'cas': allergen.cas_number or '',
                'xScore': x_score,
                'xRaw': round(x_raw, 2),
                'yScore': y_score,
                'yRaw': round(y_raw, 2),
                'zScore': z_score,
                'totalScore': total_score,
                'allScore':all_score,
                'riskLevel': risk_level,
                'evidenceSufficiency': evidence_sufficiency,
                'evidenceCount': evidence_count,
            })

        # 按原始分（xRaw * yRaw * zScore）大小降序排列
        chemical_stressors.sort(key=lambda x: (x['xRaw'] * x['yRaw'] * x['zScore']), reverse=True)

        # 生成研判建议
        recommendations = _generate_recommendations(
            product.name, symptom.symptom_name, chemical_stressors, prr_data
        )

        return jsonify({
            'productName': product.name,
            'adverseReactionName': symptom.symptom_name,
            'prr': prr_data['prr'],
            'chiSquare': prr_data['chiSquare'],
            'signalLevel': prr_data['signalLevel'],
            'signalScore': z_score,
            'chemicalStressors': chemical_stressors,
            'recommendations': recommendations,
        })
    except Exception as e:
        logger.error(f"Error in risk_matrix: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _generate_recommendations(product_name, symptom_name, chemical_stressors, prr_data):
    """生成风险矩阵研判建议"""
    if not chemical_stressors:
        return {
            'sameLevelExplanation': f'当前未找到"{product_name}-{symptom_name}"组合下的候选化学应激源。',
            'followUpSuggestions': ['扩充产品成分数据库', '补充化学物质检测数据', '收集更多伤害事件报告']
        }

    risk_levels = set(cs['riskLevel'] for cs in chemical_stressors)
    level_names = {'high': '高风险', 'medium': '中等风险', 'low': '低风险'}

    # 同等级解释
    if len(risk_levels) == 1:
        level = list(risk_levels)[0]
        same_level_text = (
            f'当前候选物均处于同一风险等级（{level_names[level]}），主要原因：\n'
            f'1. 本次评估针对固定的"产品-不良反应"组合，Z轴信号得分相近；\n'
            f'2. 目前公开证据类型与质量相近，导致Y轴伤害风险分值接近；\n'
            f'3. 暴露潜势（X轴）因产品属性与使用人群相似而趋同。'
        )
    else:
        same_level_text = f'当前候选化学应激源分布在 {", ".join(level_names[l] for l in risk_levels)} 等风险等级。综合得分越高的化学物质越值得优先关注。'

    # 后续建议
    follow_up = [
        '产品实际含量',
        '毒化产物检测',
        '证据释放量',
        '儿童使用场景',
        '更高质量毒理证据（如人体研究、剂量反应）'
    ]

    return {
        'sameLevelExplanation': same_level_text,
        'followUpSuggestions': follow_up,
    }
