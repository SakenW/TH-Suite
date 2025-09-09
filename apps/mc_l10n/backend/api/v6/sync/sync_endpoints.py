"""
V6 同步协议 API端点
实现Bloom握手、分片传输、会话管理等同步功能
"""

import uuid
import hashlib
import blake3
import base64
import struct
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
import structlog

from .models import (
    BloomHandshakeRequest, BloomHandshakeResponse,
    ChunkUploadRequest, ChunkUploadResponse, 
    SyncCommitRequest, SyncCommitResponse,
    EntryDelta, SyncSession, SyncStatistics, SyncCapability,
    SyncProtocolVersion
)
from .sync_service import get_sync_service
from services.content_addressing import compute_cid, HashAlgorithm
from services.performance_optimizer import get_upload_manager, PerformanceOptimizer

# 初始化日志
logger = structlog.get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/sync", tags=["同步协议"])

# 模拟会话存储 (生产环境应该使用数据库)
active_sessions: Dict[str, SyncSession] = {}
session_chunks: Dict[str, Dict[str, List[bytes]]] = {}  # session_id -> cid -> chunks

# 全局性能优化器实例
_performance_optimizer: Optional[PerformanceOptimizer] = None


async def get_performance_optimizer() -> PerformanceOptimizer:
    """获取性能优化器实例"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer(
            max_concurrent_uploads=8,
            chunk_size_kb=2048,  # 2MB
            memory_limit_mb=512,
            enable_compression=True
        )
        await _performance_optimizer.start()
        logger.info("同步协议性能优化器初始化完成")
    return _performance_optimizer


class BloomFilter:
    """简单的Bloom过滤器实现"""
    
    def __init__(self, bits: int = 8388608, hashes: int = 7):
        self.bits = bits
        self.hashes = hashes
        self.bit_array = bytearray(bits // 8)
    
    def _hash_functions(self, data: str) -> List[int]:
        """生成多个哈希值"""
        hashes = []
        for i in range(self.hashes):
            h = hashlib.blake2b(data.encode(), key=f"hash{i}".encode(), digest_size=8)
            hash_int = struct.unpack('>Q', h.digest())[0]
            hashes.append(hash_int % self.bits)
        return hashes
    
    def add(self, data: str):
        """添加数据到过滤器"""
        for hash_val in self._hash_functions(data):
            byte_idx = hash_val // 8
            bit_idx = hash_val % 8
            self.bit_array[byte_idx] |= (1 << bit_idx)
    
    def might_contain(self, data: str) -> bool:
        """检查数据是否可能存在"""
        for hash_val in self._hash_functions(data):
            byte_idx = hash_val // 8
            bit_idx = hash_val % 8
            if not (self.bit_array[byte_idx] & (1 << bit_idx)):
                return False
        return True
    
    def to_base64(self) -> str:
        """转换为Base64字符串"""
        return base64.b64encode(self.bit_array).decode('ascii')
    
    @classmethod
    def from_base64(cls, b64_data: str, bits: int = 8388608, hashes: int = 7):
        """从Base64字符串创建"""
        bloom = cls(bits, hashes)
        bloom.bit_array = bytearray(base64.b64decode(b64_data))
        return bloom


def get_server_capabilities() -> SyncCapability:
    """获取服务端同步能力"""
    return SyncCapability(
        supported_versions=[SyncProtocolVersion.V1],
        max_chunk_size_bytes=2097152,  # 2MB
        max_concurrent_chunks=4,
        compression_algorithms=["zstd", "gzip"],
        supported_formats=["json"],
        supports_resume=True,
        supports_delta_compression=False
    )


async def get_server_cids(sync_scope: Optional[Dict[str, Any]] = None) -> List[str]:
    """获取服务端所有CID列表"""
    sync_service = get_sync_service()
    return await sync_service.get_server_cids(sync_scope)


def find_missing_cids(client_bloom: BloomFilter, server_cids: List[str]) -> List[str]:
    """查找客户端缺失的CID"""
    missing = []
    for cid in server_cids:
        if not client_bloom.might_contain(cid):
            missing.append(cid)
    return missing


@router.post("/handshake", 
             response_model=BloomHandshakeResponse,
             summary="Bloom握手",
             description="通过Bloom过滤器协商需要同步的数据")
async def bloom_handshake(request: BloomHandshakeRequest):
    """
    执行Bloom握手协议
    
    1. 接收客户端的Bloom过滤器
    2. 与服务端CID集合对比
    3. 返回客户端缺失的CID列表
    4. 创建同步会话
    """
    try:
        logger.info("开始Bloom握手", 
                   client_id=request.client_id,
                   session_id=request.session_id)
        
        # 解析客户端Bloom过滤器
        client_bloom = BloomFilter.from_base64(
            request.bloom_filter,
            request.bloom_bits,
            request.bloom_hashes
        )
        
        # 获取同步服务
        sync_service = get_sync_service()
        
        # 获取服务端CID集合
        server_cids = await sync_service.get_server_cids(request.sync_scope)
        
        # 查找缺失的CID
        missing_cids = find_missing_cids(client_bloom, server_cids)
        
        # 创建同步会话
        session = await sync_service.create_sync_session(
            client_id=request.client_id,
            session_id=request.session_id,
            ttl_hours=1
        )
        
        # 更新会话元数据
        session.total_cids = len(missing_cids)
        session.metadata = {
            "bloom_bits": request.bloom_bits,
            "bloom_hashes": request.bloom_hashes,
            "missing_cids": missing_cids[:10],  # 只保存前10个用于调试
            "server_cids_count": len(server_cids)
        }
        
        # 存储会话
        active_sessions[request.session_id] = session
        session_chunks[request.session_id] = {}
        
        # 准备响应
        response = BloomHandshakeResponse(
            session_id=request.session_id,
            server_protocol_version=SyncProtocolVersion.V1,
            missing_cids=missing_cids,
            server_info={
                "server_time": datetime.now().isoformat(),
                "total_server_cids": len(server_cids),
                "server_capabilities": get_server_capabilities().dict()
            },
            chunk_size_bytes=2097152,
            max_concurrent_chunks=4,
            session_expires_at=session.expires_at
        )
        
        logger.info("Bloom握手完成",
                   session_id=request.session_id,
                   missing_cids_count=len(missing_cids),
                   bloom_efficiency=1.0 - (len(missing_cids) / len(server_cids)) if server_cids else 0)
        
        return response
        
    except Exception as e:
        logger.error("Bloom握手失败", 
                    session_id=request.session_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"握手失败: {str(e)}")


@router.put("/chunk/{cid}",
           response_model=ChunkUploadResponse,
           summary="分片上传", 
           description="上传Entry-Delta数据分片")
async def upload_chunk(
    cid: str,
    request: ChunkUploadRequest,
    x_idempotency_key: Optional[str] = Header(None)
):
    """
    上传Entry-Delta数据分片
    
    支持断点续传和并发上传
    """
    try:
        # 验证会话
        session = active_sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        if session.status != "active":
            raise HTTPException(status_code=400, detail=f"会话状态无效: {session.status}")
        
        # 验证CID格式
        if not cid.startswith("blake3:"):
            raise HTTPException(status_code=400, detail="无效的CID格式，必须以blake3:开头")
        
        # 解码数据
        try:
            chunk_data = base64.b64decode(request.data)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的Base64数据")
        
        # 验证分片哈希 (使用真实的BLAKE3)
        actual_cid = compute_cid(chunk_data, HashAlgorithm.BLAKE3)
        actual_hash = str(actual_cid)
        if request.chunk_hash != actual_hash:
            raise HTTPException(status_code=400, detail="分片哈希验证失败")
        
        # 初始化CID的分片存储
        if cid not in session_chunks[request.session_id]:
            session_chunks[request.session_id][cid] = [None] * request.total_chunks
        
        chunks = session_chunks[request.session_id][cid]
        
        # 使用性能优化器处理分片存储
        optimizer = await get_performance_optimizer()
        
        # 存储分片（保持原有逻辑以保证兼容性）
        if request.chunk_index < len(chunks):
            chunks[request.chunk_index] = chunk_data
        else:
            raise HTTPException(status_code=400, detail="分片索引超出范围")
        
        # 更新性能指标
        if optimizer.upload_manager:
            optimizer.upload_manager.metrics.uploaded_bytes += len(chunk_data)
            optimizer.upload_manager.metrics.completed_tasks += 1
        
        # 计算进度
        received_chunks = sum(1 for chunk in chunks if chunk is not None)
        bytes_received = sum(len(chunk) for chunk in chunks if chunk is not None)
        
        # 判断是否完成
        if received_chunks == request.total_chunks:
            status = "completed"
            # TODO: 这里应该将完整数据写入数据库
            logger.info("CID分片传输完成", 
                       session_id=request.session_id,
                       cid=cid,
                       total_bytes=bytes_received)
        else:
            status = "received"
        
        # 确定下一个分片
        next_chunk_index = None
        for i, chunk in enumerate(chunks):
            if chunk is None:
                next_chunk_index = i
                break
        
        response = ChunkUploadResponse(
            session_id=request.session_id,
            cid=cid,
            chunk_index=request.chunk_index,
            status=status,
            bytes_received=bytes_received,
            total_bytes=request.data_size * request.total_chunks,  # 估算
            next_chunk_index=next_chunk_index
        )
        
        logger.info("分片上传成功",
                   session_id=request.session_id,
                   cid=cid,
                   chunk_index=request.chunk_index,
                   progress=f"{received_chunks}/{request.total_chunks}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("分片上传失败",
                    session_id=request.session_id,
                    cid=cid,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/commit",
            response_model=SyncCommitResponse,
            summary="提交同步会话",
            description="提交已完成的同步数据并执行合并")
async def commit_sync(request: SyncCommitRequest):
    """
    提交同步会话
    
    1. 验证所有CID都已完整上传
    2. 解析Entry-Delta数据
    3. 执行3-way合并
    4. 处理冲突
    5. 完成会话
    """
    try:
        # 验证会话
        session = active_sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        logger.info("开始提交同步会话",
                   session_id=request.session_id,
                   completed_cids_count=len(request.completed_cids))
        
        # 验证所有CID都已完整上传
        session_chunk_data = session_chunks.get(request.session_id, {})
        missing_cids = []
        
        for cid in request.completed_cids:
            if cid not in session_chunk_data:
                missing_cids.append(cid)
                continue
                
            chunks = session_chunk_data[cid]
            if None in chunks:
                missing_cids.append(cid)
        
        if missing_cids:
            raise HTTPException(
                status_code=400, 
                detail=f"以下CID尚未完整上传: {missing_cids[:5]}"
            )
        
        # 获取同步服务
        sync_service = get_sync_service()
        
        # 处理每个CID的数据
        all_deltas = []
        
        for cid in request.completed_cids:
            try:
                # 重建完整数据
                chunks = session_chunk_data[cid]
                full_data = b''.join(chunks)
                
                # 解析Entry-Delta格式
                from .entry_delta import get_entry_delta_processor
                processor = get_entry_delta_processor()
                deltas = processor.parse_delta_payload(full_data)
                all_deltas.extend(deltas)
                
            except Exception as e:
                logger.error("解析CID数据失败",
                           session_id=request.session_id,
                           cid=cid,
                           error=str(e))
        
        # 批量处理所有Entry-Delta
        if all_deltas:
            process_result = await sync_service.process_entry_deltas(
                all_deltas,
                merge_strategy=request.merge_strategy,
                conflict_resolution=request.conflict_resolution
            )
            
            total_entries = process_result["processed"]
            merged_entries = process_result["merged"] 
            conflict_entries = process_result["conflict_entries"]
            error_entries = process_result["errors"]
        else:
            total_entries = 0
            merged_entries = 0
            conflict_entries = []
            error_entries = 0
        
        # 更新会话状态
        session.status = "completed"
        session.completed_at = datetime.now().isoformat()
        session.completed_cids = len(request.completed_cids)
        
        # 清理会话数据
        if request.session_id in session_chunks:
            del session_chunks[request.session_id]
        
        response = SyncCommitResponse(
            session_id=request.session_id,
            total_entries_processed=total_entries,
            entries_merged=merged_entries,
            entries_conflicts=len(conflict_entries),
            entries_errors=error_entries,
            conflict_entries=conflict_entries,
            completed_at=session.completed_at
        )
        
        logger.info("同步会话提交完成",
                   session_id=request.session_id,
                   total_entries=total_entries,
                   conflicts=len(conflict_entries),
                   errors=error_entries)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("同步提交失败",
                    session_id=request.session_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.get("/sessions",
           response_model=List[SyncSession],
           summary="获取同步会话列表")
async def get_sync_sessions():
    """获取所有活动的同步会话"""
    return list(active_sessions.values())


@router.get("/sessions/{session_id}",
           response_model=SyncSession,
           summary="获取特定同步会话")
async def get_sync_session(session_id: str):
    """获取特定的同步会话信息"""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.delete("/sessions/{session_id}",
              summary="取消同步会话")
async def cancel_sync_session(session_id: str):
    """取消并清理同步会话"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 清理会话数据
    del active_sessions[session_id]
    if session_id in session_chunks:
        del session_chunks[session_id]
    
    logger.info("同步会话已取消", session_id=session_id)
    return {"status": "cancelled", "session_id": session_id}


