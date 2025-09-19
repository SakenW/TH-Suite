"""
进度监控模块测试

测试进度追踪、事件管理、WebSocket推送等功能
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ..progress_tracking import (
    ProgressTracker, ProgressManager, TaskProgress, ProgressEvent,
    ProgressEventType, TaskStatus, SpeedMetrics
)
from ..progress_tracking.config import ProgressConfig, ProgressConfigTemplates
from ..progress_tracking.websocket import WebSocketProgressNotifier
from ..progress_tracking.core import ProgressListener


class TestProgressConfig:
    """测试进度配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ProgressConfig()
        
        assert config.max_event_history == 1000
        assert config.milestone_interval == 10.0
        assert config.auto_cleanup_interval == 300.0
        assert config.websocket_enabled is True
    
    def test_config_templates(self):
        """测试配置模板"""
        # 轻量级配置
        lightweight = ProgressConfigTemplates.lightweight()
        assert lightweight.max_event_history == 100
        assert lightweight.websocket_enabled is False
        
        # 开发环境配置
        dev = ProgressConfigTemplates.development()
        assert dev.log_level == "DEBUG"
        assert dev.metrics_update_interval == 2.0
        
        # 生产环境配置
        prod = ProgressConfigTemplates.production()
        assert prod.persistence_enabled is True
        assert prod.max_concurrent_tasks == 200


class TestSpeedMetrics:
    """测试速度指标"""
    
    def test_speed_calculation(self):
        """测试速度计算"""
        metrics = SpeedMetrics()
        
        # 更新速度
        metrics.update_speed(100.0, 1.0)  # 100 units/second
        assert metrics.current_speed == 100.0
        assert metrics.peak_speed == 100.0
        
        # 更新更高速度
        metrics.update_speed(150.0, 1.0)  # 150 units/second
        assert metrics.current_speed == 150.0
        assert metrics.peak_speed == 150.0
    
    def test_speed_history(self):
        """测试速度历史"""
        metrics = SpeedMetrics()
        
        # 添加多个速度记录
        for i in range(5):
            metrics.update_speed(float(i + 1) * 10, 1.0)
        
        assert len(metrics.speed_history) == 5
        assert metrics.average_speed > 0
    
    def test_smooth_speed(self):
        """测试平滑速度"""
        metrics = SpeedMetrics()
        
        # 添加测试数据
        current_time = time.time()
        for i in range(3):
            speed = float(i + 1) * 20
            metrics.speed_history.append((current_time - i, speed))
        
        smooth_speed = metrics.get_smooth_speed(10)
        assert smooth_speed > 0


class TestTaskProgress:
    """测试任务进度"""
    
    def test_progress_creation(self):
        """测试进度创建"""
        progress = TaskProgress(
            task_id="test_task",
            title="Test Task",
            total_value=100.0
        )
        
        assert progress.task_id == "test_task"
        assert progress.title == "Test Task"
        assert progress.total_value == 100.0
        assert progress.current_value == 0.0
        assert progress.status == TaskStatus.PENDING
    
    def test_percentage_calculation(self):
        """测试百分比计算"""
        progress = TaskProgress("test", "Test", 100.0)
        
        assert progress.percentage == 0.0
        
        progress.current_value = 50.0
        assert progress.percentage == 50.0
        
        progress.current_value = 100.0
        assert progress.percentage == 100.0
        assert progress.is_completed
    
    def test_progress_update(self):
        """测试进度更新"""
        progress = TaskProgress("test", "Test", 100.0)
        progress.start_time = datetime.now()
        
        progress.update_progress(25.0)
        
        assert progress.current_value == 25.0
        assert progress.last_update_time is not None
        assert progress.speed_metrics.current_speed >= 0
    
    def test_elapsed_time(self):
        """测试已用时间"""
        progress = TaskProgress("test", "Test", 100.0)
        
        # 未开始时没有已用时间
        assert progress.elapsed_time is None
        
        # 设置开始时间
        progress.start_time = datetime.now() - timedelta(seconds=10)
        elapsed = progress.elapsed_time
        assert elapsed is not None
        assert elapsed.total_seconds() >= 9.5  # 允许小误差
    
    def test_to_dict(self):
        """测试转换为字典"""
        progress = TaskProgress("test", "Test Task", 100.0)
        progress.current_value = 30.0
        progress.start_time = datetime.now()
        
        data = progress.to_dict()
        
        assert data['task_id'] == "test"
        assert data['title'] == "Test Task"
        assert data['percentage'] == 30.0
        assert data['status'] == TaskStatus.PENDING.value
        assert 'start_time' in data


