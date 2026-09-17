from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import (
    Category, Type, Product, Allergen, Symptom1, Symptom2, Symptom3,
    AllergenProduct, AllergenSymptom, ProductSymptom
)

bp = Blueprint('entity', __name__)


# ==================== 产品管理 ====================

@bp.get('/products/level1')
def get_products_level1():
    """获取一级产品列表"""
    products = Category.query.order_by(Category.id.asc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None
    } for p in products])


@bp.get('/products/level2/<int:category_id>')
def get_products_level2(category_id: int):
    """获取二级产品列表"""
    products = Type.query.filter_by(category_id=category_id).order_by(Type.id.asc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category_id': p.category_id,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None
    } for p in products])


@bp.get('/products/level3/<int:category_id>')
def get_products_level3(category_id: int):
    """获取三级产品列表"""
    products = Product.query.filter_by(category_id=category_id).order_by(Product.id.asc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category_id': p.category_id,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None
    } for p in products])


@bp.get('/products/level3')
def get_all_products_level3():
    """获取所有三级产品列表"""
    products = Product.query.order_by(Product.id.asc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category_id': p.category_id,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None
    } for p in products])


@bp.post('/products')
def create_product():
    """创建产品"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    level = data.get('level', 1)
    category_id = data.get('category_id')

    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    try:
        if level == 1:
            product = Category(name=name)
        elif level == 2:
            if not category_id:
                return jsonify({'code': 'BadRequest', 'message': 'category_id is required for level 2'}), 400
            product = Type(name=name, category_id=int(category_id))
        elif level == 3:
            if not category_id:
                return jsonify({'code': 'BadRequest', 'message': 'category_id is required for level 3'}), 400
            product = Product(name=name, category_id=int(category_id))
        else:
            return jsonify({'code': 'BadRequest', 'message': 'invalid level'}), 400

        db.session.add(product)
        db.session.commit()

        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            if level == 1:
                sync_to_neo4j('category', product.id, 'create')
            elif level == 2:
                sync_to_neo4j('type', product.id, 'create')
            elif level == 3:
                sync_to_neo4j('product', product.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync product to Neo4j: {e}")

        return jsonify({
            'id': product.id,
            'name': product.name,
            'category_id': getattr(product, 'category_id', None)
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'product name already exists'}), 409


@bp.put('/products/<int:product_id>')
def update_product(product_id: int):
    """更新产品"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    level = data.get('level')  # 前端必须指定层级

    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    # 根据前端指定的层级查找对应的产品
    product = None
    if level == 1:
        product = Category.query.get(product_id)
    elif level == 2:
        product = Type.query.get(product_id)
    elif level == 3:
        product = Product.query.get(product_id)
    else:
        return jsonify({'code': 'BadRequest', 'message': 'level is required (1, 2, or 3)'}), 400
    
    if not product:
        return jsonify({'code': 'NotFound', 'message': f'level {level} product not found'}), 404

    product.name = name

    try:
        db.session.commit()

        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            if level == 1:
                sync_to_neo4j('category', product.id, 'update')
            elif level == 2:
                sync_to_neo4j('type', product.id, 'update')
            elif level == 3:
                sync_to_neo4j('product', product.id, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync product to Neo4j: {e}")

        return jsonify({
            'id': product.id,
            'name': product.name,
            'level': level,
            'category_id': getattr(product, 'category_id', None)
        })

    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'product name already exists'}), 409


