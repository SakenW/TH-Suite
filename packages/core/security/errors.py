"""
安全框架错误定义

定义安全相关的各种异常类型
"""

from typing import Optional, Dict, Any


class SecurityError(Exception):
    """安全基础异常"""
    
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


class AuthenticationError(SecurityError):
    """认证异常"""
    
    def __init__(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        auth_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_id = user_id
        self.auth_method = auth_method


class AuthorizationError(SecurityError):
    """授权异常"""
    
    def __init__(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        required_permission: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_id = user_id
        self.resource_id = resource_id
        self.required_permission = required_permission


class IntegrityError(SecurityError):
    """完整性异常"""
    
    def __init__(
        self, 
        message: str, 
        file_path: Optional[str] = None,
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
        algorithm: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.algorithm = algorithm


class EncryptionError(SecurityError):
    """加密异常"""
    
    def __init__(
        self, 
        message: str, 
        algorithm: Optional[str] = None,
        key_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.algorithm = algorithm
        self.key_id = key_id
        self.operation = operation


class SessionError(SecurityError):
    """会话异常"""
    
    def __init__(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.session_id = session_id
        self.user_id = user_id


class PermissionError(SecurityError):
    """权限异常"""
    
    def __init__(
        self, 
        message: str, 
        permission: Optional[str] = None,
        role: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.permission = permission
        self.role = role


class PolicyError(SecurityError):
    """策略异常"""
    
    def __init__(
        self, 
        message: str, 
        policy_name: Optional[str] = None,
        policy_version: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.policy_name = policy_name
        self.policy_version = policy_version


class AuditError(SecurityError):
    """审计异常"""
    
    def __init__(
        self, 
        message: str, 
        audit_event: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.audit_event = audit_event
        self.event_data = event_data


class RateLimitError(SecurityError):
    """速率限制异常"""
    
    def __init__(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        reset_time: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_id = user_id
        self.limit = limit
        self.window = window
        self.reset_time = reset_time


class ValidationError(SecurityError):
    """验证异常"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.constraint = constraint


class ConfigurationError(SecurityError):
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


class CryptoError(SecurityError):
    """密码学异常"""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        algorithm: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.operation = operation
        self.algorithm = algorithm


class FileSecurityError(SecurityError):
    """文件安全异常"""
    
    def __init__(
        self, 
        message: str, 
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        security_check: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.file_type = file_type
        self.security_check = security_check


class NetworkSecurityError(SecurityError):
    """网络安全异常"""
    
    def __init__(
        self, 
        message: str, 
        ip_address: Optional[str] = None,
        country: Optional[str] = None,
        blocked_reason: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.ip_address = ip_address
        self.country = country
        self.blocked_reason = blocked_reason


# 错误处理工具函数
def wrap_security_exception(func):
    """装饰器：包装异常为安全异常"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SecurityError:
            raise  # 重新抛出安全异常
        except PermissionError as e:
            raise AuthorizationError(f"权限不足: {e}")
        except ValueError as e:
            raise ValidationError(f"验证失败: {e}")
        except FileNotFoundError as e:
            raise FileSecurityError(f"文件不存在: {e}")
        except ConnectionError as e:
            raise NetworkSecurityError(f"网络连接错误: {e}")
        except Exception as e:
            raise SecurityError(f"未知安全错误: {e}")
    
    return wrapper


class SecurityErrorHandler:
    """安全错误处理器"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
        self.critical_errors: list = []
    
    def handle_error(self, error: SecurityError, context: Dict[str, Any] = None):
        """处理安全错误"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        error_record = {
            'type': error_type,
            'message': error.message,
            'code': error.error_code,
            'metadata': error.metadata,
            'context': context or {},
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'severity': self._get_error_severity(error)
        }
        
        self.error_history.append(error_record)
        
        # 标记关键错误
        if self._is_critical_error(error):
            self.critical_errors.append(error_record)
        
        # 保持历史记录在合理范围内
        if len(self.error_history) > 10000:
            self.error_history = self.error_history[-5000:]
        
        if len(self.critical_errors) > 1000:
            self.critical_errors = self.critical_errors[-500:]
    
    def _get_error_severity(self, error: SecurityError) -> str:
        """获取错误严重级别"""
        if isinstance(error, (AuthenticationError, AuthorizationError)):
            return "high"
        elif isinstance(error, (IntegrityError, EncryptionError)):
            return "critical"
        elif isinstance(error, (NetworkSecurityError, FileSecurityError)):
            return "medium"
        elif isinstance(error, RateLimitError):
            return "low"
        else:
            return "medium"
    
    def _is_critical_error(self, error: SecurityError) -> bool:
        """判断是否为关键错误"""
        critical_types = (
            IntegrityError,
            EncryptionError,
            AuthenticationError,
            NetworkSecurityError
        )
        return isinstance(error, critical_types)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            'total_errors': len(self.error_history),
            'critical_errors': len(self.critical_errors),
            'error_counts': self.error_counts.copy(),
            'recent_errors': self.error_history[-10:] if self.error_history else [],
            'recent_critical': self.critical_errors[-5:] if self.critical_errors else []
        }
    
    def should_alert(self, error: SecurityError) -> bool:
        """判断是否应该发出警报"""
        return self._is_critical_error(error)
    
    def should_block_user(self, user_id: str, error_threshold: int = 5) -> bool:
        """判断是否应该阻止用户"""
        recent_errors = [
            e for e in self.error_history[-100:]
            if e.get('context', {}).get('user_id') == user_id
        ]
        
        return len(recent_errors) >= error_threshold


# 预定义错误消息
class SecurityErrorMessages:
    """安全错误消息常量"""
    
    # 认证错误
    INVALID_CREDENTIALS = "用户名或密码错误"
    ACCOUNT_LOCKED = "账户已被锁定"
    SESSION_EXPIRED = "会话已过期"
    TOKEN_INVALID = "无效的令牌"
    
    # 授权错误
    PERMISSION_DENIED = "权限不足"
    ROLE_REQUIRED = "需要特定角色"
    RESOURCE_FORBIDDEN = "访问被禁止"
    OPERATION_NOT_ALLOWED = "操作不被允许"
    
    # 完整性错误
    CHECKSUM_MISMATCH = "校验和不匹配"
    FILE_CORRUPTED = "文件已损坏"
    INTEGRITY_VERIFICATION_FAILED = "完整性验证失败"
    MANIFEST_INVALID = "清单无效"
    
    # 加密错误
    ENCRYPTION_FAILED = "加密失败"
    DECRYPTION_FAILED = "解密失败"
    KEY_NOT_FOUND = "密钥不存在"
    INVALID_KEY_FORMAT = "无效的密钥格式"
    
    # 会话错误
    SESSION_NOT_FOUND = "会话不存在"
    SESSION_LIMIT_EXCEEDED = "会话数量超出限制"
    CONCURRENT_SESSION_DETECTED = "检测到并发会话"
    
    # 速率限制错误
    RATE_LIMIT_EXCEEDED = "请求频率超出限制"
    TOO_MANY_REQUESTS = "请求过于频繁"
    QUOTA_EXCEEDED = "配额已用完"
    
    # 文件安全错误
    FILE_TYPE_NOT_ALLOWED = "不允许的文件类型"
    FILE_SIZE_EXCEEDED = "文件大小超出限制"
    SUSPICIOUS_FILE_DETECTED = "检测到可疑文件"
    MALWARE_DETECTED = "检测到恶意软件"
    
    # 网络安全错误
    IP_BLOCKED = "IP地址已被阻止"
    COUNTRY_BLOCKED = "国家/地区已被阻止"
    SUSPICIOUS_ACTIVITY = "检测到可疑活动"
    ATTACK_DETECTED = "检测到攻击行为"