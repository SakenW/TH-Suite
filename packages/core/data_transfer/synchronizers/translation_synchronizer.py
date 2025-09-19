"""
翻译数据同步器实现

实现了翻译数据的增量同步、冲突解决和版本管理
"""

import zstandard as zstd
from datetime import datetime
from typing import Dict, List, Optional

import structlog

from ..models import (
    ConflictResolution,
    ConflictType,
    IncrementalSyncPlan,
    SyncResult,
    SyncStrategy,
    TranslationConflict,
    TranslationDelta,
    TranslationEntry,
    generate_delta_id,
)
from .interfaces import (
    BaseTranslationSynchronizer,
    IConflictResolver,
    IRemoteTranslationClient,
    ITranslationCache,
    ITranslationRepository,
)

logger = structlog.get_logger(__name__)


class TranslationDataCompressor:
    """翻译数据压缩器"""
    
    def __init__(self):
        # 为翻译文本创建专用字典
        self.translation_dict = self._build_translation_dict()
        self.compressor = zstd.ZstdCompressor(
            level=zstd.MAX_COMPRESSION_LEVEL,
            dict_data=self.translation_dict
        )
        self.decompressor = zstd.ZstdDecompressor(dict_data=self.translation_dict)
    
    def _build_translation_dict(self) -> bytes:
        """构建翻译文本专用压缩字典"""
        
        # 常见的翻译模式
        common_patterns = [
            # Minecraft常见词汇
            "minecraft", "item", "block", "entity", "gui", "tooltip",
            "enchantment", "effect", "advancement", "biome", "dimension",
            "potion", "mob", "creative", "survival", "hardcore",
            
            # 常见翻译结构
            "%s", "%d", "{}", "[]", "()", "%%", "\\n", "\\t",
            "the", "and", "or", "to", "of", "in", "for", "with", "by",
            
            # 中文常见字符
            "的", "是", "了", "在", "有", "和", "中", "一个", "这个", "那个",
            "可以", "能够", "需要", "使用", "获得", "制作", "合成", "挖掘",
            
            # 游戏术语
            "level", "damage", "health", "mana", "experience", "xp",
            "armor", "weapon", "tool", "food", "material", "ore",
        ]
        
        # 构建训练文本
        training_text = " ".join(common_patterns * 10)  # 重复增加权重
        training_data = [training_text.encode('utf-8')]
        
        # 使用zstd训练字典
        return zstd.train_dictionary(1024 * 16, training_data)
    
    def compress_entries(self, entries: List[TranslationEntry]) -> bytes:
        """压缩翻译条目列表"""
        import json
        
        # 序列化为JSON
        data = [entry.to_dict() for entry in entries]
        json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        
        # 压缩
        return self.compressor.compress(json_data.encode('utf-8'))
    
    def decompress_entries(self, compressed_data: bytes) -> List[TranslationEntry]:
        """解压缩翻译条目列表"""
        import json
        from ..models import TranslationEntry
        
        # 解压缩
        json_data = self.decompressor.decompress(compressed_data).decode('utf-8')
        
        # 反序列化
        data = json.loads(json_data)
        return [TranslationEntry.from_dict(item) for item in data]


class IncrementalTransferManager:
    """增量传输管理器"""
    
    def __init__(self, local_cache: ITranslationCache):
        self.local_cache = local_cache
        self.compressor = TranslationDataCompressor()
    
    async def prepare_incremental_sync(
        self, 
        project_id: str,
        target_entries: List[TranslationEntry]
    ) -> IncrementalSyncPlan:
        """准备增量同步方案"""
        
        # 获取本地缓存的条目指纹
        local_fingerprints = await self.local_cache.get_entry_fingerprints(project_id)
        
        # 计算需要传输的条目
        to_download = []
        to_upload = []
        
        # 创建远程条目指纹映射
        remote_fingerprints = {
            entry.entry_id: entry.checksum 
            for entry in target_entries
        }
        
        # 检查需要下载的条目
        for entry in target_entries:
            local_checksum = local_fingerprints.get(entry.entry_id)
            if local_checksum != entry.checksum:
                to_download.append(entry.entry_id)
        
        # 检查需要上传的条目  
        local_entries = await self.local_cache.get_entries(project_id)
        for entry in local_entries:
            remote_checksum = remote_fingerprints.get(entry.entry_id)
            if remote_checksum != entry.checksum:
                to_upload.append(entry)
        
        # 估算传输大小
        estimated_size = self._estimate_transfer_size(to_upload)
        
        # 估算传输时间（基于经验公式）
        estimated_time = max(1.0, estimated_size / (1024 * 1024) * 2.0)  # 假设2秒/MB
        
        return IncrementalSyncPlan(
            to_download=to_download,
            to_upload=to_upload,
            total_entries=len(target_entries),
            transfer_ratio=len(to_download + to_upload) / max(1, len(target_entries)),
            estimated_size=estimated_size,
            estimated_time=estimated_time
        )
    
    def _estimate_transfer_size(self, entries: List[TranslationEntry]) -> int:
        """估算传输大小"""
        
        if not entries:
            return 0
        
        # 采样前几个条目估算
        sample_entries = entries[:min(10, len(entries))]
        
        try:
            compressed_data = self.compressor.compress_entries(sample_entries)
            avg_size = len(compressed_data) / len(sample_entries)
            return int(avg_size * len(entries))
        except Exception:
            # 如果压缩失败，使用简单估算
            return len(entries) * 200  # 假设每个条目平均200字节


