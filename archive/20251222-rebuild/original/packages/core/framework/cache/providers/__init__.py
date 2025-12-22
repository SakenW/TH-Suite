"""
缓存提供者

提供多种缓存实现：
- 内存缓存（快速，但重启后丢失）
- 文件系统缓存（持久化，适合单机）
- Redis缓存（分布式，高性能）
"""

from .file_cache import FileCacheProvider
from .memory_cache import MemoryCacheProvider

__all__ = ["MemoryCacheProvider", "FileCacheProvider"]
