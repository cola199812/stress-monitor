from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Product

bp = Blueprint('products', __name__)


@bp.get('/')
def list_products():
    category_id = request.args.get('categoryId')
    q = Product.query
    if category_id is not None and category_id != "":
        try:
            cat_id = int(category_id)
        except (TypeError, ValueError):
            return jsonify({'code': 'BadRequest', 'message': 'categoryId must be an integer'}), 400
        q = q.filter_by(category_id=cat_id)
    products = q.order_by(Product.id.asc()).all()

    def to_dict(p: Product):
        return {
            'id': str(p.id),
            'categoryId': str(p.category_id),
            'name': p.name
        }

    return jsonify({'items': [to_dict(p) for p in products]})


@bp.post('/')
def create_product():
    data = request.get_json(silent=True) or {}
    category_id = data.get('categoryId')
    name = (data.get('name') or '').strip()

    if not category_id or not name:
        return jsonify({'code': 'BadRequest', 'message': 'categoryId and name are required'}), 400

    p = Product(product2_id=int(category_id), name=name)
    db.session.add(p)
    try:
        db.session.flush()  # 获取 p.id
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('product3', p.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync product {p.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'product already exists in the category'}), 409

    return jsonify({'id': str(p.id), 'categoryId': str(p.product2_id), 'name': p.name, 'keywords': [k.keyword for k in p.keywords] or None})


@bp.patch('/<int:prod_id>')
def update_product(prod_id: int):
    p = Product.query.get(prod_id)
    if not p:
        return jsonify({'code': 'NotFound', 'message': 'product not found'}), 404

    data = request.get_json(silent=True) or {}
    name = data.get('name')

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'code': 'BadRequest', 'message': 'name cannot be empty'}), 400
        p.name = name

    try:
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('product3', p.id, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync product {p.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'product already exists in the category'}), 409

    return jsonify({'id': str(p.id), 'categoryId': str(p.product2_id), 'name': p.name, 'keywords': [k.keyword for k in p.keywords] or None})


@bp.delete('/<int:prod_id>')
def delete_product(prod_id: int):
    p = Product.query.get(prod_id)
    if not p:
        return jsonify({'code': 'NotFound', 'message': 'product not found'}), 404

    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        sync_to_neo4j('product3', prod_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete product {prod_id} from Neo4j: {e}")

    db.session.delete(p)
    db.session.commit()
    return jsonify({'success': True})


