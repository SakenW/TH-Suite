"""
Minecraft工作流引擎测试套件
测试完整的本地化工作流处理
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from src.services.minecraft_workflow import (
    MinecraftWorkflowEngine,
    LocalizationWorkflow,
    WorkflowConfig,
    WorkflowStep,
    WorkflowStepType,
    WorkflowStatus,
    WorkflowProgress,
    WorkflowResult,
    create_default_workflow,
    create_workflow_engine
)


class TestWorkflowConfig:
    """工作流配置测试"""
    
    def test_workflow_config_creation(self):
        """测试工作流配置创建"""
        config = WorkflowConfig(
            max_concurrent_tasks=4,
            timeout_seconds=3600,
            retry_attempts=3,
            backup_enabled=True,
            validation_enabled=True
        )
        
        assert config.max_concurrent_tasks == 4
        assert config.timeout_seconds == 3600
        assert config.retry_attempts == 3
        assert config.backup_enabled is True
        assert config.validation_enabled is True
    
    def test_workflow_config_defaults(self):
        """测试默认配置值"""
        config = WorkflowConfig()
        
        assert config.max_concurrent_tasks == 2
        assert config.timeout_seconds == 1800
        assert config.retry_attempts == 2
        assert config.backup_enabled is True
        assert config.validation_enabled is True
    
    def test_workflow_config_to_dict(self):
        """测试配置字典转换"""
        config = WorkflowConfig(max_concurrent_tasks=8)
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert result["max_concurrent_tasks"] == 8
        assert "timeout_seconds" in result
        assert "backup_enabled" in result


class TestWorkflowStep:
    """工作流步骤测试"""
    
    def test_workflow_step_creation(self):
        """测试工作流步骤创建"""
        step = WorkflowStep(
            step_id="scan_mods",
            step_type=WorkflowStepType.SCAN,
            name="扫描MOD文件",
            description="扫描并识别MOD文件结构"
        )
        
        assert step.step_id == "scan_mods"
        assert step.step_type == WorkflowStepType.SCAN
        assert step.name == "扫描MOD文件"
        assert step.status == WorkflowStatus.PENDING
    
    def test_workflow_step_dependencies(self):
        """测试步骤依赖关系"""
        step = WorkflowStep(
            step_id="translate",
            step_type=WorkflowStepType.TRANSLATE,
            name="翻译处理",
            dependencies=["scan_mods", "extract_lang"]
        )
        
        assert len(step.dependencies) == 2
        assert "scan_mods" in step.dependencies
        assert "extract_lang" in step.dependencies
    
    def test_workflow_step_to_dict(self):
        """测试步骤字典转换"""
        step = WorkflowStep(
            step_id="build_pack",
            step_type=WorkflowStepType.BUILD,
            name="构建资源包"
        )
        
        result = step.to_dict()
        
        assert result["step_id"] == "build_pack"
        assert result["step_type"] == WorkflowStepType.BUILD.value
        assert result["status"] == WorkflowStatus.PENDING.value


class TestWorkflowProgress:
    """工作流进度测试"""
    
    def test_workflow_progress_creation(self):
        """测试工作流进度创建"""
        progress = WorkflowProgress(
            workflow_id="test_workflow",
            current_step="translate",
            completed_steps=2,
            total_steps=5,
            progress_percentage=40.0,
            estimated_remaining_time=600
        )
        
        assert progress.workflow_id == "test_workflow"
        assert progress.current_step == "translate"
        assert progress.progress_percentage == 40.0
        assert progress.estimated_remaining_time == 600
    
    def test_workflow_progress_to_dict(self):
        """测试进度字典转换"""
        progress = WorkflowProgress(
            workflow_id="test",
            current_step="build",
            completed_steps=4,
            total_steps=5,
            progress_percentage=80.0
        )
        
        result = progress.to_dict()
        
        assert result["workflow_id"] == "test"
        assert result["current_step"] == "build"
        assert result["progress_percentage"] == 80.0


class TestLocalizationWorkflow:
    """本地化工作流测试"""
    
    def test_localization_workflow_creation(self):
        """测试本地化工作流创建"""
        workflow = LocalizationWorkflow(
            workflow_id="test_l10n",
            name="测试本地化工作流",
            description="用于测试的本地化工作流"
        )
        
        assert workflow.workflow_id == "test_l10n"
        assert workflow.name == "测试本地化工作流"
        assert workflow.status == WorkflowStatus.PENDING
        assert len(workflow.steps) == 0
    
    def test_add_workflow_step(self):
        """测试添加工作流步骤"""
        workflow = LocalizationWorkflow("test", "测试工作流")
        
        step1 = WorkflowStep("scan", WorkflowStepType.SCAN, "扫描")
        step2 = WorkflowStep("translate", WorkflowStepType.TRANSLATE, "翻译")
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        assert len(workflow.steps) == 2
        assert workflow.steps[0].step_id == "scan"
        assert workflow.steps[1].step_id == "translate"
    
    def test_get_step_by_id(self):
        """测试按ID获取步骤"""
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("build", WorkflowStepType.BUILD, "构建")
        workflow.add_step(step)
        
        found_step = workflow.get_step_by_id("build")
        assert found_step is not None
        assert found_step.step_id == "build"
        
        not_found = workflow.get_step_by_id("nonexistent")
        assert not_found is None
    
    def test_get_next_pending_step(self):
        """测试获取下一个待处理步骤"""
        workflow = LocalizationWorkflow("test", "测试工作流")
        
        step1 = WorkflowStep("step1", WorkflowStepType.SCAN, "步骤1")
        step2 = WorkflowStep("step2", WorkflowStepType.EXTRACT, "步骤2")
        step3 = WorkflowStep("step3", WorkflowStepType.TRANSLATE, "步骤3")
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        workflow.add_step(step3)
        
        # 初始状态，应该返回第一个步骤
        next_step = workflow.get_next_pending_step()
        assert next_step is not None
        assert next_step.step_id == "step1"
        
        # 完成第一个步骤
        step1.status = WorkflowStatus.COMPLETED
        next_step = workflow.get_next_pending_step()
        assert next_step is not None
        assert next_step.step_id == "step2"
    
    def test_calculate_progress(self):
        """测试计算工作流进度"""
        workflow = LocalizationWorkflow("test", "测试工作流")
        
        # 添加5个步骤
        for i in range(5):
            step = WorkflowStep(f"step{i}", WorkflowStepType.SCAN, f"步骤{i}")
            workflow.add_step(step)
        
        # 完成2个步骤
        workflow.steps[0].status = WorkflowStatus.COMPLETED
        workflow.steps[1].status = WorkflowStatus.COMPLETED
        workflow.steps[2].status = WorkflowStatus.IN_PROGRESS
        
        progress = workflow.calculate_progress()
        
        assert progress.completed_steps == 2
        assert progress.total_steps == 5
        assert progress.progress_percentage == 40.0
        assert progress.current_step == "step2"
    
    def test_workflow_to_dict(self):
        """测试工作流字典转换"""
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("scan", WorkflowStepType.SCAN, "扫描")
        workflow.add_step(step)
        
        result = workflow.to_dict()
        
        assert result["workflow_id"] == "test"
        assert result["name"] == "测试工作流"
        assert result["status"] == WorkflowStatus.PENDING.value
        assert len(result["steps"]) == 1
        assert result["steps"][0]["step_id"] == "scan"


class TestMinecraftWorkflowEngine:
    """Minecraft工作流引擎测试"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """模拟依赖"""
        return {
            'scanner': AsyncMock(),
            'core_client': AsyncMock(), 
            'projection_adapter': AsyncMock(),
            'jar_processor': AsyncMock(),
            'pack_builder': AsyncMock(),
            'conflict_resolver': AsyncMock()
        }
    
    @pytest.fixture
    def workflow_engine(self, mock_dependencies):
        """创建工作流引擎实例"""
        config = WorkflowConfig(max_concurrent_tasks=2)
        return MinecraftWorkflowEngine(config, **mock_dependencies)
    
    def test_engine_initialization(self, workflow_engine):
        """测试引擎初始化"""
        assert workflow_engine.config.max_concurrent_tasks == 2
        assert workflow_engine.active_workflows == {}
        assert workflow_engine.workflow_history == []
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_engine):
        """测试创建工作流"""
        workflow = await workflow_engine.create_workflow(
            name="测试工作流",
            pack_id="test_pack",
            target_path="/test/path",
            steps=[
                WorkflowStep("scan", WorkflowStepType.SCAN, "扫描"),
                WorkflowStep("extract", WorkflowStepType.EXTRACT, "提取")
            ]
        )
        
        assert workflow.name == "测试工作流"
        assert len(workflow.steps) == 2
        assert workflow.workflow_id in workflow_engine.active_workflows
    
    @pytest.mark.asyncio
    async def test_execute_scan_step(self, workflow_engine, mock_dependencies):
        """测试执行扫描步骤"""
        # 设置模拟返回值
        mock_scan_result = Mock()
        mock_scan_result.is_success = True
        mock_scan_result.mods_found = [Mock(mod_id="test_mod")]
        mock_dependencies['scanner'].scan_async.return_value = mock_scan_result
        
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("scan", WorkflowStepType.SCAN, "扫描MOD")
        workflow.add_step(step)
        
        context = {"target_path": "/test/path"}
        
        result = await workflow_engine._execute_scan_step(workflow, step, context)
        
        assert result.success is True
        assert "scan_result" in result.data
        mock_dependencies['scanner'].scan_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_extract_step(self, workflow_engine, mock_dependencies):
        """测试执行提取步骤"""
        # 设置模拟返回值
        mock_lang_files = [Mock(mod_id="test", language="zh_cn")]
        mock_dependencies['scanner'].extract_language_files.return_value = mock_lang_files
        
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("extract", WorkflowStepType.EXTRACT, "提取语言文件")
        workflow.add_step(step)
        
        context = {
            "scan_result": Mock(mods_found=[Mock(file_path="/test/mod.jar")])
        }
        
        result = await workflow_engine._execute_extract_step(workflow, step, context)
        
        assert result.success is True
        assert "language_files" in result.data
    
    @pytest.mark.asyncio
    async def test_execute_ingest_step(self, workflow_engine, mock_dependencies):
        """测试执行摄入步骤"""
        # 设置模拟返回值
        mock_result = Mock(success=True, content_items=["item1", "item2"])
        mock_dependencies['core_client'].ingest_pack.return_value = mock_result
        
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("ingest", WorkflowStepType.INGEST, "摄入数据")
        workflow.add_step(step)
        
        context = {
            "pack_id": "test_pack",
            "language_files": [Mock(), Mock()]
        }
        
        result = await workflow_engine._execute_ingest_step(workflow, step, context)
        
        assert result.success is True
        assert "ingestion_result" in result.data
        mock_dependencies['core_client'].ingest_pack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_translate_step(self, workflow_engine, mock_dependencies):
        """测试执行翻译步骤"""
        # 设置模拟返回值
        mock_result = Mock(success=True, translations={"key1": "翻译1"})
        mock_dependencies['core_client'].translate_pack.return_value = mock_result
        
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("translate", WorkflowStepType.TRANSLATE, "翻译处理")
        workflow.add_step(step)
        
        context = {
            "pack_id": "test_pack",
            "target_languages": ["zh_cn", "ja_jp"]
        }
        
        result = await workflow_engine._execute_translate_step(workflow, step, context)
        
        assert result.success is True
        assert "translation_result" in result.data
    
    @pytest.mark.asyncio 
    async def test_execute_sync_step(self, workflow_engine, mock_dependencies):
        """测试执行同步步骤"""
        # 设置模拟返回值
        mock_result = Mock(success=True, synced_files=2)
        mock_dependencies['core_client'].sync_pack.return_value = mock_result
        
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("sync", WorkflowStepType.SYNC, "同步数据")
        workflow.add_step(step)
        
        context = {"pack_id": "test_pack"}
        
        result = await workflow_engine._execute_sync_step(workflow, step, context)
        
        assert result.success is True
        assert "sync_result" in result.data
        mock_dependencies['core_client'].sync_pack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_validate_step(self, workflow_engine, mock_dependencies):
        """测试执行验证步骤"""
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("validate", WorkflowStepType.VALIDATE, "验证翻译")
        workflow.add_step(step)
        
        context = {
            "language_files": [
                Mock(translations={"key1": "value1", "key2": "value2"})
            ]
        }
        
        result = await workflow_engine._execute_validate_step(workflow, step, context)
        
        assert result.success is True
        assert "validation_result" in result.data
    
    @pytest.mark.asyncio
    async def test_execute_build_step(self, workflow_engine, mock_dependencies):
        """测试执行构建步骤"""
        # 设置模拟返回值
        mock_result = Mock(success=True, output_path="/output/pack.zip")
        mock_dependencies['pack_builder'].build_resource_pack.return_value = mock_result
        
        workflow = LocalizationWorkflow("test", "测试工作流")
        step = WorkflowStep("build", WorkflowStepType.BUILD, "构建资源包")
        workflow.add_step(step)
        
        context = {
            "pack_id": "test_pack",
            "language_files": [Mock()],
            "build_strategy": "resource_pack"
        }
        
        result = await workflow_engine._execute_build_step(workflow, step, context)
        
        assert result.success is True
        assert "build_result" in result.data
        mock_dependencies['pack_builder'].build_resource_pack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_workflow_success(self, workflow_engine, mock_dependencies):
        """测试成功运行工作流"""
        # 设置所有模拟返回成功结果
        mock_dependencies['scanner'].scan_async.return_value = Mock(
            is_success=True, 
            mods_found=[Mock(file_path="/test/mod.jar")]
        )
        mock_dependencies['scanner'].extract_language_files.return_value = [
            Mock(mod_id="test", language="zh_cn")
        ]
        
        # 创建简单工作流
        workflow = await workflow_engine.create_workflow(
            name="测试工作流",
            pack_id="test_pack", 
            target_path="/test/path",
            steps=[
                WorkflowStep("scan", WorkflowStepType.SCAN, "扫描"),
                WorkflowStep("extract", WorkflowStepType.EXTRACT, "提取")
            ]
        )
        
        result = await workflow_engine.run_workflow(workflow.workflow_id)
        
        assert result.success is True
        assert result.workflow_id == workflow.workflow_id
        assert workflow.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_run_workflow_step_failure(self, workflow_engine, mock_dependencies):
        """测试工作流步骤失败"""
        # 设置扫描失败
        mock_dependencies['scanner'].scan_async.side_effect = Exception("扫描失败")
        
        workflow = await workflow_engine.create_workflow(
            name="失败测试工作流",
            pack_id="test_pack",
            target_path="/test/path", 
            steps=[
                WorkflowStep("scan", WorkflowStepType.SCAN, "扫描")
            ]
        )
        
        result = await workflow_engine.run_workflow(workflow.workflow_id)
        
        assert result.success is False
        assert "扫描失败" in result.error_message
        assert workflow.status == WorkflowStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_get_workflow_progress(self, workflow_engine):
        """测试获取工作流进度"""
        workflow = await workflow_engine.create_workflow(
            name="进度测试工作流",
            pack_id="test_pack",
            target_path="/test/path",
            steps=[
                WorkflowStep("step1", WorkflowStepType.SCAN, "步骤1"),
                WorkflowStep("step2", WorkflowStepType.EXTRACT, "步骤2")
            ]
        )
        
        # 完成第一个步骤
        workflow.steps[0].status = WorkflowStatus.COMPLETED
        workflow.steps[1].status = WorkflowStatus.IN_PROGRESS
        
        progress = await workflow_engine.get_workflow_progress(workflow.workflow_id)
        
        assert progress is not None
        assert progress.workflow_id == workflow.workflow_id
        assert progress.completed_steps == 1
        assert progress.total_steps == 2
        assert progress.progress_percentage == 50.0
        assert progress.current_step == "步骤2"
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, workflow_engine):
        """测试取消工作流"""
        workflow = await workflow_engine.create_workflow(
            name="取消测试工作流",
            pack_id="test_pack",
            target_path="/test/path",
            steps=[WorkflowStep("scan", WorkflowStepType.SCAN, "扫描")]
        )
        
        success = await workflow_engine.cancel_workflow(workflow.workflow_id)
        
        assert success is True
        assert workflow.status == WorkflowStatus.CANCELLED
    
    def test_list_active_workflows(self, workflow_engine):
        """测试列出活跃工作流"""
        # 初始状态应该为空
        active = workflow_engine.list_active_workflows()
        assert len(active) == 0


class TestWorkflowFactory:
    """工作流工厂测试"""
    
    def test_create_default_workflow(self):
        """测试创建默认工作流"""
        workflow = create_default_workflow("default_test", "测试包", "/test/path")
        
        assert workflow.name == "默认本地化工作流"
        assert len(workflow.steps) > 0
        
        # 检查是否包含必要的步骤类型
        step_types = [step.step_type for step in workflow.steps]
        assert WorkflowStepType.SCAN in step_types
        assert WorkflowStepType.EXTRACT in step_types
        assert WorkflowStepType.BUILD in step_types
    
    def test_create_workflow_engine(self):
        """测试创建工作流引擎"""
        with patch('src.services.minecraft_workflow.get_scanner') as mock_scanner:
            with patch('src.services.minecraft_workflow.TransHubClient') as mock_client:
                with patch('src.services.minecraft_workflow.create_minecraft_adapter') as mock_adapter:
                    with patch('src.services.minecraft_workflow.AdvancedJarProcessor') as mock_jar:
                        with patch('src.services.minecraft_workflow.PackBuilder') as mock_builder:
                            with patch('src.services.minecraft_workflow.create_conflict_resolver') as mock_resolver:
                                
                                engine = create_workflow_engine()
                                
                                assert isinstance(engine, MinecraftWorkflowEngine)
                                # 验证所有依赖都被正确注入
                                mock_scanner.assert_called_once()
                                mock_client.assert_called_once()
                                mock_adapter.assert_called_once()


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self, mock_dependencies):
        """测试工作流超时处理"""
        config = WorkflowConfig(timeout_seconds=1)  # 1秒超时
        engine = MinecraftWorkflowEngine(config, **mock_dependencies)
        
        # 设置慢速模拟函数
        async def slow_scan(*args, **kwargs):
            await asyncio.sleep(2)  # 超过超时时间
            return Mock(is_success=True)
        
        mock_dependencies['scanner'].scan_async = slow_scan
        
        workflow = await engine.create_workflow(
            name="超时测试",
            pack_id="timeout_test",
            target_path="/test/path",
            steps=[WorkflowStep("scan", WorkflowStepType.SCAN, "扫描")]
        )
        
        result = await engine.run_workflow(workflow.workflow_id)
        
        assert result.success is False
        assert "超时" in result.error_message or "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_workflow_retry_mechanism(self, mock_dependencies):
        """测试工作流重试机制"""
        config = WorkflowConfig(retry_attempts=2)
        engine = MinecraftWorkflowEngine(config, **mock_dependencies)
        
        # 设置前两次调用失败，第三次成功
        call_count = 0
        def failing_scan(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("临时失败")
            return Mock(is_success=True)
        
        mock_dependencies['scanner'].scan_async = failing_scan
        
        workflow = await engine.create_workflow(
            name="重试测试",
            pack_id="retry_test",
            target_path="/test/path",
            steps=[WorkflowStep("scan", WorkflowStepType.SCAN, "扫描")]
        )
        
        result = await engine.run_workflow(workflow.workflow_id)
        
        # 应该在第三次尝试时成功
        assert call_count == 3
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])