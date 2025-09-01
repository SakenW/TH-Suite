from fastapi import APIRouter, Depends, HTTPException, Query

from packages.core.models import JobStatus
from packages.protocol.schemas import (
    JobResponse,
    WorkshopItem,
    WorkshopSearchRequest,
    WorkshopSearchResult,
    WorkshopSubscribeRequest,
)
from packages.protocol.websocket import WebSocketManager

from ..dependencies import get_websocket_manager, get_workshop_service
from ..services import WorkshopService

router = APIRouter()


@router.get("/", response_model=list[WorkshopItem])
async def list_workshop_items(
    subscribed_only: bool = Query(False, description="只显示已订阅的物品"),
    search: str | None = Query(None, description="搜索关键词"),
    category: str | None = Query(None, description="物品分类"),
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """获取 Workshop 物品列表"""
    try:
        items = await workshop_service.list_items(
            subscribed_only=subscribed_only, search=search, category=category
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}", response_model=WorkshopItem)
async def get_workshop_item(
    item_id: str, workshop_service: WorkshopService = Depends(get_workshop_service)
):
    """获取特定 Workshop 物品信息"""
    try:
        item = await workshop_service.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Workshop 物品未找到")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=WorkshopSearchResult)
async def search_workshop(
    request: WorkshopSearchRequest,
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """搜索 Steam Workshop"""
    try:
        result = await workshop_service.search_workshop(
            query=request.query,
            category=request.category,
            sort_by=request.sort_by,
            time_filter=request.time_filter,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscribe", response_model=JobResponse)
async def subscribe_workshop_item(
    request: WorkshopSubscribeRequest,
    workshop_service: WorkshopService = Depends(get_workshop_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """订阅 Workshop 物品"""
    try:
        job_id = await workshop_service.subscribe_item(
            item_id=request.item_id, auto_update=request.auto_update
        )

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "subscribe_workshop",
                "item_id": request.item_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe/{item_id}", response_model=JobResponse)
async def unsubscribe_workshop_item(
    item_id: str,
    remove_files: bool = Query(False, description="是否删除本地文件"),
    workshop_service: WorkshopService = Depends(get_workshop_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """取消订阅 Workshop 物品"""
    try:
        job_id = await workshop_service.unsubscribe_item(
            item_id=item_id, remove_files=remove_files
        )

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "unsubscribe_workshop",
                "item_id": item_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=JobResponse)
async def sync_workshop_items(
    force_update: bool = Query(False, description="强制更新所有物品"),
    workshop_service: WorkshopService = Depends(get_workshop_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """同步 Workshop 物品"""
    try:
        job_id = await workshop_service.sync_items(force_update=force_update)

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "sync_workshop",
                "force_update": force_update,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def list_workshop_collections(
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """获取 Workshop 合集列表"""
    try:
        collections = await workshop_service.list_collections()
        return collections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_id}")
async def get_workshop_collection(
    collection_id: str,
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """获取特定 Workshop 合集信息"""
    try:
        collection = await workshop_service.get_collection(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Workshop 合集未找到")
        return collection
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections/{collection_id}/subscribe", response_model=JobResponse)
async def subscribe_workshop_collection(
    collection_id: str,
    workshop_service: WorkshopService = Depends(get_workshop_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """订阅 Workshop 合集"""
    try:
        job_id = await workshop_service.subscribe_collection(collection_id)

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "subscribe_collection",
                "collection_id": collection_id,
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_workshop_status(
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """获取 Workshop 状态信息"""
    try:
        status = await workshop_service.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-updates", response_model=JobResponse)
async def check_workshop_updates(
    workshop_service: WorkshopService = Depends(get_workshop_service),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """检查 Workshop 物品更新"""
    try:
        job_id = await workshop_service.check_updates()

        # 通知前端任务开始
        await ws_manager.broadcast(
            {
                "type": "job_started",
                "job_id": job_id,
                "operation": "check_workshop_updates",
            }
        )

        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_workshop_categories(
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """获取 Workshop 分类列表"""
    try:
        categories = await workshop_service.get_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_workshop_tags(
    workshop_service: WorkshopService = Depends(get_workshop_service),
):
    """获取 Workshop 标签列表"""
    try:
        tags = await workshop_service.get_tags()
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
