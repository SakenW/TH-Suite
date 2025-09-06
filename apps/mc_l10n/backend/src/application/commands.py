"""
应用层命令对象
CQRS模式中的命令定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime


@dataclass
class Command:
    """命令基类"""
    command_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None


@dataclass
class ScanCommand(Command):
    """扫描命令"""
    directory_path: str
    include_patterns: List[str] = field(default_factory=lambda: ['*.jar', '*.zip'])
    exclude_patterns: List[str] = field(default_factory=list)
    recursive: bool = True
    force_rescan: bool = False
    save_results: bool = True


@dataclass
class RescanCommand(Command):
    """重新扫描命令"""
    only_changed: bool = True
    remove_missing: bool = False
    update_metadata: bool = True


@dataclass
class CreateProjectCommand(Command):
    """创建项目命令"""
    name: str
    description: Optional[str] = None
    target_languages: Set[str] = field(default_factory=set)
    auto_scan: bool = True
    scan_interval: int = 3600


@dataclass
class AddModToProjectCommand(Command):
    """添加模组到项目命令"""
    project_id: str
    mod_ids: List[str]
    create_tasks: bool = True


@dataclass
class AssignTaskCommand(Command):
    """分配任务命令"""
    project_id: str
    task_id: str
    assignee_id: str
    deadline: Optional[datetime] = None
    priority: int = 1  # 0=low, 1=normal, 2=high


@dataclass
class TranslateCommand(Command):
    """翻译命令"""
    mod_id: str
    source_language: str
    target_language: str
    translations: Dict[str, str]
    translator_id: Optional[str] = None
    auto_approve: bool = False


@dataclass
class ApproveTranslationCommand(Command):
    """批准翻译命令"""
    mod_id: str
    language: str
    keys: List[str]
    reviewer_id: str
    comments: Optional[str] = None


@dataclass
class RejectTranslationCommand(Command):
    """拒绝翻译命令"""
    mod_id: str
    language: str
    keys: List[str]
    reviewer_id: str
    reason: str


@dataclass
class SyncCommand(Command):
    """同步命令"""
    source: str  # local or remote
    target: str  # local or remote
    conflict_resolution: str = "manual"  # manual, local_wins, remote_wins
    dry_run: bool = False


@dataclass
class ExportTranslationsCommand(Command):
    """导出翻译命令"""
    mod_ids: List[str]
    languages: List[str]
    format: str = "json"  # json, properties, yaml
    output_path: str
    include_metadata: bool = True


@dataclass
class ImportTranslationsCommand(Command):
    """导入翻译命令"""
    file_path: str
    format: str = "json"
    language: str
    overwrite: bool = False
    validate: bool = True


@dataclass
class MergeTranslationsCommand(Command):
    """合并翻译命令"""
    mod_id: str
    language: str
    source_translations: Dict[str, str]
    merge_strategy: str = "override"  # override, keep_existing, smart


@dataclass
class DeleteModCommand(Command):
    """删除模组命令"""
    mod_id: str
    delete_translations: bool = True
    delete_from_projects: bool = True


@dataclass
class UpdateProjectSettingsCommand(Command):
    """更新项目设置命令"""
    project_id: str
    auto_scan: Optional[bool] = None
    scan_interval: Optional[int] = None
    auto_sync: Optional[bool] = None
    sync_interval: Optional[int] = None
    quality_threshold: Optional[float] = None
    require_review: Optional[bool] = None


@dataclass
class AddContributorCommand(Command):
    """添加贡献者命令"""
    project_id: str
    user_id: str
    name: str
    role: str  # translator, reviewer, manager
    languages: Set[str]


@dataclass
class RemoveContributorCommand(Command):
    """移除贡献者命令"""
    project_id: str
    user_id: str
    reassign_tasks: bool = True


@dataclass
class CompleteTaskCommand(Command):
    """完成任务命令"""
    project_id: str
    task_id: str
    completed_by: str
    notes: Optional[str] = None


@dataclass
class CancelTaskCommand(Command):
    """取消任务命令"""
    project_id: str
    task_id: str
    reason: Optional[str] = None


@dataclass
class BatchTranslateCommand(Command):
    """批量翻译命令"""
    mod_ids: List[str]
    source_language: str
    target_language: str
    translation_provider: str  # manual, machine, glossary
    auto_approve: bool = False


@dataclass
class ValidateTranslationsCommand(Command):
    """验证翻译命令"""
    mod_id: str
    language: str
    check_completeness: bool = True
    check_consistency: bool = True
    check_terminology: bool = True


@dataclass
class GenerateReportCommand(Command):
    """生成报告命令"""
    project_id: Optional[str] = None
    report_type: str = "progress"  # progress, quality, contributor
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    output_format: str = "html"  # html, pdf, json