@bp.delete('/products/<int:product_id>')
def delete_product(product_id: int):
    """删除产品"""
    # 从查询参数获取层级
    level = request.args.get('level', type=int)
    
    if not level or level not in [1, 2, 3]:
        return jsonify({'code': 'BadRequest', 'message': 'level parameter is required (1, 2, or 3)'}), 400
    
    # 根据层级查找对应的产品
    product = None
    if level == 1:
        product = Category.query.get(product_id)
    elif level == 2:
        product = Type.query.get(product_id)
    elif level == 3:
        product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'code': 'NotFound', 'message': f'level {level} product not found'}), 404

    # 检查是否存在关联关系
    if level == 3:  # 只有三级产品才有关联关系
        # 检查产品-化学应激源关系
        allergen_relations = AllergenProduct.query.filter_by(product_id=product_id).count()
        if allergen_relations > 0:
            return jsonify({
                'code': 'Conflict',
                'message': f'无法删除产品，存在 {allergen_relations} 个化学应激源关联关系。请先删除相关关系后再删除此产品。'
            }), 409
        
        # 检查产品-症状关系
        symptom_relations = ProductSymptom.query.filter_by(product_id=product_id).count()
        if symptom_relations > 0:
            return jsonify({
                'code': 'Conflict',
                'message': f'无法删除产品，存在 {symptom_relations} 个症状关联关系。请先删除相关关系后再删除此产品。'
            }), 409

    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        if level == 1:
            sync_to_neo4j('category', product_id, 'delete')
        elif level == 2:
            sync_to_neo4j('type', product_id, 'delete')
        elif level == 3:
            sync_to_neo4j('product', product_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete product from Neo4j: {e}")

    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})


# ==================== 过敏原管理 ====================

@bp.get('/allergens')
def get_allergens():
    """获取过敏原列表"""
    allergens = Allergen.query.order_by(Allergen.id.asc()).all()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'description': a.description,
        'cas_number': a.cas_number,
        'created_at': a.created_at.isoformat() if a.created_at else None,
        'updated_at': a.updated_at.isoformat() if a.updated_at else None
    } for a in allergens])


