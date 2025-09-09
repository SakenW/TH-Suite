"""
事务管理
提供事务管理和工作单元模式实现
"""

import logging
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class TransactionManager:
    """事务管理器"""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self._savepoint_counter = 0
        self._in_transaction = False

    def begin(self):
        """开始事务"""
        if not self._in_transaction:
            self.connection.execute("BEGIN")
            self._in_transaction = True
            logger.debug("Transaction started")

    def commit(self):
        """提交事务"""
        if self._in_transaction:
            self.connection.commit()
            self._in_transaction = False
            logger.debug("Transaction committed")

    def rollback(self):
        """回滚事务"""
        if self._in_transaction:
            self.connection.rollback()
            self._in_transaction = False
            logger.debug("Transaction rolled back")

    @contextmanager
    def savepoint(self, name: str | None = None):
        """保存点管理"""
        if name is None:
            self._savepoint_counter += 1
            name = f"sp_{self._savepoint_counter}"

        self.connection.execute(f"SAVEPOINT {name}")
        logger.debug(f"Savepoint {name} created")

        try:
            yield
            self.connection.execute(f"RELEASE SAVEPOINT {name}")
            logger.debug(f"Savepoint {name} released")
        except Exception:
            self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
            logger.debug(f"Rolled back to savepoint {name}")
            raise


def transactional(isolation_level: str = "DEFERRED"):
    """事务装饰器

    Args:
        isolation_level: 事务隔离级别 (DEFERRED, IMMEDIATE, EXCLUSIVE)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取数据库连接（假设第一个参数是self，包含connection属性）
            self = args[0]
            if not hasattr(self, "connection"):
                # 如果没有connection，直接执行函数
                return func(*args, **kwargs)

            conn = self.connection

            # 开始事务
            conn.execute(f"BEGIN {isolation_level}")

            try:
                result = func(*args, **kwargs)
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed in {func.__name__}: {e}")
                raise

        return wrapper

    return decorator


class OutboxPattern:
    """发件箱模式实现（用于事件发布）"""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self._create_outbox_table()

    def _create_outbox_table(self):
        """创建发件箱表"""
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS outbox_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

        # 创建索引
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_outbox_status_created
            ON outbox_events(status, created_at)
        """)

    def publish_event(self, event_type: str, aggregate_id: str, payload: str):
        """发布事件到发件箱"""
        self.connection.execute(
            """
            INSERT INTO outbox_events (event_type, aggregate_id, payload)
            VALUES (?, ?, ?)
        """,
            (event_type, aggregate_id, payload),
        )

    def get_pending_events(self, limit: int = 100) -> list:
        """获取待处理事件"""
        cursor = self.connection.execute(
            """
            SELECT id, event_type, aggregate_id, payload, created_at
            FROM outbox_events
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT ?
        """,
            (limit,),
        )
        return cursor.fetchall()

    def mark_as_processed(self, event_id: int):
        """标记事件为已处理"""
        self.connection.execute(
            """
            UPDATE outbox_events
            SET status = 'processed', processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (event_id,),
        )


class OptimisticLock:
    """乐观锁实现"""

    @staticmethod
    def check_version(
        connection: sqlite3.Connection,
        table: str,
        entity_id: Any,
        expected_version: int,
    ) -> bool:
        """检查版本号"""
        cursor = connection.execute(
            f"SELECT version FROM {table} WHERE id = ?", (entity_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return False

        return row[0] == expected_version

    @staticmethod
    def update_with_version(
        connection: sqlite3.Connection,
        table: str,
        entity_id: Any,
        data: dict[str, Any],
        expected_version: int,
    ) -> bool:
        """带版本检查的更新"""
        # 构建UPDATE语句
        set_clauses = [f"{key} = ?" for key in data.keys()]
        set_clauses.append("version = version + 1")
        sql = f"""
            UPDATE {table}
            SET {", ".join(set_clauses)}
            WHERE id = ? AND version = ?
        """

        # 执行更新
        params = list(data.values()) + [entity_id, expected_version]
        cursor = connection.execute(sql, params)

        # 检查是否更新成功
        return cursor.rowcount > 0


class DistributedLock:
    """分布式锁实现（基于数据库）"""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self._create_lock_table()

    def _create_lock_table(self):
        """创建锁表"""
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS distributed_locks (
                lock_name TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)

    def acquire(self, lock_name: str, owner: str, ttl_seconds: int = 60) -> bool:
        """获取锁"""
        try:
            self.connection.execute(
                """
                INSERT INTO distributed_locks (lock_name, owner, expires_at)
                VALUES (?, ?, datetime('now', '+' || ? || ' seconds'))
            """,
                (lock_name, owner, ttl_seconds),
            )
            return True
        except sqlite3.IntegrityError:
            # 锁已存在，检查是否过期
            cursor = self.connection.execute(
                """
                DELETE FROM distributed_locks
                WHERE lock_name = ? AND expires_at < datetime('now')
            """,
                (lock_name,),
            )

            if cursor.rowcount > 0:
                # 过期锁已删除，尝试重新获取
                return self.acquire(lock_name, owner, ttl_seconds)

            return False

    def release(self, lock_name: str, owner: str) -> bool:
        """释放锁"""
        cursor = self.connection.execute(
            """
            DELETE FROM distributed_locks
            WHERE lock_name = ? AND owner = ?
        """,
            (lock_name, owner),
        )

        return cursor.rowcount > 0

    @contextmanager
    def lock(self, lock_name: str, owner: str, ttl_seconds: int = 60):
        """锁上下文管理器"""
        acquired = self.acquire(lock_name, owner, ttl_seconds)
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock: {lock_name}")

        try:
            yield
        finally:
            self.release(lock_name, owner)
