"""
翻译状态管理 - 领域服务
实现翻译状态变更、工作流执行和状态验证的核心业务逻辑
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from ..models.translation_state import (
    TranslationState, StateTransition, WorkflowRule, StateHistory,
    TranslationStateMachine, StateCategory, NotificationChannel
)

logger = structlog.get_logger(__name__)


class TranslationStateService:
    """翻译状态管理领域服务"""
    
    def __init__(self, state_machine: TranslationStateMachine):
        self.state_machine = state_machine
    
    def change_state(
        self,
        entry_uid: str,
        current_state: str,
        target_state: str,
        operator_id: str,
        operator_name: str,
        reason: str = "",
        metadata: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, str, Optional[StateHistory]]:
        """
        执行状态变更
        
        Args:
            entry_uid: 翻译条目UID
            current_state: 当前状态
            target_state: 目标状态
            operator_id: 操作者ID
            operator_name: 操作者名称
            reason: 变更原因
            metadata: 额外元数据
            context: 上下文信息（用于验证）
            
        Returns:
            (成功标志, 错误信息, 状态历史记录)
        """
        try:
            # 获取操作者权限（这里简化处理，实际应该从权限系统获取）
            operator_role = context.get("operator_role", "translator") if context else "translator"
            operator_permissions = set(context.get("operator_permissions", [])) if context else set()
            
            # 检查状态转换是否允许
            can_transition, error_msg = self.state_machine.can_transition(
                current_state, target_state, operator_role, operator_permissions
            )
            
            if not can_transition:
                return False, error_msg, None
            
            # 获取转换规则
            transitions = self.state_machine.transitions.get(current_state, [])
            transition = None
            for t in transitions:
                if t.to_state == target_state and t.can_be_triggered_by(operator_role, operator_permissions):
                    transition = t
                    break
            
            if not transition:
                return False, f"未找到有效的状态转换规则", None
            
            # 验证转换条件
            if context:
                is_valid, validation_errors = self.state_machine.validate_state_transition(transition, context)
                if not is_valid:
                    return False, f"转换验证失败: {'; '.join(validation_errors)}", None
            
            # 创建状态历史记录
            history = StateHistory(
                entry_uid=entry_uid,
                from_state=current_state,
                to_state=target_state,
                transition_name=transition.transition_name,
                operator_id=operator_id,
                operator_name=operator_name,
                reason=reason,
                metadata=metadata or {},
                created_at=datetime.now()
            )
            
            logger.info(
                "状态变更成功",
                entry_uid=entry_uid,
                from_state=current_state,
                to_state=target_state,
                operator=operator_name,
                transition=transition.transition_name
            )
            
            return True, "", history
            
        except Exception as e:
            logger.error(f"状态变更失败", entry_uid=entry_uid, error=str(e))
            return False, f"状态变更失败: {str(e)}", None
    
    def get_available_actions(
        self,
        current_state: str,
        operator_role: str,
        operator_permissions: Set[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取当前状态下可执行的动作
        
        Returns:
            可执行动作列表，包含目标状态、动作名称、描述等信息
        """
        available_actions = []
        
        transitions = self.state_machine.get_available_transitions(
            current_state, operator_role, operator_permissions
        )
        
        for transition in transitions:
            target_state = self.state_machine.states.get(transition.to_state)
            
            action = {
                "transition_name": transition.transition_name,
                "target_state": transition.to_state,
                "target_state_name": target_state.display_name if target_state else transition.to_state,
                "description": transition.description,
                "requires_approval": target_state.requires_approval if target_state else False,
                "notification_required": bool(transition.notification_template),
                "validation_rules": transition.validation_rules,
                "pre_conditions": transition.pre_conditions
            }
            
            available_actions.append(action)
        
        return available_actions
    
    def check_auto_transitions(
        self,
        entry_uid: str,
        current_state: str,
        context: Dict[str, Any]
    ) -> List[Tuple[str, StateTransition]]:
        """
        检查是否有应该自动执行的状态转换
        
        Returns:
            应该自动执行的转换列表 [(target_state, transition), ...]
        """
        auto_transitions = []
        
        transitions = self.state_machine.should_auto_transition(current_state, context)
        
        for transition in transitions:
            # 验证自动转换条件
            is_valid, validation_errors = self.state_machine.validate_state_transition(transition, context)
            
            if is_valid:
                auto_transitions.append((transition.to_state, transition))
                logger.info(
                    "检测到自动状态转换",
                    entry_uid=entry_uid,
                    from_state=current_state,
                    to_state=transition.to_state,
                    transition=transition.transition_name
                )
            else:
                logger.debug(
                    "自动转换条件不满足",
                    entry_uid=entry_uid,
                    transition=transition.transition_name,
                    errors=validation_errors
                )
        
        return auto_transitions
    
    def validate_state_change_context(
        self,
        entry_uid: str,
        translation_data: Dict[str, Any],
        quality_metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        构建状态变更的上下文信息
        
        Args:
            entry_uid: 翻译条目UID
            translation_data: 翻译数据
            quality_metrics: 质量指标
            
        Returns:
            上下文字典，用于状态转换验证
        """
        context = {
            "entry_uid": entry_uid,
            "timestamp": datetime.now(),
        }
        
        # 添加翻译完整性信息
        src_text = translation_data.get("src_text", "")
        dst_text = translation_data.get("dst_text", "")
        
        if src_text:
            completeness = len(dst_text) / len(src_text) if len(src_text) > 0 else 0
            context["completeness"] = min(completeness, 1.0)  # 最大为1.0
        else:
            context["completeness"] = 0.0
        
        # 添加质量指标
        if quality_metrics:
            context.update(quality_metrics)
        
        # 添加基础质量检查
        context["has_translation"] = bool(dst_text and dst_text.strip())
        context["source_length"] = len(src_text)
        context["target_length"] = len(dst_text)
        context["length_ratio"] = len(dst_text) / len(src_text) if len(src_text) > 0 else 0
        
        # 简单的质量评分（实际项目中可能使用更复杂的算法）
        quality_score = 0.0
        if context["has_translation"]:
            quality_score += 0.5
            
            # 长度比例合理性（目标文本不应该太短或太长）
            length_ratio = context["length_ratio"]
            if 0.5 <= length_ratio <= 2.0:
                quality_score += 0.3
            elif 0.2 <= length_ratio <= 3.0:
                quality_score += 0.2
            
            # 包含基本标点符号
            if any(punct in dst_text for punct in "。！？.,!?"):
                quality_score += 0.2
        
        context["quality_score"] = quality_score
        
        return context
    
    def get_state_statistics(self, states: List[str] = None) -> Dict[str, Any]:
        """
        获取状态统计信息
        
        Args:
            states: 指定状态列表，为None时返回所有状态
            
        Returns:
            状态统计字典
        """
        stats = {
            "total_states": len(self.state_machine.states),
            "active_states": len([s for s in self.state_machine.states.values() if s.is_active]),
            "terminal_states": len(self.state_machine.get_terminal_states()),
            "locked_states": len(self.state_machine.get_locked_states()),
            "by_category": {}
        }
        
        # 按分类统计
        for category in StateCategory:
            category_states = self.state_machine.get_state_by_category(category)
            stats["by_category"][category.value] = {
                "count": len(category_states),
                "states": [s.state_key for s in category_states]
            }
        
        # 转换统计
        total_transitions = sum(len(transitions) for transitions in self.state_machine.transitions.values())
        stats["total_transitions"] = total_transitions
        
        return stats
    
    def get_workflow_recommendations(
        self,
        target_type: str,
        target_value: str = None,
        current_context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        获取工作流建议
        
        Args:
            target_type: 目标类型（project, mod等）
            target_value: 目标值
            current_context: 当前上下文
            
        Returns:
            工作流建议列表
        """
        recommendations = []
        
        applicable_rules = self.state_machine.get_applicable_workflow_rules(target_type, target_value)
        
        for rule in applicable_rules:
            recommendation = {
                "rule_name": rule.rule_name,
                "description": rule.description,
                "priority": rule.priority,
                "stages": []
            }
            
            # 分析每个阶段
            for stage in rule.stages:
                stage_info = {
                    "name": stage.get("name"),
                    "states": stage.get("states", []),
                    "required_roles": stage.get("required_roles", []),
                    "quality_gates": stage.get("quality_gates", []),
                    "estimated_duration": stage.get("estimated_duration"),
                    "auto_transitions": stage.get("auto_transitions", [])
                }
                recommendation["stages"].append(stage_info)
            
            # 添加质量门禁信息
            recommendation["quality_gates"] = rule.quality_gates
            
            # 添加通知配置
            recommendation["notifications"] = rule.notifications
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def create_notification_context(
        self,
        entry_uid: str,
        state_history: StateHistory,
        additional_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        创建通知上下文
        
        Args:
            entry_uid: 翻译条目UID
            state_history: 状态历史记录
            additional_data: 额外数据
            
        Returns:
            通知上下文字典
        """
        context = {
            "entry_uid": entry_uid,
            "from_state": state_history.from_state,
            "to_state": state_history.to_state,
            "transition_name": state_history.transition_name,
            "operator_id": state_history.operator_id,
            "operator_name": state_history.operator_name,
            "reason": state_history.reason,
            "timestamp": state_history.created_at.isoformat() if state_history.created_at else None,
            "metadata": state_history.metadata
        }
        
        # 添加状态显示名称
        from_state_obj = self.state_machine.states.get(state_history.from_state)
        to_state_obj = self.state_machine.states.get(state_history.to_state)
        
        context["from_state_name"] = from_state_obj.display_name if from_state_obj else state_history.from_state
        context["to_state_name"] = to_state_obj.display_name if to_state_obj else state_history.to_state
        
        # 添加额外数据
        if additional_data:
            context.update(additional_data)
        
        return context
    
    def suggest_next_actions(
        self,
        current_state: str,
        context: Dict[str, Any],
        operator_role: str = None
    ) -> List[Dict[str, Any]]:
        """
        建议下一步操作
        
        Args:
            current_state: 当前状态
            context: 上下文信息
            operator_role: 操作者角色
            
        Returns:
            建议操作列表
        """
        suggestions = []
        
        # 获取当前状态对象
        state_obj = self.state_machine.states.get(current_state)
        if not state_obj:
            return suggestions
        
        # 检查是否超时
        if state_obj.max_duration_hours:
            entered_at = context.get("state_entered_at")
            if entered_at and state_obj.is_overdue(entered_at):
                suggestions.append({
                    "type": "warning",
                    "priority": "high",
                    "message": f"状态 {state_obj.display_name} 已超时，建议尽快处理",
                    "suggested_actions": ["escalate", "reassign", "review_status"]
                })
        
        # 检查自动转换
        auto_transitions = self.state_machine.should_auto_transition(current_state, context)
        for transition in auto_transitions:
            suggestions.append({
                "type": "auto_transition",
                "priority": "medium",
                "message": f"满足自动转换条件，可以转换到 {transition.to_state}",
                "transition": transition.transition_name,
                "target_state": transition.to_state
            })
        
        # 基于角色的建议
        if operator_role:
            available_actions = self.get_available_actions(current_state, operator_role)
            if available_actions:
                suggestions.append({
                    "type": "available_actions",
                    "priority": "normal",
                    "message": f"您可以执行以下操作",
                    "actions": available_actions
                })
        
        # 质量建议
        quality_score = context.get("quality_score", 0)
        if quality_score < 0.5:
            suggestions.append({
                "type": "quality_improvement",
                "priority": "medium",
                "message": "翻译质量较低，建议改进后再提交审核",
                "suggested_improvements": [
                    "检查翻译完整性",
                    "改进术语使用",
                    "检查格式和标点"
                ]
            })
        
        return suggestions