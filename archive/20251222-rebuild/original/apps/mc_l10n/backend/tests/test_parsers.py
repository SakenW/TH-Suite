# tests/test_parsers.py
"""
解析器单元测试

测试Minecraft语言文件解析器和MOD文件分析器的功能
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from packages.adapters.minecraft.parsers import MinecraftLangParser, ModFileAnalyzer
from packages.core import FileParsingError, FileType
from packages.parsers import ParserFactory


class TestMinecraftLangParser:
    """Minecraft语言文件解析器测试类"""

    @pytest.fixture
    def lang_parser(self):
        """创建语言文件解析器实例"""
        return MinecraftLangParser()

    @pytest.fixture
    def temp_json_lang_file(self):
        """创建临时JSON语言文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            lang_file = Path(temp_dir) / "en_us.json"

            lang_content = {
                "item.test_mod.sword": "Test Sword",
                "item.test_mod.pickaxe": "Test Pickaxe",
                "block.test_mod.ore": "Test Ore",
                "itemGroup.test_mod.items": "Test Items",
                "gui.test_mod.config.title": "Configuration",
            }

            lang_file.write_text(json.dumps(lang_content, indent=2))
            yield lang_file

    @pytest.fixture
    def temp_lang_file(self):
        """创建临时.lang语言文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            lang_file = Path(temp_dir) / "en_us.lang"

            lang_content = """item.test_mod.sword.name=Test Sword
item.test_mod.pickaxe.name=Test Pickaxe
block.test_mod.ore.name=Test Ore
itemGroup.test_mod.items=Test Items
gui.test_mod.config.title=Configuration
# This is a comment
"""

            lang_file.write_text(lang_content)
            yield lang_file

    @pytest.fixture
    def temp_invalid_json_file(self):
        """创建无效的JSON语言文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            lang_file = Path(temp_dir) / "invalid.json"
            lang_file.write_text('{"key": "value",}')  # 多余的逗号
            yield lang_file

    def test_parse_json_lang_file(self, lang_parser, temp_json_lang_file):
        """测试解析JSON语言文件"""
        result = lang_parser.parse(temp_json_lang_file)

        assert len(result.segments) == 5
        assert result.file_type == FileType.JSON
        assert len(result.errors) == 0

        # 检查具体的翻译段
        segments_dict = {seg.key: seg.value for seg in result.segments}
        assert segments_dict["item.test_mod.sword"] == "Test Sword"
        assert segments_dict["gui.test_mod.config.title"] == "Configuration"

    def test_parse_lang_file(self, lang_parser, temp_lang_file):
        """测试解析.lang语言文件"""
        result = lang_parser.parse(temp_lang_file)

        assert len(result.segments) == 5  # 不包括注释行
        assert result.file_type == FileType.LANG
        assert len(result.errors) == 0

        # 检查具体的翻译段
        segments_dict = {seg.key: seg.value for seg in result.segments}
        assert segments_dict["item.test_mod.sword.name"] == "Test Sword"
        assert segments_dict["gui.test_mod.config.title"] == "Configuration"

    def test_parse_invalid_json_file(self, lang_parser, temp_invalid_json_file):
        """测试解析无效JSON文件"""
        result = lang_parser.parse(temp_invalid_json_file)

        assert len(result.segments) == 0
        assert len(result.errors) > 0
        assert "JSON parsing error" in result.errors[0]

    def test_parse_nonexistent_file(self, lang_parser):
        """测试解析不存在的文件"""
        nonexistent_file = Path("/nonexistent/file.json")

        with pytest.raises(FileParsingError):
            lang_parser.parse(nonexistent_file)

    def test_detect_file_type(self, lang_parser):
        """测试文件类型检测"""
        assert lang_parser._detect_file_type(Path("test.json")) == FileType.JSON
        assert lang_parser._detect_file_type(Path("test.lang")) == FileType.LANG
        assert (
            lang_parser._detect_file_type(Path("TEST.JSON")) == FileType.JSON
        )  # 大小写不敏感
        assert (
            lang_parser._detect_file_type(Path("unknown.txt")) == FileType.JSON
        )  # 默认


