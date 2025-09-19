"""
文件传输服务 - 统一的文件上传下载管理
支持大文件分块传输、断点续传、进度监控
"""

import asyncio
import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, AsyncGenerator
import json
import logging
import blake3
import aiofiles
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TransferSessionType(Enum):
    """传输会话类型"""
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TransferStatus(Enum):
    """传输状态"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChunkStatus(Enum):
    """分块状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TransferConfig:
    """传输配置"""
    chunk_size: int = 1024 * 1024  # 1MB
    max_concurrent_chunks: int = 4
    max_retries: int = 3
    timeout_seconds: int = 30
    compression_enabled: bool = False
    auto_retry: bool = True
    session_ttl_hours: int = 24


@dataclass
class TransferProgress:
    """传输进度信息"""
    session_id: str
    percentage: float
    bytes_transferred: int
    total_bytes: int
    transfer_rate_bps: int
    estimated_completion: Optional[datetime]
    elapsed_seconds: float
    completed_chunks: int
    total_chunks: int
    current_chunk: Optional[int] = None
    failed_chunks: List[int] = None


@dataclass
class TransferSession:
    """传输会话"""
    session_id: str
    session_type: TransferSessionType
    file_name: str
    file_path: str
    file_size: int
    file_hash: str
    chunk_size: int
    total_chunks: int
    status: TransferStatus
    created_at: datetime
    expires_at: datetime
    metadata: Dict = None
    config: TransferConfig = None
    completed_chunks: int = 0
    error_message: Optional[str] = None


@dataclass
class ChunkInfo:
    """分块信息"""
    session_id: str
    chunk_index: int
    chunk_size: int
    chunk_hash: str
    chunk_offset: int
    status: ChunkStatus
    retry_count: int = 0
    transfer_duration_ms: Optional[int] = None


