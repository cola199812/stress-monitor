from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import math
from .neo4j_client import Neo4jClient


def calculate_radial_positions(center_x: float, center_y: float, count: int, radius: float = 120) -> List[Tuple[float, float]]:
    """
    计算围绕中心点的径向位置
    
    Args:
        center_x: 中心点X坐标
        center_y: 中心点Y坐标
        count: 子节点数量
        radius: 径向距离
    
    Returns:
        [(x, y), ...] 位置列表
    """
    if count == 0:
        return []
    
    positions = []
    # 从顶部开始，顺时针分布
    start_angle = -math.pi / 2  # 从12点钟方向开始
    
    for i in range(count):
        if count == 1:
            # 单个节点放在正上方
            angle = start_angle
        else:
            # 多个节点均匀分布
            angle = start_angle + (2 * math.pi * i / count)
        
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions.append((x, y))
    
    return positions


def create_virtual_node(
    node_id: str, 
    name: str, 
    entity_type: str, 
    is_menu: bool = False,
    is_group: bool = False, 
    is_more: bool = False,
    url: Optional[str] = None,
    source: Optional[str] = None,
    publish_time: Optional[str] = None,
    time: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    fixed: bool = False
) -> Dict[str, Any]:
    """创建虚拟节点"""
    node = {
        'id': node_id,
        'label': entity_type,
        'name': name,
        'entityType': entity_type,
    }
    if is_menu:
        node['isMenu'] = True
    if is_group:
        node['isGroup'] = True
    if is_more:
        node['isMore'] = True
    if url:
        node['url'] = url
    if source:
        node['source'] = source
    if publish_time:
        node['publish_time'] = publish_time
        node['publishedAt'] = publish_time  # 添加统一字段
    if time:
        node['time'] = time
        node['publishedAt'] = time  # 添加统一字段
    if meta:
        node['meta'] = meta
    if x is not None:
        node['x'] = x
    if y is not None:
        node['y'] = y
    if fixed:
        node['fixed'] = fixed
    return node


def create_virtual_edge(from_id: str, to_id: str, edge_type: str) -> Dict[str, str]:
    """创建虚拟边"""
    return {
        'from': from_id,
        'to': to_id,
        'type': edge_type
    }

