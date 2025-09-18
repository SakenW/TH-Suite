"""
TH-Suite 分层Worker管理器
Phase 3: 专门化Worker系统，处理不同类型的扫描任务
"""

import asyncio
import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import sqlite3
import json

from .checkpoint_manager import CheckpointManager
from .event_applier import EventApplier, EventType, ScanEvent

logger = structlog.get_logger(__name__)


class WorkerType(Enum):
    """Worker类型枚举"""
    ENUM = "scan_enum"      # 目录枚举和manifest解析
    META = "scan_meta"      # MOD元数据解析
    LANG = "scan_lang"      # 语言文件解析  
    VERIFY = "scan_verify"  # 去重/冲突检测/统计


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    RETRYING = "retrying"    # 重试中


@dataclass
class WorkTask:
    """Worker任务"""
    task_id: int
    task_type: WorkerType
    session_id: str
    payload: Dict[str, Any]
    priority: int
    status: TaskStatus
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass 
class WorkerResult:
    """Worker处理结果"""
    task_id: int
    success: bool
    events: List[ScanEvent]
    checkpoint_data: Optional[Dict] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict] = None


class BaseWorker(ABC):
    """Worker基类"""
    
    def __init__(self, worker_type: WorkerType, db_path: str):
        self.worker_type = worker_type
        self.db_path = db_path
        self.checkpoint_manager = CheckpointManager(db_path)
        self.is_running = False
        
    @abstractmethod
    async def process_task(self, task: WorkTask) -> WorkerResult:
        """处理任务 - 子类必须实现"""
        pass
    
    async def handle_task(self, task: WorkTask) -> WorkerResult:
        """任务处理包装器，包含错误处理和检查点恢复"""
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now().isoformat()
        
        logger.info(f"🔧 {self.worker_type.value}开始处理任务", 
                   task_id=task.task_id, session_id=task.session_id)
        
        try:
            # 尝试从检查点恢复
            checkpoint = self.checkpoint_manager.load_checkpoint(
                task.session_id, 
                task.task_type.value,
                str(task.payload.get('entity_ref', ''))
            )
            
            if checkpoint:
                logger.info(f"📋 从检查点恢复任务", checkpoint_id=checkpoint.checkpoint_id)
                # 将检查点数据添加到任务payload中
                task.payload['checkpoint'] = checkpoint.context
            
            # 执行具体的任务处理
            result = await self.process_task(task)
            
            if result.success:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                
                # 任务完成，删除检查点
                if checkpoint:
                    self.checkpoint_manager.mark_task_completed(
                        task.session_id,
                        task.task_type.value, 
                        str(task.payload.get('entity_ref', ''))
                    )
                
                logger.info(f"✅ {self.worker_type.value}任务完成",
                           task_id=task.task_id, events_count=len(result.events))
            else:
                task.status = TaskStatus.FAILED
                task.error_message = result.error_message
                
                logger.error(f"❌ {self.worker_type.value}任务失败",
                            task_id=task.task_id, error=result.error_message)
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            
            logger.error(f"❌ {self.worker_type.value}任务异常",
                        task_id=task.task_id, error=str(e))
            
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                events=[],
                error_message=str(e)
            )


class WorkerManager:
    """Worker管理器 - 负责任务分发和Worker生命周期管理"""
    
    def __init__(self, db_path: str, event_applier: EventApplier):
        self.db_path = db_path
        self.event_applier = event_applier
        self.workers: Dict[WorkerType, BaseWorker] = {}
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.is_running = False
        self.max_concurrent_tasks = 4  # 最大并发任务数
        
    def register_worker(self, worker: BaseWorker):
        """注册Worker"""
        self.workers[worker.worker_type] = worker
        logger.info(f"📝 注册Worker", worker_type=worker.worker_type.value)
    
    async def start(self):
        """启动Worker管理器"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 WorkerManager已启动", max_concurrent=self.max_concurrent_tasks)
        
        # 启动任务轮询
        asyncio.create_task(self._task_polling_loop())
    
    def stop(self):
        """停止Worker管理器"""
        self.is_running = False
        
        # 取消所有运行中的任务
        for task in self.running_tasks.values():
            task.cancel()
        
        logger.info("🛑 WorkerManager已停止")
    
    async def _task_polling_loop(self):
        """任务轮询循环"""
        while self.is_running:
            try:
                # 检查是否有可用的并发槽位
                if len(self.running_tasks) < self.max_concurrent_tasks:
                    # 获取下一个待处理任务
                    task = self._get_next_task()
                    
                    if task:
                        # 创建异步任务处理
                        async_task = asyncio.create_task(self._process_task_async(task))
                        self.running_tasks[task.task_id] = async_task
                
                # 清理已完成的任务
                await self._cleanup_completed_tasks()
                
                # 轮询间隔
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error("❌ 任务轮询异常", error=str(e))
                await asyncio.sleep(1)
    
    def _get_next_task(self) -> Optional[WorkTask]:
        """获取下一个待处理任务（按优先级排序）"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT id, type, priority, payload_json, created_at
                FROM ops_work_queue 
                WHERE type IN ('scan_enum', 'scan_meta', 'scan_lang', 'scan_verify')
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                return None
            
            task_id, task_type, priority, payload_json, created_at = row
            payload = json.loads(payload_json)
            
            # 删除已获取的任务
            conn.execute("DELETE FROM ops_work_queue WHERE id = ?", (task_id,))
            conn.commit()
            
            return WorkTask(
                task_id=task_id,
                task_type=WorkerType(task_type),
                session_id=payload.get('session_id', ''),
                payload=payload,
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=created_at
            )
            
        finally:
            conn.close()
    
    async def _process_task_async(self, task: WorkTask):
        """异步处理任务"""
        try:
            # 获取对应的Worker
            worker = self.workers.get(task.task_type)
            if not worker:
                logger.error(f"❌ 未找到Worker", worker_type=task.task_type.value)
                return
            
            # 处理任务
            result = await worker.handle_task(task)
            
            # 提交事件到EventApplier
            for event in result.events:
                self.event_applier.submit_event(event)
            
            logger.debug(f"📤 提交事件", task_id=task.task_id, 
                        events_count=len(result.events))
            
        except Exception as e:
            logger.error(f"❌ 任务处理异常", task_id=task.task_id, error=str(e))
        
        finally:
            # 从运行任务列表中移除
            self.running_tasks.pop(task.task_id, None)
    
    async def _cleanup_completed_tasks(self):
        """清理已完成的任务"""
        completed_tasks = []
        
        for task_id, async_task in self.running_tasks.items():
            if async_task.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            self.running_tasks.pop(task_id, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Worker统计信息"""
        return {
            'is_running': self.is_running,
            'registered_workers': list(self.workers.keys()),
            'running_tasks_count': len(self.running_tasks),
            'max_concurrent_tasks': self.max_concurrent_tasks
        }