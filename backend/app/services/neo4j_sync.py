"""
MySQL到Neo4j的自动数据同步服务
在数据保存到MySQL后自动同步到Neo4j
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .neo4j_client import Neo4jClient
from ..models import Literature, News, Recall, Product, Category, Allergen, Type, Symptom1, Symptom2, Symptom3

logger = logging.getLogger(__name__)


class Neo4jSyncService:
    """MySQL到Neo4j的数据同步服务"""
    
    @classmethod
    def sync_literature(cls, literature_id: int, operation: str = 'create') -> bool:
        """同步文献数据到Neo4j
        
        Args:
            literature_id: 文献ID
            operation: 操作类型 ('create', 'update', 'delete')
        """
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    # 删除节点
                    session.run(
                        "MATCH (l:文献 {id: $id}) DETACH DELETE l",
                        id=str(literature_id)
                    )
                    logger.info(f"Deleted literature node {literature_id} from Neo4j")
                    return True
                
                # 获取文献数据
                from .. import db
                lit = db.session.get(Literature, literature_id)
                if not lit:
                    logger.warning(f"Literature {literature_id} not found in MySQL")
                    return False
                
                # 创建或更新节点
                session.run("""
                    MERGE (l:文献 {id: $id})
                    SET l.name = $title,
                        l.title = $title,
                        l.authors = $authors,
                        l.abstract = $abstract,
                        l.keywords = $keywords,
                        l.publish_date = $publish_date,
                        l.link = $link,
                        l.url = $link,
                        l.source = $source,
                        l.updated_at = datetime()
                """, {
                    'id': str(lit.id),
                    'title': lit.title or '',
                    'authors': lit.authors or '',
                    'abstract': lit.abstract or '',
                    'keywords': lit.keywords or '',
                    'publish_date': lit.publish_date.isoformat() if lit.publish_date else '',
                    'link': lit.link or '',
                    'source': lit.source or ''
                })
                
                # 同步关键词关系
                cls._sync_literature_keywords(session, lit)
                
                logger.info(f"Synced literature {literature_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync literature {literature_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_news(cls, news_id: int, operation: str = 'create') -> bool:
        """同步新闻数据到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (n:新闻 {id: $id}) DETACH DELETE n",
                        id=str(news_id)
                    )
                    logger.info(f"Deleted news node {news_id} from Neo4j")
                    return True
                
                from .. import db
                news = db.session.get(News, news_id)
                if not news:
                    logger.warning(f"News {news_id} not found in MySQL")
                    return False
                
                # 预处理时间数据，转换为日期字符串
                publish_time_str = None
                if news.publish_time:
                    publish_time_str = news.publish_time.date().isoformat()  # 只保留日期部分，格式：YYYY-MM-DD
                
                session.run("""
                    MERGE (n:新闻 {id: $id})
                    SET n.name = $title,
                        n.title = $title,
                        n.abstract = $abstract,
                        n.date = $publish_time_str,
                        n.time = CASE WHEN $publish_time_str IS NULL THEN null ELSE $publish_time_str END,
                        n.publish_time = CASE WHEN $publish_time_str IS NULL THEN null ELSE $publish_time_str END,
                        n.url = $link,
                        n.source = $source,
                        n.updated_at = datetime()
                """, {
                    'id': str(news.id),
                    'title': news.title or '',
                    'abstract': news.abstract or '',
                    'publish_time_str': publish_time_str,
                    'link': news.link or '',
                    'source': news.source or ''
                })
                
                cls._sync_news_keywords(session, news)
                
                logger.info(f"Synced news {news_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync news {news_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_recall(cls, recall_id: int, operation: str = 'create') -> bool:
        """同步召回数据到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (r:召回 {id: $id}) DETACH DELETE r",
                        id=str(recall_id)
                    )
                    logger.info(f"Deleted recall node {recall_id} from Neo4j")
                    return True
                
                from .. import db
                recall = db.session.get(Recall, recall_id)
                if not recall:
                    logger.warning(f"Recall {recall_id} not found in MySQL")
                    return False
                
                # 预处理时间数据，转换为日期字符串
                time_str = None
                if recall.time:
                    time_str = recall.time.date().isoformat()  # 只保留日期部分，格式：YYYY-MM-DD
                
                session.run("""
                    MERGE (r:召回 {id: $id})
                    SET r.name = $product_name,
                        r.title = $product_name,
                        r.manufacturer = $manufacturer,
                        r.product_name = $product_name,
                        r.description = $description,
                        r.defect = $defect,
                        r.hazard = $hazard,
                        r.date = $time_str,
                        r.time = CASE WHEN $time_str IS NULL THEN null ELSE $time_str END,
                        r.url = $link,
                        r.source = $source,
                        r.external_id = $external_id,
                        r.updated_at = datetime()
                """, {
                    'id': str(recall.id),
                    'product_name': recall.product_name or '',
                    'manufacturer': recall.manufacturer or '',
                    'description': recall.description or '',
                    'defect': recall.defect or '',
                    'hazard': recall.hazard or '',
                    'time_str': time_str,
                    'link': recall.link or '',
                    'source': recall.source or '',
                    'external_id': recall.external_id or ''
                })
                
                cls._sync_recall_keywords(session, recall)
                
                logger.info(f"Synced recall {recall_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync recall {recall_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_product(cls, product_id: int, operation: str = 'create') -> bool:
        """同步三级产品到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (p:产品 {id: $id}) DETACH DELETE p",
                        id=str(product_id)
                    )
                    logger.info(f"Deleted product node {product_id} from Neo4j")
                    return True
                
                from .. import db
                from ..models import Type
                product = db.session.get(Product, product_id)
                if not product:
                    logger.warning(f"Product {product_id} not found in MySQL")
                    return False
                
                # 获取类型信息（二级产品）
                type_obj = db.session.get(Type, product.category_id)
                
                # 创建产品节点
                session.run("""
                    MERGE (p:产品 {id: $id})
                    SET p.name = $name,
                        p.parentId = $parent_id,
                        p.created_at = datetime($created_at),
                        p.updated_at = datetime($updated_at)
                """, {
                    'id': str(product.id),
                    'name': product.name or '',
                    'parent_id': str(product.category_id),
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                    'updated_at': product.updated_at.isoformat() if product.updated_at else None
                })
                
            # 检查父节点是否存在，如果不存在则报错
            if type_obj:
                with driver.session() as check_session:
                    result = check_session.run("""
                        MATCH (t:类型 {id: $type_id})
                        RETURN t
                    """, {'type_id': str(type_obj.id)})
                    parent_exists = result.single() is not None
                
                if not parent_exists:
                    error_msg = f"Parent type (ID: {type_obj.id}, Name: {type_obj.name}) not found in Neo4j. Please sync type first before creating product."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 在新session中建立关系
                with driver.session() as rel_session:
                    rel_session.run("""
                        MATCH (t:类型 {id: $type_id})
                        MATCH (p:产品 {id: $product_id})
                        MERGE (t)-[:包含]->(p)
                    """, {
                        'type_id': str(type_obj.id),
                        'product_id': str(product.id)
                    })
                    logger.info(f"Created relationship between type {type_obj.id} and product {product_id}")
                
                logger.info(f"Synced product {product_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync product {product_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def _sync_literature_keywords(cls, session, literature):
        """同步文献关键词关系"""
        try:
            # 删除旧的关键词关系
            session.run(
                "MATCH (p:产品)-[r:相关文献]->(l:文献 {id: $id}) DELETE r",
                id=str(literature.id)
            )
            
            # 创建新的关键词关系（与脚本导入保持一致：产品指向文献）
            for binding in literature.bindings:
                session.run("""
                    MATCH (l:文献 {id: $lit_id})
                    MERGE (p:产品 {id: $prod_id})
                    MERGE (p)-[:相关文献 {keyword: $keyword}]->(l)
                """, {
                    'lit_id': str(literature.id),
                    'prod_id': str(binding.product_id),
                    'keyword': binding.keyword
                })
        except Exception as e:
            logger.error(f"Failed to sync literature keywords: {e}")
    
    @classmethod
    def _sync_news_keywords(cls, session, news):
        """同步新闻关键词关系"""
        try:
            session.run(
                "MATCH (p:产品)-[r:提及于]->(n:新闻 {id: $id}) DELETE r",
                id=str(news.id)
            )
            
            # 创建新的关键词关系（与脚本导入保持一致：产品指向新闻）
            for binding in news.bindings:
                session.run("""
                    MATCH (n:新闻 {id: $news_id})
                    MERGE (p:产品 {id: $prod_id})
                    MERGE (p)-[:提及于 {keyword: $keyword}]->(n)
                """, {
                    'news_id': str(news.id),
                    'prod_id': str(binding.product_id),
                    'keyword': binding.keyword
                })
        except Exception as e:
            logger.error(f"Failed to sync news keywords: {e}")
    
    @classmethod
    def _sync_recall_keywords(cls, session, recall):
        """同步召回关键词关系"""
        try:
            session.run(
                "MATCH (p:产品)-[rel:有召回]->(r:召回 {id: $id}) DELETE rel",
                id=str(recall.id)
            )
            
            # 创建新的关键词关系（与脚本导入保持一致：产品指向召回）
            for binding in recall.bindings:
                session.run("""
                    MATCH (r:召回 {id: $recall_id})
                    MERGE (p:产品 {id: $prod_id})
                    MERGE (p)-[:有召回 {keyword: $keyword}]->(r)
                """, {
                    'recall_id': str(recall.id),
                    'prod_id': str(binding.product_id),
                    'keyword': binding.keyword
                })
        except Exception as e:
            logger.error(f"Failed to sync recall keywords: {e}")

    @classmethod
    def sync_category(cls, category_id: int, operation: str = 'create') -> bool:
        """同步一级产品（种类）到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (c:种类 {id: $id}) DETACH DELETE c",
                        id=str(category_id)
                    )
                    logger.info(f"Deleted category node {category_id} from Neo4j")
                    return True
                
                from .. import db
                from ..models import Category
                category = db.session.get(Category, category_id)
                if not category:
                    logger.warning(f"Category {category_id} not found in MySQL")
                    return False
                
                session.run("""
                    MERGE (c:种类 {id: $id})
                    SET c.name = $name,
                        c.created_at = datetime($created_at),
                        c.updated_at = datetime($updated_at)
                """, {
                    'id': str(category.id),
                    'name': category.name or '',
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None
                })
                
                logger.info(f"Synced category {category_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync category {category_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_type(cls, type_id: int, operation: str = 'create') -> bool:
        """同步二级产品（类型）到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (t:类型 {id: $id}) DETACH DELETE t",
                        id=str(type_id)
                    )
                    logger.info(f"Deleted type node {type_id} from Neo4j")
                    return True
                
                from .. import db
                from ..models import Type, Category
                type_obj = db.session.get(Type, type_id)
                if not type_obj:
                    logger.warning(f"Type {type_id} not found in MySQL")
                    return False
                
                # 获取分类信息
                category = db.session.get(Category, type_obj.category_id)
                
                # 创建类型节点
                session.run("""
                    MERGE (t:类型 {id: $id})
                    SET t.name = $name,
                        t.parentId = $parent_id,
                        t.created_at = datetime($created_at),
                        t.updated_at = datetime($updated_at)
                """, {
                    'id': str(type_obj.id),
                    'name': type_obj.name or '',
                    'parent_id': str(type_obj.category_id),
                    'created_at': type_obj.created_at.isoformat() if type_obj.created_at else None,
                    'updated_at': type_obj.updated_at.isoformat() if type_obj.updated_at else None
                })
                
            # 检查父节点是否存在，如果不存在则报错
            if category:
                with driver.session() as check_session:
                    result = check_session.run("""
                        MATCH (c:种类 {id: $category_id})
                        RETURN c
                    """, {'category_id': str(category.id)})
                    parent_exists = result.single() is not None
                
                if not parent_exists:
                    error_msg = f"Parent category (ID: {category.id}, Name: {category.name}) not found in Neo4j. Please sync category first before creating type."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 在新session中建立关系
                with driver.session() as rel_session:
                    rel_session.run("""
                        MATCH (c:种类 {id: $category_id})
                        MATCH (t:类型 {id: $type_id})
                        MERGE (c)-[:包含]->(t)
                    """, {
                        'category_id': str(category.id),
                        'type_id': str(type_obj.id)
                    })
                    logger.info(f"Created relationship between category {category.id} and type {type_id}")
                
                logger.info(f"Synced type {type_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync type {type_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_allergen(cls, allergen_id: int, operation: str = 'create') -> bool:
        """同步过敏原到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (a:化学应急源 {id: $id}) DETACH DELETE a",
                        id=str(allergen_id)
                    )
                    logger.info(f"Deleted allergen node {allergen_id} from Neo4j")
                    return True
                
                from .. import db
                from ..models import Allergen
                allergen = db.session.get(Allergen, allergen_id)
                if not allergen:
                    logger.warning(f"Allergen {allergen_id} not found in MySQL")
                    return False
                
                session.run("""
                    MERGE (a:化学应急源 {id: $id})
                    SET a.name = $name,
                        a.title = $name,
                        a.cas_number = $cas_number,
                        a.description = $description,
                        a.updated_at = datetime()
                """, {
                    'id': str(allergen.id),
                    'name': allergen.name or '',
                    'cas_number': allergen.cas_number or '',
                    'description': allergen.description or ''
                })
                
                logger.info(f"Synced allergen {allergen_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync allergen {allergen_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_symptom1(cls, symptom_id: int, operation: str = 'create') -> bool:
        """同步症状种类到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (s:症状种类 {id: $id}) DETACH DELETE s",
                        id=str(symptom_id)
                    )
                    logger.info(f"Deleted symptom1 node {symptom_id} from Neo4j")
                    return True
                
                from .. import db
                from ..models import Symptom1
                symptom = db.session.get(Symptom1, symptom_id)
                if not symptom:
                    logger.warning(f"Symptom1 {symptom_id} not found in MySQL")
                    return False
                
                # 创建或更新一级症状节点
                session.run("""
                    MERGE (s:症状种类 {id: $id})
                    SET s.name = $name,
                        s.updated_at = datetime()
                """, {
                    'id': str(symptom.id),
                    'name': symptom.symptom_name or ''
                })
                
                logger.info(f"Synced symptom1 {symptom_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync symptom1 {symptom_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_symptom2(cls, symptom_id: int, operation: str = 'create') -> bool:
        """同步症状类型到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    session.run(
                        "MATCH (s:症状类型 {id: $id}) DETACH DELETE s",
                        id=str(symptom_id)
                    )
                    logger.info(f"Deleted symptom2 node {symptom_id} from Neo4j")
                    return True
                
                from .. import db
                from ..models import Symptom2, Symptom1
                symptom = db.session.get(Symptom2, symptom_id)
                if not symptom:
                    logger.warning(f"Symptom2 {symptom_id} not found in MySQL")
                    return False
                
                # 获取症状种类信息
                major_symptom = db.session.get(Symptom1, symptom.major_id)
                
                # 创建或更新二级症状节点
                session.run("""
                    MERGE (s:症状类型 {id: $id})
                    SET s.name = $name,
                        s.parentId = $parentId,
                        s.updated_at = datetime()
                """, {
                    'id': str(symptom.id),
                    'name': symptom.symptom_name or '',
                    'parentId': str(symptom.major_id)
                })
                
            # 检查父节点是否存在，如果不存在则报错
            if major_symptom:
                with driver.session() as check_session:
                    result = check_session.run("""
                        MATCH (s1:症状种类 {id: $major_id})
                        RETURN s1
                    """, {'major_id': str(major_symptom.id)})
                    parent_exists = result.single() is not None
                
                if not parent_exists:
                    error_msg = f"Parent symptom1 (ID: {major_symptom.id}, Name: {major_symptom.symptom_name}) not found in Neo4j. Please sync symptom1 first before creating symptom2."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 在新session中建立关系
                with driver.session() as rel_session:
                    rel_session.run("""
                        MATCH (s1:症状种类 {id: $major_id})
                        MATCH (s2:症状类型 {id: $symptom_id})
                        MERGE (s1)-[:包含症状类型]->(s2)
                    """, {
                        'major_id': str(major_symptom.id),
                        'symptom_id': str(symptom.id)
                    })
                    logger.info(f"Created relationship between symptom1 {major_symptom.id} and symptom2 {symptom.id}")
                
                logger.info(f"Synced symptom2 {symptom_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync symptom2 {symptom_id} to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_symptom3(cls, symptom_id: int, operation: str = 'create') -> bool:
        """同步具体症状到Neo4j"""
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if operation == 'delete':
                    # 先删除相关的观点节点（观点节点通过symptom_id关联）
                    session.run("""
                        MATCH (v:观点 {symptom_id: $symptom_id})
                        DETACH DELETE v
                    """, {'symptom_id': str(symptom_id)})
                    
                    # 再删除具体症状节点
                    session.run(
                        "MATCH (s:具体症状 {id: $id}) DETACH DELETE s",
                        id=str(symptom_id)
                    )
                    logger.info(f"Deleted symptom3 node {symptom_id} and related viewpoint nodes from Neo4j")
                    return True
                
                from .. import db
                from ..models import Symptom3, Symptom2
                symptom = db.session.get(Symptom3, symptom_id)
                if not symptom:
                    logger.warning(f"Symptom3 {symptom_id} not found in MySQL")
                    return False
                
                # 获取症状类型信息
                sub_symptom = db.session.get(Symptom2, symptom.sub_id)
                
                # 创建或更新三级症状节点
                session.run("""
                    MERGE (s:具体症状 {id: $id})
                    SET s.name = $name,
                        s.parentId = $parentId,
                        s.updated_at = datetime()
                """, {
                    'id': str(symptom.id),
                    'name': symptom.name or '',
                    'parentId': str(symptom.sub_id)
                })
                
            # 检查父节点是否存在，如果不存在则报错
            if sub_symptom:
                with driver.session() as check_session:
                    result = check_session.run("""
                        MATCH (s2:症状类型 {id: $sub_id})
                        RETURN s2
                    """, {'sub_id': str(sub_symptom.id)})
                    parent_exists = result.single() is not None
                
                if not parent_exists:
                    error_msg = f"Parent symptom2 (ID: {sub_symptom.id}, Name: {sub_symptom.symptom_name}) not found in Neo4j. Please sync symptom2 first before creating symptom3."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 在新session中建立关系
                with driver.session() as rel_session:
                    rel_session.run("""
                        MATCH (s2:症状类型 {id: $sub_id})
                        MATCH (s3:具体症状 {id: $symptom_id})
                        MERGE (s2)-[:包含具体症状]->(s3)
                    """, {
                        'sub_id': str(sub_symptom.id),
                        'symptom_id': str(symptom.id)
                    })
                    logger.info(f"Created relationship between symptom2 {sub_symptom.id} and symptom3 {symptom.id}")
                
                logger.info(f"Synced symptom3 {symptom_id} to Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync symptom3 {symptom_id} to Neo4j: {e}")
            return False

    @classmethod
    def sync_allergen_product_relation(cls, allergen_id: int, product_id: int, 
                                      relation_id: int, operation: str = 'create', note: str = '') -> bool:
        """同步化学应激源-产品关联关系到Neo4j
        
        使用新的关系模型：产品 -[判断]-> 观点 -[包含]-> 化学应急源
        
        Args:
            allergen_id: 化学应急源ID
            product_id: 产品ID
            relation_id: 关系ID
            operation: 操作类型 ('create', 'update', 'delete')
            note: 备注信息
        """
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                from .. import db
                from ..models import AllergenProduct
                
                viewpoint_id = f"product_{relation_id}"
                
                if operation == 'delete':
                    # 根据product_id和allergen_id查找并删除观点节点
                    session.run("""
                        MATCH (v:观点)
                        WHERE v.product_id = $product_id AND v.allergen_id = $allergen_id
                        DETACH DELETE v
                    """, {
                        'product_id': str(product_id),
                        'allergen_id': str(allergen_id)
                    })
                    logger.info(f"Deleted product-allergen relation from Neo4j: product_{product_id}-allergen_{allergen_id}")
                    return True
                
                # 获取实体数据
                allergen = db.session.get(Allergen, allergen_id)
                product = db.session.get(Product, product_id)
                
                if not allergen or not product:
                    logger.warning(f"Allergen {allergen_id} or Product {product_id} not found")
                    return False
                
                # 获取关系记录以获取时间戳
                relation = db.session.get(AllergenProduct, relation_id)
                if not relation:
                    logger.warning(f"AllergenProduct relation {relation_id} not found")
                    return False
                
                if operation == 'update':
                    # 删除旧的观点节点和关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        DETACH DELETE v
                    """, {
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 重新创建观点节点和关系（使用最新的product_id和allergen_id）
                    # 1. 创建观点节点
                    session.run("""
                        CREATE (v:观点 {
                            id: $viewpoint_id,
                            product_id: $product_id,
                            allergen_id: $allergen_id,
                            type: 'product_allergen',
                            created_at: datetime($created_at),
                            updated_at: datetime($updated_at)
                        })
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'product_id': str(product_id),
                        'allergen_id': str(allergen_id),
                        'created_at': relation.created_at.isoformat() if relation.created_at else None,
                        'updated_at': relation.updated_at.isoformat() if relation.updated_at else None
                    })
                    
                    # 2. 建立 产品 -[判断]-> 观点 关系
                    session.run("""
                        MATCH (p:产品 {id: $product_id})
                        MATCH (v:观点 {id: $viewpoint_id})
                        CREATE (p)-[:判断]->(v)
                    """, {
                        'product_id': str(product_id),
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 3. 建立 观点 -[包含]-> 化学应急源 关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        MATCH (a:化学应急源 {id: $allergen_id})
                        CREATE (v)-[:包含]->(a)
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'allergen_id': str(allergen_id)
                    })
                    
                    logger.info(f"Updated product-allergen relation in Neo4j: {viewpoint_id}")
                    return True
                if operation == 'create':
                    # 创建操作：产品 -[判断]-> 观点 -[包含]-> 化学应急源
                    # 1. 创建观点节点
                    session.run("""
                        CREATE (v:观点 {
                            id: $viewpoint_id,
                            product_id: $product_id,
                            allergen_id: $allergen_id,
                            type: 'product_allergen'
                        })
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'product_id': str(product_id),
                        'allergen_id': str(allergen_id),
                    })
                    
                    # 2. 建立 产品 -[判断]-> 观点 关系
                    session.run("""
                        MATCH (p:产品 {id: $product_id})
                        MATCH (v:观点 {id: $viewpoint_id})
                        CREATE (p)-[:判断]->(v)
                    """, {
                        'product_id': str(product_id),
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 3. 建立 观点 -[包含]-> 化学应急源 关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        MATCH (a:化学应急源 {id: $allergen_id})
                        CREATE (v)-[:包含]->(a)
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'allergen_id': str(allergen_id)
                    })
                    return True
                
        except Exception as e:
            logger.error(f"Failed to sync allergen-product relation to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_allergen_symptom_relation(cls, allergen_id: int, symptom_id: int, 
                                      relation_id: int, traec_score: float = 0.0,
                                      operation: str = 'create') -> bool:
        """同步化学应激源-症状关联关系到Neo4j
        
        使用新的关系模型：化学应急源 -[判断]-> 观点 -[导致]-> 症状类型
        
        Args:
            allergen_id: 化学应急源ID
            symptom_id: 症状ID
            relation_id: 关系ID
            traec_score: TRAEC评分
            operation: 操作类型 ('create', 'update', 'delete')
        """
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                from .. import db
                from ..models import Symptom2, AllergenSymptom
                
                viewpoint_id = str(relation_id)
                
                if operation == 'delete':
                    # 根据allergen_id和symptom_id查找并删除观点节点
                    session.run("""
                        MATCH (v:观点)
                        WHERE v.allergen_id = $allergen_id AND v.symptom_id = $symptom_id
                        DETACH DELETE v
                    """, {
                        'allergen_id': str(allergen_id),
                        'symptom_id': str(symptom_id)
                    })
                    logger.info(f"Deleted allergen-symptom relation from Neo4j: allergen_{allergen_id}-symptom_{symptom_id}")
                    return True
                
                # 获取实体数据
                allergen = db.session.get(Allergen, allergen_id)
                symptom = db.session.get(Symptom2, symptom_id)
                
                if not allergen or not symptom:
                    logger.warning(f"Allergen {allergen_id} or Symptom {symptom_id} not found")
                    return False
                
                # 获取关系记录以获取时间戳
                relation = db.session.get(AllergenSymptom, relation_id)
                if not relation:
                    logger.warning(f"AllergenSymptom relation {relation_id} not found")
                    return False
                
                if operation == 'update':
                    # 删除旧的观点节点和关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        DETACH DELETE v
                    """, {
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 重新创建观点节点和关系（使用最新的allergen_id和symptom_id）
                    # 1. 创建观点节点
                    session.run("""
                        CREATE (v:观点 {
                            id: $viewpoint_id,
                            allergen_id: $allergen_id,
                            symptom_id: $symptom_id,
                            traec_score: $traec_score,
                            type: 'allergen_symptom',
                            created_at: datetime($created_at),
                            updated_at: datetime($updated_at)
                        })
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'allergen_id': str(allergen_id),
                        'symptom_id': str(symptom_id),
                        'traec_score': traec_score,
                        'created_at': relation.create_at.isoformat() if relation.create_at else None,
                        'updated_at': relation.update_at.isoformat() if relation.update_at else None
                    })
                    
                    # 2. 建立 化学应急源 -[判断]-> 观点 关系
                    session.run("""
                        MATCH (a:化学应急源 {id: $allergen_id})
                        MATCH (v:观点 {id: $viewpoint_id})
                        CREATE (a)-[:判断]->(v)
                    """, {
                        'allergen_id': str(allergen_id),
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 3. 建立 观点 -[导致]-> 具体症状 关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        MATCH (s:症状类型 {id: $symptom_id})
                        CREATE (v)-[:导致]->(s)
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'symptom_id': str(symptom_id)
                    })
                    
                    logger.info(f"Updated allergen-symptom relation in Neo4j: {viewpoint_id}")
                    return True
                
                # 创建操作：化学应急源 -[判断]-> 观点 -[导致]-> 具体症状
                # 1. 创建观点节点
                session.run("""
                    CREATE (v:观点 {
                        id: $viewpoint_id,
                        allergen_id: $allergen_id,
                        symptom_id: $symptom_id,
                        traec_score: $traec_score,
                        type: 'allergen_symptom',
                        created_at: datetime($created_at),
                        updated_at: datetime($updated_at)
                    })
                """, {
                    'viewpoint_id': viewpoint_id,
                    'allergen_id': str(allergen_id),
                    'symptom_id': str(symptom_id),
                    'traec_score': traec_score,
                    'created_at': relation.create_at.isoformat() if relation.create_at else None,
                    'updated_at': relation.update_at.isoformat() if relation.update_at else None
                })
                
                # 2. 建立 化学应急源 -[判断]-> 观点 关系
                session.run("""
                    MATCH (a:化学应急源 {id: $allergen_id})
                    MATCH (v:观点 {id: $viewpoint_id})
                    CREATE (a)-[:判断]->(v)
                """, {
                    'allergen_id': str(allergen_id),
                    'viewpoint_id': viewpoint_id
                })
                
                # 3. 建立 观点 -[导致]-> 具体症状 关系
                session.run("""
                    MATCH (v:观点 {id: $viewpoint_id})
                    MATCH (s:症状类型 {id: $symptom_id})
                    CREATE (v)-[:导致]->(s)
                """, {
                    'viewpoint_id': viewpoint_id,
                    'symptom_id': str(symptom_id)
                })
                
                logger.info(f"Synced allergen-symptom relation to Neo4j: allergen_{allergen_id} -> {viewpoint_id} -> symptom_{symptom_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync allergen-symptom relation to Neo4j: {e}")
            return False
    
    @classmethod
    def sync_product_symptom_relation(cls, product_id: int, symptom_id: int, 
                                    relation_id: int,operation: str = 'create') -> bool:
        """同步产品-症状关联关系到Neo4j
        
        使用新的关系模型：产品 -[判断]-> 观点 -[引发]-> 症状类型
        
        Args:
            product_id: 产品ID
            symptom_id: 症状ID
            relation_id: 关系ID
            operation: 操作类型 ('create', 'update', 'delete')
        """
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                from .. import db
                from ..models import Product, Symptom2, ProductSymptom
                
                viewpoint_id = f"product_symptom_{relation_id}"
                
                if operation == 'delete':
                    # 根据product_id和symptom_id查找并删除观点节点
                    session.run("""
                        MATCH (v:观点)
                        WHERE v.product_id = $product_id AND v.symptom_id = $symptom_id
                        DETACH DELETE v
                    """, {
                        'product_id': str(product_id),
                        'symptom_id': str(symptom_id)
                    })
                    logger.info(f"Deleted product-symptom relation from Neo4j: product_{product_id}-symptom_{symptom_id}")
                    return True
                
                # 获取实体数据
                product = db.session.get(Product, product_id)
                symptom = db.session.get(Symptom2, symptom_id)
                
                if not product or not symptom:
                    logger.warning(f"Product {product_id} or Symptom {symptom_id} not found")
                    return False
                
                # 获取关系记录以获取时间戳
                relation = db.session.get(ProductSymptom, relation_id)
                if not relation:
                    logger.warning(f"ProductSymptom relation {relation_id} not found")
                    return False
                
                if operation == 'update':
                    # 删除旧的观点节点和关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        DETACH DELETE v
                    """, {
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 重新创建观点节点和关系（使用最新的product_id和symptom_id）
                    # 1. 创建观点节点
                    session.run("""
                        CREATE (v:观点 {
                            id: $viewpoint_id,
                            product_id: $product_id,
                            symptom_id: $symptom_id,
                            type: 'product_symptom',
                            created_at: datetime($created_at),
                            updated_at: datetime($updated_at)
                        })
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'product_id': str(product_id),
                        'symptom_id': str(symptom_id),
                        'created_at': relation.create_at.isoformat() if relation.create_at else None,
                        'updated_at': relation.update_at.isoformat() if relation.update_at else None
                    })
                    
                    # 2. 建立 产品 -[判断]-> 观点 关系
                    session.run("""
                        MATCH (p:产品 {id: $product_id})
                        MATCH (v:观点 {id: $viewpoint_id})
                        CREATE (p)-[:判断]->(v)
                    """, {
                        'product_id': str(product_id),
                        'viewpoint_id': viewpoint_id
                    })
                    
                    # 3. 建立 观点 -[引发]-> 具体症状 关系
                    session.run("""
                        MATCH (v:观点 {id: $viewpoint_id})
                        MATCH (s:症状类型 {id: $symptom_id})
                        CREATE (v)-[:引发]->(s)
                    """, {
                        'viewpoint_id': viewpoint_id,
                        'symptom_id': str(symptom_id)
                    })
                    
                    logger.info(f"Updated product-symptom relation in Neo4j: {viewpoint_id}")
                    return True
                
                # 创建操作：产品 -[判断]-> 观点 -[引发]-> 具体症状
                # 1. 创建观点节点
                session.run("""
                    CREATE (v:观点 {
                        id: $viewpoint_id,
                        product_id: $product_id,
                        symptom_id: $symptom_id,
                        type: 'product_symptom',
                        created_at: datetime($created_at),
                        updated_at: datetime($updated_at)
                    })
                """, {
                    'viewpoint_id': viewpoint_id,
                    'product_id': str(product_id),
                    'symptom_id': str(symptom_id),
                    'created_at': relation.create_at.isoformat() if relation.create_at else None,
                    'updated_at': relation.update_at.isoformat() if relation.update_at else None
                })
                
                # 2. 建立 产品 -[判断]-> 观点 关系
                session.run("""
                    MATCH (p:产品 {id: $product_id})
                    MATCH (v:观点 {id: $viewpoint_id})
                    CREATE (p)-[:判断]->(v)
                """, {
                    'product_id': str(product_id),
                    'viewpoint_id': viewpoint_id
                })
                
                # 3. 建立 观点 -[引发]-> 具体症状 关系
                session.run("""
                    MATCH (v:观点 {id: $viewpoint_id})
                    MATCH (s:症状类型 {id: $symptom_id})
                    CREATE (v)-[:引发]->(s)
                """, {
                    'viewpoint_id': viewpoint_id,
                    'symptom_id': str(symptom_id)
                })
                
                logger.info(f"Synced product-symptom relation to Neo4j: product_{product_id} -> {viewpoint_id} -> symptom_{symptom_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync product-symptom relation to Neo4j: {e}")
            return False


