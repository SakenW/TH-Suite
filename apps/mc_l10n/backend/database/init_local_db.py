#!/usr/bin/env python
"""
本地数据库初始化脚本
用于创建和初始化MC L10n客户端的本地SQLite数据库
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LocalDatabaseInitializer:
    """本地数据库初始化器"""
    
    def __init__(self, db_path: str = "mc_l10n_local.db"):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        logger.info(f"连接到数据库: {self.db_path}")
        
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
            
    def create_tables(self):
        """创建所有本地数据库表"""
        
        # 1. 扫描缓存表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_cache (
            cache_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            scan_path TEXT NOT NULL,
            file_hash TEXT,
            scan_result TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_valid BOOLEAN DEFAULT TRUE,
            UNIQUE(scan_path, file_hash)
        )
        """)
        
        # 2. MOD发现表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS mod_discoveries (
            discovery_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            mod_id TEXT UNIQUE,
            mod_name TEXT NOT NULL,
            display_name TEXT,
            version TEXT,
            minecraft_version TEXT,
            mod_loader TEXT,
            file_path TEXT NOT NULL,
            file_hash TEXT,
            file_size INTEGER,
            language_count INTEGER DEFAULT 0,
            total_keys INTEGER DEFAULT 0,
            metadata TEXT,
            scan_result TEXT,
            is_uploaded BOOLEAN DEFAULT FALSE,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_at TIMESTAMP
        )
        """)
        
        # 3. 语言文件缓存表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS language_file_cache (
            cache_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            mod_id TEXT NOT NULL,
            language_code TEXT NOT NULL,
            file_path TEXT,
            file_format TEXT DEFAULT 'json',
            content TEXT,
            content_hash TEXT,
            entry_count INTEGER DEFAULT 0,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            UNIQUE(mod_id, language_code),
            FOREIGN KEY (mod_id) REFERENCES mod_discoveries(mod_id) ON DELETE CASCADE
        )
        """)
        
        # 4. 翻译条目缓存表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS translation_entry_cache (
            entry_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            cache_id TEXT NOT NULL,
            translation_key TEXT NOT NULL,
            original_text TEXT,
            translated_text TEXT,
            machine_translation TEXT,
            status TEXT DEFAULT 'pending',
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cache_id, translation_key),
            FOREIGN KEY (cache_id) REFERENCES language_file_cache(cache_id) ON DELETE CASCADE
        )
        """)
        
        # 5. 工作队列表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS work_queue (
            task_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            task_type TEXT NOT NULL,
            task_data TEXT,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scheduled_at TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
        
        # 6. 离线变更跟踪表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS offline_changes (
            change_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            change_data TEXT,
            conflict_resolution TEXT DEFAULT 'client_wins',
            is_synced BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_at TIMESTAMP
        )
        """)
        
        # 7. 本地设置表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS local_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string',
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 8. 本地项目表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS local_projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            target_language TEXT DEFAULT 'zh_cn',
            source_language TEXT DEFAULT 'en_us',
            scan_paths TEXT,
            include_patterns TEXT,
            exclude_patterns TEXT,
            auto_scan BOOLEAN DEFAULT FALSE,
            scan_interval INTEGER DEFAULT 3600,
            last_scan_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 9. 文件监控表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS file_watch (
            watch_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            project_id TEXT,
            watch_path TEXT NOT NULL,
            watch_type TEXT DEFAULT 'directory',
            include_patterns TEXT,
            exclude_patterns TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            last_check_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES local_projects(project_id) ON DELETE CASCADE
        )
        """)
        
        # 10. 同步日志表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            log_id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            sync_type TEXT NOT NULL,
            sync_direction TEXT,
            entity_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            conflict_count INTEGER DEFAULT 0,
            sync_data TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            duration_seconds REAL
        )
        """)
        
        logger.info("所有表创建完成")
        
    def create_indexes(self):
        """创建索引以优化查询性能"""
        
        indexes = [
            # 扫描缓存索引
            "CREATE INDEX IF NOT EXISTS idx_scan_cache_path ON scan_cache(scan_path)",
            "CREATE INDEX IF NOT EXISTS idx_scan_cache_hash ON scan_cache(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_scan_cache_expires ON scan_cache(expires_at)",
            
            # MOD发现索引
            "CREATE INDEX IF NOT EXISTS idx_discoveries_name ON mod_discoveries(mod_name)",
            "CREATE INDEX IF NOT EXISTS idx_discoveries_uploaded ON mod_discoveries(is_uploaded)",
            "CREATE INDEX IF NOT EXISTS idx_discoveries_path ON mod_discoveries(file_path)",
            
            # 语言文件缓存索引
            "CREATE INDEX IF NOT EXISTS idx_lang_cache_mod ON language_file_cache(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_lang_cache_lang ON language_file_cache(language_code)",
            
            # 翻译条目缓存索引
            "CREATE INDEX IF NOT EXISTS idx_entry_cache_id ON translation_entry_cache(cache_id)",
            "CREATE INDEX IF NOT EXISTS idx_entry_cache_key ON translation_entry_cache(translation_key)",
            "CREATE INDEX IF NOT EXISTS idx_entry_cache_status ON translation_entry_cache(status)",
            
            # 工作队列索引
            "CREATE INDEX IF NOT EXISTS idx_queue_type ON work_queue(task_type)",
            "CREATE INDEX IF NOT EXISTS idx_queue_status ON work_queue(status)",
            "CREATE INDEX IF NOT EXISTS idx_queue_priority ON work_queue(priority DESC)",
            "CREATE INDEX IF NOT EXISTS idx_queue_scheduled ON work_queue(scheduled_at)",
            
            # 离线变更索引
            "CREATE INDEX IF NOT EXISTS idx_changes_entity ON offline_changes(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_changes_synced ON offline_changes(is_synced)",
            
            # 文件监控索引
            "CREATE INDEX IF NOT EXISTS idx_watch_project ON file_watch(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_watch_active ON file_watch(is_active)",
            
            # 同步日志索引
            "CREATE INDEX IF NOT EXISTS idx_sync_type ON sync_log(sync_type)",
            "CREATE INDEX IF NOT EXISTS idx_sync_started ON sync_log(started_at DESC)"
        ]
        
        for index_sql in indexes:
            self.conn.execute(index_sql)
            
        logger.info(f"创建了 {len(indexes)} 个索引")
        
    def create_triggers(self):
        """创建触发器"""
        
        # 更新时间戳触发器
        triggers = [
            """
            CREATE TRIGGER IF NOT EXISTS update_local_settings_timestamp
            AFTER UPDATE ON local_settings
            BEGIN
                UPDATE local_settings SET updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = NEW.setting_key;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS update_local_projects_timestamp
            AFTER UPDATE ON local_projects
            BEGIN
                UPDATE local_projects SET updated_at = CURRENT_TIMESTAMP
                WHERE project_id = NEW.project_id;
            END
            """
        ]
        
        for trigger_sql in triggers:
            self.conn.execute(trigger_sql)
            
        logger.info("触发器创建完成")
        
    def insert_default_settings(self):
        """插入默认设置"""
        
        default_settings = [
            ('cache_ttl', '86400', 'integer', '缓存过期时间（秒）'),
            ('auto_sync', 'false', 'boolean', '自动同步开关'),
            ('sync_interval', '300', 'integer', '同步间隔（秒）'),
            ('max_cache_size', '1073741824', 'integer', '最大缓存大小（字节）'),
            ('scan_threads', '4', 'integer', '扫描线程数'),
            ('api_timeout', '30', 'integer', 'API超时时间（秒）'),
            ('language_priority', 'zh_cn,en_us', 'string', '语言优先级'),
            ('enable_file_watch', 'true', 'boolean', '启用文件监控'),
            ('conflict_resolution', 'client_wins', 'string', '冲突解决策略'),
            ('log_level', 'INFO', 'string', '日志级别')
        ]
        
        for key, value, type_, desc in default_settings:
            self.conn.execute("""
                INSERT OR IGNORE INTO local_settings (setting_key, setting_value, setting_type, description)
                VALUES (?, ?, ?, ?)
            """, (key, value, type_, desc))
            
        logger.info(f"插入了 {len(default_settings)} 个默认设置")
        
    def create_default_project(self):
        """创建默认项目"""
        
        self.conn.execute("""
            INSERT OR IGNORE INTO local_projects (
                project_id, project_name, target_language, source_language,
                scan_paths, auto_scan
            ) VALUES (
                'default-project',
                '默认项目',
                'zh_cn',
                'en_us',
                '[]',
                0
            )
        """)
        
        logger.info("创建默认项目完成")
        
    def create_views(self):
        """创建视图"""
        
        views = [
            """
            CREATE VIEW IF NOT EXISTS v_cache_statistics AS
            SELECT 
                COUNT(*) as total_cache_entries,
                SUM(CASE WHEN is_valid = 1 AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP) THEN 1 ELSE 0 END) as valid_entries,
                SUM(CASE WHEN expires_at <= CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as expired_entries,
                COUNT(DISTINCT scan_path) as unique_paths
            FROM scan_cache
            """,
            """
            CREATE VIEW IF NOT EXISTS v_discovery_summary AS
            SELECT 
                COUNT(*) as total_mods,
                SUM(CASE WHEN is_uploaded = 1 THEN 1 ELSE 0 END) as uploaded_mods,
                SUM(language_count) as total_languages,
                SUM(total_keys) as total_translation_keys,
                MIN(discovered_at) as first_discovery,
                MAX(discovered_at) as latest_discovery
            FROM mod_discoveries
            """,
            """
            CREATE VIEW IF NOT EXISTS v_queue_status AS
            SELECT 
                task_type,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                AVG(CASE WHEN completed_at IS NOT NULL THEN 
                    (julianday(completed_at) - julianday(started_at)) * 86400 
                ELSE NULL END) as avg_duration_seconds
            FROM work_queue
            GROUP BY task_type
            """,
            """
            CREATE VIEW IF NOT EXISTS v_sync_history AS
            SELECT 
                sync_type,
                COUNT(*) as total_syncs,
                AVG(duration_seconds) as avg_duration,
                SUM(entity_count) as total_entities,
                SUM(success_count) as total_success,
                SUM(error_count) as total_errors,
                SUM(conflict_count) as total_conflicts,
                MAX(completed_at) as last_sync
            FROM sync_log
            WHERE completed_at IS NOT NULL
            GROUP BY sync_type
            """
        ]
        
        for view_sql in views:
            self.conn.execute(view_sql)
            
        logger.info(f"创建了 {len(views)} 个视图")
        
    def initialize(self, reset: bool = False):
        """初始化数据库"""
        
        try:
            if reset and self.db_path.exists():
                self.db_path.unlink()
                logger.info(f"已删除旧数据库: {self.db_path}")
                
            self.connect()
            
            # 创建表结构
            self.create_tables()
            
            # 创建索引
            self.create_indexes()
            
            # 创建触发器
            self.create_triggers()
            
            # 创建视图
            self.create_views()
            
            # 插入默认数据
            self.insert_default_settings()
            self.create_default_project()
            
            # 提交事务
            self.conn.commit()
            
            logger.info("✅ 本地数据库初始化完成")
            
            # 显示统计信息
            self.show_statistics()
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close()
            
    def show_statistics(self):
        """显示数据库统计信息"""
        
        cursor = self.conn.cursor()
        
        # 获取表信息
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        logger.info("\n📊 数据库统计:")
        logger.info(f"  表数量: {len(tables)}")
        
        for table_name, in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"  - {table_name}: {count} 行")
            
        # 获取索引数量
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
        index_count = cursor.fetchone()[0]
        logger.info(f"  索引数量: {index_count}")
        
        # 获取视图数量
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        view_count = cursor.fetchone()[0]
        logger.info(f"  视图数量: {view_count}")
        
        # 数据库文件大小
        if self.db_path.exists():
            size_mb = self.db_path.stat().st_size / 1024 / 1024
            logger.info(f"  数据库大小: {size_mb:.2f} MB")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="本地数据库初始化工具")
    parser.add_argument(
        "--db",
        default="mc_l10n_local.db",
        help="数据库文件路径"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置数据库（删除旧数据）"
    )
    
    args = parser.parse_args()
    
    initializer = LocalDatabaseInitializer(args.db)
    initializer.initialize(reset=args.reset)


if __name__ == "__main__":
    main()