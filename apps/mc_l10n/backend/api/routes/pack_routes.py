"""
整合包管理相关路由
提供整合包的创建、配置和管理功能
V5架构 - 集成Repository模式
"""

import logging
from typing import Any, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from infrastructure.repositories.repository_factory import get_repository_factory, RepositoryFactory
from infrastructure.repositories.core_pack_repository import CorePack, PackPlatform

logger = logging.getLogger(__name__)

def get_repo_factory() -> RepositoryFactory:
    """依赖注入：获取Repository工厂"""
    return get_repository_factory()

router = APIRouter(
    prefix="/api/v1/packs",
    tags=["整合包管理"],
    responses={404: {"description": "Not found"}},
)


class PackCreateRequest(BaseModel):
    """创建整合包请求模型"""
    platform: str = "custom"  # modrinth, curseforge, custom
    slug: str
    title: str
    author: str | None = None
    homepage: str | None = None


class PackResponse(BaseModel):
    """整合包响应模型"""
    uid: str
    platform: str
    slug: str
    title: str
    author: str | None = None
    homepage: str | None = None
    created_at: str
    updated_at: str


class PackListResponse(BaseModel):
    """整合包列表响应模型"""
    packs: List[PackResponse]
    total: int


@router.get("/test", response_model=dict[str, Any])
async def pack_test_endpoint():
    """
    整合包路由测试端点
    """
    return {
        "success": True,
        "message": "Pack routes are working",
        "service": "pack-management",
        "endpoints_available": [
            "GET /api/v1/packs/test",
            "GET /api/v1/packs/",
            "POST /api/v1/packs/",
            "GET /api/v1/packs/{pack_uid}",
            "GET /api/v1/packs/platform/{platform}",
        ],
    }


@router.get("", response_model=dict[str, Any])
@router.get("/", response_model=dict[str, Any])
async def list_packs(
    limit: int = 50,
    offset: int = 0,
    platform: str | None = None,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取整合包列表

    Args:
        limit: 限制数量
        offset: 偏移量
        platform: 平台过滤（可选）
    """
    try:
        pack_repo = factory.get_core_pack_repo()
        
        if platform:
            try:
                platform_enum = PackPlatform(platform)
                packs = pack_repo.list_by_platform(platform_enum)
                total = len(packs)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的平台类型: {platform}")
        else:
            packs = pack_repo.list_all(limit=limit, offset=offset)
            total = pack_repo.count()
        
        pack_responses = [
            PackResponse(
                uid=pack.uid,
                platform=pack.platform.value,
                slug=pack.slug,
                title=pack.title,
                author=pack.author,
                homepage=pack.homepage,
                created_at=pack.created_at or "",
                updated_at=pack.updated_at or ""
            )
            for pack in packs
        ]
        
        return {
            "success": True,
            "data": {
                "packs": [p.dict() for p in pack_responses],
                "total": total
            },
            "message": "整合包列表获取成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取整合包列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict[str, Any])
@router.post("/", response_model=dict[str, Any])
async def create_pack(
    pack_data: PackCreateRequest,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    创建新整合包

    Args:
        pack_data: 整合包创建信息
    """
    try:
        pack_repo = factory.get_core_pack_repo()
        
        # 验证平台类型
        try:
            platform_enum = PackPlatform(pack_data.platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的平台类型: {pack_data.platform}")
        
        # 检查slug是否已存在
        existing = pack_repo.get_by_slug(platform_enum, pack_data.slug)
        if existing:
            raise HTTPException(
                status_code=409, 
                detail=f"整合包已存在: {pack_data.platform}/{pack_data.slug}"
            )
        
        # 创建新整合包
        new_pack = CorePack(
            uid="",  # Repository会自动生成
            platform=platform_enum,
            slug=pack_data.slug,
            title=pack_data.title,
            author=pack_data.author,
            homepage=pack_data.homepage
        )
        
        pack_uid = pack_repo.create(new_pack)
        created_pack = pack_repo.get_by_uid(pack_uid)
        
        if not created_pack:
            raise HTTPException(status_code=500, detail="整合包创建失败")
        
        response = PackResponse(
            uid=created_pack.uid,
            platform=created_pack.platform.value,
            slug=created_pack.slug,
            title=created_pack.title,
            author=created_pack.author,
            homepage=created_pack.homepage,
            created_at=created_pack.created_at or "",
            updated_at=created_pack.updated_at or ""
        )

        return {
            "success": True,
            "data": response.dict(),
            "message": f"整合包创建成功: {pack_data.title}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建整合包失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pack_uid}", response_model=dict[str, Any])
async def get_pack_info(
    pack_uid: str,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取指定整合包的详细信息

    Args:
        pack_uid: 整合包UID
    """
    try:
        pack_repo = factory.get_core_pack_repo()
        
        # 获取整合包信息
        pack = pack_repo.get_by_uid(pack_uid)
        if not pack:
            raise HTTPException(status_code=404, detail=f"整合包不存在: {pack_uid}")
        
        response = PackResponse(
            uid=pack.uid,
            platform=pack.platform.value,
            slug=pack.slug,
            title=pack.title,
            author=pack.author,
            homepage=pack.homepage,
            created_at=pack.created_at or "",
            updated_at=pack.updated_at or ""
        )

        return {
            "success": True,
            "data": {
                **response.dict(),
                "statistics": {
                    "total_versions": 0,  # TODO: 实现版本统计
                    "total_mods": 0,      # TODO: 实现MOD统计
                    "total_content": 0,   # TODO: 实现内容统计
                },
            },
            "message": f"整合包信息获取成功: {pack.title}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取整合包信息失败 {pack_uid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/{platform}", response_model=dict[str, Any])
async def list_packs_by_platform(
    platform: str,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    按平台获取整合包列表

    Args:
        platform: 平台类型 (modrinth, curseforge, custom)
    """
    try:
        pack_repo = factory.get_core_pack_repo()
        
        try:
            platform_enum = PackPlatform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的平台类型: {platform}")
        
        packs = pack_repo.list_by_platform(platform_enum)
        
        pack_responses = [
            PackResponse(
                uid=pack.uid,
                platform=pack.platform.value,
                slug=pack.slug,
                title=pack.title,
                author=pack.author,
                homepage=pack.homepage,
                created_at=pack.created_at or "",
                updated_at=pack.updated_at or ""
            )
            for pack in packs
        ]
        
        return {
            "success": True,
            "data": {
                "packs": [p.dict() for p in pack_responses],
                "total": len(pack_responses),
                "platform": platform
            },
            "message": f"{platform}平台整合包列表获取成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取{platform}平台整合包列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/platforms", response_model=dict[str, Any])
async def get_platform_stats(
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取按平台统计的整合包数量
    """
    try:
        pack_repo = factory.get_core_pack_repo()
        stats = pack_repo.get_stats_by_platform()
        
        return {
            "success": True,
            "data": {
                "platform_stats": stats,
                "total_platforms": len(stats)
            },
            "message": "平台统计信息获取成功",
        }
    except Exception as e:
        logger.error(f"获取平台统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))