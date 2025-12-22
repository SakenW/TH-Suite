"""
缓存装饰器

提供方便的函数缓存功能
"""

import functools
from collections.abc import Callable
from typing import Any

from .cache_manager import CacheManager

# 全局缓存管理器实例
_global_cache_manager: CacheManager | None = None


def set_global_cache_manager(cache_manager: CacheManager) -> None:
    """设置全局缓存管理器"""
    global _global_cache_manager
    _global_cache_manager = cache_manager


def get_global_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None:
        # 创建默认缓存管理器
        from .providers.memory_cache import MemoryCacheProvider

        _global_cache_manager = CacheManager()
        _global_cache_manager.add_provider(
            "memory", MemoryCacheProvider(), is_default=True
        )

    return _global_cache_manager


def cached(
    ttl: int | None = None,
    provider: str | None = None,
    key_prefix: str | None = None,
    cache_manager: CacheManager | None = None,
) -> Callable:
    """
    缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        provider: 缓存提供者名称
        key_prefix: 缓存键前缀
        cache_manager: 自定义缓存管理器
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 获取缓存管理器
            cm = cache_manager or get_global_cache_manager()

            # 生成缓存键
            key_parts = [key_prefix] if key_prefix else []
            key_parts.extend([func.__module__, func.__name__])

            # 添加参数到缓存键
            cache_key = "|".join(key_parts) + "|" + cm.generate_key(*args, **kwargs)

            # 尝试从缓存获取
            result = cm.get(cache_key, provider)

            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cm.set(cache_key, result, ttl, provider)

            return result

        # 添加缓存控制方法
        def cache_clear(*args, **kwargs) -> None:
            """清除特定调用的缓存"""
            cm = cache_manager or get_global_cache_manager()

            key_parts = [key_prefix] if key_prefix else []
            key_parts.extend([func.__module__, func.__name__])

            cache_key = "|".join(key_parts) + "|" + cm.generate_key(*args, **kwargs)
            cm.delete(cache_key, provider)

        def cache_clear_all() -> None:
            """清除函数的所有缓存"""
            cm = cache_manager or get_global_cache_manager()

            key_parts = [key_prefix] if key_prefix else []
            key_parts.extend([func.__module__, func.__name__])

            pattern = "|".join(key_parts) + "|*"
            keys = cm.keys(pattern, provider)

            for key in keys:
                cm.delete(key, provider)

        # 绑定缓存控制方法到包装函数
        wrapper.cache_clear = cache_clear
        wrapper.cache_clear_all = cache_clear_all

        return wrapper

    return decorator


def cache_clear(func: Callable, *args, **kwargs) -> None:
    """清除特定函数调用的缓存"""
    if hasattr(func, "cache_clear"):
        func.cache_clear(*args, **kwargs)


def cache_clear_all(func: Callable) -> None:
    """清除函数的所有缓存"""
    if hasattr(func, "cache_clear_all"):
        func.cache_clear_all()


def memoize(func: Callable) -> Callable:
    """简单的记忆化装饰器"""
    return cached()(func)
