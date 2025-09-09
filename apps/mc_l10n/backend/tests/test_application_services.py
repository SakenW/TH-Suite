"""
应用服务层单元测试
"""

from unittest.mock import Mock, patch

import pytest
from application.commands import RescanCommand, ScanCommand
from application.dto import ModDTO, ScanResultDTO
from application.services.scan_service import ScanService
from domain.models.mod import Mod, ModId


class TestScanService:
    """测试扫描服务"""

    @pytest.fixture
    def mock_repositories(self):
        """模拟仓储"""
        return {"mod_repo": Mock(), "scan_result_repo": Mock(), "scanner": Mock()}

    @pytest.fixture
    def scan_service(self, mock_repositories):
        """创建扫描服务实例"""
        return ScanService(
            mod_repository=mock_repositories["mod_repo"],
            scan_result_repository=mock_repositories["scan_result_repo"],
            scanner=mock_repositories["scanner"],
        )

    def test_scan_directory_success(self, scan_service, mock_repositories):
        """测试成功扫描目录"""
        # 准备测试数据
        command = ScanCommand(
            directory_path="/test/path",
            include_patterns=["*.jar"],
            exclude_patterns=["*.bak"],
            force_rescan=False,
        )

        # 模拟扫描器返回
        mock_scan_result = Mock()
        mock_scan_result.mod_id = "test_mod"
        mock_scan_result.name = "Test Mod"
        mock_scan_result.version = "1.0.0"
        mock_scan_result.translations = {"en_us": [], "zh_cn": []}
        mock_scan_result.to_dict = Mock(return_value={})

        mock_repositories["scanner"].scan.return_value = mock_scan_result
        mock_repositories["mod_repo"].find_by_file_path.return_value = None

        # 执行扫描
        with patch.object(
            scan_service, "_get_scannable_files", return_value=["/test/mod.jar"]
        ):
            result = scan_service.scan_directory(command)

        # 验证结果
        assert isinstance(result, ScanResultDTO)
        assert result.success
        assert result.total_files == 1
        assert result.scanned_files == 1
        assert result.new_mods == 1
        assert result.failed_files == 0

    def test_scan_file_with_cache(self, scan_service, mock_repositories):
        """测试带缓存的文件扫描"""
        # 创建已存在的mod
        existing_mod = Mock(spec=Mod)
        existing_mod.needs_rescan.return_value = False

        mock_repositories["mod_repo"].find_by_file_path.return_value = existing_mod

        # 扫描文件（应该跳过）
        scan_service.scan_file("/test/mod.jar", force=False)

        # 验证没有调用扫描器
        mock_repositories["scanner"].scan.assert_not_called()

    def test_scan_file_force_rescan(self, scan_service, mock_repositories):
        """测试强制重新扫描"""
        # 创建已存在的mod
        existing_mod = Mock(spec=Mod)
        existing_mod.scan_completed = Mock()

        mock_repositories["mod_repo"].find_by_file_path.return_value = existing_mod

        # 模拟扫描结果
        mock_scan_result = Mock()
        mock_scan_result.mod_id = "test_mod"
        mock_scan_result.name = "Test Mod"
        mock_scan_result.version = "1.0.0"
        mock_scan_result.translations = {}
        mock_scan_result.to_dict = Mock(return_value={})

        mock_repositories["scanner"].scan.return_value = mock_scan_result

        # 强制重新扫描
        scan_service.scan_file("/test/mod.jar", force=True)

        # 验证调用了扫描器
        mock_repositories["scanner"].scan.assert_called_once()
        existing_mod.scan_completed.assert_called_once()
        mock_repositories["mod_repo"].update.assert_called_once()

    def test_rescan_all_with_missing_files(self, scan_service, mock_repositories):
        """测试重新扫描所有（包含缺失文件）"""
        # 创建模拟的mod列表
        mod1 = Mock()
        mod1.mod_id = ModId("mod1")
        mod1.file_path = "/exists/mod1.jar"

        mod2 = Mock()
        mod2.mod_id = ModId("mod2")
        mod2.file_path = "/missing/mod2.jar"

        mock_repositories["mod_repo"].find_all.return_value = [mod1, mod2]

        # 模拟文件存在性检查
        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = [True, False]

            command = RescanCommand(only_changed=False, remove_missing=True)

            with patch.object(scan_service, "scan_file"):
                result = scan_service.rescan_all(command)

        # 验证删除了缺失的mod
        mock_repositories["mod_repo"].delete.assert_called_once_with(mod2.mod_id)
        assert result.total_files == 2

    def test_batch_processing_integration(self, scan_service):
        """测试批处理集成"""
        # 验证批处理器已初始化
        assert hasattr(scan_service, "batch_processor")
        assert hasattr(scan_service, "bulk_optimizer")

        # 验证批处理器配置
        assert scan_service.batch_processor.batch_size == 100
        assert scan_service.batch_processor.max_workers == 4


class TestTranslationService:
    """测试翻译服务"""

    def test_translation_workflow(self):
        """测试翻译工作流"""
        # 这里添加翻译服务的测试
        pass


class TestProjectService:
    """测试项目服务"""

    def test_create_project(self):
        """测试创建项目"""
        # 这里添加项目服务的测试
        pass

    def test_project_assignment(self):
        """测试项目分配"""
        # 这里添加分配逻辑的测试
        pass


class TestDTOs:
    """测试数据传输对象"""

    def test_scan_result_dto(self):
        """测试扫描结果DTO"""
        dto = ScanResultDTO(
            directory="/test",
            total_files=10,
            scanned_files=8,
            new_mods=3,
            updated_mods=5,
            failed_files=2,
            errors=["Error 1", "Error 2"],
        )

        assert dto.directory == "/test"
        assert dto.total_files == 10
        assert not dto.success  # 因为有失败文件
        assert len(dto.errors) == 2

    def test_mod_dto_from_domain(self):
        """测试从领域模型创建DTO"""
        # 创建领域模型
        mod = Mod.create(
            mod_id="test_mod",
            name="Test Mod",
            version="1.0.0",
            file_path="/test/mod.jar",
        )

        # 转换为DTO
        dto = ModDTO.from_domain(mod)

        assert dto.mod_id == "test_mod"
        assert dto.name == "Test Mod"
        assert dto.version == "1.0.0"
        assert dto.file_path == "/test/mod.jar"
