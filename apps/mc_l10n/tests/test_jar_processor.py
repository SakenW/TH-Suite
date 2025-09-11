"""
高级JAR处理器测试套件
测试JAR文件处理、备份、验证和完整性检查功能
"""

import pytest
import zipfile
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json
import hashlib
from datetime import datetime

from src.domain.jar_processor import (
    AdvancedJarProcessor,
    JarBackupManager,
    JarSignatureVerifier,
    JarIntegrityChecker,
    JarModificationRecord,
    JarProcessingResult,
    JarBackupInfo,
    IntegrityCheckResult,
    create_jar_processor
)


class TestJarBackupManager:
    """JAR备份管理器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def backup_manager(self, temp_dir):
        """创建备份管理器实例"""
        backup_dir = temp_dir / "backups"
        return JarBackupManager(backup_dir)
    
    @pytest.fixture
    def sample_jar(self, temp_dir):
        """创建样本JAR文件"""
        jar_path = temp_dir / "sample.jar"
        with zipfile.ZipFile(jar_path, 'w') as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zf.writestr("assets/minecraft/lang/en_us.json", '{"gui.done": "Done"}')
            zf.writestr("assets/minecraft/lang/zh_cn.json", '{"gui.done": "完成"}')
        return jar_path
    
    def test_backup_manager_initialization(self, temp_dir):
        """测试备份管理器初始化"""
        backup_dir = temp_dir / "backups"
        manager = JarBackupManager(backup_dir)
        
        assert manager.backup_dir == backup_dir
        assert manager.max_backups == 10
        assert backup_dir.exists()
    
    def test_create_backup(self, backup_manager, sample_jar):
        """测试创建备份"""
        backup_info = backup_manager.create_backup(sample_jar)
        
        assert backup_info.success is True
        assert backup_info.backup_path.exists()
        assert backup_info.backup_path.suffix == '.jar'
        assert backup_info.original_path == sample_jar
        assert isinstance(backup_info.backup_time, datetime)
    
    def test_create_backup_file_not_found(self, backup_manager, temp_dir):
        """测试备份不存在的文件"""
        nonexistent_jar = temp_dir / "nonexistent.jar"
        
        backup_info = backup_manager.create_backup(nonexistent_jar)
        
        assert backup_info.success is False
        assert "不存在" in backup_info.error_message or "not found" in backup_info.error_message.lower()
    
    def test_restore_backup(self, backup_manager, sample_jar, temp_dir):
        """测试恢复备份"""
        # 创建备份
        backup_info = backup_manager.create_backup(sample_jar)
        
        # 修改原文件
        with zipfile.ZipFile(sample_jar, 'w') as zf:
            zf.writestr("modified.txt", "modified content")
        
        # 恢复备份
        success = backup_manager.restore_backup(backup_info.backup_path, sample_jar)
        
        assert success is True
        
        # 验证文件已恢复
        with zipfile.ZipFile(sample_jar, 'r') as zf:
            assert "assets/minecraft/lang/en_us.json" in zf.namelist()
            assert "modified.txt" not in zf.namelist()
    
    def test_list_backups(self, backup_manager, sample_jar):
        """测试列出备份"""
        # 创建多个备份
        backup1 = backup_manager.create_backup(sample_jar)
        backup2 = backup_manager.create_backup(sample_jar)
        
        backups = backup_manager.list_backups(sample_jar)
        
        assert len(backups) == 2
        assert all(isinstance(b, JarBackupInfo) for b in backups)
        assert all(b.original_path == sample_jar for b in backups)
    
    def test_cleanup_old_backups(self, backup_manager, sample_jar):
        """测试清理旧备份"""
        # 设置最大备份数为2
        backup_manager.max_backups = 2
        
        # 创建3个备份
        backups = []
        for i in range(3):
            backup = backup_manager.create_backup(sample_jar)
            backups.append(backup)
        
        # 触发清理
        backup_manager.cleanup_old_backups(sample_jar)
        
        # 验证只保留了2个最新的备份
        remaining_backups = backup_manager.list_backups(sample_jar)
        assert len(remaining_backups) == 2
        
        # 最旧的备份应该被删除
        assert not backups[0].backup_path.exists()
        assert backups[1].backup_path.exists()
        assert backups[2].backup_path.exists()
    
    def test_delete_backup(self, backup_manager, sample_jar):
        """测试删除备份"""
        backup_info = backup_manager.create_backup(sample_jar)
        assert backup_info.backup_path.exists()
        
        success = backup_manager.delete_backup(backup_info.backup_path)
        
        assert success is True
        assert not backup_info.backup_path.exists()
    
    def test_get_backup_info(self, backup_manager, sample_jar):
        """测试获取备份信息"""
        original_backup = backup_manager.create_backup(sample_jar)
        
        backup_info = backup_manager.get_backup_info(original_backup.backup_path)
        
        assert backup_info is not None
        assert backup_info.original_path == sample_jar
        assert backup_info.backup_path == original_backup.backup_path


class TestJarSignatureVerifier:
    """JAR签名验证器测试"""
    
    @pytest.fixture
    def signature_verifier(self):
        """创建签名验证器实例"""
        return JarSignatureVerifier()
    
    @pytest.fixture
    def unsigned_jar(self, temp_dir):
        """创建未签名JAR文件"""
        jar_path = temp_dir / "unsigned.jar"
        with zipfile.ZipFile(jar_path, 'w') as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zf.writestr("test.txt", "test content")
        return jar_path
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_verifier_initialization(self, signature_verifier):
        """测试验证器初始化"""
        assert signature_verifier.trusted_certificates == []
    
    def test_is_signed_unsigned_jar(self, signature_verifier, unsigned_jar):
        """测试检测未签名JAR"""
        is_signed = signature_verifier.is_signed(unsigned_jar)
        assert is_signed is False
    
    def test_is_signed_nonexistent_jar(self, signature_verifier, temp_dir):
        """测试检测不存在的JAR文件"""
        nonexistent_jar = temp_dir / "nonexistent.jar"
        is_signed = signature_verifier.is_signed(nonexistent_jar)
        assert is_signed is False
    
    def test_verify_signature_unsigned_jar(self, signature_verifier, unsigned_jar):
        """测试验证未签名JAR"""
        result = signature_verifier.verify_signature(unsigned_jar)
        
        assert result.is_valid is False
        assert result.is_signed is False
        assert "未签名" in result.error_message or "not signed" in result.error_message.lower()
    
    def test_get_signature_info_unsigned_jar(self, signature_verifier, unsigned_jar):
        """测试获取未签名JAR的签名信息"""
        info = signature_verifier.get_signature_info(unsigned_jar)
        
        assert info["is_signed"] is False
        assert info["certificates"] == []
        assert info["signing_time"] is None
    
    def test_add_trusted_certificate(self, signature_verifier):
        """测试添加受信任证书"""
        cert_data = b"fake_certificate_data"
        
        signature_verifier.add_trusted_certificate(cert_data)
        
        assert len(signature_verifier.trusted_certificates) == 1
        assert signature_verifier.trusted_certificates[0] == cert_data
    
    def test_remove_signature_creates_unsigned_jar(self, signature_verifier, unsigned_jar):
        """测试移除签名（对于未签名JAR应该保持不变）"""
        # 获取原始文件大小
        original_size = unsigned_jar.stat().st_size
        
        success = signature_verifier.remove_signature(unsigned_jar)
        
        assert success is True
        # 文件大小应该基本不变（可能有轻微差异）
        new_size = unsigned_jar.stat().st_size
        assert abs(new_size - original_size) < 100


class TestJarIntegrityChecker:
    """JAR完整性检查器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def integrity_checker(self):
        """创建完整性检查器实例"""
        return JarIntegrityChecker()
    
    @pytest.fixture
    def valid_jar(self, temp_dir):
        """创建有效的JAR文件"""
        jar_path = temp_dir / "valid.jar"
        with zipfile.ZipFile(jar_path, 'w') as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nMain-Class: TestMain\n")
            zf.writestr("TestMain.class", b"fake class bytes")
            zf.writestr("assets/test/lang/en_us.json", '{"test.key": "Test Value"}')
        return jar_path
    
    def test_checker_initialization(self, integrity_checker):
        """测试检查器初始化"""
        assert hasattr(integrity_checker, 'check_integrity')
        assert hasattr(integrity_checker, 'validate_jar_structure')
        assert hasattr(integrity_checker, 'calculate_checksums')
    
    def test_check_integrity_valid_jar(self, integrity_checker, valid_jar):
        """测试检查有效JAR的完整性"""
        result = integrity_checker.check_integrity(valid_jar)
        
        assert isinstance(result, IntegrityCheckResult)
        assert result.is_valid is True
        assert result.jar_path == valid_jar
        assert len(result.issues) == 0
    
    def test_check_integrity_nonexistent_jar(self, integrity_checker, temp_dir):
        """测试检查不存在JAR文件的完整性"""
        nonexistent_jar = temp_dir / "nonexistent.jar"
        
        result = integrity_checker.check_integrity(nonexistent_jar)
        
        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("不存在" in issue or "not found" in issue.lower() for issue in result.issues)
    
    def test_check_integrity_corrupted_jar(self, integrity_checker, temp_dir):
        """测试检查损坏JAR文件的完整性"""
        corrupted_jar = temp_dir / "corrupted.jar"
        # 创建一个无效的ZIP文件
        with open(corrupted_jar, 'wb') as f:
            f.write(b"this is not a valid zip file")
        
        result = integrity_checker.check_integrity(corrupted_jar)
        
        assert result.is_valid is False
        assert len(result.issues) > 0
    
    def test_validate_jar_structure(self, integrity_checker, valid_jar):
        """测试验证JAR结构"""
        issues = integrity_checker.validate_jar_structure(valid_jar)
        
        # 有效的JAR应该没有结构问题
        assert len(issues) == 0
    
    def test_calculate_checksums(self, integrity_checker, valid_jar):
        """测试计算校验和"""
        checksums = integrity_checker.calculate_checksums(valid_jar)
        
        assert isinstance(checksums, dict)
        assert len(checksums) > 0
        
        # 检查是否包含预期的文件
        expected_files = ["META-INF/MANIFEST.MF", "TestMain.class", "assets/test/lang/en_us.json"]
        for file in expected_files:
            assert file in checksums
            assert len(checksums[file]) == 64  # SHA256 hash length
    
    def test_verify_checksums(self, integrity_checker, valid_jar):
        """测试验证校验和"""
        # 首先计算校验和
        original_checksums = integrity_checker.calculate_checksums(valid_jar)
        
        # 验证相同的文件
        is_valid = integrity_checker.verify_checksums(valid_jar, original_checksums)
        assert is_valid is True
        
        # 修改文件内容后验证
        with zipfile.ZipFile(valid_jar, 'a') as zf:
            zf.writestr("new_file.txt", "new content")
        
        is_valid = integrity_checker.verify_checksums(valid_jar, original_checksums)
        assert is_valid is False


