"""
扫描结果缓存管理
专门针对模组扫描结果的缓存优化
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from infrastructure.cache.advanced_cache import cached, cache_manager
from infrastructure.minecraft.mod_scanner import ModScanResult

logger = logging.getLogger(__name__)


class ScanCache:
    """扫描缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化缓存实例
        self._file_cache = cache_manager.create_cache(
            "file_scans",
            backend_type="sqlite",
            db_path=str(self.cache_dir / "file_scans.db"),
            default_ttl=3600,  # 1小时
            strategy="lru"
        )
        
        self._mod_info_cache = cache_manager.create_cache(
            "mod_info",
            backend_type="memory",
            max_size=500,
            default_ttl=1800,  # 30分钟
            strategy="lru"
        )
        
        self._translation_cache = cache_manager.create_cache(
            "translations",
            backend_type="sqlite", 
            db_path=str(self.cache_dir / "translations.db"),
            default_ttl=7200,  # 2小时
            strategy="lru"
        )
    
    def _get_file_hash(self, file_path: str) -> str:
        """获取文件哈希值"""
        try:
            stat = os.stat(file_path)
            # 使用文件路径、大小和修改时间生成哈希
            content = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except OSError:
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def get_scan_result(self, file_path: str) -> Optional[ModScanResult]:
        """获取扫描结果缓存"""
        file_hash = self._get_file_hash(file_path)
        cache_key = f"scan:{file_hash}"
        
        cached_result = self._file_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for {file_path}")
            return ModScanResult(**cached_result)
        
        logger.debug(f"Cache miss for {file_path}")
        return None
    
    def set_scan_result(self, file_path: str, result: ModScanResult):
        """设置扫描结果缓存"""
        file_hash = self._get_file_hash(file_path)
        cache_key = f"scan:{file_hash}"
        
        # 存储为字典格式
        self._file_cache.set(cache_key, result.to_dict())
        logger.debug(f"Cached scan result for {file_path}")
    
    def get_mod_info(self, mod_id: str) -> Optional[Dict[str, Any]]:
        """获取模组信息缓存"""
        return self._mod_info_cache.get(f"info:{mod_id}")
    
    def set_mod_info(self, mod_id: str, info: Dict[str, Any]):
        """设置模组信息缓存"""
        self._mod_info_cache.set(f"info:{mod_id}", info)
    
    def get_translations(self, mod_id: str, language: str) -> Optional[Dict[str, str]]:
        """获取翻译缓存"""
        cache_key = f"trans:{mod_id}:{language}"
        return self._translation_cache.get(cache_key)
    
    def set_translations(self, mod_id: str, language: str, translations: Dict[str, str]):
        """设置翻译缓存"""
        cache_key = f"trans:{mod_id}:{language}"
        self._translation_cache.set(cache_key, translations)
    
    def invalidate_file(self, file_path: str):
        """使文件缓存失效"""
        file_hash = self._get_file_hash(file_path)
        cache_key = f"scan:{file_hash}"
        self._file_cache.delete(cache_key)
        logger.debug(f"Invalidated cache for {file_path}")
    
    def invalidate_mod(self, mod_id: str):
        """使模组相关缓存失效"""
        # 清除模组信息缓存
        self._mod_info_cache.delete(f"info:{mod_id}")
        
        # 清除相关的翻译缓存
        # 注意：这里需要遍历所有语言，在实际应用中可能需要更高效的方法
        for key in self._translation_cache.backend.keys():
            if key.startswith(f"trans:{mod_id}:"):
                self._translation_cache.delete(key)
        
        logger.debug(f"Invalidated mod cache for {mod_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "file_cache": self._file_cache.get_stats(),
            "mod_info_cache": self._mod_info_cache.get_stats(),
            "translation_cache": self._translation_cache.get_stats(),
        }
    
    def cleanup(self):
        """清理缓存"""
        self._file_cache.clear()
        self._mod_info_cache.clear()
        self._translation_cache.clear()
        logger.info("Cache cleared")


# 全局扫描缓存实例
scan_cache = ScanCache()


# 缓存装饰器专门用于扫描相关函数
def cache_scan_result(ttl: Optional[int] = 3600):
    """扫描结果缓存装饰器"""
    return cached(
        cache_name="file_scans",
        ttl=ttl,
        backend_type="sqlite"
    )


def cache_mod_info(ttl: Optional[int] = 1800):
    """模组信息缓存装饰器"""
    return cached(
        cache_name="mod_info",
        ttl=ttl,
        backend_type="memory"
    )


def cache_translations(ttl: Optional[int] = 7200):
    """翻译缓存装饰器"""
    return cached(
        cache_name="translations", 
        ttl=ttl,
        backend_type="sqlite"
    )


# 智能缓存预热
class CachePrewarmer:
    """缓存预热器"""
    
    def __init__(self, cache: ScanCache):
        self.cache = cache
    
    def prewarm_recent_files(self, file_paths: list[str], max_files: int = 50):
        """预热最近使用的文件缓存"""
        # 按修改时间排序，选择最新的文件进行预热
        recent_files = []
        for file_path in file_paths:
            try:
                stat = os.stat(file_path)
                recent_files.append((file_path, stat.st_mtime))
            except OSError:
                continue
        
        recent_files.sort(key=lambda x: x[1], reverse=True)
        recent_files = recent_files[:max_files]
        
        logger.info(f"Prewarming cache for {len(recent_files)} recent files")
        
        for file_path, _ in recent_files:
            if not self.cache.get_scan_result(file_path):
                # 这里需要实际的扫描器来填充缓存
                # 在实际使用中，这会触发扫描并缓存结果
                pass
    
    def prewarm_popular_mods(self, mod_ids: list[str]):
        """预热热门模组的信息缓存"""
        logger.info(f"Prewarming cache for {len(mod_ids)} popular mods")
        
        for mod_id in mod_ids:
            if not self.cache.get_mod_info(mod_id):
                # 这里需要从数据库或其他来源加载模组信息
                pass


# 缓存监控和报告
class CacheMonitor:
    """缓存监控器"""
    
    def __init__(self, cache: ScanCache):
        self.cache = cache
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        stats = self.cache.get_stats()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_hit_rate": 0.0,
            "total_size": 0,
            "caches": stats,
        }
        
        # 计算总体命中率
        total_hits = sum(cache_stats.get("hits", 0) for cache_stats in stats.values())
        total_requests = sum(
            cache_stats.get("hits", 0) + cache_stats.get("misses", 0)
            for cache_stats in stats.values()
        )
        
        if total_requests > 0:
            report["overall_hit_rate"] = total_hits / total_requests
        
        # 计算总大小
        report["total_size"] = sum(
            cache_stats.get("size", 0) for cache_stats in stats.values()
        )
        
        return report
    
    def should_optimize(self) -> Dict[str, bool]:
        """判断是否需要优化"""
        stats = self.cache.get_stats()
        recommendations = {}
        
        for cache_name, cache_stats in stats.items():
            hit_rate = cache_stats.get("hit_rate", 0.0)
            size = cache_stats.get("size", 0)
            max_size = cache_stats.get("max_size", 0)
            
            recommendations[cache_name] = {
                "increase_size": hit_rate > 0.9 and size > max_size * 0.8,
                "decrease_size": hit_rate < 0.5 and size > max_size * 0.3,
                "increase_ttl": hit_rate > 0.8,
                "decrease_ttl": hit_rate < 0.3,
            }
        
        return recommendations