from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Category, Type

bp = Blueprint('categories', __name__)


@bp.get('/')
def list_categories():
    categories = Category.query.order_by(Category.id.asc()).all()
    return jsonify({
        'items': [{'id': str(c.id), 'name': c.name} for c in categories]
    })


@bp.post('/')
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    c = Category(name=name)
    db.session.add(c)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'category name already exists'}), 409

    return jsonify({'id': str(c.id), 'name': c.name})


@bp.patch('/<int:cat_id>')
def update_category(cat_id: int):
    c = Category.query.get(cat_id)
    if not c:
        return jsonify({'code': 'NotFound', 'message': 'category not found'}), 404

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'code': 'BadRequest', 'message': 'name cannot be empty'}), 400
        c.name = name
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'category name already exists'}), 409
    return jsonify({'id': str(c.id), 'name': c.name})


@bp.delete('/<int:cat_id>')
def delete_category(cat_id: int):
    c = Category.query.get(cat_id)
    if not c:
        return jsonify({'code': 'NotFound', 'message': 'category not found'}), 404

    # 获取所有关联的产品
    products = Type.query.filter_by(category_id=cat_id).all()
    
    # 先删除所有关联的产品（包括同步到Neo4j）
    for product in products:
        # 同步删除到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('product', product.id, 'delete')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to delete product {product.id} from Neo4j: {e}")
        
        # 删除产品（会自动级联删除相关的关键词绑定等）
        db.session.delete(product)
    
    # 删除分类
    db.session.delete(c)
    db.session.commit()
    return jsonify({'success': True})


