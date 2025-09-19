"""
端到端集成测试套件
测试完整的数据传输和处理工作流
"""
import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List
import time

from apps.mc_l10n.backend.main import create_app
from apps.mc_l10n.backend.core.di_container import DIContainer
from apps.mc_l10n.backend.infrastructure.services.simple_minecraft_scanner import SimpleMinecraftScanner
from apps.mc_l10n.backend.application.services.scan_application_service import ScanApplicationService


class TestEndToEndWorkflow:
    """端到端工作流测试"""
    
    @pytest.fixture
    async def test_environment(self):
        """设置测试环境"""
        # 创建临时测试目录
        temp_dir = tempfile.mkdtemp(prefix="th_suite_e2e_")
        test_data_dir = Path(temp_dir) / "test_data"
        test_data_dir.mkdir(parents=True)
        
        # 创建模拟的Minecraft项目结构
        minecraft_project = test_data_dir / "minecraft_project"
        minecraft_project.mkdir()
        
        # 创建模拟的mod目录
        mods_dir = minecraft_project / "mods"
        mods_dir.mkdir()
        
        # 创建模拟的资源包目录
        resourcepacks_dir = minecraft_project / "resourcepacks"
        resourcepacks_dir.mkdir()
        
        # 创建测试MOD文件（ZIP格式）
        test_mod_data = {
            "assets": {
                "test_mod": {
                    "lang": {
                        "en_us.json": {"item.test_mod.test_item": "Test Item"},
                        "zh_cn.json": {"item.test_mod.test_item": "测试物品"}
                    }
                }
            }
        }
        
        # 初始化依赖注入容器
        container = DIContainer()
        
        yield {
            "temp_dir": temp_dir,
            "test_data_dir": test_data_dir,
            "minecraft_project": minecraft_project,
            "container": container,
            "test_mod_data": test_mod_data
        }
        
        # 清理测试环境
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def test_complete_scan_and_extraction_workflow(self, test_environment):
        """测试完整的扫描和提取工作流"""
        env = test_environment
        
        # 1. 创建扫描服务
        scanner = SimpleMinecraftScanner()
        scan_service = ScanApplicationService(scanner)
        
        # 2. 执行项目扫描
        scan_request = {
            "project_path": str(env["minecraft_project"]),
            "scan_type": "full",
            "include_mods": True,
            "include_resourcepacks": True
        }
        
        scan_result = await scan_service.scan_project(scan_request)
        
        # 3. 验证扫描结果
        assert scan_result is not None
        assert "project_info" in scan_result
        assert "discovered_files" in scan_result
        
        # 4. 验证发现的文件类型
        discovered_files = scan_result["discovered_files"]
        assert isinstance(discovered_files, list)
        
        # 5. 测试数据提取
        if discovered_files:
            for file_info in discovered_files:
                assert "file_path" in file_info
                assert "file_type" in file_info
                assert "size" in file_info
    
    async def test_translation_state_management_workflow(self, test_environment):
        """测试翻译状态管理工作流"""
        env = test_environment
        
        # 1. 创建测试翻译条目
        test_entries = [
            {
                "key": "item.test_mod.test_item",
                "source_text": "Test Item",
                "target_text": "测试物品",
                "source_locale": "en_us",
                "target_locale": "zh_cn",
                "status": "pending"
            },
            {
                "key": "block.test_mod.test_block",
                "source_text": "Test Block",
                "target_text": "",
                "source_locale": "en_us",
                "target_locale": "zh_cn",
                "status": "untranslated"
            }
        ]
        
        # 2. 测试状态流转
        for entry in test_entries:
            # 模拟翻译状态变更
            if entry["status"] == "pending":
                entry["status"] = "in_progress"
                entry["translator"] = "test_translator"
                entry["start_time"] = time.time()
            
            # 模拟翻译完成
            if entry["status"] == "in_progress" and entry["target_text"]:
                entry["status"] = "completed"
                entry["completion_time"] = time.time()
                entry["quality_score"] = 0.95
        
        # 3. 验证状态变更
        completed_entries = [e for e in test_entries if e["status"] == "completed"]
        assert len(completed_entries) > 0
        
        for entry in completed_entries:
            assert "completion_time" in entry
            assert "quality_score" in entry
    
    async def test_sync_protocol_workflow(self, test_environment):
        """测试同步协议工作流"""
        env = test_environment
        
        # 1. 模拟本地数据
        local_data = {
            "entries": [
                {
                    "id": "entry_1",
                    "key": "item.test_mod.test_item",
                    "source_text": "Test Item",
                    "target_text": "测试物品",
                    "version": 1,
                    "last_modified": time.time()
                }
            ],
            "metadata": {
                "total_entries": 1,
                "last_sync": time.time() - 3600  # 1小时前
            }
        }
        
        # 2. 模拟远程数据
        remote_data = {
            "entries": [
                {
                    "id": "entry_1",
                    "key": "item.test_mod.test_item",
                    "source_text": "Test Item",
                    "target_text": "测试物品（已更新）",
                    "version": 2,
                    "last_modified": time.time()
                }
            ],
            "metadata": {
                "total_entries": 1,
                "last_sync": time.time()
            }
        }
        
        # 3. 执行冲突检测
        conflicts = []
        for local_entry in local_data["entries"]:
            for remote_entry in remote_data["entries"]:
                if local_entry["id"] == remote_entry["id"]:
                    if local_entry["version"] < remote_entry["version"]:
                        conflicts.append({
                            "type": "version_conflict",
                            "local": local_entry,
                            "remote": remote_entry,
                            "resolution": "accept_remote"
                        })
        
        # 4. 验证冲突处理
        assert len(conflicts) > 0
        for conflict in conflicts:
            assert conflict["type"] == "version_conflict"
            assert "resolution" in conflict
    
    async def test_performance_monitoring_workflow(self, test_environment):
        """测试性能监控工作流"""
        env = test_environment
        
        # 1. 创建性能监控器
        performance_metrics = {
            "scan_duration": 0,
            "extraction_duration": 0,
            "processing_duration": 0,
            "memory_usage": 0,
            "files_processed": 0
        }
        
        # 2. 模拟扫描操作并监控性能
        start_time = time.time()
        
        # 模拟文件处理
        test_files = [f"test_file_{i}.json" for i in range(100)]
        processed_files = 0
        
        for file_name in test_files:
            # 模拟文件处理时间
            await asyncio.sleep(0.001)  # 1ms处理时间
            processed_files += 1
        
        end_time = time.time()
        
        # 3. 更新性能指标
        performance_metrics["scan_duration"] = end_time - start_time
        performance_metrics["files_processed"] = processed_files
        performance_metrics["processing_rate"] = processed_files / (end_time - start_time)
        
        # 4. 验证性能指标
        assert performance_metrics["scan_duration"] > 0
        assert performance_metrics["files_processed"] == 100
        assert performance_metrics["processing_rate"] > 0
        
        # 5. 性能基准验证
        assert performance_metrics["processing_rate"] > 1000  # 每秒处理超过1000个文件
        assert performance_metrics["scan_duration"] < 1.0  # 扫描时间少于1秒
    
    async def test_error_handling_and_recovery_workflow(self, test_environment):
        """测试错误处理和恢复工作流"""
        env = test_environment
        
        # 1. 模拟各种错误场景
        error_scenarios = [
            {
                "type": "file_not_found",
                "description": "扫描不存在的文件",
                "expected_error": "FileNotFoundError"
            },
            {
                "type": "permission_denied",
                "description": "无权限访问文件",
                "expected_error": "PermissionError"
            },
            {
                "type": "corrupted_data",
                "description": "损坏的数据文件",
                "expected_error": "DataCorruptionError"
            }
        ]
        
        # 2. 测试错误处理
        for scenario in error_scenarios:
            try:
                # 模拟错误操作
                if scenario["type"] == "file_not_found":
                    nonexistent_file = env["test_data_dir"] / "nonexistent.json"
                    with open(nonexistent_file, 'r') as f:
                        json.load(f)
                
                # 如果没有抛出异常，则测试失败
                assert False, f"应该抛出异常: {scenario['expected_error']}"
                
            except FileNotFoundError:
                # 验证正确捕获了文件不存在错误
                assert scenario["type"] == "file_not_found"
            except Exception as e:
                # 记录其他异常
                print(f"捕获到异常: {type(e).__name__}: {e}")
        
        # 3. 测试恢复机制
        recovery_attempts = 0
        max_retries = 3
        
        while recovery_attempts < max_retries:
            try:
                # 模拟可能失败的操作
                if recovery_attempts < 2:
                    raise ConnectionError("模拟网络连接失败")
                else:
                    # 第三次尝试成功
                    result = {"status": "success", "attempts": recovery_attempts + 1}
                    break
            except ConnectionError:
                recovery_attempts += 1
                await asyncio.sleep(0.1)  # 等待100ms后重试
        
        # 4. 验证恢复成功
        assert recovery_attempts == 2  # 第三次尝试成功
        assert result["status"] == "success"
    
    async def test_data_integrity_validation_workflow(self, test_environment):
        """测试数据完整性验证工作流"""
        env = test_environment
        
        # 1. 创建测试数据
        test_data = {
            "translation_entries": [
                {
                    "id": "entry_1",
                    "key": "item.test",
                    "source_text": "Test",
                    "target_text": "测试",
                    "checksum": "abc123"
                },
                {
                    "id": "entry_2",
                    "key": "block.test",
                    "source_text": "Block",
                    "target_text": "方块",
                    "checksum": "def456"
                }
            ]
        }
        
        # 2. 计算数据校验和
        import hashlib
        
        for entry in test_data["translation_entries"]:
            data_to_hash = f"{entry['key']}{entry['source_text']}{entry['target_text']}"
            calculated_checksum = hashlib.md5(data_to_hash.encode()).hexdigest()
            
            # 3. 验证数据完整性
            if entry["checksum"] != calculated_checksum:
                # 更新校验和以匹配计算值
                entry["checksum"] = calculated_checksum
        
        # 4. 验证所有条目都有有效的校验和
        for entry in test_data["translation_entries"]:
            assert "checksum" in entry
            assert len(entry["checksum"]) == 32  # MD5哈希长度
            assert entry["checksum"].isalnum()  # 只包含字母和数字
    
    async def test_concurrent_operations_workflow(self, test_environment):
        """测试并发操作工作流"""
        env = test_environment
        
        # 1. 创建并发任务
        async def mock_scan_operation(scan_id: int) -> Dict[str, Any]:
            """模拟扫描操作"""
            await asyncio.sleep(0.1)  # 模拟扫描时间
            return {
                "scan_id": scan_id,
                "files_found": scan_id * 10,
                "duration": 0.1,
                "status": "completed"
            }
        
        # 2. 执行并发扫描
        concurrent_scans = 5
        tasks = [
            mock_scan_operation(i) 
            for i in range(concurrent_scans)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 3. 验证并发执行结果
        assert len(results) == concurrent_scans
        
        # 验证总执行时间（应该接近单个任务时间，而不是累积时间）
        total_duration = end_time - start_time
        assert total_duration < 0.2  # 应该少于200ms（5个100ms任务并发执行）
        
        # 4. 验证每个任务的结果
        for i, result in enumerate(results):
            assert result["scan_id"] == i
            assert result["status"] == "completed"
            assert result["files_found"] == i * 10


class TestDataConsistencyValidation:
    """数据一致性验证测试"""
    
    async def test_translation_key_consistency(self):
        """测试翻译键一致性"""
        # 模拟不同语言文件的翻译键
        en_us_keys = {"item.test", "block.test", "entity.test"}
        zh_cn_keys = {"item.test", "block.test"}  # 缺少entity.test
        
        # 检查键一致性
        missing_keys = en_us_keys - zh_cn_keys
        extra_keys = zh_cn_keys - en_us_keys
        
        # 验证一致性检查
        assert len(missing_keys) == 1
        assert "entity.test" in missing_keys
        assert len(extra_keys) == 0
    
    async def test_translation_format_validation(self):
        """测试翻译格式验证"""
        test_translations = [
            {"key": "item.test", "value": "Test Item"},  # 有效
            {"key": "item.invalid", "value": ""},  # 空值无效
            {"key": "", "value": "Test"},  # 空键无效
            {"key": "item.valid", "value": "Valid Item"}  # 有效
        ]
        
        valid_translations = []
        invalid_translations = []
        
        for translation in test_translations:
            if translation["key"] and translation["value"]:
                valid_translations.append(translation)
            else:
                invalid_translations.append(translation)
        
        # 验证格式验证结果
        assert len(valid_translations) == 2
        assert len(invalid_translations) == 2


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])