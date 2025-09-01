# tests/test_scan_service.py
"""
扫描服务单元测试

测试扫描服务的核心功能，包括项目扫描、MOD扫描和进度跟踪
"""

import json
import tempfile
import zipfile
from pathlib import Path
from uuid import UUID

import pytest
from src.mc_l10n.application.services.scan_service import ScanService
from src.mc_l10n.domain.scan_models import ScanProgress
from src.mc_l10n.infrastructure.parsers import ParserFactory
from src.mc_l10n.infrastructure.scanners import (
    MinecraftModScanner,
    MinecraftProjectScanner,
)

from packages.core import LoaderType, ProjectType, ScanError


class TestScanService:
    """扫描服务测试类"""

    @pytest.fixture
    def scan_service(self):
        """创建扫描服务实例"""
        project_scanner = MinecraftProjectScanner()
        mod_scanner = MinecraftModScanner()
        parser_factory = ParserFactory()

        return ScanService(
            project_scanner=project_scanner,
            mod_scanner=mod_scanner,
            parser_factory=parser_factory,
        )

    @pytest.fixture
    def temp_modpack_dir(self):
        """创建临时整合包目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            modpack_path = Path(temp_dir) / "test_modpack"
            modpack_path.mkdir()

            # 创建mods目录
            mods_dir = modpack_path / "mods"
            mods_dir.mkdir()

            # 创建一个简单的MOD文件
            mod_file = mods_dir / "test_mod.jar"
            self._create_test_mod_file(mod_file)

            # 创建instance.cfg（MultiMC格式）
            instance_cfg = modpack_path / "instance.cfg"
            instance_cfg.write_text("""
[General]
name=Test Modpack
iconKey=default
""")

            yield modpack_path

    @pytest.fixture
    def temp_mod_file(self):
        """创建临时MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "test_mod.jar"
            self._create_test_mod_file(mod_path)
            yield mod_path

    def _create_test_mod_file(self, mod_path: Path):
        """创建测试MOD文件"""
        with zipfile.ZipFile(mod_path, "w") as zip_file:
            # 添加fabric.mod.json
            mod_info = {
                "id": "test_mod",
                "name": "Test Mod",
                "version": "1.0.0",
                "description": "A test mod",
                "authors": ["TestAuthor"],
            }
            zip_file.writestr("fabric.mod.json", json.dumps(mod_info))

            # 添加语言文件
            lang_content = {
                "item.test_mod.test_item": "Test Item",
                "block.test_mod.test_block": "Test Block",
            }
            zip_file.writestr(
                "assets/test_mod/lang/en_us.json", json.dumps(lang_content)
            )

            # 添加中文语言文件
            lang_content_zh = {
                "item.test_mod.test_item": "测试物品",
                "block.test_mod.test_block": "测试方块",
            }
            zip_file.writestr(
                "assets/test_mod/lang/zh_cn.json", json.dumps(lang_content_zh)
            )

    @pytest.mark.asyncio
    async def test_start_project_scan(self, scan_service, temp_modpack_dir):
        """测试启动项目扫描"""
        # 启动扫描
        task_id = await scan_service.start_project_scan(temp_modpack_dir)

        # 验证返回的task_id格式
        assert isinstance(task_id, UUID)

        # 检查任务状态
        progress = await scan_service.get_scan_progress(task_id)
        assert progress is not None
        assert progress["task_id"] == str(task_id)
        assert "status" in progress

    @pytest.mark.asyncio
    async def test_quick_scan_project_modpack(self, scan_service, temp_modpack_dir):
        """测试快速扫描整合包"""
        result = await scan_service.quick_scan_project(temp_modpack_dir)

        assert result.success is True
        assert result.project_info is not None
        assert result.project_info.project_type == ProjectType.MODPACK
        assert result.project_info.name == "test_modpack"
        assert result.project_info.total_mods > 0

    @pytest.mark.asyncio
    async def test_quick_scan_project_single_mod(self, scan_service, temp_mod_file):
        """测试快速扫描单个MOD"""
        result = await scan_service.quick_scan_project(temp_mod_file)

        assert result.success is True
        assert result.project_info is not None
        assert result.project_info.project_type == ProjectType.SINGLE_MOD
        assert result.project_info.name == "test_mod"

    @pytest.mark.asyncio
    async def test_scan_single_mod(self, scan_service, temp_mod_file):
        """测试扫描单个MOD文件"""
        mod_info = await scan_service.scan_single_mod(temp_mod_file)

        assert mod_info.mod_id == "test_mod"
        assert mod_info.name == "Test Mod"
        assert mod_info.version == "1.0.0"
        assert mod_info.description == "A test mod"
        assert "TestAuthor" in mod_info.authors
        assert mod_info.loader_type == LoaderType.FABRIC
        assert len(mod_info.language_files) > 0
        assert "en_us" in mod_info.supported_locales
        assert "zh_cn" in mod_info.supported_locales

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self, scan_service):
        """测试扫描不存在的路径"""
        nonexistent_path = Path("/nonexistent/path")

        with pytest.raises(ScanError):
            await scan_service.start_project_scan(nonexistent_path)

    @pytest.mark.asyncio
    async def test_quick_scan_nonexistent_path(self, scan_service):
        """测试快速扫描不存在的路径"""
        nonexistent_path = Path("/nonexistent/path")

        result = await scan_service.quick_scan_project(nonexistent_path)
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_progress_callback(self, scan_service, temp_modpack_dir):
        """测试进度回调"""
        progress_updates = []

        def progress_callback(progress: ScanProgress):
            progress_updates.append(progress)

        # 启动带回调的扫描
        task_id = await scan_service.start_project_scan(
            temp_modpack_dir, progress_callback
        )

        # 等待扫描完成
        import asyncio

        await asyncio.sleep(1)  # 给扫描一些时间

        # 验证收到了进度更新
        assert len(progress_updates) > 0

        # 检查最终状态
        final_progress = await scan_service.get_scan_progress(task_id)
        assert final_progress is not None

    @pytest.mark.asyncio
    async def test_project_caching(self, scan_service, temp_mod_file):
        """测试项目缓存"""
        # 第一次扫描
        result1 = await scan_service.quick_scan_project(temp_mod_file)
        assert result1.success is True

        # 缓存项目信息
        if result1.project_info:
            await scan_service.cache_project(result1.project_info)

        # 验证缓存中有项目
        assert len(scan_service._project_cache) > 0

        # 第二次扫描相同项目应该更快（因为有缓存）
        result2 = await scan_service.quick_scan_project(temp_mod_file)
        assert result2.success is True
        assert result2.project_info.fingerprint == result1.project_info.fingerprint
