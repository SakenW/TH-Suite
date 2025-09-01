"""
仓储模块

提供数据访问仓储模式实现
"""

from .base import BaseRepository, IRepository
from .repository import Repository

__all__ = ["IRepository", "BaseRepository", "Repository"]
