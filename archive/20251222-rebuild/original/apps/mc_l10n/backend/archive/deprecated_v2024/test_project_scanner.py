# tests/test_project_scanner.py
"""
项目扫描器单元测试

测试项目扫描器的核心功能，包括项目类型检测、加载器类型检测和扫描结果
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from packages.adapters.minecraft.scanner import (
    MinecraftModScanner as MinecraftProjectScanner,
)
from packages.core import LoaderType, ProjectType
from packages.core.data.models import ScanProgress


class TestMinecraftProjectScanner:
    """Minecraft项目扫描器测试类"""

    @pytest.fixture
    def project_scanner(self):
        """创建项目扫描器实例"""
        return MinecraftProjectScanner()

    @pytest.fixture
    def temp_modpack_dir(self):
        """创建临时整合包目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            modpack_path = Path(temp_dir) / "test_modpack"
            modpack_path.mkdir()

            # 创建mods目录
            mods_dir = modpack_path / "mods"
            mods_dir.mkdir()

            # 创建测试MOD文件
            for i in range(3):
                mod_file = mods_dir / f"test_mod_{i}.jar"
                self._create_test_mod_file(mod_file, f"test_mod_{i}")

            # 创建manifest.json（CurseForge格式）
            manifest = {
                "minecraft": {"version": "1.19.2"},
                "manifestType": "minecraftModpack",
                "manifestVersion": 1,
                "name": "Test Modpack",
                "version": "1.0.0",
            }
            manifest_file = modpack_path / "manifest.json"
            manifest_file.write_text(json.dumps(manifest))

            yield modpack_path

    @pytest.fixture
    def temp_single_mod(self):
        """创建临时单MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "single_mod.jar"
            self._create_test_mod_file(mod_path, "single_mod")
            yield mod_path

    def _create_test_mod_file(self, mod_path: Path, mod_id: str):
        """创建测试MOD文件"""
        with zipfile.ZipFile(mod_path, "w") as zip_file:
            # 添加Fabric元数据
            mod_info = {
                "id": mod_id,
                "name": f"Test {mod_id}",
                "version": "1.0.0",
                "description": f"Test mod {mod_id}",
                "authors": ["TestAuthor"],
            }
            zip_file.writestr("fabric.mod.json", json.dumps(mod_info))

            # 添加语言文件
            lang_content = {
                f"item.{mod_id}.test_item": "Test Item",
                f"block.{mod_id}.test_block": "Test Block",
            }
            zip_file.writestr(
                f"assets/{mod_id}/lang/en_us.json", json.dumps(lang_content)
            )

    @pytest.mark.asyncio
    async def test_detect_project_type_modpack(self, project_scanner, temp_modpack_dir):
        """测试检测整合包项目类型"""
        project_type = await project_scanner.detect_project_type(temp_modpack_dir)
        assert project_type == ProjectType.MODPACK

    @pytest.mark.asyncio
    async def test_detect_project_type_single_mod(
        self, project_scanner, temp_single_mod
    ):
        """测试检测单MOD项目类型"""
        project_type = await project_scanner.detect_project_type(temp_single_mod)
        assert project_type == ProjectType.SINGLE_MOD

    @pytest.mark.asyncio
    async def test_detect_project_type_none(self, project_scanner):
        """测试检测不支持的项目类型"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            project_type = await project_scanner.detect_project_type(empty_dir)
            assert project_type is None

    @pytest.mark.asyncio
    async def test_detect_loader_type_fabric(self, project_scanner, temp_single_mod):
        """测试检测Fabric加载器类型"""
        loader_type = await project_scanner.detect_loader_type(temp_single_mod)
        assert loader_type == LoaderType.FABRIC

    @pytest.mark.asyncio
    async def test_scan_modpack_project(self, project_scanner, temp_modpack_dir):
        """测试扫描整合包项目"""
        result = await project_scanner.scan_project(temp_modpack_dir)

        assert result.success is True
        assert result.project_info is not None
        assert result.project_info.project_type == ProjectType.MODPACK
        assert result.project_info.name == "test_modpack"
        assert result.project_info.total_mods == 3
        assert result.scan_time is not None
        assert result.scan_time > 0

    @pytest.mark.asyncio
    async def test_scan_single_mod_project(self, project_scanner, temp_single_mod):
        """测试扫描单MOD项目"""
        result = await project_scanner.scan_project(temp_single_mod)

        assert result.success is True
        assert result.project_info is not None
        assert result.project_info.project_type == ProjectType.SINGLE_MOD
        assert result.project_info.name == "single_mod"
        assert result.project_info.total_mods == 1

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self, project_scanner):
        """测试扫描不存在的路径"""
        nonexistent_path = Path("/nonexistent/path")
        result = await project_scanner.scan_project(nonexistent_path)

        assert result.success is False
        assert len(result.errors) > 0
        assert "does not exist" in result.errors[0]

    @pytest.mark.asyncio
    async def test_scan_file_as_directory(self, project_scanner, temp_single_mod):
        """测试将文件作为目录扫描"""
        # 创建一个普通文件，不是MOD文件
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "not_a_mod.txt"
            file_path.write_text("This is not a MOD file")

            result = await project_scanner.scan_project(file_path)
            assert result.success is False
            assert "not a directory" in result.errors[0]

    @pytest.mark.asyncio
    async def test_progress_callback(self, project_scanner, temp_modpack_dir):
        """测试进度回调功能"""
        progress_updates = []

        def progress_callback(progress: ScanProgress):
            progress_updates.append(progress)

        # 设置进度回调
        project_scanner.set_progress_callback(progress_callback)

        # 执行扫描
        result = await project_scanner.scan_project(temp_modpack_dir)

        assert result.success is True
        # 验证收到了进度更新
        assert len(progress_updates) > 0

        # 检查进度更新内容
        first_progress = progress_updates[0]
        assert hasattr(first_progress, "current_step")
        assert first_progress.current_step is not None

    @pytest.mark.asyncio
    async def test_parallel_scanning(self, project_scanner, temp_modpack_dir):
        """测试并行扫描功能"""
        # 启用并行扫描
        project_scanner.parallel_scan = True
        project_scanner.max_workers = 2

        result = await project_scanner.scan_project(temp_modpack_dir)

        assert result.success is True
        assert result.project_info.total_mods == 3

        # 验证所有MOD都被正确扫描
        for mod in result.project_info.mods:
            assert mod is not None
            assert mod.mod_id.startswith("test_mod_")

    @pytest.mark.asyncio
    async def test_sequential_scanning(self, project_scanner, temp_modpack_dir):
        """测试顺序扫描功能"""
        # 禁用并行扫描
        project_scanner.parallel_scan = False

        result = await project_scanner.scan_project(temp_modpack_dir)

        assert result.success is True
        assert result.project_info.total_mods == 3

        # 验证所有MOD都被正确扫描
        for mod in result.project_info.mods:
            assert mod is not None
            assert mod.mod_id.startswith("test_mod_")

    @pytest.mark.asyncio
    async def test_should_ignore_file(self, project_scanner):
        """测试文件忽略逻辑"""
        # 测试应该被忽略的文件
        ignore_patterns = [".git", "__pycache__", ".DS_Store"]
        project_scanner.ignore_patterns = set(ignore_patterns)

        for pattern in ignore_patterns:
            test_path = Path(f"/test/{pattern}/somefile.jar")
            assert project_scanner._should_ignore_file(test_path) is True

        # 测试不应该被忽略的文件
        normal_path = Path("/test/mods/normal_mod.jar")
        assert project_scanner._should_ignore_file(normal_path) is False
