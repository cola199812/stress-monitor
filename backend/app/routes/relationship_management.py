"""
关系管理模块 - 处理化学应激源与产品、症状的关联关系
同时同步到MySQL和Neo4j数据库
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from .. import db
from ..models import (
    AllergenProduct, AllergenSymptom, ProductSymptom, ProductSymptomNews, ProductSymptomComp,
    AllergenSymptomSource, Allergen, Product, Symptom2, Symptom3, Literature, News,
    ExposureScoringDetail, LiteratureEpiScoring, LiteratureVivoScoring, 
    LiteratureVitroScoring, AllergenProductSource
)
from sqlalchemy import text
from ..services.confidence_scoring import calculate_product_symptom_signal, EventSignalCalculator
from ..services.neo4j_sync import Neo4jSyncService
import logging
import json

logger = logging.getLogger(__name__)

bp = Blueprint('relationship', __name__)

###################化学应激源-症状####################

@bp.route('/allergen-symptom', methods=['POST'])
def create_allergen_symptom_relation():
    """创建化学应激源-症状关联关系
    
    同时同步到MySQL和Neo4j
    """
    try:
        data = request.get_json()
        allergen_id = data.get('allergen_id')
        symptom_id = data.get('symptom_id')
        traec_score = data.get('traec_score', 0.0)
        
        # 验证必填字段
        if not allergen_id or not symptom_id:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: allergen_id 和 symptom_id'
            }), 400
        
        # 验证实体是否存在
        try:
            allergen = db.session.get(Allergen, allergen_id)
            if not allergen:
                return jsonify({
                    'code': 404,
                    'message': f'化学应激源 ID {allergen_id} 不存在'
                }), 404
        except Exception as allergen_error:
            return jsonify({
                'code': 500,
                'message': f'查询化学应激源失败: {str(allergen_error)}'
            }), 500
        
        try:
            symptom = db.session.get(Symptom2, symptom_id)
            if not symptom:
                return jsonify({
                    'code': 404,
                    'message': f'不良反应 ID {symptom_id} 不存在'
                }), 404
        except Exception as symptom_error:
            return jsonify({
                'code': 500,
                'message': f'查询不良反应失败: {str(symptom_error)}'
            }), 500
        
        # 检查关系是否已存在
        existing = AllergenSymptom.query.filter_by(
            allergen_id=allergen_id,
            symptom_id=symptom_id
        ).first()
        
        if existing:
            return jsonify({
                'code': 409,
                'message': '该关联关系已存在'
            }), 409
        
        # 1. 创建MySQL记录
        relation_obj = AllergenSymptom(
            allergen_id=allergen_id,
            symptom_id=symptom_id
        )
        db.session.add(relation_obj)
        db.session.commit()
        
        # 2. 同步到Neo4j
        try:
            sync_success = Neo4jSyncService.sync_allergen_symptom_relation(
                allergen_id=allergen_id,
                symptom_id=symptom_id,
                relation_id=relation_obj.id,
                traec_score=traec_score if traec_score else 0.0,
                operation='create'
            )
        except Exception as neo4j_error:
            sync_success = False
        
        if not sync_success:
            logger.warning(f'Neo4j同步失败，但MySQL记录已创建: relation_id={relation_obj.id}')
        
        return jsonify({
            'code': 200,
            'message': '关联关系创建成功',
            'data': {
                'id': relation_obj.id,
                'allergen_id': relation_obj.allergen_id,
                'allergen_name': allergen.name,
                'symptom_id': relation_obj.symptom_id,
                'symptom_name': symptom.symptom_name,
                'neo4j_synced': sync_success,
                'created_at': relation_obj.create_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-symptom/<int:relation_id>', methods=['PUT'])
def update_allergen_symptom_relation(relation_id):
    """更新化学应激源-症状关联关系
    
    编辑关联只更新AllergenSymptomSource表
    """
    try:
        data = request.get_json()
        allergen_id = data.get('allergen_id')
        symptom_id = data.get('symptom_id')
        literature_ids = data.get('literature_ids', [])  # 关联的文献ID列表
        
        # 获取现有关系
        relation_obj = db.session.get(AllergenSymptom, relation_id)
        if not relation_obj:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        # 验证必填字段
        if not allergen_id or not symptom_id:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: allergen_id 和 symptom_id'
            }), 400
        
        # 验证实体是否存在
        try:
            allergen = db.session.get(Allergen, allergen_id)
            if not allergen:
                return jsonify({
                    'code': 404,
                    'message': f'化学应激源 ID {allergen_id} 不存在'
                }), 404
        except Exception as allergen_error:
            logger.error(f'查询化学应激源异常: {allergen_error}')
            return jsonify({
                'code': 500,
                'message': f'查询化学应激源失败: {str(allergen_error)}'
            }), 500
        
        try:
            symptom = db.session.get(Symptom2, symptom_id)
            if not symptom:
                return jsonify({
                    'code': 404,
                    'message': f'不良反应 ID {symptom_id} 不存在'
                }), 404
        except Exception as symptom_error:
            logger.error(f'查询不良反应异常: {symptom_error}')
            return jsonify({
                'code': 500,
                'message': f'查询不良反应失败: {str(symptom_error)}'
            }), 500
        
        # 如果修改了关联实体，检查新的关系是否已存在
        if (relation_obj.allergen_id != allergen_id or relation_obj.symptom_id != symptom_id):
            existing = AllergenSymptom.query.filter_by(
                allergen_id=allergen_id,
                symptom_id=symptom_id
            ).filter(AllergenSymptom.id != relation_id).first()
            
            if existing:
                return jsonify({
                    'code': 409,
                    'message': '该关联关系已存在'
                }), 409
        
        # 1. 更新MySQL记录
        relation_obj.allergen_id = allergen_id
        relation_obj.symptom_id = symptom_id
        relation_obj.update_at = datetime.utcnow()
        
        # 2. 处理文献关联 - 智能更新AllergenSymptomSource表
        
        # 获取当前已关联的文献ID列表
        current_sources = AllergenSymptomSource.query.filter_by(
            allergen_symptom_id=relation_id
        ).all()
        
        current_literature_ids = set()
        
        for source in current_sources:
            current_literature_ids.add(source.literature_id)
        
        new_literature_ids = set(literature_ids)
        
        # 找出需要删除的文献关联（当前有但新列表中没有的）
        to_remove = current_literature_ids - new_literature_ids
        # 找出需要添加的文献关联（新列表中有但当前没有的）
        to_add = new_literature_ids - current_literature_ids
        
        # 删除不再需要的文献关联
        if to_remove:
            for source in current_sources:
                if source.literature_id in to_remove:
                    db.session.delete(source)
        
        # 添加新的文献关联
        for lit_id in to_add:
            # 验证文献是否存在
            literature = db.session.get(Literature, lit_id)
            if not literature:
                continue
                
            # 直接创建AllergenSymptomSource记录
            allergen_symptom_source = AllergenSymptomSource(
                allergen_symptom_id=relation_id,
                literature_id=lit_id,
                evidence_strength=1.0,  # 默认置信度
                note=f'关联文献: {literature.title}'
            )
            db.session.add(allergen_symptom_source)
        
        db.session.commit()
        
        # 3. 同步到Neo4j
        sync_success = Neo4jSyncService.sync_allergen_symptom_relation(
            allergen_id=allergen_id,
            symptom_id=symptom_id,
            relation_id=relation_id,
            traec_score=relation_obj.traec_score or 0.0,
            operation='update'
        )
        
        if not sync_success:
            logger.warning(f'Neo4j同步失败，但MySQL记录已更新: relation_id={relation_id}')
        
        # 记录操作日志
        if to_remove:
            logger.info(f'移除文献关联: relation_id={relation_id}, removed_literature_ids={list(to_remove)}')
        if to_add:
            logger.info(f'添加文献关联: relation_id={relation_id}, added_literature_ids={list(to_add)}')
        
        return jsonify({
            'code': 200,
            'message': '关联关系更新成功',
            'data': {
                'id': relation_obj.id,
                'allergen_id': relation_obj.allergen_id,
                'allergen_name': allergen.name,
                'symptom_id': relation_obj.symptom_id,
                'symptom_name': symptom.symptom_name,
                'literature_count': len(new_literature_ids),
                'added_count': len(to_add),
                'removed_count': len(to_remove),
                'neo4j_synced': sync_success,
                'updated_at': relation_obj.update_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'更新化学应激源-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-symptom/<int:relation_id>', methods=['DELETE'])
def delete_allergen_symptom_relation(relation_id):
    """删除化学应激源-症状关联关系
    
    同时从MySQL和Neo4j删除
    """
    try:
        relation = db.session.get(AllergenSymptom, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        allergen_id = relation.allergen_id
        symptom_id = relation.symptom_id
        
        # 1. 从Neo4j删除
        try:
            Neo4jSyncService.sync_allergen_symptom_relation(
                allergen_id=allergen_id,
                symptom_id=symptom_id,
                relation_id=relation_id,
                operation='delete'
            )
        except Exception as neo4j_error:
            # Neo4j删除失败不影响MySQL删除，继续执行
            pass
        
        # 2. 删除相关的佐证数据
        # 删除AllergenSymptomSource表中的佐证记录
        allergen_symptom_sources = AllergenSymptomSource.query.filter_by(
            allergen_symptom_id=relation_id
        ).all()
        
        deleted_sources_count = len(allergen_symptom_sources)
        for source in allergen_symptom_sources:
            db.session.delete(source)
        
        # 3. 从MySQL删除关系记录
        db.session.delete(relation)
        db.session.commit()
        
        logger.info(f'删除化学应激源-症状关系 {relation_id}，同时删除了 {deleted_sources_count} 条佐证记录')
        
        return jsonify({
            'code': 200,
            'message': '关联关系删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'删除化学应激源-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-symptom/batch-delete', methods=['DELETE'])
def batch_delete_allergen_symptom_relations():
    """批量删除化学应激源-症状关联关系
    
    同时从MySQL和Neo4j删除
    """
    try:
        data = request.get_json()
        relation_ids = data.get('ids', [])
        
        if not relation_ids:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: ids'
            }), 400
        
        success_ids = []
        failed_ids = []
        
        for relation_id in relation_ids:
            try:
                relation = db.session.get(AllergenSymptom, relation_id)
                if not relation:
                    failed_ids.append(relation_id)
                    continue
                
                allergen_id = relation.allergen_id
                symptom_id = relation.symptom_id
                
                # 1. 从Neo4j删除
                try:
                    Neo4jSyncService.sync_allergen_symptom_relation(
                        allergen_id=allergen_id,
                        symptom_id=symptom_id,
                        relation_id=relation_id,
                        operation='delete'
                    )
                except Exception:
                    pass
                
                # 2. 删除佐证数据
                AllergenSymptomSource.query.filter_by(
                    allergen_symptom_id=relation_id
                ).delete(synchronize_session=False)
                
                # 3. 删除关系记录
                db.session.delete(relation)
                success_ids.append(relation_id)
                
            except Exception as item_error:
                logger.error(f'删除关联关系 {relation_id} 失败: {item_error}')
                failed_ids.append(relation_id)
        
        db.session.commit()
        
        logger.info(f'批量删除化学应激源-症状关系: success={success_ids}, failed={failed_ids}')
        
        return jsonify({
            'code': 200,
            'message': f'批量删除完成，成功 {len(success_ids)} 条，失败 {len(failed_ids)} 条',
            'data': {
                'success_count': len(success_ids),
                'failed_count': len(failed_ids),
                'success_ids': success_ids,
                'failed_ids': failed_ids
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量删除化学应激源-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


###############化学应激源-产品##################

@bp.route('/allergen-product/create', methods=['POST'])
def create_allergen_product():
    """创建化学应激源-产品关联关系
    
    同时创建MySQL和Neo4j
    """
    try:
        data = request.get_json()
        new_product_id = data['product_id']
        new_allergen_id = data['allergen_id']

        if not new_product_id or not new_allergen_id:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: product_id 和 allergen_id'
            }), 400

        # 检查关系是否存在
        existing = AllergenProduct.query.filter_by(
            product_id = new_product_id,
            allergen_id = new_allergen_id
        ).first()
        if existing:
            return jsonify({
                'code': 409,
                'message': '创建关系失败，该关联关系已存在'
            }),409

        # 1.创建mysql记录
        try:
            new_relation = AllergenProduct(
                product_id = new_product_id,
                allergen_id = new_allergen_id
            )
            db.session.add(new_relation)
            db.session.commit()
        except Exception as e:
            print('创建mysql记录失败')
            return jsonify({
                'code': 500,
                'message': '创建mysql记录失败'
            }),500

        # 2.创建neo4j记录
        try:
            Neo4jSyncService.sync_allergen_product_relation(
                product_id = new_product_id,
                allergen_id = new_allergen_id,
                relation_id = new_relation.id,
                operation='create'
            )
        except Exception as e:
            print('创建neo4j记录失败')
            return jsonify({
                'code': 500,
                'message': '创建neo4j记录失败'
            }),500

        return jsonify({
            'code': 200,
            'message': '关联关系创建成功',
        }),200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 501,
            'message': f'服务器错误: {str(e)}'
        }), 501


@bp.route('/allergen-product/<int:relation_id>', methods=['PUT'])
def update_allergen_product_relation(relation_id):
    """更新化学应激源-产品关联关系
    
    同时更新MySQL和Neo4j
    """
    try:
        relation = db.session.get(AllergenProduct, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        data = request.get_json()
        note = data.get('note', '')
        product_id = data.get('product_id')
        allergen_id = data.get('allergen_id')
        
        # 验证新的产品和化学应急源是否存在（如果提供了的话）
        if product_id and product_id != relation.product_id:
            product = db.session.get(Product, product_id)
            if not product:
                return jsonify({
                    'code': 404,
                    'message': f'产品 ID {product_id} 不存在'
                }), 404
            relation.product_id = product_id
            
        if allergen_id and allergen_id != relation.allergen_id:
            allergen = db.session.get(Allergen, allergen_id)
            if not allergen:
                return jsonify({
                    'code': 404,
                    'message': f'化学应急源 ID {allergen_id} 不存在'
                }), 404
            relation.allergen_id = allergen_id
        
        # 1. 更新MySQL
        relation.note = note
        relation.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 2. 同步到Neo4j
        sync_success = Neo4jSyncService.sync_allergen_product_relation(
            allergen_id=relation.allergen_id,
            product_id=relation.product_id,
            relation_id=relation_id,
            operation='update',
            note=note
        )
        
        if not sync_success:
            logger.warning(f'Neo4j同步失败，但MySQL记录已更新: relation_id={relation_id}')
        
        return jsonify({
            'code': 200,
            'message': '关联关系更新成功',
            'data': {
                'id': relation.id,
                'allergen_id': relation.allergen_id,
                'product_id': relation.product_id,
                'note': relation.note,
                'neo4j_synced': sync_success,
                'updated_at': relation.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'更新化学应激源-产品关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-product/<int:relation_id>', methods=['DELETE'])
def delete_allergen_product_relation(relation_id):
    """删除化学应激源-产品关联关系
    
    同时从MySQL和Neo4j删除
    """
    try:
        relation = db.session.get(AllergenProduct, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        allergen_id = relation.allergen_id
        product_id = relation.product_id
        
        # 1. 从Neo4j删除
        Neo4jSyncService.sync_allergen_product_relation(
            allergen_id=allergen_id,
            product_id=product_id,
            relation_id=relation_id,
            operation='delete'
        )
        
        # 2. 删除相关的佐证数据
        # 删除AllergenProductSource表和ExposureScoringDetail中的佐证记录（如果存在的话）
        try:
            allergen_product_sources = AllergenProductSource.query.filter_by(
                allergen_product_id=relation_id
            ).all()

            ExposureScoringDetail.query.filter_by(
                allergen_product_id=relation_id
            ).delete(synchronize_session=False)
            
            for source in allergen_product_sources:
                db.session.delete(source)
            db.session.commit()
                
        except Exception as source_error:
            # 如果佐证表不存在或查询失败，继续删除主关系
            logger.warning(f'清理佐证数据时出错，但继续删除主关系: {source_error}')

        
        # 3. 从MySQL删除主关系记录
        db.session.delete(relation)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '关联关系删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'删除化学应激源-产品关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500

@bp.route('/allergen-product/batch-delete', methods=['DELETE'])
def batch_delete_allergen_product_relations():
    """批量删除化学应激源-产品关联关系
    
    同时从MySQL和Neo4j删除
    """
    try:
        data = request.get_json()
        relation_ids = data.get('ids', [])
        
        if not relation_ids:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: ids'
            }), 400
        
        success_ids = []
        failed_ids = []
        
        for relation_id in relation_ids:
            try:
                relation = db.session.get(AllergenProduct, relation_id)
                if not relation:
                    failed_ids.append(relation_id)
                    continue
                
                # 1. 从Neo4j删除
                try:
                    Neo4jSyncService.sync_allergen_product_relation(
                        allergen_id=relation.allergen_id,
                        product_id=relation.product_id,
                        relation_id=relation_id,
                        operation='delete'
                    )
                except Exception:
                    pass
                
                # 2. 删除佐证数据
                try:
                    AllergenProductSource.query.filter_by(
                        allergen_product_id=relation_id
                    ).delete(synchronize_session=False)
                    ExposureScoringDetail.query.filter_by(
                        allergen_product_id=relation_id
                    ).delete(synchronize_session=False)
                except Exception as source_error:
                    logger.warning(f'清理佐证数据时出错: {source_error}')
                
                # 3. 删除关系记录
                db.session.delete(relation)
                success_ids.append(relation_id)
                
            except Exception as item_error:
                logger.error(f'删除关联关系 {relation_id} 失败: {item_error}')
                failed_ids.append(relation_id)
        
        db.session.commit()
        
        logger.info(f'批量删除化学应激源-产品关系: success={success_ids}, failed={failed_ids}')
        
        return jsonify({
            'code': 200,
            'message': f'批量删除完成，成功 {len(success_ids)} 条，失败 {len(failed_ids)} 条',
            'data': {
                'success_count': len(success_ids),
                'failed_count': len(failed_ids),
                'success_ids': success_ids,
                'failed_ids': failed_ids
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量删除化学应激源-产品关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-product/list', methods=['GET'])
def list_allergen_product_relations():
    """查询化学应激源-产品关联关系列表"""
    try:
        allergen_id = request.args.get('allergen_id', type=int)
        product_id = request.args.get('product_id', type=int)
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        query = AllergenProduct.query
        
        if allergen_id:
            query = query.filter_by(allergen_id=allergen_id)
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        # 添加搜索功能：根据产品名称或化学应急源名称搜索
        if search:
            query = query.join(Product, AllergenProduct.product_id == Product.id)\
                        .join(Allergen, AllergenProduct.allergen_id == Allergen.id)\
                        .filter(
                            db.or_(
                                Product.name.like(f'%{search}%'),
                                Allergen.name.like(f'%{search}%')
                            )
                        )
        
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        relations = []
        for rel in pagination.items:
            # 解析暴露潜力评分详情
            exposure_details = None
            if rel.exposure_details:
                try:
                    exposure_details = json.loads(rel.exposure_details)
                except json.JSONDecodeError:
                    exposure_details = None
            
            relations.append({
                'id': rel.id,
                'allergen_id': rel.allergen_id,
                'allergen_name': rel.allergen.name if rel.allergen else '',
                'product_id': rel.product_id,
                'product_name': rel.product.name if rel.product else '',
                'exposure_score': rel.exposure_score,
                'exposure_details': exposure_details,
                'note': rel.note,
                'created_at': rel.created_at.isoformat(),
                'updated_at': rel.updated_at.isoformat()
            })
        
        return jsonify({
            'code': 200,
            'message': '查询成功',
            'data': {
                'items': relations,
                'total': pagination.total,
                'page': page,
                'page_size': page_size,
                'total_pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f'查询化学应激源-产品关联列表失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-product/<int:relation_id>/exposure-scoring', methods=['PUT'])
def update_exposure_scoring(relation_id):
    """更新产品-化学应急源关联的暴露潜力评分"""
    try:
        relation = db.session.get(AllergenProduct, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': '关联关系不存在'
            }), 404
        
        data = request.get_json()
        scoring_details = data.get('scoring_details', {})
        exposure_score = data.get('exposure_score', 0)
        note = data.get('note', '')
        
        # 查找或创建评分细节记录
        scoring_detail = db.session.query(ExposureScoringDetail).filter_by(
            allergen_product_id=relation_id
        ).first()
        
        if not scoring_detail:
            scoring_detail = ExposureScoringDetail(allergen_product_id=relation_id)
            db.session.add(scoring_detail)
        
        # 更新评分细节
        if 'age' in scoring_details:
            scoring_detail.age_score = int(scoring_details['age'])
            
        if 'product_form' in scoring_details:
            scoring_detail.product_form_score = int(scoring_details['product_form'])
            
        if 'content' in scoring_details:
            scoring_detail.content_score = int(scoring_details['content'])
            
        if 'frequency' in scoring_details:
            scoring_detail.frequency_score = int(scoring_details['frequency'])
            
        if 'duration' in scoring_details:
            scoring_detail.duration_score = int(scoring_details['duration'])
        
        # 设置总分
        scoring_detail.total_score = exposure_score
        
        # 更新AllergenProduct表的exposure_score
        relation.exposure_score = exposure_score
        relation.note = note
        relation.exposure_details = json.dumps(scoring_details, ensure_ascii=False)
        relation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '暴露潜力评分更新成功',
            'data': {
                'relation_id': relation_id,
                'exposure_score': exposure_score,
                'scoring_details': scoring_details,
                'total_score': scoring_detail.total_score
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'更新暴露潜力评分失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-product/<int:relation_id>/exposure-scoring', methods=['GET'])
def get_exposure_scoring_detail(relation_id):
    """获取产品-化学应急源关联的暴露潜力评分细节"""
    try:
        # 查找评分细节记录
        scoring_detail = db.session.query(ExposureScoringDetail).filter_by(
            allergen_product_id=relation_id
        ).first()
        
        if not scoring_detail:
            return jsonify({
                'code': 200,
                'message': '暂无评分细节',
                'data': {
                    'scoring_details': {},
                    'total_score': 0
                }
            }), 200
        
        # 构建评分细节字典
        scoring_details = {}
        if scoring_detail.age_score:
            scoring_details['age'] = str(scoring_detail.age_score)
        if scoring_detail.product_form_score:
            scoring_details['product_form'] = str(scoring_detail.product_form_score)
        if scoring_detail.content_score:
            scoring_details['content'] = str(scoring_detail.content_score)
        if scoring_detail.frequency_score:
            scoring_details['frequency'] = str(scoring_detail.frequency_score)
        if scoring_detail.duration_score:
            scoring_details['duration'] = str(scoring_detail.duration_score)
        
        return jsonify({
            'code': 200,
            'message': '获取评分细节成功',
            'data': {
                'scoring_details': scoring_details,
                'total_score': scoring_detail.total_score or 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取暴露潜力评分细节失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/available-literature', methods=['GET'])
def get_available_literature():
    """获取可用的文献列表，用于关联选择"""
    try:
        # 获取所有已处理的文献（state=1表示已处理）
        literature_query = Literature.query.filter(Literature.state == 1)
        
        # 可选的过滤条件
        literature_type = request.args.get('type')
        if literature_type:
            literature_query = literature_query.filter(Literature.literature_type == literature_type)
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        pagination = literature_query.paginate(page=page, per_page=page_size, error_out=False)
        
        literature_list = []
        for lit in pagination.items:
            literature_list.append({
                'id': lit.id,
                'title': lit.title,
                'source': lit.source,
                'pmid': lit.pmid,
                'authors': lit.authors,
                'publish_date': lit.publish_date.isoformat() if lit.publish_date else None,
                'abstract': lit.abstract[:200] + '...' if lit.abstract and len(lit.abstract) > 200 else lit.abstract,
                'literature_type': lit.literature_type,
                'created_at': lit.created_at.isoformat() if lit.created_at else None
            })
        
        return jsonify({
            'code': 200,
            'message': '查询成功',
            'data': {
                'items': literature_list,
                'total': pagination.total,
                'page': page,
                'page_size': page_size,
                'total_pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取可用文献列表失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-symptom/<int:relation_id>/literature/batch', methods=['POST'])
def batch_update_literature_relations(relation_id):
    """批量更新化学应激源-症状关联的文献关系
    
    支持批量添加和移除文献关联
    """
    try:
        data = request.get_json()
        action = data.get('action')  # 'add' 或 'remove'
        literature_ids = data.get('literature_ids', [])
        
        if not action or action not in ['add', 'remove']:
            return jsonify({
                'code': 400,
                'message': '缺少有效的操作类型，应为 add 或 remove'
            }), 400
        
        if not literature_ids:
            return jsonify({
                'code': 400,
                'message': '缺少文献ID列表'
            }), 400
        
        # 验证关系是否存在
        relation = db.session.get(AllergenSymptom, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        if action == 'add':
            # 批量添加文献关联
            added_count = 0
            for lit_id in literature_ids:
                # 检查是否已经关联
                existing = AllergenSymptomSource.query.filter_by(
                    allergen_symptom_id=relation_id,
                    literature_id=lit_id
                ).first()
                
                if existing:
                    continue
                
                # 验证文献是否存在
                literature = db.session.get(Literature, lit_id)
                if not literature:
                    continue
                
                # 直接创建关联记录
                allergen_symptom_source = AllergenSymptomSource(
                    allergen_symptom_id=relation_id,
                    literature_id=lit_id,
                    evidence_strength=1.0,
                    note=f'批量关联文献: {literature.title}'
                )
                db.session.add(allergen_symptom_source)
                added_count += 1
            
            db.session.commit()
            logger.info(f'批量添加文献关联: relation_id={relation_id}, added_count={added_count}')
            
            return jsonify({
                'code': 200,
                'message': f'成功添加 {added_count} 个文献关联',
                'data': {
                    'relation_id': relation_id,
                    'action': 'add',
                    'processed_count': added_count,
                    'total_requested': len(literature_ids)
                }
            }), 200
            
        elif action == 'remove':
            # 批量移除文献关联
            removed_count = 0
            for lit_id in literature_ids:
                # 查找并删除关联
                sources_to_remove = AllergenSymptomSource.query.filter_by(
                    allergen_symptom_id=relation_id,
                    literature_id=lit_id
                ).all()
                
                for source in sources_to_remove:
                    db.session.delete(source)
                    removed_count += 1
            
            db.session.commit()
            logger.info(f'批量移除文献关联: relation_id={relation_id}, removed_count={removed_count}')
            
            return jsonify({
                'code': 200,
                'message': f'成功移除 {removed_count} 个文献关联',
                'data': {
                    'relation_id': relation_id,
                    'action': 'remove',
                    'processed_count': removed_count,
                    'total_requested': len(literature_ids)
                }
            }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量更新文献关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/allergen-symptom/list', methods=['GET'])
def list_allergen_symptom_relations():
    """查询化学应激源-症状关联关系列表
    
    Query Parameters:
        allergen_id (int, optional): 按化学应激源ID过滤
        symptom_id (int, optional): 按症状ID过滤
        page (int, optional): 页码，默认1
        page_size (int, optional): 每页数量，默认20
    
    Returns:
        JSON: 包含关系列表、总数、分页信息和每个关系的TRAEC评分
    """
    try:
        # 获取查询参数
        allergen_id = request.args.get('allergen_id', type=int)
        symptom_id = request.args.get('symptom_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # 构建SQL查询：关联关系 + 化学应激源名称 + 症状名称 + 文献数量统计
        sql = """
            SELECT 
                asy.id,
                asy.allergen_id,
                a.name as allergen_name,
                asy.symptom_id,
                s.symptom_name as symptom_name,
                asy.update_at,
                COALESCE(lit_count.literature_count, 0) as literature_count
            FROM allergen_symptom asy
            LEFT JOIN allergen a ON asy.allergen_id = a.id
            LEFT JOIN symptom_2 s ON asy.symptom_id = s.id
            LEFT JOIN (
                SELECT 
                    ass.allergen_symptom_id,
                    COUNT(DISTINCT l.id) as literature_count
                FROM allergen_symptom_source ass
                JOIN literature l ON ass.literature_id = l.id
                GROUP BY ass.allergen_symptom_id
            ) lit_count ON asy.id = lit_count.allergen_symptom_id
            WHERE 1=1
        """
        
        # 动态添加过滤条件
        params = {}
        if allergen_id:
            sql += " AND asy.allergen_id = :allergen_id"
            params['allergen_id'] = allergen_id
        if symptom_id:
            sql += " AND asy.symptom_id = :symptom_id"
            params['symptom_id'] = symptom_id
        
        # 计算总数
        count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as subquery"
        total_result = db.session.execute(text(count_sql), params)
        total = total_result.scalar()
        
        # 添加排序和分页
        sql += " ORDER BY asy.id DESC LIMIT :limit OFFSET :offset"
        params['limit'] = page_size
        params['offset'] = (page - 1) * page_size
        
        # 执行查询
        result = db.session.execute(text(sql), params)
        
        # 构建返回数据
        relations = []
        for row in result:
            relation_id = row[0]
            
            # 计算该关系的TRAEC评分（基于关联文献的评分数据）
            traec_score = _calculate_traec_score(relation_id)
            
            relations.append({
                'id': relation_id,
                'allergen_id': row[1],
                'allergen_name': row[2] or '',
                'symptom_id': row[3],
                'symptom_name': row[4] or '',
                'updated_at': row[5].isoformat() if row[5] else None,
                'literature_count': row[6],
                'traec_score': traec_score
            })
        
        total_pages = (total + page_size - 1) // page_size
        
        return jsonify({
            'code': 200,
            'message': '查询成功',
            'data': {
                'items': relations,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f'查询化学应激源-症状关联列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


def _calculate_traec_score(relation_id):
    """计算指定关系的TRAEC评分（委托给 traec_scoring 服务）"""
    from ..services.traec_scoring import calculate_traec_score
    return calculate_traec_score(relation_id, db.session)


@bp.route('/allergen-symptom/<int:relation_id>/literature', methods=['GET'])
def get_allergen_symptom_literature(relation_id):
    """获取化学应激源-症状关联的文献数据及评分信息
    
    通过AllergenSymptomSource表获取关联的文献
    """
    try:
        # 验证关系是否存在
        relation = db.session.get(AllergenSymptom, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        # 通过AllergenSymptomSource获取关联的文献
        literature_sources = db.session.query(AllergenSymptomSource, Literature).join(
            Literature, AllergenSymptomSource.literature_id == Literature.id
        ).filter(
            AllergenSymptomSource.allergen_symptom_id == relation_id
        ).all()
        
        literature_data = []
        for source_rel, lit in literature_sources:
            # 获取评分数据
            epi_scoring = LiteratureEpiScoring.query.filter_by(literature_id=lit.id, relation_id = relation_id).first()
            vivo_scoring = LiteratureVivoScoring.query.filter_by(literature_id=lit.id, relation_id = relation_id).first()
            vitro_scoring = LiteratureVitroScoring.query.filter_by(literature_id=lit.id, relation_id = relation_id).first()
            
            # 根据文献类型选择对应的评分数据
            scoring_data = None
            if lit.literature_type == 'epidemiology' and epi_scoring:
                scoring_data = {
                    'type': 'epidemiology',
                    'type_display': '流行病学研究',
                    'reliability_score': float(epi_scoring.reliability_total_score) if epi_scoring.reliability_total_score else 0.0,
                    'correlation_score': float(epi_scoring.correlation_score) if epi_scoring.correlation_score else 0.0,
                    'concentration_weight': float(epi_scoring.concentration_weight) if epi_scoring.concentration_weight else 0.0,
                    'risk_intensity_score': float(epi_scoring.risk_intensity_score) if epi_scoring.risk_intensity_score else 0.0
                }
            elif lit.literature_type == 'in-vivo' and vivo_scoring:
                scoring_data = {
                    'type': 'in-vivo',
                    'type_display': '体内实验研究',
                    'reliability_score': float(vivo_scoring.reliability_total_score) if vivo_scoring.reliability_total_score else 0.0,
                    'correlation_score': float(vivo_scoring.correlation_score) if vivo_scoring.correlation_score else 0.0,
                    'concentration_weight': float(vivo_scoring.concentration_weight) if vivo_scoring.concentration_weight else 0.0,
                    'risk_intensity_score': float(vivo_scoring.risk_intensity_score) if vivo_scoring.risk_intensity_score else 0.0
                }
            elif lit.literature_type == 'in-vitro' and vitro_scoring:
                scoring_data = {
                    'type': 'in-vitro',
                    'type_display': '体外实验研究',
                    'reliability_score': float(vitro_scoring.reliability_total_score) if vitro_scoring.reliability_total_score else 0.0,
                    'correlation_score': float(vitro_scoring.correlation_score) if vitro_scoring.correlation_score else 0.0,
                    'concentration_weight': float(vitro_scoring.concentration_weight) if vitro_scoring.concentration_weight else 0.0,
                    'risk_intensity_score': float(vitro_scoring.risk_intensity_score) if vitro_scoring.risk_intensity_score else 0.0
                }
            
            literature_data.append({
                'id': lit.id,
                'title': lit.title,
                'source': lit.source,
                'pmid': lit.pmid,
                'authors': lit.authors,
                'publish_date': lit.publish_date.isoformat() if lit.publish_date else None,
                'abstract': lit.abstract,
                'keywords': lit.keywords,
                'link': lit.link,
                'literature_type': lit.literature_type,
                'state': lit.state,
                'scoring': scoring_data,
                'evidence_strength': float(source_rel.evidence_strength) if source_rel.evidence_strength else 1.0,
                'source_note': source_rel.note,
                'created_at': lit.created_at.isoformat() if lit.created_at else None
            })
        
        return jsonify({
            'code': 200,
            'message': '查询成功',
            'data': {
                'relation_id': relation_id,
                'allergen_name': relation.allergen.name if hasattr(relation, 'allergen') and relation.allergen else '',
                'symptom_name': relation.symptom.symptom_name if hasattr(relation, 'symptom') and relation.symptom else '',
                'relation_type': '诱发',  # 默认关系类型
                'literatures': literature_data,
                'total_count': len(literature_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取关联文献数据失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


# ==================== 产品-不良反应关联管理 ====================

@bp.route('/product-symptom', methods=['POST'])
def create_product_symptom_relation():
    """创建产品-不良反应关联关系
    
    同时同步到MySQL和Neo4j
    
    参数：
    - product_id: 产品ID (必填)
    - symptom_id: 症状ID (必填)
    - news_ids: 要关联的新闻ID列表 (可选)
    
    当提供news_ids时，会同时创建新闻与关系的关联
    """
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        symptom_id = data.get('symptom_id')
        news_ids = data.get('news_ids', [])  # 要关联的新闻ID列表
        
        # 验证必填字段
        if not product_id or not symptom_id:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: product_id 和 symptom_id'
            }), 400
        
        # 验证产品是否存在
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({
                'code': 404,
                'message': f'产品 ID {product_id} 不存在'
            }), 404
        # 验证不良反应是否存在
        symptom = db.session.get(Symptom2, symptom_id)
        if not symptom:
            return jsonify({
                'code': 404,
                'message': f'不良反应 ID {symptom_id} 不存在'
            }), 404
        
        # 检查关系是否已存在
        existing = ProductSymptom.query.filter_by(
            product_id=product_id,
            symptom_id=symptom_id
        ).first()
        
        if existing:
            return jsonify({
                'code': 409,
                'message': '该产品-症状关联关系已存在'
            }), 409
        
        # 创建MySQL记录
        relation = ProductSymptom(
            product_id=product_id,
            symptom_id=symptom_id,
            create_at=datetime.utcnow(),
            update_at=datetime.utcnow()
        )
        
        db.session.add(relation)
        db.session.flush()  # 获取relation.id
        
        # 处理新闻关联
        created_news_relations = []
        if news_ids:
            for news_id in news_ids:
                # 验证新闻是否存在
                news = db.session.get(News, news_id)
                if not news:
                    logger.warning(f"新闻ID {news_id} 不存在，跳过")
                    continue
                
                # 创建ProductSymptomNews记录
                news_source = ProductSymptomNews(
                    product_symptom_id=relation.id,
                    news_id=news_id,
                    evidence_strength=1.0
                )
                
                news.state = 1
                
                db.session.add(news_source)
                created_news_relations.append({
                    'news_id': news_id,
                    'news_title': news.title
                })
        
        db.session.commit()
        
        # 2. 同步到Neo4j
        sync_success = Neo4jSyncService.sync_product_symptom_relation(
            product_id=product_id,
            symptom_id=symptom_id,
            relation_id=relation.id,
            operation='create'
        )
        
        if not sync_success:
            logger.warning(f'Neo4j同步失败，但MySQL记录已创建: relation_id={relation.id}')
        
        return jsonify({
            'code': 200,
            'message': '产品-症状关联创建成功',
            'data': {
                'id': relation.id,
                'product_id': relation.product_id,
                'product_name': product.name,
                'symptom_id': relation.symptom_id,
                'symptom_name': symptom.symptom_name,
                'news_relations_count': len(created_news_relations),
                'news_relations': created_news_relations,
                'neo4j_synced': sync_success,
                'created_at': relation.create_at.isoformat(),
                'updated_at': relation.update_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'创建产品-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/product-symptom/<int:relation_id>', methods=['PUT'])
def update_product_symptom_relation(relation_id):
    """更新产品-症状关联关系
    
    支持两种操作：
    1. 删除现有的新闻关联（news_ids_to_remove）
    2. 添加新的新闻关联（news_ids）
    
    参数：
    - product_id: 产品ID
    - symptom_id: 症状ID  
    - news_ids: 要添加的新闻ID列表
    - news_ids_to_remove: 要删除的新闻ID列表
    """
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        symptom_id = data.get('symptom_id')
        news_ids = data.get('news_ids', [])  # 要添加的新闻 ID列表
        news_ids_to_remove = data.get('news_ids_to_remove', [])  # 要删除的新闻 ID列表
        
        # 获取现有关系
        relation_obj = db.session.get(ProductSymptom, relation_id)
        if not relation_obj:
            return jsonify({
                'code': 404,
                'message': f'关联关系 ID {relation_id} 不存在'
            }), 404
        
        # 验证实体是否存在
        try:
            product = db.session.get(Product, product_id)
            if not product:
                return jsonify({
                    'code': 404,
                    'message': f'产品 ID {product_id} 不存在'
                }), 404
        except Exception as product_error:
            logger.error(f'查询产品异常: {product_error}')
            return jsonify({
                'code': 500,
                'message': f'查询产品失败: {str(product_error)}'
            }), 500
        
        try:
            symptom = db.session.get(Symptom2, symptom_id)
            if not symptom:
                return jsonify({
                    'code': 404,
                    'message': f'不良反应 ID {symptom_id} 不存在'
                }), 404
        except Exception as symptom_error:
            logger.error(f'查询不良反应异常: {symptom_error}')
            return jsonify({
                'code': 500,
                'message': f'查询不良反应失败: {str(symptom_error)}'
            }), 500
        
        # 如果修改了关联实体，检查新的关系是否已存在
        if (relation_obj.product_id != product_id or relation_obj.symptom_id != symptom_id):
            existing = ProductSymptom.query.filter_by(
                product_id=product_id,
                symptom_id=symptom_id
            ).filter(ProductSymptom.id != relation_id).first()
            
            if existing:
                return jsonify({
                    'code': 409,
                    'message': '该关联关系已存在'
                }), 409
        
        # 1. 更新MySQL记录
        relation_obj.product_id = product_id
        relation_obj.symptom_id = symptom_id
        relation_obj.update_at = datetime.utcnow()
    
        # 获取当前已关联的新闻佐证数据
        current_sources = ProductSymptomNews.query.filter_by(
            product_symptom_id=relation_id
        ).all()
        
        current_news_ids = set()
        
        for source in current_sources:
            if source.news_id:
                current_news_ids.add(source.news_id)
        
        new_news_ids = set(news_ids)
        
        # 初始化计数器
        news_to_remove = set(news_ids_to_remove) if news_ids_to_remove else set()
        news_removed_count = 0
        
        # 处理要删除的新闻关联
        if news_ids_to_remove:
            for source in current_sources:
                if source.news_id and source.news_id in news_to_remove:
                    db.session.delete(source)
                    news_removed_count += 1
                    logger.info(f'删除新闻关联: {source.news_id}')
        
        # 处理要添加的新闻关联（只添加不存在的）
        news_to_add = new_news_ids - current_news_ids
        
        # 添加新的新闻关联
        for news_id in news_to_add:
            # 验证新闻是否存在
            news = db.session.get(News, news_id)
            if not news:
                logger.warning(f"新闻ID {news_id} 不存在，跳过")
                continue
                
            # 创建ProductSymptomNews记录
            product_symptom_source = ProductSymptomNews(
                product_symptom_id=relation_id,
                news_id=news_id,
                evidence_strength=1.0
            )
            db.session.add(product_symptom_source)
        
        # 重新计算PRR和卡方值
        try:
            signal_result = calculate_product_symptom_signal(db.session, product_id, symptom_id)
            relation_obj.PRR = signal_result.get('PRR')
            relation_obj.X_2 = signal_result.get('chi_square', 0.0)
        except Exception as e:
            logger.warning(f"更新时计算事件信号失败，保持原值: {e}")
        
        db.session.commit()
        
        # 3. 同步到Neo4j
        sync_success = Neo4jSyncService.sync_product_symptom_relation(
            product_id=product_id,
            symptom_id=symptom_id,
            relation_id=relation_id,
            operation='update'
        )
        
        if not sync_success:
            logger.warning(f'Neo4j同步失败，但MySQL记录已更新: relation_id={relation_id}')
        
        return jsonify({
            'code': 200,
            'message': '关联关系更新成功',
            'data': {
                'id': relation_obj.id,
                'product_id': relation_obj.product_id,
                'product_name': product.name,
                'symptom_id': relation_obj.symptom_id,
                'symptom_name': symptom.symptom_name,
                'news_count': len(new_news_ids),
                'news_added_count': len(news_to_add),
                'news_removed_count': news_removed_count,
                'neo4j_synced': sync_success,
                'updated_at': relation_obj.update_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'更新产品-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/product-symptom/<int:relation_id>', methods=['DELETE'])
def delete_product_symptom_relation(relation_id):
    """删除产品-症状关联关系"""
    try:
        # 检查关系是否存在
        relation = db.session.get(ProductSymptom, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'产品-症状关联 {relation_id} 不存在'
            }), 404
        
        # 同步到Neo4j (删除前)
        sync_success = Neo4jSyncService.sync_product_symptom_relation(
            product_id=relation.product_id,
            symptom_id=relation.symptom_id,
            relation_id=relation.id,
            operation='delete'
        )
        
        # 删除相关的佐证数据
        # 删除ProductSymptomNews表中的新闻关联记录
        news_sources = ProductSymptomNews.query.filter_by(
            product_symptom_id=relation_id
        ).all()
        
        # 删除ProductSymptomComp表中的投诉关联记录
        complaint_sources = ProductSymptomComp.query.filter_by(
            product_symptom_id=relation_id
        ).all()
        
        deleted_sources_count = len(news_sources) + len(complaint_sources)
        
        for source in news_sources:
            db.session.delete(source)
            
        for source in complaint_sources:
            db.session.delete(source)
        
        # 删除关系
        db.session.delete(relation)
        db.session.commit()
        
        logger.info(f'删除产品-症状关系 {relation_id}，同时删除了 {deleted_sources_count} 条佐证记录')
        
        if not sync_success:
            logger.warning(f'Neo4j同步失败，但MySQL记录已删除: relation_id={relation_id}')
        
        return jsonify({
            'code': 200,
            'message': '产品-症状关联删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'删除产品-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/product-symptom/batch-delete', methods=['DELETE'])
def batch_delete_product_symptom_relations():
    """批量删除产品-症状关联关系
    
    同时从MySQL和Neo4j删除
    """
    try:
        data = request.get_json()
        relation_ids = data.get('ids', [])
        
        if not relation_ids:
            return jsonify({
                'code': 400,
                'message': '缺少必填字段: ids'
            }), 400
        
        success_ids = []
        failed_ids = []
        
        for relation_id in relation_ids:
            try:
                relation = db.session.get(ProductSymptom, relation_id)
                if not relation:
                    failed_ids.append(relation_id)
                    continue
                
                # 1. 从Neo4j删除
                try:
                    Neo4jSyncService.sync_product_symptom_relation(
                        product_id=relation.product_id,
                        symptom_id=relation.symptom_id,
                        relation_id=relation_id,
                        operation='delete'
                    )
                except Exception:
                    pass
                
                # 2. 删除佐证数据
                ProductSymptomNews.query.filter_by(
                    product_symptom_id=relation_id
                ).delete(synchronize_session=False)
                ProductSymptomComp.query.filter_by(
                    product_symptom_id=relation_id
                ).delete(synchronize_session=False)
                
                # 3. 删除关系记录
                db.session.delete(relation)
                success_ids.append(relation_id)
                
            except Exception as item_error:
                logger.error(f'删除产品-症状关联 {relation_id} 失败: {item_error}')
                failed_ids.append(relation_id)
        
        db.session.commit()
        
        logger.info(f'批量删除产品-症状关系: success={success_ids}, failed={failed_ids}')
        
        return jsonify({
            'code': 200,
            'message': f'批量删除完成，成功 {len(success_ids)} 条，失败 {len(failed_ids)} 条',
            'data': {
                'success_count': len(success_ids),
                'failed_count': len(failed_ids),
                'success_ids': success_ids,
                'failed_ids': failed_ids
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量删除产品-症状关联失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/product-symptom/list', methods=['GET'])
def get_product_symptom_relations():
    """获取产品-症状关联关系列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 构建查询
        query = db.session.query(ProductSymptom).join(Product).join(Symptom2)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                db.or_(
                    Product.name.ilike(f'%{search}%'),
                    Symptom2.symptom_name.ilike(f'%{search}%')
                )
            )
        
        # 分页
        total = query.count()
        relations = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # 格式化数据
        items = []
        for relation in relations:
            # 计算证据数量 - 修复SQL查询
            try:
                # 分别统计新闻和投诉的证据数量
                news_count = db.session.query(db.func.count(ProductSymptomNews.id)).filter(
                    ProductSymptomNews.product_symptom_id == relation.id
                ).scalar() or 0
                
                complaint_count = db.session.query(db.func.count(ProductSymptomComp.id)).filter(
                    ProductSymptomComp.product_symptom_id == relation.id
                ).scalar() or 0
                
                evidence_count = news_count + complaint_count
            except Exception as e:
                logger.warning(f"计算证据数量失败: {e}")
                evidence_count = 0
            
            items.append({
                'id': relation.id,
                'product_id': relation.product_id,
                'product_name': relation.product.name,
                'symptom_id': relation.symptom_id,
                'symptom_name': relation.symptom.symptom_name,
                'confidence': relation.PRR or 0.0,
                'evidence_count': evidence_count,
                'created_at': relation.create_at.isoformat() if relation.create_at else None,
                'updated_at': relation.update_at.isoformat() if relation.update_at else None
            })
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取产品-症状关系列表失败: {e}")
        return jsonify({'error': '获取关系列表失败'}), 500


