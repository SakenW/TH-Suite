"""
服务容器模块测试

测试依赖注入、服务管理、配置等功能
"""

import asyncio
import pytest
from typing import Optional
from unittest.mock import MagicMock

from ..service_container import (
    ServiceContainer, ServiceScope, ServiceDescriptor, ServiceProvider,
    ServiceScopeContext, ConfigurationBuilder, ServiceCollectionExtensions,
    ServiceHost, HostBuilder, create_default_host
)
from ..file_transfer.config import TransferConfig
from ..progress_tracking.config import ProgressConfig
from ..compression.config import CompressionConfig
from ..security.config import SecurityConfig


# 测试用的服务类
class TestService:
    """测试服务"""
    
    def __init__(self, value: str = "default"):
        self.value = value
        self.disposed = False
    
    def get_value(self) -> str:
        return self.value
    
    def dispose(self):
        self.disposed = True


class DependentService:
    """依赖其他服务的测试服务"""
    
    def __init__(self, test_service: TestService):
        self.test_service = test_service
    
    def get_dependent_value(self) -> str:
        return f"Dependent: {self.test_service.get_value()}"


class ComplexService:
    """复杂依赖的测试服务"""
    
    def __init__(self, test_service: TestService, dependent_service: DependentService):
        self.test_service = test_service
        self.dependent_service = dependent_service
    
    def get_complex_value(self) -> str:
        return f"Complex: {self.dependent_service.get_dependent_value()}"


def test_service_factory() -> TestService:
    """测试服务工厂函数"""
    return TestService("from_factory")


class TestServiceDescriptor:
    """测试服务描述符"""
    
    def test_descriptor_creation(self):
        """测试描述符创建"""
        descriptor = ServiceDescriptor(
            service_type=TestService,
            implementation_type=TestService,
            scope=ServiceScope.SINGLETON
        )
        
        assert descriptor.service_type == TestService
        assert descriptor.implementation_type == TestService
        assert descriptor.scope == ServiceScope.SINGLETON
        assert not descriptor.is_factory
        assert not descriptor.is_instance
    
    def test_factory_descriptor(self):
        """测试工厂描述符"""
        descriptor = ServiceDescriptor(
            service_type=TestService,
            factory=test_service_factory,
            scope=ServiceScope.TRANSIENT
        )
        
        assert descriptor.is_factory
        assert not descriptor.is_instance
        assert descriptor.factory == test_service_factory
    
    def test_instance_descriptor(self):
        """测试实例描述符"""
        instance = TestService("singleton_instance")
        descriptor = ServiceDescriptor(
            service_type=TestService,
            instance=instance,
            scope=ServiceScope.SINGLETON
        )
        
        assert descriptor.is_instance
        assert not descriptor.is_factory
        assert descriptor.instance == instance


