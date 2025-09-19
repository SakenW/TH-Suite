"""
翻译状态管理 - 领域模型
定义翻译状态、转换规则和工作流的核心业务逻辑
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

import structlog

logger = structlog.get_logger(__name__)


class StateCategory(Enum):
    """状态分类"""
    TRANSLATION = "translation"
    QUALITY = "quality" 
    COLLABORATION = "collaboration"
    PUBLICATION = "publication"


class TransitionTriggerType(Enum):
    """转换触发类型"""
    MANUAL = "manual"      # 手动触发
    AUTO = "auto"          # 自动触发
    SCHEDULED = "scheduled"  # 定时触发
    EVENT = "event"        # 事件触发


class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"
    WEBHOOK = "webhook"


@dataclass
class TranslationState:
    """翻译状态领域实体"""
    
    state_key: str
    display_name: str
    description: str = ""
    category: StateCategory = StateCategory.TRANSLATION
    color_hex: str = "#6B7280"
    icon_name: str = "circle"
    sort_order: int = 0
    is_active: bool = True
    
    # 状态权限
    allowed_roles: Set[str] = field(default_factory=set)
    required_permissions: Set[str] = field(default_factory=set)
    
    # 状态行为
    is_terminal: bool = False          # 是否为终止状态
    is_locked: bool = False            # 是否锁定状态
    auto_assign: bool = False          # 是否自动分配
    requires_approval: bool = False    # 是否需要审批
    
    # 时间约束
    max_duration_hours: Optional[int] = None  # 最大停留时间
    warning_hours: Optional[int] = None       # 警告时间
    
    # 元数据
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = StateCategory(self.category)
    
    def can_be_accessed_by(self, role: str, permissions: Set[str] = None) -> bool:
        """检查角色是否可以访问此状态"""
        if not self.is_active:
            return False
            
        # 检查角色权限
        if self.allowed_roles and role not in self.allowed_roles:
            return False
            
        # 检查具体权限
        if self.required_permissions and permissions:
            if not self.required_permissions.issubset(permissions):
                return False
                
        return True
    
    def is_overdue(self, entered_at: datetime) -> bool:
        """检查是否超时"""
        if not self.max_duration_hours:
            return False
            
        hours_elapsed = (datetime.now() - entered_at).total_seconds() / 3600
        return hours_elapsed > self.max_duration_hours
    
    def should_warn(self, entered_at: datetime) -> bool:
        """检查是否应该发出警告"""
        if not self.warning_hours:
            return False
            
        hours_elapsed = (datetime.now() - entered_at).total_seconds() / 3600
        return hours_elapsed > self.warning_hours
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "state_key": self.state_key,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "color_hex": self.color_hex,
            "icon_name": self.icon_name,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "allowed_roles": list(self.allowed_roles),
            "required_permissions": list(self.required_permissions),
            "is_terminal": self.is_terminal,
            "is_locked": self.is_locked,
            "auto_assign": self.auto_assign,
            "requires_approval": self.requires_approval,
            "max_duration_hours": self.max_duration_hours,
            "warning_hours": self.warning_hours
        }


@dataclass
class StateTransition:
    """状态转换规则"""
    
    from_state: str
    to_state: str
    transition_name: str
    
    # 权限控制
    required_role: Optional[str] = None
    required_permission: Optional[str] = None
    allowed_roles: Set[str] = field(default_factory=set)
    
    # 触发控制
    trigger_type: TransitionTriggerType = TransitionTriggerType.MANUAL
    auto_trigger: bool = False
    trigger_condition: Dict[str, Any] = field(default_factory=dict)
    
    # 验证规则
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    pre_conditions: List[str] = field(default_factory=list)
    post_actions: List[str] = field(default_factory=list)
    
    # 通知配置
    notification_template: Optional[str] = None
    notification_channels: Set[NotificationChannel] = field(default_factory=set)
    notification_recipients: Set[str] = field(default_factory=set)
    
    # 其他属性
    sort_order: int = 0
    is_active: bool = True
    description: str = ""
    
    def __post_init__(self):
        if isinstance(self.trigger_type, str):
            self.trigger_type = TransitionTriggerType(self.trigger_type)
        
        # 转换通知渠道
        if self.notification_channels:
            channels = set()
            for channel in self.notification_channels:
                if isinstance(channel, str):
                    channels.add(NotificationChannel(channel))
                else:
                    channels.add(channel)
            self.notification_channels = channels
    
    def can_be_triggered_by(self, role: str, permissions: Set[str] = None) -> bool:
        """检查角色是否可以触发此转换"""
        if not self.is_active:
            return False
        
        # 检查角色权限
        if self.required_role and role != self.required_role:
            return False
            
        if self.allowed_roles and role not in self.allowed_roles:
            return False
        
        # 检查具体权限
        if self.required_permission and permissions:
            if self.required_permission not in permissions:
                return False
        
        return True
    
    def validate_transition(self, context: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证转换条件"""
        errors = []
        
        # 检查前置条件
        for condition in self.pre_conditions:
            if not self._evaluate_condition(condition, context):
                errors.append(f"前置条件不满足: {condition}")
        
        # 检查验证规则
        for rule_name, rule_config in self.validation_rules.items():
            if not self._validate_rule(rule_name, rule_config, context):
                errors.append(f"验证规则失败: {rule_name}")
        
        return len(errors) == 0, errors
    
    def should_auto_trigger(self, context: Dict[str, Any]) -> bool:
        """检查是否应该自动触发"""
        if not self.auto_trigger or self.trigger_type != TransitionTriggerType.AUTO:
            return False
        
        # 检查触发条件
        if self.trigger_condition:
            return self._evaluate_condition_dict(self.trigger_condition, context)
        
        return True
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 简单的条件评估，实际项目中可能需要更复杂的表达式引擎
            if "=" in condition:
                key, value = condition.split("=", 1)
                return context.get(key.strip()) == value.strip()
            elif ">" in condition:
                key, value = condition.split(">", 1)
                return float(context.get(key.strip(), 0)) > float(value.strip())
            elif "<" in condition:
                key, value = condition.split("<", 1)
                return float(context.get(key.strip(), 0)) < float(value.strip())
            elif condition in context:
                return bool(context[condition])
            else:
                return False
        except Exception as e:
            logger.warning(f"条件评估失败: {condition}", error=str(e))
            return False
    
    def _evaluate_condition_dict(self, condition_dict: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估条件字典"""
        try:
            for key, expected_value in condition_dict.items():
                actual_value = context.get(key)
                if actual_value != expected_value:
                    return False
            return True
        except Exception as e:
            logger.warning(f"条件字典评估失败: {condition_dict}", error=str(e))
            return False
    
    def _validate_rule(self, rule_name: str, rule_config: Any, context: Dict[str, Any]) -> bool:
        """验证具体规则"""
        try:
            if rule_name == "completeness_check":
                threshold = rule_config.get("threshold", 0.8)
                completeness = context.get("completeness", 0.0)
                return completeness >= threshold
            
            elif rule_name == "quality_score":
                min_score = rule_config.get("min_score", 0.7)
                quality_score = context.get("quality_score", 0.0)
                return quality_score >= min_score
            
            elif rule_name == "reviewer_count":
                min_reviewers = rule_config.get("min_reviewers", 1)
                reviewer_count = context.get("reviewer_count", 0)
                return reviewer_count >= min_reviewers
            
            elif rule_name == "time_since_last_update":
                max_hours = rule_config.get("max_hours", 24)
                last_update = context.get("last_updated")
                if last_update:
                    hours_elapsed = (datetime.now() - last_update).total_seconds() / 3600
                    return hours_elapsed <= max_hours
                return False
            
            else:
                logger.warning(f"未知验证规则: {rule_name}")
                return True
                
        except Exception as e:
            logger.error(f"规则验证失败: {rule_name}", error=str(e))
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "transition_name": self.transition_name,
            "required_role": self.required_role,
            "required_permission": self.required_permission,
            "allowed_roles": list(self.allowed_roles),
            "trigger_type": self.trigger_type.value,
            "auto_trigger": self.auto_trigger,
            "trigger_condition": self.trigger_condition,
            "validation_rules": self.validation_rules,
            "pre_conditions": self.pre_conditions,
            "post_actions": self.post_actions,
            "notification_template": self.notification_template,
            "notification_channels": [ch.value for ch in self.notification_channels],
            "notification_recipients": list(self.notification_recipients),
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "description": self.description
        }


@dataclass
class WorkflowRule:
    """工作流规则"""
    
    rule_name: str
    description: str = ""
    target_type: str = "global"      # global, project, mod, category
    target_value: Optional[str] = None
    rule_config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    is_active: bool = True
    
    # 工作流阶段
    stages: List[Dict[str, Any]] = field(default_factory=list)
    
    # 质量门禁
    quality_gates: List[Dict[str, Any]] = field(default_factory=list)
    
    # 通知配置
    notifications: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def applies_to(self, target_type: str, target_value: str = None) -> bool:
        """检查规则是否适用于目标"""
        if not self.is_active:
            return False
        
        if self.target_type == "global":
            return True
        elif self.target_type == target_type:
            if self.target_value is None:
                return True
            return self.target_value == target_value
        
        return False
    
    def get_allowed_states_for_stage(self, stage_name: str) -> Set[str]:
        """获取指定阶段允许的状态"""
        for stage in self.stages:
            if stage.get("name") == stage_name:
                return set(stage.get("states", []))
        return set()
    
    def get_required_roles_for_stage(self, stage_name: str) -> Set[str]:
        """获取指定阶段需要的角色"""
        for stage in self.stages:
            if stage.get("name") == stage_name:
                return set(stage.get("required_roles", []))
        return set()
    
    def get_quality_gates_for_stage(self, stage_name: str) -> List[Dict[str, Any]]:
        """获取指定阶段的质量门禁"""
        for stage in self.stages:
            if stage.get("name") == stage_name:
                return stage.get("quality_gates", [])
        return []
    
    def get_notification_config(self, event_name: str) -> Optional[Dict[str, Any]]:
        """获取指定事件的通知配置"""
        return self.notifications.get(event_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_name": self.rule_name,
            "description": self.description,
            "target_type": self.target_type,
            "target_value": self.target_value,
            "rule_config": self.rule_config,
            "priority": self.priority,
            "is_active": self.is_active,
            "stages": self.stages,
            "quality_gates": self.quality_gates,
            "notifications": self.notifications
        }


@dataclass
class StateHistory:
    """状态历史记录"""
    
    entry_uid: str
    from_state: Optional[str]
    to_state: str
    transition_name: Optional[str]
    operator_id: Optional[str]
    operator_name: Optional[str]
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entry_uid": self.entry_uid,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "transition_name": self.transition_name,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "reason": self.reason,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TranslationStateMachine:
    """翻译状态机"""
    
    def __init__(self):
        self.states: Dict[str, TranslationState] = {}
        self.transitions: Dict[str, List[StateTransition]] = {}
        self.workflow_rules: List[WorkflowRule] = []
    
    def add_state(self, state: TranslationState):
        """添加状态"""
        self.states[state.state_key] = state
    
    def add_transition(self, transition: StateTransition):
        """添加状态转换"""
        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = []
        self.transitions[transition.from_state].append(transition)
    
    def add_workflow_rule(self, rule: WorkflowRule):
        """添加工作流规则"""
        self.workflow_rules.append(rule)
        # 按优先级排序
        self.workflow_rules.sort(key=lambda r: r.priority, reverse=True)
    
    def get_available_transitions(self, from_state: str, role: str, permissions: Set[str] = None) -> List[StateTransition]:
        """获取可用的状态转换"""
        available = []
        
        transitions = self.transitions.get(from_state, [])
        for transition in transitions:
            if transition.can_be_triggered_by(role, permissions):
                available.append(transition)
        
        return available
    
    def can_transition(self, from_state: str, to_state: str, role: str, permissions: Set[str] = None) -> tuple[bool, str]:
        """检查是否可以进行状态转换"""
        transitions = self.transitions.get(from_state, [])
        
        for transition in transitions:
            if transition.to_state == to_state:
                if transition.can_be_triggered_by(role, permissions):
                    return True, ""
                else:
                    return False, f"权限不足，需要角色: {transition.required_role}"
        
        return False, f"不存在从 {from_state} 到 {to_state} 的转换"
    
    def get_applicable_workflow_rules(self, target_type: str, target_value: str = None) -> List[WorkflowRule]:
        """获取适用的工作流规则"""
        applicable = []
        
        for rule in self.workflow_rules:
            if rule.applies_to(target_type, target_value):
                applicable.append(rule)
        
        return applicable
    
    def validate_state_transition(self, transition: StateTransition, context: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证状态转换"""
        return transition.validate_transition(context)
    
    def should_auto_transition(self, from_state: str, context: Dict[str, Any]) -> List[StateTransition]:
        """检查是否应该自动转换状态"""
        auto_transitions = []
        
        transitions = self.transitions.get(from_state, [])
        for transition in transitions:
            if transition.should_auto_trigger(context):
                auto_transitions.append(transition)
        
        return auto_transitions
    
    def get_state_by_category(self, category: StateCategory) -> List[TranslationState]:
        """按分类获取状态"""
        return [state for state in self.states.values() if state.category == category]
    
    def get_terminal_states(self) -> List[TranslationState]:
        """获取终止状态"""
        return [state for state in self.states.values() if state.is_terminal]
    
    def get_locked_states(self) -> List[TranslationState]:
        """获取锁定状态"""
        return [state for state in self.states.values() if state.is_locked]


def create_default_state_machine() -> TranslationStateMachine:
    """创建默认的翻译状态机"""
    state_machine = TranslationStateMachine()
    
    # 定义默认状态
    states = [
        TranslationState("draft", "草稿", category=StateCategory.TRANSLATION, sort_order=10),
        TranslationState("pending", "待翻译", category=StateCategory.TRANSLATION, sort_order=20),
        TranslationState("assigned", "已分配", category=StateCategory.COLLABORATION, sort_order=25),
        TranslationState("translated", "已翻译", category=StateCategory.TRANSLATION, sort_order=30),
        TranslationState("under_review", "审核中", category=StateCategory.QUALITY, sort_order=40),
        TranslationState("reviewed", "已审核", category=StateCategory.QUALITY, sort_order=50),
        TranslationState("approved", "已批准", category=StateCategory.PUBLICATION, sort_order=60),
        TranslationState("published", "已发布", category=StateCategory.PUBLICATION, sort_order=70, is_terminal=True),
        TranslationState("rejected", "已拒绝", category=StateCategory.QUALITY, sort_order=85, is_terminal=True),
        TranslationState("locked", "已锁定", category=StateCategory.COLLABORATION, sort_order=90, is_locked=True),
    ]
    
    # 添加状态到状态机
    for state in states:
        state_machine.add_state(state)
    
    # 定义默认转换
    transitions = [
        StateTransition("draft", "pending", "提交翻译", required_role="translator"),
        StateTransition("pending", "translated", "完成翻译", required_role="translator"),
        StateTransition("translated", "under_review", "提交审核", auto_trigger=True),
        StateTransition("under_review", "reviewed", "审核通过", required_role="reviewer"),
        StateTransition("reviewed", "approved", "批准发布", required_role="admin"),
        StateTransition("approved", "published", "发布", required_role="admin"),
    ]
    
    # 添加转换到状态机
    for transition in transitions:
        state_machine.add_transition(transition)
    
    return state_machine