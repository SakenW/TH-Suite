"""
Core Platform 集成测试

验证整个Core Platform的各个组件能够正确集成和工作
"""

import asyncio
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from packages.core.application.commands.command import BaseCommandHandler, Command
from packages.core.application.queries.query import BaseQueryHandler, Query
from packages.core.data.models.aggregate import AggregateRoot
from packages.core.data.models.base_entity import BaseEntity
from packages.core.data.models.value_object import EmailAddress
from packages.core.framework.cache.decorators import cached
from packages.core.framework.events.decorators import event_handler, publish_event
from packages.core.framework.tasks.decorators import background_task

# 导入Core Platform组件
from packages.core.platform import CorePlatform


class TestEntity(BaseEntity):
    """测试实体"""

    def __init__(self, name: str, email: str = None, entity_id: str = None):
        super().__init__(entity_id)
        self.name = name
        self.email = EmailAddress(email) if email else None


class TestAggregate(AggregateRoot):
    """测试聚合根"""

    def __init__(self, title: str, entity_id: str = None):
        super().__init__(entity_id)
        self.title = title
        self.items: list = []

    def add_item(self, item: str) -> None:
        """添加项目"""
        self.items.append(item)
        self.mark_updated()
        self._track_change(f"added_item:{item}")

        # 发布领域事件
        from packages.core.framework.events.event_bus import Event

        event = Event(
            event_type="test.item.added",
            timestamp=datetime.now(),
            source="TestAggregate",
            data={"aggregate_id": self.id, "item": item},
        )
        self.add_domain_event(event)


class CreateTestCommand(Command):
    """创建测试命令"""

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title


class GetTestQuery(Query):
    """获取测试查询"""

    def __init__(self, test_id: str, **kwargs):
        super().__init__(**kwargs)
        self.test_id = test_id


class TestCommandHandler(BaseCommandHandler[CreateTestCommand]):
    """测试命令处理器"""

    def __init__(self):
        super().__init__()
        self.executed_commands = []

    async def execute(self, command: CreateTestCommand) -> str:
        """执行命令"""
        self.executed_commands.append(command)
        return f"Created: {command.title}"


class TestQueryHandler(BaseQueryHandler[GetTestQuery, dict]):
    """测试查询处理器"""

    def __init__(self):
        super().__init__()
        self.executed_queries = []

    async def execute(self, query: GetTestQuery) -> dict:
        """执行查询"""
        self.executed_queries.append(query)
        return {"id": query.test_id, "data": "test_data"}


