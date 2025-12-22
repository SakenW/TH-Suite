"""
任务管理器

管理异步任务的执行和状态
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 正在执行
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 执行失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TaskResult:
    """任务执行结果"""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration(self) -> timedelta | None:
        """执行时长"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class Task:
    """任务定义"""

    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 0
    timeout: int | None = None
    max_retries: int = 0
    retry_delay: int = 1
    created_at: datetime = field(default_factory=datetime.now)

    # 运行时状态
    status: TaskStatus = TaskStatus.PENDING
    current_retry: int = 0
    started_at: datetime | None = None
    error: Exception | None = None


class ITaskExecutor(ABC):
    """任务执行器接口"""

    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """执行任务"""
        pass


class AsyncTaskExecutor(ITaskExecutor):
    """异步任务执行器"""

    async def execute_task(self, task: Task) -> TaskResult:
        """执行异步任务"""
        result = TaskResult(
            task_id=task.task_id, status=TaskStatus.RUNNING, started_at=datetime.now()
        )

        try:
            task.status = TaskStatus.RUNNING
            task.started_at = result.started_at

            # 执行任务
            if asyncio.iscoroutinefunction(task.func):
                if task.timeout:
                    task_result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs), timeout=task.timeout
                    )
                else:
                    task_result = await task.func(*task.args, **task.kwargs)
            else:
                # 同步函数在线程池中执行
                loop = asyncio.get_event_loop()
                if task.timeout:
                    task_result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, task.func, *task.args, **task.kwargs
                        ),
                        timeout=task.timeout,
                    )
                else:
                    task_result = await loop.run_in_executor(
                        None, task.func, *task.args, **task.kwargs
                    )

            result.result = task_result
            result.status = TaskStatus.COMPLETED
            task.status = TaskStatus.COMPLETED

        except TimeoutError:
            error = TimeoutError(f"任务 {task.name} 执行超时")
            result.error = error
            result.status = TaskStatus.FAILED
            task.status = TaskStatus.FAILED
            task.error = error

        except asyncio.CancelledError:
            result.status = TaskStatus.CANCELLED
            task.status = TaskStatus.CANCELLED

        except Exception as e:
            result.error = e
            result.status = TaskStatus.FAILED
            task.status = TaskStatus.FAILED
            task.error = e

        finally:
            result.completed_at = datetime.now()

        return result


class TaskManager:
    """任务管理器"""

    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self._tasks: dict[str, Task] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._task_results: dict[str, TaskResult] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._executor = AsyncTaskExecutor()
        self._worker_tasks: list[asyncio.Task] = []
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """启动任务管理器"""
        if self._running:
            return

        self._running = True

        # 启动工作协程
        for i in range(self.max_concurrent_tasks):
            worker_task = asyncio.create_task(self._worker_loop())
            self._worker_tasks.append(worker_task)

    async def stop(self) -> None:
        """停止任务管理器"""
        if not self._running:
            return

        self._running = False

        # 取消所有工作协程
        for worker_task in self._worker_tasks:
            worker_task.cancel()

        # 等待工作协程结束
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        self._worker_tasks.clear()

        # 取消所有运行中的任务
        for task in self._running_tasks.values():
            task.cancel()

        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)

        self._running_tasks.clear()

    async def submit_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 0,
        timeout: int | None = None,
        max_retries: int = 0,
    ) -> str:
        """提交任务"""
        if kwargs is None:
            kwargs = {}

        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
        )

        async with self._lock:
            self._tasks[task_id] = task

        await self._task_queue.put(task)

        return task_id

    async def get_task_status(self, task_id: str) -> TaskStatus | None:
        """获取任务状态"""
        async with self._lock:
            task = self._tasks.get(task_id)
            return task.status if task else None

    async def get_task_result(self, task_id: str) -> TaskResult | None:
        """获取任务结果"""
        async with self._lock:
            return self._task_results.get(task_id)

    async def wait_for_task(
        self, task_id: str, timeout: float | None = None
    ) -> TaskResult:
        """等待任务完成"""
        start_time = asyncio.get_event_loop().time()

        while True:
            result = await self.get_task_result(task_id)
            if result and result.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                return result

            # 检查超时
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                raise TimeoutError("等待任务结果超时")

            await asyncio.sleep(0.1)

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            # 取消运行中的任务
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                return True

            # 将等待中的任务标记为已取消
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    self._task_results[task_id] = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.CANCELLED,
                        completed_at=datetime.now(),
                    )
                    return True

        return False

    async def get_all_tasks(self) -> list[Task]:
        """获取所有任务"""
        async with self._lock:
            return list(self._tasks.values())

    async def get_running_tasks(self) -> list[Task]:
        """获取运行中的任务"""
        async with self._lock:
            return [
                task
                for task in self._tasks.values()
                if task.status == TaskStatus.RUNNING
            ]

    async def clear_completed_tasks(self) -> None:
        """清理已完成的任务"""
        async with self._lock:
            completed_task_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status
                in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ]

            for task_id in completed_task_ids:
                del self._tasks[task_id]
                self._task_results.pop(task_id, None)

    async def _worker_loop(self) -> None:
        """工作协程循环"""
        while self._running:
            try:
                # 从队列中获取任务
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)

                # 检查任务是否已被取消
                if task.status == TaskStatus.CANCELLED:
                    continue

                # 执行任务
                asyncio_task = asyncio.create_task(self._execute_task_with_retry(task))

                async with self._lock:
                    self._running_tasks[task.task_id] = asyncio_task

                # 等待任务完成
                try:
                    result = await asyncio_task
                    async with self._lock:
                        self._task_results[task.task_id] = result
                finally:
                    async with self._lock:
                        self._running_tasks.pop(task.task_id, None)

            except TimeoutError:
                # 队列为空，继续循环
                continue
            except asyncio.CancelledError:
                # 工作协程被取消
                break
            except Exception as e:
                print(f"工作协程错误: {e}")

    async def _execute_task_with_retry(self, task: Task) -> TaskResult:
        """执行任务（包含重试逻辑）"""
        result = None

        while task.current_retry <= task.max_retries:
            result = await self._executor.execute_task(task)

            if result.status == TaskStatus.COMPLETED:
                break

            if result.status == TaskStatus.CANCELLED:
                break

            if task.current_retry < task.max_retries:
                task.current_retry += 1
                await asyncio.sleep(task.retry_delay)
                # 重置任务状态
                task.status = TaskStatus.PENDING
                task.error = None
            else:
                break

        return result
