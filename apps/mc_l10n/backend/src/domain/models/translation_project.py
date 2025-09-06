"""
TranslationProject聚合
翻译项目管理领域模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum

from .mod import ModId


class ProjectStatus(Enum):
    """项目状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TranslationStrategy(Enum):
    """翻译策略"""
    MANUAL = "manual"              # 手动翻译
    MACHINE = "machine"            # 机器翻译
    HYBRID = "hybrid"              # 混合模式
    CROWDSOURCED = "crowdsourced" # 众包翻译


@dataclass
class ProjectSettings:
    """项目设置值对象"""
    auto_scan: bool = True
    scan_interval: int = 3600  # 秒
    auto_sync: bool = False
    sync_interval: int = 7200
    translation_strategy: TranslationStrategy = TranslationStrategy.MANUAL
    quality_threshold: float = 0.8
    require_review: bool = True
    allow_partial_translation: bool = True
    
    def validate(self) -> bool:
        """验证设置"""
        if self.scan_interval < 60:
            raise ValueError("Scan interval must be at least 60 seconds")
        if self.sync_interval < 60:
            raise ValueError("Sync interval must be at least 60 seconds")
        if not 0 <= self.quality_threshold <= 1:
            raise ValueError("Quality threshold must be between 0 and 1")
        return True


@dataclass
class Contributor:
    """贡献者值对象"""
    user_id: str
    name: str
    role: str  # translator, reviewer, manager
    languages: Set[str]
    contribution_count: int = 0
    joined_at: datetime = field(default_factory=datetime.now)
    
    def can_translate(self, language: str) -> bool:
        """检查是否可以翻译指定语言"""
        return language in self.languages and self.role in ["translator", "reviewer", "manager"]
    
    def can_review(self) -> bool:
        """检查是否可以审核"""
        return self.role in ["reviewer", "manager"]
    
    def can_manage(self) -> bool:
        """检查是否可以管理"""
        return self.role == "manager"


@dataclass
class TranslationTask:
    """翻译任务值对象"""
    task_id: str
    mod_id: ModId
    language: str
    assigned_to: Optional[str] = None
    priority: int = 0  # 0=low, 1=normal, 2=high
    deadline: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def assign(self, user_id: str):
        """分配任务"""
        self.assigned_to = user_id
        self.status = "in_progress"
    
    def complete(self):
        """完成任务"""
        self.status = "completed"
        self.completed_at = datetime.now()
    
    def cancel(self):
        """取消任务"""
        self.status = "cancelled"
    
    def is_overdue(self) -> bool:
        """检查是否逾期"""
        if self.deadline and self.status not in ["completed", "cancelled"]:
            return datetime.now() > self.deadline
        return False


