"""
压缩服务配置模块

定义压缩引擎的各种配置选项
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class CompressionConfig:
    """压缩配置"""
    
    # 文件大小阈值
    small_file_threshold: int = 1024 * 1024  # 1MB
    large_file_threshold: int = 100 * 1024 * 1024  # 100MB
    
    # 默认设置
    default_algorithm: str = "zstd"
    default_level: int = 6
    
    # 流式压缩
    stream_chunk_size: int = 64 * 1024  # 64KB
    max_memory_usage: int = 256 * 1024 * 1024  # 256MB
    
    # 字典设置
    enable_dictionaries: bool = True
    dictionary_size: int = 64 * 1024  # 64KB
    dictionary_samples: int = 100
    
    # 性能设置
    max_concurrent_operations: int = 4
    enable_multiprocessing: bool = False
    worker_count: int = 2
    
    # 自动选择
    auto_select_algorithm: bool = True
    auto_select_level: bool = True
    benchmark_enabled: bool = False
    
    # 缓存设置
    enable_result_cache: bool = True
    cache_size: int = 100
    cache_ttl: int = 3600  # 1小时
    
    # 验证设置
    verify_compression: bool = False
    integrity_check: bool = True
    
    # 日志设置
    log_level: str = "INFO"
    log_compression_stats: bool = True
    
    # 高级设置
    enable_preprocessing: bool = False
    enable_postprocessing: bool = False
    custom_algorithms: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_algorithms is None:
            self.custom_algorithms = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'small_file_threshold': self.small_file_threshold,
            'large_file_threshold': self.large_file_threshold,
            'default_algorithm': self.default_algorithm,
            'default_level': self.default_level,
            'stream_chunk_size': self.stream_chunk_size,
            'max_memory_usage': self.max_memory_usage,
            'enable_dictionaries': self.enable_dictionaries,
            'dictionary_size': self.dictionary_size,
            'dictionary_samples': self.dictionary_samples,
            'max_concurrent_operations': self.max_concurrent_operations,
            'enable_multiprocessing': self.enable_multiprocessing,
            'worker_count': self.worker_count,
            'auto_select_algorithm': self.auto_select_algorithm,
            'auto_select_level': self.auto_select_level,
            'benchmark_enabled': self.benchmark_enabled,
            'enable_result_cache': self.enable_result_cache,
            'cache_size': self.cache_size,
            'cache_ttl': self.cache_ttl,
            'verify_compression': self.verify_compression,
            'integrity_check': self.integrity_check,
            'log_level': self.log_level,
            'log_compression_stats': self.log_compression_stats,
            'enable_preprocessing': self.enable_preprocessing,
            'enable_postprocessing': self.enable_postprocessing,
            'custom_algorithms': self.custom_algorithms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompressionConfig':
        """从字典创建配置"""
        return cls(**data)


# 预定义配置模板
class CompressionConfigTemplates:
    """压缩配置模板"""
    
    @staticmethod
    def speed_optimized() -> CompressionConfig:
        """速度优化配置"""
        return CompressionConfig(
            default_algorithm="lz4",
            default_level=1,
            stream_chunk_size=128 * 1024,  # 128KB
            enable_dictionaries=False,
            max_concurrent_operations=8,
            enable_multiprocessing=True,
            auto_select_algorithm=False,
            auto_select_level=False,
            benchmark_enabled=False,
            verify_compression=False,
            integrity_check=False,
            log_compression_stats=False
        )
    
    @staticmethod
    def compression_optimized() -> CompressionConfig:
        """压缩比优化配置"""
        return CompressionConfig(
            default_algorithm="zstd",
            default_level=12,
            stream_chunk_size=32 * 1024,  # 32KB
            enable_dictionaries=True,
            dictionary_size=128 * 1024,  # 128KB
            dictionary_samples=200,
            max_concurrent_operations=2,
            auto_select_algorithm=True,
            auto_select_level=True,
            benchmark_enabled=True,
            verify_compression=True,
            integrity_check=True,
            enable_preprocessing=True
        )
    
    @staticmethod
    def balanced() -> CompressionConfig:
        """平衡配置"""
        return CompressionConfig(
            default_algorithm="zstd",
            default_level=6,
            stream_chunk_size=64 * 1024,  # 64KB
            enable_dictionaries=True,
            dictionary_size=64 * 1024,  # 64KB
            max_concurrent_operations=4,
            auto_select_algorithm=True,
            auto_select_level=True,
            benchmark_enabled=False,
            verify_compression=False,
            integrity_check=True,
            log_compression_stats=True
        )
    
    @staticmethod
    def memory_constrained() -> CompressionConfig:
        """内存受限配置"""
        return CompressionConfig(
            default_algorithm="gzip",
            default_level=3,
            stream_chunk_size=16 * 1024,  # 16KB
            max_memory_usage=64 * 1024 * 1024,  # 64MB
            enable_dictionaries=False,
            max_concurrent_operations=2,
            enable_multiprocessing=False,
            worker_count=1,
            enable_result_cache=False,
            verify_compression=False,
            enable_preprocessing=False,
            enable_postprocessing=False
        )
    
    @staticmethod
    def text_optimized() -> CompressionConfig:
        """文本优化配置"""
        return CompressionConfig(
            default_algorithm="zstd",
            default_level=9,
            enable_dictionaries=True,
            dictionary_size=128 * 1024,  # 128KB
            dictionary_samples=500,  # 更多样本用于文本
            auto_select_algorithm=False,  # 固定使用ZSTD
            benchmark_enabled=True,
            verify_compression=True,
            enable_preprocessing=True,  # 文本预处理
            log_compression_stats=True
        )
    
    @staticmethod
    def development() -> CompressionConfig:
        """开发环境配置"""
        return CompressionConfig(
            default_algorithm="zstd",
            default_level=3,
            stream_chunk_size=32 * 1024,  # 32KB
            enable_dictionaries=True,
            max_concurrent_operations=2,
            auto_select_algorithm=True,
            benchmark_enabled=True,
            enable_result_cache=True,
            cache_size=50,
            verify_compression=True,
            integrity_check=True,
            log_level="DEBUG",
            log_compression_stats=True
        )
    
    @staticmethod
    def production() -> CompressionConfig:
        """生产环境配置"""
        return CompressionConfig(
            default_algorithm="zstd",
            default_level=6,
            stream_chunk_size=64 * 1024,  # 64KB
            max_memory_usage=512 * 1024 * 1024,  # 512MB
            enable_dictionaries=True,
            dictionary_size=64 * 1024,  # 64KB
            max_concurrent_operations=6,
            enable_multiprocessing=True,
            worker_count=4,
            auto_select_algorithm=True,
            benchmark_enabled=False,
            enable_result_cache=True,
            cache_size=200,
            cache_ttl=7200,  # 2小时
            verify_compression=False,
            integrity_check=True,
            log_level="INFO",
            log_compression_stats=False
        )