"""
BLAKE3内容寻址系统
提供高性能的内容寻址和缓存支持
"""

import blake3
import hashlib
import asyncio
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import struct
import json
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class HashAlgorithm(Enum):
    """哈希算法类型"""
    BLAKE3 = "blake3"
    SHA256 = "sha256"
    MD5 = "md5"
    
    @property
    def digest_size(self) -> int:
        """获取摘要长度"""
        return {
            HashAlgorithm.BLAKE3: 32,
            HashAlgorithm.SHA256: 32,
            HashAlgorithm.MD5: 16,
        }[self]
    
    @property
    def hex_length(self) -> int:
        """获取十六进制字符串长度"""
        return self.digest_size * 2


@dataclass
class ContentId:
    """内容标识符"""
    hash_value: str  # 十六进制哈希值
    algorithm: HashAlgorithm
    size: int  # 原始内容大小
    
    def __str__(self) -> str:
        return f"{self.algorithm.value}:{self.hash_value}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ContentId):
            return False
        return (self.hash_value == other.hash_value and 
                self.algorithm == other.algorithm)
    
    def __hash__(self) -> int:
        return hash((self.hash_value, self.algorithm))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hash": self.hash_value,
            "algorithm": self.algorithm.value,
            "size": self.size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentId':
        """从字典创建"""
        return cls(
            hash_value=data["hash"],
            algorithm=HashAlgorithm(data["algorithm"]),
            size=data["size"]
        )


@dataclass
class ContentAddress:
    """内容地址信息"""
    cid: ContentId
    created_at: float
    access_count: int
    last_access: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "cid": self.cid.to_dict(),
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_access": self.last_access,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentAddress':
        """从字典创建"""
        return cls(
            cid=ContentId.from_dict(data["cid"]),
            created_at=data["created_at"],
            access_count=data["access_count"],
            last_access=data["last_access"],
            metadata=data["metadata"]
        )


class ContentHasher:
    """内容哈希计算器"""
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.BLAKE3):
        self.algorithm = algorithm
        
    def compute_bytes(self, data: bytes) -> ContentId:
        """计算字节数据的哈希"""
        if self.algorithm == HashAlgorithm.BLAKE3:
            hasher = blake3.blake3()
            hasher.update(data)
            hash_value = hasher.hexdigest()
        elif self.algorithm == HashAlgorithm.SHA256:
            hasher = hashlib.sha256()
            hasher.update(data)
            hash_value = hasher.hexdigest()
        elif self.algorithm == HashAlgorithm.MD5:
            hasher = hashlib.md5()
            hasher.update(data)
            hash_value = hasher.hexdigest()
        else:
            raise ValueError(f"不支持的哈希算法: {self.algorithm}")
        
        return ContentId(
            hash_value=hash_value,
            algorithm=self.algorithm,
            size=len(data)
        )
    
    def compute_string(self, text: str, encoding: str = 'utf-8') -> ContentId:
        """计算字符串的哈希"""
        return self.compute_bytes(text.encode(encoding))
    
    def compute_json(self, data: Any) -> ContentId:
        """计算JSON数据的哈希"""
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        return self.compute_string(json_str)
    
    async def compute_file(self, file_path: Path, chunk_size: int = 65536) -> ContentId:
        """计算文件的哈希"""
        if self.algorithm == HashAlgorithm.BLAKE3:
            hasher = blake3.blake3()
        elif self.algorithm == HashAlgorithm.SHA256:
            hasher = hashlib.sha256()
        elif self.algorithm == HashAlgorithm.MD5:
            hasher = hashlib.md5()
        else:
            raise ValueError(f"不支持的哈希算法: {self.algorithm}")
        
        file_size = 0
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    file_size += len(chunk)
                    
                    # 异步让步，避免阻塞
                    if file_size % (chunk_size * 10) == 0:
                        await asyncio.sleep(0)
        
        except Exception as e:
            logger.error("文件哈希计算失败", file_path=str(file_path), error=str(e))
            raise
        
        return ContentId(
            hash_value=hasher.hexdigest(),
            algorithm=self.algorithm,
            size=file_size
        )


