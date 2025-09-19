"""
翻译状态管理 - 应用服务层
实现翻译状态管理的用例，包括状态变更、批量操作、统计报表等
"""

import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from ...domain.models.translation_state import (
    TranslationState, StateTransition, WorkflowRule, StateHistory,
    TranslationStateMachine, create_default_state_machine
)
from ...domain.services.translation_state_service import TranslationStateService
from ...infrastructure.repositories.translation_state_repository import (
    TranslationStateRepository, StateTransitionRepository,
    StateHistoryRepository, WorkflowRuleRepository
)
from ...infrastructure.repositories.core_translation_entry_repository import (
    CoreTranslationEntryRepository, CoreTranslationEntry
)

logger = structlog.get_logger(__name__)


class TranslationStateApplicationService:
    """翻译状态管理应用服务"""
    
    def __init__(
        self,
        state_repo: TranslationStateRepository,
        transition_repo: StateTransitionRepository,
        history_repo: StateHistoryRepository,
        workflow_repo: WorkflowRuleRepository,
        entry_repo: CoreTranslationEntryRepository
    ):
        self.state_repo = state_repo
        self.transition_repo = transition_repo
        self.history_repo = history_repo
        self.workflow_repo = workflow_repo
        self.entry_repo = entry_repo
        
        # 初始化状态机
        self.state_machine = self._load_state_machine()
        self.state_service = TranslationStateService(self.state_machine)
    
    def _load_state_machine(self) -> TranslationStateMachine:
        """从数据库加载状态机"""
        try:
            state_machine = TranslationStateMachine()
            
            # 加载状态
            states = self.state_repo.list_all_states()
            for state in states:
                state_machine.add_state(state)
            
            # 加载转换规则
            transitions = self.transition_repo.list_all_transitions()
            for transition in transitions:
                state_machine.add_transition(transition)
            
            # 加载工作流规则
            rules = self.workflow_repo.list_all_rules()
            for rule in rules:
                state_machine.add_workflow_rule(rule)
            
            logger.info(
                "状态机加载完成",
                states=len(states),
                transitions=len(transitions),
                rules=len(rules)
            )
            
            return state_machine
            
        except Exception as e:
            logger.error(f"加载状态机失败，使用默认配置: {e}")
            return create_default_state_machine()
    
    def change_translation_state(
        self,
        entry_uid: str,
        target_state: str,
        operator_id: str,
        operator_name: str,
        reason: str = "",
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        变更翻译条目状态
        
        Args:
            entry_uid: 翻译条目UID
            target_state: 目标状态
            operator_id: 操作者ID
            operator_name: 操作者名称
            reason: 变更原因
            metadata: 额外元数据
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            # 获取当前条目
            entry = self.entry_repo.get_by_uid(entry_uid)
            if not entry:
                return False, f"翻译条目不存在: {entry_uid}"
            
            current_state = entry.status
            
            # 构建验证上下文
            context = self.state_service.validate_state_change_context(
                entry_uid, {
                    "src_text": entry.src_text,
                    "dst_text": entry.dst_text,
                    "key": entry.key
                }
            )
            context["operator_role"] = "translator"  # 这里简化处理，实际应该从权限系统获取
            
            # 执行状态变更
            success, error_msg, history = self.state_service.change_state(
                entry_uid, current_state, target_state,
                operator_id, operator_name, reason, metadata, context
            )
            
            if not success:
                return False, error_msg
            
            # 更新数据库中的条目状态
            entry.status = target_state
            self.entry_repo.update(entry)
            
            # 保存状态历史
            if history:
                self.history_repo.create_history(history)
            
            logger.info(
                "翻译状态变更成功",
                entry_uid=entry_uid,
                from_state=current_state,
                to_state=target_state,
                operator=operator_name
            )
            
            return True, ""
            
        except Exception as e:
            logger.error(f"状态变更失败", entry_uid=entry_uid, error=str(e))
            return False, f"状态变更失败: {str(e)}"
    
    def get_available_actions(
        self,
        entry_uid: str,
        operator_role: str = "translator",
        operator_permissions: Set[str] = None
    ) -> List[Dict[str, Any]]:
        """获取条目可执行的动作"""
        try:
            entry = self.entry_repo.get_by_uid(entry_uid)
            if not entry:
                return []
            
            return self.state_service.get_available_actions(
                entry.status, operator_role, operator_permissions
            )
            
        except Exception as e:
            logger.error(f"获取可用动作失败", entry_uid=entry_uid, error=str(e))
            return []
    
    def batch_change_state(
        self,
        operation_name: str,
        target_state: str,
        filter_criteria: Dict[str, Any],
        operator_id: str,
        operator_name: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        批量状态变更
        
        Args:
            operation_name: 操作名称
            target_state: 目标状态
            filter_criteria: 筛选条件
            operator_id: 操作者ID
            operator_name: 操作者名称
            reason: 变更原因
            
        Returns:
            批量操作结果
        """
        operation_id = str(uuid.uuid4())
        
        try:
            # 根据筛选条件查找条目
            entries = self._find_entries_by_criteria(filter_criteria)
            
            if not entries:
                return {
                    "operation_id": operation_id,
                    "success": False,
                    "error": "没有找到符合条件的翻译条目",
                    "total_count": 0,
                    "processed_count": 0,
                    "success_count": 0,
                    "failed_count": 0
                }
            
            # 创建批量操作记录
            self._create_batch_operation_record(
                operation_id, operation_name, "state_change",
                filter_criteria, {"target_state": target_state},
                operator_id, operator_name, len(entries)
            )
            
            # 执行批量变更
            success_count = 0
            failed_count = 0
            
            for entry in entries:
                try:
                    success, error_msg = self.change_translation_state(
                        entry.uid, target_state, operator_id, operator_name, reason
                    )
                    
                    if success:
                        success_count += 1
                        self._update_batch_detail(operation_id, entry.uid, "success")
                    else:
                        failed_count += 1
                        self._update_batch_detail(operation_id, entry.uid, "failed", error_msg)
                        
                except Exception as e:
                    failed_count += 1
                    self._update_batch_detail(operation_id, entry.uid, "failed", str(e))
            
            # 更新批量操作状态
            self._complete_batch_operation(operation_id, success_count, failed_count)
            
            result = {
                "operation_id": operation_id,
                "success": True,
                "total_count": len(entries),
                "processed_count": success_count + failed_count,
                "success_count": success_count,
                "failed_count": failed_count
            }
            
            logger.info(
                "批量状态变更完成",
                operation_id=operation_id,
                operation_name=operation_name,
                **result
            )
            
            return result
            
        except Exception as e:
            logger.error(f"批量状态变更失败", operation_id=operation_id, error=str(e))
            return {
                "operation_id": operation_id,
                "success": False,
                "error": f"批量操作失败: {str(e)}",
                "total_count": 0,
                "processed_count": 0,
                "success_count": 0,
                "failed_count": 0
            }
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """获取状态统计信息"""
        try:
            # 获取基础统计
            base_stats = self.state_service.get_state_statistics()
            
            # 获取数据库中的实际状态分布
            query = """
                SELECT status, COUNT(*) as count
                FROM core_translation_entries
                GROUP BY status
                ORDER BY count DESC
            """
            rows = self.entry_repo.execute_query(query)
            
            current_distribution = {}
            total_entries = 0
            
            for row in rows:
                current_distribution[row['status']] = row['count']
                total_entries += row['count']
            
            # 获取历史统计
            history_stats = self.history_repo.get_state_history_stats(30)
            
            result = {
                **base_stats,
                "current_distribution": current_distribution,
                "total_entries": total_entries,
                "history_stats": history_stats,
                "completion_rates": self._calculate_completion_rates(current_distribution, total_entries)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取状态统计失败: {e}")
            return {"error": str(e)}
    
    def get_workflow_recommendations(
        self,
        project_uid: str = None,
        mod_uid: str = None
    ) -> List[Dict[str, Any]]:
        """获取工作流建议"""
        try:
            if project_uid:
                target_type = "project"
                target_value = project_uid
            elif mod_uid:
                target_type = "mod"
                target_value = mod_uid
            else:
                target_type = "global"
                target_value = None
            
            return self.state_service.get_workflow_recommendations(
                target_type, target_value
            )
            
        except Exception as e:
            logger.error(f"获取工作流建议失败: {e}")
            return []
    
    def get_entry_history(self, entry_uid: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取条目状态历史"""
        try:
            history_records = self.history_repo.get_entry_history(entry_uid, limit)
            
            result = []
            for record in history_records:
                history_dict = record.to_dict()
                
                # 添加状态显示名称
                if record.from_state:
                    from_state = self.state_machine.states.get(record.from_state)
                    history_dict["from_state_name"] = from_state.display_name if from_state else record.from_state
                
                to_state = self.state_machine.states.get(record.to_state)
                history_dict["to_state_name"] = to_state.display_name if to_state else record.to_state
                
                result.append(history_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"获取条目历史失败", entry_uid=entry_uid, error=str(e))
            return []
    
    def get_recent_activities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的状态变更活动"""
        try:
            activities = self.history_repo.get_recent_activities(limit)
            
            result = []
            for activity in activities:
                activity_dict = activity.to_dict()
                
                # 添加状态显示名称
                if activity.from_state:
                    from_state = self.state_machine.states.get(activity.from_state)
                    activity_dict["from_state_name"] = from_state.display_name if from_state else activity.from_state
                
                to_state = self.state_machine.states.get(activity.to_state)
                activity_dict["to_state_name"] = to_state.display_name if to_state else activity.to_state
                
                # 获取条目信息
                entry = self.entry_repo.get_by_uid(activity.entry_uid)
                if entry:
                    activity_dict["entry_key"] = entry.key
                    activity_dict["src_text"] = entry.src_text[:100] + "..." if len(entry.src_text) > 100 else entry.src_text
                
                result.append(activity_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"获取最近活动失败: {e}")
            return []
    
    def check_auto_transitions(self, entry_uid: str) -> List[Dict[str, Any]]:
        """检查并执行自动状态转换"""
        try:
            entry = self.entry_repo.get_by_uid(entry_uid)
            if not entry:
                return []
            
            # 构建上下文
            context = self.state_service.validate_state_change_context(
                entry_uid, {
                    "src_text": entry.src_text,
                    "dst_text": entry.dst_text,
                    "key": entry.key
                }
            )
            
            # 检查自动转换
            auto_transitions = self.state_service.check_auto_transitions(
                entry_uid, entry.status, context
            )
            
            executed_transitions = []
            
            for target_state, transition in auto_transitions:
                success, error_msg = self.change_translation_state(
                    entry_uid, target_state, "system", "自动转换", 
                    f"自动执行转换: {transition.transition_name}"
                )
                
                if success:
                    executed_transitions.append({
                        "target_state": target_state,
                        "transition_name": transition.transition_name,
                        "success": True
                    })
                else:
                    executed_transitions.append({
                        "target_state": target_state,
                        "transition_name": transition.transition_name,
                        "success": False,
                        "error": error_msg
                    })
            
            return executed_transitions
            
        except Exception as e:
            logger.error(f"自动转换检查失败", entry_uid=entry_uid, error=str(e))
            return []
    
    def _find_entries_by_criteria(self, criteria: Dict[str, Any]) -> List[CoreTranslationEntry]:
        """根据条件查找翻译条目"""
        # 这里简化处理，实际项目中应该支持更复杂的查询条件
        query_parts = ["SELECT * FROM core_translation_entries WHERE 1=1"]
        params = []
        
        if "status" in criteria:
            query_parts.append("AND status = ?")
            params.append(criteria["status"])
        
        if "language_file_uid" in criteria:
            query_parts.append("AND language_file_uid = ?")
            params.append(criteria["language_file_uid"])
        
        if "key_pattern" in criteria:
            query_parts.append("AND key LIKE ?")
            params.append(f"%{criteria['key_pattern']}%")
        
        if "limit" in criteria:
            query_parts.append(f"LIMIT {criteria['limit']}")
        
        query = " ".join(query_parts)
        rows = self.entry_repo.execute_query(query, params)
        
        return [self.entry_repo._row_to_entity(row) for row in rows]
    
    def _create_batch_operation_record(
        self,
        operation_id: str,
        operation_name: str,
        operation_type: str,
        filter_criteria: Dict[str, Any],
        operation_params: Dict[str, Any],
        operator_id: str,
        operator_name: str,
        total_count: int
    ):
        """创建批量操作记录"""
        query = """
            INSERT INTO translation_batch_operations (
                operation_id, operation_type, operation_name, target_filter,
                operation_params, operator_id, operator_name, total_count, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running')
        """
        self.entry_repo.execute_write(query, (
            operation_id, operation_type, operation_name,
            json.dumps(filter_criteria), json.dumps(operation_params),
            operator_id, operator_name, total_count
        ))
    
    def _update_batch_detail(
        self,
        operation_id: str,
        entry_uid: str,
        status: str,
        error_message: str = None
    ):
        """更新批量操作详情"""
        query = """
            INSERT OR REPLACE INTO translation_batch_operation_details (
                operation_id, entry_uid, status, error_message, processed_at
            ) VALUES (?, ?, ?, ?, datetime('now'))
        """
        self.entry_repo.execute_write(query, (
            operation_id, entry_uid, status, error_message
        ))
    
    def _complete_batch_operation(
        self,
        operation_id: str,
        success_count: int,
        failed_count: int
    ):
        """完成批量操作"""
        query = """
            UPDATE translation_batch_operations
            SET status = 'completed', success_count = ?, failed_count = ?,
                processed_count = ?, completed_at = datetime('now')
            WHERE operation_id = ?
        """
        self.entry_repo.execute_write(query, (
            success_count, failed_count, success_count + failed_count, operation_id
        ))
    
    def _calculate_completion_rates(
        self,
        distribution: Dict[str, int],
        total: int
    ) -> Dict[str, float]:
        """计算完成率"""
        if total == 0:
            return {}
        
        # 定义不同完成度的状态
        translated_states = {"translated", "reviewed", "approved", "published"}
        reviewed_states = {"reviewed", "approved", "published"}
        published_states = {"published"}
        
        translated_count = sum(distribution.get(state, 0) for state in translated_states)
        reviewed_count = sum(distribution.get(state, 0) for state in reviewed_states)
        published_count = sum(distribution.get(state, 0) for state in published_states)
        
        return {
            "translation_rate": round(translated_count / total * 100, 2),
            "review_rate": round(reviewed_count / total * 100, 2),
            "publication_rate": round(published_count / total * 100, 2)
        }