#!/usr/bin/env python
"""
通用数据库管理器
提供SQLCipher加密数据库连接管理、事务处理、连接池等通用功能
适用于所有游戏本地化工具
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List, Callable
from contextlib import contextmanager
from datetime import datetime
import sqlite3
import keyring
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class DatabaseManager:
    """通用数据库管理器 - 单例模式 + SQLCipher + 连接池"""
    
    def __init__(
        self, 
        db_path: str = None,
        password_key: str = None,
        db_version: str = "1.0.0",
        app_name: str = "th_suite"
    ):
        # 设置数据库路径
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent.parent / "data" / f"{app_name}.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_version = db_version
        self.app_name = app_name
        
        # 密钥管理
        self.password_key = password_key or f"{app_name}_master_key"
        self._setup_encryption()
        
        # 连接配置
        self._connection_params = self._get_connection_params()
        
        # 表创建回调
        self._table_creators: List[Callable] = []
        self._index_creators: List[Callable] = []
        self._view_creators: List[Callable] = []
        
        logger.info(f"通用数据库管理器初始化: {self.db_path}")
    
    def _setup_encryption(self):
        """设置SQLCipher加密密钥"""
        try:
            # 尝试从OS Keyring获取密钥
            stored_key = keyring.get_password(self.app_name, self.password_key)
            
            if not stored_key:
                # 生成新密钥
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA512(),
                    length=32,
                    salt=salt,
                    iterations=20000,
                    backend=default_backend()
                )
                key = kdf.derive(self.password_key.encode())
                
                # 组合salt和key
                combined = base64.b64encode(salt + key).decode()
                
                # 存储到keyring
                keyring.set_password(self.app_name, self.password_key, combined)
                self.db_password = combined
                
                logger.info("生成新的数据库加密密钥")
            else:
                self.db_password = stored_key
                logger.debug("从Keyring获取数据库密钥")
                
        except Exception as e:
            # Fallback: 使用PBKDF2生成密钥
            logger.warning(f"Keyring不可用，使用PBKDF2备选方案: {e}")
            
            salt = hashlib.sha256(self.password_key.encode()).digest()[:16]
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA512(),
                length=32,
                salt=salt,
                iterations=20000,
                backend=default_backend()
            )
            key = kdf.derive(self.password_key.encode())
            self.db_password = base64.b64encode(salt + key).decode()
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """获取数据库连接参数"""
        return {
            'timeout': 30.0,
            'check_same_thread': False,
            'isolation_level': None  # 手动管理事务
        }
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            # 创建连接
            conn = sqlite3.connect(str(self.db_path), **self._connection_params)
            conn.row_factory = sqlite3.Row
            
            # SQLCipher配置
            conn.execute(f"PRAGMA key = '{self.db_password}'")
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
            conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
            conn.execute("PRAGMA kdf_iter = 20000")
            
            # 性能配置
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA cache_size = -64000")  # 64MB缓存
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 测试加密是否正确
            conn.execute("SELECT 1").fetchone()
            
            yield conn
            
        except sqlite3.DatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库错误: {e}")
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def register_schema_creator(
        self, 
        table_creator: Callable = None,
        index_creator: Callable = None, 
        view_creator: Callable = None
    ):
        """注册数据库架构创建器"""
        if table_creator:
            self._table_creators.append(table_creator)
        if index_creator:
            self._index_creators.append(index_creator)
        if view_creator:
            self._view_creators.append(view_creator)
    
    def init_database(self):
        """初始化数据库"""
        try:
            with self.get_connection() as conn:
                # 检查数据库是否已初始化
                try:
                    version = conn.execute(
                        "SELECT value_json FROM cfg_local_settings WHERE key = 'db_version'"
                    ).fetchone()
                    if version and version[0].strip('"') == self.db_version:
                        logger.info(f"数据库已存在，版本: {version[0]}")
                        return
                except sqlite3.OperationalError:
                    # 表不存在，需要初始化
                    pass
                
                # 创建通用设置表
                self._create_config_table(conn)
                
                # 调用注册的创建器
                for creator in self._table_creators:
                    creator(conn)
                
                for creator in self._index_creators:
                    creator(conn)
                    
                for creator in self._view_creators:
                    creator(conn)
                
                # 插入元数据
                self._insert_metadata(conn)
                
                logger.info(f"数据库初始化完成，版本: {self.db_version}")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _create_config_table(self, conn: sqlite3.Connection):
        """创建通用配置表"""
        # 本地设置表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cfg_local_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT CHECK(json_valid(value_json)) NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
    
    def _insert_metadata(self, conn: sqlite3.Connection):
        """插入数据库元数据"""
        now = datetime.now().isoformat()
        
        metadata = [
            ('db_version', f'"{self.db_version}"'),
            ('app_name', f'"{self.app_name}"'),
            ('created_at', f'"{now}"'),
            ('updated_at', f'"{now}"'),
        ]
        
        for key, value in metadata:
            conn.execute(
                """
                INSERT OR REPLACE INTO cfg_local_settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, value, now)
            )
    
    def execute_transaction(self, operations: list):
        """执行事务操作"""
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                results = []
                for op in operations:
                    if isinstance(op, tuple):
                        sql, params = op
                        result = conn.execute(sql, params)
                    else:
                        result = conn.execute(op)
                    results.append(result)
                
                conn.commit()
                return results
            except Exception as e:
                conn.rollback()
                logger.error(f"事务执行失败: {e}")
                raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        with self.get_connection() as conn:
            # 数据库文件大小
            file_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            # 页面统计
            page_count = conn.execute("PRAGMA page_count").fetchone()[0]
            page_size = conn.execute("PRAGMA page_size").fetchone()[0]
            freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
            
            # WAL信息
            wal_checkpoint = conn.execute("PRAGMA wal_checkpoint").fetchone()
            
            return {
                'version': self.db_version,
                'app_name': self.app_name,
                'file_path': str(self.db_path),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'page_count': page_count,
                'page_size': page_size,
                'freelist_count': freelist_count,
                'wal_frames': wal_checkpoint[1] if wal_checkpoint else 0,
                'encrypted': True,
                'journal_mode': 'WAL',
                'created_at': datetime.fromtimestamp(self.db_path.stat().st_ctime).isoformat() if self.db_path.exists() else None
            }
    
    def cleanup_expired_data(self):
        """清理过期数据 - 子类需要实现具体逻辑"""
        pass
    
    def vacuum_database(self):
        """压缩数据库"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            logger.info("数据库压缩完成")
    
    def backup_database(self, backup_path: str):
        """备份数据库"""
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as source:
            backup_conn = sqlite3.connect(str(backup_path))
            backup_conn.execute(f"PRAGMA key = '{self.db_password}'")
            
            try:
                source.backup(backup_conn)
                logger.info(f"数据库备份完成: {backup_path}")
            finally:
                backup_conn.close()
    
    def restore_database(self, backup_path: str):
        """从备份恢复数据库"""
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        # 备份当前数据库
        current_backup = self.db_path.with_suffix('.backup')
        if self.db_path.exists():
            self.db_path.rename(current_backup)
        
        try:
            # 复制备份文件
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            # 验证恢复是否成功
            with self.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            
            logger.info(f"数据库恢复完成: {backup_path}")
            
            # 删除临时备份
            if current_backup.exists():
                current_backup.unlink()
                
        except Exception as e:
            # 恢复失败，回滚
            if current_backup.exists():
                current_backup.rename(self.db_path)
            logger.error(f"数据库恢复失败: {e}")
            raise


class WorkQueueManager:
    """通用工作队列管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_work_queue_table(self, conn: sqlite3.Connection):
        """创建工作队列表"""
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ops_work_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            payload_json TEXT CHECK(json_valid(payload_json)) NOT NULL,
            state TEXT CHECK(state IN ('pending','leased','done','err','dead')) DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            not_before TEXT,
            dedupe_key TEXT UNIQUE,
            attempt INTEGER DEFAULT 0,
            last_error TEXT,
            lease_owner TEXT,
            lease_expires_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
    
    def create_work_queue_indexes(self, conn: sqlite3.Connection):
        """创建工作队列索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_work_queue_state ON ops_work_queue(state, not_before, priority)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_work_queue_dedupe ON ops_work_queue(dedupe_key) WHERE dedupe_key IS NOT NULL",
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def enqueue_task(
        self, 
        task_type: str, 
        payload: Dict[str, Any],
        priority: int = 0,
        dedupe_key: str = None,
        delay_seconds: int = 0
    ) -> int:
        """入队任务"""
        import json
        from datetime import datetime, timedelta
        
        now = datetime.now()
        not_before = (now + timedelta(seconds=delay_seconds)).isoformat() if delay_seconds > 0 else None
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO ops_work_queue 
                (type, payload_json, priority, not_before, dedupe_key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task_type,
                json.dumps(payload),
                priority,
                not_before,
                dedupe_key,
                now.isoformat(),
                now.isoformat()
            ))
            
            return cursor.lastrowid
    
    def lease_task(self, lease_owner: str, lease_duration_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """租用任务"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        lease_expires = now + timedelta(seconds=lease_duration_seconds)
        
        with self.db_manager.get_connection() as conn:
            # 查找可用任务
            task = conn.execute("""
                SELECT id, type, payload_json, attempt 
                FROM ops_work_queue 
                WHERE state = 'pending' 
                AND (not_before IS NULL OR not_before <= ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """, (now.isoformat(),)).fetchone()
            
            if not task:
                return None
            
            # 租用任务
            conn.execute("""
                UPDATE ops_work_queue 
                SET state = 'leased', 
                    lease_owner = ?, 
                    lease_expires_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                lease_owner,
                lease_expires.isoformat(),
                now.isoformat(),
                task['id']
            ))
            
            return {
                'id': task['id'],
                'type': task['type'],
                'payload': json.loads(task['payload_json']),
                'attempt': task['attempt']
            }
    
    def complete_task(self, task_id: int, success: bool = True, error_message: str = None):
        """完成任务"""
        now = datetime.now().isoformat()
        
        if success:
            state = 'done'
        else:
            state = 'err'
        
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                UPDATE ops_work_queue 
                SET state = ?, 
                    last_error = ?,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE id = ?
            """, (state, error_message, now, task_id))


