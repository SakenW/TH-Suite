"""
模组管理API路由

提供模组扫描、分析和查询的REST API接口
"""

from datetime import datetime
from typing import Any

from application.commands.base_command import command_bus
from application.commands.mod_commands import (
    AnalyzeModCommand,
    BatchScanModsCommand,
    ScanModCommand,
)
from application.queries.base_query import query_bus
from application.queries.mod_queries import (
    GetModByIdQuery,
    GetModDependenciesQuery,
    GetModLanguageFilesQuery,
    GetModsQuery,
    GetModStatisticsQuery,
    SearchModsQuery,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from pydantic import BaseModel, Field

from packages.core.framework.logging import StructLogFactory

logger = StructLogFactory.get_logger(__name__)
router = APIRouter(prefix="/api/v1/mods", tags=["模组管理"])


# === DTO定义 ===


class ScanModRequest(BaseModel):
    """扫描模组请求"""

    project_id: str = Field(..., description="项目ID")
    source_path: str = Field(..., description="扫描路径")
    scan_target: str = Field(
        "both", pattern="^(jar|folder|both)$", description="扫描目标"
    )
    include_patterns: list[str] | None = Field(None, description="包含模式")
    exclude_patterns: list[str] | None = Field(None, description="排除模式")
    recursive: bool = Field(True, description="递归扫描")


class AnalyzeModRequest(BaseModel):
    """分析模组请求"""

    project_id: str = Field(..., description="项目ID")
    mod_file_path: str = Field(..., description="模组文件路径")
    deep_analysis: bool = Field(False, description="深度分析")
    extract_metadata: bool = Field(True, description="提取元数据")
    validate_structure: bool = Field(True, description="验证结构")


class BatchScanRequest(BaseModel):
    """批量扫描请求"""

    project_id: str = Field(..., description="项目ID")
    source_paths: list[str] = Field(..., description="扫描路径列表")
    scan_target: str = Field(
        "both", pattern="^(jar|folder|both)$", description="扫描目标"
    )
    parallel_workers: int = Field(4, ge=1, le=16, description="并行工作数")
    include_patterns: list[str] | None = Field(None, description="包含模式")
    exclude_patterns: list[str] | None = Field(None, description="排除模式")


class ModResponse(BaseModel):
    """模组响应"""

    mod_id: str
    name: str
    version: str
    description: str | None = None
    author: str | None = None
    loader_type: str | None = None
    minecraft_versions: list[str]
    file_path: str
    file_size_mb: float
    created_at: datetime
    has_language_files: bool
    language_files: list[dict[str, Any]] | None = None
    dependencies: list[dict[str, Any]] | None = None
    statistics: dict[str, Any] | None = None


class ModListResponse(BaseModel):
    """模组列表响应"""

    mods: list[ModResponse]
    pagination: dict[str, Any]
    filters_applied: dict[str, Any]


class ScanResultResponse(BaseModel):
    """扫描结果响应"""

    project_id: str
    source_path: str
    scan_target: str
    total_files_found: int
    total_mods_found: int
    scan_results: list[dict[str, Any]]


class AnalysisResultResponse(BaseModel):
    """分析结果响应"""

    project_id: str
    mod_file_path: str
    mod_id: str | None = None
    mod_name: str | None = None
    mod_version: str | None = None
    mod_loader_type: str | None = None
    minecraft_versions: list[str] = []
    dependencies: list[dict[str, Any]] = []
    language_files: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    deep_analysis: dict[str, Any] | None = None


class LanguageFilesResponse(BaseModel):
    """语言文件响应"""

    mod_id: str
    language_files: list[dict[str, Any]]
    statistics: dict[str, Any]
    filters_applied: dict[str, Any]


class ApiResponse(BaseModel):
    """通用API响应"""

    success: bool
    data: Any | None = None
    message: str = ""
    error_code: str | None = None


# === 依赖注入 ===


def get_user_id() -> str:
    """获取当前用户ID（简化实现）"""
    return "default_user"


# === API路由实现 ===


@router.post(
    "/scan",
    response_model=ScanResultResponse,
    summary="扫描模组文件",
    description="扫描指定路径下的模组文件",
)
async def scan_mods(
    request: ScanModRequest, user_id: str = Depends(get_user_id)
) -> ScanResultResponse:
    """扫描模组文件"""
    try:
        logger.info(f"扫描模组请求: {request.source_path}")

        # 创建命令
        command = ScanModCommand(
            project_id=request.project_id,
            source_path=request.source_path,
            scan_target=request.scan_target,
            include_patterns=request.include_patterns,
            exclude_patterns=request.exclude_patterns,
            recursive=request.recursive,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"扫描模组失败: {result.error_message}",
            )

        return ScanResultResponse(**result.result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫描模组API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.post(
    "/analyze",
    response_model=AnalysisResultResponse,
    summary="分析模组文件",
    description="深度分析单个模组文件",
)
async def analyze_mod(
    request: AnalyzeModRequest, user_id: str = Depends(get_user_id)
) -> AnalysisResultResponse:
    """分析模组文件"""
    try:
        logger.info(f"分析模组请求: {request.mod_file_path}")

        # 创建命令
        command = AnalyzeModCommand(
            project_id=request.project_id,
            mod_file_path=request.mod_file_path,
            deep_analysis=request.deep_analysis,
            extract_metadata=request.extract_metadata,
            validate_structure=request.validate_structure,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分析模组失败: {result.error_message}",
            )

        return AnalysisResultResponse(**result.result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析模组API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.post(
    "/batch-scan",
    response_model=ApiResponse,
    summary="批量扫描模组",
    description="批量扫描多个路径下的模组文件",
)
async def batch_scan_mods(
    request: BatchScanRequest, user_id: str = Depends(get_user_id)
) -> ApiResponse:
    """批量扫描模组"""
    try:
        logger.info(f"批量扫描模组请求: {len(request.source_paths)} 个路径")

        # 创建命令
        command = BatchScanModsCommand(
            project_id=request.project_id,
            source_paths=request.source_paths,
            scan_target=request.scan_target,
            parallel_workers=request.parallel_workers,
            include_patterns=request.include_patterns,
            exclude_patterns=request.exclude_patterns,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"批量扫描模组失败: {result.error_message}",
            )

        return ApiResponse(success=True, data=result.result, message="批量扫描完成")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量扫描模组API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/",
    response_model=ModListResponse,
    summary="获取模组列表",
    description="获取项目中的模组列表，支持分页、排序和过滤",
)
async def get_mods(
    project_id: str = Query(..., description="项目ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_field: str = Query("name", description="排序字段"),
    sort_direction: str = Query("asc", regex="^(asc|desc)$", description="排序方向"),
    search_text: str | None = Query(None, description="搜索文本"),
    loader_type_filter: str | None = Query(None, description="模组加载器类型过滤"),
    mc_version_filter: str | None = Query(None, description="MC版本过滤"),
    user_id: str = Depends(get_user_id),
) -> ModListResponse:
    """获取模组列表"""
    try:
        logger.info(f"获取模组列表: 项目={project_id}, 页码={page}")

        # 创建查询
        query = GetModsQuery(
            project_id=project_id,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_direction=sort_direction,
            search_text=search_text,
            loader_type_filter=loader_type_filter,
            mc_version_filter=mc_version_filter,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取模组列表失败: {result.error_message}",
            )

        # 转换响应格式
        mods = [
            ModResponse(
                mod_id=m["mod_id"],
                name=m["name"],
                version=m["version"],
                author=m.get("author"),
                loader_type=m.get("loader_type"),
                minecraft_versions=m["minecraft_versions"],
                file_size_mb=m["file_size_mb"],
                created_at=datetime.fromisoformat(m["created_at"]),
                has_language_files=m["has_language_files"],
                file_path="",  # 简化响应
            )
            for m in result.result["mods"]
        ]

        return ModListResponse(
            mods=mods,
            pagination=result.result["pagination"],
            filters_applied=result.result["filters_applied"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模组列表API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/{mod_id}",
    response_model=ModResponse,
    summary="获取模组详情",
    description="根据模组ID获取详细信息",
)
async def get_mod(
    mod_id: str = Path(..., description="模组ID"),
    project_id: str = Query(..., description="项目ID"),
    include_language_files: bool = Query(True, description="包含语言文件"),
    include_dependencies: bool = Query(True, description="包含依赖关系"),
    include_statistics: bool = Query(False, description="包含统计信息"),
    user_id: str = Depends(get_user_id),
) -> ModResponse:
    """获取模组详情"""
    try:
        logger.info(f"获取模组详情: {mod_id}")

        # 创建查询
        query = GetModByIdQuery(
            project_id=project_id,
            mod_id=mod_id,
            include_language_files=include_language_files,
            include_dependencies=include_dependencies,
            include_statistics=include_statistics,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            if result.error_code == "MOD_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="模组不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"获取模组详情失败: {result.error_message}",
                )

        # 转换响应格式
        mod_data = result.result
        return ModResponse(
            mod_id=mod_data["mod_id"],
            name=mod_data["name"],
            version=mod_data["version"],
            description=mod_data.get("description"),
            author=mod_data.get("author"),
            loader_type=mod_data.get("loader_type"),
            minecraft_versions=mod_data["minecraft_versions"],
            file_path=mod_data["file_path"],
            file_size_mb=mod_data["file_size_bytes"] / (1024 * 1024),
            created_at=datetime.fromisoformat(mod_data["created_at"]),
            has_language_files=len(mod_data.get("language_files", [])) > 0,
            language_files=mod_data.get("language_files"),
            dependencies=mod_data.get("dependencies"),
            statistics=mod_data.get("statistics"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模组详情API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/{mod_id}/language-files",
    response_model=LanguageFilesResponse,
    summary="获取模组语言文件",
    description="获取模组的语言文件列表",
)
async def get_mod_language_files(
    mod_id: str = Path(..., description="模组ID"),
    project_id: str = Query(..., description="项目ID"),
    file_type_filter: str | None = Query(None, description="文件类型过滤"),
    language_filter: str | None = Query(None, description="语言过滤"),
    user_id: str = Depends(get_user_id),
) -> LanguageFilesResponse:
    """获取模组语言文件"""
    try:
        logger.info(f"获取模组语言文件: {mod_id}")

        # 创建查询
        query = GetModLanguageFilesQuery(
            project_id=project_id,
            mod_id=mod_id,
            file_type_filter=file_type_filter,
            language_filter=language_filter,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取模组语言文件失败: {result.error_message}",
            )

        return LanguageFilesResponse(**result.result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模组语言文件API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/{mod_id}/dependencies",
    response_model=ApiResponse,
    summary="获取模组依赖关系",
    description="获取模组的依赖关系图",
)
async def get_mod_dependencies(
    mod_id: str = Path(..., description="模组ID"),
    project_id: str = Query(..., description="项目ID"),
    include_reverse_dependencies: bool = Query(False, description="包含反向依赖"),
    depth_limit: int = Query(3, ge=1, le=10, description="依赖深度限制"),
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """获取模组依赖关系"""
    try:
        logger.info(f"获取模组依赖关系: {mod_id}")

        # 创建查询
        query = GetModDependenciesQuery(
            project_id=project_id,
            mod_id=mod_id,
            include_reverse_dependencies=include_reverse_dependencies,
            depth_limit=depth_limit,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取模组依赖关系失败: {result.error_message}",
            )

        return ApiResponse(success=True, data=result.result, message="获取依赖关系成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模组依赖关系API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/statistics",
    response_model=ApiResponse,
    summary="获取模组统计信息",
    description="获取项目中模组的统计信息",
)
async def get_mod_statistics(
    project_id: str = Query(..., description="项目ID"),
    mod_id: str | None = Query(None, description="特定模组ID（可选）"),
    include_translation_stats: bool = Query(True, description="包含翻译统计"),
    include_file_stats: bool = Query(True, description="包含文件统计"),
    group_by_language: bool = Query(False, description="按语言分组"),
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """获取模组统计信息"""
    try:
        logger.info(f"获取模组统计信息: 项目={project_id}")

        # 创建查询
        query = GetModStatisticsQuery(
            project_id=project_id,
            mod_id=mod_id,
            include_translation_stats=include_translation_stats,
            include_file_stats=include_file_stats,
            group_by_language=group_by_language,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取模组统计信息失败: {result.error_message}",
            )

        return ApiResponse(success=True, data=result.result, message="获取统计信息成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模组统计信息API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/search",
    response_model=ModListResponse,
    summary="搜索模组",
    description="根据关键词搜索模组",
)
async def search_mods(
    project_id: str = Query(..., description="项目ID"),
    search_text: str = Query(..., min_length=2, description="搜索关键词"),
    search_fields: list[str] = Query(
        ["name", "mod_id", "description"], description="搜索字段"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_user_id),
) -> ModListResponse:
    """搜索模组"""
    try:
        logger.info(f"搜索模组: '{search_text}'")

        # 创建查询
        query = SearchModsQuery(
            project_id=project_id,
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
                detail=f"搜索模组失败: {result.error_message}",
            )

        # 转换响应格式（简化）
        mods = [
            ModResponse(
                mod_id=m["mod_id"],
                name=m["name"],
                version=m.get("version", ""),
                author=m.get("author"),
                minecraft_versions=[],
                file_path="",
                file_size_mb=0.0,
                created_at=datetime.utcnow(),
                has_language_files=False,
            )
            for m in result.result.get("mods", [])
        ]

        return ModListResponse(
            mods=mods,
            pagination=result.result.get("pagination", {}),
            filters_applied={"search_text": search_text},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索模组API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )
