"""
高级缓存策略服务
实现多层缓存、LRU策略、智能预加载等功能
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from collections import OrderedDict
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    key: str
    value: T
    created_at: float
    accessed_at: float
    access_count: int
    ttl: Optional[float] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间"""
        self.accessed_at = time.time()
        self.access_count += 1


class LRUCache(Generic[T]):
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存项"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            # 更新访问信息并移到末尾 (最近使用)
            entry.touch()
            self._cache.move_to_end(key)
            self._hits += 1
            
            return entry.value
    
    def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """存储缓存项"""
        with self._lock:
            # 计算大小
            size_bytes = self._estimate_size(value)
            
            # 如果已存在，先删除
            if key in self._cache:
                del self._cache[key]
            
            # 检查空间，必要时清理
            while len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # 添加新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=1,
                ttl=ttl or self.default_ttl,
                size_bytes=size_bytes
            )
            
            self._cache[key] = entry
    
    def remove(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def _evict_lru(self) -> None:
        """清理最久未使用的条目"""
        if self._cache:
            self._cache.popitem(last=False)  # 删除最旧的项
            self._evictions += 1
    
    def _estimate_size(self, value: T) -> int:
        """估算对象大小"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (dict, list)):
                return len(json.dumps(value).encode('utf-8'))
            elif hasattr(value, '__sizeof__'):
                return value.__sizeof__()
            else:
                return 64  # 默认大小
        except Exception:
            return 64
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 3),
                "evictions": self._evictions,
                "total_size_bytes": total_size,
                "avg_size_bytes": total_size // len(self._cache) if self._cache else 0
            }


class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(self):
        # L1: 内存缓存 (最近访问的1000个翻译条目)
        self.l1_translations = LRUCache[Dict](max_size=1000, default_ttl=3600)
        
        # L2: 语言文件缓存 (最近100个语言文件)
        self.l2_language_files = LRUCache[Dict](max_size=100, default_ttl=7200)
        
        # L3: MOD元数据缓存 (最近500个MOD)
        self.l3_mod_metadata = LRUCache[Dict](max_size=500, default_ttl=14400)
        
        # L4: 统计数据缓存
        self.l4_statistics = LRUCache[Dict](max_size=50, default_ttl=1800)
        
        # 预加载任务队列
        self.preload_queue: List[Callable] = []
        
        logger.info("多级缓存系统初始化完成")
    
    def get_translation(self, key: str) -> Optional[Dict[str, Any]]:
        """获取翻译条目"""
        return self.l1_translations.get(key)
    
    def put_translation(self, key: str, translation: Dict[str, Any], ttl: Optional[float] = None):
        """存储翻译条目"""
        self.l1_translations.put(key, translation, ttl)
    
    def get_language_file(self, key: str) -> Optional[Dict[str, Any]]:
        """获取语言文件"""
        return self.l2_language_files.get(key)
    
    def put_language_file(self, key: str, language_file: Dict[str, Any], ttl: Optional[float] = None):
        """存储语言文件"""
        self.l2_language_files.put(key, language_file, ttl)
    
    def get_mod_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """获取MOD元数据"""
        return self.l3_mod_metadata.get(key)
    
    def put_mod_metadata(self, key: str, mod_data: Dict[str, Any], ttl: Optional[float] = None):
        """存储MOD元数据"""
        self.l3_mod_metadata.put(key, mod_data, ttl)
    
    def get_statistics(self, key: str) -> Optional[Dict[str, Any]]:
        """获取统计数据"""
        return self.l4_statistics.get(key)
    
    def put_statistics(self, key: str, stats: Dict[str, Any], ttl: Optional[float] = None):
        """存储统计数据"""
        self.l4_statistics.put(key, stats, ttl)
    
    def clear_all(self):
        """清空所有缓存"""
        self.l1_translations.clear()
        self.l2_language_files.clear()
        self.l3_mod_metadata.clear()
        self.l4_statistics.clear()
        logger.info("清空所有缓存")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有缓存层统计"""
        return {
            "l1_translations": self.l1_translations.get_stats(),
            "l2_language_files": self.l2_language_files.get_stats(),
            "l3_mod_metadata": self.l3_mod_metadata.get_stats(),
            "l4_statistics": self.l4_statistics.get_stats(),
            "total_memory_estimate_mb": self._estimate_total_memory() / (1024 * 1024)
        }
    
    def _estimate_total_memory(self) -> int:
        """估算总内存使用"""
        return (
            self.l1_translations.get_stats().get("total_size_bytes", 0) +
            self.l2_language_files.get_stats().get("total_size_bytes", 0) +
            self.l3_mod_metadata.get_stats().get("total_size_bytes", 0) +
            self.l4_statistics.get_stats().get("total_size_bytes", 0)
        )


class SmartCacheWarmer:
    """智能缓存预热器"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.warming_strategies: List[Callable] = []
        
    def add_warming_strategy(self, strategy: Callable):
        """添加预热策略"""
        self.warming_strategies.append(strategy)
    
    async def warm_popular_translations(self, db_manager):
        """预热热门翻译"""
        try:
            from database.repositories.translation_entry_repository import TranslationEntryRepository
            repo = TranslationEntryRepository(db_manager)
            
            # 获取最近更新的翻译
            recent_entries = await repo.get_recent_updates(limit=100)
            
            for entry in recent_entries:
                cache_key = f"translation:{entry.uid}"
                self.cache.put_translation(
                    cache_key,
                    entry.to_dict(),
                    ttl=3600
                )
            
            logger.info("预热热门翻译完成", count=len(recent_entries))
            
        except Exception as e:
            logger.error("预热热门翻译失败", error=str(e))
    
    async def warm_mod_metadata(self, db_manager):
        """预热MOD元数据"""
        try:
            from database.repositories.mod_repository import ModRepository
            repo = ModRepository(db_manager)
            
            # 获取活跃的MOD
            mods = await repo.find_by(limit=50)  # 假设有这个方法
            
            for mod in mods:
                cache_key = f"mod:{mod.uid}"
                self.cache.put_mod_metadata(
                    cache_key,
                    mod.to_dict(),
                    ttl=14400
                )
            
            logger.info("预热MOD元数据完成", count=len(mods))
            
        except Exception as e:
            logger.error("预热MOD元数据失败", error=str(e))


class CacheKeyGenerator:
    """缓存键生成器"""
    
    @staticmethod
    def translation_key(translation_uid: str) -> str:
        """翻译条目缓存键"""
        return f"translation:{translation_uid}"
    
    @staticmethod
    def language_file_key(file_uid: str) -> str:
        """语言文件缓存键"""
        return f"language_file:{file_uid}"
    
    @staticmethod
    def mod_key(mod_uid: str) -> str:
        """MOD缓存键"""
        return f"mod:{mod_uid}"
    
    @staticmethod
    def statistics_key(stat_type: str, params: Dict[str, Any]) -> str:
        """统计数据缓存键"""
        param_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"stats:{stat_type}:{param_hash}"
    
    @staticmethod
    def search_result_key(query: str, filters: Dict[str, Any]) -> str:
        """搜索结果缓存键"""
        search_hash = hashlib.md5(
            f"{query}:{json.dumps(filters, sort_keys=True)}".encode()
        ).hexdigest()[:8]
        return f"search:{search_hash}"


class CacheService:
    """高级缓存服务"""
    
    def __init__(self):
        self.cache = MultiLevelCache()
        self.warmer = SmartCacheWarmer(self.cache)
        self.key_gen = CacheKeyGenerator()
        
        # 缓存配置
        self.config = {
            "enable_preloading": True,
            "auto_warmup": True,
            "cleanup_interval": 3600,  # 1小时清理一次
            "max_memory_mb": 256,      # 最大内存使用
            "hit_rate_threshold": 0.7   # 命中率阈值
        }
        
        # 性能统计
        self.performance_stats = {
            "cache_saves_ms": [],  # 缓存节省的毫秒数
            "memory_usage_history": []
        }
        
    def get_or_compute(
        self, 
        key: str, 
        compute_func: Callable[[], T], 
        cache_level: str = "l1",
        ttl: Optional[float] = None
    ) -> T:
        """获取缓存或计算值"""
        start_time = time.time()
        
        # 从对应缓存层获取
        cache_map = {
            "l1": self.cache.l1_translations,
            "l2": self.cache.l2_language_files, 
            "l3": self.cache.l3_mod_metadata,
            "l4": self.cache.l4_statistics
        }
        
        cache_instance = cache_map.get(cache_level, self.cache.l1_translations)
        cached_value = cache_instance.get(key)
        
        if cached_value is not None:
            # 记录缓存命中节省的时间
            saved_ms = (time.time() - start_time) * 1000
            self.performance_stats["cache_saves_ms"].append(saved_ms)
            return cached_value
        
        # 计算值
        computed_value = compute_func()
        
        # 存储到缓存
        cache_instance.put(key, computed_value, ttl)
        
        return computed_value
    
    def invalidate_pattern(self, pattern: str):
        """按模式失效缓存"""
        # 简单实现：清理包含模式的所有键
        for cache_instance in [
            self.cache.l1_translations,
            self.cache.l2_language_files,
            self.cache.l3_mod_metadata,
            self.cache.l4_statistics
        ]:
            with cache_instance._lock:
                keys_to_remove = [
                    key for key in cache_instance._cache.keys()
                    if pattern in key
                ]
                for key in keys_to_remove:
                    cache_instance.remove(key)
        
        logger.info("按模式失效缓存", pattern=pattern)
    
    async def cleanup_expired(self):
        """清理过期缓存"""
        total_removed = 0
        
        for cache_name, cache_instance in [
            ("l1", self.cache.l1_translations),
            ("l2", self.cache.l2_language_files),
            ("l3", self.cache.l3_mod_metadata),
            ("l4", self.cache.l4_statistics)
        ]:
            with cache_instance._lock:
                expired_keys = [
                    key for key, entry in cache_instance._cache.items()
                    if entry.is_expired()
                ]
                
                for key in expired_keys:
                    del cache_instance._cache[key]
                    total_removed += 1
        
        logger.info("清理过期缓存完成", removed_count=total_removed)
        return total_removed
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取缓存健康报告"""
        all_stats = self.cache.get_all_stats()
        
        # 计算整体命中率
        total_hits = sum(
            stats.get("hits", 0) for stats in all_stats.values()
            if isinstance(stats, dict)
        )
        total_requests = sum(
            stats.get("hits", 0) + stats.get("misses", 0)
            for stats in all_stats.values()
            if isinstance(stats, dict)
        )
        
        overall_hit_rate = total_hits / total_requests if total_requests > 0 else 0.0
        
        # 内存使用状况
        memory_usage_mb = all_stats.get("total_memory_estimate_mb", 0)
        memory_health = "good" if memory_usage_mb < self.config["max_memory_mb"] else "warning"
        
        # 性能指标
        avg_cache_save_ms = (
            sum(self.performance_stats["cache_saves_ms"]) / 
            len(self.performance_stats["cache_saves_ms"])
            if self.performance_stats["cache_saves_ms"] else 0
        )
        
        return {
            "overall_hit_rate": round(overall_hit_rate, 3),
            "memory_usage_mb": memory_usage_mb,
            "memory_health": memory_health,
            "avg_cache_save_ms": round(avg_cache_save_ms, 2),
            "cache_levels": all_stats,
            "config": self.config,
            "health_score": self._calculate_health_score(overall_hit_rate, memory_usage_mb)
        }
    
    def _calculate_health_score(self, hit_rate: float, memory_mb: float) -> float:
        """计算缓存健康评分 (0-100)"""
        hit_rate_score = min(100, hit_rate * 100)
        memory_score = max(0, 100 - (memory_mb / self.config["max_memory_mb"]) * 100)
        
        return round((hit_rate_score * 0.7 + memory_score * 0.3), 1)


# 全局缓存服务实例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        logger.info("高级缓存服务初始化完成")
    return _cache_service