class TestServiceContainer:
    """测试服务容器"""
    
    def test_container_creation(self):
        """测试容器创建"""
        container = ServiceContainer()
        
        assert len(container._services) == 0
        assert len(container._instances) == 0
    
    def test_register_singleton(self):
        """测试注册单例服务"""
        container = ServiceContainer()
        
        container.register_singleton(TestService, TestService)
        
        assert TestService in container._services
        descriptor = container._services[TestService]
        assert descriptor.scope == ServiceScope.SINGLETON
        assert descriptor.implementation_type == TestService
    
    def test_register_transient(self):
        """测试注册瞬时服务"""
        container = ServiceContainer()
        
        container.register_transient(TestService, TestService)
        
        descriptor = container._services[TestService]
        assert descriptor.scope == ServiceScope.TRANSIENT
    
    def test_register_with_factory(self):
        """测试使用工厂注册"""
        container = ServiceContainer()
        
        container.register_singleton(TestService, factory=test_service_factory)
        
        descriptor = container._services[TestService]
        assert descriptor.is_factory
        assert descriptor.factory == test_service_factory
    
    def test_register_with_instance(self):
        """测试使用实例注册"""
        container = ServiceContainer()
        instance = TestService("pre_created")
        
        container.register_singleton(TestService, instance=instance)
        
        descriptor = container._services[TestService]
        assert descriptor.is_instance
        assert descriptor.instance == instance
    
    def test_invalid_registration(self):
        """测试无效注册"""
        container = ServiceContainer()
        
        # 必须提供且仅提供一个参数
        with pytest.raises(ValueError, match="必须提供且仅提供一个"):
            container.register_singleton(TestService)
        
        with pytest.raises(ValueError, match="必须提供且仅提供一个"):
            container.register_singleton(
                TestService,
                implementation_type=TestService,
                factory=test_service_factory
            )
    
    def test_resolve_singleton(self):
        """测试解析单例服务"""
        container = ServiceContainer()
        container.register_singleton(TestService, TestService)
        
        # 第一次解析
        service1 = container.get_service(TestService)
        assert service1 is not None
        assert isinstance(service1, TestService)
        
        # 第二次解析应该返回同一个实例
        service2 = container.get_service(TestService)
        assert service1 is service2
    
    def test_resolve_transient(self):
        """测试解析瞬时服务"""
        container = ServiceContainer()
        container.register_transient(TestService, TestService)
        
        # 每次解析应该返回新实例
        service1 = container.get_service(TestService)
        service2 = container.get_service(TestService)
        
        assert service1 is not service2
        assert isinstance(service1, TestService)
        assert isinstance(service2, TestService)
    
    def test_resolve_with_factory(self):
        """测试使用工厂解析"""
        container = ServiceContainer()
        container.register_singleton(TestService, factory=test_service_factory)
        
        service = container.get_service(TestService)
        assert service is not None
        assert service.value == "from_factory"
    
    def test_resolve_with_instance(self):
        """测试使用实例解析"""
        container = ServiceContainer()
        instance = TestService("pre_created")
        container.register_singleton(TestService, instance=instance)
        
        service = container.get_service(TestService)
        assert service is instance
    
    def test_resolve_unregistered_service(self):
        """测试解析未注册的服务"""
        container = ServiceContainer()
        
        service = container.get_service(TestService)
        assert service is None
    
    def test_get_required_service(self):
        """测试获取必需服务"""
        container = ServiceContainer()
        container.register_singleton(TestService, TestService)
        
        # 注册的服务应该正常返回
        service = container.get_required_service(TestService)
        assert service is not None
        
        # 未注册的服务应该抛出异常
        with pytest.raises(ValueError, match="无法解析必需服务"):
            container.get_required_service(DependentService)
    
    def test_dependency_injection(self):
        """测试依赖注入"""
        container = ServiceContainer()
        
        # 注册依赖服务
        container.register_singleton(TestService, TestService)
        container.register_singleton(DependentService, DependentService)
        
        # 解析依赖服务
        dependent_service = container.get_service(DependentService)
        assert dependent_service is not None
        assert isinstance(dependent_service.test_service, TestService)
    
    def test_complex_dependency_chain(self):
        """测试复杂依赖链"""
        container = ServiceContainer()
        
        # 注册依赖链
        container.register_singleton(TestService, TestService)
        container.register_singleton(DependentService, DependentService)
        container.register_singleton(ComplexService, ComplexService)
        
        # 解析复杂服务
        complex_service = container.get_service(ComplexService)
        assert complex_service is not None
        assert isinstance(complex_service.test_service, TestService)
        assert isinstance(complex_service.dependent_service, DependentService)
        
        # 验证依赖关系
        value = complex_service.get_complex_value()
        assert "Complex: Dependent: default" in value
    
    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        # 这个测试需要特殊的类来模拟循环依赖
        # 在实际项目中应该避免循环依赖
        pass
    
    def test_scoped_services(self):
        """测试作用域服务"""
        container = ServiceContainer()
        container.register_scoped(TestService, TestService)
        
        # 在作用域外解析应该创建新实例
        service1 = container.get_service(TestService)
        service2 = container.get_service(TestService)
        assert service1 is not service2
        
        # 在同一作用域内应该返回同一实例
        with container.create_scope("test_scope"):
            scoped_service1 = container.get_service(TestService)
            scoped_service2 = container.get_service(TestService)
            assert scoped_service1 is scoped_service2
        
        # 不同作用域应该有不同实例
        with container.create_scope("another_scope"):
            another_service = container.get_service(TestService)
            assert another_service is not scoped_service1
    
    def test_scope_cleanup(self):
        """测试作用域清理"""
        container = ServiceContainer()
        container.register_scoped(TestService, TestService)
        
        scope_name = "cleanup_test"
        
        # 在作用域内创建服务
        with container.create_scope(scope_name):
            service = container.get_service(TestService)
            assert service is not None
        
        # 作用域退出后应该清理缓存
        assert scope_name not in container._scoped_instances
    
    def test_service_info(self):
        """测试服务信息"""
        container = ServiceContainer()
        container.register_singleton(TestService, TestService)
        container.register_transient(DependentService, DependentService)
        
        info = container.get_service_info()
        
        assert info['registered_services'] == 2
        assert TestService.__name__ in info['service_types']
        assert DependentService.__name__ in info['service_types']


