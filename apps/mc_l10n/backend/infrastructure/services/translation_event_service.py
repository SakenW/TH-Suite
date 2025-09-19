"""
翻译事件通知服务
实现状态变更事件的通知、订阅和分发机制
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import structlog

from ...domain.models.translation_state import StateHistory, NotificationChannel

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """事件类型"""
    STATE_CHANGED = "state_changed"
    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_COMPLETED = "assignment_completed"
    BATCH_OPERATION_STARTED = "batch_operation_started"
    BATCH_OPERATION_COMPLETED = "batch_operation_completed"
    QUALITY_ISSUE_DETECTED = "quality_issue_detected"
    DEADLINE_APPROACHING = "deadline_approaching"
    WORKFLOW_VIOLATION = "workflow_violation"


class EventPriority(Enum):
    """事件优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TranslationEvent:
    """翻译事件"""
    event_id: str
    event_type: EventType
    priority: EventPriority
    source: str                    # 事件源
    data: Dict[str, Any]          # 事件数据
    context: Dict[str, Any]       # 上下文信息
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 通知配置
    notification_channels: Set[NotificationChannel] = field(default_factory=set)
    recipients: Set[str] = field(default_factory=set)
    template_name: Optional[str] = None
    
    # 处理状态
    is_processed: bool = False
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class NotificationTemplate:
    """通知模板"""
    template_name: str
    subject_template: str
    body_template: str
    channels: Set[NotificationChannel]
    variables: Set[str] = field(default_factory=set)
    is_active: bool = True


class EventHandler(ABC):
    """事件处理器接口"""
    
    @abstractmethod
    async def handle(self, event: TranslationEvent) -> bool:
        """处理事件"""
        pass
    
    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """检查是否可以处理指定类型的事件"""
        pass


