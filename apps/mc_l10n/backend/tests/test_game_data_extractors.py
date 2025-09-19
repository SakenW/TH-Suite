"""
游戏专属数据提取器测试
测试Minecraft、RimWorld、Factorio数据提取器的功能
"""

import asyncio
import json
import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from infrastructure.services.game_data_extractors import (
    MinecraftDataExtractor, RimWorldDataExtractor, FactorioDataExtractor,
    GameType, FileFormat, TranslationEntry, LanguageFile, ExtractorRegistry
)
from infrastructure.services.unified_data_extraction_service import UnifiedDataExtractionService


class TestMinecraftDataExtractor:
    """Minecraft数据提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        return MinecraftDataExtractor(":memory:")
    
    @pytest.fixture
    def sample_minecraft_mod_data(self):
        return {
            "type": "mod",
            "mod_id": "test_mod",
            "name": "测试MOD",
            "path": "/test/mod.jar",
            "language_files": [
                {
                    "type": "language_file",
                    "language_code": "zh_cn",
                    "file_path": "assets/test_mod/lang/zh_cn.json",
                    "translations": {
                        "item.test_mod.test_item": "测试物品",
                        "block.test_mod.test_block": "测试方块",
                        "gui.test_mod.title": "测试界面"
                    }
                }
            ]
        }
    
    def test_game_type(self, extractor):
        assert extractor._get_game_type() == GameType.MINECRAFT
    
    def test_supported_formats(self, extractor):
        formats = extractor._get_supported_formats()
        assert FileFormat.JSON in formats
        assert FileFormat.LANG in formats
        assert FileFormat.PROPERTIES in formats
    
    @pytest.mark.asyncio
    async def test_extract_from_mod_data(self, extractor, sample_minecraft_mod_data):
        discovered_items = [sample_minecraft_mod_data]
        
        result = await extractor.extract_from_discovered_items(discovered_items)
        
        assert result.success
        assert len(result.language_files) == 1
        
        lang_file = result.language_files[0]
        assert lang_file.locale == "zh_cn"
        assert lang_file.carrier_type == "mod"
        assert lang_file.carrier_uid == "test_mod"
        assert len(lang_file.entries) == 3
        
        # 检查翻译条目
        entries_by_key = {entry.key: entry for entry in lang_file.entries}
        assert "item.test_mod.test_item" in entries_by_key
        assert entries_by_key["item.test_mod.test_item"].source_text == "测试物品"
    
    @pytest.mark.asyncio
    async def test_parse_json_content(self, extractor):
        json_content = '''
        {
            "item.test.sword": "测试剑",
            "block.test.ore": "测试矿石"
        }
        '''
        
        entries = await extractor._parse_json_content(json_content, "test_mod")
        
        assert len(entries) == 2
        assert entries[0].key == "item.test.sword"
        assert entries[0].source_text == "测试剑"
        assert entries[0].namespace == "test_mod"
        assert entries[0].format == FileFormat.JSON
    
    @pytest.mark.asyncio
    async def test_parse_lang_content(self, extractor):
        lang_content = '''
        # 测试注释
        item.test.sword=测试剑
        block.test.ore=测试矿石
        # 另一个注释
        gui.test.title=测试标题
        '''
        
        entries = await extractor._parse_lang_content(lang_content, "test_mod")
        
        assert len(entries) == 3
        assert entries[0].key == "item.test.sword"
        assert entries[0].source_text == "测试剑"
        assert entries[0].format == FileFormat.LANG
    
    def test_detect_file_format(self, extractor):
        assert extractor._detect_file_format(Path("test.json")) == FileFormat.JSON
        assert extractor._detect_file_format(Path("test.lang")) == FileFormat.LANG
        assert extractor._detect_file_format(Path("test.properties")) == FileFormat.PROPERTIES
    
    def test_extract_namespace_from_path(self, extractor):
        assert extractor._extract_namespace_from_path("assets/testmod/lang/zh_cn.json") == "testmod"
        assert extractor._extract_namespace_from_path("assets/minecraft/lang/en_us.json") == "minecraft"
        assert extractor._extract_namespace_from_path("invalid/path.json") == "minecraft"


class TestRimWorldDataExtractor:
    """RimWorld数据提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        return RimWorldDataExtractor(":memory:")
    
    @pytest.fixture
    def sample_definjection_xml(self):
        return '''<?xml version="1.0" encoding="utf-8"?>
        <LanguageData>
            <ThingDef.Meal_Simple.label>简单食物</ThingDef.Meal_Simple.label>
            <ThingDef.Meal_Simple.description>基础的营养食物</ThingDef.Meal_Simple.description>
            <ThingDef.Weapon_Pistol.label>手枪</ThingDef.Weapon_Pistol.label>
        </LanguageData>'''
    
    def test_game_type(self, extractor):
        assert extractor._get_game_type() == GameType.RIMWORLD
    
    def test_supported_formats(self, extractor):
        formats = extractor._get_supported_formats()
        assert FileFormat.XML in formats
    
    @pytest.mark.asyncio
    async def test_extract_definjection_xml(self, extractor, sample_definjection_xml):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(sample_definjection_xml)
            f.flush()
            
            try:
                carrier_info = {"mod_id": "test_mod"}
                lang_file = await extractor._extract_definjection_xml(
                    Path(f.name), "zh_cn", "ThingDefs", carrier_info
                )
                
                assert lang_file is not None
                assert lang_file.locale == "zh_cn"
                assert lang_file.format == FileFormat.XML
                assert len(lang_file.entries) == 3
                
                # 检查条目
                entries_by_key = {entry.key: entry for entry in lang_file.entries}
                assert "ThingDefs.ThingDef.Meal_Simple.label" in entries_by_key
                assert entries_by_key["ThingDefs.ThingDef.Meal_Simple.label"].source_text == "简单食物"
                
            finally:
                os.unlink(f.name)


