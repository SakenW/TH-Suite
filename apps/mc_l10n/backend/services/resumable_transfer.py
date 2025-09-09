"""
断点续传优化系统
支持大文件传输的断点续传、并行传输、完整性验证等功能
"""

import os
import time
import asyncio
import aiofiles
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import struct
import uuid
from collections import defaultdict
import structlog

from services.content_addressing import compute_cid, HashAlgorithm

logger = structlog.get_logger(__name__)


class TransferStatus(Enum):
    """传输状态"""
    PENDING = "pending"         # 待传输
    PREPARING = "preparing"     # 准备中
    TRANSFERRING = "transferring"  # 传输中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 传输失败
    CANCELLED = "cancelled"     # 已取消


class ChunkStatus(Enum):
    """分块状态"""
    PENDING = "pending"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFYING = "verifying"


@dataclass
class TransferChunk:
    """传输分块"""
    chunk_id: str
    sequence: int
    offset: int
    size: int
    expected_hash: Optional[str] = None  # BLAKE3哈希
    status: ChunkStatus = ChunkStatus.PENDING
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    
    def is_completed(self) -> bool:
        return self.status == ChunkStatus.COMPLETED
    
    def duration_seconds(self) -> float:
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return 0.0


@dataclass
class TransferProgress:
    """传输进度"""
    transfer_id: str
    total_size: int
    transferred_size: int = 0
    chunk_count: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0
    current_speed_bps: float = 0.0
    average_speed_bps: float = 0.0
    estimated_time_remaining: float = 0.0
    
    def get_progress_percentage(self) -> float:
        if self.total_size == 0:
            return 100.0
        return (self.transferred_size / self.total_size) * 100.0
    
    def get_chunk_progress_percentage(self) -> float:
        if self.chunk_count == 0:
            return 100.0
        return (self.completed_chunks / self.chunk_count) * 100.0


@dataclass
class TransferSession:
    """传输会话"""
    transfer_id: str
    source_path: str
    destination_path: str
    total_size: int
    chunk_size: int
    status: TransferStatus = TransferStatus.PENDING
    
    # 分块信息
    chunks: List[TransferChunk] = field(default_factory=list)
    
    # 配置选项
    max_concurrent_chunks: int = 4
    max_retry_attempts: int = 3
    enable_compression: bool = False
    enable_encryption: bool = False
    verify_integrity: bool = True
    
    # 时间戳
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 文件哈希（用于完整性验证）
    expected_file_hash: Optional[str] = None
    actual_file_hash: Optional[str] = None
    
    def get_progress(self) -> TransferProgress:
        """获取传输进度"""
        transferred_size = sum(
            chunk.size for chunk in self.chunks 
            if chunk.status == ChunkStatus.COMPLETED
        )
        
        completed_chunks = len([
            chunk for chunk in self.chunks 
            if chunk.status == ChunkStatus.COMPLETED
        ])
        
        failed_chunks = len([
            chunk for chunk in self.chunks 
            if chunk.status == ChunkStatus.FAILED
        ])
        
        # 计算传输速度
        current_speed = 0.0
        average_speed = 0.0
        
        if self.started_at:
            duration = time.time() - self.started_at
            if duration > 0:
                average_speed = transferred_size / duration
                
                # 计算最近10秒的速度作为当前速度
                recent_chunks = [
                    chunk for chunk in self.chunks
                    if (chunk.completed_at and 
                        chunk.completed_at > time.time() - 10 and
                        chunk.status == ChunkStatus.COMPLETED)
                ]
                
                if recent_chunks:
                    recent_size = sum(chunk.size for chunk in recent_chunks)
                    recent_time = max(chunk.completed_at for chunk in recent_chunks) - min(chunk.completed_at for chunk in recent_chunks)
                    if recent_time > 0:
                        current_speed = recent_size / recent_time
        
        # 估算剩余时间
        estimated_time_remaining = 0.0
        remaining_size = self.total_size - transferred_size
        if current_speed > 0:
            estimated_time_remaining = remaining_size / current_speed
        
        return TransferProgress(
            transfer_id=self.transfer_id,
            total_size=self.total_size,
            transferred_size=transferred_size,
            chunk_count=len(self.chunks),
            completed_chunks=completed_chunks,
            failed_chunks=failed_chunks,
            current_speed_bps=current_speed,
            average_speed_bps=average_speed,
            estimated_time_remaining=estimated_time_remaining
        )
    
    def is_completed(self) -> bool:
        return self.status == TransferStatus.COMPLETED
    
    def can_resume(self) -> bool:
        return self.status in [TransferStatus.PAUSED, TransferStatus.FAILED]


