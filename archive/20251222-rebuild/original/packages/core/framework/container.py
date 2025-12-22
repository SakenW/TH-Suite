"""
IoC容器（依赖注入容器）

提供完整的服务管理与生命周期管理，支持：
- 服务注册和解析
- 生命周期管理（单例、瞬态、作用域）
- 自动依赖注入
- 接口绑定和实现
"""

import inspect
import threading
from collections.abc import Callable
from contextlib import contextmanager
from enum import Enum
from typing import Any, TypeVar, get_type_hints

T = TypeVar("T")


class ServiceLifetime(Enum):
    """服务生命周期"""

    SINGLETON = "singleton"  # 单例
    TRANSIENT = "transient"  # 瞬态（每次创建新实例）
    SCOPED = "scoped"  # 作用域（在作用域内单例）


class ServiceDescriptor:
    """服务描述符"""

    def __init__(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime

        if not any([implementation, factory, instance]):
            raise ValueError("必须提供implementation、factory或instance中的一个")


class ServiceScope:
    """服务作用域"""

    def __init__(self):
        self._scoped_instances: dict[type, Any] = {}
        self._disposed = False

    def get_scoped_instance(self, service_type: type[T]) -> T | None:
        """获取作用域实例"""
        return self._scoped_instances.get(service_type)

    def set_scoped_instance(self, service_type: type[T], instance: T) -> None:
        """设置作用域实例"""
        self._scoped_instances[service_type] = instance

    def dispose(self) -> None:
        """释放作用域资源"""
        if self._disposed:
            return

        for instance in self._scoped_instances.values():
            if hasattr(instance, "dispose"):
                instance.dispose()

        self._scoped_instances.clear()
        self._disposed = True


class IoCContainer:
    """依赖注入容器"""

    def __init__(self):
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        self._lock = threading.RLock()
        self._current_scope: ServiceScope | None = None

    def register(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> "IoCContainer":
        """注册服务"""
        with self._lock:
            if instance is not None:
                # 如果提供了实例，强制使用单例生命周期
                lifetime = ServiceLifetime.SINGLETON

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation=implementation,
                factory=factory,
                instance=instance,
                lifetime=lifetime,
            )

            self._services[service_type] = descriptor

            # 如果是预创建的实例，直接存储为单例
            if instance is not None:
                self._singletons[service_type] = instance

        return self

    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
    ) -> "IoCContainer":
        """注册单例服务"""
        return self.register(
            service_type, implementation, factory, instance, ServiceLifetime.SINGLETON
        )

    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "IoCContainer":
        """注册瞬态服务"""
        return self.register(
            service_type, implementation, factory, None, ServiceLifetime.TRANSIENT
        )

    def register_scoped(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "IoCContainer":
        """注册作用域服务"""
        return self.register(
            service_type, implementation, factory, None, ServiceLifetime.SCOPED
        )

    def resolve(self, service_type: type[T]) -> T:
        """解析服务"""
        with self._lock:
            if service_type not in self._services:
                # 尝试自动注册具体类
                if not inspect.isabstract(service_type):
                    self.register_transient(service_type, service_type)
                else:
                    raise ValueError(f"服务类型 {service_type} 未注册")

            descriptor = self._services[service_type]

            # 处理不同生命周期
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                return self._get_singleton(descriptor)
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                return self._get_scoped(descriptor)
            else:  # TRANSIENT
                return self._create_instance(descriptor)

    def _get_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """获取单例实例"""
        if descriptor.service_type in self._singletons:
            return self._singletons[descriptor.service_type]

        instance = self._create_instance(descriptor)
        self._singletons[descriptor.service_type] = instance
        return instance

    def _get_scoped(self, descriptor: ServiceDescriptor) -> Any:
        """获取作用域实例"""
        if self._current_scope is None:
            raise RuntimeError("没有活动的服务作用域")

        instance = self._current_scope.get_scoped_instance(descriptor.service_type)
        if instance is None:
            instance = self._create_instance(descriptor)
            self._current_scope.set_scoped_instance(descriptor.service_type, instance)

        return instance

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例"""
        if descriptor.instance is not None:
            return descriptor.instance

        if descriptor.factory is not None:
            return descriptor.factory()

        if descriptor.implementation is not None:
            return self._create_with_di(descriptor.implementation)

        raise ValueError(f"无法创建服务实例: {descriptor.service_type}")

    def _create_with_di(self, implementation_type: type[T]) -> T:
        """使用依赖注入创建实例"""
        try:
            # 获取构造函数签名
            signature = inspect.signature(implementation_type.__init__)
            parameters = signature.parameters

            # 跳过self参数
            param_names = [name for name in parameters.keys() if name != "self"]

            if not param_names:
                # 无参构造函数
                return implementation_type()

            # 获取类型注解
            type_hints = get_type_hints(implementation_type.__init__)

            # 解析依赖
            kwargs = {}
            for param_name in param_names:
                param = parameters[param_name]

                # 获取参数类型
                param_type = type_hints.get(param_name)
                if param_type is None:
                    param_type = param.annotation

                if param_type == inspect.Parameter.empty:
                    if param.default != inspect.Parameter.empty:
                        # 有默认值，跳过
                        continue
                    else:
                        raise ValueError(f"参数 {param_name} 没有类型注解且无默认值")

                # 递归解析依赖
                kwargs[param_name] = self.resolve(param_type)

            return implementation_type(**kwargs)

        except Exception as e:
            raise RuntimeError(f"创建实例 {implementation_type} 失败: {e}")

    @contextmanager
    def create_scope(self):
        """创建服务作用域"""
        scope = ServiceScope()
        old_scope = self._current_scope

        try:
            self._current_scope = scope
            yield scope
        finally:
            self._current_scope = old_scope
            scope.dispose()

    def is_registered(self, service_type: type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services

    def clear(self) -> None:
        """清除所有注册的服务"""
        with self._lock:
            # 释放单例资源
            for instance in self._singletons.values():
                if hasattr(instance, "dispose"):
                    instance.dispose()

            self._services.clear()
            self._singletons.clear()
