"""
V6 MOD管理API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.database.repositories.mod_repository import ModRepository
from apps.mc_l10n.backend.core.di_container import get_database_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v6/mods", tags=["MOD管理"])


class ModCreateRequest(BaseModel):
    modid: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    homepage: Optional[str] = Field(None, max_length=500)


class ModVersionCreateRequest(BaseModel):
    mod_uid: str = Field(..., min_length=1)
    loader: str = Field(..., min_length=1, max_length=20)
    mc_version: str = Field(..., min_length=1, max_length=20)
    version: str = Field(..., min_length=1, max_length=50)
    meta_json: Optional[Dict[str, Any]] = Field(None)
    source: Optional[str] = Field(None, max_length=500)


def get_mod_repository(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> ModRepository:
    return ModRepository(db_manager)


@router.get("")
async def list_mods(
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    modid: Optional[str] = Query(None),
    slug: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """列出MOD"""
    try:
        conditions = {}
        if modid:
            conditions['modid'] = modid
        if slug:
            conditions['slug'] = slug
            
        if search:
            # 支持搜索功能
            mods = await mod_repo.search_mods(search, limit=limit, offset=offset)
            total = await mod_repo.count_search_results(search)
        else:
            mods = await mod_repo.find_mods(conditions=conditions, limit=limit, offset=offset)
            total = await mod_repo.count_mods(conditions=conditions)
        
        return {
            "mods": mods,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error("列出MOD失败", error=str(e))
        raise HTTPException(status_code=500, detail="列出MOD失败")


@router.post("")
async def create_mod(
    mod_data: ModCreateRequest,
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """创建MOD"""
    try:
        mod = await mod_repo.create_mod(
            modid=mod_data.modid,
            slug=mod_data.slug,
            name=mod_data.name,
            homepage=mod_data.homepage
        )
        return {"mod": mod}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建MOD失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建MOD失败")


@router.get("/{mod_uid}")
async def get_mod(
    mod_uid: str,
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """获取MOD详情"""
    try:
        mod = await mod_repo.get_mod_by_uid(mod_uid)
        if not mod:
            raise HTTPException(status_code=404, detail="MOD不存在")
        return {"mod": mod}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取MOD失败", mod_uid=mod_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取MOD失败")


@router.get("/{mod_uid}/versions")
async def list_mod_versions(
    mod_uid: str,
    loader: Optional[str] = Query(None),
    mc_version: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """列出MOD版本"""
    try:
        conditions = {"mod_uid": mod_uid}
        if loader:
            conditions["loader"] = loader
        if mc_version:
            conditions["mc_version"] = mc_version
        if version:
            conditions["version"] = version
            
        versions = await mod_repo.find_mod_versions(conditions=conditions, limit=limit, offset=offset)
        total = await mod_repo.count_mod_versions(conditions=conditions)
        
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
        logger.error("列出MOD版本失败", mod_uid=mod_uid, error=str(e))
        raise HTTPException(status_code=500, detail="列出MOD版本失败")


@router.post("/versions")
async def create_mod_version(
    version_data: ModVersionCreateRequest,
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """创建MOD版本"""
    try:
        version = await mod_repo.create_mod_version(
            mod_uid=version_data.mod_uid,
            loader=version_data.loader,
            mc_version=version_data.mc_version,
            version=version_data.version,
            meta_json=version_data.meta_json,
            source=version_data.source
        )
        return {"version": version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建MOD版本失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建MOD版本失败")


@router.get("/{mod_uid}/compatibility")
async def get_mod_compatibility(
    mod_uid: str,
    target_mc_version: Optional[str] = Query(None),
    target_loader: Optional[str] = Query(None),
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """获取MOD兼容性矩阵"""
    try:
        compatibility = await mod_repo.get_compatibility_matrix(
            mod_uid=mod_uid,
            target_mc_version=target_mc_version,
            target_loader=target_loader
        )
        return {"compatibility": compatibility}
    except Exception as e:
        logger.error("获取MOD兼容性失败", mod_uid=mod_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取MOD兼容性失败")


@router.get("/search/similar")
async def find_similar_mods(
    name: str = Query(..., min_length=1),
    threshold: float = Query(0.8, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    mod_repo: ModRepository = Depends(get_mod_repository)
) -> Dict[str, Any]:
    """查找相似MOD"""
    try:
        similar_mods = await mod_repo.find_similar_mods(
            name=name,
            threshold=threshold,
            limit=limit
        )
        return {"similar_mods": similar_mods}
    except Exception as e:
        logger.error("查找相似MOD失败", name=name, error=str(e))
        raise HTTPException(status_code=500, detail="查找相似MOD失败")