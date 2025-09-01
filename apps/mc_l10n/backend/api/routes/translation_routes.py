"""
翻译管理API路由

提供翻译条目的提取、导入、导出和管理REST API接口
"""

import os
import tempfile
from datetime import datetime
from typing import Any

from application.commands.base_command import command_bus
from application.commands.translation_commands import (
    BatchUpdateTranslationsCommand,
    ExportTranslationsCommand,
    ExtractTranslationsCommand,
    ImportTranslationsCommand,
    UpdateTranslationCommand,
)
from application.queries.base_query import query_bus
from application.queries.translation_queries import (
    GetTranslationProgressQuery,
    GetTranslationQuery,
    GetTranslationsQuery,
    GetUntranslatedEntriesQuery,
    SearchTranslationsQuery,
)
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from packages.core.framework.logging import StructLogFactory

logger = StructLogFactory.get_logger(__name__)
router = APIRouter(prefix="/api/v1/translations", tags=["翻译管理"])


# === DTO定义 ===


class ExtractTranslationsRequest(BaseModel):
    """提取翻译请求"""

    project_id: str = Field(..., description="项目ID")
    source_file_paths: list[str] = Field(..., description="源文件路径列表")
    target_language: str = Field(..., description="目标语言代码")
    source_language: str | None = Field("en_us", description="源语言代码")
    overwrite_existing: bool = Field(False, description="覆盖现有翻译")
    validate_format: bool = Field(True, description="验证文件格式")


class ImportTranslationsRequest(BaseModel):
    """导入翻译请求"""

    project_id: str = Field(..., description="项目ID")
    language_code: str = Field(..., description="语言代码")
    merge_strategy: str = Field(
        "overwrite", pattern="^(overwrite|merge|skip_existing)$", description="合并策略"
    )
    validate_keys: bool = Field(True, description="验证翻译键")
    backup_existing: bool = Field(True, description="备份现有翻译")


class ExportTranslationsRequest(BaseModel):
    """导出翻译请求"""

    project_id: str = Field(..., description="项目ID")
    language_code: str = Field(..., description="语言代码")
    file_format: str = Field(
        "json", pattern="^(json|properties)$", description="文件格式"
    )
    include_empty: bool = Field(False, description="包含空值")
    include_comments: bool = Field(True, description="包含注释")
    sort_keys: bool = Field(True, description="按键排序")


class UpdateTranslationRequest(BaseModel):
    """更新翻译请求"""

    project_id: str = Field(..., description="项目ID")
    translation_key: str = Field(..., description="翻译键")
    language_code: str = Field(..., description="语言代码")
    new_value: str = Field(..., description="新的翻译值")
    comment: str | None = Field(None, description="备注")
    validate_placeholders: bool = Field(True, description="验证占位符")


class BatchUpdateRequest(BaseModel):
    """批量更新翻译请求"""

    project_id: str = Field(..., description="项目ID")
    language_code: str = Field(..., description="语言代码")
    translations: dict[str, str] = Field(..., description="翻译数据（键值对）")
    overwrite_existing: bool = Field(True, description="覆盖现有翻译")
    validate_all_keys: bool = Field(True, description="验证所有翻译键")


class TranslationResponse(BaseModel):
    """翻译条目响应"""

    entry_id: str
    translation_key: str
    source_value: str | None = None
    translated_value: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    comment: str | None = None
    context: str | None = None
    metadata: dict[str, Any] | None = None


class TranslationListResponse(BaseModel):
    """翻译列表响应"""

    translations: list[TranslationResponse]
    pagination: dict[str, Any]
    filters_applied: dict[str, Any]


class TranslationProgressResponse(BaseModel):
    """翻译进度响应"""

    project_id: str
    language_code: str | None = None
    generated_at: datetime
    overall_progress: dict[str, Any]
    language_progress: dict[str, Any] | None = None
    by_language: dict[str, dict[str, Any]] | None = None
    by_mod: dict[str, dict[str, Any]] | None = None
    by_category: dict[str, dict[str, Any]] | None = None
    details: dict[str, Any] | None = None


