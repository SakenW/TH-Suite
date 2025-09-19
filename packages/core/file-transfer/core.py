"""
文件传输核心引擎

提供分块传输、断点续传、并发控制等核心功能
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    AsyncIterator, 
    Callable, 
    Dict, 
    List, 
    Optional, 
    Protocol,
    Any,
    Union
)
from datetime import datetime, timedelta
import aiofiles
import blake3

from .config import TransferConfig, ChunkConfig
from .errors import TransferError, ChunkError, ValidationError


class TransferStatus(Enum):
    """传输状态枚举"""
    PENDING = "pending"
    PREPARING = "preparing"
    TRANSFERRING = "transferring"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChunkStatus(Enum):
    """分块状态枚举"""
    PENDING = "pending"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ChunkInfo:
    """分块信息"""
    index: int
    start: int
    end: int
    size: int
    hash: Optional[str] = None
    status: ChunkStatus = ChunkStatus.PENDING
    attempts: int = 0
    last_error: Optional[str] = None
    
    @property
    def is_completed(self) -> bool:
        return self.status == ChunkStatus.COMPLETED
    
    @property
    def can_retry(self) -> bool:
        return self.attempts < 3 and self.status == ChunkStatus.FAILED


@dataclass 
class TransferProgress:
    """传输进度信息"""
    total_size: int
    transferred_size: int = 0
    chunks_total: int = 0
    chunks_completed: int = 0
    chunks_failed: int = 0
    start_time: Optional[datetime] = None
    current_speed: float = 0.0  # bytes/sec
    average_speed: float = 0.0  # bytes/sec
    eta: Optional[timedelta] = None
    
    @property
    def percentage(self) -> float:
        if self.total_size == 0:
            return 0.0
        return (self.transferred_size / self.total_size) * 100
    
    @property
    def is_completed(self) -> bool:
        return self.transferred_size >= self.total_size


@dataclass
class TransferTask:
    """传输任务"""
    id: str
    source_path: Union[str, Path]
    target_url: str
    file_size: int
    file_hash: Optional[str] = None
    chunks: List[ChunkInfo] = field(default_factory=list)
    status: TransferStatus = TransferStatus.PENDING
    progress: TransferProgress = field(default_factory=lambda: TransferProgress(0))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.progress.total_size = self.file_size


@dataclass
class TransferResult:
    """传输结果"""
    task_id: str
    success: bool
    transferred_size: int
    total_time: timedelta
    average_speed: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TransferStrategy(Protocol):
    """传输策略协议"""
    
    async def upload_chunk(
        self,
        chunk_data: bytes,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """上传单个分块"""
        ...
    
    async def verify_chunk(
        self,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """验证分块完整性"""
        ...


class FileTransferEngine:
    """文件传输引擎"""
    
    def __init__(self, config: TransferConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_tasks: Dict[str, TransferTask] = {}
        self._semaphore = asyncio.Semaphore(config.max_concurrent_transfers)
        self._strategy: Optional[TransferStrategy] = None
        
    def set_strategy(self, strategy: TransferStrategy) -> None:
        """设置传输策略"""
        self._strategy = strategy
    
    async def start_transfer(
        self,
        task: TransferTask,
        progress_callback: Optional[Callable[[TransferProgress], None]] = None
    ) -> TransferResult:
        """开始传输任务"""
        if not self._strategy:
            raise TransferError("传输策略未设置")
        
        async with self._semaphore:
            try:
                self.active_tasks[task.id] = task
                result = await self._execute_transfer(task, progress_callback)
                return result
            finally:
                self.active_tasks.pop(task.id, None)
    
    async def _execute_transfer(
        self,
        task: TransferTask,
        progress_callback: Optional[Callable[[TransferProgress], None]]
    ) -> TransferResult:
        """执行传输任务"""
        start_time = datetime.now()
        task.status = TransferStatus.PREPARING
        task.progress.start_time = start_time
        
        try:
            # 准备分块
            await self._prepare_chunks(task)
            
            # 验证文件
            if self.config.verify_before_transfer:
                await self._verify_file(task)
            
            task.status = TransferStatus.TRANSFERRING
            
            # 执行传输
            await self._transfer_chunks(task, progress_callback)
            
            # 验证传输结果
            if self.config.verify_after_transfer:
                await self._verify_transfer(task)
            
            task.status = TransferStatus.COMPLETED
            
            total_time = datetime.now() - start_time
            average_speed = task.file_size / total_time.total_seconds() if total_time.total_seconds() > 0 else 0
            
            return TransferResult(
                task_id=task.id,
                success=True,
                transferred_size=task.progress.transferred_size,
                total_time=total_time,
                average_speed=average_speed
            )
            
        except Exception as e:
            task.status = TransferStatus.FAILED
            self.logger.error(f"传输任务失败 {task.id}: {e}")
            
            total_time = datetime.now() - start_time
            return TransferResult(
                task_id=task.id,
                success=False,
                transferred_size=task.progress.transferred_size,
                total_time=total_time,
                average_speed=0,
                error=str(e)
            )
    
    async def _prepare_chunks(self, task: TransferTask) -> None:
        """准备分块信息"""
        chunk_size = self.config.chunk_config.size
        total_chunks = (task.file_size + chunk_size - 1) // chunk_size
        
        task.chunks = []
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, task.file_size)
            size = end - start
            
            chunk = ChunkInfo(
                index=i,
                start=start,
                end=end,
                size=size
            )
            task.chunks.append(chunk)
        
        task.progress.chunks_total = len(task.chunks)
        self.logger.info(f"任务 {task.id} 准备了 {len(task.chunks)} 个分块")
    
    async def _verify_file(self, task: TransferTask) -> None:
        """验证源文件"""
        source_path = Path(task.source_path)
        if not source_path.exists():
            raise ValidationError(f"源文件不存在: {source_path}")
        
        actual_size = source_path.stat().st_size
        if actual_size != task.file_size:
            raise ValidationError(f"文件大小不匹配: 期望 {task.file_size}, 实际 {actual_size}")
        
        # 计算文件哈希
        if task.file_hash:
            hasher = blake3.blake3()
            async with aiofiles.open(source_path, 'rb') as f:
                while chunk := await f.read(self.config.chunk_config.size):
                    hasher.update(chunk)
            
            actual_hash = hasher.hexdigest()
            if actual_hash != task.file_hash:
                raise ValidationError(f"文件哈希不匹配: 期望 {task.file_hash}, 实际 {actual_hash}")
    
    async def _transfer_chunks(
        self,
        task: TransferTask,
        progress_callback: Optional[Callable[[TransferProgress], None]]
    ) -> None:
        """传输所有分块"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_chunks)
        
        async def transfer_single_chunk(chunk: ChunkInfo) -> None:
            async with semaphore:
                await self._transfer_chunk(task, chunk)
                
                # 更新进度
                if chunk.is_completed:
                    task.progress.chunks_completed += 1
                    task.progress.transferred_size += chunk.size
                else:
                    task.progress.chunks_failed += 1
                
                # 计算速度和ETA
                self._update_transfer_speed(task)
                
                # 通知进度回调
                if progress_callback:
                    progress_callback(task.progress)
        
        # 并发传输所有分块
        tasks_list = [
            transfer_single_chunk(chunk)
            for chunk in task.chunks
        ]
        
        await asyncio.gather(*tasks_list, return_exceptions=True)
        
        # 检查失败的分块
        failed_chunks = [c for c in task.chunks if not c.is_completed]
        if failed_chunks:
            raise TransferError(f"有 {len(failed_chunks)} 个分块传输失败")
    
    async def _transfer_chunk(self, task: TransferTask, chunk: ChunkInfo) -> None:
        """传输单个分块"""
        max_retries = self.config.retry_config.max_attempts
        
        for attempt in range(max_retries):
            try:
                chunk.status = ChunkStatus.TRANSFERRING
                chunk.attempts = attempt + 1
                
                # 读取分块数据
                chunk_data = await self._read_chunk_data(task, chunk)
                
                # 计算分块哈希
                if self.config.verify_chunks:
                    chunk.hash = blake3.blake3(chunk_data).hexdigest()
                
                # 上传分块
                success = await self._strategy.upload_chunk(chunk_data, chunk, task)
                
                if success:
                    # 验证分块
                    if self.config.verify_chunks:
                        verified = await self._strategy.verify_chunk(chunk, task)
                        if not verified:
                            raise ChunkError(f"分块 {chunk.index} 验证失败")
                    
                    chunk.status = ChunkStatus.COMPLETED
                    self.logger.debug(f"分块 {chunk.index} 传输成功")
                    return
                else:
                    raise ChunkError(f"分块 {chunk.index} 上传失败")
                    
            except Exception as e:
                chunk.last_error = str(e)
                chunk.status = ChunkStatus.FAILED
                
                if attempt < max_retries - 1:
                    chunk.status = ChunkStatus.RETRYING
                    retry_delay = self.config.retry_config.delay * (2 ** attempt)
                    await asyncio.sleep(retry_delay)
                    self.logger.warning(f"分块 {chunk.index} 重试 {attempt + 1}/{max_retries}: {e}")
                else:
                    self.logger.error(f"分块 {chunk.index} 最终失败: {e}")
                    raise
    
    async def _read_chunk_data(self, task: TransferTask, chunk: ChunkInfo) -> bytes:
        """读取分块数据"""
        async with aiofiles.open(task.source_path, 'rb') as f:
            await f.seek(chunk.start)
            data = await f.read(chunk.size)
            
            if len(data) != chunk.size:
                raise ChunkError(f"读取分块 {chunk.index} 数据长度不匹配")
            
            return data
    
    def _update_transfer_speed(self, task: TransferTask) -> None:
        """更新传输速度"""
        if not task.progress.start_time:
            return
        
        elapsed = datetime.now() - task.progress.start_time
        elapsed_seconds = elapsed.total_seconds()
        
        if elapsed_seconds > 0:
            task.progress.average_speed = task.progress.transferred_size / elapsed_seconds
            
            # 计算ETA
            if task.progress.average_speed > 0:
                remaining_size = task.file_size - task.progress.transferred_size
                eta_seconds = remaining_size / task.progress.average_speed
                task.progress.eta = timedelta(seconds=eta_seconds)
    
    async def _verify_transfer(self, task: TransferTask) -> None:
        """验证传输完整性"""
        if task.progress.transferred_size != task.file_size:
            raise ValidationError(f"传输大小不匹配: 期望 {task.file_size}, 实际 {task.progress.transferred_size}")
        
        # 验证所有分块
        for chunk in task.chunks:
            if not chunk.is_completed:
                raise ValidationError(f"分块 {chunk.index} 未完成传输")
    
    async def pause_transfer(self, task_id: str) -> bool:
        """暂停传输"""
        task = self.active_tasks.get(task_id)
        if task and task.status == TransferStatus.TRANSFERRING:
            task.status = TransferStatus.PAUSED
            return True
        return False
    
    async def resume_transfer(self, task_id: str) -> bool:
        """恢复传输"""
        task = self.active_tasks.get(task_id)
        if task and task.status == TransferStatus.PAUSED:
            task.status = TransferStatus.TRANSFERRING
            return True
        return False
    
    async def cancel_transfer(self, task_id: str) -> bool:
        """取消传输"""
        task = self.active_tasks.get(task_id)
        if task:
            task.status = TransferStatus.CANCELLED
            return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TransferTask]:
        """获取任务状态"""
        return self.active_tasks.get(task_id)
    
    def list_active_tasks(self) -> List[TransferTask]:
        """列出活跃任务"""
        return list(self.active_tasks.values())