@bp.post('/product-symptom/recalculate-all-scores')
def recalculate_all_product_symptom_scores():
    """重新计算所有产品-症状关系的PRR和卡方值"""
    logger = logging.getLogger(__name__)
    
    try:
        # 获取所有产品-症状关系
        all_relations = db.session.query(ProductSymptom).all()
        updated_count = 0
        
        for relation in all_relations:
            try:
                # 重新计算PRR和卡方值
                signal_result = calculate_product_symptom_signal(
                    db.session, 
                    relation.product_id, 
                    relation.symptom_id
                )
                
                # 更新PRR和卡方值
                old_prr = relation.PRR
                old_chi2 = relation.X_2
                relation.PRR = signal_result.get('PRR')
                relation.X_2 = signal_result.get('chi_square', 0.0)
                updated_count += 1
                
                logger.info(
                    f"更新关系 {relation.id} "
                    f"(产品: {relation.product.name}, 症状: {relation.symptom.symptom_name}) "
                    f"PRR: {old_prr} -> {relation.PRR}, "
                    f"χ²: {old_chi2} -> {relation.X_2}, "
                    f"信号: {signal_result.get('signal_label')}"
                )
                
            except Exception as e:
                logger.error(f"重新计算关系 {relation.id} 的事件信号失败: {e}")
                continue
        
        # 提交数据库更改
        db.session.commit()
        
        logger.info(f"成功更新了 {updated_count} 个产品-症状关系的事件信号")
        
        return jsonify({
            'message': f'成功重新计算了 {updated_count} 个关系的事件信号(PRR/卡方值)',
            'updated_count': updated_count,
            'total_count': len(all_relations)
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"重新计算所有产品-症状关系事件信号失败: {e}")
        return jsonify({'error': '重新计算事件信号失败'}), 500


# ==================== 产品-症状证据来源管理 ====================

@bp.route('/product-symptom/<int:relation_id>/sources', methods=['GET'])
def get_product_symptom_sources(relation_id):
    """获取产品-症状关联的证据来源列表"""
    try:
        # 验证关系是否存在
        relation = db.session.get(ProductSymptom, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'产品-症状关联 {relation_id} 不存在'
            }), 404
        
        # 获取证据来源 - 分别从新闻和投诉表获取
        news_sources = db.session.query(ProductSymptomNews)\
            .filter_by(product_symptom_id=relation_id)\
            .all()
            
        complaint_sources = db.session.query(ProductSymptomComp)\
            .filter_by(product_symptom_id=relation_id)\
            .all()
        
        # 格式化数据
        items = []
        
        # 添加新闻来源
        for source in news_sources:
            item = {
                'id': f"news_{source.id}",
                'type': 'news',
                'source_id': source.id,
                'product_symptom_id': source.product_symptom_id,
                'news_id': source.news_id,
                'evidence_strength': source.evidence_strength,
                'created_at': getattr(source, 'created_at', None).isoformat() if getattr(source, 'created_at', None) else None,
                'updated_at': getattr(source, 'updated_at', None).isoformat() if getattr(source, 'updated_at', None) else None
            }
            
            # 添加新闻信息
            if source.news_id:
                try:
                    news = db.session.get(News, source.news_id)
                    if news:
                        item['news_info'] = {
                            'title': news.title,
                            'source': news.source,
                            'publishTime': news.publish_time.isoformat() if news.publish_time else None
                        }
                except Exception as e:
                    logger.warning(f"获取新闻信息失败: {e}")
            
            items.append(item)
            
        # 添加投诉来源
        for source in complaint_sources:
            item = {
                'id': f"complaint_{source.id}",
                'type': 'complaint',
                'source_id': source.id,
                'product_symptom_id': source.product_symptom_id,
                'complaints_id': source.complaints_id,
                'created_at': getattr(source, 'created_at', None).isoformat() if getattr(source, 'created_at', None) else None,
                'updated_at': getattr(source, 'updated_at', None).isoformat() if getattr(source, 'updated_at', None) else None
            }
            
            # 添加投诉信息
            if source.complaints_id:
                try:
                    from ..models import Complaints
                    complaint = db.session.get(Complaints, source.complaints_id)
                    if complaint:
                        item['complaint_info'] = {
                            'id': f"complaint_{source.id}",
                            'title': complaint.title ,
                            'source': getattr(complaint, 'source', None) or '投诉来源',
                            'publish_time': complaint.publish_time.isoformat() if getattr(complaint, 'publish_time', None) else None,
                            'abstract': getattr(complaint, 'abstract', None) or getattr(complaint, 'summary', None),
                        }
                except Exception as e:
                    logger.warning(f"获取投诉信息失败: {e}")
            
            items.append(item)
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'items': items,
                'total': len(items)
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取产品-症状证据来源失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500


