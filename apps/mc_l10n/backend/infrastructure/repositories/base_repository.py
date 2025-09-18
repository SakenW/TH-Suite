"""
V5架构基础Repository类
提供通用的数据库操作方法和连接管理
"""

import sqlite3
import structlog
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, TypeVar, Generic
from contextlib import contextmanager

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """V5架构基础Repository类"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # 支持字典式访问
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_transaction(self):
        """获取事务的上下文管理器"""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"事务回滚: {e}")
                raise
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_single(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """执行查询并返回单个结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def execute_write(self, query: str, params: tuple = ()) -> int:
        """执行写操作并返回受影响的行数"""
        with self.get_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_write_with_id(self, query: str, params: tuple = ()) -> int:
        """执行写操作并返回新插入记录的ID"""
        with self.get_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid
    
    def execute_batch(self, query: str, params_list: List[tuple]) -> int:
        """批量执行写操作"""
        with self.get_transaction() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    def table_name(self) -> str:
        """返回表名"""
        pass
    
    @abstractmethod
    def create(self, entity: T) -> str:
        """创建实体并返回UID"""
        pass
    
    @abstractmethod
    def get_by_uid(self, uid: str) -> Optional[T]:
        """根据UID获取实体"""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> bool:
        """更新实体"""
        pass
    
    @abstractmethod
    def delete_by_uid(self, uid: str) -> bool:
        """根据UID删除实体"""
        pass
    
    @abstractmethod
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """列出所有实体"""
        pass
    
    # 通用辅助方法
    def exists_by_uid(self, uid: str) -> bool:
        """检查UID是否存在"""
        query = f"SELECT 1 FROM {self.table_name()} WHERE uid = ? LIMIT 1"
        result = self.execute_single(query, (uid,))
        return result is not None
    
    def count(self) -> int:
        """计算表中记录总数"""
        query = f"SELECT COUNT(*) FROM {self.table_name()}"
        result = self.execute_single(query)
        return result[0] if result else 0
    
    def get_table_info(self) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        query = f"PRAGMA table_info({self.table_name()})"
        rows = self.execute_query(query)
        return [dict(row) for row in rows]