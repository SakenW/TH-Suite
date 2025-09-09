"""
基于BLAKE3的高性能磁盘缓存
优化磁盘JSON缓存使用BLAKE3进行内容寻址
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog
import aiofiles
import asyncio
from dataclasses import dataclass

from services.content_addressing import (
    ContentAddressingSystem, 
    ContentId, 
    HashAlgorithm,
    compute_cid
)

logger = structlog.get_logger(__name__)


@dataclass
class Blake3CacheEntry:
    """基于BLAKE3的缓存条目"""
    cid: ContentId
    key: str  # 用户指定的键
    created_at: float
    expires_at: Optional[float]
    access_count: int
    last_access: float
    compression_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "cid": self.cid.to_dict(),
            "key": self.key,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_access": self.last_access,
            "compression_type": self.compression_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Blake3CacheEntry':
        """从字典创建"""
        return cls(
            cid=ContentId.from_dict(data["cid"]),
            key=data["key"],
            created_at=data["created_at"],
            expires_at=data.get("expires_at"),
            access_count=data["access_count"],
            last_access=data["last_access"],
            compression_type=data.get("compression_type"),
        )


class Blake3DiskCache:
    """基于BLAKE3内容寻址的磁盘缓存"""
    
    def __init__(
        self,
        cache_dir: str = "./blake3_cache",
        max_size_mb: int = 1000,  # 增加默认缓存大小
        default_ttl: int = 3600 * 24 * 7,  # 默认7天过期
        cleanup_interval: int = 3600,
        compression: str = "zstd",  # 默认使用zstd压缩
        index_file: str = "blake3_cache_index.json",
        enable_deduplication: bool = True,  # 启用去重
        enable_content_verification: bool = True  # 启用内容验证
    ):
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.compression = compression
        self.index_file = self.cache_dir / index_file
        self.enable_deduplication = enable_deduplication
        self.enable_content_verification = enable_content_verification
        
        # 内容寻址系统
        self.content_addressing = ContentAddressingSystem(
            algorithm=HashAlgorithm.BLAKE3,
            enable_caching=True,
            max_cache_entries=50000,
            performance_monitoring=True
        )
        
        # 缓存索引
        self.index: Dict[str, Blake3CacheEntry] = {}  # key -> entry
        self.cid_to_entries: Dict[str, List[Blake3CacheEntry]] = {}  # cid -> entries (去重)
        self.total_size = 0
        self.cleanup_timer = None
        
        # 性能统计
        self.stats = {
            "total_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "deduplication_saves": 0,
            "verification_failures": 0,
            "compression_ratio": 1.0,
            "storage_saved_bytes": 0,
        }
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("BLAKE3磁盘缓存初始化", 
                   cache_dir=str(self.cache_dir),
                   max_size_mb=max_size_mb,
                   compression=compression,
                   deduplication=enable_deduplication)
    
    async def initialize(self):
        """初始化缓存"""
        await self._load_index()
        await self._start_cleanup_timer()
        logger.info("BLAKE3磁盘缓存启动完成",
                   entries=len(self.index),
                   total_size_mb=round(self.total_size / 1024 / 1024, 2),
                   unique_content_blocks=len(self.cid_to_entries))
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        self.stats["total_operations"] += 1
        
        entry = self.index.get(key)
        if not entry:
            self.stats["cache_misses"] += 1
            return None
        
        # 检查过期
        if entry.expires_at and time.time() > entry.expires_at:
            await self._remove_entry(key)
            self.stats["cache_misses"] += 1
            return None
        
        try:
            # 读取文件
            file_path = self._get_cid_file_path(entry.cid)
            
            if not file_path.exists():
                logger.warning("缓存文件不存在", key=key, cid=str(entry.cid))
                await self._remove_entry(key)
                self.stats["cache_misses"] += 1
                return None
            
            # 读取和解压数据
            data = await self._read_compressed_file(file_path, entry.compression_type)
            
            # 内容验证
            if self.enable_content_verification:
                if not self.content_addressing.verify_content(data, entry.cid):
                    logger.error("内容验证失败，可能存在数据损坏", key=key, cid=str(entry.cid))
                    await self._remove_entry(key)
                    self.stats["verification_failures"] += 1
                    self.stats["cache_misses"] += 1
                    return None
            
            # 更新访问统计
            entry.access_count += 1
            entry.last_access = time.time()
            
            # 反序列化
            result = json.loads(data)
            self.stats["cache_hits"] += 1
            
            logger.debug("BLAKE3缓存命中", key=key, cid=str(entry.cid)[:16])
            return result
            
        except Exception as e:
            logger.error("BLAKE3缓存读取失败", key=key, error=str(e))
            await self._remove_entry(key)
            self.stats["cache_misses"] += 1
            return None
    
    async def put(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """存储缓存数据"""
        self.stats["total_operations"] += 1
        
        try:
            # 序列化数据
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            
            # 计算内容ID
            cid = compute_cid(json_data, HashAlgorithm.BLAKE3)
            cid_str = str(cid)
            
            # 检查是否已存在相同内容（去重）
            existing_entries = self.cid_to_entries.get(cid_str, [])
            if existing_entries and self.enable_deduplication:
                # 内容去重：直接创建新的缓存条目，指向同一个文件
                current_time = time.time()
                expires_at = current_time + (ttl or self.default_ttl) if ttl != 0 else None
                
                new_entry = Blake3CacheEntry(
                    cid=cid,
                    key=key,
                    created_at=current_time,
                    expires_at=expires_at,
                    access_count=1,
                    last_access=current_time,
                    compression_type=existing_entries[0].compression_type
                )
                
                # 如果key已存在，先移除旧的
                if key in self.index:
                    await self._remove_entry(key)
                
                # 添加新条目
                self.index[key] = new_entry
                self.cid_to_entries[cid_str].append(new_entry)
                
                self.stats["deduplication_saves"] += 1
                
                # 异步保存索引
                asyncio.create_task(self._save_index())
                
                logger.debug("BLAKE3缓存去重存储", 
                            key=key, 
                            cid=cid_str[:16],
                            existing_refs=len(existing_entries))
                return True
            
            # 压缩数据
            compressed_data, compression_type = await self._compress_data(json_data.encode('utf-8'))
            
            # 检查空间限制
            await self._ensure_space(len(compressed_data))
            
            # 写入文件
            file_path = self._get_cid_file_path(cid)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(compressed_data)
            
            # 更新索引
            current_time = time.time()
            expires_at = current_time + (ttl or self.default_ttl) if ttl != 0 else None
            
            new_entry = Blake3CacheEntry(
                cid=cid,
                key=key,
                created_at=current_time,
                expires_at=expires_at,
                access_count=1,
                last_access=current_time,
                compression_type=compression_type
            )
            
            # 如果key已存在，先移除旧的
            if key in self.index:
                await self._remove_entry(key)
            
            # 添加新条目
            self.index[key] = new_entry
            if cid_str not in self.cid_to_entries:
                self.cid_to_entries[cid_str] = []
            self.cid_to_entries[cid_str].append(new_entry)
            
            self.total_size += len(compressed_data)
            
            # 更新压缩统计
            original_size = len(json_data.encode('utf-8'))
            compression_ratio = len(compressed_data) / original_size
            self.stats["compression_ratio"] = (
                self.stats["compression_ratio"] * (self.stats["total_operations"] - 1) + compression_ratio
            ) / self.stats["total_operations"]
            
            # 异步保存索引
            asyncio.create_task(self._save_index())
            
            logger.debug("BLAKE3缓存存储成功", 
                        key=key, 
                        cid=cid_str[:16],
                        size_kb=round(len(compressed_data) / 1024, 2),
                        compression=compression_type,
                        compression_ratio=round(compression_ratio, 3))
            return True
            
        except Exception as e:
            logger.error("BLAKE3缓存存储失败", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        return await self._remove_entry(key)
    
    async def clear(self) -> int:
        """清空所有缓存"""
        cleared_count = len(self.index)
        
        # 删除所有文件
        for cid_entries in self.cid_to_entries.values():
            if cid_entries:
                file_path = self._get_cid_file_path(cid_entries[0].cid)
                if file_path.exists():
                    file_path.unlink()
        
        # 清理索引
        self.index.clear()
        self.cid_to_entries.clear()
        self.total_size = 0
        
        await self._save_index()
        
        logger.info("BLAKE3磁盘缓存已清空", cleared_count=cleared_count)
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
            logger.info("清理过期BLAKE3缓存", removed_count=len(expired_keys))
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        current_time = time.time()
        expired_count = 0
        
        for entry in self.index.values():
            if entry.expires_at and current_time > entry.expires_at:
                expired_count += 1
        
        hit_rate = 0.0
        if self.stats["total_operations"] > 0:
            hit_rate = self.stats["cache_hits"] / self.stats["total_operations"]
        
        return {
            "total_entries": len(self.index),
            "unique_content_blocks": len(self.cid_to_entries),
            "total_size_mb": round(self.total_size / 1024 / 1024, 2),
            "max_size_mb": round(self.max_size_bytes / 1024 / 1024, 2),
            "utilization_percent": round((self.total_size / self.max_size_bytes) * 100, 1),
            "expired_entries": expired_count,
            "cache_hit_rate": round(hit_rate * 100, 1),
            "compression_algorithm": self.compression,
            "average_compression_ratio": round(self.stats["compression_ratio"], 3),
            "deduplication_enabled": self.enable_deduplication,
            "content_verification_enabled": self.enable_content_verification,
            **{k: v for k, v in self.stats.items() if k != "compression_ratio"},
            "content_addressing_stats": self.content_addressing.get_performance_stats(),
        }
    
    async def _compress_data(self, data: bytes) -> tuple[bytes, str]:
        """压缩数据"""
        if self.compression == "zstd":
            try:
                import zstandard as zstd
                compressor = zstd.ZstdCompressor(level=3)
                compressed = compressor.compress(data)
                return compressed, "zstd"
            except ImportError:
                logger.warning("zstd未安装，回退到gzip")
        
        if self.compression in ("gzip", "zstd"):  # zstd回退情况
            import gzip
            compressed = gzip.compress(data)
            return compressed, "gzip"
        
        # 无压缩
        return data, None
    
    async def _read_compressed_file(self, file_path: Path, compression_type: Optional[str]) -> str:
        """读取并解压文件"""
        async with aiofiles.open(file_path, 'rb') as f:
            compressed_data = await f.read()
        
        if compression_type == "zstd":
            import zstandard as zstd
            decompressor = zstd.ZstdDecompressor()
            data = decompressor.decompress(compressed_data).decode('utf-8')
        elif compression_type == "gzip":
            import gzip
            data = gzip.decompress(compressed_data).decode('utf-8')
        else:
            data = compressed_data.decode('utf-8')
        
        return data
    
    def _get_cid_file_path(self, cid: ContentId) -> Path:
        """获取CID对应的文件路径"""
        # 使用前两位作为子目录，避免单个目录文件过多
        prefix = cid.hash_value[:2]
        subdir = self.cache_dir / prefix
        subdir.mkdir(exist_ok=True)
        return subdir / f"{cid.hash_value}.cache"
    
    async def _remove_entry(self, key: str) -> bool:
        """移除缓存条目"""
        if key not in self.index:
            return False
        
        try:
            entry = self.index[key]
            cid_str = str(entry.cid)
            
            # 从索引中移除
            del self.index[key]
            
            # 从CID映射中移除
            cid_entries = self.cid_to_entries.get(cid_str, [])
            cid_entries = [e for e in cid_entries if e.key != key]
            
            if not cid_entries:
                # 没有其他引用，删除文件
                file_path = self._get_cid_file_path(entry.cid)
                if file_path.exists():
                    file_path.unlink()
                    self.total_size -= file_path.stat().st_size if file_path.exists() else 0
                
                # 从映射中移除
                del self.cid_to_entries[cid_str]
            else:
                # 更新映射
                self.cid_to_entries[cid_str] = cid_entries
            
            return True
            
        except Exception as e:
            logger.error("移除BLAKE3缓存条目失败", key=key, error=str(e))
            return False
    
    async def _ensure_space(self, required_bytes: int):
        """确保有足够的空间"""
        while self.total_size + required_bytes > self.max_size_bytes:
            if not self.index:
                break
            
            # 按访问次数和最后访问时间排序，清除最少使用的
            lru_key = min(
                self.index.keys(),
                key=lambda k: (
                    self.index[k].access_count,
                    self.index[k].last_access
                )
            )
            
            await self._remove_entry(lru_key)
            logger.debug("BLAKE3缓存空间清理", removed_key=lru_key)
    
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
                entry = Blake3CacheEntry.from_dict(entry_data)
                
                # 验证文件是否存在
                file_path = self._get_cid_file_path(entry.cid)
                if file_path.exists():
                    self.index[key] = entry
                    
                    cid_str = str(entry.cid)
                    if cid_str not in self.cid_to_entries:
                        self.cid_to_entries[cid_str] = []
                    self.cid_to_entries[cid_str].append(entry)
                    
                    self.total_size += file_path.stat().st_size
                else:
                    logger.warning("BLAKE3缓存文件不存在，跳过索引条目", 
                                  key=key, cid=str(entry.cid)[:16])
            
            logger.info("BLAKE3缓存索引加载完成", 
                       entries=len(self.index),
                       content_blocks=len(self.cid_to_entries))
            
        except Exception as e:
            logger.error("加载BLAKE3缓存索引失败", error=str(e))
            self.index.clear()
            self.cid_to_entries.clear()
            self.total_size = 0
    
    async def _save_index(self):
        """保存缓存索引"""
        try:
            index_data = {
                "version": "2.0",
                "algorithm": "blake3",
                "saved_at": time.time(),
                "entries": {}
            }
            
            for key, entry in self.index.items():
                index_data["entries"][key] = entry.to_dict()
            
            # 写入索引文件
            async with aiofiles.open(self.index_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index_data, indent=2))
                
        except Exception as e:
            logger.error("保存BLAKE3缓存索引失败", error=str(e))
    
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
                    logger.error("BLAKE3缓存定期清理失败", error=str(e))
        
        self.cleanup_timer = asyncio.create_task(cleanup_task())
        logger.info("BLAKE3缓存定期清理启动", interval_seconds=self.cleanup_interval)
    
    async def shutdown(self):
        """关闭缓存服务"""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
            try:
                await self.cleanup_timer
            except asyncio.CancelledError:
                pass
        
        await self._save_index()
        logger.info("BLAKE3磁盘缓存服务已关闭")


# ==================== 全局实例 ====================

_global_blake3_cache: Optional[Blake3DiskCache] = None


def get_blake3_cache() -> Blake3DiskCache:
    """获取全局BLAKE3缓存实例"""
    global _global_blake3_cache
    if _global_blake3_cache is None:
        _global_blake3_cache = Blake3DiskCache()
    return _global_blake3_cache


async def initialize_blake3_cache(config: Optional[Dict[str, Any]] = None):
    """初始化全局BLAKE3缓存"""
    global _global_blake3_cache
    
    if config:
        _global_blake3_cache = Blake3DiskCache(**config)
    else:
        _global_blake3_cache = Blake3DiskCache()
    
    await _global_blake3_cache.initialize()


async def shutdown_blake3_cache():
    """关闭全局BLAKE3缓存"""
    global _global_blake3_cache
    if _global_blake3_cache:
        await _global_blake3_cache.shutdown()
        _global_blake3_cache = None