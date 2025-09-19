"""
翻译数据同步器接口定义

定义了翻译数据同步的标准接口和协议
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol

from ..models import (
    ConflictResolution,
    IncrementalSyncPlan,
    SyncResult,
    SyncStrategy,
    TranslationConflict,
    TranslationDelta,
    TranslationEntry,
    TranslationProject,
)


class ITranslationRepository(Protocol):
    """翻译数据仓库接口"""
    
    async def get_project(self, project_id: str) -> Optional[TranslationProject]:
        """获取项目信息"""
        ...
    
    async def save_project(self, project: TranslationProject) -> None:
        """保存项目信息"""
        ...
    
    async def get_project_version(self, project_id: str) -> int:
        """获取项目当前版本号"""
        ...
    
    async def get_entries(
        self, 
        project_id: str,
        language: Optional[str] = None,
        namespace: Optional[str] = None
    ) -> List[TranslationEntry]:
        """获取翻译条目"""
        ...
    
    async def save_entries(self, entries: List[TranslationEntry]) -> None:
        """保存翻译条目"""
        ...
    
    async def get_entry(self, entry_id: str) -> Optional[TranslationEntry]:
        """获取单个翻译条目"""
        ...
    
    async def delete_entries(self, entry_ids: List[str]) -> None:
        """删除翻译条目"""
        ...
    
    async def get_delta(
        self, 
        project_id: str,
        from_version: int,
        to_version: int
    ) -> TranslationDelta:
        """获取版本间的变更记录"""
        ...
    
    async def save_delta(self, delta: TranslationDelta) -> None:
        """保存变更记录"""
        ...
    
    async def apply_delta(self, delta: TranslationDelta) -> None:
        """应用变更记录"""
        ...
    
    async def get_entry_fingerprints(self, project_id: str) -> dict[str, str]:
        """获取条目指纹映射"""
        ...


class IRemoteTranslationClient(Protocol):
    """远程翻译服务客户端接口"""
    
    async def get_project_version(self, project_id: str) -> int:
        """获取远程项目版本"""
        ...
    
    async def push_delta(
        self, 
        project_id: str,
        delta: TranslationDelta
    ) -> SyncResult:
        """推送变更到远程"""
        ...
    
    async def pull_delta(
        self, 
        project_id: str,
        since_version: int
    ) -> TranslationDelta:
        """从远程拉取变更"""
        ...
    
    async def get_entries(
        self, 
        project_id: str,
        entry_ids: List[str]
    ) -> List[TranslationEntry]:
        """获取远程翻译条目"""
        ...
    
    async def upload_entries(
        self, 
        project_id: str,
        entries: List[TranslationEntry]
    ) -> SyncResult:
        """上传翻译条目"""
        ...


class IConflictResolver(Protocol):
    """冲突解决器接口"""
    
    async def resolve_conflicts(
        self, 
        conflicts: List[TranslationConflict]
    ) -> List[TranslationEntry]:
        """解决翻译冲突"""
        ...
    
    def get_default_resolution(self, conflict: TranslationConflict) -> ConflictResolution:
        """获取默认解决策略"""
        ...


class ITranslationCache(Protocol):
    """翻译数据缓存接口"""
    
    async def get_entries(self, project_id: str) -> List[TranslationEntry]:
        """获取缓存的翻译条目"""
        ...
    
    async def cache_entries(self, project_id: str, entries: List[TranslationEntry]) -> None:
        """缓存翻译条目"""
        ...
    
    async def get_entry_fingerprints(self, project_id: str) -> dict[str, str]:
        """获取条目指纹映射"""
        ...
    
    async def invalidate_project(self, project_id: str) -> None:
        """使项目缓存失效"""
        ...


class ITranslationSynchronizer(Protocol):
    """翻译数据同步器接口"""
    
    async def sync_project(
        self, 
        project_id: str,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> SyncResult:
        """同步项目翻译数据"""
        ...
    
    async def push_delta(
        self, 
        project_id: str,
        delta: TranslationDelta
    ) -> SyncResult:
        """推送翻译变更"""
        ...
    
    async def pull_delta(
        self, 
        project_id: str,
        since_version: int
    ) -> TranslationDelta:
        """拉取翻译变更"""
        ...
    
    async def resolve_conflicts(
        self, 
        conflicts: List[TranslationConflict]
    ) -> List[TranslationEntry]:
        """解决翻译冲突"""
        ...
    
    async def prepare_incremental_sync(
        self, 
        project_id: str,
        target_entries: List[TranslationEntry]
    ) -> IncrementalSyncPlan:
        """准备增量同步方案"""
        ...


class BaseTranslationSynchronizer(ABC):
    """翻译数据同步器基类"""
    
    def __init__(
        self,
        local_repo: ITranslationRepository,
        remote_client: IRemoteTranslationClient,
        conflict_resolver: IConflictResolver,
        cache: Optional[ITranslationCache] = None
    ):
        self.local_repo = local_repo
        self.remote_client = remote_client
        self.conflict_resolver = conflict_resolver
        self.cache = cache
    
    @abstractmethod
    async def sync_project(
        self, 
        project_id: str,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> SyncResult:
        """同步项目翻译数据"""
        pass
    
    async def push_delta(
        self, 
        project_id: str,
        delta: TranslationDelta
    ) -> SyncResult:
        """推送翻译变更"""
        return await self.remote_client.push_delta(project_id, delta)
    
    async def pull_delta(
        self, 
        project_id: str,
        since_version: int
    ) -> TranslationDelta:
        """拉取翻译变更"""
        return await self.remote_client.pull_delta(project_id, since_version)
    
    async def resolve_conflicts(
        self, 
        conflicts: List[TranslationConflict]
    ) -> List[TranslationEntry]:
        """解决翻译冲突"""
        return await self.conflict_resolver.resolve_conflicts(conflicts)
    
    async def _detect_conflicts(
        self, 
        remote_delta: TranslationDelta,
        local_version: int
    ) -> List[TranslationConflict]:
        """检测翻译冲突"""
        from ..models import ConflictType, TranslationConflict
        
        conflicts = []
        
        # 检查修改冲突
        for remote_entry in remote_delta.modified:
            local_entry = await self.local_repo.get_entry(remote_entry.entry_id)
            
            if local_entry and local_entry.version > local_version:
                # 本地也有修改，产生冲突
                conflict = TranslationConflict(
                    entry_id=remote_entry.entry_id,
                    local_entry=local_entry,
                    remote_entry=remote_entry,
                    conflict_type=ConflictType.MODIFY_MODIFY
                )
                conflicts.append(conflict)
        
        # 检查删除冲突
        for deleted_entry_id in remote_delta.deleted:
            local_entry = await self.local_repo.get_entry(deleted_entry_id)
            
            if local_entry and local_entry.version > local_version:
                # 本地有修改，远程删除，产生冲突
                conflict = TranslationConflict(
                    entry_id=deleted_entry_id,
                    local_entry=local_entry,
                    remote_entry=None,  # 已删除
                    conflict_type=ConflictType.MODIFY_DELETE
                )
                conflicts.append(conflict)
        
        return conflicts