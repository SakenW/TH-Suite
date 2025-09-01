"""
Core Platform 集成示例

展示如何使用完整的Core Platform架构
"""

import asyncio
from pathlib import Path

# Core Platform 导入
from .framework import (
    CacheManager,
    ConfigManager,
    EventBus,
    IoCContainer,
    TaskManager,
    TaskScheduler,
)
from .framework.cache.providers import FileCacheProvider, MemoryCacheProvider
from .framework.config.providers import (
    EnvironmentConfigProvider,
    FileConfigProvider,
    UserConfigProvider,
)
from .framework.events.decorators import event_handler, set_global_event_bus
from .framework.logging import StructLogFactory, setup_logging
from .framework.tasks.decorators import background_task, set_global_task_manager


class CorePlatform:
    """Core Platform 主类"""

    def __init__(self, app_name: str = "TH-Suite"):
        self.app_name = app_name
        self.container = IoCContainer()
        self.config_manager = ConfigManager()
        self.event_bus = EventBus()
        self.cache_manager = CacheManager()
        self.task_manager = TaskManager()
        self.task_scheduler = TaskScheduler(self.task_manager)

        # 先初始化 structlog 系统，然后获取日志器
        StructLogFactory.initialize_logging(
            log_level="INFO",
            log_format="console",
            service=app_name.lower().replace("-", "_"),
        )
        self.logger = StructLogFactory.get_logger("core_platform")

        # 设置全局实例
        self._setup_global_instances()

    def _setup_global_instances(self):
        """设置全局实例"""
        # 设置全局事件总线
        set_global_event_bus(self.event_bus)

        # 设置全局任务管理器
        set_global_task_manager(self.task_manager)

    async def initialize(self):
        """初始化Core Platform"""
        try:
            # 1. 配置系统初始化
            await self._initialize_config()

            # 2. 日志系统初始化
            await self._initialize_logging()

            # 3. 缓存系统初始化
            await self._initialize_cache()

            # 4. 依赖注入容器初始化
            await self._initialize_container()

            # 5. 任务系统初始化
            await self._initialize_tasks()

            self.logger.info("Core Platform 初始化完成")

            # 发布系统启动事件
            from datetime import datetime

            from .framework.events.event_bus import Event
            from .framework.events.event_handler import EventTypes

            startup_event = Event(
                event_type=EventTypes.SYSTEM_STARTUP,
                timestamp=datetime.now(),
                source="core_platform",
                data={"app_name": self.app_name},
            )
            self.event_bus.publish(startup_event)

        except Exception as e:
            self.logger.error("Core Platform 初始化失败", exception=e)
            raise

    async def _initialize_config(self):
        """初始化配置系统"""
        # 添加配置提供者（优先级从低到高）
        self.config_manager.add_provider(
            FileConfigProvider(Path("config.yaml"), priority=30)
        )
        self.config_manager.add_provider(UserConfigProvider(Path.home() / ".th-suite"))
        self.config_manager.add_provider(EnvironmentConfigProvider("TH_"))

        # 加载配置
        self.config_manager.load_config()

        # 启用自动重载
        self.config_manager.set_auto_reload(True, interval=60)

    async def _initialize_logging(self):
        """初始化日志系统"""
        # structlog 系统已经在构造函数中初始化
        # 这里可以根据配置进行调整，例如切换到 JSON 格式或调整日志级别

        log_format = self.config_manager.get_setting("log_format") or "console"
        log_level = self.config_manager.get_setting("log_level") or "INFO"

        # 如果配置与初始设置不同，重新初始化
        if log_format != "console" or log_level != "INFO":
            setup_logging(
                log_level=log_level,
                log_format=log_format,
                service=self.app_name.lower().replace("-", "_"),
                show_timestamp=True,
                show_logger_name=True,
            )

        self.logger.info(
            "Trans-Hub 风格日志系统已启用", log_format=log_format, log_level=log_level
        )

    async def _initialize_cache(self):
        """初始化缓存系统"""
        # 添加内存缓存提供者
        memory_cache = MemoryCacheProvider(max_size=1000)
        self.cache_manager.add_provider("memory", memory_cache, is_default=True)

        # 添加文件缓存提供者
        cache_dir = Path(self.config_manager.get_setting("cache_dir") or "cache")
        file_cache = FileCacheProvider(cache_dir)
        self.cache_manager.add_provider("file", file_cache)

    async def _initialize_container(self):
        """初始化依赖注入容器"""
        # 注册核心服务
        self.container.register_singleton(ConfigManager, instance=self.config_manager)
        self.container.register_singleton(EventBus, instance=self.event_bus)
        self.container.register_singleton(CacheManager, instance=self.cache_manager)
        self.container.register_singleton(TaskManager, instance=self.task_manager)
        self.container.register_singleton(TaskScheduler, instance=self.task_scheduler)

        # 注册日志服务
        from .framework.logging.logger import ILogger

        self.container.register_singleton(ILogger, instance=self.logger)

        # 注册 StructLog 工厂
        self.container.register_singleton(StructLogFactory, instance=StructLogFactory)

    async def _initialize_tasks(self):
        """初始化任务系统"""
        # 启动任务管理器
        await self.task_manager.start()

        # 启动任务调度器
        await self.task_scheduler.start()

    async def shutdown(self):
        """关闭Core Platform"""
        try:
            self.logger.info("Core Platform 开始关闭")

            # 发布系统关闭事件
            from datetime import datetime

            from .framework.events.event_bus import Event
            from .framework.events.event_handler import EventTypes

            shutdown_event = Event(
                event_type=EventTypes.SYSTEM_SHUTDOWN,
                timestamp=datetime.now(),
                source="core_platform",
            )
            self.event_bus.publish(shutdown_event)

            # 停止任务系统
            await self.task_scheduler.stop()
            await self.task_manager.stop()

            # 清理资源
            self.container.clear()
            self.cache_manager.clear()

            self.logger.info("Core Platform 关闭完成")

        except Exception as e:
            self.logger.error("Core Platform 关闭时发生错误", exception=e)


# 使用示例
async def example_usage():
    """Core Platform 使用示例"""

    # 1. 创建并初始化平台
    platform = CorePlatform("example-app")
    await platform.initialize()

    try:
        # 2. 注册事件处理器
        @event_handler("user.login")
        def handle_user_login(event):
            print(f"用户登录: {event.data}")

        # 3. 使用后台任务
        @background_task(name="example_task")
        async def example_task(message: str):
            await asyncio.sleep(1)
            return f"处理完成: {message}"

        # 4. 使用缓存
        platform.cache_manager.set("test_key", "test_value", ttl=300)
        cached_value = platform.cache_manager.get("test_key")
        print(f"缓存值: {cached_value}")

        # 5. 发布事件
        from .framework.events.decorators import publish_event

        publish_event("user.login", {"user_id": "123", "username": "test_user"})

        # 6. 提交后台任务
        task_result = await example_task.submit("Hello World")
        print(f"任务结果: {task_result}")

        # 7. 使用配置
        app_name = platform.config_manager.get_setting("app_name")
        print(f"应用名称: {app_name}")

        # 等待一段时间让任务完成
        await asyncio.sleep(2)

    finally:
        # 8. 关闭平台
        await platform.shutdown()


if __name__ == "__main__":
    asyncio.run(example_usage())