class TestProgressEvent:
    """测试进度事件"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = ProgressEvent(
            event_type=ProgressEventType.TASK_STARTED,
            task_id="test_task",
            message="Task started"
        )
        
        assert event.event_type == ProgressEventType.TASK_STARTED
        assert event.task_id == "test_task"
        assert event.message == "Task started"
        assert event.timestamp is not None
    
    def test_event_to_dict(self):
        """测试事件转换为字典"""
        event = ProgressEvent(
            event_type=ProgressEventType.TASK_PROGRESS,
            task_id="test",
            data={'current_value': 50.0}
        )
        
        data = event.to_dict()
        
        assert data['event_type'] == ProgressEventType.TASK_PROGRESS.value
        assert data['task_id'] == "test"
        assert data['data']['current_value'] == 50.0


class MockProgressListener(ProgressListener):
    """模拟进度监听器"""
    
    def __init__(self):
        self.events = []
    
    async def on_progress_event(self, event: ProgressEvent) -> None:
        self.events.append(event)


@pytest.fixture
def progress_config():
    """进度配置fixture"""
    return ProgressConfig(
        auto_cleanup_interval=0,  # 禁用自动清理
        metrics_update_interval=0  # 禁用指标更新
    )


@pytest.fixture
def progress_tracker(progress_config):
    """进度追踪器fixture"""
    return ProgressTracker(progress_config)


class TestProgressTracker:
    """测试进度追踪器"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, progress_tracker):
        """测试创建任务"""
        progress = await progress_tracker.create_task(
            task_id="test_task",
            title="Test Task",
            total_value=100.0
        )
        
        assert progress.task_id == "test_task"
        assert progress.title == "Test Task"
        assert progress.total_value == 100.0
        assert "test_task" in progress_tracker.progress_data
    
    @pytest.mark.asyncio
    async def test_start_task(self, progress_tracker):
        """测试开始任务"""
        await progress_tracker.create_task("test", "Test", 100.0)
        
        await progress_tracker.start_task("test")
        
        progress = progress_tracker.get_task_progress("test")
        assert progress.status == TaskStatus.RUNNING
        assert progress.start_time is not None
    
    @pytest.mark.asyncio
    async def test_update_progress(self, progress_tracker):
        """测试更新进度"""
        await progress_tracker.create_task("test", "Test", 100.0)
        await progress_tracker.start_task("test")
        
        await progress_tracker.update_progress("test", 50.0, "Half done")
        
        progress = progress_tracker.get_task_progress("test")
        assert progress.current_value == 50.0
        assert progress.last_update_time is not None
    
    @pytest.mark.asyncio
    async def test_complete_task(self, progress_tracker):
        """测试完成任务"""
        await progress_tracker.create_task("test", "Test", 100.0)
        await progress_tracker.start_task("test")
        
        await progress_tracker.complete_task("test", "Task completed")
        
        progress = progress_tracker.get_task_progress("test")
        assert progress.status == TaskStatus.COMPLETED
        assert progress.current_value == 100.0
        assert progress.end_time is not None
    
    @pytest.mark.asyncio
    async def test_fail_task(self, progress_tracker):
        """测试任务失败"""
        await progress_tracker.create_task("test", "Test", 100.0)
        await progress_tracker.start_task("test")
        
        await progress_tracker.fail_task("test", "Something went wrong")
        
        progress = progress_tracker.get_task_progress("test")
        assert progress.status == TaskStatus.FAILED
        assert progress.error_message == "Something went wrong"
        assert progress.end_time is not None
    
    @pytest.mark.asyncio
    async def test_task_control(self, progress_tracker):
        """测试任务控制"""
        await progress_tracker.create_task("test", "Test", 100.0)
        await progress_tracker.start_task("test")
        
        # 暂停任务
        await progress_tracker.pause_task("test")
        progress = progress_tracker.get_task_progress("test")
        assert progress.status == TaskStatus.PAUSED
        
        # 恢复任务
        await progress_tracker.resume_task("test")
        progress = progress_tracker.get_task_progress("test")
        assert progress.status == TaskStatus.RUNNING
        
        # 取消任务
        await progress_tracker.cancel_task("test")
        progress = progress_tracker.get_task_progress("test")
        assert progress.status == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_event_listening(self, progress_tracker):
        """测试事件监听"""
        listener = MockProgressListener()
        progress_tracker.add_listener(listener)
        
        await progress_tracker.create_task("test", "Test", 100.0)
        await progress_tracker.start_task("test")
        await progress_tracker.update_progress("test", 50.0)
        await progress_tracker.complete_task("test")
        
        # 验证事件
        assert len(listener.events) >= 3
        event_types = [e.event_type for e in listener.events]
        assert ProgressEventType.TASK_STARTED in event_types
        assert ProgressEventType.TASK_PROGRESS in event_types
        assert ProgressEventType.TASK_COMPLETED in event_types
    
    @pytest.mark.asyncio
    async def test_milestone_events(self, progress_config):
        """测试里程碑事件"""
        # 设置较小的里程碑间隔
        progress_config.milestone_interval = 25.0
        tracker = ProgressTracker(progress_config)
        
        listener = MockProgressListener()
        tracker.add_listener(listener)
        
        await tracker.create_task("test", "Test", 100.0)
        await tracker.start_task("test")
        
        # 更新到第一个里程碑
        await tracker.update_progress("test", 30.0)
        
        # 检查里程碑事件
        milestone_events = [
            e for e in listener.events 
            if e.event_type == ProgressEventType.MILESTONE_REACHED
        ]
        assert len(milestone_events) >= 1
    
    def test_list_tasks(self, progress_tracker):
        """测试列出任务"""
        # 这个测试需要同步版本，因为list_tasks是同步方法
        # 我们需要先运行异步操作来创建任务
        async def setup_tasks():
            await progress_tracker.create_task("task1", "Task 1", 100.0)
            await progress_tracker.create_task("task2", "Task 2", 100.0)
            await progress_tracker.start_task("task1")
            await progress_tracker.complete_task("task2")
        
        # 运行设置
        asyncio.get_event_loop().run_until_complete(setup_tasks())
        
        # 测试列出所有任务
        all_tasks = progress_tracker.list_tasks()
        assert len(all_tasks) == 2
        
        # 测试按状态过滤
        running_tasks = progress_tracker.list_tasks(status_filter=TaskStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0].task_id == "task1"
        
        completed_tasks = progress_tracker.list_tasks(status_filter=TaskStatus.COMPLETED)
        assert len(completed_tasks) == 1
        assert completed_tasks[0].task_id == "task2"
    
    @pytest.mark.asyncio
    async def test_hierarchical_tasks(self, progress_tracker):
        """测试层次化任务"""
        # 创建父任务
        await progress_tracker.create_task("parent", "Parent Task", 100.0)
        
        # 创建子任务
        await progress_tracker.create_task(
            "child1", "Child Task 1", 50.0, parent_task_id="parent"
        )
        await progress_tracker.create_task(
            "child2", "Child Task 2", 50.0, parent_task_id="parent"
        )
        
        # 验证层次关系
        parent = progress_tracker.get_task_progress("parent")
        child1 = progress_tracker.get_task_progress("child1")
        child2 = progress_tracker.get_task_progress("child2")
        
        assert len(parent.subtask_ids) == 2
        assert "child1" in parent.subtask_ids
        assert "child2" in parent.subtask_ids
        assert child1.parent_task_id == "parent"
        assert child2.parent_task_id == "parent"
    
    @pytest.mark.asyncio
    async def test_remove_task(self, progress_tracker):
        """测试移除任务"""
        await progress_tracker.create_task("test", "Test", 100.0)
        assert "test" in progress_tracker.progress_data
        
        await progress_tracker.remove_task("test")
        assert "test" not in progress_tracker.progress_data


