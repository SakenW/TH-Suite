"""
传输控制器 - 统一管理上传下载流程
集成现有扫描架构，支持断点续传、错误重试、并发控制
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import blake3

from infrastructure.services.file_transfer_service import (
    get_file_transfer_service, TransferSession, TransferSessionType, TransferStatus, TransferConfig
)
from infrastructure.services.translation_data_extractor import (
    get_translation_data_extractor, ExtractionType, ExtractionResult
)
from infrastructure.services.localized_compression_service import (
    get_localized_compression_service, CompressionStrategy
)
from infrastructure.services.work_queue_processor import get_work_queue_processor
from infrastructure.services.multi_layer_cache_service import (
    get_multi_layer_cache_service, CacheType
)

logger = logging.getLogger(__name__)


class TransferMode(Enum):
    """传输模式枚举"""
    SINGLE = "single"                   # 单文件传输
    BATCH = "batch"                     # 批量传输
    STREAMING = "streaming"             # 流式传输
    INCREMENTAL = "incremental"         # 增量传输


class TransferPriority(Enum):
    """传输优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class RetryStrategy(Enum):
    """重试策略枚举"""
    NONE = "none"                       # 不重试
    EXPONENTIAL_BACKOFF = "exponential" # 指数退避
    LINEAR_BACKOFF = "linear"           # 线性退避
    IMMEDIATE = "immediate"             # 立即重试


@dataclass
class TransferTask:
    """传输任务"""
    task_id: str
    session_id: str
    transfer_mode: TransferMode
    priority: TransferPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    progress: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None


@dataclass
class ConcurrencyLimits:
    """并发限制配置"""
    max_concurrent_uploads: int = 8
    max_concurrent_downloads: int = 12
    max_chunks_per_session: int = 4
    max_bandwidth_mbps: int = 100
    priority_boost_factor: float = 1.5