class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self, default_resolution: ConflictResolution = ConflictResolution.REMOTE):
        self.default_resolution = default_resolution
    
    async def resolve_conflicts(
        self, 
        conflicts: List[TranslationConflict]
    ) -> List[TranslationEntry]:
        """解决翻译冲突"""
        
        resolved_entries = []
        
        for conflict in conflicts:
            resolution = conflict.resolution or self.get_default_resolution(conflict)
            
            try:
                resolved_entry = await self._resolve_single_conflict(conflict, resolution)
                if resolved_entry:
                    resolved_entries.append(resolved_entry)
                    conflict.resolved_entry = resolved_entry
                    conflict.resolution = resolution
            
            except Exception as e:
                logger.error(
                    "Failed to resolve conflict",
                    entry_id=conflict.entry_id,
                    conflict_type=conflict.conflict_type.value,
                    error=str(e)
                )
        
        logger.info(
            "Conflicts resolved",
            total_conflicts=len(conflicts),
            resolved_count=len(resolved_entries)
        )
        
        return resolved_entries
    
    def get_default_resolution(self, conflict: TranslationConflict) -> ConflictResolution:
        """获取默认解决策略"""
        
        # 根据冲突类型选择默认策略
        if conflict.conflict_type == ConflictType.MODIFY_DELETE:
            # 修改-删除冲突，倾向于保留本地修改
            return ConflictResolution.LOCAL
        elif conflict.conflict_type == ConflictType.ADD_ADD:
            # 双方添加相同key，使用远程版本
            return ConflictResolution.REMOTE
        else:
            # 默认使用配置的策略
            return self.default_resolution
    
    async def _resolve_single_conflict(
        self, 
        conflict: TranslationConflict,
        resolution: ConflictResolution
    ) -> Optional[TranslationEntry]:
        """解决单个冲突"""
        
        if resolution == ConflictResolution.LOCAL:
            return conflict.local_entry
        
        elif resolution == ConflictResolution.REMOTE:
            return conflict.remote_entry
        
        elif resolution == ConflictResolution.MERGE:
            return await self._merge_entries(conflict.local_entry, conflict.remote_entry)
        
        elif resolution == ConflictResolution.MANUAL:
            # 手动解决需要外部干预
            logger.warning(
                "Manual conflict resolution required",
                entry_id=conflict.entry_id
            )
            return None
        
        return None
    
    async def _merge_entries(
        self, 
        local_entry: TranslationEntry,
        remote_entry: Optional[TranslationEntry]
    ) -> Optional[TranslationEntry]:
        """智能合并条目"""
        
        if not remote_entry:
            return local_entry
        
        # 创建合并后的条目
        merged_entry = TranslationEntry(
            entry_id=local_entry.entry_id,
            namespace=local_entry.namespace,
            key=local_entry.key,
            source_text=remote_entry.source_text or local_entry.source_text,  # 优先使用远程源文本
            target_text=local_entry.target_text or remote_entry.target_text,  # 优先使用本地翻译
            target_language=local_entry.target_language,
            game_type=local_entry.game_type,
            mod_info=local_entry.mod_info,
            file_path=local_entry.file_path,
            category=local_entry.category,
            version=max(local_entry.version, remote_entry.version) + 1,  # 版本号递增
            last_modified=datetime.now(),
            status=local_entry.status,
            translator=local_entry.translator or remote_entry.translator,
            reviewer=None,  # 合并后需要重新审核
            comments=local_entry.comments + remote_entry.comments  # 合并评论
        )
        
        return merged_entry