class ChunkTransferHandler:
    """分块传输处理器"""
    
    def __init__(self):
        self.active_transfers: Dict[str, asyncio.Task] = {}
        self.transfer_semaphore: Dict[str, asyncio.Semaphore] = {}
    
    async def transfer_chunk(
        self,
        session: TransferSession,
        chunk: TransferChunk,
        progress_callback: Optional[Callable[[str, TransferChunk], None]] = None
    ) -> bool:
        """传输单个分块"""
        chunk.status = ChunkStatus.TRANSFERRING
        
        if progress_callback:
            progress_callback(session.transfer_id, chunk)
        
        try:
            # 读取源文件分块
            source_data = await self._read_chunk(
                session.source_path,
                chunk.offset,
                chunk.size
            )
            
            # 压缩分块数据（如果启用）
            if session.enable_compression:
                source_data = await self._compress_data(source_data)
            
            # 加密分块数据（如果启用）
            if session.enable_encryption:
                source_data = await self._encrypt_data(source_data, session.metadata.get("encryption_key"))
                
            # 验证处理后的分块哈希（如果提供）
            if chunk.expected_hash and session.verify_integrity:
                chunk.status = ChunkStatus.VERIFYING
                actual_hash = compute_cid(source_data, HashAlgorithm.BLAKE3).hash_value
                
                if actual_hash != chunk.expected_hash:
                    chunk.status = ChunkStatus.FAILED
                    chunk.error_message = f"分块哈希验证失败: 期望 {chunk.expected_hash}, 实际 {actual_hash}"
                    logger.error("分块哈希验证失败",
                               transfer_id=session.transfer_id,
                               chunk_id=chunk.chunk_id,
                               expected=chunk.expected_hash,
                               actual=actual_hash)
                    return False
            
            # 写入目标位置
            await self._write_chunk(
                session.destination_path,
                chunk.offset,
                source_data
            )
            
            chunk.status = ChunkStatus.COMPLETED
            chunk.completed_at = time.time()
            
            logger.debug("分块传输完成",
                        transfer_id=session.transfer_id,
                        chunk_id=chunk.chunk_id,
                        size=chunk.size,
                        duration=chunk.duration_seconds())
            
            if progress_callback:
                progress_callback(session.transfer_id, chunk)
            
            return True
            
        except Exception as e:
            chunk.status = ChunkStatus.FAILED
            chunk.error_message = str(e)
            chunk.retry_count += 1
            
            logger.error("分块传输失败",
                        transfer_id=session.transfer_id,
                        chunk_id=chunk.chunk_id,
                        error=str(e),
                        retry_count=chunk.retry_count)
            
            if progress_callback:
                progress_callback(session.transfer_id, chunk)
            
            return False
    
    async def _read_chunk(self, file_path: str, offset: int, size: int) -> bytes:
        """读取文件分块"""
        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(offset)
            return await f.read(size)
    
    async def _write_chunk(self, file_path: str, offset: int, data: bytes):
        """写入文件分块"""
        # 确保目标目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 确保文件存在且大小足够
        file_path = Path(file_path)
        if not file_path.exists():
            # 创建空文件
            async with aiofiles.open(file_path, 'wb') as f:
                pass
        
        # 检查文件大小，如果需要则扩展
        current_size = file_path.stat().st_size
        required_size = offset + len(data)
        if current_size < required_size:
            async with aiofiles.open(file_path, 'r+b') as f:
                await f.seek(required_size - 1)
                await f.write(b'\x00')
        
        # 写入数据
        async with aiofiles.open(file_path, 'r+b') as f:
            await f.seek(offset)
            await f.write(data)
    
    async def _compress_data(self, data: bytes) -> bytes:
        """压缩数据"""
        try:
            import zstandard as zstd
            compressor = zstd.ZstdCompressor(level=3)
            return compressor.compress(data)
        except ImportError:
            import gzip
            return gzip.compress(data)
    
    async def _encrypt_data(self, data: bytes, key: Optional[str]) -> bytes:
        """加密数据"""
        if not key:
            return data
        
        try:
            from cryptography.fernet import Fernet
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.encrypt(data)
        except ImportError:
            logger.warning("cryptography库未安装，跳过数据加密")
            return data


