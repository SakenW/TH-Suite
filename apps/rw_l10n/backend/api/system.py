from fastapi import APIRouter, Depends, HTTPException, Query

from packages.core.job_manager import JobManager
from packages.core.logging import get_logger
from packages.core.models import JobStatus
from packages.protocol.schemas import JobInfo, SystemInfo
from packages.protocol.websocket import WebSocketManager

from ..dependencies import get_config_service, get_websocket_manager
from ..services import ConfigService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/info", response_model=SystemInfo)
async def get_system_info(config_service: ConfigService = Depends(get_config_service)):
    """获取系统信息"""
    try:
        import platform
        import sys
        from pathlib import Path

        import psutil

        # 获取系统基本信息
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "python_version": sys.version,
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": {
                "total": psutil.disk_usage("/").total,
                "used": psutil.disk_usage("/").used,
                "free": psutil.disk_usage("/").free,
            },
        }

        # 获取游戏路径信息
        game_paths = await config_service.get_game_paths()

        # 检查路径有效性
        path_status = {}
        for name, path in game_paths.items():
            if path:
                path_obj = Path(path)
                path_status[name] = {
                    "path": path,
                    "exists": path_obj.exists(),
                    "is_directory": path_obj.is_dir() if path_obj.exists() else False,
                    "readable": path_obj.exists() and path_obj.stat().st_mode & 0o444,
                    "writable": path_obj.exists() and path_obj.stat().st_mode & 0o222,
                }
            else:
                path_status[name] = {
                    "path": None,
                    "exists": False,
                    "is_directory": False,
                    "readable": False,
                    "writable": False,
                }

        return SystemInfo(
            **system_info,
            game_paths=path_status,
            app_version="1.0.0",  # 从配置或环境变量获取
            backend_version="1.0.0",
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "version": "1.0.0",
    }


@router.get("/jobs", response_model=list[JobInfo])
async def list_jobs(
    status: JobStatus | None = Query(None, description="按状态过滤"),
    limit: int = Query(50, description="返回数量限制"),
):
    """获取任务列表"""
    try:
        job_manager = JobManager()
        jobs = await job_manager.list_jobs(status=status, limit=limit)
        return jobs
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobInfo)
async def get_job(job_id: str):
    """获取特定任务信息"""
    try:
        job_manager = JobManager()
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="任务未找到")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str, ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """取消任务"""
    try:
        job_manager = JobManager()
        await job_manager.cancel_job(job_id)

        # 通知前端任务已取消
        await ws_manager.broadcast({"type": "job_cancelled", "job_id": job_id})

        return {"message": "任务已取消"}
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """删除任务记录"""
    try:
        job_manager = JobManager()
        await job_manager.delete_job(job_id)
        return {"message": "任务记录已删除"}
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/cleanup")
async def cleanup_jobs(
    older_than_hours: int = Query(24, description="清理多少小时前的已完成任务"),
    keep_failed: bool = Query(True, description="是否保留失败的任务"),
):
    """清理旧的任务记录"""
    try:
        job_manager = JobManager()
        result = await job_manager.cleanup_jobs(
            older_than_hours=older_than_hours, keep_failed=keep_failed
        )
        return result
    except Exception as e:
        logger.error(f"Failed to cleanup jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_logs(
    level: str | None = Query(None, description="日志级别过滤"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
):
    """获取系统日志"""
    try:
        # 这里应该从日志系统获取日志
        # 暂时返回模拟数据
        logs = [
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "level": "INFO",
                "logger": "rw_studio.main",
                "message": "RW Studio Backend started successfully",
            }
        ]
        return logs
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics():
    """获取性能指标"""
    try:
        import time

        import psutil

        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存使用情况
        memory = psutil.virtual_memory()

        # 磁盘使用情况
        disk = psutil.disk_usage("/")

        # 网络统计
        network = psutil.net_io_counters()

        return {
            "timestamp": time.time(),
            "cpu": {"usage_percent": cpu_percent, "count": psutil.cpu_count()},
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restart")
async def restart_application(
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """重启应用"""
    try:
        # 通知所有客户端应用即将重启
        await ws_manager.broadcast(
            {"type": "app_restarting", "message": "应用即将重启，请稍候..."}
        )

        # 这里应该实现重启逻辑
        # 在实际环境中，可能需要使用进程管理器或容器编排工具

        return {"message": "应用重启请求已提交"}
    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shutdown")
async def shutdown_application(
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """关闭应用"""
    try:
        # 通知所有客户端应用即将关闭
        await ws_manager.broadcast(
            {"type": "app_shutting_down", "message": "应用即将关闭..."}
        )

        # 这里应该实现优雅关闭逻辑

        return {"message": "应用关闭请求已提交"}
    except Exception as e:
        logger.error(f"Failed to shutdown application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/version")
async def get_version_info():
    """获取版本信息"""
    try:
        return {
            "app_version": "1.0.0",
            "backend_version": "1.0.0",
            "api_version": "v1",
            "build_date": "2024-01-01",
            "git_commit": "unknown",
        }
    except Exception as e:
        logger.error(f"Failed to get version info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
