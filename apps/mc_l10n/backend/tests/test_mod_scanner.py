# tests/test_mod_scanner.py
"""
MOD扫描器单元测试

测试MOD扫描器的核心功能，包括MOD信息提取、语言文件分析和元数据解析
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from packages.adapters.minecraft.scanner import MinecraftModScanner
from packages.core import FileType, LoaderType, ModParsingError
from packages.parsers import ParserFactory


class TestMinecraftModScanner:
    """Minecraft MOD扫描器测试类"""

    @pytest.fixture
    def mod_scanner(self):
        """创建MOD扫描器实例"""
        parser_factory = ParserFactory()
        return MinecraftModScanner(parser_factory)

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
                    "version": "1.2.3",
                    "description": "A test Fabric mod",
                    "authors": ["FabricAuthor", "SecondAuthor"],
                }
                zip_file.writestr("fabric.mod.json", json.dumps(mod_info, indent=2))

                # 添加多个语言文件
                lang_files = {
                    "assets/test_fabric_mod/lang/en_us.json": {
                        "item.test_fabric_mod.test_item": "Test Item",
                        "block.test_fabric_mod.test_block": "Test Block",
                        "itemGroup.test_fabric_mod.items": "Test Items",
                    },
                    "assets/test_fabric_mod/lang/zh_cn.json": {
                        "item.test_fabric_mod.test_item": "测试物品",
                        "block.test_fabric_mod.test_block": "测试方块",
                        "itemGroup.test_fabric_mod.items": "测试物品",
                    },
                    "assets/test_fabric_mod/lang/ja_jp.json": {
                        "item.test_fabric_mod.test_item": "テストアイテム",
                        "block.test_fabric_mod.test_block": "テストブロック",
                    },
                }

                for file_path, content in lang_files.items():
                    zip_file.writestr(
                        file_path, json.dumps(content, indent=2, ensure_ascii=False)
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
                        "version": "2.1.0",
                        "description": "A test Forge mod",
                        "authorList": ["ForgeAuthor"],
                        "mcversion": "1.19.2",
                    }
                ]
                zip_file.writestr("mcmod.info", json.dumps(mod_info, indent=2))

                # 添加.lang格式语言文件
                lang_content_en = """item.test_forge_mod.test_item.name=Test Item
block.test_forge_mod.test_block.name=Test Block
itemGroup.test_forge_mod.items=Test Items"""

                lang_content_zh = """item.test_forge_mod.test_item.name=测试物品