class ExtractionResultResponse(BaseModel):
    """提取结果响应"""

    project_id: str
    target_language: str
    source_language: str | None = None
    total_files_processed: int
    successful_extractions: int
    failed_extractions: int
    total_entries_extracted: int
    extraction_results: list[dict[str, Any]]
    failed_files: list[dict[str, Any]]


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
    "/extract",
    response_model=ExtractionResultResponse,
    summary="提取翻译条目",
    description="从模组文件中提取翻译条目",
)
async def extract_translations(
    request: ExtractTranslationsRequest, user_id: str = Depends(get_user_id)
) -> ExtractionResultResponse:
    """提取翻译条目"""
    try:
        logger.info(
            f"提取翻译请求: 项目={request.project_id}, 文件数={len(request.source_file_paths)}"
        )

        # 创建命令
        command = ExtractTranslationsCommand(
            project_id=request.project_id,
            source_file_paths=request.source_file_paths,
            target_language=request.target_language,
            source_language=request.source_language,
            overwrite_existing=request.overwrite_existing,
            validate_format=request.validate_format,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"提取翻译失败: {result.error_message}",
            )

        return ExtractionResultResponse(**result.result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取翻译API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.post(
    "/import",
    response_model=ApiResponse,
    summary="导入翻译文件",
    description="从上传的文件中导入翻译数据",
)
async def import_translations(
    project_id: str = Form(..., description="项目ID"),
    language_code: str = Form(..., description="语言代码"),
    merge_strategy: str = Form("overwrite", description="合并策略"),
    validate_keys: bool = Form(True, description="验证翻译键"),
    backup_existing: bool = Form(True, description="备份现有翻译"),
    file: UploadFile = File(..., description="翻译文件"),
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """导入翻译文件"""
    try:
        logger.info(f"导入翻译请求: 项目={project_id}, 文件={file.filename}")

        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # 创建命令
            command = ImportTranslationsCommand(
                project_id=project_id,
                translation_file_path=temp_file_path,
                language_code=language_code,
                merge_strategy=merge_strategy,
                validate_keys=validate_keys,
                backup_existing=backup_existing,
                user_id=user_id,
            )

            # 执行命令
            result = await command_bus.execute(command)

            if not result.success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"导入翻译失败: {result.error_message}",
                )

            return ApiResponse(success=True, data=result.result, message="翻译导入成功")

        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入翻译API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.post(
    "/export",
    response_class=FileResponse,
    summary="导出翻译文件",
    description="导出项目的翻译数据为文件",
)
async def export_translations(
    request: ExportTranslationsRequest, user_id: str = Depends(get_user_id)
) -> FileResponse:
    """导出翻译文件"""
    try:
        logger.info(
            f"导出翻译请求: 项目={request.project_id}, 语言={request.language_code}"
        )

        # 生成临时文件路径
        file_extension = ".json" if request.file_format == "json" else ".properties"
        temp_file_path = tempfile.mktemp(suffix=file_extension)

        # 创建命令
        command = ExportTranslationsCommand(
            project_id=request.project_id,
            output_file_path=temp_file_path,
            language_code=request.language_code,
            file_format=request.file_format,
            include_empty=request.include_empty,
            include_comments=request.include_comments,
            sort_keys=request.sort_keys,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"导出翻译失败: {result.error_message}",
            )

        # 生成文件名
        filename = f"{request.project_id}_{request.language_code}{file_extension}"

        return FileResponse(
            path=temp_file_path,
            filename=filename,
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出翻译API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/",
    response_model=TranslationListResponse,
    summary="获取翻译列表",
    description="获取翻译条目列表，支持分页、排序和过滤",
)
async def get_translations(
    project_id: str = Query(..., description="项目ID"),
    language_code: str = Query(..., description="语言代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    sort_field: str = Query("key", description="排序字段"),
    sort_direction: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
    search_text: str | None = Query(None, description="搜索文本"),
    status_filter: str | None = Query(None, description="状态过滤"),
    mod_filter: str | None = Query(None, description="模组过滤"),
    category_filter: str | None = Query(None, description="分类过滤"),
    user_id: str = Depends(get_user_id),
) -> TranslationListResponse:
    """获取翻译列表"""
    try:
        logger.info(
            f"获取翻译列表: 项目={project_id}, 语言={language_code}, 页码={page}"
        )

        # 创建查询
        query = GetTranslationsQuery(
            project_id=project_id,
            language_code=language_code,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_direction=sort_direction,
            search_text=search_text,
            status_filter=status_filter,
            mod_filter=mod_filter,
            category_filter=category_filter,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取翻译列表失败: {result.error_message}",
            )

        # 转换响应格式
        translations = [
            TranslationResponse(
                entry_id=t["entry_id"],
                translation_key=t["translation_key"],
                source_value=t.get("source_value"),
                translated_value=t.get("translated_value"),
                status=t["status"],
                created_at=datetime.utcnow(),  # 简化实现
                updated_at=datetime.fromisoformat(t["updated_at"])
                if t.get("updated_at")
                else None,
                has_comment=t.get("has_comment", False),
            )
            for t in result.result.get("translations", [])
        ]

        return TranslationListResponse(
            translations=translations,
            pagination=result.result.get("pagination", {}),
            filters_applied=result.result.get("filters_applied", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取翻译列表API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/{translation_key}",
    response_model=TranslationResponse,
    summary="获取翻译条目详情",
    description="根据翻译键获取详细信息",
)
async def get_translation(
    translation_key: str = Path(..., description="翻译键"),
    project_id: str = Query(..., description="项目ID"),
    language_code: str = Query(..., description="语言代码"),
    include_metadata: bool = Query(True, description="包含元数据"),
    user_id: str = Depends(get_user_id),
) -> TranslationResponse:
    """获取翻译条目详情"""
    try:
        logger.info(f"获取翻译详情: 键={translation_key}, 项目={project_id}")

        # 创建查询
        query = GetTranslationQuery(
            project_id=project_id,
            translation_key=translation_key,
            language_code=language_code,
            include_metadata=include_metadata,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            if result.error_code == "TRANSLATION_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="翻译条目不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"获取翻译详情失败: {result.error_message}",
                )

        # 转换响应格式
        t = result.result
        return TranslationResponse(
            entry_id=t["entry_id"],
            translation_key=t["translation_key"],
            source_value=t.get("source_value"),
            translated_value=t.get("translated_value"),
            status=t["status"],
            created_at=datetime.fromisoformat(t["created_at"]),
            updated_at=datetime.fromisoformat(t["updated_at"])
            if t.get("updated_at")
            else None,
            comment=t.get("comment"),
            context=t.get("context"),
            metadata=t.get("metadata"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取翻译详情API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.put(
    "/{translation_key}",
    response_model=ApiResponse,
    summary="更新翻译条目",
    description="更新指定的翻译条目",
)
async def update_translation(
    translation_key: str = Path(..., description="翻译键"),
    request: UpdateTranslationRequest = ...,
    user_id: str = Depends(get_user_id),
) -> ApiResponse:
    """更新翻译条目"""
    try:
        logger.info(f"更新翻译: 键={translation_key}")

        # 创建命令（使用路径参数中的translation_key）
        command = UpdateTranslationCommand(
            project_id=request.project_id,
            translation_key=translation_key,
            language_code=request.language_code,
            new_value=request.new_value,
            comment=request.comment,
            validate_placeholders=request.validate_placeholders,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"更新翻译失败: {result.error_message}",
            )

        return ApiResponse(success=True, data=result.result, message="翻译更新成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新翻译API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.post(
    "/batch-update",
    response_model=ApiResponse,
    summary="批量更新翻译",
    description="批量更新多个翻译条目",
)
async def batch_update_translations(
    request: BatchUpdateRequest, user_id: str = Depends(get_user_id)
) -> ApiResponse:
    """批量更新翻译"""
    try:
        logger.info(
            f"批量更新翻译: 项目={request.project_id}, 条目数={len(request.translations)}"
        )

        # 创建命令
        command = BatchUpdateTranslationsCommand(
            project_id=request.project_id,
            language_code=request.language_code,
            translations=request.translations,
            overwrite_existing=request.overwrite_existing,
            validate_all_keys=request.validate_all_keys,
            user_id=user_id,
        )

        # 执行命令
        result = await command_bus.execute(command)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"批量更新翻译失败: {result.error_message}",
            )

        return ApiResponse(success=True, data=result.result, message="批量更新翻译成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新翻译API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/progress",
    response_model=TranslationProgressResponse,
    summary="获取翻译进度",
    description="获取项目的翻译进度统计",
)
async def get_translation_progress(
    project_id: str = Query(..., description="项目ID"),
    language_code: str | None = Query(None, description="特定语言代码"),
    group_by_mod: bool = Query(True, description="按模组分组"),
    group_by_category: bool = Query(False, description="按分类分组"),
    include_details: bool = Query(False, description="包含详细信息"),
    user_id: str = Depends(get_user_id),
) -> TranslationProgressResponse:
    """获取翻译进度"""
    try:
        logger.info(f"获取翻译进度: 项目={project_id}, 语言={language_code}")

        # 创建查询
        query = GetTranslationProgressQuery(
            project_id=project_id,
            language_code=language_code,
            group_by_mod=group_by_mod,
            group_by_category=group_by_category,
            include_details=include_details,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取翻译进度失败: {result.error_message}",
            )

        # 转换响应格式
        progress_data = result.result
        return TranslationProgressResponse(
            project_id=progress_data["project_id"],
            language_code=progress_data.get("language_code"),
            generated_at=datetime.fromisoformat(progress_data["generated_at"]),
            overall_progress=progress_data["overall_progress"],
            language_progress=progress_data.get("language_progress"),
            by_language=progress_data.get("by_language"),
            by_mod=progress_data.get("by_mod"),
            by_category=progress_data.get("by_category"),
            details=progress_data.get("details"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取翻译进度API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/untranslated",
    response_model=TranslationListResponse,
    summary="获取未翻译条目",
    description="获取未翻译的条目列表",
)
async def get_untranslated_entries(
    project_id: str = Query(..., description="项目ID"),
    language_code: str = Query(..., description="语言代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    priority_order: bool = Query(True, description="按优先级排序"),
    mod_filter: str | None = Query(None, description="模组过滤"),
    user_id: str = Depends(get_user_id),
) -> TranslationListResponse:
    """获取未翻译条目"""
    try:
        logger.info(f"获取未翻译条目: 项目={project_id}, 语言={language_code}")

        # 创建查询
        query = GetUntranslatedEntriesQuery(
            project_id=project_id,
            language_code=language_code,
            page=page,
            page_size=page_size,
            priority_order=priority_order,
            mod_filter=mod_filter,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取未翻译条目失败: {result.error_message}",
            )

        # 转换响应格式（简化实现）
        translations = []  # 应该根据实际查询结果转换

        return TranslationListResponse(
            translations=translations,
            pagination=result.result.get("pagination", {}),
            filters_applied={"status_filter": "untranslated"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取未翻译条目API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )


@router.get(
    "/search",
    response_model=TranslationListResponse,
    summary="搜索翻译条目",
    description="在翻译条目中搜索关键词",
)
async def search_translations(
    project_id: str = Query(..., description="项目ID"),
    search_text: str = Query(..., min_length=2, description="搜索关键词"),
    search_in_keys: bool = Query(True, description="搜索翻译键"),
    search_in_values: bool = Query(True, description="搜索翻译值"),
    search_in_comments: bool = Query(False, description="搜索注释"),
    language_codes: list[str] | None = Query(None, description="语言代码列表"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    user_id: str = Depends(get_user_id),
) -> TranslationListResponse:
    """搜索翻译条目"""
    try:
        logger.info(f"搜索翻译: 项目={project_id}, 关键词='{search_text}'")

        # 创建查询
        query = SearchTranslationsQuery(
            project_id=project_id,
            search_text=search_text,
            search_in_keys=search_in_keys,
            search_in_values=search_in_values,
            search_in_comments=search_in_comments,
            language_codes=language_codes,
            page=page,
            page_size=page_size,
            user_id=user_id,
        )

        # 执行查询
        result = await query_bus.execute(query)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"搜索翻译失败: {result.error_message}",
            )

        # 转换响应格式（简化实现）
        translations = []  # 应该根据实际查询结果转换

        return TranslationListResponse(
            translations=translations,
            pagination=result.result.get("pagination", {}),
            filters_applied={"search_text": search_text},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索翻译API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误"
        )
