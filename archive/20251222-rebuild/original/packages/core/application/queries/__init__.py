"""
查询模块

提供CQRS中的查询处理功能
"""

from .query import BaseQueryHandler, IQueryHandler, Query, QueryBus

__all__ = ["Query", "IQueryHandler", "BaseQueryHandler", "QueryBus"]
