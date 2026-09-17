from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy import func
from ..models import Literature, News, Recall, Category, Product
from .. import db


bp = Blueprint('collection', __name__)


@bp.get('/stats')
def collection_def_summary():
    """聚合统计（为大屏/摘要页提供后端数据）。
量：文献/新闻/投诉(以召回替代)。

    Query: product?: string(名称，仅保留兼容，不在此处使用);
           from?: yyyy-MM-dd; to?: yyyy-MM-dd
    Response: { months: string[]; literature: number[]; news: number[]; complaints: number[] }
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

    # 文献 publish_date 为 Date；统计时按月聚合（在 Python 侧格式化，避免 DB 方言差异）
    lit_q = Literature.query
    if dt_from:
        lit_q = lit_q.filter(Literature.publish_date >= dt_from.date())
    if dt_to:
        lit_q = lit_q.filter(Literature.publish_date <= dt_to.date())
    lit_rows = lit_q.with_entities(
        Literature.publish_date, func.count(Literature.id)
    ).group_by(Literature.publish_date).all()

    # 新闻 publish_time 为 DateTime
    news_q = News.query
    if dt_from:
        news_q = news_q.filter(News.publish_time >= dt_from)
    if dt_to:
        news_q = news_q.filter(News.publish_time <= dt_to)
    news_rows = news_q.with_entities(
        News.publish_time, func.count(News.id)
    ).group_by(News.publish_time).all()

    # 投诉：数据库中没有专门投诉表，先用 Recall 近似统计（按 time 字段）
    rec_q = Recall.query
    if dt_from:
        rec_q = rec_q.filter(Recall.time >= dt_from)
    if dt_to:
        rec_q = rec_q.filter(Recall.time <= dt_to)
    rec_rows = rec_q.with_entities(
        Recall.time, func.count(Recall.id)
    ).group_by(Recall.time).all()

    def to_month_map(rows):
        d = {}
        for dt_val, cnt in rows:
            if dt_val is None:
                continue
            # date / datetime 都支持 strftime，统一取到月
            key = dt_val.strftime('%Y-%m')
            d[key] = d.get(key, 0) + int(cnt or 0)
        return d

    lit_map = to_month_map(lit_rows)
    news_map = to_month_map(news_rows)
    rec_map = to_month_map(rec_rows)

    months = sorted(set(lit_map) | set(news_map) | set(rec_map))

    result = {
        'months': months,
        'literature': [lit_map.get(m, 0) for m in months],
        'news': [news_map.get(m, 0) for m in months],
        'recall': [rec_map.get(m, 0) for m in months],
        # 兼容旧字段名
        'complaints': [rec_map.get(m, 0) for m in months],
    }
    return jsonify(result)


@bp.get('/category-counts')
def category_counts():
    """返回六大类别的总量统计：总产品、总过敏原、总症状。

    数据库结构：product_1(类别) -> product_2(类型) -> product_3(产品)
    过敏原通过AllergenProduct关系与产品关联
    症状通过AllergenSymptom关系与过敏原关联

    Response: { items: [{ name, products, allergens, symptoms }] }
    """
    from ..models import Type, AllergenProduct, AllergenSymptom

    # 获取所有类别（product_1）
    cat_rows = db.session.query(Category.id, Category.name).all()
    name_to_id = {name: int(cid) for cid, name in cat_rows}

    print(f"找到的类别: {name_to_id}")

    items = []
    for cat_id, cat_name in cat_rows:
        # 1. 统计该类别下的产品数量（通过 product_1 -> product_2 -> product_3）
        product_count = (
            db.session.query(func.count(Product.id))
            .join(Type, Product.category_id == Type.id)
            .filter(Type.category_id == cat_id)
            .scalar() or 0
        )

        # 2. 统计该类别下的过敏原数量（通过产品-过敏原关系）
        allergen_count = (
            db.session.query(func.count(func.distinct(AllergenProduct.allergen_id)))
            .join(Product, AllergenProduct.product_id == Product.id)
            .join(Type, Product.category_id == Type.id)
            .filter(Type.category_id == cat_id)
            .scalar() or 0
        )

        # 3. 统计该类别下的症状数量（通过产品-过敏原-症状关系）
        symptom_count = (
            db.session.query(func.count(func.distinct(AllergenSymptom.symptom_id)))
            .join(AllergenProduct, AllergenSymptom.allergen_id == AllergenProduct.allergen_id)
            .join(Product, AllergenProduct.product_id == Product.id)
            .join(Type, Product.category_id == Type.id)
            .filter(Type.category_id == cat_id)
            .scalar() or 0
        )

        print(f"类别 {cat_name}: 产品={product_count}, 过敏原={allergen_count}, 症状={symptom_count}")

        items.append({
            'name': cat_name,
            'products': int(product_count),
            'allergens': int(allergen_count),
            'symptoms': int(symptom_count),
        })

    return jsonify({ 'items': items })

