"""
项目管理API路由

提供翻译项目的创建、管理和查询REST API接口
"""

from datetime import datetime
from typing import Any

from application.commands.base_command import command_bus
from application.commands.project_commands import (
    ArchiveProjectCommand,
    CreateProjectCommand,
    DeleteProjectCommand,
    UpdateProjectCommand,
)
from application.queries.base_query import query_bus
from application.queries.project_queries import (
    GetProjectByIdQuery,
    GetProjectsQuery,
    GetProjectStatisticsQuery,
    SearchProjectsQuery,
)
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from packages.core.framework.logging import StructLogFactory

logger = StructLogFactory.get_logger(__name__)
router = APIRouter(prefix="/api/v1/projects", tags=["项目管理"])


# === DTO定义 ===


class CreateProjectRequest(BaseModel):
    """创建项目请求"""

    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: str = Field("", max_length=1000, description="项目描述")
    mc_version: str = Field(..., description="Minecraft版本")
    target_language: str = Field(..., description="目标语言代码")
    source_path: str = Field(..., description="源文件路径")
    output_path: str = Field(..., description="输出路径")


class UpdateProjectRequest(BaseModel):
    """更新项目请求"""

    name: str | None = Field(None, min_length=1, max_length=100, description="项目名称")
    description: str | None = Field(None, max_length=1000, description="项目描述")
    mc_version: str | None = Field(None, description="Minecraft版本")
    target_language: str | None = Field(None, description="目标语言代码")
    source_path: str | None = Field(None, description="源文件路径")
    output_path: str | None = Field(None, description="输出路径")


class ProjectResponse(BaseModel):
    """项目响应"""

    project_id: str
    name: str
    description: str
    mc_version: str
    target_language: str
    source_path: str
    output_path: str
    created_at: datetime
    updated_at: datetime | None
    is_archived: bool
    archive_reason: str | None = None
    statistics: dict[str, Any] | None = None


class ProjectListResponse(BaseModel):
    """项目列表响应"""

    projects: list[ProjectResponse]
    pagination: dict[str, Any]


class ProjectStatisticsResponse(BaseModel):
    """项目统计响应"""

    project_id: str
    generated_at: datetime
    translation_progress: dict[str, Any] | None = None
    file_statistics: dict[str, Any] | None = None
    mod_statistics: dict[str, Any] | None = None


class ApiResponse(BaseModel):
    """通用API响应"""

    success: bool
    data: Any | None = None
    message: str = ""
    error_code: str | None = None


# === 依赖注入 ===


def get_user_id() -> str:
    """获取当前用户ID（简化实现）"""
    # TODO: 从认证中间件或JWT token中获取实际用户ID
    return "default_user"


# === API路由实现 ===


