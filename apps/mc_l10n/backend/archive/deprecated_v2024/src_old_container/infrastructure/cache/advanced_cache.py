"""
高级缓存系统
提供多层缓存、智能淘汰策略和性能监控
"""

import hashlib
import logging
import pickle
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import OrderedDict
import sqlite3

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    TTL = "ttl"  # 时间过期
    FIFO = "fifo"  # 先进先出


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int
    ttl: Optional[int] = None
    size: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def touch(self):
        """更新访问时间和计数"""
        self.accessed_at = datetime.now()
        self.access_count += 1


class CacheMetrics:
    """缓存指标"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size = 0
        self.max_size = 0
        self._lock = threading.Lock()
    
    def record_hit(self):
        with self._lock:
            self.hits += 1
    
    def record_miss(self):
        with self._lock:
            self.misses += 1
    
    def record_eviction(self):
        with self._lock:
            self.evictions += 1
    
    def update_size(self, size: int):
        with self._lock:
            self.size = size
    
    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.get_hit_rate(),
            "size": self.size,
            "max_size": self.max_size,
        }


class CacheBackend(ABC):
    """缓存后端接口"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        pass
    
    @abstractmethod
    def set(self, key: str, entry: CacheEntry) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        pass
    
    @abstractmethod
    def size(self) -> int:
        pass


class MemoryCache(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                # LRU: 将访问的项移到末尾
                self._cache.move_to_end(key)
                entry.touch()
            return entry
    
    def set(self, key: str, entry: CacheEntry) -> bool:
        with self._lock:
            # 检查是否需要淘汰
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # 删除最旧的项
            
            self._cache[key] = entry
            return True
    
    def delete(self, key: str) -> bool:
        with self._lock:
            return self._cache.pop(key, None) is not None
    
    def clear(self) -> bool:
        with self._lock:
            self._cache.clear()
            return True
    
    def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())
    
    def size(self) -> int:
        return len(self._cache)


