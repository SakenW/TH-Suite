"""
压缩服务错误定义

定义压缩过程中可能出现的各种异常
"""

from typing import Optional, Dict, Any


class CompressionError(Exception):
    """压缩基础异常"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.metadata = metadata or {}


class AlgorithmError(CompressionError):
    """压缩算法异常"""
    
    def __init__(
        self, 
        message: str, 
        algorithm: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.algorithm = algorithm


class DictionaryError(CompressionError):
    """字典处理异常"""
    
    def __init__(
        self, 
        message: str, 
        dictionary_name: Optional[str] = None,
        dictionary_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.dictionary_name = dictionary_name
        self.dictionary_size = dictionary_size


class StreamingError(CompressionError):
    """流式压缩异常"""
    
    def __init__(
        self, 
        message: str, 
        stream_position: Optional[int] = None,
        chunk_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.stream_position = stream_position
        self.chunk_size = chunk_size


class ConfigurationError(CompressionError):
    """配置异常"""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class MemoryError(CompressionError):
    """内存异常"""
    
    def __init__(
        self, 
        message: str, 
        required_memory: Optional[int] = None,
        available_memory: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_memory = required_memory
        self.available_memory = available_memory


class IntegrityError(CompressionError):
    """完整性异常"""
    
    def __init__(
        self, 
        message: str, 
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
        original_size: Optional[int] = None,
        decompressed_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.original_size = original_size
        self.decompressed_size = decompressed_size


class PerformanceError(CompressionError):
    """性能异常"""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        elapsed_time: Optional[float] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.operation = operation
        self.elapsed_time = elapsed_time
        self.timeout = timeout


class UnsupportedFormatError(CompressionError):
    """不支持的格式异常"""
    
    def __init__(
        self, 
        message: str, 
        format_type: Optional[str] = None,
        supported_formats: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.format_type = format_type
        self.supported_formats = supported_formats or []


class CompressionRatioError(CompressionError):
    """压缩比异常"""
    
    def __init__(
        self, 
        message: str, 
        achieved_ratio: Optional[float] = None,
        expected_ratio: Optional[float] = None,
        original_size: Optional[int] = None,
        compressed_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.achieved_ratio = achieved_ratio
        self.expected_ratio = expected_ratio
        self.original_size = original_size
        self.compressed_size = compressed_size


# 错误处理工具函数
def wrap_compression_exception(func):
    """装饰器：包装异常为压缩异常"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CompressionError:
            raise  # 重新抛出压缩异常
        except MemoryError as e:
            raise MemoryError(f"内存不足: {e}")
        except ValueError as e:
            raise ConfigurationError(f"配置错误: {e}")
        except FileNotFoundError as e:
            raise CompressionError(f"文件不存在: {e}")
        except PermissionError as e:
            raise CompressionError(f"权限不足: {e}")
        except OSError as e:
            raise CompressionError(f"系统错误: {e}")
        except Exception as e:
            raise CompressionError(f"未知错误: {e}")
    
    return wrapper


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
    
    def handle_error(self, error: CompressionError, context: Dict[str, Any] = None):
        """处理错误"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        error_record = {
            'type': error_type,
            'message': error.message,
            'code': error.error_code,
            'metadata': error.metadata,
            'context': context or {},
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        self.error_history.append(error_record)
        
        # 保持历史记录在合理范围内
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            'total_errors': len(self.error_history),
            'error_counts': self.error_counts.copy(),
            'recent_errors': self.error_history[-10:] if self.error_history else []
        }
    
    def should_retry(self, error: CompressionError, attempt: int, max_attempts: int) -> bool:
        """判断是否应该重试"""
        if attempt >= max_attempts:
            return False
        
        # 根据错误类型决定是否重试
        if isinstance(error, (MemoryError, PerformanceError)):
            return True  # 内存或性能问题可以重试
        elif isinstance(error, (ConfigurationError, UnsupportedFormatError)):
            return False  # 配置或格式错误不重试
        elif isinstance(error, StreamingError):
            return True  # 流式错误可以重试
        elif isinstance(error, IntegrityError):
            return False  # 完整性错误不重试
        else:
            return True  # 默认重试


# 预定义错误消息
class ErrorMessages:
    """错误消息常量"""
    
    # 算法错误
    ALGORITHM_NOT_SUPPORTED = "不支持的压缩算法"
    ALGORITHM_INIT_FAILED = "压缩算法初始化失败"
    ALGORITHM_COMPRESS_FAILED = "压缩操作失败"
    ALGORITHM_DECOMPRESS_FAILED = "解压操作失败"
    
    # 字典错误
    DICTIONARY_NOT_FOUND = "压缩字典不存在"
    DICTIONARY_INVALID = "无效的压缩字典"
    DICTIONARY_TOO_LARGE = "压缩字典过大"
    DICTIONARY_TRAINING_FAILED = "字典训练失败"
    
    # 流式错误
    STREAM_READ_FAILED = "流读取失败"
    STREAM_WRITE_FAILED = "流写入失败"
    STREAM_POSITION_INVALID = "无效的流位置"
    STREAM_CHUNK_TOO_LARGE = "流分块过大"
    
    # 配置错误
    CONFIG_INVALID = "无效的配置"
    CONFIG_MISSING = "缺少必要配置"
    CONFIG_CONFLICT = "配置冲突"
    
    # 内存错误
    MEMORY_INSUFFICIENT = "内存不足"
    MEMORY_LIMIT_EXCEEDED = "超出内存限制"
    MEMORY_ALLOCATION_FAILED = "内存分配失败"
    
    # 完整性错误
    CHECKSUM_MISMATCH = "校验和不匹配"
    SIZE_MISMATCH = "大小不匹配"
    CORRUPTION_DETECTED = "检测到数据损坏"
    
    # 性能错误
    TIMEOUT_EXCEEDED = "操作超时"
    PERFORMANCE_DEGRADED = "性能下降"
    RESOURCE_EXHAUSTED = "资源耗尽"
    
    # 格式错误
    FORMAT_NOT_SUPPORTED = "不支持的格式"
    FORMAT_INVALID = "无效的格式"
    FORMAT_VERSION_MISMATCH = "格式版本不匹配"