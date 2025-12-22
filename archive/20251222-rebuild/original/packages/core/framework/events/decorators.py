"""
事件装饰器

提供方便的事件处理装饰器
"""

from collections.abc import Callable

from .event_bus import Event, EventBus

# 全局事件总线实例
_global_event_bus: EventBus | None = None


def set_global_event_bus(event_bus: EventBus) -> None:
    """设置全局事件总线"""
    global _global_event_bus
    _global_event_bus = event_bus


def get_global_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def event_handler(
    event_type: str | list[str], priority: int = 0, event_bus: EventBus | None = None
) -> Callable:
    """
    事件处理器装饰器

    Args:
        event_type: 事件类型或类型列表
        priority: 处理器优先级
        event_bus: 自定义事件总线
    """

    def decorator(func: Callable) -> Callable:
        bus = event_bus or get_global_event_bus()

        event_types = event_type if isinstance(event_type, list) else [event_type]

        # 为每个事件类型注册处理器
        for et in event_types:
            bus.subscribe(et, func, priority=priority, is_async=False)

        return func

    return decorator


def async_event_handler(
    event_type: str | list[str], priority: int = 0, event_bus: EventBus | None = None
) -> Callable:
    """
    异步事件处理器装饰器

    Args:
        event_type: 事件类型或类型列表
        priority: 处理器优先级
        event_bus: 自定义事件总线
    """

    def decorator(func: Callable) -> Callable:
        bus = event_bus or get_global_event_bus()

        event_types = event_type if isinstance(event_type, list) else [event_type]

        # 为每个事件类型注册异步处理器
        for et in event_types:
            bus.subscribe(et, func, priority=priority, is_async=True)

        return func

    return decorator


def global_event_handler(
    priority: int = 0, event_bus: EventBus | None = None
) -> Callable:
    """
    全局事件处理器装饰器（监听所有事件）

    Args:
        priority: 处理器优先级
        event_bus: 自定义事件总线
    """

    def decorator(func: Callable) -> Callable:
        bus = event_bus or get_global_event_bus()
        bus.subscribe_global(func, priority=priority, is_async=False)
        return func

    return decorator


def publish_event(
    event_type: str,
    data: dict | None = None,
    source: str | None = None,
    event_bus: EventBus | None = None,
) -> None:
    """
    发布事件的便捷函数

    Args:
        event_type: 事件类型
        data: 事件数据
        source: 事件源
        event_bus: 自定义事件总线
    """
    bus = event_bus or get_global_event_bus()
    event = Event(event_type=event_type, data=data, source=source, timestamp=None)
    bus.publish(event)


async def publish_event_async(
    event_type: str,
    data: dict | None = None,
    source: str | None = None,
    event_bus: EventBus | None = None,
) -> None:
    """
    异步发布事件的便捷函数

    Args:
        event_type: 事件类型
        data: 事件数据
        source: 事件源
        event_bus: 自定义事件总线
    """
    bus = event_bus or get_global_event_bus()
    event = Event(event_type=event_type, data=data, source=source, timestamp=None)
    await bus.publish_async(event)
