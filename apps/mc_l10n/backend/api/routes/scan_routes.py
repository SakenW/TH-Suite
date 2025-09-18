"""
扫描相关路由
提供目录扫描、进度查询和结果获取功能
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from application.services.scan_application_service import ScanApplicationService
from infrastructure.services.scan_session_manager import ScanSessionManager, ScanMode

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
            "GET /api/v1/scan/test",
            "POST /api/v1/scan/start",
            "GET /api/v1/scan/status/{scan_id}",
            "GET /api/v1/scan/results/{scan_id}",
            "POST /api/v1/scan/cancel/{scan_id}",
            "GET /api/v1/scan/active",
            "GET /api/v1/scan/stats",
            "GET /api/v1/scan/statistics",
            "GET /api/v1/scan/history",
        ],
    }


@router.post("/start", response_model=dict[str, Any])
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    启动目录扫描 - 使用新架构的ScanSessionManager

    Args:
        request: 扫描请求参数
        background_tasks: 后台任务管理器
    """
    try:
        # 使用新架构的扫描会话管理器
        from pathlib import Path
        
        # 初始化扫描会话管理器
        db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n.db"
        manager = ScanSessionManager(str(db_path))
        await manager.start()
        
        # 确定扫描模式
        if request.incremental:
            scan_mode = ScanMode.INCREMENTAL
        else:
            scan_mode = ScanMode.FULL
        
        # 解析扫描选项
        scan_options = request.options or {}
        target_languages = scan_options.get("target_languages", ["en_us", "zh_cn"])
        
        # 启动扫描会话
        session_id = await manager.start_scan(
            root_path=request.directory,
            mode=scan_mode,
            target_languages=target_languages,
            incremental=request.incremental
        )
        
        if session_id:
            return {
                "success": True,
                "data": {
                    "scan_id": session_id,
                    "directory": request.directory,
                    "incremental": request.incremental,
                    "status": "started",
                    "mode": scan_mode.value,
                    "target_languages": target_languages,
                },
                "message": f"新架构扫描会话已启动: {session_id}",
            }
        else:
            raise HTTPException(status_code=500, detail="启动扫描会话失败")
            
    except FileNotFoundError as e:
        logger.error(f"扫描目录不存在: {e}")
        raise HTTPException(status_code=400, detail=f"目标路径不存在: {request.directory}")
    except ValueError as e:
        logger.error(f"启动扫描参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{scan_id}", response_model=dict[str, Any])
async def get_scan_status(scan_id: str):
    """
    获取扫描状态 - 使用新架构的ScanSessionManager

    Args:
        scan_id: 扫描会话ID
    """
    try:
        # 使用新架构的扫描会话管理器
        from pathlib import Path
        
        # 初始化扫描会话管理器
        db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n.db"
        manager = ScanSessionManager(str(db_path))
        await manager.start()
        
        # 获取扫描状态
        status = await manager.get_scan_status(scan_id)
        
        if status:
            # 安全地处理stage字段，支持枚举类型转换
            stage_value = status["stage"]
            if hasattr(stage_value, 'value'):
                stage_str = stage_value.value
            else:
                stage_str = str(stage_value)
            
            # 安全地获取任务统计信息
            tasks_info = status.get("tasks", {})
            completed_count = tasks_info.get("completed", 0) if isinstance(tasks_info, dict) else 0
            total_count = tasks_info.get("total", 0) if isinstance(tasks_info, dict) else 0
            
            return {
                "success": True,
                "data": {
                    "scan_id": scan_id,
                    "status": stage_str,
                    "progress": status.get("progress", 0),
                    "current_item": status.get("current_item", ""),
                    "processed_count": completed_count,
                    "total_count": total_count,
                    "duration_seconds": status.get("duration_seconds", 0),
                    "error_message": status.get("error_message"),
                    # 新架构统计信息
                    "statistics": status.get("statistics", {}),
                    # 前端兼容字段
                    "total_mods": status.get("statistics", {}).get("mods", 0),
                    "total_content_instances": status.get("statistics", {}).get("entries", 0),
                    "total_files": total_count,
                    "processed_files": completed_count,
                    "total_keys": status.get("statistics", {}).get("keys", 0),
                    "language_files_found": status.get("statistics", {}).get("lang_files", 0),
                    "stage": stage_str,
                    "mode": status.get("mode", "full"),
                    "created_at": status.get("created_at"),
                    "updated_at": status.get("updated_at")
                },
                "message": f"新架构扫描状态获取成功: {scan_id}",
            }
        else:
            raise HTTPException(status_code=404, detail=f"扫描会话不存在: {scan_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取扫描状态失败 {scan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{scan_id}", response_model=dict[str, Any])
async def get_scan_results(scan_id: str):
    """
    获取扫描结果 - 使用新架构的ScanSessionManager

    Args:
        scan_id: 扫描会话ID
    """
    try:
        # 使用新架构的扫描会话管理器
        from pathlib import Path
        
        # 初始化扫描会话管理器
        db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n.db"
        manager = ScanSessionManager(str(db_path))
        await manager.start()
        
        # 获取扫描结果
        results = await manager.get_scan_results(scan_id)
        
        if results:
            return {
                "success": True,
                "data": results,
                "message": f"新架构扫描结果获取成功: {scan_id}",
            }
        else:
            raise HTTPException(status_code=404, detail=f"扫描结果不存在或扫描未完成: {scan_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取扫描结果失败 {scan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{scan_id}", response_model=dict[str, Any])
async def cancel_scan(scan_id: str):
    """
    取消扫描任务 - 使用新架构的ScanSessionManager

    Args:
        scan_id: 扫描会话ID
    """
    try:
        # 使用新架构的扫描会话管理器
        from pathlib import Path
        
        # 初始化扫描会话管理器
        db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n.db"
        manager = ScanSessionManager(str(db_path))
        await manager.start()
        
        # 取消扫描
        result = await manager.cancel_scan(scan_id)
        
        if result:
            return {
                "success": True,
                "data": {"scan_id": scan_id, "status": "cancelled"},
                "message": f"新架构扫描会话已取消: {scan_id}",
            }
        else:
            raise HTTPException(status_code=404, detail=f"扫描会话不存在或无法取消: {scan_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消扫描失败 {scan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=dict[str, Any])
async def get_active_scans():
    """
    获取当前活跃的扫描任务 - 使用新架构的ScanSessionManager
    """
    try:
        # 使用新架构的扫描会话管理器
        from pathlib import Path
        
        # 初始化扫描会话管理器
        db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n.db"
        manager = ScanSessionManager(str(db_path))
        await manager.start()
        
        # 获取活跃扫描会话
        active_sessions = await manager.list_active_sessions()
        
        # 为前端兼容性，直接返回active_scans数组格式
        return {
            "success": True,
            "data": active_sessions,  # 直接返回数组，不包装在active_scans对象中
            "message": f"成功获取 {len(active_sessions)} 个活跃扫描会话",
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
        from infrastructure.db_initializer import ensure_database, get_database_stats
        
        # 使用数据库路径
        db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n.db"
        
        # 确保数据库存在，如果不存在则自动创建
        if not ensure_database(str(db_path)):
            logger.error("数据库初始化失败")
            raise HTTPException(status_code=500, detail="数据库初始化失败")
        
        # 获取数据库统计信息
        db_stats = get_database_stats(str(db_path))
        
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
                "database_path": db_stats.get("database_path", str(db_path)),
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