class ContentAddressingSystem:
    """内容寻址系统"""
    
    def __init__(
        self,
        algorithm: HashAlgorithm = HashAlgorithm.BLAKE3,
        enable_caching: bool = True,
        max_cache_entries: int = 10000,
        performance_monitoring: bool = True
    ):
        self.hasher = ContentHasher(algorithm)
        self.enable_caching = enable_caching
        self.max_cache_entries = max_cache_entries
        self.performance_monitoring = performance_monitoring
        
        # 内存缓存
        self.address_cache: Dict[str, ContentAddress] = {}
        self.cid_to_content: Dict[ContentId, Any] = {}
        
        # 性能统计
        self.stats = {
            "hash_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_bytes_processed": 0,
            "average_hash_time_ms": 0.0,
            "algorithm": algorithm.value
        }
        
        logger.info("内容寻址系统初始化", 
                   algorithm=algorithm.value,
                   caching=enable_caching,
                   max_cache_entries=max_cache_entries)
    
    def compute_cid(self, content: Union[str, bytes, Any]) -> ContentId:
        """计算内容的CID"""
        start_time = time.time()
        
        try:
            if isinstance(content, bytes):
                cid = self.hasher.compute_bytes(content)
            elif isinstance(content, str):
                cid = self.hasher.compute_string(content)
            else:
                cid = self.hasher.compute_json(content)
            
            # 更新统计
            if self.performance_monitoring:
                self.stats["hash_operations"] += 1
                self.stats["total_bytes_processed"] += cid.size
                
                hash_time = (time.time() - start_time) * 1000
                self.stats["average_hash_time_ms"] = (
                    self.stats["average_hash_time_ms"] * (self.stats["hash_operations"] - 1) + hash_time
                ) / self.stats["hash_operations"]
            
            logger.debug("内容CID计算完成",
                        algorithm=cid.algorithm.value,
                        hash=cid.hash_value[:16],
                        size=cid.size,
                        time_ms=round((time.time() - start_time) * 1000, 2))
            
            return cid
            
        except Exception as e:
            logger.error("CID计算失败", error=str(e))
            raise
    
    async def compute_file_cid(self, file_path: Path) -> ContentId:
        """计算文件的CID"""
        start_time = time.time()
        
        try:
            cid = await self.hasher.compute_file(file_path)
            
            # 更新统计
            if self.performance_monitoring:
                self.stats["hash_operations"] += 1
                self.stats["total_bytes_processed"] += cid.size
                
                hash_time = (time.time() - start_time) * 1000
                self.stats["average_hash_time_ms"] = (
                    self.stats["average_hash_time_ms"] * (self.stats["hash_operations"] - 1) + hash_time
                ) / self.stats["hash_operations"]
            
            logger.debug("文件CID计算完成",
                        file_path=str(file_path),
                        algorithm=cid.algorithm.value,
                        hash=cid.hash_value[:16],
                        size=cid.size,
                        time_ms=round((time.time() - start_time) * 1000, 2))
            
            return cid
            
        except Exception as e:
            logger.error("文件CID计算失败", file_path=str(file_path), error=str(e))
            raise
    
    def store_content(self, content: Any, metadata: Optional[Dict[str, Any]] = None) -> ContentId:
        """存储内容并返回CID"""
        cid = self.compute_cid(content)
        
        if self.enable_caching:
            # 检查缓存容量
            if len(self.address_cache) >= self.max_cache_entries:
                self._evict_lru_entry()
            
            # 创建地址信息
            current_time = time.time()
            address = ContentAddress(
                cid=cid,
                created_at=current_time,
                access_count=1,
                last_access=current_time,
                metadata=metadata or {}
            )
            
            self.address_cache[str(cid)] = address
            self.cid_to_content[cid] = content
            
            logger.debug("内容已存储", cid=str(cid), metadata_keys=list((metadata or {}).keys()))
        
        return cid
    
    def retrieve_content(self, cid: ContentId) -> Optional[Any]:
        """根据CID检索内容"""
        cid_str = str(cid)
        
        if not self.enable_caching:
            return None
        
        if cid_str in self.address_cache:
            # 缓存命中
            address = self.address_cache[cid_str]
            address.access_count += 1
            address.last_access = time.time()
            
            content = self.cid_to_content.get(cid)
            
            if self.performance_monitoring:
                self.stats["cache_hits"] += 1
            
            logger.debug("内容缓存命中", cid=cid_str[:16])
            return content
        else:
            # 缓存未命中
            if self.performance_monitoring:
                self.stats["cache_misses"] += 1
            
            logger.debug("内容缓存未命中", cid=cid_str[:16])
            return None
    
    def batch_compute_cids(self, contents: List[Any]) -> List[ContentId]:
        """批量计算CID"""
        cids = []
        
        for content in contents:
            cid = self.compute_cid(content)
            cids.append(cid)
        
        logger.debug("批量CID计算完成", count=len(cids))
        return cids
    
    def compare_content(self, cid1: ContentId, cid2: ContentId) -> bool:
        """比较两个内容是否相同"""
        return cid1 == cid2
    
    def verify_content(self, content: Any, expected_cid: ContentId) -> bool:
        """验证内容的完整性"""
        actual_cid = self.compute_cid(content)
        is_valid = actual_cid == expected_cid
        
        if not is_valid:
            logger.warning("内容验证失败",
                          expected_cid=str(expected_cid),
                          actual_cid=str(actual_cid))
        
        return is_valid
    
    def get_content_info(self, cid: ContentId) -> Optional[ContentAddress]:
        """获取内容地址信息"""
        cid_str = str(cid)
        return self.address_cache.get(cid_str)
    
    def list_cached_content(self) -> List[ContentAddress]:
        """列出所有缓存的内容"""
        return list(self.address_cache.values())
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        cache_hit_rate = 0.0
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_requests > 0:
            cache_hit_rate = self.stats["cache_hits"] / total_requests
        
        return {
            **self.stats,
            "cached_entries": len(self.address_cache),
            "cache_hit_rate": cache_hit_rate,
            "bytes_per_hash_operation": (
                self.stats["total_bytes_processed"] / max(self.stats["hash_operations"], 1)
            ),
        }
    
    def clear_cache(self) -> int:
        """清空缓存"""
        cleared_count = len(self.address_cache)
        self.address_cache.clear()
        self.cid_to_content.clear()
        
        logger.info("内容寻址缓存已清空", cleared_count=cleared_count)
        return cleared_count
    
    def _evict_lru_entry(self):
        """清除最少使用的条目"""
        if not self.address_cache:
            return
        
        # 找到最少使用的条目
        lru_key = min(
            self.address_cache.keys(),
            key=lambda k: (
                self.address_cache[k].access_count,
                self.address_cache[k].last_access
            )
        )
        
        # 移除条目
        address = self.address_cache.pop(lru_key)
        self.cid_to_content.pop(address.cid, None)
        
        logger.debug("LRU条目已清除", cid=lru_key[:16])


