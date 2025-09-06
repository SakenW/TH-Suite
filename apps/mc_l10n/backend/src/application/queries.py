"""
应用层查询对象
CQRS模式中的查询定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
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
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetModsByStatusQuery(Query):
    """根据状态获取模组查询"""
    query_id: str
    status: str  # pending, scanning, completed, failed
    limit: int = 100
    offset: int = 0
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SearchModsQuery(Query):
    """搜索模组查询"""
    query_id: str
    search_term: str
    limit: int = 50
    user_id: Optional[str] = None
    search_in: List[str] = field(default_factory=lambda: ['name', 'id', 'description'])
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetProjectByIdQuery(Query):
    """根据ID获取项目查询"""
    query_id: str
    project_id: str
    include_statistics: bool = True
    include_contributors: bool = True
    include_tasks: bool = False
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetProjectsByStatusQuery(Query):
    """根据状态获取项目查询"""
    query_id: str
    status: str  # draft, active, paused, completed, archived
    limit: int = 100
    offset: int = 0
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetUserProjectsQuery(Query):
    """获取用户参与的项目查询"""
    query_id: str
    query_user_id: str  # 重命名以避免与父类冲突
    include_archived: bool = False
    user_id: Optional[str] = None  # 这是查询者的ID
    role: Optional[str] = None  # translator, reviewer, manager
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetTranslationsQuery(Query):
    """获取翻译查询"""
    query_id: str
    mod_id: str
    language: str
    include_metadata: bool = False
    user_id: Optional[str] = None
    status: Optional[str] = None  # pending, approved, rejected
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetTranslationProgressQuery(Query):
    """获取翻译进度查询"""
    query_id: str
    user_id: Optional[str] = None
    mod_ids: Optional[List[str]] = None
    project_id: Optional[str] = None
    languages: Optional[List[str]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GetTranslationStatsQuery(Query):
    """获取翻译统计查询"""
    query_id: str
    user_id: Optional[str] = None
    mod_id: Optional[str] = None
    project_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
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
    mod_id: Optional[str] = None
    language: Optional[str] = None


@dataclass
class GetTasksQuery(Query):
    """获取任务查询"""
    query_id: str
    overdue_only: bool = False
    project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, completed, cancelled
    language: Optional[str] = None


@dataclass
class GetContributorStatsQuery(Query):
    """获取贡献者统计查询"""
    query_id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class GetScanHistoryQuery(Query):
    """获取扫描历史查询"""
    query_id: str
    limit: int = 50
    include_results: bool = False
    mod_id: Optional[str] = None


@dataclass
class GetSyncHistoryQuery(Query):
    """获取同步历史查询"""
    query_id: str
    limit: int = 100
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class GetTerminologyQuery(Query):
    """获取术语查询"""
    query_id: str
    language: str
    term: Optional[str] = None
    category: Optional[str] = None


@dataclass
class GetQualityMetricsQuery(Query):
    """获取质量指标查询"""
    query_id: str
    mod_id: Optional[str] = None
    project_id: Optional[str] = None
    language: Optional[str] = None


@dataclass
class GetRecentActivityQuery(Query):
    """获取最近活动查询"""
    query_id: str
    limit: int = 50
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    activity_types: Optional[List[str]] = None


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
    mod_ids: Optional[List[str]] = None
    project_id: Optional[str] = None
    target_languages: Optional[List[str]] = None


@dataclass
class SearchTranslationsQuery(Query):
    """搜索翻译查询"""
    query_id: str
    search_term: str
    search_in_keys: bool = True
    search_in_values: bool = True
    limit: int = 100
    language: Optional[str] = None
    mod_ids: Optional[List[str]] = None


@dataclass
class GetDuplicateTranslationsQuery(Query):
    """获取重复翻译查询"""
    query_id: str
    language: str
    threshold: float = 0.9  # 相似度阈值
    mod_ids: Optional[List[str]] = None


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
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_types: Optional[List[str]] = None