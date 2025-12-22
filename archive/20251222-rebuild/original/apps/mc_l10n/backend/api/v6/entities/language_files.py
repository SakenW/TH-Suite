"""
V6 语言文件管理API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.database.repositories.language_file_repository import LanguageFileRepository
from apps.mc_l10n.backend.core.di_container import get_database_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/language-files", tags=["语言文件管理"])


class LanguageFileCreateRequest(BaseModel):
    carrier_type: str = Field(..., pattern=r"^(mod|resource_pack|data_pack|override)$")
    carrier_uid: str = Field(..., min_length=1)
    locale: str = Field(..., min_length=2, max_length=10)
    rel_path: str = Field(..., min_length=1, max_length=500)
    format: str = Field(..., pattern=r"^(json|lang|properties)$")
    size: int = Field(0, ge=0)


class LanguageFileUpdateRequest(BaseModel):
    size: Optional[int] = Field(None, ge=0)


def get_language_file_repository(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> LanguageFileRepository:
    return LanguageFileRepository(db_manager)


@router.get("")
async def list_language_files(
    carrier_type: Optional[str] = Query(None, pattern=r"^(mod|resource_pack|data_pack|override)$"),
    carrier_uid: Optional[str] = Query(None),
    locale: Optional[str] = Query(None),
    format: Optional[str] = Query(None, pattern=r"^(json|lang|properties)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """列出语言文件"""
    try:
        conditions = {}
        if carrier_type:
            conditions['carrier_type'] = carrier_type
        if carrier_uid:
            conditions['carrier_uid'] = carrier_uid
        if locale:
            conditions['locale'] = locale
        if format:
            conditions['format'] = format
            
        files = await lang_file_repo.find_language_files(conditions=conditions, limit=limit, offset=offset)
        total = await lang_file_repo.count_language_files(conditions=conditions)
        
        return {
            "language_files": files,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error("列出语言文件失败", error=str(e))
        raise HTTPException(status_code=500, detail="列出语言文件失败")


@router.post("")
async def create_language_file(
    file_data: LanguageFileCreateRequest,
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """创建语言文件"""
    try:
        language_file = await lang_file_repo.create_language_file(
            carrier_type=file_data.carrier_type,
            carrier_uid=file_data.carrier_uid,
            locale=file_data.locale,
            rel_path=file_data.rel_path,
            format=file_data.format,
            size=file_data.size
        )
        return {"language_file": language_file}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建语言文件失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建语言文件失败")


@router.get("/{file_uid}")
async def get_language_file(
    file_uid: str,
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """获取语言文件详情"""
    try:
        language_file = await lang_file_repo.get_language_file_by_uid(file_uid)
        if not language_file:
            raise HTTPException(status_code=404, detail="语言文件不存在")
        return {"language_file": language_file}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取语言文件失败", file_uid=file_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取语言文件失败")


@router.put("/{file_uid}")
async def update_language_file(
    file_uid: str,
    update_data: LanguageFileUpdateRequest,
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """更新语言文件"""
    try:
        updates = {}
        if update_data.size is not None:
            updates['size'] = update_data.size
            
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供更新数据")
            
        success = await lang_file_repo.update_language_file(file_uid, updates)
        if not success:
            raise HTTPException(status_code=404, detail="语言文件不存在")
            
        # 返回更新后的文件
        language_file = await lang_file_repo.get_language_file_by_uid(file_uid)
        return {"language_file": language_file}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新语言文件失败", file_uid=file_uid, error=str(e))
        raise HTTPException(status_code=500, detail="更新语言文件失败")


@router.delete("/{file_uid}")
async def delete_language_file(
    file_uid: str,
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """删除语言文件"""
    try:
        success = await lang_file_repo.delete_language_file(file_uid)
        if not success:
            raise HTTPException(status_code=404, detail="语言文件不存在")
        return {"message": "语言文件删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除语言文件失败", file_uid=file_uid, error=str(e))
        raise HTTPException(status_code=500, detail="删除语言文件失败")


@router.get("/carriers/{carrier_uid}/coverage")
async def get_coverage_stats(
    carrier_uid: str,
    carrier_type: str = Query(..., pattern=r"^(mod|resource_pack|data_pack|override)$"),
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """获取语言覆盖率统计"""
    try:
        coverage = await lang_file_repo.get_coverage_statistics(
            carrier_type=carrier_type,
            carrier_uid=carrier_uid
        )
        return {"coverage": coverage}
    except Exception as e:
        logger.error("获取覆盖率统计失败", carrier_uid=carrier_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取覆盖率统计失败")


@router.get("/batch")
async def batch_get_language_files(
    carrier_uids: str = Query(..., description="逗号分隔的carrier_uid列表"),
    carrier_type: str = Query(..., pattern=r"^(mod|resource_pack|data_pack|override)$"),
    locale: Optional[str] = Query(None),
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """批量获取语言文件"""
    try:
        uid_list = [uid.strip() for uid in carrier_uids.split(',') if uid.strip()]
        if not uid_list:
            raise HTTPException(status_code=400, detail="carrier_uids不能为空")
        
        if len(uid_list) > 100:
            raise HTTPException(status_code=400, detail="carrier_uids数量不能超过100个")
        
        files = await lang_file_repo.batch_get_by_carriers(
            carrier_type=carrier_type,
            carrier_uids=uid_list,
            locale=locale
        )
        return {"language_files": files}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("批量获取语言文件失败", error=str(e))
        raise HTTPException(status_code=500, detail="批量获取语言文件失败")


@router.get("/locales")
async def list_available_locales(
    carrier_type: Optional[str] = Query(None, pattern=r"^(mod|resource_pack|data_pack|override)$"),
    carrier_uid: Optional[str] = Query(None),
    lang_file_repo: LanguageFileRepository = Depends(get_language_file_repository)
) -> Dict[str, Any]:
    """列出可用的语言区域"""
    try:
        conditions = {}
        if carrier_type:
            conditions['carrier_type'] = carrier_type
        if carrier_uid:
            conditions['carrier_uid'] = carrier_uid
            
        locales = await lang_file_repo.get_available_locales(conditions)
        return {"locales": locales}
    except Exception as e:
        logger.error("获取可用语言区域失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取可用语言区域失败")