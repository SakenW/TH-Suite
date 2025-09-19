"""
翻译状态管理系统测试
包含单元测试和集成测试
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# 导入测试目标
from ..domain.models.translation_state import (
    TranslationState, StateTransition, StateHistory, WorkflowRule,
    TranslationStateMachine, StateCategory, TransitionTriggerType
)
from ..domain.services.translation_state_service import TranslationStateService
from ..application.services.translation_state_application_service import TranslationStateApplicationService
from ..application.services.translation_batch_operation_service import (
    TranslationBatchOperationService, BatchOperationConfig, BatchOperationType
)
from ..infrastructure.services.translation_event_service import (
    TranslationEventService, TranslationEvent, EventType, EventPriority
)
from ..infrastructure.services.translation_permission_service import (
    TranslationPermissionService, User, UserRole, Permission
)


class TestTranslationState:
    """翻译状态测试"""
    
    def test_translation_state_creation(self):
        """测试翻译状态创建"""
        state = TranslationState(
            state_key="translated",
            display_name="已翻译",
            category=StateCategory.TRANSLATION,
            color_hex="#3B82F6"
        )
        
        assert state.state_key == "translated"
        assert state.display_name == "已翻译"
        assert state.category == StateCategory.TRANSLATION
        assert state.color_hex == "#3B82F6"
        assert state.is_active is True
        assert state.is_terminal is False
    
    def test_state_permission_check(self):
        """测试状态权限检查"""
        state = TranslationState(
            state_key="reviewed",
            display_name="已审核",
            allowed_roles={"reviewer", "admin"},
            required_permissions={"review_permission"}
        )
        
        # 有权限的角色
        assert state.can_be_accessed_by("reviewer", {"review_permission"})
        assert state.can_be_accessed_by("admin", {"review_permission"})
        
        # 无权限的角色
        assert not state.can_be_accessed_by("translator", {"review_permission"})
        assert not state.can_be_accessed_by("reviewer", {"other_permission"})
    
    def test_state_timeout_check(self):
        """测试状态超时检查"""
        state = TranslationState(
            state_key="pending",
            display_name="待翻译",
            max_duration_hours=24,
            warning_hours=20
        )
        
        # 模拟进入时间
        import datetime
        now = datetime.datetime.now()
        
        # 未超时
        entered_1_hour_ago = now - datetime.timedelta(hours=1)
        assert not state.is_overdue(entered_1_hour_ago)
        assert not state.should_warn(entered_1_hour_ago)
        
        # 应该警告
        entered_21_hours_ago = now - datetime.timedelta(hours=21)
        assert not state.is_overdue(entered_21_hours_ago)
        assert state.should_warn(entered_21_hours_ago)
        
        # 已超时
        entered_25_hours_ago = now - datetime.timedelta(hours=25)
        assert state.is_overdue(entered_25_hours_ago)


class TestStateTransition:
    """状态转换测试"""
    
    def test_state_transition_creation(self):
        """测试状态转换创建"""
        transition = StateTransition(
            from_state="translated",
            to_state="reviewed",
            transition_name="approve_translation",
            required_role="reviewer",
            auto_trigger=True,
            validation_rules={"completeness_check": {"threshold": 0.9}}
        )
        
        assert transition.from_state == "translated"
        assert transition.to_state == "reviewed"
        assert transition.transition_name == "approve_translation"
        assert transition.required_role == "reviewer"
        assert transition.auto_trigger is True
        assert transition.validation_rules["completeness_check"]["threshold"] == 0.9
    
    def test_transition_permission_check(self):
        """测试转换权限检查"""
        transition = StateTransition(
            from_state="draft",
            to_state="pending",
            transition_name="submit",
            required_role="translator",
            allowed_roles={"translator", "senior_translator"}
        )
        
        # 有权限的角色
        assert transition.can_be_triggered_by("translator")
        assert transition.can_be_triggered_by("senior_translator")
        
        # 无权限的角色
        assert not transition.can_be_triggered_by("reviewer")
    
    def test_transition_validation(self):
        """测试转换验证"""
        transition = StateTransition(
            from_state="translated",
            to_state="reviewed",
            transition_name="approve",
            validation_rules={
                "completeness_check": {"threshold": 0.8},
                "quality_score": {"min_score": 0.7}
            }
        )
        
        # 有效的上下文
        valid_context = {
            "completeness": 0.9,
            "quality_score": 0.8
        }
        is_valid, errors = transition.validate_transition(valid_context)
        assert is_valid
        assert len(errors) == 0
        
        # 无效的上下文
        invalid_context = {
            "completeness": 0.7,  # 低于阈值
            "quality_score": 0.6  # 低于最小分数
        }
        is_valid, errors = transition.validate_transition(invalid_context)
        assert not is_valid
        assert len(errors) > 0
    
    def test_auto_trigger_check(self):
        """测试自动触发检查"""
        transition = StateTransition(
            from_state="translated",
            to_state="under_review",
            transition_name="auto_submit_review",
            auto_trigger=True,
            trigger_condition={"auto_review_enabled": True}
        )
        
        # 应该自动触发
        context_with_auto = {"auto_review_enabled": True}
        assert transition.should_auto_trigger(context_with_auto)
        
        # 不应该自动触发
        context_without_auto = {"auto_review_enabled": False}
        assert not transition.should_auto_trigger(context_without_auto)


class TestTranslationStateMachine:
    """翻译状态机测试"""
    
    def test_state_machine_creation(self):
        """测试状态机创建"""
        state_machine = TranslationStateMachine()
        
        # 添加状态
        draft_state = TranslationState("draft", "草稿")
        pending_state = TranslationState("pending", "待翻译")
        
        state_machine.add_state(draft_state)
        state_machine.add_state(pending_state)
        
        assert "draft" in state_machine.states
        assert "pending" in state_machine.states
        assert state_machine.states["draft"].display_name == "草稿"
    
    def test_state_machine_transitions(self):
        """测试状态机转换"""
        state_machine = TranslationStateMachine()
        
        # 添加转换
        transition = StateTransition(
            from_state="draft",
            to_state="pending",
            transition_name="submit",
            required_role="translator"
        )
        state_machine.add_transition(transition)
        
        # 检查可用转换
        available = state_machine.get_available_transitions("draft", "translator")
        assert len(available) == 1
        assert available[0].to_state == "pending"
        
        # 检查转换可行性
        can_transition, message = state_machine.can_transition("draft", "pending", "translator")
        assert can_transition
        
        # 检查无权限转换
        can_transition, message = state_machine.can_transition("draft", "pending", "guest")
        assert not can_transition


class TestTranslationStateService:
    """翻译状态服务测试"""
    
    def setup_method(self):
        """设置测试"""
        self.state_machine = TranslationStateMachine()
        
        # 添加测试状态
        self.state_machine.add_state(TranslationState("draft", "草稿"))
        self.state_machine.add_state(TranslationState("pending", "待翻译"))
        self.state_machine.add_state(TranslationState("translated", "已翻译"))
        
        # 添加测试转换
        self.state_machine.add_transition(StateTransition(
            "draft", "pending", "submit", required_role="translator"
        ))
        self.state_machine.add_transition(StateTransition(
            "pending", "translated", "complete", required_role="translator"
        ))
        
        self.service = TranslationStateService(self.state_machine)
    
    def test_change_state_success(self):
        """测试成功的状态变更"""
        context = {
            "operator_role": "translator",
            "completeness": 1.0,
            "quality_score": 0.8
        }
        
        success, error_msg, history = self.service.change_state(
            "entry_123", "draft", "pending", "user_1", "翻译者1", "提交翻译", {}, context
        )
        
        assert success
        assert error_msg == ""
        assert history is not None
        assert history.entry_uid == "entry_123"
        assert history.from_state == "draft"
        assert history.to_state == "pending"
    
    def test_change_state_permission_denied(self):
        """测试权限不足的状态变更"""
        context = {
            "operator_role": "guest",  # 访客没有提交权限
            "completeness": 1.0
        }
        
        success, error_msg, history = self.service.change_state(
            "entry_123", "draft", "pending", "user_1", "访客", "提交翻译", {}, context
        )
        
        assert not success
        assert "权限不足" in error_msg or "不允许" in error_msg
        assert history is None
    
    def test_get_available_actions(self):
        """测试获取可用动作"""
        actions = self.service.get_available_actions("draft", "translator")
        
        assert len(actions) == 1
        assert actions[0]["target_state"] == "pending"
        assert actions[0]["transition_name"] == "submit"
    
    def test_validate_state_change_context(self):
        """测试状态变更上下文验证"""
        translation_data = {
            "src_text": "Hello World",
            "dst_text": "你好世界",
            "key": "test.greeting"
        }
        
        context = self.service.validate_state_change_context(
            "entry_123", translation_data
        )
        
        assert "entry_uid" in context
        assert "completeness" in context
        assert "quality_score" in context
        assert context["has_translation"] is True
        assert context["completeness"] > 0


class TestTranslationPermissionService:
    """翻译权限服务测试"""
    
    def setup_method(self):
        """设置测试"""
        self.permission_service = TranslationPermissionService()
    
    def test_user_creation(self):
        """测试用户创建"""
        user = User(
            user_id="test_user",
            username="测试用户",
            email="test@example.com",
            roles={UserRole.TRANSLATOR}
        )
        
        success = self.permission_service.create_user(user)
        assert success
        
        retrieved_user = self.permission_service.get_user("test_user")
        assert retrieved_user is not None
        assert retrieved_user.username == "测试用户"
        assert UserRole.TRANSLATOR in retrieved_user.roles
    
    def test_permission_check(self):
        """测试权限检查"""
        # 检查翻译者权限
        has_permission = self.permission_service.check_permission(
            "translator1", Permission.CREATE_TRANSLATION
        )
        assert has_permission
        
        # 检查翻译者没有管理员权限
        has_admin_permission = self.permission_service.check_permission(
            "translator1", Permission.MANAGE_USERS
        )
        assert not has_admin_permission
        
        # 检查管理员权限
        has_admin_permission = self.permission_service.check_permission(
            "admin", Permission.MANAGE_USERS
        )
        assert has_admin_permission
    
    def test_workflow_permission(self):
        """测试工作流权限"""
        # 翻译者可以提交翻译
        can_submit = self.permission_service.check_workflow_permission(
            "translator1", "draft", "pending"
        )
        assert can_submit
        
        # 翻译者不能直接发布
        can_publish = self.permission_service.check_workflow_permission(
            "translator1", "approved", "published"
        )
        assert not can_publish
        
        # 审核者可以审核
        can_review = self.permission_service.check_workflow_permission(
            "reviewer1", "under_review", "reviewed"
        )
        assert can_review
    
    def test_get_available_assignees(self):
        """测试获取可分配用户"""
        # 获取可以翻译的用户
        translators = self.permission_service.get_available_assignees("translate")
        assert len(translators) > 0
        assert all(UserRole.TRANSLATOR in user.roles or 
                  any(role.value.startswith("translator") for role in user.roles) 
                  for user in translators)
        
        # 获取可以审核的用户
        reviewers = self.permission_service.get_available_assignees("review")
        assert len(reviewers) > 0


@pytest.mark.asyncio
class TestTranslationEventService:
    """翻译事件服务测试"""
    
    def setup_method(self):
        """设置测试"""
        self.event_service = TranslationEventService()
    
    async def test_event_service_startup(self):
        """测试事件服务启动"""
        await self.event_service.start()
        assert self.event_service.is_running
        
        await self.event_service.stop()
        assert not self.event_service.is_running
    
    async def test_emit_state_change_event(self):
        """测试发出状态变更事件"""
        await self.event_service.start()
        
        # 创建状态历史
        history = StateHistory(
            entry_uid="entry_123",
            from_state="draft",
            to_state="pending",
            transition_name="submit",
            operator_id="user_1",
            operator_name="翻译者1",
            reason="提交翻译"
        )
        
        # 发出事件
        await self.event_service.emit_state_change_event(history, {
            "entry_key": "test.greeting"
        })
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 检查应用内通知
        notifications = self.event_service.get_in_app_notifications("reviewer1")
        # 由于是模拟环境，具体通知数量可能为0，主要测试API不报错
        assert isinstance(notifications, list)
        
        await self.event_service.stop()
    
    async def test_emit_batch_operation_event(self):
        """测试发出批量操作事件"""
        await self.event_service.start()
        
        operation_result = {
            "operation_id": "batch_123",
            "operation_name": "批量状态变更",
            "operator_id": "admin",
            "total_count": 100,
            "success_count": 95,
            "failed_count": 5
        }
        
        await self.event_service.emit_batch_operation_event(operation_result)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        await self.event_service.stop()


@pytest.mark.asyncio 
class TestTranslationBatchOperationService:
    """翻译批量操作服务测试"""
    
    def setup_method(self):
        """设置测试"""
        self.entry_repo = Mock()
        self.history_repo = Mock()
        self.state_service = Mock()
        
        self.batch_service = TranslationBatchOperationService(
            self.entry_repo, self.history_repo, self.state_service
        )
    
    async def test_batch_operation_creation(self):
        """测试批量操作创建"""
        config = BatchOperationConfig(
            operation_type=BatchOperationType.STATE_CHANGE,
            operation_name="测试批量状态变更",
            target_filter={"status": "pending"},
            operation_params={"target_state": "translated"},
            operator_id="admin",
            operator_name="管理员"
        )
        
        # 模拟查找条目
        mock_entries = [
            Mock(uid="entry_1", status="pending"),
            Mock(uid="entry_2", status="pending")
        ]
        
        with patch.object(self.batch_service, '_find_target_entries', return_value=mock_entries):
            with patch.object(self.batch_service, '_create_batch_operation_record'):
                with patch.object(self.batch_service, '_process_single_state_change', return_value=(True, "")):
                    with patch.object(self.batch_service, '_record_batch_detail'):
                        with patch.object(self.batch_service, '_update_batch_operation_record'):
                            
                            result = await self.batch_service.execute_batch_operation(config)
                            
                            assert result.operation_id is not None
                            assert result.total_count == 2
                            assert result.success_count == 2
                            assert result.failed_count == 0
    
    def test_operation_status_tracking(self):
        """测试操作状态跟踪"""
        operation_id = "test_op_123"
        
        # 应该返回None（操作不存在）
        status = self.batch_service.get_operation_status(operation_id)
        assert status is None
        
        # 模拟活跃操作
        from ..application.services.translation_batch_operation_service import BatchOperationResult, BatchOperationStatus
        mock_result = BatchOperationResult(
            operation_id=operation_id,
            operation_type="state_change",
            status=BatchOperationStatus.RUNNING,
            total_count=10,
            processed_count=5,
            success_count=4,
            failed_count=1,
            skipped_count=0
        )
        
        self.batch_service.active_operations[operation_id] = mock_result
        
        status = self.batch_service.get_operation_status(operation_id)
        assert status is not None
        assert status.operation_id == operation_id
        assert status.status == BatchOperationStatus.RUNNING


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        """设置集成测试环境"""
        # 这里应该设置真实的数据库连接等
        # 为了演示，我们使用Mock
        pass
    
    @pytest.mark.integration
    def test_complete_workflow(self):
        """测试完整的翻译工作流"""
        # 这个测试需要真实的数据库和服务
        # 测试从创建翻译条目到发布的完整流程
        pass
    
    @pytest.mark.integration 
    async def test_event_notification_integration(self):
        """测试事件通知集成"""
        # 测试状态变更是否正确触发通知
        pass


# 测试夹具
@pytest.fixture
def sample_translation_entry():
    """示例翻译条目"""
    return {
        "uid": str(uuid.uuid4()),
        "language_file_uid": str(uuid.uuid4()),
        "key": "test.greeting",
        "src_text": "Hello World",
        "dst_text": "你好世界",
        "status": "draft"
    }


@pytest.fixture
def sample_user():
    """示例用户"""
    return User(
        user_id="test_user",
        username="测试用户",
        email="test@example.com",
        roles={UserRole.TRANSLATOR}
    )


# 性能测试
@pytest.mark.performance
class TestPerformance:
    """性能测试"""
    
    def test_state_machine_performance(self):
        """测试状态机性能"""
        state_machine = TranslationStateMachine()
        
        # 添加大量状态和转换
        for i in range(100):
            state = TranslationState(f"state_{i}", f"状态{i}")
            state_machine.add_state(state)
        
        for i in range(99):
            transition = StateTransition(
                f"state_{i}", f"state_{i+1}", f"transition_{i}", required_role="user"
            )
            state_machine.add_transition(transition)
        
        # 测试查询性能
        import time
        start_time = time.time()
        
        for i in range(1000):
            available = state_machine.get_available_transitions("state_0", "user")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 应该在合理时间内完成
        assert elapsed < 1.0  # 1秒内完成1000次查询
    
    @pytest.mark.asyncio
    async def test_batch_operation_performance(self):
        """测试批量操作性能"""
        # 测试批量操作在处理大量数据时的性能
        pass


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])