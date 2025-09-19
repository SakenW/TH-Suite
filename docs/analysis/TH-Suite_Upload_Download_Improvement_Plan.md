# TH-Suite 上传下载功能改进实施方案

## 📋 项目概述

本方案旨在全面升级TH-Suite MC L10n的上传下载功能，使其达到现代翻译管理平台的标准。通过分阶段实施，预计在20周内完成核心功能改进，显著提升用户体验和系统性能。

### 项目目标
- **性能提升**: 文件传输速度提升5-10倍
- **功能完善**: 支持大文件、断点续传、批量操作
- **体验优化**: 现代化界面、实时进度、智能错误处理
- **稳定性增强**: 99.5%可用性、98%成功率

---

## 🎯 阶段一：核心基础设施改进 (Week 1-6)

### Phase 1.1: 大文件传输基础设施 (Week 1-2)

#### 后端实现

**1.1.1 文件传输服务重构**

```python
# apps/mc_l10n/backend/infrastructure/services/file_transfer_service.py
"""
大文件传输服务
支持分块上传、断点续传、并行传输
"""

import asyncio
import hashlib
import os
from typing import Dict, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
from fastapi import UploadFile
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class ChunkInfo:
    """文件分块信息"""
    chunk_id: str
    chunk_index: int
    chunk_size: int
    chunk_hash: str
    uploaded: bool = False
    upload_time: Optional[datetime] = None

@dataclass
class UploadSession:
    """上传会话信息"""
    session_id: str
    file_name: str
    file_size: int
    total_chunks: int
    chunk_size: int
    chunks: List[ChunkInfo]
    created_at: datetime
    last_activity: datetime
    status: str  # 'active', 'paused', 'completed', 'failed'
    upload_dir: str

@dataclass
class UploadProgress:
    """上传进度信息"""
    session_id: str
    uploaded_bytes: int
    total_bytes: int
    progress_percentage: float
    upload_speed: float  # bytes/second
    eta_seconds: Optional[float]
    current_chunk: int
    total_chunks: int

class FileTransferService:
    """文件传输服务"""
    
    def __init__(self, upload_dir: str = "uploads", chunk_size: int = 8 * 1024 * 1024):
        self.upload_dir = Path(upload_dir)
        self.chunk_size = chunk_size
        self.active_sessions: Dict[str, UploadSession] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
    async def create_upload_session(
        self, 
        file_name: str, 
        file_size: int,
        file_hash: Optional[str] = None
    ) -> UploadSession:
        """创建上传会话"""
        
        session_id = hashlib.md5(
            f"{file_name}_{file_size}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        session_dir = self.upload_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        chunks = []
        for i in range(total_chunks):
            chunk_id = f"{session_id}_chunk_{i}"
            chunk_size = min(self.chunk_size, file_size - i * self.chunk_size)
            chunks.append(ChunkInfo(
                chunk_id=chunk_id,
                chunk_index=i,
                chunk_size=chunk_size,
                chunk_hash="",
                uploaded=False
            ))
        
        session = UploadSession(
            session_id=session_id,
            file_name=file_name,
            file_size=file_size,
            total_chunks=total_chunks,
            chunk_size=self.chunk_size,
            chunks=chunks,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            status='active',
            upload_dir=str(session_dir)
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Created upload session: {session_id} for file: {file_name}")
        
        return session
    
    async def upload_chunk(
        self,
        session_id: str,
        chunk_index: int,
        chunk_data: bytes
    ) -> bool:
        """上传文件分块"""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Upload session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        if chunk_index >= len(session.chunks):
            raise ValueError(f"Invalid chunk index: {chunk_index}")
        
        chunk = session.chunks[chunk_index]
        chunk_path = Path(session.upload_dir) / f"chunk_{chunk_index}"
        
        # 验证分块大小
        if len(chunk_data) != chunk.chunk_size:
            raise ValueError(f"Chunk size mismatch: expected {chunk.chunk_size}, got {len(chunk_data)}")
        
        # 计算分块哈希
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        
        # 保存分块到临时文件
        async with aiofiles.open(chunk_path, 'wb') as f:
            await f.write(chunk_data)
        
        # 更新分块信息
        chunk.chunk_hash = chunk_hash
        chunk.uploaded = True
        chunk.upload_time = datetime.now()
        session.last_activity = datetime.now()
        
        # 通知进度更新
        await self._notify_progress(session_id)
        
        logger.debug(f"Uploaded chunk {chunk_index} for session {session_id}")
        return True
    
    async def complete_upload(self, session_id: str) -> str:
        """完成上传，合并所有分块"""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Upload session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        
        # 检查所有分块是否已上传
        missing_chunks = [i for i, chunk in enumerate(session.chunks) if not chunk.uploaded]
        if missing_chunks:
            raise ValueError(f"Missing chunks: {missing_chunks}")
        
        # 合并分块
        final_file_path = Path(session.upload_dir) / session.file_name
        
        async with aiofiles.open(final_file_path, 'wb') as output_file:
            for i in range(session.total_chunks):
                chunk_path = Path(session.upload_dir) / f"chunk_{i}"
                async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                    chunk_data = await chunk_file.read()
                    await output_file.write(chunk_data)
                
                # 删除临时分块文件
                os.unlink(chunk_path)
        
        # 验证最终文件
        actual_size = final_file_path.stat().st_size
        if actual_size != session.file_size:
            raise ValueError(f"File size mismatch: expected {session.file_size}, got {actual_size}")
        
        session.status = 'completed'
        
        # 最终进度通知
        await self._notify_progress(session_id)
        
        logger.info(f"Completed upload for session {session_id}, file: {final_file_path}")
        return str(final_file_path)
    
    async def get_upload_progress(self, session_id: str) -> UploadProgress:
        """获取上传进度"""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Upload session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        uploaded_chunks = sum(1 for chunk in session.chunks if chunk.uploaded)
        uploaded_bytes = sum(chunk.chunk_size for chunk in session.chunks if chunk.uploaded)
        
        progress_percentage = (uploaded_bytes / session.file_size) * 100
        
        # 计算上传速度
        upload_speed = 0.0
        eta_seconds = None
        
        if uploaded_chunks > 0:
            uploaded_chunk_times = [chunk.upload_time for chunk in session.chunks if chunk.uploaded and chunk.upload_time]
            if len(uploaded_chunk_times) > 1:
                time_span = (max(uploaded_chunk_times) - min(uploaded_chunk_times)).total_seconds()
                if time_span > 0:
                    upload_speed = uploaded_bytes / time_span
                    remaining_bytes = session.file_size - uploaded_bytes
                    eta_seconds = remaining_bytes / upload_speed if upload_speed > 0 else None
        
        return UploadProgress(
            session_id=session_id,
            uploaded_bytes=uploaded_bytes,
            total_bytes=session.file_size,
            progress_percentage=progress_percentage,
            upload_speed=upload_speed,
            eta_seconds=eta_seconds,
            current_chunk=uploaded_chunks,
            total_chunks=session.total_chunks
        )
    
    async def resume_upload(self, session_id: str) -> UploadSession:
        """恢复中断的上传"""
        
        if session_id not in self.active_sessions:
            # 尝试从磁盘恢复会话信息
            session = await self._restore_session_from_disk(session_id)
            if not session:
                raise ValueError(f"Upload session not found: {session_id}")
            self.active_sessions[session_id] = session
        
        session = self.active_sessions[session_id]
        session.status = 'active'
        session.last_activity = datetime.now()
        
        logger.info(f"Resumed upload session: {session_id}")
        return session
    
    async def pause_upload(self, session_id: str) -> bool:
        """暂停上传"""
        
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session.status = 'paused'
        session.last_activity = datetime.now()
        
        logger.info(f"Paused upload session: {session_id}")
        return True
    
    async def cancel_upload(self, session_id: str) -> bool:
        """取消上传"""
        
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # 清理临时文件
        session_dir = Path(session.upload_dir)
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
        
        # 移除会话
        del self.active_sessions[session_id]
        
        logger.info(f"Cancelled upload session: {session_id}")
        return True
    
    def subscribe_progress(self, session_id: str, callback: Callable):
        """订阅进度更新"""
        if session_id not in self.progress_callbacks:
            self.progress_callbacks[session_id] = []
        self.progress_callbacks[session_id].append(callback)
    
    async def _notify_progress(self, session_id: str):
        """通知进度更新"""
        if session_id in self.progress_callbacks:
            progress = await self.get_upload_progress(session_id)
            for callback in self.progress_callbacks[session_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(progress)
                    else:
                        callback(progress)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
    
    async def _restore_session_from_disk(self, session_id: str) -> Optional[UploadSession]:
        """从磁盘恢复上传会话"""
        session_dir = self.upload_dir / session_id
        if not session_dir.exists():
            return None
        
        # 这里应该从持久化存储（如数据库）中恢复会话信息
        # 暂时返回None，表示不支持持久化恢复
        return None
    
    async def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """清理过期的上传会话"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if (now - session.last_activity).total_seconds() > max_age_hours * 3600:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.cancel_upload(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")

# 全局文件传输服务实例
file_transfer_service = FileTransferService()
```