@bp.route('/product-symptom/<int:relation_id>/sources', methods=['POST'])
def create_product_symptom_source(relation_id):
    """创建产品-症状证据来源"""
    try:
        # 验证关系是否存在
        relation = db.session.get(ProductSymptom, relation_id)
        if not relation:
            return jsonify({
                'code': 404,
                'message': f'产品-症状关联 {relation_id} 不存在'
            }), 404
        
        data = request.get_json()
        news_id = data.get('news_id')
        evidence_strength = data.get('evidence_strength', 1.0)
        
        # 验证新闻是否存在
        if news_id:
            news = db.session.get(News, news_id)
            if not news:
                return jsonify({
                    'code': 404,
                    'message': f'新闻 {news_id} 不存在'
                }), 404
        
        # 创建证据来源记录
        source = ProductSymptomNews(
            product_symptom_id=relation_id,
            news_id=news_id,
            evidence_strength=evidence_strength
        )
        
        # 只有当字段存在时才设置时间戳
        if hasattr(ProductSymptomNews, 'created_at'):
            source.created_at = datetime.utcnow()
        if hasattr(ProductSymptomNews, 'updated_at'):
            source.updated_at = datetime.utcnow()
        
        db.session.add(source)
        db.session.flush()
        
        # 重新计算该产品-症状关联的PRR和卡方值
        try:
            signal_result = calculate_product_symptom_signal(
                db.session, relation.product_id, relation.symptom_id
            )
            relation.PRR = signal_result.get('PRR')
            relation.X_2 = signal_result.get('chi_square', 0.0)
            logger.info(
                f"证据创建后更新事件信号: relation_id={relation_id}, "
                f"PRR={relation.PRR}, χ²={relation.X_2}, "
                f"信号={signal_result.get('signal_label')}"
            )
        except Exception as e:
            logger.warning(f"创建证据后计算事件信号失败: {e}")
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '证据来源创建成功',
            'data': {
                'id': source.id,
                'product_symptom_id': source.product_symptom_id,
                'news_id': source.news_id,
                'evidence_strength': source.evidence_strength,
                'PRR': relation.PRR,
                'chi_square': relation.X_2,
                'created_at': source.created_at.isoformat() if source.created_at else None,
                'updated_at': source.updated_at.isoformat() if source.updated_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'创建产品-症状证据来源失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }), 500