@router.post(
    "/",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建翻译项目",
    description="创建一个新的Minecraft模组翻译项目",
)
async def create_project(
    request: CreateProjectRequest, user_id: str = Depends(get_user_id)
) -> ApiResponse:
    """创建翻译项目"""
    try:
        logger.info(f"创建项目请求: {request.name}")

        # 创建命令
        command = CreateProjectCommand(
            name=request.name,
            description=request.description,
            mc_version=request.mc_version,
            target_language=request.target_language,
            source_path=request.source_path,
            output_path=request.output_path,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"创建项目失败: {result.error_message}",
            )

        return ApiResponse(
            success=True, data={"project_id": result.result}, message="项目创建成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建项目API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="获取项目列表",
    description="获取翻译项目列表，支持分页、排序和过滤",
)
async def get_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_field: str = Query("created_at", description="排序字段"),
    sort_direction: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    search_text: str | None = Query(None, description="搜索文本"),
    mc_version_filter: str | None = Query(None, description="MC版本过滤"),
    language_filter: str | None = Query(None, description="语言过滤"),
    include_archived: bool = Query(False, description="是否包含归档项目"),
    include_statistics: bool = Query(False, description="是否包含统计信息"),
    user_id: str = Depends(get_user_id),
) -> ProjectListResponse:
    """获取项目列表"""
    try:
        logger.info(f"获取项目列表: 页码={page}, 页大小={page_size}")

        # 创建查询
        query = GetProjectsQuery(
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_direction=sort_direction,
            search_text=search_text,
            mc_version_filter=mc_version_filter,
            language_filter=language_filter,
            include_archived=include_archived,
            include_statistics=include_statistics,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取项目列表失败: {result.error_message}",
            )

        # 转换响应格式
        projects = [
            ProjectResponse(
                project_id=p["project_id"],
                name=p["name"],
                description=p["description"],
                mc_version=p["mc_version"],
                target_language=p["target_language"],
                source_path=p["source_path"],
                output_path=p["output_path"],
                created_at=datetime.fromisoformat(p["created_at"]),
                updated_at=datetime.fromisoformat(p["updated_at"])
                if p["updated_at"]
                else None,
                is_archived=p["is_archived"],
                archive_reason=p.get("archive_reason"),
                statistics=p.get("statistics"),
            )
            for p in result.result["projects"]
        ]

        return ProjectListResponse(
            projects=projects, pagination=result.result["pagination"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目列表API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="获取项目详情",
    description="根据项目ID获取详细信息",
)
async def get_project(
    project_id: str = Path(..., description="项目ID"),
    include_statistics: bool = Query(True, description="是否包含统计信息"),
    user_id: str = Depends(get_user_id),
) -> ProjectResponse:
    """获取项目详情"""
    try:
        logger.info(f"获取项目详情: {project_id}")

        # 创建查询
        query = GetProjectByIdQuery(
            project_id=project_id,
            include_statistics=include_statistics,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            if result.error_code == "PROJECT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"获取项目详情失败: {result.error_message}",
                )

        # 转换响应格式
        project_data = result.result
        return ProjectResponse(
            project_id=project_data["project_id"],
            name=project_data["name"],
            description=project_data["description"],
            mc_version=project_data["mc_version"],
            target_language=project_data["target_language"],
            source_path=project_data["source_path"],
            output_path=project_data["output_path"],
            created_at=datetime.fromisoformat(project_data["created_at"]),
            updated_at=datetime.fromisoformat(project_data["updated_at"])
            if project_data["updated_at"]
            else None,
            is_archived=project_data["is_archived"],
            archive_reason=project_data.get("archive_reason"),
            statistics=project_data.get("statistics"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.put(
    "/{project_id}",
    response_model=ApiResponse,
    summary="更新项目",
    description="更新项目信息",
)
async def update_project(
    project_id: str = Path(..., description="项目ID"),
    request: UpdateProjectRequest = ...,
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """更新项目"""
    try:
        logger.info(f"更新项目: {project_id}")

        # 创建命令
        command = UpdateProjectCommand(
            project_id=project_id,
            name=request.name,
            description=request.description,
            mc_version=request.mc_version,
            target_language=request.target_language,
            source_path=request.source_path,
            output_path=request.output_path,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            if result.error_code == "PROJECT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"更新项目失败: {result.error_message}",
                )

        return ApiResponse(
            success=True, data={"updated": result.result}, message="项目更新成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.delete(
    "/{project_id}",
    response_model=ApiResponse,
    summary="删除项目",
    description="删除项目及其相关数据",
)
async def delete_project(
    project_id: str = Path(..., description="项目ID"),
    force: bool = Query(False, description="强制删除（忽略数据检查）"),
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """删除项目"""
    try:
        logger.info(f"删除项目: {project_id}, 强制删除: {force}")

        # 创建命令
        command = DeleteProjectCommand(
            project_id=project_id, force=force, user_id=user_id
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            if result.error_code == "PROJECT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
                )
            elif result.error_code == "PROJECT_HAS_DATA":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="项目包含重要数据，无法删除。使用force=true强制删除",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"删除项目失败: {result.error_message}",
                )

        return ApiResponse(
            success=True, data={"deleted": result.result}, message="项目删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.post(
    "/{project_id}/archive",
    response_model=ApiResponse,
    summary="归档项目",
    description="将项目设置为归档状态",
)
async def archive_project(
    project_id: str = Path(..., description="项目ID"),
    archive_reason: str | None = Query(None, description="归档原因"),
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """归档项目"""
    try:
        logger.info(f"归档项目: {project_id}")

        # 创建命令
        command = ArchiveProjectCommand(
            project_id=project_id, archive_reason=archive_reason, user_id=user_id
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            if result.error_code == "PROJECT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"归档项目失败: {result.error_message}",
                )

        return ApiResponse(
            success=True, data={"archived": result.result}, message="项目归档成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"归档项目API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/{project_id}/statistics",
    response_model=ProjectStatisticsResponse,
    summary="获取项目统计信息",
    description="获取项目的详细统计信息",
)
async def get_project_statistics(
    project_id: str = Path(..., description="项目ID"),
    include_translation_progress: bool = Query(True, description="包含翻译进度"),
    include_file_statistics: bool = Query(True, description="包含文件统计"),
    include_mod_statistics: bool = Query(True, description="包含模组统计"),
    user_id: str = Depends(get_user_id),
) -> ProjectStatisticsResponse:
    """获取项目统计信息"""
    try:
        logger.info(f"获取项目统计信息: {project_id}")

        # 创建查询
        query = GetProjectStatisticsQuery(
            project_id=project_id,
            include_translation_progress=include_translation_progress,
            include_file_statistics=include_file_statistics,
            include_mod_statistics=include_mod_statistics,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            if result.error_code == "PROJECT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"获取项目统计失败: {result.error_message}",
                )

        # 转换响应格式
        stats_data = result.result
        return ProjectStatisticsResponse(
            project_id=stats_data["project_id"],
            generated_at=datetime.fromisoformat(stats_data["generated_at"]),
            translation_progress=stats_data.get("translation_progress"),
            file_statistics=stats_data.get("file_statistics"),
            mod_statistics=stats_data.get("mod_statistics"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目统计API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/search",
    response_model=ProjectListResponse,
    summary="搜索项目",
    description="根据关键词搜索项目",
)
async def search_projects(
    search_text: str = Query(..., min_length=2, description="搜索关键词"),
    search_fields: list[str] = Query(["name", "description"], description="搜索字段"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_user_id),
) -> ProjectListResponse:
    """搜索项目"""
    try:
        logger.info(f"搜索项目: '{search_text}'")

        # 创建查询
        query = SearchProjectsQuery(
            search_text=search_text,
            search_fields=search_fields,
            page=page,
            page_size=page_size,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"搜索项目失败: {result.error_message}",
            )

        # 转换响应格式（简化，实际应该包含搜索高亮等信息）
        projects = [
            ProjectResponse(
                project_id=p["project_id"],
                name=p["name"],
                description=p["description"],
                mc_version=p["mc_version"],
                target_language=p["target_language"],
                source_path="",  # 搜索结果中可能不包含完整信息
                output_path="",
                created_at=datetime.fromisoformat(p["created_at"]),
                updated_at=None,
                is_archived=False,
            )
            for p in result.result["projects"]
        ]

        return ProjectListResponse(
            projects=projects, pagination=result.result["pagination"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索项目API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )
