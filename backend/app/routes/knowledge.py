from __future__ import annotations

from flask import Blueprint, request, jsonify

from app.services.graph_repository import (
    query_neighbors_by_id,
    query_neighbors_by_id_smart,
    search_nodes,
)
from app.services.qa.answer import build_qa_answer
from app.services.graph_view import (
    get_category_menus,
    get_category_types,
    get_category_products,
    get_category_allergens,
    get_type_products,
    get_product_recalls,
    get_product_news,
    get_allergen_symptoms,
    get_allergen_literature,
)

from ..models import db, Allergen, AllergenSymptom, Symptom2, Symptom3, Literature, AllergenSymptomSource
import logging

bp = Blueprint('knowledge', __name__)
@bp.post('/translate')
def translate_generic():
    """通用服务：将任意 texts 翻译为指定语言，默认 zh-CN。
    body: { texts: string[], to?: string }
    返回: { items: string[] }
    """
    body = request.get_json(silent=True) or {}
    texts = body.get('texts') or []
    to = (body.get('to') or 'zh-CN').strip() or 'zh-CN'
    if not isinstance(texts, list) or not texts:
        return jsonify({'items': []})
    try:
        from ..services.translator import ensure_async_translations_and_get_cached
        norm = [str(t or '') for t in texts]
        # 非阻塞：立即返回缓存命中，并将缺失项投递后台
        res = ensure_async_translations_and_get_cached(norm, 'auto', to)
        return jsonify({'items': res})
    except Exception:
        # 任何异常都不阻塞显示，直接返回原文
        return jsonify({'items': texts})



@bp.post('/qa')
def qa():
    data = request.get_json(silent=True) or {}
    q = str(data.get('question', '') or '').strip()
    session_id = data.get('sessionId')
    print(f"Question: {q}")
    print(f"Session ID: {session_id}")
    result = build_qa_answer(q, session_id=session_id)
    return jsonify(result)


@bp.get('/node/<node_id>/neighbors')
def neighbors(node_id: str):
    limit = int(request.args.get('limit', 200))
    per_node = int(request.args.get('perNode', 30))
    types = request.args.get('types')
    type_list = [t for t in (types.split(',') if types else []) if t]
    smart = request.args.get('smart', 'false').lower() == 'true'
    fallback_name = request.args.get('name')

    try:
        if smart:
            data = query_neighbors_by_id_smart(node_id, limit=limit, per_node=per_node, types=type_list or None)
        else:
            data = query_neighbors_by_id(node_id, limit=limit, per_node=per_node, types=type_list or None)
    except Exception:
        data = { 'nodes': [], 'edges': [] }

    if (not data.get('nodes')) and fallback_name:
        try:
            candidates = search_nodes(fallback_name, label='类别', limit=10, mode='auto', synonyms=True)
            for cand in (candidates or []):
                try:
                    cand_id = cand.get('id')
                    if not cand_id:
                        continue
                    got = query_neighbors_by_id(cand_id, limit=limit, per_node=per_node, types=type_list or None)
                    if got.get('nodes'):
                        data = got
                        break
                except Exception:
                    continue
            if not data.get('nodes'):
                candidates2 = search_nodes(fallback_name, label=None, limit=10, mode='auto', synonyms=True)
                for cand in (candidates2 or []):
                    try:
                        cand_id = cand.get('id')
                        if not cand_id:
                            continue
                        got = query_neighbors_by_id(cand_id, limit=limit, per_node=per_node, types=type_list or None)
                        if got.get('nodes'):
                            data = got
                            break
                    except Exception:
                        continue
        except Exception:
            pass
    return jsonify(data)


@bp.get('/search')
def search():
    q = request.args.get('q', '')
    label = request.args.get('label')
    mode = request.args.get('mode', 'auto')
    limit = int(request.args.get('limit', 20))
    synonyms = request.args.get('synonyms', 'false').lower() == 'true'
    if not q:
        return jsonify([])
    try:
        data = search_nodes(q, label=label, limit=limit, mode=mode, synonyms=synonyms)
    except Exception:
        data = []
    return jsonify(data)


# 虚拟视图 API 端点
# 已修改
@bp.get('/category/<product_1_id>/menus')
def get_category(product_1_id: str):
    """获取类别的菜单节点：产品/过敏原"""
    try:
        data = get_category_menus(product_1_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.post('/edges/product-allergen')
def product_allergen_edges():
    """返回给定产品elementId与过敏原elementId集合之间的"产品-包含过敏原->过敏原"边。

    请求体(JSON): { "productIds": [elementId...], "allergenIds": [elementId...] }
    响应: [ { from: elementId(p), to: elementId(a), type: '包含过敏原' } ]
    """
    try:
        data = request.get_json(silent=True) or {}
        product_ids = data.get('productIds') or []
        allergen_ids = data.get('allergenIds') or []
        # 兼容以名称匹配，避免由于elementId不一致导致无法命中
        product_names = data.get('productNames') or []
        allergen_names = data.get('allergenNames') or []
        if not product_ids or not allergen_ids:
            # 若ID缺失但传了名称，也允许仅按名称匹配
            if not product_names or not allergen_names:
                return jsonify([])

        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        cypher = (
            """
            MATCH (p:产品)-[r:判断]->(opinion:观点)-[r2:包含]->(allergen:化学应急源)
            WHERE (
                (size($productIds) > 0 AND elementId(p) IN $productIds) OR
                (size($productNames) > 0 AND toString(p.name) IN $productNames)
            )
            AND (
                (size($allergenIds) > 0 AND elementId(allergen) IN $allergenIds) OR
                (size($allergenNames) > 0 AND toString(allergen.name) IN $allergenNames)
            )
            RETURN elementId(p) AS src, elementId(allergen) AS dst, '包含过敏原' AS type
            """
        )
        edges = []
        with driver.session() as session:
            result = session.run(
                cypher,
                productIds=product_ids,
                allergenIds=allergen_ids,
                productNames=product_names,
                allergenNames=allergen_names,
            )
            for rec in result:
                edges.append({ 'from': rec['src'], 'to': rec['dst'], 'type': rec['type'] })
        return jsonify(edges)
    except Exception as e:
        return jsonify([]), 500


@bp.get('/category/<category_id>/products')
def category_products(category_id: str):
    """获取类别的产品列表（4条+更多）"""
    limit = int(request.args.get('limit', 5))
    try:
        data = get_category_products(category_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'meta': {'hasMore': False}, 'error': str(e)}), 500


@bp.get('/category/<category_id>/types')
def category_types(category_id: str):
    """获取种类下的类型(Type)节点"""
    try:
        data = get_category_types(category_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.get('/category/<category_id>/allergens')
def category_allergens(category_id: str):
    """获取类别的过敏原列表（4条+更多）"""
    limit = int(request.args.get('limit', 4))
    try:
        data = get_category_allergens(category_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'meta': {'hasMore': False}, 'error': str(e)}), 500


@bp.get('/category/<category_id>/products/all')
def category_products_all(category_id: str):
    """获取类别的所有产品列表（用于更多按钮）"""
    try:
        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        
        with driver.session() as session:
            cypher = """
            MATCH (c:类别 {id: $categoryId})-[:包含产品]->(p:产品)
            RETURN p.name as name, elementId(p) as id, 'Product' as entityType
            ORDER BY p.name ASC
            LIMIT 100
            """
            result = session.run(cypher, categoryId=int(category_id))
            products = []
            for record in result:
                products.append({
                    'id': record['id'],
                    'name': record['name'],
                    'entityType': record['entityType']
                })
            
            return jsonify(products)
    except Exception as e:
        return jsonify([]), 500


