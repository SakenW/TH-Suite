"""
模组API路由
处理模组相关的HTTP请求
"""

import logging
from typing import Any

from application.commands import DeleteModCommand
from application.dto import ErrorDTO, PagedResultDTO
from application.queries import GetModByIdQuery, GetModsByStatusQuery, SearchModsQuery
from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_mod_service, get_query_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mods", tags=["mods"])


@router.get("/{mod_id}")
async def get_mod(
    mod_id: str,
    include_translations: bool = True,
    include_metadata: bool = True,
    query_service=Depends(get_query_service),
) -> dict[str, Any]:
    """
    获取模组详情

    Args:
        mod_id: 模组ID
        include_translations: 是否包含翻译
        include_metadata: 是否包含元数据

    Returns:
        模组信息
    """
    try:
        query = GetModByIdQuery(
            query_id=f"get_mod_{mod_id}",
            mod_id=mod_id,
            include_translations=include_translations,
            include_metadata=include_metadata,
        )

        result = query_service.handle_query(query)
        if not result:
            raise HTTPException(status_code=404, detail=f"Mod {mod_id} not found")

        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mod {mod_id}: {e}")
        error = ErrorDTO.from_exception(e, "GET_MOD_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.get("/")
async def list_mods(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    query_service=Depends(get_query_service),
) -> dict[str, Any]:
    """
    获取模组列表

    Args:
        status: 筛选状态
        page: 页码
        page_size: 每页数量

    Returns:
        模组列表
    """
    try:
        offset = (page - 1) * page_size

        if status:
            query = GetModsByStatusQuery(
                query_id="get_mods_by_status",
                status=status,
                limit=page_size,
                offset=offset,
            )
        else:
            # 获取所有模组
            query = GetModsByStatusQuery(
                query_id="get_all_mods", status="all", limit=page_size, offset=offset
            )

        mods = query_service.handle_query(query)
        total = query_service.count_mods(status)

        result = PagedResultDTO(
            items=[mod.to_dict() for mod in mods],
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_previous=page > 1,
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"Failed to list mods: {e}")
        error = ErrorDTO.from_exception(e, "LIST_MODS_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.get("/search")
async def search_mods(
    q: str = Query(..., min_length=1),
    search_in: list[str] = Query(default=["name", "id"]),
    limit: int = Query(50, ge=1, le=100),
    query_service=Depends(get_query_service),
) -> list[dict[str, Any]]:
    """
    搜索模组

    Args:
        q: 搜索关键词
        search_in: 搜索字段
        limit: 返回数量限制

    Returns:
        搜索结果
    """
    try:
        query = SearchModsQuery(
            query_id="search_mods", search_term=q, search_in=search_in, limit=limit
        )

        results = query_service.handle_query(query)
        return [mod.to_dict() for mod in results]

    except Exception as e:
        logger.error(f"Failed to search mods: {e}")
        error = ErrorDTO.from_exception(e, "SEARCH_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.delete("/{mod_id}")
async def delete_mod(
    mod_id: str,
    delete_translations: bool = True,
    delete_from_projects: bool = True,
    mod_service=Depends(get_mod_service),
) -> dict[str, Any]:
    """
    删除模组

    Args:
        mod_id: 模组ID
        delete_translations: 是否删除翻译
        delete_from_projects: 是否从项目中移除

    Returns:
        删除结果
    """
    try:
        command = DeleteModCommand(
            command_id=f"delete_mod_{mod_id}",
            mod_id=mod_id,
            delete_translations=delete_translations,
            delete_from_projects=delete_from_projects,
        )

        success = mod_service.handle_command(command)
        if success:
            return {
                "status": "deleted",
                "mod_id": mod_id,
                "deleted_translations": delete_translations,
                "deleted_from_projects": delete_from_projects,
            }
        else:
            raise HTTPException(status_code=404, detail=f"Mod {mod_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete mod {mod_id}: {e}")
        error = ErrorDTO.from_exception(e, "DELETE_MOD_FAILED")
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.get("/{mod_id}/dependencies")
async def get_mod_dependencies(
    mod_id: str,
    include_optional: bool = True,
    resolve_transitive: bool = False,
    query_service=Depends(get_query_service),
) -> dict[str, Any]:
    """
    获取模组依赖

    Args:
        mod_id: 模组ID
        include_optional: 包含可选依赖
        resolve_transitive: 解析传递依赖

    Returns:
        依赖信息
    """
    try:
        # 这里应该调用实际的查询服务
        return {
            "mod_id": mod_id,
            "dependencies": [
                {"mod_id": "minecraft", "version": "1.20.1", "required": True},
                {"mod_id": "forge", "version": "47.1.0", "required": True},
            ],
            "optional_dependencies": []
            if not include_optional
            else [{"mod_id": "jei", "version": "15.2.0", "required": False}],
        }
    except Exception as e:
        logger.error(f"Failed to get dependencies for {mod_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mod_id}/stats")
async def get_mod_stats(
    mod_id: str, query_service=Depends(get_query_service)
) -> dict[str, Any]:
    """
    获取模组统计信息

    Args:
        mod_id: 模组ID

    Returns:
        统计信息
    """
    try:
        # 这里应该调用实际的统计服务
        return {
            "mod_id": mod_id,
            "total_keys": 500,
            "languages": {
                "zh_cn": {"translated": 450, "approved": 400, "progress": 90.0},
                "ja_jp": {"translated": 300, "approved": 250, "progress": 60.0},
            },
            "last_updated": "2025-09-06T16:00:00",
            "file_size": 1024000,
            "scan_count": 5,
        }
    except Exception as e:
        logger.error(f"Failed to get stats for {mod_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