**1.1.2 文件传输API路由**

```python
# apps/mc_l10n/backend/api/routes/file_transfer_routes.py
"""
文件传输API路由
支持大文件分块上传、断点续传
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import logging

from infrastructure.services.file_transfer_service import (
    file_transfer_service, 
    UploadSession, 
    UploadProgress
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/files",
    tags=["文件传输"],
    responses={404: {"description": "Not found"}},
)

class CreateUploadSessionRequest(BaseModel):
    """创建上传会话请求"""
    file_name: str
    file_size: int
    file_hash: Optional[str] = None

class UploadChunkRequest(BaseModel):
    """上传分块请求"""
    session_id: str
    chunk_index: int

@router.post("/upload/session", response_model=dict)
async def create_upload_session(request: CreateUploadSessionRequest):
    """创建文件上传会话"""
    try:
        session = await file_transfer_service.create_upload_session(
            file_name=request.file_name,
            file_size=request.file_size,
            file_hash=request.file_hash
        )
        
        return {
            "success": True,
            "data": {
                "session_id": session.session_id,
                "chunk_size": session.chunk_size,
                "total_chunks": session.total_chunks,
                "upload_url": f"/api/v1/files/upload/chunk/{session.session_id}"
            },
            "message": "上传会话创建成功"
        }
    except Exception as e:
        logger.error(f"创建上传会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/chunk/{session_id}/{chunk_index}")
async def upload_chunk(
    session_id: str,
    chunk_index: int,
    file: UploadFile = File(...)
):
    """上传文件分块"""
    try:
        chunk_data = await file.read()
        
        success = await file_transfer_service.upload_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data
        )
        
        return {
            "success": success,
            "message": f"分块 {chunk_index} 上传成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"上传分块失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/complete/{session_id}")
async def complete_upload(session_id: str, background_tasks: BackgroundTasks):
    """完成文件上传"""
    try:
        file_path = await file_transfer_service.complete_upload(session_id)
        
        # 后台处理文件（如病毒扫描、格式验证等）
        background_tasks.add_task(process_uploaded_file, file_path)
        
        return {
            "success": True,
            "data": {
                "file_path": file_path,
                "session_id": session_id
            },
            "message": "文件上传完成"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"完成上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/upload/progress/{session_id}", response_model=dict)
async def get_upload_progress(session_id: str):
    """获取上传进度"""
    try:
        progress = await file_transfer_service.get_upload_progress(session_id)
        
        return {
            "success": True,
            "data": {
                "session_id": progress.session_id,
                "uploaded_bytes": progress.uploaded_bytes,
                "total_bytes": progress.total_bytes,
                "progress_percentage": progress.progress_percentage,
                "upload_speed": progress.upload_speed,
                "eta_seconds": progress.eta_seconds,
                "current_chunk": progress.current_chunk,
                "total_chunks": progress.total_chunks
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取上传进度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/resume/{session_id}")
async def resume_upload(session_id: str):
    """恢复上传"""
    try:
        session = await file_transfer_service.resume_upload(session_id)
        
        return {
            "success": True,
            "data": {
                "session_id": session.session_id,
                "status": session.status,
                "uploaded_chunks": sum(1 for chunk in session.chunks if chunk.uploaded),
                "total_chunks": session.total_chunks
            },
            "message": "上传恢复成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"恢复上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/pause/{session_id}")
async def pause_upload(session_id: str):
    """暂停上传"""
    try:
        success = await file_transfer_service.pause_upload(session_id)
        
        return {
            "success": success,
            "message": "上传已暂停" if success else "上传会话未找到"
        }
    except Exception as e:
        logger.error(f"暂停上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/upload/{session_id}")
async def cancel_upload(session_id: str):
    """取消上传"""
    try:
        success = await file_transfer_service.cancel_upload(session_id)
        
        return {
            "success": success,
            "message": "上传已取消" if success else "上传会话未找到"
        }
    except Exception as e:
        logger.error(f"取消上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_uploaded_file(file_path: str):
    """后台处理上传的文件"""
    try:
        # 文件格式验证
        # 病毒扫描
        # 内容解析
        # 数据库记录
        logger.info(f"开始处理上传文件: {file_path}")
        
        # 这里添加具体的文件处理逻辑
        
        logger.info(f"文件处理完成: {file_path}")
    except Exception as e:
        logger.error(f"文件处理失败: {file_path}, 错误: {e}")
```

#### 前端实现

**1.1.3 大文件上传组件**