def sync_allergen_with_old_name(allergen_id: int, old_name: str, operation: str = 'update') -> bool:
    """使用旧名称同步过敏原数据到Neo4j"""
    try:
        driver = Neo4jClient.get_driver()
        with driver.session() as session:
            if operation == 'delete':
                # 删除操作使用旧名称
                session.run(
                    "MATCH (a:化学应急源 {name: $old_name}) DETACH DELETE a",
                    old_name=old_name
                )
                return True
            
            # 获取MySQL中的最新数据
            from .. import db
            allergen = db.session.get(Allergen, allergen_id)
            if not allergen:
                return False
            
            # 获取分类信息
            from ..models import Category
            category = db.session.get(Category, allergen.category_id)
            
            # 检查新名称是否已经被其他节点使用
            if old_name != allergen.name:  # 只有名称真正改变时才检查
                check_result = session.run("""
                    MATCH (a:化学应急源 {name: $new_name})
                    WHERE a.name <> $old_name
                    RETURN count(a) as count
                """, {
                    'new_name': allergen.name or '',
                    'old_name': old_name
                })
                
                count_record = check_result.single()
                if count_record and count_record['count'] > 0:
                    return False
            
            # 用旧名称查找节点，更新为新数据
            result = session.run("""
                MATCH (a:化学应急源 {name: $old_name})
                SET a.name = $new_name,
                    a.title = $new_name,
                    a.description = $description,
                    a.category_id = $category_id,
                    a.category_name = $category_name,
                    a.id = $id,
                    a.updated_at = datetime()
                RETURN a
            """, {
                'old_name': old_name,
                'new_name': allergen.name or '',
                'description': allergen.description or '',
                'category_id': str(allergen.category_id),
                'category_name': category.name if category else '',
                'id': str(allergen.id)
            })
            
            updated_node = result.single()
            if updated_node:
                # 同步分类关系
                if category:
                    session.run("""
                        MERGE (c:类别 {id: $cat_id})
                        SET c.name = $cat_name, c.title = $cat_name
                        WITH c
                        MATCH (a:化学应急源 {name: $allergen_name})
                        MERGE (c)-[:聚合化学应急源]->(a)
                    """, {
                        'cat_id': str(category.id),
                        'cat_name': category.name,
                        'allergen_name': allergen.name
                    })
                
                return True
            else:
                return False
                
    except Exception as e:
        logger.error(f"Failed to sync allergen {allergen_id} with old name {old_name} to Neo4j: {e}")
        return False

