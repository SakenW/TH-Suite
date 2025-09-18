"""
同步协议管理相关路由
提供与Trans-Hub平台的数据同步功能
V5架构 - 集成同步协议服务
"""

import logging
from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from infrastructure.services.sync_protocol_service import (
    get_sync_protocol_service, 
    SyncProtocolService,
    SyncDirection,
    SyncStatus
)

logger = logging.getLogger(__name__)

def get_sync_service() -> SyncProtocolService:
    """依赖注入：获取同步协议服务"""
    return get_sync_protocol_service()

router = APIRouter(
    prefix="/api/v1/sync",
    tags=["同步协议管理"],
    responses={404: {"description": "Not found"}},
)


class SyncRequest(BaseModel):
    """同步请求模型"""
    direction: str = "bidirectional"  # sync_in, sync_out, bidirectional
    sync_type: str = "incremental"    # incremental, full, realtime
    project_uid: Optional[str] = None


class ScheduleRequest(BaseModel):
    """同步调度请求模型"""
    sync_type: str = "incremental"
    interval_seconds: Optional[int] = None


class ConflictResolutionRequest(BaseModel):
    """冲突解决请求模型"""
    conflict_id: str
    resolution: str  # use_local, use_remote, merge, ignore


@router.get("/test", response_model=dict[str, Any])
async def sync_test_endpoint():
    """
    同步路由测试端点
    """
    return {
        "success": True,
        "message": "Sync routes are working",
        "service": "sync-protocol",
        "supported_directions": ["sync_in", "sync_out", "bidirectional"],
        "supported_types": ["incremental", "full", "realtime"],
        "endpoints_available": [
            "GET /api/v1/sync/test",
            "GET /api/v1/sync/status",
            "POST /api/v1/sync/execute",
            "POST /api/v1/sync/schedule",
            "GET /api/v1/sync/conflicts",
            "POST /api/v1/sync/conflicts/{conflict_id}/resolve",
            "GET /api/v1/sync/validate-connection"
        ],
    }


@router.get("/status", response_model=dict[str, Any])
async def get_sync_status(
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    获取同步状态信息
    """
    try:
        status = sync_service.get_sync_status()
        
        return {
            "success": True,
            "data": status,
            "message": "同步状态获取成功",
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=dict[str, Any])
async def execute_sync(
    request: SyncRequest,
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    执行数据同步
    
    Args:
        request: 同步请求参数
    """
    try:
        # 验证同步方向
        try:
            direction = SyncDirection(request.direction)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的同步方向: {request.direction}"
            )
            
        # 验证同步类型
        valid_types = ["incremental", "full", "realtime"]
        if request.sync_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的同步类型: {request.sync_type}。支持的类型: {valid_types}"
            )
            
        # 执行同步
        result = await sync_service.sync_data(
            direction=direction,
            sync_type=request.sync_type,
            project_uid=request.project_uid
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": f"同步执行成功: {request.direction} {request.sync_type}",
            }
        else:
            return {
                "success": False,
                "error": {
                    "code": "SYNC_FAILED",
                    "message": result.get("message", "同步执行失败"),
                    "details": result
                },
                "message": "同步执行失败",
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule", response_model=dict[str, Any])
async def schedule_sync(
    request: ScheduleRequest,
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    调度定期同步
    
    Args:
        request: 调度请求参数
    """
    try:
        # 验证同步类型
        valid_types = ["incremental", "full", "realtime"]
        if request.sync_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的同步类型: {request.sync_type}。支持的类型: {valid_types}"
            )
            
        # 调度同步
        result = await sync_service.schedule_sync(
            sync_type=request.sync_type,
            interval_seconds=request.interval_seconds
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"同步调度成功: {request.sync_type}",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调度同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate-connection", response_model=dict[str, Any])
async def validate_connection(
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    验证与Trans-Hub的连接
    """
    try:
        result = await sync_service.validate_connection()
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "连接验证成功",
            }
        else:
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": result.get("message", "连接验证失败"),
                    "details": result
                },
                "message": "连接验证失败",
            }
            
    except Exception as e:
        logger.error(f"验证连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts", response_model=dict[str, Any])
async def get_sync_conflicts(
    project_uid: Optional[str] = None,
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    获取同步冲突信息
    
    Args:
        project_uid: 项目UID（可选，过滤特定项目的冲突）
    """
    try:
        result = await sync_service.get_sync_conflicts(project_uid=project_uid)
        
        return {
            "success": True,
            "data": result,
            "message": "同步冲突信息获取成功",
        }
        
    except Exception as e:
        logger.error(f"获取同步冲突失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflicts/{conflict_id}/resolve", response_model=dict[str, Any])
async def resolve_conflict(
    conflict_id: str,
    request: ConflictResolutionRequest,
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    解决同步冲突
    
    Args:
        conflict_id: 冲突ID
        request: 冲突解决请求
    """
    try:
        # 验证冲突ID一致性
        if conflict_id != request.conflict_id:
            raise HTTPException(
                status_code=400,
                detail="路径中的conflict_id与请求体中的conflict_id不一致"
            )
            
        # 解决冲突
        result = await sync_service.resolve_conflict(
            conflict_id=conflict_id,
            resolution=request.resolution
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": f"冲突解决成功: {conflict_id}",
            }
        else:
            return {
                "success": False,
                "error": {
                    "code": "CONFLICT_RESOLUTION_FAILED",
                    "message": result.get("message", "冲突解决失败"),
                    "details": result
                },
                "message": "冲突解决失败",
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决冲突失败 {conflict_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=dict[str, Any])
async def get_sync_statistics(
    sync_service: SyncProtocolService = Depends(get_sync_service)
):
    """
    获取同步统计信息
    """
    try:
        # 获取同步状态
        status = sync_service.get_sync_status()
        
        # 模拟统计数据
        statistics = {
            "total_syncs": 42,
            "successful_syncs": 39,
            "failed_syncs": 3,
            "last_24h_syncs": 8,
            "avg_sync_duration": 12.5,
            "data_volume": {
                "total_synced_mb": 145.7,
                "last_sync_mb": 3.2,
                "compression_ratio": 0.68
            },
            "sync_types": {
                "incremental": 35,
                "full": 5,
                "realtime": 2
            },
            "directions": {
                "sync_in": 18,
                "sync_out": 16,
                "bidirectional": 8
            }
        }
        
        return {
            "success": True,
            "data": {
                "current_status": status,
                "statistics": statistics,
                "generated_at": datetime.now().isoformat()
            },
            "message": "同步统计信息获取成功",
        }
        
    except Exception as e:
        logger.error(f"获取同步统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))