class TestAdvancedJarProcessor:
    """高级JAR处理器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def jar_processor(self, temp_dir):
        """创建JAR处理器实例"""
        return AdvancedJarProcessor(temp_dir / "backups")
    
    @pytest.fixture
    def test_jar(self, temp_dir):
        """创建测试JAR文件"""
        jar_path = temp_dir / "test_mod.jar"
        with zipfile.ZipFile(jar_path, 'w') as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zf.writestr("assets/testmod/lang/en_us.json", json.dumps({
                "item.testmod.test_item": "Test Item",
                "block.testmod.test_block": "Test Block"
            }))
            zf.writestr("assets/testmod/lang/zh_cn.json", json.dumps({
                "item.testmod.test_item": "测试物品"
            }))
        return jar_path
    
    def test_processor_initialization(self, jar_processor):
        """测试处理器初始化"""
        assert isinstance(jar_processor.backup_manager, JarBackupManager)
        assert isinstance(jar_processor.signature_verifier, JarSignatureVerifier)
        assert isinstance(jar_processor.integrity_checker, JarIntegrityChecker)
    
    def test_process_jar_basic(self, jar_processor, test_jar):
        """测试基本JAR处理"""
        # 准备修改操作
        modifications = {
            "assets/testmod/lang/zh_cn.json": json.dumps({
                "item.testmod.test_item": "测试物品",
                "block.testmod.test_block": "测试方块"  # 新增翻译
            })
        }
        
        result = jar_processor.process_jar(
            test_jar,
            modifications,
            create_backup=True
        )
        
        assert result.success is True
        assert result.jar_path == test_jar
        assert result.backup_created is True
        assert result.backup_path is not None
        assert len(result.modifications) > 0
    
    def test_process_jar_with_validation(self, jar_processor, test_jar):
        """测试带验证的JAR处理"""
        modifications = {
            "assets/testmod/lang/fr_fr.json": json.dumps({
                "item.testmod.test_item": "Objet de Test"
            })
        }
        
        result = jar_processor.process_jar(
            test_jar,
            modifications,
            create_backup=True,
            validate_integrity=True
        )
        
        assert result.success is True
        assert result.integrity_check is not None
        assert result.integrity_check.is_valid is True
    
    def test_process_jar_without_backup(self, jar_processor, test_jar):
        """测试不创建备份的JAR处理"""
        modifications = {
            "new_file.txt": "new content"
        }
        
        result = jar_processor.process_jar(
            test_jar,
            modifications,
            create_backup=False
        )
        
        assert result.success is True
        assert result.backup_created is False
        assert result.backup_path is None
    
    def test_process_jar_failure_handling(self, jar_processor, temp_dir):
        """测试JAR处理失败情况"""
        nonexistent_jar = temp_dir / "nonexistent.jar"
        modifications = {"test.txt": "content"}
        
        result = jar_processor.process_jar(
            nonexistent_jar,
            modifications
        )
        
        assert result.success is False
        assert result.error_message is not None
        assert len(result.modifications) == 0
    
    def test_extract_language_files(self, jar_processor, test_jar):
        """测试提取语言文件"""
        lang_files = jar_processor.extract_language_files(test_jar)
        
        assert len(lang_files) == 2  # en_us.json 和 zh_cn.json
        
        # 检查英文文件
        en_file = next((f for f in lang_files if f["locale"] == "en_us"), None)
        assert en_file is not None
        assert "item.testmod.test_item" in en_file["content"]
        assert en_file["content"]["item.testmod.test_item"] == "Test Item"
        
        # 检查中文文件
        zh_file = next((f for f in lang_files if f["locale"] == "zh_cn"), None)
        assert zh_file is not None
        assert "item.testmod.test_item" in zh_file["content"]
        assert zh_file["content"]["item.testmod.test_item"] == "测试物品"
    
    def test_update_language_files(self, jar_processor, test_jar):
        """测试更新语言文件"""
        new_translations = {
            "zh_cn": {
                "item.testmod.test_item": "测试物品（更新）",
                "block.testmod.test_block": "测试方块"
            },
            "ja_jp": {
                "item.testmod.test_item": "テストアイテム"
            }
        }
        
        result = jar_processor.update_language_files(
            test_jar,
            new_translations,
            create_backup=True
        )
        
        assert result.success is True
        assert len(result.modifications) >= 2  # 至少更新了2个语言文件
        
        # 验证文件是否正确更新
        updated_lang_files = jar_processor.extract_language_files(test_jar)
        
        zh_file = next((f for f in updated_lang_files if f["locale"] == "zh_cn"), None)
        assert zh_file is not None
        assert zh_file["content"]["item.testmod.test_item"] == "测试物品（更新）"
        assert zh_file["content"]["block.testmod.test_block"] == "测试方块"
        
        ja_file = next((f for f in updated_lang_files if f["locale"] == "ja_jp"), None)
        assert ja_file is not None
        assert ja_file["content"]["item.testmod.test_item"] == "テストアイテム"
    
    def test_rollback_changes(self, jar_processor, test_jar):
        """测试回滚更改"""
        # 首先进行修改
        modifications = {"test_file.txt": "test content"}
        result = jar_processor.process_jar(
            test_jar,
            modifications,
            create_backup=True
        )
        
        assert result.success is True
        backup_path = result.backup_path
        
        # 验证修改已应用
        with zipfile.ZipFile(test_jar, 'r') as zf:
            assert "test_file.txt" in zf.namelist()
        
        # 回滚更改
        rollback_success = jar_processor.rollback_changes(test_jar, backup_path)
        assert rollback_success is True
        
        # 验证回滚成功
        with zipfile.ZipFile(test_jar, 'r') as zf:
            assert "test_file.txt" not in zf.namelist()
    
    def test_get_processing_history(self, jar_processor, test_jar):
        """测试获取处理历史"""
        # 执行一些处理操作
        modifications1 = {"file1.txt": "content1"}
        jar_processor.process_jar(test_jar, modifications1)
        
        modifications2 = {"file2.txt": "content2"}
        jar_processor.process_jar(test_jar, modifications2)
        
        # 获取处理历史
        history = jar_processor.get_processing_history(test_jar)
        
        assert len(history) == 2
        assert all(isinstance(record, JarModificationRecord) for record in history)
        assert history[0].jar_path == test_jar
        assert history[1].jar_path == test_jar
    
    def test_cleanup_old_backups(self, jar_processor, test_jar):
        """测试清理旧备份"""
        # 设置最大备份数
        jar_processor.backup_manager.max_backups = 2
        
        # 创建多个备份
        for i in range(4):
            modifications = {f"file{i}.txt": f"content{i}"}
            jar_processor.process_jar(test_jar, modifications, create_backup=True)
        
        # 获取备份列表
        backups = jar_processor.backup_manager.list_backups(test_jar)
        
        # 应该只保留最新的2个备份
        assert len(backups) <= 2


class TestFactoryFunctions:
    """工厂函数测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_create_jar_processor_default(self):
        """测试创建默认JAR处理器"""
        processor = create_jar_processor()
        
        assert isinstance(processor, AdvancedJarProcessor)
        assert isinstance(processor.backup_manager, JarBackupManager)
        assert isinstance(processor.signature_verifier, JarSignatureVerifier)
        assert isinstance(processor.integrity_checker, JarIntegrityChecker)
    
    def test_create_jar_processor_custom_backup_dir(self, temp_dir):
        """测试创建自定义备份目录的JAR处理器"""
        custom_backup_dir = temp_dir / "custom_backups"
        processor = create_jar_processor(backup_dir=custom_backup_dir)
        
        assert processor.backup_manager.backup_dir == custom_backup_dir
        assert custom_backup_dir.exists()