```typescript
// apps/mc_l10n/frontend/src/components/upload/LargeFileUpload.tsx
/**
 * 大文件上传组件
 * 支持分块上传、断点续传、拖拽上传
 */

import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  Card,
  Progress,
  Button,
  Alert,
  Space,
  Typography,
  Upload as AntUpload,
  message,
  Modal,
  Table
} from 'antd'
import {
  CloudUploadOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import type { UploadProps, UploadFile } from 'antd'

const { Text, Title } = Typography
const { Dragger } = AntUpload

interface UploadProgress {
  session_id: string
  uploaded_bytes: number
  total_bytes: number
  progress_percentage: number
  upload_speed: number
  eta_seconds?: number
  current_chunk: number
  total_chunks: number
}

interface UploadSession {
  session_id: string
  file_name: string
  file_size: number
  total_chunks: number
  chunk_size: number
  status: 'active' | 'paused' | 'completed' | 'failed'
  progress?: UploadProgress
  error?: string
}

interface LargeFileUploadProps {
  accept?: string[]
  maxSize?: number // bytes
  onSuccess?: (session: UploadSession) => void
  onError?: (error: string) => void
  onProgress?: (progress: UploadProgress) => void
}

export const LargeFileUpload: React.FC<LargeFileUploadProps> = ({
  accept = ['.json', '.zip', '.jar'],
  maxSize = 1024 * 1024 * 1024, // 1GB
  onSuccess,
  onError,
  onProgress
}) => {
  const [sessions, setSessions] = useState<UploadSession[]>([])
  const [dragOver, setDragOver] = useState(false)
  const intervalRefs = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // 创建上传会话
  const createUploadSession = async (file: File): Promise<string> => {
    const response = await fetch('/api/v1/files/upload/session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_name: file.name,
        file_size: file.size,
        file_hash: await calculateFileHash(file)
      })
    })

    if (!response.ok) {
      throw new Error(`创建上传会话失败: ${response.statusText}`)
    }

    const result = await response.json()
    return result.data.session_id
  }

  // 上传文件分块
  const uploadChunk = async (
    sessionId: string, 
    chunkIndex: number, 
    chunkData: Blob
  ): Promise<boolean> => {
    const formData = new FormData()
    formData.append('file', chunkData, `chunk_${chunkIndex}`)

    const response = await fetch(
      `/api/v1/files/upload/chunk/${sessionId}/${chunkIndex}`,
      {
        method: 'POST',
        body: formData
      }
    )

    return response.ok
  }

  // 完成上传
  const completeUpload = async (sessionId: string): Promise<void> => {
    const response = await fetch(
      `/api/v1/files/upload/complete/${sessionId}`,
      {
        method: 'POST'
      }
    )

    if (!response.ok) {
      throw new Error(`完成上传失败: ${response.statusText}`)
    }
  }

  // 获取上传进度
  const getUploadProgress = async (sessionId: string): Promise<UploadProgress> => {
    const response = await fetch(`/api/v1/files/upload/progress/${sessionId}`)
    
    if (!response.ok) {
      throw new Error(`获取进度失败: ${response.statusText}`)
    }

    const result = await response.json()
    return result.data
  }

  // 开始文件上传
  const startFileUpload = async (file: File) => {
    try {
      // 文件大小检查
      if (file.size > maxSize) {
        message.error(`文件大小超过限制 (${formatFileSize(maxSize)})`)
        return
      }

      // 创建上传会话
      const sessionId = await createUploadSession(file)
      
      const newSession: UploadSession = {
        session_id: sessionId,
        file_name: file.name,
        file_size: file.size,
        total_chunks: 0,
        chunk_size: 8 * 1024 * 1024, // 8MB
        status: 'active'
      }

      setSessions(prev => [...prev, newSession])

      // 开始分块上传
      await performChunkedUpload(sessionId, file)

    } catch (error) {
      console.error('上传失败:', error)
      message.error(`上传失败: ${error}`)
      onError?.(String(error))
    }
  }

  // 执行分块上传
  const performChunkedUpload = async (sessionId: string, file: File) => {
    const chunkSize = 8 * 1024 * 1024 // 8MB
    const totalChunks = Math.ceil(file.size / chunkSize)
    
    // 更新会话信息
    setSessions(prev => prev.map(session => 
      session.session_id === sessionId 
        ? { ...session, total_chunks: totalChunks, chunk_size: chunkSize }
        : session
    ))

    // 开始进度监控
    startProgressMonitoring(sessionId)

    try {
      // 并行上传分块（限制并发数）
      const concurrency = 3
      const chunks: Promise<void>[] = []

      for (let i = 0; i < totalChunks; i += concurrency) {
        const batchPromises = []
        
        for (let j = 0; j < concurrency && i + j < totalChunks; j++) {
          const chunkIndex = i + j
          const start = chunkIndex * chunkSize
          const end = Math.min(start + chunkSize, file.size)
          const chunkData = file.slice(start, end)
          
          batchPromises.push(uploadChunk(sessionId, chunkIndex, chunkData))
        }

        await Promise.all(batchPromises)
      }

      // 完成上传
      await completeUpload(sessionId)

      // 更新状态
      setSessions(prev => prev.map(session => 
        session.session_id === sessionId 
          ? { ...session, status: 'completed' }
          : session
      ))

      message.success('文件上传完成')
      
      const completedSession = sessions.find(s => s.session_id === sessionId)
      if (completedSession) {
        onSuccess?.(completedSession)
      }

    } catch (error) {
      console.error('分块上传失败:', error)
      
      // 更新错误状态
      setSessions(prev => prev.map(session => 
        session.session_id === sessionId 
          ? { ...session, status: 'failed', error: String(error) }
          : session
      ))

      message.error(`上传失败: ${error}`)
      onError?.(String(error))
    } finally {
      stopProgressMonitoring(sessionId)
    }
  }

  // 开始进度监控
  const startProgressMonitoring = (sessionId: string) => {
    const interval = setInterval(async () => {
      try {
        const progress = await getUploadProgress(sessionId)
        
        setSessions(prev => prev.map(session => 
          session.session_id === sessionId 
            ? { ...session, progress }
            : session
        ))

        onProgress?.(progress)

        // 如果上传完成，停止监控
        if (progress.progress_percentage >= 100) {
          stopProgressMonitoring(sessionId)
        }

      } catch (error) {
        console.warn('获取进度失败:', error)
      }
    }, 1000) // 每秒更新一次

    intervalRefs.current.set(sessionId, interval)
  }

  // 停止进度监控
  const stopProgressMonitoring = (sessionId: string) => {
    const interval = intervalRefs.current.get(sessionId)
    if (interval) {
      clearInterval(interval)
      intervalRefs.current.delete(sessionId)
    }
  }

  // 暂停上传
  const pauseUpload = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/v1/files/upload/pause/${sessionId}`, {
        method: 'POST'
      })

      if (response.ok) {
        setSessions(prev => prev.map(session => 
          session.session_id === sessionId 
            ? { ...session, status: 'paused' }
            : session
        ))
        stopProgressMonitoring(sessionId)
        message.success('上传已暂停')
      }
    } catch (error) {
      message.error(`暂停失败: ${error}`)
    }
  }

  // 恢复上传
  const resumeUpload = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/v1/files/upload/resume/${sessionId}`, {
        method: 'POST'
      })

      if (response.ok) {
        setSessions(prev => prev.map(session => 
          session.session_id === sessionId 
            ? { ...session, status: 'active' }
            : session
        ))
        startProgressMonitoring(sessionId)
        message.success('上传已恢复')
      }
    } catch (error) {
      message.error(`恢复失败: ${error}`)
    }
  }

  // 取消上传
  const cancelUpload = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/v1/files/upload/${sessionId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setSessions(prev => prev.filter(session => session.session_id !== sessionId))
        stopProgressMonitoring(sessionId)
        message.success('上传已取消')
      }
    } catch (error) {
      message.error(`取消失败: ${error}`)
    }
  }

  // 计算文件哈希
  const calculateFileHash = async (file: File): Promise<string> => {
    // 这里可以使用Web Crypto API计算文件哈希
    // 为简化，返回文件名和大小的组合
    return `${file.name}_${file.size}_${file.lastModified}`
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  // 格式化上传速度
  const formatUploadSpeed = (bytesPerSecond: number): string => {
    return `${formatFileSize(bytesPerSecond)}/s`
  }

  // 格式化预估时间
  const formatETA = (seconds?: number): string => {
    if (!seconds) return '未知'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`
    }
  }

  // 文件拖拽处理
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: accept.join(','),
    beforeUpload: (file) => {
      startFileUpload(file)
      return false // 阻止默认上传
    },
    onDrop: (e) => {
      setDragOver(false)
    },
    onDragOver: () => {
      setDragOver(true)
    },
    onDragLeave: () => {
      setDragOver(false)
    }
  }

  // 清理定时器
  useEffect(() => {
    return () => {
      intervalRefs.current.forEach(interval => clearInterval(interval))
    }
  }, [])

  // 渲染上传会话表格列
  const sessionColumns = [
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      width: 200,
      render: (name: string) => <Text ellipsis title={name}>{name}</Text>
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 120,
      render: (size: number) => formatFileSize(size)
    },
    {
      title: '进度',
      key: 'progress',
      width: 200,
      render: (_: any, record: UploadSession) => {
        const progress = record.progress?.progress_percentage || 0
        return (
          <div>
            <Progress percent={Math.round(progress)} size="small" />
            <Text type="secondary" className="text-xs">
              {record.progress?.current_chunk || 0}/{record.total_chunks} 分块
            </Text>
          </div>
        )
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          active: { icon: <CloudUploadOutlined />, color: 'blue', text: '上传中' },
          paused: { icon: <PauseCircleOutlined />, color: 'orange', text: '已暂停' },
          completed: { icon: <CheckCircleOutlined />, color: 'green', text: '已完成' },
          failed: { icon: <ExclamationCircleOutlined />, color: 'red', text: '失败' }
        }
        
        const config = statusConfig[status as keyof typeof statusConfig]
        return (
          <Space>
            <span style={{ color: config.color }}>{config.icon}</span>
            <Text>{config.text}</Text>
          </Space>
        )
      }
    },
    {
      title: '速度',
      key: 'speed',
      width: 120,
      render: (_: any, record: UploadSession) => {
        const speed = record.progress?.upload_speed || 0
        return speed > 0 ? formatUploadSpeed(speed) : '-'
      }
    },
    {
      title: '预估时间',
      key: 'eta',
      width: 100,
      render: (_: any, record: UploadSession) => {
        return formatETA(record.progress?.eta_seconds)
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: UploadSession) => (
        <Space>
          {record.status === 'active' && (
            <Button 
              type="text" 
              icon={<PauseCircleOutlined />} 
              onClick={() => pauseUpload(record.session_id)}
              size="small"
            >
              暂停
            </Button>
          )}
          {record.status === 'paused' && (
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />} 
              onClick={() => resumeUpload(record.session_id)}
              size="small"
            >
              恢复
            </Button>
          )}
          {['active', 'paused'].includes(record.status) && (
            <Button 
              type="text" 
              icon={<StopOutlined />} 
              onClick={() => cancelUpload(record.session_id)}
              danger
              size="small"
            >
              取消
            </Button>
          )}
        </Space>
      )
    }
  ]

  return (
    <div className="space-y-4">
      {/* 文件上传区域 */}
      <Card>
        <Dragger 
          {...uploadProps}
          className={`${dragOver ? 'border-blue-400 bg-blue-50' : ''}`}
          style={{ padding: '40px 20px' }}
        >
          <div className="text-center">
            <CloudUploadOutlined className="text-4xl text-blue-500 mb-4" />
            <Title level={4}>拖拽文件到这里或点击选择</Title>
            <Text type="secondary">
              支持格式: {accept.join(', ')} | 最大大小: {formatFileSize(maxSize)}
            </Text>
          </div>
        </Dragger>
      </Card>

      {/* 上传会话列表 */}
      {sessions.length > 0 && (
        <Card title="上传任务">
          <Table
            columns={sessionColumns}
            dataSource={sessions}
            rowKey="session_id"
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* 错误信息显示 */}
      {sessions.some(s => s.status === 'failed') && (
        <Alert
          message="部分文件上传失败"
          description="请检查网络连接或文件格式，然后重试"
          type="error"
          showIcon
          closable
        />
      )}
    </div>
  )
}

