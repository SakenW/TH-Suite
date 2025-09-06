"""
TranslationProject聚合
翻译项目管理领域模型
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
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
    """翻译项目聚合根
    
    负责维护翻译项目的完整性和业务规则：
    - 管理项目生命周期
    - 协调模组、贡献者和任务
    - 确保翻译流程的一致性
    - 跟踪项目进度和质量
    """
    
    # 业务常量
    MAX_MODS_PER_PROJECT = 100
    MAX_CONTRIBUTORS = 50
    MAX_LANGUAGES = 20
    MIN_QUALITY_THRESHOLD = 0.5
    
    def __init__(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        target_languages: Optional[Set[str]] = None
    ):
        # 验证输入
        if not project_id:
            raise ValueError("Project ID is required")
        if not name or len(name) < 3:
            raise ValueError("Project name must be at least 3 characters")
        
        self.project_id = project_id
        self.name = name
        self.description = description
        self.target_languages = target_languages or set()
        
        # 验证目标语言数量
        if len(self.target_languages) > self.MAX_LANGUAGES:
            raise ValueError(f"Cannot have more than {self.MAX_LANGUAGES} target languages")
        
        self.mod_ids: Set[ModId] = set()
        self.status = ProjectStatus.DRAFT
        self.settings = ProjectSettings()
        self.contributors: Dict[str, Contributor] = {}
        self.tasks: List[TranslationTask] = []
        self.statistics: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.domain_events = []
        
        # 新增：业务状态
        self.owner_id: Optional[str] = None
        self.quality_metrics: Dict[str, float] = {}
        self.completion_date: Optional[datetime] = None
        self.review_required_count = 0
        self.auto_assignment_enabled = False
    
    def add_mod(self, mod_id: ModId):
        """添加模组到项目
        
        业务规则：
        - 只能在非归档状态添加
        - 不能超过最大模组数量
        - 自动创建翻译任务
        - 如果启用自动分配，尝试分配任务
        """
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Cannot add mods to archived project")
        
        if self.status == ProjectStatus.COMPLETED:
            raise ValueError("Cannot add mods to completed project")
        
        if len(self.mod_ids) >= self.MAX_MODS_PER_PROJECT:
            raise ValueError(f"Cannot add more than {self.MAX_MODS_PER_PROJECT} mods to a project")
        
        if mod_id in self.mod_ids:
            raise ValueError(f"Mod {mod_id} is already in the project")
        
        self.mod_ids.add(mod_id)
        self.updated_at = datetime.now()
        
        # 为每个目标语言创建任务
        for language in self.target_languages:
            task = self._create_task(mod_id, language)
            
            # 自动分配任务给可用的贡献者
            if self.auto_assignment_enabled:
                self._auto_assign_task(task)
    
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
        """添加贡献者
        
        业务规则：
        - 只能在非归档状态添加
        - 不能超过最大贡献者数量
        - 验证贡献者的语言能力
        - 第一个贡献者成为项目负责人（如果是manager角色）
        """
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Cannot add contributors to archived project")
        
        if len(self.contributors) >= self.MAX_CONTRIBUTORS:
            raise ValueError(f"Cannot have more than {self.MAX_CONTRIBUTORS} contributors")
        
        if contributor.user_id in self.contributors:
            raise ValueError(f"Contributor {contributor.user_id} is already in the project")
        
        # 验证贡献者的语言能力与项目需求匹配
        if contributor.languages:
            matching_languages = contributor.languages.intersection(self.target_languages)
            if not matching_languages and contributor.role != "manager":
                raise ValueError("Contributor's languages don't match project's target languages")
        
        self.contributors[contributor.user_id] = contributor
        
        # 第一个manager成为项目负责人
        if not self.owner_id and contributor.can_manage():
            self.owner_id = contributor.user_id
        
        self.updated_at = datetime.now()
        
        # 如果启用自动分配，为新贡献者分配待处理任务
        if self.auto_assignment_enabled:
            self._assign_pending_tasks_to_contributor(contributor)
    
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
        """分配任务
        
        业务规则：
        - 只能分配给项目贡献者
        - 贡献者必须具备相应语言能力
        - 不能分配给已有过多任务的贡献者
        - 优先级高的任务优先分配
        """
        if self.status not in [ProjectStatus.ACTIVE, ProjectStatus.PAUSED]:
            raise ValueError(f"Cannot assign tasks in {self.status.value} project")
        
        task = self._get_task(task_id)
        
        if task.status == "completed":
            raise ValueError("Cannot assign completed task")
        
        if task.status == "cancelled":
            raise ValueError("Cannot assign cancelled task")
        
        contributor = self.contributors.get(user_id)
        
        if not contributor:
            raise ValueError(f"Contributor {user_id} not found")
        
        if not contributor.can_translate(task.language):
            raise ValueError(f"Contributor cannot translate {task.language}")
        
        # 检查贡献者的任务负载
        active_tasks = self._get_contributor_active_tasks(user_id)
        if len(active_tasks) >= 10:  # 每人最多10个活跃任务
            raise ValueError(f"Contributor {user_id} has too many active tasks")
        
        task.assign(user_id)
        contributor.contribution_count += 1
        self.updated_at = datetime.now()
    
    def complete_task(self, task_id: str, quality_score: float = 1.0):
        """完成任务
        
        业务规则：
        - 只能完成已分配的任务
        - 记录质量分数
        - 更新项目进度
        - 检查是否所有任务完成
        """
        task = self._get_task(task_id)
        
        if task.status != "in_progress":
            raise ValueError("Can only complete in-progress tasks")
        
        if not task.assigned_to:
            raise ValueError("Cannot complete unassigned task")
        
        # 验证质量分数
        if not 0 <= quality_score <= 1:
            raise ValueError("Quality score must be between 0 and 1")
        
        task.complete()
        
        # 记录质量指标
        if task.language not in self.quality_metrics:
            self.quality_metrics[task.language] = quality_score
        else:
            # 计算平均质量
            completed_tasks = [t for t in self.tasks 
                             if t.language == task.language and t.status == "completed"]
            total_quality = self.quality_metrics[task.language] * (len(completed_tasks) - 1) + quality_score
            self.quality_metrics[task.language] = total_quality / len(completed_tasks)
        
        # 检查是否需要审核
        if quality_score < self.settings.quality_threshold:
            self.review_required_count += 1
        
        self.updated_at = datetime.now()
        self._update_statistics()
        
        # 检查是否所有任务完成
        if self._all_tasks_completed():
            self._trigger_completion_check()
    
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
    
    def _auto_assign_task(self, task: TranslationTask):
        """自动分配任务给合适的贡献者"""
        # 找到能处理该语言且任务最少的贡献者
        suitable_contributors = [
            (c, self._get_contributor_active_tasks(c.user_id))
            for c in self.contributors.values()
            if c.can_translate(task.language)
        ]
        
        if not suitable_contributors:
            return
        
        # 按任务数量排序，选择任务最少的
        suitable_contributors.sort(key=lambda x: len(x[1]))
        best_contributor = suitable_contributors[0][0]
        
        # 分配任务
        if len(self._get_contributor_active_tasks(best_contributor.user_id)) < 10:
            task.assign(best_contributor.user_id)
    
    def _assign_pending_tasks_to_contributor(self, contributor: Contributor):
        """为新贡献者分配待处理任务"""
        pending_tasks = [
            t for t in self.tasks 
            if t.status == "pending" and 
            t.language in contributor.languages
        ]
        
        # 按优先级排序
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        # 分配前5个任务
        for task in pending_tasks[:5]:
            task.assign(contributor.user_id)
    
    def _get_contributor_active_tasks(self, user_id: str) -> List[TranslationTask]:
        """获取贡献者的活跃任务"""
        return [
            t for t in self.tasks 
            if t.assigned_to == user_id and 
            t.status == "in_progress"
        ]
    
    def _all_tasks_completed(self) -> bool:
        """检查是否所有任务完成"""
        return all(
            t.status in ["completed", "cancelled"] 
            for t in self.tasks
        )
    
    def _trigger_completion_check(self):
        """触发项目完成检查"""
        # 计算整体质量分数
        if self.quality_metrics:
            avg_quality = sum(self.quality_metrics.values()) / len(self.quality_metrics)
            
            # 如果质量达标且允许完成，自动标记项目完成
            if avg_quality >= self.settings.quality_threshold:
                if self.settings.allow_partial_translation or self._all_tasks_completed():
                    self.status = ProjectStatus.COMPLETED
                    self.completion_date = datetime.now()
    
    def set_owner(self, user_id: str):
        """设置项目负责人"""
        if user_id not in self.contributors:
            raise ValueError(f"User {user_id} is not a contributor")
        
        if not self.contributors[user_id].can_manage():
            raise ValueError(f"User {user_id} does not have manager role")
        
        self.owner_id = user_id
        self.updated_at = datetime.now()
    
    def enable_auto_assignment(self):
        """启用自动任务分配"""
        self.auto_assignment_enabled = True
        # 立即尝试分配所有待处理任务
        for task in self.tasks:
            if task.status == "pending":
                self._auto_assign_task(task)
    
    def disable_auto_assignment(self):
        """禁用自动任务分配"""
        self.auto_assignment_enabled = False
    
    def calculate_estimated_completion(self) -> Optional[datetime]:
        """计算预估完成时间"""
        if not self.tasks:
            return None
        
        completed_tasks = [t for t in self.tasks if t.status == "completed"]
        if not completed_tasks:
            return None
        
        # 基于历史完成速度预估
        avg_completion_time = sum(
            (t.completed_at - t.created_at).total_seconds() 
            for t in completed_tasks if t.completed_at
        ) / len(completed_tasks)
        
        remaining_tasks = [t for t in self.tasks if t.status in ["pending", "in_progress"]]
        if not remaining_tasks:
            return self.completion_date
        
        estimated_seconds = avg_completion_time * len(remaining_tasks)
        return datetime.now() + timedelta(seconds=estimated_seconds)