"""
文件传输模块测试

测试文件传输引擎、策略、配置等功能
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ..file_transfer import (
    FileTransferEngine, TransferTask, TransferResult, TransferStatus,
    ChunkInfo, ChunkStatus, TransferProgress
)
from ..file_transfer.config import TransferConfig, ConfigTemplates
from ..file_transfer.strategies import HttpUploadStrategy, StrategyFactory
from ..file_transfer.errors import TransferError, ChunkError, ValidationError


class TestTransferConfig:
    """测试传输配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = TransferConfig()
        
        assert config.max_concurrent_transfers == 3
        assert config.max_concurrent_chunks == 8
        assert config.chunk_config is not None
        assert config.retry_config is not None
    
    def test_config_optimization(self):
        """测试配置优化"""
        config = TransferConfig()
        
        # 小文件优化
        small_config = config.optimize_for_file_size(1024 * 1024)  # 1MB
        assert small_config.max_concurrent_chunks == 2
        
        # 大文件优化
        large_config = config.optimize_for_file_size(500 * 1024 * 1024)  # 500MB
        assert large_config.max_concurrent_chunks == 8
    
    def test_network_optimization(self):
        """测试网络优化"""
        config = TransferConfig()
        
        # 低带宽优化
        low_bandwidth_config = config.optimize_for_network(5.0, 300.0)
        assert low_bandwidth_config.max_concurrent_chunks == 2
        assert low_bandwidth_config.max_concurrent_transfers == 1
        
        # 高带宽优化
        high_bandwidth_config = config.optimize_for_network(100.0, 50.0)
        assert high_bandwidth_config.max_concurrent_chunks == 8
        assert high_bandwidth_config.max_concurrent_transfers == 3
    
    def test_config_templates(self):
        """测试配置模板"""
        fast_config = ConfigTemplates.fast_local()
        assert fast_config.max_concurrent_transfers == 5
        assert fast_config.verify_chunks is False
        
        reliable_config = ConfigTemplates.reliable_remote()
        assert reliable_config.max_concurrent_transfers == 2
        assert reliable_config.verify_chunks is True


class TestChunkInfo:
    """测试分块信息"""
    
    def test_chunk_creation(self):
        """测试分块创建"""
        chunk = ChunkInfo(
            index=0,
            start=0,
            end=1024,
            size=1024
        )
        
        assert chunk.index == 0
        assert chunk.start == 0
        assert chunk.end == 1024
        assert chunk.size == 1024
        assert chunk.status == ChunkStatus.PENDING
        assert not chunk.is_completed
        assert not chunk.can_retry
    
    def test_chunk_retry_logic(self):
        """测试分块重试逻辑"""
        chunk = ChunkInfo(0, 0, 1024, 1024)
        
        # 标记失败
        chunk.status = ChunkStatus.FAILED
        chunk.attempts = 1
        assert chunk.can_retry
        
        # 超过最大重试次数
        chunk.attempts = 3
        assert not chunk.can_retry


class TestTransferProgress:
    """测试传输进度"""
    
    def test_progress_calculation(self):
        """测试进度计算"""
        progress = TransferProgress(total_size=1000)
        assert progress.percentage == 0.0
        assert not progress.is_completed
        
        progress.transferred_size = 500
        assert progress.percentage == 50.0
        
        progress.transferred_size = 1000
        assert progress.percentage == 100.0
        assert progress.is_completed
    
    def test_progress_with_zero_size(self):
        """测试零大小的进度"""
        progress = TransferProgress(total_size=0)
        assert progress.percentage == 0.0