class OutboxManager:
    """通用Outbox模式管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_outbox_table(self, conn: sqlite3.Connection):
        """创建Outbox表"""
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ops_outbox_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_uid TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            base_version TEXT,
            diff_json TEXT CHECK(json_valid(diff_json)) NOT NULL,
            idempotency_key TEXT UNIQUE NOT NULL,
            state TEXT CHECK(state IN ('pending','sent','acked','err')) DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
    
    def create_outbox_indexes(self, conn: sqlite3.Connection):
        """创建Outbox索引"""
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_state ON ops_outbox_journal(state, created_at)")
    
    def record_change(
        self, 
        entity_uid: str, 
        entity_type: str, 
        diff: Dict[str, Any],
        base_version: str = None
    ):
        """记录实体变更"""
        import json
        import uuid
        from datetime import datetime
        
        now = datetime.now().isoformat()
        idempotency_key = str(uuid.uuid4())
        
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO ops_outbox_journal 
                (entity_uid, entity_type, base_version, diff_json, idempotency_key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_uid,
                entity_type,
                base_version,
                json.dumps(diff),
                idempotency_key,
                now,
                now
            ))


def create_database_manager(
    app_name: str,
    db_version: str,
    db_path: str = None,
    password_key: str = None
) -> DatabaseManager:
    """创建数据库管理器工厂函数"""
    return DatabaseManager(
        db_path=db_path,
        password_key=password_key,
        db_version=db_version,
        app_name=app_name
    )