"""
全局测试配置文件
提供通用的测试 fixtures 和设置
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
import json
import sqlite3
from unittest.mock import Mock, AsyncMock

# 添加项目路径到 Python 路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.mc_l10n.backend.core.di_container import DIContainer
from apps.mc_l10n.backend.main import create_app
from apps.mc_l10n.backend.infrastructure.db_initializer import DatabaseInitializer


@pytest.fixture(scope="session")
def event_loop():
    """创建用于整个测试会话的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """提供临时目录"""
    temp_path = Path(tempfile.mkdtemp(prefix="th_suite_test_"))
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
async def test_db() -> AsyncGenerator[str, None]:
    """提供测试数据库"""
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = db_file.name
    db_file.close()
    
    try:
        # 初始化测试数据库
        db_initializer = DatabaseInitializer(db_path)
        await db_initializer.initialize()
        
        yield f"sqlite:///{db_path}"
    finally:
        # 清理测试数据库
        try:
            Path(db_path).unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def mock_di_container():
    """模拟依赖注入容器"""
    container = Mock(spec=DIContainer)
    
    # 设置常用的服务模拟
    container.get_project_service = Mock()
    container.get_scan_service = Mock()
    container.get_translation_service = Mock()
    container.get_sync_service = Mock()
    
    return container


@pytest.fixture
async def test_app():
    """提供测试应用实例"""
    app = create_app()
    
    # 设置测试配置
    app.state.testing = True
    
    return app


@pytest.fixture
def sample_minecraft_project(temp_dir: Path) -> Path:
    """创建示例 Minecraft 项目结构"""
    project_path = temp_dir / "sample_minecraft_project"
    project_path.mkdir()
    
    # 创建 MOD 结构
    mod_assets = project_path / "assets" / "sample_mod" / "lang"
    mod_assets.mkdir(parents=True)
    
    # 英文语言文件
    en_us_data = {
        "item.sample_mod.iron_sword": "Iron Sword",
        "item.sample_mod.golden_apple": "Golden Apple",
        "block.sample_mod.magic_ore": "Magic Ore",
        "entity.sample_mod.fire_dragon": "Fire Dragon",
        "gui.sample_mod.inventory": "Inventory"
    }
    (mod_assets / "en_us.json").write_text(
        json.dumps(en_us_data, indent=2, ensure_ascii=False)
    )
    
    # 中文语言文件（部分翻译）
    zh_cn_data = {
        "item.sample_mod.iron_sword": "铁剑",
        "item.sample_mod.golden_apple": "金苹果",
        "block.sample_mod.magic_ore": "魔法矿石"
        # 故意遗漏部分翻译条目
    }
    (mod_assets / "zh_cn.json").write_text(
        json.dumps(zh_cn_data, indent=2, ensure_ascii=False)
    )
    
    # 创建 MOD 元数据
    mods_toml = project_path / "META-INF" / "mods.toml"
    mods_toml.parent.mkdir(parents=True)
    mods_toml.write_text("""
modLoader="forge"
loaderVersion="[43,)"
license="MIT"

[[mods]]
modId="sample_mod"
version="1.0.0"
displayName="Sample Mod"
description="A sample mod for testing"
""")
    
    # 创建资源包元数据
    pack_mcmeta = project_path / "pack.mcmeta"
    pack_mcmeta.write_text(json.dumps({
        "pack": {
            "pack_format": 9,
            "description": "Sample resource pack for testing"
        }
    }, indent=2))
    
    return project_path


@pytest.fixture
def sample_jar_file(temp_dir: Path) -> Path:
    """创建示例 JAR 文件"""
    import zipfile
    
    jar_path = temp_dir / "sample_mod.jar"
    
    with zipfile.ZipFile(jar_path, 'w') as jar:
        # 添加语言文件
        jar.writestr(
            "assets/sample_mod/lang/en_us.json",
            json.dumps({
                "item.sample_mod.test_item": "Test Item",
                "block.sample_mod.test_block": "Test Block"
            }, indent=2)
        )
        
        # 添加 MOD 元数据
        jar.writestr(
            "META-INF/mods.toml",
            """
modLoader="forge"
loaderVersion="[43,)"

[[mods]]
modId="sample_mod"
version="1.0.0"
displayName="Sample Mod"
"""
        )
        
        # 添加一些虚拟类文件
        jar.writestr("com/example/SampleMod.class", b"dummy class content")
    
    return jar_path