class TestFactorioDataExtractor:
    """Factorio数据提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        return FactorioDataExtractor(":memory:")
    
    @pytest.fixture
    def sample_locale_cfg(self):
        return '''[entity-name]
transport-belt=传送带
inserter=机械臂

[item-name]
iron-ore=铁矿石
copper-ore=铜矿石

[recipe-name]
iron-plate=铁板'''
    
    def test_game_type(self, extractor):
        assert extractor._get_game_type() == GameType.FACTORIO
    
    def test_supported_formats(self, extractor):
        formats = extractor._get_supported_formats()
        assert FileFormat.CFG in formats
    
    @pytest.mark.asyncio
    async def test_parse_cfg_content(self, extractor, sample_locale_cfg):
        entries = await extractor._parse_cfg_content(sample_locale_cfg, "test.cfg", "test_mod")
        
        assert len(entries) == 5
        
        # 检查条目
        entries_by_key = {entry.key: entry for entry in entries}
        assert "entity-name.transport-belt" in entries_by_key
        assert entries_by_key["entity-name.transport-belt"].source_text == "传送带"
        assert "item-name.iron-ore" in entries_by_key
        assert entries_by_key["item-name.iron-ore"].source_text == "铁矿石"
    
    def test_has_placeholders(self, extractor):
        assert extractor._has_placeholders("Hello __1__ world __2__")
        assert not extractor._has_placeholders("Hello world")
    
    def test_process_factorio_interpolation(self, extractor):
        text = "Hello __1__ world __2__"
        result = extractor._process_factorio_interpolation(text)
        assert result == text  # 保持原样


class TestExtractorRegistry:
    """提取器注册表测试"""
    
    def test_registry_initialization(self):
        # 清空注册表
        ExtractorRegistry._extractors.clear()
        
        # 注册提取器
        minecraft_extractor = MinecraftDataExtractor(":memory:")
        ExtractorRegistry.register(GameType.MINECRAFT, minecraft_extractor)
        
        # 验证注册
        registered = ExtractorRegistry.get_extractor(GameType.MINECRAFT)
        assert registered is minecraft_extractor
    
    def test_detect_minecraft_game_type(self):
        minecraft_items = [
            {"type": "mod", "loader_type": "forge", "path": "/test/mod.jar"},
            {"path": "assets/testmod/lang/zh_cn.json"}
        ]
        
        detected = ExtractorRegistry.detect_game_type(minecraft_items)
        assert detected == GameType.MINECRAFT
    
    def test_detect_rimworld_game_type(self):
        rimworld_items = [
            {"path": "Languages/ChineseSimplified/DefInjected/ThingDef/Weapons.xml"}
        ]
        
        detected = ExtractorRegistry.detect_game_type(rimworld_items)
        assert detected == GameType.RIMWORLD
    
    def test_detect_factorio_game_type(self):
        factorio_items = [
            {"path": "locale/zh-CN/base.cfg"}
        ]
        
        detected = ExtractorRegistry.detect_game_type(factorio_items)
        assert detected == GameType.FACTORIO


class TestUnifiedDataExtractionService:
    """统一数据提取服务测试"""
    
    @pytest.fixture
    def service(self):
        return UnifiedDataExtractionService(":memory:")
    
    @pytest.fixture
    def mixed_discovered_items(self):
        return [
            {
                "type": "mod",
                "mod_id": "minecraft_mod",
                "loader_type": "forge",
                "path": "/test/minecraft_mod.jar",
                "language_files": [
                    {
                        "type": "language_file",
                        "language_code": "zh_cn",
                        "file_path": "assets/minecraft_mod/lang/zh_cn.json",
                        "translations": {"item.test": "测试物品"}
                    }
                ]
            },
            {
                "path": "Languages/ChineseSimplified/DefInjected/ThingDef/Test.xml",
                "type": "definjection_file"
            },
            {
                "path": "locale/zh-CN/test.cfg",
                "type": "locale_file"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_group_items_by_game(self, service, mixed_discovered_items):
        grouped = await service._group_items_by_game(mixed_discovered_items)
        
        assert GameType.MINECRAFT in grouped
        assert GameType.RIMWORLD in grouped
        assert GameType.FACTORIO in grouped
        
        assert len(grouped[GameType.MINECRAFT]) == 1
        assert len(grouped[GameType.RIMWORLD]) == 1
        assert len(grouped[GameType.FACTORIO]) == 1
    
    def test_get_supported_games(self, service):
        supported = service.get_supported_games()
        assert "minecraft" in supported
        assert "rimworld" in supported
        assert "factorio" in supported


class TestLanguageFile:
    """语言文件数据结构测试"""
    
    def test_language_file_creation(self):
        entries = [
            TranslationEntry("test.key1", "测试文本1", namespace="test"),
            TranslationEntry("test.key2", "测试文本2", namespace="test")
        ]
        
        lang_file = LanguageFile(
            uid="test_uid",
            path="/test/file.json",
            relative_path="assets/test/lang/zh_cn.json",
            locale="zh_cn",
            format=FileFormat.JSON,
            size=100,
            carrier_type="mod",
            carrier_uid="test_mod",
            entries=entries
        )
        
        assert lang_file.uid == "test_uid"
        assert lang_file.locale == "zh_cn"
        assert len(lang_file.entries) == 2
        assert lang_file.keyset_hash  # 应该自动计算
        assert lang_file.content_hash  # 应该自动计算
    
    def test_keyset_hash_calculation(self):
        entries1 = [
            TranslationEntry("key1", "text1"),
            TranslationEntry("key2", "text2")
        ]
        
        entries2 = [
            TranslationEntry("key2", "text2"),
            TranslationEntry("key1", "text1")  # 顺序不同
        ]
        
        lang_file1 = LanguageFile(
            uid="", path="", relative_path="", locale="",
            format=FileFormat.JSON, size=0, carrier_type="",
            carrier_uid="", entries=entries1
        )
        
        lang_file2 = LanguageFile(
            uid="", path="", relative_path="", locale="",
            format=FileFormat.JSON, size=0, carrier_type="",
            carrier_uid="", entries=entries2
        )
        
        # 键集哈希应该相同（键的顺序不影响）
        assert lang_file1.keyset_hash == lang_file2.keyset_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])