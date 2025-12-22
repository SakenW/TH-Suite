"""
数据库连接池管理
提供线程安全的连接池实现
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, current_thread
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionPool:
    """SQLite连接池"""

    def __init__(
        self,
        database_path: str,
        max_connections: int = 10,
        check_same_thread: bool = False,
        timeout: float = 5.0,
    ):
        self.database_path = database_path
        self.max_connections = max_connections
        self.check_same_thread = check_same_thread
        self.timeout = timeout

        self._lock = Lock()
        self._connections: dict[int, sqlite3.Connection] = {}
        self._available: list[sqlite3.Connection] = []
        self._in_use: dict[int, sqlite3.Connection] = {}

        # 确保数据库文件存在
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """创建新连接"""
        conn = sqlite3.connect(
            self.database_path,
            timeout=self.timeout,
            check_same_thread=self.check_same_thread,
        )
        conn.row_factory = sqlite3.Row

        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")

        # 优化性能
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache

        return conn

    @contextmanager
    def get_connection(self):
        """获取连接（上下文管理器）"""
        thread_id = current_thread().ident
        conn = None

        try:
            with self._lock:
                # 检查是否已有该线程的连接
                if thread_id in self._in_use:
                    conn = self._in_use[thread_id]
                    logger.debug(f"Reusing connection for thread {thread_id}")
                elif self._available:
                    # 从可用池中获取
                    conn = self._available.pop()
                    self._in_use[thread_id] = conn
                    logger.debug(f"Got connection from pool for thread {thread_id}")
                elif len(self._in_use) < self.max_connections:
                    # 创建新连接
                    conn = self._create_connection()
                    self._in_use[thread_id] = conn
                    logger.debug(f"Created new connection for thread {thread_id}")
                else:
                    raise RuntimeError(
                        f"Connection pool exhausted (max={self.max_connections})"
                    )

            yield conn

        finally:
            if conn:
                with self._lock:
                    # 归还连接到可用池
                    if thread_id in self._in_use:
                        del self._in_use[thread_id]
                        if len(self._available) < self.max_connections:
                            self._available.append(conn)
                        else:
                            conn.close()
                            logger.debug(
                                f"Closed excess connection for thread {thread_id}"
                            )

    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            # 关闭可用连接
            for conn in self._available:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

            # 关闭使用中的连接
            for conn in self._in_use.values():
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing in-use connection: {e}")

            self._available.clear()
            self._in_use.clear()
            logger.info("All connections closed")

    def get_stats(self) -> dict[str, Any]:
        """获取连接池统计信息"""
        with self._lock:
            return {
                "database": self.database_path,
                "max_connections": self.max_connections,
                "available": len(self._available),
                "in_use": len(self._in_use),
                "total": len(self._available) + len(self._in_use),
            }


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, database_path: str, **pool_kwargs):
        self.database_path = database_path
        self.pool = ConnectionPool(database_path, **pool_kwargs)
        self._lock = Lock()

    @contextmanager
    def transaction(self):
        """事务管理器"""
        with self.pool.get_connection() as conn:
            try:
                conn.execute("BEGIN")
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise

    def execute(self, sql: str, params: tuple = None) -> sqlite3.Cursor:
        """执行SQL语句"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """批量执行SQL"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, params_list)
            conn.commit()
            return cursor

    def query(self, sql: str, params: tuple = None) -> list:
        """查询数据"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetchall()

    def query_one(self, sql: str, params: tuple = None) -> sqlite3.Row | None:
        """查询单条数据"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetchone()

    def close(self):
        """关闭数据库管理器"""
        self.pool.close_all()