@bp.get('/category/<category_id>/allergens/all')
def category_allergens_all(category_id: str):
    """获取类别的所有化学应急源列表（用于更多按钮），排除已展示的前4个"""
    try:
        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        
        with driver.session() as session:
            # 首先获取前4个已展示的化学应急源的elementId（使用相同的查询逻辑）
            shown_cypher = """
            MATCH (c:种类 {id: $categoryId})-[:包含]->(t:类型)-[:包含]->(p:产品)-[:判断]->(v:观点)-[:包含]->(a:化学应急源)
            WITH a, collect(DISTINCT p) AS products
            OPTIONAL MATCH (a)<-[:包含]-(v2:观点)<-[:判断]-(s)
            WHERE ANY(label IN labels(s) WHERE label CONTAINS '症状')
            WITH a, products, collect(DISTINCT s) AS symptoms
            WITH a, 
                 size(products) AS productCount,
                 size(symptoms) AS symptomsCount
            ORDER BY a.name ASC
            LIMIT 4
            RETURN collect(elementId(a)) as shownIds
            """
            shown_result = session.run(shown_cypher, categoryId=category_id)
            shown_record = shown_result.single()
            shown_ids = shown_record['shownIds'] if shown_record else []
            
            # 获取所有化学应急源，但排除已展示的前4个
            all_cypher = """
            MATCH (c:种类 {id: $categoryId})-[:包含]->(t:类型)-[:包含]->(p:产品)-[:判断]->(v:观点)-[:包含]->(a:化学应急源)
            WHERE NOT elementId(a) IN $shownIds
            RETURN DISTINCT a.name as name, elementId(a) as id, 'Allergen' as entityType
            ORDER BY a.name ASC
            LIMIT 100
            """
            result = session.run(all_cypher, categoryId=category_id, shownIds=shown_ids)
            allergens = []
            for record in result:
                allergens.append({
                    'id': record['id'],
                    'name': record['name'],
                    'entityType': record['entityType']
                })
            
            return jsonify(allergens)
    except Exception as e:
        return jsonify([]), 500