class TestServiceScopeContext:
    """测试服务作用域上下文"""
    
    def test_scope_context(self):
        """测试作用域上下文"""
        container = ServiceContainer()
        scope_name = "test_scope"
        
        # 使用上下文管理器
        with ServiceScopeContext(container, scope_name):
            assert scope_name in container._scope_stack
        
        # 退出后应该清理
        assert scope_name not in container._scope_stack


class TestConfigurationBuilder:
    """测试配置构建器"""
    
    def test_builder_creation(self):
        """测试构建器创建"""
        builder = ConfigurationBuilder()
        assert len(builder.configurations) == 0
    
    def test_add_configurations(self):
        """测试添加配置"""
        builder = ConfigurationBuilder()
        
        transfer_config = TransferConfig()
        progress_config = ProgressConfig()
        
        configs = (builder
                  .add_file_transfer_config(transfer_config)
                  .add_progress_config(progress_config)
                  .build())
        
        assert TransferConfig in configs
        assert ProgressConfig in configs
        assert configs[TransferConfig] == transfer_config
        assert configs[ProgressConfig] == progress_config


class TestServiceCollectionExtensions:
    """测试服务集合扩展"""
    
    def test_add_file_transfer_services(self):
        """测试添加文件传输服务"""
        container = ServiceContainer()
        
        ServiceCollectionExtensions.add_file_transfer_services(container)
        
        assert TransferConfig in container._services
        # FileTransferEngine 需要实际存在才能测试
        # assert FileTransferEngine in container._services
    
    def test_add_progress_services(self):
        """测试添加进度服务"""
        container = ServiceContainer()
        
        ServiceCollectionExtensions.add_progress_services(container)
        
        assert ProgressConfig in container._services
        # ProgressManager 需要实际存在才能测试
        # assert ProgressManager in container._services
    
    def test_add_all_core_services(self):
        """测试添加所有核心服务"""
        container = ServiceContainer()
        
        ServiceCollectionExtensions.add_all_core_services(container)
        
        # 验证配置服务已注册
        assert TransferConfig in container._services
        assert ProgressConfig in container._services
        assert CompressionConfig in container._services
        assert SecurityConfig in container._services


class TestServiceHost:
    """测试服务主机"""
    
    def test_host_creation(self):
        """测试主机创建"""
        container = ServiceContainer()
        host = ServiceHost(container)
        
        assert host.container == container
        assert not host.is_running
    
    @pytest.mark.asyncio
    async def test_startup_and_shutdown(self):
        """测试启动和关闭"""
        container = ServiceContainer()
        host = ServiceHost(container)
        
        startup_called = False
        shutdown_called = False
        
        def startup_task():
            nonlocal startup_called
            startup_called = True
        
        def shutdown_task():
            nonlocal shutdown_called
            shutdown_called = True
        
        host.add_startup_task(startup_task)
        host.add_shutdown_task(shutdown_task)
        
        # 启动
        await host.start_async()
        assert host.is_running
        assert startup_called
        
        # 关闭
        await host.stop_async()
        assert not host.is_running
        assert shutdown_called
    
    @pytest.mark.asyncio
    async def test_async_tasks(self):
        """测试异步任务"""
        container = ServiceContainer()
        host = ServiceHost(container)
        
        async_startup_called = False
        async_shutdown_called = False
        
        async def async_startup_task():
            nonlocal async_startup_called
            async_startup_called = True
        
        async def async_shutdown_task():
            nonlocal async_shutdown_called
            async_shutdown_called = True
        
        host.add_startup_task(async_startup_task)
        host.add_shutdown_task(async_shutdown_task)
        
        await host.start_async()
        assert async_startup_called
        
        await host.stop_async()
        assert async_shutdown_called
    
    def test_get_services(self):
        """测试获取服务"""
        container = ServiceContainer()
        container.register_singleton(TestService, TestService)
        
        host = ServiceHost(container)
        
        # 获取服务
        service = host.get_service(TestService)
        assert service is not None
        
        # 获取必需服务
        required_service = host.get_required_service(TestService)
        assert required_service is not None
        
        # 获取不存在的服务
        nonexistent = host.get_service(DependentService)
        assert nonexistent is None


