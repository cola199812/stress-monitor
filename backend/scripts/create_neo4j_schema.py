#!/usr/bin/env python3
"""
Neo4j 数据库结构创建脚本
基于现有的 MySQL 数据结构和 Neo4j 同步服务生成对应的图数据库结构
"""

import os
import sys
import logging
from typing import Optional
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.app.services.neo4j_client import Neo4jClient
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jSchemaCreator:
    """Neo4j 数据库结构创建器"""
    
    def __init__(self):
        load_dotenv()
        self.driver = None
        
    def connect(self):
        """连接到 Neo4j 数据库"""
        try:
            self.driver = Neo4jClient.get_driver()
            logger.info("成功连接到 Neo4j 数据库")
            return True
        except Exception as e:
            logger.error(f"连接 Neo4j 失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            Neo4jClient.close()
            logger.info("已关闭 Neo4j 连接")
    
    def create_constraints(self):
        """创建唯一性约束和索引"""
        constraints = [
            # 文献节点约束
            "CREATE CONSTRAINT literature_id_unique IF NOT EXISTS FOR (l:文献) REQUIRE l.id IS UNIQUE",
            
            # 新闻节点约束
            "CREATE CONSTRAINT news_id_unique IF NOT EXISTS FOR (n:新闻) REQUIRE n.id IS UNIQUE",
            
            # 召回节点约束
            "CREATE CONSTRAINT recall_id_unique IF NOT EXISTS FOR (r:召回) REQUIRE r.id IS UNIQUE",
            
            # 产品层级约束
            "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:种类) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT type_id_unique IF NOT EXISTS FOR (t:类型) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:产品) REQUIRE p.id IS UNIQUE",
            
            # 化学应激源约束
            "CREATE CONSTRAINT allergen_id_unique IF NOT EXISTS FOR (a:化学应急源) REQUIRE a.id IS UNIQUE",
            
            # 症状层级约束
            "CREATE CONSTRAINT symptom1_id_unique IF NOT EXISTS FOR (s:症状种类) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT symptom2_id_unique IF NOT EXISTS FOR (s:症状类型) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT symptom3_id_unique IF NOT EXISTS FOR (s:具体症状) REQUIRE s.id IS UNIQUE",
            
            # 观点节点约束
            "CREATE CONSTRAINT viewpoint_id_unique IF NOT EXISTS FOR (v:观点) REQUIRE v.id IS UNIQUE",
        ]
        
        indexes = [
            # 名称索引
            "CREATE INDEX literature_title_index IF NOT EXISTS FOR (l:文献) ON (l.title)",
            "CREATE INDEX news_title_index IF NOT EXISTS FOR (n:新闻) ON (n.title)",
            "CREATE INDEX recall_title_index IF NOT EXISTS FOR (r:召回) ON (r.title)",
            "CREATE INDEX category_name_index IF NOT EXISTS FOR (c:种类) ON (c.name)",
            "CREATE INDEX type_name_index IF NOT EXISTS FOR (t:类型) ON (t.name)",
            "CREATE INDEX product_name_index IF NOT EXISTS FOR (p:产品) ON (p.name)",
            "CREATE INDEX allergen_name_index IF NOT EXISTS FOR (a:化学应急源) ON (a.name)",
            "CREATE INDEX symptom1_name_index IF NOT EXISTS FOR (s:症状种类) ON (s.name)",
            "CREATE INDEX symptom2_name_index IF NOT EXISTS FOR (s:症状类型) ON (s.name)",
            "CREATE INDEX symptom3_name_index IF NOT EXISTS FOR (s:具体症状) ON (s.name)",
            
            # 关系属性索引
            "CREATE INDEX viewpoint_type_index IF NOT EXISTS FOR (v:观点) ON (v.type)",
            "CREATE INDEX viewpoint_allergen_id_index IF NOT EXISTS FOR (v:观点) ON (v.allergen_id)",
            "CREATE INDEX viewpoint_product_id_index IF NOT EXISTS FOR (v:观点) ON (v.product_id)",
            "CREATE INDEX viewpoint_symptom_id_index IF NOT EXISTS FOR (v:观点) ON (v.symptom_id)",
        ]
        
        try:
            with self.driver.session() as session:
                logger.info("创建唯一性约束...")
                for constraint in constraints:
                    try:
                        session.run(constraint)
                        logger.info(f"✓ {constraint}")
                    except Exception as e:
                        logger.warning(f"约束创建失败 (可能已存在): {constraint} - {e}")
                
                logger.info("创建索引...")
                for index in indexes:
                    try:
                        session.run(index)
                        logger.info(f"✓ {index}")
                    except Exception as e:
                        logger.warning(f"索引创建失败 (可能已存在): {index} - {e}")
                        
            logger.info("约束和索引创建完成")
            return True
            
        except Exception as e:
            logger.error(f"创建约束和索引失败: {e}")
            return False
    
    def create_sample_data(self):
        """创建示例数据结构 (不包含实际数据)"""
        sample_queries = [
            # 创建示例产品层级结构
            """
            MERGE (c1:种类 {id: 'sample_category_1', name: '示例产品种类1'})
            MERGE (t1:类型 {id: 'sample_type_1', name: '示例产品类型1', parentId: 'sample_category_1'})
            MERGE (p1:产品 {id: 'sample_product_1', name: '示例产品1', parentId: 'sample_type_1'})
            MERGE (c1)-[:包含]->(t1)
            MERGE (t1)-[:包含]->(p1)
            """,
            
            # 创建示例症状层级结构
            """
            MERGE (s1:症状种类 {id: 'sample_symptom1_1', name: '示例症状种类1'})
            MERGE (s2:症状类型 {id: 'sample_symptom2_1', name: '示例症状类型1', parentId: 'sample_symptom1_1'})
            MERGE (s3:具体症状 {id: 'sample_symptom3_1', name: '示例具体症状1', parentId: 'sample_symptom2_1'})
            MERGE (s1)-[:包含症状类型]->(s2)
            MERGE (s2)-[:包含具体症状]->(s3)
            """,
            
            # 创建示例化学应激源
            """
            MERGE (a1:化学应急源 {
                id: 'sample_allergen_1', 
                name: '示例化学应激源1',
                cas_number: 'CAS-000-00-0',
                description: '这是一个示例化学应激源'
            })
            """,
            
            # 创建示例文献
            """
            MERGE (l1:文献 {
                id: 'sample_literature_1',
                title: '示例文献标题1',
                authors: '示例作者1, 示例作者2',
                pmid: 'PMID12345678',
                source: 'PubMed'
            })
            """,
            
            # 创建示例新闻
            """
            MERGE (n1:新闻 {
                id: 'sample_news_1',
                title: '示例新闻标题1',
                source: '示例新闻来源',
                url: 'https://example.com/news/1'
            })
            """,
            
            # 创建示例召回
            """
            MERGE (r1:召回 {
                id: 'sample_recall_1',
                title: '示例召回标题1',
                source: '示例召回来源',
                external_id: 'RECALL-001'
            })
            """,
            
            # 创建示例关系: 化学应激源 -> 观点 -> 具体症状
            """
            MATCH (a:化学应急源 {id: 'sample_allergen_1'})
            MATCH (s:具体症状 {id: 'sample_symptom3_1'})
            MERGE (v1:观点 {
                id: 'sample_viewpoint_1',
                type: 'allergen_symptom',
                allergen_id: 'sample_allergen_1',
                symptom_id: 'sample_symptom3_1',
                traec_score: 2.5
            })
            MERGE (a)-[:判断]->(v1)
            MERGE (v1)-[:导致]->(s)
            """,
            
            # 创建示例关系: 产品 -> 观点 -> 化学应激源
            """
            MATCH (p:产品 {id: 'sample_product_1'})
            MATCH (a:化学应急源 {id: 'sample_allergen_1'})
            MERGE (v2:观点 {
                id: 'sample_viewpoint_2',
                type: 'product_allergen',
                product_id: 'sample_product_1',
                allergen_id: 'sample_allergen_1',
                note: '示例产品包含化学应激源'
            })
            MERGE (p)-[:判断]->(v2)
            MERGE (v2)-[:包含]->(a)
            """,
            
            # 创建示例关系: 产品 -> 观点 -> 具体症状
            """
            MATCH (p:产品 {id: 'sample_product_1'})
            MATCH (s:具体症状 {id: 'sample_symptom3_1'})
            MERGE (v3:观点 {
                id: 'sample_viewpoint_3',
                type: 'product_symptom',
                product_id: 'sample_product_1',
                symptom_id: 'sample_symptom3_1'
            })
            MERGE (p)-[:判断]->(v3)
            MERGE (v3)-[:引发]->(s)
            """
        ]
        
        try:
            with self.driver.session() as session:
                logger.info("创建示例数据结构...")
                for i, query in enumerate(sample_queries, 1):
                    try:
                        session.run(query)
                        logger.info(f"✓ 示例数据 {i}/{len(sample_queries)} 创建成功")
                    except Exception as e:
                        logger.error(f"✗ 示例数据 {i} 创建失败: {e}")
                        
            logger.info("示例数据结构创建完成")
            return True
            
        except Exception as e:
            logger.error(f"创建示例数据失败: {e}")
            return False
    
    def verify_schema(self):
        """验证数据库结构"""
        verification_queries = [
            ("节点标签", "CALL db.labels() YIELD label RETURN label ORDER BY label"),
            ("关系类型", "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType"),
            ("约束", "SHOW CONSTRAINTS YIELD name, type RETURN name, type"),
            ("索引", "SHOW INDEXES YIELD name, type RETURN name, type"),
            ("节点统计", """
                MATCH (n) 
                RETURN labels(n)[0] as label, count(n) as count 
                ORDER BY label
            """),
            ("关系统计", """
                MATCH ()-[r]->() 
                RETURN type(r) as relationship_type, count(r) as count 
                ORDER BY relationship_type
            """)
        ]
        
        try:
            with self.driver.session() as session:
                logger.info("验证数据库结构...")
                
                for desc, query in verification_queries:
                    logger.info(f"\n=== {desc} ===")
                    try:
                        result = session.run(query)
                        records = list(result)
                        if records:
                            for record in records:
                                logger.info(f"  {dict(record)}")
                        else:
                            logger.info("  (无数据)")
                    except Exception as e:
                        logger.error(f"  查询失败: {e}")
                        
            return True
            
        except Exception as e:
            logger.error(f"验证数据库结构失败: {e}")
            return False
    
    def clear_database(self, confirm: bool = False):
        """清空数据库 (危险操作)"""
        if not confirm:
            logger.warning("清空数据库需要确认参数 confirm=True")
            return False
            
        try:
            with self.driver.session() as session:
                logger.warning("正在清空 Neo4j 数据库...")
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("数据库已清空")
                return True
                
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Neo4j 数据库结构创建工具')
    parser.add_argument('--clear', action='store_true', help='清空现有数据库 (危险操作)')
    parser.add_argument('--sample-data', action='store_true', help='创建示例数据')
    parser.add_argument('--verify-only', action='store_true', help='仅验证现有结构')
    
    args = parser.parse_args()
    
    creator = Neo4jSchemaCreator()
    
    try:
        # 连接数据库
        if not creator.connect():
            logger.error("无法连接到 Neo4j 数据库")
            return 1
        
        # 仅验证模式
        if args.verify_only:
            creator.verify_schema()
            return 0
        
        # 清空数据库 (如果请求)
        if args.clear:
            if not creator.clear_database(confirm=True):
                logger.error("清空数据库失败")
                return 1
        
        # 创建约束和索引
        if not creator.create_constraints():
            logger.error("创建约束和索引失败")
            return 1
        
        # 创建示例数据 (如果请求)
        if args.sample_data:
            if not creator.create_sample_data():
                logger.error("创建示例数据失败")
                return 1
        
        # 验证结构
        creator.verify_schema()
        
        logger.info("Neo4j 数据库结构创建完成!")
        return 0
        
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return 1
        
    finally:
        creator.close()


if __name__ == '__main__':
    exit(main())