# ==================== 全局内容寻址系统 ====================

_global_content_addressing: Optional[ContentAddressingSystem] = None


def get_content_addressing() -> ContentAddressingSystem:
    """获取全局内容寻址系统"""
    global _global_content_addressing
    if _global_content_addressing is None:
        _global_content_addressing = ContentAddressingSystem()
    return _global_content_addressing


def initialize_content_addressing(
    algorithm: HashAlgorithm = HashAlgorithm.BLAKE3,
    **kwargs
):
    """初始化全局内容寻址系统"""
    global _global_content_addressing
    _global_content_addressing = ContentAddressingSystem(algorithm, **kwargs)


# ==================== 便捷函数 ====================

def compute_cid(content: Any, algorithm: HashAlgorithm = HashAlgorithm.BLAKE3) -> ContentId:
    """便捷函数：计算内容的CID"""
    hasher = ContentHasher(algorithm)
    
    if isinstance(content, bytes):
        return hasher.compute_bytes(content)
    elif isinstance(content, str):
        return hasher.compute_string(content)
    else:
        return hasher.compute_json(content)


async def compute_file_cid(file_path: Path, algorithm: HashAlgorithm = HashAlgorithm.BLAKE3) -> ContentId:
    """便捷函数：计算文件的CID"""
    hasher = ContentHasher(algorithm)
    return await hasher.compute_file(file_path)


def verify_content_integrity(content: Any, expected_cid: ContentId) -> bool:
    """便捷函数：验证内容完整性"""
    cas = get_content_addressing()
    return cas.verify_content(content, expected_cid)


def benchmark_hash_algorithms(content: bytes, iterations: int = 1000) -> Dict[str, float]:
    """基准测试：比较不同哈希算法的性能"""
    algorithms = [HashAlgorithm.BLAKE3, HashAlgorithm.SHA256, HashAlgorithm.MD5]
    results = {}
    
    for algorithm in algorithms:
        hasher = ContentHasher(algorithm)
        
        start_time = time.time()
        for _ in range(iterations):
            hasher.compute_bytes(content)
        end_time = time.time()
        
        avg_time_ms = ((end_time - start_time) / iterations) * 1000
        results[algorithm.value] = avg_time_ms
    
    logger.info("哈希算法性能基准测试完成", 
               content_size=len(content),
               iterations=iterations,
               results=results)
    
    return results