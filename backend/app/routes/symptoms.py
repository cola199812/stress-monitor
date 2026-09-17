from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Allergen

bp = Blueprint('symptoms', __name__)


@bp.get('/')
def list_symptoms():
    """获取症状列表"""
    allergen_id = request.args.get('allergenId')
    
    q = Symptom.query
    if allergen_id is not None and allergen_id != "":
        try:
            allerg_id = int(allergen_id)
            q = q.filter_by(allergen_id=allerg_id)
        except (TypeError, ValueError):
            return jsonify({'code': 'BadRequest', 'message': 'allergenId must be an integer'}), 400
    
    symptoms = q.order_by(Symptom.id.asc()).all()

    def to_dict(s: Symptom):
        return {
            'id': str(s.id),
            'allergenId': str(s.allergen_id),
            'name': s.name,
            'description': s.description
        }

    return jsonify({'items': [to_dict(s) for s in symptoms]})


@bp.post('/')
def create_symptom():
    """创建症状"""
    data = request.get_json(silent=True) or {}
    allergen_id = data.get('allergenId')
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip() or None

    if not allergen_id or not name:
        return jsonify({'code': 'BadRequest', 'message': 'allergenId and name are required'}), 400

    # 验证过敏原是否存在
    allergen = Allergen.query.get(int(allergen_id))
    if not allergen:
        return jsonify({'code': 'BadRequest', 'message': 'allergen not found'}), 400

    s = Symptom(
        allergen_id=int(allergen_id), 
        name=name,
        description=description
    )
    db.session.add(s)
    
    try:
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('symptom', s.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync symptom {s.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'symptom already exists for this allergen'}), 409

    return jsonify({
        'id': str(s.id), 
        'allergenId': str(s.allergen_id), 
        'name': s.name,
        'description': s.description
    })


@bp.patch('/<int:symptom_id>')
def update_symptom(symptom_id: int):
    """更新症状"""
    s = Symptom.query.get(symptom_id)
    if not s:
        return jsonify({'code': 'NotFound', 'message': 'symptom not found'}), 404

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    description = data.get('description')

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'code': 'BadRequest', 'message': 'name cannot be empty'}), 400
        s.name = name

    if description is not None:
        s.description = description.strip() or None

    try:
        db.session.commit()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('symptom', s.id, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync symptom {s.id} to Neo4j: {e}")
            
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'symptom name already exists for this allergen'}), 409

    return jsonify({
        'id': str(s.id), 
        'allergenId': str(s.allergen_id), 
        'name': s.name,
        'description': s.description
    })


@bp.delete('/<int:symptom_id>')
def delete_symptom(symptom_id: int):
    """删除症状"""
    s = Symptom.query.get(symptom_id)
    if not s:
        return jsonify({'code': 'NotFound', 'message': 'symptom not found'}), 404

    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        sync_to_neo4j('symptom', symptom_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete symptom {symptom_id} from Neo4j: {e}")

    db.session.delete(s)
    db.session.commit()
    return jsonify({'success': True})


@bp.get('/<int:symptom_id>')
def get_symptom(symptom_id: int):
    """获取单个症状详情"""
    s = Symptom.query.get(symptom_id)
    if not s:
        return jsonify({'code': 'NotFound', 'message': 'symptom not found'}), 404

    return jsonify({
        'id': str(s.id),
        'allergenId': str(s.allergen_id),
        'name': s.name,
        'description': s.description,
        'allergen': {
            'id': str(s.allergen.id),
            'name': s.allergen.name,
            'product': {
                'id': str(s.allergen.product.id),
                'name': s.allergen.product.name
            } if s.allergen.product else None
        } if s.allergen else None
    })
