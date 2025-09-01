"""
Framework Layer

提供系统的核心基础设施服务：
- IoC容器和依赖注入
- 配置管理（多环境、热更新）
- 事件系统（发布订阅模式）
- 缓存系统（多种实现）
- 日志系统（统一接口）
- 任务调度（异步处理）
- 验证框架
"""

from .cache.cache_manager import CacheManager
from .config.config_manager import ConfigManager
from .container import IoCContainer
from .events.event_bus import EventBus
from .logging.logger import ILogger, Logger
from .tasks.task_manager import TaskManager
from .tasks.task_scheduler import TaskScheduler
from .validation.validator import Validator

__all__ = [
    "IoCContainer",
    "ConfigManager",
    "EventBus",
    "CacheManager",
    "ILogger",
    "Logger",
    "TaskManager",
    "TaskScheduler",
    "Validator",
]
