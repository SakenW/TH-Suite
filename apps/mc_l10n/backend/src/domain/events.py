"""
领域事件定义
所有领域事件的集中定义
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DomainEvent:
    """领域事件基类"""

    event_id: str
    aggregate_id: str
    event_type: str
    timestamp: datetime
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }


class ModScannedEvent(DomainEvent):
    """模组扫描完成事件"""

    def __init__(
        self,
        mod_id: str,
        timestamp: datetime,
        translation_count: int,
        content_hash: str,
    ):
        super().__init__(
            event_id=f"mod_scanned_{mod_id}_{timestamp.timestamp()}",
            aggregate_id=mod_id,
            event_type="ModScanned",
            timestamp=timestamp,
        )
        self.mod_id = mod_id
        self.translation_count = translation_count
        self.content_hash = content_hash


class ModTranslatedEvent(DomainEvent):
    """模组翻译完成事件"""

    def __init__(
        self, mod_id: str, language: str, timestamp: datetime, progress: float
    ):
        super().__init__(
            event_id=f"mod_translated_{mod_id}_{language}_{timestamp.timestamp()}",
            aggregate_id=mod_id,
            event_type="ModTranslated",
            timestamp=timestamp,
        )
        self.mod_id = mod_id
        self.language = language
        self.progress = progress


class TranslationConflictEvent(DomainEvent):
    """翻译冲突事件"""

    def __init__(
        self,
        mod_id: str,
        language: str,
        key: str,
        existing_value: str,
        new_value: str,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"translation_conflict_{mod_id}_{key}_{timestamp.timestamp()}",
            aggregate_id=mod_id,
            event_type="TranslationConflict",
            timestamp=timestamp,
        )
        self.mod_id = mod_id
        self.language = language
        self.key = key
        self.existing_value = existing_value
        self.new_value = new_value


class ProjectCreatedEvent(DomainEvent):
    """项目创建事件"""

    project_id: str
    name: str
    creator: str

    def __init__(self, project_id: str, name: str, creator: str, timestamp: datetime):
        super().__init__(
            event_id=f"project_created_{project_id}_{timestamp.timestamp()}",
            aggregate_id=project_id,
            event_type="ProjectCreated",
            timestamp=timestamp,
        )
        self.project_id = project_id
        self.name = name
        self.creator = creator


class ProjectStatusChangedEvent(DomainEvent):
    """项目状态变更事件"""

    project_id: str
    old_status: str
    new_status: str
    changed_by: str

    def __init__(
        self,
        project_id: str,
        old_status: str,
        new_status: str,
        changed_by: str,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"project_status_changed_{project_id}_{timestamp.timestamp()}",
            aggregate_id=project_id,
            event_type="ProjectStatusChanged",
            timestamp=timestamp,
        )
        self.project_id = project_id
        self.old_status = old_status
        self.new_status = new_status
        self.changed_by = changed_by


class SyncStartedEvent(DomainEvent):
    """同步开始事件"""

    sync_id: str
    source: str
    target: str

    def __init__(self, sync_id: str, source: str, target: str, timestamp: datetime):
        super().__init__(
            event_id=f"sync_started_{sync_id}_{timestamp.timestamp()}",
            aggregate_id=sync_id,
            event_type="SyncStarted",
            timestamp=timestamp,
        )
        self.sync_id = sync_id
        self.source = source
        self.target = target


class SyncCompletedEvent(DomainEvent):
    """同步完成事件"""

    sync_id: str
    items_synced: int
    conflicts_resolved: int
    errors: int

    def __init__(
        self,
        sync_id: str,
        items_synced: int,
        conflicts_resolved: int,
        errors: int,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"sync_completed_{sync_id}_{timestamp.timestamp()}",
            aggregate_id=sync_id,
            event_type="SyncCompleted",
            timestamp=timestamp,
        )
        self.sync_id = sync_id
        self.items_synced = items_synced
        self.conflicts_resolved = conflicts_resolved
        self.errors = errors


class TranslationApprovedEvent(DomainEvent):
    """翻译批准事件"""

    translation_id: str
    mod_id: str
    language: str
    key: str
    approved_by: str

    def __init__(
        self,
        translation_id: str,
        mod_id: str,
        language: str,
        key: str,
        approved_by: str,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"translation_approved_{translation_id}_{timestamp.timestamp()}",
            aggregate_id=mod_id,
            event_type="TranslationApproved",
            timestamp=timestamp,
        )
        self.translation_id = translation_id
        self.mod_id = mod_id
        self.language = language
        self.key = key
        self.approved_by = approved_by


class TranslationRejectedEvent(DomainEvent):
    """翻译拒绝事件"""

    translation_id: str
    mod_id: str
    language: str
    key: str
    rejected_by: str
    reason: str | None = None

    def __init__(
        self,
        translation_id: str,
        mod_id: str,
        language: str,
        key: str,
        rejected_by: str,
        timestamp: datetime,
        reason: str | None = None,
    ):
        super().__init__(
            event_id=f"translation_rejected_{translation_id}_{timestamp.timestamp()}",
            aggregate_id=mod_id,
            event_type="TranslationRejected",
            timestamp=timestamp,
        )
        self.translation_id = translation_id
        self.mod_id = mod_id
        self.language = language
        self.key = key
        self.rejected_by = rejected_by
        self.reason = reason


class ProjectCompletedEvent(DomainEvent):
    """项目完成事件"""

    project_id: str
    completion_rate: float
    quality_score: float

    def __init__(
        self,
        project_id: str,
        completion_rate: float,
        quality_score: float,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"project_completed_{project_id}_{timestamp.timestamp()}",
            aggregate_id=project_id,
            event_type="ProjectCompleted",
            timestamp=timestamp,
        )
        self.project_id = project_id
        self.completion_rate = completion_rate
        self.quality_score = quality_score


class TaskAssignedEvent(DomainEvent):
    """任务分配事件"""

    task_id: str
    project_id: str
    assignee: str
    assignor: str

    def __init__(
        self,
        task_id: str,
        project_id: str,
        assignee: str,
        assignor: str,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"task_assigned_{task_id}_{timestamp.timestamp()}",
            aggregate_id=project_id,
            event_type="TaskAssigned",
            timestamp=timestamp,
        )
        self.task_id = task_id
        self.project_id = project_id
        self.assignee = assignee
        self.assignor = assignor


class TaskCompletedEvent(DomainEvent):
    """任务完成事件"""

    task_id: str
    project_id: str
    completed_by: str
    quality_score: float

    def __init__(
        self,
        task_id: str,
        project_id: str,
        completed_by: str,
        quality_score: float,
        timestamp: datetime,
    ):
        super().__init__(
            event_id=f"task_completed_{task_id}_{timestamp.timestamp()}",
            aggregate_id=project_id,
            event_type="TaskCompleted",
            timestamp=timestamp,
        )
        self.task_id = task_id
        self.project_id = project_id
        self.completed_by = completed_by
        self.quality_score = quality_score