@bp.get('/product/<product_id>/recalls')
def product_recalls(product_id: str):
    """获取产品的召回叶子节点"""
    limit = int(request.args.get('limit', 4))
    try:
        data = get_product_recalls(product_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.get('/product/<product_id>/news')
def product_news(product_id: str):
    """获取产品的新闻叶子节点"""
    limit = int(request.args.get('limit', 4))
    try:
        data = get_product_news(product_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.get('/allergen/<allergen_id>/product-symptom-evidence')
def allergen_product_symptom_evidence(allergen_id: str):
    """获取某化学应急源包含的产品列表和症状列表（用于过敏原弹窗单表展示）"""
    try:
        from app.services.graph_view import get_allergen_products_and_symptoms
        data = get_allergen_products_and_symptoms(allergen_id)
        return jsonify(data)
    except Exception as e:
        print(f"Error in allergen_product_symptom_evidence: {e}")
        return jsonify({'error': str(e), 'debug': 'Check server logs'}), 500


@bp.get('/allergen/<allergen_id>/symptoms')
def allergen_symptoms(allergen_id: str):
    """获取过敏原的症状叶子节点"""
    limit = int(request.args.get('limit', 4))
    try:
        data = get_allergen_symptoms(allergen_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.get('/allergen/<allergen_id>/literature')
def allergen_literature(allergen_id: str):
    """获取过敏原的文献叶子节点"""
    limit = int(request.args.get('limit', 4))
    try:
        data = get_allergen_literature(allergen_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.get('/type/<type_id>/products')
def type_products(type_id: str):
    """获取类型下的产品（附新闻/召回数量）"""
    limit = int(request.args.get('limit', 50))
    try:
        data = get_type_products(type_id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'nodes': [], 'edges': [], 'error': str(e)}), 500


@bp.get('/allergen/<allergen_id>/symptoms/all')
def allergen_symptoms_all(allergen_id: str):
    """获取过敏原的所有症状列表及相关产品、文献（混合查询 Neo4j + MySQL）"""
    try:
        from app.services.neo4j_client import Neo4jClient
        import psycopg
        from psycopg.rows import dict_row
        from flask import current_app
        
        driver = Neo4jClient.get_driver()
        
        # 1. 从 Neo4j 获取过敏原信息和相关产品
        with driver.session() as session:
            # 通过 elementId 或 MySQL id 查询过敏原
            allergen_query = """
            MATCH (a:过敏原)
            WHERE elementId(a) = $allergenId OR toString(a.id) = $allergenId OR a.name = $allergenId
            RETURN a.name as name, a.id as mysql_id, elementId(a) as elementId
            """
            allergen_result = session.run(allergen_query, allergenId=allergen_id)
            allergen_record = allergen_result.single()
            
            if not allergen_record:
                return jsonify({'error': '过敏原不存在'}), 404
            
            allergen_name = allergen_record['name']
            mysql_allergen_id = allergen_record['mysql_id']
            
            # 查询包含该过敏原的产品
            products_query = """
            MATCH (p:产品)-[:包含过敏原]->(a:过敏原)
            WHERE elementId(a) = $allergenId
            RETURN p.name as name, p.id as id, elementId(p) as elementId
            ORDER BY p.name ASC
            """
            products_result = session.run(products_query, allergenId=allergen_record['elementId'])
            products = []
            for record in products_result:
                products.append({
                    'id': str(record['id']) if record['id'] else record['elementId'],
                    'name': record['name'],
                    'entityType': 'Product',
                    'elementId': record['elementId']
                })
        
        # 2. 从 PostgreSQL 获取症状和文献信息
        conn = psycopg.connect(
            host=current_app.config.get('POSTGRES_HOST', '127.0.0.1'),
            port=current_app.config.get('POSTGRES_PORT', 5432),
            user=current_app.config.get('POSTGRES_USER', 'postgres'),
            password=current_app.config.get('POSTGRES_PASSWORD', ''),
            dbname=current_app.config.get('POSTGRES_DB', 'medical_system')
        )

        try:
            cursor = conn.cursor(row_factory=dict_row)

            # 查询过敏原的症状及其文献证据
            symptoms_query = """
            SELECT
                s.id AS symptom_id,
                s.symptom_name AS symptom_name,
                l.id AS literature_id,
                l.title AS literature_title,
                l.link AS literature_url
            FROM allergen_symptom ass
            JOIN symptom_2 s ON ass.symptom_id = s.id
            LEFT JOIN allergen_symptom_source ass2 ON ass2.allergen_symptom_id = ass.id
            LEFT JOIN literature l ON ass2.literature_id = l.id
            WHERE ass.allergen_id = %s
            ORDER BY s.symptom_name, l.id
            """

            cursor.execute(symptoms_query, (mysql_allergen_id,))
            symptoms_data = cursor.fetchall()

            # 组织症状数据（按症状聚合文献）
            symptoms_map = {}
            for row in symptoms_data:
                sid = row['symptom_id']
                if sid not in symptoms_map:
                    symptoms_map[sid] = {
                        'id': str(sid),
                        'name': row['symptom_name'],
                        'entityType': 'Symptom',
                        'literature': []
                    }
                if row['literature_id'] is not None:
                    symptoms_map[sid]['literature'].append({
                        'id': str(row['literature_id']),
                        'title': row['literature_title'] or '',
                        'url': row['literature_url'] or '',
                        'entityType': 'Literature'
                    })

            symptoms = []
            for symptom in symptoms_map.values():
                symptom['evidenceCount'] = len(symptom['literature'])
                symptoms.append(symptom)

        finally:
            conn.close()
        
        # 3. 返回完整数据：过敏原 -> 产品列表 + 症状列表（含文献）
        response = {
            'allergen': {
                'id': allergen_record['elementId'],
                'mysql_id': mysql_allergen_id,
                'name': allergen_name,
                'entityType': 'Allergen'
            },
            'products': products,
            'symptoms': symptoms,
            'summary': {
                'productCount': len(products),
                'symptomCount': len(symptoms),
                'totalLiterature': sum(len(s.get('literature', [])) for s in symptoms)
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.get('/allergen/<allergen_id>/literature/all')
def allergen_literature_all(allergen_id: str):
    """获取过敏原的所有文献列表（用于更多按钮）"""
    try:
        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        
        with driver.session() as session:
            cypher = """
            MATCH (a:过敏原)-[r]->(l:文献)
            WHERE elementId(a) = $allergenId OR a.name = $allergenId OR toString(a.id) = $allergenId
            RETURN l.title as name, toString(l.id) as id, 'Literature' as entityType, l.url as url
            ORDER BY coalesce(l.year,0) DESC, l.title ASC
            LIMIT 100
            """
            result = session.run(cypher, allergenId=allergen_id)
            literature = []
            for record in result:
                literature.append({
                    'id': record['id'],
                    'name': record['name'],
                    'entityType': record['entityType'],
                    'url': record.get('url')
                })
            
            return jsonify(literature)
    except Exception as e:
        return jsonify([]), 500


@bp.get('/product/<product_id>/recalls/all')
def product_recalls_all(product_id: str):
    """获取产品的所有召回列表（用于更多按钮）"""
    try:
        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        
        with driver.session() as session:
            # 先通过elementId找到产品名称
            product_query = """
            MATCH (p:产品) WHERE elementId(p) = $productId RETURN p.name as name
            """
            product_result = session.run(product_query, productId=product_id)
            product_record = product_result.single()
            if not product_record:
                return jsonify([]), 404
            
            product_name = product_record['name']
            cypher = """
            MATCH (p:产品 {name: $productName})-[:有召回]->(r:召回)
            RETURN r.title as title, toString(r.id) as id, 'Recall' as entityType, r.url as url,
                   r.time as publishDate, r.source as source
            ORDER BY coalesce(r.time, datetime('1970-01-01')) DESC
            LIMIT 100
            """
            result = session.run(cypher, productName=product_name)
            recalls = []
            for record in result:
                # 安全处理日期格式化
                publish_date = None
                if record['publishDate']:
                    try:
                        # 尝试不同的日期处理方法
                        date_obj = record['publishDate']
                        if hasattr(date_obj, 'to_native'):
                            publish_date = date_obj.to_native().strftime('%Y-%m-%d')
                        elif hasattr(date_obj, 'strftime'):
                            publish_date = date_obj.strftime('%Y-%m-%d')
                        elif hasattr(date_obj, 'iso_format'):
                            publish_date = date_obj.iso_format()[:10]
                        else:
                            publish_date = str(date_obj)[:10]
                    except Exception as e:
                        print(f"Date formatting error: {e}, date_obj: {record['publishDate']}, type: {type(record['publishDate'])}")
                        publish_date = None
                
                recalls.append({
                    'id': f"recall_{record['id']}",  # 添加前缀避免与新闻ID冲突
                    'title': record['title'],
                    'entityType': record['entityType'],
                    'url': record.get('url'),
                    'source': record.get('source') or '召回公告',
                    'publishDate': publish_date
                })
            
            return jsonify(recalls)
    except Exception as e:
        print(f"Error in product_recalls_all: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500


@bp.get('/product/<product_id>/news/all')
def product_news_all(product_id: str):
    """获取产品的所有新闻列表（用于更多按钮）- 从MySQL查询"""
    try:
        from app.models import db, ProductSymptom, ProductSymptomNews, News
        from app.services.neo4j_client import Neo4jClient
        
        # 先通过Neo4j的elementId找到产品的业务ID
        driver = Neo4jClient.get_driver()
        with driver.session() as session:
            product_query = """
            MATCH (p:产品) WHERE elementId(p) = $productId RETURN p.id as business_id
            """
            product_result = session.run(product_query, productId=product_id)
            product_record = product_result.single()
            if not product_record:
                return jsonify([])
            
            business_id = str(product_record['business_id'])
        
        # 通过ProductSymptom和ProductSymptomNews获取去重的新闻ID
        news_ids_query = db.session.query(ProductSymptomNews.news_id).distinct().join(
            ProductSymptom, ProductSymptom.id == ProductSymptomNews.product_symptom_id
        ).filter(
            ProductSymptom.product_id == business_id,
            ProductSymptomNews.news_id.isnot(None)
        )
        
        news_ids = [row.news_id for row in news_ids_query.all()]
        
        if not news_ids:
            return jsonify([])
        
        # 通过News表获取新闻详细信息
        # 使用case_when来处理NULL值，确保MySQL兼容性
        from sqlalchemy import case
        news_list = db.session.query(News).filter(News.id.in_(news_ids)).order_by(
            case(
                (News.publish_time.is_(None), 0),
                else_=1
            ).desc(),
            News.publish_time.desc()
        ).all()
        
        news = []
        for news_item in news_list:
            # 安全处理日期格式化
            publish_date = None
            if news_item.publish_time:
                try:
                    publish_date = news_item.publish_time.strftime('%Y-%m-%d')
                except Exception as e:
                    print(f"Date formatting error: {e}")
                    publish_date = None
            
            news.append({
                'id': f"news_{news_item.id}",  # 添加前缀避免与召回ID冲突
                'title': news_item.title,
                'entityType': 'News',
                'url': news_item.link,
                'source': news_item.source or '新闻',
                'publishDate': publish_date
            })
        
        return jsonify(news)
    except Exception as e:
        print(f"Error in product_news_all: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500


@bp.get('/symptom/<symptom_name>/literature/all')
def symptom_literature_all(symptom_name: str):
    """获取症状的所有相关文献列表（用于症状查看按钮）"""
    try:
        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        
        with driver.session() as session:
            cypher = """
            MATCH (s:症状3 {name: $symptomName})-[:有证明]->(prof:文献证明)-[:依据文献]->(l:文献)
            RETURN l.title as name, toString(l.id) as id, 'Literature' as entityType,
                   l.url as url,
                   prof.confidence as confidence, prof.source as source, prof.notes as notes
            ORDER BY coalesce(prof.confidence, 0) DESC, l.title ASC
            LIMIT 100
            """
            result = session.run(cypher, symptomName=symptom_name)
            literature = []
            for record in result:
                literature.append({
                    'id': record['id'],
                    'name': record['name'],
                    'entityType': record['entityType'],
                    'url': record.get('url'),
                    'confidence': record.get('confidence'),
                    'source': record.get('source'),
                    'notes': record.get('notes')
                })
            
            return jsonify(literature)
    except Exception as e:
        return jsonify([]), 500


@bp.post('/hazard-assessment')
def hazard_assessment():
    """危害评估功能：根据化学物质名称或CAS号查找风险评估信息"""
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json(silent=True) or {}
        query_input = str(data.get('input', '') or '').strip()
        
        if not query_input:
            return jsonify({
                'success': False,
                'message': '请输入化学物质名称或CAS号'
            }), 400
        
        logger.info(f'危害评估查询: {query_input}')
        
        # 1. 通过知识图谱查找化学物质
        allergen_info = _search_allergen_in_graph(query_input)
        if not allergen_info:
            return jsonify({
                'success': False,
                'message': '未找到相关的化学物质信息'
            }), 404
        
        # 2. 查找该化学物质与不良反应的关联对
        risk_pairs = _get_allergen_symptom_pairs(allergen_info['id'], allergen_info['name'])
        
        # 3. 获取TRAEC评分和佐证文献
        assessment_results = []
        for pair in risk_pairs:
            traec_score = pair.get('traec_score', 0.0)
            literature = _get_supporting_literature(pair['allergen_id'], pair['symptom_id'])
            
            assessment_results.append({
                'allergen_name': pair['allergen_name'],
                'symptom_name': pair['symptom_name'],
                'traec_score': traec_score,
                'risk_level': _get_risk_level(traec_score),
                'literature_count': len(literature),
                'supporting_literature': literature[:5]  # 只返回前5篇文献
            })
        
        # 按TRAEC评分降序排列
        assessment_results.sort(key=lambda x: x['traec_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'allergen_info': allergen_info,
                'assessment_results': assessment_results,
                'total_pairs': len(assessment_results)
            }
        })
        
    except Exception as e:
        logger.error(f'危害评估失败: {e}')
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


def _search_allergen_in_graph(query_input):
    """在知识图谱中搜索化学物质"""
    try:
        from app.services.neo4j_client import Neo4jClient
        driver = Neo4jClient.get_driver()
        
        with driver.session() as session:
            # 搜索化学物质节点，支持名称和CAS号
            cypher = """
            MATCH (a:过敏原)
            WHERE a.name CONTAINS $query OR a.cas_number = $query OR a.cas_number CONTAINS $query
            RETURN a.name as name, toString(a.id) as id, a.cas_number as cas_number
            LIMIT 1
            """
            result = session.run(cypher, query=query_input)
            record = result.single()
            
            if record:
                return {
                    'id': record['id'],
                    'name': record['name'],
                    'cas_number': record.get('cas_number')
                }
            
            return None
    except Exception as e:
        logging.getLogger(__name__).error(f'知识图谱搜索失败: {e}')
        return None


def _get_allergen_symptom_pairs(graph_allergen_id, allergen_name):
    """获取化学物质与不良反应的关联对"""
    try:
        # 首先在MySQL中查找对应的过敏原
        allergen = Allergen.query.filter_by(name=allergen_name).first()
        if not allergen:
            return []
        
        # 查询该过敏原的所有症状关联
        pairs = db.session.query(AllergenSymptom, Symptom2).join(
            Symptom2, AllergenSymptom.symptom_id == Symptom2.id
        ).filter(
            AllergenSymptom.allergen_id == allergen.id
        ).all()
        
        result = []
        for allergen_symptom, symptom in pairs:
            result.append({
                'allergen_id': allergen.id,
                'allergen_name': allergen.name,
                'symptom_id': symptom.id,
                'symptom_name': symptom.symptom_name,
                'traec_score': allergen_symptom.traec_score or 0.0
            })
        
        return result
    except Exception as e:
        logging.getLogger(__name__).error(f'获取关联对失败: {e}')
        return []


def _get_supporting_literature(allergen_id, symptom_id):
    """获取佐证文献"""
    try:
        # 查找该过敏原-症状关联的文献
        allergen_symptom = AllergenSymptom.query.filter_by(
            allergen_id=allergen_id,
            symptom_id=symptom_id
        ).first()
        
        if not allergen_symptom:
            return []
        
        # 查询关联的文献
        literature_sources = db.session.query(AllergenSymptomSource, Literature).join(
            Literature, AllergenSymptomSource.literature_id == Literature.id
        ).filter(
            AllergenSymptomSource.allergen_symptom_id == allergen_symptom.id
        ).all()
        
        result = []
        for source, literature in literature_sources:
            result.append({
                'id': literature.id,
                'title': literature.title,
                'authors': literature.authors,
                'source': literature.source,
                'pmid': literature.pmid,
                'publish_date': literature.publish_date.isoformat() if literature.publish_date else None,
                'literature_type': literature.literature_type,
                'evidence_strength': float(source.evidence_strength) if source.evidence_strength else 1.0
            })
        
        # 按证据强度降序排列
        result.sort(key=lambda x: x['evidence_strength'], reverse=True)
        return result
        
    except Exception as e:
        logging.getLogger(__name__).error(f'获取佐证文献失败: {e}')
        return []


def _get_risk_level(traec_score):
    """根据TRAEC评分确定风险等级"""
    if traec_score >= 0.8:
        return {'level': 'high', 'label': '高风险', 'color': 'red'}
    elif traec_score >= 0.5:
        return {'level': 'medium', 'label': '中等风险', 'color': 'orange'}
    elif traec_score >= 0.2:
        return {'level': 'low', 'label': '低风险', 'color': 'yellow'}
    else:
        return {'level': 'minimal', 'label': '极低风险', 'color': 'green'}

