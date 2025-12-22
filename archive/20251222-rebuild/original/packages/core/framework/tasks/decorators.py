"""
任务装饰器

提供方便的任务执行装饰器
"""

import asyncio
import functools
from collections.abc import Callable
from datetime import datetime, timedelta

from .task_manager import TaskManager
from .task_scheduler import TaskScheduler

# 全局任务管理器和调度器实例
_global_task_manager: TaskManager | None = None
_global_task_scheduler: TaskScheduler | None = None


def set_global_task_manager(task_manager: TaskManager) -> None:
    """设置全局任务管理器"""
    global _global_task_manager
    _global_task_manager = task_manager


def set_global_task_scheduler(scheduler: TaskScheduler) -> None:
    """设置全局任务调度器"""
    global _global_task_scheduler
    _global_task_scheduler = scheduler


def get_global_task_manager() -> TaskManager:
    """获取全局任务管理器"""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = TaskManager()
    return _global_task_manager


def get_global_task_scheduler() -> TaskScheduler:
    """获取全局任务调度器"""
    global _global_task_scheduler
    if _global_task_scheduler is None:
        task_manager = get_global_task_manager()
        _global_task_scheduler = TaskScheduler(task_manager)
    return _global_task_scheduler


def background_task(
    name: str | None = None,
    priority: int = 0,
    timeout: int | None = None,
    max_retries: int = 0,
    task_manager: TaskManager | None = None,
) -> Callable:
    """
    后台任务装饰器

    Args:
        name: 任务名称
        priority: 任务优先级
        timeout: 任务超时时间（秒）
        max_retries: 最大重试次数
        task_manager: 自定义任务管理器
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tm = task_manager or get_global_task_manager()
            task_name = name or f"{func.__module__}.{func.__name__}"

            task_id = await tm.submit_task(
                name=task_name,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
            )

            if asyncio.iscoroutinefunction(func):
                return await tm.wait_for_task(task_id)
            else:
                return tm.wait_for_task(task_id)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.create_task(async_wrapper(*args, **kwargs))

        # 添加任务控制方法
        async def submit(*args, **kwargs) -> str:
            """提交任务到后台执行"""
            tm = task_manager or get_global_task_manager()
            task_name = name or f"{func.__module__}.{func.__name__}"

            return await tm.submit_task(
                name=task_name,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
            )

        # 判断是否为异步函数
        if asyncio.iscoroutinefunction(func):
            wrapper = async_wrapper
        else:
            wrapper = sync_wrapper

        wrapper.submit = submit
        return wrapper

    return decorator


def scheduled_task(
    interval: timedelta | None = None,
    cron: str | None = None,
    run_at: datetime | None = None,
    name: str | None = None,
    start_immediately: bool = False,
    scheduler: TaskScheduler | None = None,
) -> Callable:
    """
    定时任务装饰器

    Args:
        interval: 执行间隔
        cron: Cron表达式
        run_at: 指定执行时间
        name: 任务名称
        start_immediately: 是否立即开始执行
        scheduler: 自定义调度器
    """

    def decorator(func: Callable) -> Callable:
        sch = scheduler or get_global_task_scheduler()
        task_name = name or f"{func.__module__}.{func.__name__}"

        if interval:
            task_id = sch.schedule_interval(
                name=task_name,
                func=func,
                interval=interval,
                start_immediately=start_immediately,
            )
        elif cron:
            task_id = sch.schedule_cron(name=task_name, func=func, cron_expression=cron)
        elif run_at:
            task_id = sch.schedule_at(name=task_name, func=func, run_at=run_at)
        else:
            raise ValueError("必须指定interval、cron或run_at中的一个")

        # 添加调度控制方法
        def enable():
            """启用定时任务"""
            return sch.enable_task(task_id)

        def disable():
            """禁用定时任务"""
            return sch.disable_task(task_id)

        def unschedule():
            """取消定时任务"""
            return sch.unschedule(task_id)

        func.enable = enable
        func.disable = disable
        func.unschedule = unschedule
        func.task_id = task_id

        return func

    return decorator


def every(interval: timedelta) -> Callable:
    """每隔指定时间执行的装饰器简化版"""
    return scheduled_task(interval=interval, start_immediately=True)


def daily(hour: int = 0, minute: int = 0) -> Callable:
    """每日执行的装饰器"""
    return scheduled_task(interval=timedelta(days=1))


def hourly(minute: int = 0) -> Callable:
    """每小时执行的装饰器"""
    return scheduled_task(interval=timedelta(hours=1))
