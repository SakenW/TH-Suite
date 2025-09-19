"""
全面的API接口测试套件
覆盖所有REST API端点的功能和错误情况
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import status
import json
import time
from typing import Dict, Any, List
from pathlib import Path

from apps.mc_l10n.backend.main import create_app
from apps.mc_l10n.backend.core.di_container import DIContainer


class TestProjectAPI:
    """项目管理API测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        app = create_app()
        return TestClient(app)
    
    def test_create_project_success(self, client):
        """测试创建项目成功案例"""
        project_data = {
            "name": "Test Project",
            "description": "A test project for unit testing",
            "project_type": "minecraft_mod",
            "source_language": "en_us",
            "target_languages": ["zh_cn", "ja_jp"],
            "project_path": "/path/to/test/project"
        }
        
        response = client.post("/api/v1/projects", json=project_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        response_data = response.json()
        assert "id" in response_data
        assert response_data["name"] == project_data["name"]
        assert response_data["project_type"] == project_data["project_type"]
        assert response_data["status"] == "created"
    
    def test_create_project_validation_errors(self, client):
        """测试创建项目验证错误"""
        # 缺少必填字段
        invalid_data = {
            "name": "",  # 空名称
            "project_type": "invalid_type",  # 无效类型
            "source_language": "invalid_lang"  # 无效语言代码
        }
        
        response = client.post("/api/v1/projects", json=invalid_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        errors = response.json()["detail"]
        assert len(errors) > 0
        
        # 验证错误信息包含字段验证失败
        error_fields = [error["loc"][-1] for error in errors]
        assert "name" in error_fields
        assert "project_type" in error_fields
    
    def test_get_project_by_id(self, client):
        """测试通过ID获取项目"""
        # 首先创建一个项目
        project_data = {
            "name": "Test Project for Get",
            "description": "Test project",
            "project_type": "minecraft_mod",
            "source_language": "en_us",
            "target_languages": ["zh_cn"],
            "project_path": "/path/to/test"
        }
        
        create_response = client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]
        
        # 获取项目
        response = client.get(f"/api/v1/projects/{project_id}")
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["id"] == project_id
        assert response_data["name"] == project_data["name"]
    
    def test_get_project_not_found(self, client):
        """测试获取不存在的项目"""
        non_existent_id = "non-existent-project-id"
        
        response = client.get(f"/api/v1/projects/{non_existent_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()
    
    def test_list_projects(self, client):
        """测试项目列表"""
        # 创建多个测试项目
        projects = []
        for i in range(3):
            project_data = {
                "name": f"Test Project {i}",
                "description": f"Test project {i}",
                "project_type": "minecraft_mod",
                "source_language": "en_us",
                "target_languages": ["zh_cn"],
                "project_path": f"/path/to/test/{i}"
            }
            response = client.post("/api/v1/projects", json=project_data)
            projects.append(response.json())
        
        # 获取项目列表
        response = client.get("/api/v1/projects")
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert "items" in response_data
        assert "total" in response_data
        assert len(response_data["items"]) >= 3
    
    def test_update_project(self, client):
        """测试更新项目"""
        # 创建项目
        project_data = {
            "name": "Original Project",
            "description": "Original description",
            "project_type": "minecraft_mod",
            "source_language": "en_us",
            "target_languages": ["zh_cn"],
            "project_path": "/path/to/original"
        }
        
        create_response = client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]
        
        # 更新项目
        update_data = {
            "name": "Updated Project",
            "description": "Updated description",
            "target_languages": ["zh_cn", "ja_jp", "ko_kr"]
        }
        
        response = client.put(f"/api/v1/projects/{project_id}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["name"] == update_data["name"]
        assert response_data["description"] == update_data["description"]
        assert len(response_data["target_languages"]) == 3
    
    def test_delete_project(self, client):
        """测试删除项目"""
        # 创建项目
        project_data = {
            "name": "Project to Delete",
            "description": "This project will be deleted",
            "project_type": "minecraft_mod",
            "source_language": "en_us",
            "target_languages": ["zh_cn"],
            "project_path": "/path/to/delete"
        }
        
        create_response = client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]
        
        # 删除项目
        response = client.delete(f"/api/v1/projects/{project_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 验证项目已删除
        get_response = client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestScanAPI:
    """扫描API测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        app = create_app()
        return TestClient(app)
    
    def test_start_scan_success(self, client):
        """测试开始扫描成功"""
        scan_request = {
            "project_path": "/path/to/minecraft/project",
            "scan_type": "full",
            "include_mods": True,
            "include_resourcepacks": True,
            "recursive": True
        }
        
        response = client.post("/api/v1/scan/start", json=scan_request)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        response_data = response.json()
        assert "scan_id" in response_data
        assert "status" in response_data
        assert response_data["status"] == "started"
    
    def test_start_scan_invalid_path(self, client):
        """测试扫描无效路径"""
        scan_request = {
            "project_path": "",  # 空路径
            "scan_type": "full"
        }
        
        response = client.post("/api/v1/scan/start", json=scan_request)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_scan_status(self, client):
        """测试获取扫描状态"""
        # 首先开始扫描
        scan_request = {
            "project_path": "/path/to/test/project",
            "scan_type": "incremental"
        }
        
        start_response = client.post("/api/v1/scan/start", json=scan_request)
        scan_id = start_response.json()["scan_id"]
        
        # 获取扫描状态
        response = client.get(f"/api/v1/scan/{scan_id}/status")
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert "scan_id" in response_data
        assert "status" in response_data
        assert "progress" in response_data
        assert response_data["scan_id"] == scan_id
    
    def test_get_scan_results(self, client):
        """测试获取扫描结果"""
        # 模拟完成的扫描
        scan_request = {
            "project_path": "/path/to/completed/project",
            "scan_type": "full"
        }
        
        start_response = client.post("/api/v1/scan/start", json=scan_request)
        scan_id = start_response.json()["scan_id"]
        
        # 等待扫描完成（在真实测试中可能需要轮询）
        import time
        time.sleep(0.1)
        
        # 获取扫描结果
        response = client.get(f"/api/v1/scan/{scan_id}/results")
        
        # 注意：实际结果取决于扫描实现
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "scan_id" in response_data
            assert "results" in response_data
    
    def test_cancel_scan(self, client):
        """测试取消扫描"""
        # 开始扫描
        scan_request = {
            "project_path": "/path/to/large/project",
            "scan_type": "full"
        }
        
        start_response = client.post("/api/v1/scan/start", json=scan_request)
        scan_id = start_response.json()["scan_id"]
        
        # 取消扫描
        response = client.post(f"/api/v1/scan/{scan_id}/cancel")
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["scan_id"] == scan_id
        assert "cancelled" in response_data["status"].lower()


class TestTranslationAPI:
    """翻译API测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        app = create_app()
        return TestClient(app)
    
    def test_create_translation_entry(self, client):
        """测试创建翻译条目"""
        translation_data = {
            "key": "item.test_mod.test_item",
            "source_text": "Test Item",
            "source_language": "en_us",
            "target_language": "zh_cn",
            "project_id": "test-project-id",
            "context": "Item name for inventory display"
        }
        
        response = client.post("/api/v1/translations", json=translation_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        response_data = response.json()
        assert "id" in response_data
        assert response_data["key"] == translation_data["key"]
        assert response_data["source_text"] == translation_data["source_text"]
        assert response_data["status"] == "pending"
    
    def test_update_translation(self, client):
        """测试更新翻译"""
        # 创建翻译条目
        translation_data = {
            "key": "item.test_mod.sword",
            "source_text": "Iron Sword",
            "source_language": "en_us",
            "target_language": "zh_cn",
            "project_id": "test-project-id"
        }
        
        create_response = client.post("/api/v1/translations", json=translation_data)
        translation_id = create_response.json()["id"]
        
        # 更新翻译
        update_data = {
            "target_text": "铁剑",
            "status": "completed",
            "translator": "test_translator",
            "quality_score": 0.95
        }
        
        response = client.put(f"/api/v1/translations/{translation_id}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["target_text"] == update_data["target_text"]
        assert response_data["status"] == update_data["status"]
        assert response_data["quality_score"] == update_data["quality_score"]
    
    def test_batch_translation_update(self, client):
        """测试批量翻译更新"""
        # 创建多个翻译条目
        translations = []
        for i in range(3):
            translation_data = {
                "key": f"item.test_mod.item_{i}",
                "source_text": f"Test Item {i}",
                "source_language": "en_us",
                "target_language": "zh_cn",
                "project_id": "test-project-id"
            }
            response = client.post("/api/v1/translations", json=translation_data)
            translations.append(response.json())
        
        # 批量更新
        batch_updates = [
            {
                "id": translations[0]["id"],
                "target_text": "测试物品 0",
                "status": "completed"
            },
            {
                "id": translations[1]["id"],
                "target_text": "测试物品 1",
                "status": "completed"
            },
            {
                "id": translations[2]["id"],
                "target_text": "测试物品 2",
                "status": "review"
            }
        ]
        
        response = client.put("/api/v1/translations/batch", json={"updates": batch_updates})
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert "updated_count" in response_data
        assert response_data["updated_count"] == 3
    
    def test_get_translation_by_key(self, client):
        """测试通过键获取翻译"""
        # 创建翻译条目
        translation_data = {
            "key": "entity.test_mod.test_entity",
            "source_text": "Test Entity",
            "source_language": "en_us",
            "target_language": "zh_cn",
            "project_id": "test-project-id"
        }
        
        client.post("/api/v1/translations", json=translation_data)
        
        # 通过键获取翻译
        response = client.get("/api/v1/translations/by-key", params={
            "key": translation_data["key"],
            "project_id": translation_data["project_id"],
            "target_language": translation_data["target_language"]
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["key"] == translation_data["key"]
        assert response_data["source_text"] == translation_data["source_text"]


class TestSyncAPI:
    """同步API测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        app = create_app()
        return TestClient(app)
    
    def test_start_sync_to_trans_hub(self, client):
        """测试开始同步到Trans-Hub"""
        sync_request = {
            "project_id": "test-project-id",
            "sync_type": "push",
            "target": "trans_hub",
            "include_untranslated": True,
            "include_pending": True
        }
        
        response = client.post("/api/v1/sync/start", json=sync_request)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        response_data = response.json()
        assert "sync_id" in response_data
        assert "status" in response_data
        assert response_data["status"] == "started"
    
    def test_get_sync_status(self, client):
        """测试获取同步状态"""
        # 开始同步
        sync_request = {
            "project_id": "test-project-id",
            "sync_type": "pull",
            "target": "trans_hub"
        }
        
        start_response = client.post("/api/v1/sync/start", json=sync_request)
        sync_id = start_response.json()["sync_id"]
        
        # 获取同步状态
        response = client.get(f"/api/v1/sync/{sync_id}/status")
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert "sync_id" in response_data
        assert "status" in response_data
        assert "progress" in response_data
    
    def test_sync_conflict_resolution(self, client):
        """测试同步冲突解决"""
        # 模拟有冲突的同步
        sync_request = {
            "project_id": "test-project-id",
            "sync_type": "bidirectional",
            "target": "trans_hub",
            "conflict_resolution": "manual"
        }
        
        start_response = client.post("/api/v1/sync/start", json=sync_request)
        sync_id = start_response.json()["sync_id"]
        
        # 获取冲突信息
        response = client.get(f"/api/v1/sync/{sync_id}/conflicts")
        
        # 根据实现可能返回不同状态
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "conflicts" in response_data
            
            # 如果有冲突，测试冲突解决
            if response_data["conflicts"]:
                resolution_data = {
                    "resolutions": [
                        {
                            "conflict_id": response_data["conflicts"][0]["id"],
                            "resolution": "accept_remote",
                            "comment": "Accepting remote version"
                        }
                    ]
                }
                
                resolve_response = client.post(
                    f"/api/v1/sync/{sync_id}/resolve-conflicts",
                    json=resolution_data
                )
                
                assert resolve_response.status_code == status.HTTP_200_OK


class TestErrorHandlingAndEdgeCases:
    """错误处理和边界情况测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        app = create_app()
        return TestClient(app)
    
    def test_malformed_json_request(self, client):
        """测试格式错误的JSON请求"""
        # 发送格式错误的JSON
        response = client.post(
            "/api/v1/projects",
            data="{ invalid json format",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_missing_content_type(self, client):
        """测试缺少Content-Type头"""
        project_data = {
            "name": "Test Project",
            "project_type": "minecraft_mod",
            "source_language": "en_us"
        }
        
        response = client.post(
            "/api/v1/projects",
            data=json.dumps(project_data)
            # 没有设置content-type
        )
        
        # FastAPI应该能处理这种情况
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_201_CREATED]
    
    def test_extremely_large_request(self, client):
        """测试极大的请求"""
        # 创建一个极大的项目数据
        large_description = "x" * (10 * 1024 * 1024)  # 10MB字符串
        
        project_data = {
            "name": "Large Project",
            "description": large_description,
            "project_type": "minecraft_mod",
            "source_language": "en_us"
        }
        
        response = client.post("/api/v1/projects", json=project_data)
        
        # 应该被限制或处理
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_201_CREATED  # 如果服务器接受大请求
        ]
    
    def test_sql_injection_attempt(self, client):
        """测试SQL注入尝试"""
        malicious_data = {
            "name": "'; DROP TABLE projects; --",
            "description": "' OR '1'='1",
            "project_type": "minecraft_mod",
            "source_language": "en_us"
        }
        
        response = client.post("/api/v1/projects", json=malicious_data)
        
        # 无论成功还是失败，都不应该导致SQL注入
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
        
        # 如果创建成功，验证数据被正确转义
        if response.status_code == status.HTTP_201_CREATED:
            response_data = response.json()
            assert response_data["name"] == malicious_data["name"]  # 原样保存，但不执行
    
    def test_concurrent_requests(self, client):
        """测试并发请求"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            project_data = {
                "name": f"Concurrent Project {threading.current_thread().ident}",
                "project_type": "minecraft_mod",
                "source_language": "en_us"
            }
            response = client.post("/api/v1/projects", json=project_data)
            results.put(response.status_code)
        
        # 创建多个并发线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有请求都成功处理
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        assert len(status_codes) == 10
        # 大部分或全部请求应该成功
        success_count = sum(1 for code in status_codes if code == status.HTTP_201_CREATED)
        assert success_count >= 8  # 至少80%成功
    
    def test_rate_limiting(self, client):
        """测试速率限制"""
        # 快速发送大量请求
        responses = []
        for i in range(100):
            project_data = {
                "name": f"Rate Test Project {i}",
                "project_type": "minecraft_mod",
                "source_language": "en_us"
            }
            response = client.post("/api/v1/projects", json=project_data)
            responses.append(response.status_code)
            
            # 如果遇到速率限制，停止测试
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        
        # 验证速率限制行为
        if status.HTTP_429_TOO_MANY_REQUESTS in responses:
            print("检测到速率限制，这是正常的保护机制")
        else:
            print("未检测到速率限制，可能需要配置")


class TestAPIDocumentationCompliance:
    """API文档合规性测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        app = create_app()
        return TestClient(app)
    
    def test_openapi_schema_availability(self, client):
        """测试OpenAPI模式可用性"""
        response = client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_api_documentation_accessibility(self, client):
        """测试API文档可访问性"""
        # 测试Swagger UI
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        
        # 测试ReDoc
        response = client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK


if __name__ == "__main__":
    # 运行API测试
    pytest.main([__file__, "-v"])