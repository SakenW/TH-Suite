"""
压缩服务模块

提供高效的数据压缩功能，支持：
- Zstd算法和语言特化字典
- 流式压缩，内存效率优化
- 自适应压缩策略选择
- 多种压缩算法支持
"""

from .core import (
    CompressionEngine,
    CompressionResult,
    CompressionStrategy,
    CompressionLevel
)
from .algorithms import (
    ZstdCompressor,
    GzipCompressor,
    Lz4Compressor,
    BrotliCompressor
)
from .dictionary import (
    DictionaryManager,
    LanguageDictionary,
    DictionaryTrainer
)
from .streaming import (
    StreamingCompressor,
    StreamingDecompressor,
    ChunkedCompressor
)
from .config import CompressionConfig
from .errors import (
    CompressionError,
    DictionaryError,
    StreamingError
)

__all__ = [
    # 核心组件
    'CompressionEngine',
    'CompressionResult',
    'CompressionStrategy',
    'CompressionLevel',
    
    # 压缩算法
    'ZstdCompressor',
    'GzipCompressor',
    'Lz4Compressor',
    'BrotliCompressor',
    
    # 字典管理
    'DictionaryManager',
    'LanguageDictionary',
    'DictionaryTrainer',
    
    # 流式压缩
    'StreamingCompressor',
    'StreamingDecompressor',
    'ChunkedCompressor',
    
    # 配置和错误
    'CompressionConfig',
    'CompressionError',
    'DictionaryError',
    'StreamingError',
]