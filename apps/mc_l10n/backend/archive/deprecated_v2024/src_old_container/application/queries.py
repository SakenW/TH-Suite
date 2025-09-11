"""
应用层查询对象
CQRS模式中的查询定义
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Query:
    """查询基类"""

    query_id: str


@dataclass
class GetModByIdQuery(Query):
    """根据ID获取模组查询"""

    query_id: str
    mod_id: str
    include_translations: bool = True
    include_metadata: bool = True
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetModsByStatusQuery(Query):
    """根据状态获取模组查询"""

    query_id: str
    status: str  # pending, scanning, completed, failed
    limit: int = 100
    offset: int = 0
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SearchModsQuery(Query):
    """搜索模组查询"""

    query_id: str
    search_term: str
    limit: int = 50
    user_id: str | None = None
    search_in: list[str] = field(default_factory=lambda: ["name", "id", "description"])
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetProjectByIdQuery(Query):
    """根据ID获取项目查询"""

    query_id: str
    project_id: str
    include_statistics: bool = True
    include_contributors: bool = True
    include_tasks: bool = False
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetProjectsByStatusQuery(Query):
    """根据状态获取项目查询"""

    query_id: str
    status: str  # draft, active, paused, completed, archived
    limit: int = 100
    offset: int = 0
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetUserProjectsQuery(Query):
    """获取用户参与的项目查询"""

    query_id: str
    query_user_id: str  # 重命名以避免与父类冲突
    include_archived: bool = False
    user_id: str | None = None  # 这是查询者的ID
    role: str | None = None  # translator, reviewer, manager
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetTranslationsQuery(Query):
    """获取翻译查询"""

    query_id: str
    mod_id: str
    language: str
    include_metadata: bool = False
    user_id: str | None = None
    status: str | None = None  # pending, approved, rejected
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetTranslationProgressQuery(Query):
    """获取翻译进度查询"""

    query_id: str
    user_id: str | None = None
    mod_ids: list[str] | None = None
    project_id: str | None = None
    languages: list[str] | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetTranslationStatsQuery(Query):
    """获取翻译统计查询"""

    query_id: str
    user_id: str | None = None
    mod_id: str | None = None
    project_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetUntranslatedKeysQuery(Query):
    """获取未翻译键查询"""

    query_id: str
    mod_id: str
    language: str
    limit: int = 1000


@dataclass
class GetConflictsQuery(Query):
    """获取冲突查询"""

    query_id: str
    unresolved_only: bool = True
    mod_id: str | None = None
    language: str | None = None


@dataclass
class GetTasksQuery(Query):
    """获取任务查询"""

    query_id: str
    overdue_only: bool = False
    project_id: str | None = None
    assigned_to: str | None = None
    status: str | None = None  # pending, in_progress, completed, cancelled
    language: str | None = None


@dataclass
class GetContributorStatsQuery(Query):
    """获取贡献者统计查询"""

    query_id: str
    project_id: str | None = None
    user_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


@dataclass
class GetScanHistoryQuery(Query):
    """获取扫描历史查询"""

    query_id: str
    limit: int = 50
    include_results: bool = False
    mod_id: str | None = None


@dataclass
class GetSyncHistoryQuery(Query):
    """获取同步历史查询"""

    query_id: str
    limit: int = 100
    start_date: datetime | None = None
    end_date: datetime | None = None


@dataclass
class GetTerminologyQuery(Query):
    """获取术语查询"""

    query_id: str
    language: str
    term: str | None = None
    category: str | None = None


@dataclass
class GetQualityMetricsQuery(Query):
    """获取质量指标查询"""

    query_id: str
    mod_id: str | None = None
    project_id: str | None = None
    language: str | None = None


@dataclass
class GetRecentActivityQuery(Query):
    """获取最近活动查询"""

    query_id: str
    limit: int = 50
    project_id: str | None = None
    user_id: str | None = None
    activity_types: list[str] | None = None


@dataclass
class GetModDependenciesQuery(Query):
    """获取模组依赖查询"""

    query_id: str
    mod_id: str
    include_optional: bool = True
    resolve_transitive: bool = False


@dataclass
class GetLanguageCoverageQuery(Query):
    """获取语言覆盖率查询"""

    query_id: str
    mod_ids: list[str] | None = None
    project_id: str | None = None
    target_languages: list[str] | None = None


@dataclass
class SearchTranslationsQuery(Query):
    """搜索翻译查询"""

    query_id: str
    search_term: str
    search_in_keys: bool = True
    search_in_values: bool = True
    limit: int = 100
    language: str | None = None
    mod_ids: list[str] | None = None


@dataclass
class GetDuplicateTranslationsQuery(Query):
    """获取重复翻译查询"""

    query_id: str
    language: str
    threshold: float = 0.9  # 相似度阈值
    mod_ids: list[str] | None = None


@dataclass
class GetTranslationHistoryQuery(Query):
    """获取翻译历史查询"""

    query_id: str
    mod_id: str
    language: str
    key: str
    limit: int = 20


@dataclass
class GetProjectTimelineQuery(Query):
    """获取项目时间线查询"""

    query_id: str
    project_id: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    event_types: list[str] | None = None