export default LargeFileUpload
```

### Phase 1.2: 实时进度监控系统 (Week 3-4)

#### 后端WebSocket服务

**1.2.1 WebSocket进度推送服务**

```python
# apps/mc_l10n/backend/infrastructure/services/websocket_progress_service.py
"""
WebSocket实时进度推送服务
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger(__name__)

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接 {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 订阅关系 {task_id: Set[connection_id]}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # 连接元数据 {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, metadata: Optional[Dict] = None):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = metadata or {}
        
        logger.info(f"WebSocket连接建立: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # 清理订阅关系
        for task_id, subscribers in self.subscriptions.items():
            subscribers.discard(connection_id)
        
        # 清理空的订阅
        empty_subscriptions = [task_id for task_id, subscribers in self.subscriptions.items() if not subscribers]
        for task_id in empty_subscriptions:
            del self.subscriptions[task_id]
        
        logger.info(f"WebSocket连接断开: {connection_id}")
    
    def subscribe(self, connection_id: str, task_id: str):
        """订阅任务进度"""
        if task_id not in self.subscriptions:
            self.subscriptions[task_id] = set()
        
        self.subscriptions[task_id].add(connection_id)
        logger.debug(f"连接 {connection_id} 订阅任务 {task_id}")
    
    def unsubscribe(self, connection_id: str, task_id: str):
        """取消订阅"""
        if task_id in self.subscriptions:
            self.subscriptions[task_id].discard(connection_id)
            
            if not self.subscriptions[task_id]:
                del self.subscriptions[task_id]
        
        logger.debug(f"连接 {connection_id} 取消订阅任务 {task_id}")
    
    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """发送个人消息"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"发送个人消息失败: {connection_id}, 错误: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_task_subscribers(self, task_id: str, message: Dict[str, Any]):
        """向任务订阅者广播消息"""
        if task_id not in self.subscriptions:
            return
        
        # 添加任务ID到消息中
        message["task_id"] = task_id
        message["timestamp"] = datetime.now().isoformat()
        
        # 获取订阅者列表的副本，避免迭代时修改
        subscribers = list(self.subscriptions[task_id])
        
        # 并发发送消息
        send_tasks = []
        for connection_id in subscribers:
            if connection_id in self.active_connections:
                send_tasks.append(self._send_safe(connection_id, message))
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    async def _send_safe(self, connection_id: str, message: Dict[str, Any]):
        """安全发送消息，处理连接异常"""
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(message))
        except WebSocketDisconnect:
            self.disconnect(connection_id)
        except Exception as e:
            logger.warning(f"发送消息失败: {connection_id}, 错误: {e}")
            self.disconnect(connection_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        message["timestamp"] = datetime.now().isoformat()
        
        # 获取所有连接ID的副本
        connection_ids = list(self.active_connections.keys())
        
        # 并发发送
        send_tasks = [self._send_safe(conn_id, message) for conn_id in connection_ids]
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    def get_connection_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)
    
    def get_task_subscriber_count(self, task_id: str) -> int:
        """获取任务订阅者数量"""
        return len(self.subscriptions.get(task_id, set()))

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()