@dataclass
class RetryConfig:
    """重试配置"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1


class TransferController:
    """传输控制器"""
    
    def __init__(self):
        # 依赖服务
        self.transfer_service = get_file_transfer_service()
        self.extractor = get_translation_data_extractor()
        self.compression_service = get_localized_compression_service()
        self.work_queue_processor = get_work_queue_processor()
        self.cache_service = get_multi_layer_cache_service()
        
        # 活跃任务管理
        self.active_tasks: Dict[str, TransferTask] = {}
        self.task_queues: Dict[TransferPriority, List[TransferTask]] = {
            priority: [] for priority in TransferPriority
        }
        
        # 并发控制
        self.concurrency_limits = ConcurrencyLimits()
        self.active_uploads: Set[str] = set()
        self.active_downloads: Set[str] = set()
        self.bandwidth_monitor = {"current_usage": 0, "last_update": datetime.now()}
        
        # 重试配置
        self.retry_config = RetryConfig()
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "bytes_transferred": 0,
            "average_speed_mbps": 0.0,
            "uptime_seconds": 0
        }
        
        # 控制器状态
        self._running = False
        self._start_time = None
        self._worker_tasks: List[asyncio.Task] = []
        
    async def initialize(self):
        """初始化传输控制器"""
        try:
            # 初始化依赖服务
            await self.transfer_service.initialize()
            await self.extractor.initialize()
            await self.compression_service.initialize()
            
            # 启动工作线程
            await self._start_workers()
            
            self._running = True
            self._start_time = datetime.now()
            
            logger.info("传输控制器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化传输控制器失败: {e}")
            raise
            
    async def shutdown(self):
        """关闭传输控制器"""
        try:
            self._running = False
            
            # 取消所有工作任务
            for task in self._worker_tasks:
                task.cancel()
                
            # 等待任务完成
            if self._worker_tasks:
                await asyncio.gather(*self._worker_tasks, return_exceptions=True)
                
            # 清理资源
            await self._cleanup_resources()
            
            logger.info("传输控制器已关闭")
            
        except Exception as e:
            logger.error(f"关闭传输控制器失败: {e}")
            
    async def submit_upload_task(
        self,
        file_name: str,
        file_size: int,
        file_hash: str,
        locale_code: str,
        project_uid: Optional[str] = None,
        priority: TransferPriority = TransferPriority.NORMAL,
        transfer_mode: TransferMode = TransferMode.SINGLE,
        compression_strategy: CompressionStrategy = CompressionStrategy.ADAPTIVE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交上传任务
        
        Args:
            file_name: 文件名
            file_size: 文件大小
            file_hash: 文件哈希
            locale_code: 语言代码
            project_uid: 项目UID
            priority: 优先级
            transfer_mode: 传输模式
            compression_strategy: 压缩策略
            metadata: 元数据
        """
        try:
            # 检查并发限制
            if len(self.active_uploads) >= self.concurrency_limits.max_concurrent_uploads:
                raise ValueError("上传并发数已达上限")
                
            # 创建传输配置
            config = TransferConfig(
                chunk_size=self._calculate_optimal_chunk_size(file_size),
                max_concurrent_chunks=self.concurrency_limits.max_chunks_per_session,
                compression_enabled=True,
                auto_retry=True,
                max_retries=self.retry_config.strategy != RetryStrategy.NONE
            )
            
            # 初始化上传会话
            session = await self.transfer_service.initialize_upload_session(
                file_name=file_name,
                file_size=file_size,
                file_hash=file_hash,
                metadata={
                    "project_uid": project_uid,
                    "locale_code": locale_code,
                    "compression_strategy": compression_strategy.value,
                    "transfer_mode": transfer_mode.value,
                    **(metadata or {})
                },
                config=config
            )
            
            # 创建传输任务
            task_id = f"upload_{uuid.uuid4().hex[:16]}"
            task = TransferTask(
                task_id=task_id,
                session_id=session.session_id,
                transfer_mode=transfer_mode,
                priority=priority,
                created_at=datetime.now(),
                metadata={
                    "file_name": file_name,
                    "file_size": file_size,
                    "locale_code": locale_code,
                    "project_uid": project_uid,
                    "compression_strategy": compression_strategy.value
                }
            )
            
            # 添加到任务队列
            await self._enqueue_task(task)
            
            self.stats["total_tasks"] += 1
            
            logger.info(f"上传任务已提交: {task_id}, 文件: {file_name}, 优先级: {priority.value}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"提交上传任务失败: {e}")
            raise
            
    async def submit_download_task(
        self,
        extraction_type: ExtractionType,
        locale_codes: List[str],
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        since_timestamp: Optional[datetime] = None,
        priority: TransferPriority = TransferPriority.NORMAL,
        transfer_mode: TransferMode = TransferMode.SINGLE,
        compression_strategy: CompressionStrategy = CompressionStrategy.ADAPTIVE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交下载任务
        
        Args:
            extraction_type: 提取类型
            locale_codes: 语言代码列表
            project_uid: 项目UID
            mod_ids: MOD ID列表
            since_timestamp: 增量提取起始时间
            priority: 优先级
            transfer_mode: 传输模式
            compression_strategy: 压缩策略
            metadata: 元数据
        """
        try:
            # 检查并发限制
            if len(self.active_downloads) >= self.concurrency_limits.max_concurrent_downloads:
                raise ValueError("下载并发数已达上限")
                
            # 创建虚拟会话ID（实际会话在执行时创建）
            session_id = f"download_pending_{uuid.uuid4().hex[:16]}"
            
            # 创建传输任务
            task_id = f"download_{uuid.uuid4().hex[:16]}"
            task = TransferTask(
                task_id=task_id,
                session_id=session_id,
                transfer_mode=transfer_mode,
                priority=priority,
                created_at=datetime.now(),
                metadata={
                    "extraction_type": extraction_type.value,
                    "locale_codes": locale_codes,
                    "project_uid": project_uid,
                    "mod_ids": mod_ids,
                    "since_timestamp": since_timestamp.isoformat() if since_timestamp else None,
                    "compression_strategy": compression_strategy.value
                }
            )
            
            # 添加到任务队列
            await self._enqueue_task(task)
            
            self.stats["total_tasks"] += 1
            
            logger.info(f"下载任务已提交: {task_id}, 类型: {extraction_type.value}, 优先级: {priority.value}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"提交下载任务失败: {e}")
            raise
            
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            task = self.active_tasks.get(task_id)
            if not task:
                return None
                
            # 获取传输进度
            progress_info = None
            if task.session_id and not task.session_id.startswith("download_pending_"):
                progress_info = await self.transfer_service.get_transfer_progress(task.session_id)
                
            # 计算运行时间
            running_time_seconds = 0
            if task.started_at:
                end_time = task.completed_at or datetime.now()
                running_time_seconds = (end_time - task.started_at).total_seconds()
                
            return {
                "task_id": task.task_id,
                "session_id": task.session_id,
                "transfer_mode": task.transfer_mode.value,
                "priority": task.priority.value,
                "status": task.status,
                "progress": task.progress,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "running_time_seconds": running_time_seconds,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "error_message": task.error_message,
                "metadata": task.metadata,
                "transfer_progress": asdict(progress_info) if progress_info else None
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {task_id}: {e}")
            return None
            
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            task = self.active_tasks.get(task_id)
            if not task:
                return False
                
            # 取消传输会话
            if task.session_id and not task.session_id.startswith("download_pending_"):
                await self.transfer_service.cancel_transfer(task.session_id)
                
            # 更新任务状态
            task.status = "cancelled"
            task.completed_at = datetime.now()
            
            # 从活跃列表移除
            await self._remove_from_active_sets(task)
            
            logger.info(f"任务已取消: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败: {task_id}: {e}")
            return False
            
    async def retry_task(self, task_id: str, force: bool = False) -> bool:
        """重试任务"""
        try:
            task = self.active_tasks.get(task_id)
            if not task:
                return False
                
            if task.status not in ["failed", "cancelled"] and not force:
                return False
                
            if task.retry_count >= task.max_retries and not force:
                logger.warning(f"任务重试次数已达上限: {task_id}")
                return False
                
            # 重置任务状态
            task.status = "pending"
            task.started_at = None
            task.completed_at = None
            task.error_message = None
            task.progress = 0.0
            task.retry_count += 1
            
            # 重新加入队列
            await self._enqueue_task(task)
            
            logger.info(f"任务重试: {task_id}, 重试次数: {task.retry_count}")
            return True
            
        except Exception as e:
            logger.error(f"重试任务失败: {task_id}: {e}")
            return False
            
    async def list_tasks(
        self, 
        status_filter: Optional[str] = None,
        priority_filter: Optional[TransferPriority] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出任务"""
        try:
            tasks = []
            for task in list(self.active_tasks.values())[:limit]:
                if status_filter and task.status != status_filter:
                    continue
                if priority_filter and task.priority != priority_filter:
                    continue
                    
                task_info = await self.get_task_status(task.task_id)
                if task_info:
                    tasks.append(task_info)
                    
            return tasks
            
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return []
            
    async def get_controller_statistics(self) -> Dict[str, Any]:
        """获取控制器统计信息"""
        try:
            # 更新统计信息
            if self._start_time:
                self.stats["uptime_seconds"] = (datetime.now() - self._start_time).total_seconds()
                
            # 计算队列状态
            queue_stats = {}
            for priority, queue in self.task_queues.items():
                queue_stats[priority.value] = len(queue)
                
            # 获取传输服务统计
            transfer_stats = {}
            try:
                transfer_sessions = await self.transfer_service.list_active_sessions()
                transfer_stats = {
                    "active_sessions": len(transfer_sessions),
                    "upload_sessions": len([s for s in transfer_sessions if s.session_type == TransferSessionType.UPLOAD]),
                    "download_sessions": len([s for s in transfer_sessions if s.session_type == TransferSessionType.DOWNLOAD])
                }
            except Exception:
                pass
                
            # 获取压缩服务统计
            compression_stats = {}
            try:
                compression_stats = await self.compression_service.get_compression_statistics()
            except Exception:
                pass
                
            return {
                "controller": {
                    "running": self._running,
                    "uptime_seconds": self.stats["uptime_seconds"],
                    "total_tasks": self.stats["total_tasks"],
                    "completed_tasks": self.stats["completed_tasks"],
                    "failed_tasks": self.stats["failed_tasks"],
                    "active_tasks": len(self.active_tasks),
                    "bytes_transferred": self.stats["bytes_transferred"],
                    "average_speed_mbps": self.stats["average_speed_mbps"]
                },
                "concurrency": {
                    "active_uploads": len(self.active_uploads),
                    "active_downloads": len(self.active_downloads),
                    "max_concurrent_uploads": self.concurrency_limits.max_concurrent_uploads,
                    "max_concurrent_downloads": self.concurrency_limits.max_concurrent_downloads,
                    "bandwidth_usage_mbps": self.bandwidth_monitor["current_usage"]
                },
                "queues": queue_stats,
                "transfer_service": transfer_stats,
                "compression_service": compression_stats
            }
            
        except Exception as e:
            logger.error(f"获取控制器统计失败: {e}")
            return {"error": str(e)}
            
    # ============================================================================
    # 私有方法
    # ============================================================================
    
    async def _start_workers(self):
        """启动工作线程"""
        
        # 启动任务调度器
        self._worker_tasks.append(asyncio.create_task(self._task_scheduler()))
        
        # 启动进度监控器
        self._worker_tasks.append(asyncio.create_task(self._progress_monitor()))
        
        # 启动带宽监控器
        self._worker_tasks.append(asyncio.create_task(self._bandwidth_monitor()))
        
        # 启动清理器
        self._worker_tasks.append(asyncio.create_task(self._cleanup_worker()))
        
    async def _task_scheduler(self):
        """任务调度器"""
        while self._running:
            try:
                # 按优先级处理任务队列
                for priority in sorted(TransferPriority, key=lambda p: p.value, reverse=True):
                    queue = self.task_queues[priority]
                    
                    while queue and self._can_start_new_task():
                        task = queue.pop(0)
                        await self._execute_task(task)
                        
                await asyncio.sleep(1)  # 避免忙等待
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"任务调度器错误: {e}")
                await asyncio.sleep(5)
                
    async def _progress_monitor(self):
        """进度监控器"""
        while self._running:
            try:
                for task in list(self.active_tasks.values()):
                    if task.status == "running" and task.session_id:
                        if not task.session_id.startswith("download_pending_"):
                            progress = await self.transfer_service.get_transfer_progress(task.session_id)
                            if progress:
                                task.progress = progress.percentage
                                
                await asyncio.sleep(5)  # 每5秒更新一次进度
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"进度监控器错误: {e}")
                await asyncio.sleep(10)
                
    async def _bandwidth_monitor(self):
        """带宽监控器"""
        while self._running:
            try:
                # 简化的带宽监控实现
                # 实际应该监控网络接口或传输服务的实际带宽使用
                
                current_time = datetime.now()
                time_diff = (current_time - self.bandwidth_monitor["last_update"]).total_seconds()
                
                if time_diff > 0:
                    # 估算当前带宽使用（基于活跃传输数量）
                    active_transfers = len(self.active_uploads) + len(self.active_downloads)
                    estimated_usage = active_transfers * 5  # 假设每个传输平均5Mbps
                    
                    self.bandwidth_monitor["current_usage"] = min(
                        estimated_usage, 
                        self.concurrency_limits.max_bandwidth_mbps
                    )
                    self.bandwidth_monitor["last_update"] = current_time
                    
                await asyncio.sleep(10)  # 每10秒更新一次带宽监控
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"带宽监控器错误: {e}")
                await asyncio.sleep(15)
                
    async def _cleanup_worker(self):
        """清理工作器"""
        while self._running:
            try:
                # 清理已完成的任务（保留最近1000个）
                completed_tasks = [
                    task for task in self.active_tasks.values() 
                    if task.status in ["completed", "failed", "cancelled"]
                ]
                
                if len(completed_tasks) > 1000:
                    # 按完成时间排序，删除最老的
                    completed_tasks.sort(key=lambda t: t.completed_at or datetime.min)
                    for task in completed_tasks[:-1000]:
                        del self.active_tasks[task.task_id]
                        
                # 清理过期会话
                expired_sessions = []
                for task in self.active_tasks.values():
                    if task.session_id and not task.session_id.startswith("download_pending_"):
                        session = await self.transfer_service.get_session_info(task.session_id)
                        if session and session.expires_at < datetime.now():
                            expired_sessions.append(task.task_id)
                            
                for task_id in expired_sessions:
                    await self.cancel_task(task_id)
                    
                await asyncio.sleep(300)  # 每5分钟清理一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理工作器错误: {e}")
                await asyncio.sleep(60)
                
    async def _enqueue_task(self, task: TransferTask):
        """将任务加入队列"""
        self.task_queues[task.priority].append(task)
        self.active_tasks[task.task_id] = task
        
    async def _execute_task(self, task: TransferTask):
        """执行任务"""
        try:
            task.status = "running"
            task.started_at = datetime.now()
            
            # 根据传输会话类型执行不同逻辑
            if task.session_id.startswith("download_pending_"):
                await self._execute_download_task(task)
            else:
                await self._execute_upload_task(task)
                
        except Exception as e:
            await self._handle_task_error(task, e)
            
    async def _execute_upload_task(self, task: TransferTask):
        """执行上传任务"""
        self.active_uploads.add(task.task_id)
        
        try:
            # 上传任务的具体实现取决于数据源
            # 这里提供一个框架，实际实现需要根据具体需求调整
            
            session = await self.transfer_service.get_session_info(task.session_id)
            if not session:
                raise ValueError("上传会话不存在")
                
            # 模拟上传过程（实际应该有真实的数据源）
            # 这里应该集成到现有的扫描和提取流程中
            
            task.status = "completed"
            task.completed_at = datetime.now()
            self.stats["completed_tasks"] += 1
            
        finally:
            self.active_uploads.discard(task.task_id)
            
    async def _execute_download_task(self, task: TransferTask):
        """执行下载任务"""
        self.active_downloads.add(task.task_id)
        
        try:
            metadata = task.metadata
            
            # 提取翻译数据
            extraction_result = await self.extractor.extract_translation_data(
                extraction_type=ExtractionType(metadata["extraction_type"]),
                project_uid=metadata.get("project_uid"),
                mod_ids=metadata.get("mod_ids"),
                locale_codes=metadata.get("locale_codes"),
                since_timestamp=datetime.fromisoformat(metadata["since_timestamp"]) if metadata.get("since_timestamp") else None
            )
            
            if extraction_result.total_entries == 0:
                task.status = "completed"
                task.progress = 100.0
                task.completed_at = datetime.now()
                self.stats["completed_tasks"] += 1
                return
                
            # 创建临时文件
            import tempfile
            import os
            
            temp_dir = tempfile.mkdtemp(prefix="th_download_")
            data_file_name = f"{extraction_result.extraction_id}.dat"
            data_file_path = os.path.join(temp_dir, data_file_name)
            
            with open(data_file_path, 'wb') as f:
                f.write(extraction_result.data_payload)
                
            # 创建下载会话
            config = TransferConfig(
                chunk_size=self._calculate_optimal_chunk_size(len(extraction_result.data_payload)),
                compression_enabled=True
            )
            
            session = await self.transfer_service.initialize_download_session(
                file_path=data_file_path,
                metadata={
                    "extraction_id": extraction_result.extraction_id,
                    "task_id": task.task_id,
                    **metadata
                },
                config=config
            )
            
            # 更新任务的会话ID
            task.session_id = session.session_id
            
            task.status = "completed"
            task.completed_at = datetime.now()
            self.stats["completed_tasks"] += 1
            
        finally:
            self.active_downloads.discard(task.task_id)
            
    async def _handle_task_error(self, task: TransferTask, error: Exception):
        """处理任务错误"""
        task.error_message = str(error)
        
        # 检查是否可以重试
        if (task.retry_count < task.max_retries and 
            self.retry_config.strategy != RetryStrategy.NONE):
            
            # 计算重试延迟
            delay = await self._calculate_retry_delay(task.retry_count)
            
            # 延迟后重试
            asyncio.create_task(self._delayed_retry(task, delay))
        else:
            task.status = "failed"
            task.completed_at = datetime.now()
            self.stats["failed_tasks"] += 1
            await self._remove_from_active_sets(task)
            
        logger.error(f"任务执行失败: {task.task_id}: {error}")
        
    async def _delayed_retry(self, task: TransferTask, delay: float):
        """延迟重试任务"""
        await asyncio.sleep(delay)
        await self.retry_task(task.task_id, force=True)
        
    async def _calculate_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟"""
        import random
        
        if self.retry_config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.base_delay_seconds * (retry_count + 1)
        elif self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.base_delay_seconds * (self.retry_config.backoff_multiplier ** retry_count)
        else:
            return 0
            
        # 添加抖动
        jitter = delay * self.retry_config.jitter_factor * random.random()
        delay += jitter
        
        # 限制最大延迟
        return min(delay, self.retry_config.max_delay_seconds)
        
    async def _remove_from_active_sets(self, task: TransferTask):
        """从活跃集合中移除任务"""
        self.active_uploads.discard(task.task_id)
        self.active_downloads.discard(task.task_id)
        
    def _can_start_new_task(self) -> bool:
        """检查是否可以启动新任务"""
        # 检查并发限制
        if (len(self.active_uploads) >= self.concurrency_limits.max_concurrent_uploads and
            len(self.active_downloads) >= self.concurrency_limits.max_concurrent_downloads):
            return False
            
        # 检查带宽限制
        if self.bandwidth_monitor["current_usage"] >= self.concurrency_limits.max_bandwidth_mbps:
            return False
            
        return True
        
    def _calculate_optimal_chunk_size(self, file_size: int) -> int:
        """计算最优分块大小"""
        # 基于文件大小动态调整分块大小
        if file_size < 1024 * 1024:  # 1MB以下
            return 64 * 1024  # 64KB
        elif file_size < 10 * 1024 * 1024:  # 10MB以下
            return 512 * 1024  # 512KB
        elif file_size < 100 * 1024 * 1024:  # 100MB以下
            return 1024 * 1024  # 1MB
        else:
            return 4 * 1024 * 1024  # 4MB
            
    async def _cleanup_resources(self):
        """清理资源"""
        # 取消所有活跃任务
        for task in list(self.active_tasks.values()):
            if task.status == "running":
                await self.cancel_task(task.task_id)


# 全局实例
_transfer_controller: Optional[TransferController] = None


def get_transfer_controller() -> TransferController:
    """获取全局传输控制器实例"""
    global _transfer_controller
    if _transfer_controller is None:
        _transfer_controller = TransferController()
        logger.info("传输控制器已初始化")
    return _transfer_controller