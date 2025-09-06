#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MC L10n 本地数据库管理器
负责管理本地SQLite数据库，处理扫描缓存、离线工作等
"""

import sqlite3
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import uuid

logger = logging.getLogger(__name__)

class LocalDatabaseManager:
    """本地数据库管理器"""
    
    def __init__(self, db_path: str = "mc_l10n_local.db"):
        """
        初始化本地数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建扫描缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_scan_cache (
                    cache_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    scan_path TEXT NOT NULL,
                    scan_type TEXT DEFAULT 'mods',
                    game_version TEXT,
                    mod_loader TEXT,
                    cache_key TEXT NOT NULL UNIQUE,
                    cache_data TEXT NOT NULL,
                    cache_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    is_valid BOOLEAN DEFAULT 1,
                    needs_refresh BOOLEAN DEFAULT 0
                )
            """)
            
            # 创建MOD发现表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_mod_discoveries (
                    discovery_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    mod_id TEXT NOT NULL,
                    mod_name TEXT NOT NULL,
                    mod_version TEXT,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER,
                    metadata TEXT,
                    language_files TEXT,
                    entry_count INTEGER DEFAULT 0,
                    is_processed BOOLEAN DEFAULT 0,
                    is_uploaded BOOLEAN DEFAULT 0,
                    upload_error TEXT,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    uploaded_at TIMESTAMP
                )
            """)
            
            # 创建工作队列表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_work_queue (
                    task_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    task_type TEXT NOT NULL,
                    task_data TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    result TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # 创建离线变更表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_offline_changes (
                    change_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    change_data TEXT NOT NULL,
                    conflict_resolution TEXT DEFAULT 'client_wins',
                    is_synced BOOLEAN DEFAULT 0,
                    sync_attempts INTEGER DEFAULT 0,
                    sync_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP
                )
            """)
            
            # 创建本地设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    setting_type TEXT DEFAULT 'string',
                    is_synced BOOLEAN DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建最近项目表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_recent_projects (
                    project_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    project_path TEXT,
                    server_url TEXT,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    cached_data TEXT
                )
            """)
            
            # 创建文件监控表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_file_watch (
                    watch_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    watch_path TEXT NOT NULL,
                    watch_pattern TEXT,
                    watch_recursive BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    last_scan_at TIMESTAMP,
                    last_change_at TIMESTAMP,
                    file_snapshot TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建同步配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_sync_config (
                    config_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    server_url TEXT NOT NULL,
                    api_key TEXT,
                    user_token TEXT,
                    auto_sync BOOLEAN DEFAULT 1,
                    sync_interval INTEGER DEFAULT 300,
                    conflict_resolution TEXT DEFAULT 'ask',
                    last_sync_at TIMESTAMP,
                    last_sync_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建同步日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_sync_log (
                    log_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    sync_type TEXT NOT NULL,
                    sync_direction TEXT,
                    items_sent INTEGER DEFAULT 0,
                    items_received INTEGER DEFAULT 0,
                    conflicts_resolved INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    sync_details TEXT,
                    error_details TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_ms INTEGER
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_cache_key ON local_scan_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_cache_expires ON local_scan_cache(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discoveries_hash ON local_mod_discoveries(file_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discoveries_uploaded ON local_mod_discoveries(is_uploaded)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON local_work_queue(status, priority DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_offline_changes_sync ON local_offline_changes(is_synced)")
            
            logger.info(f"本地数据库初始化完成: {self.db_path}")
    
    # ============ 扫描缓存管理 ============
    
    def get_scan_cache(self, scan_path: str, game_version: str = None, 
                      mod_loader: str = None) -> Optional[Dict]:
        """
        获取扫描缓存
        
        Args:
            scan_path: 扫描路径
            game_version: 游戏版本
            mod_loader: 模组加载器
            
        Returns:
            缓存数据或None
        """
        cache_key = self._generate_cache_key(scan_path, game_version, mod_loader)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cache_data, expires_at, cache_id
                FROM local_scan_cache
                WHERE cache_key = ? AND is_valid = 1
            """, (cache_key,))
            
            row = cursor.fetchone()
            if row:
                # 检查是否过期
                if row['expires_at']:
                    expires_at = datetime.fromisoformat(row['expires_at'])
                    if expires_at < datetime.now():
                        # 标记为无效
                        cursor.execute("""
                            UPDATE local_scan_cache
                            SET is_valid = 0, needs_refresh = 1
                            WHERE cache_id = ?
                        """, (row['cache_id'],))
                        return None
                
                # 更新访问信息
                cursor.execute("""
                    UPDATE local_scan_cache
                    SET last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE cache_id = ?
                """, (row['cache_id'],))
                
                return json.loads(row['cache_data'])
        
        return None
    
    def save_scan_cache(self, scan_path: str, cache_data: Dict,
                       game_version: str = None, mod_loader: str = None,
                       ttl_hours: int = 24) -> str:
        """
        保存扫描缓存
        
        Args:
            scan_path: 扫描路径
            cache_data: 缓存数据
            game_version: 游戏版本
            mod_loader: 模组加载器
            ttl_hours: 缓存有效期（小时）
            
        Returns:
            缓存ID
        """
        cache_key = self._generate_cache_key(scan_path, game_version, mod_loader)
        cache_json = json.dumps(cache_data, ensure_ascii=False)
        cache_size = len(cache_json)
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 使用UPSERT
            cursor.execute("""
                INSERT OR REPLACE INTO local_scan_cache (
                    scan_path, scan_type, game_version, mod_loader,
                    cache_key, cache_data, cache_size, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_path, 'mods', game_version, mod_loader,
                cache_key, cache_json, cache_size, expires_at
            ))
            
            return cache_key
    
    def clear_expired_cache(self) -> int:
        """清理过期缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM local_scan_cache
                WHERE expires_at < CURRENT_TIMESTAMP
                   OR is_valid = 0
            """)
            return cursor.rowcount
    
    # ============ MOD发现管理 ============
    
    def save_mod_discovery(self, mod_info: Dict) -> str:
        """
        保存发现的MOD信息
        
        Args:
            mod_info: MOD信息字典
            
        Returns:
            发现ID
        """
        discovery_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO local_mod_discoveries (
                    discovery_id, mod_id, mod_name, mod_version,
                    file_path, file_hash, file_size,
                    metadata, language_files, entry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                discovery_id,
                mod_info.get('mod_id'),
                mod_info.get('name'),
                mod_info.get('version'),
                mod_info.get('file_path'),
                mod_info.get('file_hash'),
                mod_info.get('file_size'),
                json.dumps(mod_info.get('metadata', {})),
                json.dumps(mod_info.get('language_files', [])),
                mod_info.get('entry_count', 0)
            ))
            
            # 添加到工作队列
            self.add_work_task('upload', {
                'discovery_id': discovery_id,
                'mod_info': mod_info
            })
            
            return discovery_id
    
    def get_unprocessed_discoveries(self, limit: int = 100) -> List[Dict]:
        """获取未处理的MOD发现"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM local_mod_discoveries
                WHERE is_processed = 0
                ORDER BY discovered_at
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_discovery_processed(self, discovery_id: str, uploaded: bool = False):
        """标记发现已处理"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE local_mod_discoveries
                SET is_processed = 1,
                    is_uploaded = ?,
                    processed_at = CURRENT_TIMESTAMP,
                    uploaded_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE discovery_id = ?
            """, (uploaded, uploaded, discovery_id))
    
    # ============ 工作队列管理 ============
    
    def add_work_task(self, task_type: str, task_data: Dict, 
                     priority: int = 0) -> str:
        """
        添加工作任务
        
        Args:
            task_type: 任务类型
            task_data: 任务数据
            priority: 优先级（越大越优先）
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO local_work_queue (
                    task_id, task_type, task_data, priority
                ) VALUES (?, ?, ?, ?)
            """, (
                task_id, task_type, 
                json.dumps(task_data, ensure_ascii=False),
                priority
            ))
            
            return task_id
    
    def get_pending_tasks(self, task_type: str = None, limit: int = 10) -> List[Dict]:
        """获取待处理任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if task_type:
                cursor.execute("""
                    SELECT * FROM local_work_queue
                    WHERE status = 'pending' AND task_type = ?
                    ORDER BY priority DESC, created_at
                    LIMIT ?
                """, (task_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM local_work_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_task_status(self, task_id: str, status: str, 
                          result: Dict = None, error: str = None):
        """更新任务状态"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            update_fields = ["status = ?"]
            params = [status]
            
            if status == 'processing':
                update_fields.append("started_at = CURRENT_TIMESTAMP")
            elif status in ('completed', 'failed'):
                update_fields.append("completed_at = CURRENT_TIMESTAMP")
            
            if result:
                update_fields.append("result = ?")
                params.append(json.dumps(result, ensure_ascii=False))
            
            if error:
                update_fields.append("error_message = ?")
                params.append(error)
            
            params.append(task_id)
            
            cursor.execute(f"""
                UPDATE local_work_queue
                SET {', '.join(update_fields)}
                WHERE task_id = ?
            """, params)
    
    # ============ 离线变更管理 ============
    
    def save_offline_change(self, entity_type: str, entity_id: str,
                           operation: str, change_data: Dict) -> str:
        """
        保存离线变更
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            operation: 操作类型
            change_data: 变更数据
            
        Returns:
            变更ID
        """
        change_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO local_offline_changes (
                    change_id, entity_type, entity_id, 
                    operation, change_data
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                change_id, entity_type, entity_id, operation,
                json.dumps(change_data, ensure_ascii=False)
            ))
            
            return change_id
    
    def get_unsync_changes(self, limit: int = 100) -> List[Dict]:
        """获取未同步的变更"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM local_offline_changes
                WHERE is_synced = 0 AND sync_attempts < 3
                ORDER BY created_at
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_change_synced(self, change_id: str, success: bool = True, 
                          error: str = None):
        """标记变更已同步"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if success:
                cursor.execute("""
                    UPDATE local_offline_changes
                    SET is_synced = 1,
                        synced_at = CURRENT_TIMESTAMP
                    WHERE change_id = ?
                """, (change_id,))
            else:
                cursor.execute("""
                    UPDATE local_offline_changes
                    SET sync_attempts = sync_attempts + 1,
                        sync_error = ?
                    WHERE change_id = ?
                """, (error, change_id))
    
    # ============ 设置管理 ============
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting_value, setting_type
                FROM local_settings
                WHERE setting_key = ?
            """, (key,))
            
            row = cursor.fetchone()
            if row:
                value = row['setting_value']
                setting_type = row['setting_type']
                
                # 类型转换
                if setting_type == 'json':
                    return json.loads(value)
                elif setting_type == 'int':
                    return int(value)
                elif setting_type == 'bool':
                    return value.lower() == 'true'
                else:
                    return value
            
            return default
    
    def set_setting(self, key: str, value: Any, sync: bool = False):
        """设置值"""
        # 类型检测
        if isinstance(value, (dict, list)):
            setting_type = 'json'
            value_str = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            setting_type = 'bool'
            value_str = str(value)
        elif isinstance(value, int):
            setting_type = 'int'
            value_str = str(value)
        else:
            setting_type = 'string'
            value_str = str(value)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO local_settings (
                    setting_key, setting_value, setting_type, is_synced
                ) VALUES (?, ?, ?, ?)
            """, (key, value_str, setting_type, sync))
    
    # ============ 项目管理 ============
    
    def add_recent_project(self, project_id: str, project_name: str,
                          project_path: str = None, server_url: str = None):
        """添加最近项目"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute("""
                SELECT project_id FROM local_recent_projects
                WHERE project_id = ?
            """, (project_id,))
            
            if cursor.fetchone():
                # 更新访问信息
                cursor.execute("""
                    UPDATE local_recent_projects
                    SET last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE project_id = ?
                """, (project_id,))
            else:
                # 插入新项目
                cursor.execute("""
                    INSERT INTO local_recent_projects (
                        project_id, project_name, project_path, server_url
                    ) VALUES (?, ?, ?, ?)
                """, (project_id, project_name, project_path, server_url))
    
    def get_recent_projects(self, limit: int = 10) -> List[Dict]:
        """获取最近项目列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM local_recent_projects
                ORDER BY last_accessed DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ 文件监控 ============
    
    def add_file_watch(self, watch_path: str, pattern: str = None,
                      recursive: bool = True) -> str:
        """添加文件监控"""
        watch_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO local_file_watch (
                    watch_id, watch_path, watch_pattern, watch_recursive
                ) VALUES (?, ?, ?, ?)
            """, (watch_id, watch_path, pattern, recursive))
            
            return watch_id
    
    def get_active_watches(self) -> List[Dict]:
        """获取活动的文件监控"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM local_file_watch
                WHERE is_active = 1
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_watch_snapshot(self, watch_id: str, snapshot: Dict):
        """更新文件快照"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE local_file_watch
                SET file_snapshot = ?,
                    last_scan_at = CURRENT_TIMESTAMP
                WHERE watch_id = ?
            """, (json.dumps(snapshot, ensure_ascii=False), watch_id))
    
    # ============ 同步管理 ============
    
    def get_sync_config(self) -> Optional[Dict]:
        """获取同步配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM local_sync_config
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_sync_config(self, server_url: str, api_key: str = None,
                        auto_sync: bool = True, sync_interval: int = 300):
        """保存同步配置"""
        config_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 删除旧配置
            cursor.execute("DELETE FROM local_sync_config")
            
            # 插入新配置
            cursor.execute("""
                INSERT INTO local_sync_config (
                    config_id, server_url, api_key, 
                    auto_sync, sync_interval
                ) VALUES (?, ?, ?, ?, ?)
            """, (config_id, server_url, api_key, auto_sync, sync_interval))
            
            return config_id
    
    def log_sync(self, sync_type: str, sync_direction: str,
                 items_sent: int = 0, items_received: int = 0,
                 errors: List[str] = None) -> str:
        """记录同步日志"""
        log_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO local_sync_log (
                    log_id, sync_type, sync_direction,
                    items_sent, items_received, errors_count,
                    error_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, sync_type, sync_direction,
                items_sent, items_received,
                len(errors) if errors else 0,
                json.dumps(errors) if errors else None
            ))
            
            return log_id
    
    # ============ 工具方法 ============
    
    def _generate_cache_key(self, scan_path: str, game_version: str = None,
                           mod_loader: str = None) -> str:
        """生成缓存键"""
        key_parts = [scan_path]
        if game_version:
            key_parts.append(game_version)
        if mod_loader:
            key_parts.append(mod_loader)
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 各表记录数
            tables = [
                'local_scan_cache', 'local_mod_discoveries',
                'local_work_queue', 'local_offline_changes',
                'local_recent_projects', 'local_file_watch'
            ]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            # 待处理任务数
            cursor.execute("""
                SELECT COUNT(*) FROM local_work_queue
                WHERE status = 'pending'
            """)
            stats['pending_tasks'] = cursor.fetchone()[0]
            
            # 未同步变更数
            cursor.execute("""
                SELECT COUNT(*) FROM local_offline_changes
                WHERE is_synced = 0
            """)
            stats['unsync_changes'] = cursor.fetchone()[0]
            
            # 数据库文件大小
            stats['db_size'] = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return stats
    
    def vacuum(self):
        """优化数据库"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            logger.info("数据库优化完成")


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建管理器
    db_manager = LocalDatabaseManager()
    
    # 测试扫描缓存
    test_data = {
        'mods': ['mod1', 'mod2'],
        'total': 2,
        'timestamp': datetime.now().isoformat()
    }
    
    cache_id = db_manager.save_scan_cache(
        '/path/to/mods',
        test_data,
        game_version='1.20.1',
        mod_loader='forge'
    )
    print(f"保存缓存: {cache_id}")
    
    # 获取缓存
    cached = db_manager.get_scan_cache(
        '/path/to/mods',
        game_version='1.20.1',
        mod_loader='forge'
    )
    print(f"获取缓存: {cached}")
    
    # 添加工作任务
    task_id = db_manager.add_work_task(
        'scan',
        {'path': '/path/to/mods'},
        priority=10
    )
    print(f"添加任务: {task_id}")
    
    # 获取统计
    stats = db_manager.get_statistics()
    print(f"数据库统计: {stats}")