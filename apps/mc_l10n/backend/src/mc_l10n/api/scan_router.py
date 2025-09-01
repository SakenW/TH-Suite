# apps/mc-l10n/backend/src/mc_l10n/api/scan_router.py
"""
扫描相关API路由

提供项目和MOD扫描的REST API端点
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator

from packages.core import ProjectAlreadyExistsError, ScanError

from src.mc_l10n.application.services.scan_service import ScanService
from src.mc_l10n.di.simple_container import get_simple_container

router = APIRouter(prefix="/api/scan", tags=["扫描"])


# Request/Response模型
class ScanProjectRequest(BaseModel):
    """扫描项目请求"""

    path: str

    @validator("path")
    def validate_path(self, v):
        if not v:
            raise ValueError("路径不能为空")
        return v


class QuickScanProjectRequest(BaseModel):
    """快速扫描项目请求"""

    path: str

    @validator("path")
    def validate_path(self, v):
        if not v:
            raise ValueError("路径不能为空")
        return v


class ScanTaskResponse(BaseModel):
    """扫描任务响应"""

    task_id: str
    message: str


class ScanProgressResponse(BaseModel):
    """扫描进度响应"""

    task_id: str
    status: str
    progress: float | None = None
    current_step: str | None = None
    error_message: str | None = None


class ProjectInfoResponse(BaseModel):
    """项目信息响应"""

    name: str
    path: str
    project_type: str
    loader_type: str | None = None
    total_mods: int
    estimated_segments: int
    supported_locales: list[str]
    fingerprint: str | None = None


class QuickScanResponse(BaseModel):
    """快速扫描响应"""

    success: bool
    project_info: ProjectInfoResponse | None = None
    errors: list[str] = []


class ModInfoResponse(BaseModel):
    """MOD信息响应"""

    mod_id: str
    name: str
    version: str | None = None
    description: str | None = None
    authors: list[str] = []
    file_path: str
    file_size: int
    loader_type: str | None = None


# 依赖注入
def get_scan_service() -> ScanService:
    """获取扫描服务"""
    container = get_simple_container()
    return container.get_scan_service()


# API端点
@router.post("/project/start", response_model=ScanTaskResponse)
async def start_project_scan(
    request: ScanProjectRequest, scan_service: ScanService = Depends(get_scan_service)
):
    """启动项目扫描任务"""
    try:
        path = Path(request.path)
        task_id = await scan_service.start_project_scan(path)

        return ScanTaskResponse(task_id=str(task_id), message="扫描任务已启动")

    except ProjectAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=f"项目已在扫描中: {e}")
    except ScanError as e:
        raise HTTPException(status_code=400, detail=f"扫描错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")


@router.get("/progress/{task_id}", response_model=ScanProgressResponse)
async def get_scan_progress(
    task_id: str, scan_service: ScanService = Depends(get_scan_service)
):
    """获取扫描进度"""
    try:
        task_uuid = UUID(task_id)
        progress = await scan_service.get_scan_progress(task_uuid)

        if not progress:
            raise HTTPException(status_code=404, detail="任务不存在")

        return ScanProgressResponse(**progress)

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的任务ID格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")


@router.post("/project/quick", response_model=QuickScanResponse)
async def quick_scan_project(
    request: QuickScanProjectRequest,
    scan_service: ScanService = Depends(get_scan_service),
):
    """快速扫描项目"""
    try:
        path = Path(request.path)
        result = await scan_service.quick_scan_project(path)

        # 转换响应格式
        project_info_response = None
        if result.project_info:
            pi = result.project_info
            project_info_response = ProjectInfoResponse(
                name=pi.name,
                path=str(pi.path),
                project_type=pi.project_type.value,
                loader_type=pi.loader_type.value if pi.loader_type else None,
                total_mods=pi.total_mods,
                estimated_segments=pi.estimated_segments,
                supported_locales=list(pi.supported_locales),
                fingerprint=pi.fingerprint,
            )

        return QuickScanResponse(
            success=result.success,
            project_info=project_info_response,
            errors=result.errors,
        )

    except ScanError as e:
        raise HTTPException(status_code=400, detail=f"扫描错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")


@router.post("/mod", response_model=ModInfoResponse)
async def scan_single_mod(
    request: dict, scan_service: ScanService = Depends(get_scan_service)
):
    """扫描单个MOD文件"""
    try:
        mod_path = Path(request["path"])

        if not mod_path.exists():
            raise HTTPException(status_code=404, detail="MOD文件不存在")

        mod_info = await scan_service.scan_single_mod(mod_path)

        return ModInfoResponse(
            mod_id=mod_info.mod_id,
            name=mod_info.name,
            version=mod_info.version,
            description=mod_info.description,
            authors=mod_info.authors,
            file_path=str(mod_info.file_path),
            file_size=mod_info.file_size,
            loader_type=mod_info.loader_type.value if mod_info.loader_type else None,
        )

    except ScanError as e:
        raise HTTPException(status_code=400, detail=f"扫描错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "scan"}