class TranslationSynchronizer(BaseTranslationSynchronizer):
    """翻译数据同步器实现"""
    
    def __init__(
        self,
        local_repo: ITranslationRepository,
        remote_client: IRemoteTranslationClient,
        conflict_resolver: Optional[IConflictResolver] = None,
        cache: Optional[ITranslationCache] = None
    ):
        if conflict_resolver is None:
            conflict_resolver = ConflictResolver()
        
        super().__init__(local_repo, remote_client, conflict_resolver, cache)
        
        self.transfer_manager = IncrementalTransferManager(cache) if cache else None
    
    async def sync_project(
        self, 
        project_id: str,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> SyncResult:
        """同步项目翻译数据"""
        
        result = SyncResult(project_id=project_id)
        
        try:
            logger.info("Starting project synchronization", project_id=project_id, strategy=strategy.value)
            
            if strategy == SyncStrategy.FULL:
                result = await self._full_sync(project_id)
            elif strategy == SyncStrategy.INCREMENTAL:
                result = await self._incremental_sync(project_id)
            elif strategy == SyncStrategy.FORCE_PUSH:
                result = await self._force_push(project_id)
            elif strategy == SyncStrategy.FORCE_PULL:
                result = await self._force_pull(project_id)
            
            logger.info(
                "Project synchronization completed",
                project_id=project_id,
                success=result.success,
                pushed=result.pushed_entries,
                pulled=result.pulled_entries,
                conflicts=result.conflicts_resolved
            )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(
                "Project synchronization failed",
                project_id=project_id,
                error=str(e)
            )
        
        return result
    
    async def prepare_incremental_sync(
        self, 
        project_id: str,
        target_entries: List[TranslationEntry]
    ) -> IncrementalSyncPlan:
        """准备增量同步方案"""
        
        if self.transfer_manager:
            return await self.transfer_manager.prepare_incremental_sync(project_id, target_entries)
        else:
            # 如果没有缓存，返回简单的同步方案
            return IncrementalSyncPlan(
                to_download=[],
                to_upload=target_entries,
                total_entries=len(target_entries),
                transfer_ratio=1.0
            )
    
    async def _incremental_sync(self, project_id: str) -> SyncResult:
        """增量同步"""
        
        result = SyncResult(project_id=project_id)
        
        # 1. 获取本地和远程版本信息
        local_version = await self.local_repo.get_project_version(project_id)
        remote_version = await self.remote_client.get_project_version(project_id)
        
        logger.debug(
            "Version comparison",
            project_id=project_id,
            local_version=local_version,
            remote_version=remote_version
        )
        
        # 2. 推送本地变更
        if local_version > remote_version:
            local_delta = await self.local_repo.get_delta(
                project_id, 
                remote_version, 
                local_version
            )
            
            push_result = await self.remote_client.push_delta(project_id, local_delta)
            result.pushed_entries = len(local_delta.added) + len(local_delta.modified)
            
            if not push_result.success:
                result.warnings.append(f"Failed to push changes: {push_result.error}")
        
        # 3. 拉取远程变更
        if remote_version > local_version:
            remote_delta = await self.remote_client.pull_delta(project_id, local_version)
            
            # 检测冲突
            conflicts = await self._detect_conflicts(remote_delta, local_version)
            result.conflicts_detected = len(conflicts)
            
            if conflicts:
                # 解决冲突
                resolved_entries = await self.conflict_resolver.resolve_conflicts(conflicts)
                result.conflicts_resolved = len([e for e in resolved_entries if e is not None])
                result.conflicts = conflicts
                
                # 更新delta中的条目为解决后的版本
                resolved_map = {e.entry_id: e for e in resolved_entries if e is not None}
                for i, entry in enumerate(remote_delta.modified):
                    if entry.entry_id in resolved_map:
                        remote_delta.modified[i] = resolved_map[entry.entry_id]
            
            # 应用远程变更
            await self.local_repo.apply_delta(remote_delta)
            result.pulled_entries = len(remote_delta.added) + len(remote_delta.modified)
        
        result.success = True
        return result
    
    async def _full_sync(self, project_id: str) -> SyncResult:
        """完整同步"""
        
        result = SyncResult(project_id=project_id)
        
        # 获取远程所有条目
        remote_version = await self.remote_client.get_project_version(project_id)
        remote_delta = await self.remote_client.pull_delta(project_id, 0)
        
        # 清空本地数据并应用远程数据
        local_entries = await self.local_repo.get_entries(project_id)
        if local_entries:
            await self.local_repo.delete_entries([e.entry_id for e in local_entries])
        
        await self.local_repo.apply_delta(remote_delta)
        result.pulled_entries = len(remote_delta.added) + len(remote_delta.modified)
        
        result.success = True
        return result
    
    async def _force_push(self, project_id: str) -> SyncResult:
        """强制推送"""
        
        result = SyncResult(project_id=project_id)
        
        # 获取本地所有条目作为变更
        local_entries = await self.local_repo.get_entries(project_id)
        local_version = await self.local_repo.get_project_version(project_id)
        
        delta = TranslationDelta(
            delta_id=generate_delta_id(project_id, 0, local_version),
            project_id=project_id,
            base_version=0,
            target_version=local_version,
            added=local_entries,
            author="system",
            commit_message="Force push"
        )
        
        push_result = await self.remote_client.push_delta(project_id, delta)
        result.pushed_entries = len(local_entries)
        result.success = push_result.success
        
        if not result.success:
            result.error = push_result.error
        
        return result
    
    async def _force_pull(self, project_id: str) -> SyncResult:
        """强制拉取"""
        
        # 强制拉取就是完整同步
        return await self._full_sync(project_id)