class TestProgressManager:
    """测试进度管理器"""
    
    @pytest.fixture
    def progress_manager(self, progress_config):
        """进度管理器fixture"""
        return ProgressManager(progress_config)
    
    @pytest.mark.asyncio
    async def test_create_and_start_task(self, progress_manager):
        """测试创建并开始任务"""
        progress = await progress_manager.create_and_start_task(
            "test", "Test Task", 100.0
        )
        
        assert progress.task_id == "test"
        assert progress.status == TaskStatus.RUNNING
        assert progress.start_time is not None
    
    @pytest.mark.asyncio
    async def test_update_task_increment(self, progress_manager):
        """测试增量更新任务"""
        await progress_manager.create_and_start_task("test", "Test", 100.0)
        
        # 增量更新
        await progress_manager.update_task("test", increment=25.0)
        progress = progress_manager.tracker.get_task_progress("test")
        assert progress.current_value == 25.0
        
        # 再次增量更新
        await progress_manager.update_task("test", increment=25.0)
        progress = progress_manager.tracker.get_task_progress("test")
        assert progress.current_value == 50.0
    
    @pytest.mark.asyncio
    async def test_update_task_absolute(self, progress_manager):
        """测试绝对值更新任务"""
        await progress_manager.create_and_start_task("test", "Test", 100.0)
        
        # 绝对值更新
        await progress_manager.update_task("test", current_value=75.0)
        progress = progress_manager.tracker.get_task_progress("test")
        assert progress.current_value == 75.0
    
    @pytest.mark.asyncio
    async def test_batch_update(self, progress_manager):
        """测试批量更新"""
        await progress_manager.create_and_start_task("task1", "Task 1", 100.0)
        await progress_manager.create_and_start_task("task2", "Task 2", 100.0)
        
        updates = [
            {'task_id': 'task1', 'current_value': 30.0, 'message': 'Task 1 progress'},
            {'task_id': 'task2', 'increment': 40.0, 'message': 'Task 2 progress'}
        ]
        
        await progress_manager.batch_update(updates)
        
        task1 = progress_manager.tracker.get_task_progress("task1")
        task2 = progress_manager.tracker.get_task_progress("task2")
        
        assert task1.current_value == 30.0
        assert task2.current_value == 40.0
    
    @pytest.mark.asyncio
    async def test_get_task_tree(self, progress_manager):
        """测试获取任务树"""
        # 创建层次化任务
        await progress_manager.create_and_start_task("parent", "Parent", 100.0)
        await progress_manager.tracker.create_task(
            "child", "Child", 50.0, parent_task_id="parent"
        )
        
        tree = await progress_manager.get_task_tree("parent")
        
        assert tree['task_id'] == "parent"
        assert len(tree['subtasks']) == 1
        assert tree['subtasks'][0]['task_id'] == "child"