class TestIntegrationScenarios:
    """集成场景测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def complete_mod_jar(self, temp_dir):
        """创建完整的MOD JAR文件"""
        jar_path = temp_dir / "complete_mod.jar"
        
        manifest_content = """Manifest-Version: 1.0
Implementation-Title: Complete Test Mod
Implementation-Version: 1.0.0
Implementation-Vendor: Test Vendor
"""
        
        with zipfile.ZipFile(jar_path, 'w') as zf:
            zf.writestr("META-INF/MANIFEST.MF", manifest_content)
            zf.writestr("META-INF/mods.toml", """
modLoader="javafml"
loaderVersion="[47,)"
license="MIT"

[[mods]]
modId="completemod"
version="1.0.0"
displayName="Complete Test Mod"
description="A complete test mod for integration testing"
""")
            
            # 添加多个语言文件
            languages = {
                "en_us": {
                    "item.completemod.sword": "Complete Sword",
                    "item.completemod.shield": "Complete Shield",
                    "block.completemod.ore": "Complete Ore"
                },
                "zh_cn": {
                    "item.completemod.sword": "完整之剑",
                    "item.completemod.shield": "完整盾牌"
                },
                "ja_jp": {
                    "item.completemod.sword": "コンプリートソード"
                }
            }
            
            for lang_code, translations in languages.items():
                zf.writestr(
                    f"assets/completemod/lang/{lang_code}.json",
                    json.dumps(translations, ensure_ascii=False, indent=2)
                )
        
        return jar_path
    
    @pytest.mark.asyncio
    async def test_complete_localization_workflow(self, temp_dir, complete_mod_jar):
        """测试完整的本地化工作流"""
        processor = create_jar_processor(temp_dir / "backups")
        
        # 1. 提取现有语言文件
        existing_lang_files = processor.extract_language_files(complete_mod_jar)
        assert len(existing_lang_files) == 3  # en_us, zh_cn, ja_jp
        
        # 2. 添加新的翻译
        new_translations = {
            "zh_cn": {
                "item.completemod.sword": "完整之剑",
                "item.completemod.shield": "完整盾牌", 
                "block.completemod.ore": "完整矿石"  # 新增翻译
            },
            "fr_fr": {  # 新增语言
                "item.completemod.sword": "Épée Complète",
                "item.completemod.shield": "Bouclier Complet",
                "block.completemod.ore": "Minerai Complet"
            }
        }
        
        # 3. 应用翻译更新
        result = processor.update_language_files(
            complete_mod_jar,
            new_translations,
            create_backup=True,
            validate_integrity=True
        )
        
        assert result.success is True
        assert result.backup_created is True
        assert result.integrity_check.is_valid is True
        
        # 4. 验证更新结果
        updated_lang_files = processor.extract_language_files(complete_mod_jar)
        assert len(updated_lang_files) == 4  # 现在应该有4种语言
        
        # 检查中文翻译是否完整
        zh_file = next((f for f in updated_lang_files if f["locale"] == "zh_cn"), None)
        assert zh_file is not None
        assert len(zh_file["content"]) == 3  # 应该有3个翻译项目
        assert zh_file["content"]["block.completemod.ore"] == "完整矿石"
        
        # 检查法文翻译是否正确添加
        fr_file = next((f for f in updated_lang_files if f["locale"] == "fr_fr"), None)
        assert fr_file is not None
        assert fr_file["content"]["item.completemod.sword"] == "Épée Complète"
        
        # 5. 测试回滚功能
        rollback_success = processor.rollback_changes(
            complete_mod_jar,
            result.backup_path
        )
        assert rollback_success is True
        
        # 验证回滚后状态
        rolled_back_files = processor.extract_language_files(complete_mod_jar)
        assert len(rolled_back_files) == 3  # 回滚到原来的3种语言
        
        fr_file = next((f for f in rolled_back_files if f["locale"] == "fr_fr"), None)
        assert fr_file is None  # 法文文件应该被移除


if __name__ == "__main__":
    pytest.main([__file__, "-v"])