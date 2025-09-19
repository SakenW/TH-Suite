"""
安全配置模块

定义安全框架的各种配置选项
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Set, Optional


@dataclass
class SecurityConfig:
    """安全配置"""
    
    # 会话管理
    default_session_timeout: int = 3600  # 1小时（秒）
    max_sessions_per_user: int = 5
    session_cleanup_interval: int = 300  # 5分钟（秒）
    
    # 认证设置
    enable_authentication: bool = True
    require_strong_passwords: bool = True
    password_min_length: int = 8
    password_require_special_chars: bool = True
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 15分钟（秒）
    
    # 授权设置
    default_permissions: Set[str] = None
    admin_roles: Set[str] = None
    guest_permissions: Set[str] = None
    
    # 速率限制
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100  # 每个窗口的最大请求数
    rate_limit_window: int = 60  # 窗口大小（秒）
    
    # 完整性验证
    default_hash_algorithm: str = "blake3"
    verify_file_integrity: bool = True
    verify_transfer_integrity: bool = True
    integrity_check_chunk_size: int = 64 * 1024  # 64KB
    
    # 加密设置
    encryption_enabled: bool = False
    default_encryption_algorithm: str = "aes-256-gcm"
    key_rotation_interval: int = 86400  # 24小时（秒）
    
    # 审计日志
    enable_audit_logging: bool = True
    audit_log_level: str = "INFO"
    audit_log_format: str = "json"
    audit_log_retention: int = 7776000  # 90天（秒）
    
    # 安全策略
    security_level: str = "medium"  # low, medium, high, critical
    enforce_https: bool = True
    enable_csrf_protection: bool = True
    enable_xss_protection: bool = True
    
    # 文件安全
    allowed_file_types: Set[str] = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    quarantine_suspicious_files: bool = True
    scan_uploaded_files: bool = True
    
    # 网络安全
    allowed_ip_ranges: List[str] = None
    blocked_ip_ranges: List[str] = None
    enable_geo_blocking: bool = False
    allowed_countries: List[str] = None
    
    # 高级设置
    enable_honeypot: bool = False
    enable_intrusion_detection: bool = False
    security_headers: Dict[str, str] = None
    custom_security_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.default_permissions is None:
            self.default_permissions = {"read"}
        
        if self.admin_roles is None:
            self.admin_roles = {"admin", "superuser"}
        
        if self.guest_permissions is None:
            self.guest_permissions = {"read"}
        
        if self.allowed_file_types is None:
            self.allowed_file_types = {
                ".txt", ".json", ".xml", ".csv", ".log",
                ".png", ".jpg", ".jpeg", ".gif", ".webp",
                ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                ".zip", ".tar", ".gz", ".7z"
            }
        
        if self.security_headers is None:
            self.security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'"
            }
        
        if self.custom_security_rules is None:
            self.custom_security_rules = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'default_session_timeout': self.default_session_timeout,
            'max_sessions_per_user': self.max_sessions_per_user,
            'session_cleanup_interval': self.session_cleanup_interval,
            'enable_authentication': self.enable_authentication,
            'require_strong_passwords': self.require_strong_passwords,
            'password_min_length': self.password_min_length,
            'password_require_special_chars': self.password_require_special_chars,
            'max_login_attempts': self.max_login_attempts,
            'lockout_duration': self.lockout_duration,
            'default_permissions': list(self.default_permissions),
            'admin_roles': list(self.admin_roles),
            'guest_permissions': list(self.guest_permissions),
            'enable_rate_limiting': self.enable_rate_limiting,
            'rate_limit_requests': self.rate_limit_requests,
            'rate_limit_window': self.rate_limit_window,
            'default_hash_algorithm': self.default_hash_algorithm,
            'verify_file_integrity': self.verify_file_integrity,
            'verify_transfer_integrity': self.verify_transfer_integrity,
            'integrity_check_chunk_size': self.integrity_check_chunk_size,
            'encryption_enabled': self.encryption_enabled,
            'default_encryption_algorithm': self.default_encryption_algorithm,
            'key_rotation_interval': self.key_rotation_interval,
            'enable_audit_logging': self.enable_audit_logging,
            'audit_log_level': self.audit_log_level,
            'audit_log_format': self.audit_log_format,
            'audit_log_retention': self.audit_log_retention,
            'security_level': self.security_level,
            'enforce_https': self.enforce_https,
            'enable_csrf_protection': self.enable_csrf_protection,
            'enable_xss_protection': self.enable_xss_protection,
            'allowed_file_types': list(self.allowed_file_types),
            'max_file_size': self.max_file_size,
            'quarantine_suspicious_files': self.quarantine_suspicious_files,
            'scan_uploaded_files': self.scan_uploaded_files,
            'allowed_ip_ranges': self.allowed_ip_ranges,
            'blocked_ip_ranges': self.blocked_ip_ranges,
            'enable_geo_blocking': self.enable_geo_blocking,
            'allowed_countries': self.allowed_countries,
            'enable_honeypot': self.enable_honeypot,
            'enable_intrusion_detection': self.enable_intrusion_detection,
            'security_headers': self.security_headers,
            'custom_security_rules': self.custom_security_rules
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityConfig':
        """从字典创建配置"""
        # 转换列表为集合
        if 'default_permissions' in data:
            data['default_permissions'] = set(data['default_permissions'])
        if 'admin_roles' in data:
            data['admin_roles'] = set(data['admin_roles'])
        if 'guest_permissions' in data:
            data['guest_permissions'] = set(data['guest_permissions'])
        if 'allowed_file_types' in data:
            data['allowed_file_types'] = set(data['allowed_file_types'])
        
        return cls(**data)


# 预定义配置模板
class SecurityConfigTemplates:
    """安全配置模板"""
    
    @staticmethod
    def development() -> SecurityConfig:
        """开发环境配置"""
        return SecurityConfig(
            default_session_timeout=7200,  # 2小时
            require_strong_passwords=False,
            max_login_attempts=10,
            enable_rate_limiting=False,
            verify_file_integrity=True,
            verify_transfer_integrity=False,  # 开发时关闭以提高速度
            encryption_enabled=False,
            audit_log_level="DEBUG",
            security_level="low",
            enforce_https=False,
            enable_csrf_protection=False,
            enable_xss_protection=False,
            quarantine_suspicious_files=False,
            scan_uploaded_files=False,
            enable_intrusion_detection=False
        )
    
    @staticmethod
    def testing() -> SecurityConfig:
        """测试环境配置"""
        return SecurityConfig(
            default_session_timeout=1800,  # 30分钟
            require_strong_passwords=False,
            max_login_attempts=20,
            enable_rate_limiting=True,
            rate_limit_requests=200,
            verify_file_integrity=True,
            verify_transfer_integrity=True,
            encryption_enabled=False,
            audit_log_level="INFO",
            security_level="medium",
            enforce_https=False,
            enable_csrf_protection=True,
            enable_xss_protection=True,
            quarantine_suspicious_files=True,
            scan_uploaded_files=True,
            enable_intrusion_detection=False
        )
    
    @staticmethod
    def production() -> SecurityConfig:
        """生产环境配置"""
        return SecurityConfig(
            default_session_timeout=3600,  # 1小时
            max_sessions_per_user=3,
            require_strong_passwords=True,
            password_min_length=12,
            max_login_attempts=3,
            lockout_duration=1800,  # 30分钟
            enable_rate_limiting=True,
            rate_limit_requests=50,
            verify_file_integrity=True,
            verify_transfer_integrity=True,
            encryption_enabled=True,
            enable_audit_logging=True,
            audit_log_level="INFO",
            security_level="high",
            enforce_https=True,
            enable_csrf_protection=True,
            enable_xss_protection=True,
            quarantine_suspicious_files=True,
            scan_uploaded_files=True,
            enable_intrusion_detection=True
        )
    
    @staticmethod
    def high_security() -> SecurityConfig:
        """高安全级别配置"""
        return SecurityConfig(
            default_session_timeout=1800,  # 30分钟
            max_sessions_per_user=2,
            require_strong_passwords=True,
            password_min_length=16,
            max_login_attempts=3,
            lockout_duration=3600,  # 1小时
            enable_rate_limiting=True,
            rate_limit_requests=30,
            rate_limit_window=60,
            verify_file_integrity=True,
            verify_transfer_integrity=True,
            encryption_enabled=True,
            key_rotation_interval=3600,  # 1小时
            enable_audit_logging=True,
            audit_log_level="DEBUG",
            audit_log_retention=15552000,  # 180天
            security_level="critical",
            enforce_https=True,
            enable_csrf_protection=True,
            enable_xss_protection=True,
            max_file_size=50 * 1024 * 1024,  # 50MB
            quarantine_suspicious_files=True,
            scan_uploaded_files=True,
            enable_geo_blocking=True,
            enable_honeypot=True,
            enable_intrusion_detection=True
        )
    
    @staticmethod
    def minimal() -> SecurityConfig:
        """最小安全配置"""
        return SecurityConfig(
            default_session_timeout=86400,  # 24小时
            enable_authentication=False,
            enable_rate_limiting=False,
            verify_file_integrity=False,
            verify_transfer_integrity=False,
            encryption_enabled=False,
            enable_audit_logging=False,
            security_level="low",
            enforce_https=False,
            enable_csrf_protection=False,
            enable_xss_protection=False,
            quarantine_suspicious_files=False,
            scan_uploaded_files=False,
            enable_intrusion_detection=False
        )
    
    @staticmethod
    def file_transfer_optimized() -> SecurityConfig:
        """文件传输优化配置"""
        return SecurityConfig(
            default_session_timeout=7200,  # 2小时，支持长时间传输
            enable_rate_limiting=True,
            rate_limit_requests=1000,  # 高并发传输
            verify_file_integrity=True,
            verify_transfer_integrity=True,
            integrity_check_chunk_size=128 * 1024,  # 128KB
            encryption_enabled=True,
            audit_log_level="INFO",
            security_level="medium",
            max_file_size=1024 * 1024 * 1024,  # 1GB
            allowed_file_types={
                ".zip", ".tar", ".gz", ".7z", ".rar",
                ".iso", ".img", ".bin", ".exe", ".dmg",
                ".json", ".xml", ".txt", ".log", ".csv"
            }
        )