from typing import Any

import structlog
from mc_l10n.application.services.local_entry_service import LocalEntryService
from mc_l10n.application.services.mapping_link_service import MappingLinkService
from mc_l10n.application.services.mapping_plan_service import MappingPlanService
from mc_l10n.application.services.sync_queue_service import SyncQueueService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from packages.backend_kit.dependencies import get_database_dependency

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/local", tags=["Local Data Management"])

# ==================== Pydantic Models ====================


class LocalEntryCreate(BaseModel):
    source_file: str = Field(..., description="源文件路径")
    namespace: str = Field(..., description="命名空间")
    keys_sha256_hex: str = Field(..., description="键的SHA256哈希")
    lang_mc: str = Field(..., description="Minecraft语言代码")
    content: dict[str, Any] = Field(..., description="内容数据")


class LocalEntryUpdate(BaseModel):
    source_file: str | None = Field(None, description="源文件路径")
    namespace: str | None = Field(None, description="命名空间")
    content: dict[str, Any] | None = Field(None, description="内容数据")


class MappingPlanCreate(BaseModel):
    proposed_namespace: str = Field(..., description="建议的命名空间")
    lang_mc: str = Field(..., description="Minecraft语言代码")
    keys_structure: dict[str, Any] = Field(..., description="键结构")
    plan_state: str = Field("draft", description="计划状态")
    notes: str | None = Field(None, description="备注")


class ImportScanRequest(BaseModel):
    inventory_file: str = Field(..., description="扫描结果文件路径")
    project_id: str = Field("minecraft", description="项目ID")


class MappingPlanUpdate(BaseModel):
    proposed_namespace: str | None = Field(None, description="建议的命名空间")
    keys_structure: dict[str, Any] | None = Field(None, description="键结构")
    plan_state: str | None = Field(None, description="计划状态")
    notes: str | None = Field(None, description="备注")


class OutboundQueueCreate(BaseModel):
    plan_id: int = Field(..., description="映射计划ID")
    intent: str = Field(..., description="意图：upsert或delete")
    submit_payload: dict[str, Any] = Field(..., description="提交载荷")
    base_etag: str | None = Field(None, description="基础ETag")


class OutboundQueueUpdate(BaseModel):
    queue_state: str | None = Field(None, description="队列状态")
    result_message: str | None = Field(None, description="结果消息")
    server_content_id: str | None = Field(None, description="服务器内容ID")


class InboundSnapshotCreate(BaseModel):
    snapshot_id: str = Field(..., description="快照ID")
    project_id: str = Field(..., description="项目ID")
    from_snapshot_id: str | None = Field(None, description="来源快照ID")


class InboundItemCreate(BaseModel):
    server_content_id: str = Field(..., description="服务器内容ID")
    namespace: str = Field(..., description="命名空间")
    keys_sha256_hex: str = Field(..., description="键的SHA256哈希")
    lang_mc: str = Field(..., description="Minecraft语言代码")
    server_payload: dict[str, Any] = Field(..., description="服务器载荷")
    etag: str | None = Field(None, description="ETag")
    updated_at: str | None = Field(None, description="更新时间")


class MappingLinkCreate(BaseModel):
    local_entry_id: int = Field(..., description="本地条目ID")
    server_content_id: str = Field(..., description="服务器内容ID")
    link_state: str = Field("active", description="链接状态")


# ==================== Dependency Functions ====================


def get_local_entry_service(db=Depends(get_database_dependency)):
    return LocalEntryService(db)


def get_mapping_plan_service(db=Depends(get_database_dependency)):
    return MappingPlanService(db)


def get_sync_queue_service(db=Depends(get_database_dependency)):
    return SyncQueueService(db)


def get_mapping_link_service(db=Depends(get_database_dependency)):
    return MappingLinkService(db)


# ==================== Local Entries Routes ====================


@router.post("/entries", response_model=dict[str, Any])
def create_local_entry(
    entry: LocalEntryCreate,
    service: LocalEntryService = Depends(get_local_entry_service),
):
    """创建本地条目"""
    try:
        entry_id = service.create_local_entry(
            source_file=entry.source_file,
            namespace=entry.namespace,
            keys_sha256_hex=entry.keys_sha256_hex,
            lang_mc=entry.lang_mc,
            content=entry.content,
        )
        return {"entry_id": entry_id, "message": "Local entry created successfully"}
    except Exception as e:
        logger.error(f"Failed to create local entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries/statistics", response_model=dict[str, Any])
def get_local_entries_statistics(
    service: LocalEntryService = Depends(get_local_entry_service),
):
    """获取本地条目统计信息"""
    try:
        stats = service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get local entries statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries/{entry_id}", response_model=dict[str, Any])
def get_local_entry(
    entry_id: int, service: LocalEntryService = Depends(get_local_entry_service)
):
    """获取本地条目"""
    try:
        entry = service.get_local_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Local entry not found")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get local entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries", response_model=list[dict[str, Any]])