class TestHostBuilder:
    """测试主机构建器"""
    
    def test_builder_creation(self):
        """测试构建器创建"""
        builder = HostBuilder()
        
        assert builder.container is not None
        assert len(builder.startup_tasks) == 0
        assert len(builder.shutdown_tasks) == 0
    
    def test_configure_services(self):
        """测试配置服务"""
        builder = HostBuilder()
        
        def configure(services: ServiceContainer):
            services.register_singleton(TestService, TestService)
        
        builder.configure_services(configure)
        
        # 验证服务已配置
        assert TestService in builder.container._services
    
    def test_add_tasks(self):
        """测试添加任务"""
        builder = HostBuilder()
        
        def startup_task():
            pass
        
        def shutdown_task():
            pass
        
        builder.add_startup_task(startup_task)
        builder.add_shutdown_task(shutdown_task)
        
        assert len(builder.startup_tasks) == 1
        assert len(builder.shutdown_tasks) == 1
    
    def test_build_host(self):
        """测试构建主机"""
        builder = HostBuilder()
        
        def startup_task():
            pass
        
        def shutdown_task():
            pass
        
        def configure(services: ServiceContainer):
            services.register_singleton(TestService, TestService)
        
        host = (builder
                .configure_services(configure)
                .add_startup_task(startup_task)
                .add_shutdown_task(shutdown_task)
                .build())
        
        assert isinstance(host, ServiceHost)
        assert TestService in host.container._services


class TestDefaultHostFactory:
    """测试默认主机工厂"""
    
    def test_create_default_host(self):
        """测试创建默认主机"""
        host = create_default_host()
        
        assert isinstance(host, ServiceHost)
        assert isinstance(host.container, ServiceContainer)
        
        # 验证核心服务已注册
        container = host.container
        assert TransferConfig in container._services
        assert ProgressConfig in container._services
        assert CompressionConfig in container._services
        assert SecurityConfig in container._services


@pytest.mark.asyncio
async def test_integration_service_container_workflow():
    """集成测试：完整的服务容器工作流程"""
    
    # 1. 创建并配置主机
    host = (HostBuilder()
            .configure_services(lambda services: (
                services.register_singleton(TestService, TestService),
                services.register_transient(DependentService, DependentService),
                ServiceCollectionExtensions.add_all_core_services(services)
            ))
            .add_startup_task(lambda: print("启动任务执行"))
            .add_shutdown_task(lambda: print("关闭任务执行"))
            .build())
    
    # 2. 启动主机
    await host.start_async()
    assert host.is_running
    
    # 3. 使用服务
    test_service = host.get_required_service(TestService)
    assert test_service is not None
    assert test_service.get_value() == "default"
    
    dependent_service = host.get_required_service(DependentService)
    assert dependent_service is not None
    assert "Dependent: default" in dependent_service.get_dependent_value()
    
    # 4. 验证单例行为
    another_test_service = host.get_service(TestService)
    assert test_service is another_test_service
    
    # 5. 验证瞬时行为
    another_dependent_service = host.get_service(DependentService)
    assert dependent_service is not another_dependent_service
    
    # 6. 使用作用域
    with host.container.create_scope("integration_test"):
        scoped_service1 = host.get_service(TestService)
        scoped_service2 = host.get_service(TestService)
        assert scoped_service1 is scoped_service2  # 在同一作用域内是同一实例
    
    # 7. 获取配置服务
    transfer_config = host.get_service(TransferConfig)
    assert transfer_config is not None
    assert isinstance(transfer_config, TransferConfig)
    
    progress_config = host.get_service(ProgressConfig)
    assert progress_config is not None
    assert isinstance(progress_config, ProgressConfig)
    
    # 8. 获取服务信息
    info = host.container.get_service_info()
    assert info['registered_services'] >= 6  # 至少有我们注册的服务
    
    # 9. 关闭主机
    await host.stop_async()
    assert not host.is_running


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])