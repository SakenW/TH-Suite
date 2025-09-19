"""
进度监控核心模块

实现进度追踪、事件管理、状态同步等核心功能
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Dict, List, Optional, Callable, Any, 
    AsyncIterator, Protocol, Union, Set
)
import weakref
from collections import defaultdict, deque

from .config import ProgressConfig


class ProgressEventType(Enum):
    """进度事件类型"""
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_CANCELLED = "task_cancelled"
    SUBTASK_STARTED = "subtask_started"
    SUBTASK_COMPLETED = "subtask_completed"
    MILESTONE_REACHED = "milestone_reached"
    ERROR_OCCURRED = "error_occurred"
    SPEED_UPDATED = "speed_updated"
    ETA_UPDATED = "eta_updated"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressEvent:
    """进度事件"""
    event_type: ProgressEventType
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type.value,
            'task_id': self.task_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'message': self.message
        }


@dataclass
class SpeedMetrics:
    """速度指标"""
    current_speed: float = 0.0  # 当前速度 (单位/秒)
    average_speed: float = 0.0  # 平均速度
    peak_speed: float = 0.0  # 峰值速度
    speed_history: deque = field(default_factory=lambda: deque(maxlen=60))  # 最近60秒的速度记录
    
    def update_speed(self, processed_amount: float, time_delta: float) -> None:
        """更新速度指标"""
        if time_delta > 0:
            self.current_speed = processed_amount / time_delta
            self.speed_history.append((time.time(), self.current_speed))
            
            # 更新峰值速度
            if self.current_speed > self.peak_speed:
                self.peak_speed = self.current_speed
            
            # 计算平均速度（基于最近的记录）
            if len(self.speed_history) > 1:
                recent_speeds = [speed for _, speed in self.speed_history]
                self.average_speed = sum(recent_speeds) / len(recent_speeds)
    
    def get_smooth_speed(self, window_seconds: int = 10) -> float:
        """获取平滑后的速度"""
        if not self.speed_history:
            return 0.0
        
        cutoff_time = time.time() - window_seconds
        recent_records = [
            speed for timestamp, speed in self.speed_history
            if timestamp >= cutoff_time
        ]
        
        return sum(recent_records) / len(recent_records) if recent_records else 0.0


@dataclass
class TaskProgress:
    """任务进度信息"""
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    
    # 进度数值
    current_value: float = 0.0
    total_value: float = 100.0
    unit: str = "items"
    
    # 时间信息
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    
    # 速度和ETA
    speed_metrics: SpeedMetrics = field(default_factory=SpeedMetrics)
    eta: Optional[timedelta] = None
    
    # 层次信息
    parent_task_id: Optional[str] = None
    subtask_ids: Set[str] = field(default_factory=set)
    
    # 额外信息
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        """进度百分比"""
        if self.total_value == 0:
            return 0.0
        return min((self.current_value / self.total_value) * 100, 100.0)
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == TaskStatus.COMPLETED
    
    @property
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.status in (TaskStatus.RUNNING, TaskStatus.PAUSED)
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """已用时间"""
        if not self.start_time:
            return None
        
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    def update_progress(
        self, 
        current_value: float, 
        message: Optional[str] = None
    ) -> None:
        """更新进度"""
        old_value = self.current_value
        self.current_value = min(current_value, self.total_value)
        self.last_update_time = datetime.now()
        
        # 更新速度指标
        if self.start_time and old_value < self.current_value:
            elapsed = (self.last_update_time - self.start_time).total_seconds()
            if elapsed > 0:
                processed_amount = self.current_value - old_value
                time_delta = 1.0  # 假设1秒间隔，实际应根据调用频率调整
                self.speed_metrics.update_speed(processed_amount, time_delta)
        
        # 计算ETA
        self._calculate_eta()
    
    def _calculate_eta(self) -> None:
        """计算预计完成时间"""
        if (
            self.current_value >= self.total_value or
            self.speed_metrics.average_speed <= 0 or
            not self.start_time
        ):
            self.eta = None
            return
        
        remaining = self.total_value - self.current_value
        speed = self.speed_metrics.get_smooth_speed()
        
        if speed > 0:
            eta_seconds = remaining / speed
            self.eta = timedelta(seconds=eta_seconds)
        else:
            self.eta = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'status': self.status.value,
            'current_value': self.current_value,
            'total_value': self.total_value,
            'percentage': self.percentage,
            'unit': self.unit,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'elapsed_time': self.elapsed_time.total_seconds() if self.elapsed_time else None,
            'current_speed': self.speed_metrics.current_speed,
            'average_speed': self.speed_metrics.average_speed,
            'peak_speed': self.speed_metrics.peak_speed,
            'eta': self.eta.total_seconds() if self.eta else None,
            'parent_task_id': self.parent_task_id,
            'subtask_count': len(self.subtask_ids),
            'metadata': self.metadata,
            'error_message': self.error_message
        }


class ProgressListener(Protocol):
    """进度监听器协议"""
    
    async def on_progress_event(self, event: ProgressEvent) -> None:
        """处理进度事件"""
        ...


class ProgressTracker:
    """进度追踪器"""
    
    def __init__(self, config: ProgressConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.progress_data: Dict[str, TaskProgress] = {}
        self.listeners: List[ProgressListener] = []
        self.event_history: deque = deque(maxlen=config.max_event_history)
        self._lock = asyncio.Lock()
        self._background_tasks: Set[asyncio.Task] = set()
        
        # 启动后台任务
        if config.auto_cleanup_interval > 0:
            self._start_cleanup_task()
        
        if config.metrics_update_interval > 0:
            self._start_metrics_task()
    
    def add_listener(self, listener: ProgressListener) -> None:
        """添加进度监听器"""
        self.listeners.append(listener)
    
    def remove_listener(self, listener: ProgressListener) -> None:
        """移除进度监听器"""
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    async def create_task(
        self,
        task_id: str,
        title: str,
        total_value: float = 100.0,
        unit: str = "items",
        parent_task_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> TaskProgress:
        """创建新任务"""
        async with self._lock:
            if task_id in self.progress_data:
                raise ValueError(f"任务 {task_id} 已存在")
            
            progress = TaskProgress(
                task_id=task_id,
                title=title,
                total_value=total_value,
                unit=unit,
                parent_task_id=parent_task_id,
                metadata=metadata or {}
            )
            
            self.progress_data[task_id] = progress
            
            # 如果有父任务，添加到父任务的子任务列表
            if parent_task_id and parent_task_id in self.progress_data:
                self.progress_data[parent_task_id].subtask_ids.add(task_id)
            
            await self._emit_event(ProgressEventType.TASK_STARTED, task_id)
            return progress
    
    async def start_task(self, task_id: str) -> None:
        """开始任务"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            progress.status = TaskStatus.RUNNING
            progress.start_time = datetime.now()
            
            await self._emit_event(ProgressEventType.TASK_STARTED, task_id)
    
    async def update_progress(
        self,
        task_id: str,
        current_value: float,
        message: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """更新任务进度"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            old_percentage = progress.percentage
            
            progress.update_progress(current_value, message)
            
            if metadata:
                progress.metadata.update(metadata)
            
            # 检查是否达到里程碑
            new_percentage = progress.percentage
            milestone_interval = self.config.milestone_interval
            
            if milestone_interval > 0:
                old_milestone = int(old_percentage // milestone_interval)
                new_milestone = int(new_percentage // milestone_interval)
                
                if new_milestone > old_milestone:
                    await self._emit_event(
                        ProgressEventType.MILESTONE_REACHED,
                        task_id,
                        {'milestone': new_milestone * milestone_interval}
                    )
            
            await self._emit_event(
                ProgressEventType.TASK_PROGRESS,
                task_id,
                {'current_value': current_value, 'message': message}
            )
    
    async def complete_task(
        self,
        task_id: str,
        message: Optional[str] = None
    ) -> None:
        """完成任务"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            progress.status = TaskStatus.COMPLETED
            progress.current_value = progress.total_value
            progress.end_time = datetime.now()
            
            await self._emit_event(
                ProgressEventType.TASK_COMPLETED,
                task_id,
                {'message': message}
            )
    
    async def fail_task(
        self,
        task_id: str,
        error_message: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """任务失败"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            progress.status = TaskStatus.FAILED
            progress.error_message = error_message
            progress.end_time = datetime.now()
            
            if metadata:
                progress.metadata.update(metadata)
            
            await self._emit_event(
                ProgressEventType.TASK_FAILED,
                task_id,
                {'error_message': error_message, 'metadata': metadata}
            )
    
    async def pause_task(self, task_id: str) -> None:
        """暂停任务"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            if progress.status == TaskStatus.RUNNING:
                progress.status = TaskStatus.PAUSED
                
                await self._emit_event(ProgressEventType.TASK_PAUSED, task_id)
    
    async def resume_task(self, task_id: str) -> None:
        """恢复任务"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            if progress.status == TaskStatus.PAUSED:
                progress.status = TaskStatus.RUNNING
                
                await self._emit_event(ProgressEventType.TASK_RESUMED, task_id)
    
    async def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        async with self._lock:
            if task_id not in self.progress_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            progress = self.progress_data[task_id]
            progress.status = TaskStatus.CANCELLED
            progress.end_time = datetime.now()
            
            await self._emit_event(ProgressEventType.TASK_CANCELLED, task_id)
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        return self.progress_data.get(task_id)
    
    def list_tasks(
        self,
        status_filter: Optional[TaskStatus] = None,
        parent_task_id: Optional[str] = None
    ) -> List[TaskProgress]:
        """列出任务"""
        tasks = list(self.progress_data.values())
        
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        if parent_task_id is not None:
            tasks = [t for t in tasks if t.parent_task_id == parent_task_id]
        
        return tasks
    
    async def remove_task(self, task_id: str) -> None:
        """移除任务"""
        async with self._lock:
            if task_id in self.progress_data:
                progress = self.progress_data[task_id]
                
                # 移除父任务的子任务引用
                if progress.parent_task_id and progress.parent_task_id in self.progress_data:
                    parent = self.progress_data[progress.parent_task_id]
                    parent.subtask_ids.discard(task_id)
                
                # 移除所有子任务
                for subtask_id in progress.subtask_ids.copy():
                    await self.remove_task(subtask_id)
                
                del self.progress_data[task_id]
    
    async def _emit_event(
        self,
        event_type: ProgressEventType,
        task_id: str,
        data: Dict[str, Any] = None,
        message: Optional[str] = None
    ) -> None:
        """发出进度事件"""
        event = ProgressEvent(
            event_type=event_type,
            task_id=task_id,
            data=data or {},
            message=message
        )
        
        self.event_history.append(event)
        
        # 通知所有监听器
        for listener in self.listeners:
            try:
                await listener.on_progress_event(event)
            except Exception as e:
                self.logger.error(f"进度监听器错误: {e}")
    
    def _start_cleanup_task(self) -> None:
        """启动清理任务"""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(self.config.auto_cleanup_interval)
                    await self._cleanup_completed_tasks()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"清理任务错误: {e}")
        
        task = asyncio.create_task(cleanup_task())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    def _start_metrics_task(self) -> None:
        """启动指标更新任务"""
        async def metrics_task():
            while True:
                try:
                    await asyncio.sleep(self.config.metrics_update_interval)
                    await self._update_metrics()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"指标更新任务错误: {e}")
        
        task = asyncio.create_task(metrics_task())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def _cleanup_completed_tasks(self) -> None:
        """清理已完成的任务"""
        cutoff_time = datetime.now() - timedelta(seconds=self.config.completed_task_retention)
        
        tasks_to_remove = []
        for task_id, progress in self.progress_data.items():
            if (
                progress.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED) and
                progress.end_time and
                progress.end_time < cutoff_time
            ):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            await self.remove_task(task_id)
        
        if tasks_to_remove:
            self.logger.info(f"清理了 {len(tasks_to_remove)} 个已完成的任务")
    
    async def _update_metrics(self) -> None:
        """更新性能指标"""
        for progress in self.progress_data.values():
            if progress.is_active:
                # 更新ETA
                progress._calculate_eta()
                
                # 发出速度更新事件
                if progress.speed_metrics.current_speed > 0:
                    await self._emit_event(
                        ProgressEventType.SPEED_UPDATED,
                        progress.task_id,
                        {
                            'current_speed': progress.speed_metrics.current_speed,
                            'average_speed': progress.speed_metrics.average_speed
                        }
                    )
                
                # 发出ETA更新事件
                if progress.eta:
                    await self._emit_event(
                        ProgressEventType.ETA_UPDATED,
                        progress.task_id,
                        {'eta_seconds': progress.eta.total_seconds()}
                    )
    
    async def shutdown(self) -> None:
        """关闭进度追踪器"""
        # 取消所有后台任务
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, config: ProgressConfig):
        self.config = config
        self.tracker = ProgressTracker(config)
        self.logger = logging.getLogger(__name__)
    
    async def create_and_start_task(
        self,
        task_id: str,
        title: str,
        total_value: float = 100.0,
        unit: str = "items",
        parent_task_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> TaskProgress:
        """创建并开始任务"""
        progress = await self.tracker.create_task(
            task_id, title, total_value, unit, parent_task_id, metadata
        )
        await self.tracker.start_task(task_id)
        return progress
    
    async def update_task(
        self,
        task_id: str,
        increment: Optional[float] = None,
        current_value: Optional[float] = None,
        message: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """更新任务进度（支持增量或绝对值）"""
        progress = self.tracker.get_task_progress(task_id)
        if not progress:
            raise ValueError(f"任务 {task_id} 不存在")
        
        if increment is not None:
            new_value = progress.current_value + increment
        elif current_value is not None:
            new_value = current_value
        else:
            raise ValueError("必须提供 increment 或 current_value 参数")
        
        await self.tracker.update_progress(task_id, new_value, message, metadata)
    
    async def batch_update(self, updates: List[Dict[str, Any]]) -> None:
        """批量更新任务进度"""
        for update in updates:
            task_id = update.get('task_id')
            if not task_id:
                continue
            
            try:
                await self.update_task(
                    task_id=task_id,
                    increment=update.get('increment'),
                    current_value=update.get('current_value'),
                    message=update.get('message'),
                    metadata=update.get('metadata')
                )
            except Exception as e:
                self.logger.error(f"批量更新任务 {task_id} 失败: {e}")
    
    def add_listener(self, listener: ProgressListener) -> None:
        """添加进度监听器"""
        self.tracker.add_listener(listener)
    
    def remove_listener(self, listener: ProgressListener) -> None:
        """移除进度监听器"""
        self.tracker.remove_listener(listener)
    
    async def get_task_tree(self, root_task_id: Optional[str] = None) -> Dict[str, Any]:
        """获取任务树"""
        def build_tree(task_id: str) -> Dict[str, Any]:
            progress = self.tracker.get_task_progress(task_id)
            if not progress:
                return {}
            
            tree = progress.to_dict()
            tree['subtasks'] = [
                build_tree(subtask_id)
                for subtask_id in progress.subtask_ids
            ]
            
            return tree
        
        if root_task_id:
            return build_tree(root_task_id)
        else:
            # 返回所有根任务
            root_tasks = self.tracker.list_tasks(parent_task_id=None)
            return {
                'root_tasks': [build_tree(task.task_id) for task in root_tasks]
            }
    
    async def shutdown(self) -> None:
        """关闭进度管理器"""
        await self.tracker.shutdown()