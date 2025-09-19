"""
版本管理性能优化器 - TH-Suite MC L10n
实现版本数据的压缩、缓存、增量存储等性能优化策略
"""

import asyncio
import json
import logging
import gzip
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import pickle

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.services.multi_layer_cache_service import get_cache_service

logger = logging.getLogger(__name__)


class CompressionAlgorithm(Enum):
    """压缩算法枚举"""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"
    LZMA = "lzma"


class CacheStrategy(Enum):
    """缓存策略枚举"""
    NO_CACHE = "no_cache"
    MEMORY_ONLY = "memory_only"
    DISK_ONLY = "disk_only"
    HYBRID = "hybrid"
    DISTRIBUTED = "distributed"


class StorageMode(Enum):
    """存储模式枚举"""
    FULL_SNAPSHOT = "full_snapshot"
    INCREMENTAL_DELTA = "incremental_delta"
    DEDUPLICATED = "deduplicated"
    COMPRESSED_CHUNKS = "compressed_chunks"


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    start_time: datetime
    end_time: datetime
    input_size: int
    output_size: int
    compression_ratio: float
    cache_hit: bool
    memory_usage: int


class VersionPerformanceOptimizer:
    """版本管理性能优化器"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self.cache_service = get_cache_service()
        
        self.config = {
            # 压缩配置
            "default_compression": CompressionAlgorithm.GZIP,
            "compression_threshold": 1024,  # 1KB以上才压缩
            "compression_level": 6,         # 压缩级别
            
            # 缓存配置
            "cache_strategy": CacheStrategy.HYBRID,
            "cache_ttl": 3600,             # 1小时
            "max_cache_size": 100 * 1024 * 1024,  # 100MB
            "cache_cleanup_interval": 300,  # 5分钟
            
            # 存储配置
            "storage_mode": StorageMode.INCREMENTAL_DELTA,
            "chunk_size": 64 * 1024,       # 64KB分块
            "dedup_threshold": 0.8,        # 去重阈值
            
            # 性能配置
            "parallel_operations": True,
            "max_workers": 4,
            "memory_limit": 512 * 1024 * 1024,  # 512MB
            "gc_threshold": 0.8            # 垃圾回收阈值
        }
        
        self.metrics = []
        self.compression_stats = {
            "total_compressed": 0,
            "total_original": 0,
            "compression_time": 0,
            "decompression_time": 0
        }
    
    # ============================================================
    # 1. 数据压缩优化
    # ============================================================
    
    async def compress_version_data(self, data: Union[Dict, str, bytes], 
                                  algorithm: CompressionAlgorithm = None) -> Dict[str, Any]:
        """
        压缩版本数据
        
        Args:
            data: 要压缩的数据
            algorithm: 压缩算法
        
        Returns:
            压缩结果和元数据
        """
        start_time = datetime.now()
        
        try:
            # 确定压缩算法
            if algorithm is None:
                algorithm = CompressionAlgorithm(self.config["default_compression"])
            
            # 数据预处理
            if isinstance(data, dict):
                raw_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            elif isinstance(data, str):
                raw_data = data.encode('utf-8')
            elif isinstance(data, bytes):
                raw_data = data
            else:
                raise ValueError(f"不支持的数据类型: {type(data)}")
            
            original_size = len(raw_data)
            
            # 检查压缩阈值
            if original_size < self.config["compression_threshold"]:
                return {
                    "success": True,
                    "compressed": False,
                    "data": raw_data,
                    "original_size": original_size,
                    "compressed_size": original_size,
                    "compression_ratio": 1.0,
                    "algorithm": "none"
                }
            
            # 执行压缩
            if algorithm == CompressionAlgorithm.GZIP:
                compressed_data = await self._compress_gzip(raw_data)
            elif algorithm == CompressionAlgorithm.ZSTD:
                compressed_data = await self._compress_zstd(raw_data)
            elif algorithm == CompressionAlgorithm.LZMA:
                compressed_data = await self._compress_lzma(raw_data)
            else:
                compressed_data = raw_data
                algorithm = CompressionAlgorithm.NONE
            
            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            
            # 更新统计
            self.compression_stats["total_original"] += original_size
            self.compression_stats["total_compressed"] += compressed_size
            self.compression_stats["compression_time"] += (datetime.now() - start_time).total_seconds()
            
            # 记录性能指标
            await self._record_performance_metric(PerformanceMetrics(
                operation="compress",
                start_time=start_time,
                end_time=datetime.now(),
                input_size=original_size,
                output_size=compressed_size,
                compression_ratio=compression_ratio,
                cache_hit=False,
                memory_usage=original_size + compressed_size
            ))
            
            return {
                "success": True,
                "compressed": True,
                "data": compressed_data,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "algorithm": algorithm.value
            }
            
        except Exception as e:
            logger.error(f"压缩版本数据失败: {e}")
            return {
                "success": False,
                "message": f"压缩失败: {str(e)}"
            }
    
    async def decompress_version_data(self, compressed_data: bytes, 
                                    algorithm: str) -> Dict[str, Any]:
        """
        解压缩版本数据
        
        Args:
            compressed_data: 压缩数据
            algorithm: 压缩算法
        
        Returns:
            解压缩结果
        """
        start_time = datetime.now()
        
        try:
            if algorithm == "none":
                return {
                    "success": True,
                    "data": compressed_data
                }
            
            # 执行解压缩
            if algorithm == "gzip":
                decompressed_data = await self._decompress_gzip(compressed_data)
            elif algorithm == "zstd":
                decompressed_data = await self._decompress_zstd(compressed_data)
            elif algorithm == "lzma":
                decompressed_data = await self._decompress_lzma(compressed_data)
            else:
                raise ValueError(f"不支持的压缩算法: {algorithm}")
            
            # 更新统计
            self.compression_stats["decompression_time"] += (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "data": decompressed_data
            }
            
        except Exception as e:
            logger.error(f"解压缩版本数据失败: {e}")
            return {
                "success": False,
                "message": f"解压缩失败: {str(e)}"
            }
    
    async def _compress_gzip(self, data: bytes) -> bytes:
        """GZIP压缩"""
        return gzip.compress(data, compresslevel=self.config["compression_level"])
    
    async def _decompress_gzip(self, data: bytes) -> bytes:
        """GZIP解压缩"""
        return gzip.decompress(data)
    
    async def _compress_zstd(self, data: bytes) -> bytes:
        """ZSTD压缩 (模拟实现)"""
        # 实际应使用 zstandard 库
        return gzip.compress(data, compresslevel=self.config["compression_level"])
    
    async def _decompress_zstd(self, data: bytes) -> bytes:
        """ZSTD解压缩 (模拟实现)"""
        # 实际应使用 zstandard 库
        return gzip.decompress(data)
    
    async def _compress_lzma(self, data: bytes) -> bytes:
        """LZMA压缩"""
        import lzma
        return lzma.compress(data, preset=self.config["compression_level"])
    
    async def _decompress_lzma(self, data: bytes) -> bytes:
        """LZMA解压缩"""
        import lzma
        return lzma.decompress(data)
    
    # ============================================================
    # 2. 缓存优化
    # ============================================================
    
    async def get_cached_version_data(self, cache_key: str, 
                                    fallback_loader: callable = None) -> Dict[str, Any]:
        """
        获取缓存的版本数据
        
        Args:
            cache_key: 缓存键
            fallback_loader: 回退加载函数
        
        Returns:
            缓存数据或加载结果
        """
        try:
            cache_strategy = CacheStrategy(self.config["cache_strategy"])
            
            # 尝试从缓存获取
            cached_data = None
            cache_hit = False
            
            if cache_strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.HYBRID]:
                cached_data = await self._get_memory_cache(cache_key)
                if cached_data:
                    cache_hit = True
            
            if not cached_data and cache_strategy in [CacheStrategy.DISK_ONLY, CacheStrategy.HYBRID]:
                cached_data = await self._get_disk_cache(cache_key)
                if cached_data:
                    cache_hit = True
                    # 写回内存缓存
                    if cache_strategy == CacheStrategy.HYBRID:
                        await self._set_memory_cache(cache_key, cached_data)
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "cache_hit": True,
                    "source": "cache"
                }
            
            # 缓存未命中，使用回退加载器
            if fallback_loader:
                loaded_data = await fallback_loader()
                if loaded_data.get("success"):
                    # 写入缓存
                    await self.set_cached_version_data(cache_key, loaded_data["data"])
                    loaded_data["cache_hit"] = False
                    loaded_data["source"] = "loader"
                    return loaded_data
            
            return {
                "success": False,
                "message": "缓存未命中且无回退加载器",
                "cache_hit": False
            }
            
        except Exception as e:
            logger.error(f"获取缓存版本数据失败: {e}")
            return {
                "success": False,
                "message": f"获取缓存失败: {str(e)}"
            }
    
    async def set_cached_version_data(self, cache_key: str, data: Any, 
                                    ttl: int = None) -> Dict[str, Any]:
        """
        设置缓存版本数据
        
        Args:
            cache_key: 缓存键
            data: 缓存数据
            ttl: 生存时间
        
        Returns:
            设置结果
        """
        try:
            if ttl is None:
                ttl = self.config["cache_ttl"]
            
            cache_strategy = CacheStrategy(self.config["cache_strategy"])
            
            # 序列化数据
            serialized_data = pickle.dumps(data)
            
            # 检查大小限制
            if len(serialized_data) > self.config["max_cache_size"]:
                return {
                    "success": False,
                    "message": "数据大小超过缓存限制"
                }
            
            # 设置内存缓存
            if cache_strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.HYBRID]:
                await self._set_memory_cache(cache_key, data, ttl)
            
            # 设置磁盘缓存
            if cache_strategy in [CacheStrategy.DISK_ONLY, CacheStrategy.HYBRID]:
                await self._set_disk_cache(cache_key, data, ttl)
            
            return {
                "success": True,
                "cache_key": cache_key,
                "data_size": len(serialized_data),
                "ttl": ttl
            }
            
        except Exception as e:
            logger.error(f"设置缓存版本数据失败: {e}")
            return {
                "success": False,
                "message": f"设置缓存失败: {str(e)}"
            }
    
    async def _get_memory_cache(self, cache_key: str) -> Any:
        """从内存缓存获取数据"""
        try:
            result = await self.cache_service.get(f"version:{cache_key}")
            if result and result.get("success"):
                return result.get("data")
            return None
        except Exception as e:
            logger.error(f"内存缓存获取失败: {e}")
            return None
    
    async def _set_memory_cache(self, cache_key: str, data: Any, ttl: int = None) -> None:
        """设置内存缓存"""
        try:
            await self.cache_service.set(f"version:{cache_key}", data, ttl)
        except Exception as e:
            logger.error(f"内存缓存设置失败: {e}")
    
    async def _get_disk_cache(self, cache_key: str) -> Any:
        """从磁盘缓存获取数据"""
        try:
            cache_file = Path(f"/tmp/th_suite_cache/version_{cache_key}.pkl")
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    cached_item = pickle.load(f)
                
                # 检查过期时间
                if cached_item["expires_at"] > datetime.now():
                    return cached_item["data"]
                else:
                    cache_file.unlink()  # 删除过期文件
            
            return None
        except Exception as e:
            logger.error(f"磁盘缓存获取失败: {e}")
            return None
    
    async def _set_disk_cache(self, cache_key: str, data: Any, ttl: int = None) -> None:
        """设置磁盘缓存"""
        try:
            cache_dir = Path("/tmp/th_suite_cache")
            cache_dir.mkdir(exist_ok=True)
            
            cache_file = cache_dir / f"version_{cache_key}.pkl"
            expires_at = datetime.now() + timedelta(seconds=ttl or self.config["cache_ttl"])
            
            cached_item = {
                "data": data,
                "expires_at": expires_at,
                "created_at": datetime.now()
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cached_item, f)
                
        except Exception as e:
            logger.error(f"磁盘缓存设置失败: {e}")
    
    # ============================================================
    # 3. 增量存储优化
    # ============================================================
    
    async def store_version_incrementally(self, repository_uid: str, 
                                        current_data: Dict[str, Any],
                                        previous_commit_uid: str = None) -> Dict[str, Any]:
        """
        增量存储版本数据
        
        Args:
            repository_uid: 仓库UID
            current_data: 当前数据
            previous_commit_uid: 前一个提交UID
        
        Returns:
            存储结果
        """
        try:
            storage_mode = StorageMode(self.config["storage_mode"])
            
            if storage_mode == StorageMode.FULL_SNAPSHOT:
                return await self._store_full_snapshot(repository_uid, current_data)
            
            elif storage_mode == StorageMode.INCREMENTAL_DELTA:
                return await self._store_incremental_delta(
                    repository_uid, current_data, previous_commit_uid
                )
            
            elif storage_mode == StorageMode.DEDUPLICATED:
                return await self._store_deduplicated(repository_uid, current_data)
            
            elif storage_mode == StorageMode.COMPRESSED_CHUNKS:
                return await self._store_compressed_chunks(repository_uid, current_data)
            
            else:
                raise ValueError(f"不支持的存储模式: {storage_mode.value}")
                
        except Exception as e:
            logger.error(f"增量存储失败: {e}")
            return {
                "success": False,
                "message": f"增量存储失败: {str(e)}"
            }
    
    async def _store_full_snapshot(self, repository_uid: str, 
                                 data: Dict[str, Any]) -> Dict[str, Any]:
        """存储完整快照"""
        
        # 压缩数据
        compression_result = await self.compress_version_data(data)
        if not compression_result["success"]:
            return compression_result
        
        # 生成内容ID
        content_id = hashlib.blake3(compression_result["data"]).hexdigest()
        
        # 存储到CAS
        storage_result = await self._store_to_cas(content_id, compression_result)
        
        return {
            "success": True,
            "storage_mode": "full_snapshot",
            "content_id": content_id,
            "original_size": compression_result["original_size"],
            "stored_size": compression_result["compressed_size"],
            "compression_ratio": compression_result["compression_ratio"]
        }
    
    async def _store_incremental_delta(self, repository_uid: str, 
                                     current_data: Dict[str, Any],
                                     previous_commit_uid: str = None) -> Dict[str, Any]:
        """存储增量差异"""
        
        if not previous_commit_uid:
            # 没有前一个提交，存储完整快照
            return await self._store_full_snapshot(repository_uid, current_data)
        
        # 获取前一个提交的数据
        previous_data = await self._load_commit_data(previous_commit_uid)
        if not previous_data["success"]:
            # 无法获取前一个提交数据，存储完整快照
            return await self._store_full_snapshot(repository_uid, current_data)
        
        # 计算差异
        from infrastructure.services.version_diff_engine import VersionDiffEngine
        diff_engine = VersionDiffEngine()
        
        version_diff = diff_engine.calculate_diff(
            previous_data["data"], current_data
        )
        
        # 压缩差异数据
        diff_data = {
            "operations": [
                {
                    "op": op.op.value,
                    "path": op.path,
                    "value": op.value,
                    "old_value": op.old_value,
                    "from_path": op.from_path
                }
                for op in version_diff.operations
            ],
            "metadata": version_diff.metadata
        }
        
        compression_result = await self.compress_version_data(diff_data)
        if not compression_result["success"]:
            return compression_result
        
        # 生成差异ID
        diff_id = hashlib.blake3(compression_result["data"]).hexdigest()
        
        # 存储差异
        storage_result = await self._store_to_cas(diff_id, compression_result)
        
        return {
            "success": True,
            "storage_mode": "incremental_delta",
            "diff_id": diff_id,
            "operations_count": len(version_diff.operations),
            "original_size": compression_result["original_size"],
            "stored_size": compression_result["compressed_size"],
            "compression_ratio": compression_result["compression_ratio"],
            "base_commit_uid": previous_commit_uid
        }
    
    async def _store_to_cas(self, content_id: str, 
                          compression_result: Dict[str, Any]) -> Dict[str, Any]:
        """存储到内容寻址存储"""
        try:
            async with self.factory.get_db_connection() as conn:
                # 检查是否已存在
                cursor = await conn.execute("""
                    SELECT cid FROM ops_cas_objects WHERE cid = ?
                """, (content_id,))
                
                if await cursor.fetchone():
                    # 增加引用计数
                    await conn.execute("""
                        UPDATE ops_cas_objects SET ref_count = ref_count + 1 WHERE cid = ?
                    """, (content_id,))
                else:
                    # 新建对象
                    await conn.execute("""
                        INSERT INTO ops_cas_objects 
                        (cid, size, algo, ref_count, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        content_id,
                        compression_result["compressed_size"],
                        compression_result["algorithm"],
                        1,
                        datetime.now().isoformat()
                    ))
                
                await conn.commit()
            
            # TODO: 实际存储数据到文件系统
            
            return {
                "success": True,
                "content_id": content_id
            }
            
        except Exception as e:
            logger.error(f"存储到CAS失败: {e}")
            return {
                "success": False,
                "message": f"存储到CAS失败: {str(e)}"
            }
    
    # ============================================================
    # 4. 性能监控
    # ============================================================
    
    async def _record_performance_metric(self, metric: PerformanceMetrics) -> None:
        """记录性能指标"""
        try:
            self.metrics.append(metric)
            
            # 保持最近1000条记录
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
                
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        try:
            if not self.metrics:
                return {
                    "success": True,
                    "message": "暂无性能数据",
                    "stats": {}
                }
            
            # 计算统计信息
            total_operations = len(self.metrics)
            total_input_size = sum(m.input_size for m in self.metrics)
            total_output_size = sum(m.output_size for m in self.metrics)
            total_duration = sum((m.end_time - m.start_time).total_seconds() for m in self.metrics)
            cache_hits = sum(1 for m in self.metrics if m.cache_hit)
            
            avg_compression_ratio = sum(m.compression_ratio for m in self.metrics) / total_operations
            cache_hit_rate = cache_hits / total_operations if total_operations > 0 else 0
            
            return {
                "success": True,
                "stats": {
                    "total_operations": total_operations,
                    "total_input_size": total_input_size,
                    "total_output_size": total_output_size,
                    "total_duration": total_duration,
                    "avg_compression_ratio": avg_compression_ratio,
                    "cache_hit_rate": cache_hit_rate,
                    "compression_stats": self.compression_stats,
                    "operations_per_second": total_operations / total_duration if total_duration > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return {
                "success": False,
                "message": f"获取性能统计失败: {str(e)}"
            }


# 全局性能优化器实例
version_performance_optimizer: Optional[VersionPerformanceOptimizer] = None


def get_version_performance_optimizer() -> VersionPerformanceOptimizer:
    """获取全局版本性能优化器实例"""
    global version_performance_optimizer
    if version_performance_optimizer is None:
        version_performance_optimizer = VersionPerformanceOptimizer()
        logger.info("版本性能优化器已初始化")
    return version_performance_optimizer