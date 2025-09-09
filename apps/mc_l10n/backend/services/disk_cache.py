"""
磁盘JSON缓存服务
提供可选的磁盘缓存支持，用于缓存大型JSON数据
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog
import aiofiles
import asyncio
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class DiskCacheEntry:
    """磁盘缓存条目"""
    key: str
    data: Any
    created_at: float
    expires_at: Optional[float]
    size_bytes: int
    access_count: int
    last_access: float


class DiskJSONCache:
    """磁盘JSON缓存实现"""
    
    def __init__(
        self,
        cache_dir: str = "./cache",
        max_size_mb: int = 500,  # 最大缓存500MB
        default_ttl: int = 3600 * 24,  # 默认24小时过期
        cleanup_interval: int = 3600,  # 每小时清理一次
        compression: bool = True,  # 启用压缩
        index_file: str = "cache_index.json"
    ):
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.compression = compression
        self.index_file = self.cache_dir / index_file
        
        # 内存索引
        self.index: Dict[str, DiskCacheEntry] = {}
        self.total_size = 0
        self.cleanup_timer = None
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("磁盘JSON缓存初始化", 
                   cache_dir=str(self.cache_dir),
                   max_size_mb=max_size_mb,
                   default_ttl=default_ttl)
    
    async def initialize(self):
        """初始化缓存"""
        await self._load_index()
        await self._start_cleanup_timer()
        logger.info("磁盘JSON缓存启动完成",
                   entries=len(self.index),
                   total_size_mb=round(self.total_size / 1024 / 1024, 2))
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        entry = self.index.get(key)
        if not entry:
            return None
        
        # 检查过期
        if entry.expires_at and time.time() > entry.expires_at:
            await self._remove_entry(key)
            return None
        
        try:
            # 读取文件
            file_path = self._get_file_path(key)
            
            if self.compression:
                import gzip
                async with aiofiles.open(file_path, 'rb') as f:
                    compressed_data = await f.read()
                data = gzip.decompress(compressed_data).decode('utf-8')
            else:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    data = await f.read()
            
            # 更新访问统计
            entry.access_count += 1
            entry.last_access = time.time()
            
            # 反序列化
            return json.loads(data)
            
        except Exception as e:
            logger.error("磁盘缓存读取失败", key=key, error=str(e))
            await self._remove_entry(key)
            return None
    
    async def put(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """存储缓存数据"""
        try:
            # 序列化数据
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            
            # 压缩数据
            if self.compression:
                import gzip
                compressed_data = gzip.compress(json_data.encode('utf-8'))
                data_to_write = compressed_data
                mode = 'wb'
            else:
                data_to_write = json_data.encode('utf-8')
                mode = 'wb'
            
            # 计算大小
            size_bytes = len(data_to_write)
            
            # 检查空间限制
            await self._ensure_space(size_bytes)
            
            # 写入文件
            file_path = self._get_file_path(key)
            async with aiofiles.open(file_path, mode) as f:
                await f.write(data_to_write)
            
            # 更新索引
            current_time = time.time()
            expires_at = current_time + (ttl or self.default_ttl) if ttl != 0 else None
            
            # 如果key已存在，先移除旧的
            if key in self.index:
                self.total_size -= self.index[key].size_bytes
            
            entry = DiskCacheEntry(
                key=key,
                data=None,  # 不在内存中存储数据
                created_at=current_time,
                expires_at=expires_at,
                size_bytes=size_bytes,
                access_count=1,
                last_access=current_time
            )
            
            self.index[key] = entry
            self.total_size += size_bytes
            
            # 异步保存索引
            asyncio.create_task(self._save_index())
            
            logger.debug("磁盘缓存存储成功", 
                        key=key, 
                        size_kb=round(size_bytes / 1024, 2),
                        compressed=self.compression)
            return True
            
        except Exception as e:
            logger.error("磁盘缓存存储失败", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        return await self._remove_entry(key)
    
    async def clear(self) -> int:
        """清空所有缓存"""
        cleared_count = len(self.index)
        
        # 删除所有文件
        for key in list(self.index.keys()):
            await self._remove_entry(key)
        
        # 清理索引
        self.index.clear()
        self.total_size = 0
        
        await self._save_index()
        
        logger.info("磁盘缓存已清空", cleared_count=cleared_count)
        return cleared_count
    
    async def cleanup_expired(self) -> int:
        """清理过期的缓存条目"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.index.items():
            if entry.expires_at and current_time > entry.expires_at:
                expired_keys.append(key)
        
        # 删除过期条目
        for key in expired_keys:
            await self._remove_entry(key)
        
        if expired_keys:
            await self._save_index()
            logger.info("清理过期磁盘缓存", removed_count=len(expired_keys))
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        current_time = time.time()
        expired_count = 0
        
        for entry in self.index.values():
            if entry.expires_at and current_time > entry.expires_at:
                expired_count += 1
        
        return {
            "total_entries": len(self.index),
            "total_size_mb": round(self.total_size / 1024 / 1024, 2),
            "max_size_mb": round(self.max_size_bytes / 1024 / 1024, 2),
            "utilization_percent": round((self.total_size / self.max_size_bytes) * 100, 1),
            "expired_entries": expired_count,
            "compression_enabled": self.compression,
            "cache_directory": str(self.cache_dir),
        }
    
    def get_entries_info(self) -> List[Dict[str, Any]]:
        """获取所有缓存条目信息"""
        current_time = time.time()
        entries_info = []
        
        for entry in self.index.values():
            info = {
                "key": entry.key,
                "size_kb": round(entry.size_bytes / 1024, 2),
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "access_count": entry.access_count,
                "last_access": entry.last_access,
                "is_expired": entry.expires_at and current_time > entry.expires_at,
                "age_hours": round((current_time - entry.created_at) / 3600, 1),
            }
            entries_info.append(info)
        
        # 按最后访问时间排序
        return sorted(entries_info, key=lambda x: x['last_access'], reverse=True)
    
    async def _load_index(self):
        """加载缓存索引"""
        try:
            if not self.index_file.exists():
                return
            
            async with aiofiles.open(self.index_file, 'r', encoding='utf-8') as f:
                data = await f.read()
            
            index_data = json.loads(data)
            
            # 重建索引
            for key, entry_data in index_data.get('entries', {}).items():
                entry = DiskCacheEntry(
                    key=entry_data['key'],
                    data=None,
                    created_at=entry_data['created_at'],
                    expires_at=entry_data.get('expires_at'),
                    size_bytes=entry_data['size_bytes'],
                    access_count=entry_data['access_count'],
                    last_access=entry_data['last_access'],
                )
                
                # 验证文件是否存在
                file_path = self._get_file_path(key)
                if file_path.exists():
                    self.index[key] = entry
                    self.total_size += entry.size_bytes
                else:
                    logger.warning("缓存文件不存在，跳过索引条目", key=key, file_path=str(file_path))
            
            logger.info("磁盘缓存索引加载完成", entries=len(self.index))
            
        except Exception as e:
            logger.error("加载磁盘缓存索引失败", error=str(e))
            self.index.clear()
            self.total_size = 0
    
    async def _save_index(self):
        """保存缓存索引"""
        try:
            index_data = {
                "version": "1.0",
                "saved_at": time.time(),
                "entries": {}
            }
            
            for key, entry in self.index.items():
                index_data["entries"][key] = {
                    "key": entry.key,
                    "created_at": entry.created_at,
                    "expires_at": entry.expires_at,
                    "size_bytes": entry.size_bytes,
                    "access_count": entry.access_count,
                    "last_access": entry.last_access,
                }
            
            # 写入索引文件
            async with aiofiles.open(self.index_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index_data, indent=2))
                
        except Exception as e:
            logger.error("保存磁盘缓存索引失败", error=str(e))
    
    def _get_file_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用key的哈希作为文件名，避免特殊字符问题
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def _remove_entry(self, key: str) -> bool:
        """移除缓存条目"""
        if key not in self.index:
            return False
        
        try:
            entry = self.index[key]
            file_path = self._get_file_path(key)
            
            # 删除文件
            if file_path.exists():
                file_path.unlink()
            
            # 更新统计
            self.total_size -= entry.size_bytes
            del self.index[key]
            
            return True
        except Exception as e:
            logger.error("移除磁盘缓存条目失败", key=key, error=str(e))
            return False
    
    async def _ensure_space(self, required_bytes: int):
        """确保有足够的空间"""
        while self.total_size + required_bytes > self.max_size_bytes:
            # 找到最少使用的条目
            if not self.index:
                break
            
            # 按访问次数和最后访问时间排序
            entries_by_usage = sorted(
                self.index.items(),
                key=lambda x: (x[1].access_count, x[1].last_access)
            )
            
            # 移除最少使用的条目
            key_to_remove = entries_by_usage[0][0]
            await self._remove_entry(key_to_remove)
            
            logger.debug("磁盘缓存空间清理", removed_key=key_to_remove)
    
    async def _start_cleanup_timer(self):
        """启动定期清理定时器"""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("磁盘缓存定期清理失败", error=str(e))
        
        self.cleanup_timer = asyncio.create_task(cleanup_task())
        logger.info("磁盘缓存定期清理启动", interval_seconds=self.cleanup_interval)
    
    async def shutdown(self):
        """关闭缓存服务"""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
            try:
                await self.cleanup_timer
            except asyncio.CancelledError:
                pass
        
        await self._save_index()
        logger.info("磁盘JSON缓存服务已关闭")