def sync_to_neo4j(model_name: str, record_id: int, operation: str = 'create') -> bool:
    """通用的同步函数
    
    Args:
        model_name: 模型名称 ('literature', 'news', 'recall', 'product', 'allergen', 'category', 'type', 'symptom1', 'symptom2', 'symptom3')
        record_id: 记录ID
        operation: 操作类型 ('create', 'update', 'delete')
    """
    logger.info(f"Syncing {model_name} {record_id} to Neo4j with operation: {operation}")
    
    try:
        result = False
        if model_name == 'literature':
            result = Neo4jSyncService.sync_literature(record_id, operation)
        elif model_name == 'news':
            result = Neo4jSyncService.sync_news(record_id, operation)
        elif model_name == 'recall':
            result = Neo4jSyncService.sync_recall(record_id, operation)
        elif model_name == 'product':
            result = Neo4jSyncService.sync_product(record_id, operation)
        elif model_name == 'allergen':
            result = Neo4jSyncService.sync_allergen(record_id, operation)
        elif model_name == 'category':
            result = Neo4jSyncService.sync_category(record_id, operation)
        elif model_name == 'type':
            result = Neo4jSyncService.sync_type(record_id, operation)
        elif model_name == 'symptom1':
            result = Neo4jSyncService.sync_symptom1(record_id, operation)
        elif model_name == 'symptom2':
            result = Neo4jSyncService.sync_symptom2(record_id, operation)
        elif model_name == 'symptom3':
            result = Neo4jSyncService.sync_symptom3(record_id, operation)
        else:
            logger.warning(f"Unsupported model for Neo4j sync: {model_name}")
            return False
        
        logger.info(f"Neo4j sync success: {model_name} ID={record_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to sync {model_name} {record_id} to Neo4j: {e}")
        return False