@router.get("/statistics",
           response_model=SyncStatistics,
           summary="获取同步统计")
async def get_sync_statistics():
    """获取同步协议的统计信息"""
    active_count = len([s for s in active_sessions.values() if s.status == "active"])
    completed_today = len([s for s in active_sessions.values() if s.status == "completed"])
    
    return SyncStatistics(
        active_sessions=active_count,
        total_sessions_today=len(active_sessions),
        bytes_transferred_today=0,  # TODO: 实际统计
        chunks_uploaded_today=0,    # TODO: 实际统计
        avg_session_duration_seconds=300.0,  # 模拟数据
        avg_chunk_upload_speed_mbps=10.0,    # 模拟数据
        bloom_false_positive_rate=0.01,      # 模拟数据
        bloom_efficiency=0.95                # 模拟数据
    )


@router.get("/capabilities",
           response_model=SyncCapability,
           summary="获取服务端同步能力")
async def get_sync_capabilities():
    """获取服务端支持的同步能力"""
    return get_server_capabilities()


@router.get("/performance",
           summary="获取性能优化统计")
async def get_performance_stats():
    """获取同步协议的性能优化统计信息"""
    try:
        optimizer = await get_performance_optimizer()
        performance_summary = optimizer.get_performance_summary()
        
        # 添加同步协议特定的统计
        sync_stats = {
            "active_sessions": len(active_sessions),
            "total_session_chunks": sum(len(chunks) for chunks in session_chunks.values()),
            "chunks_in_progress": sum(
                sum(1 for chunk in chunks.values() if any(c is None for c in chunk))
                for chunks in session_chunks.values()
            ),
            "completed_chunks": sum(
                sum(1 for chunk in chunks.values() if all(c is not None for c in chunk))
                for chunks in session_chunks.values()
            )
        }
        
        return {
            "performance_optimizer": performance_summary,
            "sync_protocol": sync_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("获取性能统计失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取性能统计失败: {str(e)}")


@router.post("/performance/optimize",
            summary="触发性能优化")
async def trigger_performance_optimization(optimization_type: str = "auto"):
    """手动触发性能优化"""
    try:
        optimizer = await get_performance_optimizer()
        
        if optimization_type == "large_files":
            await optimizer.optimize_for_large_files()
            message = "已切换到大文件优化模式"
        elif optimization_type == "small_files":
            await optimizer.optimize_for_small_files()
            message = "已切换到小文件优化模式"
        elif optimization_type == "memory_gc":
            if optimizer.memory_monitor:
                optimizer.memory_monitor.force_gc()
            message = "已执行内存垃圾回收"
        else:
            message = "自动优化模式，无需手动调整"
        
        return {
            "success": True,
            "optimization_type": optimization_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("性能优化触发失败", optimization_type=optimization_type, error=str(e))
        raise HTTPException(status_code=500, detail=f"性能优化失败: {str(e)}")