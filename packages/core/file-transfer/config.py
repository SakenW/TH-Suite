"""
文件传输配置模块

定义传输引擎的各种配置选项
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ChunkConfig:
    """分块配置"""
    size: int = 8 * 1024 * 1024  # 8MB 默认分块大小
    min_size: int = 1024 * 1024  # 1MB 最小分块大小
    max_size: int = 64 * 1024 * 1024  # 64MB 最大分块大小
    
    def __post_init__(self):
        if self.size < self.min_size:
            self.size = self.min_size
        elif self.size > self.max_size:
            self.size = self.max_size


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    delay: float = 1.0  # 基础延迟时间（秒）
    backoff_factor: float = 2.0  # 指数退避因子
    max_delay: float = 60.0  # 最大延迟时间（秒）
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


@dataclass
class CompressionConfig:
    """压缩配置"""
    enabled: bool = False
    algorithm: str = "zstd"  # 支持: zstd, gzip, lz4
    level: int = 3  # 压缩级别
    min_file_size: int = 1024 * 1024  # 最小压缩文件大小 (1MB)
    
    def should_compress(self, file_size: int) -> bool:
        """判断是否应该压缩"""
        return self.enabled and file_size >= self.min_file_size


@dataclass
class SecurityConfig:
    """安全配置"""
    verify_ssl: bool = True
    use_encryption: bool = False
    encryption_algorithm: str = "AES-256-GCM"
    verify_certificates: bool = True
    allowed_hosts: Optional[list] = None
    
    def is_host_allowed(self, host: str) -> bool:
        """检查主机是否被允许"""
        if self.allowed_hosts is None:
            return True
        return host in self.allowed_hosts


@dataclass
class PerformanceConfig:
    """性能配置"""
    buffer_size: int = 64 * 1024  # 64KB 缓冲区大小
    io_timeout: float = 30.0  # I/O 超时时间（秒）
    connect_timeout: float = 10.0  # 连接超时时间（秒）
    read_timeout: float = 60.0  # 读取超时时间（秒）
    write_timeout: float = 60.0  # 写入超时时间（秒）
    max_memory_usage: int = 512 * 1024 * 1024  # 最大内存使用 (512MB)
    
    def get_optimal_chunk_size(self, file_size: int) -> int:
        """根据文件大小计算最优分块大小"""
        if file_size < 10 * 1024 * 1024:  # 10MB
            return 1 * 1024 * 1024  # 1MB
        elif file_size < 100 * 1024 * 1024:  # 100MB
            return 4 * 1024 * 1024  # 4MB
        elif file_size < 1024 * 1024 * 1024:  # 1GB
            return 8 * 1024 * 1024  # 8MB
        else:
            return 16 * 1024 * 1024  # 16MB


@dataclass
class TransferConfig:
    """传输配置"""
    # 并发控制
    max_concurrent_transfers: int = 3
    max_concurrent_chunks: int = 8
    
    # 分块配置
    chunk_config: ChunkConfig = None
    
    # 重试配置
    retry_config: RetryConfig = None
    
    # 压缩配置
    compression_config: CompressionConfig = None
    
    # 安全配置
    security_config: SecurityConfig = None
    
    # 性能配置
    performance_config: PerformanceConfig = None
    
    # 验证选项
    verify_before_transfer: bool = True
    verify_after_transfer: bool = True
    verify_chunks: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_progress_interval: float = 5.0  # 进度日志间隔（秒）
    
    # 高级选项
    enable_resume: bool = True
    enable_deduplication: bool = False
    max_file_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    
    # 自定义元数据
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.chunk_config is None:
            self.chunk_config = ChunkConfig()
        
        if self.retry_config is None:
            self.retry_config = RetryConfig()
        
        if self.compression_config is None:
            self.compression_config = CompressionConfig()
        
        if self.security_config is None:
            self.security_config = SecurityConfig()
        
        if self.performance_config is None:
            self.performance_config = PerformanceConfig()
        
        if self.metadata is None:
            self.metadata = {}
    
    def optimize_for_file_size(self, file_size: int) -> 'TransferConfig':
        """根据文件大小优化配置"""
        # 克隆当前配置
        config = TransferConfig(
            max_concurrent_transfers=self.max_concurrent_transfers,
            max_concurrent_chunks=self.max_concurrent_chunks,
            chunk_config=ChunkConfig(
                size=self.performance_config.get_optimal_chunk_size(file_size),
                min_size=self.chunk_config.min_size,
                max_size=self.chunk_config.max_size
            ),
            retry_config=self.retry_config,
            compression_config=self.compression_config,
            security_config=self.security_config,
            performance_config=self.performance_config,
            verify_before_transfer=self.verify_before_transfer,
            verify_after_transfer=self.verify_after_transfer,
            verify_chunks=self.verify_chunks,
            log_level=self.log_level,
            log_progress_interval=self.log_progress_interval,
            enable_resume=self.enable_resume,
            enable_deduplication=self.enable_deduplication,
            max_file_size=self.max_file_size,
            metadata=self.metadata.copy()
        )
        
        # 根据文件大小调整并发设置
        if file_size < 10 * 1024 * 1024:  # 小文件 (<10MB)
            config.max_concurrent_chunks = 2
        elif file_size < 100 * 1024 * 1024:  # 中等文件 (<100MB)
            config.max_concurrent_chunks = 4
        else:  # 大文件 (>=100MB)
            config.max_concurrent_chunks = 8
        
        return config
    
    def optimize_for_network(self, bandwidth_mbps: float, latency_ms: float) -> 'TransferConfig':
        """根据网络条件优化配置"""
        config = self.__class__(
            max_concurrent_transfers=self.max_concurrent_transfers,
            max_concurrent_chunks=self.max_concurrent_chunks,
            chunk_config=self.chunk_config,
            retry_config=self.retry_config,
            compression_config=self.compression_config,
            security_config=self.security_config,
            performance_config=self.performance_config,
            verify_before_transfer=self.verify_before_transfer,
            verify_after_transfer=self.verify_after_transfer,
            verify_chunks=self.verify_chunks,
            log_level=self.log_level,
            log_progress_interval=self.log_progress_interval,
            enable_resume=self.enable_resume,
            enable_deduplication=self.enable_deduplication,
            max_file_size=self.max_file_size,
            metadata=self.metadata.copy()
        )
        
        # 根据带宽调整并发数
        if bandwidth_mbps < 10:  # 低带宽
            config.max_concurrent_chunks = 2
            config.max_concurrent_transfers = 1
        elif bandwidth_mbps < 50:  # 中等带宽
            config.max_concurrent_chunks = 4
            config.max_concurrent_transfers = 2
        else:  # 高带宽
            config.max_concurrent_chunks = 8
            config.max_concurrent_transfers = 3
        
        # 根据延迟调整超时时间
        if latency_ms > 500:  # 高延迟
            config.performance_config.connect_timeout = 20.0
            config.performance_config.read_timeout = 120.0
            config.retry_config.delay = 3.0
        elif latency_ms > 200:  # 中等延迟
            config.performance_config.connect_timeout = 15.0
            config.performance_config.read_timeout = 90.0
            config.retry_config.delay = 2.0
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'max_concurrent_transfers': self.max_concurrent_transfers,
            'max_concurrent_chunks': self.max_concurrent_chunks,
            'chunk_size': self.chunk_config.size,
            'retry_max_attempts': self.retry_config.max_attempts,
            'compression_enabled': self.compression_config.enabled,
            'verify_chunks': self.verify_chunks,
            'log_level': self.log_level,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransferConfig':
        """从字典创建配置"""
        config = cls()
        
        if 'max_concurrent_transfers' in data:
            config.max_concurrent_transfers = data['max_concurrent_transfers']
        
        if 'max_concurrent_chunks' in data:
            config.max_concurrent_chunks = data['max_concurrent_chunks']
        
        if 'chunk_size' in data:
            config.chunk_config.size = data['chunk_size']
        
        if 'retry_max_attempts' in data:
            config.retry_config.max_attempts = data['retry_max_attempts']
        
        if 'compression_enabled' in data:
            config.compression_config.enabled = data['compression_enabled']
        
        if 'verify_chunks' in data:
            config.verify_chunks = data['verify_chunks']
        
        if 'log_level' in data:
            config.log_level = data['log_level']
        
        if 'metadata' in data:
            config.metadata = data['metadata']
        
        return config


# 预定义配置模板
class ConfigTemplates:
    """配置模板"""
    
    @staticmethod
    def fast_local() -> TransferConfig:
        """快速本地传输配置"""
        return TransferConfig(
            max_concurrent_transfers=5,
            max_concurrent_chunks=16,
            chunk_config=ChunkConfig(size=16 * 1024 * 1024),  # 16MB
            verify_chunks=False,  # 本地传输可以关闭验证
            compression_config=CompressionConfig(enabled=False)
        )
    
    @staticmethod
    def reliable_remote() -> TransferConfig:
        """可靠远程传输配置"""
        return TransferConfig(
            max_concurrent_transfers=2,
            max_concurrent_chunks=4,
            chunk_config=ChunkConfig(size=4 * 1024 * 1024),  # 4MB
            retry_config=RetryConfig(max_attempts=5, delay=2.0),
            verify_chunks=True,
            compression_config=CompressionConfig(enabled=True, level=3)
        )
    
    @staticmethod
    def low_bandwidth() -> TransferConfig:
        """低带宽网络配置"""
        return TransferConfig(
            max_concurrent_transfers=1,
            max_concurrent_chunks=2,
            chunk_config=ChunkConfig(size=1 * 1024 * 1024),  # 1MB
            retry_config=RetryConfig(max_attempts=5, delay=3.0),
            compression_config=CompressionConfig(enabled=True, level=6),
            performance_config=PerformanceConfig(
                connect_timeout=30.0,
                read_timeout=180.0
            )
        )
    
    @staticmethod
    def high_performance() -> TransferConfig:
        """高性能传输配置"""
        return TransferConfig(
            max_concurrent_transfers=5,
            max_concurrent_chunks=16,
            chunk_config=ChunkConfig(size=32 * 1024 * 1024),  # 32MB
            verify_chunks=False,  # 为了性能关闭分块验证
            compression_config=CompressionConfig(enabled=False),
            performance_config=PerformanceConfig(
                buffer_size=128 * 1024,  # 128KB
                io_timeout=10.0
            )
        )