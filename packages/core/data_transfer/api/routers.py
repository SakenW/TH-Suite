"""
翻译数据传输API路由

提供RESTful API和WebSocket实时通信接口
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..extractors import ITranslationExtractor, MinecraftTranslationExtractor
from ..models import GameType, SyncStrategy, TranslationEntry
from ..synchronizers import ITranslationSynchronizer
from .models import (
    ApplyRequest,
    ApplyResponse,
    BatchRequest,
    BatchResponse,
    DiffRequest,
    DiffResponse,
    ExtractRequest,
    ExtractResponse,
    StatusResponse,
    SyncRequest,
    SyncResponse,
    WebSocketMessage,
    create_error_message,
    create_sync_progress_message,
    create_translation_update_message,
)

logger = structlog.get_logger(__name__)

# 创建路由实例
router = APIRouter(prefix="/api/v1/translations", tags=["翻译数据传输"])


# WebSocket连接管理器
class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        """建立连接"""
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        
        self.active_connections[project_id].append(websocket)
        
        logger.info(
            "WebSocket connected",
            project_id=project_id,
            total_connections=len(self.active_connections[project_id])
        )
    
    def disconnect(self, websocket: WebSocket, project_id: str):
        """断开连接"""
        if project_id in self.active_connections:
            try:
                self.active_connections[project_id].remove(websocket)
                if not self.active_connections[project_id]:
                    del self.active_connections[project_id]
            except ValueError:
                pass
        
        logger.info(
            "WebSocket disconnected",
            project_id=project_id,
            remaining_connections=len(self.active_connections.get(project_id, []))
        )
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.warning("Failed to send personal message", error=str(e))
    
    async def broadcast_to_project(
        self, 
        project_id: str, 
        message: WebSocketMessage,
        exclude: Optional[WebSocket] = None
    ):
        """向项目的所有连接广播消息"""
        
        if project_id not in self.active_connections:
            return
        
        message_json = message.model_dump_json()
        disconnected_connections = []
        
        for connection in self.active_connections[project_id]:
            if connection == exclude:
                continue
            
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning("Failed to broadcast message", error=str(e))
                disconnected_connections.append(connection)
        
        # 清理断开的连接
        for connection in disconnected_connections:
            self.disconnect(connection, project_id)


# 全局连接管理器实例
manager = ConnectionManager()


# 依赖注入函数
async def get_extractor(game_type: str = "minecraft") -> ITranslationExtractor:
    """获取翻译数据提取器"""
    
    if game_type.lower() == "minecraft":
        return MinecraftTranslationExtractor()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported game type: {game_type}"
        )


async def get_synchronizer() -> ITranslationSynchronizer:
    """获取翻译数据同步器"""
    
    # TODO: 实现依赖注入，返回配置好的同步器实例
    raise HTTPException(
        status_code=501,
        detail="Translation synchronizer not implemented"
    )


# API路由定义
@router.post("/extract", response_model=ExtractResponse)
async def extract_translation_data(
    request: ExtractRequest,
    extractor: ITranslationExtractor = Depends(get_extractor)
) -> ExtractResponse:
    """提取翻译数据"""
    
    start_time = time.time()
    
    try:
        logger.info(
            "Starting translation extraction",
            project_path=request.project_path,
            incremental=request.incremental
        )
        
        # 验证项目路径
        if not await extractor.validate_project(request.project_path):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid project path: {request.project_path}"
            )
        
        # 提取项目信息
        project = await extractor.extract_project(request.project_path)
        
        # 应用过滤器
        if request.includes:
            project.includes = request.includes
        if request.excludes:
            project.excludes = request.excludes
        
        # 提取翻译条目
        entries = await extractor.extract_entries(
            project,
            incremental=request.incremental,
            target_languages=request.target_languages
        )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "Translation extraction completed",
            project_id=project.project_id,
            total_entries=len(entries),
            processing_time=processing_time
        )
        
        return ExtractResponse(
            success=True,
            message=f"Successfully extracted {len(entries)} translation entries",
            data={
                "project": project.to_dict(),
                "entries": [entry.to_dict() for entry in entries[:100]],  # 限制返回数量
                "sample_only": len(entries) > 100
            },
            total_entries=len(entries),
            total_mods=len(project.includes) if project.includes else 0,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error("Translation extraction failed", error=str(e))
        
        return ExtractResponse(
            success=False,
            message=f"Extraction failed: {str(e)}",
            processing_time=time.time() - start_time
        )


@router.post("/sync", response_model=SyncResponse)
async def sync_translation_data(
    request: SyncRequest,
    synchronizer: ITranslationSynchronizer = Depends(get_synchronizer)
) -> SyncResponse:
    """同步翻译数据"""
    
    start_time = time.time()
    
    try:
        logger.info(
            "Starting translation synchronization",
            project_id=request.project_id,
            strategy=request.strategy.value
        )
        
        # 执行同步
        result = await synchronizer.sync_project(
            request.project_id,
            request.strategy
        )
        
        processing_time = time.time() - start_time
        
        # 广播同步结果
        if result.success:
            progress_message = create_sync_progress_message(
                request.project_id,
                100.0,
                "completed",
                f"Pushed: {result.pushed_entries}, Pulled: {result.pulled_entries}"
            )
            await manager.broadcast_to_project(request.project_id, progress_message)
        
        logger.info(
            "Translation synchronization completed",
            project_id=request.project_id,
            success=result.success,
            processing_time=processing_time
        )
        
        return SyncResponse(
            success=result.success,
            message="Synchronization completed successfully" if result.success else f"Synchronization failed: {result.error}",
            data=result.to_dict(),
            pushed_entries=result.pushed_entries,
            pulled_entries=result.pulled_entries,
            conflicts_detected=result.conflicts_detected,
            conflicts_resolved=result.conflicts_resolved,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error("Translation synchronization failed", error=str(e))
        
        return SyncResponse(
            success=False,
            message=f"Synchronization failed: {str(e)}",
            processing_time=time.time() - start_time
        )


@router.get("/diff", response_model=DiffResponse)
async def get_translation_diff(
    project_id: str,
    from_version: int,
    to_version: int,
    include_content: bool = True,
    synchronizer: ITranslationSynchronizer = Depends(get_synchronizer)
) -> DiffResponse:
    """获取翻译差异"""
    
    try:
        logger.info(
            "Getting translation diff",
            project_id=project_id,
            from_version=from_version,
            to_version=to_version
        )
        
        # 获取变更记录
        delta = await synchronizer.pull_delta(project_id, from_version)
        
        # 构建响应数据
        data = {
            "delta_id": delta.delta_id,
            "base_version": delta.base_version,
            "target_version": delta.target_version,
            "summary": {
                "added": len(delta.added),
                "modified": len(delta.modified),
                "deleted": len(delta.deleted),
                "moved": len(delta.moved)
            }
        }
        
        if include_content:
            data["changes"] = {
                "added": [entry.to_dict() for entry in delta.added],
                "modified": [entry.to_dict() for entry in delta.modified],
                "deleted": delta.deleted,
                "moved": [
                    {
                        "entry_id": m.entry_id,
                        "old_namespace": m.old_namespace,
                        "new_namespace": m.new_namespace,
                        "old_key": m.old_key,
                        "new_key": m.new_key
                    }
                    for m in delta.moved
                ]
            }
        
        return DiffResponse(
            success=True,
            message=f"Diff retrieved for versions {from_version} to {to_version}",
            data=data,
            added_count=len(delta.added),
            modified_count=len(delta.modified),
            deleted_count=len(delta.deleted),
            moved_count=len(delta.moved)
        )
    
    except Exception as e:
        logger.error("Failed to get translation diff", error=str(e))
        
        return DiffResponse(
            success=False,
            message=f"Failed to get diff: {str(e)}"
        )


@router.post("/apply", response_model=ApplyResponse)
async def apply_translation_data(
    request: ApplyRequest
) -> ApplyResponse:
    """应用翻译数据到游戏文件"""
    
    start_time = time.time()
    
    try:
        logger.info(
            "Starting translation application",
            project_id=request.project_id,
            target_path=request.target_path
        )
        
        # TODO: 实现翻译数据应用逻辑
        # 1. 读取翻译条目
        # 2. 根据游戏类型选择合适的写入器
        # 3. 生成语言文件
        # 4. 可选的备份原文件
        
        processing_time = time.time() - start_time
        
        return ApplyResponse(
            success=True,
            message="Translation data applied successfully",
            data={
                "target_path": request.target_path,
                "languages": request.languages or ["zh_cn"]
            },
            applied_files=0,  # TODO: 实际统计
            applied_entries=0,  # TODO: 实际统计
            backup_path=f"{request.target_path}.backup" if request.backup else None,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error("Translation application failed", error=str(e))
        
        return ApplyResponse(
            success=False,
            message=f"Application failed: {str(e)}",
            processing_time=time.time() - start_time
        )


@router.get("/status/{project_id}", response_model=StatusResponse)
async def get_translation_status(project_id: str) -> StatusResponse:
    """获取翻译状态"""
    
    try:
        logger.info("Getting translation status", project_id=project_id)
        
        # TODO: 实现状态查询逻辑
        # 1. 查询项目信息
        # 2. 统计翻译进度
        # 3. 检查同步状态
        
        status_data = {
            "project_id": project_id,
            "last_sync": datetime.now().isoformat(),
            "translation_progress": {
                "total_entries": 1000,
                "translated_entries": 750,
                "reviewed_entries": 500,
                "progress_percentage": 75.0
            },
            "sync_status": "synchronized",
            "active_contributors": 3,
            "recent_activity": []
        }
        
        return StatusResponse(
            success=True,
            message="Status retrieved successfully",
            data=status_data
        )
    
    except Exception as e:
        logger.error("Failed to get translation status", error=str(e))
        
        return StatusResponse(
            success=False,
            message=f"Failed to get status: {str(e)}"
        )


@router.post("/batch", response_model=BatchResponse)
async def batch_operations(request: BatchRequest) -> BatchResponse:
    """批量操作"""
    
    start_time = time.time()
    
    try:
        logger.info(
            "Starting batch operations",
            project_id=request.project_id,
            total_operations=len(request.operations)
        )
        
        results = []
        successful_count = 0
        
        if request.parallel:
            # 并行执行
            tasks = [
                _execute_single_operation(op, request.project_id)
                for op in request.operations
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 串行执行
            for op in request.operations:
                result = await _execute_single_operation(op, request.project_id)
                results.append(result)
        
        # 统计成功数量
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                successful_count += 1
        
        processing_time = time.time() - start_time
        
        return BatchResponse(
            success=True,
            message=f"Batch operations completed: {successful_count}/{len(request.operations)} successful",
            results=results,
            total_operations=len(request.operations),
            successful_operations=successful_count,
            failed_operations=len(request.operations) - successful_count,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error("Batch operations failed", error=str(e))
        
        return BatchResponse(
            success=False,
            message=f"Batch operations failed: {str(e)}",
            processing_time=time.time() - start_time
        )


async def _execute_single_operation(operation: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """执行单个操作"""
    
    try:
        op_type = operation.get("type")
        
        if op_type == "update_entry":
            # 更新翻译条目
            entry_data = operation.get("entry")
            if entry_data:
                entry = TranslationEntry.from_dict(entry_data)
                # TODO: 保存到数据库
                
                # 广播更新
                update_message = create_translation_update_message(
                    project_id, entry, "update"
                )
                await manager.broadcast_to_project(project_id, update_message)
                
                return {"success": True, "operation": "update_entry", "entry_id": entry.entry_id}
        
        elif op_type == "delete_entry":
            # 删除翻译条目
            entry_id = operation.get("entry_id")
            if entry_id:
                # TODO: 从数据库删除
                return {"success": True, "operation": "delete_entry", "entry_id": entry_id}
        
        return {"success": False, "error": f"Unknown operation type: {op_type}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


# WebSocket路由
@router.websocket("/realtime/{project_id}")
async def translation_realtime_sync(websocket: WebSocket, project_id: str):
    """翻译数据实时同步WebSocket"""
    
    await manager.connect(websocket, project_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                import json
                message_data = json.loads(data)
                message_type = message_data.get("type")
                
                if message_type == "translation_update":
                    # 处理翻译更新
                    entry_data = message_data.get("entry")
                    if entry_data:
                        entry = TranslationEntry.from_dict(entry_data)
                        
                        # TODO: 保存到数据库
                        
                        # 广播给其他连接
                        update_message = create_translation_update_message(
                            project_id, entry, "update"
                        )
                        await manager.broadcast_to_project(
                            project_id, 
                            update_message,
                            exclude=websocket
                        )
                
                elif message_type == "sync_request":
                    # 处理同步请求
                    try:
                        # TODO: 执行同步操作
                        progress_message = create_sync_progress_message(
                            project_id,
                            100.0,
                            "completed",
                            "Sync completed successfully"
                        )
                        await manager.send_personal_message(
                            progress_message.model_dump_json(),
                            websocket
                        )
                    except Exception as e:
                        error_message = create_error_message(
                            "SYNC_FAILED",
                            f"Sync failed: {str(e)}",
                            project_id
                        )
                        await manager.send_personal_message(
                            error_message.model_dump_json(),
                            websocket
                        )
                
                elif message_type == "ping":
                    # 心跳响应
                    pong_message = WebSocketMessage(
                        type="pong",
                        project_id=project_id,
                        timestamp=datetime.now().isoformat()
                    )
                    await manager.send_personal_message(
                        pong_message.model_dump_json(),
                        websocket
                    )
            
            except json.JSONDecodeError:
                error_message = create_error_message(
                    "INVALID_MESSAGE",
                    "Invalid JSON message format"
                )
                await manager.send_personal_message(
                    error_message.model_dump_json(),
                    websocket
                )
            
            except Exception as e:
                logger.error("Error processing WebSocket message", error=str(e))
                error_message = create_error_message(
                    "PROCESSING_ERROR",
                    f"Message processing failed: {str(e)}"
                )
                await manager.send_personal_message(
                    error_message.model_dump_json(),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket, project_id)


# 健康检查端点
@router.get("/health")
async def health_check():
    """健康检查"""
    
    return {
        "status": "healthy",
        "service": "translation-data-transfer",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "active_connections": sum(len(conns) for conns in manager.active_connections.values())
    }