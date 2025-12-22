"""
事件系统

提供松耦合的事件驱动架构：
- 事件定义和发布
- 事件监听和处理
- 异步事件处理
- 事件装饰器
"""

from .decorators import async_event_handler, event_handler
from .event_bus import Event, EventBus, EventHandler
from .event_handler import AsyncEventHandler, IEventHandler

__all__ = [
    "EventBus",
    "Event",
    "EventHandler",
    "IEventHandler",
    "AsyncEventHandler",
    "event_handler",
    "async_event_handler",
]
