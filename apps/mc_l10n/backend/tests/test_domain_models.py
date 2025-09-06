"""
领域模型单元测试
"""

import pytest
from datetime import datetime
from domain.models.mod import Mod, ModId, ModMetadata, ModVersion, ModState
from domain.models.translation_project import TranslationProject, ProjectStatus
from domain.value_objects import (
    FilePath, ContentHash, LanguageCode, 
    QualityScore, Percentage, TranslatorId
)
from domain.events import ModScannedEvent, TaskAssignedEvent


class TestModAggregate:
    """测试Mod聚合根"""
    
    def test_create_mod(self):
        """测试创建Mod"""
        mod = Mod.create(
            mod_id="test_mod",
            name="Test Mod",
            version="1.0.0",
            file_path="/path/to/mod.jar"
        )
        
        assert mod.mod_id == ModId("test_mod")
        assert mod.metadata.name == "Test Mod"
        assert mod.metadata.version == ModVersion("1.0.0")
        assert mod.state == ModState.ACTIVE
        assert len(mod.domain_events) == 1
    
    def test_start_scan_validation(self):
        """测试扫描前验证"""
        mod = Mod.create(
            mod_id="test_mod",
            name="Test Mod",
            version="1.0.0",
            file_path="/path/to/mod.jar"
        )
        
        # 停用模组
        mod.deactivate()
        
        # 尝试扫描停用的模组应该失败
        with pytest.raises(ValueError, match="Cannot scan inactive mod"):
            mod.start_scan()
    
    def test_scan_lifecycle(self):
        """测试扫描生命周期"""
        mod = Mod.create(
            mod_id="test_mod",
            name="Test Mod",
            version="1.0.0",
            file_path="/path/to/mod.jar"
        )
        
        # 开始扫描
        mod.start_scan()
        assert mod.scan_status == "scanning"
        
        # 完成扫描
        content_hash = ContentHash.from_content("test content")
        mod.scan_completed(content_hash, 100)
        
        assert mod.scan_status == "completed"
        assert mod.last_content_hash == content_hash
        assert mod.translation_count == 100
        
        # 检查事件
        events = [e for e in mod.domain_events if isinstance(e, ModScannedEvent)]
        assert len(events) == 1
        assert events[0].mod_id == mod.mod_id
        assert events[0].translation_count == 100
    
    def test_translation_locking(self):
        """测试翻译锁定"""
        mod = Mod.create(
            mod_id="test_mod",
            name="Test Mod",
            version="1.0.0",
            file_path="/path/to/mod.jar"
        )
        
        # 锁定翻译
        mod.lock_translations("user1")
        assert mod.is_locked
        assert mod.locked_by == "user1"
        
        # 其他用户不能锁定
        with pytest.raises(ValueError, match="already locked"):
            mod.lock_translations("user2")
        
        # 解锁
        mod.unlock_translations("user1")
        assert not mod.is_locked
    
    def test_needs_rescan(self):
        """测试重新扫描判断"""
        mod = Mod.create(
            mod_id="test_mod",
            name="Test Mod",
            version="1.0.0",
            file_path="/path/to/mod.jar"
        )
        
        # 初始扫描
        hash1 = ContentHash.from_content("content1")
        mod.scan_completed(hash1, 50)
        
        # 相同内容不需要重新扫描
        assert not mod.needs_rescan(hash1)
        
        # 不同内容需要重新扫描
        hash2 = ContentHash.from_content("content2")
        assert mod.needs_rescan(hash2)


