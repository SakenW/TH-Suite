"""
任务调度器

定时执行任务的调度器
"""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .task_manager import TaskManager


@dataclass
class ScheduledTask:
    """定时任务"""

    task_id: str
    name: str
    func: Callable
    args: tuple
    kwargs: dict

    # 调度配置
    interval: timedelta | None = None  # 间隔执行
    cron_expression: str | None = None  # Cron表达式
    run_at: datetime | None = None  # 指定时间执行

    # 状态
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0

    def should_run(self, now: datetime) -> bool:
        """检查是否应该执行"""
        if not self.enabled:
            return False

        if self.next_run and now >= self.next_run:
            return True

        return False

    def calculate_next_run(self, now: datetime) -> None:
        """计算下次执行时间"""
        if self.interval:
            self.next_run = now + self.interval
        elif self.run_at:
            if self.run_count == 0:
                self.next_run = self.run_at
            else:
                self.enabled = False  # 一次性任务
        # TODO: 实现Cron表达式解析


class TaskScheduler:
    """任务调度器"""

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._scheduled_tasks: dict[str, ScheduledTask] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._running = False
        self._check_interval = 1  # 检查间隔（秒）

    async def start(self) -> None:
        """启动调度器"""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """停止调度器"""
        if not self._running:
            return

        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    def schedule_interval(
        self,
        name: str,
        func: Callable,
        interval: timedelta,
        args: tuple = (),
        kwargs: dict = None,
        start_immediately: bool = False,
    ) -> str:
        """定时间隔执行任务"""
        if kwargs is None:
            kwargs = {}

        task_id = str(uuid.uuid4())
        now = datetime.now()

        scheduled_task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            interval=interval,
        )

        if start_immediately:
            scheduled_task.next_run = now
        else:
            scheduled_task.next_run = now + interval

        self._scheduled_tasks[task_id] = scheduled_task
        return task_id

    def schedule_at(
        self,
        name: str,
        func: Callable,
        run_at: datetime,
        args: tuple = (),
        kwargs: dict = None,
    ) -> str:
        """在指定时间执行任务"""
        if kwargs is None:
            kwargs = {}

        task_id = str(uuid.uuid4())

        scheduled_task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            run_at=run_at,
            next_run=run_at,
        )

        self._scheduled_tasks[task_id] = scheduled_task
        return task_id

    def schedule_cron(
        self,
        name: str,
        func: Callable,
        cron_expression: str,
        args: tuple = (),
        kwargs: dict = None,
    ) -> str:
        """使用Cron表达式调度任务"""
        if kwargs is None:
            kwargs = {}

        task_id = str(uuid.uuid4())

        scheduled_task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            cron_expression=cron_expression,
        )

        # TODO: 根据Cron表达式计算next_run
        scheduled_task.next_run = datetime.now() + timedelta(minutes=1)

        self._scheduled_tasks[task_id] = scheduled_task
        return task_id

    def unschedule(self, task_id: str) -> bool:
        """取消调度任务"""
        return self._scheduled_tasks.pop(task_id, None) is not None

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id].enabled = True
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id].enabled = False
            return True
        return False

    def get_scheduled_tasks(self) -> list[ScheduledTask]:
        """获取所有调度任务"""
        return list(self._scheduled_tasks.values())

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """获取调度任务"""
        return self._scheduled_tasks.get(task_id)

    async def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while self._running:
            try:
                now = datetime.now()

                # 检查所有调度任务
                for scheduled_task in list(self._scheduled_tasks.values()):
                    if scheduled_task.should_run(now):
                        # 提交任务给任务管理器
                        await self.task_manager.submit_task(
                            name=f"scheduled:{scheduled_task.name}",
                            func=scheduled_task.func,
                            args=scheduled_task.args,
                            kwargs=scheduled_task.kwargs,
                        )

                        # 更新任务状态
                        scheduled_task.last_run = now
                        scheduled_task.run_count += 1
                        scheduled_task.calculate_next_run(now)

                        # 如果是一次性任务且已执行，删除它
                        if not scheduled_task.enabled and scheduled_task.run_at:
                            del self._scheduled_tasks[scheduled_task.task_id]

                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"调度器循环错误: {e}")
                await asyncio.sleep(self._check_interval)
