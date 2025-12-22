from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from packages.core.models import JobStatus
from packages.protocol.schemas import (
    JobResponse,
    ModInfo,
    ModInstallRequest,
    ModSearchRequest,
    ModSearchResult,
    ModUpdateRequest,
)
from packages.protocol.websocket import WebSocketManager

from ..dependencies import get_mod_service, get_websocket_manager
from ..services import ModService

router = APIRouter()


@router.get("/", response_model=list[ModInfo])
async def list_mods(
    installed_only: bool = Query(False, description="只显示已安装的模组"),
    search: str | None = Query(None, description="搜索关键词"),
    category: str | None = Query(None, description="模组分类"),
    mod_service: ModService = Depends(get_mod_service),
):
    """获取模组列表"""
    try:
        mods = await mod_service.list_mods(
            installed_only=installed_only, search=search, category=category
        )
        return mods
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mod_id}", response_model=ModInfo)
async def get_mod(mod_id: str, mod_service: ModService = Depends(get_mod_service)):
    """获取特定模组信息"""
    try:
        mod = await mod_service.get_mod(mod_id)
        if not mod:
            raise HTTPException(status_code=404, detail="模组未找到")
        return mod
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install", response_model=JobResponse)
async def install_mod(
    request: ModInstallRequest,
    mod_service: ModService = Depends(get_mod_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """安装模组"""
    try:
        job_id = await mod_service.install_mod(
            mod_id=request.mod_id,
            version=request.version,
            force_reinstall=request.force_reinstall,
        )

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "install_mod",
                "mod_id": request.mod_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uninstall/{mod_id}", response_model=JobResponse)
async def uninstall_mod(
    mod_id: str,
    remove_data: bool = Query(False, description="是否删除模组数据"),
    mod_service: ModService = Depends(get_mod_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """卸载模组"""
    try:
        job_id = await mod_service.uninstall_mod(mod_id=mod_id, remove_data=remove_data)

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "uninstall_mod",
                "mod_id": mod_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update", response_model=JobResponse)
async def update_mod(
    request: ModUpdateRequest,
    mod_service: ModService = Depends(get_mod_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """更新模组"""
    try:
        job_id = await mod_service.update_mod(
            mod_id=request.mod_id, target_version=request.target_version
        )

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "update_mod",
                "mod_id": request.mod_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=ModSearchResult)
async def search_mods(
    request: ModSearchRequest, mod_service: ModService = Depends(get_mod_service)
):
    """搜索模组"""
    try:
        result = await mod_service.search_mods(
            query=request.query,
            category=request.category,
            sort_by=request.sort_by,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=JobResponse)
async def upload_mod(
    file: UploadFile = File(...),
    mod_service: ModService = Depends(get_mod_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """上传本地模组文件"""
    try:
        # 验证文件类型
        if not file.filename or not file.filename.endswith((".zip", ".rar", ".7z")):
            raise HTTPException(status_code=400, detail="不支持的文件格式")

        job_id = await mod_service.upload_mod(file)

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "upload_mod",
                "filename": file.filename,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable/{mod_id}")
async def enable_mod(mod_id: str, mod_service: ModService = Depends(get_mod_service)):
    """启用模组"""
    try:
        await mod_service.enable_mod(mod_id)
        return {"message": "模组已启用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable/{mod_id}")
async def disable_mod(mod_id: str, mod_service: ModService = Depends(get_mod_service)):
    """禁用模组"""
    try:
        await mod_service.disable_mod(mod_id)
        return {"message": "模组已禁用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependencies/{mod_id}")
async def get_mod_dependencies(
    mod_id: str, mod_service: ModService = Depends(get_mod_service)
):
    """获取模组依赖关系"""
    try:
        dependencies = await mod_service.get_dependencies(mod_id)
        return dependencies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/{mod_id}")
async def get_mod_conflicts(
    mod_id: str, mod_service: ModService = Depends(get_mod_service)
):
    """获取模组冲突信息"""
    try:
        conflicts = await mod_service.get_conflicts(mod_id)
        return conflicts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_mods(mod_service: ModService = Depends(get_mod_service)):
    """验证所有模组的完整性和兼容性"""
    try:
        result = await mod_service.validate_all_mods()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{mod_id}")
async def export_mod(mod_id: str, mod_service: ModService = Depends(get_mod_service)):
    """导出模组文件"""
    try:
        file_path = await mod_service.export_mod(mod_id)
        return FileResponse(
            path=file_path, filename=f"{mod_id}.zip", media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
