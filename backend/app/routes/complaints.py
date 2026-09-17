from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import case
from datetime import datetime
from .. import db
from ..models import Complaints, ProductSymptom, ProductSymptomComp, Product, Symptom2
from ..services.neo4j_sync import Neo4jSyncService


bp = Blueprint('complaints', __name__)


@bp.get('/')
def get_complaints():
    """获取投诉列表，支持前端数据管理功能"""
    
    # 直接获取所有投诉，按发布时间倒序排列（MySQL兼容的NULL处理）
    nulls_last = case((Complaints.publish_time.is_(None), 1), else_=0)
    q = Complaints.query.order_by(nulls_last.asc(), Complaints.publish_time.desc(), Complaints.id.desc())
    items = q.all()
    
    def to_dict(x: Complaints):
        # 查询投诉的所有实体关系
        complaint_entity_relations = []
        try:
            # 查询该投诉作为佐证数据的所有产品-症状关系
            relation_sources = db.session.query(ProductSymptomComp).join(
                ProductSymptom, ProductSymptomComp.product_symptom_id == ProductSymptom.id
            ).join(
                Product, ProductSymptom.product_id == Product.id
            ).join(
                Symptom2, ProductSymptom.symptom_id == Symptom2.id
            ).filter(ProductSymptomComp.complaints_id == x.id).all()
            
            for relation_source in relation_sources:
                product_name = relation_source.product_symptom.product.name
                symptom_name = relation_source.product_symptom.symptom.symptom_name
                complaint_entity_relations.append({
                    'relation': f"{product_name} - {symptom_name}",
                    'type': 'product-symptom',
                    'product_id': relation_source.product_symptom.product_id,
                    'symptom_id': relation_source.product_symptom.symptom_id
                })
        except Exception as e:
            print(f"查询投诉 {x.id} 的实体关系失败: {e}")
        
        return {
            'id': str(x.id),
            'source': x.source,
            'title': x.title,
            'publishTime': x.publish_time.isoformat() if x.publish_time else None,
            'publishDate': x.publish_time.isoformat()[:10] if x.publish_time else None,
            'abstract': x.abstract,
            'link': x.link,
            'state': bool(getattr(x, 'state', 0)),  # 转换为布尔值以匹配前端
            'entityRelations': complaint_entity_relations  # 返回所有实体关系的数组
        }
    
    return jsonify([to_dict(x) for x in items])


@bp.post('/create')
def create_complaints():
    """创建投诉"""
    data = request.get_json()

    basic_info = data.get('basicInfo', {})
    entity_relations = data.get('entityRelations', [])

    if not basic_info["title"] and not basic_info["link"]:
        return jsonify({
            'code': 400,
            'message': 'Title and source are required'
        }), 400

    try:
        has_entity_relations = len(entity_relations) > 0
        news_state = 1 if has_entity_relations else 0

        complatints = Complaints(
            source=basic_info['source'],
            title=basic_info['title'],
            publish_time=basic_info['publishTime'],
            abstract=basic_info.get('abstract'),
            link=basic_info.get('link'),
            state=news_state  # 根据实体关系设置状态
        )

        db.session.add(complatints)
        db.session.flush()

        # 处理实体关系
        create_relations = []
        for relation in entity_relations:
            product_id = relation.get('productId')
            symptom_id = relation.get('symptomId')

            if product_id and symptom_id:
                product_symptom = ProductSymptom.query.filter_by(
                    product_id=product_id,
                    symptom_id=symptom_id
                ).first()

                if not product_symptom:
                    # 创建新的产品-症状关系
                    product_symptom = ProductSymptom(
                        product_id=product_id,
                        symptom_id=symptom_id,
                    )
                    db.session.add(product_symptom)
                    db.session.flush()

                    # 同步新增的产品-症状关系到 Neo4j
                    try:
                        Neo4jSyncService.sync_product_symptom_relation(
                            product_id=product_id,
                            symptom_id=symptom_id,
                            relation_id=product_symptom.id,
                            operation='create'
                        )
                    except Exception as e:
                        print(f"[News] Neo4j 同步产品-症状关系失败(create): {e}")

                # 直接创建新的投诉-产品症状关联记录
                complaint_source = ProductSymptomComp(
                    product_symptom_id=product_symptom.id,
                    complaints_id=complatints.id,
                )
                db.session.add(complaint_source)

                create_relations.append({
                    'product_id': product_id,
                    'symptom_id': symptom_id,
                    'relation_id': product_symptom.id
                })
        
        db.session.commit()
        print(f'[Complatints] 创建成功: {complatints.title}')

        return jsonify({
            'success': True,
            'id': str(complatints.id),
            'message': '投诉创建成功',
            'entityRelations': create_relations
        })   

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({
            'code': 'InternalError', 'message': str(e)
            }), 500


