"""
同步协议服务层
集成数据库Repository，实现完整的数据同步逻辑
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog

from .models import SyncSession, EntryDelta
from .entry_delta import get_entry_delta_processor, MergeContext
from database.repositories.translation_entry_repository import TranslationEntryRepository, TranslationEntry
from database.repositories.language_file_repository import LanguageFileRepository
from database.core.manager import McL10nDatabaseManager

logger = structlog.get_logger(__name__)


class SyncProtocolService:
    """同步协议服务，集成数据库操作"""
    
    def __init__(self, db_manager: McL10nDatabaseManager):
        self.db_manager = db_manager
        self.translation_repo = TranslationEntryRepository(db_manager)
        self.language_file_repo = LanguageFileRepository(db_manager)
        self.entry_delta_processor = get_entry_delta_processor()
    
    async def get_server_cids(self, sync_scope: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        获取服务端CID列表
        
        Args:
            sync_scope: 同步范围限制，可以限制特定项目、MOD等
        """
        try:
            cids = []
            
            # 获取所有有UIDA的翻译条目
            entries = await self.translation_repo.find_by(limit=1000)  # 限制返回数量
            
            for entry in entries:
                if entry.uida_hash:
                    # 使用UIDA作为CID
                    cid = f"blake3:{entry.uida_hash}"
                    cids.append(cid)
            
            logger.info("获取服务端CID列表", 
                       total_cids=len(cids),
                       scope=sync_scope)
            
            return cids
            
        except Exception as e:
            logger.error("获取服务端CID失败", error=str(e))
            return []
    
    async def get_entry_deltas_by_cids(self, cids: List[str]) -> Dict[str, List[EntryDelta]]:
        """
        根据CID列表获取Entry-Delta数据
        
        Args:
            cids: CID列表
            
        Returns:
            Dict[cid, List[EntryDelta]]: CID到Entry-Delta列表的映射
        """
        cid_deltas = {}
        
        for cid in cids:
            try:
                # 从CID提取UIDA SHA256
                if cid.startswith("blake3:"):
                    uida_hash = cid[7:]  # 移除blake3:前缀
                    
                    # 查询对应的翻译条目
                    entries = await self.translation_repo.find_by_uida_hash(uida_hash)
                    
                    deltas = []
                    for entry in entries:
                        delta = self.entry_delta_processor.serialize_entry_delta(entry, "update")
                        deltas.append(delta)
                    
                    if deltas:
                        cid_deltas[cid] = deltas
                        
            except Exception as e:
                logger.error("获取Entry-Delta失败",
                           cid=cid,
                           error=str(e))
                continue
        
        logger.info("获取Entry-Delta完成",
                   requested_cids=len(cids),
                   found_cids=len(cid_deltas))
        
        return cid_deltas
    
    async def process_entry_deltas(
        self, 
        deltas: List[EntryDelta],
        merge_strategy: str = "3way",
        conflict_resolution: str = "mark_for_review"
    ) -> Dict[str, Any]:
        """
        处理Entry-Delta列表，执行合并和冲突处理
        
        Args:
            deltas: Entry-Delta列表
            merge_strategy: 合并策略
            conflict_resolution: 冲突处理策略
            
        Returns:
            处理结果统计
        """
        results = {
            "processed": 0,
            "merged": 0,
            "conflicts": 0,
            "errors": 0,
            "conflict_entries": [],
            "error_entries": []
        }
        
        for delta in deltas:
            try:
                results["processed"] += 1
                
                # 反序列化为翻译条目
                remote_entry = self.entry_delta_processor.deserialize_entry_delta(delta)
                
                # 查询现有条目 (本地版本)
                local_entry = None
                if delta.uida_hash:
                    existing_entries = await self.translation_repo.find_by_uida_hash(delta.uida_hash)
                    if existing_entries:
                        local_entry = existing_entries[0]
                
                # 创建合并上下文
                context = MergeContext(
                    base_entry=local_entry,  # 简化：使用local作为base
                    local_entry=local_entry,
                    remote_entry=remote_entry,
                    merge_strategy=merge_strategy,
                    conflict_resolution=conflict_resolution
                )
                
                # 执行3-way合并
                merge_result = self.entry_delta_processor.perform_3way_merge(context)
                
                if not merge_result.success:
                    results["errors"] += 1
                    results["error_entries"].append({
                        "entry_uid": delta.entry_uid,
                        "error": merge_result.error_message
                    })
                    continue
                
                if merge_result.has_conflict:
                    results["conflicts"] += 1
                    results["conflict_entries"].append({
                        "entry_uid": delta.entry_uid,
                        "uida_hash": delta.uida_hash,
                        "conflict_type": merge_result.conflict_type,
                        "conflict_details": merge_result.conflict_details
                    })
                
                # 保存合并结果
                if merge_result.merged_entry:
                    if local_entry:
                        # 更新现有条目
                        await self.translation_repo.update(merge_result.merged_entry)
                    else:
                        # 创建新条目
                        await self.translation_repo.create(merge_result.merged_entry)
                    
                    results["merged"] += 1
                
            except Exception as e:
                results["errors"] += 1
                results["error_entries"].append({
                    "entry_uid": delta.entry_uid,
                    "error": str(e)
                })
                logger.error("处理Entry-Delta失败",
                           entry_uid=delta.entry_uid,
                           error=str(e))
        
        logger.info("批量处理Entry-Delta完成",
                   processed=results["processed"],
                   merged=results["merged"],
                   conflicts=results["conflicts"],
                   errors=results["errors"])
        
        return results
    
    async def create_sync_session(
        self,
        client_id: str,
        session_id: Optional[str] = None,
        ttl_hours: int = 1
    ) -> SyncSession:
        """创建同步会话"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = SyncSession(
            session_id=session_id,
            client_id=client_id,
            status="active",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
            chunk_size_bytes=2097152,
            metadata={}
        )
        
        logger.info("创建同步会话",
                   session_id=session_id,
                   client_id=client_id,
                   expires_at=session.expires_at)
        
        return session
    
    async def validate_session(self, session_id: str) -> Optional[SyncSession]:
        """验证会话是否有效"""
        # TODO: 从数据库或缓存中获取会话
        # 这里暂时返回None，表示需要实现会话持久化
        logger.warning("会话验证未实现持久化", session_id=session_id)
        return None
    
    async def get_translation_statistics(self) -> Dict[str, Any]:
        """获取翻译统计信息"""
        try:
            stats = await self.translation_repo.get_translator_statistics()
            uida_stats = await self.translation_repo.get_uida_coverage_stats()
            
            return {
                "translation_stats": stats,
                "uida_coverage": uida_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("获取翻译统计失败", error=str(e))
            return {}
    
    async def find_similar_translations(
        self,
        src_text: str,
        uida_hash: Optional[str] = None,
        limit: int = 10
    ) -> List[TranslationEntry]:
        """查找相似翻译 (基于UIDA或文本相似性)"""
        try:
            if uida_hash:
                # 基于UIDA查找
                entries = await self.translation_repo.find_by_uida_hash(uida_hash)
                return entries[:limit]
            else:
                # 基于文本相似性查找
                entries = await self.translation_repo.find_similar_translations(
                    src_text, 
                    similarity_threshold=0.8
                )
                return entries[:limit]
                
        except Exception as e:
            logger.error("查找相似翻译失败", 
                        src_text=src_text[:50], 
                        uida_hash=uida_hash,
                        error=str(e))
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        # TODO: 实现会话清理逻辑
        logger.info("清理过期会话 (未实现)")
        return 0


# 全局服务实例
_sync_service: Optional[SyncProtocolService] = None


def get_sync_service() -> SyncProtocolService:
    """获取同步协议服务实例"""
    global _sync_service
    if _sync_service is None:
        from database.core.manager import get_database_manager
        db_manager = get_database_manager()
        _sync_service = SyncProtocolService(db_manager)
        logger.info("同步协议服务初始化完成")
    return _sync_service