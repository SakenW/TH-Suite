#!/usr/bin/env python
"""
MC L10n V6 数据库管理器
继承通用数据库管理器，实现MC特定的数据库架构
"""

import logging
from pathlib import Path
from typing import Optional, Any, Dict
import sqlite3

# 导入通用数据库管理器
from packages.core.infrastructure.database.manager import (
    DatabaseManager as BaseDatabaseManager, 
    WorkQueueManager,
    OutboxManager
)
from ..models.tables import create_tables

logger = logging.getLogger(__name__)


class McL10nDatabaseManager(BaseDatabaseManager):
    """MC L10n V6数据库管理器 - 继承通用数据库管理器"""
    
    DB_VERSION = "6.0.0"
    _instance = None
    
    def __new__(cls, db_path: str = None, password_key: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = None, password_key: str = None):
        # 设置MC L10n专属路径
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n_v6.db"
        
        # 调用通用基类
        super().__init__(
            db_path=db_path,
            password_key=password_key or "mc_l10n_v6_master_key", 
            db_version=self.DB_VERSION,
            app_name="mc_l10n"
        )
        
        # 注册MC L10n专属的数据库架构创建器
        self.register_schema_creator(
            table_creator=self._create_mc_tables,
            index_creator=self._create_mc_indexes, 
            view_creator=self._create_mc_views
        )
        
        # 集成工作队列和Outbox管理器
        self.work_queue = WorkQueueManager(self)
        self.outbox = OutboxManager(self)
        
        # 初始化数据库
        self.init_database()
        
        logger.info(f"MC L10n V6数据库管理器初始化完成: {self.db_path}")
    
    def _create_mc_tables(self, conn: sqlite3.Connection):
        """创建MC L10n专属表"""
        create_tables(conn)
        
        # 注册工作队列和Outbox表
        self.work_queue.create_work_queue_table(conn)
        self.outbox.create_outbox_table(conn)
        
        # 创建内容寻址存储表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ops_cas_objects (
            cid TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            algo TEXT CHECK(algo IN ('zstd','gzip','none')) DEFAULT 'zstd',
            dict_id TEXT,
            ref_count INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)
        
        # 创建同步日志表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ops_sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT CHECK(direction IN ('up','down')) NOT NULL,
            endpoint TEXT NOT NULL,
            request_meta TEXT CHECK(json_valid(request_meta)),
            response_meta TEXT CHECK(json_valid(response_meta)),
            result TEXT CHECK(result IN ('success','fail','partial')) NOT NULL,
            idempotency_key TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # 创建文件监控表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cfg_file_watch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_path TEXT NOT NULL,
            globs TEXT CHECK(json_valid(globs)) NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TEXT NOT NULL
        )
        """)
        
        logger.info("MC L10n专属表创建完成")
    
    def _create_mc_indexes(self, conn: sqlite3.Connection):
        """创建MC L10n专属索引"""
        indexes = [
            # 核心索引
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_file_key ON core_translation_entries(language_file_uid, key)",
            "CREATE INDEX IF NOT EXISTS idx_language_files_carrier ON core_language_files(carrier_type, carrier_uid, locale)",
            "CREATE INDEX IF NOT EXISTS idx_mod_versions_lookup ON core_mod_versions(mod_uid, loader, mc_version, version)",
            "CREATE INDEX IF NOT EXISTS idx_pack_items_lookup ON core_pack_items(pack_version_uid, item_type, identity)",
            
            # 同步索引
            "CREATE INDEX IF NOT EXISTS idx_cas_objects_cid ON ops_cas_objects(cid)",
            "CREATE INDEX IF NOT EXISTS idx_sync_log_created ON ops_sync_log(created_at DESC)",
            
            # 时间戳索引
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_updated ON core_translation_entries(updated_at)",
        ]
        
        # 注册通用索引
        self.work_queue.create_work_queue_indexes(conn)
        self.outbox.create_outbox_indexes(conn)
        
        for index_sql in indexes:
            conn.execute(index_sql)
            
        logger.info("MC L10n专属索引创建完成")
    
    def _create_mc_views(self, conn: sqlite3.Connection):
        """创建MC L10n专属视图"""
        # 缓存统计视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_cache_statistics AS
        SELECT 
            'scan_results' as cache_type,
            COUNT(*) as total_entries,
            COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
            ROUND(AVG(LENGTH(result_json)), 2) as avg_size_bytes
        FROM cache_scan_results
        """)
        
        # 队列状态视图  
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_queue_status AS
        SELECT 
            state,
            COUNT(*) as count,
            MIN(created_at) as oldest_created,
            MAX(updated_at) as latest_updated
        FROM ops_work_queue 
        GROUP BY state
        """)
        
        # 同步历史视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_sync_history AS
        SELECT 
            direction,
            result,
            COUNT(*) as count,
            MAX(created_at) as latest_sync
        FROM ops_sync_log
        WHERE created_at > datetime('now', '-7 days')
        GROUP BY direction, result
        """)
        
        # 差量积压视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_delta_backlog AS
        SELECT 
            entity_type,
            state,
            COUNT(*) as count,
            MIN(created_at) as oldest_pending
        FROM ops_outbox_journal
        GROUP BY entity_type, state
        """)
        
        # MC L10n专属统计视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_mc_translation_progress AS
        SELECT 
            cm.name as mod_name,
            clf.locale,
            COUNT(cte.id) as total_entries,
            SUM(CASE WHEN cte.status IN ('reviewed', 'locked') THEN 1 ELSE 0 END) as completed_entries,
            ROUND(100.0 * SUM(CASE WHEN cte.status IN ('reviewed', 'locked') THEN 1 ELSE 0 END) / COUNT(cte.id), 2) as progress_percentage
        FROM core_translation_entries cte
        JOIN core_language_files clf ON cte.language_file_uid = clf.uid
        JOIN core_mods cm ON clf.carrier_uid = cm.uid
        WHERE clf.carrier_type = 'mod'
        GROUP BY cm.name, clf.locale
        """)
        
        logger.info("MC L10n专属视图创建完成")
    
    def cleanup_expired_data(self):
        """清理MC L10n过期数据"""
        with self.get_connection() as conn:
            # 清理过期缓存
            expired_cache = conn.execute("""
                DELETE FROM cache_scan_results 
                WHERE valid_until < datetime('now')
            """)
            
            # 清理完成的工作队列任务（保留7天）
            expired_tasks = conn.execute("""
                DELETE FROM ops_work_queue 
                WHERE state IN ('done', 'dead') 
                AND updated_at < datetime('now', '-7 days')
            """)
            
            # 清理旧同步日志（保留30天）
            expired_logs = conn.execute("""
                DELETE FROM ops_sync_log 
                WHERE created_at < datetime('now', '-30 days')
            """)
            
            conn.commit()
            
            logger.info(f"MC L10n数据清理完成: 缓存{expired_cache.rowcount}条, "
                       f"任务{expired_tasks.rowcount}条, 日志{expired_logs.rowcount}条")
    
    def get_mc_statistics(self) -> Dict[str, Any]:
        """获取MC L10n专属统计信息"""
        with self.get_connection() as conn:
            stats = {}
            
            # 基础实体统计
            entity_counts = {}
            for table in ['core_packs', 'core_pack_versions', 'core_mods', 
                         'core_mod_versions', 'core_language_files', 'core_translation_entries']:
                count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                entity_counts[table.replace('core_', '')] = count['cnt']
            
            stats['entities'] = entity_counts
            
            # 队列统计
            queue_stats = conn.execute("SELECT * FROM v_queue_status").fetchall()
            stats['queue'] = {row['state']: row['count'] for row in queue_stats}
            
            # 缓存统计
            cache_stats = conn.execute("SELECT * FROM v_cache_statistics").fetchone()
            if cache_stats:
                stats['cache'] = dict(cache_stats)
            
            # 翻译进度统计
            progress_stats = conn.execute("""
                SELECT 
                    locale,
                    COUNT(*) as mod_count,
                    AVG(progress_percentage) as avg_progress
                FROM v_mc_translation_progress
                GROUP BY locale
            """).fetchall()
            
            stats['translation_progress'] = {
                row['locale']: {
                    'mod_count': row['mod_count'],
                    'avg_progress': round(row['avg_progress'], 2)
                } for row in progress_stats
            }
            
            return stats


def get_database_manager(db_path: str = None, password_key: str = None) -> McL10nDatabaseManager:
    """获取MC L10n数据库管理器实例"""
    return McL10nDatabaseManager(db_path, password_key)


# 全局实例
_global_manager = None


def get_global_database_manager() -> McL10nDatabaseManager:
    """获取全局MC L10n数据库管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = McL10nDatabaseManager()
    return _global_manager