"""
通用文件传输模块

提供高性能、可靠的文件传输功能，支持：
- 分块上传/下载
- 断点续传
- 并发控制
- 多种传输协议
"""

from .core import FileTransferEngine, TransferTask, TransferResult
from .strategies import (
    HttpUploadStrategy,
    WebSocketStrategy,
    StreamingStrategy
)
from .config import TransferConfig, ChunkConfig, RetryConfig
from .errors import (
    TransferError,
    ChunkError,
    NetworkError,
    ValidationError
)

__all__ = [
    # 核心组件
    'FileTransferEngine',
    'TransferTask', 
    'TransferResult',
    
    # 传输策略
    'HttpUploadStrategy',
    'WebSocketStrategy',
    'StreamingStrategy',
    
    # 配置
    'TransferConfig',
    'ChunkConfig',
    'RetryConfig',
    
    # 异常
    'TransferError',
    'ChunkError',
    'NetworkError',
    'ValidationError',
]