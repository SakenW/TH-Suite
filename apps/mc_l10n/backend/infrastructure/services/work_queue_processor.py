"""
V5架构 - 工作队列处理器
提供异步任务处理和队列管理功能
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.repositories.ops_work_queue_repository_v2 import TaskState, WorkQueueTask

logger = logging.getLogger(__name__)


class WorkQueueProcessor:
    """工作队列处理器 - 异步任务处理引擎"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self.queue_repo = self.factory.get_ops_work_queue_repo()
        self.task_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}
        self.running = False
        self.worker_name = "default_worker"
        self.lease_duration = 30  # 租约持续时间（分钟）
        self.poll_interval = 5    # 轮询间隔（秒）
        
    def register_handler(self, task_type: str, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        logger.info(f"已注册任务处理器: {task_type}")
        
    async def start(self):
        """启动工作队列处理器"""
        self.running = True
        logger.info(f"工作队列处理器已启动: {self.worker_name}")
        
        while self.running:
            try:
                await self._process_pending_tasks()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"工作队列处理循环错误: {e}")
                await asyncio.sleep(self.poll_interval)
                
    async def stop(self):
        """停止工作队列处理器"""
        self.running = False
        logger.info(f"工作队列处理器已停止: {self.worker_name}")
        
    async def _process_pending_tasks(self):
        """处理待处理任务"""
        try:
            # 清理过期租约
            expired_count = self.queue_repo.cleanup_expired_leases()
            if expired_count > 0:
                logger.info(f"清理了 {expired_count} 个过期租约")
                
            # 获取待处理任务
            pending_tasks = self.queue_repo.get_pending_tasks(limit=5)
            
            for task in pending_tasks:
                if not self.running:
                    break
                    
                # 尝试获取任务租约
                success = self.queue_repo.mark_as_running(
                    task.id, 
                    self.worker_name, 
                    self.lease_duration
                )
                
                if success:
                    logger.info(f"开始处理任务: {task.id} ({task.task_type})")
                    await self._execute_task(task)
                    
        except Exception as e:
            logger.error(f"处理待处理任务时出错: {e}")
            
    async def _execute_task(self, task: WorkQueueTask):
        """执行单个任务"""
        try:
            # 检查是否有注册的处理器
            if task.task_type not in self.task_handlers:
                error_msg = f"未找到任务类型的处理器: {task.task_type}"
                logger.warning(error_msg)
                self.queue_repo.mark_as_failed(task.id, error_msg, increment_attempt=True)
                return
                
            # 执行任务处理器
            handler = self.task_handlers[task.task_type]
            result = await handler(task.payload)
            
            # 标记任务完成
            self.queue_repo.mark_as_completed(task.id)
            logger.info(f"任务完成: {task.id} ({task.task_type})")
            
        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            logger.error(f"任务 {task.id} 执行失败: {e}")
            self.queue_repo.mark_as_failed(task.id, error_msg, increment_attempt=True)
            
    async def submit_task(self, task_type: str, payload: Dict[str, Any], 
                         priority: int = 0, dedupe_key: Optional[str] = None) -> int:
        """提交新任务到队列"""
        task = WorkQueueTask(
            task_type=task_type,
            payload=payload,
            state=TaskState.PENDING,
            priority=priority,
            dedupe_key=dedupe_key
        )
        
        task_id = self.queue_repo.create(task)
        logger.info(f"已提交任务: {task_id} ({task_type})")
        return task_id
        
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        stats = self.queue_repo.get_task_stats()
        return {
            "task_stats": stats,
            "total_tasks": sum(stats.values()),
            "registered_handlers": list(self.task_handlers.keys()),
            "worker_name": self.worker_name,
            "running": self.running
        }


# 默认任务处理器
async def handle_sync_in(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理同步输入任务"""
    logger.info(f"处理同步输入任务: {payload}")
    
    # 模拟同步处理
    await asyncio.sleep(1)
    
    return {"status": "completed", "processed_items": len(payload)}


async def handle_sync_out(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理同步输出任务"""
    logger.info(f"处理同步输出任务: {payload}")
    
    # 模拟同步处理
    await asyncio.sleep(2)
    
    return {"status": "completed", "exported_items": len(payload)}


async def handle_import_delta_block(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理增量导入任务"""
    logger.info(f"处理增量导入任务: {payload}")
    
    # 模拟导入处理
    await asyncio.sleep(3)
    
    return {"status": "completed", "imported_deltas": payload.get("delta_count", 0)}


async def handle_export_stream(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理流式导出任务"""
    logger.info(f"处理流式导出任务: {payload}")
    
    # 模拟流式导出
    await asyncio.sleep(1.5)
    
    return {"status": "completed", "stream_size": payload.get("size", 0)}


async def handle_tm_index(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理翻译记忆索引任务"""
    logger.info(f"处理翻译记忆索引任务: {payload}")
    
    # 模拟索引处理
    await asyncio.sleep(4)
    
    return {"status": "completed", "indexed_entries": payload.get("entry_count", 0)}


async def handle_qa_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理质量保证运行任务"""
    logger.info(f"处理质量保证运行任务: {payload}")
    
    # 模拟QA检查
    await asyncio.sleep(2.5)
    
    return {"status": "completed", "checked_items": payload.get("item_count", 0)}


async def handle_merge_resolve(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理合并解决任务"""
    logger.info(f"处理合并解决任务: {payload}")
    
    # 模拟合并处理
    await asyncio.sleep(3.5)
    
    return {"status": "completed", "resolved_conflicts": payload.get("conflict_count", 0)}


# 全局工作队列处理器实例
work_queue_processor: Optional[WorkQueueProcessor] = None


def get_work_queue_processor() -> WorkQueueProcessor:
    """获取全局工作队列处理器实例"""
    global work_queue_processor
    if work_queue_processor is None:
        work_queue_processor = WorkQueueProcessor()
        
        # 注册默认任务处理器
        work_queue_processor.register_handler("sync_in", handle_sync_in)
        work_queue_processor.register_handler("sync_out", handle_sync_out)
        work_queue_processor.register_handler("import_delta_block", handle_import_delta_block)
        work_queue_processor.register_handler("export_stream", handle_export_stream)
        work_queue_processor.register_handler("tm_index", handle_tm_index)
        work_queue_processor.register_handler("qa_run", handle_qa_run)
        work_queue_processor.register_handler("merge_resolve", handle_merge_resolve)
        
        logger.info("工作队列处理器已初始化，注册了7个默认处理器")
        
    return work_queue_processor


async def start_work_queue_processor():
    """启动工作队列处理器（用于应用启动时调用）"""
    processor = get_work_queue_processor()
    await processor.start()


async def stop_work_queue_processor():
    """停止工作队列处理器（用于应用关闭时调用）"""
    global work_queue_processor
    if work_queue_processor:
        await work_queue_processor.stop()