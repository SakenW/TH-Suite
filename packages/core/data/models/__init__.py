"""
领域模型

提供DDD中的基础模型类
"""

from .aggregate import AggregateRoot
from .base_entity import BaseEntity
from .value_object import ValueObject

__all__ = ["BaseEntity", "ValueObject", "AggregateRoot"]