class TestWebSocketProgressNotifier:
    """测试WebSocket进度通知器"""
    
    @pytest.fixture
    def websocket_config(self):
        """WebSocket配置fixture"""
        config = ProgressConfig()
        config.websocket_enabled = True
        config.websocket_port = 8999  # 使用不同端口避免冲突
        return config
    
    def test_notifier_creation(self, websocket_config):
        """测试通知器创建"""
        notifier = WebSocketProgressNotifier(websocket_config)
        
        assert notifier.config == websocket_config
        assert len(notifier.connections) == 0
        assert len(notifier.client_subscriptions) == 0
    
    @pytest.mark.asyncio
    async def test_event_handling(self, websocket_config):
        """测试事件处理"""
        notifier = WebSocketProgressNotifier(websocket_config)
        
        # 创建测试事件
        event = ProgressEvent(
            event_type=ProgressEventType.TASK_PROGRESS,
            task_id="test_task",
            data={'current_value': 50.0}
        )
        
        # 没有连接时应该正常处理
        await notifier.on_progress_event(event)
        
        # 验证没有错误
        assert True  # 如果到达这里说明没有异常


@pytest.mark.asyncio
async def test_integration_progress_tracking():
    """集成测试：完整的进度追踪流程"""
    config = ProgressConfig(
        auto_cleanup_interval=0,
        metrics_update_interval=0,
        milestone_interval=20.0
    )
    
    manager = ProgressManager(config)
    listener = MockProgressListener()
    manager.add_listener(listener)
    
    # 创建主任务
    main_task = await manager.create_and_start_task(
        "main_task", "Main Processing Task", 100.0
    )
    
    # 创建子任务
    await manager.tracker.create_task(
        "subtask1", "Subtask 1", 40.0, parent_task_id="main_task"
    )
    await manager.tracker.create_task(
        "subtask2", "Subtask 2", 60.0, parent_task_id="main_task"
    )
    
    # 模拟进度更新
    for i in range(1, 11):
        await manager.update_task("main_task", increment=10.0, message=f"Step {i}")
        await asyncio.sleep(0.01)  # 小延迟模拟真实处理
    
    # 完成任务
    await manager.tracker.complete_task("main_task", "All done!")
    
    # 验证最终状态
    final_progress = manager.tracker.get_task_progress("main_task")
    assert final_progress.status == TaskStatus.COMPLETED
    assert final_progress.current_value == 100.0
    assert final_progress.percentage == 100.0
    
    # 验证事件
    assert len(listener.events) > 0
    
    # 验证有里程碑事件
    milestone_events = [
        e for e in listener.events 
        if e.event_type == ProgressEventType.MILESTONE_REACHED
    ]
    assert len(milestone_events) >= 4  # 20%, 40%, 60%, 80%
    
    # 获取任务树
    tree = await manager.get_task_tree("main_task")
    assert len(tree['subtasks']) == 2


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])