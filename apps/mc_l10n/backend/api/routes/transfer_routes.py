"""
数据传输路由 - 分块传输API接口
支持大文件上传下载、断点续传、进度监控
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import blake3

from infrastructure.services.file_transfer_service import (
    get_file_transfer_service, TransferConfig, TransferSessionType, TransferStatus
)
from infrastructure.services.translation_data_extractor import (
    get_translation_data_extractor, ExtractionType
)
from infrastructure.services.work_queue_processor import get_work_queue_processor

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/transfer", tags=["数据传输"])

# Pydantic 模型定义
class PrepareUploadRequest(BaseModel):
    """准备上传请求"""
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., gt=0, description="文件大小（字节）")
    file_hash: str = Field(..., description="文件BLAKE3哈希")
    chunk_size: Optional[int] = Field(1024*1024, gt=0, le=16*1024*1024, description="分块大小（默认1MB，最大16MB）")
    max_concurrent_chunks: Optional[int] = Field(4, gt=0, le=16, description="最大并发分块数")
    project_uid: Optional[str] = Field(None, description="项目UID")
    compression_enabled: Optional[bool] = Field(False, description="启用压缩")
    metadata: Optional[Dict[str, Any]] = Field({}, description="元数据")


class PrepareDownloadRequest(BaseModel):
    """准备下载请求"""
    extraction_type: ExtractionType = Field(ExtractionType.FULL, description="提取类型")
    project_uid: Optional[str] = Field(None, description="项目UID过滤")
    mod_ids: Optional[List[str]] = Field(None, description="MOD ID列表过滤")
    locale_codes: Optional[List[str]] = Field(None, description="语言代码列表过滤")
    since_timestamp: Optional[str] = Field(None, description="增量提取起始时间（ISO格式）")
    chunk_size: Optional[int] = Field(1024*1024, gt=0, le=16*1024*1024, description="分块大小")
    compression_enabled: Optional[bool] = Field(True, description="启用压缩")


class ChunkUploadRequest(BaseModel):
    """分块上传请求"""
    chunk_index: int = Field(..., ge=0, description="分块索引")
    chunk_hash: str = Field(..., description="分块BLAKE3哈希")


class TransferSessionResponse(BaseModel):
    """传输会话响应"""
    session_id: str
    session_type: str
    file_name: str
    file_size: int
    total_chunks: int
    chunk_size: int
    status: str
    created_at: str
    expires_at: str
    upload_urls: Optional[List[str]] = None
    download_url: Optional[str] = None


class TransferProgressResponse(BaseModel):
    """传输进度响应"""
    session_id: str
    percentage: float
    bytes_transferred: int
    total_bytes: int
    transfer_rate_bps: int
    estimated_completion: Optional[str]
    elapsed_seconds: float
    completed_chunks: int
    total_chunks: int
    current_chunk: Optional[int] = None
    failed_chunks: List[int] = []
    status: str


class ChunkResponse(BaseModel):
    """分块响应"""
    chunk_index: int
    chunk_size: int
    chunk_hash: str
    upload_url: Optional[str] = None
    status: str


# ============================================================================
# 上传相关接口
# ============================================================================

@router.post("/upload/prepare", response_model=TransferSessionResponse, summary="准备上传会话")
async def prepare_upload(
    request: PrepareUploadRequest,
    transfer_service=Depends(get_file_transfer_service)
):
    """
    准备上传会话，支持大文件分块上传
    
    - 创建上传会话
    - 生成分块信息
    - 返回上传配置
    """
    try:
        # 创建传输配置
        config = TransferConfig(
            chunk_size=request.chunk_size,
            max_concurrent_chunks=request.max_concurrent_chunks,
            compression_enabled=request.compression_enabled,
            auto_retry=True,
            max_retries=3
        )
        
        # 初始化上传会话
        session = await transfer_service.initialize_upload_session(
            file_name=request.file_name,
            file_size=request.file_size,
            file_hash=request.file_hash,
            metadata={
                "project_uid": request.project_uid,
                "upload_type": "translation_data",
                **request.metadata
            },
            config=config
        )
        
        # 生成分块上传URLs（简化实现）
        upload_urls = []
        for chunk_index in range(session.total_chunks):
            upload_urls.append(f"/api/v1/transfer/upload/chunk/{session.session_id}/{chunk_index}")
            
        logger.info(f"准备上传会话成功: {session.session_id}, 文件: {request.file_name}")
        
        return TransferSessionResponse(
            session_id=session.session_id,
            session_type=session.session_type.value,
            file_name=session.file_name,
            file_size=session.file_size,
            total_chunks=session.total_chunks,
            chunk_size=session.chunk_size,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            expires_at=session.expires_at.isoformat(),
            upload_urls=upload_urls
        )
        
    except Exception as e:
        logger.error(f"准备上传会话失败: {e}")
        raise HTTPException(status_code=400, detail=f"准备上传失败: {str(e)}")


@router.post("/upload/chunk/{session_id}/{chunk_index}", summary="上传文件分块")
async def upload_chunk(
    session_id: str,
    chunk_index: int,
    chunk_file: UploadFile = File(..., description="分块文件"),
    chunk_hash: str = Query(..., description="分块BLAKE3哈希"),
    transfer_service=Depends(get_file_transfer_service)
):
    """
    上传文件分块
    
    - 验证分块完整性
    - 保存分块数据
    - 更新传输进度
    - 检查上传完成状态
    """
    try:
        # 读取分块数据
        chunk_data = await chunk_file.read()
        
        # 验证分块哈希
        actual_hash = blake3.blake3(chunk_data).hexdigest()
        if actual_hash != chunk_hash:
            raise HTTPException(status_code=400, detail="分块哈希校验失败")
            
        # 上传分块
        success = await transfer_service.upload_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="分块上传失败")
            
        # 获取会话信息
        session = await transfer_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
            
        logger.debug(f"分块上传成功: {session_id}#{chunk_index}")
        
        return {
            "success": True,
            "message": f"分块 {chunk_index} 上传成功",
            "chunk_index": chunk_index,
            "chunk_size": len(chunk_data),
            "session_status": session.status.value,
            "completed_chunks": session.completed_chunks,
            "total_chunks": session.total_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传分块失败: {session_id}#{chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"上传分块失败: {str(e)}")


@router.get("/upload/{session_id}/status", response_model=TransferProgressResponse, summary="获取上传进度")
async def get_upload_progress(
    session_id: str,
    transfer_service=Depends(get_file_transfer_service)
):
    """获取上传进度信息"""
    try:
        progress = await transfer_service.get_transfer_progress(session_id)
        if not progress:
            raise HTTPException(status_code=404, detail="会话不存在")
            
        session = await transfer_service.get_session_info(session_id)
        
        return TransferProgressResponse(
            session_id=progress.session_id,
            percentage=progress.percentage,
            bytes_transferred=progress.bytes_transferred,
            total_bytes=progress.total_bytes,
            transfer_rate_bps=progress.transfer_rate_bps,
            estimated_completion=progress.estimated_completion.isoformat() if progress.estimated_completion else None,
            elapsed_seconds=progress.elapsed_seconds,
            completed_chunks=progress.completed_chunks,
            total_chunks=progress.total_chunks,
            current_chunk=progress.current_chunk,
            failed_chunks=progress.failed_chunks or [],
            status=session.status.value if session else "unknown"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传进度失败: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")


# ============================================================================
# 下载相关接口
# ============================================================================

@router.post("/download/prepare", response_model=TransferSessionResponse, summary="准备下载会话")
async def prepare_download(
    request: PrepareDownloadRequest,
    transfer_service=Depends(get_file_transfer_service),
    extractor=Depends(get_translation_data_extractor)
):
    """
    准备下载会话，提取并打包翻译数据
    
    - 提取翻译数据
    - 压缩数据包
    - 创建下载会话
    - 生成分块信息
    """
    try:
        # 解析时间戳
        since_timestamp = None
        if request.since_timestamp:
            since_timestamp = datetime.fromisoformat(request.since_timestamp)
            
        # 提取翻译数据
        extraction_result = await extractor.extract_translation_data(
            extraction_type=request.extraction_type,
            project_uid=request.project_uid,
            mod_ids=request.mod_ids,
            locale_codes=request.locale_codes,
            since_timestamp=since_timestamp
        )
        
        if extraction_result.total_entries == 0:
            return TransferSessionResponse(
                session_id="empty",
                session_type="download",
                file_name="empty.json",
                file_size=0,
                total_chunks=0,
                chunk_size=0,
                status="completed",
                created_at=datetime.now().isoformat(),
                expires_at=datetime.now().isoformat(),
                download_url=None
            )
            
        # 保存提取的数据到临时文件
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp(prefix="th_download_")
        data_file_name = f"{extraction_result.extraction_id}_{request.extraction_type.value}.dat"
        data_file_path = os.path.join(temp_dir, data_file_name)
        
        with open(data_file_path, 'wb') as f:
            f.write(extraction_result.data_payload)
            
        # 创建传输配置
        config = TransferConfig(
            chunk_size=request.chunk_size,
            compression_enabled=request.compression_enabled,
            auto_retry=True
        )
        
        # 初始化下载会话
        session = await transfer_service.initialize_download_session(
            file_path=data_file_path,
            metadata={
                "extraction_id": extraction_result.extraction_id,
                "extraction_type": request.extraction_type.value,
                "project_uid": request.project_uid,
                "mod_ids": request.mod_ids,
                "locale_codes": request.locale_codes,
                "data_fingerprint": extraction_result.data_fingerprint,
                "key_set_fingerprint": extraction_result.key_set_fingerprint,
                "total_entries": extraction_result.total_entries,
                "categories": {k.value: v for k, v in extraction_result.categories.items()},
                "extraction_metadata": extraction_result.metadata
            },
            config=config
        )
        
        logger.info(f"准备下载会话成功: {session.session_id}, "
                   f"提取: {extraction_result.extraction_id}, "
                   f"条目: {extraction_result.total_entries}")
        
        return TransferSessionResponse(
            session_id=session.session_id,
            session_type=session.session_type.value,
            file_name=session.file_name,
            file_size=session.file_size,
            total_chunks=session.total_chunks,
            chunk_size=session.chunk_size,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            expires_at=session.expires_at.isoformat(),
            download_url=f"/api/v1/transfer/download/stream/{session.session_id}"
        )
        
    except Exception as e:
        logger.error(f"准备下载会话失败: {e}")
        raise HTTPException(status_code=400, detail=f"准备下载失败: {str(e)}")


@router.get("/download/chunk/{session_id}/{chunk_index}", summary="下载文件分块")
async def download_chunk(
    session_id: str,
    chunk_index: int,
    transfer_service=Depends(get_file_transfer_service)
):
    """
    下载文件分块
    
    - 验证会话有效性
    - 读取分块数据
    - 返回分块内容
    """
    try:
        # 下载分块
        chunk_data = await transfer_service.download_chunk(
            session_id=session_id,
            chunk_index=chunk_index
        )
        
        # 计算分块哈希
        chunk_hash = blake3.blake3(chunk_data).hexdigest()
        
        logger.debug(f"分块下载成功: {session_id}#{chunk_index}")
        
        return StreamingResponse(
            io.BytesIO(chunk_data),
            media_type="application/octet-stream",
            headers={
                "Content-Length": str(len(chunk_data)),
                "X-Chunk-Index": str(chunk_index),
                "X-Chunk-Hash": chunk_hash,
                "X-Session-ID": session_id
            }
        )
        
    except Exception as e:
        logger.error(f"下载分块失败: {session_id}#{chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"下载分块失败: {str(e)}")


@router.get("/download/stream/{session_id}", summary="流式下载文件")
async def download_stream(
    session_id: str,
    transfer_service=Depends(get_file_transfer_service)
):
    """
    流式下载完整文件
    
    - 支持大文件流式传输
    - 自动分块读取
    - 减少内存占用
    """
    try:
        # 获取会话信息
        session = await transfer_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
            
        if session.session_type != TransferSessionType.DOWNLOAD:
            raise HTTPException(status_code=400, detail="不是下载会话")
            
        # 流式生成器
        async def stream_generator():
            try:
                for chunk_index in range(session.total_chunks):
                    chunk_data = await transfer_service.download_chunk(session_id, chunk_index)
                    yield chunk_data
                    
            except Exception as e:
                logger.error(f"流式下载失败: {session_id}: {e}")
                # 在流中发送错误信息会比较复杂，这里简单记录日志
                
        return StreamingResponse(
            stream_generator(),
            media_type="application/octet-stream",
            headers={
                "Content-Length": str(session.file_size),
                "Content-Disposition": f"attachment; filename={session.file_name}",
                "X-Session-ID": session_id,
                "X-File-Hash": session.file_hash,
                "X-Total-Chunks": str(session.total_chunks)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式下载失败: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/download/{session_id}/status", response_model=TransferProgressResponse, summary="获取下载进度")
async def get_download_progress(
    session_id: str,
    transfer_service=Depends(get_file_transfer_service)
):
    """获取下载进度信息"""
    try:
        progress = await transfer_service.get_transfer_progress(session_id)
        if not progress:
            raise HTTPException(status_code=404, detail="会话不存在")
            
        session = await transfer_service.get_session_info(session_id)
        
        return TransferProgressResponse(
            session_id=progress.session_id,
            percentage=progress.percentage,
            bytes_transferred=progress.bytes_transferred,
            total_bytes=progress.total_bytes,
            transfer_rate_bps=progress.transfer_rate_bps,
            estimated_completion=progress.estimated_completion.isoformat() if progress.estimated_completion else None,
            elapsed_seconds=progress.elapsed_seconds,
            completed_chunks=progress.completed_chunks,
            total_chunks=progress.total_chunks,
            current_chunk=progress.current_chunk,
            failed_chunks=progress.failed_chunks or [],
            status=session.status.value if session else "unknown"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取下载进度失败: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")


# ============================================================================
# 通用会话管理接口
# ============================================================================

@router.get("/sessions", summary="列出活跃会话")
async def list_sessions(
    session_type: Optional[str] = Query(None, description="会话类型过滤"),
    project_uid: Optional[str] = Query(None, description="项目UID过滤"),
    transfer_service=Depends(get_file_transfer_service)
):
    """列出活跃的传输会话"""
    try:
        sessions = await transfer_service.list_active_sessions()
        
        # 过滤会话
        filtered_sessions = []
        for session in sessions:
            if session_type and session.session_type.value != session_type:
                continue
            if project_uid and session.metadata.get("project_uid") != project_uid:
                continue
            filtered_sessions.append(session)
            
        # 转换响应格式
        session_responses = []
        for session in filtered_sessions:
            session_responses.append({
                "session_id": session.session_id,
                "session_type": session.session_type.value,
                "file_name": session.file_name,
                "file_size": session.file_size,
                "total_chunks": session.total_chunks,
                "completed_chunks": session.completed_chunks,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "metadata": session.metadata
            })
            
        return {
            "sessions": session_responses,
            "total_count": len(session_responses)
        }
        
    except Exception as e:
        logger.error(f"列出会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出会话失败: {str(e)}")


@router.post("/sessions/{session_id}/cancel", summary="取消传输会话")
async def cancel_session(
    session_id: str,
    transfer_service=Depends(get_file_transfer_service)
):
    """取消传输会话"""
    try:
        success = await transfer_service.cancel_transfer(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或已完成")
            
        return {
            "success": True,
            "message": f"会话 {session_id} 已取消"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消会话失败: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"取消会话失败: {str(e)}")


@router.post("/sessions/{session_id}/resume", summary="恢复传输会话")
async def resume_session(
    session_id: str,
    transfer_service=Depends(get_file_transfer_service)
):
    """恢复暂停的传输会话"""
    try:
        success = await transfer_service.resume_transfer(session_id)
        if not success:
            raise HTTPException(status_code=400, detail="会话无法恢复")
            
        return {
            "success": True,
            "message": f"会话 {session_id} 已恢复"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复会话失败: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"恢复会话失败: {str(e)}")


# ============================================================================
# 批量操作接口
# ============================================================================

@router.post("/batch/upload/prepare", summary="批量准备上传")
async def batch_prepare_upload(
    requests: List[PrepareUploadRequest],
    transfer_service=Depends(get_file_transfer_service)
):
    """批量创建上传会话"""
    try:
        results = []
        errors = []
        
        for i, request in enumerate(requests):
            try:
                config = TransferConfig(
                    chunk_size=request.chunk_size,
                    max_concurrent_chunks=request.max_concurrent_chunks,
                    compression_enabled=request.compression_enabled
                )
                
                session = await transfer_service.initialize_upload_session(
                    file_name=request.file_name,
                    file_size=request.file_size,
                    file_hash=request.file_hash,
                    metadata={
                        "project_uid": request.project_uid,
                        "batch_index": i,
                        **request.metadata
                    },
                    config=config
                )
                
                results.append({
                    "index": i,
                    "session_id": session.session_id,
                    "status": "success"
                })
                
            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e),
                    "file_name": request.file_name
                })
                
        return {
            "success": len(errors) == 0,
            "total_requests": len(requests),
            "successful_sessions": len(results),
            "failed_sessions": len(errors),
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"批量准备上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


# 导入缺少的模块
import io