class FileTransferService:
    """文件传输服务"""
    
    def __init__(self, db_manager, storage_root: str = "data/transfers"):
        self.db_manager = db_manager
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        # 内存中的活跃会话缓存
        self.active_sessions: Dict[str, TransferSession] = {}
        self.active_chunks: Dict[str, Dict[int, ChunkInfo]] = {}
        
        # 传输统计
        self.transfer_stats: Dict[str, Dict] = {}
        
        # 事件回调
        self.progress_callbacks: Dict[str, List] = {}
        
    async def initialize_upload_session(
        self,
        file_name: str,
        file_size: int,
        file_hash: str,
        metadata: Optional[Dict] = None,
        config: Optional[TransferConfig] = None
    ) -> TransferSession:
        """初始化上传会话"""
        
        if config is None:
            config = TransferConfig()
            
        # 生成会话ID
        session_id = f"upload_{uuid.uuid4().hex}"
        
        # 计算分块数量
        total_chunks = (file_size + config.chunk_size - 1) // config.chunk_size
        
        # 创建会话对象
        session = TransferSession(
            session_id=session_id,
            session_type=TransferSessionType.UPLOAD,
            file_name=file_name,
            file_path=str(self.storage_root / "uploads" / session_id / file_name),
            file_size=file_size,
            file_hash=file_hash,
            chunk_size=config.chunk_size,
            total_chunks=total_chunks,
            status=TransferStatus.INITIALIZING,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=config.session_ttl_hours),
            metadata=metadata or {},
            config=config
        )
        
        # 创建存储目录
        upload_dir = Path(session.file_path).parent
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到数据库
        await self._save_session_to_db(session)
        
        # 初始化分块状态
        await self._initialize_chunks(session)
        
        # 缓存到内存
        self.active_sessions[session_id] = session
        self.active_chunks[session_id] = {}
        
        # 初始化统计信息
        await self._initialize_transfer_stats(session)
        
        logger.info(f"初始化上传会话: {session_id}, 文件: {file_name}, 大小: {file_size}, 分块数: {total_chunks}")
        
        return session
        
    async def initialize_download_session(
        self,
        file_path: str,
        metadata: Optional[Dict] = None,
        config: Optional[TransferConfig] = None
    ) -> TransferSession:
        """初始化下载会话"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        if config is None:
            config = TransferConfig()
            
        # 获取文件信息
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        # 计算文件哈希
        file_hash = await self._calculate_file_hash(file_path)
        
        # 生成会话ID
        session_id = f"download_{uuid.uuid4().hex}"
        
        # 计算分块数量
        total_chunks = (file_size + config.chunk_size - 1) // config.chunk_size
        
        # 创建会话对象
        session = TransferSession(
            session_id=session_id,
            session_type=TransferSessionType.DOWNLOAD,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            chunk_size=config.chunk_size,
            total_chunks=total_chunks,
            status=TransferStatus.INITIALIZING,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=config.session_ttl_hours),
            metadata=metadata or {},
            config=config
        )
        
        # 保存到数据库
        await self._save_session_to_db(session)
        
        # 初始化分块状态
        await self._initialize_chunks(session)
        
        # 缓存到内存
        self.active_sessions[session_id] = session
        self.active_chunks[session_id] = {}
        
        # 初始化统计信息
        await self._initialize_transfer_stats(session)
        
        logger.info(f"初始化下载会话: {session_id}, 文件: {file_name}, 大小: {file_size}, 分块数: {total_chunks}")
        
        return session
        
    async def upload_chunk(
        self,
        session_id: str,
        chunk_index: int,
        chunk_data: bytes
    ) -> bool:
        """上传文件分块"""
        
        session = await self._get_session(session_id)
        if not session or session.session_type != TransferSessionType.UPLOAD:
            raise ValueError(f"无效的上传会话: {session_id}")
            
        if session.status not in [TransferStatus.INITIALIZING, TransferStatus.ACTIVE]:
            raise ValueError(f"会话状态不允许上传: {session.status}")
            
        if chunk_index >= session.total_chunks:
            raise ValueError(f"分块索引超出范围: {chunk_index} >= {session.total_chunks}")
            
        start_time = time.time()
        
        try:
            # 计算分块哈希
            chunk_hash = blake3.blake3(chunk_data).hexdigest()
            
            # 获取或创建分块信息
            chunk_info = await self._get_or_create_chunk_info(session_id, chunk_index, len(chunk_data), chunk_hash)
            
            # 更新分块状态为上传中
            chunk_info.status = ChunkStatus.UPLOADING
            await self._update_chunk_status(chunk_info)
            
            # 计算文件偏移量
            chunk_offset = chunk_index * session.chunk_size
            
            # 写入分块数据
            temp_chunk_path = Path(session.file_path).parent / f"chunk_{chunk_index}.tmp"
            async with aiofiles.open(temp_chunk_path, 'wb') as f:
                await f.write(chunk_data)
                
            # 验证分块完整性
            if await self._verify_chunk_hash(temp_chunk_path, chunk_hash):
                # 标记分块完成
                chunk_info.status = ChunkStatus.COMPLETED
                chunk_info.transfer_duration_ms = int((time.time() - start_time) * 1000)
                await self._update_chunk_status(chunk_info)
                
                # 更新会话统计
                await self._update_transfer_progress(session_id, len(chunk_data))
                
                # 检查是否所有分块都已完成
                if await self._check_upload_completion(session_id):
                    await self._finalize_upload(session_id)
                    
                logger.debug(f"分块上传成功: {session_id}#{chunk_index}")
                return True
            else:
                raise ValueError("分块哈希校验失败")
                
        except Exception as e:
            # 标记分块失败
            chunk_info = await self._get_chunk_info(session_id, chunk_index)
            if chunk_info:
                chunk_info.status = ChunkStatus.FAILED
                chunk_info.retry_count += 1
                await self._update_chunk_status(chunk_info)
                
            logger.error(f"分块上传失败: {session_id}#{chunk_index}: {e}")
            raise
            
    async def download_chunk(
        self,
        session_id: str,
        chunk_index: int
    ) -> bytes:
        """下载文件分块"""
        
        session = await self._get_session(session_id)
        if not session or session.session_type != TransferSessionType.DOWNLOAD:
            raise ValueError(f"无效的下载会话: {session_id}")
            
        if session.status not in [TransferStatus.INITIALIZING, TransferStatus.ACTIVE]:
            raise ValueError(f"会话状态不允许下载: {session.status}")
            
        if chunk_index >= session.total_chunks:
            raise ValueError(f"分块索引超出范围: {chunk_index} >= {session.total_chunks}")
            
        start_time = time.time()
        
        try:
            # 获取分块信息
            chunk_info = await self._get_chunk_info(session_id, chunk_index)
            if not chunk_info:
                raise ValueError(f"分块信息不存在: {chunk_index}")
                
            # 更新分块状态为下载中
            chunk_info.status = ChunkStatus.DOWNLOADING
            await self._update_chunk_status(chunk_info)
            
            # 计算分块范围
            chunk_offset = chunk_index * session.chunk_size
            chunk_size = min(session.chunk_size, session.file_size - chunk_offset)
            
            # 读取分块数据
            async with aiofiles.open(session.file_path, 'rb') as f:
                await f.seek(chunk_offset)
                chunk_data = await f.read(chunk_size)
                
            # 验证分块哈希
            actual_hash = blake3.blake3(chunk_data).hexdigest()
            if actual_hash != chunk_info.chunk_hash:
                raise ValueError("分块哈希校验失败")
                
            # 标记分块完成
            chunk_info.status = ChunkStatus.COMPLETED
            chunk_info.transfer_duration_ms = int((time.time() - start_time) * 1000)
            await self._update_chunk_status(chunk_info)
            
            # 更新传输统计
            await self._update_transfer_progress(session_id, len(chunk_data))
            
            logger.debug(f"分块下载成功: {session_id}#{chunk_index}")
            return chunk_data
            
        except Exception as e:
            # 标记分块失败
            chunk_info = await self._get_chunk_info(session_id, chunk_index)
            if chunk_info:
                chunk_info.status = ChunkStatus.FAILED
                chunk_info.retry_count += 1
                await self._update_chunk_status(chunk_info)
                
            logger.error(f"分块下载失败: {session_id}#{chunk_index}: {e}")
            raise
            
    async def get_transfer_progress(self, session_id: str) -> Optional[TransferProgress]:
        """获取传输进度"""
        
        session = await self._get_session(session_id)
        if not session:
            return None
            
        stats = self.transfer_stats.get(session_id, {})
        
        # 计算进度百分比
        percentage = (session.completed_chunks / session.total_chunks) * 100 if session.total_chunks > 0 else 0
        
        # 计算传输速率
        elapsed_seconds = (datetime.now() - session.created_at).total_seconds()
        bytes_transferred = stats.get('bytes_transferred', 0)
        transfer_rate = bytes_transferred / elapsed_seconds if elapsed_seconds > 0 else 0
        
        # 估算完成时间
        remaining_bytes = session.file_size - bytes_transferred
        estimated_completion = None
        if transfer_rate > 0 and remaining_bytes > 0:
            remaining_seconds = remaining_bytes / transfer_rate
            estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
            
        # 获取失败的分块
        failed_chunks = []
        if session_id in self.active_chunks:
            for chunk_index, chunk_info in self.active_chunks[session_id].items():
                if chunk_info.status == ChunkStatus.FAILED:
                    failed_chunks.append(chunk_index)
                    
        return TransferProgress(
            session_id=session_id,
            percentage=percentage,
            bytes_transferred=bytes_transferred,
            total_bytes=session.file_size,
            transfer_rate_bps=int(transfer_rate),
            estimated_completion=estimated_completion,
            elapsed_seconds=elapsed_seconds,
            completed_chunks=session.completed_chunks,
            total_chunks=session.total_chunks,
            failed_chunks=failed_chunks
        )
        
    async def cancel_transfer(self, session_id: str) -> bool:
        """取消传输"""
        
        session = await self._get_session(session_id)
        if not session:
            return False
            
        # 更新会话状态
        session.status = TransferStatus.CANCELLED
        await self._save_session_to_db(session)
        
        # 清理临时文件
        await self._cleanup_session_files(session_id)
        
        # 从内存缓存中移除
        self.active_sessions.pop(session_id, None)
        self.active_chunks.pop(session_id, None)
        self.transfer_stats.pop(session_id, None)
        
        logger.info(f"传输已取消: {session_id}")
        return True
        
    async def resume_transfer(self, session_id: str) -> bool:
        """恢复传输"""
        
        session = await self._get_session(session_id)
        if not session:
            return False
            
        if session.status != TransferStatus.PAUSED:
            return False
            
        # 更新会话状态
        session.status = TransferStatus.ACTIVE
        await self._save_session_to_db(session)
        
        # 重新加载到内存缓存
        self.active_sessions[session_id] = session
        
        logger.info(f"传输已恢复: {session_id}")
        return True
        
    async def get_session_info(self, session_id: str) -> Optional[TransferSession]:
        """获取会话信息"""
        return await self._get_session(session_id)
        
    async def list_active_sessions(self, user_id: Optional[str] = None) -> List[TransferSession]:
        """列出活跃的传输会话"""
        
        sessions = []
        for session in self.active_sessions.values():
            if user_id is None or session.metadata.get('user_id') == user_id:
                sessions.append(session)
                
        return sessions
        
    # ============================================================================
    # 私有方法
    # ============================================================================
    
    async def _save_session_to_db(self, session: TransferSession):
        """保存会话到数据库"""
        
        async with self.db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO transfer_sessions (
                    session_id, session_type, file_name, file_path, file_size, file_hash,
                    chunk_size, total_chunks, completed_chunks, status, created_at, expires_at,
                    error_message, metadata, max_concurrent_chunks, compression_enabled,
                    auto_retry, max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, session.session_type.value, session.file_name,
                session.file_path, session.file_size, session.file_hash,
                session.chunk_size, session.total_chunks, session.completed_chunks,
                session.status.value, session.created_at, session.expires_at,
                session.error_message, json.dumps(session.metadata),
                session.config.max_concurrent_chunks if session.config else 4,
                session.config.compression_enabled if session.config else False,
                session.config.auto_retry if session.config else True,
                session.config.max_retries if session.config else 3
            ))
            await conn.commit()
            
    async def _get_session(self, session_id: str) -> Optional[TransferSession]:
        """从缓存或数据库获取会话"""
        
        # 先检查内存缓存
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
            
        # 从数据库加载
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT session_id, session_type, file_name, file_path, file_size, file_hash,
                       chunk_size, total_chunks, completed_chunks, status, created_at, expires_at,
                       error_message, metadata, max_concurrent_chunks, compression_enabled,
                       auto_retry, max_retries
                FROM transfer_sessions WHERE session_id = ?
            """, (session_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
                
            config = TransferConfig(
                max_concurrent_chunks=row[14],
                compression_enabled=bool(row[15]),
                auto_retry=bool(row[16]),
                max_retries=row[17]
            )
            
            session = TransferSession(
                session_id=row[0],
                session_type=TransferSessionType(row[1]),
                file_name=row[2],
                file_path=row[3],
                file_size=row[4],
                file_hash=row[5],
                chunk_size=row[6],
                total_chunks=row[7],
                completed_chunks=row[8],
                status=TransferStatus(row[9]),
                created_at=datetime.fromisoformat(row[10]),
                expires_at=datetime.fromisoformat(row[11]),
                error_message=row[12],
                metadata=json.loads(row[13]) if row[13] else {},
                config=config
            )
            
            # 缓存到内存
            self.active_sessions[session_id] = session
            return session
            
    async def _initialize_chunks(self, session: TransferSession):
        """初始化分块状态"""
        
        async with self.db_manager.get_connection() as conn:
            for chunk_index in range(session.total_chunks):
                chunk_offset = chunk_index * session.chunk_size
                chunk_size = min(session.chunk_size, session.file_size - chunk_offset)
                
                # 为下载会话预计算分块哈希
                chunk_hash = ""
                if session.session_type == TransferSessionType.DOWNLOAD:
                    chunk_hash = await self._calculate_chunk_hash(session.file_path, chunk_offset, chunk_size)
                
                await conn.execute("""
                    INSERT INTO transfer_chunks (
                        session_id, chunk_index, chunk_size, chunk_hash, chunk_offset, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id, chunk_index, chunk_size, chunk_hash, chunk_offset, ChunkStatus.PENDING.value
                ))
                
            await conn.commit()
            
    async def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件BLAKE3哈希"""
        
        hasher = blake3.blake3()
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
                
        return hasher.hexdigest()
        
    async def _calculate_chunk_hash(self, file_path: str, offset: int, size: int) -> str:
        """计算分块BLAKE3哈希"""
        
        hasher = blake3.blake3()
        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(offset)
            chunk_data = await f.read(size)
            hasher.update(chunk_data)
            
        return hasher.hexdigest()
        
    async def _verify_chunk_hash(self, chunk_path: Path, expected_hash: str) -> bool:
        """验证分块哈希"""
        
        actual_hash = await self._calculate_file_hash(str(chunk_path))
        return actual_hash == expected_hash
        
    async def _get_or_create_chunk_info(self, session_id: str, chunk_index: int, chunk_size: int, chunk_hash: str) -> ChunkInfo:
        """获取或创建分块信息"""
        
        if session_id not in self.active_chunks:
            self.active_chunks[session_id] = {}
            
        if chunk_index not in self.active_chunks[session_id]:
            chunk_info = ChunkInfo(
                session_id=session_id,
                chunk_index=chunk_index,
                chunk_size=chunk_size,
                chunk_hash=chunk_hash,
                chunk_offset=chunk_index * chunk_size,
                status=ChunkStatus.PENDING
            )
            self.active_chunks[session_id][chunk_index] = chunk_info
            
        return self.active_chunks[session_id][chunk_index]
        
    async def _get_chunk_info(self, session_id: str, chunk_index: int) -> Optional[ChunkInfo]:
        """获取分块信息"""
        
        if session_id not in self.active_chunks:
            return None
            
        return self.active_chunks[session_id].get(chunk_index)
        
    async def _update_chunk_status(self, chunk_info: ChunkInfo):
        """更新分块状态"""
        
        async with self.db_manager.get_connection() as conn:
            await conn.execute("""
                UPDATE transfer_chunks 
                SET status = ?, retry_count = ?, transfer_duration_ms = ?, completed_at = ?
                WHERE session_id = ? AND chunk_index = ?
            """, (
                chunk_info.status.value, chunk_info.retry_count, chunk_info.transfer_duration_ms,
                datetime.now() if chunk_info.status == ChunkStatus.COMPLETED else None,
                chunk_info.session_id, chunk_info.chunk_index
            ))
            await conn.commit()
            
    async def _initialize_transfer_stats(self, session: TransferSession):
        """初始化传输统计"""
        
        self.transfer_stats[session.session_id] = {
            'bytes_transferred': 0,
            'start_time': datetime.now(),
            'last_update': datetime.now()
        }
        
        async with self.db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT INTO transfer_stats (
                    session_id, bytes_transferred, start_time
                ) VALUES (?, ?, ?)
            """, (session.session_id, 0, datetime.now()))
            await conn.commit()
            
    async def _update_transfer_progress(self, session_id: str, bytes_added: int):
        """更新传输进度"""
        
        stats = self.transfer_stats.get(session_id, {})
        stats['bytes_transferred'] = stats.get('bytes_transferred', 0) + bytes_added
        stats['last_update'] = datetime.now()
        
        # 计算传输速率
        elapsed = (stats['last_update'] - stats['start_time']).total_seconds()
        if elapsed > 0:
            stats['transfer_rate'] = stats['bytes_transferred'] / elapsed
            
        # 更新数据库
        async with self.db_manager.get_connection() as conn:
            await conn.execute("""
                UPDATE transfer_stats 
                SET bytes_transferred = ?, current_transfer_rate_bps = ?, last_update_time = ?
                WHERE session_id = ?
            """, (
                stats['bytes_transferred'], 
                int(stats.get('transfer_rate', 0)),
                stats['last_update'],
                session_id
            ))
            await conn.commit()
            
    async def _check_upload_completion(self, session_id: str) -> bool:
        """检查上传是否完成"""
        
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM transfer_chunks 
                WHERE session_id = ? AND status = ?
            """, (session_id, ChunkStatus.COMPLETED.value))
            
            completed_count = (await cursor.fetchone())[0]
            
            cursor = await conn.execute("""
                SELECT total_chunks FROM transfer_sessions WHERE session_id = ?
            """, (session_id,))
            
            total_chunks = (await cursor.fetchone())[0]
            
            return completed_count == total_chunks
            
    async def _finalize_upload(self, session_id: str):
        """完成上传，合并分块文件"""
        
        session = await self._get_session(session_id)
        if not session:
            return
            
        try:
            # 合并分块文件
            final_path = Path(session.file_path)
            temp_chunks_dir = final_path.parent
            
            async with aiofiles.open(final_path, 'wb') as output_file:
                for chunk_index in range(session.total_chunks):
                    chunk_path = temp_chunks_dir / f"chunk_{chunk_index}.tmp"
                    if chunk_path.exists():
                        async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                            chunk_data = await chunk_file.read()
                            await output_file.write(chunk_data)
                        # 删除临时分块文件
                        chunk_path.unlink()
                        
            # 验证最终文件哈希
            final_hash = await self._calculate_file_hash(session.file_path)
            if final_hash == session.file_hash:
                # 更新会话状态为完成
                session.status = TransferStatus.COMPLETED
                await self._save_session_to_db(session)
                
                logger.info(f"上传完成: {session_id}, 文件: {session.file_name}")
            else:
                raise ValueError("最终文件哈希校验失败")
                
        except Exception as e:
            session.status = TransferStatus.FAILED
            session.error_message = str(e)
            await self._save_session_to_db(session)
            logger.error(f"上传完成处理失败: {session_id}: {e}")
            
    async def _cleanup_session_files(self, session_id: str):
        """清理会话相关的临时文件"""
        
        session = await self._get_session(session_id)
        if not session:
            return
            
        try:
            # 删除临时分块文件
            temp_dir = Path(session.file_path).parent
            if temp_dir.exists():
                for chunk_file in temp_dir.glob("chunk_*.tmp"):
                    chunk_file.unlink()
                    
                # 如果目录为空，删除目录
                if not any(temp_dir.iterdir()):
                    temp_dir.rmdir()
                    
        except Exception as e:
            logger.warning(f"清理会话文件失败: {session_id}: {e}")


# 全局文件传输服务实例
_file_transfer_service: Optional[FileTransferService] = None


def get_file_transfer_service(db_manager=None) -> FileTransferService:
    """获取全局文件传输服务实例"""
    global _file_transfer_service
    
    if _file_transfer_service is None:
        if db_manager is None:
            from core.di_container import get_database_manager
            db_manager = get_database_manager()
            
        _file_transfer_service = FileTransferService(db_manager)
        logger.info("文件传输服务已初始化")
        
    return _file_transfer_service