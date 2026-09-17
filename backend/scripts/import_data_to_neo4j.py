#!/usr/bin/env python3
"""
Neo4j 数据导入脚本
支持两种导入方式：
1. 导入 Neo4j dump 文件 (neo4j.dump)
2. 从 MySQL 导入数据到 Neo4j

使用方法:
python backend/scripts/import_data_to_neo4j.py --action dump --dump-file backend/scripts/neo4j.dump
python backend/scripts/import_data_to_neo4j.py --action mysql
python backend/scripts/import_data_to_neo4j.py --action both --dump-file backend/scripts/neo4j.dump
"""

import argparse
import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jDataImporter:
    """Neo4j 数据导入器"""
    
    def __init__(self, neo4j_uri: str = None, neo4j_user: str = None, neo4j_password: str = None):
        from dotenv import load_dotenv
        load_dotenv()
        
        self.neo4j_uri = neo4j_uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = neo4j_user or os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = neo4j_password or os.getenv('NEO4J_PASSWORD', '123456789')
        
        # 设置环境变量供其他模块使用
        os.environ['NEO4J_URI'] = self.neo4j_uri
        os.environ['NEO4J_USER'] = self.neo4j_user
        os.environ['NEO4J_PASSWORD'] = self.neo4j_password
        
        self.driver = None
        
        logger.debug(f"初始化 Neo4j 导入器: {self.neo4j_uri}")
        
    def connect(self):
        """连接到 Neo4j 数据库"""
        try:
            from app.services.neo4j_client import Neo4jClient
            self.driver = Neo4jClient.get_driver()
            
            # 测试连接
            with self.driver.session() as session:
                session.run('RETURN 1')
            
            logger.info(f"✓ Neo4j 连接成功: {self.neo4j_uri}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Neo4j 连接失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            from app.services.neo4j_client import Neo4jClient
            Neo4jClient.close()
            logger.info("Neo4j 连接已关闭")
    
    def clear_database(self, confirm: bool = False):
        """清空 Neo4j 数据库"""
        if not confirm:
            logger.warning("清空数据库需要确认参数")
            return False
            
        try:
            with self.driver.session() as session:
                logger.warning("正在清空 Neo4j 数据库...")
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("✓ Neo4j 数据库已清空")
                return True
                
        except Exception as e:
            logger.error(f"✗ 清空数据库失败: {e}")
            return False
    
    def import_dump_file(self, dump_file_path: str, clear_first: bool = False):
        """导入 Neo4j dump 文件"""
        dump_path = Path(dump_file_path)
        
        if not dump_path.exists():
            logger.error(f"✗ Dump 文件不存在: {dump_path}")
            return False
        
        logger.info(f"开始导入 Neo4j dump 文件: {dump_path}")
        
        try:
            # 清空数据库 (如果请求)
            if clear_first:
                if not self.clear_database(confirm=True):
                    return False
            
            # 使用 neo4j-admin 工具导入 dump 文件
            # 注意：这需要 Neo4j 服务停止状态下进行
            logger.info("准备导入 dump 文件...")
            logger.warning("注意: 导入 dump 文件需要停止 Neo4j 服务")
            
            # 检查是否有 neo4j-admin 工具
            neo4j_admin_paths = [
                'neo4j-admin',  # 如果在 PATH 中
                '/usr/bin/neo4j-admin',  # Linux 默认路径
                '/opt/neo4j/bin/neo4j-admin',  # Linux 安装路径
                'C:\\Program Files\\Neo4j\\bin\\neo4j-admin.bat',  # Windows 默认路径
            ]
            
            neo4j_admin = None
            for path in neo4j_admin_paths:
                try:
                    result = subprocess.run([path, 'version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        neo4j_admin = path
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            if not neo4j_admin:
                logger.error("✗ 未找到 neo4j-admin 工具")
                logger.info("请确保 Neo4j 已正确安装并且 neo4j-admin 在 PATH 中")
                logger.info("或者手动使用以下命令导入:")
                logger.info(f"neo4j-admin database load --from-path={dump_path.parent} --overwrite-destination=true neo4j")
                return False
            
            # 构建导入命令
            # Neo4j 4.x+ 使用 database load 命令
            cmd = [
                neo4j_admin,
                'database', 'load',
                f'--from-path={dump_path.parent}',
                '--overwrite-destination=true',
                'neo4j'  # 数据库名称
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 执行导入命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✓ Neo4j dump 文件导入成功")
                logger.info("请重新启动 Neo4j 服务")
                return True
            else:
                logger.error(f"✗ Neo4j dump 导入失败:")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("✗ Neo4j dump 导入超时")
            return False
        except Exception as e:
            logger.error(f"✗ Neo4j dump 导入失败: {e}")
            return False
    
    def import_from_mysql(self, mysql_host: str = None, mysql_port: int = None, 
                         mysql_user: str = None, mysql_password: str = None, 
                         mysql_db: str = None, clear_first: bool = False):
        """从 MySQL 导入数据到 Neo4j"""
        
        # 使用默认值或环境变量
        mysql_host = mysql_host or os.getenv('POSTGRES_HOST', '127.0.0.1')
        mysql_port = mysql_port or int(os.getenv('POSTGRES_PORT', '5432'))
        mysql_user = mysql_user or os.getenv('POSTGRES_USER', 'postgres')
        mysql_password = mysql_password or os.getenv('POSTGRES_PASSWORD', '123456')
        mysql_db = mysql_db or os.getenv('POSTGRES_DB', 'medical_system')
        
        # 验证必要参数
        if not all([mysql_host, mysql_port, mysql_user, mysql_db]):
            raise ValueError("MySQL 连接参数不完整")
        
        logger.info(f"开始从 MySQL 导入数据到 Neo4j")
        logger.info(f"MySQL: {mysql_host}:{mysql_port}/{mysql_db}")
        
        try:
            # 导入必要的模块
            from app import create_app, db
            from app.models import (
                Literature, News, Recall, Category, Type, Product, Allergen,
                Symptom1, Symptom2, Symptom3, AllergenProduct, AllergenSymptom, ProductSymptom
            )
            from app.services.neo4j_sync import Neo4jSyncService
            
            # 创建 Flask 应用上下文
            app = create_app()
            
            # 设置数据库连接
            app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}'
            
            with app.app_context():
                # 测试 MySQL 连接
                try:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('SELECT 1'))
                    logger.info(f"✓ MySQL 连接成功: {mysql_host}:{mysql_port}/{mysql_db}")
                except Exception as e:
                    logger.error(f"✗ MySQL 连接失败: {e}")
                    return False
                
                # 清空 Neo4j 数据库 (如果请求)
                if clear_first:
                    if not self.clear_database(confirm=True):
                        return False
                
                # 导入顺序：先导入基础实体，再导入关系
                import_steps = [
                    # 第一步：导入基础实体
                    ('文献', Literature, 'sync_literature'),
                    ('新闻', News, 'sync_news'),
                    ('召回', Recall, 'sync_recall'),
                    ('化学应激源', Allergen, 'sync_allergen'),
                    
                    # 第二步：导入产品层级 (按层级顺序)
                    ('产品种类', Category, 'sync_category'),
                    ('产品类型', Type, 'sync_type'),
                    ('产品', Product, 'sync_product'),
                    
                    # 第三步：导入症状层级 (按层级顺序)
                    ('症状种类', Symptom1, 'sync_symptom1'),
                    ('症状类型', Symptom2, 'sync_symptom2'),
                    ('具体症状', Symptom3, 'sync_symptom3'),
                ]
                
                # 导入基础实体
                total_success = 0
                total_records = 0
                
                for entity_name, model_class, sync_method in import_steps:
                    try:
                        logger.info(f"导入{entity_name}...")
                        
                        # 获取所有记录
                        records = model_class.query.all()
                        total = len(records)
                        total_records += total
                        
                        if total == 0:
                            logger.warning(f"⚠ {entity_name}: 无数据")
                            continue
                        
                        success_count = 0
                        for i, record in enumerate(records, 1):
                            try:
                                # 调用对应的同步方法
                                sync_func = getattr(Neo4jSyncService, sync_method)
                                if sync_func(record.id, 'create'):
                                    success_count += 1
                                
                                if i % 100 == 0 or i == total:
                                    logger.info(f"  进度: {i}/{total} ({success_count} 成功)")
                                    
                            except Exception as e:
                                logger.debug(f"  ✗ {entity_name} ID {record.id} 导入失败: {e}")
                                continue
                        
                        total_success += success_count
                        logger.info(f"✓ {entity_name}: {success_count}/{total} 导入成功")
                        
                    except Exception as e:
                        logger.error(f"✗ {entity_name} 导入失败: {e}")
                        continue
                
                # 导入关系数据
                relationship_steps = [
                    ('化学应激源-产品关系', AllergenProduct, 'sync_allergen_product_relation'),
                    ('化学应激源-症状关系', AllergenSymptom, 'sync_allergen_symptom_relation'),
                    ('产品-症状关系', ProductSymptom, 'sync_product_symptom_relation'),
                ]
                
                for rel_name, model_class, sync_method in relationship_steps:
                    try:
                        logger.info(f"导入{rel_name}...")
                        
                        # 获取所有关系记录
                        relations = model_class.query.all()
                        total = len(relations)
                        
                        if total == 0:
                            logger.warning(f"⚠ {rel_name}: 无数据")
                            continue
                        
                        success_count = 0
                        for i, relation in enumerate(relations, 1):
                            try:
                                # 根据关系类型调用不同的同步方法
                                sync_func = getattr(Neo4jSyncService, sync_method)
                                
                                if model_class == AllergenProduct:
                                    success = sync_func(
                                        allergen_id=relation.allergen_id,
                                        product_id=relation.product_id,
                                        relation_id=relation.id,
                                        operation='create',
                                        note=getattr(relation, 'note', '')
                                    )
                                elif model_class == AllergenSymptom:
                                    success = sync_func(
                                        allergen_id=relation.allergen_id,
                                        symptom_id=relation.symptom_id,
                                        relation_id=relation.id,
                                        traec_score=getattr(relation, 'traec_score', 0.0),
                                        operation='create'
                                    )
                                elif model_class == ProductSymptom:
                                    success = sync_func(
                                        product_id=relation.product_id,
                                        symptom_id=relation.symptom_id,
                                        relation_id=relation.id,
                                        operation='create'
                                    )
                                else:
                                    success = False
                                
                                if success:
                                    success_count += 1
                                
                                if i % 50 == 0 or i == total:
                                    logger.info(f"  进度: {i}/{total} ({success_count} 成功)")
                                    
                            except Exception as e:
                                logger.debug(f"  ✗ {rel_name} ID {relation.id} 导入失败: {e}")
                                continue
                        
                        logger.info(f"✓ {rel_name}: {success_count}/{total} 导入成功")
                        
                    except Exception as e:
                        logger.error(f"✗ {rel_name} 导入失败: {e}")
                        continue
                
                # 验证导入结果
                self._verify_import_results()
                
                logger.info("✓ MySQL 到 Neo4j 数据导入完成!")
                return True
                
        except ImportError as e:
            logger.error(f"✗ 缺少必要的依赖模块: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ MySQL 到 Neo4j 导入失败: {e}")
            return False
    
    def _verify_import_results(self):
        """验证导入结果"""
        logger.info("验证导入结果...")
        try:
            with self.driver.session() as session:
                # 统计节点数量
                node_stats = session.run("""
                    MATCH (n) 
                    RETURN labels(n)[0] as label, count(n) as count 
                    ORDER BY label
                """)
                
                logger.info("节点统计:")
                total_nodes = 0
                for record in node_stats:
                    label = record['label']
                    count = record['count']
                    total_nodes += count
                    logger.info(f"  {label}: {count}")
                
                # 统计关系数量
                rel_stats = session.run("""
                    MATCH ()-[r]->() 
                    RETURN type(r) as relationship_type, count(r) as count 
                    ORDER BY relationship_type
                """)
                
                logger.info("关系统计:")
                total_rels = 0
                for record in rel_stats:
                    rel_type = record['relationship_type']
                    count = record['count']
                    total_rels += count
                    logger.info(f"  {rel_type}: {count}")
                
                logger.info(f"✓ 导入完成: 总节点 {total_nodes}, 总关系 {total_rels}")
                
        except Exception as e:
            logger.warning(f"⚠ 验证失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Neo4j 数据导入工具')
    parser.add_argument('--action', choices=['dump', 'mysql', 'both'], required=True,
                       help='导入类型: dump(导入dump文件), mysql(从MySQL导入), both(两者都执行)')
    
    # MySQL 参数组
    mysql_group = parser.add_argument_group('MySQL 连接参数')
    mysql_group.add_argument('--mysql-host', default=os.getenv('POSTGRES_HOST', '127.0.0.1'), help='数据库主机地址')
    mysql_group.add_argument('--mysql-port', type=int, default=int(os.getenv('POSTGRES_PORT', '5432')), help='数据库端口号')
    mysql_group.add_argument('--mysql-user', default=os.getenv('POSTGRES_USER', 'postgres'), help='数据库用户名')
    mysql_group.add_argument('--mysql-password', default=os.getenv('POSTGRES_PASSWORD', '123456'), help='数据库密码')
    mysql_group.add_argument('--mysql-db', default=os.getenv('POSTGRES_DB', 'medical_system'), help='数据库名')
    
    # Neo4j 参数组
    neo4j_group = parser.add_argument_group('Neo4j 连接参数')
    neo4j_group.add_argument('--neo4j-uri', default=os.getenv('NEO4J_URI', 'bolt://localhost:7687'), help='Neo4j 连接URI')
    neo4j_group.add_argument('--neo4j-user', default=os.getenv('NEO4J_USER', 'neo4j'), help='Neo4j 用户名')
    neo4j_group.add_argument('--neo4j-password', default=os.getenv('NEO4J_PASSWORD', '123456789'), help='Neo4j 密码')
    
    # 文件参数组
    file_group = parser.add_argument_group('文件参数')
    file_group.add_argument('--dump-file', default=os.path.join(os.path.dirname(__file__), 'neo4j.dump'), 
                           help='Neo4j dump 文件路径 (默认: backend/scripts/neo4j.dump)')
    
    # 其他参数
    parser.add_argument('--clear', action='store_true', help='导入前清空 Neo4j 数据库')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建导入器
    importer = Neo4jDataImporter(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )
    
    # 验证文件路径
    if args.action in ['dump', 'both']:
        dump_path = Path(args.dump_file)
        if not dump_path.exists():
            logger.error(f"Dump 文件不存在: {dump_path}")
            return 1
    
    # 显示配置信息
    logger.info("=== 配置信息 ===")
    logger.info(f"导入类型: {args.action}")
    logger.info(f"Neo4j URI: {args.neo4j_uri}")
    logger.info(f"Neo4j User: {args.neo4j_user}")
    if args.action in ['mysql', 'both']:
        logger.info(f"MySQL: {args.mysql_user}@{args.mysql_host}:{args.mysql_port}/{args.mysql_db}")
    if args.action in ['dump', 'both']:
        logger.info(f"Dump 文件: {args.dump_file}")
    logger.info(f"清空数据库: {'是' if args.clear else '否'}")
    logger.info(f"详细输出: {'是' if args.verbose else '否'}")
    logger.info("==================")
    
    try:
        # 连接到 Neo4j
        if not importer.connect():
            logger.error("无法连接到 Neo4j 数据库")
            return 1
        
        success = True
        
        # 执行导入操作
        if args.action in ['dump', 'both']:
            logger.info("=== 导入 Neo4j Dump 文件 ===")
            try:
                if not importer.import_dump_file(args.dump_file, clear_first=args.clear):
                    success = False
                    logger.error("Dump 文件导入失败")
                
                # 如果导入了 dump 文件，需要重新连接
                if success and args.action == 'both':
                    logger.info("等待 Neo4j 服务重启后继续...")
                    logger.info("请按以下步骤操作:")
                    logger.info("1. 重启 Neo4j 服务")
                    logger.info("2. 确认服务正常启动")
                    logger.info("3. 按 Enter 键继续 MySQL 数据导入")
                    input("按 Enter 继续...")
                    
                    importer.close()
                    if not importer.connect():
                        logger.error("重新连接 Neo4j 失败")
                        return 1
            except Exception as e:
                logger.error(f"Dump 文件导入过程中出现异常: {e}")
                success = False
        
        if args.action in ['mysql', 'both']:
            logger.info("=== 从 MySQL 导入数据 ===")
            try:
                clear_for_mysql = args.clear and args.action == 'mysql'  # 只有纯 MySQL 导入时才清空
                if not importer.import_from_mysql(
                    mysql_host=args.mysql_host,
                    mysql_port=args.mysql_port,
                    mysql_user=args.mysql_user,
                    mysql_password=args.mysql_password,
                    mysql_db=args.mysql_db,
                    clear_first=clear_for_mysql
                ):
                    success = False
                    logger.error("MySQL 数据导入失败")
            except Exception as e:
                logger.error(f"MySQL 数据导入过程中出现异常: {e}")
                success = False
        
        if success:
            logger.info("🎉 所有数据导入完成!")
            return 0
        else:
            logger.error("❌ 数据导入过程中出现错误")
            return 1
            
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return 1
        
    finally:
        importer.close()


if __name__ == '__main__':
    exit(main())


"""
Neo4j 数据导入工具使用说明

支持的命令行参数:

基本参数:
  --action {dump,mysql,both}    指定导入类型 (必需)
                                dump: 导入 Neo4j dump 文件
                                mysql: 从 MySQL 导入数据
                                both: 先导入 dump 文件，再导入 MySQL 数据

MySQL 连接参数:
  --mysql-host HOST             MySQL 主机地址
                                (默认: 从环境变量 MYSQL_HOST 获取，或使用 '127.0.0.1')
  --mysql-port PORT             MySQL 端口号
                                (默认: 从环境变量 MYSQL_PORT 获取，或使用 3306)
  --mysql-user USER             MySQL 用户名
                                (默认: 从环境变量 MYSQL_USER 获取，或使用 'root')
  --mysql-password PASSWORD     MySQL 密码
                                (默认: 从环境变量 MYSQL_PASSWORD 获取，或使用 '123456')
  --mysql-db DB                MySQL 数据库名称
                                (默认: 从环境变量 MYSQL_DB 获取，或使用 'medical_system')

Neo4j 连接参数:
  --neo4j-uri URI              Neo4j 连接URI
                                (默认: 从环境变量 NEO4J_URI 获取，或使用 'bolt://localhost:7687')
  --neo4j-user USER            Neo4j 用户名
                                (默认: 从环境变量 NEO4J_USER 获取，或使用 'neo4j')
  --neo4j-password PASSWORD    Neo4j 密码
                                (默认: 从环境变量 NEO4J_PASSWORD 获取，或使用 '123456789')

文件参数:
  --dump-file FILE             Neo4j dump 文件路径
                                (默认: backend/scripts/neo4j.dump)

其他参数:
  --clear                      导入前清空 Neo4j 数据库
  --verbose                    详细输出 (调试模式)

使用示例:

1. 仅导入 Neo4j dump 文件:
   
   导入默认 dump 文件:
   python backend/scripts/import_data_to_neo4j.py --action dump
   
   指定 dump 文件路径:
   python backend/scripts/import_data_to_neo4j.py --action dump --dump-file /path/to/your/neo4j.dump
   
   清空数据库后导入:
   python backend/scripts/import_data_to_neo4j.py --action dump --clear

2. 仅从 MySQL 导入数据:
   
   使用默认配置:
   python backend/scripts/import_data_to_neo4j.py --action mysql
   
   指定 MySQL 连接参数:
   python backend/scripts/import_data_to_neo4j.py --action mysql --mysql-host localhost --mysql-port 3306 --mysql-user root --mysql-password mypassword --mysql-db medical_system
   
   清空 Neo4j 后导入:
   python backend/scripts/import_data_to_neo4j.py --action mysql --clear

3. 完整导入 (推荐):
   
   先导入 dump 文件，再导入 MySQL 数据:
   python backend/scripts/import_data_to_neo4j.py --action both
   
   指定所有参数:
   python backend/scripts/import_data_to_neo4j.py --action both --dump-file backend/scripts/neo4j.dump --mysql-host localhost --mysql-port 3306 --mysql-user root --mysql-password 123456 --mysql-db medical_system --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password 123456789
   
   清空数据库后完整导入:
   python backend/scripts/import_data_to_neo4j.py --action both --clear

4. 使用环境变量:
   
   设置环境变量后使用默认配置:
   export MYSQL_HOST=localhost
   export MYSQL_PORT=3306
   export MYSQL_USER=root
   export MYSQL_PASSWORD=mypassword
   export MYSQL_DB=medical_system
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=mypassword
   
   python backend/scripts/import_data_to_neo4j.py --action both

注意事项:
1. Neo4j dump 文件导入需要停止 Neo4j 服务，导入完成后需要重启服务
2. 脚本会自动检测 neo4j-admin 工具，确保 Neo4j 已正确安装
3. MySQL 导入使用现有的同步服务，确保数据格式兼容
4. 使用 --verbose 参数可以查看详细的导入过程和调试信息
5. 建议在导入前备份现有的 Neo4j 数据库
6. 大型数据库的导入可能需要较长时间，请耐心等待
7. 如果导入过程中出现错误，脚本会跳过失败的记录并继续导入
8. 导入完成后会显示统计信息，包括节点和关系的数量
"""
