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


class ScanCommand(Command):
    """扫描命令"""
    def __init__(
        self,
        command_id: str,
        directory_path: str,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        recursive: bool = True,
        force_rescan: bool = False,
        save_results: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.directory_path = directory_path
        self.include_patterns = include_patterns or ['*.jar', '*.zip']
        self.exclude_patterns = exclude_patterns or []
        self.recursive = recursive
        self.force_rescan = force_rescan
        self.save_results = save_results


class RescanCommand(Command):
    """重新扫描命令"""
    def __init__(
        self,
        command_id: str,
        only_changed: bool = True,
        remove_missing: bool = False,
        update_metadata: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.only_changed = only_changed
        self.remove_missing = remove_missing
        self.update_metadata = update_metadata


class CreateProjectCommand(Command):
    """创建项目命令"""
    def __init__(
        self,
        command_id: str,
        name: str,
        description: Optional[str] = None,
        target_languages: Set[str] = None,
        auto_scan: bool = True,
        scan_interval: int = 3600,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.name = name
        self.description = description
        self.target_languages = target_languages or set()
        self.auto_scan = auto_scan
        self.scan_interval = scan_interval


class AddModToProjectCommand(Command):
    """添加模组到项目命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        mod_ids: List[str],
        create_tasks: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.mod_ids = mod_ids
        self.create_tasks = create_tasks


class AssignTaskCommand(Command):
    """分配任务命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        task_id: str,
        assignee_id: str,
        deadline: Optional[datetime] = None,
        priority: int = 1,  # 0=low, 1=normal, 2=high
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.task_id = task_id
        self.assignee_id = assignee_id
        self.deadline = deadline
        self.priority = priority


class TranslateCommand(Command):
    """翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_id: str,
        source_language: str,
        target_language: str,
        translations: Dict[str, str],
        translator_id: Optional[str] = None,
        auto_approve: bool = False,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_id = mod_id
        self.source_language = source_language
        self.target_language = target_language
        self.translations = translations
        self.translator_id = translator_id
        self.auto_approve = auto_approve


class ApproveTranslationCommand(Command):
    """批准翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_id: str,
        language: str,
        keys: List[str],
        reviewer_id: str,
        comments: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_id = mod_id
        self.language = language
        self.keys = keys
        self.reviewer_id = reviewer_id
        self.comments = comments


class RejectTranslationCommand(Command):
    """拒绝翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_id: str,
        language: str,
        keys: List[str],
        reviewer_id: str,
        reason: str,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_id = mod_id
        self.language = language
        self.keys = keys
        self.reviewer_id = reviewer_id
        self.reason = reason


class SyncCommand(Command):
    """同步命令"""
    def __init__(
        self,
        command_id: str,
        source: str,  # local or remote
        target: str,  # local or remote
        conflict_resolution: str = "manual",  # manual, local_wins, remote_wins
        dry_run: bool = False,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.source = source
        self.target = target
        self.conflict_resolution = conflict_resolution
        self.dry_run = dry_run


class ExportTranslationsCommand(Command):
    """导出翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_ids: List[str],
        languages: List[str],
        output_path: str,
        format: str = "json",  # json, properties, yaml
        include_metadata: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_ids = mod_ids
        self.languages = languages
        self.format = format
        self.output_path = output_path
        self.include_metadata = include_metadata


class ImportTranslationsCommand(Command):
    """导入翻译命令"""
    def __init__(
        self,
        command_id: str,
        file_path: str,
        language: str,
        format: str = "json",
        overwrite: bool = False,
        validate: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.file_path = file_path
        self.format = format
        self.language = language
        self.overwrite = overwrite
        self.validate = validate


class MergeTranslationsCommand(Command):
    """合并翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_id: str,
        language: str,
        source_translations: Dict[str, str],
        merge_strategy: str = "override",  # override, keep_existing, smart
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_id = mod_id
        self.language = language
        self.source_translations = source_translations
        self.merge_strategy = merge_strategy


class DeleteModCommand(Command):
    """删除模组命令"""
    def __init__(
        self,
        command_id: str,
        mod_id: str,
        delete_translations: bool = True,
        delete_from_projects: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_id = mod_id
        self.delete_translations = delete_translations
        self.delete_from_projects = delete_from_projects


class UpdateProjectSettingsCommand(Command):
    """更新项目设置命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        auto_scan: Optional[bool] = None,
        scan_interval: Optional[int] = None,
        auto_sync: Optional[bool] = None,
        sync_interval: Optional[int] = None,
        quality_threshold: Optional[float] = None,
        require_review: Optional[bool] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.auto_scan = auto_scan
        self.scan_interval = scan_interval
        self.auto_sync = auto_sync
        self.sync_interval = sync_interval
        self.quality_threshold = quality_threshold
        self.require_review = require_review


class AddContributorCommand(Command):
    """添加贡献者命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        contributor_user_id: str,
        name: str,
        role: str,  # translator, reviewer, manager
        languages: Set[str],
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.contributor_user_id = contributor_user_id
        self.name = name
        self.role = role
        self.languages = languages


class RemoveContributorCommand(Command):
    """移除贡献者命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        contributor_user_id: str,
        reassign_tasks: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.contributor_user_id = contributor_user_id
        self.reassign_tasks = reassign_tasks


class CompleteTaskCommand(Command):
    """完成任务命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        task_id: str,
        completed_by: str,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.task_id = task_id
        self.completed_by = completed_by
        self.notes = notes


class CancelTaskCommand(Command):
    """取消任务命令"""
    def __init__(
        self,
        command_id: str,
        project_id: str,
        task_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.task_id = task_id
        self.reason = reason


class BatchTranslateCommand(Command):
    """批量翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_ids: List[str],
        source_language: str,
        target_language: str,
        translation_provider: str,  # manual, machine, glossary
        auto_approve: bool = False,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_ids = mod_ids
        self.source_language = source_language
        self.target_language = target_language
        self.translation_provider = translation_provider
        self.auto_approve = auto_approve


class ValidateTranslationsCommand(Command):
    """验证翻译命令"""
    def __init__(
        self,
        command_id: str,
        mod_id: str,
        language: str,
        check_completeness: bool = True,
        check_consistency: bool = True,
        check_terminology: bool = True,
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.mod_id = mod_id
        self.language = language
        self.check_completeness = check_completeness
        self.check_consistency = check_consistency
        self.check_terminology = check_terminology


class GenerateReportCommand(Command):
    """生成报告命令"""
    def __init__(
        self,
        command_id: str,
        project_id: Optional[str] = None,
        report_type: str = "progress",  # progress, quality, contributor
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        output_format: str = "html",  # html, pdf, json
        user_id: Optional[str] = None
    ):
        super().__init__(command_id, user_id=user_id)
        self.project_id = project_id
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        self.output_format = output_format