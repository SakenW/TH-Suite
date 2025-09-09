"""
集成测试
测试各层之间的协作
"""

import os
import tempfile

import pytest
from container import ServiceContainer
from domain.value_objects import LanguageCode
from facade.mc_l10n_facade import MCL10nFacade


class TestIntegration:
    """集成测试套件"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def container(self, temp_db):
        """创建服务容器"""
        container = ServiceContainer(database_path=temp_db)
        container.initialize()
        yield container
        container.cleanup()

    @pytest.fixture
    def facade(self, container):
        """创建门面服务"""
        return MCL10nFacade(container)

    def test_end_to_end_scan_workflow(self, facade, tmp_path):
        """测试端到端扫描工作流"""
        # 创建测试文件结构
        test_dir = tmp_path / "test_mods"
        test_dir.mkdir()

        # 创建模拟的jar文件
        mod_file = test_dir / "test_mod.jar"
        mod_file.write_text("mock jar content")

        # 执行扫描
        result = facade.scan_mods(
            path=str(test_dir), recursive=True, auto_extract=False
        )

        # 验证结果
        assert result.success
        assert result.total_files > 0
        assert result.duration > 0

    def test_translation_workflow(self, facade):
        """测试翻译工作流"""
        # 创建测试mod
        mod_id = "test_mod_trans"

        # 模拟翻译数据
        translations = {"item.test.name": "测试物品", "block.test.name": "测试方块"}

        # 执行翻译
        result = facade.translate_mod(
            mod_id=mod_id,
            language="zh_cn",
            translations=translations,
            translator="test_user",
            auto_approve=True,
        )

        # 验证结果
        assert result.mod_id == mod_id
        assert result.language == "zh_cn"
        # 注意：实际翻译可能失败因为mod不存在

    def test_project_management(self, facade):
        """测试项目管理"""
        # 创建项目
        project_id = facade.create_project(
            name="Test Project",
            mod_ids=["mod1", "mod2"],
            target_languages=["zh_cn", "ja_jp"],
            auto_assign=True,
        )

        assert project_id is not None
        assert project_id.startswith("proj_")

        # 获取项目状态
        status = facade.get_project_status(project_id)

        assert status["id"] == project_id
        assert status["name"] == "Test Project"
        assert status["status"] == "active"

    def test_quality_check(self, facade):
        """测试质量检查"""
        # 执行质量检查
        report = facade.check_quality(mod_id="test_mod", language="zh_cn")

        # 验证报告结构
        assert "mod_id" in report
        assert "language" in report

        # 如果mod不存在，应该有错误信息
        if "error" in report:
            assert report["error"] == "Mod not found"

    def test_cache_functionality(self, facade):
        """测试缓存功能"""
        # 第一次调用（缓存未命中）
        result1 = facade.quick_scan("/test/path")

        # 第二次调用（缓存命中）
        result2 = facade.quick_scan("/test/path")

        # 结果应该相同
        assert result1 == result2

    def test_sync_with_server(self, facade):
        """测试服务器同步"""
        # 执行同步
        result = facade.sync_with_server()

        # 验证结果
        assert result.synced_count >= 0
        assert result.conflict_count >= 0
        assert result.error_count >= 0
        assert result.duration >= 0


class TestPerformanceOptimizations:
    """测试性能优化"""

    def test_batch_processor(self):
        """测试批处理器"""
        from infrastructure.batch_processor import BatchProcessor

        processor = BatchProcessor(batch_size=10, max_workers=2)

        # 处理函数
        def process_item(item):
            return item * 2

        # 测试数据
        items = list(range(100))

        # 执行批处理
        result = processor.process(items=items, processor=process_item)

        # 验证结果
        assert len(result.successful) == 100
        assert result.successful[0] == 0
        assert result.successful[50] == 100
        assert result.success_rate == 1.0

    def test_connection_pool(self, temp_db):
        """测试连接池"""
        from infrastructure.db.connection_pool import ConnectionPool

        pool = ConnectionPool(
            database_path=temp_db, min_connections=2, max_connections=5
        )

        # 获取连接
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

        # 检查统计
        stats = pool.get_stats()
        assert stats["created"] >= 2
        assert stats["reused"] >= 0

        # 清理
        pool.close()

    @pytest.mark.asyncio
    async def test_request_batcher(self):
        """测试请求批处理器"""
        from infrastructure.request_batcher import RequestBatcher

        batcher = RequestBatcher(batch_window=0.01, max_batch_size=5)

        # 注册处理器
        async def batch_processor(requests):
            return [r["value"] * 2 for r in requests]

        batcher.register_processor("test", batch_processor)

        # 提交多个请求
        import asyncio

        tasks = [batcher.submit("test", {"value": i}) for i in range(10)]

        # 等待结果
        results = await asyncio.gather(*tasks)

        # 验证结果
        assert results[0] == 0
        assert results[5] == 10

        # 检查统计
        stats = batcher.get_stats()
        assert stats["total_requests"] == 10
        assert stats["batch_count"] > 0


class TestErrorHandling:
    """测试错误处理"""

    def test_invalid_mod_scan(self, facade):
        """测试无效mod扫描"""
        result = facade.scan_mods(path="/non/existent/path", recursive=True)

        # 应该返回错误但不崩溃
        assert not result.success
        assert len(result.errors) > 0

    def test_invalid_language_code(self):
        """测试无效语言代码"""

        # 有效转换
        lang = LanguageCode.from_string("zh_cn")
        assert lang == LanguageCode.ZH_CN

        # 无效转换
        lang = LanguageCode.from_string("invalid_lang")
        assert lang is None

    def test_repository_error_handling(self, container):
        """测试仓储错误处理"""
        mod_repo = container.get_repository("mod")

        # 查找不存在的mod
        result = mod_repo.find_by_id("non_existent_mod")
        assert result is None

        # 不应该抛出异常
        try:
            mod_repo.delete("non_existent_mod")
        except Exception:
            pytest.fail("Delete should not raise exception for non-existent item")