class TestTransferTask:
    """测试传输任务"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = TransferTask(
            id="test_task",
            source_path="/test/file.txt",
            target_url="http://example.com/upload",
            file_size=1024
        )
        
        assert task.id == "test_task"
        assert task.file_size == 1024
        assert task.status == TransferStatus.PENDING
        assert task.progress.total_size == 1024
    
    def test_task_with_chunks(self):
        """测试带分块的任务"""
        task = TransferTask(
            id="chunked_task",
            source_path="/test/large_file.txt",
            target_url="http://example.com/upload",
            file_size=10240
        )
        
        # 添加分块
        for i in range(10):
            chunk = ChunkInfo(i, i * 1024, (i + 1) * 1024, 1024)
            task.chunks.append(chunk)
        
        task.progress.chunks_total = len(task.chunks)
        assert len(task.chunks) == 10


@pytest.fixture
def temp_file():
    """创建临时文件"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"Hello, World!" * 100)  # 1300 bytes
        temp_path = Path(f.name)
    
    yield temp_path
    
    # 清理
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_strategy():
    """模拟传输策略"""
    strategy = AsyncMock()
    strategy.upload_chunk.return_value = True
    strategy.verify_chunk.return_value = True
    return strategy


class TestFileTransferEngine:
    """测试文件传输引擎"""
    
    @pytest.mark.asyncio
    async def test_engine_creation(self):
        """测试引擎创建"""
        config = TransferConfig()
        engine = FileTransferEngine(config)
        
        assert engine.config == config
        assert len(engine.active_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_chunk_preparation(self, temp_file):
        """测试分块准备"""
        config = TransferConfig()
        config.chunk_config.size = 500  # 500 bytes per chunk
        
        engine = FileTransferEngine(config)
        
        task = TransferTask(
            id="test_prep",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        await engine._prepare_chunks(task)
        
        # 1300 bytes / 500 bytes = 3 chunks
        assert len(task.chunks) == 3
        assert task.chunks[0].size == 500
        assert task.chunks[1].size == 500
        assert task.chunks[2].size == 300  # 剩余部分
    
    @pytest.mark.asyncio
    async def test_file_verification(self, temp_file):
        """测试文件验证"""
        config = TransferConfig()
        engine = FileTransferEngine(config)
        
        task = TransferTask(
            id="test_verify",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        # 正常验证应该通过
        await engine._verify_file(task)
        
        # 错误的文件大小应该失败
        task.file_size = 999
        with pytest.raises(ValidationError):
            await engine._verify_file(task)
    
    @pytest.mark.asyncio
    async def test_transfer_execution(self, temp_file, mock_strategy):
        """测试传输执行"""
        config = TransferConfig()
        config.chunk_config.size = 500
        config.verify_before_transfer = False
        config.verify_after_transfer = False
        
        engine = FileTransferEngine(config)
        engine.set_strategy(mock_strategy)
        
        task = TransferTask(
            id="test_transfer",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        result = await engine.start_transfer(task)
        
        assert result.success
        assert result.task_id == "test_transfer"
        assert result.transferred_size == temp_file.stat().st_size
    
    @pytest.mark.asyncio
    async def test_transfer_without_strategy(self, temp_file):
        """测试没有策略的传输"""
        config = TransferConfig()
        engine = FileTransferEngine(config)
        
        task = TransferTask(
            id="no_strategy",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        with pytest.raises(TransferError, match="传输策略未设置"):
            await engine.start_transfer(task)
    
    @pytest.mark.asyncio
    async def test_chunk_upload_failure(self, temp_file):
        """测试分块上传失败"""
        config = TransferConfig()
        config.chunk_config.size = 500
        config.verify_before_transfer = False
        config.verify_after_transfer = False
        
        # 模拟失败的策略
        failing_strategy = AsyncMock()
        failing_strategy.upload_chunk.return_value = False
        
        engine = FileTransferEngine(config)
        engine.set_strategy(failing_strategy)
        
        task = TransferTask(
            id="test_failure",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        result = await engine.start_transfer(task)
        
        assert not result.success
        assert "分块传输失败" in result.error
    
    @pytest.mark.asyncio
    async def test_task_control_operations(self, temp_file, mock_strategy):
        """测试任务控制操作"""
        config = TransferConfig()
        engine = FileTransferEngine(config)
        engine.set_strategy(mock_strategy)
        
        task = TransferTask(
            id="control_test",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        # 添加到活跃任务
        engine.active_tasks[task.id] = task
        task.status = TransferStatus.TRANSFERRING
        
        # 测试暂停
        assert await engine.pause_transfer(task.id)
        assert task.status == TransferStatus.PAUSED
        
        # 测试恢复
        assert await engine.resume_transfer(task.id)
        assert task.status == TransferStatus.TRANSFERRING
        
        # 测试取消
        assert await engine.cancel_transfer(task.id)
        assert task.status == TransferStatus.CANCELLED
    
    def test_task_status_operations(self, temp_file):
        """测试任务状态操作"""
        config = TransferConfig()
        engine = FileTransferEngine(config)
        
        task = TransferTask(
            id="status_test",
            source_path=temp_file,
            target_url="http://example.com/upload",
            file_size=temp_file.stat().st_size
        )
        
        engine.active_tasks[task.id] = task
        
        # 获取任务状态
        retrieved_task = engine.get_task_status(task.id)
        assert retrieved_task == task
        
        # 列出活跃任务
        active_tasks = engine.list_active_tasks()
        assert len(active_tasks) == 1
        assert active_tasks[0] == task


class TestStrategyFactory:
    """测试策略工厂"""
    
    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = StrategyFactory.create_strategy("http")
        assert isinstance(strategy, HttpUploadStrategy)
        
        with pytest.raises(ValueError):
            StrategyFactory.create_strategy("unknown")
    
    def test_strategy_registration(self):
        """测试策略注册"""
        class CustomStrategy:
            pass
        
        # 注册自定义策略
        StrategyFactory.register_strategy("custom", CustomStrategy)
        
        # 验证注册
        strategies = StrategyFactory.list_strategies()
        assert "custom" in strategies
        
        # 创建策略
        strategy = StrategyFactory.create_strategy("custom")
        assert isinstance(strategy, CustomStrategy)


class TestTransferErrors:
    """测试传输错误"""
    
    def test_transfer_error(self):
        """测试传输错误"""
        error = TransferError("Test error", error_code="TEST_001")
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_001"
        assert error.metadata == {}
    
    def test_chunk_error(self):
        """测试分块错误"""
        error = ChunkError("Chunk failed", chunk_index=5, chunk_size=1024)
        
        assert error.chunk_index == 5
        assert error.chunk_size == 1024
    
    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError(
            "Size mismatch", 
            expected_value=1000, 
            actual_value=900
        )
        
        assert error.expected_value == 1000
        assert error.actual_value == 900


@pytest.mark.asyncio
async def test_integration_file_transfer(temp_file):
    """集成测试：完整的文件传输流程"""
    # 创建配置
    config = TransferConfig()
    config.chunk_config.size = 400  # 小分块用于测试
    config.verify_before_transfer = True
    config.verify_after_transfer = True
    config.verify_chunks = True
    
    # 创建引擎
    engine = FileTransferEngine(config)
    
    # 模拟策略
    mock_strategy = AsyncMock()
    mock_strategy.upload_chunk.return_value = True
    mock_strategy.verify_chunk.return_value = True
    engine.set_strategy(mock_strategy)
    
    # 创建任务
    task = TransferTask(
        id="integration_test",
        source_path=temp_file,
        target_url="http://example.com/upload",
        file_size=temp_file.stat().st_size
    )
    
    # 进度回调
    progress_updates = []
    
    def progress_callback(progress: TransferProgress):
        progress_updates.append(progress.percentage)
    
    # 执行传输
    result = await engine.start_transfer(task, progress_callback)
    
    # 验证结果
    assert result.success
    assert result.task_id == "integration_test"
    assert result.transferred_size == temp_file.stat().st_size
    assert result.average_speed > 0
    
    # 验证进度回调被调用
    assert len(progress_updates) > 0
    
    # 验证策略被正确调用
    assert mock_strategy.upload_chunk.called
    if config.verify_chunks:
        assert mock_strategy.verify_chunk.called


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])