@pytest.fixture
def sample_translation_entries():
    """提供示例翻译条目数据"""
    return [
        {
            "id": "entry_1",
            "key": "item.sample_mod.iron_sword",
            "source_text": "Iron Sword",
            "target_text": "铁剑",
            "source_language": "en_us",
            "target_language": "zh_cn",
            "status": "completed",
            "version": 1
        },
        {
            "id": "entry_2",
            "key": "item.sample_mod.golden_apple",
            "source_text": "Golden Apple",
            "target_text": "金苹果",
            "source_language": "en_us",
            "target_language": "zh_cn",
            "status": "completed",
            "version": 1
        },
        {
            "id": "entry_3",
            "key": "block.sample_mod.magic_ore",
            "source_text": "Magic Ore",
            "target_text": "",
            "source_language": "en_us",
            "target_language": "zh_cn",
            "status": "pending",
            "version": 1
        }
    ]


@pytest.fixture
def mock_trans_hub_api():
    """模拟 Trans-Hub API 服务"""
    api_mock = AsyncMock()
    
    # 模拟 API 响应
    api_mock.push_translations.return_value = {
        "success": True,
        "uploaded_count": 10,
        "failed_count": 0
    }
    
    api_mock.pull_translations.return_value = {
        "success": True,
        "entries": [
            {
                "key": "item.test.new_item",
                "source_text": "New Item",
                "target_text": "新物品",
                "language": "zh_cn",
                "status": "completed"
            }
        ]
    }
    
    api_mock.check_connection.return_value = True
    
    return api_mock


@pytest.fixture
def performance_monitor():
    """性能监控器"""
    import time
    import psutil
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.process = psutil.Process()
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss
        
        def stop(self):
            if self.start_time is None:
                raise ValueError("Performance monitor not started")
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss
            
            return {
                "duration": end_time - self.start_time,
                "memory_delta": end_memory - self.start_memory,
                "peak_memory": end_memory
            }
    
    return PerformanceMonitor()


@pytest.fixture
def test_data_factory():
    """测试数据工厂"""
    class TestDataFactory:
        @staticmethod
        def create_project_data(**overrides):
            default_data = {
                "name": "Test Project",
                "description": "A test project",
                "project_type": "mod",
                "project_path": "/path/to/test/project",
                "source_language": "en_us",
                "target_languages": ["zh_cn", "ja_jp"]
            }
            return {**default_data, **overrides}
        
        @staticmethod
        def create_translation_entry(**overrides):
            default_entry = {
                "key": "item.test.test_item",
                "source_text": "Test Item",
                "target_text": "测试物品",
                "source_language": "en_us",
                "target_language": "zh_cn",
                "status": "completed",
                "version": 1
            }
            return {**default_entry, **overrides}
        
        @staticmethod
        def create_scan_result(**overrides):
            default_result = {
                "total_files": 5,
                "total_entries": 50,
                "completed_entries": 30,
                "pending_entries": 20,
                "scan_duration": 1.5
            }
            return {**default_result, **overrides}
    
    return TestDataFactory()


# 测试标记定义
pytest_plugins = []

def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """根据标记自动跳过某些测试"""
    skip_slow = pytest.mark.skip(reason="slow test skipped by default")
    skip_e2e = pytest.mark.skip(reason="e2e test skipped in unit test run")
    
    for item in items:
        # 如果运行时没有指定 --run-slow，跳过慢测试
        if "slow" in item.keywords and not config.getoption("--run-slow", default=False):
            item.add_marker(skip_slow)
        
        # 如果运行时没有指定 --run-e2e，跳过端到端测试
        if "e2e" in item.keywords and not config.getoption("--run-e2e", default=False):
            item.add_marker(skip_e2e)


def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="run end-to-end tests"
    )
    parser.addoption(
        "--performance-baseline",
        action="store",
        default=None,
        help="path to performance baseline file"
    )


@pytest.fixture(autouse=True)
def setup_test_logging():
    """设置测试日志"""
    import structlog
    import logging
    
    # 配置 structlog 用于测试
    structlog.configure(
        processors=[
            structlog.testing.LogCapture(),
        ],
        wrapper_class=structlog.testing.LogCapture,
        logger_factory=lambda: [],
        cache_logger_on_first_use=True,
    )
    
    # 设置基本日志级别
    logging.getLogger().setLevel(logging.WARNING)


