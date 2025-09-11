"""
领域事件处理器
处理各种领域事件的具体逻辑
"""

import logging
from datetime import datetime

from ..domain.events import (
    ModScannedEvent,
    ModTranslatedEvent,
    ProjectCompletedEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TranslationApprovedEvent,
    TranslationConflictEvent,
    TranslationRejectedEvent,
)
from ..domain.repositories import (
    ModRepository,
    NotificationRepository,
    TranslationProjectRepository,
)
from .event_bus import get_event_bus

logger = logging.getLogger(__name__)


class ModEventHandler:
    """模组事件处理器"""

    def __init__(
        self,
        mod_repository: ModRepository,
        notification_repository: NotificationRepository | None = None,
    ):
        self.mod_repository = mod_repository
        self.notification_repository = notification_repository

        # 注册事件处理器
        self._register_handlers()

    def _register_handlers(self):
        """注册所有处理器"""
        bus = get_event_bus()

        bus.subscribe(ModScannedEvent, self.handle_mod_scanned, priority=10)
        bus.subscribe(ModTranslatedEvent, self.handle_mod_translated, priority=10)
        bus.subscribe(
            TranslationConflictEvent, self.handle_translation_conflict, priority=20
        )

    def handle_mod_scanned(self, event: ModScannedEvent):
        """处理模组扫描完成事件"""
        logger.info(f"Handling ModScannedEvent for mod {event.mod_id}")

        try:
            # 更新模组的扫描统计
            mod = self.mod_repository.get_by_id(event.mod_id)
            if mod:
                # 更新缓存或索引
                self._update_search_index(mod)

                # 发送通知
                if self.notification_repository:
                    self._create_notification(
                        f"Mod {event.mod_id} scanned successfully",
                        f"Found {event.translation_count} translations",
                        "success",
                    )

        except Exception as e:
            logger.error(f"Error handling ModScannedEvent: {e}")
            raise

    def handle_mod_translated(self, event: ModTranslatedEvent):
        """处理模组翻译完成事件"""
        logger.info(f"Handling ModTranslatedEvent for mod {event.mod_id}")

        try:
            # 更新翻译进度
            if event.progress >= 100:
                # 标记为完全翻译
                if self.notification_repository:
                    self._create_notification(
                        f"Mod {event.mod_id} fully translated",
                        f"Language: {event.language}",
                        "success",
                    )

            # 触发质量检查
            self._trigger_quality_check(event.mod_id, event.language)

        except Exception as e:
            logger.error(f"Error handling ModTranslatedEvent: {e}")
            raise

    def handle_translation_conflict(self, event: TranslationConflictEvent):
        """处理翻译冲突事件"""
        logger.warning(
            f"Translation conflict in mod {event.mod_id} "
            f"for key {event.key} in language {event.language}"
        )

        try:
            # 记录冲突
            self._log_conflict(event)

            # 发送通知给管理员
            if self.notification_repository:
                self._create_notification(
                    "Translation conflict detected",
                    f"Mod: {event.mod_id}, Key: {event.key}",
                    "warning",
                )

        except Exception as e:
            logger.error(f"Error handling TranslationConflictEvent: {e}")
            raise

    def _update_search_index(self, mod):
        """更新搜索索引"""
        # 实现搜索索引更新逻辑
        pass

    def _trigger_quality_check(self, mod_id: str, language: str):
        """触发质量检查"""
        # 实现质量检查逻辑
        pass

    def _log_conflict(self, event: TranslationConflictEvent):
        """记录冲突到数据库"""
        # 实现冲突记录逻辑
        pass

    def _create_notification(self, title: str, message: str, level: str):
        """创建通知"""
        if self.notification_repository:
            # 实现通知创建逻辑
            pass


class TranslationEventHandler:
    """翻译事件处理器"""

    def __init__(
        self,
        project_repository: TranslationProjectRepository,
        notification_repository: NotificationRepository | None = None,
    ):
        self.project_repository = project_repository
        self.notification_repository = notification_repository

        # 注册事件处理器
        self._register_handlers()

    def _register_handlers(self):
        """注册所有处理器"""
        bus = get_event_bus()

        bus.subscribe(TranslationApprovedEvent, self.handle_translation_approved)
        bus.subscribe(TranslationRejectedEvent, self.handle_translation_rejected)

    def handle_translation_approved(self, event: TranslationApprovedEvent):
        """处理翻译批准事件"""
        logger.info(f"Translation approved: {event.translation_id}")

        try:
            # 更新项目统计
            self._update_project_stats(event.mod_id, event.language, "approved")

            # 检查是否触发项目完成
            self._check_project_completion(event.mod_id)

            # 记录审核历史
            self._log_review_history(
                event.translation_id, event.approved_by, "approved", event.timestamp
            )

        except Exception as e:
            logger.error(f"Error handling TranslationApprovedEvent: {e}")
            raise

    def handle_translation_rejected(self, event: TranslationRejectedEvent):
        """处理翻译拒绝事件"""
        logger.info(f"Translation rejected: {event.translation_id}")

        try:
            # 更新项目统计
            self._update_project_stats(event.mod_id, event.language, "rejected")

            # 通知翻译者
            if self.notification_repository:
                self._notify_translator(event)

            # 记录审核历史
            self._log_review_history(
                event.translation_id,
                event.rejected_by,
                "rejected",
                event.timestamp,
                event.reason,
            )

        except Exception as e:
            logger.error(f"Error handling TranslationRejectedEvent: {e}")
            raise

    def _update_project_stats(self, mod_id: str, language: str, action: str):
        """更新项目统计"""
        # 实现项目统计更新逻辑
        pass

    def _check_project_completion(self, mod_id: str):
        """检查项目是否完成"""
        # 实现项目完成检查逻辑
        pass

    def _log_review_history(
        self,
        translation_id: str,
        reviewer: str,
        action: str,
        timestamp: datetime,
        reason: str | None = None,
    ):
        """记录审核历史"""
        # 实现审核历史记录逻辑
        pass

    def _notify_translator(self, event: TranslationRejectedEvent):
        """通知翻译者"""
        if self.notification_repository:
            # 实现翻译者通知逻辑
            pass