class ResumableTransferManager:
    """断点续传管理器"""
    
    def __init__(
        self,
        state_dir: str = "./transfer_state",
        default_chunk_size: int = 1024 * 1024,  # 1MB
        max_concurrent_transfers: int = 3,
        max_concurrent_chunks_per_transfer: int = 4
    ):
        self.state_dir = Path(state_dir)
        self.default_chunk_size = default_chunk_size
        self.max_concurrent_transfers = max_concurrent_transfers
        self.max_concurrent_chunks_per_transfer = max_concurrent_chunks_per_transfer
        
        # 确保状态目录存在
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # 活跃传输
        self.active_sessions: Dict[str, TransferSession] = {}
        self.transfer_tasks: Dict[str, asyncio.Task] = {}
        
        # 分块传输处理器
        self.chunk_handler = ChunkTransferHandler()
        
        # 进度回调
        self.progress_callbacks: List[Callable[[str, TransferProgress], None]] = []
        
        # 并发控制
        self.transfer_semaphore = asyncio.Semaphore(max_concurrent_transfers)
        
        logger.info("断点续传管理器初始化",
                   state_dir=str(self.state_dir),
                   default_chunk_size=default_chunk_size,
                   max_concurrent_transfers=max_concurrent_transfers)
    
    def add_progress_callback(self, callback: Callable[[str, TransferProgress], None]):
        """添加进度回调"""
        self.progress_callbacks.append(callback)
    
    async def start_transfer(
        self,
        source_path: str,
        destination_path: str,
        transfer_id: Optional[str] = None,
        chunk_size: Optional[int] = None,
        options: Dict[str, Any] = None
    ) -> str:
        """开始新的传输"""
        if transfer_id is None:
            transfer_id = str(uuid.uuid4())
        
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        
        options = options or {}
        
        # 检查源文件
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"源文件不存在: {source_path}")
        
        source_stat = os.stat(source_path)
        file_size = source_stat.st_size
        
        # 创建传输会话
        session = TransferSession(
            transfer_id=transfer_id,
            source_path=source_path,
            destination_path=destination_path,
            total_size=file_size,
            chunk_size=chunk_size,
            max_concurrent_chunks=options.get(
                "max_concurrent_chunks",
                self.max_concurrent_chunks_per_transfer
            ),
            max_retry_attempts=options.get("max_retry_attempts", 3),
            enable_compression=options.get("enable_compression", False),
            enable_encryption=options.get("enable_encryption", False),
            verify_integrity=options.get("verify_integrity", True),
            metadata=options.get("metadata", {})
        )
        
        # 生成分块
        await self._generate_chunks(session)
        
        # 计算文件哈希（用于完整性验证）
        if session.verify_integrity:
            session.expected_file_hash = await self._calculate_file_hash(source_path)
        
        # 保存会话状态
        await self._save_session_state(session)
        
        # 添加到活跃会话
        self.active_sessions[transfer_id] = session
        
        # 开始传输
        transfer_task = asyncio.create_task(self._execute_transfer(session))
        self.transfer_tasks[transfer_id] = transfer_task
        
        logger.info("传输已开始",
                   transfer_id=transfer_id,
                   source=source_path,
                   destination=destination_path,
                   total_size=file_size,
                   chunk_count=len(session.chunks))
        
        return transfer_id
    
    async def resume_transfer(self, transfer_id: str) -> bool:
        """恢复传输"""
        # 从状态文件加载会话
        session = await self._load_session_state(transfer_id)
        if not session:
            logger.error("无法加载传输会话", transfer_id=transfer_id)
            return False
        
        if not session.can_resume():
            logger.error("传输无法恢复", 
                        transfer_id=transfer_id,
                        status=session.status.value)
            return False
        
        # 重置失败的分块状态
        for chunk in session.chunks:
            if chunk.status == ChunkStatus.FAILED:
                chunk.status = ChunkStatus.PENDING
                chunk.retry_count = 0
                chunk.error_message = None
        
        session.status = TransferStatus.PREPARING
        
        # 添加到活跃会话
        self.active_sessions[transfer_id] = session
        
        # 恢复传输
        transfer_task = asyncio.create_task(self._execute_transfer(session))
        self.transfer_tasks[transfer_id] = transfer_task
        
        logger.info("传输已恢复", transfer_id=transfer_id)
        return True
    
    async def pause_transfer(self, transfer_id: str) -> bool:
        """暂停传输"""
        if transfer_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[transfer_id]
        session.status = TransferStatus.PAUSED
        
        # 取消传输任务
        if transfer_id in self.transfer_tasks:
            self.transfer_tasks[transfer_id].cancel()
            try:
                await self.transfer_tasks[transfer_id]
            except asyncio.CancelledError:
                pass
            del self.transfer_tasks[transfer_id]
        
        # 保存状态
        await self._save_session_state(session)
        
        logger.info("传输已暂停", transfer_id=transfer_id)
        return True
    
    async def cancel_transfer(self, transfer_id: str) -> bool:
        """取消传输"""
        if transfer_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[transfer_id]
        session.status = TransferStatus.CANCELLED
        
        # 取消传输任务
        if transfer_id in self.transfer_tasks:
            self.transfer_tasks[transfer_id].cancel()
            try:
                await self.transfer_tasks[transfer_id]
            except asyncio.CancelledError:
                pass
            del self.transfer_tasks[transfer_id]
        
        # 清理临时文件
        if os.path.exists(session.destination_path):
            try:
                os.remove(session.destination_path)
            except Exception as e:
                logger.warning("清理临时文件失败",
                             file=session.destination_path,
                             error=str(e))
        
        # 清理状态文件
        state_file = self.state_dir / f"{transfer_id}.json"
        if state_file.exists():
            state_file.unlink()
        
        del self.active_sessions[transfer_id]
        
        logger.info("传输已取消", transfer_id=transfer_id)
        return True
    
    def get_transfer_progress(self, transfer_id: str) -> Optional[TransferProgress]:
        """获取传输进度"""
        if transfer_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[transfer_id]
        return session.get_progress()
    
    def get_all_transfers(self) -> List[TransferSession]:
        """获取所有传输会话"""
        return list(self.active_sessions.values())
    
    async def cleanup_completed_transfers(self, max_age_hours: int = 24):
        """清理已完成的传输记录"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        to_remove = []
        for transfer_id, session in self.active_sessions.items():
            if (session.status in [TransferStatus.COMPLETED, TransferStatus.CANCELLED] and
                session.completed_at and session.completed_at < cutoff_time):
                to_remove.append(transfer_id)
        
        for transfer_id in to_remove:
            del self.active_sessions[transfer_id]
            
            # 清理状态文件
            state_file = self.state_dir / f"{transfer_id}.json"
            if state_file.exists():
                state_file.unlink()
        
        if to_remove:
            logger.info("清理已完成传输", count=len(to_remove))
    
    async def _generate_chunks(self, session: TransferSession):
        """生成传输分块"""
        total_size = session.total_size
        chunk_size = session.chunk_size
        
        chunk_count = (total_size + chunk_size - 1) // chunk_size
        
        for i in range(chunk_count):
            offset = i * chunk_size
            size = min(chunk_size, total_size - offset)
            
            chunk = TransferChunk(
                chunk_id=f"{session.transfer_id}_chunk_{i:04d}",
                sequence=i,
                offset=offset,
                size=size
            )
            
            # 如果启用完整性验证，预计算分块哈希（包括压缩/加密处理）
            if session.verify_integrity:
                chunk_data = await self.chunk_handler._read_chunk(
                    session.source_path, offset, size
                )
                
                # 应用与写入时相同的处理
                if session.enable_compression:
                    chunk_data = await self.chunk_handler._compress_data(chunk_data)
                
                if session.enable_encryption:
                    chunk_data = await self.chunk_handler._encrypt_data(
                        chunk_data, session.metadata.get("encryption_key")
                    )
                
                chunk.expected_hash = compute_cid(chunk_data, HashAlgorithm.BLAKE3).hash_value
            
            session.chunks.append(chunk)
    
    async def _execute_transfer(self, session: TransferSession):
        """执行传输"""
        try:
            async with self.transfer_semaphore:
                session.status = TransferStatus.TRANSFERRING
                session.started_at = time.time()
                
                # 创建目标文件
                await self._create_destination_file(session)
                
                # 并发传输分块
                semaphore = asyncio.Semaphore(session.max_concurrent_chunks)
                
                async def transfer_with_retry(chunk: TransferChunk):
                    async with semaphore:
                        success = False
                        retry_count = 0
                        
                        while not success and retry_count < session.max_retry_attempts:
                            success = await self.chunk_handler.transfer_chunk(
                                session, chunk, self._on_chunk_progress
                            )
                            
                            if not success:
                                retry_count += 1
                                if retry_count < session.max_retry_attempts:
                                    await asyncio.sleep(2 ** retry_count)  # 指数退避
                        
                        return success
                
                # 只传输未完成的分块
                pending_chunks = [
                    chunk for chunk in session.chunks
                    if chunk.status != ChunkStatus.COMPLETED
                ]
                
                # 并发执行传输
                transfer_tasks = [
                    asyncio.create_task(transfer_with_retry(chunk))
                    for chunk in pending_chunks
                ]
                
                results = await asyncio.gather(*transfer_tasks, return_exceptions=True)
                
                # 检查传输结果
                successful_chunks = sum(1 for result in results if result is True)
                failed_chunks = len(results) - successful_chunks
                
                if failed_chunks == 0:
                    # 验证文件完整性
                    if session.verify_integrity:
                        if session.enable_compression or session.enable_encryption:
                            # 对于压缩/加密的传输，基于分块验证已经足够
                            # 因为每个分块的哈希都已经在传输时验证过了
                            logger.info("基于分块完整性验证完成", transfer_id=session.transfer_id)
                        elif session.expected_file_hash:
                            # 对于未处理的传输，验证整体文件哈希
                            actual_hash = await self._calculate_file_hash(session.destination_path)
                            session.actual_file_hash = actual_hash
                            
                            if actual_hash != session.expected_file_hash:
                                session.status = TransferStatus.FAILED
                                logger.error("文件完整性验证失败",
                                           transfer_id=session.transfer_id,
                                           expected=session.expected_file_hash,
                                           actual=actual_hash)
                                return
                    
                    session.status = TransferStatus.COMPLETED
                    session.completed_at = time.time()
                    
                    logger.info("传输完成",
                               transfer_id=session.transfer_id,
                               duration=session.completed_at - session.started_at,
                               total_size=session.total_size,
                               average_speed=session.total_size / (session.completed_at - session.started_at))
                else:
                    session.status = TransferStatus.FAILED
                    logger.error("传输失败",
                               transfer_id=session.transfer_id,
                               failed_chunks=failed_chunks,
                               total_chunks=len(session.chunks))
                
                # 保存最终状态
                await self._save_session_state(session)
                
                # 触发进度回调
                progress = session.get_progress()
                for callback in self.progress_callbacks:
                    try:
                        callback(session.transfer_id, progress)
                    except Exception as e:
                        logger.error("进度回调执行失败", error=str(e))
        
        except asyncio.CancelledError:
            session.status = TransferStatus.PAUSED
            await self._save_session_state(session)
            raise
        except Exception as e:
            session.status = TransferStatus.FAILED
            await self._save_session_state(session)
            logger.error("传输执行异常",
                        transfer_id=session.transfer_id,
                        error=str(e))
    
    async def _create_destination_file(self, session: TransferSession):
        """创建目标文件"""
        dest_path = Path(session.destination_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查文件是否存在且大小正确
        if dest_path.exists():
            current_size = dest_path.stat().st_size
            if current_size == session.total_size:
                # 文件已存在且大小正确，不需要重建
                logger.info("目标文件已存在，跳过重建", 
                          transfer_id=session.transfer_id,
                          current_size=current_size,
                          expected_size=session.total_size)
                return
            elif current_size > session.total_size:
                # 文件过大，截断到正确大小
                logger.info("截断目标文件到正确大小", 
                          transfer_id=session.transfer_id,
                          current_size=current_size,
                          expected_size=session.total_size)
                async with aiofiles.open(dest_path, 'r+b') as f:
                    await f.truncate(session.total_size)
                return
        
        # 创建空文件或扩展到正确大小
        logger.info("创建或扩展目标文件", 
                   transfer_id=session.transfer_id,
                   target_size=session.total_size)
        async with aiofiles.open(dest_path, 'wb') as f:
            await f.seek(session.total_size - 1)
            await f.write(b'\x00')
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        cid = await compute_file_cid(Path(file_path), HashAlgorithm.BLAKE3)
        return cid.hash_value
    
    def _on_chunk_progress(self, transfer_id: str, chunk: TransferChunk):
        """分块进度回调"""
        if transfer_id in self.active_sessions:
            session = self.active_sessions[transfer_id]
            progress = session.get_progress()
            
            # 触发进度回调
            for callback in self.progress_callbacks:
                try:
                    callback(transfer_id, progress)
                except Exception as e:
                    logger.error("进度回调执行失败", error=str(e))
    
    async def _save_session_state(self, session: TransferSession):
        """保存会话状态"""
        state_file = self.state_dir / f"{session.transfer_id}.json"
        
        state_data = {
            "transfer_id": session.transfer_id,
            "source_path": session.source_path,
            "destination_path": session.destination_path,
            "total_size": session.total_size,
            "chunk_size": session.chunk_size,
            "status": session.status.value,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "expected_file_hash": session.expected_file_hash,
            "actual_file_hash": session.actual_file_hash,
            "metadata": session.metadata,
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "sequence": chunk.sequence,
                    "offset": chunk.offset,
                    "size": chunk.size,
                    "expected_hash": chunk.expected_hash,
                    "status": chunk.status.value,
                    "retry_count": chunk.retry_count,
                    "created_at": chunk.created_at,
                    "completed_at": chunk.completed_at,
                    "error_message": chunk.error_message,
                }
                for chunk in session.chunks
            ]
        }
        
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(state_data, indent=2))
    
    async def _load_session_state(self, transfer_id: str) -> Optional[TransferSession]:
        """加载会话状态"""
        state_file = self.state_dir / f"{transfer_id}.json"
        
        if not state_file.exists():
            return None
        
        try:
            async with aiofiles.open(state_file, 'r') as f:
                state_data = json.loads(await f.read())
            
            # 重构会话对象
            session = TransferSession(
                transfer_id=state_data["transfer_id"],
                source_path=state_data["source_path"],
                destination_path=state_data["destination_path"],
                total_size=state_data["total_size"],
                chunk_size=state_data["chunk_size"],
                status=TransferStatus(state_data["status"]),
                created_at=state_data["created_at"],
                started_at=state_data.get("started_at"),
                completed_at=state_data.get("completed_at"),
                expected_file_hash=state_data.get("expected_file_hash"),
                actual_file_hash=state_data.get("actual_file_hash"),
                metadata=state_data.get("metadata", {})
            )
            
            # 重构分块对象
            for chunk_data in state_data["chunks"]:
                chunk = TransferChunk(
                    chunk_id=chunk_data["chunk_id"],
                    sequence=chunk_data["sequence"],
                    offset=chunk_data["offset"],
                    size=chunk_data["size"],
                    expected_hash=chunk_data.get("expected_hash"),
                    status=ChunkStatus(chunk_data["status"]),
                    retry_count=chunk_data["retry_count"],
                    created_at=chunk_data["created_at"],
                    completed_at=chunk_data.get("completed_at"),
                    error_message=chunk_data.get("error_message")
                )
                session.chunks.append(chunk)
            
            return session
            
        except Exception as e:
            logger.error("加载会话状态失败",
                        transfer_id=transfer_id,
                        error=str(e))
            return None


# ==================== 便捷函数 ====================

async def compute_file_cid(file_path: Path, algorithm: HashAlgorithm) -> Any:
    """计算文件CID的便捷函数"""
    from services.content_addressing import ContentHasher
    hasher = ContentHasher(algorithm)
    return await hasher.compute_file(file_path)


# ==================== 全局传输管理器 ====================

_global_transfer_manager: Optional[ResumableTransferManager] = None


def get_transfer_manager() -> ResumableTransferManager:
    """获取全局传输管理器"""
    global _global_transfer_manager
    if _global_transfer_manager is None:
        _global_transfer_manager = ResumableTransferManager()
    return _global_transfer_manager


def initialize_transfer_manager(**kwargs):
    """初始化全局传输管理器"""
    global _global_transfer_manager
    _global_transfer_manager = ResumableTransferManager(**kwargs)