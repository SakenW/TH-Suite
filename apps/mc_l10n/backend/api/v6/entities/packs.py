"""
V6 整合包管理API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.database.repositories.pack_repository import PackRepository
from apps.mc_l10n.backend.core.di_container import get_database_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v6/packs", tags=["整合包管理"])


class PackCreateRequest(BaseModel):
    platform: str = Field(..., regex=r"^(modrinth|curseforge|custom)$")
    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    author: Optional[str] = Field(None, max_length=100)
    homepage: Optional[str] = Field(None, max_length=500)


class PackVersionCreateRequest(BaseModel):
    pack_uid: str = Field(..., min_length=1)
    mc_version: str = Field(..., min_length=1, max_length=20)
    loader: str = Field(..., regex=r"^(forge|neoforge|fabric|quilt|multi|unknown)$")
    manifest_json: Dict[str, Any] = Field(...)


class PackInstallationCreateRequest(BaseModel):
    pack_version_uid: str = Field(..., min_length=1)
    root_path: Optional[str] = Field(None, max_length=500)
    launcher: Optional[str] = Field(None, regex=r"^(curseforge|modrinth|vanilla|custom)$")
    enabled: bool = Field(True)


def get_pack_repository(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> PackRepository:
    return PackRepository(db_manager)


@router.get("")
async def list_packs(
    platform: Optional[str] = Query(None, regex=r"^(modrinth|curseforge|custom)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """列出整合包"""
    try:
        conditions = {}
        if platform:
            conditions['platform'] = platform
            
        packs = await pack_repo.find_packs(conditions=conditions, limit=limit, offset=offset)
        total = await pack_repo.count_packs(conditions=conditions)
        
        return {
            "packs": packs,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error("列出整合包失败", error=str(e))
        raise HTTPException(status_code=500, detail="列出整合包失败")


@router.post("")
async def create_pack(
    pack_data: PackCreateRequest,
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """创建整合包"""
    try:
        pack = await pack_repo.create_pack(
            platform=pack_data.platform,
            slug=pack_data.slug,
            title=pack_data.title,
            author=pack_data.author,
            homepage=pack_data.homepage
        )
        return {"pack": pack}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建整合包失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建整合包失败")


@router.get("/{pack_uid}")
async def get_pack(
    pack_uid: str,
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """获取整合包详情"""
    try:
        pack = await pack_repo.get_pack_by_uid(pack_uid)
        if not pack:
            raise HTTPException(status_code=404, detail="整合包不存在")
        return {"pack": pack}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取整合包失败", pack_uid=pack_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取整合包失败")


@router.get("/{pack_uid}/versions")
async def list_pack_versions(
    pack_uid: str,
    mc_version: Optional[str] = Query(None),
    loader: Optional[str] = Query(None, regex=r"^(forge|neoforge|fabric|quilt|multi|unknown)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """列出整合包版本"""
    try:
        conditions = {"pack_uid": pack_uid}
        if mc_version:
            conditions["mc_version"] = mc_version
        if loader:
            conditions["loader"] = loader
            
        versions = await pack_repo.find_pack_versions(conditions=conditions, limit=limit, offset=offset)
        total = await pack_repo.count_pack_versions(conditions=conditions)
        
        return {
            "versions": versions,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error("列出整合包版本失败", pack_uid=pack_uid, error=str(e))
        raise HTTPException(status_code=500, detail="列出整合包版本失败")


@router.post("/versions")
async def create_pack_version(
    version_data: PackVersionCreateRequest,
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """创建整合包版本"""
    try:
        version = await pack_repo.create_pack_version(
            pack_uid=version_data.pack_uid,
            mc_version=version_data.mc_version,
            loader=version_data.loader,
            manifest_json=version_data.manifest_json
        )
        return {"version": version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建整合包版本失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建整合包版本失败")


@router.get("/{pack_uid}/installations")
async def list_pack_installations(
    pack_uid: str,
    enabled: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """列出整合包安装实例"""
    try:
        conditions = {"pack_uid": pack_uid}
        if enabled is not None:
            conditions["enabled"] = enabled
            
        installations = await pack_repo.find_pack_installations(conditions=conditions, limit=limit, offset=offset)
        total = await pack_repo.count_pack_installations(conditions=conditions)
        
        return {
            "installations": installations,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error("列出整合包安装实例失败", pack_uid=pack_uid, error=str(e))
        raise HTTPException(status_code=500, detail="列出整合包安装实例失败")


@router.post("/installations")
async def create_pack_installation(
    installation_data: PackInstallationCreateRequest,
    pack_repo: PackRepository = Depends(get_pack_repository)
) -> Dict[str, Any]:
    """创建整合包安装实例"""
    try:
        installation = await pack_repo.create_pack_installation(
            pack_version_uid=installation_data.pack_version_uid,
            root_path=installation_data.root_path,
            launcher=installation_data.launcher,
            enabled=installation_data.enabled
        )
        return {"installation": installation}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建整合包安装实例失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建整合包安装实例失败")