@bp.post('/allergens')
def create_allergen():
    """创建过敏原"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip() or None
    cas_number = (data.get('cas_number') or '').strip() or None

    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    allergen = Allergen(name=name, description=description, cas_number=cas_number)
    db.session.add(allergen)

    try:
        db.session.commit()

        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('allergen', allergen.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync allergen to Neo4j: {e}")

        return jsonify({
            'id': allergen.id,
            'name': allergen.name,
            'description': allergen.description,
            'cas_number': allergen.cas_number
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'allergen name already exists'}), 409


@bp.put('/allergens/<int:allergen_id>')
def update_allergen(allergen_id: int):
    """更新过敏原"""
    allergen = Allergen.query.get(allergen_id)
    if not allergen:
        return jsonify({'code': 'NotFound', 'message': 'allergen not found'}), 404

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    description = data.get('description')
    cas_number = data.get('cas_number')

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'code': 'BadRequest', 'message': 'name cannot be empty'}), 400
        allergen.name = name

    if description is not None:
        allergen.description = description.strip() or None

    if cas_number is not None:
        allergen.cas_number = cas_number.strip() or None

    try:
        db.session.commit()

        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('allergen', allergen.id, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync allergen to Neo4j: {e}")

        return jsonify({
            'id': allergen.id,
            'name': allergen.name,
            'description': allergen.description,
            'cas_number': allergen.cas_number
        })

    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'allergen name already exists'}), 409


@bp.delete('/allergens/<int:allergen_id>')
def delete_allergen(allergen_id: int):
    """删除过敏原"""
    allergen = Allergen.query.get(allergen_id)
    if not allergen:
        return jsonify({'code': 'NotFound', 'message': 'allergen not found'}), 404

    # 检查是否存在关联关系
    # 检查化学应激源-产品关系
    product_relations = AllergenProduct.query.filter_by(allergen_id=allergen_id).count()
    if product_relations > 0:
        return jsonify({
            'code': 'Conflict',
            'message': f'无法删除化学应激源，存在 {product_relations} 个产品关联关系。请先删除相关关系后再删除此化学应激源。'
        }), 409
    
    # 检查化学应激源-症状关系
    symptom_relations = AllergenSymptom.query.filter_by(allergen_id=allergen_id).count()
    if symptom_relations > 0:
        return jsonify({
            'code': 'Conflict',
            'message': f'无法删除化学应激源，存在 {symptom_relations} 个症状关联关系。请先删除相关关系后再删除此化学应激源。'
        }), 409

    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        sync_to_neo4j('allergen', allergen_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete allergen from Neo4j: {e}")

    db.session.delete(allergen)
    db.session.commit()
    return jsonify({'success': True})


# ==================== 症状管理 ====================

@bp.get('/symptoms/level1')
def get_symptoms_level1():
    """获取一级症状列表"""
    symptoms = Symptom1.query.order_by(Symptom1.id.asc()).all()
    return jsonify([{
        'id': s.id,
        'symptom_name': s.symptom_name,
        'name': s.symptom_name,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None
    } for s in symptoms])


@bp.get('/symptoms/level2/<int:major_id>')
def get_symptoms_level2(major_id: int):
    """获取二级症状列表"""
    symptoms = Symptom2.query.filter_by(major_id=major_id).order_by(Symptom2.id.asc()).all()
    return jsonify([{
        'id': s.id,
        'symptom_name': s.symptom_name,
        'name': s.symptom_name,
        'major_id': s.major_id,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None
    } for s in symptoms])


@bp.get('/symptoms/level2')  
def get_all_symptoms_level2():
    """获取所有二级症状列表"""
    from sqlalchemy import text
    # 直接查询，避免JSON解析问题
    result = db.session.execute(text("""
        SELECT id, symptom_name, major_id, created_at, updated_at 
        FROM symptom_2 
        ORDER BY id ASC
    """))
    
    symptoms = []
    for row in result:
        symptoms.append({
            'id': row[0],
            'name': row[1],  # 为了前端兼容性
            'symptom_name': row[1],
            'major_id': row[2],
            'created_at': row[3].isoformat() if row[3] else None,
            'updated_at': row[4].isoformat() if row[4] else None
        })
    
    return jsonify(symptoms)


@bp.get('/symptoms/level3/<int:sub_id>')
def get_symptoms_level3(sub_id: int):
    """获取三级症状列表"""
    symptoms = Symptom3.query.filter_by(sub_id=sub_id).order_by(Symptom3.id.asc()).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'symptom_name': s.name,
        'sub_id': s.sub_id,
        'description': s.description,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None
    } for s in symptoms])


@bp.get('/symptoms/level3')
def get_all_symptoms_level3():
    """获取所有三级症状列表"""
    from sqlalchemy import text
    # 直接查询，避免JSON解析问题
    result = db.session.execute(text("""
        SELECT id, name, sub_id, created_at, updated_at 
        FROM symptom_3 
        ORDER BY id ASC
    """))
    
    symptoms = []
    for row in result:
        symptoms.append({
            'id': row[0],
            'name': row[1],
            'symptom_name': row[1],
            'sub_id': row[2],
            'description': None,
            'created_at': row[3].isoformat() if row[3] else None,
            'updated_at': row[4].isoformat() if row[4] else None
        })
    
    return jsonify(symptoms)


@bp.post('/symptoms')
def create_symptom():
    """创建症状"""
    data = request.get_json(silent=True) or {}
    name = (data.get('symptom_name') or data.get('name') or '').strip()
    level = data.get('level', 1)
    major_id = data.get('major_id')
    sub_id = data.get('sub_id')
    description = (data.get('description') or '').strip() or None

    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    try:
        if level == 1:
            symptom = Symptom1(symptom_name=name)
        elif level == 2:
            if not major_id:
                return jsonify({'code': 'BadRequest', 'message': 'major_id is required for level 2'}), 400
            symptom = Symptom2(symptom_name=name, major_id=int(major_id))
        elif level == 3:
            if not sub_id:
                return jsonify({'code': 'BadRequest', 'message': 'sub_id is required for level 3'}), 400
            symptom = Symptom3(name=name, sub_id=int(sub_id), description=description)
        else:
            return jsonify({'code': 'BadRequest', 'message': 'invalid level'}), 400

        db.session.add(symptom)
        db.session.commit()

        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j(f'symptom{level}', symptom.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync symptom to Neo4j: {e}")

        return jsonify({
            'id': symptom.id,
            'name': getattr(symptom, 'name', None) or getattr(symptom, 'symptom_name', None),
            'symptom_name': getattr(symptom, 'symptom_name', None) or getattr(symptom, 'name', None),
            'description': getattr(symptom, 'description', None)
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'symptom name already exists'}), 409


@bp.put('/symptoms/<int:symptom_id>')
def update_symptom(symptom_id: int):
    """更新症状"""
    data = request.get_json(silent=True) or {}
    name = (data.get('symptom_name') or data.get('name') or '').strip()
    description = data.get('description')
    level = data.get('level')  # 前端必须指定层级

    if not name:
        return jsonify({'code': 'BadRequest', 'message': 'name is required'}), 400

    # 根据前端指定的层级查找对应的症状
    symptom = None
    if level == 1:
        symptom = Symptom1.query.get(symptom_id)
    elif level == 2:
        symptom = Symptom2.query.get(symptom_id)
    elif level == 3:
        symptom = Symptom3.query.get(symptom_id)
    else:
        return jsonify({'code': 'BadRequest', 'message': 'level is required (1, 2, or 3)'}), 400
    
    if not symptom:
        return jsonify({'code': 'NotFound', 'message': f'level {level} symptom not found'}), 404

    # 更新名称
    if hasattr(symptom, 'symptom_name'):
        symptom.symptom_name = name
    if hasattr(symptom, 'name'):
        symptom.name = name

    # 更新描述（仅symptom3有description字段）
    if description is not None and hasattr(symptom, 'description'):
        symptom.description = description.strip() or None

    try:
        db.session.commit()

        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j(f'symptom{level}', symptom.id, 'update')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync symptom to Neo4j: {e}")

        return jsonify({
            'id': symptom.id,
            'name': getattr(symptom, 'name', None) or getattr(symptom, 'symptom_name', None),
            'symptom_name': getattr(symptom, 'symptom_name', None) or getattr(symptom, 'name', None),
            'description': getattr(symptom, 'description', None),
            'level': level
        })

    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'symptom name already exists'}), 409


@bp.delete('/symptoms/<int:symptom_id>')
def delete_symptom(symptom_id: int):
    """删除症状"""
    # 从查询参数获取层级
    level = request.args.get('level', type=int)
    
    if not level or level not in [1, 2, 3]:
        return jsonify({'code': 'BadRequest', 'message': 'level parameter is required (1, 2, or 3)'}), 400
    
    # 根据层级查找对应的症状
    symptom = None
    if level == 1:
        symptom = Symptom1.query.get(symptom_id)
    elif level == 2:
        symptom = Symptom2.query.get(symptom_id)
    elif level == 3:
        symptom = Symptom3.query.get(symptom_id)
    
    if not symptom:
        return jsonify({'code': 'NotFound', 'message': f'level {level} symptom not found'}), 404

    # 检查是否存在关联关系
    if level == 2:  # 二级症状需要检查化学应激源和产品关联关系
        # 检查症状-化学应激源关系
        allergen_relations = AllergenSymptom.query.filter_by(symptom_id=symptom_id).count()
        if allergen_relations > 0:
            return jsonify({
                'code': 'Conflict',
                'message': f'无法删除不良反应，存在 {allergen_relations} 个化学应激源关联关系。请先删除相关关系后再删除此不良反应。'
            }), 409
        
        # 检查症状-产品关系
        product_relations = ProductSymptom.query.filter_by(symptom_id=symptom_id).count()
        if product_relations > 0:
            return jsonify({
                'code': 'Conflict',
                'message': f'无法删除不良反应，存在 {product_relations} 个产品关联关系。请先删除相关关系后再删除此不良反应。'
            }), 409

    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        sync_to_neo4j(f'symptom{level}', symptom_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete symptom from Neo4j: {e}")

    db.session.delete(symptom)
    db.session.commit()
    return jsonify({'success': True})
