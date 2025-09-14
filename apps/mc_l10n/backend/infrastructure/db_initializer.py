"""
TH-Suite v2.1 数据库初始化工具
自动创建数据库和表结构，支持首次运行时初始化
"""

import sqlite3
import structlog
from pathlib import Path
from typing import Optional

logger = structlog.get_logger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.schema_file = Path(__file__).parent.parent / "migrations" / "002_optimized_database_schema.sql"
    
    def ensure_database_exists(self) -> bool:
        """确保数据库存在，如果不存在则创建"""
        try:
            # 确保数据目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查数据库是否存在
            if self.db_path.exists():
                logger.info(f"📊 数据库已存在: {self.db_path}")
                return self._verify_database_schema()
            
            # 创建新数据库
            logger.info(f"🆕 创建新数据库: {self.db_path}")
            return self._create_database()
            
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False
    
    def _create_database(self) -> bool:
        """创建数据库和表结构"""
        try:
            # 读取 SQL 架构文件
            if not self.schema_file.exists():
                logger.error(f"❌ 找不到数据库架构文件: {self.schema_file}")
                return False
            
            schema_sql = self.schema_file.read_text(encoding='utf-8')
            
            # 创建数据库连接并执行 SQL
            conn = sqlite3.connect(str(self.db_path))
            conn.executescript(schema_sql)
            conn.close()
            
            logger.info(f"✅ 数据库创建成功: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            return False
    
    def _verify_database_schema(self) -> bool:
        """验证数据库表结构是否完整"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 检查核心表是否存在
            required_tables = [
                'packs', 'pack_versions', 'mod_version_instances',
                'pack_mod_relations', 'content_instances', 'pack_content_relations'
            ]
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            missing_tables = set(required_tables) - existing_tables
            
            if missing_tables:
                logger.warning(f"⚠️ 数据库缺少表: {missing_tables}")
                conn.close()
                
                # 尝试重新创建缺少的表
                return self._recreate_missing_tables(missing_tables)
            
            # 检查统计视图是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view' AND name='pack_version_stats'
            """)
            has_stats_view = bool(cursor.fetchall())
            
            if not has_stats_view:
                logger.warning("⚠️ 缺少统计视图，尝试重新创建")
                conn.close()
                return self._create_database()  # 重新执行完整架构
            
            conn.close()
            logger.info("✅ 数据库架构验证通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库验证失败: {e}")
            return False
    
    def _recreate_missing_tables(self, missing_tables: set) -> bool:
        """重新创建缺少的表"""
        try:
            logger.info(f"🔧 重新创建缺少的表: {missing_tables}")
            
            # 备份现有数据库
            backup_path = self.db_path.with_suffix('.backup.db')
            if self.db_path.exists():
                import shutil
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"📋 数据库已备份至: {backup_path}")
            
            # 重新创建完整架构
            return self._create_database()
            
        except Exception as e:
            logger.error(f"❌ 重新创建表失败: {e}")
            return False
    
    def get_database_stats(self) -> dict:
        """获取数据库统计信息"""
        try:
            if not self.db_path.exists():
                return {
                    "database_exists": False,
                    "error": "数据库文件不存在"
                }
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 获取表统计
            stats = {"database_exists": True}
            
            # 检查表是否存在并获取行数
            tables = ['packs', 'pack_versions', 'mod_version_instances', 
                     'pack_mod_relations', 'content_instances', 'pack_content_relations']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[f"{table}_count"] = count
                except sqlite3.OperationalError:
                    stats[f"{table}_count"] = 0
                    stats[f"{table}_missing"] = True
            
            # 获取总表数
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            stats["total_tables"] = cursor.fetchone()[0]
            
            # 获取视图数
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
            stats["total_views"] = cursor.fetchone()[0]
            
            # 数据库文件大小
            stats["database_size"] = self.db_path.stat().st_size
            stats["database_path"] = str(self.db_path)
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取数据库统计失败: {e}")
            return {
                "database_exists": False,
                "error": str(e)
            }


def ensure_v2_1_database(db_path: str) -> bool:
    """确保 V2.1 数据库存在的便捷函数"""
    initializer = DatabaseInitializer(db_path)
    return initializer.ensure_database_exists()


def get_v2_1_database_stats(db_path: str) -> dict:
    """获取 V2.1 数据库统计信息的便捷函数"""
    initializer = DatabaseInitializer(db_path)
    return initializer.get_database_stats()