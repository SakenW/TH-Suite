"""
安全框架核心模块

实现安全管理器、安全策略、访问控制等核心功能
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Dict, List, Optional, Set, Union, Any, 
    Callable, Protocol, Awaitable
)
import uuid

from .config import SecurityConfig
from .errors import SecurityError, AuthenticationError, AuthorizationError


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    """操作类型"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    MODIFY = "modify"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    ACCESS = "access"


class PermissionLevel(Enum):
    """权限级别"""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 4
    DELETE = 8
    ADMIN = 15  # 所有权限


@dataclass
class SecurityContext:
    """安全上下文"""
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    permissions: Set[str] = field(default_factory=set)
    roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        """检查是否已过期"""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    @property
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return "admin" in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions or self.is_admin
    
    def has_role(self, role: str) -> bool:
        """检查是否有指定角色"""
        return role in self.roles


@dataclass
class SecurityResource:
    """安全资源"""
    resource_id: str
    resource_type: str
    owner_id: str
    path: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    required_permissions: Set[str] = field(default_factory=set)
    allowed_roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def requires_permission(self, permission: str) -> bool:
        """检查是否需要指定权限"""
        return permission in self.required_permissions
    
    def allows_role(self, role: str) -> bool:
        """检查是否允许指定角色"""
        return not self.allowed_roles or role in self.allowed_roles


class SecurityPolicy(ABC):
    """安全策略抽象基类"""
    
    @abstractmethod
    async def evaluate(
        self, 
        context: SecurityContext, 
        resource: SecurityResource, 
        action: ActionType
    ) -> bool:
        """评估安全策略"""
        pass


class DefaultSecurityPolicy(SecurityPolicy):
    """默认安全策略"""
    
    async def evaluate(
        self, 
        context: SecurityContext, 
        resource: SecurityResource, 
        action: ActionType
    ) -> bool:
        """评估默认安全策略"""
        # 检查会话是否过期
        if context.is_expired:
            return False
        
        # 管理员有所有权限
        if context.is_admin:
            return True
        
        # 检查资源所有者
        if resource.owner_id == context.user_id:
            return True
        
        # 检查角色权限
        if resource.allowed_roles and not any(
            role in context.roles for role in resource.allowed_roles
        ):
            return False
        
        # 检查操作权限
        required_permission = f"{resource.resource_type}:{action.value}"
        if resource.requires_permission(required_permission):
            return context.has_permission(required_permission)
        
        # 默认允许读取操作
        return action == ActionType.READ


