from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from .. import db
from ..models import (
    Literature, Allergen, Product, AllergenSymptom
)

bp = Blueprint('info_management', __name__)


@bp.get('/literature/search')
def search_literature():
    """搜索文献数据"""
    allergen_id = request.args.get('allergenId', type=int)
    category_id = request.args.get('categoryId', type=int)
    symptom_keyword = request.args.get('symptomKeyword', '').strip()
    start_date = request.args.get('startDate', '').strip()
    end_date = request.args.get('endDate', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 100, type=int)
    
    if not allergen_id:
        return jsonify({'code': 'BadRequest', 'message': 'allergenId is required'}), 400
    
    # 构建查询
    query = Literature.query
    
    # 通过过敏原关联的产品来查找文献
    if category_id:
        # 如果指定了类别，先找到该类别下与过敏原关联的产品
        product_ids = db.session.query(Product.id).join(
            ProductAllergen, Product.id == ProductAllergen.product_id
        ).filter(
            ProductAllergen.allergen_id == allergen_id,
            Product.category_id == category_id
        ).all()
        product_ids = [pid[0] for pid in product_ids]
    else:
        # 找到所有与过敏原关联的产品
        product_ids = db.session.query(ProductAllergen.product_id).filter(
            ProductAllergen.allergen_id == allergen_id
        ).all()
        product_ids = [pid[0] for pid in product_ids]
    
    if not product_ids:
        return jsonify({'items': [], 'page': page, 'pageSize': page_size, 'total': 0})
    
    # 通过产品ID查找文献
    literature_ids = db.session.query(LiteratureKeyword.literature_id).filter(
        LiteratureKeyword.product_id.in_(product_ids)
    ).all()
    literature_ids = [lid[0] for lid in literature_ids]
    
    if not literature_ids:
        return jsonify({'items': [], 'page': page, 'pageSize': page_size, 'total': 0})
    
    query = query.filter(Literature.id.in_(literature_ids))
    
    # 症状关键词筛选
    if symptom_keyword:
        keyword_lower = symptom_keyword.lower()
        query = query.filter(
            or_(
                Literature.title.ilike(f'%{keyword_lower}%'),
                Literature.abstract.ilike(f'%{keyword_lower}%'),
                Literature.keywords.ilike(f'%{keyword_lower}%')
            )
        )
    
    # 日期筛选
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Literature.publish_date >= start_date_obj)
        except ValueError:
            return jsonify({'code': 'BadRequest', 'message': 'Invalid start date format. Use YYYY-MM-DD'}), 400
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Literature.publish_date <= end_date_obj)
        except ValueError:
            return jsonify({'code': 'BadRequest', 'message': 'Invalid end date format. Use YYYY-MM-DD'}), 400
    
    # 分页
    total = query.count()
    items = query.order_by(Literature.publish_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # 转换为字典格式
    result_items = []
    for item in items:
        # 检查是否有症状关联
        symptom_associations = SymptomLiterature.query.filter_by(
            literature_id=item.id
        ).all()
        
        result_items.append({
            'id': str(item.id),
            'title': item.title,
            'title_zh': item.title,  # 可以后续添加翻译
            'authors': item.authors,
            'keywords': item.keywords,
            'abstract': item.abstract,
            'abstract_zh': item.abstract,  # 可以后续添加翻译
            'publishDate': item.publish_date.isoformat() if item.publish_date else None,
            'url': item.link,
            'source': item.source,
            'symptomAssociations': [
                {
                    'symptomName': sa.symptom_name,
                    'allergenId': sa.allergen_id
                } for sa in symptom_associations
            ]
        })
    
    return jsonify({
        'items': result_items,
        'page': page,
        'pageSize': page_size,
        'total': total
    })


@bp.get('/toxicity/search')
def search_toxicity():
    """搜索毒性数据"""
    allergen_id = request.args.get('allergenId', type=int)
    category_id = request.args.get('categoryId', type=int)
    symptom_keyword = request.args.get('symptomKeyword', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 100, type=int)
    
    if not allergen_id:
        return jsonify({'code': 'BadRequest', 'message': 'allergenId is required'}), 400
    
    # 构建查询
    query = Toxicity.query
    
    # 通过过敏原关联的产品来查找毒性数据
    if category_id:
        # 如果指定了类别，先找到该类别下与过敏原关联的产品
        product_ids = db.session.query(Product.id).join(
            ProductAllergen, Product.id == ProductAllergen.product_id
        ).filter(
            ProductAllergen.allergen_id == allergen_id,
            Product.category_id == category_id
        ).all()
        product_ids = [pid[0] for pid in product_ids]
    else:
        # 找到所有与过敏原关联的产品
        product_ids = db.session.query(ProductAllergen.product_id).filter(
            ProductAllergen.allergen_id == allergen_id
        ).all()
        product_ids = [pid[0] for pid in product_ids]
    
    if not product_ids:
        return jsonify({'items': [], 'page': page, 'pageSize': page_size, 'total': 0})
    
    # 通过产品ID查找毒性数据
    toxicity_ids = db.session.query(ToxicityKeyword.toxicity_id).filter(
        ToxicityKeyword.allergen_id == allergen_id
    ).all()
    toxicity_ids = [tid[0] for tid in toxicity_ids]
    
    if not toxicity_ids:
        return jsonify({'items': [], 'page': page, 'pageSize': page_size, 'total': 0})
    
    query = query.filter(Toxicity.id.in_(toxicity_ids))
    
    # 症状关键词筛选
    if symptom_keyword:
        keyword_lower = symptom_keyword.lower()
        query = query.filter(
            or_(
                Toxicity.name.ilike(f'%{keyword_lower}%'),
                Toxicity.compound_descriptor.ilike(f'%{keyword_lower}%')
            )
        )
    
    # 分页
    total = query.count()
    items = query.order_by(Toxicity.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # 转换为字典格式
    result_items = []
    for item in items:
        result_items.append({
            'id': str(item.id),
            'name': item.name,
            'molecular_formula': item.molecular_formula,
            'compound_descriptor': item.compound_descriptor,
            'health_hazards': [
                {
                    'experiment_type': hh.experiment_type,
                    'exposure_route': hh.exposure_route,
                    'test_species': hh.test_species,
                    'duration': hh.duration,
                    'toxic_effects': hh.toxic_effects
                } for hh in item.health_hazards
            ],
            'created_at': item.created_at.isoformat() if item.created_at else None
        })
    
    return jsonify({
        'items': result_items,
        'page': page,
        'pageSize': page_size,
        'total': total
    })


@bp.post('/symptom/associate')
def associate_symptom():
    """关联症状与文献/毒性数据"""
    body = request.get_json(silent=True) or {}
    symptom_name = body.get('symptomName', '').strip()
    allergen_id = body.get('allergenId')
    data_type = body.get('dataType')  # 'literature' or 'toxicity'
    item_ids = body.get('itemIds', [])
    
    if not symptom_name:
        return jsonify({'code': 'BadRequest', 'message': 'symptomName is required'}), 400
    
    if not allergen_id:
        return jsonify({'code': 'BadRequest', 'message': 'allergenId is required'}), 400
    
    if not item_ids:
        return jsonify({'code': 'BadRequest', 'message': 'itemIds is required'}), 400
    
    if data_type not in ['literature', 'toxicity']:
        return jsonify({'code': 'BadRequest', 'message': 'dataType must be literature or toxicity'}), 400
    
    try:
        allergen_id = int(allergen_id)
    except (TypeError, ValueError):
        return jsonify({'code': 'BadRequest', 'message': 'allergenId must be an integer'}), 400
    
    # 验证过敏原存在
    allergen = Allergen.query.get(allergen_id)
    if not allergen:
        return jsonify({'code': 'NotFound', 'message': 'allergen not found'}), 404
    
    associated_count = 0
    errors = []
    
    try:
        for item_id in item_ids:
            try:
                item_id_int = int(item_id)
            except (TypeError, ValueError):
                errors.append(f"Invalid item ID: {item_id}")
                continue
            
            if data_type == 'literature':
                # 验证文献存在
                literature = Literature.query.get(item_id_int)
                if not literature:
                    errors.append(f"Literature not found: {item_id}")
                    continue
                
                # 检查是否已存在关联
                existing = SymptomLiterature.query.filter_by(
                    symptom_name=symptom_name,
                    literature_id=item_id_int
                ).first()
                
                if not existing:
                    # 创建新的症状-文献关联
                    symptom_literature = SymptomLiterature(
                        symptom_name=symptom_name,
                        literature_id=item_id_int,
                        allergen_id=allergen_id
                    )
                    db.session.add(symptom_literature)
                    associated_count += 1
                else:
                    # 更新现有关联的过敏原ID
                    existing.allergen_id = allergen_id
            
            elif data_type == 'toxicity':
                # 对于毒性数据，我们可能需要创建类似的关联表
                # 这里暂时跳过，因为当前模型中没有症状-毒性关联表
                errors.append(f"Toxicity symptom association not implemented yet: {item_id}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'associatedCount': associated_count,
            'errors': errors,
            'message': f'Successfully associated {associated_count} items with symptom "{symptom_name}"'
        })
        
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'Database constraint violation'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.delete('/symptom/associate')
def remove_symptom_association():
    """移除症状关联"""
    body = request.get_json(silent=True) or {}
    symptom_name = body.get('symptomName', '').strip()
    data_type = body.get('dataType')
    item_ids = body.get('itemIds', [])
    
    if not symptom_name:
        return jsonify({'code': 'BadRequest', 'message': 'symptomName is required'}), 400
    
    if not item_ids:
        return jsonify({'code': 'BadRequest', 'message': 'itemIds is required'}), 400
    
    if data_type not in ['literature', 'toxicity']:
        return jsonify({'code': 'BadRequest', 'message': 'dataType must be literature or toxicity'}), 400
    
    removed_count = 0
    
    try:
        for item_id in item_ids:
            try:
                item_id_int = int(item_id)
            except (TypeError, ValueError):
                continue
            
            if data_type == 'literature':
                # 删除症状-文献关联
                associations = SymptomLiterature.query.filter_by(
                    symptom_name=symptom_name,
                    literature_id=item_id_int
                ).all()
                
                for association in associations:
                    db.session.delete(association)
                    removed_count += 1
            
            elif data_type == 'toxicity':
                # 毒性数据的症状关联删除暂未实现
                continue
        
        db.session.commit()
        
        return jsonify({
            'removedCount': removed_count,
            'message': f'Successfully removed {removed_count} symptom associations'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.get('/categories')
def get_categories():
    """获取产品类别列表"""
    from ..models import Category
    
    categories = Category.query.all()
    return jsonify({
        'items': [
            {
                'id': cat.id,
                'name': cat.name
            } for cat in categories
        ]
    })


@bp.get('/allergens')
def get_allergens():
    """获取过敏原列表"""
    category_id = request.args.get('categoryId', type=int)
    
    query = Allergen.query
    if category_id:
        # 通过产品关联查找过敏原
        allergen_ids = db.session.query(ProductAllergen.allergen_id).join(
            Product, ProductAllergen.product_id == Product.id
        ).filter(Product.category_id == category_id).distinct().all()
        allergen_ids = [aid[0] for aid in allergen_ids]
        query = query.filter(Allergen.id.in_(allergen_ids))
    
    allergens = query.all()
    return jsonify({
        'items': [
            {
                'id': allergen.id,
                'name': allergen.name,
                'description': allergen.description
            } for allergen in allergens
        ]
    })


@bp.get('/symptoms')
def get_symptoms():
    """获取症状列表"""
    try:
        # 先获取所有症状，然后分别处理有过敏原和没有过敏原的症状
        all_sub_symptoms = db.session.query(SubSymptom).order_by(SubSymptom.created_at.desc()).all()
        
        result_items = []
        for sub_symptom in all_sub_symptoms:
            # 查找该症状的过敏原
            allergen_symptoms = db.session.query(AllergenSymptom).filter_by(symptom_id=sub_symptom.id).all()
            allergen_names = []
            
            if allergen_symptoms:
                allergen_ids = [as_rel.allergen_id for as_rel in allergen_symptoms]
                allergens = db.session.query(Allergen).filter(Allergen.id.in_(allergen_ids)).all()
                allergen_names = [allergen.name for allergen in allergens]
            
            # 处理description字段 - 保持JSON数组格式
            description = sub_symptom.description
            if isinstance(description, str):
                # 如果是字符串，尝试解析为JSON数组
                try:
                    description = json.loads(description)
                except (json.JSONDecodeError, TypeError):
                    # 如果解析失败，保持原字符串
                    description = description
            elif isinstance(description, list):
                # 如果已经是数组，直接使用
                description = description
            elif description is None:
                description = []
            else:
                # 其他情况，转换为字符串
                description = str(description)
            
            result_items.append({
                'id': sub_symptom.id,
                'name': sub_symptom.symptom_name,
                'description': description,
                'allergen_names': allergen_names,
            })
        
        return jsonify({
            'items': result_items,
            'total': len(result_items)
        })
        
    except Exception as e:
        print(f"查询错误: {str(e)}")
        return jsonify({
            'code': 'InternalError',
            'message': f'查询症状列表失败: {str(e)}'
        }), 500



@bp.get('/major-symptoms')
def get_major_symptoms():
    """获取主要症状列表"""
    try:
        major_symptoms = db.session.query(MajorSymptom).order_by(MajorSymptom.name).all()
        result_items = []
        for major_symptom in major_symptoms:
            result_items.append({
                'id': major_symptom.id,
                'name': major_symptom.name
            })
        
        return jsonify({
            'items': result_items,
            'total': len(result_items)
        })
    except Exception as e:
        print(f"获取主要症状列表出错: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get('/sub-symptoms/<int:major_symptom_id>')
def get_sub_symptoms(major_symptom_id):
    """获取特定主要症状下的子症状列表"""
    try:
        sub_symptoms = db.session.query(SubSymptom).filter_by(major_id=major_symptom_id).order_by(SubSymptom.symptom_name).all()
        result_items = []
        for sub_symptom in sub_symptoms:
            result_items.append({
                'id': sub_symptom.id,
                'name': sub_symptom.symptom_name,
                'description': sub_symptom.description
            })
        
        return jsonify({
            'items': result_items,
            'total': len(result_items)
        })
    except Exception as e:
        print(f"获取子症状列表出错: {e}")
        return jsonify({'error': str(e)}), 500


@bp.post('/symptoms')
def create_symptom():
    """新增症状"""
    body = request.get_json(silent=True) or {}
    major_id = body.get('majorId')
    symptom_name = body.get('name', '').strip()
    symptom_description = body.get('description', '').strip()
    allergen_id = body.get('allergenId')
    
    if not major_id:
        return jsonify({'code': 'BadRequest', 'message': 'majorId is required'}), 400

    if not symptom_name:
        return jsonify({'code': 'BadRequest', 'message': 'symptomName is required'}), 400
    
    if not symptom_description:
        return jsonify({'code': 'BadRequest', 'message': 'symptomDescription is required'}), 400
    
    if not allergen_id:
        return jsonify({'code': 'BadRequest', 'message': 'allergenId is required'}), 400

    
    # 验证过敏原是否存在
    allergen = Allergen.query.get(allergen_id)
    if not allergen:
        return jsonify({'code': 'NotFound', 'message': f'Allergen with id {allergen_id} not found'}), 404
    
    try:
        # 处理description字段 - 确保以JSON数组格式存储
        if isinstance(symptom_description, str):
            # 如果是逗号分隔的字符串，转换为数组
            if ',' in symptom_description:
                description_array = [item.strip() for item in symptom_description.split(',')]
            else:
                description_array = [symptom_description.strip()]
        elif isinstance(symptom_description, list):
            description_array = symptom_description
        else:
            description_array = [str(symptom_description)]
        
        # 创建子症状
        sub_symptom = SubSymptom(
            major_id=major_id,
            symptom_name=symptom_name,
            description=description_array
        )
        db.session.add(sub_symptom)
        db.session.flush()  # 获取新创建的ID
        
        # 创建过敏原症状关联
        allergen_symptom = AllergenSymptom(
            allergen_id=allergen_id,
            symptom_id=sub_symptom.id,
            evidence_count=1
        )
        db.session.add(allergen_symptom)
        db.session.commit()
        
        return jsonify({
            'id': sub_symptom.id,
            'name': sub_symptom.symptom_name,
            'description': sub_symptom.description,
            'majorSymptomId': sub_symptom.major_id,
            'allergenId': allergen_id,
            'message': 'Symptom created successfully'
        })
        
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'Symptom with this name already exists for this major symptom'}), 409
    except Exception as e:
        db.session.rollback()
        print(f"创建症状出错: {e}")
        return jsonify({'code': 'InternalError', 'message': f'Failed to create symptom: {str(e)}'}), 500


@bp.put('/symptoms/<int:symptom_id>')
def update_symptom(symptom_id):
    """更新症状"""
    body = request.get_json(silent=True) or {}
    symptom_name = body.get('name', '').strip()
    symptom_description = body.get('description', '').strip()
    allergen_id = body.get('allergenId')
    
    if not symptom_name:
        return jsonify({'code': 'BadRequest', 'message': 'symptomName is required'}), 400
    
    if not symptom_description:
        return jsonify({'code': 'BadRequest', 'message': 'symptomDescription is required'}), 400
    
    if not allergen_id:
        return jsonify({'code': 'BadRequest', 'message': 'allergenId is required'}), 400
    
    try:
        allergen_id = int(allergen_id)
    except (TypeError, ValueError):
        return jsonify({'code': 'BadRequest', 'message': 'allergenId must be an integer'}), 400
    
    # 验证症状是否存在
    sub_symptom = SubSymptom.query.get(symptom_id)
    if not sub_symptom:
        return jsonify({'code': 'NotFound', 'message': 'Symptom not found'}), 404
    
    try:
        # 处理description字段 - 确保以JSON数组格式存储
        if isinstance(symptom_description, str):
            # 如果是逗号分隔的字符串，转换为数组
            if ',' in symptom_description:
                description_array = [item.strip() for item in symptom_description.split(',')]
            else:
                description_array = [symptom_description.strip()]
        elif isinstance(symptom_description, list):
            description_array = symptom_description
        else:
            description_array = [str(symptom_description)]
        
        # 更新症状信息
        sub_symptom.symptom_name = symptom_name
        sub_symptom.description = description_array

        db.session.add(sub_symptom)
        db.session.commit()
        
        
        return jsonify({
            'id': sub_symptom.id,
            'name': sub_symptom.symptom_name,
            'description': sub_symptom.description,
            'allergenId': allergen_id,
            'message': 'Symptom updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"更新症状出错: {e}")
        return jsonify({'code': 'InternalError', 'message': f'Failed to update symptom: {str(e)}'}), 500