class ProgressBroadcaster:
    """进度广播器"""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
    
    async def broadcast_upload_progress(self, session_id: str, progress_data: Dict[str, Any]):
        """广播上传进度"""
        message = {
            "type": "upload_progress",
            "session_id": session_id,
            "data": progress_data
        }
        
        await self.manager.broadcast_to_task_subscribers(session_id, message)
    
    async def broadcast_sync_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """广播同步进度"""
        message = {
            "type": "sync_progress", 
            "task_id": task_id,
            "data": progress_data
        }
        
        await self.manager.broadcast_to_task_subscribers(task_id, message)
    
    async def broadcast_scan_progress(self, scan_id: str, progress_data: Dict[str, Any]):
        """广播扫描进度"""
        message = {
            "type": "scan_progress",
            "scan_id": scan_id,
            "data": progress_data
        }
        
        await self.manager.broadcast_to_task_subscribers(scan_id, message)
    
    async def broadcast_error(self, task_id: str, error_data: Dict[str, Any]):
        """广播错误信息"""
        message = {
            "type": "error",
            "task_id": task_id,
            "data": error_data
        }
        
        await self.manager.broadcast_to_task_subscribers(task_id, message)
    
    async def broadcast_completion(self, task_id: str, result_data: Dict[str, Any]):
        """广播任务完成"""
        message = {
            "type": "task_completed",
            "task_id": task_id, 
            "data": result_data
        }
        
        await self.manager.broadcast_to_task_subscribers(task_id, message)

# 全局进度广播器实例
progress_broadcaster = ProgressBroadcaster(websocket_manager)
```

**1.2.2 WebSocket API路由**

```python
# apps/mc_l10n/backend/api/routes/websocket_routes.py
"""
WebSocket API路由
"""

import json
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
import structlog

from infrastructure.services.websocket_progress_service import websocket_manager

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.websocket("/ws/progress")
async def websocket_progress_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """WebSocket进度推送端点"""
    
    # 生成连接ID
    connection_id = client_id or str(uuid.uuid4())
    
    try:
        # 建立连接
        await websocket_manager.connect(
            websocket, 
            connection_id,
            metadata={"connected_at": datetime.now().isoformat()}
        )
        
        # 发送连接确认
        await websocket_manager.send_personal_message(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "WebSocket连接已建立"
        })
        
        logger.info(f"WebSocket连接建立: {connection_id}")
        
        # 消息处理循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "无效的JSON格式"
                })
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                await websocket_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": f"处理消息失败: {str(e)}"
                })
    
    except Exception as e:
        logger.error(f"WebSocket连接失败: {e}")
    
    finally:
        # 断开连接
        websocket_manager.disconnect(connection_id)
        logger.info(f"WebSocket连接断开: {connection_id}")

async def handle_client_message(connection_id: str, message: dict):
    """处理客户端消息"""
    
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # 订阅任务进度
        task_id = message.get("task_id")
        if task_id:
            websocket_manager.subscribe(connection_id, task_id)
            await websocket_manager.send_personal_message(connection_id, {
                "type": "subscribed",
                "task_id": task_id,
                "message": f"已订阅任务 {task_id}"
            })
    
    elif message_type == "unsubscribe":
        # 取消订阅
        task_id = message.get("task_id")
        if task_id:
            websocket_manager.unsubscribe(connection_id, task_id)
            await websocket_manager.send_personal_message(connection_id, {
                "type": "unsubscribed",
                "task_id": task_id,
                "message": f"已取消订阅任务 {task_id}"
            })
    
    elif message_type == "ping":
        # 心跳检测
        await websocket_manager.send_personal_message(connection_id, {
            "type": "pong",
            "message": "连接正常"
        })
    
    else:
        await websocket_manager.send_personal_message(connection_id, {
            "type": "error",
            "message": f"未知消息类型: {message_type}"
        })