@bp.delete('/<int:complaint_id>')
def delete_complaints(complaint_id: int):
    """删除投诉"""
    complaints = Complaints.query.get(complaint_id)

    try:
        # 删除相关的投诉-产品症状关联记录
        existing_sources = ProductSymptomComp.query.filter_by(
            complaints_id=complaint_id
        ).all()

        for source in existing_sources:
            db.session.delete(source)

        # 删除投诉记录
        db.session.delete(complaints)
        db.session.commit()
        print(f'[Complaints] 删除成功: {complaints.title}')
        
        return jsonify({
            'success': True,
            'message': '投诉删除成功'
        })

    except Exception as e:
        db.session.rollback()
        print(f"删除失败 {str(e)}")
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bp.put('/<int:complaint_id>')
def update_complaints(complaint_id: int):
    """更新投诉"""
    complaints = Complaints.query.get(complaint_id)
    if not complaints:
        return jsonify({
            'code': 404,
            'message': 'Complaint not found'
        }), 404
        
    data = request.get_json()
    basic_info = data.get('basicInfo', {})
    entity_relations = data.get('entityRelations', [])

    try:
        # 1. 更新基本信息
        complaints.title = basic_info['title']
        complaints.publish_time = datetime.fromisoformat(basic_info['publishTime'])
        complaints.source = basic_info['source']
        complaints.abstract = basic_info.get('abstract')
        complaints.link = basic_info['link']
        
        # 根据是否有实体关系设置状态
        has_entity_relations = len(entity_relations) > 0
        complaints.state = 1 if has_entity_relations else 0

        # 2. 删除该投诉的所有现有关系
        existing_sources = ProductSymptomComp.query.filter_by(
            complaints_id=complaint_id
        ).all()
        for source in existing_sources:
            db.session.delete(source)

        # 3. 添加新的关系
        for relation in entity_relations:
            product_id = relation.get('productId')
            symptom_id = relation.get('symptomId')
            
            if product_id and symptom_id:
                # 查找或创建ProductSymptom
                product_symptom = ProductSymptom.query.filter_by(
                    product_id=product_id,
                    symptom_id=symptom_id
                ).first()
                
                if not product_symptom:
                    # 创建新的产品-症状关系
                    product_symptom = ProductSymptom(
                        product_id=product_id,
                        symptom_id=symptom_id,
                    )
                    db.session.add(product_symptom)
                    db.session.flush()

                    # 同步到Neo4j
                    try:
                        Neo4jSyncService.sync_product_symptom_relation(
                            product_id=product_id,
                            symptom_id=symptom_id,
                            relation_id=product_symptom.id,
                            operation='create'
                        )
                    except Exception as e:
                        print(f"Neo4j 同步产品-症状关系失败(create): {e}")

                # 创建新的投诉-产品症状关联记录
                complaint_source = ProductSymptomComp(
                    product_symptom_id=product_symptom.id,
                    complaints_id=complaint_id,
                )
                db.session.add(complaint_source)

        db.session.commit()
        print(f'[Complaints] 更新成功: {complaints.title}')
        
        return jsonify({
            'success': True,
            'message': '投诉更新成功'
        })

    except Exception as e:
        db.session.rollback()
        print(f'[Complaints] 更新失败: {e}')
        return jsonify({
            'code': 'InternalError', 
            'message': str(e)
        }), 500