class TestModFileAnalyzer:
    """MOD文件分析器测试类"""

    @pytest.fixture
    def mod_analyzer(self):
        """创建MOD文件分析器实例"""
        return ModFileAnalyzer()

    @pytest.fixture
    def temp_fabric_mod(self):
        """创建临时Fabric MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "fabric_mod.jar"

            with zipfile.ZipFile(mod_path, "w") as zip_file:
                # 添加fabric.mod.json
                mod_info = {
                    "id": "test_fabric_mod",
                    "name": "Test Fabric Mod",
                    "version": "1.0.0",
                    "description": "A test Fabric mod",
                }
                zip_file.writestr("fabric.mod.json", json.dumps(mod_info))

                # 添加语言文件
                lang_content = {"test.key": "Test Value"}
                zip_file.writestr(
                    "assets/test_fabric_mod/lang/en_us.json", json.dumps(lang_content)
                )
                zip_file.writestr(
                    "assets/test_fabric_mod/lang/zh_cn.json",
                    json.dumps({"test.key": "测试值"}),
                )

            yield mod_path

    @pytest.fixture
    def temp_forge_mod(self):
        """创建临时Forge MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "forge_mod.jar"

            with zipfile.ZipFile(mod_path, "w") as zip_file:
                # 添加mcmod.info
                mod_info = [
                    {
                        "modid": "test_forge_mod",
                        "name": "Test Forge Mod",
                        "version": "2.0.0",
                    }
                ]
                zip_file.writestr("mcmod.info", json.dumps(mod_info))

                # 添加.lang语言文件
                zip_file.writestr(
                    "assets/test_forge_mod/lang/en_us.lang", "test.key=Test Value"
                )

            yield mod_path

    @pytest.fixture
    def temp_invalid_zip(self):
        """创建无效的ZIP文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "invalid.jar"
            invalid_path.write_text("This is not a valid ZIP file")
            yield invalid_path

    def test_analyze_fabric_mod(self, mod_analyzer, temp_fabric_mod):
        """测试分析Fabric MOD"""
        analysis = mod_analyzer.analyze_mod_archive(temp_fabric_mod)

        assert analysis["errors"] == []
        assert analysis["loader_type"] == "fabric"
        assert analysis["file_size"] > 0

        mod_info = analysis["mod_info"]
        assert mod_info["mod_id"] == "test_fabric_mod"
        assert mod_info["name"] == "Test Fabric Mod"
        assert mod_info["version"] == "1.0.0"

        # 检查语言文件
        assert len(analysis["language_files"]) == 2
        locales = [lf["locale"] for lf in analysis["language_files"]]
        assert "en_us" in locales
        assert "zh_cn" in locales

    def test_analyze_forge_mod(self, mod_analyzer, temp_forge_mod):
        """测试分析Forge MOD"""
        analysis = mod_analyzer.analyze_mod_archive(temp_forge_mod)

        assert analysis["errors"] == []
        assert analysis["loader_type"] == "forge"

        mod_info = analysis["mod_info"]
        assert mod_info["mod_id"] == "test_forge_mod"
        assert mod_info["name"] == "Test Forge Mod"
        assert mod_info["version"] == "2.0.0"

        # 检查语言文件
        assert len(analysis["language_files"]) == 1
        assert analysis["language_files"][0]["locale"] == "en_us"

    def test_analyze_invalid_zip(self, mod_analyzer, temp_invalid_zip):
        """测试分析无效ZIP文件"""
        analysis = mod_analyzer.analyze_mod_archive(temp_invalid_zip)

        assert len(analysis["errors"]) > 0
        assert "Invalid ZIP file" in analysis["errors"][0]
        assert analysis["mod_info"] == {}
        assert analysis["language_files"] == []

    def test_analyze_nonexistent_file(self, mod_analyzer):
        """测试分析不存在的文件"""
        nonexistent_path = Path("/nonexistent/mod.jar")
        analysis = mod_analyzer.analyze_mod_archive(nonexistent_path)

        assert len(analysis["errors"]) > 0
        assert "File not found" in analysis["errors"][0]

    def test_detect_loader_type(self, mod_analyzer):
        """测试检测加载器类型"""
        # 测试Fabric检测
        fabric_files = ["fabric.mod.json"]
        assert mod_analyzer._detect_loader_type(fabric_files) == "fabric"

        # 测试Forge检测
        forge_files = ["mcmod.info", "META-INF/mods.toml"]
        assert mod_analyzer._detect_loader_type(forge_files) == "forge"

        # 测试Quilt检测
        quilt_files = ["quilt.mod.json"]
        assert mod_analyzer._detect_loader_type(quilt_files) == "quilt"

        # 测试NeoForge检测
        neoforge_files = ["META-INF/neoforge.mods.toml"]
        assert mod_analyzer._detect_loader_type(neoforge_files) == "neoforge"

        # 测试未知类型
        unknown_files = ["some_file.txt"]
        assert mod_analyzer._detect_loader_type(unknown_files) == "unknown"

    def test_extract_language_file_info(self, mod_analyzer):
        """测试提取语言文件信息"""
        # 测试JSON文件
        json_info = mod_analyzer._extract_language_file_info(
            "assets/testmod/lang/en_us.json"
        )
        assert json_info["locale"] == "en_us"
        assert json_info["file_type"] == "json"
        assert json_info["relative_path"] == "assets/testmod/lang/en_us.json"

        # 测试.lang文件
        lang_info = mod_analyzer._extract_language_file_info(
            "assets/testmod/lang/zh_cn.lang"
        )
        assert lang_info["locale"] == "zh_cn"
        assert lang_info["file_type"] == "lang"

        # 测试无法识别的文件
        unknown_info = mod_analyzer._extract_language_file_info(
            "assets/testmod/lang/invalid.txt"
        )
        assert unknown_info["locale"] == "unknown"
        assert unknown_info["file_type"] == "json"  # 默认值


class TestParserFactory:
    """解析器工厂测试类"""

    @pytest.fixture
    def parser_factory(self):
        """创建解析器工厂实例"""
        return ParserFactory()

    def test_get_parser_json(self, parser_factory):
        """测试获取JSON解析器"""
        parser = parser_factory.get_parser(Path("test.json"))
        assert isinstance(parser, MinecraftLangParser)

    def test_get_parser_lang(self, parser_factory):
        """测试获取.lang解析器"""
        parser = parser_factory.get_parser(Path("test.lang"))
        assert isinstance(parser, MinecraftLangParser)

    def test_get_parser_unsupported(self, parser_factory):
        """测试获取不支持的文件类型解析器"""
        parser = parser_factory.get_parser(Path("test.txt"))
        assert parser is None

    def test_register_custom_parser(self, parser_factory):
        """测试注册自定义解析器"""

        class CustomParser:
            def parse(self, file_path):
                pass

        custom_parser = CustomParser()
        parser_factory.register_parser("custom", custom_parser)

        # 测试能否获取注册的解析器
        retrieved_parser = parser_factory.get_parser(Path("test.custom"))
        assert retrieved_parser is custom_parser

    def test_get_supported_extensions(self, parser_factory):
        """测试获取支持的文件扩展名"""
        extensions = parser_factory.get_supported_extensions()

        assert ".json" in extensions
        assert ".lang" in extensions
        assert len(extensions) >= 2

    def test_is_supported_file(self, parser_factory):
        """测试文件支持检查"""
        assert parser_factory.is_supported_file(Path("test.json")) is True
        assert parser_factory.is_supported_file(Path("test.lang")) is True
        assert parser_factory.is_supported_file(Path("test.txt")) is False
        assert (
            parser_factory.is_supported_file(Path("test.JSON")) is True
        )  # 大小写不敏感