class TranslationProject:
    """翻译项目聚合根"""
    
    def __init__(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        target_languages: Optional[Set[str]] = None
    ):
        self.project_id = project_id
        self.name = name
        self.description = description
        self.target_languages = target_languages or set()
        self.mod_ids: Set[ModId] = set()
        self.status = ProjectStatus.DRAFT
        self.settings = ProjectSettings()
        self.contributors: Dict[str, Contributor] = {}
        self.tasks: List[TranslationTask] = []
        self.statistics: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.domain_events = []
    
    def add_mod(self, mod_id: ModId):
        """添加模组到项目"""
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Cannot add mods to archived project")
        
        self.mod_ids.add(mod_id)
        self.updated_at = datetime.now()
        
        # 为每个目标语言创建任务
        for language in self.target_languages:
            self._create_task(mod_id, language)
    
    def remove_mod(self, mod_id: ModId):
        """从项目移除模组"""
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Cannot remove mods from archived project")
        
        self.mod_ids.discard(mod_id)
        
        # 取消相关任务
        for task in self.tasks:
            if task.mod_id == mod_id and task.status in ["pending", "in_progress"]:
                task.cancel()
        
        self.updated_at = datetime.now()
    
    def add_contributor(self, contributor: Contributor):
        """添加贡献者"""
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Cannot add contributors to archived project")
        
        self.contributors[contributor.user_id] = contributor
        self.updated_at = datetime.now()
    
    def remove_contributor(self, user_id: str):
        """移除贡献者"""
        if user_id in self.contributors:
            # 重新分配该用户的任务
            for task in self.tasks:
                if task.assigned_to == user_id and task.status == "in_progress":
                    task.assigned_to = None
                    task.status = "pending"
            
            del self.contributors[user_id]
            self.updated_at = datetime.now()
    
    def add_target_language(self, language: str):
        """添加目标语言"""
        if language not in self.target_languages:
            self.target_languages.add(language)
            
            # 为所有模组创建新语言的任务
            for mod_id in self.mod_ids:
                self._create_task(mod_id, language)
            
            self.updated_at = datetime.now()
    
    def remove_target_language(self, language: str):
        """移除目标语言"""
        self.target_languages.discard(language)
        
        # 取消相关任务
        for task in self.tasks:
            if task.language == language and task.status in ["pending", "in_progress"]:
                task.cancel()
        
        self.updated_at = datetime.now()
    
    def assign_task(self, task_id: str, user_id: str):
        """分配任务"""
        task = self._get_task(task_id)
        contributor = self.contributors.get(user_id)
        
        if not contributor:
            raise ValueError(f"Contributor {user_id} not found")
        
        if not contributor.can_translate(task.language):
            raise ValueError(f"Contributor cannot translate {task.language}")
        
        task.assign(user_id)
        self.updated_at = datetime.now()
    
    def complete_task(self, task_id: str):
        """完成任务"""
        task = self._get_task(task_id)
        task.complete()
        
        # 更新贡献者统计
        if task.assigned_to and task.assigned_to in self.contributors:
            self.contributors[task.assigned_to].contribution_count += 1
        
        self.updated_at = datetime.now()
        self._update_statistics()
    
    def activate(self):
        """激活项目"""
        if self.status != ProjectStatus.DRAFT:
            raise ValueError("Only draft projects can be activated")
        
        self.status = ProjectStatus.ACTIVE
        self.updated_at = datetime.now()
    
    def pause(self):
        """暂停项目"""
        if self.status != ProjectStatus.ACTIVE:
            raise ValueError("Only active projects can be paused")
        
        self.status = ProjectStatus.PAUSED
        self.updated_at = datetime.now()
    
    def complete(self):
        """完成项目"""
        # 检查是否所有任务都已完成
        incomplete_tasks = [t for t in self.tasks if t.status not in ["completed", "cancelled"]]
        
        if incomplete_tasks and not self.settings.allow_partial_translation:
            raise ValueError(f"Cannot complete project with {len(incomplete_tasks)} incomplete tasks")
        
        self.status = ProjectStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def archive(self):
        """归档项目"""
        if self.status not in [ProjectStatus.COMPLETED, ProjectStatus.PAUSED]:
            raise ValueError("Only completed or paused projects can be archived")
        
        self.status = ProjectStatus.ARCHIVED
        self.updated_at = datetime.now()
    
    def get_progress(self) -> Dict[str, float]:
        """获取项目进度"""
        progress = {}
        
        for language in self.target_languages:
            tasks = [t for t in self.tasks if t.language == language]
            if tasks:
                completed = sum(1 for t in tasks if t.status == "completed")
                progress[language] = (completed / len(tasks)) * 100
            else:
                progress[language] = 0.0
        
        return progress
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取项目统计"""
        return {
            'total_mods': len(self.mod_ids),
            'total_languages': len(self.target_languages),
            'total_tasks': len(self.tasks),
            'completed_tasks': sum(1 for t in self.tasks if t.status == "completed"),
            'pending_tasks': sum(1 for t in self.tasks if t.status == "pending"),
            'in_progress_tasks': sum(1 for t in self.tasks if t.status == "in_progress"),
            'total_contributors': len(self.contributors),
            'progress': self.get_progress()
        }
    
    def _create_task(self, mod_id: ModId, language: str):
        """创建翻译任务"""
        task = TranslationTask(
            task_id=f"{self.project_id}_{mod_id}_{language}",
            mod_id=mod_id,
            language=language
        )
        self.tasks.append(task)
    
    def _get_task(self, task_id: str) -> TranslationTask:
        """获取任务"""
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return task
    
    def _update_statistics(self):
        """更新统计信息"""
        self.statistics = self.get_statistics()