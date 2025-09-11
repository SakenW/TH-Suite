"""
扫描相关路由
提供目录扫描、进度查询和结果获取功能
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from application.services.scan_application_service import ScanApplicationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/scan",
    tags=["扫描管理"],
    responses={404: {"description": "Not found"}},
)


class ScanRequest(BaseModel):
    """扫描请求模型"""

    directory: str
    incremental: bool = True
    project_id: str | None = None


class ScanStatus(BaseModel):
    """扫描状态模型"""

    scan_id: str
    status: str  # scanning, completed, failed, cancelled
    progress: float
    current_file: str | None = None
    processed_files: int = 0
    total_files: int = 0


@router.get("/test", response_model=dict[str, Any])
async def scan_test_endpoint():
    """
    扫描路由测试端点

    用于验证扫描路由是否正常工作
    """
    return {
        "success": True,
        "message": "Scan routes are working",
        "service": "scan-management",
        "endpoints_available": [
            "GET /api/v1/scan/test",
            "POST /api/v1/scan/start",
            "GET /api/v1/scan/status/{scan_id}",
            "GET /api/v1/scan/results/{scan_id}",
            "POST /api/v1/scan/cancel/{scan_id}",
        ],
    }


@router.post("/start", response_model=dict[str, Any])
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    启动目录扫描

    Args:
        request: 扫描请求参数
        background_tasks: 后台任务管理器
    """
    try:
        # 使用扫描应用服务启动扫描
        scan_service = ScanApplicationService()
        result = await scan_service.start_project_scan(
            directory=request.directory,
            incremental=request.incremental
        )
        
        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "scan_id": result["scan_id"],
                    "directory": request.directory,
                    "incremental": request.incremental,
                    "status": "started",
                    "started_at": result.get("started_at"),
                },
                "message": result.get("message", "扫描任务已启动"),
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "启动扫描失败"))
            
    except ValueError as e:
        logger.error(f"启动扫描参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{scan_id}", response_model=dict[str, Any])
async def get_scan_status(scan_id: str):
    """
    获取扫描状态

    Args:
        scan_id: 扫描任务ID
    """
    try:
        # 使用扫描应用服务获取状态
        scan_service = ScanApplicationService()
        result = await scan_service.get_scan_status(scan_id)
        
        if result.get("success"):
            return {
                "success": True,
                "data": result["data"],
                "message": f"扫描状态获取成功: {scan_id}",
            }
        else:
            # 如果扫描不存在，返回404而不是500
            if "未找到" in result.get("message", ""):
                raise HTTPException(status_code=404, detail=result.get("message"))
            raise HTTPException(status_code=500, detail=result.get("message"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取扫描状态失败 {scan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{scan_id}", response_model=dict[str, Any])
async def get_scan_results(scan_id: str):
    """
    获取扫描结果

    Args:
        scan_id: 扫描任务ID
    """
    try:
        # 使用扫描应用服务获取结果
        scan_service = ScanApplicationService()
        result = await scan_service.get_scan_results(scan_id)
        
        if result.get("success"):
            return {
                "success": True,
                "data": result["data"],
                "message": f"扫描结果获取成功: {scan_id}",
            }
        else:
            # 根据错误类型返回相应的HTTP状态码
            error_msg = result.get("message", "")
            if "不存在" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            elif "未完成" in error_msg:
                raise HTTPException(status_code=409, detail=error_msg)  # Conflict
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取扫描结果失败 {scan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{scan_id}", response_model=dict[str, Any])
async def cancel_scan(scan_id: str):
    """
    取消扫描任务

    Args:
        scan_id: 扫描任务ID
    """
    try:
        # 使用扫描应用服务取消扫描
        scan_service = ScanApplicationService()
        result = await scan_service.cancel_scan(scan_id)
        
        if result.get("success"):
            return {
                "success": True,
                "data": {"scan_id": scan_id, "status": "cancelled"},
                "message": result.get("message", f"扫描任务已取消: {scan_id}"),
            }
        else:
            # 如果扫描不存在或已完成，返回404
            error_msg = result.get("message", "")
            if "不存在" in error_msg or "已完成" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消扫描失败 {scan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=dict[str, Any])
async def get_active_scans():
    """
    获取当前活跃的扫描任务
    """
    try:
        # 从扫描器实例获取活跃扫描
        from core.ddd_scanner_simple import get_scanner_instance
        from pathlib import Path
        
        # 使用V6 API数据库路径，保持数据库一致性
        v6_db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n_v6.db"
        scanner = get_scanner_instance(str(v6_db_path))
        active_scans = []
        
        for scan_id, scan_data in scanner.active_scans.items():
            active_scans.append({
                "scan_id": scan_id,
                "status": scan_data.get("status", "unknown"),
                "progress": scan_data.get("progress", 0.0),
                "started_at": scan_data.get("started_at"),
                "current_file": scan_data.get("current_file"),
                "processed_files": scan_data.get("processed_files", 0),
                "total_files": scan_data.get("total_files", 0),
            })
        
        return {
            "success": True,
            "data": {"active_scans": active_scans, "total": len(active_scans)},
            "message": "活跃扫描列表获取成功",
        }
    except Exception as e:
        logger.error(f"获取活跃扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict[str, Any])
async def get_database_stats():
    """
    获取数据库统计信息
    直接从V6数据库查询统计数据，用于前端显示
    """
    try:
        import sqlite3
        from pathlib import Path
        
        # 使用V6数据库路径
        v6_db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n_v6.db"
        
        if not v6_db_path.exists():
            raise HTTPException(status_code=404, detail="V6数据库不存在")
            
        conn = sqlite3.connect(str(v6_db_path))
        cursor = conn.cursor()
        
        # 获取各表统计数据
        cursor.execute("SELECT COUNT(*) FROM core_mods")
        mod_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM core_language_files")
        file_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM core_translation_entries")
        entry_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "totalProjects": mod_count,
                "totalFiles": file_count,
                "totalEntries": entry_count,
                "database_path": str(v6_db_path),
            },
            "message": "数据库统计获取成功",
        }
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
