"""
翻译状态管理 - Repository层
实现翻译状态、转换规则、历史记录等的数据访问
"""

import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Set

from .base_repository import BaseRepository
from ...domain.models.translation_state import (
    TranslationState, StateTransition, WorkflowRule, StateHistory,
    StateCategory, TransitionTriggerType, NotificationChannel
)


class TranslationStateRepository(BaseRepository):
    """翻译状态Repository"""
    
    def table_name(self) -> str:
        return "translation_states"
    
    def create_state(self, state: TranslationState) -> bool:
        """创建翻译状态"""
        try:
            query = """
                INSERT INTO translation_states (
                    state_key, display_name, description, category, color_hex, 
                    icon_name, sort_order, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_write(query, (
                state.state_key, state.display_name, state.description,
                state.category.value, state.color_hex, state.icon_name,
                state.sort_order, state.is_active
            ))
            return True
        except Exception as e:
            self.logger.error(f"创建翻译状态失败: {e}")
            return False
    
    def get_state_by_key(self, state_key: str) -> Optional[TranslationState]:
        """根据状态键获取状态"""
        query = """
            SELECT state_key, display_name, description, category, color_hex,
                   icon_name, sort_order, is_active, created_at, updated_at
            FROM translation_states 
            WHERE state_key = ? AND is_active = TRUE
        """
        row = self.execute_single(query, (state_key,))
        return self._row_to_state(row) if row else None
    
    def list_all_states(self, active_only: bool = True) -> List[TranslationState]:
        """获取所有状态"""
        query = """
            SELECT state_key, display_name, description, category, color_hex,
                   icon_name, sort_order, is_active, created_at, updated_at
            FROM translation_states
        """
        params = []
        
        if active_only:
            query += " WHERE is_active = TRUE"
        
        query += " ORDER BY sort_order, state_key"
        
        rows = self.execute_query(query, params)
        return [self._row_to_state(row) for row in rows]
    
    def get_states_by_category(self, category: StateCategory) -> List[TranslationState]:
        """根据分类获取状态"""
        query = """
            SELECT state_key, display_name, description, category, color_hex,
                   icon_name, sort_order, is_active, created_at, updated_at
            FROM translation_states 
            WHERE category = ? AND is_active = TRUE
            ORDER BY sort_order
        """
        rows = self.execute_query(query, (category.value,))
        return [self._row_to_state(row) for row in rows]
    
    def update_state(self, state: TranslationState) -> bool:
        """更新状态"""
        try:
            query = """
                UPDATE translation_states 
                SET display_name = ?, description = ?, category = ?, color_hex = ?,
                    icon_name = ?, sort_order = ?, is_active = ?, updated_at = datetime('now')
                WHERE state_key = ?
            """
            affected = self.execute_write(query, (
                state.display_name, state.description, state.category.value,
                state.color_hex, state.icon_name, state.sort_order,
                state.is_active, state.state_key
            ))
            return affected > 0
        except Exception as e:
            self.logger.error(f"更新翻译状态失败: {e}")
            return False
    
    def _row_to_state(self, row) -> TranslationState:
        """将数据库行转换为状态实体"""
        return TranslationState(
            state_key=row['state_key'],
            display_name=row['display_name'],
            description=row['description'] or "",
            category=StateCategory(row['category']),
            color_hex=row['color_hex'],
            icon_name=row['icon_name'],
            sort_order=row['sort_order'],
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
        )


class StateTransitionRepository(BaseRepository):
    """状态转换Repository"""
    
    def table_name(self) -> str:
        return "translation_state_transitions"
    
    def create_transition(self, transition: StateTransition) -> bool:
        """创建状态转换"""
        try:
            query = """
                INSERT INTO translation_state_transitions (
                    from_state, to_state, transition_name, required_role, required_permission,
                    auto_trigger, trigger_condition, validation_rules, notification_template,
                    sort_order, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_write(query, (
                transition.from_state, transition.to_state, transition.transition_name,
                transition.required_role, transition.required_permission,
                transition.auto_trigger, json.dumps(transition.trigger_condition),
                json.dumps(transition.validation_rules), transition.notification_template,
                transition.sort_order, transition.is_active
            ))
            return True
        except Exception as e:
            self.logger.error(f"创建状态转换失败: {e}")
            return False
    
    def get_transitions_from_state(self, from_state: str) -> List[StateTransition]:
        """获取从指定状态出发的转换"""
        query = """
            SELECT from_state, to_state, transition_name, required_role, required_permission,
                   auto_trigger, trigger_condition, validation_rules, notification_template,
                   sort_order, is_active
            FROM translation_state_transitions 
            WHERE from_state = ? AND is_active = TRUE
            ORDER BY sort_order
        """
        rows = self.execute_query(query, (from_state,))
        return [self._row_to_transition(row) for row in rows]
    
    def get_transition(self, from_state: str, to_state: str, transition_name: str) -> Optional[StateTransition]:
        """获取特定的状态转换"""
        query = """
            SELECT from_state, to_state, transition_name, required_role, required_permission,
                   auto_trigger, trigger_condition, validation_rules, notification_template,
                   sort_order, is_active
            FROM translation_state_transitions 
            WHERE from_state = ? AND to_state = ? AND transition_name = ? AND is_active = TRUE
        """
        row = self.execute_single(query, (from_state, to_state, transition_name))
        return self._row_to_transition(row) if row else None
    
    def list_all_transitions(self, active_only: bool = True) -> List[StateTransition]:
        """获取所有状态转换"""
        query = """
            SELECT from_state, to_state, transition_name, required_role, required_permission,
                   auto_trigger, trigger_condition, validation_rules, notification_template,
                   sort_order, is_active
            FROM translation_state_transitions
        """
        params = []
        
        if active_only:
            query += " WHERE is_active = TRUE"
        
        query += " ORDER BY from_state, sort_order"
        
        rows = self.execute_query(query, params)
        return [self._row_to_transition(row) for row in rows]
    
    def get_auto_transitions(self) -> List[StateTransition]:
        """获取所有自动转换"""
        query = """
            SELECT from_state, to_state, transition_name, required_role, required_permission,
                   auto_trigger, trigger_condition, validation_rules, notification_template,
                   sort_order, is_active
            FROM translation_state_transitions 
            WHERE auto_trigger = TRUE AND is_active = TRUE
            ORDER BY from_state, sort_order
        """
        rows = self.execute_query(query)
        return [self._row_to_transition(row) for row in rows]
    
    def _row_to_transition(self, row) -> StateTransition:
        """将数据库行转换为转换实体"""
        trigger_condition = {}
        validation_rules = {}
        
        try:
            if row['trigger_condition']:
                trigger_condition = json.loads(row['trigger_condition'])
        except (json.JSONDecodeError, TypeError):
            pass
        
        try:
            if row['validation_rules']:
                validation_rules = json.loads(row['validation_rules'])
        except (json.JSONDecodeError, TypeError):
            pass
        
        return StateTransition(
            from_state=row['from_state'],
            to_state=row['to_state'],
            transition_name=row['transition_name'],
            required_role=row.get('required_role'),
            required_permission=row.get('required_permission'),
            auto_trigger=bool(row['auto_trigger']),
            trigger_condition=trigger_condition,
            validation_rules=validation_rules,
            notification_template=row.get('notification_template'),
            sort_order=row['sort_order'],
            is_active=bool(row['is_active'])
        )


class StateHistoryRepository(BaseRepository):
    """状态历史Repository"""
    
    def table_name(self) -> str:
        return "translation_state_history"
    
    def create_history(self, history: StateHistory) -> bool:
        """创建状态历史记录"""
        try:
            query = """
                INSERT INTO translation_state_history (
                    entry_uid, from_state, to_state, transition_name,
                    operator_id, operator_name, reason, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_write(query, (
                history.entry_uid, history.from_state, history.to_state,
                history.transition_name, history.operator_id, history.operator_name,
                history.reason, json.dumps(history.metadata)
            ))
            return True
        except Exception as e:
            self.logger.error(f"创建状态历史失败: {e}")
            return False
    
    def get_entry_history(self, entry_uid: str, limit: int = 50) -> List[StateHistory]:
        """获取条目的状态历史"""
        query = """
            SELECT entry_uid, from_state, to_state, transition_name,
                   operator_id, operator_name, reason, metadata, created_at
            FROM translation_state_history 
            WHERE entry_uid = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self.execute_query(query, (entry_uid, limit))
        return [self._row_to_history(row) for row in rows]
    
    def get_operator_history(self, operator_id: str, limit: int = 100) -> List[StateHistory]:
        """获取操作者的历史记录"""
        query = """
            SELECT entry_uid, from_state, to_state, transition_name,
                   operator_id, operator_name, reason, metadata, created_at
            FROM translation_state_history 
            WHERE operator_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self.execute_query(query, (operator_id, limit))
        return [self._row_to_history(row) for row in rows]
    
    def get_state_history_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取状态历史统计"""
        query = """
            SELECT 
                to_state,
                COUNT(*) as change_count,
                COUNT(DISTINCT entry_uid) as unique_entries,
                COUNT(DISTINCT operator_id) as unique_operators
            FROM translation_state_history
            WHERE created_at >= datetime('now', '-{} days')
            GROUP BY to_state
            ORDER BY change_count DESC
        """.format(days)
        
        rows = self.execute_query(query)
        
        stats = {
            "period_days": days,
            "by_state": [],
            "total_changes": 0,
            "unique_entries": 0,
            "unique_operators": 0
        }
        
        entry_uids = set()
        operator_ids = set()
        
        for row in rows:
            state_stats = {
                "state": row['to_state'],
                "change_count": row['change_count'],
                "unique_entries": row['unique_entries'],
                "unique_operators": row['unique_operators']
            }
            stats["by_state"].append(state_stats)
            stats["total_changes"] += row['change_count']
        
        # 获取总体统计
        total_query = """
            SELECT 
                COUNT(DISTINCT entry_uid) as unique_entries,
                COUNT(DISTINCT operator_id) as unique_operators
            FROM translation_state_history
            WHERE created_at >= datetime('now', '-{} days')
        """.format(days)
        
        total_row = self.execute_single(total_query)
        if total_row:
            stats["unique_entries"] = total_row['unique_entries']
            stats["unique_operators"] = total_row['unique_operators']
        
        return stats
    
    def get_recent_activities(self, limit: int = 20) -> List[StateHistory]:
        """获取最近的活动"""
        query = """
            SELECT entry_uid, from_state, to_state, transition_name,
                   operator_id, operator_name, reason, metadata, created_at
            FROM translation_state_history 
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self.execute_query(query, (limit,))
        return [self._row_to_history(row) for row in rows]
    
    def cleanup_old_history(self, days: int = 365) -> int:
        """清理旧的历史记录"""
        query = """
            DELETE FROM translation_state_history
            WHERE created_at < datetime('now', '-{} days')
        """.format(days)
        
        return self.execute_write(query)
    
    def _row_to_history(self, row) -> StateHistory:
        """将数据库行转换为历史实体"""
        metadata = {}
        try:
            if row['metadata']:
                metadata = json.loads(row['metadata'])
        except (json.JSONDecodeError, TypeError):
            pass
        
        return StateHistory(
            entry_uid=row['entry_uid'],
            from_state=row.get('from_state'),
            to_state=row['to_state'],
            transition_name=row.get('transition_name'),
            operator_id=row.get('operator_id'),
            operator_name=row.get('operator_name'),
            reason=row.get('reason', ''),
            metadata=metadata,
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None
        )


class WorkflowRuleRepository(BaseRepository):
    """工作流规则Repository"""
    
    def table_name(self) -> str:
        return "translation_workflow_rules"
    
    def create_rule(self, rule: WorkflowRule) -> bool:
        """创建工作流规则"""
        try:
            query = """
                INSERT INTO translation_workflow_rules (
                    rule_name, description, target_type, target_value,
                    rule_config, priority, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_write(query, (
                rule.rule_name, rule.description, rule.target_type,
                rule.target_value, json.dumps(rule.rule_config),
                rule.priority, rule.is_active
            ))
            return True
        except Exception as e:
            self.logger.error(f"创建工作流规则失败: {e}")
            return False
    
    def get_rule_by_name(self, rule_name: str) -> Optional[WorkflowRule]:
        """根据名称获取规则"""
        query = """
            SELECT rule_name, description, target_type, target_value,
                   rule_config, priority, is_active, created_at, updated_at
            FROM translation_workflow_rules 
            WHERE rule_name = ? AND is_active = TRUE
        """
        row = self.execute_single(query, (rule_name,))
        return self._row_to_rule(row) if row else None
    
    def get_applicable_rules(self, target_type: str, target_value: str = None) -> List[WorkflowRule]:
        """获取适用的规则"""
        query = """
            SELECT rule_name, description, target_type, target_value,
                   rule_config, priority, is_active, created_at, updated_at
            FROM translation_workflow_rules 
            WHERE is_active = TRUE 
            AND (
                target_type = 'global' 
                OR (target_type = ? AND (target_value IS NULL OR target_value = ?))
            )
            ORDER BY priority DESC, rule_name
        """
        rows = self.execute_query(query, (target_type, target_value))
        return [self._row_to_rule(row) for row in rows]
    
    def list_all_rules(self, active_only: bool = True) -> List[WorkflowRule]:
        """获取所有规则"""
        query = """
            SELECT rule_name, description, target_type, target_value,
                   rule_config, priority, is_active, created_at, updated_at
            FROM translation_workflow_rules
        """
        params = []
        
        if active_only:
            query += " WHERE is_active = TRUE"
        
        query += " ORDER BY priority DESC, rule_name"
        
        rows = self.execute_query(query, params)
        return [self._row_to_rule(row) for row in rows]
    
    def update_rule(self, rule: WorkflowRule) -> bool:
        """更新工作流规则"""
        try:
            query = """
                UPDATE translation_workflow_rules 
                SET description = ?, target_type = ?, target_value = ?,
                    rule_config = ?, priority = ?, is_active = ?, updated_at = datetime('now')
                WHERE rule_name = ?
            """
            affected = self.execute_write(query, (
                rule.description, rule.target_type, rule.target_value,
                json.dumps(rule.rule_config), rule.priority, rule.is_active,
                rule.rule_name
            ))
            return affected > 0
        except Exception as e:
            self.logger.error(f"更新工作流规则失败: {e}")
            return False
    
    def _row_to_rule(self, row) -> WorkflowRule:
        """将数据库行转换为规则实体"""
        rule_config = {}
        try:
            if row['rule_config']:
                rule_config = json.loads(row['rule_config'])
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 从rule_config中提取结构化信息
        stages = rule_config.get('stages', [])
        quality_gates = rule_config.get('quality_gates', [])
        notifications = rule_config.get('notifications', {})
        
        return WorkflowRule(
            rule_name=row['rule_name'],
            description=row['description'] or "",
            target_type=row['target_type'],
            target_value=row.get('target_value'),
            rule_config=rule_config,
            priority=row['priority'],
            is_active=bool(row['is_active']),
            stages=stages,
            quality_gates=quality_gates,
            notifications=notifications,
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
        )