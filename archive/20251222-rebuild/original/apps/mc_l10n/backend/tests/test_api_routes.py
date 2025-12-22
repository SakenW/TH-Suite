# tests/test_api_routes.py
"""
API路由测试

测试扫描相关的REST API端点
"""

# 导入FastAPI应用
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from api.routes.mod_routes import ModInfo  # noqa: E402
from api.routes.project_routes import ProjectInfo  # noqa: E402
from main import app  # noqa: E402
from src.application.dto import ScanResultDTO as ScanResult  # noqa: E402

from packages.core import LoaderType, ProjectType, ScanError  # noqa: E402


class TestScanAPI:
    """扫描API测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_scan_service(self):
        """模拟扫描服务"""
        service = AsyncMock()
        return service

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_scan_health_check(self, client):
        """测试扫描服务健康检查"""
        response = client.get("/api/scan/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "scan"

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_start_project_scan_success(
        self, mock_get_service, client, sample_modpack_dir
    ):
        """测试成功启动项目扫描"""
        from uuid import uuid4

        # 设置模拟
        mock_service = AsyncMock()
        mock_task_id = uuid4()
        mock_service.start_project_scan.return_value = mock_task_id
        mock_get_service.return_value = mock_service

        # 发送请求
        request_data = {"path": str(sample_modpack_dir)}
        response = client.post("/api/scan/project/start", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(mock_task_id)
        assert "已启动" in data["message"]

        # 验证服务调用
        mock_service.start_project_scan.assert_called_once()

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_start_project_scan_invalid_path(self, mock_get_service, client):
        """测试使用无效路径启动项目扫描"""
        mock_service = AsyncMock()
        mock_service.start_project_scan.side_effect = ScanError("Path does not exist")
        mock_get_service.return_value = mock_service

        request_data = {"path": "/nonexistent/path"}
        response = client.post("/api/scan/project/start", json=request_data)

        assert response.status_code == 400
        assert "扫描错误" in response.json()["detail"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_start_project_scan_empty_path(self, mock_get_service, client):
        """测试使用空路径启动项目扫描"""
        request_data = {"path": ""}
        response = client.post("/api/scan/project/start", json=request_data)

        assert response.status_code == 422  # Validation error

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_get_scan_progress_success(self, mock_get_service, client):
        """测试成功获取扫描进度"""
        from uuid import uuid4

        mock_service = AsyncMock()
        task_id = uuid4()
        mock_progress = {
            "task_id": str(task_id),
            "status": "in_progress",
            "progress": 0.5,
            "current_step": "扫描MOD文件",
            "error_message": None,
        }
        mock_service.get_scan_progress.return_value = mock_progress
        mock_get_service.return_value = mock_service

        response = client.get(f"/api/scan/progress/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task_id)
        assert data["status"] == "in_progress"
        assert data["progress"] == 0.5
        assert data["current_step"] == "扫描MOD文件"

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_get_scan_progress_not_found(self, mock_get_service, client):
        """测试获取不存在的扫描进度"""
        from uuid import uuid4

        mock_service = AsyncMock()
        mock_service.get_scan_progress.return_value = None
        mock_get_service.return_value = mock_service

        task_id = uuid4()
        response = client.get(f"/api/scan/progress/{task_id}")

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_get_scan_progress_invalid_uuid(self, mock_get_service, client):
        """测试使用无效UUID获取扫描进度"""
        response = client.get("/api/scan/progress/invalid-uuid")

        assert response.status_code == 400
        assert "无效的任务ID格式" in response.json()["detail"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_quick_scan_project_success(
        self, mock_get_service, client, sample_modpack_dir
    ):
        """测试成功快速扫描项目"""
        mock_service = AsyncMock()

        # 创建模拟项目信息
        project_info = ProjectInfo(
            name="Test Modpack",
            path=sample_modpack_dir,
            project_type=ProjectType.MODPACK,
            loader_type=LoaderType.FABRIC,
        )
        project_info.fingerprint = "test_fingerprint"
        project_info.supported_locales.update(["en_us", "zh_cn"])

        # 创建模拟扫描结果
        scan_result = ScanResult(success=True, project_info=project_info)

        mock_service.quick_scan_project.return_value = scan_result
        mock_get_service.return_value = mock_service

        request_data = {"path": str(sample_modpack_dir)}
        response = client.post("/api/scan/project/quick", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_info"]["name"] == "Test Modpack"
        assert data["project_info"]["project_type"] == "modpack"
        assert data["project_info"]["loader_type"] == "fabric"
        assert "en_us" in data["project_info"]["supported_locales"]
        assert "zh_cn" in data["project_info"]["supported_locales"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_quick_scan_project_failed(self, mock_get_service, client):
        """测试快速扫描项目失败"""
        mock_service = AsyncMock()

        scan_result = ScanResult(
            success=False, errors=["Unsupported project type", "Path not accessible"]
        )

        mock_service.quick_scan_project.return_value = scan_result
        mock_get_service.return_value = mock_service

        request_data = {"path": "/invalid/path"}
        response = client.post("/api/scan/project/quick", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["project_info"] is None
        assert len(data["errors"]) == 2
        assert "Unsupported project type" in data["errors"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_scan_single_mod_success(self, mock_get_service, client, sample_fabric_mod):
        """测试成功扫描单个MOD文件"""
        # ModInfo should be available from the main imports or packages

        mock_service = AsyncMock()

        # 创建模拟MOD信息
        mod_info = ModInfo(
            mod_id="sample_fabric_mod",
            name="Sample Fabric Mod",
            version="1.0.0",
            description="A sample Fabric mod",
            authors=["TestAuthor"],
            file_path=sample_fabric_mod,
            file_size=2048,
            loader_type=LoaderType.FABRIC,
        )

        mock_service.scan_single_mod.return_value = mod_info
        mock_get_service.return_value = mock_service

        request_data = {"path": str(sample_fabric_mod)}
        response = client.post("/api/scan/mod", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["mod_id"] == "sample_fabric_mod"
        assert data["name"] == "Sample Fabric Mod"
        assert data["version"] == "1.0.0"
        assert data["loader_type"] == "fabric"
        assert "TestAuthor" in data["authors"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_scan_single_mod_not_found(self, mock_get_service, client):
        """测试扫描不存在的MOD文件"""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        request_data = {"path": "/nonexistent/mod.jar"}
        response = client.post("/api/scan/mod", json=request_data)

        assert response.status_code == 404
        assert "MOD文件不存在" in response.json()["detail"]

    @patch("src.mc_l10n.api.scan_router.get_scan_service")
    def test_scan_single_mod_scan_error(self, mock_get_service, client):
        """测试扫描MOD时出现扫描错误"""
        mock_service = AsyncMock()
        mock_service.scan_single_mod.side_effect = ScanError("Invalid MOD file")
        mock_get_service.return_value = mock_service

        with tempfile.TemporaryDirectory() as temp_dir:
            mod_path = Path(temp_dir) / "invalid.jar"
            mod_path.write_text("not a jar file")

            request_data = {"path": str(mod_path)}
            response = client.post("/api/scan/mod", json=request_data)

            assert response.status_code == 400
            assert "扫描错误" in response.json()["detail"]

    def test_root_endpoint(self, client):
        """测试根路径端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "MC L10n Backend API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"

    def test_api_documentation_accessible(self, client):
        """测试API文档可访问"""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200