def list_local_entries(
    namespace: str | None = Query(None, description="命名空间过滤"),
    lang_mc: str | None = Query(None, description="语言代码过滤"),
    source_file: str | None = Query(None, description="源文件过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: LocalEntryService = Depends(get_local_entry_service),
):
    """列出本地条目"""
    try:
        entries = service.list_local_entries(
            namespace=namespace,
            lang_mc=lang_mc,
            source_file=source_file,
            limit=limit,
            offset=offset,
        )
        return entries
    except Exception as e:
        logger.error(f"Failed to list local entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entries/{entry_id}", response_model=dict[str, Any])
def update_local_entry(
    entry_id: int,
    entry: LocalEntryUpdate,
    service: LocalEntryService = Depends(get_local_entry_service),
):
    """更新本地条目"""
    try:
        updated = service.update_local_entry(
            entry_id=entry_id,
            source_file=entry.source_file,
            namespace=entry.namespace,
            content=entry.content,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Local entry not found")
        return {"message": "Local entry updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update local entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entries/{entry_id}", response_model=dict[str, Any])
def delete_local_entry(
    entry_id: int, service: LocalEntryService = Depends(get_local_entry_service)
):
    """删除本地条目"""
    try:
        deleted = service.delete_local_entry(entry_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Local entry not found")
        return {"message": "Local entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete local entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entries/import-scan", response_model=dict[str, Any])
def import_scan_results(
    request: ImportScanRequest,
    service: LocalEntryService = Depends(get_local_entry_service),
):
    """导入扫描结果到本地数据库"""
    try:
        import json
        from pathlib import Path

        inventory_path = Path(request.inventory_file)
        if not inventory_path.exists():
            raise HTTPException(status_code=404, detail="Inventory file not found")

        # 读取扫描结果文件
        with open(inventory_path, encoding="utf-8") as f:
            inventory_data = json.load(f)

        items = inventory_data.get("items", [])
        imported_count = 0

        for item in items:
            try:
                # 创建本地条目
                entry_id = service.create_entry(
                    project_id=request.project_id,
                    source_type="mod",  # 默认为mod类型
                    source_file=item.get("path", ""),
                    source_locator=item.get("locale", ""),
                    source_lang_bcp47=item.get("locale", ""),
                    source_context={
                        "modid": item.get("modid", ""),
                        "namespace": item.get("modid", ""),
                        "format": item.get("format", "json"),
                    },
                    source_payload={
                        "hash": item.get("hash", ""),
                        "size": item.get("size", 0),
                        "locale": item.get("locale", ""),
                    },
                    note=f"Imported from scan: {request.inventory_file}",
                )
                imported_count += 1
                logger.info(
                    f"Imported entry {entry_id} for {item.get('modid', 'unknown')}:{item.get('locale', 'unknown')}"
                )
            except Exception as e:
                logger.warning(f"Failed to import item {item}: {e}")
                continue

        return {
            "message": f"Successfully imported {imported_count} entries from scan results",
            "imported_count": imported_count,
            "total_items": len(items),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import scan results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Mapping Plans Routes ====================


@router.post("/mapping-plans", response_model=dict[str, Any])
def create_mapping_plan(
    plan: MappingPlanCreate,
    service: MappingPlanService = Depends(get_mapping_plan_service),
):
    """创建映射计划"""
    try:
        plan_id = service.create_plan(
            local_id=1,  # TODO: 从请求中获取实际的local_id
            proposed_namespace=plan.proposed_namespace,
            proposed_keys=plan.keys_structure,
            lang_mc=plan.lang_mc,
            validation_state=plan.plan_state,
        )
        return {"plan_id": plan_id, "message": "Mapping plan created successfully"}
    except Exception as e:
        logger.error(f"Failed to create mapping plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping-plans/{plan_id}", response_model=dict[str, Any])
def get_mapping_plan(
    plan_id: int, service: MappingPlanService = Depends(get_mapping_plan_service)
):
    """获取映射计划"""
    try:
        plan = service.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Mapping plan not found")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mapping plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping-plans", response_model=list[dict[str, Any]])
def list_mapping_plans(
    plan_state: str | None = Query(None, description="计划状态过滤"),
    lang_mc: str | None = Query(None, description="语言代码过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: MappingPlanService = Depends(get_mapping_plan_service),
):
    """列出映射计划"""
    try:
        plans = service.list_plans(
            validation_state=plan_state, limit=limit, offset=offset
        )
        return plans
    except Exception as e:
        logger.error(f"Failed to list mapping plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mapping-plans/{plan_id}", response_model=dict[str, Any])
def update_mapping_plan(
    plan_id: int,
    plan: MappingPlanUpdate,
    service: MappingPlanService = Depends(get_mapping_plan_service),
):
    """更新映射计划"""
    try:
        updated = service.update_plan(
            plan_id=plan_id,
            proposed_namespace=plan.proposed_namespace,
            proposed_keys=plan.keys_structure,
            validation_state=plan.plan_state,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Mapping plan not found")
        return {"message": "Mapping plan updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update mapping plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mapping-plans/{plan_id}", response_model=dict[str, Any])
def delete_mapping_plan(
    plan_id: int, service: MappingPlanService = Depends(get_mapping_plan_service)
):
    """删除映射计划"""
    try:
        deleted = service.delete_plan(plan_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Mapping plan not found")
        return {"message": "Mapping plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete mapping plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Sync Queue Routes ====================


@router.post("/outbound-queue", response_model=dict[str, Any])
def create_outbound_item(
    item: OutboundQueueCreate,
    service: SyncQueueService = Depends(get_sync_queue_service),
):
    """创建出站队列项"""
    try:
        queue_id = service.create_outbound_item(
            plan_id=item.plan_id,
            intent=item.intent,
            submit_payload=item.submit_payload,
            base_etag=item.base_etag,
        )
        return {
            "queue_id": queue_id,
            "message": "Outbound queue item created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create outbound queue item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outbound-queue/{queue_id}", response_model=dict[str, Any])
def get_outbound_item(
    queue_id: int, service: SyncQueueService = Depends(get_sync_queue_service)
):
    """获取出站队列项"""
    try:
        item = service.get_outbound_item(queue_id)
        if not item:
            raise HTTPException(status_code=404, detail="Outbound queue item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get outbound queue item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outbound-queue", response_model=list[dict[str, Any]])
def list_outbound_items(
    queue_state: str | None = Query(None, description="队列状态过滤"),
    intent: str | None = Query(None, description="意图过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: SyncQueueService = Depends(get_sync_queue_service),
):
    """列出出站队列项"""
    try:
        items = service.list_outbound_items(
            queue_state=queue_state, intent=intent, limit=limit, offset=offset
        )
        return items
    except Exception as e:
        logger.error(f"Failed to list outbound queue items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/outbound-queue/{queue_id}", response_model=dict[str, Any])
def update_outbound_item(
    queue_id: int,
    item: OutboundQueueUpdate,
    service: SyncQueueService = Depends(get_sync_queue_service),
):
    """更新出站队列项"""
    try:
        updated = service.update_outbound_item(
            queue_id=queue_id,
            queue_state=item.queue_state,
            result_message=item.result_message,
            server_content_id=item.server_content_id,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Outbound queue item not found")
        return {"message": "Outbound queue item updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update outbound queue item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-statistics", response_model=dict[str, Any])
def get_queue_statistics(service: SyncQueueService = Depends(get_sync_queue_service)):
    """获取队列统计信息"""
    try:
        stats = service.get_queue_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Mapping Links Routes ====================


@router.post("/mapping-links", response_model=dict[str, Any])
def create_mapping_link(
    link: MappingLinkCreate,
    service: MappingLinkService = Depends(get_mapping_link_service),
):
    """创建映射链接"""
    try:
        link_id = service.create_mapping_link(
            local_entry_id=link.local_entry_id,
            server_content_id=link.server_content_id,
            link_state=link.link_state,
        )
        return {"link_id": link_id, "message": "Mapping link created successfully"}
    except Exception as e:
        logger.error(f"Failed to create mapping link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping-links/{link_id}", response_model=dict[str, Any])
def get_mapping_link(
    link_id: int, service: MappingLinkService = Depends(get_mapping_link_service)
):
    """获取映射链接"""
    try:
        link = service.get_mapping_link(link_id)
        if not link:
            raise HTTPException(status_code=404, detail="Mapping link not found")
        return link
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mapping link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping-links", response_model=list[dict[str, Any]])
def list_mapping_links(
    link_state: str | None = Query(None, description="链接状态过滤"),
    namespace: str | None = Query(None, description="命名空间过滤"),
    lang_mc: str | None = Query(None, description="语言代码过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: MappingLinkService = Depends(get_mapping_link_service),
):
    """列出映射链接"""
    try:
        links = service.list_mapping_links(
            link_state=link_state,
            namespace=namespace,
            lang_mc=lang_mc,
            limit=limit,
            offset=offset,
        )
        return links
    except Exception as e:
        logger.error(f"Failed to list mapping links: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping-links/unmapped", response_model=list[dict[str, Any]])
def get_unmapped_entries(
    namespace: str | None = Query(None, description="命名空间过滤"),
    lang_mc: str | None = Query(None, description="语言代码过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    service: MappingLinkService = Depends(get_mapping_link_service),
):
    """获取未映射的本地条目"""
    try:
        entries = service.get_unmapped_local_entries(
            namespace=namespace, lang_mc=lang_mc, limit=limit
        )
        return entries
    except Exception as e:
        logger.error(f"Failed to get unmapped entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping-links/statistics", response_model=dict[str, Any])
def get_mapping_statistics(
    service: MappingLinkService = Depends(get_mapping_link_service),
):
    """获取映射统计信息"""
    try:
        stats = service.get_mapping_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get mapping statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
