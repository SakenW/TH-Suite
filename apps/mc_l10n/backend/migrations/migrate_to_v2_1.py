#!/usr/bin/env python3
"""
TH-Suite 数据库迁移脚本 v2.0 → v2.1
基于 docs/optimization/02-database-optimization.md 的优化方案

主要变更:
- 实现细粒度版本管理
- 数据分层设计 (本地构建数据 vs 同步业务数据)
- 统一内容映射系统
- 消除冗余的聚合字段
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class DatabaseMigrationV21:
    """数据库迁移器 v2.0 → v2.1"""
    
    def __init__(self, db_path: str, backup_path: Optional[str] = None):
        self.db_path = Path(db_path)
        self.backup_path = Path(backup_path) if backup_path else None
        self.conn: Optional[sqlite3.Connection] = None
        
    async def run_migration(self) -> bool:
        """执行完整的数据库迁移"""
        try:
            await self._backup_database()
            await self._connect_database()
            
            # 检查是否需要迁移
            if await self._is_already_migrated():
                logger.info("数据库已经是v2.1版本，跳过迁移")
                return True
                
            # 执行迁移步骤
            await self._create_new_tables()
            await self._migrate_existing_data()
            await self._verify_migration()
            await self._cleanup_old_tables()
            
            logger.info("数据库迁移到v2.1完成!")
            return True
            
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            await self._rollback_migration()
            return False
        finally:
            if self.conn:
                self.conn.close()
    
    async def _backup_database(self) -> None:
        """备份现有数据库"""
        if not self.db_path.exists():
            logger.info("数据库文件不存在，跳过备份")
            return
            
        backup_path = self.backup_path or self.db_path.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        
        # 使用SQLite的备份API
        source_conn = sqlite3.connect(str(self.db_path))
        backup_conn = sqlite3.connect(str(backup_path))
        
        try:
            source_conn.backup(backup_conn)
            logger.info(f"数据库备份完成: {backup_path}")
        finally:
            source_conn.close()
            backup_conn.close()
    
    async def _connect_database(self) -> None:
        """连接数据库"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # 启用列名访问
        self.conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
    
    async def _is_already_migrated(self) -> bool:
        """检查是否已经迁移到v2.1"""
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='packs'
        """)
        return cursor.fetchone() is not None
    
    async def _create_new_tables(self) -> None:
        """创建新的表结构"""
        logger.info("创建新的表结构...")
        
        # 读取并执行新的schema
        migration_sql_path = Path(__file__).parent / "002_optimized_database_schema.sql"
        
        with open(migration_sql_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # 分割并执行SQL语句
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement.startswith('--') or not statement:
                continue
            try:
                self.conn.execute(statement)
            except sqlite3.Error as e:
                logger.warning(f"执行SQL语句失败 (可能是已存在): {e}")
        
        self.conn.commit()
        logger.info("新表结构创建完成")
    
    async def _migrate_existing_data(self) -> None:
        """迁移现有数据到新结构"""
        logger.info("开始迁移现有数据...")
        
        # 检查是否有旧的projects表
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='projects'
        """)
        
        if not cursor.fetchone():
            logger.info("没有找到旧的projects表，创建示例数据")
            await self._create_sample_data()
            return
        
        # 迁移projects → packs + pack_versions
        await self._migrate_projects()
        
        # 迁移mods → mod_version_instances + pack_mod_relations
        await self._migrate_mods()
        
        # 迁移language_files → content_instances + pack_content_relations
        await self._migrate_language_files()
        
        self.conn.commit()
        logger.info("数据迁移完成")
    
    async def _migrate_projects(self) -> None:
        """迁移项目数据"""
        logger.info("迁移项目数据...")
        
        cursor = self.conn.execute("SELECT * FROM projects WHERE is_active = 1")
        projects = cursor.fetchall()
        
        for project in projects:
            # 创建pack记录
            pack_id = await self._insert_pack(project)
            
            # 创建默认版本
            await self._insert_default_pack_version(pack_id, project)
        
        logger.info(f"迁移了 {len(projects)} 个项目")
    
    async def _insert_pack(self, project: sqlite3.Row) -> int:
        """插入pack记录"""
        cursor = self.conn.execute("""
            INSERT INTO packs (
                name, project_type, game_type, description, author,
                path, sync_config, build_config, 
                created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project['name'],
            project.get('project_type', 'modpack'),
            project.get('game_type', 'minecraft'),
            project.get('description', ''),
            project.get('author', ''),
            project['path'],
            json.dumps({"sync_enabled": True}),
            json.dumps({"auto_build": False}),
            project['created_at'],
            project['updated_at'],
            project['is_active']
        ))
        
        return cursor.lastrowid
    
    async def _insert_default_pack_version(self, pack_id: int, project: sqlite3.Row) -> int:
        """插入默认包版本"""
        # 解析minecraft_versions
        mc_versions = []
        if project.get('minecraft_versions'):
            try:
                mc_versions = json.loads(project['minecraft_versions'])
            except:
                mc_versions = [project['minecraft_versions']]
        
        # 使用第一个MC版本或默认值
        minecraft_version = mc_versions[0] if mc_versions else "1.20.1"
        
        cursor = self.conn.execute("""
            INSERT INTO pack_versions (
                pack_id, version_tag, minecraft_version, loader_type, 
                display_name, is_default, is_stable, local_path,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pack_id,
            "default",
            minecraft_version,
            project.get('loader_type', 'forge'),
            f"{project['name']} Default Version",
            1,  # 默认版本
            1,  # 稳定版本
            project['path'],
            project['created_at'],
            project['updated_at']
        ))
        
        return cursor.lastrowid
    
    async def _migrate_mods(self) -> None:
        """迁移MOD数据"""
        logger.info("迁移MOD数据...")
        
        # 检查mods表是否存在
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='mods'
        """)
        
        if not cursor.fetchone():
            logger.info("没有找到mods表，跳过MOD迁移")
            return
        
        cursor = self.conn.execute("SELECT * FROM mods")
        mods = cursor.fetchall()
        
        for mod in mods:
            # 创建mod_version_instances记录
            mod_instance_id = await self._insert_mod_instance(mod)
            
            # 创建pack_mod_relations记录
            await self._link_mod_to_pack_version(mod_instance_id, mod)
        
        logger.info(f"迁移了 {len(mods)} 个MOD")
    
    async def _insert_mod_instance(self, mod: sqlite3.Row) -> int:
        """插入MOD版本实例"""
        cursor = self.conn.execute("""
            INSERT INTO mod_version_instances (
                mod_id, mod_version, mod_name, description, authors,
                jar_file_path, jar_file_size, jar_file_hash,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mod.get('mod_id', mod['name'].lower().replace(' ', '_')),
            mod.get('version', '1.0.0'),
            mod['name'],
            mod.get('description', ''),
            json.dumps([mod.get('author', 'Unknown')]),
            mod.get('jar_path', ''),
            mod.get('file_size', 0),
            mod.get('file_hash', ''),
            mod['created_at'],
            mod['updated_at']
        ))
        
        return cursor.lastrowid
    
    async def _link_mod_to_pack_version(self, mod_instance_id: int, mod: sqlite3.Row) -> None:
        """链接MOD到包版本"""
        # 查找对应的pack_version
        cursor = self.conn.execute("""
            SELECT pv.id 
            FROM pack_versions pv
            JOIN packs p ON pv.pack_id = p.id
            WHERE p.id = (
                SELECT id FROM projects WHERE id = ? LIMIT 1
            )
        """, (mod.get('project_id', 1),))
        
        pack_version = cursor.fetchone()
        if not pack_version:
            logger.warning(f"找不到MOD {mod['name']} 对应的pack_version")
            return
        
        self.conn.execute("""
            INSERT INTO pack_mod_relations (
                pack_version_id, mod_instance_id, relation_type,
                detection_method, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            pack_version['id'],
            mod_instance_id,
            'included',
            'migration_v2_1',
            datetime.now().isoformat()
        ))
    
    async def _migrate_language_files(self) -> None:
        """迁移语言文件数据"""
        logger.info("迁移语言文件数据...")
        
        # 检查language_files表是否存在
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='language_files'
        """)
        
        if not cursor.fetchone():
            logger.info("没有找到language_files表，跳过语言文件迁移")
            return
        
        cursor = self.conn.execute("SELECT * FROM language_files")
        language_files = cursor.fetchall()
        
        for lang_file in language_files:
            # 创建content_instances记录
            content_instance_id = await self._insert_content_instance(lang_file)
            
            # 创建pack_content_relations记录
            await self._link_content_to_pack_version(content_instance_id, lang_file)
        
        logger.info(f"迁移了 {len(language_files)} 个语言文件")
    
    async def _insert_content_instance(self, lang_file: sqlite3.Row) -> int:
        """插入内容实例"""
        # 解析文件内容创建多个条目
        content_data = []
        
        # 如果有content字段，解析JSON
        if lang_file.get('content'):
            try:
                parsed_content = json.loads(lang_file['content'])
                for key, value in parsed_content.items():
                    content_data.append((key, value))
            except:
                # 如果解析失败，创建单个条目
                content_data.append((lang_file.get('file_name', 'unknown'), ''))
        else:
            content_data.append((lang_file.get('file_name', 'unknown'), ''))
        
        # 插入第一个内容实例并返回ID
        if content_data:
            key, value = content_data[0]
            cursor = self.conn.execute("""
                INSERT INTO content_instances (
                    content_key, content_source, source_identifier,
                    source_text, language_code, content_type, category,
                    file_path, file_format, raw_content,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                'mod_jar',  # 默认来源
                lang_file.get('mod_id', 'unknown'),
                value,
                lang_file.get('language', 'en_us'),
                'translation',
                'gui',
                lang_file.get('file_path', ''),
                lang_file.get('file_format', 'json'),
                lang_file.get('content', ''),
                lang_file['created_at'],
                lang_file['updated_at']
            ))
            
            return cursor.lastrowid
        
        return 0
    
    async def _link_content_to_pack_version(self, content_instance_id: int, lang_file: sqlite3.Row) -> None:
        """链接内容到包版本"""
        # 查找对应的pack_version
        cursor = self.conn.execute("""
            SELECT pv.id 
            FROM pack_versions pv
            JOIN packs p ON pv.pack_id = p.id
            WHERE p.id = (
                SELECT id FROM projects WHERE id = ? LIMIT 1
            )
        """, (lang_file.get('project_id', 1),))
        
        pack_version = cursor.fetchone()
        if not pack_version:
            logger.warning(f"找不到语言文件对应的pack_version")
            return
        
        self.conn.execute("""
            INSERT INTO pack_content_relations (
                pack_version_id, content_instance_id, inclusion_reason,
                change_type, detection_method, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pack_version['id'],
            content_instance_id,
            'direct',
            'stable',
            'migration_v2_1',
            datetime.now().isoformat()
        ))
    
    async def _create_sample_data(self) -> None:
        """创建示例数据用于测试"""
        logger.info("创建示例数据...")
        
        # 创建示例pack
        cursor = self.conn.execute("""
            INSERT INTO packs (
                name, project_type, game_type, description, author,
                path, sync_config, build_config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "示例整合包",
            "modpack",
            "minecraft",
            "用于演示的示例整合包",
            "TH-Suite",
            "/path/to/example/pack",
            json.dumps({"sync_enabled": True}),
            json.dumps({"auto_build": False})
        ))
        
        pack_id = cursor.lastrowid
        
        # 创建示例版本
        self.conn.execute("""
            INSERT INTO pack_versions (
                pack_id, version_tag, minecraft_version, loader_type,
                display_name, is_default, is_stable
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pack_id,
            "v1.0.0",
            "1.20.1",
            "forge",
            "示例整合包 v1.0.0",
            1,
            1
        ))
        
        logger.info("示例数据创建完成")
    
    async def _verify_migration(self) -> None:
        """验证迁移结果"""
        logger.info("验证迁移结果...")
        
        # 检查表是否存在
        tables = ['packs', 'pack_versions', 'mod_version_instances', 
                 'pack_mod_relations', 'content_instances', 'pack_content_relations']
        
        for table in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"表 {table}: {count} 条记录")
        
        # 检查视图
        cursor = self.conn.execute("SELECT COUNT(*) FROM pack_version_stats")
        count = cursor.fetchone()[0]
        logger.info(f"视图 pack_version_stats: {count} 条记录")
        
        logger.info("数据验证完成")
    
    async def _cleanup_old_tables(self) -> None:
        """清理旧表 (可选)"""
        logger.info("保留旧表作为备份 (不删除)")
        # 出于安全考虑，我们不删除旧表
        # 用户可以手动删除: DROP TABLE projects; DROP TABLE mods; DROP TABLE language_files;
    
    async def _rollback_migration(self) -> None:
        """回滚迁移 (恢复备份)"""
        logger.error("开始回滚迁移...")
        # 在实际应用中，这里应该恢复备份数据库
        logger.info("请手动恢复数据库备份文件")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TH-Suite数据库迁移工具 v2.0→v2.1")
    parser.add_argument("--db-path", required=True, help="数据库文件路径")
    parser.add_argument("--backup-path", help="备份文件路径 (可选)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    
    args = parser.parse_args()
    
    # 配置日志
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger.info(f"开始数据库迁移: {args.db_path}")
    logger.info(f"备份路径: {args.backup_path or '自动生成'}")
    
    if args.dry_run:
        logger.info("试运行模式 - 不会实际修改数据库")
        return
    
    migrator = DatabaseMigrationV21(args.db_path, args.backup_path)
    success = await migrator.run_migration()
    
    if success:
        logger.info("✅ 数据库迁移成功完成!")
    else:
        logger.error("❌ 数据库迁移失败!")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))