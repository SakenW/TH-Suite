"""
冲突解决器测试套件
测试翻译冲突检测和解决机制
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Dict, Optional

from src.services.conflict_resolver import (
    MinecraftConflictResolver,
    ConflictType,
    ConflictResolution,
    ConflictDetail,
    FileConflict,
    create_conflict_resolver,
    detect_and_resolve_conflicts
)

from src.adapters.projection import MinecraftLanguageFile


class TestConflictDetail:
    """冲突详情测试"""
    
    def test_conflict_detail_creation(self):
        """测试冲突详情创建"""
        detail = ConflictDetail(
            key="gui.done",
            local_value="完成",
            remote_value="确定",
            conflict_type=ConflictType.CONTENT_MISMATCH,
            severity="medium",
            description="翻译内容不同",
            suggestions=["检查上下文", "选择更准确的翻译"]
        )
        
        assert detail.key == "gui.done"
        assert detail.local_value == "完成"
        assert detail.remote_value == "确定"
        assert detail.conflict_type == ConflictType.CONTENT_MISMATCH
        assert detail.severity == "medium"
        assert len(detail.suggestions) == 2
    
    def test_conflict_detail_to_dict(self):
        """测试冲突详情字典转换"""
        detail = ConflictDetail(
            key="item.apple",
            local_value="苹果",
            remote_value="红苹果",
            conflict_type=ConflictType.CONTENT_MISMATCH,
            severity="low",
            description="描述性差异",
            suggestions=["保留本地版本"]
        )
        
        result = detail.to_dict()
        
        assert result["key"] == "item.apple"
        assert result["local_value"] == "苹果"
        assert result["remote_value"] == "红苹果"
        assert result["conflict_type"] == ConflictType.CONTENT_MISMATCH
        assert result["severity"] == "low"


class TestFileConflict:
    """文件冲突测试"""
    
    def test_file_conflict_creation(self):
        """测试文件冲突创建"""
        conflict_details = [
            ConflictDetail(
                key="gui.done",
                local_value="完成",
                remote_value="确定",
                conflict_type=ConflictType.CONTENT_MISMATCH,
                severity="medium",
                description="翻译不同",
                suggestions=["检查上下文"]
            )
        ]
        
        file_conflict = FileConflict(
            mod_id="minecraft",
            language="zh_cn",
            file_path="assets/minecraft/lang/zh_cn.json",
            conflict_details=conflict_details,
            local_hash="abc123",
            remote_hash="def456"
        )
        
        assert file_conflict.mod_id == "minecraft"
        assert file_conflict.language == "zh_cn"
        assert len(file_conflict.conflict_details) == 1
        assert file_conflict.local_hash == "abc123"
        assert file_conflict.remote_hash == "def456"
    
    def test_file_conflict_severity_level(self):
        """测试文件冲突严重性级别计算"""
        # 测试关键冲突
        critical_detail = ConflictDetail(
            key="test.key",
            local_value="local",
            remote_value="remote",
            conflict_type=ConflictType.PLACEHOLDER_MISMATCH,
            severity="critical",
            description="关键冲突",
            suggestions=[]
        )
        
        file_conflict = FileConflict(
            mod_id="test",
            language="zh_cn",
            file_path="test.json",
            conflict_details=[critical_detail],
            local_hash="hash1",
            remote_hash="hash2"
        )
        
        assert file_conflict.severity_level == "critical"
        
        # 测试高级冲突
        high_detail = ConflictDetail(
            key="test.key",
            local_value="local",
            remote_value="remote", 
            conflict_type=ConflictType.MISSING_KEYS,
            severity="high",
            description="高级冲突",
            suggestions=[]
        )
        
        file_conflict.conflict_details = [high_detail]
        assert file_conflict.severity_level == "high"
        
        # 测试无冲突
        file_conflict.conflict_details = []
        assert file_conflict.severity_level == "none"
    
    def test_file_conflict_to_dict(self):
        """测试文件冲突字典转换"""
        detail = ConflictDetail(
            key="test.key",
            local_value="本地值",
            remote_value="远程值",
            conflict_type=ConflictType.CONTENT_MISMATCH,
            severity="low",
            description="测试冲突",
            suggestions=["建议1"]
        )
        
        file_conflict = FileConflict(
            mod_id="testmod",
            language="zh_cn",
            file_path="test.json",
            conflict_details=[detail],
            local_hash="local123",
            remote_hash="remote456",
            resolution_strategy=ConflictResolution.KEEP_LOCAL
        )
        
        result = file_conflict.to_dict()
        
        assert result["mod_id"] == "testmod"
        assert result["language"] == "zh_cn"
        assert result["resolution_strategy"] == "keep_local"
        assert len(result["conflict_details"]) == 1


class TestMinecraftConflictResolver:
    """Minecraft冲突解决器测试"""
    
    @pytest.fixture
    def resolver(self):
        """创建冲突解决器实例"""
        return MinecraftConflictResolver()
    
    def test_resolver_initialization(self, resolver):
        """测试解决器初始化"""
        assert len(resolver.placeholder_patterns) > 0
        assert len(resolver.critical_keys) > 0
        assert "gui.done" in resolver.critical_keys
    
    @pytest.mark.asyncio
    async def test_detect_local_conflicts_no_existing_files(self, resolver):
        """测试没有现有文件时的冲突检测"""
        new_files = [
            self._create_language_file("minecraft", "zh_cn", {"gui.done": "完成"})
        ]
        
        conflicts = await resolver.detect_local_conflicts("test_pack", new_files, None)
        
        assert len(conflicts) == 0
    
    @pytest.mark.asyncio
    async def test_detect_local_conflicts_no_conflicts(self, resolver):
        """测试无冲突情况"""
        existing_file = self._create_language_file("minecraft", "zh_cn", {"gui.done": "完成"})
        new_file = self._create_language_file("minecraft", "zh_cn", {"gui.done": "完成"})
        
        conflicts = await resolver.detect_local_conflicts("test_pack", [new_file], [existing_file])
        
        assert len(conflicts) == 0
    
    @pytest.mark.asyncio
    async def test_detect_content_mismatch_conflict(self, resolver):
        """测试内容不匹配冲突"""
        existing_file = self._create_language_file("minecraft", "zh_cn", {"gui.done": "完成"})
        new_file = self._create_language_file("minecraft", "zh_cn", {"gui.done": "确定"})
        
        conflicts = await resolver.detect_local_conflicts("test_pack", [new_file], [existing_file])
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.mod_id == "minecraft"
        assert conflict.language == "zh_cn"
        assert len(conflict.conflict_details) == 1
        
        detail = conflict.conflict_details[0]
        assert detail.key == "gui.done"
        assert detail.local_value == "完成"
        assert detail.remote_value == "确定"
        assert detail.conflict_type == ConflictType.CONTENT_MISMATCH
    
    @pytest.mark.asyncio
    async def test_detect_missing_keys_conflict(self, resolver):
        """测试缺失键冲突"""
        existing_file = self._create_language_file("minecraft", "zh_cn", {
            "gui.done": "完成",
            "gui.cancel": "取消"
        })
        new_file = self._create_language_file("minecraft", "zh_cn", {
            "gui.done": "完成"
        })
        
        conflicts = await resolver.detect_local_conflicts("test_pack", [new_file], [existing_file])
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        
        # 应该检测到缺失的 gui.cancel 键
        missing_detail = next((d for d in conflict.conflict_details if d.conflict_type == ConflictType.MISSING_KEYS), None)
        assert missing_detail is not None
        assert missing_detail.key == "gui.cancel"
        assert missing_detail.local_value == "取消"
        assert missing_detail.remote_value is None
    
    @pytest.mark.asyncio
    async def test_detect_extra_keys_conflict(self, resolver):
        """测试多余键冲突"""
        existing_file = self._create_language_file("minecraft", "zh_cn", {
            "gui.done": "完成"
        })
        new_file = self._create_language_file("minecraft", "zh_cn", {
            "gui.done": "完成",
            "gui.new_feature": "新功能"
        })
        
        conflicts = await resolver.detect_local_conflicts("test_pack", [new_file], [existing_file])
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        
        # 应该检测到多余的 gui.new_feature 键
        extra_detail = next((d for d in conflict.conflict_details if d.conflict_type == ConflictType.EXTRA_KEYS), None)
        assert extra_detail is not None
        assert extra_detail.key == "gui.new_feature"
        assert extra_detail.local_value is None
        assert extra_detail.remote_value == "新功能"
    
    @pytest.mark.asyncio
    async def test_detect_placeholder_mismatch(self, resolver):
        """测试占位符不匹配冲突"""
        existing_file = self._create_language_file("minecraft", "zh_cn", {
            "commands.give.success": "给予了 %s 个 %s"
        })
        new_file = self._create_language_file("minecraft", "zh_cn", {
            "commands.give.success": "给予了 %s 物品"  # 缺少一个占位符
        })
        
        conflicts = await resolver.detect_local_conflicts("test_pack", [new_file], [existing_file])
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        
        detail = conflict.conflict_details[0]
        assert detail.conflict_type == ConflictType.PLACEHOLDER_MISMATCH
        assert detail.severity == "critical"  # commands.give.success 是关键键
    
    def test_analyze_value_conflict_placeholder_mismatch(self, resolver):
        """测试分析占位符不匹配"""
        conflict_type, severity, description, suggestions = resolver._analyze_value_conflict(
            "commands.give.success",
            "给予了 %s 个 %s",
            "给予了 %s 物品"
        )
        
        assert conflict_type == ConflictType.PLACEHOLDER_MISMATCH
        assert severity == "critical"
        assert "占位符不匹配" in description
        assert len(suggestions) > 0
    
    def test_analyze_value_conflict_length_difference(self, resolver):
        """测试分析长度差异冲突"""
        short_text = "短"
        long_text = "这是一个非常长的翻译文本，包含了很多详细信息"
        
        conflict_type, severity, description, suggestions = resolver._analyze_value_conflict(
            "test.key",
            short_text,
            long_text
        )
        
        assert conflict_type == ConflictType.CONTENT_MISMATCH
        assert severity == "medium"
        assert "长度差异较大" in description
    
    def test_analyze_value_conflict_critical_key(self, resolver):
        """测试分析关键键冲突"""
        conflict_type, severity, description, suggestions = resolver._analyze_value_conflict(
            "gui.done",  # 这是关键键
            "完成",
            "确定"
        )
        
        assert conflict_type == ConflictType.CONTENT_MISMATCH
        assert severity == "critical"
    
    @pytest.mark.asyncio
    async def test_resolve_conflicts_keep_remote(self, resolver):
        """测试解决冲突 - 保留远程版本"""
        new_file = self._create_language_file("minecraft", "zh_cn", {"gui.done": "确定"})
        
        conflict = FileConflict(
            mod_id="minecraft",
            language="zh_cn", 
            file_path="zh_cn.json",
            conflict_details=[],
            local_hash="local123",
            remote_hash="remote456",
            resolution_strategy=ConflictResolution.KEEP_REMOTE
        )
        
        resolved_files = await resolver.resolve_conflicts([new_file], [conflict])
        
        assert len(resolved_files) == 1
        resolved_file = resolved_files[0]
        assert resolved_file.translations["gui.done"] == "确定"
    
    @pytest.mark.asyncio
    async def test_resolve_conflicts_auto_merge(self, resolver):
        """测试解决冲突 - 自动合并"""
        new_file = self._create_language_file("minecraft", "zh_cn", {
            "gui.done": "完成",
            "gui.new": "新功能"
        })
        
        # 创建包含缺失键和额外键的冲突
        conflict_details = [
            ConflictDetail(
                key="gui.old",
                local_value="旧功能",
                remote_value=None,
                conflict_type=ConflictType.MISSING_KEYS,
                severity="medium",
                description="缺失键",
                suggestions=[]
            ),
            ConflictDetail(
                key="gui.new",
                local_value=None,
                remote_value="新功能",
                conflict_type=ConflictType.EXTRA_KEYS,
                severity="low",
                description="额外键",
                suggestions=[]
            )
        ]
        
        conflict = FileConflict(
            mod_id="minecraft",
            language="zh_cn",
            file_path="zh_cn.json",
            conflict_details=conflict_details,
            local_hash="local123",
            remote_hash="remote456",
            resolution_strategy=ConflictResolution.MERGE_AUTO
        )
        
        resolved_files = await resolver.resolve_conflicts([new_file], [conflict])
        
        assert len(resolved_files) == 1
        resolved_file = resolved_files[0]
        
        # 应该保留缺失的键，接受新增的键
        assert "gui.done" in resolved_file.translations
        assert "gui.new" in resolved_file.translations
        assert resolved_file.translations["gui.old"] == "旧功能"  # 从本地恢复
        assert resolved_file.translations["gui.new"] == "新功能"  # 接受新增
    
    def test_determine_auto_resolution_strategy_critical_conflicts(self, resolver):
        """测试确定自动解决策略 - 关键冲突"""
        conflict = FileConflict(
            mod_id="test",
            language="zh_cn",
            file_path="test.json",
            conflict_details=[
                ConflictDetail(
                    key="test.key",
                    local_value="本地",
                    remote_value="远程",
                    conflict_type=ConflictType.PLACEHOLDER_MISMATCH,
                    severity="critical",
                    description="关键冲突",
                    suggestions=[]
                )
            ],
            local_hash="local123",
            remote_hash="remote456"
        )
        
        strategy = resolver._determine_auto_resolution_strategy(conflict)
        assert strategy == ConflictResolution.MERGE_MANUAL
    
    def test_determine_auto_resolution_strategy_mostly_extra_keys(self, resolver):
        """测试确定自动解决策略 - 主要是新增键"""
        conflict_details = []
        
        # 添加多个额外键冲突
        for i in range(5):
            conflict_details.append(ConflictDetail(
                key=f"new.key.{i}",
                local_value=None,
                remote_value=f"新值{i}",
                conflict_type=ConflictType.EXTRA_KEYS,
                severity="low",
                description="额外键",
                suggestions=[]
            ))
        
        # 添加一个其他类型的冲突
        conflict_details.append(ConflictDetail(
            key="other.key",
            local_value="本地",
            remote_value="远程",
            conflict_type=ConflictType.CONTENT_MISMATCH,
            severity="medium",
            description="内容冲突",
            suggestions=[]
        ))
        
        conflict = FileConflict(
            mod_id="test",
            language="zh_cn",
            file_path="test.json",
            conflict_details=conflict_details,
            local_hash="local123",
            remote_hash="remote456"
        )
        
        strategy = resolver._determine_auto_resolution_strategy(conflict)
        assert strategy == ConflictResolution.MERGE_AUTO
    
    def test_get_conflict_summary_empty(self, resolver):
        """测试获取空冲突摘要"""
        summary = resolver.get_conflict_summary([])
        
        assert summary["total_conflicts"] == 0
        assert summary["severity_distribution"] == {}
        assert summary["conflict_type_distribution"] == {}
        assert summary["affected_files"] == 0
    
    def test_get_conflict_summary_with_conflicts(self, resolver):
        """测试获取冲突摘要"""
        conflicts = [
            FileConflict(
                mod_id="mod1",
                language="zh_cn",
                file_path="test1.json",
                conflict_details=[
                    ConflictDetail(
                        key="key1",
                        local_value="本地1",
                        remote_value="远程1",
                        conflict_type=ConflictType.CONTENT_MISMATCH,
                        severity="high",
                        description="冲突1",
                        suggestions=[]
                    ),
                    ConflictDetail(
                        key="key2",
                        local_value="本地2",
                        remote_value=None,
                        conflict_type=ConflictType.MISSING_KEYS,
                        severity="medium",
                        description="冲突2",
                        suggestions=[]
                    )
                ],
                local_hash="hash1",
                remote_hash="hash2"
            )
        ]
        
        summary = resolver.get_conflict_summary(conflicts)
        
        assert summary["total_conflicts"] == 1
        assert summary["affected_files"] == 1
        assert summary["total_conflict_details"] == 2
        assert summary["severity_distribution"]["high"] == 1
        assert summary["conflict_type_distribution"]["content_mismatch"] == 1
        assert summary["conflict_type_distribution"]["missing_keys"] == 1
    
    def _create_language_file(self, mod_id: str, language: str, translations: Dict[str, str]) -> MinecraftLanguageFile:
        """创建语言文件实例"""
        lang_file = MinecraftLanguageFile(mod_id, language, f"{language}.json")
        lang_file.translations = translations
        return lang_file


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_create_conflict_resolver(self):
        """测试创建冲突解决器"""
        resolver = create_conflict_resolver()
        
        assert isinstance(resolver, MinecraftConflictResolver)
        assert len(resolver.placeholder_patterns) > 0
        assert len(resolver.critical_keys) > 0
    
    @pytest.mark.asyncio
    async def test_detect_and_resolve_conflicts_convenience(self):
        """测试便捷的检测和解决冲突函数"""
        new_files = [
            self._create_language_file("minecraft", "zh_cn", {"gui.done": "完成"})
        ]
        existing_files = [
            self._create_language_file("minecraft", "zh_cn", {"gui.done": "确定"})
        ]
        
        resolved_files, conflicts = await detect_and_resolve_conflicts(
            "test_pack",
            new_files,
            existing_files
        )
        
        assert len(resolved_files) == 1
        assert len(conflicts) == 1
        assert conflicts[0].mod_id == "minecraft"
    
    def _create_language_file(self, mod_id: str, language: str, translations: Dict[str, str]) -> MinecraftLanguageFile:
        """创建语言文件实例"""
        lang_file = MinecraftLanguageFile(mod_id, language, f"{language}.json")
        lang_file.translations = translations
        return lang_file


class TestIntegrationScenarios:
    """集成场景测试"""
    
    @pytest.mark.asyncio
    async def test_complex_conflict_resolution_scenario(self):
        """测试复杂冲突解决场景"""
        resolver = MinecraftConflictResolver()
        
        # 现有文件：有一些基础翻译
        existing_file = MinecraftLanguageFile("complexmod", "zh_cn", "zh_cn.json")
        existing_file.translations = {
            "item.complexmod.sword": "铁剑",
            "item.complexmod.shield": "木盾",
            "block.complexmod.ore": "铁矿石",
            "gui.complexmod.inventory": "背包",
            "commands.complexmod.give": "给予了 %s 个 %s"  # 有占位符
        }
        
        # 新文件：有更新和新增内容
        new_file = MinecraftLanguageFile("complexmod", "zh_cn", "zh_cn.json")
        new_file.translations = {
            "item.complexmod.sword": "精铁剑",        # 内容变更
            "item.complexmod.shield": "木盾",         # 无变更
            "block.complexmod.diamond_ore": "钻石矿石",  # 新增
            "gui.complexmod.inventory": "物品栏",      # 内容变更
            "commands.complexmod.give": "给予了 %s 物品"  # 占位符不匹配
        }
        # 注意：缺少了 block.complexmod.ore
        
        # 检测冲突
        conflicts = await resolver.detect_local_conflicts(
            "complex_pack",
            [new_file],
            [existing_file]
        )
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        
        # 验证检测到的冲突类型
        conflict_types = [detail.conflict_type for detail in conflict.conflict_details]
        
        assert ConflictType.CONTENT_MISMATCH in conflict_types  # 内容变更
        assert ConflictType.MISSING_KEYS in conflict_types      # 缺失的矿石
        assert ConflictType.EXTRA_KEYS in conflict_types        # 新增的钻石矿石
        assert ConflictType.PLACEHOLDER_MISMATCH in conflict_types  # 占位符问题
        
        # 验证严重性级别
        assert conflict.severity_level == "critical"  # 因为有占位符不匹配
        
        # 解决冲突（自动策略）
        resolved_files = await resolver.resolve_conflicts([new_file], conflicts)
        
        assert len(resolved_files) == 1
        resolved_file = resolved_files[0]
        
        # 验证解决结果
        assert "item.complexmod.sword" in resolved_file.translations
        assert "block.complexmod.ore" in resolved_file.translations  # 应该恢复缺失的键
        assert "block.complexmod.diamond_ore" in resolved_file.translations  # 应该保留新增的键
    
    @pytest.mark.asyncio
    async def test_multiple_files_conflict_resolution(self):
        """测试多文件冲突解决"""
        resolver = MinecraftConflictResolver()
        
        # 创建多个现有文件
        existing_files = [
            self._create_language_file("mod1", "zh_cn", {
                "item.mod1.sword": "剑",
                "item.mod1.shield": "盾"
            }),
            self._create_language_file("mod2", "zh_cn", {
                "block.mod2.stone": "石头",
                "block.mod2.dirt": "泥土"
            })
        ]
        
        # 创建对应的新文件
        new_files = [
            self._create_language_file("mod1", "zh_cn", {
                "item.mod1.sword": "铁剑",  # 内容变更
                "item.mod1.shield": "盾",   # 无变更
                "item.mod1.bow": "弓"      # 新增
            }),
            self._create_language_file("mod2", "zh_cn", {
                "block.mod2.stone": "石头",  # 无变更
                "block.mod2.grass": "草地"  # 新增，缺少 dirt
            })
        ]
        
        # 检测冲突
        conflicts = await resolver.detect_local_conflicts(
            "multi_pack",
            new_files,
            existing_files
        )
        
        # 应该检测到两个文件的冲突
        assert len(conflicts) == 2
        
        mod1_conflict = next((c for c in conflicts if c.mod_id == "mod1"), None)
        mod2_conflict = next((c for c in conflicts if c.mod_id == "mod2"), None)
        
        assert mod1_conflict is not None
        assert mod2_conflict is not None
        
        # 验证 mod1 的冲突
        mod1_conflict_types = [detail.conflict_type for detail in mod1_conflict.conflict_details]
        assert ConflictType.CONTENT_MISMATCH in mod1_conflict_types  # sword 变更
        assert ConflictType.EXTRA_KEYS in mod1_conflict_types        # bow 新增
        
        # 验证 mod2 的冲突
        mod2_conflict_types = [detail.conflict_type for detail in mod2_conflict.conflict_details]
        assert ConflictType.MISSING_KEYS in mod2_conflict_types      # dirt 缺失
        assert ConflictType.EXTRA_KEYS in mod2_conflict_types        # grass 新增
        
        # 解决所有冲突
        resolved_files = await resolver.resolve_conflicts(new_files, conflicts)
        
        assert len(resolved_files) == 2
        
        # 验证解决结果
        mod1_resolved = next((f for f in resolved_files if f.mod_id == "mod1"), None)
        mod2_resolved = next((f for f in resolved_files if f.mod_id == "mod2"), None)
        
        assert mod1_resolved is not None
        assert mod2_resolved is not None
        
        # mod1 应该包含所有键
        assert "item.mod1.sword" in mod1_resolved.translations
        assert "item.mod1.shield" in mod1_resolved.translations
        assert "item.mod1.bow" in mod1_resolved.translations
        
        # mod2 应该恢复缺失的键并保留新增的键
        assert "block.mod2.stone" in mod2_resolved.translations
        assert "block.mod2.dirt" in mod2_resolved.translations  # 应该恢复
        assert "block.mod2.grass" in mod2_resolved.translations  # 应该保留
    
    def _create_language_file(self, mod_id: str, language: str, translations: Dict[str, str]) -> MinecraftLanguageFile:
        """创建语言文件实例"""
        lang_file = MinecraftLanguageFile(mod_id, language, f"{language}.json")
        lang_file.translations = translations
        return lang_file


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_empty_file_conflict_detection(self):
        """测试空文件冲突检测"""
        resolver = MinecraftConflictResolver()
        
        empty_existing = MinecraftLanguageFile("test", "zh_cn", "zh_cn.json")
        empty_existing.translations = {}
        
        new_file = MinecraftLanguageFile("test", "zh_cn", "zh_cn.json") 
        new_file.translations = {"key": "value"}
        
        conflicts = await resolver.detect_local_conflicts(
            "test_pack",
            [new_file],
            [empty_existing]
        )
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert any(detail.conflict_type == ConflictType.EXTRA_KEYS for detail in conflict.conflict_details)
    
    @pytest.mark.asyncio
    async def test_identical_hash_no_conflict(self):
        """测试相同哈希值时无冲突"""
        resolver = MinecraftConflictResolver()
        
        # 创建两个内容完全相同的文件
        translations = {"gui.done": "完成", "gui.cancel": "取消"}
        
        existing_file = MinecraftLanguageFile("test", "zh_cn", "zh_cn.json")
        existing_file.translations = translations.copy()
        
        new_file = MinecraftLanguageFile("test", "zh_cn", "zh_cn.json")
        new_file.translations = translations.copy()
        
        conflicts = await resolver.detect_local_conflicts(
            "test_pack",
            [new_file],
            [existing_file]
        )
        
        assert len(conflicts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])