@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket统计信息"""
    return {
        "success": True,
        "data": {
            "active_connections": websocket_manager.get_connection_count(),
            "total_subscriptions": sum(len(subscribers) for subscribers in websocket_manager.subscriptions.values()),
            "active_tasks": len(websocket_manager.subscriptions)
        }
    }
```

#### 前端WebSocket集成

**1.2.3 实时进度Hook**

```typescript
// apps/mc_l10n/frontend/src/hooks/useWebSocketProgress.ts
/**
 * WebSocket实时进度Hook
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { message } from 'antd'

interface ProgressEvent {
  type: string
  task_id?: string
  session_id?: string
  scan_id?: string
  data: any
  timestamp: string
}

interface WebSocketConfig {
  autoReconnect: boolean
  reconnectInterval: number
  maxReconnectAttempts: number
  heartbeatInterval: number
}

interface WebSocketState {
  connected: boolean
  connecting: boolean
  error?: string
  connectionId?: string
}

const defaultConfig: WebSocketConfig = {
  autoReconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  heartbeatInterval: 30000
}

export const useWebSocketProgress = (config: Partial<WebSocketConfig> = {}) => {
  const finalConfig = { ...defaultConfig, ...config }
  
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    connecting: false
  })
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const heartbeatInterval = useRef<NodeJS.Timeout | null>(null)
  const subscriptions = useRef<Set<string>>(new Set())
  const eventHandlers = useRef<Map<string, Set<(event: ProgressEvent) => void>>>(new Map())

  // 建立WebSocket连接
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setState(prev => ({ ...prev, connecting: true, error: undefined }))

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/progress`
      
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        setState(prev => ({
          ...prev,
          connected: true,
          connecting: false
        }))
        
        reconnectAttempts.current = 0
        startHeartbeat()
        
        // 重新订阅之前的任务
        subscriptions.current.forEach(taskId => {
          subscribe(taskId)
        })

        console.log('WebSocket连接已建立')
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: ProgressEvent = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
        }
      }

      wsRef.current.onclose = (event) => {
        setState(prev => ({
          ...prev,
          connected: false,
          connecting: false
        }))
        
        stopHeartbeat()
        
        if (!event.wasClean && finalConfig.autoReconnect) {
          handleReconnect()
        }

        console.log('WebSocket连接已关闭')
      }

      wsRef.current.onerror = (error) => {
        setState(prev => ({
          ...prev,
          error: 'WebSocket连接错误',
          connecting: false
        }))
        
        console.error('WebSocket错误:', error)
      }

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: `连接失败: ${error}`,
        connecting: false
      }))
    }
  }, [finalConfig.autoReconnect])

  // 断开连接
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    stopHeartbeat()
    setState({
      connected: false,
      connecting: false
    })
  }, [])

  // 处理重连
  const handleReconnect = useCallback(() => {
    if (reconnectAttempts.current < finalConfig.maxReconnectAttempts) {
      reconnectAttempts.current++
      
      console.log(`WebSocket重连中 (${reconnectAttempts.current}/${finalConfig.maxReconnectAttempts})...`)
      
      setTimeout(() => {
        connect()
      }, finalConfig.reconnectInterval)
    } else {
      setState(prev => ({
        ...prev,
        error: '重连失败，已达到最大重连次数'
      }))
      message.error('连接已断开，请刷新页面重试')
    }
  }, [connect, finalConfig.maxReconnectAttempts, finalConfig.reconnectInterval])

  // 开始心跳
  const startHeartbeat = useCallback(() => {
    heartbeatInterval.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, finalConfig.heartbeatInterval)
  }, [finalConfig.heartbeatInterval])

  // 停止心跳
  const stopHeartbeat = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current)
      heartbeatInterval.current = null
    }
  }, [])

  // 处理消息
  const handleMessage = useCallback((message: ProgressEvent) => {
    // 处理系统消息
    if (message.type === 'connection_established') {
      setState(prev => ({
        ...prev,
        connectionId: message.data?.connection_id
      }))
      return
    }

    if (message.type === 'pong') {
      // 心跳响应，无需处理
      return
    }

    // 触发相应的事件处理器
    const handlers = eventHandlers.current.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          console.error('事件处理器执行失败:', error)
        }
      })
    }

    // 触发通用处理器
    const allHandlers = eventHandlers.current.get('*')
    if (allHandlers) {
      allHandlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          console.error('通用事件处理器执行失败:', error)
        }
      })
    }
  }, [])

  // 订阅任务进度
  const subscribe = useCallback((taskId: string) => {
    subscriptions.current.add(taskId)
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        task_id: taskId
      }))
    }
  }, [])

  // 取消订阅
  const unsubscribe = useCallback((taskId: string) => {
    subscriptions.current.delete(taskId)
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe', 
        task_id: taskId
      }))
    }
  }, [])

  // 添加事件监听器
  const addEventListener = useCallback((
    eventType: string,
    handler: (event: ProgressEvent) => void
  ) => {
    if (!eventHandlers.current.has(eventType)) {
      eventHandlers.current.set(eventType, new Set())
    }
    
    eventHandlers.current.get(eventType)!.add(handler)

    // 返回清理函数
    return () => {
      const handlers = eventHandlers.current.get(eventType)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          eventHandlers.current.delete(eventType)
        }
      }
    }
  }, [])

  // 组件挂载时连接
  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    // 状态
    connected: state.connected,
    connecting: state.connecting,
    error: state.error,
    connectionId: state.connectionId,
    
    // 方法
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    addEventListener
  }
}

// 上传进度专用Hook
export const useUploadProgress = (sessionId?: string) => {
  const [progress, setProgress] = useState<any>(null)
  const [error, setError] = useState<string | undefined>()
  
  const { connected, subscribe, unsubscribe, addEventListener } = useWebSocketProgress()

  useEffect(() => {
    if (!sessionId || !connected) return

    // 订阅上传进度
    subscribe(sessionId)

    // 添加进度监听器
    const unsubscribeProgress = addEventListener('upload_progress', (event) => {
      if (event.session_id === sessionId) {
        setProgress(event.data)
      }
    })

    // 添加错误监听器
    const unsubscribeError = addEventListener('error', (event) => {
      if (event.session_id === sessionId) {
        setError(event.data?.message || '上传失败')
      }
    })

    return () => {
      unsubscribe(sessionId)
      unsubscribeProgress()
      unsubscribeError()
    }
  }, [sessionId, connected, subscribe, unsubscribe, addEventListener])

  return { progress, error, connected }
}

// 同步进度专用Hook
export const useSyncProgress = (taskId?: string) => {
  const [progress, setProgress] = useState<any>(null)
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState<string | undefined>()
  
  const { connected, subscribe, unsubscribe, addEventListener } = useWebSocketProgress()

  useEffect(() => {
    if (!taskId || !connected) return

    subscribe(taskId)

    const unsubscribeProgress = addEventListener('sync_progress', (event) => {
      if (event.task_id === taskId) {
        setProgress(event.data)
      }
    })

    const unsubscribeCompletion = addEventListener('task_completed', (event) => {
      if (event.task_id === taskId) {
        setCompleted(true)
        setProgress(event.data)
      }
    })

    const unsubscribeError = addEventListener('error', (event) => {
      if (event.task_id === taskId) {
        setError(event.data?.message || '同步失败')
      }
    })

    return () => {
      unsubscribe(taskId)
      unsubscribeProgress()
      unsubscribeCompletion()
      unsubscribeError()
    }
  }, [taskId, connected, subscribe, unsubscribe, addEventListener])

  return { progress, completed, error, connected }
}
```

### Phase 1.3: 错误处理和用户体验优化 (Week 5-6)

#### 智能错误处理系统

**1.3.1 错误分类和恢复策略**

```python
# apps/mc_l10n/backend/infrastructure/services/error_recovery_service.py
"""
智能错误处理和恢复服务
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"           # 警告级别，不影响功能
    MEDIUM = "medium"     # 中等级别，影响部分功能
    HIGH = "high"         # 高级别，影响主要功能
    CRITICAL = "critical" # 严重级别，系统不可用

class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"           # 网络相关错误
    FILE_SYSTEM = "file_system"   # 文件系统错误
    VALIDATION = "validation"     # 数据验证错误
    PERMISSION = "permission"     # 权限错误
    RESOURCE = "resource"         # 资源不足错误
    TIMEOUT = "timeout"           # 超时错误
    EXTERNAL_API = "external_api" # 外部API错误
    INTERNAL = "internal"         # 内部逻辑错误

class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"               # 重试
    FALLBACK = "fallback"         # 降级处理
    SKIP = "skip"                 # 跳过错误项
    MANUAL = "manual"             # 需要手动处理
    ABORT = "abort"               # 中止操作

@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = None

@dataclass
class RecoveryAction:
    """恢复动作"""
    strategy: RecoveryStrategy
    description: str
    action_func: Optional[Callable] = None
    parameters: Dict[str, Any] = None
    priority: int = 0  # 优先级，数值越小优先级越高

