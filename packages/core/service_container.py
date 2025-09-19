"""
服务容器和依赖注入

提供统一的服务管理和依赖注入功能
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Dict, List, Optional, Union, Any, Type, 
    TypeVar, Generic, Callable, get_type_hints
)
import inspect
import weakref

from .file_transfer import FileTransferEngine, TransferConfig
from .progress_tracking import ProgressManager, ProgressConfig
from .compression import CompressionEngine, CompressionConfig
from .security import SecurityManager, SecurityConfig


T = TypeVar('T')


class ServiceScope(Enum):
    """服务作用域"""
    SINGLETON = "singleton"  # 单例
    TRANSIENT = "transient"  # 瞬时
    SCOPED = "scoped"        # 作用域


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    service_type: Type
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: ServiceScope = ServiceScope.SINGLETON
    dependencies: List[Type] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_factory(self) -> bool:
        return self.factory is not None
    
    @property
    def is_instance(self) -> bool:
        return self.instance is not None


class ServiceProvider(ABC):
    """服务提供者抽象基类"""
    
    @abstractmethod
    def get_service(self, service_type: Type[T]) -> T:
        """获取服务"""
        pass
    
    @abstractmethod
    def get_required_service(self, service_type: Type[T]) -> T:
        """获取必需服务（不存在时抛出异常）"""
        pass


class ServiceContainer(ServiceProvider):
    """服务容器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._building: set = set()  # 防止循环依赖
        self._scope_stack: List[str] = []
        
    def register_singleton(
        self, 
        service_type: Type[T], 
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None
    ) -> 'ServiceContainer':
        """注册单例服务"""
        return self._register_service(
            service_type, implementation_type, factory, instance, ServiceScope.SINGLETON
        )
    
    def register_transient(
        self, 
        service_type: Type[T], 
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'ServiceContainer':
        """注册瞬时服务"""
        return self._register_service(
            service_type, implementation_type, factory, None, ServiceScope.TRANSIENT
        )
    
    def register_scoped(
        self, 
        service_type: Type[T], 
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'ServiceContainer':
        """注册作用域服务"""
        return self._register_service(
            service_type, implementation_type, factory, None, ServiceScope.SCOPED
        )
    
    def _register_service(
        self,
        service_type: Type,
        implementation_type: Optional[Type] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        scope: ServiceScope = ServiceScope.SINGLETON
    ) -> 'ServiceContainer':
        """注册服务"""
        if sum(x is not None for x in [implementation_type, factory, instance]) != 1:
            raise ValueError("必须提供且仅提供一个: implementation_type, factory, 或 instance")
        
        # 分析依赖
        dependencies = []
        if implementation_type:
            dependencies = self._analyze_dependencies(implementation_type)
        elif factory:
            dependencies = self._analyze_dependencies(factory)
        
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            factory=factory,
            instance=instance,
            scope=scope,
            dependencies=dependencies
        )
        
        self._services[service_type] = descriptor
        
        self.logger.debug(
            f"注册服务: {service_type.__name__}, "
            f"实现: {implementation_type.__name__ if implementation_type else 'factory/instance'}, "
            f"作用域: {scope.value}"
        )
        
        return self
    
    def get_service(self, service_type: Type[T]) -> Optional[T]:
        """获取服务"""
        try:
            return self._resolve_service(service_type)
        except Exception as e:
            self.logger.error(f"获取服务失败: {service_type.__name__}, {e}")
            return None
    
    def get_required_service(self, service_type: Type[T]) -> T:
        """获取必需服务"""
        service = self.get_service(service_type)
        if service is None:
            raise ValueError(f"无法解析必需服务: {service_type.__name__}")
        return service
    
    def _resolve_service(self, service_type: Type[T]) -> T:
        """解析服务"""
        if service_type in self._building:
            raise RuntimeError(f"检测到循环依赖: {service_type.__name__}")
        
        descriptor = self._services.get(service_type)
        if not descriptor:
            raise ValueError(f"服务未注册: {service_type.__name__}")
        
        # 检查作用域缓存
        if descriptor.scope == ServiceScope.SINGLETON:
            if service_type in self._instances:
                return self._instances[service_type]
        elif descriptor.scope == ServiceScope.SCOPED:
            current_scope = self._get_current_scope()
            if current_scope and current_scope in self._scoped_instances:
                scoped_cache = self._scoped_instances[current_scope]
                if service_type in scoped_cache:
                    return scoped_cache[service_type]
        
        # 如果有预创建的实例
        if descriptor.is_instance:
            instance = descriptor.instance
        else:
            # 创建新实例
            self._building.add(service_type)
            try:
                instance = self._create_instance(descriptor)
            finally:
                self._building.discard(service_type)
        
        # 缓存实例
        if descriptor.scope == ServiceScope.SINGLETON:
            self._instances[service_type] = instance
        elif descriptor.scope == ServiceScope.SCOPED:
            current_scope = self._get_current_scope()
            if current_scope:
                if current_scope not in self._scoped_instances:
                    self._scoped_instances[current_scope] = {}
                self._scoped_instances[current_scope][service_type] = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例"""
        if descriptor.is_factory:
            # 使用工厂方法
            return self._invoke_factory(descriptor.factory)
        else:
            # 使用构造函数
            return self._invoke_constructor(descriptor.implementation_type)
    
    def _invoke_factory(self, factory: Callable) -> Any:
        """调用工厂方法"""
        dependencies = self._resolve_dependencies(factory)
        return factory(**dependencies)
    
    def _invoke_constructor(self, implementation_type: Type) -> Any:
        """调用构造函数"""
        dependencies = self._resolve_dependencies(implementation_type)
        return implementation_type(**dependencies)
    
    def _resolve_dependencies(self, target: Union[Type, Callable]) -> Dict[str, Any]:
        """解析依赖项"""
        signature = inspect.signature(target)
        dependencies = {}
        
        for param_name, param in signature.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                continue
            
            dependency_type = param.annotation
            dependency = self._resolve_service(dependency_type)
            dependencies[param_name] = dependency
        
        return dependencies
    
    def _analyze_dependencies(self, target: Union[Type, Callable]) -> List[Type]:
        """分析依赖类型"""
        signature = inspect.signature(target)
        dependencies = []
        
        for param in signature.parameters.values():
            if param.annotation != inspect.Parameter.empty:
                dependencies.append(param.annotation)
        
        return dependencies
    
    def _get_current_scope(self) -> Optional[str]:
        """获取当前作用域"""
        return self._scope_stack[-1] if self._scope_stack else None
    
    def create_scope(self, scope_name: Optional[str] = None) -> 'ServiceScope':
        """创建作用域"""
        if scope_name is None:
            scope_name = f"scope_{len(self._scoped_instances)}"
        
        return ServiceScopeContext(self, scope_name)
    
    def _enter_scope(self, scope_name: str) -> None:
        """进入作用域"""
        self._scope_stack.append(scope_name)
        if scope_name not in self._scoped_instances:
            self._scoped_instances[scope_name] = {}
    
    def _exit_scope(self, scope_name: str) -> None:
        """退出作用域"""
        if self._scope_stack and self._scope_stack[-1] == scope_name:
            self._scope_stack.pop()
        
        # 清理作用域缓存
        if scope_name in self._scoped_instances:
            scoped_cache = self._scoped_instances.pop(scope_name)
            
            # 清理资源
            for instance in scoped_cache.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception as e:
                        self.logger.warning(f"清理作用域实例失败: {e}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            'registered_services': len(self._services),
            'singleton_instances': len(self._instances),
            'scoped_caches': len(self._scoped_instances),
            'service_types': [t.__name__ for t in self._services.keys()]
        }


class ServiceScopeContext:
    """服务作用域上下文"""
    
    def __init__(self, container: ServiceContainer, scope_name: str):
        self.container = container
        self.scope_name = scope_name
    
    def __enter__(self) -> 'ServiceScopeContext':
        self.container._enter_scope(self.scope_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.container._exit_scope(self.scope_name)


class ConfigurationBuilder:
    """配置构建器"""
    
    def __init__(self):
        self.configurations: Dict[Type, Any] = {}
    
    def add_file_transfer_config(self, config: TransferConfig) -> 'ConfigurationBuilder':
        """添加文件传输配置"""
        self.configurations[TransferConfig] = config
        return self
    
    def add_progress_config(self, config: ProgressConfig) -> 'ConfigurationBuilder':
        """添加进度配置"""
        self.configurations[ProgressConfig] = config
        return self
    
    def add_compression_config(self, config: CompressionConfig) -> 'ConfigurationBuilder':
        """添加压缩配置"""
        self.configurations[CompressionConfig] = config
        return self
    
    def add_security_config(self, config: SecurityConfig) -> 'ConfigurationBuilder':
        """添加安全配置"""
        self.configurations[SecurityConfig] = config
        return self
    
    def build(self) -> Dict[Type, Any]:
        """构建配置"""
        return self.configurations.copy()


class ServiceCollectionExtensions:
    """服务集合扩展"""
    
    @staticmethod
    def add_file_transfer_services(
        container: ServiceContainer,
        config: Optional[TransferConfig] = None
    ) -> ServiceContainer:
        """添加文件传输服务"""
        if config is None:
            config = TransferConfig()
        
        container.register_singleton(TransferConfig, instance=config)
        container.register_singleton(FileTransferEngine, FileTransferEngine)
        
        return container
    
    @staticmethod
    def add_progress_services(
        container: ServiceContainer,
        config: Optional[ProgressConfig] = None
    ) -> ServiceContainer:
        """添加进度服务"""
        if config is None:
            config = ProgressConfig()
        
        container.register_singleton(ProgressConfig, instance=config)
        container.register_singleton(ProgressManager, ProgressManager)
        
        return container
    
    @staticmethod
    def add_compression_services(
        container: ServiceContainer,
        config: Optional[CompressionConfig] = None
    ) -> ServiceContainer:
        """添加压缩服务"""
        if config is None:
            config = CompressionConfig()
        
        container.register_singleton(CompressionConfig, instance=config)
        container.register_singleton(CompressionEngine, CompressionEngine)
        
        return container
    
    @staticmethod
    def add_security_services(
        container: ServiceContainer,
        config: Optional[SecurityConfig] = None
    ) -> ServiceContainer:
        """添加安全服务"""
        if config is None:
            config = SecurityConfig()
        
        container.register_singleton(SecurityConfig, instance=config)
        container.register_singleton(SecurityManager, SecurityManager)
        
        return container
    
    @staticmethod
    def add_all_core_services(
        container: ServiceContainer,
        transfer_config: Optional[TransferConfig] = None,
        progress_config: Optional[ProgressConfig] = None,
        compression_config: Optional[CompressionConfig] = None,
        security_config: Optional[SecurityConfig] = None
    ) -> ServiceContainer:
        """添加所有核心服务"""
        ServiceCollectionExtensions.add_file_transfer_services(container, transfer_config)
        ServiceCollectionExtensions.add_progress_services(container, progress_config)
        ServiceCollectionExtensions.add_compression_services(container, compression_config)
        ServiceCollectionExtensions.add_security_services(container, security_config)
        
        return container


class ServiceHost:
    """服务主机"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger(__name__)
        self._startup_tasks: List[Callable] = []
        self._shutdown_tasks: List[Callable] = []
        self._is_running = False
    
    def add_startup_task(self, task: Callable) -> 'ServiceHost':
        """添加启动任务"""
        self._startup_tasks.append(task)
        return self
    
    def add_shutdown_task(self, task: Callable) -> 'ServiceHost':
        """添加关闭任务"""
        self._shutdown_tasks.append(task)
        return self
    
    async def start_async(self) -> None:
        """异步启动服务主机"""
        if self._is_running:
            return
        
        self.logger.info("启动服务主机...")
        
        try:
            # 执行启动任务
            for task in self._startup_tasks:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            
            self._is_running = True
            self.logger.info("服务主机启动完成")
            
        except Exception as e:
            self.logger.error(f"服务主机启动失败: {e}")
            raise
    
    async def stop_async(self) -> None:
        """异步停止服务主机"""
        if not self._is_running:
            return
        
        self.logger.info("停止服务主机...")
        
        try:
            # 执行关闭任务（逆序）
            for task in reversed(self._shutdown_tasks):
                try:
                    if asyncio.iscoroutinefunction(task):
                        await task()
                    else:
                        task()
                except Exception as e:
                    self.logger.warning(f"关闭任务执行失败: {e}")
            
            self._is_running = False
            self.logger.info("服务主机已停止")
            
        except Exception as e:
            self.logger.error(f"服务主机停止失败: {e}")
            raise
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running
    
    def get_service(self, service_type: Type[T]) -> Optional[T]:
        """获取服务"""
        return self.container.get_service(service_type)
    
    def get_required_service(self, service_type: Type[T]) -> T:
        """获取必需服务"""
        return self.container.get_required_service(service_type)


# 便捷的构建器类
class HostBuilder:
    """主机构建器"""
    
    def __init__(self):
        self.container = ServiceContainer()
        self.startup_tasks: List[Callable] = []
        self.shutdown_tasks: List[Callable] = []
    
    def configure_services(self, configure: Callable[[ServiceContainer], None]) -> 'HostBuilder':
        """配置服务"""
        configure(self.container)
        return self
    
    def add_startup_task(self, task: Callable) -> 'HostBuilder':
        """添加启动任务"""
        self.startup_tasks.append(task)
        return self
    
    def add_shutdown_task(self, task: Callable) -> 'HostBuilder':
        """添加关闭任务"""
        self.shutdown_tasks.append(task)
        return self
    
    def build(self) -> ServiceHost:
        """构建服务主机"""
        host = ServiceHost(self.container)
        
        for task in self.startup_tasks:
            host.add_startup_task(task)
        
        for task in self.shutdown_tasks:
            host.add_shutdown_task(task)
        
        return host


# 默认配置函数
def create_default_host() -> ServiceHost:
    """创建默认服务主机"""
    return (HostBuilder()
            .configure_services(lambda services: 
                ServiceCollectionExtensions.add_all_core_services(services)
            )
            .build())


def create_file_transfer_host(
    transfer_config: Optional[TransferConfig] = None,
    progress_config: Optional[ProgressConfig] = None
) -> ServiceHost:
    """创建文件传输专用主机"""
    return (HostBuilder()
            .configure_services(lambda services: (
                ServiceCollectionExtensions.add_file_transfer_services(services, transfer_config),
                ServiceCollectionExtensions.add_progress_services(services, progress_config)
            ))
            .build())