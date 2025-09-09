"""
事件总线实现
处理领域事件的发布和订阅
"""

import asyncio
import logging
from abc import ABC
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any

logger = logging.getLogger(__name__)


class DomainEvent(ABC):
    """领域事件基类"""

    def __init__(self):
        self.event_id = self._generate_event_id()
        self.occurred_at = datetime.now()

    @staticmethod
    def _generate_event_id() -> str:
        """生成事件ID"""
        import uuid

        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "occurred_at": self.occurred_at.isoformat(),
            "data": {
                k: v
                for k, v in self.__dict__.items()
                if k not in ["event_id", "occurred_at"]
            },
        }


@dataclass
class EventHandler:
    """事件处理器包装"""

    handler: Callable
    event_type: type[DomainEvent]
    priority: int = 0
    is_async: bool = False
    error_handler: Callable | None = None

    def __post_init__(self):
        # 检测是否为异步处理器
        self.is_async = asyncio.iscoroutinefunction(self.handler)


class EventBus:
    """事件总线"""

    def __init__(
        self,
        async_enabled: bool = True,
        max_workers: int = 10,
        max_queue_size: int = 1000,
    ):
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}
        self._lock = Lock()
        self._async_enabled = async_enabled

        # 异步处理
        if async_enabled:
            self._event_queue = Queue(maxsize=max_queue_size)
            self._executor = ThreadPoolExecutor(max_workers=max_workers)
            self._running = False
            self._worker_thread = None

        # 事件历史记录
        self._event_history: list[DomainEvent] = []
        self._max_history_size = 1000

        # 错误处理
        self._global_error_handler: Callable | None = None

        # 中间件
        self._middlewares: list[Callable] = []

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable,
        priority: int = 0,
        error_handler: Callable | None = None,
    ):
        """订阅事件

        Args:
            event_type: 事件类型
            handler: 处理函数
            priority: 优先级（数字越大优先级越高）
            error_handler: 错误处理函数
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []

            event_handler = EventHandler(
                handler=handler,
                event_type=event_type,
                priority=priority,
                error_handler=error_handler,
            )

            self._handlers[event_type].append(event_handler)

            # 按优先级排序
            self._handlers[event_type].sort(key=lambda x: x.priority, reverse=True)

            logger.debug(f"Subscribed {handler.__name__} to {event_type.__name__}")

    def unsubscribe(self, event_type: type[DomainEvent], handler: Callable):
        """取消订阅

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h.handler != handler
                ]

                if not self._handlers[event_type]:
                    del self._handlers[event_type]

                logger.debug(
                    f"Unsubscribed {handler.__name__} from {event_type.__name__}"
                )

    def publish(self, event: DomainEvent):
        """发布事件

        Args:
            event: 领域事件
        """
        # 应用中间件
        for middleware in self._middlewares:
            event = middleware(event)
            if event is None:
                logger.debug("Event cancelled by middleware")
                return

        # 记录事件历史
        self._record_event(event)

        # 获取处理器
        handlers = self._get_handlers(type(event))

        if not handlers:
            logger.debug(f"No handlers for event {type(event).__name__}")
            return

        # 同步或异步处理
        if self._async_enabled:
            self._event_queue.put((event, handlers))
            if not self._running:
                self.start()
        else:
            self._process_event_sync(event, handlers)

        logger.info(f"Published event: {type(event).__name__}")

    def publish_batch(self, events: list[DomainEvent]):
        """批量发布事件

        Args:
            events: 事件列表
        """
        for event in events:
            self.publish(event)

    def _process_event_sync(self, event: DomainEvent, handlers: list[EventHandler]):
        """同步处理事件"""
        for handler in handlers:
            try:
                if handler.is_async:
                    # 在新线程中运行异步处理器
                    asyncio.run(handler.handler(event))
                else:
                    handler.handler(event)

            except Exception as e:
                self._handle_error(event, handler, e)

    def _process_event_async(self):
        """异步处理事件（工作线程）"""
        while self._running:
            try:
                # 从队列获取事件
                event, handlers = self._event_queue.get(timeout=1)

                # 并发处理
                futures = []
                for handler in handlers:
                    if handler.is_async:
                        future = self._executor.submit(
                            asyncio.run, handler.handler(event)
                        )
                    else:
                        future = self._executor.submit(handler.handler, event)
                    futures.append((future, handler))

                # 等待完成并处理错误
                for future, handler in futures:
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        self._handle_error(event, handler, e)

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in event processing thread: {e}")

    def _handle_error(
        self, event: DomainEvent, handler: EventHandler, error: Exception
    ):
        """处理错误"""
        logger.error(
            f"Error handling event {type(event).__name__} "
            f"in handler {handler.handler.__name__}: {error}"
        )

        # 调用特定错误处理器
        if handler.error_handler:
            try:
                handler.error_handler(event, error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")

        # 调用全局错误处理器
        if self._global_error_handler:
            try:
                self._global_error_handler(event, handler, error)
            except Exception as e:
                logger.error(f"Error in global error handler: {e}")

    def _get_handlers(self, event_type: type[DomainEvent]) -> list[EventHandler]:
        """获取事件处理器"""
        handlers = []

        with self._lock:
            # 直接匹配
            if event_type in self._handlers:
                handlers.extend(self._handlers[event_type])

            # 检查父类（支持事件继承）
            for registered_type, registered_handlers in self._handlers.items():
                if (
                    issubclass(event_type, registered_type)
                    and registered_type != event_type
                ):
                    handlers.extend(registered_handlers)

        # 按优先级排序
        handlers.sort(key=lambda x: x.priority, reverse=True)
        return handlers

    def _record_event(self, event: DomainEvent):
        """记录事件历史"""
        self._event_history.append(event)

        # 限制历史大小
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size :]

    def add_middleware(self, middleware: Callable):
        """添加中间件

        中间件函数接收事件并返回事件（或None以取消事件）
        """
        self._middlewares.append(middleware)

    def set_global_error_handler(self, handler: Callable):
        """设置全局错误处理器"""
        self._global_error_handler = handler

    def start(self):
        """启动异步处理"""
        if self._async_enabled and not self._running:
            self._running = True
            self._worker_thread = Thread(target=self._process_event_async)
            self._worker_thread.daemon = True
            self._worker_thread.start()
            logger.info("Event bus started")

    def stop(self):
        """停止异步处理"""
        if self._async_enabled and self._running:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5)
            self._executor.shutdown(wait=True)
            logger.info("Event bus stopped")

    def get_event_history(
        self, event_type: type[DomainEvent] | None = None, limit: int = 100
    ) -> list[DomainEvent]:
        """获取事件历史

        Args:
            event_type: 筛选的事件类型
            limit: 最大返回数量

        Returns:
            事件列表
        """
        history = self._event_history

        if event_type:
            history = [e for e in history if isinstance(e, event_type)]

        return history[-limit:]

    def clear_history(self):
        """清空事件历史"""
        self._event_history.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_handlers": sum(len(h) for h in self._handlers.values()),
            "event_types": len(self._handlers),
            "history_size": len(self._event_history),
            "is_running": self._running if self._async_enabled else False,
        }

        if self._async_enabled:
            stats["queue_size"] = self._event_queue.qsize()

        # 按事件类型统计
        stats["handlers_by_type"] = {
            event_type.__name__: len(handlers)
            for event_type, handlers in self._handlers.items()
        }

        return stats


# 全局事件总线实例
_global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return _global_event_bus


# 装饰器支持
def event_handler(
    event_type: type[DomainEvent],
    priority: int = 0,
    error_handler: Callable | None = None,
):
    """事件处理器装饰器

    使用示例:
    @event_handler(ModScannedEvent, priority=10)
    def handle_mod_scanned(event: ModScannedEvent):
        print(f"Mod {event.mod_id} scanned")
    """

    def decorator(func: Callable):
        get_event_bus().subscribe(event_type, func, priority, error_handler)
        return func

    return decorator
