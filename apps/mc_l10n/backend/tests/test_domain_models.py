# tests/test_domain_models.py
"""
领域模型单元测试

测试扫描相关的领域模型和业务规则
"""

import tempfile
from pathlib import Path

from src.mc_l10n.domain.scan_models import (
    FileFingerprint,
    LanguageFileInfo,
    MinecraftModScanRule,
    ModInfo,
    ModpackScanRule,
    ProjectInfo,
    ScanProgress,
    ScanResult,
)

from packages.core import FileType, LoaderType, ProjectType


class TestProjectInfo:
    """项目信息模型测试类"""

    def test_create_project_info(self):
        """测试创建项目信息"""
        project_info = ProjectInfo(
            name="Test Project",
            path=Path("/test/project"),
            project_type=ProjectType.MODPACK,
            loader_type=LoaderType.FABRIC,
        )

        assert project_info.name == "Test Project"
        assert project_info.path == Path("/test/project")
        assert project_info.project_type == ProjectType.MODPACK
        assert project_info.loader_type == LoaderType.FABRIC
        assert project_info.total_mods == 0
        assert project_info.estimated_segments == 0
        assert len(project_info.supported_locales) == 0

    def test_add_mod(self):
        """测试添加MOD"""
        project_info = ProjectInfo(
            name="Test Project", path=Path("/test"), project_type=ProjectType.MODPACK
        )

        mod_info = ModInfo(
            mod_id="test_mod",
            name="Test Mod",
            file_path=Path("/test/mod.jar"),
            file_size=1024,
        )
        mod_info.supported_locales.update(["en_us", "zh_cn"])

        project_info.add_mod(mod_info)

        assert project_info.total_mods == 1
        assert len(project_info.mods) == 1
        assert project_info.mods[0] == mod_info
        assert "en_us" in project_info.supported_locales
        assert "zh_cn" in project_info.supported_locales

    def test_generate_fingerprint(self):
        """测试生成项目指纹"""
        project_info = ProjectInfo(
            name="Test Project",
            path=Path("/test/project"),
            project_type=ProjectType.MODPACK,
        )

        # 添加一些MOD
        for i in range(3):
            mod_info = ModInfo(
                mod_id=f"mod_{i}",
                name=f"Mod {i}",
                file_path=Path(f"/test/mod_{i}.jar"),
                file_size=1024,
            )
            project_info.add_mod(mod_info)

        # 生成指纹
        project_info.generate_fingerprint()

        assert project_info.fingerprint is not None
        assert len(project_info.fingerprint) > 0

        # 相同内容应该生成相同指纹
        original_fingerprint = project_info.fingerprint
        project_info.generate_fingerprint()
        assert project_info.fingerprint == original_fingerprint


