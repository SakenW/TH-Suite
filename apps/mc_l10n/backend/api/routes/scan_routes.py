# apps/mc-l10n/backend/api/routes/scan_routes.py
"""
扫描相关API路由

提供项目和MOD扫描的REST API端点
"""

import logging
import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

# 添加scanner_service到路径
current_dir = os.path.dirname(__file__)
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, backend_dir)

from ddd_scanner import get_scanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scan", tags=["扫描"])


@router.get("/health")
async def scan_health_check():
    """扫描服务健康检查"""
    return {"status": "healthy", "service": "scan"}


@router.get("/test")
async def scan_test():
    """扫描服务测试端点"""
    return {
        "message": "扫描服务正在运行",
        "available_endpoints": [
            "/api/scan/health",
            "/api/scan/test",
            "/api/scan/project/start",
            "/api/scan/progress/{task_id}",
            "/api/v1/scan-project"
        ]
    }


class ScanRequest(BaseModel):
    path: str
    incremental: bool = True
    options: Optional[Dict[str, Any]] = None


@router.post("/project/start")
async def start_project_scan(request: ScanRequest):
    """启动真实的项目扫描任务"""
    try:
        scanner_service = get_scanner()
        if not scanner_service:
            raise HTTPException(status_code=500, detail="Scanner service not initialized")
        
        # 启动真实扫描
        result = await scanner_service.start_scan(
            target_path=request.path,
            incremental=request.incremental,
            options=request.options
        )
        
        logger.info(f"Started real scan: {result['scan_id']} for path: {request.path}")
        
        # 返回前端期望的标准响应格式（同时兼容新旧格式）
        return {
            "success": True,
            "data": {
                "scan_id": result["scan_id"],
                "task_id": result["scan_id"],  # 兼容旧字段
                "status": "started"
            },
            # 同时保留旧的扁平格式字段
            "scan_id": result["scan_id"],
            "task_id": result["scan_id"],
            "status": "started",
            "message": "扫描任务已启动",
            "target_path": request.path,  # 使用请求中的path，而不是result中的
            "game_type": result.get("game_type", "minecraft")
        }
        
    except Exception as e:
        logger.error(f"Failed to start scan: {e}", exc_info=True)
        # 返回标准错误格式
        return {
            "success": False,
            "error": {
                "code": "SCAN_START_FAILED",
                "message": f"扫描启动失败: {str(e)}"
            }
        }


@router.get("/progress/{task_id}")
async def get_scan_progress(task_id: str):
    """获取真实的扫描进度"""
    try:
        scanner_service = get_scanner()
        if not scanner_service:
            raise HTTPException(status_code=500, detail="Scanner service not initialized")
        
        # 获取真实的扫描状态
        status = await scanner_service.get_scan_status(task_id)
        
        if not status:
            # 返回标准错误格式而不是抛出异常
            return {
                "success": False,
                "error": {
                    "code": "SCAN_NOT_FOUND",
                    "message": f"找不到扫描任务: {task_id}"
                }
            }
        
        logger.info(f"Got scan status for {task_id}: {status}")
        
        # 确保进度在0-100范围内
        progress_percent = min(100, max(0, status.get("progress_percent", 0)))
        
        # 获取统计数据，确保不是None
        statistics = status.get("statistics") or {}
        
        # 转换为前端期望的标准响应格式
        response_data = {
            "success": True,
            "data": {
                "status": status["status"],
                "progress": progress_percent,  # 保持为0-100范围
                "current_step": status.get("current_item", "处理中..."),
                "processed_files": status.get("processed_count", 0),
                "total_files": status.get("total_count", 0),
                "statistics": statistics,
                "current_file": status.get("current_item", ""),
                "total_mods": statistics.get("total_mods", 0) if statistics else 0,
                "total_language_files": statistics.get("total_language_files", 0) if statistics else 0,
                "total_keys": statistics.get("total_keys", 0) if statistics else 0
            }
        }
        
        # 如果扫描完成，添加结果数据
        if status["status"] == "completed":
            response_data["data"]["result"] = {
                "success": True,
                "statistics": {
                    "total_mods": status.get("total_mods", 0),
                    "total_language_files": status.get("total_language_files", 0),
                    "total_keys": status.get("total_keys", 0),
                    "total_entries": status.get("total_entries", 0)
                },
                "entries": status.get("entries", {}),
                "errors": status.get("errors", []),
                "warnings": status.get("warnings", [])
            }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Failed to get scan progress: {e}", exc_info=True)
        # 返回标准错误格式
        return {
            "success": False,
            "error": {
                "code": "SCAN_PROGRESS_ERROR",
                "message": f"获取扫描进度失败: {str(e)}"
            }
        }


# 添加兼容性端点用于旧的前端代码
@router.post("/v1/scan-project", deprecated=True)
async def start_scan_v1_compat(request: dict):
    """兼容旧版API的扫描端点 - 使用真实扫描"""
    try:
        scanner_service = get_scanner()
        if not scanner_service:
            raise HTTPException(status_code=500, detail="Scanner service not initialized")
        
        # 从请求中提取路径
        target_path = request.get("path", request.get("projectPath", "/home/saken/minecraft/mods"))
        
        # 启动真实扫描
        result = await scanner_service.start_scan(
            target_path=target_path,
            incremental=request.get("incremental", True)
        )
        
        return {
            "success": True,
            "data": {
                "task_id": result["scan_id"],
                "scan_id": result["scan_id"],
                "message": "扫描任务已启动",
                "status": "started",
                "target_path": target_path
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to start v1 scan: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/statistics")
async def get_scan_statistics():
    """获取扫描统计信息"""
    try:
        scanner_service = get_scanner()
        if not scanner_service:
            raise HTTPException(status_code=500, detail="Scanner service not initialized")
        stats = await scanner_service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/cancel/{task_id}")
async def cancel_scan(task_id: str):
    """取消扫描任务"""
    try:
        scanner_service = get_scanner()
        if not scanner_service:
            raise HTTPException(status_code=500, detail="Scanner service not initialized")
        success = await scanner_service.cancel_scan(task_id)
        
        if success:
            return {"success": True, "message": "扫描已取消"}
        else:
            raise HTTPException(status_code=404, detail=f"找不到扫描任务: {task_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取消扫描失败: {str(e)}")


# 添加全局的扫描结果路由（兼容前端的 /scan-results/xxx 路径）
from fastapi import FastAPI

def register_scan_results_route(app: FastAPI):
    """注册全局的扫描结果路由"""
    
    @app.get("/scan-results/{scan_id}")
    async def get_scan_results_global(scan_id: str):
        """获取扫描结果（全局路由）"""
        scanner_service = get_scanner()
        if not scanner_service:
            return {
                "success": False,
                "error": {
                    "code": "NO_SCANNER",
                    "message": "Scanner service not initialized"
                }
            }
        
        status = await scanner_service.get_scan_progress(scan_id)
        if not status:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Scan not found: {scan_id}"
                }
            }
        
        statistics = status.get("statistics", {})
        return {
            "success": True,
            "data": {
                "scan_id": scan_id,
                "status": status.get("status"),
                "statistics": statistics,
                "total_mods": statistics.get("total_mods", 0),
                "total_language_files": statistics.get("total_language_files", 0),
                "total_keys": statistics.get("total_keys", 0),
                "entries": {},
                "errors": [],
                "warnings": []
            }
        }