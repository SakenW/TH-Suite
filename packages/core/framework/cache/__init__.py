"""
缓存系统

提供统一的缓存接口和多种实现：
- 内存缓存
- Redis缓存
- 文件系统缓存
- 缓存装饰器
"""

from .cache_manager import CacheManager, ICacheProvider
from .decorators import cache_clear, cached
from .providers.file_cache import FileCacheProvider
from .providers.memory_cache import MemoryCacheProvider

__all__ = [
    "ICacheProvider",
    "CacheManager",
    "MemoryCacheProvider",
    "FileCacheProvider",
    "cached",
    "cache_clear",
]
