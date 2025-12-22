"""
数据访问层

提供统一的数据访问抽象：
- 工作单元模式（Unit of Work）
- 仓储模式（Repository Pattern）
- 领域驱动设计（DDD）模型
- 数据库连接和事务管理
"""

from .models.aggregate import AggregateRoot
from .models.base_entity import BaseEntity
from .models.value_object import ValueObject
from .repositories.base import BaseRepository, IRepository
from .repositories.repository import Repository
from .unit_of_work import IUnitOfWork, UnitOfWork

__all__ = [
    "UnitOfWork",
    "IUnitOfWork",
    "IRepository",
    "BaseRepository",
    "Repository",
    "BaseEntity",
    "ValueObject",
    "AggregateRoot",
]