class AccessControl:
    """访问控制"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.policies: List[SecurityPolicy] = []
        self.rate_limiter: Dict[str, List[float]] = {}
        
    def add_policy(self, policy: SecurityPolicy) -> None:
        """添加安全策略"""
        self.policies.append(policy)
    
    async def check_access(
        self, 
        context: SecurityContext, 
        resource: SecurityResource, 
        action: ActionType
    ) -> bool:
        """检查访问权限"""
        # 速率限制检查
        if not await self._check_rate_limit(context):
            self.logger.warning(f"用户 {context.user_id} 触发速率限制")
            return False
        
        # 执行所有安全策略
        for policy in self.policies:
            try:
                if not await policy.evaluate(context, resource, action):
                    self.logger.warning(
                        f"用户 {context.user_id} 访问资源 {resource.resource_id} "
                        f"执行 {action.value} 操作被策略 {policy.__class__.__name__} 拒绝"
                    )
                    return False
            except Exception as e:
                self.logger.error(f"安全策略评估失败: {e}")
                return False
        
        self.logger.debug(
            f"用户 {context.user_id} 访问资源 {resource.resource_id} "
            f"执行 {action.value} 操作通过权限检查"
        )
        return True
    
    async def _check_rate_limit(self, context: SecurityContext) -> bool:
        """检查速率限制"""
        if not self.config.enable_rate_limiting:
            return True
        
        user_id = context.user_id
        current_time = time.time()
        window_size = self.config.rate_limit_window
        max_requests = self.config.rate_limit_requests
        
        # 获取用户的请求历史
        if user_id not in self.rate_limiter:
            self.rate_limiter[user_id] = []
        
        request_times = self.rate_limiter[user_id]
        
        # 清理过期的请求记录
        cutoff_time = current_time - window_size
        self.rate_limiter[user_id] = [
            t for t in request_times if t > cutoff_time
        ]
        
        # 检查是否超过限制
        if len(self.rate_limiter[user_id]) >= max_requests:
            return False
        
        # 记录当前请求
        self.rate_limiter[user_id].append(current_time)
        return True


class SecurityManager:
    """安全管理器"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.access_control = AccessControl(config)
        self.sessions: Dict[str, SecurityContext] = {}
        self.resources: Dict[str, SecurityResource] = {}
        
        # 添加默认策略
        self.access_control.add_policy(DefaultSecurityPolicy())
        
        # 启动清理任务
        if config.session_cleanup_interval > 0:
            asyncio.create_task(self._cleanup_expired_sessions())
    
    async def create_session(
        self, 
        user_id: str, 
        ip_address: str, 
        user_agent: str,
        permissions: Set[str] = None,
        roles: Set[str] = None,
        expires_in: Optional[timedelta] = None
    ) -> SecurityContext:
        """创建安全会话"""
        session_id = str(uuid.uuid4())
        
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + expires_in
        elif self.config.default_session_timeout > 0:
            expires_at = datetime.now() + timedelta(
                seconds=self.config.default_session_timeout
            )
        
        context = SecurityContext(
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            permissions=permissions or set(),
            roles=roles or set(),
            expires_at=expires_at
        )
        
        self.sessions[session_id] = context
        
        self.logger.info(
            f"创建安全会话: 用户 {user_id}, 会话 {session_id}, "
            f"过期时间 {expires_at}"
        )
        
        return context
    
    def get_session(self, session_id: str) -> Optional[SecurityContext]:
        """获取安全会话"""
        context = self.sessions.get(session_id)
        
        if context and context.is_expired:
            self.logger.info(f"会话已过期: {session_id}")
            self.sessions.pop(session_id, None)
            return None
        
        return context
    
    async def revoke_session(self, session_id: str) -> bool:
        """撤销安全会话"""
        if session_id in self.sessions:
            context = self.sessions.pop(session_id)
            self.logger.info(f"撤销会话: 用户 {context.user_id}, 会话 {session_id}")
            return True
        return False
    
    def register_resource(
        self, 
        resource_id: str, 
        resource_type: str, 
        owner_id: str,
        **kwargs
    ) -> SecurityResource:
        """注册安全资源"""
        resource = SecurityResource(
            resource_id=resource_id,
            resource_type=resource_type,
            owner_id=owner_id,
            **kwargs
        )
        
        self.resources[resource_id] = resource
        
        self.logger.debug(f"注册安全资源: {resource_id}, 类型: {resource_type}")
        return resource
    
    def get_resource(self, resource_id: str) -> Optional[SecurityResource]:
        """获取安全资源"""
        return self.resources.get(resource_id)
    
    async def check_permission(
        self, 
        session_id: str, 
        resource_id: str, 
        action: ActionType
    ) -> bool:
        """检查权限"""
        # 获取会话
        context = self.get_session(session_id)
        if not context:
            raise AuthenticationError("无效的会话")
        
        # 获取资源
        resource = self.get_resource(resource_id)
        if not resource:
            raise SecurityError(f"资源不存在: {resource_id}")
        
        # 检查访问权限
        return await self.access_control.check_access(context, resource, action)
    
    async def require_permission(
        self, 
        session_id: str, 
        resource_id: str, 
        action: ActionType
    ) -> None:
        """要求权限（失败时抛出异常）"""
        if not await self.check_permission(session_id, resource_id, action):
            raise AuthorizationError(
                f"权限不足: 会话 {session_id}, 资源 {resource_id}, 操作 {action.value}"
            )
    
    def add_security_policy(self, policy: SecurityPolicy) -> None:
        """添加安全策略"""
        self.access_control.add_policy(policy)
    
    async def _cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        while True:
            try:
                await asyncio.sleep(self.config.session_cleanup_interval)
                
                expired_sessions = [
                    session_id for session_id, context in self.sessions.items()
                    if context.is_expired
                ]
                
                for session_id in expired_sessions:
                    await self.revoke_session(session_id)
                
                if expired_sessions:
                    self.logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理过期会话失败: {e}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        active_sessions = len([
            c for c in self.sessions.values() if not c.is_expired
        ])
        
        expired_sessions = len([
            c for c in self.sessions.values() if c.is_expired
        ])
        
        return {
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'total_sessions': len(self.sessions),
            'registered_resources': len(self.resources),
            'security_policies': len(self.access_control.policies),
            'rate_limit_enabled': self.config.enable_rate_limiting,
            'session_timeout': self.config.default_session_timeout
        }


# 安全装饰器
def require_permission(resource_type: str, action: ActionType):
    """权限要求装饰器"""
    def decorator(func):
        async def wrapper(self, session_id: str, *args, **kwargs):
            # 假设第一个参数是资源ID
            resource_id = args[0] if args else kwargs.get('resource_id')
            if not resource_id:
                raise SecurityError("缺少资源ID")
            
            # 检查权限
            security_manager = getattr(self, 'security_manager', None)
            if security_manager:
                await security_manager.require_permission(
                    session_id, resource_id, action
                )
            
            return await func(self, session_id, *args, **kwargs)
        
        return wrapper
    return decorator


def security_audit(operation: str):
    """安全审计装饰器"""
    def decorator(func):
        async def wrapper(self, session_id: str, *args, **kwargs):
            start_time = time.time()
            success = False
            error_message = None
            
            try:
                result = await func(self, session_id, *args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_message = str(e)
                raise
            finally:
                # 记录审计日志
                audit_logger = getattr(self, 'audit_logger', None)
                if audit_logger:
                    elapsed_time = time.time() - start_time
                    # 这里应该调用审计记录功能
                    pass
        
        return wrapper
    return decorator