# 已修改
def get_category_menus(product_1_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """获取种类的菜单节点：主节点、过敏原节点、包含的所有类型节点"""
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 查询种类主节点信息
        category_query = """
        MATCH (c:种类 {id: $id}) 
        RETURN c.name AS name, elementId(c) AS elementId
        """
        category_result = session.run(category_query, id=str(product_1_id))
        category_record = category_result.single()
        
        if not category_record:
            return {'nodes': [], 'edges': []}
        
        category_name = category_record['name']
        
        # 查询种类包含的所有类型节点
        type_query = """
        MATCH (c:种类 {id: $id})-[:包含]->(t:类型)
        RETURN t.name AS name, elementId(t) AS elementId, t.id AS id
        ORDER BY t.name ASC
        """
        type_results = session.run(type_query, id=str(product_1_id))
        type_nodes = []
        for record in type_results:
            type_nodes.append({
                'name': record['name'],
                'elementId': record['elementId'],
                'id': record['id']
            })
    
    # 构造主节点（种类）
    category_node_id = f"category:{product_1_id}"
    category_node = create_virtual_node(
        category_node_id, category_name, "Category"
    )
    
    # 创建化学应急源（过敏原）菜单节点
    allergen_node_id = f"menu:category:{product_1_id}:allergens"
    allergen_node = create_virtual_node(
        allergen_node_id, "化学应急源", "Allergen", is_menu=True
    )
    
    nodes = [category_node, allergen_node]
    edges = []
    
    # 添加主节点到过敏原的边
    edges.append(create_virtual_edge(category_node_id, allergen_node_id, "HAS_MENU"))
    
    # 添加所有 Type 节点（作为真实节点显示在图中）
    for t in type_nodes:
        type_node_id = f"type:{t['elementId']}"
        type_node = create_virtual_node(
            type_node_id, t['name'], "Type", meta={ 'businessId': t['id'] }
        )
        nodes.append(type_node)
        edges.append(create_virtual_edge(category_node_id, type_node_id, "HAS_TYPE"))
    
    return {'nodes': nodes, 'edges': edges}


def get_category_types(category_id: str) -> Dict[str, Any]:
    """返回指定种类下的所有类型(Type)节点，连接到 Category 节点。"""
    driver = Neo4jClient.get_driver()
    with driver.session() as session:
        cypher = """
        MATCH (c:种类 {id: $categoryId})-[:包含]->(t:类型)
        RETURN t.name AS name, elementId(t) AS elementId, t.id AS id
        ORDER BY t.name ASC
        """
        result = session.run(cypher, categoryId=str(category_id))
        nodes = []
        edges = []
        category_node_id = f"category:{category_id}"
        for rec in result:
            type_node_id = f"type:{rec['elementId']}"
            nodes.append(create_virtual_node(type_node_id, rec['name'], 'Type', meta={ 'businessId': rec['id'] }))
            edges.append(create_virtual_edge(category_node_id, type_node_id, 'HAS_TYPE'))
        return { 'nodes': nodes, 'edges': edges }


def get_type_products(type_id: str, limit: int = 10) -> Dict[str, Any]:
    """返回某类型(Type)下的产品节点，边从 Type 节点指向产品节点。"""
    driver = Neo4jClient.get_driver()
    with driver.session() as session:
        cypher = """
        MATCH (t:类型)
        WHERE elementId(t) = $typeRef OR toString(t.id) = $typeRef
        WITH t, elementId(t) AS eid
        MATCH (t)-[:包含]->(p:产品)
        WITH eid, p
        ORDER BY coalesce(p.updated_at, datetime('1970-01-01')) DESC, p.name ASC
        LIMIT $limit
        RETURN eid AS typeElementId, p.name AS name, elementId(p) AS elementId, p.id AS id
        """
        result = session.run(cypher, typeRef=type_id, limit=limit)
        nodes = []
        edges = []
        for rec in result:
            product_node_id = f"product:{rec['elementId']}"
            type_node_id = f"type:{rec['typeElementId']}"
            nodes.append(create_virtual_node(
                product_node_id,
                rec['name'],
                'Product'
            ))
            edges.append(create_virtual_edge(type_node_id, product_node_id, 'HAS_PRODUCT'))
        return { 'nodes': nodes, 'edges': edges }


def get_category_products(category_id: str, limit: int = 5) -> Dict[str, Any]:
    """获取类别的产品列表（5条+更多）+ 同时展开分组节点"""
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 通过种类->类型->产品的路径查询
        cypher = """
        MATCH (c:种类 {id: $categoryId})-[:包含]->(t:类型)-[:包含]->(p:产品)
        WITH p
        ORDER BY coalesce(p.updated_at, datetime('1970-01-01')) DESC, p.name ASC
        LIMIT $limitPlusOne
        WITH collect({
            name: p.name, 
            elementId: elementId(p), 
            id: p.id,
            meta: { 
                debug: { 
                    hasId: p.id IS NOT NULL,
                    productName: p.name,
                    businessId: p.id,
                    elementId: elementId(p)
                }
            }
        }) AS products
        RETURN products[..$limit] AS items, size(products) > $limit AS hasMore
        """
        result = session.run(cypher, categoryId=str(category_id), limit=limit, limitPlusOne=limit+1)
        records = list(result)
        record = records[0] if records else None
        
        if not record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        products = record['items']
        has_more = record['hasMore']
        
        menu_id = f"menu:category:{category_id}:products"
        nodes = []
        edges = []
        
        # 添加产品节点
        for i, product in enumerate(products):
            # 使用elementId作为唯一标识，因为产品的id字段为None
            product_element_id = product.get('elementId', f'product_{i}')
            product_node_id = f"product:{product_element_id}"
            product_node = create_virtual_node(
                product_node_id, 
                product['name'], 
                "Product",
                meta=product.get('meta')
            )
            nodes.append(product_node)
            edges.append(create_virtual_edge(menu_id, product_node_id, "EXPANDS"))
        
        # 添加"更多..."节点
        if has_more:
            more_id = f"more:category:{category_id}:products"
            more_node = create_virtual_node(
                more_id, "更多...", "More", is_more=True,
                meta={"target": "products"}
            )
            nodes.append(more_node)
            edges.append(create_virtual_edge(menu_id, more_id, "EXPANDS"))
        
        return {
            'nodes': nodes, 
            'edges': edges, 
            'meta': {'hasMore': has_more}
        }


def get_category_allergens(category_id: str, limit: int = 4) -> Dict[str, Any]:
    """获取种类相关的化学应急源（过敏原）列表（4条+更多）+ 同时展开分组节点"""
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 根据新的数据库结构：种类-类型-产品-观点-化学应急源，通过观点节点统计症状
        cypher = """
        MATCH (c:种类 {id: $categoryId})-[:包含]->(t:类型)-[:包含]->(p:产品)-[:判断]->(opinion:观点)-[:包含]->(allergen:化学应急源)
        
        // 统计产品数量：直接统计相关的产品
        WITH allergen, collect(DISTINCT p) AS products
        
        // 通过观点节点统计症状 - 使用allergen_id属性关联
        OPTIONAL MATCH (symptom_opinion:观点)
        WHERE symptom_opinion.allergen_id = toString(allergen.id) AND symptom_opinion.symptom_id IS NOT NULL
        OPTIONAL MATCH (symptom:具体症状 {id: symptom_opinion.symptom_id})
        
        WITH allergen, products, collect(DISTINCT symptom) AS symptoms
        
        // 计算统计数量
        WITH allergen, 
             size(products) AS productCount,
             size(symptoms) AS symptomsCount
        
        ORDER BY allergen.name ASC
        LIMIT $limitPlusOne
        
        WITH collect({
            name: allergen.name, 
            elementId: elementId(allergen), 
            id: allergen.id,
            meta: { 
                symptomsCount: symptomsCount, 
                productCount: productCount
            }
        }) AS allergens
        
        RETURN allergens[..$limit] AS items, size(allergens) > $limit AS hasMore
        """
        
        result = session.run(cypher, categoryId=str(category_id), limit=limit, limitPlusOne=limit+1)
        records = list(result)
        record = records[0] if records else None
        
        if not record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        allergens = record['items']
        has_more = record['hasMore']
        
        menu_id = f"menu:category:{category_id}:allergens"
        nodes = []
        edges = []
        
        # 添加过敏原节点
        for i, allergen in enumerate(allergens):
            # 使用Neo4j的elementId作为唯一标识
            allergen_element_id = allergen.get('elementId', f'allergen_{i}')
            allergen_node_id = f"allergen:{allergen_element_id}"
            allergen_node = create_virtual_node(
                allergen_node_id, 
                allergen['name'], 
                "Allergen",
                meta=allergen.get('meta')
            )
            nodes.append(allergen_node)
            edges.append(create_virtual_edge(menu_id, allergen_node_id, "EXPANDS"))
        
        # 添加"更多..."节点
        if has_more:
            more_id = f"more:category:{category_id}:allergens"
            more_node = create_virtual_node(
                more_id, "更多...", "More", is_more=True,
                meta={"target": "allergens"}
            )
            nodes.append(more_node)
            edges.append(create_virtual_edge(menu_id, more_id, "EXPANDS"))
        
        return {
            'nodes': nodes, 
            'edges': edges, 
            'meta': {'hasMore': has_more}
        }


def get_product_children(product_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """获取产品的子分组：召回信息/新闻"""
    product_node_id = f"product:{product_id}"
    
    recall_group_id = f"group:product:{product_id}:recalls"
    recall_group = create_virtual_node(
        recall_group_id, "召回信息", "Group", is_group=True
    )
    
    news_group_id = f"group:product:{product_id}:news"
    news_group = create_virtual_node(
        news_group_id, "新闻", "Group", is_group=True
    )
    
    nodes = [recall_group, news_group]
    edges = [
        create_virtual_edge(product_node_id, recall_group_id, "HAS_GROUP"),
        create_virtual_edge(product_node_id, news_group_id, "HAS_GROUP"),
    ]
    
    return {'nodes': nodes, 'edges': edges}


def get_product_recalls(product_id: str, limit: int = 4) -> Dict[str, Any]:
    """获取产品的召回叶子节点（4条+更多）"""
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 查询前limit+1个召回（用于判断hasMore）
        cypher = """
        MATCH (p:产品 {name: $productName})-[:有召回]->(r:召回)
        WITH r ORDER BY coalesce(r.date, '1970-01-01') DESC
        LIMIT $limitPlusOne
        WITH collect({
            title: r.title, 
            id: r.id, 
            url: r.url,
            source: r.source,
            date: r.date,
            time: r.time
        }) AS recalls
        RETURN recalls[..$limit] AS items, size(recalls) > $limit AS hasMore
        """
        # 由于产品id为None，我们需要先通过elementId找到产品名称
        product_query = """
        MATCH (p:产品) WHERE elementId(p) = $productId RETURN p.name as name
        """
        product_result = session.run(product_query, productId=product_id)
        product_record = product_result.single()
        if not product_record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        product_name = product_record['name']
        result = session.run(cypher, productName=product_name, limit=limit, limitPlusOne=limit+1)
        records = list(result)
        record = records[0] if records else None
        
        if not record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        recalls = record['items']
        has_more = record['hasMore']
        
        group_id = f"group:product:{product_id}:recalls"
        nodes = []
        edges = []
        
        # 添加召回节点
        for recall in recalls:
            recall_id = str(recall['id'])
            recall_node = create_virtual_node(
                f"recall:{recall_id}", 
                recall.get('title', ''), 
                "Recall",
                url=recall.get('url'),
                source=recall.get('source'),
                time=recall.get('time')
            )
            nodes.append(recall_node)
            edges.append(create_virtual_edge(group_id, f"recall:{recall_id}", "CONTAINS"))
        
        # 添加"更多..."节点
        if has_more:
            more_id = f"more:product:{product_id}:recalls"
            more_node = create_virtual_node(
                more_id, "更多...", "More", is_more=True,
                meta={"target": "recalls"}
            )
            nodes.append(more_node)
            edges.append(create_virtual_edge(group_id, more_id, "CONTAINS"))
        
        return {
            'nodes': nodes, 
            'edges': edges, 
            'meta': {'hasMore': has_more}
        }


def get_product_news(product_id: str, limit: int = 4) -> Dict[str, Any]:
    """获取产品的新闻叶子节点（4条+更多）"""
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 查询前limit+1个新闻（用于判断hasMore）
        cypher = """
        MATCH (p:产品 {name: $productName})-[:提及于]->(n:新闻)
        WITH n ORDER BY coalesce(n.date, '1970-01-01') DESC
        LIMIT $limitPlusOne
        WITH collect({
            title: n.title, 
            id: n.id, 
            url: n.url,
            source: n.source,
            date: n.date,
            time: n.time,
            publish_time: n.publish_time
        }) AS news
        RETURN news[..$limit] AS items, size(news) > $limit AS hasMore
        """
        # 由于产品id为None，我们需要先通过elementId找到产品名称
        product_query = """
        MATCH (p:产品) WHERE elementId(p) = $productId RETURN p.name as name
        """
        product_result = session.run(product_query, productId=product_id)
        product_record = product_result.single()
        if not product_record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        product_name = product_record['name']
        result = session.run(cypher, productName=product_name, limit=limit, limitPlusOne=limit+1)
        records = list(result)
        record = records[0] if records else None
        
        if not record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        news_list = record['items']
        has_more = record['hasMore']
        
        group_id = f"group:product:{product_id}:news"
        nodes = []
        edges = []
        
        # 添加新闻节点
        for news in news_list:
            news_id = str(news['id'])
            news_node = create_virtual_node(
                f"news:{news_id}", 
                news.get('title', ''), 
                "News",
                url=news.get('url'),
                source=news.get('source'),
                publish_time=news.get('publish_time')
            )
            nodes.append(news_node)
            edges.append(create_virtual_edge(group_id, f"news:{news_id}", "CONTAINS"))
        
        # 添加"更多..."节点
        if has_more:
            more_id = f"more:product:{product_id}:news"
            more_node = create_virtual_node(
                more_id, "更多...", "More", is_more=True,
                meta={"target": "news"}
            )
            nodes.append(more_node)
            edges.append(create_virtual_edge(group_id, more_id, "CONTAINS"))
        
        return {
            'nodes': nodes, 
            'edges': edges, 
            'meta': {'hasMore': has_more}
        }


def get_allergen_children(allergen_id: str) -> List[Dict[str, Any]]:
    """
    获取化学应急源的子节点：包含该化学应急源的产品、导致的症状、相关文献
    
    数据结构：
    - 观点节点通过allergen_id属性关联化学应急源
    - 观点节点通过symptom_id属性关联症状
    - 产品通过判断关系连接观点
    
    Args:
        allergen_id: 化学应急源的Neo4j elementId或业务ID
    
    Returns:
        前端期望的数据结构：每个产品包含其相关症状和文献
    """
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 首先获取化学应急源的业务ID
        allergen_business_id_query = """
        MATCH (a:化学应急源)
        WHERE elementId(a) = $allergen_id OR toString(a.id) = $allergen_id
        RETURN a.id as business_id
        """
        allergen_result = session.run(allergen_business_id_query, allergen_id=allergen_id)
        allergen_record = allergen_result.single()
        
        if not allergen_record:
            return []
        
        business_id = str(allergen_record['business_id'])
        
        # 查询产品及其相关症状（通过化学应急源关联所有症状）
        query = """
        MATCH (p:产品)-[:判断]->(opinion:观点 {allergen_id: $business_id})
        WITH DISTINCT p
        MATCH (symptom_opinion:观点 {allergen_id: $business_id})
        WHERE symptom_opinion.symptom_id IS NOT NULL
        MATCH (symptom:具体症状 {id: symptom_opinion.symptom_id})
        WITH p, collect(DISTINCT {
            id: symptom.id,
            name: symptom.name
        }) as symptoms
        RETURN DISTINCT 
            p.id as product_id,
            p.name as product_name,
            symptoms as valid_symptoms
        LIMIT 50
        """
        
        try:
            result = session.run(query, business_id=business_id)
            products = []
            
            for record in result:
                # 处理症状数据
                symptoms_data = record['valid_symptoms'] or []
                
                product_data = {
                    'id': f"product:{record['product_id']}",
                    'name': record['product_name'] or '未知产品',
                    'entityType': 'Product',
                    'symptoms': [{'name': s.get('name')} for s in symptoms_data if s.get('name')],
                    'literature': []  # 暂时为空，可以后续扩展
                }
                
                products.append(product_data)
            
            return products
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error querying allergen children for {allergen_id}: {e}")
            return []


def get_allergen_symptoms(allergen_id: str, limit: int = 4) -> Dict[str, Any]:
    """获取化学应急源的症状叶子节点（4条+更多）"""
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 首先获取化学应急源的业务ID
        allergen_business_id_query = """
        MATCH (a:化学应急源)
        WHERE elementId(a) = $allergen_id OR toString(a.id) = $allergen_id
        RETURN a.id as business_id
        """
        allergen_result = session.run(allergen_business_id_query, allergen_id=allergen_id)
        allergen_record = allergen_result.single()
        
        if not allergen_record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        business_id = str(allergen_record['business_id'])
        
        # 查询前limit+1个症状（用于判断hasMore）- 基于观点的属性关联
        cypher = """
        MATCH (opinion:观点 {allergen_id: $business_id})
        MATCH (symptom:具体症状 {id: opinion.symptom_id})
        WITH symptom ORDER BY symptom.name ASC
        LIMIT $limitPlusOne
        WITH collect({name: symptom.name, id: symptom.id}) AS symptoms
        RETURN symptoms[..$limit] AS items, size(symptoms) > $limit AS hasMore
        """
        result = session.run(cypher, business_id=business_id, limit=limit, limitPlusOne=limit+1)
        records = list(result)
        record = records[0] if records else None
        
        if not record:
            return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}
        
        symptoms = record['items']
        has_more = record['hasMore']
        
        group_id = f"group:allergen:{allergen_id}:symptoms"
        nodes = []
        edges = []
        
        # 添加症状节点
        for i, symptom in enumerate(symptoms):
            symptom_name = symptom.get('name', f'symptom_{i}')
            symptom_business_id = symptom.get('id', f'symptom_{i}')
            symptom_node_id = f"symptom:{symptom_business_id}"
            symptom_node = create_virtual_node(
                symptom_node_id, 
                symptom_name, 
                "Symptom"
            )
            nodes.append(symptom_node)
            edges.append(create_virtual_edge(group_id, symptom_node_id, "CONTAINS"))
        
        # 添加"更多..."节点
        if has_more:
            more_id = f"more:allergen:{allergen_id}:symptoms"
            more_node = create_virtual_node(
                more_id, "更多...", "More", is_more=True,
                meta={"target": "symptoms"}
            )
            nodes.append(more_node)
            edges.append(create_virtual_edge(group_id, more_id, "CONTAINS"))
        
        return {
            'nodes': nodes, 
            'edges': edges, 
            'meta': {'hasMore': has_more}
        }


def get_allergen_literature(allergen_id: str, limit: int = 4) -> Dict[str, Any]:
    """获取化学应急源的文献叶子节点（4条+更多）- 当前数据库中暂无直接文献关系"""
    # 当前数据库结构中没有直接的文献关系，返回空结果
    # 可以后续根据需要扩展
    return {'nodes': [], 'edges': [], 'meta': {'hasMore': False}}


def get_allergen_products_and_symptoms(allergen_id: str) -> List[Dict[str, Any]]:
    """
    获取某化学应急源包含的产品列表，每个产品包含该化学应急源的所有症状和相关文献（用于过敏原弹窗单表展示）
    
    Args:
        allergen_id: 化学应急源的Neo4j elementId或业务ID
    
    Returns:
        产品列表，每个产品包含症状信息和文献信息
        [
            {
                'id': str,
                'name': str,
                'entityType': 'Product',
                'symptoms': [{'name': str, 'literature': [{'title': str, 'link': str}, ...]}, ...],
                'literature': [{'title': str, 'link': str}, ...]
            },
            ...
        ]
    """
    from ..models import db, AllergenSymptom, AllergenSymptomSource, Literature
    
    driver = Neo4jClient.get_driver()
    
    with driver.session() as session:
        # 首先获取化学应急源的业务ID
        allergen_business_id_query = """
        MATCH (a:化学应急源)
        WHERE elementId(a) = $allergen_id OR toString(a.id) = $allergen_id
        RETURN a.id as business_id, a.name as name
        """
        allergen_result = session.run(allergen_business_id_query, allergen_id=allergen_id)
        allergen_record = allergen_result.single()
        
        if not allergen_record:
            return []
        
        business_id = int(allergen_record['business_id'])
        
        # 查询该化学应急源相关的产品
        products_query = """
        MATCH (p:产品)-[:判断]->(opinion:观点 {allergen_id: $business_id})
        RETURN DISTINCT p.id as product_id, p.name as product_name
        ORDER BY p.name
        """
        products_result = session.run(products_query, business_id=str(business_id))
        
        # 查询该化学应急源相关的所有症状
        symptoms_query = """
        MATCH (opinion:观点 {allergen_id: $business_id})
        WHERE opinion.symptom_id IS NOT NULL
        MATCH (symptom:具体症状 {id: opinion.symptom_id})
        RETURN DISTINCT symptom.id as symptom_id, symptom.name as symptom_name
        ORDER BY symptom.name
        """
        symptoms_result = session.run(symptoms_query, business_id=str(business_id))
        
        # 首先获取该化学应急源的所有相关文献（去重）
        allergen_symptom_relations = db.session.query(AllergenSymptom).filter_by(
            allergen_id=business_id
        ).all()
        
        # 使用字典来基于文献标题去重（因为PMID可能为空或重复）
        unique_literature = {}
        for relation in allergen_symptom_relations:
            literature_sources = db.session.query(AllergenSymptomSource).filter_by(
                allergen_symptom_id=relation.id
            ).all()
            
            for source in literature_sources:
                literature = db.session.query(Literature).filter_by(id=source.literature_id).first()
                if literature and literature.title:
                    # 使用文献标题作为唯一键来去重，标题相同的文献视为重复
                    title_key = literature.title.strip()
                    if title_key not in unique_literature:
                        unique_literature[title_key] = {
                            'title': literature.title,
                            'url': literature.link
                        }
        
        # 转换为列表
        all_literature = list(unique_literature.values())
        
        # 构建症状列表，每个症状包含相关文献
        symptoms = []
        global_seen_literature_titles = set()  # 全局去重集合，使用文献标题
        
        for record in symptoms_result:
            symptom_id = int(record['symptom_id'])
            symptom_name = record['symptom_name']
            
            # 通过MySQL查询该过敏原-症状关系的文献
            allergen_symptom_relations = db.session.query(AllergenSymptom).filter_by(
                allergen_id=business_id,
                symptom_id=symptom_id
            ).all()
            
            symptom_literature = []
            for relation in allergen_symptom_relations:
                # 通过AllergenSymptomSource获取文献
                literature_sources = db.session.query(AllergenSymptomSource).filter_by(
                    allergen_symptom_id=relation.id
                ).all()
                
                for source in literature_sources:
                    literature = db.session.query(Literature).filter_by(id=source.literature_id).first()
                    if literature and literature.title:
                        # 使用文献标题进行全局去重
                        title_key = literature.title.strip()
                        if title_key not in global_seen_literature_titles:
                            symptom_literature.append({
                                'title': literature.title,
                                'url': literature.link
                            })
                            global_seen_literature_titles.add(title_key)
            
            symptoms.append({
                'name': symptom_name,
                'literature': symptom_literature,
            })
        
        # 为每个产品创建包含所有症状和文献的记录
        products = []
        for record in products_result:
            products.append({
                'id': record['product_id'],
                'name': record['product_name'],
                'entityType': 'Product',
                'symptoms': symptoms,  
                'literature': all_literature  
            })
        
        return products
