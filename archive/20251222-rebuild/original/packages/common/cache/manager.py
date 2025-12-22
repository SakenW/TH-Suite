"""
缓存管理器
提供多种缓存策略实现
"""

import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class CacheStrategy:
    """缓存策略基类"""

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int | None = None):
        """设置缓存值"""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        raise NotImplementedError

    def clear(self):
        """清空缓存"""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        raise NotImplementedError


class LRUCache(CacheStrategy):
    """LRU缓存策略"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key in self._cache:
                # 移动到末尾（最近使用）
                self._cache.move_to_end(key)
                return self._cache[key]["value"]
            return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        with self._lock:
            # 检查是否需要驱逐
            if key not in self._cache and len(self._cache) >= self.max_size:
                # 删除最老的项（第一个）
                self._cache.popitem(last=False)

            # 添加或更新缓存项
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl if ttl else None,
            }
            self._cache.move_to_end(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False

            # 检查是否过期
            item = self._cache[key]
            if item["expires_at"] and time.time() > item["expires_at"]:
                del self._cache[key]
                return False

            return True


class TTLCache(CacheStrategy):
    """TTL缓存策略"""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key in self._cache:
                item = self._cache[key]
                if time.time() < item["expires_at"]:
                    return item["value"]
                else:
                    # 过期，删除
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        with self._lock:
            ttl = ttl or self.default_ttl
            self._cache[key] = {"value": value, "expires_at": time.time() + ttl}

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def cleanup_expired(self):
        """清理过期项"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, item in self._cache.items()
                if current_time > item["expires_at"]
            ]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class CacheManager:
    """缓存管理器"""

    def __init__(self, strategy: CacheStrategy | None = None):
        self.strategy = strategy or LRUCache()
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
        self._lock = Lock()

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        value = self.strategy.get(key)

        with self._lock:
            if value is not None:
                self._stats["hits"] += 1
            else:
                self._stats["misses"] += 1

        return value if value is not None else default

    def set(self, key: str, value: Any, ttl: int | None = None):
        """设置缓存值"""
        self.strategy.set(key, value, ttl)

        with self._lock:
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        result = self.strategy.delete(key)

        if result:
            with self._lock:
                self._stats["deletes"] += 1

        return result

    def clear(self):
        """清空缓存"""
        self.strategy.clear()

        with self._lock:
            self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self.strategy.exists(key)

    def get_stats(self) -> dict[str, int]:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.copy()
            total = stats["hits"] + stats["misses"]
            if total > 0:
                stats["hit_rate"] = stats["hits"] / total
            else:
                stats["hit_rate"] = 0.0
            return stats

    def get_or_set(
        self, key: str, factory: Callable[[], Any], ttl: int | None = None
    ) -> Any:
        """获取或设置缓存值"""
        value = self.get(key)

        if value is None:
            value = factory()
            self.set(key, value, ttl)

        return value


def cached(
    ttl: int | None = None,
    key_prefix: str = "",
    cache_manager: CacheManager | None = None,
):
    """缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        cache_manager: 缓存管理器实例
    """

    def decorator(func: Callable) -> Callable:
        # 使用默认缓存管理器
        nonlocal cache_manager
        if cache_manager is None:
            cache_manager = CacheManager()

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)

            # 尝试从缓存获取
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存储到缓存
            cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__} with key {cache_key}")

            return result

        # 添加缓存管理方法
        wrapper.cache_clear = lambda: cache_manager.clear()
        wrapper.cache_delete = lambda *args, **kwargs: cache_manager.delete(
            _generate_cache_key(func, args, kwargs, key_prefix)
        )
        wrapper.cache_manager = cache_manager

        return wrapper

    return decorator


def _generate_cache_key(
    func: Callable, args: tuple, kwargs: dict, prefix: str = ""
) -> str:
    """生成缓存键"""
    # 创建键的组成部分
    parts = [prefix] if prefix else []
    parts.append(func.__module__)
    parts.append(func.__name__)

    # 添加参数
    if args:
        # 跳过self/cls参数
        if hasattr(args[0].__class__, func.__name__):
            args = args[1:]
        parts.append(str(args))

    if kwargs:
        # 排序kwargs以保证一致性
        sorted_kwargs = sorted(kwargs.items())
        parts.append(str(sorted_kwargs))

    # 生成哈希
    key_str = ":".join(parts)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()

    return (
        f"{prefix}:{func.__name__}:{key_hash}"
        if prefix
        else f"{func.__name__}:{key_hash}"
    )


class MultiLevelCache:
    """多级缓存"""

    def __init__(self, levels: list[CacheStrategy]):
        """
        Args:
            levels: 缓存级别列表，从快到慢排序
        """
        self.levels = levels

    def get(self, key: str) -> Any | None:
        """从多级缓存获取值"""
        for i, cache in enumerate(self.levels):
            value = cache.get(key)
            if value is not None:
                # 回填到更快的缓存级别
                for j in range(i):
                    self.levels[j].set(key, value)
                return value
        return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        """设置所有级别的缓存"""
        for cache in self.levels:
            cache.set(key, value, ttl)

    def delete(self, key: str):
        """从所有级别删除"""
        for cache in self.levels:
            cache.delete(key)

    def clear(self):
        """清空所有级别"""
        for cache in self.levels:
            cache.clear()
