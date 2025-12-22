"""
事件总线

实现发布订阅模式的事件系统
"""

import asyncio
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T", bound="Event")


@dataclass
class Event:
    """事件基类"""

    event_type: str
    timestamp: datetime
    source: str | None = None
    data: dict[str, Any] | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}


class EventHandler:
    """事件处理器包装"""

    def __init__(
        self,
        handler: Callable,
        event_type: str,
        is_async: bool = False,
        priority: int = 0,
    ):
        self.handler = handler
        self.event_type = event_type
        self.is_async = is_async
        self.priority = priority
        self.handler_id = id(handler)

    def __call__(self, event: Event) -> Any:
        return self.handler(event)

    def __eq__(self, other):
        if not isinstance(other, EventHandler):
            return False
        return self.handler_id == other.handler_id

    def __hash__(self):
        return hash(self.handler_id)


class EventBus:
    """事件总线"""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._lock = threading.RLock()
        self._event_history: list[Event] = []
        self._max_history_size = 1000

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        priority: int = 0,
        is_async: bool = False,
    ) -> EventHandler:
        """订阅事件"""
        with self._lock:
            event_handler = EventHandler(handler, event_type, is_async, priority)

            self._handlers[event_type].append(event_handler)
            # 按优先级排序（高优先级在前）
            self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)

            return event_handler

    def subscribe_global(
        self, handler: Callable, priority: int = 0, is_async: bool = False
    ) -> EventHandler:
        """订阅所有事件"""
        with self._lock:
            event_handler = EventHandler(handler, "*", is_async, priority)

            self._global_handlers.append(event_handler)
            self._global_handlers.sort(key=lambda h: h.priority, reverse=True)

            return event_handler

    def unsubscribe(self, event_handler: EventHandler) -> bool:
        """取消订阅"""
        with self._lock:
            # 从特定事件处理器中移除
            if event_handler.event_type in self._handlers:
                handlers = self._handlers[event_handler.event_type]
                if event_handler in handlers:
                    handlers.remove(event_handler)
                    return True

            # 从全局处理器中移除
            if event_handler in self._global_handlers:
                self._global_handlers.remove(event_handler)
                return True

            return False

    def unsubscribe_all(self, event_type: str) -> int:
        """取消特定事件类型的所有订阅"""
        with self._lock:
            if event_type in self._handlers:
                count = len(self._handlers[event_type])
                del self._handlers[event_type]
                return count
            return 0

    def publish(self, event: Event) -> None:
        """发布事件"""
        with self._lock:
            # 添加到历史记录
            self._add_to_history(event)

            # 获取处理器
            handlers = self._get_handlers_for_event(event.event_type)

            # 同步处理器
            sync_handlers = [h for h in handlers if not h.is_async]
            for handler in sync_handlers:
                try:
                    handler(event)
                except Exception as e:
                    print(f"事件处理器执行失败: {e}")

            # 异步处理器
            async_handlers = [h for h in handlers if h.is_async]
            if async_handlers:
                # 在新的任务中异步执行
                asyncio.create_task(self._handle_async_events(event, async_handlers))

    def publish_async(self, event: Event) -> asyncio.Task:
        """异步发布事件"""
        return asyncio.create_task(self._publish_async_impl(event))

    async def _publish_async_impl(self, event: Event) -> None:
        """异步发布事件实现"""
        with self._lock:
            # 添加到历史记录
            self._add_to_history(event)

            # 获取处理器
            handlers = self._get_handlers_for_event(event.event_type)

        # 并发执行所有处理器
        tasks = []
        for handler in handlers:
            if handler.is_async:
                tasks.append(self._call_async_handler(handler, event))
            else:
                tasks.append(self._call_sync_handler(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_async_events(
        self, event: Event, handlers: list[EventHandler]
    ) -> None:
        """处理异步事件"""
        tasks = [self._call_async_handler(handler, event) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _call_async_handler(self, handler: EventHandler, event: Event) -> Any:
        """调用异步处理器"""
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            print(f"异步事件处理器执行失败: {e}")

    async def _call_sync_handler(self, handler: EventHandler, event: Event) -> Any:
        """在异步上下文中调用同步处理器"""
        try:
            return handler(event)
        except Exception as e:
            print(f"同步事件处理器执行失败: {e}")

    def _get_handlers_for_event(self, event_type: str) -> list[EventHandler]:
        """获取事件的所有处理器"""
        handlers = []

        # 特定事件处理器
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])

        # 全局处理器
        handlers.extend(self._global_handlers)

        # 按优先级排序
        handlers.sort(key=lambda h: h.priority, reverse=True)

        return handlers

    def _add_to_history(self, event: Event) -> None:
        """添加到事件历史"""
        self._event_history.append(event)

        # 限制历史记录大小
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)

    def get_event_history(
        self, event_type: str | None = None, limit: int | None = None
    ) -> list[Event]:
        """获取事件历史"""
        with self._lock:
            events = self._event_history

            if event_type:
                events = [e for e in events if e.event_type == event_type]

            if limit:
                events = events[-limit:]

            return events.copy()

    def clear_history(self) -> None:
        """清空事件历史"""
        with self._lock:
            self._event_history.clear()

    def get_handler_count(self, event_type: str | None = None) -> int:
        """获取处理器数量"""
        with self._lock:
            if event_type is None:
                total = sum(len(handlers) for handlers in self._handlers.values())
                total += len(self._global_handlers)
                return total

            return len(self._handlers.get(event_type, []))

    def get_registered_event_types(self) -> list[str]:
        """获取已注册的事件类型"""
        with self._lock:
            return list(self._handlers.keys())

    def clear_all_handlers(self) -> None:
        """清空所有处理器"""
        with self._lock:
            self._handlers.clear()
            self._global_handlers.clear()

    def set_history_size(self, size: int) -> None:
        """设置历史记录大小"""
        self._max_history_size = max(0, size)

        with self._lock:
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size :]
