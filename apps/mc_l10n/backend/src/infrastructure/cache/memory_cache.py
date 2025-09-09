"""
内存缓存实现
实现CacheRepository接口
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Any

from domain.repositories import CacheRepository

logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目"""

    def __init__(self, value: Any, ttl: int | None = None):
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl
        self.last_accessed = datetime.now()
        self.access_count = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False

        expiry = self.created_at + timedelta(seconds=self.ttl)
        return datetime.now() > expiry

    def access(self) -> Any:
        """访问缓存值"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        return self.value


class MemoryCacheRepository(CacheRepository):
    """内存缓存仓储实现"""

    def __init__(self, max_size: int = 10000):
        self.cache: dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]

                # 检查是否过期
                if entry.is_expired():
                    del self.cache[key]
                    self.misses += 1
                    return None

                self.hits += 1
                return entry.access()

            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值"""
        with self.lock:
            # 检查容量
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict()

            self.cache[key] = CacheEntry(value, ttl)
            return True

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    return True
                else:
                    del self.cache[key]
            return False

    def clear(self) -> bool:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            return True

    def _evict(self):
        """驱逐策略（LRU）"""
        if not self.cache:
            return

        # 找到最少使用的条目
        oldest_key = None
        oldest_time = datetime.now()

        for key, entry in self.cache.items():
            if entry.last_accessed < oldest_time:
                oldest_time = entry.last_accessed
                oldest_key = key

        if oldest_key:
            del self.cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
            }

    def cleanup_expired(self):
        """清理过期条目"""
        with self.lock:
            expired_keys = []

            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
