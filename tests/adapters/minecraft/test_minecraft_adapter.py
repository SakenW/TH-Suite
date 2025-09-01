# tests/adapters/minecraft/test_minecraft_adapter.py
"""
Minecraft 适配器集成测试

测试 Minecraft 游戏插件的完整功能，包括扫描、解析、存储等操作。
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from packages.adapters.minecraft import (
    MinecraftGamePlugin,
    MinecraftParserFactory,
    MinecraftProjectRepository,
    MinecraftProjectScanner,
)
from packages.core.types import ProjectInfo


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def minecraft_plugin():
    """创建 Minecraft 插件实例"""
    return MinecraftGamePlugin()


class TestMinecraftGamePlugin:
    """测试 Minecraft 游戏插件"""

    def test_plugin_properties(self, minecraft_plugin):
        """测试插件基本属性"""
        assert minecraft_plugin.name == "minecraft"
        assert minecraft_plugin.display_name == "Minecraft"
        assert minecraft_plugin.version == "1.0.0"

        assert ".json" in minecraft_plugin.supported_file_extensions
        assert ".lang" in minecraft_plugin.supported_file_extensions

        assert "modpack" in minecraft_plugin.supported_project_types
        assert "single_mod" in minecraft_plugin.supported_project_types

    def test_plugin_factory_methods(self, minecraft_plugin):
        """测试插件工厂方法"""
        scanner = minecraft_plugin.create_project_scanner()
        assert isinstance(scanner, MinecraftProjectScanner)

        parser_factory = minecraft_plugin.create_parser_factory()
        assert isinstance(parser_factory, MinecraftParserFactory)

        repository = minecraft_plugin.create_project_repository()
        assert isinstance(repository, MinecraftProjectRepository)

    def test_default_config(self, minecraft_plugin):
        """测试默认配置"""
        config = minecraft_plugin.get_default_config()

        assert "scan" in config
        assert "loaders" in config
        assert "project_detection" in config
        assert "export" in config

        assert config["scan"]["max_file_size"] > 0
        assert "fabric" in config["loaders"]
        assert "forge" in config["loaders"]

    def test_project_validation(self, minecraft_plugin, temp_dir):
        """测试项目结构验证"""
        # 测试不存在的路径
        result = minecraft_plugin.validate_project_structure(temp_dir / "nonexistent")
        assert not result["is_valid"]
        assert "does not exist" in result["issues"][0]

        # 创建一个模拟整合包
        modpack_dir = temp_dir / "test_modpack"
        modpack_dir.mkdir()
        (modpack_dir / "manifest.json").write_text('{"name": "Test Modpack"}')

        result = minecraft_plugin.validate_project_structure(modpack_dir)
        assert result["is_valid"]
        assert result["project_type"] == "modpack"


class TestMinecraftProjectScanner:
    """测试 Minecraft 项目扫描器"""

    @pytest.fixture
    def scanner(self):
        return MinecraftProjectScanner()

    def create_mock_modpack(self, base_dir: Path) -> Path:
        """创建模拟整合包"""
        modpack_dir = base_dir / "test_modpack"
        modpack_dir.mkdir()

        # 创建 manifest.json
        manifest = {
            "minecraft": {"version": "1.20.1"},
            "modLoaders": [{"id": "fabric-0.14.21", "primary": True}],
            "name": "Test Modpack",
            "version": "1.0.0",
        }
        (modpack_dir / "manifest.json").write_text(json.dumps(manifest))

        # 创建 mods 目录
        mods_dir = modpack_dir / "mods"
        mods_dir.mkdir()

        # 创建模拟 Fabric MOD
        self.create_mock_fabric_mod(mods_dir / "test_mod.jar")

        # 创建配置文件夹（带语言文件）
        config_dir = modpack_dir / "config"
        config_dir.mkdir()
        lang_dir = config_dir / "lang"
        lang_dir.mkdir()
        (lang_dir / "en_us.json").write_text('{"test.key": "Test Value"}')

        return modpack_dir

    def create_mock_fabric_mod(self, mod_path: Path) -> None:
        """创建模拟 Fabric MOD 文件"""
        with zipfile.ZipFile(mod_path, "w") as zf:
            # fabric.mod.json
            fabric_json = {
                "schemaVersion": 1,
                "id": "test_mod",
                "version": "1.0.0",
                "name": "Test Mod",
                "description": "A test mod",
                "authors": ["Test Author"],
                "depends": {"fabricloader": ">=0.14.0", "minecraft": ">=1.20.0"},
            }
            zf.writestr("fabric.mod.json", json.dumps(fabric_json))

            # 语言文件
            zf.writestr(
                "assets/test_mod/lang/en_us.json",
                json.dumps({"item.test_mod.test_item": "Test Item"}),
            )
            zf.writestr(
                "assets/test_mod/lang/zh_cn.json",
                json.dumps({"item.test_mod.test_item": "测试物品"}),
            )

    def create_mock_single_mod(self, base_dir: Path) -> Path:
        """创建单个 MOD 文件"""
        mod_path = base_dir / "single_mod.jar"
        self.create_mock_fabric_mod(mod_path)
        return mod_path

    def create_mock_resource_pack(self, base_dir: Path) -> Path:
        """创建模拟资源包"""
        pack_dir = base_dir / "test_resource_pack"
        pack_dir.mkdir()

        # pack.mcmeta
        pack_meta = {"pack": {"pack_format": 15, "description": "Test Resource Pack"}}
        (pack_dir / "pack.mcmeta").write_text(json.dumps(pack_meta))

        # assets 目录结构
        assets_dir = pack_dir / "assets" / "minecraft" / "lang"
        assets_dir.mkdir(parents=True)
        (assets_dir / "en_us.json").write_text('{"block.stone": "Stone"}')
        (assets_dir / "zh_cn.json").write_text('{"block.stone": "石头"}')

        return pack_dir

    @pytest.mark.asyncio
    async def test_scan_modpack(self, scanner, temp_dir):
        """测试扫描整合包"""
        modpack_dir = self.create_mock_modpack(temp_dir)

        progress_messages = []

        def progress_callback(message: str, percent: float):
            progress_messages.append((message, percent))

        result = await scanner.scan_project(modpack_dir, progress_callback)

        # 验证扫描结果
        assert result.success
        assert result.project_info.name == "test_modpack"
        assert result.project_info.project_type == "modpack"
        assert result.project_info.game_type == "minecraft"

        # 验证 MOD 信息
        assert len(result.mods_info) == 1
        mod = result.mods_info[0]
        assert mod.name == "Test Mod"
        assert mod.mod_id == "test_mod"
        assert mod.loader_type == "fabric"

        # 验证语言文件
        assert len(result.language_files) >= 2  # MOD中的语言文件 + 整合包级别的语言文件

        # 验证进度回调
        assert len(progress_messages) > 0
        assert progress_messages[-1][1] == 100.0  # 最后一个进度应该是100%

    @pytest.mark.asyncio
    async def test_scan_single_mod(self, scanner, temp_dir):
        """测试扫描单个 MOD"""
        mod_path = self.create_mock_single_mod(temp_dir)

        result = await scanner.scan_project(mod_path)

        assert result.success
        assert result.project_info.project_type == "single_mod"
        assert len(result.mods_info) == 1

        mod = result.mods_info[0]
        assert mod.name == "Test Mod"
        assert "zh_cn" in mod.supported_languages
        assert "en_us" in mod.supported_languages

    @pytest.mark.asyncio
    async def test_scan_resource_pack(self, scanner, temp_dir):
        """测试扫描资源包"""
        pack_dir = self.create_mock_resource_pack(temp_dir)

        result = await scanner.scan_project(pack_dir)

        assert result.success
        assert result.project_info.project_type == "resource_pack"
        assert len(result.mods_info) == 0  # 资源包没有 MOD
        assert len(result.language_files) >= 2  # en_us.json 和 zh_cn.json

    @pytest.mark.asyncio
    async def test_scan_unsupported_project(self, scanner, temp_dir):
        """测试扫描不支持的项目"""
        # 创建空目录
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with pytest.raises(Exception):  # 应该抛出 UnsupportedProjectTypeError
            await scanner.scan_project(empty_dir)


class TestMinecraftParserFactory:
    """测试 Minecraft 解析器工厂"""

    @pytest.fixture
    def parser_factory(self):
        return MinecraftParserFactory()

    def test_get_parser(self, parser_factory, temp_dir):
        """测试获取解析器"""
        # JSON 文件
        json_file = temp_dir / "test.json"
        parser = parser_factory.get_parser(json_file)
        assert parser is not None
        assert parser.can_parse(json_file)

        # .lang 文件
        lang_file = temp_dir / "test.lang"
        parser = parser_factory.get_parser(lang_file)
        assert parser is not None
        assert parser.can_parse(lang_file)

        # 不支持的文件
        unknown_file = temp_dir / "test.unknown"
        parser = parser_factory.get_parser(unknown_file)
        assert parser is None

    def test_detect_format(self, parser_factory, temp_dir):
        """测试格式检测"""
        json_file = temp_dir / "test.json"
        assert parser_factory.detect_format(json_file).value == "json"

        lang_file = temp_dir / "test.lang"
        assert parser_factory.detect_format(lang_file).value == "lang"

        unknown_file = temp_dir / "test.txt"
        assert parser_factory.detect_format(unknown_file).value == "unknown"

    @pytest.mark.asyncio
    async def test_parse_json_file(self, parser_factory, temp_dir):
        """测试解析 JSON 文件"""
        # 创建测试 JSON 文件
        json_file = temp_dir / "en_us.json"
        test_data = {
            "item.test.sword": "Test Sword",
            "block.test.ore": "Test Ore",
            "nested": {"key": "Nested Value"},
        }
        json_file.write_text(json.dumps(test_data), encoding="utf-8")

        # 解析文件
        result = await parser_factory.parse_file(json_file)

        assert result.success
        assert result.file_format == "json"
        assert result.total_keys == 3  # 包含嵌套键

        # 查找特定条目
        entries_dict = {entry.key: entry.value for entry in result.entries}
        assert entries_dict["item.test.sword"] == "Test Sword"
        assert entries_dict["nested.key"] == "Nested Value"

    @pytest.mark.asyncio
    async def test_parse_lang_file(self, parser_factory, temp_dir):
        """测试解析 .lang 文件"""
        # 创建测试 .lang 文件
        lang_file = temp_dir / "en_us.lang"
        lang_content = """# Test language file
