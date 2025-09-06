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
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None


@dataclass
class GetModByIdQuery(Query):
    """根据ID获取模组查询"""
    mod_id: str
    include_translations: bool = True
    include_metadata: bool = True


@dataclass
class GetModsByStatusQuery(Query):
    """根据状态获取模组查询"""
    status: str  # pending, scanning, completed, failed
    limit: int = 100
    offset: int = 0


@dataclass
class SearchModsQuery(Query):
    """搜索模组查询"""
    search_term: str
    search_in: List[str] = field(default_factory=lambda: ['name', 'id', 'description'])
    limit: int = 50


@dataclass
class GetProjectByIdQuery(Query):
    """根据ID获取项目查询"""
    project_id: str
    include_statistics: bool = True
    include_contributors: bool = True
    include_tasks: bool = False


@dataclass
class GetProjectsByStatusQuery(Query):
    """根据状态获取项目查询"""
    status: str  # draft, active, paused, completed, archived
    limit: int = 100
    offset: int = 0


@dataclass
class GetUserProjectsQuery(Query):
    """获取用户参与的项目查询"""
    user_id: str
    role: Optional[str] = None  # translator, reviewer, manager
    include_archived: bool = False


@dataclass
class GetTranslationsQuery(Query):
    """获取翻译查询"""
    mod_id: str
    language: str
    status: Optional[str] = None  # pending, approved, rejected
    include_metadata: bool = False


@dataclass
class GetTranslationProgressQuery(Query):
    """获取翻译进度查询"""
    mod_ids: Optional[List[str]] = None
    project_id: Optional[str] = None
    languages: Optional[List[str]] = None


@dataclass
class GetTranslationStatsQuery(Query):
    """获取翻译统计查询"""
    mod_id: Optional[str] = None
    project_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class GetUntranslatedKeysQuery(Query):
    """获取未翻译键查询"""
    mod_id: str
    language: str
    limit: int = 1000


@dataclass
class GetConflictsQuery(Query):
    """获取冲突查询"""
    mod_id: Optional[str] = None
    language: Optional[str] = None
    unresolved_only: bool = True


@dataclass
class GetTasksQuery(Query):
    """获取任务查询"""
    project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, completed, cancelled
    language: Optional[str] = None
    overdue_only: bool = False


@dataclass
class GetContributorStatsQuery(Query):
    """获取贡献者统计查询"""
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class GetScanHistoryQuery(Query):
    """获取扫描历史查询"""
    mod_id: Optional[str] = None
    limit: int = 50
    include_results: bool = False


@dataclass
class GetSyncHistoryQuery(Query):
    """获取同步历史查询"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100


@dataclass
class GetTerminologyQuery(Query):
    """获取术语查询"""
    language: str
    term: Optional[str] = None
    category: Optional[str] = None


@dataclass
class GetQualityMetricsQuery(Query):
    """获取质量指标查询"""
    mod_id: Optional[str] = None
    project_id: Optional[str] = None
    language: Optional[str] = None


@dataclass
class GetRecentActivityQuery(Query):
    """获取最近活动查询"""
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    activity_types: Optional[List[str]] = None
    limit: int = 50


@dataclass
class GetModDependenciesQuery(Query):
    """获取模组依赖查询"""
    mod_id: str
    include_optional: bool = True
    resolve_transitive: bool = False


@dataclass
class GetLanguageCoverageQuery(Query):
    """获取语言覆盖率查询"""
    mod_ids: Optional[List[str]] = None
    project_id: Optional[str] = None
    target_languages: Optional[List[str]] = None


@dataclass
class SearchTranslationsQuery(Query):
    """搜索翻译查询"""
    search_term: str
    language: Optional[str] = None
    mod_ids: Optional[List[str]] = None
    search_in_keys: bool = True
    search_in_values: bool = True
    limit: int = 100


@dataclass
class GetDuplicateTranslationsQuery(Query):
    """获取重复翻译查询"""
    language: str
    mod_ids: Optional[List[str]] = None
    threshold: float = 0.9  # 相似度阈值


@dataclass
class GetTranslationHistoryQuery(Query):
    """获取翻译历史查询"""
    mod_id: str
    language: str
    key: str
    limit: int = 20


@dataclass
class GetProjectTimelineQuery(Query):
    """获取项目时间线查询"""
    project_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_types: Optional[List[str]] = None