class TestModInfo:
    """MOD信息模型测试类"""

    def test_create_mod_info(self):
        """测试创建MOD信息"""
        mod_info = ModInfo(
            mod_id="test_mod",
            name="Test Mod",
            file_path=Path("/test/mod.jar"),
            file_size=2048,
        )

        assert mod_info.mod_id == "test_mod"
        assert mod_info.name == "Test Mod"
        assert mod_info.file_path == Path("/test/mod.jar")
        assert mod_info.file_size == 2048
        assert len(mod_info.language_files) == 0
        assert len(mod_info.supported_locales) == 0
        assert mod_info.estimated_segments == 0

    def test_add_language_file(self):
        """测试添加语言文件"""
        mod_info = ModInfo(
            mod_id="test_mod",
            name="Test Mod",
            file_path=Path("/test/mod.jar"),
            file_size=1024,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            lang_file_path = Path(temp_dir) / "en_us.json"
            lang_file_path.write_text('{"key": "value"}')

            lang_file_info = LanguageFileInfo(
                path=lang_file_path,
                relative_path=Path("assets/mod/lang/en_us.json"),
                file_type=FileType.JSON,
                locale="en_us",
                fingerprint=FileFingerprint.create_from_file(lang_file_path),
            )
            lang_file_info.key_count = 1

            mod_info.add_language_file(lang_file_info)

            assert len(mod_info.language_files) == 1
            assert "en_us" in mod_info.supported_locales
            assert mod_info.estimated_segments == 1


class TestLanguageFileInfo:
    """语言文件信息模型测试类"""

    def test_create_language_file_info(self):
        """测试创建语言文件信息"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            file_path.write_text('{"test": "value"}')

            fingerprint = FileFingerprint.create_from_file(file_path)

            lang_file_info = LanguageFileInfo(
                path=file_path,
                relative_path=Path("assets/mod/lang/en_us.json"),
                file_type=FileType.JSON,
                locale="en_us",
                fingerprint=fingerprint,
            )

            assert lang_file_info.path == file_path
            assert lang_file_info.relative_path == Path("assets/mod/lang/en_us.json")
            assert lang_file_info.file_type == FileType.JSON
            assert lang_file_info.locale == "en_us"
            assert lang_file_info.fingerprint == fingerprint
            assert lang_file_info.key_count == 0
            assert len(lang_file_info.parse_errors) == 0


class TestFileFingerprint:
    """文件指纹模型测试类"""

    def test_create_from_file(self):
        """测试从文件创建指纹"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            file_path.write_text("Hello World!")

            fingerprint = FileFingerprint.create_from_file(file_path)

            assert fingerprint.file_path == file_path
            assert fingerprint.file_size == len("Hello World!")
            assert fingerprint.hash_sha256 is not None
            assert len(fingerprint.hash_sha256) == 64  # SHA256 hex string
            assert fingerprint.last_modified is not None

    def test_fingerprint_consistency(self):
        """测试指纹一致性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            file_path.write_text("Consistent content")

            fingerprint1 = FileFingerprint.create_from_file(file_path)
            fingerprint2 = FileFingerprint.create_from_file(file_path)

            # 相同文件应该生成相同指纹
            assert fingerprint1.hash_sha256 == fingerprint2.hash_sha256
            assert fingerprint1.file_size == fingerprint2.file_size

    def test_fingerprint_difference(self):
        """测试不同文件的指纹差异"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "test1.txt"
            file2 = Path(temp_dir) / "test2.txt"

            file1.write_text("Content A")
            file2.write_text("Content B")

            fingerprint1 = FileFingerprint.create_from_file(file1)
            fingerprint2 = FileFingerprint.create_from_file(file2)

            # 不同文件应该有不同指纹
            assert fingerprint1.hash_sha256 != fingerprint2.hash_sha256


class TestScanProgress:
    """扫描进度模型测试类"""

    def test_create_scan_progress(self):
        """测试创建扫描进度"""
        progress = ScanProgress(current_step="初始化")

        assert progress.current_step == "初始化"
        assert progress.current_file is None
        assert progress.total_files == 0
        assert progress.processed_files == 0
        assert progress.progress_percentage == 0.0
        assert len(progress.errors) == 0

    def test_calculate_progress_percentage(self):
        """测试计算进度百分比"""
        progress = ScanProgress()
        progress.total_files = 10
        progress.processed_files = 3

        assert progress.progress_percentage == 30.0

        # 测试边界情况
        progress.total_files = 0
        assert progress.progress_percentage == 0.0

        progress.total_files = 5
        progress.processed_files = 5
        assert progress.progress_percentage == 100.0

    def test_add_error(self):
        """测试添加错误"""
        progress = ScanProgress()

        progress.add_error("Test error 1")
        progress.add_error("Test error 2")

        assert len(progress.errors) == 2
        assert "Test error 1" in progress.errors
        assert "Test error 2" in progress.errors


class TestScanResult:
    """扫描结果模型测试类"""

    def test_create_successful_result(self):
        """测试创建成功的扫描结果"""
        project_info = ProjectInfo(
            name="Test Project", path=Path("/test"), project_type=ProjectType.MODPACK
        )

        result = ScanResult(success=True, project_info=project_info, scan_time=1.5)

        assert result.success is True
        assert result.project_info == project_info
        assert result.scan_time == 1.5
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_create_failed_result(self):
        """测试创建失败的扫描结果"""
        result = ScanResult(
            success=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )

        assert result.success is False
        assert result.project_info is None
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "Error 1" in result.errors
        assert "Warning 1" in result.warnings


class TestMinecraftModScanRule:
    """Minecraft MOD扫描规则测试类"""

    def test_mod_rule_matches(self):
        """测试MOD文件匹配规则"""
        rule = MinecraftModScanRule()

        # 测试匹配的文件
        assert rule.matches(Path("test.jar")) is True
        assert rule.matches(Path("test.JAR")) is True  # 大小写不敏感
        assert rule.matches(Path("test.zip")) is True

        # 测试不匹配的文件
        assert rule.matches(Path("test.txt")) is False
        assert rule.matches(Path("test.json")) is False
        assert rule.matches(Path("/path/to/directory")) is False


class TestModpackScanRule:
    """整合包扫描规则测试类"""

    def test_modpack_rule_matches(self):
        """测试整合包目录匹配规则"""
        rule = ModpackScanRule()

        with tempfile.TemporaryDirectory() as temp_dir:
            modpack_dir = Path(temp_dir) / "modpack"
            modpack_dir.mkdir()

            # 创建mods目录
            mods_dir = modpack_dir / "mods"
            mods_dir.mkdir()

            # 创建manifest.json
            manifest_file = modpack_dir / "manifest.json"
            manifest_file.write_text('{"manifestType": "minecraftModpack"}')

            # 应该匹配
            assert rule.matches(modpack_dir) is True

            # 空目录不应该匹配
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()
            assert rule.matches(empty_dir) is False

    def test_find_mod_directories(self):
        """测试查找MOD目录"""
        rule = ModpackScanRule()

        with tempfile.TemporaryDirectory() as temp_dir:
            modpack_dir = Path(temp_dir) / "modpack"
            modpack_dir.mkdir()

            # 创建多个可能的MOD目录
            mods_dir = modpack_dir / "mods"
            mods_dir.mkdir()

            plugins_dir = modpack_dir / "plugins"
            plugins_dir.mkdir()

            # 查找MOD目录
            mod_dirs = rule.find_mod_directories(modpack_dir)

            assert len(mod_dirs) >= 1
            assert mods_dir in mod_dirs
