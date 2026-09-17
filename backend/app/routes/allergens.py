from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Allergen, Product, AllergenProduct, Type

bp = Blueprint('allergens', __name__)


@bp.get('/')
def list_allergens():
    """获取过敏原列表"""
    category_id = request.args.get('categoryId')
    product_id = request.args.get('productId')
    
    q = Allergen.query
    if product_id is not None and product_id != "":
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return jsonify({'code': 'BadRequest', 'message': 'productId must be an integer'}), 400
        q = q.join(AllergenProduct, AllergenProduct.allergen_id == Allergen.id).filter(AllergenProduct.product_id == pid)
    elif category_id is not None and category_id != "":
        try:
            cat_id = int(category_id)
            # 通过产品链路筛选：Category(Product1) -> Type(Product2) -> Product(Product3) -> AllergenProduct -> Allergen
            q = (
                q.join(AllergenProduct, AllergenProduct.allergen_id == Allergen.id)
                 .join(Product, AllergenProduct.product_id == Product.id)
                 .join(Type, Product.category_id == Type.id)
                 .filter(Type.category_id == cat_id)
            )
        except (TypeError, ValueError):
            return jsonify({'code': 'BadRequest', 'message': 'categoryId must be an integer'}), 400
    
    allergens = q.order_by(Allergen.id.asc()).all()

    def to_dict(a: Allergen):
        return {
            'id': str(a.id),
            'name': a.name,
            'description': a.description
        }

    return jsonify({'items': [to_dict(a) for a in allergens]})


@bp.post('/')
def create_allergen():
    """创建过敏原（全局，不直接归属类别）"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip() or None

    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    a = Allergen(
        name=name,
        description=description
    )
    db.session.add(a)
    
    try:
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('allergen', a.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync allergen {a.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'allergen name already exists'}), 409

    return jsonify({
        'id': str(a.id),
        'name': a.name,
        'description': a.description
    })


@bp.patch('/<int:allergen_id>')
def update_allergen(allergen_id: int):
    """更新过敏原"""
    a = Allergen.query.get(allergen_id)
    if not a:
        return jsonify({'code': 'NotFound', 'message': 'allergen not found'}), 404

    # 记录旧名称用于Neo4j同步
    old_name = a.name

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    description = data.get('description')

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'code': 'BadRequest', 'message': 'name cannot be empty'}), 400
        a.name = name

    if description is not None:
        a.description = description.strip() or None

    try:
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_allergen_with_old_name
            sync_allergen_with_old_name(a.id, old_name, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync allergen {a.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'allergen name already exists for this product'}), 409

    return jsonify({
        'id': str(a.id),
        'name': a.name,
        'description': a.description
    })


@bp.get('/<int:allergen_id>')
def get_allergen(allergen_id: int):
    """获取单个过敏原详情"""
    a = Allergen.query.get(allergen_id)
    if not a:
        return jsonify({'code': 'NotFound', 'message': 'allergen not found'}), 404

    return jsonify({
        'id': str(a.id),
        'name': a.name,
        'description': a.description
    })
