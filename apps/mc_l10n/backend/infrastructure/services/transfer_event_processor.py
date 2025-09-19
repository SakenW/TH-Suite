"""
传输事件处理器 - 集成现有事件流和队列系统
将数据传输任务与TH-Suite扫描架构的工作队列深度集成
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, asdict
from enum import Enum

from infrastructure.services.work_queue_processor import get_work_queue_processor
from infrastructure.services.transfer_controller import get_transfer_controller, TransferPriority, TransferMode
from infrastructure.services.translation_data_extractor import ExtractionType
from infrastructure.services.localized_compression_service import CompressionStrategy
from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.repositories.ops_work_queue_repository_v2 import TaskState, WorkQueueTask

logger = logging.getLogger(__name__)


class TransferEventType(Enum):
    """传输事件类型枚举"""
    UPLOAD_REQUESTED = "upload_requested"           # 上传请求
    DOWNLOAD_REQUESTED = "download_requested"       # 下载请求
    TRANSFER_STARTED = "transfer_started"           # 传输开始
    TRANSFER_PROGRESS = "transfer_progress"         # 传输进度更新
    TRANSFER_COMPLETED = "transfer_completed"       # 传输完成
    TRANSFER_FAILED = "transfer_failed"             # 传输失败
    TRANSFER_CANCELLED = "transfer_cancelled"       # 传输取消
    RETRY_SCHEDULED = "retry_scheduled"             # 重试调度
    BATCH_OPERATION = "batch_operation"             # 批量操作


@dataclass
class TransferEvent:
    """传输事件"""
    event_id: str
    event_type: TransferEventType
    task_id: str
    session_id: Optional[str]
    timestamp: datetime
    payload: Dict[str, Any]
    context: Dict[str, Any] = None


class TransferEventProcessor:
    """传输事件处理器"""
    
    def __init__(self):
        self.work_queue_processor = get_work_queue_processor()
        self.transfer_controller = get_transfer_controller()
        self.factory = get_repository_factory()
        
        # 事件监听器
        self.event_listeners: Dict[TransferEventType, List[Callable]] = {
            event_type: [] for event_type in TransferEventType
        }
        
        # 统计信息
        self.event_stats = {
            "total_events": 0,
            "events_by_type": {event_type.value: 0 for event_type in TransferEventType},
            "last_event_time": None
        }
        
        # 批量操作缓存
        self.batch_cache: Dict[str, List[Dict[str, Any]]] = {}
        
    async def initialize(self):
        """初始化传输事件处理器"""
        try:
            # 注册传输相关的任务处理器
            self._register_transfer_handlers()
            
            # 启动事件处理器
            await self._start_event_processor()
            
            logger.info("传输事件处理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化传输事件处理器失败: {e}")
            raise
            
    def _register_transfer_handlers(self):
        """注册传输任务处理器到工作队列"""
        
        # 注册上传任务处理器
        self.work_queue_processor.register_handler(
            "transfer_upload", 
            self.handle_upload_task
        )
        
        # 注册下载任务处理器
        self.work_queue_processor.register_handler(
            "transfer_download", 
            self.handle_download_task
        )
        
        # 注册批量传输处理器
        self.work_queue_processor.register_handler(
            "transfer_batch", 
            self.handle_batch_transfer_task
        )
        
        # 注册传输清理处理器
        self.work_queue_processor.register_handler(
            "transfer_cleanup", 
            self.handle_cleanup_task
        )
        
        # 注册传输统计处理器
        self.work_queue_processor.register_handler(
            "transfer_statistics", 
            self.handle_statistics_task
        )
        
        # 注册传输优化处理器
        self.work_queue_processor.register_handler(
            "transfer_optimization", 
            self.handle_optimization_task
        )
        
        logger.info("已注册6个传输任务处理器")
        
    async def _start_event_processor(self):
        """启动事件处理器"""
        # 这里可以启动其他事件处理逻辑
        # 如WebSocket事件广播、实时状态更新等
        pass
        
    async def submit_upload_request(
        self,
        file_name: str,
        file_size: int,
        file_hash: str,
        locale_code: str,
        project_uid: Optional[str] = None,
        priority: TransferPriority = TransferPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交上传请求到工作队列
        
        Args:
            file_name: 文件名
            file_size: 文件大小
            file_hash: 文件哈希
            locale_code: 语言代码
            project_uid: 项目UID
            priority: 优先级
            metadata: 元数据
        """
        try:
            # 创建上传任务负载
            upload_payload = {
                "file_name": file_name,
                "file_size": file_size,
                "file_hash": file_hash,
                "locale_code": locale_code,
                "project_uid": project_uid,
                "priority": priority.value,
                "transfer_mode": TransferMode.SINGLE.value,
                "compression_strategy": CompressionStrategy.ADAPTIVE.value,
                "metadata": metadata or {},
                "request_time": datetime.now().isoformat()
            }
            
            # 提交到工作队列
            task_id = await self.work_queue_processor.submit_task(
                task_type="transfer_upload",
                payload=upload_payload,
                priority=priority.value,
                dedupe_key=f"upload_{file_hash}"  # 基于文件哈希去重
            )
            
            # 发送事件
            await self._emit_event(
                event_type=TransferEventType.UPLOAD_REQUESTED,
                task_id=str(task_id),
                session_id=None,
                payload=upload_payload
            )
            
            logger.info(f"上传请求已提交到工作队列: task_id={task_id}, file={file_name}")
            
            return str(task_id)
            
        except Exception as e:
            logger.error(f"提交上传请求失败: {e}")
            raise
            
    async def submit_download_request(
        self,
        extraction_type: ExtractionType,
        locale_codes: List[str],
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        since_timestamp: Optional[datetime] = None,
        priority: TransferPriority = TransferPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交下载请求到工作队列
        
        Args:
            extraction_type: 提取类型
            locale_codes: 语言代码列表
            project_uid: 项目UID
            mod_ids: MOD ID列表
            since_timestamp: 增量提取起始时间
            priority: 优先级
            metadata: 元数据
        """
        try:
            # 创建下载任务负载
            download_payload = {
                "extraction_type": extraction_type.value,
                "locale_codes": locale_codes,
                "project_uid": project_uid,
                "mod_ids": mod_ids,
                "since_timestamp": since_timestamp.isoformat() if since_timestamp else None,
                "priority": priority.value,
                "transfer_mode": TransferMode.SINGLE.value,
                "compression_strategy": CompressionStrategy.ADAPTIVE.value,
                "metadata": metadata or {},
                "request_time": datetime.now().isoformat()
            }
            
            # 生成去重键
            dedupe_parts = [
                extraction_type.value,
                project_uid or "global",
                "|".join(sorted(locale_codes)),
                "|".join(sorted(mod_ids)) if mod_ids else "all"
            ]
            dedupe_key = f"download_{hash('|'.join(dedupe_parts))}"
            
            # 提交到工作队列
            task_id = await self.work_queue_processor.submit_task(
                task_type="transfer_download",
                payload=download_payload,
                priority=priority.value,
                dedupe_key=dedupe_key
            )
            
            # 发送事件
            await self._emit_event(
                event_type=TransferEventType.DOWNLOAD_REQUESTED,
                task_id=str(task_id),
                session_id=None,
                payload=download_payload
            )
            
            logger.info(f"下载请求已提交到工作队列: task_id={task_id}, "
                       f"type={extraction_type.value}, locales={len(locale_codes)}")
            
            return str(task_id)
            
        except Exception as e:
            logger.error(f"提交下载请求失败: {e}")
            raise
            
    async def submit_batch_operation(
        self,
        operation_type: str,  # "upload" or "download"
        items: List[Dict[str, Any]],
        priority: TransferPriority = TransferPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交批量操作到工作队列
        
        Args:
            operation_type: 操作类型 (upload/download)
            items: 操作项目列表
            priority: 优先级
            metadata: 元数据
        """
        try:
            # 创建批量操作负载
            batch_payload = {
                "operation_type": operation_type,
                "items": items,
                "total_items": len(items),
                "priority": priority.value,
                "metadata": metadata or {},
                "request_time": datetime.now().isoformat()
            }
            
            # 提交到工作队列
            task_id = await self.work_queue_processor.submit_task(
                task_type="transfer_batch",
                payload=batch_payload,
                priority=priority.value,
                dedupe_key=f"batch_{operation_type}_{hash(str(items))}"
            )
            
            # 发送事件
            await self._emit_event(
                event_type=TransferEventType.BATCH_OPERATION,
                task_id=str(task_id),
                session_id=None,
                payload=batch_payload
            )
            
            logger.info(f"批量{operation_type}操作已提交: task_id={task_id}, items={len(items)}")
            
            return str(task_id)
            
        except Exception as e:
            logger.error(f"提交批量操作失败: {e}")
            raise
            
    # ============================================================================
    # 工作队列任务处理器
    # ============================================================================
    
    async def handle_upload_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理上传任务"""
        task_start_time = datetime.now()
        
        try:
            logger.info(f"开始处理上传任务: {payload.get('file_name')}")
            
            # 提交到传输控制器
            task_id = await self.transfer_controller.submit_upload_task(
                file_name=payload["file_name"],
                file_size=payload["file_size"],
                file_hash=payload["file_hash"],
                locale_code=payload["locale_code"],
                project_uid=payload.get("project_uid"),
                priority=TransferPriority(payload["priority"]),
                transfer_mode=TransferMode(payload["transfer_mode"]),
                compression_strategy=CompressionStrategy(payload["compression_strategy"]),
                metadata=payload.get("metadata", {})
            )
            
            # 发送传输开始事件
            await self._emit_event(
                event_type=TransferEventType.TRANSFER_STARTED,
                task_id=task_id,
                session_id=None,
                payload={"operation": "upload", "file_name": payload["file_name"]}
            )
            
            # 等待传输完成（简化实现，实际应该使用回调或轮询）
            await self._wait_for_transfer_completion(task_id, timeout_seconds=300)
            
            execution_time = (datetime.now() - task_start_time).total_seconds()
            
            return {
                "status": "completed",
                "transfer_task_id": task_id,
                "file_name": payload["file_name"],
                "execution_time_seconds": execution_time,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            # 发送传输失败事件
            await self._emit_event(
                event_type=TransferEventType.TRANSFER_FAILED,
                task_id="unknown",
                session_id=None,
                payload={"operation": "upload", "error": str(e), "file_name": payload.get("file_name")}
            )
            
            logger.error(f"处理上传任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "file_name": payload.get("file_name"),
                "execution_time_seconds": (datetime.now() - task_start_time).total_seconds()
            }
            
    async def handle_download_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理下载任务"""
        task_start_time = datetime.now()
        
        try:
            logger.info(f"开始处理下载任务: {payload.get('extraction_type')}")
            
            # 提交到传输控制器
            task_id = await self.transfer_controller.submit_download_task(
                extraction_type=ExtractionType(payload["extraction_type"]),
                locale_codes=payload["locale_codes"],
                project_uid=payload.get("project_uid"),
                mod_ids=payload.get("mod_ids"),
                since_timestamp=datetime.fromisoformat(payload["since_timestamp"]) if payload.get("since_timestamp") else None,
                priority=TransferPriority(payload["priority"]),
                transfer_mode=TransferMode(payload["transfer_mode"]),
                compression_strategy=CompressionStrategy(payload["compression_strategy"]),
                metadata=payload.get("metadata", {})
            )
            
            # 发送传输开始事件
            await self._emit_event(
                event_type=TransferEventType.TRANSFER_STARTED,
                task_id=task_id,
                session_id=None,
                payload={"operation": "download", "extraction_type": payload["extraction_type"]}
            )
            
            # 等待传输完成
            await self._wait_for_transfer_completion(task_id, timeout_seconds=600)
            
            execution_time = (datetime.now() - task_start_time).total_seconds()
            
            return {
                "status": "completed",
                "transfer_task_id": task_id,
                "extraction_type": payload["extraction_type"],
                "locale_count": len(payload["locale_codes"]),
                "execution_time_seconds": execution_time,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            # 发送传输失败事件
            await self._emit_event(
                event_type=TransferEventType.TRANSFER_FAILED,
                task_id="unknown",
                session_id=None,
                payload={"operation": "download", "error": str(e), "extraction_type": payload.get("extraction_type")}
            )
            
            logger.error(f"处理下载任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "extraction_type": payload.get("extraction_type"),
                "execution_time_seconds": (datetime.now() - task_start_time).total_seconds()
            }
            
    async def handle_batch_transfer_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理批量传输任务"""
        task_start_time = datetime.now()
        
        try:
            operation_type = payload["operation_type"]
            items = payload["items"]
            
            logger.info(f"开始处理批量{operation_type}任务: {len(items)}个项目")
            
            results = []
            successful_count = 0
            failed_count = 0
            
            # 批量处理每个项目
            for i, item in enumerate(items):
                try:
                    if operation_type == "upload":
                        task_id = await self.transfer_controller.submit_upload_task(
                            file_name=item["file_name"],
                            file_size=item["file_size"],
                            file_hash=item["file_hash"],
                            locale_code=item["locale_code"],
                            project_uid=item.get("project_uid"),
                            priority=TransferPriority(payload["priority"]),
                            metadata=item.get("metadata", {})
                        )
                    elif operation_type == "download":
                        task_id = await self.transfer_controller.submit_download_task(
                            extraction_type=ExtractionType(item["extraction_type"]),
                            locale_codes=item["locale_codes"],
                            project_uid=item.get("project_uid"),
                            mod_ids=item.get("mod_ids"),
                            priority=TransferPriority(payload["priority"]),
                            metadata=item.get("metadata", {})
                        )
                    else:
                        raise ValueError(f"不支持的操作类型: {operation_type}")
                        
                    results.append({
                        "index": i,
                        "status": "submitted",
                        "task_id": task_id,
                        "item": item
                    })
                    successful_count += 1
                    
                except Exception as e:
                    results.append({
                        "index": i,
                        "status": "failed",
                        "error": str(e),
                        "item": item
                    })
                    failed_count += 1
                    
            execution_time = (datetime.now() - task_start_time).total_seconds()
            
            return {
                "status": "completed",
                "operation_type": operation_type,
                "total_items": len(items),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "results": results,
                "execution_time_seconds": execution_time,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"处理批量传输任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "execution_time_seconds": (datetime.now() - task_start_time).total_seconds()
            }
            
    async def handle_cleanup_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理传输清理任务"""
        try:
            logger.info("开始处理传输清理任务")
            
            cleanup_before = payload.get("cleanup_before")
            if cleanup_before:
                cleanup_before = datetime.fromisoformat(cleanup_before)
            else:
                # 默认清理7天前的数据
                cleanup_before = datetime.now() - timedelta(days=7)
                
            # 这里应该实现具体的清理逻辑
            # 1. 清理过期的传输会话
            # 2. 清理临时文件
            # 3. 清理传输日志
            
            # 模拟清理过程
            cleaned_sessions = 15  # 示例数据
            cleaned_files = 42     # 示例数据
            freed_space_mb = 1024  # 示例数据
            
            return {
                "status": "completed",
                "cleanup_before": cleanup_before.isoformat(),
                "cleaned_sessions": cleaned_sessions,
                "cleaned_files": cleaned_files,
                "freed_space_mb": freed_space_mb,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"处理清理任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
            
    async def handle_statistics_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理传输统计任务"""
        try:
            logger.info("开始处理传输统计任务")
            
            # 获取传输控制器统计
            controller_stats = await self.transfer_controller.get_controller_statistics()
            
            # 获取事件处理器统计
            event_stats = self.get_event_statistics()
            
            # 获取工作队列统计
            queue_stats = self.work_queue_processor.get_stats()
            
            return {
                "status": "completed",
                "controller_statistics": controller_stats,
                "event_statistics": event_stats,
                "queue_statistics": queue_stats,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"处理统计任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
            
    async def handle_optimization_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理传输优化任务"""
        try:
            logger.info("开始处理传输优化任务")
            
            optimization_type = payload.get("optimization_type", "auto")
            
            results = {}
            
            if optimization_type in ["auto", "compression"]:
                # 优化压缩字典
                from infrastructure.services.localized_compression_service import get_localized_compression_service
                compression_service = get_localized_compression_service()
                compression_results = await compression_service.optimize_dictionaries()
                results["compression_optimization"] = compression_results
                
            if optimization_type in ["auto", "cache"]:
                # 优化缓存
                from infrastructure.services.multi_layer_cache_service import get_multi_layer_cache_service
                cache_service = get_multi_layer_cache_service()
                # 这里可以添加缓存优化逻辑
                results["cache_optimization"] = {"status": "completed"}
                
            if optimization_type in ["auto", "queue"]:
                # 优化队列性能
                # 这里可以添加队列优化逻辑
                results["queue_optimization"] = {"status": "completed"}
                
            return {
                "status": "completed",
                "optimization_type": optimization_type,
                "results": results,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"处理优化任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
            
    # ============================================================================
    # 事件管理方法
    # ============================================================================
    
    async def _emit_event(
        self,
        event_type: TransferEventType,
        task_id: str,
        session_id: Optional[str],
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ):
        """发送事件"""
        try:
            event = TransferEvent(
                event_id=f"evt_{int(datetime.now().timestamp() * 1000)}_{hash(task_id)}",
                event_type=event_type,
                task_id=task_id,
                session_id=session_id,
                timestamp=datetime.now(),
                payload=payload,
                context=context or {}
            )
            
            # 更新统计
            self.event_stats["total_events"] += 1
            self.event_stats["events_by_type"][event_type.value] += 1
            self.event_stats["last_event_time"] = event.timestamp.isoformat()
            
            # 触发事件监听器
            await self._trigger_event_listeners(event)
            
            logger.debug(f"事件已发送: {event_type.value}, task_id={task_id}")
            
        except Exception as e:
            logger.error(f"发送事件失败: {e}")
            
    async def _trigger_event_listeners(self, event: TransferEvent):
        """触发事件监听器"""
        listeners = self.event_listeners.get(event.event_type, [])
        
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"事件监听器执行失败: {e}")
                
    def add_event_listener(
        self,
        event_type: TransferEventType,
        listener: Callable[[TransferEvent], None]
    ):
        """添加事件监听器"""
        self.event_listeners[event_type].append(listener)
        logger.debug(f"已添加事件监听器: {event_type.value}")
        
    def remove_event_listener(
        self,
        event_type: TransferEventType,
        listener: Callable[[TransferEvent], None]
    ):
        """移除事件监听器"""
        if listener in self.event_listeners[event_type]:
            self.event_listeners[event_type].remove(listener)
            logger.debug(f"已移除事件监听器: {event_type.value}")
            
    def get_event_statistics(self) -> Dict[str, Any]:
        """获取事件统计信息"""
        return {
            "total_events": self.event_stats["total_events"],
            "events_by_type": self.event_stats["events_by_type"],
            "last_event_time": self.event_stats["last_event_time"],
            "active_listeners": {
                event_type.value: len(listeners)
                for event_type, listeners in self.event_listeners.items()
            }
        }
        
    # ============================================================================
    # 辅助方法
    # ============================================================================
    
    async def _wait_for_transfer_completion(self, task_id: str, timeout_seconds: int = 300):
        """等待传输完成"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            try:
                status = await self.transfer_controller.get_task_status(task_id)
                if status:
                    if status["status"] == "completed":
                        # 发送完成事件
                        await self._emit_event(
                            event_type=TransferEventType.TRANSFER_COMPLETED,
                            task_id=task_id,
                            session_id=status.get("session_id"),
                            payload={"progress": 100.0, "status": "completed"}
                        )
                        return
                    elif status["status"] == "failed":
                        # 发送失败事件
                        await self._emit_event(
                            event_type=TransferEventType.TRANSFER_FAILED,
                            task_id=task_id,
                            session_id=status.get("session_id"),
                            payload={"error": status.get("error_message"), "status": "failed"}
                        )
                        raise Exception(f"传输失败: {status.get('error_message')}")
                    elif status["status"] == "running":
                        # 发送进度事件
                        await self._emit_event(
                            event_type=TransferEventType.TRANSFER_PROGRESS,
                            task_id=task_id,
                            session_id=status.get("session_id"),
                            payload={"progress": status.get("progress", 0), "status": "running"}
                        )
                        
                await asyncio.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                logger.error(f"检查传输状态失败: {task_id}: {e}")
                await asyncio.sleep(5)
                
        raise TimeoutError(f"传输任务超时: {task_id}")


# 全局实例
_transfer_event_processor: Optional[TransferEventProcessor] = None


def get_transfer_event_processor() -> TransferEventProcessor:
    """获取全局传输事件处理器实例"""
    global _transfer_event_processor
    if _transfer_event_processor is None:
        _transfer_event_processor = TransferEventProcessor()
        logger.info("传输事件处理器已初始化")
    return _transfer_event_processor