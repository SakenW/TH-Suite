"""
TH-Suite 数据库初始化工具
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
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.schema_files = [
            self.migrations_dir / "001_create_core_tables.sql",
            self.migrations_dir / "002_create_operations_tables.sql",
            self.migrations_dir / "003_create_configuration_tables.sql",
            self.migrations_dir / "004_create_cache_tables.sql",
            self.migrations_dir / "005_create_scan_tables.sql",
            self.migrations_dir / "006_create_indexes_and_constraints.sql",
            self.migrations_dir / "007_create_views.sql",
            self.migrations_dir / "008_create_triggers.sql",
            self.migrations_dir / "009_insert_default_data.sql",
            self.migrations_dir / "010_create_translation_state_management.sql",
            self.migrations_dir / "011_insert_default_translation_states.sql"
        ]
    
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
            # 按顺序执行所有migration文件
            conn = sqlite3.connect(str(self.db_path))
            
            for schema_file in self.schema_files:
                if not schema_file.exists():
                    logger.error(f"❌ 找不到数据库架构文件: {schema_file}")
                    conn.close()
                    return False
                
                logger.info(f"📋 执行迁移文件: {schema_file.name}")
                schema_sql = schema_file.read_text(encoding='utf-8')
                
                # 执行迁移SQL
                conn.executescript(schema_sql)
                logger.info(f"✅ 迁移文件执行成功: {schema_file.name}")
            
            conn.close()
            logger.info(f"✅ 数据库创建成功: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def _verify_database_schema(self) -> bool:
        """验证数据库表结构是否完整"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 检查V5架构完整表结构是否存在（19个表）
            required_tables = [
                # Core tables (9个)
                'core_projects', 'core_packs', 'core_pack_versions', 'core_mods',
                'core_mod_versions', 'core_pack_installations', 'core_pack_items',
                'core_language_files', 'core_translation_entries',
                # Operations tables (4个)  
                'ops_work_queue', 'ops_sync_log', 'ops_cas_objects', 'ops_outbox_journal',
                # Configuration tables (2个)
                'cfg_local_settings', 'cfg_file_watch',
                # Cache tables (4个)
                'cache_entry', 'cache_lang_file', 'cache_scan_results', 'cache_stats'
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
            
            # 检查V5架构视图是否存在（如果有的话）
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view'
            """)
            views = cursor.fetchall()
            has_views = len(views) > 0
            
            # V5架构暂时不需要特殊视图检查
            # 如果后续有视图需求，可以在这里添加检查
            
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
    
    def _recreate_views_only(self) -> bool:
        """仅重新创建视图和索引，不清除表数据"""
        try:
            logger.info("🔧 重新创建数据库视图和索引（保留数据）")
            
            # 读取所有架构文件
            all_schema_sql = ""
            for schema_file in self.schema_files:
                if not schema_file.exists():
                    logger.error(f"❌ 找不到数据库架构文件: {schema_file}")
                    return False
                
                schema_sql = schema_file.read_text(encoding='utf-8')
                all_schema_sql += "\n" + schema_sql
            
            # 只执行CREATE VIEW和CREATE INDEX语句，跳过CREATE TABLE
            conn = sqlite3.connect(str(self.db_path))
            
            # 分行执行，只处理视图和索引
            for line in all_schema_sql.split('\n'):
                line = line.strip()
                if line.startswith('CREATE VIEW') or line.startswith('CREATE INDEX') or line.startswith('CREATE TRIGGER'):
                    try:
                        # 对于多行语句，需要找到完整的语句
                        if 'CREATE VIEW' in line:
                            # 找到视图创建语句的完整内容
                            view_start = all_schema_sql.find(line)
                            view_end = all_schema_sql.find(';', view_start) + 1
                            view_sql = all_schema_sql[view_start:view_end]
                            conn.execute(view_sql)
                            logger.info(f"✅ 重新创建视图: {line}")
                        elif line.endswith(';'):
                            conn.execute(line)
                            logger.info(f"✅ 执行: {line[:50]}...")
                    except sqlite3.Error as e:
                        # 忽略已存在的错误
                        if "already exists" not in str(e):
                            logger.warning(f"⚠️ SQL执行警告: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info("✅ 视图和索引重新创建成功（数据已保留）")
            return True
            
        except Exception as e:
            logger.error(f"❌ 重新创建视图失败: {e}")
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
            
            # 检查V5架构表是否存在并获取行数
            tables = ['core_projects', 'core_packs', 'core_pack_versions', 
                     'core_mods', 'core_pack_installations', 'ops_work_queue']
            
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


def ensure_database(db_path: str) -> bool:
    """确保数据库存在的便捷函数"""
    initializer = DatabaseInitializer(db_path)
    return initializer.ensure_database_exists()


def get_database_stats(db_path: str) -> dict:
    """获取数据库统计信息的便捷函数"""
    initializer = DatabaseInitializer(db_path)
    return initializer.get_database_stats()