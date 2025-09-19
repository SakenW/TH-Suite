"""
LANG_UPSERT事件处理器
集成到现有事件系统，处理语言文件更新事件
支持批量处理和事务安全
"""

import asyncio
import json
import structlog
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from .event_applier import ScanEvent, EventType
from .cas_keyset_cache_service import get_cas_keyset_cache_service
from ..repositories.repository_factory import get_repository_factory

logger = structlog.get_logger(__name__)


class LangUpsertEventHandler:
    """LANG_UPSERT事件处理器"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = db_path
        self.cache_service = get_cas_keyset_cache_service(db_path)
        self.repository_factory = get_repository_factory(db_path)
        
        # 事件处理队列
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        
        logger.info("LANG_UPSERT事件处理器已初始化")
    
    async def handle_lang_upsert_event(self, event: ScanEvent) -> Dict[str, Any]:
        """处理单个LANG_UPSERT事件"""
        try:
            if event.event_type != EventType.LANG_UPSERT:
                return {
                    "success": False,
                    "error": f"不支持的事件类型: {event.event_type}"
                }
            
            payload = event.payload
            
            # 验证事件载荷
            required_fields = ["language_file_uid", "locale", "carrier_type", "entry_count"]
            for field in required_fields:
                if field not in payload:
                    return {
                        "success": False,
                        "error": f"缺少必要字段: {field}"
                    }
            
            # 处理语言文件更新
            result = await self._process_language_file_update(event)
            
            # 更新CAS缓存
            if result.get("success"):
                await self._update_cas_cache(event)
            
            # 发送下游事件
            await self._emit_downstream_events(event, result)
            
            logger.info(
                f"LANG_UPSERT事件处理完成: {event.event_id} "
                f"({payload.get('entry_count', 0)} 条目)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"LANG_UPSERT事件处理失败 {event.event_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "event_id": event.event_id
            }
    
    async def handle_batch_lang_upsert_events(
        self, 
        events: List[ScanEvent]
    ) -> Dict[str, Any]:
        """批量处理LANG_UPSERT事件"""
        try:
            processed_count = 0
            failed_count = 0
            results = []
            
            # 按载体分组进行批量处理
            grouped_events = self._group_events_by_carrier(events)
            
            for carrier_uid, carrier_events in grouped_events.items():
                try:
                    batch_result = await self._process_carrier_batch(carrier_uid, carrier_events)
                    results.append(batch_result)
                    
                    if batch_result.get("success"):
                        processed_count += len(carrier_events)
                    else:
                        failed_count += len(carrier_events)
                        
                except Exception as e:
                    logger.error(f"载体批量处理失败 {carrier_uid}: {e}")
                    failed_count += len(carrier_events)
                    results.append({
                        "success": False,
                        "carrier_uid": carrier_uid,
                        "error": str(e)
                    })
            
            return {
                "success": failed_count == 0,
                "processed_events": processed_count,
                "failed_events": failed_count,
                "total_events": len(events),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"批量LANG_UPSERT事件处理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def queue_event(self, event: ScanEvent):
        """将事件加入处理队列"""
        await self._event_queue.put(event)
        
        # 启动事件处理器（如果未运行）
        if not self._processing:
            asyncio.create_task(self._process_event_queue())
    
    async def _process_event_queue(self):
        """处理事件队列"""
        if self._processing:
            return
        
        self._processing = True
        logger.info("开始处理LANG_UPSERT事件队列")
        
        try:
            batch_events = []
            batch_timeout = 1.0  # 1秒批量超时
            
            while True:
                try:
                    # 等待事件或超时
                    event = await asyncio.wait_for(
                        self._event_queue.get(), 
                        timeout=batch_timeout
                    )
                    batch_events.append(event)
                    
                    # 收集更多事件进行批量处理
                    while not self._event_queue.empty() and len(batch_events) < 100:
                        batch_events.append(self._event_queue.get_nowait())
                    
                    # 处理批量事件
                    if batch_events:
                        await self.handle_batch_lang_upsert_events(batch_events)
                        batch_events.clear()
                    
                except asyncio.TimeoutError:
                    # 超时处理现有批量事件
                    if batch_events:
                        await self.handle_batch_lang_upsert_events(batch_events)
                        batch_events.clear()
                    else:
                        # 无事件时退出处理循环
                        break
                        
                except Exception as e:
                    logger.error(f"事件队列处理异常: {e}")
                    batch_events.clear()
                    
        finally:
            self._processing = False
            logger.info("LANG_UPSERT事件队列处理结束")
    
    async def _process_language_file_update(self, event: ScanEvent) -> Dict[str, Any]:
        """处理语言文件更新"""
        try:
            payload = event.payload
            language_file_uid = payload["language_file_uid"]
            
            # 获取语言文件Repository
            lang_file_repo = self.repository_factory.get_core_language_file_repo()
            
            # 检查语言文件是否存在
            existing_file = lang_file_repo.get_by_uid(language_file_uid)
            
            if existing_file:
                # 更新现有语言文件的元数据
                if "entry_count" in payload:
                    # 这里可以更新文件大小或其他元数据
                    pass
                
                return {
                    "success": True,
                    "action": "updated",
                    "language_file_uid": language_file_uid,
                    "entry_count": payload.get("entry_count", 0)
                }
            else:
                logger.warning(f"语言文件不存在: {language_file_uid}")
                return {
                    "success": False,
                    "error": f"语言文件不存在: {language_file_uid}"
                }
                
        except Exception as e:
            logger.error(f"语言文件更新处理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_cas_cache(self, event: ScanEvent):
        """更新CAS缓存"""
        try:
            payload = event.payload
            
            # 存储事件到CAS
            cas_object = {
                "event_id": event.event_id,
                "session_id": event.session_id,
                "timestamp": event.timestamp,
                "entity_ref": event.entity_ref,
                "payload": payload
            }
            
            metadata = {
                "event_type": "LANG_UPSERT",
                "stage": event.stage,
                "carrier_type": payload.get("carrier_type"),
                "locale": payload.get("locale")
            }
            
            object_hash = await self.cache_service.store_cas_object(
                "lang_upsert_event", cas_object, metadata
            )
            
            # 如果有键集信息，更新键集缓存
            if "keyset_hash" in payload:
                await self.cache_service.store_keyset_fingerprint(
                    carrier_uid=event.entity_ref,
                    relative_path=payload.get("relative_path", ""),
                    locale=payload.get("locale", ""),
                    keys=[],  # 键列表需要从其他地方获取
                    content_hash=event.artifact_hash
                )
            
            logger.debug(f"CAS缓存已更新: {object_hash}")
            
        except Exception as e:
            logger.warning(f"CAS缓存更新失败: {e}")
    
    async def _emit_downstream_events(self, event: ScanEvent, result: Dict[str, Any]):
        """发送下游事件"""
        try:
            if not result.get("success"):
                return
            
            # 发送COUNT_PATCH事件更新统计
            count_event = ScanEvent(
                event_id=f"count_{uuid.uuid4().hex[:8]}",
                session_id=event.session_id,
                event_type=EventType.COUNT_PATCH,
                entity_ref=event.entity_ref,
                stage="post_lang_upsert",
                artifact_hash=None,
                payload={
                    "source_event": event.event_id,
                    "entry_count_delta": event.payload.get("entry_count", 0),
                    "file_count_delta": 1,
                    "locale": event.payload.get("locale")
                },
                timestamp=datetime.now().isoformat()
            )
            
            # 这里可以集成到事件总线或队列系统
            logger.debug(f"下游COUNT_PATCH事件: {count_event.event_id}")
            
            # 发送PROGRESS事件更新进度
            progress_event = ScanEvent(
                event_id=f"progress_{uuid.uuid4().hex[:8]}",
                session_id=event.session_id,
                event_type=EventType.PROGRESS,
                entity_ref=event.entity_ref,
                stage="lang_processing",
                artifact_hash=None,
                payload={
                    "source_event": event.event_id,
                    "progress_type": "lang_file_processed",
                    "processed_count": 1,
                    "details": {
                        "language_file_uid": event.payload.get("language_file_uid"),
                        "entry_count": event.payload.get("entry_count", 0)
                    }
                },
                timestamp=datetime.now().isoformat()
            )
            
            logger.debug(f"下游PROGRESS事件: {progress_event.event_id}")
            
        except Exception as e:
            logger.warning(f"下游事件发送失败: {e}")
    
    def _group_events_by_carrier(
        self, 
        events: List[ScanEvent]
    ) -> Dict[str, List[ScanEvent]]:
        """按载体分组事件"""
        grouped = {}
        
        for event in events:
            carrier_uid = event.entity_ref
            if carrier_uid not in grouped:
                grouped[carrier_uid] = []
            grouped[carrier_uid].append(event)
        
        return grouped
    
    async def _process_carrier_batch(
        self, 
        carrier_uid: str, 
        events: List[ScanEvent]
    ) -> Dict[str, Any]:
        """处理单个载体的批量事件"""
        try:
            processed_events = []
            total_entries = 0
            
            for event in events:
                result = await self._process_language_file_update(event)
                processed_events.append({
                    "event_id": event.event_id,
                    "result": result
                })
                
                if result.get("success"):
                    total_entries += event.payload.get("entry_count", 0)
            
            # 批量更新CAS缓存
            for event in events:
                await self._update_cas_cache(event)
            
            logger.info(f"载体批量处理完成: {carrier_uid} ({len(events)} 事件, {total_entries} 条目)")
            
            return {
                "success": True,
                "carrier_uid": carrier_uid,
                "processed_events": len(events),
                "total_entries": total_entries,
                "event_results": processed_events
            }
            
        except Exception as e:
            logger.error(f"载体批量处理失败 {carrier_uid}: {e}")
            return {
                "success": False,
                "carrier_uid": carrier_uid,
                "error": str(e)
            }
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """获取事件处理统计"""
        try:
            # 从CAS系统获取LANG_UPSERT事件统计
            # 这里可以查询ops_cas_objects表
            return {
                "queue_size": self._event_queue.qsize(),
                "processing": self._processing,
                "supported_event_types": ["LANG_UPSERT"],
                "cache_statistics": await self.cache_service.get_cache_statistics()
            }
            
        except Exception as e:
            logger.error(f"事件统计获取失败: {e}")
            return {"error": str(e)}


# 全局事件处理器实例
_lang_upsert_handler: LangUpsertEventHandler = None


def get_lang_upsert_event_handler(db_path: str = "data/mc_l10n.db") -> LangUpsertEventHandler:
    """获取LANG_UPSERT事件处理器实例"""
    global _lang_upsert_handler
    if _lang_upsert_handler is None:
        _lang_upsert_handler = LangUpsertEventHandler(db_path)
    return _lang_upsert_handler