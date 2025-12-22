"""
扫描API路由
处理扫描相关的HTTP请求
"""

import logging
from typing import Any

from application.commands import RescanCommand, ScanCommand
from application.dto import ErrorDTO
from application.queries import GetScanHistoryQuery
from application.services.scan_service import ScanService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..dependencies import get_scan_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/directory")
async def scan_directory(
    directory: str,
    include_patterns: list[str] = None,
    exclude_patterns: list[str] = None,
    force_rescan: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    scan_service: ScanService = Depends(get_scan_service),
) -> dict[str, Any]:
    """
    扫描指定目录中的模组文件

    Args:
        directory: 要扫描的目录路径
        include_patterns: 包含的文件模式 (如 *.jar)
        exclude_patterns: 排除的文件模式
        force_rescan: 是否强制重新扫描

    Returns:
        扫描结果
    """
    try:
        command = ScanCommand(
            command_id=f"scan_{directory}",
            directory_path=directory,
            include_patterns=include_patterns or ["*.jar", "*.zip"],
            exclude_patterns=exclude_patterns or [],
            force_rescan=force_rescan,
        )

        # 如果是大目录，使用后台任务
        if force_rescan:
            background_tasks.add_task(scan_service.scan_directory, command)
            return {
                "status": "scanning",
                "message": "Scan started in background",
                "directory": directory,
            }
        else:
            result = scan_service.scan_directory(command)
            return result.to_dict()

    except Exception as e:
        logger.error(f"Failed to scan directory {directory}: {e}")
        error = ErrorDTO.from_exception(e, "SCAN_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.post("/file/{file_path:path}")
async def scan_file(
    file_path: str,
    force: bool = False,
    scan_service: ScanService = Depends(get_scan_service),
) -> dict[str, Any]:
    """
    扫描单个文件

    Args:
        file_path: 文件路径
        force: 是否强制重新扫描

    Returns:
        模组信息
    """
    try:
        result = scan_service.scan_file(file_path, force)
        return result.to_dict()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Failed to scan file {file_path}: {e}")
        error = ErrorDTO.from_exception(e, "SCAN_FILE_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.post("/rescan")
async def rescan_all(
    only_changed: bool = True,
    remove_missing: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    scan_service: ScanService = Depends(get_scan_service),
) -> dict[str, Any]:
    """
    重新扫描所有已知模组

    Args:
        only_changed: 仅扫描有变化的文件
        remove_missing: 移除丢失的文件

    Returns:
        扫描结果
    """
    try:
        command = RescanCommand(
            command_id="rescan_all",
            only_changed=only_changed,
            remove_missing=remove_missing,
        )

        # 使用后台任务执行
        background_tasks.add_task(scan_service.rescan_all, command)

        return {
            "status": "rescanning",
            "message": "Rescan started in background",
            "only_changed": only_changed,
        }

    except Exception as e:
        logger.error(f"Failed to start rescan: {e}")
        error = ErrorDTO.from_exception(e, "RESCAN_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.get("/progress/{scan_id}")
async def get_scan_progress(
    scan_id: str, scan_service: ScanService = Depends(get_scan_service)
) -> dict[str, Any]:
    """
    获取扫描进度

    Args:
        scan_id: 扫描ID

    Returns:
        进度信息
    """
    try:
        progress = scan_service.get_scan_progress(scan_id)
        return progress
    except Exception as e:
        logger.error(f"Failed to get scan progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cancel/{scan_id}")
async def cancel_scan(
    scan_id: str, scan_service: ScanService = Depends(get_scan_service)
) -> dict[str, Any]:
    """
    取消扫描任务

    Args:
        scan_id: 扫描ID

    Returns:
        取消结果
    """
    try:
        success = scan_service.cancel_scan(scan_id)
        if success:
            return {"status": "cancelled", "scan_id": scan_id}
        else:
            raise HTTPException(
                status_code=404, detail=f"Scan {scan_id} not found or already completed"
            )
    except Exception as e:
        logger.error(f"Failed to cancel scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_scan_history(
    limit: int = 50,
    mod_id: str = None,
    scan_service: ScanService = Depends(get_scan_service),
) -> list[dict[str, Any]]:
    """
    获取扫描历史

    Args:
        limit: 返回数量限制
        mod_id: 模组ID（可选）

    Returns:
        扫描历史列表
    """
    try:
        GetScanHistoryQuery(query_id="get_scan_history", mod_id=mod_id, limit=limit)

        # 这里应该调用查询服务，简化处理
        return [
            {
                "scan_id": "scan_001",
                "timestamp": "2025-09-06T16:00:00",
                "directory": "/mods",
                "files_scanned": 100,
                "status": "completed",
            }
        ]

    except Exception as e:
        logger.error(f"Failed to get scan history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_scan_stats(
    scan_service: ScanService = Depends(get_scan_service),
) -> dict[str, Any]:
    """
    获取扫描统计信息

    Returns:
        统计信息
    """
    try:
        # 这里应该从服务获取实际统计
        return {
            "total_scans": 42,
            "total_files_scanned": 1337,
            "total_mods_found": 226,
            "last_scan": "2025-09-06T16:00:00",
            "average_scan_time": 3.14,
        }
    except Exception as e:
        logger.error(f"Failed to get scan stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