class SQLiteCache(CacheBackend):
    """SQLite持久化缓存后端"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    ttl INTEGER,
                    size INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)
            """)
    
    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM cache_entries WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                entry = CacheEntry(
                    key=row["key"],
                    value=pickle.loads(row["value"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    accessed_at=datetime.fromisoformat(row["accessed_at"]),
                    access_count=row["access_count"],
                    ttl=row["ttl"],
                    size=row["size"],
                )
                
                # 更新访问时间
                entry.touch()
                conn.execute(
                    """
                    UPDATE cache_entries 
                    SET accessed_at = ?, access_count = ?
                    WHERE key = ?
                    """,
                    (entry.accessed_at.isoformat(), entry.access_count, key)
                )
                
                return entry
    
    def set(self, key: str, entry: CacheEntry) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO cache_entries
                        (key, value, created_at, accessed_at, access_count, ttl, size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            key,
                            pickle.dumps(entry.value),
                            entry.created_at.isoformat(),
                            entry.accessed_at.isoformat(),
                            entry.access_count,
                            entry.ttl,
                            entry.size,
                        )
                    )
                return True
            except Exception as e:
                logger.error(f"Failed to set cache entry {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to delete cache entry {key}: {e}")
                return False
    
    def clear(self) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM cache_entries")
                return True
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
                return False
    
    def keys(self) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key FROM cache_entries")
            return [row[0] for row in cursor.fetchall()]
    
    def size(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
            return cursor.fetchone()[0]


class AdvancedCache:
    """高级缓存管理器"""
    
    def __init__(
        self,
        backend: CacheBackend,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: Optional[int] = None,
        max_memory_size: int = 100 * 1024 * 1024,  # 100MB
        cleanup_interval: int = 300,  # 5分钟
    ):
        self.backend = backend
        self.strategy = strategy
        self.default_ttl = default_ttl
        self.max_memory_size = max_memory_size
        self.cleanup_interval = cleanup_interval
        self.metrics = CacheMetrics()
        
        # 启动清理任务
        self._cleanup_timer = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """启动定期清理任务"""
        def cleanup_task():
            self._cleanup_expired()
            self._cleanup_timer = threading.Timer(self.cleanup_interval, cleanup_task)
            self._cleanup_timer.start()
        
        self._cleanup_timer = threading.Timer(self.cleanup_interval, cleanup_task)
        self._cleanup_timer.start()
    
    def _cleanup_expired(self):
        """清理过期条目"""
        expired_keys = []
        
        for key in self.backend.keys():
            entry = self.backend.get(key)
            if entry and entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.backend.delete(key)
            self.metrics.record_eviction()
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            return len(pickle.dumps(value))
        except Exception:
            return 1024  # 默认大小
    
    def _make_key(self, key: Union[str, Tuple]) -> str:
        """生成缓存键"""
        if isinstance(key, str):
            return key
        
        # 对复杂键生成哈希
        key_str = str(key)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: Union[str, Tuple]) -> Optional[Any]:
        """获取缓存值"""
        cache_key = self._make_key(key)
        entry = self.backend.get(cache_key)
        
        if entry is None:
            self.metrics.record_miss()
            return None
        
        if entry.is_expired():
            self.backend.delete(cache_key)
            self.metrics.record_miss()
            self.metrics.record_eviction()
            return None
        
        self.metrics.record_hit()
        return entry.value
    
    def set(
        self,
        key: Union[str, Tuple],
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存值"""
        cache_key = self._make_key(key)
        size = self._calculate_size(value)
        
        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=0,
            ttl=ttl or self.default_ttl,
            size=size,
        )
        
        return self.backend.set(cache_key, entry)
    
    def delete(self, key: Union[str, Tuple]) -> bool:
        """删除缓存值"""
        cache_key = self._make_key(key)
        return self.backend.delete(cache_key)
    
    def clear(self) -> bool:
        """清空缓存"""
        return self.backend.clear()
    
    def get_or_set(
        self,
        key: Union[str, Tuple],
        factory_func,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """获取或设置缓存值"""
        value = self.get(key)
        if value is not None:
            return value
        
        # 计算新值
        value = factory_func(*args, **kwargs)
        self.set(key, value, ttl)
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = self.metrics.get_stats()
        stats.update({
            "backend_size": self.backend.size(),
            "strategy": self.strategy.value,
            "default_ttl": self.default_ttl,
        })
        return stats
    
    def shutdown(self):
        """关闭缓存管理器"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()


class CacheManager:
    """缓存管理器 - 管理多个缓存实例"""
    
    def __init__(self):
        self._caches: Dict[str, AdvancedCache] = {}
    
    def create_cache(
        self,
        name: str,
        backend_type: str = "memory",
        **options
    ) -> AdvancedCache:
        """创建缓存实例"""
        if backend_type == "memory":
            backend = MemoryCache(max_size=options.get("max_size", 1000))
        elif backend_type == "sqlite":
            db_path = options.get("db_path", f"{name}_cache.db")
            backend = SQLiteCache(db_path)
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")
        
        cache = AdvancedCache(
            backend=backend,
            strategy=CacheStrategy(options.get("strategy", "lru")),
            default_ttl=options.get("default_ttl"),
            max_memory_size=options.get("max_memory_size", 100 * 1024 * 1024),
            cleanup_interval=options.get("cleanup_interval", 300),
        )
        
        self._caches[name] = cache
        logger.info(f"Created cache '{name}' with backend '{backend_type}'")
        return cache
    
    def get_cache(self, name: str) -> Optional[AdvancedCache]:
        """获取缓存实例"""
        return self._caches.get(name)
    
    def remove_cache(self, name: str) -> bool:
        """移除缓存实例"""
        if name in self._caches:
            cache = self._caches.pop(name)
            cache.shutdown()
            return True
        return False
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的统计信息"""
        return {name: cache.get_stats() for name, cache in self._caches.items()}
    
    def shutdown_all(self):
        """关闭所有缓存"""
        for cache in self._caches.values():
            cache.shutdown()
        self._caches.clear()


# 全局缓存管理器实例
cache_manager = CacheManager()


# 缓存装饰器
def cached(
    cache_name: str = "default",
    key_func=None,
    ttl: Optional[int] = None,
    backend_type: str = "memory",
    **cache_options
):
    """缓存装饰器"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取或创建缓存
            cache = cache_manager.get_cache(cache_name)
            if cache is None:
                cache = cache_manager.create_cache(
                    cache_name, backend_type, **cache_options
                )
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 计算并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator