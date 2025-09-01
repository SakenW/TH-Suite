"""
仓储实现

通用的仓储实现
"""

from typing import TypeVar

from .base import BaseRepository

T = TypeVar("T")


class Repository(BaseRepository[T]):
    """通用仓储实现"""

    def __init__(self):
        super().__init__()
