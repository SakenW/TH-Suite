"""
内存缓存提供者

基于内存的缓存实现，速度快但不持久化
"""

import fnmatch
import threading
from datetime import datetime
from typing import Any

from ..cache_manager import CacheEntry, ICacheProvider


class MemoryCacheProvider(ICacheProvider):
    """内存缓存提供者"""

    def __init__(self, max_size: int = 1000, cleanup_interval: int = 300):
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._last_cleanup = datetime.now()

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        with self._lock:
            self._cleanup_if_needed()

            if key not in self._cache:
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                return None

            # 更新访问信息
            entry.touch()
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值"""
        with self._lock:
            self._cleanup_if_needed()

            # 如果缓存已满，移除最少使用的条目
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()

            entry = CacheEntry(key, value, ttl)
            self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return False

            return True

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()

    def keys(self, pattern: str | None = None) -> list[str]:
        """获取所有键"""
        with self._lock:
            self._cleanup_if_needed()

            if pattern is None:
                return list(self._cache.keys())

            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    def _cleanup_if_needed(self) -> None:
        """定期清理过期条目"""
        now = datetime.now()
        if (now - self._last_cleanup).seconds < self.cleanup_interval:
            return

        self._cleanup_expired()
        self._last_cleanup = now

    def _cleanup_expired(self) -> None:
        """清理过期条目"""
        expired_keys = []

        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

    def _evict_lru(self) -> None:
        """移除最少使用的条目"""
        if not self._cache:
            return

        # 找到最少使用的条目
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)

        del self._cache[lru_key]

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_entries = len(self._cache)
            expired_count = sum(
                1 for entry in self._cache.values() if entry.is_expired()
            )

            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "max_size": self.max_size,
                "memory_usage": f"{total_entries}/{self.max_size} ({total_entries / self.max_size * 100:.1f}%)",
            }