class ErrorRecoveryService:
    """错误恢复服务"""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.error_history: List[ErrorInfo] = []
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """初始化错误模式匹配规则"""
        return {
            # 网络错误模式
            "connection_timeout": {
                "patterns": ["timeout", "connection timed out", "request timeout"],
                "category": ErrorCategory.TIMEOUT,
                "severity": ErrorSeverity.MEDIUM
            },
            "connection_refused": {
                "patterns": ["connection refused", "connection reset", "no route to host"],
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH
            },
            "dns_resolution": {
                "patterns": ["name resolution failed", "getaddrinfo failed", "dns"],
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH
            },
            
            # 文件系统错误
            "file_not_found": {
                "patterns": ["file not found", "no such file", "path does not exist"],
                "category": ErrorCategory.FILE_SYSTEM,
                "severity": ErrorSeverity.MEDIUM
            },
            "permission_denied": {
                "patterns": ["permission denied", "access denied", "forbidden"],
                "category": ErrorCategory.PERMISSION,
                "severity": ErrorSeverity.HIGH
            },
            "disk_full": {
                "patterns": ["no space left", "disk full", "storage full"],
                "category": ErrorCategory.RESOURCE,
                "severity": ErrorSeverity.CRITICAL
            },
            
            # 数据验证错误
            "invalid_format": {
                "patterns": ["invalid format", "malformed", "parse error"],
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM
            },
            "schema_validation": {
                "patterns": ["schema validation", "validation failed", "invalid schema"],
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM
            },
            
            # API错误
            "api_rate_limit": {
                "patterns": ["rate limit", "too many requests", "quota exceeded"],
                "category": ErrorCategory.EXTERNAL_API,
                "severity": ErrorSeverity.MEDIUM
            },
            "api_unauthorized": {
                "patterns": ["unauthorized", "invalid token", "authentication failed"],
                "category": ErrorCategory.EXTERNAL_API,
                "severity": ErrorSeverity.HIGH
            },
            
            # 资源错误
            "memory_exhausted": {
                "patterns": ["out of memory", "memory exhausted", "allocation failed"],
                "category": ErrorCategory.RESOURCE,
                "severity": ErrorSeverity.CRITICAL
            }
        }
    
    def _initialize_recovery_strategies(self) -> Dict[ErrorCategory, List[RecoveryAction]]:
        """初始化恢复策略"""
        return {
            ErrorCategory.NETWORK: [
                RecoveryAction(
                    strategy=RecoveryStrategy.RETRY,
                    description="等待后重试网络请求",
                    priority=1
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.FALLBACK,
                    description="使用缓存数据或离线模式",
                    priority=2
                )
            ],
            
            ErrorCategory.TIMEOUT: [
                RecoveryAction(
                    strategy=RecoveryStrategy.RETRY,
                    description="增加超时时间后重试",
                    priority=1
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.SKIP,
                    description="跳过当前项目，继续处理其他项目",
                    priority=2
                )
            ],
            
            ErrorCategory.FILE_SYSTEM: [
                RecoveryAction(
                    strategy=RecoveryStrategy.MANUAL,
                    description="请检查文件路径和权限",
                    priority=1
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.SKIP,
                    description="跳过该文件，继续处理",
                    priority=2
                )
            ],
            
            ErrorCategory.PERMISSION: [
                RecoveryAction(
                    strategy=RecoveryStrategy.MANUAL,
                    description="请检查文件和目录权限",
                    priority=1
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.FALLBACK,
                    description="使用只读模式",
                    priority=2
                )
            ],
            
            ErrorCategory.VALIDATION: [
                RecoveryAction(
                    strategy=RecoveryStrategy.SKIP,
                    description="跳过无效数据",
                    priority=1
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.MANUAL,
                    description="手动修复数据格式",
                    priority=2
                )
            ],
            
            ErrorCategory.RESOURCE: [
                RecoveryAction(
                    strategy=RecoveryStrategy.ABORT,
                    description="资源不足，需要释放空间或增加资源",
                    priority=1
                )
            ],
            
            ErrorCategory.EXTERNAL_API: [
                RecoveryAction(
                    strategy=RecoveryStrategy.RETRY,
                    description="等待API限制解除后重试",
                    priority=1
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.FALLBACK,
                    description="使用备用API或离线功能",
                    priority=2
                )
            ]
        }
    
    def classify_error(self, error_message: str, exception: Optional[Exception] = None) -> ErrorInfo:
        """分类错误并生成错误信息"""
        
        # 生成唯一错误ID
        error_id = f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(error_message) % 10000}"
        
        # 默认错误信息
        category = ErrorCategory.INTERNAL
        severity = ErrorSeverity.MEDIUM
        recovery_suggestions = []
        
        # 错误消息小写用于匹配
        error_lower = error_message.lower()
        
        # 匹配错误模式
        for pattern_name, pattern_info in self.error_patterns.items():
            for pattern in pattern_info["patterns"]:
                if pattern in error_lower:
                    category = pattern_info["category"]
                    severity = pattern_info["severity"]
                    break
        
        # 生成恢复建议
        if category in self.recovery_strategies:
            recovery_suggestions = [
                action.description 
                for action in sorted(self.recovery_strategies[category], key=lambda x: x.priority)
            ]
        
        # 构建上下文信息
        context = {
            "original_message": error_message,
            "pattern_matched": pattern_name if 'pattern_name' in locals() else None,
            "exception_type": type(exception).__name__ if exception else None
        }
        
        # 获取堆栈跟踪
        stack_trace = None
        if exception:
            import traceback
            stack_trace = traceback.format_exc()
        
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=error_message,
            details={"exception": str(exception) if exception else None},
            timestamp=datetime.now(),
            context=context,
            stack_trace=stack_trace,
            recovery_suggestions=recovery_suggestions
        )
        
        # 记录错误历史
        self.error_history.append(error_info)
        
        # 限制历史记录数量
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
        
        logger.error(f"错误分类完成: {error_id} | {category.value} | {severity.value} | {error_message}")
        
        return error_info
    
    def get_recovery_actions(self, error_info: ErrorInfo) -> List[RecoveryAction]:
        """获取错误恢复动作"""
        
        actions = self.recovery_strategies.get(error_info.category, [])
        
        # 根据错误严重程度调整动作
        if error_info.severity == ErrorSeverity.CRITICAL:
            # 严重错误优先使用中止策略
            actions = [action for action in actions if action.strategy == RecoveryStrategy.ABORT] + actions
        elif error_info.severity == ErrorSeverity.LOW:
            # 轻微错误优先跳过
            actions = [action for action in actions if action.strategy == RecoveryStrategy.SKIP] + actions
        
        return sorted(actions, key=lambda x: x.priority)
    
    async def auto_recover(self, error_info: ErrorInfo, context: Dict[str, Any] = None) -> bool:
        """自动恢复处理"""
        
        actions = self.get_recovery_actions(error_info)
        
        for action in actions:
            if action.strategy in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK, RecoveryStrategy.SKIP]:
                try:
                    if action.action_func:
                        # 执行自定义恢复函数
                        result = await action.action_func(error_info, context or {})
                        if result:
                            logger.info(f"自动恢复成功: {error_info.error_id} | 策略: {action.strategy.value}")
                            return True
                    else:
                        # 默认恢复行为
                        if action.strategy == RecoveryStrategy.RETRY:
                            await asyncio.sleep(2)  # 简单延迟重试
                            return True
                        elif action.strategy == RecoveryStrategy.SKIP:
                            logger.warning(f"跳过错误项目: {error_info.error_id}")
                            return True
                
                except Exception as recovery_error:
                    logger.error(f"恢复动作失败: {action.strategy.value} | {recovery_error}")
                    continue
        
        logger.warning(f"自动恢复失败: {error_info.error_id}")
        return False
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误统计信息"""
        
        # 过滤指定时间范围内的错误
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [error for error in self.error_history if error.timestamp >= cutoff_time]
        
        if not recent_errors:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
                "most_common": [],
                "recovery_rate": 0.0
            }
        
        # 按分类统计
        by_category = {}
        for error in recent_errors:
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1
        
        # 按严重程度统计
        by_severity = {}
        for error in recent_errors:
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # 最常见错误
        error_messages = {}
        for error in recent_errors:
            message = error.message[:100]  # 截取前100字符
            error_messages[message] = error_messages.get(message, 0) + 1
        
        most_common = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_errors": len(recent_errors),
            "by_category": by_category,
            "by_severity": by_severity,
            "most_common": most_common,
            "time_range_hours": hours
        }

# 全局错误恢复服务实例
error_recovery_service = ErrorRecoveryService()
```

**1.3.2 用户友好的错误界面**

```typescript
// apps/mc_l10n/frontend/src/components/error/ErrorBoundary.tsx
/**
 * 错误边界组件 - 捕获和处理React错误
 */

import React, { Component, ReactNode } from 'react'
import { Result, Button, Alert, Collapse, Typography, Space } from 'antd'
import { 
  BugOutlined, 
  ReloadOutlined, 
  QuestionCircleOutlined,
  CopyOutlined 
} from '@ant-design/icons'

const { Panel } = Collapse
const { Text, Paragraph } = Typography

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: any) => void
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: any
  errorId?: string
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorId: `react_error_${Date.now()}`
    }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    this.setState({ errorInfo })
    
    // 记录错误到监控系统
    this.logErrorToService(error, errorInfo)
    
    // 调用外部错误处理函数
    this.props.onError?.(error, errorInfo)
  }

  logErrorToService = async (error: Error, errorInfo: any) => {
    try {
      await fetch('/api/v1/errors/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'react_error',
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent
        })
      })
    } catch (reportError) {
      console.error('Failed to report error:', reportError)
    }
  }

  handleReload = () => {
    window.location.reload()
  }

  handleReportBug = () => {
    const { error, errorInfo, errorId } = this.state
    
    const bugReport = {
      errorId,
      timestamp: new Date().toISOString(),
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      url: window.location.href
    }
    
    // 复制错误信息到剪贴板
    navigator.clipboard.writeText(JSON.stringify(bugReport, null, 2))
      .then(() => {
        // 可以显示复制成功提示
        console.log('错误信息已复制到剪贴板')
      })
      .catch(err => {
        console.error('复制失败:', err)
      })
  }

  render() {
    if (this.state.hasError) {
      // 使用自定义fallback组件
      if (this.props.fallback) {
        return this.props.fallback
      }

      const { error, errorInfo, errorId } = this.state

      return (
        <div className="p-8">
          <Result
            status="error"
            title="页面出现了问题"
            subTitle={`错误ID: ${errorId}`}
            extra={[
              <Button 
                type="primary" 
                icon={<ReloadOutlined />}
                onClick={this.handleReload}
                key="reload"
              >
                重新加载页面
              </Button>,
              <Button 
                icon={<BugOutlined />}
                onClick={this.handleReportBug}
                key="report"
              >
                报告问题
              </Button>
            ]}
          >
            <div className="max-w-2xl mx-auto">
              <Alert
                message="发生了意外错误"
                description="我们已经记录了这个错误，开发团队会尽快修复。您可以尝试重新加载页面或报告这个问题。"
                type="error"
                showIcon
                className="mb-4"
              />

              <Collapse>
                <Panel 
                  header={
                    <Space>
                      <QuestionCircleOutlined />
                      查看错误详情
                    </Space>
                  } 
                  key="details"
                >
                  <div className="space-y-4">
                    <div>
                      <Text strong>错误信息:</Text>
                      <Paragraph 
                        code 
                        copyable={{ 
                          icon: <CopyOutlined />,
                          text: error?.message 
                        }}
                      >
                        {error?.message}
                      </Paragraph>
                    </div>

                    <div>
                      <Text strong>错误堆栈:</Text>
                      <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-40">
                        {error?.stack}
                      </pre>
                    </div>

                    {errorInfo?.componentStack && (
                      <div>
                        <Text strong>组件堆栈:</Text>
                        <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-40">
                          {errorInfo.componentStack}
                        </pre>
                      </div>
                    )}

                    <Alert
                      message="隐私说明"
                      description="错误信息仅用于问题诊断，不包含个人敏感数据。"
                      type="info"
                      showIcon
                    />
                  </div>
                </Panel>
              </Collapse>
            </div>
          </Result>
        </div>
      )
    }

    return this.props.children
  }
}

// 高阶组件：为组件添加错误边界
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode
) => {
  return (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  )
}

export default ErrorBoundary
```

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "\u5206\u6790TH-Suite\u540e\u7aefAPI\u8def\u7531\u548c\u4e0a\u4f20\u4e0b\u8f7d\u529f\u80fd", "status": "completed", "activeForm": "\u5206\u6790TH-Suite\u540e\u7aefAPI\u8def\u7531\u548c\u4e0a\u4f20\u4e0b\u8f7d\u529f\u80fd"}, {"content": "\u68c0\u67e5\u73b0\u6709\u670d\u52a1\u5c42\u5b9e\u73b0\u548c\u6587\u4ef6\u5904\u7406\u903b\u8f91", "status": "completed", "activeForm": "\u68c0\u67e5\u73b0\u6709\u670d\u52a1\u5c42\u5b9e\u73b0\u548c\u6587\u4ef6\u5904\u7406\u903b\u8f91"}, {"content": "\u8bc4\u4f30\u524d\u7aefAPI\u670d\u52a1\u548c\u7ec4\u4ef6\u5b9e\u73b0", "status": "completed", "activeForm": "\u8bc4\u4f30\u524d\u7aefAPI\u670d\u52a1\u548c\u7ec4\u4ef6\u5b9e\u73b0"}, {"content": "\u8bc6\u522b\u6027\u80fd\u74f6\u9888\u548c\u67b6\u6784\u95ee\u9898", "status": "completed", "activeForm": "\u8bc6\u522b\u6027\u80fd\u74f6\u9888\u548c\u67b6\u6784\u95ee\u9898"}, {"content": "\u5bf9\u6bd4Trans-Hub\u6838\u5fc3\u529f\u80fd\u5dee\u8ddd", "status": "completed", "activeForm": "\u5bf9\u6bd4Trans-Hub\u6838\u5fc3\u529f\u80fd\u5dee\u8ddd"}, {"content": "\u5236\u5b9a\u529f\u80fd\u6539\u8fdb\u4f18\u5148\u7ea7\u5217\u8868", "status": "completed", "activeForm": "\u5236\u5b9a\u529f\u80fd\u6539\u8fdb\u4f18\u5148\u7ea7\u5217\u8868"}, {"content": "\u751f\u6210\u8be6\u7ec6\u5bf9\u6bd4\u5206\u6790\u62a5\u544a", "status": "completed", "activeForm": "\u751f\u6210\u8be6\u7ec6\u5bf9\u6bd4\u5206\u6790\u62a5\u544a"}, {"content": "\u5236\u5b9a\u5177\u4f53\u6539\u8fdb\u5b9e\u65bd\u65b9\u6848", "status": "completed", "activeForm": "\u5236\u5b9a\u5177\u4f53\u6539\u8fdb\u5b9e\u65bd\u65b9\u6848"}]