class TestTranslationProject:
    """测试翻译项目聚合根"""
    
    def test_create_project(self):
        """测试创建项目"""
        project = TranslationProject(
            project_id="proj_001",
            name="Test Project",
            target_languages={"zh_cn", "ja_jp"}
        )
        
        assert project.project_id == "proj_001"
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.DRAFT
        assert len(project.target_languages) == 2
    
    def test_project_lifecycle(self):
        """测试项目生命周期"""
        project = TranslationProject(
            project_id="proj_001",
            name="Test Project",
            target_languages={"zh_cn"}
        )
        
        # 激活项目
        project.activate()
        assert project.status == ProjectStatus.ACTIVE
        
        # 暂停项目
        project.pause()
        assert project.status == ProjectStatus.PAUSED
        
        # 恢复项目
        project.resume()
        assert project.status == ProjectStatus.ACTIVE
        
        # 完成项目
        project.complete()
        assert project.status == ProjectStatus.COMPLETED
    
    def test_add_mods(self):
        """测试添加模组"""
        project = TranslationProject(
            project_id="proj_001",
            name="Test Project",
            target_languages={"zh_cn"}
        )
        
        # 添加模组
        mod_id1 = ModId("mod1")
        mod_id2 = ModId("mod2")
        
        project.add_mod(mod_id1)
        project.add_mod(mod_id2)
        
        assert len(project.mod_ids) == 2
        assert mod_id1 in project.mod_ids
        assert mod_id2 in project.mod_ids
        
        # 重复添加应该忽略
        project.add_mod(mod_id1)
        assert len(project.mod_ids) == 2
    
    def test_assign_translator(self):
        """测试分配翻译者"""
        project = TranslationProject(
            project_id="proj_001",
            name="Test Project",
            target_languages={"zh_cn"}
        )
        
        # 激活项目
        project.activate()
        
        # 分配翻译者
        project.assign_translator(
            translator_id=TranslatorId("user1"),
            language="zh_cn",
            mod_ids=[ModId("mod1")]
        )
        
        # 检查事件
        events = [e for e in project.domain_events if isinstance(e, TaskAssignedEvent)]
        assert len(events) == 1
        assert events[0].translator_id == TranslatorId("user1")
        assert events[0].language == "zh_cn"
    
    def test_auto_assignment(self):
        """测试自动分配"""
        project = TranslationProject(
            project_id="proj_001",
            name="Test Project",
            target_languages={"zh_cn"}
        )
        
        # 启用自动分配
        project.enable_auto_assignment()
        assert project.auto_assignment_enabled
        
        # 禁用自动分配
        project.disable_auto_assignment()
        assert not project.auto_assignment_enabled


class TestValueObjects:
    """测试值对象"""
    
    def test_file_path_validation(self):
        """测试文件路径验证"""
        # 有效路径
        path = FilePath("/valid/path/to/file.jar")
        assert path.value == "/valid/path/to/file.jar"
        
        # 无效路径
        with pytest.raises(ValueError, match="cannot be empty"):
            FilePath("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            FilePath("   ")
    
    def test_content_hash(self):
        """测试内容哈希"""
        # 从内容生成哈希
        hash1 = ContentHash.from_content("test content")
        hash2 = ContentHash.from_content("test content")
        hash3 = ContentHash.from_content("different content")
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert hash1.value == "9a0364b9e99bb480dd25e1f0284c8555"
    
    def test_language_code(self):
        """测试语言代码"""
        # 有效语言代码
        assert LanguageCode.ZH_CN.value == "zh_cn"
        assert LanguageCode.EN_US.value == "en_us"
        
        # 从字符串转换
        lang = LanguageCode.from_string("zh_cn")
        assert lang == LanguageCode.ZH_CN
        
        # 无效语言代码
        lang = LanguageCode.from_string("invalid")
        assert lang is None
    
    def test_quality_score(self):
        """测试质量分数"""
        # 有效分数
        score = QualityScore(0.85)
        assert score.value == 0.85
        assert score.is_high_quality()
        
        # 边界值
        score_min = QualityScore(0.0)
        score_max = QualityScore(1.0)
        assert score_min.value == 0.0
        assert score_max.value == 1.0
        
        # 无效分数
        with pytest.raises(ValueError, match="must be between"):
            QualityScore(-0.1)
        
        with pytest.raises(ValueError, match="must be between"):
            QualityScore(1.1)
    
    def test_percentage(self):
        """测试百分比"""
        # 有效百分比
        pct = Percentage(75)
        assert pct.value == 75
        assert pct.as_decimal() == 0.75
        
        # 边界值
        pct_min = Percentage(0)
        pct_max = Percentage(100)
        assert pct_min.value == 0
        assert pct_max.value == 100
        
        # 无效百分比
        with pytest.raises(ValueError, match="must be between"):
            Percentage(-1)
        
        with pytest.raises(ValueError, match="must be between"):
            Percentage(101)