@pytest.fixture
async def temp_dir():
    """临时目录fixture"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
async def platform(temp_dir):
    """Core Platform fixture"""
    # 设置临时配置
    import os

    os.environ["TH_DATA_DIR"] = str(temp_dir / "data")
    os.environ["TH_LOG_DIR"] = str(temp_dir / "logs")
    os.environ["TH_CACHE_DIR"] = str(temp_dir / "cache")

    platform = CorePlatform("test-app")
    await platform.initialize()

    yield platform

    await platform.shutdown()


class TestCorePlatformIntegration:
    """Core Platform 集成测试"""

    @pytest.mark.asyncio
    async def test_platform_initialization(self, platform):
        """测试平台初始化"""
        assert platform is not None
        assert platform.app_name == "test-app"
        assert platform.container is not None
        assert platform.config_manager is not None
        assert platform.event_bus is not None
        assert platform.cache_manager is not None
        assert platform.task_manager is not None
        assert platform.task_scheduler is not None

    @pytest.mark.asyncio
    async def test_dependency_injection(self, platform):
        """测试依赖注入"""

        # 注册测试服务
        class TestService:
            def get_name(self):
                return "test_service"

        class TestClient:
            def __init__(self, service: TestService):
                self.service = service

        # 注册到容器
        platform.container.register_singleton(TestService, TestService())
        platform.container.register_transient(TestClient, TestClient)

        # 解析服务
        client = platform.container.resolve(TestClient)

        assert client is not None
        assert client.service is not None
        assert client.service.get_name() == "test_service"

    @pytest.mark.asyncio
    async def test_configuration_system(self, platform):
        """测试配置系统"""
        # 设置配置
        platform.config_manager.set_value("test_key", "test_value")

        # 获取配置
        value = platform.config_manager.get_value("test_key")
        assert value == "test_value"

        # 测试Settings
        settings = platform.config_manager.get_settings()
        assert settings is not None

        app_name = platform.config_manager.get_setting("app_name")
        assert app_name == "TH-Suite"  # 默认值

    @pytest.mark.asyncio
    async def test_logging_system(self, platform):
        """测试日志系统"""
        logger = platform.logger

        # 测试各种日志级别
        logger.info("测试信息日志")
        logger.warning("测试警告日志")
        logger.error("测试错误日志", exception=Exception("测试异常"))

        # 日志应该正常工作，不抛出异常
        assert True

    @pytest.mark.asyncio
    async def test_cache_system(self, platform):
        """测试缓存系统"""
        cache = platform.cache_manager

        # 测试基本缓存操作
        cache.set("test_key", "test_value", ttl=60)

        value = cache.get("test_key")
        assert value == "test_value"

        exists = cache.exists("test_key")
        assert exists is True

        # 测试缓存装饰器
        call_count = 0

        @cached(ttl=60)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * x

        # 第一次调用
        result1 = expensive_function(5)
        assert result1 == 25
        assert call_count == 1

        # 第二次调用（应该从缓存获取）
        result2 = expensive_function(5)
        assert result2 == 25
        assert call_count == 1  # 计数不应该增加

    @pytest.mark.asyncio
    async def test_event_system(self, platform):
        """测试事件系统"""

        # 事件处理器
        received_events = []

        @event_handler("test.event")
        def handle_test_event(event):
            received_events.append(event)

        # 发布事件
        publish_event("test.event", {"message": "Hello World"})

        # 给事件处理一点时间
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "test.event"
        assert received_events[0].data["message"] == "Hello World"

    @pytest.mark.asyncio
    async def test_task_system(self, platform):
        """测试任务系统"""
        task_manager = platform.task_manager

        # 提交后台任务
        @background_task(name="test_task")
        async def test_task(message: str) -> str:
            await asyncio.sleep(0.1)
            return f"Processed: {message}"

        # 提交任务
        task_id = await test_task.submit("Hello World")

        # 等待任务完成
        result = await task_manager.wait_for_task(task_id, timeout=5.0)

        assert result is not None
        assert result.result == "Processed: Hello World"

    @pytest.mark.asyncio
    async def test_domain_models(self, platform):
        """测试领域模型"""
        # 测试实体
        entity = TestEntity("John Doe", "john@example.com")
        assert entity.name == "John Doe"
        assert entity.email.email == "john@example.com"
        assert entity.id is not None

        # 测试聚合根
        aggregate = TestAggregate("Test Aggregate")
        assert aggregate.title == "Test Aggregate"
        assert aggregate.version == 0

        # 添加项目
        aggregate.add_item("Item 1")
        assert len(aggregate.items) == 1
        assert aggregate.version == 1
        assert "added_item:Item 1" in aggregate.get_changes()

        # 检查领域事件
        events = aggregate.get_domain_events()
        assert len(events) == 1
        assert events[0].event_type == "test.item.added"

    @pytest.mark.asyncio
    async def test_cqrs_pattern(self, platform):
        """测试CQRS模式"""
        from packages.core.application.commands.command import CommandBus
        from packages.core.application.queries.query import QueryBus

        # 创建命令和查询总线
        command_bus = CommandBus()
        query_bus = QueryBus()

        # 注册处理器
        command_handler = TestCommandHandler()
        query_handler = TestQueryHandler()

        command_bus.register_handler(CreateTestCommand, command_handler)
        query_bus.register_handler(GetTestQuery, query_handler)

        # 执行命令
        command = CreateTestCommand("Test Title")
        result = await command_bus.send(command)

        assert result == "Created: Test Title"
        assert len(command_handler.executed_commands) == 1

        # 执行查询
        query = GetTestQuery("test_id_123")
        result = await query_bus.send(query)

        assert result["id"] == "test_id_123"
        assert result["data"] == "test_data"
        assert len(query_handler.executed_queries) == 1

    @pytest.mark.asyncio
    async def test_storage_system(self, platform):
        """测试存储系统"""
        from packages.core.infrastructure.storage.storage_manager import (
            LocalStorageProvider,
            StorageManager,
        )

        # 创建存储管理器
        storage_manager = StorageManager()

        # 添加本地存储提供者
        temp_storage = Path(tempfile.mkdtemp())
        local_provider = LocalStorageProvider(temp_storage)
        storage_manager.register_provider("local", local_provider, is_default=True)

        try:
            # 测试文本存储
            await storage_manager.put_text("test.txt", "Hello World")

            # 读取文本
            text = await storage_manager.get_text("test.txt")
            assert text == "Hello World"

            # 测试JSON存储
            test_data = {"name": "test", "value": 123}
            await storage_manager.put_json("test.json", test_data)

            # 读取JSON
            json_data = await storage_manager.get_json("test.json")
            assert json_data["name"] == "test"
            assert json_data["value"] == 123

            # 测试列表键
            keys = await storage_manager.list_keys()
            assert "test.txt" in keys
            assert "test.json" in keys

        finally:
            shutil.rmtree(temp_storage, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_value_objects(self, platform):
        """测试值对象"""
        # 测试邮箱地址
        email1 = EmailAddress("test@example.com")
        email2 = EmailAddress("test@example.com")
        email3 = EmailAddress("other@example.com")

        # 值对象相等性
        assert email1 == email2
        assert email1 != email3

        # 哈希一致性
        assert hash(email1) == hash(email2)

        # 不可变性
        with pytest.raises(AttributeError):
            email1.email = "changed@example.com"


if __name__ == "__main__":
    # 运行单个测试
    async def run_single_test():
        temp_path = Path(tempfile.mkdtemp())

        try:
            # 设置环境变量
            import os

            os.environ["TH_DATA_DIR"] = str(temp_path / "data")
            os.environ["TH_LOG_DIR"] = str(temp_path / "logs")
            os.environ["TH_CACHE_DIR"] = str(temp_path / "cache")

            # 创建和初始化平台
            platform = CorePlatform("test-app")
            await platform.initialize()

            try:
                print("🚀 Core Platform 集成测试开始...")

                # 运行基本测试
                test_instance = TestCorePlatformIntegration()

                await test_instance.test_platform_initialization(platform)
                print("✅ 平台初始化测试通过")

                await test_instance.test_cache_system(platform)
                print("✅ 缓存系统测试通过")

                await test_instance.test_event_system(platform)
                print("✅ 事件系统测试通过")

                await test_instance.test_task_system(platform)
                print("✅ 任务系统测试通过")

                await test_instance.test_domain_models(platform)
                print("✅ 领域模型测试通过")

                await test_instance.test_value_objects(platform)
                print("✅ 值对象测试通过")

                print("🎉 所有测试通过！Core Platform 工作正常！")

            finally:
                await platform.shutdown()

        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    # 运行测试
    asyncio.run(run_single_test())
