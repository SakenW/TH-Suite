"""
文件传输错误定义

定义传输过程中可能出现的各种异常
"""

from typing import Optional, Dict, Any


class TransferError(Exception):
    """传输基础异常"""
    
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


class ChunkError(TransferError):
    """分块传输异常"""
    
    def __init__(
        self, 
        message: str, 
        chunk_index: Optional[int] = None,
        chunk_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.chunk_index = chunk_index
        self.chunk_size = chunk_size


class NetworkError(TransferError):
    """网络传输异常"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_headers = response_headers or {}


class ValidationError(TransferError):
    """验证异常"""
    
    def __init__(
        self, 
        message: str, 
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.expected_value = expected_value
        self.actual_value = actual_value


class ConfigurationError(TransferError):
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


class AuthenticationError(TransferError):
    """认证异常"""
    
    def __init__(
        self, 
        message: str, 
        auth_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.auth_method = auth_method


class AuthorizationError(TransferError):
    """授权异常"""
    
    def __init__(
        self, 
        message: str, 
        required_permission: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_permission = required_permission


class TimeoutError(TransferError):
    """超时异常"""
    
    def __init__(
        self, 
        message: str, 
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class StorageError(TransferError):
    """存储异常"""
    
    def __init__(
        self, 
        message: str, 
        storage_path: Optional[str] = None,
        available_space: Optional[int] = None,
        required_space: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.storage_path = storage_path
        self.available_space = available_space
        self.required_space = required_space


class CompressionError(TransferError):
    """压缩异常"""
    
    def __init__(
        self, 
        message: str, 
        algorithm: Optional[str] = None,
        original_size: Optional[int] = None,
        compressed_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.algorithm = algorithm
        self.original_size = original_size
        self.compressed_size = compressed_size


class EncryptionError(TransferError):
    """加密异常"""
    
    def __init__(
        self, 
        message: str, 
        algorithm: Optional[str] = None,
        key_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.algorithm = algorithm
        self.key_size = key_size


class ConcurrencyError(TransferError):
    """并发异常"""
    
    def __init__(
        self, 
        message: str, 
        active_tasks: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.active_tasks = active_tasks
        self.max_concurrent = max_concurrent


class IntegrityError(TransferError):
    """完整性异常"""
    
    def __init__(
        self, 
        message: str, 
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
        hash_algorithm: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.hash_algorithm = hash_algorithm


class ProtocolError(TransferError):
    """协议异常"""
    
    def __init__(
        self, 
        message: str, 
        protocol: Optional[str] = None,
        version: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.protocol = protocol
        self.version = version


# 错误处理工具函数
def wrap_exception(func):
    """装饰器：包装异常为传输异常"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TransferError:
            raise  # 重新抛出传输异常
        except ConnectionError as e:
            raise NetworkError(f"连接错误: {e}")
        except TimeoutError as e:
            raise TimeoutError(f"操作超时: {e}")
        except PermissionError as e:
            raise AuthorizationError(f"权限不足: {e}")
        except FileNotFoundError as e:
            raise ValidationError(f"文件不存在: {e}")
        except OSError as e:
            raise StorageError(f"存储错误: {e}")
        except Exception as e:
            raise TransferError(f"未知错误: {e}")
    
    return wrapper


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
    
    def handle_error(self, error: TransferError, context: Dict[str, Any] = None):
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
    
    def should_retry(self, error: TransferError, attempt: int, max_attempts: int) -> bool:
        """判断是否应该重试"""
        if attempt >= max_attempts:
            return False
        
        # 根据错误类型决定是否重试
        if isinstance(error, (NetworkError, TimeoutError)):
            return True
        elif isinstance(error, ChunkError):
            return True
        elif isinstance(error, (AuthenticationError, AuthorizationError)):
            return False  # 认证/授权错误不重试
        elif isinstance(error, (ValidationError, ConfigurationError)):
            return False  # 配置/验证错误不重试
        elif isinstance(error, IntegrityError):
            return True  # 完整性错误可以重试
        else:
            return True  # 默认重试


# 预定义错误消息
class ErrorMessages:
    """错误消息常量"""
    
    # 网络错误
    CONNECTION_FAILED = "连接服务器失败"
    CONNECTION_TIMEOUT = "连接超时"
    REQUEST_TIMEOUT = "请求超时"
    NETWORK_UNREACHABLE = "网络不可达"
    
    # 文件错误
    FILE_NOT_FOUND = "文件不存在"
    FILE_TOO_LARGE = "文件过大"
    FILE_PERMISSION_DENIED = "文件权限不足"
    FILE_CORRUPTED = "文件已损坏"
    
    # 传输错误
    TRANSFER_FAILED = "传输失败"
    CHUNK_UPLOAD_FAILED = "分块上传失败"
    CHUNK_VERIFICATION_FAILED = "分块验证失败"
    TRANSFER_CANCELLED = "传输已取消"
    
    # 配置错误
    INVALID_CONFIG = "配置无效"
    MISSING_CONFIG = "缺少必要配置"
    CONFIG_CONFLICT = "配置冲突"
    
    # 认证错误
    AUTH_REQUIRED = "需要认证"
    AUTH_FAILED = "认证失败"
    TOKEN_EXPIRED = "令牌已过期"
    PERMISSION_DENIED = "权限不足"
    
    # 存储错误
    DISK_FULL = "磁盘空间不足"
    STORAGE_UNAVAILABLE = "存储不可用"
    WRITE_FAILED = "写入失败"
    READ_FAILED = "读取失败"