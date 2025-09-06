"""
数据库连接池
管理数据库连接的生命周期
"""

from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from threading import Lock, current_thread
from queue import Queue, Empty, Full
import sqlite3
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """连接信息"""
    
    def __init__(self, connection, created_at: datetime):
        self.connection = connection
        self.created_at = created_at
        self.last_used = created_at
        self.use_count = 0
        self.thread_id = None
    
    def is_expired(self, max_age_seconds: int) -> bool:
        """检查连接是否过期"""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > max_age_seconds
    
    def is_idle(self, idle_timeout: int) -> bool:
        """检查连接是否空闲超时"""
        idle_time = (datetime.now() - self.last_used).total_seconds()
        return idle_time > idle_timeout


class ConnectionPool:
    """数据库连接池
    
    特性：
    - 连接复用
    - 自动重连
    - 连接健康检查
    - 线程安全
    """
    
    def __init__(
        self,
        database_path: str,
        min_connections: int = 2,
        max_connections: int = 10,
        connection_timeout: int = 30,
        idle_timeout: int = 300,
        max_age: int = 3600
    ):
        """初始化连接池
        
        Args:
            database_path: 数据库路径
            min_connections: 最小连接数
            max_connections: 最大连接数
            connection_timeout: 获取连接超时（秒）
            idle_timeout: 空闲超时（秒）
            max_age: 连接最大生存时间（秒）
        """
        self.database_path = database_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.max_age = max_age
        
        self._pool = Queue(maxsize=max_connections)
        self._active_connections: Dict[int, ConnectionInfo] = {}
        self._lock = Lock()
        self._closed = False
        
        # 统计信息
        self._stats = {
            'created': 0,
            'reused': 0,
            'closed': 0,
            'errors': 0,
            'wait_time_total': 0,
            'use_count_total': 0
        }
        
        # 初始化最小连接数
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.min_connections):
            try:
                conn_info = self._create_connection()
                self._pool.put(conn_info, block=False)
            except Full:
                break
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
    
    def _create_connection(self) -> ConnectionInfo:
        """创建新连接"""
        connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=self.connection_timeout
        )
        
        # 启用外键约束
        connection.execute("PRAGMA foreign_keys = ON")
        
        # 优化设置
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA cache_size = -2000")  # 2MB cache
        connection.execute("PRAGMA temp_store = MEMORY")
        
        conn_info = ConnectionInfo(connection, datetime.now())
        
        with self._lock:
            self._stats['created'] += 1
        
        logger.debug(f"Created new connection (total: {self._stats['created']})")
        return conn_info
    
    def _validate_connection(self, conn_info: ConnectionInfo) -> bool:
        """验证连接是否有效"""
        try:
            # 执行简单查询测试连接
            conn_info.connection.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False
    
    @contextmanager
    def get_connection(self):
        """获取连接（上下文管理器）
        
        使用示例：
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM mods")
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        conn_info = None
        start_time = time.time()
        
        try:
            # 尝试从池中获取连接
            while True:
                try:
                    conn_info = self._pool.get(
                        block=True,
                        timeout=self.connection_timeout
                    )
                    
                    # 检查连接是否有效
                    if conn_info.is_expired(self.max_age) or \
                       not self._validate_connection(conn_info):
                        # 关闭无效连接
                        self._close_connection(conn_info)
                        conn_info = None
                        
                        # 创建新连接
                        if len(self._active_connections) < self.max_connections:
                            conn_info = self._create_connection()
                            break
                    else:
                        # 连接有效，可以使用
                        with self._lock:
                            self._stats['reused'] += 1
                        break
                        
                except Empty:
                    # 池为空，创建新连接
                    with self._lock:
                        if len(self._active_connections) < self.max_connections:
                            conn_info = self._create_connection()
                            break
                    
                    raise TimeoutError(
                        f"Failed to get connection within {self.connection_timeout}s"
                    )
            
            # 更新连接信息
            conn_info.last_used = datetime.now()
            conn_info.use_count += 1
            conn_info.thread_id = current_thread().ident
            
            with self._lock:
                self._active_connections[id(conn_info)] = conn_info
                wait_time = time.time() - start_time
                self._stats['wait_time_total'] += wait_time
                self._stats['use_count_total'] += 1
            
            yield conn_info.connection
            
        except Exception as e:
            with self._lock:
                self._stats['errors'] += 1
            logger.error(f"Connection error: {e}")
            raise
            
        finally:
            # 归还连接到池
            if conn_info:
                with self._lock:
                    self._active_connections.pop(id(conn_info), None)
                
                if not self._closed:
                    try:
                        self._pool.put(conn_info, block=False)
                    except Full:
                        # 池已满，关闭连接
                        self._close_connection(conn_info)
    
    def _close_connection(self, conn_info: ConnectionInfo):
        """关闭连接"""
        try:
            conn_info.connection.close()
            with self._lock:
                self._stats['closed'] += 1
            logger.debug(f"Closed connection (total closed: {self._stats['closed']})")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    def cleanup_idle_connections(self):
        """清理空闲连接"""
        cleaned = 0
        
        # 获取所有空闲连接
        idle_connections = []
        try:
            while not self._pool.empty():
                conn_info = self._pool.get_nowait()
                if conn_info.is_idle(self.idle_timeout):
                    idle_connections.append(conn_info)
                else:
                    # 放回池中
                    self._pool.put_nowait(conn_info)
        except (Empty, Full):
            pass
        
        # 关闭空闲连接
        for conn_info in idle_connections:
            self._close_connection(conn_info)
            cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} idle connections")
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = dict(self._stats)
            stats['pool_size'] = self._pool.qsize()
            stats['active_connections'] = len(self._active_connections)
            stats['total_connections'] = stats['pool_size'] + stats['active_connections']
            
            if stats['use_count_total'] > 0:
                stats['avg_wait_time'] = stats['wait_time_total'] / stats['use_count_total']
                stats['reuse_rate'] = stats['reused'] / stats['use_count_total']
            else:
                stats['avg_wait_time'] = 0
                stats['reuse_rate'] = 0
        
        return stats
    
    def close(self):
        """关闭连接池"""
        if self._closed:
            return
        
        self._closed = True
        
        # 等待活动连接完成
        for _ in range(10):
            with self._lock:
                if not self._active_connections:
                    break
            time.sleep(0.1)
        
        # 关闭所有连接
        closed_count = 0
        while not self._pool.empty():
            try:
                conn_info = self._pool.get_nowait()
                self._close_connection(conn_info)
                closed_count += 1
            except Empty:
                break
        
        logger.info(f"Connection pool closed, {closed_count} connections closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncConnectionPool:
    """异步连接池（用于异步操作）"""
    
    def __init__(self, database_path: str, **kwargs):
        """初始化异步连接池
        
        注意：SQLite不支持真正的异步，这里使用线程池模拟
        """
        self.sync_pool = ConnectionPool(database_path, **kwargs)
    
    async def get_connection(self):
        """异步获取连接"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 在线程池中执行同步操作
        return await loop.run_in_executor(
            None,
            self.sync_pool.get_connection
        )
    
    async def execute(self, query: str, params: tuple = ()):
        """执行查询"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _execute():
            with self.sync_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        
        return await loop.run_in_executor(None, _execute)
    
    async def close(self):
        """关闭连接池"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sync_pool.close)


# 全局连接池实例
_connection_pool: Optional[ConnectionPool] = None


def get_connection_pool(database_path: str = None) -> ConnectionPool:
    """获取全局连接池实例"""
    global _connection_pool
    
    if _connection_pool is None:
        if database_path is None:
            raise ValueError("Database path is required for first initialization")
        
        _connection_pool = ConnectionPool(database_path)
    
    return _connection_pool


def close_connection_pool():
    """关闭全局连接池"""
    global _connection_pool
    
    if _connection_pool:
        _connection_pool.close()
        _connection_pool = None