# ==================== 全局磁盘缓存实例 ====================

_global_disk_cache: Optional[DiskJSONCache] = None


def get_disk_cache() -> DiskJSONCache:
    """获取全局磁盘缓存实例"""
    global _global_disk_cache
    if _global_disk_cache is None:
        _global_disk_cache = DiskJSONCache()
    return _global_disk_cache


async def initialize_disk_cache(config: Optional[Dict[str, Any]] = None):
    """初始化全局磁盘缓存"""
    global _global_disk_cache
    
    if config:
        _global_disk_cache = DiskJSONCache(**config)
    else:
        _global_disk_cache = DiskJSONCache()
    
    await _global_disk_cache.initialize()


async def shutdown_disk_cache():
    """关闭全局磁盘缓存"""
    global _global_disk_cache
    if _global_disk_cache:
        await _global_disk_cache.shutdown()
        _global_disk_cache = None


# ==================== 便捷函数 ====================

async def disk_cache_get(key: str) -> Optional[Any]:
    """从磁盘缓存获取数据"""
    cache = get_disk_cache()
    return await cache.get(key)


async def disk_cache_put(key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """存储数据到磁盘缓存"""
    cache = get_disk_cache()
    return await cache.put(key, data, ttl)


async def disk_cache_delete(key: str) -> bool:
    """从磁盘缓存删除数据"""
    cache = get_disk_cache()
    return await cache.delete(key)


def disk_cache_stats() -> Dict[str, Any]:
    """获取磁盘缓存统计"""
    cache = get_disk_cache()
    return cache.get_stats()