block.test_forge_mod.test_block.name=测试方块
itemGroup.test_forge_mod.items=测试物品"""

                zip_file.writestr(
                    "assets/test_forge_mod/lang/en_us.lang", lang_content_en
                )
                zip_file.writestr(
                    "assets/test_forge_mod/lang/zh_cn.lang", lang_content_zh
                )

            yield mod_path

    @pytest.fixture
    def temp_invalid_mod(self):
        """创建无效的MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "invalid_mod.jar"
            mod_path.write_text("This is not a valid ZIP file")
            yield mod_path

    @pytest.mark.asyncio
    async def test_scan_fabric_mod(self, mod_scanner, temp_fabric_mod):
        """测试扫描Fabric MOD"""
        mod_info = await mod_scanner.scan_mod(temp_fabric_mod)

        assert mod_info.mod_id == "test_fabric_mod"
        assert mod_info.name == "Test Fabric Mod"
        assert mod_info.version == "1.2.3"
        assert mod_info.description == "A test Fabric mod"
        assert "FabricAuthor" in mod_info.authors
        assert "SecondAuthor" in mod_info.authors
        assert mod_info.loader_type == LoaderType.FABRIC

        # 检查语言文件
        assert len(mod_info.language_files) == 3
        assert "en_us" in mod_info.supported_locales
        assert "zh_cn" in mod_info.supported_locales
        assert "ja_jp" in mod_info.supported_locales

        # 检查文件指纹
        assert mod_info.fingerprint is not None
        assert mod_info.fingerprint.hash_blake3 is not None

    @pytest.mark.asyncio
    async def test_scan_forge_mod(self, mod_scanner, temp_forge_mod):
        """测试扫描Forge MOD"""
        mod_info = await mod_scanner.scan_mod(temp_forge_mod)

        assert mod_info.mod_id == "test_forge_mod"
        assert mod_info.name == "Test Forge Mod"
        assert mod_info.version == "2.1.0"
        assert mod_info.description == "A test Forge mod"
        assert "ForgeAuthor" in mod_info.authors
        assert mod_info.minecraft_version == "1.19.2"
        assert mod_info.loader_type == LoaderType.FORGE

        # 检查语言文件
        assert len(mod_info.language_files) == 2
        assert "en_us" in mod_info.supported_locales
        assert "zh_cn" in mod_info.supported_locales

    @pytest.mark.asyncio
    async def test_extract_mod_info_fabric(self, mod_scanner, temp_fabric_mod):
        """测试提取Fabric MOD信息"""
        mod_info_data = await mod_scanner.extract_mod_info(temp_fabric_mod)

        assert mod_info_data["mod_id"] == "test_fabric_mod"
        assert mod_info_data["name"] == "Test Fabric Mod"
        assert mod_info_data["version"] == "1.2.3"
        assert mod_info_data["loader_type"] == "fabric"

    @pytest.mark.asyncio
    async def test_extract_mod_info_forge(self, mod_scanner, temp_forge_mod):
        """测试提取Forge MOD信息"""
        mod_info_data = await mod_scanner.extract_mod_info(temp_forge_mod)

        assert mod_info_data["mod_id"] == "test_forge_mod"
        assert mod_info_data["name"] == "Test Forge Mod"
        assert mod_info_data["version"] == "2.1.0"
        assert mod_info_data["loader_type"] == "forge"
        assert mod_info_data["minecraft_version"] == "1.19.2"

    @pytest.mark.asyncio
    async def test_scan_language_files(self, mod_scanner, temp_fabric_mod):
        """测试扫描语言文件"""
        language_files = await mod_scanner.scan_language_files(temp_fabric_mod)

        assert len(language_files) == 3

        # 检查文件路径格式
        file_names = [f.name for f in language_files]
        assert "en_us.json" in file_names
        assert "zh_cn.json" in file_names
        assert "ja_jp.json" in file_names

    @pytest.mark.asyncio
    async def test_scan_nonexistent_mod(self, mod_scanner):
        """测试扫描不存在的MOD文件"""
        nonexistent_path = Path("/nonexistent/mod.jar")

        with pytest.raises(FileNotFoundError):
            await mod_scanner.scan_mod(nonexistent_path)

    @pytest.mark.asyncio
    async def test_scan_invalid_mod(self, mod_scanner, temp_invalid_mod):
        """测试扫描无效的MOD文件"""
        with pytest.raises(ModParsingError):
            await mod_scanner.scan_mod(temp_invalid_mod)

    @pytest.mark.asyncio
    async def test_scan_oversized_mod(self, mod_scanner):
        """测试扫描超大MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "oversized_mod.jar"

            # 创建一个超过最大文件大小的MOD文件
            original_max_size = mod_scanner.max_file_size
            mod_scanner.max_file_size = 100  # 设置很小的限制

            try:
                # 创建一个大于100字节的文件
                mod_path.write_bytes(b"x" * 200)

                with pytest.raises(ModParsingError) as exc_info:
                    await mod_scanner.scan_mod(mod_path)

                assert "File too large" in str(exc_info.value)

            finally:
                # 恢复原始设置
                mod_scanner.max_file_size = original_max_size

    def test_is_language_file(self, mod_scanner):
        """测试语言文件识别"""
        # 有效的语言文件路径
        valid_paths = [
            "assets/testmod/lang/en_us.json",
            "assets/testmod/lang/zh_cn.lang",
            "data/testmod/lang/ja_jp.json",
            "lang/en_us.json",
        ]

        for path in valid_paths:
            assert mod_scanner._is_language_file(path) is True

        # 无效的语言文件路径
        invalid_paths = [
            "assets/testmod/models/item.json",
            "textures/item/test.png",
            "META-INF/MANIFEST.MF",
            "lang.json",  # 不在正确目录
            "assets/lang/test.txt",  # 错误扩展名
        ]

        for path in invalid_paths:
            assert mod_scanner._is_language_file(path) is False

    def test_is_metadata_file(self, mod_scanner):
        """测试元数据文件识别"""
        # 有效的元数据文件
        valid_files = [
            "fabric.mod.json",
            "quilt.mod.json",
            "mcmod.info",
            "META-INF/mods.toml",
            "meta-inf/neoforge.mods.toml",
        ]

        for file_path in valid_files:
            assert mod_scanner._is_metadata_file(file_path) is True

        # 无效的元数据文件
        invalid_files = [
            "some_file.json",
            "assets/mod.json",
            "mods.toml",  # 不在META-INF目录
            "fabric.json",
        ]

        for file_path in invalid_files:
            assert mod_scanner._is_metadata_file(file_path) is False

    def test_detect_locale_from_path(self, mod_scanner):
        """测试从路径检测语言代码"""
        # 测试标准语言代码
        test_cases = [
            (Path("assets/mod/lang/en_us.json"), "en_us"),
            (Path("assets/mod/lang/zh_cn.json"), "zh_cn"),
            (Path("data/mod/lang/ja_jp.lang"), "ja_jp"),
            (Path("lang/de_de.json"), "de_de"),
            (Path("some/path/fr_fr.lang"), "fr_fr"),
        ]

        for path, expected_locale in test_cases:
            detected = mod_scanner._detect_locale_from_path(path)
            assert detected == expected_locale

        # 测试无法检测的情况
        invalid_paths = [
            Path("assets/mod/lang/invalid.json"),
            Path("assets/mod/lang/en.json"),  # 格式不正确
            Path("some/file.txt"),
        ]

        for path in invalid_paths:
            detected = mod_scanner._detect_locale_from_path(path)
            assert detected is None

    def test_detect_file_type(self, mod_scanner):
        """测试文件类型检测"""
        assert mod_scanner._detect_file_type(Path("test.json")) == FileType.JSON
        assert mod_scanner._detect_file_type(Path("test.lang")) == FileType.LANG
        assert (
            mod_scanner._detect_file_type(Path("test.JSON")) == FileType.JSON
        )  # 大小写不敏感
        assert (
            mod_scanner._detect_file_type(Path("test.txt")) == FileType.JSON
        )  # 默认值

    @pytest.mark.asyncio
    async def test_detect_encoding(self, mod_scanner):
        """测试编码检测"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建UTF-8文件
            utf8_file = Path(temp_dir) / "utf8.txt"
            utf8_file.write_text("Hello 世界", encoding="utf-8")

            detected = await mod_scanner._detect_encoding(utf8_file)
            assert detected == "utf-8"

            # 创建GBK文件
            gbk_file = Path(temp_dir) / "gbk.txt"
            gbk_file.write_text("Hello 世界", encoding="gbk")

            detected = await mod_scanner._detect_encoding(gbk_file)
            # 应该能检测出适合的编码（可能是gbk或utf-8，取决于配置）
            assert detected in ["utf-8", "gbk", "gb2312"]