class ProjectEventHandler:
    """项目事件处理器"""

    def __init__(
        self,
        project_repository: TranslationProjectRepository,
        notification_repository: NotificationRepository | None = None,
    ):
        self.project_repository = project_repository
        self.notification_repository = notification_repository

        # 注册事件处理器
        self._register_handlers()

    def _register_handlers(self):
        """注册所有处理器"""
        bus = get_event_bus()

        bus.subscribe(ProjectCompletedEvent, self.handle_project_completed)
        bus.subscribe(TaskAssignedEvent, self.handle_task_assigned)
        bus.subscribe(TaskCompletedEvent, self.handle_task_completed)

    def handle_project_completed(self, event: ProjectCompletedEvent):
        """处理项目完成事件"""
        logger.info(f"Project completed: {event.project_id}")

        try:
            # 生成项目报告
            self._generate_project_report(event.project_id)

            # 通知所有贡献者
            self._notify_contributors(event.project_id)

            # 归档项目数据
            self._archive_project_data(event.project_id)

            # 触发后续流程（如自动发布）
            self._trigger_post_completion_workflow(event.project_id)

        except Exception as e:
            logger.error(f"Error handling ProjectCompletedEvent: {e}")
            raise

    def handle_task_assigned(self, event: TaskAssignedEvent):
        """处理任务分配事件"""
        logger.info(f"Task {event.task_id} assigned to {event.assignee}")

        try:
            # 通知被分配者
            if self.notification_repository:
                self._create_task_notification(
                    event.assignee, f"New task assigned: {event.task_id}", "info"
                )

            # 更新用户工作负载
            self._update_workload(event.assignee, 1)

        except Exception as e:
            logger.error(f"Error handling TaskAssignedEvent: {e}")
            raise

    def handle_task_completed(self, event: TaskCompletedEvent):
        """处理任务完成事件"""
        logger.info(f"Task completed: {event.task_id}")

        try:
            # 更新项目进度
            project = self._get_project_by_task(event.task_id)
            if project:
                self._update_project_progress(project.project_id)

            # 更新用户统计
            if event.completed_by:
                self._update_user_stats(event.completed_by, event.quality_score)

            # 检查里程碑
            self._check_milestones(project.project_id if project else None)

        except Exception as e:
            logger.error(f"Error handling TaskCompletedEvent: {e}")
            raise

    def _generate_project_report(self, project_id: str):
        """生成项目报告"""
        # 实现项目报告生成逻辑
        pass

    def _notify_contributors(self, project_id: str):
        """通知所有贡献者"""
        # 实现贡献者通知逻辑
        pass

    def _archive_project_data(self, project_id: str):
        """归档项目数据"""
        # 实现项目归档逻辑
        pass

    def _trigger_post_completion_workflow(self, project_id: str):
        """触发完成后工作流"""
        # 实现后续工作流逻辑
        pass

    def _create_task_notification(self, user_id: str, message: str, level: str):
        """创建任务通知"""
        if self.notification_repository:
            # 实现任务通知逻辑
            pass

    def _update_workload(self, user_id: str, delta: int):
        """更新用户工作负载"""
        # 实现工作负载更新逻辑
        pass

    def _get_project_by_task(self, task_id: str):
        """通过任务ID获取项目"""
        # 实现项目查询逻辑
        return None

    def _update_project_progress(self, project_id: str):
        """更新项目进度"""
        # 实现项目进度更新逻辑
        pass

    def _update_user_stats(self, user_id: str, quality_score: float):
        """更新用户统计"""
        # 实现用户统计更新逻辑
        pass

    def _check_milestones(self, project_id: str | None):
        """检查里程碑"""
        if project_id:
            # 实现里程碑检查逻辑
            pass


class EventHandlerRegistry:
    """事件处理器注册表"""

    def __init__(
        self,
        mod_repository: ModRepository,
        project_repository: TranslationProjectRepository,
        notification_repository: NotificationRepository | None = None,
    ):
        self.mod_handler = ModEventHandler(mod_repository, notification_repository)
        self.translation_handler = TranslationEventHandler(
            project_repository, notification_repository
        )
        self.project_handler = ProjectEventHandler(
            project_repository, notification_repository
        )

        logger.info("Event handlers registered")

    def start(self):
        """启动事件处理"""
        bus = get_event_bus()
        bus.start()
        logger.info("Event processing started")

    def stop(self):
        """停止事件处理"""
        bus = get_event_bus()
        bus.stop()
        logger.info("Event processing stopped")
