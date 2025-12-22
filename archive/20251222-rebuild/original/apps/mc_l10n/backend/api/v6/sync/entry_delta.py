"""
Entry-Delta 处理器
处理键级差量数据的序列化、反序列化和合并
"""

import json
import hashlib
import blake3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import structlog

from .models import EntryDelta
from database.repositories.translation_entry_repository import TranslationEntry, TranslationEntryRepository
from services.content_addressing import compute_cid, HashAlgorithm

logger = structlog.get_logger(__name__)


@dataclass
class MergeContext:
    """合并上下文信息"""
    base_entry: Optional[TranslationEntry] = None  # 基础版本
    local_entry: Optional[TranslationEntry] = None  # 本地版本  
    remote_entry: Optional[TranslationEntry] = None  # 远程版本
    
    merge_strategy: str = "3way"  # 合并策略
    conflict_resolution: str = "mark_for_review"  # 冲突处理


@dataclass 
class MergeResult:
    """合并结果"""
    success: bool
    merged_entry: Optional[TranslationEntry] = None
    has_conflict: bool = False
    conflict_type: Optional[str] = None
    conflict_details: Dict[str, Any] = None
    error_message: Optional[str] = None


class EntryDeltaProcessor:
    """Entry-Delta处理器"""
    
    def __init__(self, entry_repository: Optional[TranslationEntryRepository] = None):
        self.supported_operations = ["create", "update", "delete"]
        self.entry_repository = entry_repository
    
    def serialize_entry_delta(self, entry: TranslationEntry, operation: str = "update") -> EntryDelta:
        """将翻译条目序列化为Entry-Delta格式"""
        if operation not in self.supported_operations:
            raise ValueError(f"不支持的操作类型: {operation}")
        
        delta = EntryDelta(
            entry_uid=entry.uid,
            uida_keys_b64=entry.uida_keys_b64 or "",
            uida_hash=entry.uida_hash or "",
            operation=operation,
            key=entry.key,
            src_text=entry.src_text,
            dst_text=entry.dst_text,
            status=entry.status,
            language_file_uid=entry.language_file_uid,
            updated_at=entry.updated_at or datetime.now().isoformat(),
            qa_flags=entry.qa_flags or {}
        )
        
        return delta
    
    def deserialize_entry_delta(self, delta: EntryDelta) -> TranslationEntry:
        """将Entry-Delta反序列化为翻译条目"""
        entry = TranslationEntry(
            uid=delta.entry_uid,
            uida_keys_b64=delta.uida_keys_b64,
            uida_hash=delta.uida_hash,
            key=delta.key,
            src_text=delta.src_text,
            dst_text=delta.dst_text,
            status=delta.status,
            language_file_uid=delta.language_file_uid,
            updated_at=delta.updated_at,
            created_at=datetime.now().isoformat(),  # 添加created_at
            qa_flags=delta.qa_flags
        )
        
        return entry
    
    def create_delta_payload(self, deltas: List[EntryDelta]) -> bytes:
        """创建Entry-Delta载荷数据"""
        try:
            # 转换为可序列化的格式
            payload_data = {
                "format_version": "1.0",
                "created_at": datetime.now().isoformat(),
                "entries": [delta.dict() for delta in deltas]
            }
            
            # JSON序列化
            json_data = json.dumps(payload_data, ensure_ascii=False, separators=(',', ':'))
            payload_bytes = json_data.encode('utf-8')
            
            logger.info("创建Entry-Delta载荷",
                       entries_count=len(deltas),
                       payload_size=len(payload_bytes))
            
            return payload_bytes
            
        except Exception as e:
            logger.error("创建Entry-Delta载荷失败", error=str(e))
            raise
    
    def parse_delta_payload(self, payload_bytes: bytes) -> List[EntryDelta]:
        """解析Entry-Delta载荷数据"""
        try:
            # JSON反序列化
            json_data = payload_bytes.decode('utf-8')
            payload_data = json.loads(json_data)
            
            # 验证格式版本
            format_version = payload_data.get("format_version", "1.0")
            if format_version not in ["1.0"]:
                raise ValueError(f"不支持的格式版本: {format_version}")
            
            # 解析条目
            entries = payload_data.get("entries", [])
            deltas = []
            
            for entry_data in entries:
                try:
                    delta = EntryDelta(**entry_data)
                    deltas.append(delta)
                except Exception as e:
                    logger.warning("跳过无效的Entry-Delta条目", 
                                 entry_uid=entry_data.get("entry_uid"),
                                 error=str(e))
                    continue
            
            logger.info("解析Entry-Delta载荷完成",
                       total_entries=len(entries),
                       valid_entries=len(deltas))
            
            return deltas
            
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败", error=str(e))
            raise ValueError(f"无效的JSON格式: {str(e)}")
        except Exception as e:
            logger.error("解析Entry-Delta载荷失败", error=str(e))
            raise
    
    def calculate_payload_cid(self, payload_bytes: bytes) -> str:
        """计算载荷的内容标识符 (CID)"""
        # 使用真实的BLAKE3进行内容寻址
        cid = compute_cid(payload_bytes, HashAlgorithm.BLAKE3)
        return str(cid)
    
    def perform_3way_merge(self, context: MergeContext) -> MergeResult:
        """执行3-way合并"""
        try:
            base = context.base_entry
            local = context.local_entry  
            remote = context.remote_entry
            
            # Case 1: 只有远程版本 (新增)
            if not local and not base and remote:
                return MergeResult(
                    success=True,
                    merged_entry=remote,
                    has_conflict=False
                )
            
            # Case 2: 只有本地版本 (本地新增)
            if local and not base and not remote:
                return MergeResult(
                    success=True,
                    merged_entry=local,
                    has_conflict=False
                )
            
            # Case 3: 远程删除，本地未修改
            if base and local and not remote:
                if self._entries_equal(base, local):
                    return MergeResult(
                        success=True,
                        merged_entry=None,  # 删除
                        has_conflict=False
                    )
            
            # Case 4: 远程修改，本地未修改
            if base and local and remote:
                if self._entries_equal(base, local):
                    return MergeResult(
                        success=True,
                        merged_entry=remote,
                        has_conflict=False
                    )
            
            # Case 5: 本地修改，远程未修改
            if base and local and remote:
                if self._entries_equal(base, remote):
                    return MergeResult(
                        success=True,
                        merged_entry=local,
                        has_conflict=False
                    )
            
            # Case 6: 双方都修改，内容相同
            if local and remote and self._entries_equal(local, remote):
                return MergeResult(
                    success=True,
                    merged_entry=local,
                    has_conflict=False
                )
            
            # Case 7: 冲突情况
            return self._handle_conflict(context)
            
        except Exception as e:
            logger.error("3-way合并失败", error=str(e))
            return MergeResult(
                success=False,
                error_message=str(e)
            )
    
    def _entries_equal(self, entry1: TranslationEntry, entry2: TranslationEntry) -> bool:
        """比较两个条目是否相等 (忽略时间戳和ID)"""
        if not entry1 or not entry2:
            return False
        
        return (
            entry1.key == entry2.key and
            entry1.src_text == entry2.src_text and
            entry1.dst_text == entry2.dst_text and
            entry1.status == entry2.status
        )
    
    def _handle_conflict(self, context: MergeContext) -> MergeResult:
        """处理合并冲突"""
        local = context.local_entry
        remote = context.remote_entry
        
        # 根据冲突处理策略
        if context.conflict_resolution == "take_remote":
            return MergeResult(
                success=True,
                merged_entry=remote,
                has_conflict=False
            )
        elif context.conflict_resolution == "take_local":
            return MergeResult(
                success=True,
                merged_entry=local,
                has_conflict=False
            )
        else:  # mark_for_review
            # 创建冲突标记的条目
            conflict_entry = remote if remote else local
            if conflict_entry:
                conflict_entry.status = "conflict"
                conflict_entry.qa_flags = conflict_entry.qa_flags or {}
                conflict_entry.qa_flags["merge_conflict"] = {
                    "local_dst_text": local.dst_text if local else None,
                    "remote_dst_text": remote.dst_text if remote else None,
                    "conflict_detected_at": datetime.now().isoformat()
                }
            
            conflict_details = {
                "local_version": local.to_dict() if local else None,
                "remote_version": remote.to_dict() if remote else None
            }
            
            return MergeResult(
                success=True,
                merged_entry=conflict_entry,
                has_conflict=True,
                conflict_type="content_conflict",
                conflict_details=conflict_details
            )
    
    async def batch_process_deltas(self, deltas: List[EntryDelta], merge_strategy: str = "3way") -> Dict[str, Any]:
        """批量处理Entry-Delta列表"""
        if not self.entry_repository:
            logger.warning("EntryDeltaProcessor未配置数据库Repository，使用模拟模式")
            return self._simulate_batch_process(deltas)
        
        results = {
            "processed": 0,
            "merged": 0,
            "conflicts": 0,
            "errors": 0,
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "conflict_entries": [],
            "error_entries": []
        }
        
        for delta in deltas:
            try:
                results["processed"] += 1
                logger.debug("处理Entry-Delta", 
                           entry_uid=delta.entry_uid, 
                           operation=delta.operation,
                           key=delta.key)
                
                # 从数据库查询现有条目
                local_entry = None
                if delta.entry_uid:
                    local_entry = await self.entry_repository.find_by_id(delta.entry_uid)
                elif delta.uida_hash:
                    # 通过UIDA查找现有条目
                    matching_entries = await self.entry_repository.find_by_uida_hash(delta.uida_hash)
                    if matching_entries:
                        local_entry = matching_entries[0]
                elif delta.key and delta.language_file_uid:
                    # 通过key和语言文件UID查找
                    local_entry = await self.entry_repository.get_entry_by_key(
                        delta.language_file_uid, delta.key
                    )
                
                # 构建合并上下文
                remote_entry = self.deserialize_entry_delta(delta)
                context = MergeContext(
                    base_entry=local_entry,  # 使用本地条目作为base
                    local_entry=local_entry,
                    remote_entry=remote_entry,
                    merge_strategy=merge_strategy
                )
                
                # 执行合并
                merge_result = self.perform_3way_merge(context)
                
                if not merge_result.success:
                    results["errors"] += 1
                    results["error_entries"].append({
                        "entry_uid": delta.entry_uid,
                        "error": merge_result.error_message
                    })
                    continue
                
                # 处理合并结果
                if merge_result.has_conflict:
                    results["conflicts"] += 1
                    results["conflict_entries"].append({
                        "entry_uid": delta.entry_uid,
                        "uida_hash": delta.uida_hash,
                        "conflict_type": merge_result.conflict_type,
                        "conflict_details": merge_result.conflict_details
                    })
                
                # 应用数据库操作
                if merge_result.merged_entry is None:
                    # 删除操作
                    if local_entry:
                        await self.entry_repository.delete(local_entry.uid)
                        results["deleted"] += 1
                        logger.debug("删除条目", entry_uid=local_entry.uid)
                elif local_entry is None:
                    # 创建操作
                    created_id = await self.entry_repository.create(merge_result.merged_entry)
                    results["created"] += 1
                    logger.debug("创建条目", entry_uid=merge_result.merged_entry.uid, created_id=created_id)
                else:
                    # 更新操作
                    merge_result.merged_entry.uid = local_entry.uid  # 保持原UID
                    await self.entry_repository.update(merge_result.merged_entry)
                    results["updated"] += 1
                    logger.debug("更新条目", entry_uid=local_entry.uid)
                
                results["merged"] += 1
                
            except Exception as e:
                results["errors"] += 1
                results["error_entries"].append({
                    "entry_uid": delta.entry_uid,
                    "error": str(e)
                })
                logger.error("处理Entry-Delta失败",
                           entry_uid=delta.entry_uid,
                           operation=getattr(delta, 'operation', 'unknown'),
                           error=str(e))
        
        logger.info("批量处理Entry-Delta完成",
                   processed=results["processed"],
                   merged=results["merged"],
                   created=results["created"],
                   updated=results["updated"],
                   deleted=results["deleted"],
                   conflicts=results["conflicts"],
                   errors=results["errors"])
        
        return results
    
    def _simulate_batch_process(self, deltas: List[EntryDelta]) -> Dict[str, Any]:
        """模拟批量处理（用于测试）"""
        results = {
            "processed": 0,
            "merged": 0,
            "conflicts": 0,
            "errors": 0,
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "conflict_entries": [],
            "error_entries": []
        }
        
        for delta in deltas:
            try:
                results["processed"] += 1
                
                # 模拟处理结果
                if results["processed"] % 10 == 0:  # 每10个产生一个冲突
                    results["conflicts"] += 1
                    results["conflict_entries"].append({
                        "entry_uid": delta.entry_uid,
                        "uida_hash": delta.uida_hash,
                        "conflict_type": "content_conflict"
                    })
                else:
                    results["merged"] += 1
                    if delta.operation == "create":
                        results["created"] += 1
                    elif delta.operation == "update":
                        results["updated"] += 1
                    elif delta.operation == "delete":
                        results["deleted"] += 1
                
            except Exception as e:
                results["errors"] += 1
                results["error_entries"].append({
                    "entry_uid": delta.entry_uid,
                    "error": str(e)
                })
        
        logger.info("模拟批量处理Entry-Delta完成",
                   **{k: v for k, v in results.items() if k not in ["conflict_entries", "error_entries"]})
        
        return results


# 全局处理器实例
_entry_delta_processor: Optional[EntryDeltaProcessor] = None


def get_entry_delta_processor(entry_repository: Optional[TranslationEntryRepository] = None) -> EntryDeltaProcessor:
    """获取Entry-Delta处理器实例 (单例)"""
    global _entry_delta_processor
    if _entry_delta_processor is None:
        _entry_delta_processor = EntryDeltaProcessor(entry_repository)
        logger.info("Entry-Delta处理器初始化完成",
                   has_repository=entry_repository is not None)
    elif entry_repository and not _entry_delta_processor.entry_repository:
        # 如果处理器已存在但没有Repository，则注入依赖
        _entry_delta_processor.entry_repository = entry_repository
        logger.info("Entry-Delta处理器Repository依赖注入完成")
    return _entry_delta_processor