item.test.sword=Test Sword
item.test.shield=Test Shield

# Block translations
block.test.ore=Test Ore
"""
        lang_file.write_text(lang_content, encoding="utf-8")

        # 解析文件
        result = await parser_factory.parse_file(lang_file)

        assert result.success
        assert result.file_format == "lang"
        assert result.total_keys == 3

        # 检查元数据
        assert result.metadata["comments_count"] == 2
        assert result.metadata["empty_lines_count"] == 1

    def test_supported_formats(self, parser_factory):
        """测试支持的格式"""
        formats = parser_factory.get_supported_formats()
        assert "json" in formats
        assert "lang" in formats
        assert "properties" in formats

        extensions = parser_factory.get_format_extensions()
        assert ".json" in extensions["json"]
        assert ".lang" in extensions["lang"]


class TestMinecraftProjectRepository:
    """测试 Minecraft 项目仓储"""

    @pytest.fixture
    async def repository(self, temp_dir):
        """创建测试仓储"""
        db_path = temp_dir / "test.db"
        repo = MinecraftProjectRepository(db_path)
        await repo.initialize()
        yield repo
        await repo.close()

    @pytest.fixture
    def sample_project_info(self):
        """创建样例项目信息"""
        return ProjectInfo(
            name="Test Project",
            path="/test/project",
            project_type="modpack",
            game_type="minecraft",
            loader_type="fabric",
            minecraft_versions=["1.20.1"],
            total_mods=1,
            total_language_files=2,
            supported_languages=["en_us", "zh_cn"],
            metadata={"test": "data"},
        )

    @pytest.mark.asyncio
    async def test_add_and_get_project(self, repository, sample_project_info):
        """测试添加和获取项目"""
        # 添加项目
        project_id = await repository.add_project(sample_project_info)
        assert project_id > 0

        # 根据 ID 获取项目
        retrieved_project = await repository.get_project_by_id(project_id)
        assert retrieved_project is not None
        assert retrieved_project.name == sample_project_info.name
        assert retrieved_project.path == sample_project_info.path

        # 根据路径获取项目
        retrieved_project = await repository.get_project_by_path(
            sample_project_info.path
        )
        assert retrieved_project is not None
        assert retrieved_project.name == sample_project_info.name

    @pytest.mark.asyncio
    async def test_update_project(self, repository, sample_project_info):
        """测试更新项目"""
        # 添加项目
        project_id = await repository.add_project(sample_project_info)

        # 更新项目信息
        sample_project_info.name = "Updated Project"
        sample_project_info.total_mods = 5
        await repository.update_project(project_id, sample_project_info)

        # 验证更新
        retrieved_project = await repository.get_project_by_id(project_id)
        assert retrieved_project.name == "Updated Project"
        assert retrieved_project.total_mods == 5

    @pytest.mark.asyncio
    async def test_list_projects(self, repository, sample_project_info):
        """测试列出项目"""
        # 添加多个项目
        await repository.add_project(sample_project_info)

        sample_project_info2 = sample_project_info
        sample_project_info2.path = "/test/project2"
        sample_project_info2.project_type = "single_mod"
        await repository.add_project(sample_project_info2)

        # 列出所有项目
        all_projects = await repository.list_projects()
        assert len(all_projects) == 2

        # 按类型筛选
        modpack_projects = await repository.list_projects(project_type="modpack")
        assert len(modpack_projects) == 1
        assert modpack_projects[0].project_type == "modpack"

    @pytest.mark.asyncio
    async def test_delete_project(self, repository, sample_project_info):
        """测试删除项目"""
        # 添加项目
        project_id = await repository.add_project(sample_project_info)

        # 确认项目存在
        project = await repository.get_project_by_id(project_id)
        assert project is not None

        # 删除项目
        await repository.delete_project(project_id)

        # 确认项目已被软删除
        project = await repository.get_project_by_id(project_id)
        assert project is None


class TestMinecraftIntegration:
    """Minecraft 适配器集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_dir):
        """测试完整工作流程"""
        # 1. 创建插件实例
        plugin = MinecraftGamePlugin()

        # 2. 创建模拟项目
        modpack_dir = temp_dir / "integration_test_modpack"
        modpack_dir.mkdir()

        # 创建 manifest.json
        manifest = {
            "minecraft": {"version": "1.20.1"},
            "modLoaders": [{"id": "fabric-0.14.21"}],
            "name": "Integration Test Modpack",
        }
        (modpack_dir / "manifest.json").write_text(json.dumps(manifest))

        # 创建 mods 目录和模拟 MOD
        mods_dir = modpack_dir / "mods"
        mods_dir.mkdir()

        with zipfile.ZipFile(mods_dir / "test_mod.jar", "w") as zf:
            fabric_json = {
                "id": "integration_test_mod",
                "name": "Integration Test Mod",
                "version": "1.0.0",
            }
            zf.writestr("fabric.mod.json", json.dumps(fabric_json))
            zf.writestr(
                "assets/test/lang/en_us.json", json.dumps({"test.item": "Test Item"})
            )

        # 3. 扫描项目
        scanner = plugin.create_project_scanner()
        scan_result = await scanner.scan_project(modpack_dir)

        assert scan_result.success
        assert len(scan_result.mods_info) == 1

        # 4. 解析语言文件
        parser_factory = plugin.create_parser_factory()

        for lang_file in scan_result.language_files:
            if not lang_file.is_archived:  # 跳过压缩包内的文件
                full_path = Path(lang_file.full_path)
                if full_path.exists():
                    parse_result = await parser_factory.parse_file(full_path)
                    assert parse_result.success

        # 5. 保存到仓储
        repository = plugin.create_project_repository()
        await repository.initialize()

        try:
            # 添加项目
            project_id = await repository.add_project(scan_result.project_info)

            # 保存完整扫描结果
            await repository.save_scan_result(project_id, scan_result)

            # 验证数据保存
            saved_project = await repository.get_project_by_id(project_id)
            assert saved_project is not None
            assert saved_project.name == "integration_test_modpack"

            mods = await repository.get_mods_by_project(project_id)
            assert len(mods) == 1
            assert mods[0].name == "Integration Test Mod"

            lang_files = await repository.get_language_files_by_project(project_id)
            assert len(lang_files) >= 1

        finally:
            await repository.close()


if __name__ == "__main__":
    # 运行测试的简单方法
    pytest.main([__file__, "-v"])
