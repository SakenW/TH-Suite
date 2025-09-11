"""
数据传输对象（DTO）
用于应用层和外部层之间的数据传输
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BaseDTO:
    """DTO基类"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, list | set):
                result[key] = list(value)
            elif hasattr(value, "to_dict"):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result


@dataclass
class ModDTO(BaseDTO):
    """模组DTO"""

    mod_id: str
    name: str
    version: str
    authors: list[str]
    description: str | None
    minecraft_version: str | None
    loader_type: str | None
    file_path: str
    scan_status: str
    last_scanned: str | None
    content_hash: str | None
    translation_languages: list[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, mod: Any) -> "ModDTO":
        """从领域模型创建DTO"""
        return cls(
            mod_id=str(mod.mod_id),
            name=mod.metadata.name,
            version=str(mod.metadata.version),
            authors=mod.metadata.authors,
            description=mod.metadata.description,
            minecraft_version=mod.metadata.minecraft_version,
            loader_type=mod.metadata.loader_type,
            file_path=mod.file_path,
            scan_status=mod.scan_status,
            last_scanned=mod.last_scanned.isoformat() if mod.last_scanned else None,
            content_hash=mod.content_hash,
            translation_languages=list(mod.translations.keys()),
            created_at=mod.created_at.isoformat(),
            updated_at=mod.updated_at.isoformat(),
        )


@dataclass
class TranslationDTO(BaseDTO):
    """翻译DTO"""

    key: str
    original: str
    translated: str
    language: str
    status: str
    translator: str | None
    reviewed_by: str | None
    quality_score: float | None

    @classmethod
    def from_domain(cls, entry: Any) -> "TranslationDTO":
        """从领域模型创建DTO"""
        return cls(
            key=entry.key,
            original=entry.original,
            translated=entry.translated,
            language=entry.language,
            status=entry.status,
            translator=entry.translator,
            reviewed_by=entry.reviewed_by,
            quality_score=None,  # 需要计算
        )


@dataclass
class ProjectDTO(BaseDTO):
    """项目DTO"""

    project_id: str
    name: str
    description: str | None
    status: str
    target_languages: list[str]
    mod_count: int
    contributor_count: int
    task_count: int
    progress: dict[str, float]
    settings: dict[str, Any]
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, project: Any) -> "ProjectDTO":
        """从领域模型创建DTO"""
        return cls(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            status=project.status.value,
            target_languages=list(project.target_languages),
            mod_count=len(project.mod_ids),
            contributor_count=len(project.contributors),
            task_count=len(project.tasks),
            progress=project.get_progress(),
            settings={
                "auto_scan": project.settings.auto_scan,
                "scan_interval": project.settings.scan_interval,
                "auto_sync": project.settings.auto_sync,
                "sync_interval": project.settings.sync_interval,
                "quality_threshold": project.settings.quality_threshold,
                "require_review": project.settings.require_review,
            },
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )


@dataclass
class TaskDTO(BaseDTO):
    """任务DTO"""

    task_id: str
    project_id: str
    mod_id: str
    language: str
    assigned_to: str | None
    priority: int
    deadline: str | None
    status: str
    created_at: str
    completed_at: str | None
    is_overdue: bool

    @classmethod
    def from_domain(cls, task: Any, project_id: str) -> "TaskDTO":
        """从领域模型创建DTO"""
        return cls(
            task_id=task.task_id,
            project_id=project_id,
            mod_id=str(task.mod_id),
            language=task.language,
            assigned_to=task.assigned_to,
            priority=task.priority,
            deadline=task.deadline.isoformat() if task.deadline else None,
            status=task.status,
            created_at=task.created_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            is_overdue=task.is_overdue(),
        )


@dataclass
class ContributorDTO(BaseDTO):
    """贡献者DTO"""

    user_id: str
    name: str
    role: str
    languages: list[str]
    contribution_count: int
    joined_at: str

    @classmethod
    def from_domain(cls, contributor: Any) -> "ContributorDTO":
        """从领域模型创建DTO"""
        return cls(
            user_id=contributor.user_id,
            name=contributor.name,
            role=contributor.role,
            languages=list(contributor.languages),
            contribution_count=contributor.contribution_count,
            joined_at=contributor.joined_at.isoformat(),
        )


@dataclass
class ScanResultDTO(BaseDTO):
    """扫描结果DTO"""

    directory: str
    total_files: int
    scanned_files: int
    new_mods: int
    updated_mods: int
    failed_files: int
    errors: list[str]
    success: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        """扫描耗时（秒）"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class SyncResultDTO(BaseDTO):
    """同步结果DTO"""

    sync_id: str
    source: str
    target: str
    items_pushed: int
    items_pulled: int
    conflicts_found: int
    conflicts_resolved: int
    errors: int
    details: dict[str, list[str]]
    started_at: datetime
    completed_at: datetime | None
    success: bool


@dataclass
class TranslationProgressDTO(BaseDTO):
    """翻译进度DTO"""

    mod_id: str
    mod_name: str
    languages: dict[str, float]  # language -> progress percentage
    total_keys: int
    translated_keys: dict[str, int]  # language -> count
    approved_keys: dict[str, int]  # language -> count

    @property
    def overall_progress(self) -> float:
        """总体进度"""
        if not self.languages:
            return 0.0
        return sum(self.languages.values()) / len(self.languages)


@dataclass
class ConflictDTO(BaseDTO):
    """冲突DTO"""

    conflict_id: str
    mod_id: str
    language: str
    key: str
    local_value: str
    remote_value: str
    suggested_resolution: str | None
    resolution_strategy: str
    resolved: bool
    resolved_by: str | None
    resolved_at: str | None


@dataclass
class QualityMetricsDTO(BaseDTO):
    """质量指标DTO"""

    mod_id: str | None
    project_id: str | None
    language: str
    completeness: float  # 完整性 0-100
    consistency: float  # 一致性 0-100
    terminology: float  # 术语正确性 0-100
    overall_score: float  # 总体分数 0-100
    issues: list[dict[str, str]]  # 发现的问题


@dataclass
class ActivityDTO(BaseDTO):
    """活动DTO"""

    activity_id: str
    activity_type: str  # scan, translate, review, sync, etc.
    user_id: str | None
    project_id: str | None
    mod_id: str | None
    description: str
    metadata: dict[str, Any]
    timestamp: str


@dataclass
class StatisticsDTO(BaseDTO):
    """统计DTO"""

    total_mods: int
    total_projects: int
    total_translations: int
    total_languages: int
    total_contributors: int
    active_tasks: int
    completed_tasks: int
    translation_coverage: dict[str, float]  # language -> coverage
    recent_activity: list[ActivityDTO]
    top_contributors: list[dict[str, Any]]


@dataclass
class ErrorDTO(BaseDTO):
    """错误DTO"""

    error_code: str
    message: str
    details: dict[str, Any] | None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_exception(
        cls, exception: Exception, error_code: str = "UNKNOWN"
    ) -> "ErrorDTO":
        """从异常创建错误DTO"""
        return cls(
            error_code=error_code,
            message=str(exception),
            details={
                "type": exception.__class__.__name__,
                "args": exception.args if hasattr(exception, "args") else None,
            },
        )


@dataclass
class PagedResultDTO(BaseDTO):
    """分页结果DTO"""

    items: list[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

    @property
    def total_pages(self) -> int:
        """总页数"""
        return (
            (self.total + self.page_size - 1) // self.page_size
            if self.page_size > 0
            else 0
        )
