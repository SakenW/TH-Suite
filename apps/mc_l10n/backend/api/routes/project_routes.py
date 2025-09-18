"""
项目管理相关路由
提供项目的创建、配置和管理功能
V5架构 - 集成Repository模式
"""

import logging
from typing import Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from infrastructure.repositories.repository_factory import get_repository_factory, RepositoryFactory
from infrastructure.repositories.core_project_repository import CoreProject

logger = logging.getLogger(__name__)

def get_repo_factory() -> RepositoryFactory:
    """依赖注入：获取Repository工厂"""
    return get_repository_factory()

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["项目管理"],
    responses={404: {"description": "Not found"}},
)


class ProjectCreateRequest(BaseModel):
    """创建项目请求模型"""
    name: str
    description: str | None = None


class ProjectResponse(BaseModel):
    """项目响应模型"""
    uid: str
    name: str
    description: str | None = None
    created_at: str
    updated_at: str


class ProjectListResponse(BaseModel):
    """项目列表响应模型"""
    projects: List[ProjectResponse]
    total: int


@router.get("/test", response_model=dict[str, Any])
async def project_test_endpoint():
    """
    项目路由测试端点

    用于验证项目路由是否正常工作
    """
    return {
        "success": True,
        "message": "Project routes are working",
        "service": "project-management",
        "endpoints_available": [
            "GET /api/v1/projects/test",
            "GET /api/v1/projects/",
            "POST /api/v1/projects/",
            "GET /api/v1/projects/{project_id}",
        ],
    }


@router.get("", response_model=dict[str, Any])
@router.get("/", response_model=dict[str, Any])
async def list_projects(
    limit: int = 50,
    offset: int = 0,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取项目列表

    返回所有已创建的项目信息
    """
    try:
        project_repo = factory.get_core_project_repo()
        projects = project_repo.list_all(limit=limit, offset=offset)
        total = project_repo.count()
        
        project_responses = [
            ProjectResponse(
                uid=project.uid,
                name=project.name,
                description=project.description,
                created_at=project.created_at or "",
                updated_at=project.updated_at or ""
            )
            for project in projects
        ]
        
        return {
            "success": True,
            "data": {
                "projects": [p.dict() for p in project_responses],
                "total": total
            },
            "message": "项目列表获取成功",
        }
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict[str, Any])
@router.post("/", response_model=dict[str, Any])
async def create_project(
    project_data: ProjectCreateRequest,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    创建新项目

    Args:
        project_data: 项目创建信息
    """
    try:
        project_repo = factory.get_core_project_repo()
        
        # 检查名称是否已存在
        existing = project_repo.get_by_name(project_data.name)
        if existing:
            raise HTTPException(status_code=409, detail=f"项目名称已存在: {project_data.name}")
        
        # 创建新项目
        new_project = CoreProject(
            uid="",  # Repository会自动生成
            name=project_data.name,
            description=project_data.description
        )
        
        project_uid = project_repo.create(new_project)
        created_project = project_repo.get_by_uid(project_uid)
        
        if not created_project:
            raise HTTPException(status_code=500, detail="项目创建失败")
        
        response = ProjectResponse(
            uid=created_project.uid,
            name=created_project.name,
            description=created_project.description,
            created_at=created_project.created_at or "",
            updated_at=created_project.updated_at or ""
        )

        return {
            "success": True,
            "data": response.dict(),
            "message": f"项目创建成功: {project_data.name}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_uid}", response_model=dict[str, Any])
async def get_project_info(
    project_uid: str,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取指定项目的详细信息

    Args:
        project_uid: 项目UID
    """
    try:
        project_repo = factory.get_core_project_repo()
        pack_repo = factory.get_core_pack_repo()
        mod_repo = factory.get_core_mod_repo()
        
        # 获取项目信息
        project = project_repo.get_by_uid(project_uid)
        if not project:
            raise HTTPException(status_code=404, detail=f"项目不存在: {project_uid}")
        
        # 获取统计信息
        pack_count = pack_repo.count()
        mod_count = mod_repo.count()
        
        response = ProjectResponse(
            uid=project.uid,
            name=project.name,
            description=project.description,
            created_at=project.created_at or "",
            updated_at=project.updated_at or ""
        )

        return {
            "success": True,
            "data": {
                **response.dict(),
                "statistics": {
                    "total_packs": pack_count,
                    "total_mods": mod_count,
                    "total_language_files": 0,  # TODO: 实现语言文件统计
                    "total_keys": 0,
                    "translated_keys": 0,
                    "translation_progress": 0.0,
                },
            },
            "message": f"项目信息获取成功: {project.name}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目信息失败 {project_uid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
