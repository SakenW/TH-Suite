# MC L10n 使用指南

## 目录

1. [快速开始](#快速开始)
2. [安装与配置](#安装与配置)
3. [基本使用](#基本使用)
4. [高级功能](#高级功能)
5. [最佳实践](#最佳实践)
6. [故障排除](#故障排除)

## 快速开始

### 系统要求

- **Python**: 3.12 或更高版本
- **内存**: 最少 2GB RAM（推荐 4GB）
- **磁盘**: 至少 500MB 可用空间
- **操作系统**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)

### 快速安装

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/TH-Suite.git
cd TH-Suite

# 2. 安装依赖
poetry install

# 3. 进入MC L10n目录
cd apps/mc_l10n/backend

# 4. 启动服务
poetry run python main.py
```

服务启动后，访问 http://localhost:18000/docs 查看API文档。

### 第一次扫描

```python
# 使用Python客户端
from mc_l10n_facade import MCL10nFacade

facade = MCL10nFacade()

# 扫描你的MOD目录
result = facade.scan_mods(
    path="/path/to/your/minecraft/mods",
    recursive=True,
    auto_extract=True
)

print(f"找到 {result.mods_found} 个MOD")
print(f"发现 {result.translations_found} 个翻译条目")
```

## 安装与配置

### 详细安装步骤

#### 1. 环境准备

```bash
# 安装Python 3.12
# Windows: 从 python.org 下载安装
# macOS: brew install python@3.12
# Linux: sudo apt install python3.12

# 安装Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 验证安装
python --version  # 应该显示 3.12.x
poetry --version  # 应该显示 1.x.x
```

#### 2. 项目设置

```bash
# 克隆项目
git clone https://github.com/yourusername/TH-Suite.git
cd TH-Suite

# 创建虚拟环境
poetry env use python3.12

# 安装依赖
poetry install

# 安装开发依赖（可选）
poetry install --with dev
```

#### 3. 数据库初始化

```bash
cd apps/mc_l10n/backend

# 初始化数据库
poetry run python -c "from container import get_container; c = get_container(); c.initialize()"

# 验证数据库
poetry run python test_architecture.py
```

### 配置文件

创建 `.env` 文件进行配置：

```bash
# apps/mc_l10n/backend/.env

# 数据库配置
DATABASE_PATH=./data/mc_l10n.db
DATABASE_ENCRYPTION_KEY=your-encryption-key-here

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=18000
WORKER_COUNT=4

# 扫描配置
SCAN_BATCH_SIZE=100
SCAN_MAX_WORKERS=4
SCAN_TIMEOUT=300

# 缓存配置
CACHE_TTL=300
CACHE_MAX_SIZE=1000

# Trans-Hub配置
TRANSHUB_API_URL=https://api.trans-hub.cn
TRANSHUB_API_KEY=your-api-key

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/mc_l10n.log
```

## 基本使用

### 1. 扫描MOD

#### 扫描单个文件

```python
from facade.mc_l10n_facade import MCL10nFacade

facade = MCL10nFacade(get_container())

# 扫描单个JAR文件
mod_dto = facade.scan_file(
    "/path/to/twilightforest-1.21.1.jar",
    force=True  # 强制重新扫描
)

print(f"MOD ID: {mod_dto.mod_id}")
print(f"版本: {mod_dto.version}")
```

#### 批量扫描

```python
# 扫描整个目录
result = facade.scan_mods(
    path="/path/to/mods",
    recursive=True,
    auto_extract=True
)

if result.success:
    print(f"成功扫描 {result.scanned_files} 个文件")
    print(f"新增 {result.new_mods} 个MOD")
    print(f"更新 {result.updated_mods} 个MOD")
else:
    print("扫描失败:")
    for error in result.errors:
        print(f"  - {error}")
```

#### 快速预览

```python
# 快速扫描（不保存到数据库）
stats = facade.quick_scan("/path/to/mods")

print(f"MOD总数: {stats['total_mods']}")
print(f"语言: {', '.join(stats['languages'])}")
print(f"预计翻译条目: {stats['estimated_translations']}")
```

### 2. 管理翻译

#### 提交翻译

```python
# 单个MOD翻译
result = facade.translate_mod(
    mod_id="twilightforest",
    language="zh_cn",
    translations={
        "item.twilightforest.naga_scale": "娜迦鳞片",
        "block.twilightforest.castle_brick": "城堡砖块"
    },
    translator="your_username",
    auto_approve=False
)

print(f"翻译进度: {result.progress:.1f}%")
print(f"质量分数: {result.quality_score:.2f}")
```

#### 批量翻译

```python
# 使用术语表批量翻译
from domain.services import Glossary

# 创建术语表
glossary = Glossary()
glossary.add_term("Naga", "娜迦", "zh_cn")
glossary.add_term("Twilight", "暮色", "zh_cn")

# 批量翻译多个MOD
results = facade.batch_translate(
    mod_ids=["twilightforest", "ars_nouveau", "create"],
    language="zh_cn",
    glossary=glossary,
    quality_threshold=0.8
)

for result in results:
    print(f"{result.mod_id}: {result.translated_count} 条已翻译")
```

### 3. 项目管理

#### 创建项目

```python
# 创建翻译项目
project_id = facade.create_project(
    name="ATM10 整合包翻译",
    mod_ids=["mod1", "mod2", "mod3"],
    target_languages=["zh_cn", "zh_tw", "ja_jp"],
    auto_assign=True
)

print(f"项目已创建: {project_id}")
```

#### 跟踪进度

```python
# 获取项目状态
status = facade.get_project_status(project_id)

print(f"项目: {status['name']}")
print(f"总体进度: {status['progress']:.1f}%")
print(f"状态: {status['status']}")

# 详细统计
stats = status['statistics']
print(f"已翻译: {stats['translated']}/{stats['total']}")
print(f"已批准: {stats['approved']}")
print(f"待审核: {stats['pending']}")
```

### 4. 质量管理

#### 质量检查

```python
# 检查翻译质量
report = facade.check_quality(
    mod_id="twilightforest",
    language="zh_cn"
)

print(f"平均质量: {report['average_quality']:.2f}")
print(f"批准率: {report['approval_rate']:.1f}%")

if report['needs_review']:
    print(f"有 {report['pending']} 条翻译需要审核")
```

#### 批准翻译

```python
# 批准高质量翻译
from application.services import ReviewService

review_service = container.get_service('review')

review_service.bulk_approve(
    mod_id="twilightforest",
    language="zh_cn",
    min_quality=0.9,
    reviewer="admin"
)
```

## 高级功能

### 1. 自定义扫描器

```python
from infrastructure.minecraft.base_scanner import BaseScanner

class CustomScanner(BaseScanner):
    """自定义MOD扫描器"""
    
    def can_handle(self, file_path: str) -> bool:
        # 判断是否能处理此文件
        return file_path.endswith('.custom')
    
    def scan(self, file_path: str):
        # 实现扫描逻辑
        pass

# 注册扫描器
container.register_scanner(CustomScanner())
```

### 2. 事件监听

```python
from infrastructure.event_bus import get_event_bus
from domain.events import ModScannedEvent

event_bus = get_event_bus()

# 监听扫描完成事件
@event_bus.subscribe(ModScannedEvent)
def on_mod_scanned(event: ModScannedEvent):
    print(f"MOD {event.mod_id} 扫描完成")
    print(f"发现 {event.translation_count} 个翻译")
    
    # 自动触发翻译
    if event.translation_count > 0:
        # 你的翻译逻辑
        pass
```

### 3. 批处理优化

```python
from infrastructure.batch_processor import BatchProcessor

# 创建批处理器
processor = BatchProcessor(
    batch_size=50,
    max_workers=8
)

# 处理大量文件
def process_mod(mod_path):
    # 处理逻辑
    return scan_result

# 批量处理
results = processor.process(
    items=mod_paths,
    processor=process_mod,
    progress_callback=lambda cur, total: 
        print(f"进度: {cur}/{total}")
)

print(f"成功率: {results.success_rate:.1%}")
```

### 4. 缓存管理

```python
from infrastructure.cache.cache_decorator import cache, get_cache_manager

# 使用缓存装饰器
@cache(ttl=600)  # 10分钟缓存
def expensive_operation(param):
    # 耗时操作
    return result

# 管理缓存
cache_manager = get_cache_manager()

# 查看缓存统计
stats = cache_manager.get_stats()
print(f"缓存命中率: {stats['hit_rate']:.1%}")

# 清空缓存
cache_manager.clear()
```

### 5. 数据库连接池

```python
from infrastructure.db.connection_pool import get_connection_pool

# 获取连接池
pool = get_connection_pool()

# 使用连接
with pool.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mods")
    count = cursor.fetchone()[0]
    print(f"MOD总数: {count}")

# 查看连接池统计
stats = pool.get_stats()
print(f"活动连接: {stats['active_connections']}")
print(f"连接复用率: {stats['reuse_rate']:.1%}")
```

## 最佳实践

### 1. 性能优化

#### 使用批处理
```python
# 好的做法 ✓
results = facade.batch_translate(mod_ids, language)

# 避免的做法 ✗
for mod_id in mod_ids:
    facade.translate_mod(mod_id, language, ...)
```

#### 启用缓存
```python
# 使用缓存的快速扫描
stats = facade.quick_scan(path)  # 5分钟缓存

# 对于频繁访问的数据
@cache_5min
def get_mod_stats(mod_id):
    return calculate_stats(mod_id)
```

#### 异步处理
```python
import asyncio

async def process_mods_async():
    tasks = []
    for mod_path in mod_paths:
        task = scan_mod_async(mod_path)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 2. 错误处理

```python
from contextlib import contextmanager

@contextmanager
def safe_operation():
    try:
        yield
    except ValidationError as e:
        logger.warning(f"验证失败: {e}")
        # 处理验证错误
    except DatabaseError as e:
        logger.error(f"数据库错误: {e}")
        # 处理数据库错误
    except Exception as e:
        logger.critical(f"未知错误: {e}")
        # 处理其他错误
        raise

# 使用
with safe_operation():
    result = facade.scan_mods(path)
```

### 3. 日志记录

```python
import structlog

logger = structlog.get_logger()

# 结构化日志
logger.info(
    "scan_completed",
    mod_id=mod_id,
    duration=duration,
    translation_count=count
)

# 性能监控
with logger.contextvars.bind(operation="batch_translate"):
    start = time.time()
    result = batch_translate(...)
    logger.info("performance", duration=time.time() - start)
```

### 4. 测试策略

```python
import pytest

# 单元测试
def test_mod_creation():
    mod = Mod.create(
        mod_id="test",
        name="Test Mod",
        version="1.0.0",
        file_path="/test.jar"
    )
    assert mod.mod_id == ModId("test")

# 集成测试
def test_scan_workflow(facade, tmp_path):
    # 创建测试文件
    test_file = tmp_path / "test.jar"
    test_file.write_bytes(b"fake jar")
    
    # 执行扫描
    result = facade.scan_mods(str(tmp_path))
    assert result.success

# 性能测试
@pytest.mark.benchmark
def test_batch_performance(benchmark):
    result = benchmark(process_batch, large_dataset)
    assert result.duration < 10  # 秒
```

## 故障排除

### 常见问题

#### 1. 数据库锁定错误

**问题**: `sqlite3.OperationalError: database is locked`

**解决方案**:
```python
# 使用连接池避免锁定
from infrastructure.db.connection_pool import ConnectionPool

pool = ConnectionPool(
    database_path="./data/mc_l10n.db",
    max_connections=10,
    connection_timeout=30
)
```

#### 2. 内存不足

**问题**: 处理大量MOD时内存不足

**解决方案**:
```python
# 使用批处理和流式处理
processor = BatchProcessor(
    batch_size=20,  # 减小批次大小
    max_workers=2   # 减少并发数
)

# 或使用生成器
def scan_mods_stream(directory):
    for mod_path in Path(directory).glob("*.jar"):
        yield scan_single_mod(mod_path)
```

#### 3. 扫描速度慢

**问题**: 扫描大型MOD包很慢

**解决方案**:
```python
# 1. 启用多线程扫描
facade = MCL10nFacade(
    batch_size=100,
    max_workers=8  # 增加工作线程
)

# 2. 使用快速扫描进行预览
stats = facade.quick_scan(path)

# 3. 只扫描更改的文件
result = facade.rescan_all(only_changed=True)
```

#### 4. 翻译冲突

**问题**: 多人同时翻译产生冲突

**解决方案**:
```python
# 使用锁定机制
mod = get_mod(mod_id)
mod.lock_translations(user_id)

try:
    # 进行翻译
    translate(...)
finally:
    mod.unlock_translations(user_id)

# 或使用冲突解决策略
from domain.services import ConflictResolutionStrategy

facade.sync_with_server(
    conflict_strategy=ConflictResolutionStrategy.KEEP_HIGHEST_QUALITY
)
```

### 调试技巧

#### 启用详细日志

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 或使用环境变量
# LOG_LEVEL=DEBUG poetry run python main.py
```

#### 性能分析

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 你的代码
result = facade.scan_mods(path)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # 打印前10个最耗时的函数
```

#### 内存分析

```python
from memory_profiler import profile

@profile
def memory_intensive_operation():
    # 你的代码
    pass

# 运行时添加 -m memory_profiler
# python -m memory_profiler your_script.py
```

### 获取帮助

- **文档**: 查看 `/docs/projects/mc-l10n/` 目录
- **API文档**: 访问 http://localhost:18000/docs
- **问题反馈**: 提交到 GitHub Issues
- **社区支持**: 加入 Discord 服务器

## 附录

### 环境变量列表

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_PATH` | `./data/mc_l10n.db` | 数据库路径 |
| `SERVER_PORT` | `18000` | 服务器端口 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `CACHE_TTL` | `300` | 缓存时间(秒) |
| `SCAN_BATCH_SIZE` | `100` | 扫描批次大小 |
| `MAX_WORKERS` | `4` | 最大工作线程 |

### 命令行工具

```bash
# 扫描命令
poetry run python -m mc_l10n scan /path/to/mods

# 翻译命令
poetry run python -m mc_l10n translate --mod twilightforest --lang zh_cn

# 导出命令
poetry run python -m mc_l10n export --mod twilightforest --format json

# 同步命令
poetry run python -m mc_l10n sync --server https://api.trans-hub.cn
```

### 相关资源

- [Minecraft Wiki - 语言文件格式](https://minecraft.wiki/w/Language)
- [Trans-Hub API 文档](https://docs.trans-hub.cn)
- [Python Poetry 文档](https://python-poetry.org/docs/)
- [FastAPI 文档](https://fastapi.tiangolo.com)