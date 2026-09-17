from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Type

bp = Blueprint('types', __name__)


@bp.get('/')
def list_types():
    category_id = request.args.get('categoryId')
    q = Type.query
    if category_id is not None and category_id != "":
        try:
            cat_id = int(category_id)
        except (TypeError, ValueError):
            return jsonify({'code': 'BadRequest', 'message': 'categoryId must be an integer'}), 400
        q = q.filter_by(category_id=cat_id)
    types = q.order_by(Type.id.asc()).all()

    def to_dict(t: Type):
        return {
            'id': str(t.id),
            'categoryId': str(t.category_id),
            'name': t.name
        }

    return jsonify({'items': [to_dict(t) for t in types]})


@bp.post('/')
def create_type():
    data = request.get_json(silent=True) or {}
    category_id = data.get('categoryId')
    name = (data.get('name') or '').strip()

    if not category_id or not name:
        return jsonify({'code': 'BadRequest', 'message': 'categoryId and name are required'}), 400

    t = Type(category_id=int(category_id), name=name)
    db.session.add(t)
    try:
        db.session.flush() 
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('product2', t.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync type {t.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'type already exists in the category'}), 409

    return jsonify({'id': str(t.id), 'categoryId': str(t.product1_id), 'name': t.name, 'keywords': [k.keyword for k in t.keywords] or None})


@bp.patch('/<int:type_id>')
def update_type(type_id: int):
    t = Type.query.get(type_id)
    if not t:
        return jsonify({'code': 'NotFound', 'message': 'type not found'}), 404

    data = request.get_json(silent=True) or {}
    name = data.get('name')

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'code': 'BadRequest', 'message': 'name cannot be empty'}), 400
        t.name = name

    try:
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('product2', t.id, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync type {t.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'type already exists in the category'}), 409

    return jsonify({'id': str(t.id), 'categoryId': str(t.product1_id), 'name': t.name, 'keywords': [k.keyword for k in t.keywords] or None})


@bp.delete('/<int:type_id>')
def delete_type(type_id: int):
    t = Type.query.get(type_id)
    if not t:
        return jsonify({'code': 'NotFound', 'message': 'type not found'}), 404

    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        sync_to_neo4j('product2', type_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete type {type_id} from Neo4j: {e}")

    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True})
