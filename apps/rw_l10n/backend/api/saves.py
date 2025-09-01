from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from packages.core.models import JobStatus
from packages.protocol.schemas import (
    JobResponse,
    SaveGameAnalysisResult,
    SaveGameBackupRequest,
    SaveGameInfo,
    SaveGameRestoreRequest,
)
from packages.protocol.websocket import WebSocketManager

from ..dependencies import get_save_game_service, get_websocket_manager
from ..services import SaveGameService

router = APIRouter()


@router.get("/", response_model=list[SaveGameInfo])
async def list_save_games(
    search: str | None = Query(None, description="搜索关键词"),
    sort_by: str = Query("modified_time", description="排序方式"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """获取存档列表"""
    try:
        saves = await save_service.list_saves(search=search, sort_by=sort_by)
        return saves
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{save_id}", response_model=SaveGameInfo)
async def get_save_game(
    save_id: str, save_service: SaveGameService = Depends(get_save_game_service)
):
    """获取特定存档信息"""
    try:
        save = await save_service.get_save(save_id)
        if not save:
            raise HTTPException(status_code=404, detail="存档未找到")
        return save
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup", response_model=JobResponse)
async def backup_save_game(
    request: SaveGameBackupRequest,
    save_service: SaveGameService = Depends(get_save_game_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """备份存档"""
    try:
        job_id = await save_service.backup_save(
            save_id=request.save_id,
            backup_name=request.backup_name,
            include_mods=request.include_mods,
            compress=request.compress,
        )

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "backup_save",
                "save_id": request.save_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore", response_model=JobResponse)
async def restore_save_game(
    request: SaveGameRestoreRequest,
    save_service: SaveGameService = Depends(get_save_game_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """恢复存档"""
    try:
        job_id = await save_service.restore_save(
            backup_id=request.backup_id,
            target_save_id=request.target_save_id,
            restore_mods=request.restore_mods,
        )

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "restore_save",
                "backup_id": request.backup_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backups")
async def list_save_backups(
    save_id: str | None = Query(None, description="特定存档的备份"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """获取存档备份列表"""
    try:
        backups = await save_service.list_backups(save_id=save_id)
        return backups
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backups/{backup_id}")
async def delete_save_backup(
    backup_id: str, save_service: SaveGameService = Depends(get_save_game_service)
):
    """删除存档备份"""
    try:
        await save_service.delete_backup(backup_id)
        return {"message": "备份已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{save_id}", response_model=SaveGameAnalysisResult)
async def analyze_save_game(
    save_id: str,
    deep_analysis: bool = Query(False, description="是否进行深度分析"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """分析存档"""
    try:
        result = await save_service.analyze_save(
            save_id=save_id, deep_analysis=deep_analysis
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mods/{save_id}")
async def get_save_mods(
    save_id: str, save_service: SaveGameService = Depends(get_save_game_service)
):
    """获取存档使用的模组列表"""
    try:
        mods = await save_service.get_save_mods(save_id)
        return mods
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/{save_id}")
async def validate_save_game(
    save_id: str,
    check_mods: bool = Query(True, description="是否检查模组兼容性"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """验证存档完整性"""
    try:
        result = await save_service.validate_save(
            save_id=save_id, check_mods=check_mods
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_save_game(
    file: UploadFile = File(...),
    save_name: str | None = Query(None, description="存档名称"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """上传存档文件"""
    try:
        # 验证文件类型
        if not file.filename or not file.filename.endswith((".rws", ".zip")):
            raise HTTPException(status_code=400, detail="不支持的文件格式")

        save_id = await save_service.upload_save(file=file, save_name=save_name)

        return {"save_id": save_id, "message": "存档上传成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{save_id}")
async def download_save_game(
    save_id: str,
    include_mods: bool = Query(False, description="是否包含模组"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """下载存档文件"""
    try:
        file_path = await save_service.export_save(
            save_id=save_id, include_mods=include_mods
        )

        filename = f"{save_id}.zip" if include_mods else f"{save_id}.rws"

        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{save_id}")
async def delete_save_game(
    save_id: str,
    delete_backups: bool = Query(False, description="是否同时删除备份"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """删除存档"""
    try:
        await save_service.delete_save(save_id=save_id, delete_backups=delete_backups)
        return {"message": "存档已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_saves(
    older_than_days: int = Query(30, description="删除多少天前的备份"),
    keep_recent: int = Query(5, description="保留最近几个备份"),
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """清理旧的存档备份"""
    try:
        result = await save_service.cleanup_backups(
            older_than_days=older_than_days, keep_recent=keep_recent
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_save_statistics(
    save_service: SaveGameService = Depends(get_save_game_service),
):
    """获取存档统计信息"""
    try:
        stats = await save_service.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
