"""
V6 翻译条目管理API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.database.repositories.translation_entry_repository import TranslationEntryRepository
from apps.mc_l10n.backend.core.di_container import get_database_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v6/translations", tags=["翻译条目管理"])


class TranslationEntryCreateRequest(BaseModel):
    language_file_uid: str = Field(..., min_length=1)
    key: str = Field(..., min_length=1, max_length=500)
    src_text: str = Field(..., max_length=10000)
    dst_text: str = Field("", max_length=10000)
    status: str = Field("new", regex=r"^(new|mt|reviewed|locked|rejected|conflict)$")
    qa_flags: Optional[Dict[str, Any]] = Field(None)


class TranslationEntryUpdateRequest(BaseModel):
    dst_text: Optional[str] = Field(None, max_length=10000)
    status: Optional[str] = Field(None, regex=r"^(new|mt|reviewed|locked|rejected|conflict)$")
    qa_flags: Optional[Dict[str, Any]] = Field(None)


class BatchTranslationUpdate(BaseModel):
    entry_uid: str = Field(..., min_length=1)
    dst_text: Optional[str] = Field(None, max_length=10000)
    status: Optional[str] = Field(None, regex=r"^(new|mt|reviewed|locked|rejected|conflict)$")
    qa_flags: Optional[Dict[str, Any]] = Field(None)


def get_translation_entry_repository(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> TranslationEntryRepository:
    return TranslationEntryRepository(db_manager)


@router.get("")
async def list_translation_entries(
    language_file_uid: Optional[str] = Query(None),
    status: Optional[str] = Query(None, regex=r"^(new|mt|reviewed|locked|rejected|conflict)$"),
    key: Optional[str] = Query(None),
    search: Optional[str] = Query(None, min_length=1),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    after: Optional[str] = Query(None, description="游标分页：在指定entry_uid之后的条目"),
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """列出翻译条目"""
    try:
        conditions = {}
        if language_file_uid:
            conditions['language_file_uid'] = language_file_uid
        if status:
            conditions['status'] = status
        if key:
            conditions['key'] = key
            
        if search:
            # 支持搜索功能
            entries = await trans_repo.search_entries(
                search_term=search,
                language_file_uid=language_file_uid,
                limit=limit,
                offset=offset
            )
            total = await trans_repo.count_search_results(search, language_file_uid)
        elif after:
            # 游标分页
            entries = await trans_repo.find_entries_after_cursor(
                after_uid=after,
                conditions=conditions,
                limit=limit
            )
            total = None  # 游标分页不提供总数
        else:
            # 普通分页
            entries = await trans_repo.find_entries(conditions=conditions, limit=limit, offset=offset)
            total = await trans_repo.count_entries(conditions=conditions)
        
        pagination = {
            "limit": limit,
            "offset": offset if not after else None,
            "cursor": after,
            "has_more": len(entries) == limit
        }
        
        if total is not None:
            pagination["total"] = total
        
        return {
            "translation_entries": entries,
            "pagination": pagination
        }
    except Exception as e:
        logger.error("列出翻译条目失败", error=str(e))
        raise HTTPException(status_code=500, detail="列出翻译条目失败")


@router.post("")
async def create_translation_entry(
    entry_data: TranslationEntryCreateRequest,
    x_idempotency_key: Optional[str] = Header(None),
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """创建翻译条目"""
    try:
        entry = await trans_repo.create_entry(
            language_file_uid=entry_data.language_file_uid,
            key=entry_data.key,
            src_text=entry_data.src_text,
            dst_text=entry_data.dst_text,
            status=entry_data.status,
            qa_flags=entry_data.qa_flags or {}
        )
        return {"translation_entry": entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建翻译条目失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建翻译条目失败")


@router.get("/{entry_uid}")
async def get_translation_entry(
    entry_uid: str,
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """获取翻译条目详情"""
    try:
        entry = await trans_repo.get_entry_by_uid(entry_uid)
        if not entry:
            raise HTTPException(status_code=404, detail="翻译条目不存在")
        return {"translation_entry": entry}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取翻译条目失败", entry_uid=entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取翻译条目失败")


@router.put("/{entry_uid}")
async def update_translation_entry(
    entry_uid: str,
    update_data: TranslationEntryUpdateRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_idempotency_key: Optional[str] = Header(None),
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """更新翻译条目"""
    try:
        updates = {}
        if update_data.dst_text is not None:
            updates['dst_text'] = update_data.dst_text
        if update_data.status is not None:
            updates['status'] = update_data.status
        if update_data.qa_flags is not None:
            updates['qa_flags'] = update_data.qa_flags
            
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供更新数据")
        
        # TODO: 实现版本控制检查 (if_match)
        success = await trans_repo.update_entry(entry_uid, updates)
        if not success:
            raise HTTPException(status_code=404, detail="翻译条目不存在")
            
        # 返回更新后的条目
        entry = await trans_repo.get_entry_by_uid(entry_uid)
        return {"translation_entry": entry}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新翻译条目失败", entry_uid=entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail="更新翻译条目失败")


@router.delete("/{entry_uid}")
async def delete_translation_entry(
    entry_uid: str,
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """删除翻译条目"""
    try:
        success = await trans_repo.delete_entry(entry_uid)
        if not success:
            raise HTTPException(status_code=404, detail="翻译条目不存在")
        return {"message": "翻译条目删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除翻译条目失败", entry_uid=entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail="删除翻译条目失败")


@router.post("/batch")
async def batch_update_translations(
    updates: List[BatchTranslationUpdate],
    x_idempotency_key: Optional[str] = Header(None),
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """批量更新翻译条目"""
    try:
        if not updates:
            raise HTTPException(status_code=400, detail="更新列表不能为空")
            
        if len(updates) > 1000:
            raise HTTPException(status_code=400, detail="批量更新数量不能超过1000条")
        
        # 转换为内部格式
        update_data = []
        for update in updates:
            entry_updates = {}
            if update.dst_text is not None:
                entry_updates['dst_text'] = update.dst_text
            if update.status is not None:
                entry_updates['status'] = update.status
            if update.qa_flags is not None:
                entry_updates['qa_flags'] = update.qa_flags
                
            if entry_updates:
                update_data.append((update.entry_uid, entry_updates))
        
        results = await trans_repo.batch_update_entries(update_data)
        
        return {
            "updated_count": len([r for r in results if r]),
            "failed_count": len([r for r in results if not r]),
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("批量更新翻译条目失败", error=str(e))
        raise HTTPException(status_code=500, detail="批量更新翻译条目失败")


@router.get("/files/{file_uid}/progress")
async def get_translation_progress(
    file_uid: str,
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """获取语言文件的翻译进度"""
    try:
        progress = await trans_repo.get_progress_by_file(file_uid)
        return {"progress": progress}
    except Exception as e:
        logger.error("获取翻译进度失败", file_uid=file_uid, error=str(e))
        raise HTTPException(status_code=500, detail="获取翻译进度失败")


@router.get("/similar")
async def find_similar_entries(
    src_text: str = Query(..., min_length=1),
    language_file_uid: Optional[str] = Query(None),
    threshold: float = Query(0.8, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> Dict[str, Any]:
    """查找相似翻译条目"""
    try:
        similar_entries = await trans_repo.find_similar_entries(
            src_text=src_text,
            language_file_uid=language_file_uid,
            threshold=threshold,
            limit=limit
        )
        return {"similar_entries": similar_entries}
    except Exception as e:
        logger.error("查找相似翻译条目失败", error=str(e))
        raise HTTPException(status_code=500, detail="查找相似翻译条目失败")


def generate_ndjson_stream(entries: List[Dict[str, Any]]):
    """生成NDJSON流"""
    for entry in entries:
        yield json.dumps(entry, ensure_ascii=False) + '\n'


@router.get("/export/ndjson")
async def export_translations_ndjson(
    language_file_uid: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    trans_repo: TranslationEntryRepository = Depends(get_translation_entry_repository)
) -> StreamingResponse:
    """导出翻译条目为NDJSON格式"""
    try:
        conditions = {}
        if language_file_uid:
            conditions['language_file_uid'] = language_file_uid
        if status:
            conditions['status'] = status
            
        entries = await trans_repo.find_entries(
            conditions=conditions, 
            limit=limit, 
            offset=offset
        )
        
        return StreamingResponse(
            generate_ndjson_stream(entries),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": "attachment; filename=translations.ndjson",
                "X-TH-DB-Schema": "v6.0"
            }
        )
    except Exception as e:
        logger.error("导出翻译条目失败", error=str(e))
        raise HTTPException(status_code=500, detail="导出翻译条目失败")