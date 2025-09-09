"""
基础Repository和Entity定义
提供数据访问层的抽象基类
"""

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, TypeVar
from uuid import UUID, uuid4

T = TypeVar("T", bound="BaseEntity")


@dataclass
class BaseEntity:
    """基础实体类"""

    id: str | int | UUID | None = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_timestamp(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, UUID):
                result[key] = str(value)
            else:
                result[key] = value
        return result


class BaseRepository[T: "BaseEntity"](ABC):
    """基础Repository抽象类"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._lock = Lock()
        self._connection_pool = []
        self.max_connections = 5

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        with self._lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = sqlite3.connect(self.connection_string)
                conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            with self._lock:
                if len(self._connection_pool) < self.max_connections:
                    self._connection_pool.append(conn)
                else:
                    conn.close()

    @abstractmethod
    def find_by_id(self, entity_id: str | int) -> T | None:
        """根据ID查找实体"""
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """查找所有实体"""
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        """保存实体"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, entity_id: str | int) -> bool:
        """删除实体"""
        pass

    def exists(self, entity_id: str | int) -> bool:
        """检查实体是否存在"""
        return self.find_by_id(entity_id) is not None

    def count(self) -> int:
        """统计实体数量"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]

    @property
    @abstractmethod
    def table_name(self) -> str:
        """表名"""
        pass


class UnitOfWork:
    """工作单元模式"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection = None
        self._repositories = {}

    def __enter__(self):
        self._connection = sqlite3.connect(self.connection_string)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self._connection.close()

    def commit(self):
        """提交事务"""
        if self._connection:
            self._connection.commit()

    def rollback(self):
        """回滚事务"""
        if self._connection:
            self._connection.rollback()

    def register_repository(self, name: str, repository: BaseRepository):
        """注册Repository"""
        self._repositories[name] = repository
        repository._connection = self._connection

    def get_repository(self, name: str) -> BaseRepository | None:
        """获取Repository"""
        return self._repositories.get(name)


class QueryBuilder:
    """SQL查询构建器"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._select_fields = ["*"]
        self._where_conditions = []
        self._join_clauses = []
        self._order_by = []
        self._limit = None
        self._offset = None
        self._group_by = []

    def select(self, *fields):
        """选择字段"""
        self._select_fields = list(fields) if fields else ["*"]
        return self

    def where(self, condition: str, *params):
        """添加WHERE条件"""
        self._where_conditions.append((condition, params))
        return self

    def join(self, table: str, on: str):
        """添加JOIN"""
        self._join_clauses.append(f"JOIN {table} ON {on}")
        return self

    def left_join(self, table: str, on: str):
        """添加LEFT JOIN"""
        self._join_clauses.append(f"LEFT JOIN {table} ON {on}")
        return self

    def order_by(self, field: str, direction: str = "ASC"):
        """添加排序"""
        self._order_by.append(f"{field} {direction}")
        return self

    def limit(self, limit: int):
        """设置限制"""
        self._limit = limit
        return self

    def offset(self, offset: int):
        """设置偏移"""
        self._offset = offset
        return self

    def group_by(self, *fields):
        """分组"""
        self._group_by = list(fields)
        return self

    def build(self) -> tuple[str, list]:
        """构建SQL查询"""
        sql = f"SELECT {', '.join(self._select_fields)} FROM {self.table_name}"
        params = []

        # 添加JOIN
        for join_clause in self._join_clauses:
            sql += f" {join_clause}"

        # 添加WHERE
        if self._where_conditions:
            conditions = []
            for condition, condition_params in self._where_conditions:
                conditions.append(condition)
                params.extend(condition_params)
            sql += f" WHERE {' AND '.join(conditions)}"

        # 添加GROUP BY
        if self._group_by:
            sql += f" GROUP BY {', '.join(self._group_by)}"

        # 添加ORDER BY
        if self._order_by:
            sql += f" ORDER BY {', '.join(self._order_by)}"

        # 添加LIMIT和OFFSET
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"

        return sql, params