@pytest.fixture
def capture_logs():
    """捕获日志输出"""
    import structlog
    
    cap = structlog.testing.LogCapture()
    
    # 重新配置以使用日志捕获器
    structlog.configure(
        processors=[cap],
        wrapper_class=structlog.testing.LogCapture,
        logger_factory=lambda: cap,
        cache_logger_on_first_use=False,
    )
    
    yield cap
    
    # 恢复原始配置（如果需要）
    structlog.reset_defaults()


# 异步测试辅助工具
class AsyncTestHelper:
    """异步测试辅助类"""
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """等待条件满足"""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if await condition_func():
                return True
            
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                raise TimeoutError(f"Condition not met within {timeout} seconds")
            
            await asyncio.sleep(interval)
    
    @staticmethod
    async def run_with_timeout(coro, timeout=5.0):
        """运行协程并设置超时"""
        import asyncio
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")


@pytest.fixture
def async_helper():
    """提供异步测试辅助工具"""
    return AsyncTestHelper()


# 性能测试基准
class PerformanceBaseline:
    """性能基准管理"""
    
    def __init__(self, baseline_file: Path = None):
        self.baseline_file = baseline_file or Path("tests/performance_baseline.json")
        self.baselines = self._load_baselines()
    
    def _load_baselines(self):
        """加载性能基准"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def save_baselines(self):
        """保存性能基准"""
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baselines, f, indent=2)
    
    def check_performance(self, test_name: str, metrics: dict, tolerance: float = 0.1):
        """检查性能是否符合基准"""
        if test_name not in self.baselines:
            # 第一次运行，保存为基准
            self.baselines[test_name] = metrics
            return True
        
        baseline = self.baselines[test_name]
        for metric_name, value in metrics.items():
            if metric_name in baseline:
                baseline_value = baseline[metric_name]
                if value > baseline_value * (1 + tolerance):
                    return False
        
        return True
    
    def update_baseline(self, test_name: str, metrics: dict):
        """更新性能基准"""
        self.baselines[test_name] = metrics


@pytest.fixture
def performance_baseline(request):
    """性能基准管理器"""
    baseline_file = request.config.getoption("--performance-baseline")
    if baseline_file:
        baseline_file = Path(baseline_file)
    
    return PerformanceBaseline(baseline_file)


# 数据库测试工具
class DatabaseTestHelper:
    """数据库测试辅助工具"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    def execute_sql(self, sql: str, params=None):
        """执行 SQL 语句"""
        # 这里简化处理，实际应该使用 SQLAlchemy
        if self.db_url.startswith("sqlite://"):
            db_path = self.db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
                return cursor.fetchall()
            finally:
                conn.close()
    
    def count_rows(self, table_name: str) -> int:
        """计算表中行数"""
        result = self.execute_sql(f"SELECT COUNT(*) FROM {table_name}")
        return result[0][0] if result else 0
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_sql(sql, (table_name,))
        return len(result) > 0


@pytest.fixture
def db_helper(test_db):
    """数据库测试辅助工具"""
    return DatabaseTestHelper(test_db)


# 文件系统测试工具
class FileSystemTestHelper:
    """文件系统测试辅助工具"""
    
    @staticmethod
    def create_test_files(base_path: Path, file_structure: dict):
        """根据结构创建测试文件"""
        for name, content in file_structure.items():
            file_path = base_path / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(content, dict):
                # 如果是字典，创建为 JSON 文件
                file_path.write_text(json.dumps(content, indent=2, ensure_ascii=False))
            else:
                # 否则直接写入文本内容
                file_path.write_text(str(content))
    
    @staticmethod
    def assert_file_exists(file_path: Path, content: str = None):
        """断言文件存在并检查内容"""
        assert file_path.exists(), f"File {file_path} does not exist"
        
        if content is not None:
            actual_content = file_path.read_text()
            assert actual_content == content, f"File content mismatch in {file_path}"
    
    @staticmethod
    def assert_directory_structure(base_path: Path, expected_structure: list):
        """断言目录结构符合预期"""
        for expected_path in expected_structure:
            full_path = base_path / expected_path
            assert full_path.exists(), f"Expected path {expected_path} does not exist"


@pytest.fixture
def fs_helper():
    """文件系统测试辅助工具"""
    return FileSystemTestHelper()