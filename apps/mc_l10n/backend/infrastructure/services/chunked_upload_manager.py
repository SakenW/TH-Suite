"""
分块上传管理器 - 高级并发分块传输管理
支持智能并发控制、自适应重试、实时监控
"""

import asyncio
import time
from typing import Dict, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import blake3

from .file_transfer_service import (
    FileTransferService, TransferSession, ChunkInfo, 
    ChunkStatus, TransferStatus, get_file_transfer_service
)

logger = logging.getLogger(__name__)


class UploadStrategy(Enum):
    """上传策略"""
    SEQUENTIAL = "sequential"      # 顺序上传
    PARALLEL = "parallel"          # 并行上传
    ADAPTIVE = "adaptive"          # 自适应上传


class RetryStrategy(Enum):
    """重试策略"""
    IMMEDIATE = "immediate"        # 立即重试
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    LINEAR_BACKOFF = "linear_backoff"  # 线性退避


@dataclass
class UploadConfig:
    """上传配置"""
    strategy: UploadStrategy = UploadStrategy.ADAPTIVE
    max_concurrent_chunks: int = 4
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_retries_per_chunk: int = 3
    timeout_per_chunk: int = 30
    min_upload_rate: int = 1024  # 最小上传速率 bytes/s
    adaptive_threshold: float = 0.8  # 自适应调整阈值
    enable_compression: bool = False
    verify_chunks: bool = True


@dataclass
class ChunkUploadTask:
    """分块上传任务"""
    session_id: str
    chunk_index: int
    chunk_data: bytes
    chunk_hash: str
    retry_count: int = 0
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    upload_rate: float = 0.0  # bytes/s
    
    def __post_init__(self):
        if not self.chunk_hash:
            self.chunk_hash = blake3.blake3(self.chunk_data).hexdigest()


@dataclass
class UploadMetrics:
    """上传性能指标"""
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0
    active_chunks: int = 0
    
    total_bytes: int = 0
    uploaded_bytes: int = 0
    upload_rate_bps: float = 0.0
    average_rate_bps: float = 0.0
    peak_rate_bps: float = 0.0
    
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    retry_count: int = 0
    error_count: int = 0
    
    concurrent_uploads: int = 0
    optimal_concurrency: int = 4


