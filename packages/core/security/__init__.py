"""
安全验证框架

提供文件完整性验证、权限控制、加密传输等安全功能，支持：
- 文件完整性验证（BLAKE3）
- 权限控制和访问验证
- 加密传输和存储支持
- 安全审计和日志记录
"""

from .core import (
    SecurityManager,
    SecurityPolicy,
    SecurityContext,
    AccessControl
)
from .integrity import (
    IntegrityVerifier,
    HashCalculator,
    ChecksumValidator,
    FileIntegrityChecker
)
from .encryption import (
    EncryptionManager,
    EncryptionProvider,
    AESEncryption,
    ChaCha20Encryption
)
from .auth import (
    AuthenticationManager,
    AuthorizationManager,
    TokenValidator,
    PermissionChecker
)
from .audit import (
    SecurityAuditor,
    AuditLogger,
    SecurityEvent,
    AuditTrail
)
from .config import SecurityConfig
from .errors import (
    SecurityError,
    IntegrityError,
    EncryptionError,
    AuthenticationError,
    AuthorizationError,
    AuditError
)

__all__ = [
    # 核心组件
    'SecurityManager',
    'SecurityPolicy',
    'SecurityContext',
    'AccessControl',
    
    # 完整性验证
    'IntegrityVerifier',
    'HashCalculator',
    'ChecksumValidator',
    'FileIntegrityChecker',
    
    # 加密服务
    'EncryptionManager',
    'EncryptionProvider',
    'AESEncryption',
    'ChaCha20Encryption',
    
    # 认证授权
    'AuthenticationManager',
    'AuthorizationManager',
    'TokenValidator',
    'PermissionChecker',
    
    # 安全审计
    'SecurityAuditor',
    'AuditLogger',
    'SecurityEvent',
    'AuditTrail',
    
    # 配置和错误
    'SecurityConfig',
    'SecurityError',
    'IntegrityError',
    'EncryptionError',
    'AuthenticationError',
    'AuthorizationError',
    'AuditError',
]