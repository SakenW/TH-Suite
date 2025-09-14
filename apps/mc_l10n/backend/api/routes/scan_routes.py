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
    prefix="/api/v2.1/scan",
    tags=["扫描管理"],
    responses={404: {"description": "Not found"}},
)


class ScanRequest(BaseModel):
    """扫描请求模型"""

    directory: str
    incremental: bool = True
    project_id: str | None = None
    options: dict | None = None


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
            "GET /api/v2.1/scan/test",
            "POST /api/v2.1/scan/start",
            "GET /api/v2.1/scan/status/{scan_id}",
            "GET /api/v2.1/scan/results/{scan_id}",
            "POST /api/v2.1/scan/cancel/{scan_id}",
            "GET /api/v2.1/scan/active",
            "GET /api/v2.1/scan/stats",
            "GET /api/v2.1/scan/statistics",
            "GET /api/v2.1/scan/history",
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
        # 直接使用简化的Minecraft扫描服务，避免复杂的依赖注入
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        scanner_service = get_simple_minecraft_scanner_service()
        
        # 准备扫描选项
        scan_options = request.options or {}
        scan_options.update({
            "include_subdirectories": True,
            "validate_after_scan": True,
            "generate_statistics": True,
            "file_extensions": [".jar", ".zip"],
            "max_depth": 10,
            "max_file_size_mb": 500
        })
        
        # 启动扫描
        result = await scanner_service.start_scan(
            target_path=request.directory,
            incremental=request.incremental,
            scan_options=scan_options
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
            # 检查是否是路径不存在的错误，返回400而不是500
            error_msg = result.get("error", result.get("message", "启动扫描失败"))
            if "目标路径不存在" in str(error_msg) or ("路径" in str(error_msg) and "不存在" in str(error_msg)):
                raise HTTPException(status_code=400, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
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
        # 直接使用简化的Minecraft扫描服务
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        scanner_service = get_simple_minecraft_scanner_service()
        result = await scanner_service.get_scan_status(scan_id)
        
        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "scan_id": scan_id,
                    "status": result["status"],
                    "progress": result["progress"],
                    "current_item": result.get("current_item", ""),
                    "processed_count": result.get("processed_count", 0),
                    "total_count": result.get("total_count", 0),
                    "duration_seconds": result.get("duration_seconds", 0),
                    "error_message": result.get("error_message"),
                    # 添加统计信息
                    "statistics": result.get("statistics", {}),
                    "mods_found": result.get("mods_found", 0),
                    "total_translation_keys": result.get("total_translation_keys", 0),
                    "language_files_found": result.get("language_files_found", 0),
                    "discovered_items": result.get("discovered_items", [])
                },
                "message": f"扫描状态获取成功: {scan_id}",
            }
        else:
            # 如果扫描不存在，返回404而不是500
            if "不存在" in result.get("error", ""):
                raise HTTPException(status_code=404, detail=result.get("error"))
            raise HTTPException(status_code=500, detail=result.get("error"))
            
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
        # 简化实现，暂时返回空的活跃扫描列表
        active_scans = []  # 暂时没有活跃扫描
        
        return {
            "success": True,
            "data": active_scans,
            "message": f"成功获取 {len(active_scans)} 个活跃扫描",
        }
    except Exception as e:
        logger.error(f"获取活跃扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict[str, Any])
async def get_database_stats():
    """
    获取数据库统计信息
    自动初始化V2.1数据库，用于前端显示
    """
    try:
        from pathlib import Path
        from infrastructure.db_initializer import ensure_v2_1_database, get_v2_1_database_stats
        
        # 使用V2.1数据库路径
        v2_1_db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n_v2_1.db"
        
        # 确保数据库存在，如果不存在则自动创建
        if not ensure_v2_1_database(str(v2_1_db_path)):
            logger.error("数据库初始化失败")
            raise HTTPException(status_code=500, detail="数据库初始化失败")
        
        # 获取数据库统计信息
        db_stats = get_v2_1_database_stats(str(v2_1_db_path))
        
        if not db_stats.get("database_exists", False):
            error_msg = db_stats.get("error", "数据库不存在")
            logger.error(f"数据库统计获取失败: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 转换为前端期望的格式，包含扫描统计数据
        return {
            "success": True,
            "data": {
                # 数据库统计（原有字段）
                "totalProjects": db_stats.get("packs_count", 0),
                "totalFiles": db_stats.get("content_instances_count", 0),
                "totalEntries": db_stats.get("pack_content_relations_count", 0),
                "totalTables": db_stats.get("total_tables", 0),
                "database_path": db_stats.get("database_path", str(v2_1_db_path)),
                "database_size": db_stats.get("database_size", 0),
                "pack_versions": db_stats.get("pack_versions_count", 0),
                "mod_instances": db_stats.get("mod_version_instances_count", 0),
                "pack_mod_relations": db_stats.get("pack_mod_relations_count", 0),
                "total_views": db_stats.get("total_views", 0),
                
                # 扫描统计数据（前端期望的字段）
                "total_scans": 0,  # 总扫描次数 TODO: 从扫描历史表获取
                "active_scans": 0,  # 活跃扫描数量 TODO: 从活跃扫描获取
                "successful_scans": 0,  # 成功扫描数量 TODO: 从扫描历史表获取
                "failed_scans": 0,  # 失败扫描数量 TODO: 从扫描历史表获取
                "average_scan_duration_ms": 0,  # 平均扫描耗时 TODO: 从扫描历史表计算
            },
            "message": "数据库统计获取成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=dict[str, Any])
async def get_scan_statistics():
    """
    获取扫描统计信息 (前端兼容性路由)
    与 /stats 路由相同的功能，但路径名适配前端期望
    """
    return await get_database_stats()


@router.get("/history", response_model=dict[str, Any])
async def get_scan_history():
    """
    获取扫描历史记录
    返回最近的扫描任务历史
    """
    return {
        "success": True,
        "data": {
            "recent_scans": [],
            "total_count": 0,
        },
        "message": "扫描历史获取成功（暂无历史数据）",
    }