class ChunkedUploadManager:
    """分块上传管理器"""
    
    def __init__(self, transfer_service: Optional[FileTransferService] = None):
        self.transfer_service = transfer_service or get_file_transfer_service()
        
        # 活跃的上传会话
        self.active_uploads: Dict[str, Dict] = {}
        
        # 任务队列管理
        self.pending_tasks: Dict[str, List[ChunkUploadTask]] = {}
        self.active_tasks: Dict[str, Set[int]] = {}  # session_id -> set of chunk_indices
        self.completed_tasks: Dict[str, Set[int]] = {}
        self.failed_tasks: Dict[str, Dict[int, ChunkUploadTask]] = {}
        
        # 性能监控
        self.upload_metrics: Dict[str, UploadMetrics] = {}
        
        # 并发控制
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # 事件回调
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.completion_callbacks: Dict[str, List[Callable]] = {}
        self.error_callbacks: Dict[str, List[Callable]] = {}
        
    async def start_chunked_upload(
        self,
        session_id: str,
        file_data: bytes,
        config: Optional[UploadConfig] = None
    ) -> bool:
        """启动分块上传"""
        
        if config is None:
            config = UploadConfig()
            
        # 获取传输会话
        session = await self.transfer_service.get_session_info(session_id)
        if not session:
            raise ValueError(f"传输会话不存在: {session_id}")
            
        # 初始化上传状态
        self.active_uploads[session_id] = {
            'config': config,
            'session': session,
            'start_time': datetime.now()
        }
        
        # 创建并发控制信号量
        self.semaphores[session_id] = asyncio.Semaphore(config.max_concurrent_chunks)
        
        # 初始化任务队列
        self.pending_tasks[session_id] = []
        self.active_tasks[session_id] = set()
        self.completed_tasks[session_id] = set()
        self.failed_tasks[session_id] = {}
        
        # 初始化性能指标
        self.upload_metrics[session_id] = UploadMetrics(
            total_chunks=session.total_chunks,
            total_bytes=session.file_size,
            start_time=datetime.now(),
            optimal_concurrency=config.max_concurrent_chunks
        )
        
        try:
            # 分割文件为分块
            await self._create_upload_tasks(session_id, file_data, session.chunk_size)
            
            # 根据策略执行上传
            if config.strategy == UploadStrategy.SEQUENTIAL:
                await self._sequential_upload(session_id)
            elif config.strategy == UploadStrategy.PARALLEL:
                await self._parallel_upload(session_id)
            elif config.strategy == UploadStrategy.ADAPTIVE:
                await self._adaptive_upload(session_id)
                
            logger.info(f"分块上传启动成功: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"分块上传启动失败: {session_id}: {e}")
            await self._cleanup_upload_session(session_id)
            raise
            
    async def resume_chunked_upload(self, session_id: str) -> bool:
        """恢复分块上传"""
        
        # 获取传输会话
        session = await self.transfer_service.get_session_info(session_id)
        if not session:
            raise ValueError(f"传输会话不存在: {session_id}")
            
        if session.status != TransferStatus.PAUSED:
            raise ValueError(f"会话状态不支持恢复: {session.status}")
            
        # 检查已完成的分块
        completed_chunks = await self._get_completed_chunks(session_id)
        
        # 重建任务队列（只包含未完成的分块）
        await self._rebuild_pending_tasks(session_id, completed_chunks)
        
        # 恢复上传
        config = self.active_uploads.get(session_id, {}).get('config', UploadConfig())
        
        if config.strategy == UploadStrategy.SEQUENTIAL:
            await self._sequential_upload(session_id)
        elif config.strategy == UploadStrategy.PARALLEL:
            await self._parallel_upload(session_id)
        elif config.strategy == UploadStrategy.ADAPTIVE:
            await self._adaptive_upload(session_id)
            
        logger.info(f"分块上传恢复成功: {session_id}")
        return True
        
    async def cancel_chunked_upload(self, session_id: str) -> bool:
        """取消分块上传"""
        
        if session_id not in self.active_uploads:
            return False
            
        # 取消所有活跃任务
        if session_id in self.active_tasks:
            # 这里可以添加取消逻辑，目前简单清理状态
            self.active_tasks[session_id].clear()
            
        # 清理上传会话
        await self._cleanup_upload_session(session_id)
        
        logger.info(f"分块上传已取消: {session_id}")
        return True
        
    async def get_upload_progress(self, session_id: str) -> Optional[Dict]:
        """获取上传进度"""
        
        if session_id not in self.upload_metrics:
            return None
            
        metrics = self.upload_metrics[session_id]
        
        # 计算进度百分比
        progress_percentage = (metrics.completed_chunks / metrics.total_chunks * 100) if metrics.total_chunks > 0 else 0
        
        # 计算剩余时间
        remaining_time = None
        if metrics.upload_rate_bps > 0:
            remaining_bytes = metrics.total_bytes - metrics.uploaded_bytes
            remaining_seconds = remaining_bytes / metrics.upload_rate_bps
            remaining_time = timedelta(seconds=remaining_seconds)
            
        return {
            'session_id': session_id,
            'progress_percentage': round(progress_percentage, 2),
            'completed_chunks': metrics.completed_chunks,
            'total_chunks': metrics.total_chunks,
            'failed_chunks': metrics.failed_chunks,
            'active_chunks': metrics.active_chunks,
            'uploaded_bytes': metrics.uploaded_bytes,
            'total_bytes': metrics.total_bytes,
            'upload_rate_bps': int(metrics.upload_rate_bps),
            'average_rate_bps': int(metrics.average_rate_bps),
            'peak_rate_bps': int(metrics.peak_rate_bps),
            'retry_count': metrics.retry_count,
            'error_count': metrics.error_count,
            'concurrent_uploads': metrics.concurrent_uploads,
            'optimal_concurrency': metrics.optimal_concurrency,
            'remaining_time_seconds': remaining_time.total_seconds() if remaining_time else None,
            'estimated_completion': metrics.estimated_completion.isoformat() if metrics.estimated_completion else None
        }
        
    def add_progress_callback(self, session_id: str, callback: Callable):
        """添加进度回调"""
        if session_id not in self.progress_callbacks:
            self.progress_callbacks[session_id] = []
        self.progress_callbacks[session_id].append(callback)
        
    def add_completion_callback(self, session_id: str, callback: Callable):
        """添加完成回调"""
        if session_id not in self.completion_callbacks:
            self.completion_callbacks[session_id] = []
        self.completion_callbacks[session_id].append(callback)
        
    def add_error_callback(self, session_id: str, callback: Callable):
        """添加错误回调"""
        if session_id not in self.error_callbacks:
            self.error_callbacks[session_id] = []
        self.error_callbacks[session_id].append(callback)
        
    # ============================================================================
    # 私有方法
    # ============================================================================
    
    async def _create_upload_tasks(self, session_id: str, file_data: bytes, chunk_size: int):
        """创建上传任务"""
        
        tasks = []
        total_size = len(file_data)
        
        for chunk_index in range(0, total_size, chunk_size):
            chunk_data = file_data[chunk_index:chunk_index + chunk_size]
            
            task = ChunkUploadTask(
                session_id=session_id,
                chunk_index=chunk_index // chunk_size,
                chunk_data=chunk_data,
                chunk_hash=""  # 将在__post_init__中计算
            )
            
            tasks.append(task)
            
        self.pending_tasks[session_id] = tasks
        logger.debug(f"创建了 {len(tasks)} 个上传任务: {session_id}")
        
    async def _sequential_upload(self, session_id: str):
        """顺序上传"""
        
        tasks = self.pending_tasks.get(session_id, [])
        
        for task in tasks:
            try:
                await self._upload_single_chunk(task)
                self._update_metrics_on_completion(session_id, task)
                await self._notify_progress(session_id)
                
            except Exception as e:
                await self._handle_chunk_failure(task, str(e))
                
        await self._check_upload_completion(session_id)
        
    async def _parallel_upload(self, session_id: str):
        """并行上传"""
        
        tasks = self.pending_tasks.get(session_id, [])
        semaphore = self.semaphores[session_id]
        
        async def upload_with_semaphore(task: ChunkUploadTask):
            async with semaphore:
                try:
                    await self._upload_single_chunk(task)
                    self._update_metrics_on_completion(session_id, task)
                    await self._notify_progress(session_id)
                    
                except Exception as e:
                    await self._handle_chunk_failure(task, str(e))
                    
        # 创建并发任务
        upload_tasks = [upload_with_semaphore(task) for task in tasks]
        
        # 等待所有任务完成
        await asyncio.gather(*upload_tasks, return_exceptions=True)
        
        await self._check_upload_completion(session_id)
        
    async def _adaptive_upload(self, session_id: str):
        """自适应上传"""
        
        config = self.active_uploads[session_id]['config']
        tasks = self.pending_tasks.get(session_id, [])
        
        # 动态调整并发数
        optimal_concurrency = config.max_concurrent_chunks
        performance_window = []
        
        # 分批处理任务
        batch_size = optimal_concurrency
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            
            # 记录批次开始时间
            batch_start = time.time()
            
            # 并行处理当前批次
            semaphore = asyncio.Semaphore(optimal_concurrency)
            
            async def adaptive_upload_chunk(task: ChunkUploadTask):
                async with semaphore:
                    chunk_start = time.time()
                    try:
                        await self._upload_single_chunk(task)
                        chunk_duration = time.time() - chunk_start
                        chunk_rate = len(task.chunk_data) / chunk_duration if chunk_duration > 0 else 0
                        
                        performance_window.append(chunk_rate)
                        if len(performance_window) > 10:  # 保持窗口大小
                            performance_window.pop(0)
                            
                        self._update_metrics_on_completion(session_id, task)
                        await self._notify_progress(session_id)
                        
                    except Exception as e:
                        await self._handle_chunk_failure(task, str(e))
                        
            # 执行当前批次
            batch_tasks_coroutines = [adaptive_upload_chunk(task) for task in batch_tasks]
            await asyncio.gather(*batch_tasks_coroutines, return_exceptions=True)
            
            # 评估性能并调整并发数
            if len(performance_window) >= 5:
                avg_rate = sum(performance_window) / len(performance_window)
                
                # 如果性能良好且错误率低，增加并发数
                error_rate = self.upload_metrics[session_id].error_count / max(1, i + batch_size)
                if avg_rate > config.min_upload_rate and error_rate < 0.1:
                    optimal_concurrency = min(optimal_concurrency + 1, config.max_concurrent_chunks * 2)
                elif avg_rate < config.min_upload_rate * 0.5 or error_rate > 0.2:
                    optimal_concurrency = max(1, optimal_concurrency - 1)
                    
                # 更新指标
                self.upload_metrics[session_id].optimal_concurrency = optimal_concurrency
                
            logger.debug(f"自适应并发调整: {session_id}, 当前并发: {optimal_concurrency}")
            
        await self._check_upload_completion(session_id)
        
    async def _upload_single_chunk(self, task: ChunkUploadTask):
        """上传单个分块"""
        
        task.start_time = datetime.now()
        self.active_tasks[task.session_id].add(task.chunk_index)
        
        start_time = time.time()
        
        try:
            # 执行实际上传
            success = await self.transfer_service.upload_chunk(
                task.session_id,
                task.chunk_index,
                task.chunk_data
            )
            
            if success:
                # 计算上传速率
                duration = time.time() - start_time
                task.upload_rate = len(task.chunk_data) / duration if duration > 0 else 0
                task.completion_time = datetime.now()
                
                # 移动到已完成集合
                self.active_tasks[task.session_id].discard(task.chunk_index)
                self.completed_tasks[task.session_id].add(task.chunk_index)
                
                logger.debug(f"分块上传成功: {task.session_id}#{task.chunk_index}")
                
            else:
                raise Exception("上传失败")
                
        except Exception as e:
            self.active_tasks[task.session_id].discard(task.chunk_index)
            task.error_message = str(e)
            raise
            
    async def _handle_chunk_failure(self, task: ChunkUploadTask, error_message: str):
        """处理分块上传失败"""
        
        task.retry_count += 1
        task.error_message = error_message
        
        config = self.active_uploads[task.session_id]['config']
        
        # 检查是否应该重试
        if task.retry_count <= config.max_retries_per_chunk:
            # 计算重试延迟
            if config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                delay = min(2 ** task.retry_count, 30)  # 最大30秒
            elif config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
                delay = task.retry_count * 2
            else:  # IMMEDIATE
                delay = 0
                
            logger.warning(f"分块上传失败，将在 {delay} 秒后重试: {task.session_id}#{task.chunk_index}, 错误: {error_message}")
            
            # 延迟后重试
            if delay > 0:
                await asyncio.sleep(delay)
                
            try:
                await self._upload_single_chunk(task)
                self._update_metrics_on_completion(task.session_id, task)
                await self._notify_progress(task.session_id)
                
            except Exception as retry_error:
                await self._handle_chunk_failure(task, str(retry_error))
                
        else:
            # 重试次数已用完，标记为最终失败
            self.failed_tasks[task.session_id][task.chunk_index] = task
            self.upload_metrics[task.session_id].failed_chunks += 1
            
            logger.error(f"分块上传最终失败: {task.session_id}#{task.chunk_index}, 重试次数: {task.retry_count}")
            
            # 调用错误回调
            await self._notify_error(task.session_id, task)
            
    def _update_metrics_on_completion(self, session_id: str, task: ChunkUploadTask):
        """更新完成指标"""
        
        metrics = self.upload_metrics[session_id]
        
        metrics.completed_chunks += 1
        metrics.uploaded_bytes += len(task.chunk_data)
        metrics.last_update = datetime.now()
        
        # 更新速率统计
        if task.upload_rate > 0:
            metrics.peak_rate_bps = max(metrics.peak_rate_bps, task.upload_rate)
            
            # 计算平均速率
            if metrics.start_time:
                elapsed = (metrics.last_update - metrics.start_time).total_seconds()
                metrics.average_rate_bps = metrics.uploaded_bytes / elapsed if elapsed > 0 else 0
                
        # 估算完成时间
        if metrics.average_rate_bps > 0:
            remaining_bytes = metrics.total_bytes - metrics.uploaded_bytes
            remaining_seconds = remaining_bytes / metrics.average_rate_bps
            metrics.estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
            
    async def _notify_progress(self, session_id: str):
        """通知进度更新"""
        
        callbacks = self.progress_callbacks.get(session_id, [])
        progress = await self.get_upload_progress(session_id)
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {e}")
                
    async def _notify_completion(self, session_id: str):
        """通知上传完成"""
        
        callbacks = self.completion_callbacks.get(session_id, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session_id)
                else:
                    callback(session_id)
            except Exception as e:
                logger.warning(f"完成回调执行失败: {e}")
                
    async def _notify_error(self, session_id: str, task: ChunkUploadTask):
        """通知错误"""
        
        callbacks = self.error_callbacks.get(session_id, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session_id, task)
                else:
                    callback(session_id, task)
            except Exception as e:
                logger.warning(f"错误回调执行失败: {e}")
                
    async def _check_upload_completion(self, session_id: str):
        """检查上传是否完成"""
        
        metrics = self.upload_metrics[session_id]
        
        if metrics.completed_chunks + metrics.failed_chunks >= metrics.total_chunks:
            if metrics.failed_chunks == 0:
                logger.info(f"分块上传全部完成: {session_id}")
                await self._notify_completion(session_id)
            else:
                logger.warning(f"分块上传完成但有失败: {session_id}, 失败数: {metrics.failed_chunks}")
                
            # 清理上传会话
            await self._cleanup_upload_session(session_id)
            
    async def _get_completed_chunks(self, session_id: str) -> Set[int]:
        """获取已完成的分块索引"""
        
        # 这里应该从数据库查询已完成的分块
        # 简化实现，返回空集合
        return set()
        
    async def _rebuild_pending_tasks(self, session_id: str, completed_chunks: Set[int]):
        """重建待处理任务队列"""
        
        # 这里应该重建未完成的分块任务
        # 简化实现
        pass
        
    async def _cleanup_upload_session(self, session_id: str):
        """清理上传会话"""
        
        # 清理内存状态
        self.active_uploads.pop(session_id, None)
        self.pending_tasks.pop(session_id, None)
        self.active_tasks.pop(session_id, None)
        self.completed_tasks.pop(session_id, None)
        self.failed_tasks.pop(session_id, None)
        self.upload_metrics.pop(session_id, None)
        self.semaphores.pop(session_id, None)
        
        # 清理回调
        self.progress_callbacks.pop(session_id, None)
        self.completion_callbacks.pop(session_id, None)
        self.error_callbacks.pop(session_id, None)
        
        logger.debug(f"上传会话已清理: {session_id}")


# 全局分块上传管理器实例
_chunked_upload_manager: Optional[ChunkedUploadManager] = None


def get_chunked_upload_manager() -> ChunkedUploadManager:
    """获取全局分块上传管理器实例"""
    global _chunked_upload_manager
    
    if _chunked_upload_manager is None:
        _chunked_upload_manager = ChunkedUploadManager()
        logger.info("分块上传管理器已初始化")
        
    return _chunked_upload_manager