class NotificationChannel(ABC):
    """通知渠道接口"""
    
    @abstractmethod
    async def send(
        self, 
        recipients: List[str], 
        subject: str, 
        message: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送通知"""
        pass


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_config = smtp_config
    
    async def send(
        self, 
        recipients: List[str], 
        subject: str, 
        message: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送邮件通知"""
        try:
            # 这里应该实现实际的邮件发送逻辑
            logger.info(
                "发送邮件通知",
                recipients=recipients,
                subject=subject,
                message=message[:100] + "..." if len(message) > 100 else message
            )
            
            # 模拟发送延迟
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
            return False


class InAppNotificationChannel(NotificationChannel):
    """应用内通知渠道"""
    
    def __init__(self):
        self.notifications_store: List[Dict[str, Any]] = []
    
    async def send(
        self, 
        recipients: List[str], 
        subject: str, 
        message: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送应用内通知"""
        try:
            for recipient in recipients:
                notification = {
                    "id": f"notif_{datetime.now().timestamp()}",
                    "recipient": recipient,
                    "subject": subject,
                    "message": message,
                    "metadata": metadata or {},
                    "created_at": datetime.now().isoformat(),
                    "is_read": False
                }
                self.notifications_store.append(notification)
            
            logger.info(
                "发送应用内通知",
                recipients=recipients,
                subject=subject
            )
            
            return True
            
        except Exception as e:
            logger.error(f"发送应用内通知失败: {e}")
            return False
    
    def get_notifications(self, recipient: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """获取用户通知"""
        notifications = [
            notif for notif in self.notifications_store 
            if notif["recipient"] == recipient
        ]
        
        if unread_only:
            notifications = [notif for notif in notifications if not notif["is_read"]]
        
        return sorted(notifications, key=lambda x: x["created_at"], reverse=True)
    
    def mark_as_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        for notif in self.notifications_store:
            if notif["id"] == notification_id:
                notif["is_read"] = True
                return True
        return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知渠道"""
    
    def __init__(self, webhook_urls: List[str]):
        self.webhook_urls = webhook_urls
    
    async def send(
        self, 
        recipients: List[str], 
        subject: str, 
        message: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送Webhook通知"""
        try:
            payload = {
                "subject": subject,
                "message": message,
                "recipients": recipients,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # 这里应该实现实际的HTTP请求
            logger.info(
                "发送Webhook通知",
                webhook_urls=self.webhook_urls,
                payload=payload
            )
            
            return True
            
        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}")
            return False


class StateChangeEventHandler(EventHandler):
    """状态变更事件处理器"""
    
    def __init__(self, notification_service):
        self.notification_service = notification_service
    
    async def handle(self, event: TranslationEvent) -> bool:
        """处理状态变更事件"""
        try:
            if event.event_type != EventType.STATE_CHANGED:
                return False
            
            # 提取事件数据
            entry_uid = event.data.get("entry_uid")
            from_state = event.data.get("from_state")
            to_state = event.data.get("to_state")
            operator_name = event.data.get("operator_name")
            
            # 根据状态变更类型发送不同的通知
            if to_state == "translated":
                await self._handle_translation_completed(event)
            elif to_state == "reviewed":
                await self._handle_review_completed(event)
            elif to_state == "published":
                await self._handle_publication_completed(event)
            elif to_state == "rejected":
                await self._handle_translation_rejected(event)
            
            return True
            
        except Exception as e:
            logger.error(f"处理状态变更事件失败: {e}")
            return False
    
    def can_handle(self, event_type: EventType) -> bool:
        """检查是否可以处理指定类型的事件"""
        return event_type == EventType.STATE_CHANGED
    
    async def _handle_translation_completed(self, event: TranslationEvent):
        """处理翻译完成事件"""
        notification_event = TranslationEvent(
            event_id=f"{event.event_id}_notif",
            event_type=EventType.STATE_CHANGED,
            priority=EventPriority.NORMAL,
            source="translation_completed",
            data=event.data,
            context=event.context,
            template_name="translation_completed",
            notification_channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL},
            recipients={"reviewers", "coordinators"}
        )
        
        await self.notification_service.send_notification(notification_event)
    
    async def _handle_review_completed(self, event: TranslationEvent):
        """处理审核完成事件"""
        notification_event = TranslationEvent(
            event_id=f"{event.event_id}_notif",
            event_type=EventType.STATE_CHANGED,
            priority=EventPriority.NORMAL,
            source="review_completed",
            data=event.data,
            context=event.context,
            template_name="review_completed",
            notification_channels={NotificationChannel.IN_APP},
            recipients={"translators", "admins"}
        )
        
        await self.notification_service.send_notification(notification_event)
    
    async def _handle_publication_completed(self, event: TranslationEvent):
        """处理发布完成事件"""
        notification_event = TranslationEvent(
            event_id=f"{event.event_id}_notif",
            event_type=EventType.STATE_CHANGED,
            priority=EventPriority.HIGH,
            source="publication_completed",
            data=event.data,
            context=event.context,
            template_name="publication_completed",
            notification_channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.WEBHOOK},
            recipients={"all"}
        )
        
        await self.notification_service.send_notification(notification_event)
    
    async def _handle_translation_rejected(self, event: TranslationEvent):
        """处理翻译被拒绝事件"""
        notification_event = TranslationEvent(
            event_id=f"{event.event_id}_notif",
            event_type=EventType.STATE_CHANGED,
            priority=EventPriority.HIGH,
            source="translation_rejected",
            data=event.data,
            context=event.context,
            template_name="translation_rejected",
            notification_channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL},
            recipients={event.data.get("operator_id", "unknown")}
        )
        
        await self.notification_service.send_notification(notification_event)


class BatchOperationEventHandler(EventHandler):
    """批量操作事件处理器"""
    
    def __init__(self, notification_service):
        self.notification_service = notification_service
    
    async def handle(self, event: TranslationEvent) -> bool:
        """处理批量操作事件"""
        try:
            if event.event_type not in [EventType.BATCH_OPERATION_STARTED, EventType.BATCH_OPERATION_COMPLETED]:
                return False
            
            # 只对完成的批量操作发送通知
            if event.event_type == EventType.BATCH_OPERATION_COMPLETED:
                await self._handle_batch_completed(event)
            
            return True
            
        except Exception as e:
            logger.error(f"处理批量操作事件失败: {e}")
            return False
    
    def can_handle(self, event_type: EventType) -> bool:
        """检查是否可以处理指定类型的事件"""
        return event_type in [EventType.BATCH_OPERATION_STARTED, EventType.BATCH_OPERATION_COMPLETED]
    
    async def _handle_batch_completed(self, event: TranslationEvent):
        """处理批量操作完成事件"""
        operation_result = event.data.get("operation_result", {})
        success_count = operation_result.get("success_count", 0)
        failed_count = operation_result.get("failed_count", 0)
        
        # 根据成功率确定优先级
        total_count = success_count + failed_count
        if total_count > 0:
            success_rate = success_count / total_count
            priority = EventPriority.HIGH if success_rate < 0.8 else EventPriority.NORMAL
        else:
            priority = EventPriority.NORMAL
        
        notification_event = TranslationEvent(
            event_id=f"{event.event_id}_notif",
            event_type=EventType.BATCH_OPERATION_COMPLETED,
            priority=priority,
            source="batch_operation_completed",
            data=event.data,
            context=event.context,
            template_name="batch_operation_completed",
            notification_channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL},
            recipients={event.data.get("operator_id", "unknown")}
        )
        
        await self.notification_service.send_notification(notification_event)


class TranslationEventService:
    """翻译事件服务"""
    
    def __init__(self):
        self.event_handlers: List[EventHandler] = []
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.notification_templates: Dict[str, NotificationTemplate] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        
        # 初始化默认通知渠道
        self._setup_default_channels()
        self._setup_default_templates()
        self._setup_default_handlers()
    
    def _setup_default_channels(self):
        """设置默认通知渠道"""
        self.notification_channels["email"] = EmailNotificationChannel({})
        self.notification_channels["in_app"] = InAppNotificationChannel()
        self.notification_channels["webhook"] = WebhookNotificationChannel([])
    
    def _setup_default_templates(self):
        """设置默认通知模板"""
        templates = [
            NotificationTemplate(
                template_name="translation_completed",
                subject_template="翻译已完成 - {entry_key}",
                body_template="翻译条目 {entry_key} 已完成翻译，请及时进行审核。\n翻译者：{operator_name}\n完成时间：{timestamp}",
                channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL}
            ),
            NotificationTemplate(
                template_name="review_completed",
                subject_template="审核已完成 - {entry_key}",
                body_template="翻译条目 {entry_key} 的审核已完成。\n审核结果：{to_state}\n审核者：{operator_name}\n审核时间：{timestamp}",
                channels={NotificationChannel.IN_APP}
            ),
            NotificationTemplate(
                template_name="publication_completed",
                subject_template="翻译已发布 - {entry_key}",
                body_template="翻译条目 {entry_key} 已成功发布。\n发布者：{operator_name}\n发布时间：{timestamp}",
                channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.WEBHOOK}
            ),
            NotificationTemplate(
                template_name="translation_rejected",
                subject_template="翻译被拒绝 - {entry_key}",
                body_template="您的翻译条目 {entry_key} 被拒绝。\n拒绝原因：{reason}\n审核者：{operator_name}\n请查看并重新翻译。",
                channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL}
            ),
            NotificationTemplate(
                template_name="batch_operation_completed",
                subject_template="批量操作已完成 - {operation_name}",
                body_template="批量操作 {operation_name} 已完成。\n处理总数：{total_count}\n成功：{success_count}\n失败：{failed_count}",
                channels={NotificationChannel.IN_APP, NotificationChannel.EMAIL}
            )
        ]
        
        for template in templates:
            self.notification_templates[template.template_name] = template
    
    def _setup_default_handlers(self):
        """设置默认事件处理器"""
        self.event_handlers = [
            StateChangeEventHandler(self),
            BatchOperationEventHandler(self)
        ]
    
    async def start(self):
        """启动事件服务"""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._process_events())
        logger.info("翻译事件服务已启动")
    
    async def stop(self):
        """停止事件服务"""
        self.is_running = False
        logger.info("翻译事件服务已停止")
    
    async def emit_event(self, event: TranslationEvent):
        """发出事件"""
        await self.event_queue.put(event)
        logger.debug(f"事件已发出", event_type=event.event_type.value, event_id=event.event_id)
    
    async def emit_state_change_event(self, state_history: StateHistory, context: Dict[str, Any] = None):
        """发出状态变更事件"""
        event = TranslationEvent(
            event_id=f"state_change_{state_history.entry_uid}_{datetime.now().timestamp()}",
            event_type=EventType.STATE_CHANGED,
            priority=EventPriority.NORMAL,
            source="translation_state_service",
            data={
                "entry_uid": state_history.entry_uid,
                "from_state": state_history.from_state,
                "to_state": state_history.to_state,
                "transition_name": state_history.transition_name,
                "operator_id": state_history.operator_id,
                "operator_name": state_history.operator_name,
                "reason": state_history.reason,
                "entry_key": context.get("entry_key", "") if context else "",
                "timestamp": state_history.created_at.isoformat() if state_history.created_at else datetime.now().isoformat()
            },
            context=context or {}
        )
        
        await self.emit_event(event)
    
    async def emit_batch_operation_event(
        self, 
        operation_result: Dict[str, Any], 
        event_type: EventType = EventType.BATCH_OPERATION_COMPLETED
    ):
        """发出批量操作事件"""
        event = TranslationEvent(
            event_id=f"batch_op_{operation_result.get('operation_id', 'unknown')}_{datetime.now().timestamp()}",
            event_type=event_type,
            priority=EventPriority.NORMAL,
            source="batch_operation_service",
            data={
                "operation_result": operation_result,
                "operation_id": operation_result.get("operation_id"),
                "operation_name": operation_result.get("operation_name", "未知操作"),
                "operator_id": operation_result.get("operator_id"),
                "total_count": operation_result.get("total_count", 0),
                "success_count": operation_result.get("success_count", 0),
                "failed_count": operation_result.get("failed_count", 0),
                "timestamp": datetime.now().isoformat()
            },
            context={}
        )
        
        await self.emit_event(event)
    
    async def send_notification(self, event: TranslationEvent):
        """发送通知"""
        try:
            if not event.template_name:
                logger.warning(f"事件缺少通知模板", event_id=event.event_id)
                return
            
            template = self.notification_templates.get(event.template_name)
            if not template or not template.is_active:
                logger.warning(f"通知模板不存在或已禁用", template_name=event.template_name)
                return
            
            # 渲染通知内容
            subject = self._render_template(template.subject_template, event.data)
            message = self._render_template(template.body_template, event.data)
            
            # 解析收件人
            recipients = self._resolve_recipients(event.recipients, event.context)
            
            if not recipients:
                logger.debug(f"没有找到通知收件人", event_id=event.event_id)
                return
            
            # 发送到各个渠道
            for channel_name in template.channels:
                channel = self.notification_channels.get(channel_name.value)
                if channel:
                    success = await channel.send(recipients, subject, message, event.data)
                    logger.debug(
                        f"通知发送结果",
                        channel=channel_name.value,
                        success=success,
                        recipients=recipients
                    )
        
        except Exception as e:
            logger.error(f"发送通知失败", event_id=event.event_id, error=str(e))
    
    async def _process_events(self):
        """处理事件队列"""
        while self.is_running:
            try:
                # 等待事件
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # 查找并执行处理器
                handled = False
                for handler in self.event_handlers:
                    if handler.can_handle(event.event_type):
                        try:
                            success = await handler.handle(event)
                            if success:
                                handled = True
                                logger.debug(f"事件处理成功", event_id=event.event_id, handler=handler.__class__.__name__)
                        except Exception as e:
                            logger.error(f"事件处理器执行失败", event_id=event.event_id, handler=handler.__class__.__name__, error=str(e))
                
                if not handled:
                    logger.warning(f"没有找到事件处理器", event_type=event.event_type.value, event_id=event.event_id)
                
                # 标记任务完成
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                # 正常超时，继续循环
                continue
            except Exception as e:
                logger.error(f"事件处理循环异常: {e}")
                await asyncio.sleep(1)
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            return template.format(**data)
        except KeyError as e:
            logger.warning(f"模板变量缺失: {e}")
            return template
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return template
    
    def _resolve_recipients(self, recipients: Set[str], context: Dict[str, Any]) -> List[str]:
        """解析收件人"""
        resolved = []
        
        for recipient in recipients:
            if recipient == "all":
                # 所有用户（这里简化处理）
                resolved.extend(["admin", "coordinator", "translator", "reviewer"])
            elif recipient == "translators":
                resolved.extend(["translator1", "translator2"])
            elif recipient == "reviewers":
                resolved.extend(["reviewer1", "reviewer2"])
            elif recipient == "coordinators":
                resolved.extend(["coordinator1"])
            elif recipient == "admins":
                resolved.extend(["admin"])
            else:
                # 直接的用户ID
                resolved.append(recipient)
        
        return list(set(resolved))  # 去重
    
    def add_event_handler(self, handler: EventHandler):
        """添加事件处理器"""
        self.event_handlers.append(handler)
    
    def add_notification_channel(self, name: str, channel: NotificationChannel):
        """添加通知渠道"""
        self.notification_channels[name] = channel
    
    def add_notification_template(self, template: NotificationTemplate):
        """添加通知模板"""
        self.notification_templates[template.template_name] = template
    
    def get_in_app_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """获取应用内通知"""
        in_app_channel = self.notification_channels.get("in_app")
        if isinstance(in_app_channel, InAppNotificationChannel):
            return in_app_channel.get_notifications(user_id, unread_only)
        return []
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        in_app_channel = self.notification_channels.get("in_app")
        if isinstance(in_app_channel, InAppNotificationChannel):
            return in_app_channel.mark_as_read(notification_id)
        return False