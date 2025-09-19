"""
压缩服务核心模块

实现压缩引擎、策略管理、结果处理等核心功能
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Dict, List, Optional, Protocol, Union, 
    Any, AsyncIterator, BinaryIO
)
import aiofiles

from .config import CompressionConfig
from .errors import CompressionError, StreamingError


class CompressionLevel(Enum):
    """压缩级别"""
    FASTEST = 1
    FAST = 3
    BALANCED = 6
    HIGH = 9
    MAXIMUM = 12


class CompressionAlgorithm(Enum):
    """压缩算法"""
    ZSTD = "zstd"
    GZIP = "gzip"
    LZ4 = "lz4"
    BROTLI = "brotli"
    DEFLATE = "deflate"


@dataclass
class CompressionResult:
    """压缩结果"""
    algorithm: CompressionAlgorithm
    original_size: int
    compressed_size: int
    compression_time: float
    compression_ratio: float = field(init=False)
    space_saved_bytes: int = field(init=False)
    space_saved_percentage: float = field(init=False)
    throughput_mbps: float = field(init=False)
    
    def __post_init__(self):
        self.compression_ratio = (
            self.compressed_size / self.original_size 
            if self.original_size > 0 else 0.0
        )
        self.space_saved_bytes = self.original_size - self.compressed_size
        self.space_saved_percentage = (
            (self.space_saved_bytes / self.original_size) * 100 
            if self.original_size > 0 else 0.0
        )
        self.throughput_mbps = (
            (self.original_size / (1024 * 1024)) / self.compression_time 
            if self.compression_time > 0 else 0.0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'algorithm': self.algorithm.value,
            'original_size': self.original_size,
            'compressed_size': self.compressed_size,
            'compression_time': self.compression_time,
            'compression_ratio': self.compression_ratio,
            'space_saved_bytes': self.space_saved_bytes,
            'space_saved_percentage': self.space_saved_percentage,
            'throughput_mbps': self.throughput_mbps
        }


class CompressionStrategy(Protocol):
    """压缩策略协议"""
    
    @property
    def algorithm(self) -> CompressionAlgorithm:
        """获取算法类型"""
        ...
    
    async def compress(
        self, 
        data: bytes, 
        level: CompressionLevel = CompressionLevel.BALANCED,
        dictionary: Optional[bytes] = None
    ) -> bytes:
        """压缩数据"""
        ...
    
    async def decompress(
        self, 
        compressed_data: bytes,
        dictionary: Optional[bytes] = None
    ) -> bytes:
        """解压数据"""
        ...
    
    async def compress_stream(
        self, 
        input_stream: AsyncIterator[bytes],
        level: CompressionLevel = CompressionLevel.BALANCED,
        dictionary: Optional[bytes] = None
    ) -> AsyncIterator[bytes]:
        """流式压缩"""
        ...
    
    async def decompress_stream(
        self, 
        input_stream: AsyncIterator[bytes],
        dictionary: Optional[bytes] = None
    ) -> AsyncIterator[bytes]:
        """流式解压"""
        ...


class CompressionEngine:
    """压缩引擎"""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.strategies: Dict[CompressionAlgorithm, CompressionStrategy] = {}
        self.dictionaries: Dict[str, bytes] = {}
        
    def register_strategy(
        self, 
        algorithm: CompressionAlgorithm, 
        strategy: CompressionStrategy
    ) -> None:
        """注册压缩策略"""
        self.strategies[algorithm] = strategy
        self.logger.info(f"注册压缩算法: {algorithm.value}")
    
    def set_dictionary(self, name: str, dictionary: bytes) -> None:
        """设置压缩字典"""
        self.dictionaries[name] = dictionary
        self.logger.info(f"设置压缩字典: {name}, 大小: {len(dictionary)} 字节")
    
    def get_strategy(self, algorithm: CompressionAlgorithm) -> CompressionStrategy:
        """获取压缩策略"""
        if algorithm not in self.strategies:
            raise CompressionError(f"不支持的压缩算法: {algorithm.value}")
        return self.strategies[algorithm]
    
    async def compress_data(
        self,
        data: bytes,
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[CompressionLevel] = None,
        dictionary_name: Optional[str] = None
    ) -> CompressionResult:
        """压缩数据"""
        # 选择算法
        if algorithm is None:
            algorithm = self._select_algorithm(len(data))
        
        # 选择压缩级别
        if level is None:
            level = self._select_level(len(data))
        
        # 获取字典
        dictionary = None
        if dictionary_name and dictionary_name in self.dictionaries:
            dictionary = self.dictionaries[dictionary_name]
        
        strategy = self.get_strategy(algorithm)
        
        start_time = time.time()
        try:
            compressed_data = await strategy.compress(data, level, dictionary)
            compression_time = time.time() - start_time
            
            result = CompressionResult(
                algorithm=algorithm,
                original_size=len(data),
                compressed_size=len(compressed_data),
                compression_time=compression_time
            )
            
            self.logger.debug(
                f"压缩完成: {algorithm.value}, "
                f"原始大小: {result.original_size}, "
                f"压缩后: {result.compressed_size}, "
                f"压缩比: {result.compression_ratio:.3f}, "
                f"节省: {result.space_saved_percentage:.1f}%"
            )
            
            return result
            
        except Exception as e:
            compression_time = time.time() - start_time
            self.logger.error(f"压缩失败: {e}")
            raise CompressionError(f"压缩失败: {e}")
    
    async def decompress_data(
        self,
        compressed_data: bytes,
        algorithm: CompressionAlgorithm,
        dictionary_name: Optional[str] = None
    ) -> bytes:
        """解压数据"""
        # 获取字典
        dictionary = None
        if dictionary_name and dictionary_name in self.dictionaries:
            dictionary = self.dictionaries[dictionary_name]
        
        strategy = self.get_strategy(algorithm)
        
        try:
            data = await strategy.decompress(compressed_data, dictionary)
            self.logger.debug(
                f"解压完成: {algorithm.value}, "
                f"压缩大小: {len(compressed_data)}, "
                f"解压后: {len(data)}"
            )
            return data
            
        except Exception as e:
            self.logger.error(f"解压失败: {e}")
            raise CompressionError(f"解压失败: {e}")
    
    async def compress_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[CompressionLevel] = None,
        dictionary_name: Optional[str] = None,
        chunk_size: int = 1024 * 1024  # 1MB
    ) -> CompressionResult:
        """压缩文件"""
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise CompressionError(f"输入文件不存在: {input_path}")
        
        file_size = input_path.stat().st_size
        
        # 选择算法和级别
        if algorithm is None:
            algorithm = self._select_algorithm(file_size)
        if level is None:
            level = self._select_level(file_size)
        
        # 获取字典
        dictionary = None
        if dictionary_name and dictionary_name in self.dictionaries:
            dictionary = self.dictionaries[dictionary_name]
        
        strategy = self.get_strategy(algorithm)
        
        start_time = time.time()
        compressed_size = 0
        
        try:
            async with aiofiles.open(input_path, 'rb') as input_file:
                async with aiofiles.open(output_path, 'wb') as output_file:
                    
                    async def input_stream():
                        while chunk := await input_file.read(chunk_size):
                            yield chunk
                    
                    async for compressed_chunk in strategy.compress_stream(
                        input_stream(), level, dictionary
                    ):
                        await output_file.write(compressed_chunk)
                        compressed_size += len(compressed_chunk)
            
            compression_time = time.time() - start_time
            
            result = CompressionResult(
                algorithm=algorithm,
                original_size=file_size,
                compressed_size=compressed_size,
                compression_time=compression_time
            )
            
            self.logger.info(
                f"文件压缩完成: {input_path} -> {output_path}, "
                f"算法: {algorithm.value}, "
                f"压缩比: {result.compression_ratio:.3f}, "
                f"节省: {result.space_saved_percentage:.1f}%"
            )
            
            return result
            
        except Exception as e:
            # 清理输出文件
            if output_path.exists():
                output_path.unlink()
            
            self.logger.error(f"文件压缩失败: {e}")
            raise CompressionError(f"文件压缩失败: {e}")
    
    async def decompress_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        algorithm: CompressionAlgorithm,
        dictionary_name: Optional[str] = None,
        chunk_size: int = 1024 * 1024  # 1MB
    ) -> None:
        """解压文件"""
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise CompressionError(f"输入文件不存在: {input_path}")
        
        # 获取字典
        dictionary = None
        if dictionary_name and dictionary_name in self.dictionaries:
            dictionary = self.dictionaries[dictionary_name]
        
        strategy = self.get_strategy(algorithm)
        
        try:
            async with aiofiles.open(input_path, 'rb') as input_file:
                async with aiofiles.open(output_path, 'wb') as output_file:
                    
                    async def input_stream():
                        while chunk := await input_file.read(chunk_size):
                            yield chunk
                    
                    async for decompressed_chunk in strategy.decompress_stream(
                        input_stream(), dictionary
                    ):
                        await output_file.write(decompressed_chunk)
            
            self.logger.info(f"文件解压完成: {input_path} -> {output_path}")
            
        except Exception as e:
            # 清理输出文件
            if output_path.exists():
                output_path.unlink()
            
            self.logger.error(f"文件解压失败: {e}")
            raise CompressionError(f"文件解压失败: {e}")
    
    def _select_algorithm(self, data_size: int) -> CompressionAlgorithm:
        """根据数据大小选择算法"""
        if data_size < self.config.small_file_threshold:
            # 小文件优先速度
            return CompressionAlgorithm.LZ4
        elif data_size < self.config.large_file_threshold:
            # 中等文件平衡压缩比和速度
            return CompressionAlgorithm.ZSTD
        else:
            # 大文件优先压缩比
            return CompressionAlgorithm.ZSTD
    
    def _select_level(self, data_size: int) -> CompressionLevel:
        """根据数据大小选择压缩级别"""
        if data_size < self.config.small_file_threshold:
            return CompressionLevel.FAST
        elif data_size < self.config.large_file_threshold:
            return CompressionLevel.BALANCED
        else:
            return CompressionLevel.HIGH
    
    async def benchmark_algorithms(
        self, 
        test_data: bytes,
        algorithms: Optional[List[CompressionAlgorithm]] = None
    ) -> Dict[CompressionAlgorithm, CompressionResult]:
        """基准测试压缩算法"""
        if algorithms is None:
            algorithms = list(self.strategies.keys())
        
        results = {}
        
        for algorithm in algorithms:
            if algorithm not in self.strategies:
                continue
            
            try:
                result = await self.compress_data(
                    test_data, 
                    algorithm, 
                    CompressionLevel.BALANCED
                )
                results[algorithm] = result
                
            except Exception as e:
                self.logger.warning(f"算法 {algorithm.value} 基准测试失败: {e}")
        
        # 按压缩比排序
        sorted_results = dict(
            sorted(
                results.items(), 
                key=lambda x: x[1].compression_ratio
            )
        )
        
        self.logger.info(f"基准测试完成，测试了 {len(results)} 个算法")
        return sorted_results
    
    async def find_best_algorithm(
        self, 
        test_data: bytes,
        priority: str = "compression_ratio"  # compression_ratio, speed, balanced
    ) -> CompressionAlgorithm:
        """找到最佳压缩算法"""
        results = await self.benchmark_algorithms(test_data)
        
        if not results:
            raise CompressionError("没有可用的压缩算法")
        
        if priority == "compression_ratio":
            # 选择压缩比最好的
            best = min(results.items(), key=lambda x: x[1].compression_ratio)
        elif priority == "speed":
            # 选择速度最快的
            best = max(results.items(), key=lambda x: x[1].throughput_mbps)
        elif priority == "balanced":
            # 平衡压缩比和速度
            best = min(
                results.items(), 
                key=lambda x: x[1].compression_ratio * (1 / (x[1].throughput_mbps + 1))
            )
        else:
            raise CompressionError(f"未知的优先级: {priority}")
        
        return best[0]
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        return {
            'available_algorithms': [alg.value for alg in self.strategies.keys()],
            'dictionaries': list(self.dictionaries.keys()),
            'config': self.config.to_dict()
        }


class CompressionSelector:
    """压缩选择器"""
    
    @staticmethod
    def select_for_content_type(content_type: str) -> CompressionAlgorithm:
        """根据内容类型选择压缩算法"""
        content_type = content_type.lower()
        
        if content_type in ('text/plain', 'application/json', 'text/xml'):
            return CompressionAlgorithm.ZSTD  # 文本类型用ZSTD
        elif content_type.startswith('text/'):
            return CompressionAlgorithm.GZIP  # 其他文本用GZIP
        elif content_type in ('application/octet-stream', 'application/zip'):
            return CompressionAlgorithm.LZ4   # 二进制快速压缩
        else:
            return CompressionAlgorithm.ZSTD  # 默认使用ZSTD
    
    @staticmethod
    def select_for_file_extension(file_path: Union[str, Path]) -> CompressionAlgorithm:
        """根据文件扩展名选择压缩算法"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # 文本文件
        if ext in ('.txt', '.json', '.xml', '.csv', '.log', '.md'):
            return CompressionAlgorithm.ZSTD
        
        # 代码文件
        elif ext in ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h'):
            return CompressionAlgorithm.ZSTD
        
        # 配置文件
        elif ext in ('.ini', '.conf', '.cfg', '.yaml', '.yml', '.toml'):
            return CompressionAlgorithm.GZIP
        
        # 已压缩文件
        elif ext in ('.zip', '.gz', '.bz2', '.xz', '.7z'):
            return CompressionAlgorithm.LZ4  # 已压缩文件用快速算法
        
        # 二进制文件
        else:
            return CompressionAlgorithm.LZ4
    
    @staticmethod
    def select_level_for_priority(priority: str) -> CompressionLevel:
        """根据优先级选择压缩级别"""
        if priority == "speed":
            return CompressionLevel.FASTEST
        elif priority == "size":
            return CompressionLevel.MAXIMUM
        elif priority == "balanced":
            return CompressionLevel.BALANCED
        else:
            return CompressionLevel.BALANCED