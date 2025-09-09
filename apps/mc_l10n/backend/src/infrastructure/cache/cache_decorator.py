"""
缓存装饰器
提供便捷的缓存功能
"""

import hashlib
import json
import logging
import pickle
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self._cache: dict[str, tuple] = {}
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry is None or datetime.now() < expiry:
                self._stats["hits"] += 1
                return value
            else:
                # 过期了，删除
                del self._cache[key]
                self._stats["evictions"] += 1

        self._stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
        """
        expiry = None
        if ttl:
            expiry = datetime.now() + timedelta(seconds=ttl)

        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get_stats(self) -> dict[str, int]:
        """获取统计信息"""
        return {
            **self._stats,
            "size": len(self._cache),
            "hit_rate": self._stats["hits"]
            / max(1, self._stats["hits"] + self._stats["misses"]),
        }


# 全局缓存实例
_cache_manager = CacheManager()


def cache(ttl: int | None = 300, key_prefix: str = ""):
    """缓存装饰器

    Args:
        ttl: 缓存时间（秒），默认5分钟
        key_prefix: 键前缀

    使用示例:
        @cache(ttl=600)
        def expensive_function(param):
            # 昂贵的操作
            return result
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)

            # 尝试从缓存获取
            cached_value = _cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            _cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")

            return result

        # 添加缓存管理方法
        wrapper.cache_clear = lambda: _clear_function_cache(func, key_prefix)
        wrapper.cache_info = lambda: _cache_manager.get_stats()

        return wrapper

    return decorator


def async_cache(ttl: int | None = 300, key_prefix: str = ""):
    """异步缓存装饰器

    Args:
        ttl: 缓存时间（秒）
        key_prefix: 键前缀
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)

            # 尝试从缓存获取
            cached_value = _cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # 执行异步函数
            result = await func(*args, **kwargs)

            # 存入缓存
            _cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")

            return result

        wrapper.cache_clear = lambda: _clear_function_cache(func, key_prefix)
        wrapper.cache_info = lambda: _cache_manager.get_stats()

        return wrapper

    return decorator


def invalidate_cache(pattern: str | None = None):
    """清除缓存装饰器

    用于在函数执行后清除相关缓存

    Args:
        pattern: 要清除的缓存键模式
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 清除匹配的缓存
            if pattern:
                keys_to_delete = [
                    k for k in _cache_manager._cache.keys() if pattern in k
                ]
                for key in keys_to_delete:
                    _cache_manager.delete(key)
                    logger.debug(f"Invalidated cache: {key}")
            else:
                # 清除所有缓存
                _cache_manager.clear()
                logger.debug("Cleared all cache")

            return result

        return wrapper

    return decorator


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict, prefix: str) -> str:
    """生成缓存键"""
    # 创建键的组成部分
    parts = [
        prefix,
        func.__module__,
        func.__name__,
        _serialize_args(args),
        _serialize_kwargs(kwargs),
    ]

    # 过滤空字符串并连接
    key_str = ":".join(filter(None, parts))

    # 如果键太长，使用哈希
    if len(key_str) > 250:
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{func.__name__}:{key_hash}"

    return key_str


def _serialize_args(args: tuple) -> str:
    """序列化参数"""
    try:
        # 尝试JSON序列化（更快）
        return json.dumps(args, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # 回退到pickle
        return hashlib.md5(pickle.dumps(args)).hexdigest()


def _serialize_kwargs(kwargs: dict) -> str:
    """序列化关键字参数"""
    if not kwargs:
        return ""

    try:
        # 尝试JSON序列化
        return json.dumps(kwargs, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # 回退到pickle
        return hashlib.md5(pickle.dumps(kwargs)).hexdigest()


def _clear_function_cache(func: Callable, prefix: str):
    """清除特定函数的缓存"""
    pattern = f"{prefix}:{func.__module__}:{func.__name__}"
    keys_to_delete = [k for k in _cache_manager._cache.keys() if pattern in k]

    for key in keys_to_delete:
        _cache_manager.delete(key)

    logger.info(f"Cleared {len(keys_to_delete)} cache entries for {func.__name__}")


# 导出
def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    return _cache_manager


# 预定义的缓存装饰器
cache_1min = cache(ttl=60)
cache_5min = cache(ttl=300)
cache_10min = cache(ttl=600)
cache_30min = cache(ttl=1800)
cache_1hour = cache(ttl=3600)
cache_1day = cache(ttl=86400)
