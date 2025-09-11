"""
投影适配器测试套件
测试Minecraft投影适配器的双向转换功能
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import asyncio

from src.adapters.projection import (
    MinecraftProjectionAdapter,
    MinecraftLanguageFile,
    ProjectionSpec,
    UIDA,
    TextStabilizer,
    load_projection_spec,
    create_minecraft_adapter
)


class TestProjectionSpec:
    """投影规范测试"""
    
    def test_projection_spec_creation(self):
        """测试投影规范创建"""
        spec = ProjectionSpec(
            name="test_spec",
            version="1.0.0",
            source_format="minecraft_lang",
            target_format="trans_hub_uida",
            key_expressions={
                "mod_prefix": "^([a-z_]+)\\.",
                "category": "\\.(gui|item|block|entity)\\.",
                "identifier": "\\.([^.]+)$"
            },
            context_mapping={
                "gui": "界面",
                "item": "物品",
                "block": "方块",
                "entity": "实体"
            }
        )
        
        assert spec.name == "test_spec"
        assert spec.version == "1.0.0"
        assert "mod_prefix" in spec.key_expressions
        assert "gui" in spec.context_mapping
    
    def test_key_expression_matching(self):
        """测试键表达式匹配"""
        spec = ProjectionSpec(
            key_expressions={
                "mod_id": "^([a-z_]+)\\.",
                "category": "\\.(gui|item|block)\\.",
                "name": "\\.([^.]+)$"
            }
        )
        
        key = "minecraft.gui.done"
        
        # 模拟正则表达式匹配
        import re
        mod_match = re.search(spec.key_expressions["mod_id"], key)
        category_match = re.search(spec.key_expressions["category"], key)
        name_match = re.search(spec.key_expressions["name"], key)
        
        assert mod_match and mod_match.group(1) == "minecraft"
        assert category_match and category_match.group(1) == "gui"
        assert name_match and name_match.group(1) == "done"


class TestTextStabilizer:
    """文本稳定器测试"""
    
    def test_normalize_whitespace(self):
        """测试空白字符标准化"""
        stabilizer = TextStabilizer()
        
        test_cases = [
            ("  多个  空格  ", "多个 空格"),
            ("制表符\t和\n换行", "制表符 和 换行"),
            ("", ""),
            ("正常文本", "正常文本")
        ]
        
        for input_text, expected in test_cases:
            result = stabilizer.normalize_whitespace(input_text)
            assert result == expected
    
    def test_normalize_quotes(self):
        """测试引号标准化"""
        stabilizer = TextStabilizer()
        
        test_cases = [
            ('"英文引号"', '"英文引号"'),
            ('"中文引号"', '"中文引号"'),
            ("'单引号'", "'单引号'"),
            ("混合\"引号'测试", "混合\"引号'测试")
        ]
        
        for input_text, expected in test_cases:
            result = stabilizer.normalize_quotes(input_text)
            assert result == expected
    
    def test_remove_formatting_codes(self):
        """测试移除格式代码"""
        stabilizer = TextStabilizer()
        
        test_cases = [
            ("§c红色文本", "红色文本"),
            ("§l§n粗体下划线", "粗体下划线"),
            ("正常§r重置§a绿色", "正常重置绿色"),
            ("无格式代码", "无格式代码")
        ]
        
        for input_text, expected in test_cases:
            result = stabilizer.remove_formatting_codes(input_text)
            assert result == expected
    
    def test_stabilize_text(self):
        """测试文本稳定化"""
        stabilizer = TextStabilizer()
        
        input_text = "  §c红色  文本§r  \n  §l粗体  "
        expected = "红色 文本 粗体"
        
        result = stabilizer.stabilize_text(input_text)
        assert result == expected


class TestUIDA:
    """UIDA测试"""
    
    def test_uida_creation(self):
        """测试UIDA创建"""
        uida = UIDA(
            namespace="minecraft",
            category="gui",
            identifier="done",
            context={"type": "button", "screen": "main_menu"}
        )
        
        assert uida.namespace == "minecraft"
        assert uida.category == "gui"
        assert uida.identifier == "done"
        assert uida.context["type"] == "button"
    
    def test_uida_to_string(self):
        """测试UIDA字符串转换"""
        uida = UIDA(
            namespace="minecraft",
            category="gui",
            identifier="done"
        )
        
        expected = "minecraft:gui.done"
        result = uida.to_string()
        assert result == expected
    
    def test_uida_from_string(self):
        """测试从字符串创建UIDA"""
        uida_str = "minecraft:gui.done"
        uida = UIDA.from_string(uida_str)
        
        assert uida.namespace == "minecraft"
        assert uida.category == "gui"
        assert uida.identifier == "done"
    
    def test_uida_to_dict(self):
        """测试UIDA字典转换"""
        uida = UIDA(
            namespace="jei",
            category="item",
            identifier="recipe_book",
            context={"mod": "jei", "version": "15.2.0"}
        )
        
        result = uida.to_dict()
        expected = {
            "namespace": "jei",
            "category": "item",
            "identifier": "recipe_book",
            "context": {"mod": "jei", "version": "15.2.0"}
        }
        
        assert result == expected


class TestMinecraftLanguageFile:
    """Minecraft语言文件测试"""
    
    def test_language_file_creation(self):
        """测试语言文件创建"""
        lang_file = MinecraftLanguageFile(
            mod_id="minecraft",
            language="zh_cn",
            file_path="/path/to/zh_cn.json"
        )
        
        assert lang_file.mod_id == "minecraft"
        assert lang_file.language == "zh_cn"
        assert lang_file.file_path == "/path/to/zh_cn.json"
        assert lang_file.translations == {}
    
    def test_add_translation(self):
        """测试添加翻译"""
        lang_file = MinecraftLanguageFile("minecraft", "zh_cn", "test.json")
        
        lang_file.add_translation("gui.done", "完成")
        lang_file.add_translation("item.apple", "苹果")
        
        assert len(lang_file.translations) == 2
        assert lang_file.translations["gui.done"] == "完成"
        assert lang_file.translations["item.apple"] == "苹果"
    
    def test_get_translation(self):
        """测试获取翻译"""
        lang_file = MinecraftLanguageFile("minecraft", "zh_cn", "test.json")
        lang_file.translations = {
            "gui.done": "完成",
            "item.apple": "苹果"
        }
        
        assert lang_file.get_translation("gui.done") == "完成"
        assert lang_file.get_translation("nonexistent") is None
        assert lang_file.get_translation("nonexistent", "默认值") == "默认值"
    
    def test_to_dict(self):
        """测试字典转换"""
        lang_file = MinecraftLanguageFile("jei", "zh_cn", "test.json")
        lang_file.translations = {"jei.item.recipe": "配方"}
        lang_file.mod_version = "15.2.0"
        
        result = lang_file.to_dict()
        
        assert result["mod_id"] == "jei"
        assert result["language"] == "zh_cn"
        assert result["translations"]["jei.item.recipe"] == "配方"
        assert result["mod_version"] == "15.2.0"


class TestMinecraftProjectionAdapter:
    """Minecraft投影适配器测试"""
    
    @pytest.fixture
    def mock_projection_spec(self):
        """模拟投影规范"""
        return ProjectionSpec(
            name="minecraft_projection",
            version="1.0.0",
            source_format="minecraft_lang",
            target_format="trans_hub_uida",
            key_expressions={
                "namespace": "^([a-z_]+)\\.",
                "category": "\\.(gui|item|block|entity)\\.",
                "identifier": "\\.([^.]+)$"
            },
            context_mapping={
                "gui": "界面",
                "item": "物品",
                "block": "方块",
                "entity": "实体"
            },
            reverse_key_template="{namespace}.{category}.{identifier}"
        )
    
    @pytest.fixture
    def adapter(self, mock_projection_spec):
        """创建适配器实例"""
        return MinecraftProjectionAdapter(mock_projection_spec)
    
    def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter.spec.name == "minecraft_projection"
        assert isinstance(adapter.text_stabilizer, TextStabilizer)
    
    @pytest.mark.asyncio
    async def test_minecraft_key_to_uida(self, adapter):
        """测试Minecraft键转换为UIDA"""
        key = "minecraft.gui.done"
        text = "完成"
        
        uida = await adapter._minecraft_key_to_uida(key, text)
        
        assert uida.namespace == "minecraft"
        assert uida.category == "gui"
        assert uida.identifier == "done"
        assert uida.context["original_key"] == key
        assert uida.context["source_text"] == text
    
    @pytest.mark.asyncio
    async def test_uida_to_minecraft_key(self, adapter):
        """测试UIDA转换为Minecraft键"""
        uida = UIDA(
            namespace="minecraft",
            category="gui",
            identifier="done",
            context={"original_key": "minecraft.gui.done"}
        )
        
        key = await adapter._uida_to_minecraft_key(uida)
        assert key == "minecraft.gui.done"
    
    @pytest.mark.asyncio
    async def test_project_to_uida(self, adapter):
        """测试投影到UIDA"""
        lang_file = MinecraftLanguageFile("minecraft", "zh_cn", "zh_cn.json")
        lang_file.translations = {
            "minecraft.gui.done": "完成",
            "minecraft.item.apple": "苹果",
            "minecraft.block.stone": "石头"
        }
        
        result = await adapter.project_to_uida([lang_file])
        
        assert len(result) == 1
        uida_file = result[0]
        assert len(uida_file.entries) == 3
        
        # 检查UIDA条目
        done_entry = next((e for e in uida_file.entries if e.uida.identifier == "done"), None)
        assert done_entry is not None
        assert done_entry.target_text == "完成"
        assert done_entry.uida.category == "gui"
    
    @pytest.mark.asyncio
    async def test_project_from_uida(self, adapter):
        """测试从UIDA投影"""
        from dataclasses import dataclass
        from typing import List
        
        @dataclass
        class MockUIDAEntry:
            uida: UIDA
            source_text: str
            target_text: str
        
        @dataclass
        class MockUIDAFile:
            namespace: str
            language: str
            entries: List[MockUIDAEntry]
        
        uida_entries = [
            MockUIDAEntry(
                uida=UIDA("minecraft", "gui", "done"),
                source_text="Done",
                target_text="完成"
            ),
            MockUIDAEntry(
                uida=UIDA("minecraft", "item", "apple"),
                source_text="Apple", 
                target_text="苹果"
            )
        ]
        
        uida_file = MockUIDAFile("minecraft", "zh_cn", uida_entries)
        
        result = await adapter.project_from_uida([uida_file])
        
        assert len(result) == 1
        lang_file = result[0]
        assert lang_file.mod_id == "minecraft"
        assert lang_file.language == "zh_cn"
        assert len(lang_file.translations) == 2
        assert lang_file.translations["minecraft.gui.done"] == "完成"
        assert lang_file.translations["minecraft.item.apple"] == "苹果"


class TestProjectionSpecLoader:
    """投影规范加载器测试"""
    
    def test_load_projection_spec_success(self):
        """测试成功加载投影规范"""
        yaml_content = """
