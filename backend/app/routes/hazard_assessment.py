from flask import Blueprint, request, jsonify
from ..services.neo4j_client import Neo4jClient
from ..models import (
    Allergen, AllergenSymptom, AllergenSymptomSource, Literature, Symptom2,
    Product, AllergenProduct, ProductSymptom, ExposureScoringDetail
)
from .. import db
from ..services.confidence_scoring import EventSignalCalculator, calculate_product_symptom_signal
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('hazard_assessment', __name__)


@bp.route('/assess', methods=['POST'])
def assess_hazard():
    """危害评估：根据化学物质名称或CAS号查询不良反应
    
    请求参数:
        - query: 化学物质名称或CAS号
    
    返回:
        - allergen: 化学应急源信息
        - symptoms: 不良反应列表（按TRAEC评分降序）
        - graph_data: 知识图谱数据（节点和边）
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'code': 400,
                'message': '请输入化学物质名称或CAS号'
            }), 400
        
        # 1. 从MySQL查找化学应急源（通过名称或CAS号）
        allergen = Allergen.query.filter(
            db.or_(
                Allergen.name == query,
                Allergen.cas_number == query
            )
        ).first()
        
        if not allergen:
            return jsonify({
                'code': 404,
                'message': f'未找到化学物质: {query}'
            }), 404
        
        # 2. 从MySQL查询该化学应急源的所有不良反应（按TRAEC评分降序）
        symptoms_data = []
        
        # 查询化学应急源关联的二级症状（不良反应）
        relations = db.session.query(AllergenSymptom, Symptom2).join(
            Symptom2, AllergenSymptom.symptom_id == Symptom2.id
        ).filter(
            AllergenSymptom.allergen_id == allergen.id
        ).order_by(AllergenSymptom.traec_score.desc().nullslast()).all()
        
        for relation, symptom in relations:
            # 查询该关系的佐证文献
            literatures = []
            try:
                sources = AllergenSymptomSource.query.filter_by(
                    allergen_symptom_id=relation.id
                ).all()
                
                for source in sources:
                    lit = db.session.get(Literature, source.literature_id)
                    if lit:
                        literatures.append({
                            'id': lit.id,
                            'title': lit.title,
                            'authors': lit.authors,
                            'source': lit.source,
                            'publish_date': lit.publish_date.isoformat() if lit.publish_date else None,
                            'pmid': lit.pmid,
                            'link': lit.link,
                            'evidence_strength': source.evidence_strength
                        })
            except Exception as lit_error:
                logger.warning(f'查询佐证文献失败: {lit_error}')
            
            symptoms_data.append({
                'symptom_id': symptom.id,
                'symptom_name': symptom.symptom_name,
                'traec_score': relation.traec_score or 0.0,
                'relation_id': relation.id,
                'literatures': literatures
            })
        
        # 4. 构建知识图谱数据
        graph_data = build_knowledge_graph(allergen, symptoms_data)
        
        return jsonify({
            'code': 200,
            'data': {
                'allergen': {
                    'id': allergen.id,
                    'name': allergen.name,
                    'cas_number': allergen.cas_number,
                    'description': allergen.description
                },
                'symptoms': symptoms_data,
                'graph_data': graph_data
            }
        }), 200
        
    except Exception as e:
        logger.error(f'危害评估失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'危害评估失败: {str(e)}'
        }), 500


def build_knowledge_graph(allergen, symptoms_data):
    """构建知识图谱数据结构
    
    三层结构：化学应急源 -> 不良反应 -> 具体症状（显示TRAEC评分和文献数量）
    
    Args:
        allergen: 化学应急源对象
        symptoms_data: 症状数据列表
    
    Returns:
        包含nodes和edges的字典
    """
    nodes = []
    edges = []
    
    # 1. 添加化学应急源节点（中心节点）
    allergen_node = {
        'id': f'allergen_{allergen.id}',
        'label': allergen.name,
        'type': 'allergen',
        'data': {
            'name': allergen.name,
            'cas_number': allergen.cas_number,
            'description': allergen.description
        }
    }
    nodes.append(allergen_node)
    
    # 2. 添加"不良反应"节点（固定节点）
    adverse_reaction_node = {
        'id': 'adverse_reaction',
        'label': '不良反应',
        'type': 'adverse_reaction',
        'data': {
            'name': '不良反应',
            'description': '化学应急源可能导致的不良反应'
        }
    }
    nodes.append(adverse_reaction_node)
    
    # 添加边: 化学应急源 -> 不良反应
    edges.append({
        'source': f'allergen_{allergen.id}',
        'target': 'adverse_reaction',
        'label': '可能导致',
        'type': 'may_cause'
    })
    
    # 3. 添加具体症状节点（显示TRAEC评分和文献数量）
    for symptom in symptoms_data:
        lit_count = len(symptom['literatures'])
        
        # 构建标签：症状名称 + TRAEC评分 + 文献数量
        symptom_label = symptom['symptom_name']
        if symptom['traec_score'] > 0:
            symptom_label += f'\nTRAEC: {symptom["traec_score"]:.2f}'
        if lit_count > 0:
            symptom_label += f'\n({lit_count}篇文献)'
        
        symptom_node = {
            'id': f'symptom_{symptom["symptom_id"]}',
            'label': symptom_label,
            'type': 'symptom',
            'data': {
                'name': symptom['symptom_name'],
                'traec_score': symptom['traec_score'],
                'literature_count': lit_count,
                # 将文献详情存储在节点数据中，供前端点击时使用
                'literatures': symptom['literatures']
            }
        }
        nodes.append(symptom_node)
        
        # 添加边: 不良反应 -> 具体症状
        edges.append({
            'source': 'adverse_reaction',
            'target': f'symptom_{symptom["symptom_id"]}',
            'label': '包括',
            'type': 'includes'
        })
    
    return {
        'nodes': nodes,
        'edges': edges
    }


@bp.route('/products', methods=['GET'])
def get_all_products():
    """获取所有产品列表"""
    try:
        products = Product.query.order_by(Product.name).all()
        product_list = [{'id': p.id, 'name': p.name} for p in products]
        
        return jsonify({
            'code': 200,
            'data': {'products': product_list}
        }), 200
    except Exception as e:
        logger.error(f'获取产品列表失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'查询失败: {str(e)}'}), 500


@bp.route('/product-chemicals/<int:product_id>', methods=['GET'])
def get_product_chemicals(product_id):
    """根据产品ID获取产品信息及关联的化学物质（含图谱数据）"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'code': 404, 'message': '产品不存在'}), 404

        # 查询产品关联的化学物质
        relations = db.session.query(AllergenProduct, Allergen).join(
            Allergen, AllergenProduct.allergen_id == Allergen.id
        ).filter(
            AllergenProduct.product_id == product.id
        ).all()

        chemicals = []
        graph_nodes = [{
            'id': f'product_{product.id}',
            'label': product.name,
            'type': 'product',
            'data': {'name': product.name}
        }]
        graph_edges = []

        for rel, allergen in relations:
            chemicals.append({
                'id': allergen.id,
                'name': allergen.name,
                'cas_number': allergen.cas_number,
                'exposure_score': rel.exposure_score,
                'relation_id': rel.id
            })
            graph_nodes.append({
                'id': f'allergen_{allergen.id}',
                'label': allergen.name + (f'\nCAS: {allergen.cas_number}' if allergen.cas_number else ''),
                'type': 'allergen',
                'data': {'name': allergen.name, 'cas_number': allergen.cas_number}
            })
            graph_edges.append({
                'source': f'product_{product.id}',
                'target': f'allergen_{allergen.id}',
                'label': '含有',
                'type': 'contains'
            })

        return jsonify({
            'code': 200,
            'data': {
                'product': {'id': product.id, 'name': product.name},
                'chemicals': chemicals,
                'graph_data': {'nodes': graph_nodes, 'edges': graph_edges}
            }
        }), 200

    except Exception as e:
        logger.error(f'搜索产品化学物质失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'查询失败: {str(e)}'}), 500


@bp.route('/product-symptoms', methods=['GET'])
def get_product_symptoms():
    """根据产品ID获取关联的不良反应列表（用于选择框）"""
    try:
        product_id = request.args.get('product_id', type=int)
        if not product_id:
            return jsonify({'code': 400, 'message': '缺少product_id参数'}), 400

        # 查询产品关联的不良反应（通过ProductSymptom表）
        relations = db.session.query(ProductSymptom, Symptom2).join(
            Symptom2, ProductSymptom.symptom_id == Symptom2.id
        ).filter(
            ProductSymptom.product_id == product_id
        ).all()

        symptoms = []
        for rel, symptom in relations:
            symptoms.append({
                'id': symptom.id,
                'name': symptom.symptom_name,
                'confidence': rel.confidence
            })

        return jsonify({
            'code': 200,
            'data': {'symptoms': symptoms}
        }), 200

    except Exception as e:
        logger.error(f'获取产品不良反应失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'查询失败: {str(e)}'}), 500


@bp.route('/identify', methods=['POST'])
def hazard_identify():
    """危害识别：根据产品和不良反应计算风险评分
    
    算法：
    1. 集合A = 产品关联的化学应激源（通过AllergenProduct）
    2. 集合B = 不良反应关联的化学物质（通过AllergenSymptom）
    3. 交集 = A ∩ B
    4. 对每个交集中的化学物质计算三个维度分数并相乘
    """
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        symptom_id = data.get('symptom_id')

        if not product_id or not symptom_id:
            return jsonify({'code': 400, 'message': '缺少product_id或symptom_id'}), 400

        product = db.session.get(Product, product_id)
        symptom = db.session.get(Symptom2, symptom_id)
        if not product:
            return jsonify({'code': 404, 'message': '产品不存在'}), 404
        if not symptom:
            return jsonify({'code': 404, 'message': '不良反应不存在'}), 404

        # 集合A：产品 -> 化学应激源
        set_a = db.session.query(AllergenProduct, Allergen).join(
            Allergen, AllergenProduct.allergen_id == Allergen.id
        ).filter(
            AllergenProduct.product_id == product_id
        ).all()
        set_a_dict = {allergen.id: (rel, allergen) for rel, allergen in set_a}

        # 集合B：不良反应 -> 化学物质
        set_b = db.session.query(AllergenSymptom, Allergen).join(
            Allergen, AllergenSymptom.allergen_id == Allergen.id
        ).filter(
            AllergenSymptom.symptom_id == symptom_id
        ).all()
        set_b_dict = {allergen.id: (rel, allergen) for rel, allergen in set_b}

        # 取交集
        intersection_ids = set(set_a_dict.keys()) & set(set_b_dict.keys())

        # 计算事件信号（PRR和卡方值）
        calculator = EventSignalCalculator(db.session)
        signal_result = calculator.calculate_event_signal(product_id, symptom_id)
        signal_score = signal_result.get('signal_score', 1)
        signal_label = signal_result.get('signal_label', '弱事件信号')

        # 评分函数
        def exposure_level(score):
            if score is None:
                return 1
            if score >= 16:
                return 3
            elif score >= 10:
                return 2
            else:
                return 1

        def traec_level(score):
            if score is None:
                return 1
            if score >= 8:
                return 3
            elif score >= 4:
                return 2
            else:
                return 1

        def event_signal_level(score):
            """事件信号等级已由EventSignalCalculator直接给出，此处直接返回"""
            if score is None:
                return 1
            return score

        def risk_label(total):
            if total >= 18:
                return '高风险'
            elif total >= 8:
                return '中风险'
            else:
                return '低风险'

        results = []
        graph_nodes = [
            {
                'id': f'product_{product.id}',
                'label': product.name,
                'type': 'product',
                'data': {'name': product.name}
            },
            {
                'id': f'symptom_{symptom.id}',
                'label': symptom.symptom_name,
                'type': 'symptom',
                'data': {'name': symptom.symptom_name}
            }
        ]
        graph_edges = []
        
        # 添加产品 -> 不良反应的边（只添加一次）
        graph_edges.append({
            'source': f'product_{product.id}',
            'target': f'symptom_{symptom.id}',
            'label': f'{signal_label}({signal_score}分)',
            'type': 'related'
        })

        for allergen_id in intersection_ids:
            ap_rel, allergen = set_a_dict[allergen_id]
            as_rel, _ = set_b_dict[allergen_id]

            exp_score = ap_rel.exposure_score or 0
            traec_score = as_rel.traec_score or 0

            s1 = exposure_level(exp_score)
            s2 = traec_level(traec_score)
            s3 = event_signal_level(signal_score)
            total = s1 * s2 * s3
            label = risk_label(total)

            results.append({
                'allergen_id': allergen.id,
                'allergen_name': allergen.name,
                'cas_number': allergen.cas_number,
                'exposure_score': exp_score,
                'exposure_level': s1,
                'traec_score': traec_score,
                'traec_level': s2,
                'signal_score': signal_score,
                'signal_level': s3,
                'signal_label': signal_label,
                'total_score': total,
                'risk_label': label
            })

            # 构建图谱节点和边
            node_id = f'allergen_{allergen.id}'
            graph_nodes.append({
                'id': node_id,
                'label': f'{allergen.name}\n风险: {label}({total}分)',
                'type': 'allergen',
                'data': {
                    'name': allergen.name,
                    'cas_number': allergen.cas_number,
                    'risk_label': label,
                    'total_score': total
                }
            })
            # 不良反应 -> 化学应激源
            graph_edges.append({
                'source': f'symptom_{symptom.id}',
                'target': node_id,
                'label': f'TRAEC({traec_score:.1f})',
                'type': 'causes'
            })

        # 按总分降序排列
        results.sort(key=lambda x: x['total_score'], reverse=True)

        return jsonify({
            'code': 200,
            'data': {
                'product': {'id': product.id, 'name': product.name},
                'symptom': {'id': symptom.id, 'name': symptom.symptom_name},
                'event_signal': {
                    'PRR': signal_result.get('PRR'),
                    'chi_square': signal_result.get('chi_square'),
                    'score': signal_score,
                    'label': signal_label,
                    'contingency_table': signal_result.get('contingency_table', {})
                },
                'combinations': results,
                'graph_data': {'nodes': graph_nodes, 'edges': graph_edges}
            }
        }), 200

    except Exception as e:
        logger.error(f'危害识别失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'危害识别失败: {str(e)}'}), 500


@bp.route('/literature-scores/<int:symptom_id>', methods=['GET'])
def get_literature_scores(symptom_id):
    """获取症状相关文献的详细评分数据
    
    Args:
        symptom_id: 症状ID
    
    Returns:
        包含文献详细评分的JSON响应
    """
    try:
        from ..models import Literature, LiteratureEpiScoring, LiteratureVivoScoring, LiteratureVitroScoring, AllergenSymptomSource, AllergenSymptom
        
        # 先查询症状相关的文献ID列表
        literature_ids = db.session.query(
            Literature.id
        ).join(
            AllergenSymptomSource, Literature.id == AllergenSymptomSource.literature_id
        ).join(
            AllergenSymptom, AllergenSymptomSource.allergen_symptom_id == AllergenSymptom.id
        ).filter(
            AllergenSymptom.symptom_id == symptom_id
        ).all()
        
        if not literature_ids:
            return jsonify({
                'code': 404,
                'message': '未找到该症状的相关文献'
            }), 404
        
        literature_id_list = [lit.id for lit in literature_ids]
        
        # 查询文献基本信息
        literatures = db.session.query(Literature).filter(
            Literature.id.in_(literature_id_list)
        ).all()
        
        literature_list = []
        for lit in literatures:
            
            # 查询流行病学评分
            epi_score = db.session.query(LiteratureEpiScoring).filter(
                LiteratureEpiScoring.literature_id == lit.id
            ).first()
            
            # 查询体内实验评分
            vivo_score = db.session.query(LiteratureVivoScoring).filter(
                LiteratureVivoScoring.literature_id == lit.id
            ).first()
            
            # 查询体外实验评分
            vitro_score = db.session.query(LiteratureVitroScoring).filter(
                LiteratureVitroScoring.literature_id == lit.id
            ).first()
            
            # 安全转换函数
            def safe_float_convert(value):
                if value is None:
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    if isinstance(value, str):
                        if value in ['-1', '0', '1']:
                            return float(value)
                        elif value in ['0.4', '0.8', '1']:
                            return float(value)
                    return 0.0
            
            # 获取评分数据（优先级：流行病学 > 体内实验 > 体外实验）
            reliability = 0.0
            correlation = 0.0
            risk_intensity = 0.0
            concentration_weight = 0.0
            
            if epi_score:
                reliability = safe_float_convert(epi_score.reliability_total_score)
                correlation = safe_float_convert(epi_score.correlation_score)
                risk_intensity = safe_float_convert(epi_score.risk_intensity_score)
                concentration_weight = safe_float_convert(epi_score.concentration_weight)
            elif vivo_score:
                reliability = safe_float_convert(vivo_score.reliability_total_score)
                correlation = safe_float_convert(vivo_score.correlation_score)
                risk_intensity = safe_float_convert(vivo_score.risk_intensity_score)
                concentration_weight = safe_float_convert(vivo_score.concentration_weight)
            elif vitro_score:
                reliability = safe_float_convert(vitro_score.reliability_total_score)
                correlation = safe_float_convert(vitro_score.correlation_score)
                risk_intensity = safe_float_convert(vitro_score.risk_intensity_score)
                concentration_weight = safe_float_convert(vitro_score.concentration_weight)
            else:
                print(f"  未找到任何评分数据")
            
            literature_data = {
                'id': lit.id,
                'title': lit.title,
                'authors': lit.authors,
                'source': lit.source,
                'publish_date': lit.publish_date.strftime('%Y-%m-%d') if lit.publish_date else None,
                'pmid': lit.pmid,
                'link': lit.link,
                'reliability': reliability,
                'relevance': correlation,
                'risk_intensity': risk_intensity,
                'concentration_weight': concentration_weight,
                'evidence_strength': (reliability + abs(correlation) + risk_intensity) / 3 if (reliability + abs(correlation) + risk_intensity) > 0 else 0
            }
            literature_list.append(literature_data)
        
        return jsonify({
            'code': 200,
            'data': literature_list,
            'message': f'成功获取{len(literature_list)}篇文献的评分数据'
        })
        
    except Exception as e:
        print(f'获取文献评分失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'code': 500,
            'message': f'获取文献评分失败: {str(e)}'
        }), 500
