"""
缓存管理器

提供统一的缓存接口和管理
"""

import hashlib
import pickle
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any


class CacheEntry:
    """缓存条目"""

    def __init__(self, key: str, value: Any, ttl: int | None = None):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False

        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

    def touch(self) -> None:
        """更新访问时间"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class ICacheProvider(ABC):
    """缓存提供者接口"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存"""
        pass

    @abstractmethod
    def keys(self, pattern: str | None = None) -> list[str]:
        """获取所有键"""
        pass


class CacheManager:
    """缓存管理器"""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._providers: dict[str, ICacheProvider] = {}
        self._default_provider: ICacheProvider | None = None
        self._lock = threading.RLock()

    def add_provider(
        self, name: str, provider: ICacheProvider, is_default: bool = False
    ) -> "CacheManager":
        """添加缓存提供者"""
        with self._lock:
            self._providers[name] = provider
            if is_default or self._default_provider is None:
                self._default_provider = provider
        return self

    def get_provider(self, name: str | None = None) -> ICacheProvider:
        """获取缓存提供者"""
        with self._lock:
            if name is None:
                if self._default_provider is None:
                    raise ValueError("没有设置默认缓存提供者")
                return self._default_provider

            if name not in self._providers:
                raise ValueError(f"缓存提供者 {name} 不存在")

            return self._providers[name]

    def get(self, key: str, provider: str | None = None) -> Any | None:
        """获取缓存值"""
        cache_provider = self.get_provider(provider)
        return cache_provider.get(key)

    def set(
        self, key: str, value: Any, ttl: int | None = None, provider: str | None = None
    ) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl

        cache_provider = self.get_provider(provider)
        cache_provider.set(key, value, ttl)

    def delete(self, key: str, provider: str | None = None) -> bool:
        """删除缓存值"""
        cache_provider = self.get_provider(provider)
        return cache_provider.delete(key)

    def exists(self, key: str, provider: str | None = None) -> bool:
        """检查键是否存在"""
        cache_provider = self.get_provider(provider)
        return cache_provider.exists(key)

    def clear(self, provider: str | None = None) -> None:
        """清空缓存"""
        if provider is None:
            # 清空所有提供者
            with self._lock:
                for cache_provider in self._providers.values():
                    cache_provider.clear()
        else:
            cache_provider = self.get_provider(provider)
            cache_provider.clear()

    def keys(
        self, pattern: str | None = None, provider: str | None = None
    ) -> list[str]:
        """获取键列表"""
        cache_provider = self.get_provider(provider)
        return cache_provider.keys(pattern)

    def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: int | None = None,
        provider: str | None = None,
    ) -> Any:
        """获取缓存值，如果不存在则通过工厂函数创建"""
        value = self.get(key, provider)

        if value is None:
            value = factory()
            self.set(key, value, ttl, provider)

        return value

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """生成缓存键"""
        # 创建一个包含所有参数的字符串
        key_parts = []

        for arg in args:
            if isinstance(arg, str | int | float | bool):
                key_parts.append(str(arg))
            else:
                key_parts.append(str(hash(pickle.dumps(arg, protocol=0))))

        for k, v in sorted(kwargs.items()):
            if isinstance(v, str | int | float | bool):
                key_parts.append(f"{k}={v}")
            else:
                key_parts.append(f"{k}={hash(pickle.dumps(v, protocol=0))}")

        key_string = "|".join(key_parts)

        # 使用MD5生成固定长度的键
        return hashlib.md5(key_string.encode("utf-8")).hexdigest()