name: "minecraft_projection"
version: "1.0.0"
source_format: "minecraft_lang"
target_format: "trans_hub_uida"
key_expressions:
  namespace: "^([a-z_]+)\\\\."
  category: "\\\\.(gui|item|block)\\\\."
  identifier: "\\\\.([^.]+)$"
context_mapping:
  gui: "界面"
  item: "物品"
  block: "方块"
reverse_key_template: "{namespace}.{category}.{identifier}"
"""
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("pathlib.Path.exists", return_value=True):
                spec = load_projection_spec("test_spec.yaml")
                
                assert spec.name == "minecraft_projection"
                assert spec.version == "1.0.0"
                assert "namespace" in spec.key_expressions
                assert "gui" in spec.context_mapping
    
    def test_load_projection_spec_file_not_found(self):
        """测试文件不存在"""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                load_projection_spec("nonexistent.yaml")


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    @patch('src.adapters.projection.load_projection_spec')
    def test_create_minecraft_adapter(self, mock_load_spec):
        """测试创建Minecraft适配器"""
        mock_spec = ProjectionSpec(
            name="minecraft",
            version="1.0.0",
            source_format="minecraft_lang",
            target_format="trans_hub_uida"
        )
        mock_load_spec.return_value = mock_spec
        
        adapter = create_minecraft_adapter("test_spec.yaml")
        
        assert isinstance(adapter, MinecraftProjectionAdapter)
        assert adapter.spec.name == "minecraft"
        mock_load_spec.assert_called_once_with("test_spec.yaml")


class TestIntegrationScenarios:
    """集成场景测试"""
    
    @pytest.mark.asyncio
    async def test_roundtrip_conversion(self):
        """测试双向转换一致性"""
        spec = ProjectionSpec(
            name="test",
            version="1.0.0",
            source_format="minecraft_lang",
            target_format="trans_hub_uida",
            key_expressions={
                "namespace": "^([a-z_]+)\\.",
                "category": "\\.(gui|item|block)\\.",
                "identifier": "\\.([^.]+)$"
            },
            context_mapping={
                "gui": "界面",
                "item": "物品",
                "block": "方块"
            },
            reverse_key_template="{namespace}.{category}.{identifier}"
        )
        
        adapter = MinecraftProjectionAdapter(spec)
        
        # 创建原始语言文件
        original_lang_file = MinecraftLanguageFile("minecraft", "zh_cn", "zh_cn.json")
        original_lang_file.translations = {
            "minecraft.gui.done": "完成",
            "minecraft.item.apple": "苹果"
        }
        
        # 正向转换：Minecraft -> UIDA
        uida_files = await adapter.project_to_uida([original_lang_file])
        assert len(uida_files) == 1
        
        # 反向转换：UIDA -> Minecraft
        restored_lang_files = await adapter.project_from_uida(uida_files)
        assert len(restored_lang_files) == 1
        
        restored_lang_file = restored_lang_files[0]
        
        # 验证往返转换的一致性
        assert restored_lang_file.mod_id == original_lang_file.mod_id
        assert restored_lang_file.language == original_lang_file.language
        assert len(restored_lang_file.translations) == len(original_lang_file.translations)
        
        for key, value in original_lang_file.translations.items():
            assert key in restored_lang_file.translations
            assert restored_lang_file.translations[key] == value
    
    @pytest.mark.asyncio
    async def test_complex_key_patterns(self):
        """测试复杂键模式处理"""
        spec = ProjectionSpec(
            key_expressions={
                "namespace": "^([a-z_]+)\\.",
                "category": "\\.(gui|item|block|entity|effect)\\.",
                "subcategory": "\\.(\\w+)\\.",
                "identifier": "\\.([^.]+)$"
            }
        )
        
        adapter = MinecraftProjectionAdapter(spec)
        
        complex_key = "minecraft.entity.zombie.name"
        uida = await adapter._minecraft_key_to_uida(complex_key, "僵尸")
        
        assert uida.namespace == "minecraft"
        assert uida.category == "entity"
        assert uida.identifier == "name"
        assert uida.context["original_key"] == complex_key
    
    @pytest.mark.asyncio 
    async def test_error_handling(self):
        """测试错误处理"""
        spec = ProjectionSpec(
            key_expressions={
                "namespace": "^([a-z_]+)\\.",
                "category": "\\.(gui|item)\\."
            }
        )
        
        adapter = MinecraftProjectionAdapter(spec)
        
        # 测试不匹配的键
        invalid_key = "invalid_key_format"
        uida = await adapter._minecraft_key_to_uida(invalid_key, "测试")
        
        # 应该创建一个通用UIDA
        assert uida.namespace == "unknown"
        assert uida.category == "general"
        assert uida.context["original_key"] == invalid_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])