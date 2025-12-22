"""
事件处理器接口和实现
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from .event_bus import Event


class IEventHandler(ABC):
    """事件处理器接口"""

    @abstractmethod
    def handle(self, event: Event) -> Any:
        """处理事件"""
        pass

    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """检查是否能处理特定类型的事件"""
        pass


class AsyncEventHandler(IEventHandler):
    """异步事件处理器基类"""

    @abstractmethod
    async def handle_async(self, event: Event) -> Any:
        """异步处理事件"""
        pass

    def handle(self, event: Event) -> Any:
        """同步处理事件（包装异步方法）"""
        return asyncio.create_task(self.handle_async(event))


class BaseEventHandler(IEventHandler):
    """基础事件处理器"""

    def __init__(self, event_types: list | None = None):
        self.event_types = event_types or []

    def can_handle(self, event_type: str) -> bool:
        """检查是否能处理特定类型的事件"""
        return not self.event_types or event_type in self.event_types

    def handle(self, event: Event) -> Any:
        """处理事件（子类需要重写）"""
        pass


# 常用的事件类型常量
class EventTypes:
    """标准事件类型"""

    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # 应用事件
    APP_INITIALIZED = "app.initialized"
    APP_READY = "app.ready"

    # 用户事件
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # 文件事件
    FILE_CREATED = "file.created"
    FILE_UPDATED = "file.updated"
    FILE_DELETED = "file.deleted"

    # 任务事件
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # MC相关事件
    MOD_SCANNED = "mc.mod.scanned"
    TRANSLATION_EXTRACTED = "mc.translation.extracted"
    BUILD_COMPLETED = "mc.build.completed"
