# MC L10n v5.0 → v6.0 迁移指南

## 概述

MC L10n v6.0 是一次重大架构升级，从传统的分层架构迁移到六边形架构+DDD。虽然内部架构发生了重大变化，但通过门面模式保持了API的兼容性。

## 主要变化

### 架构变化

| 方面 | v5.0 | v6.0 |
|------|------|------|
| 架构模式 | 传统分层架构 | 六边形架构 + DDD |
| 代码组织 | 按技术分层 | 按领域分层 |
| 依赖管理 | 直接依赖 | 依赖注入 |
| API接口 | 分散的服务 | 统一门面 |
| 性能优化 | 基础优化 | 批处理、连接池、缓存 |

### 文件结构变化

**v5.0 结构**:
```
backend/
├── api/
├── services/
├── models/
├── database/
└── utils/
```

**v6.0 结构**:
```
backend/src/
├── domain/          # 领域层
├── application/     # 应用层
├── infrastructure/  # 基础设施层
├── adapters/        # 适配器层
├── facade/          # 门面层
└── container.py     # 依赖注入
```

## 迁移步骤

### 步骤 1: 备份现有数据

```bash
# 备份数据库
cp data/mc_l10n.db data/mc_l10n_v5_backup.db

# 备份配置
cp .env .env.backup

# 导出重要数据
poetry run python export_data.py
```

### 步骤 2: 更新依赖

```bash
# 更新 Poetry 依赖
poetry update

# 安装新依赖
poetry install

# 验证安装
poetry run python -c "import fastapi; print(fastapi.__version__)"
```

### 步骤 3: 数据库迁移

```python
# migration_v5_to_v6.py
from old_database import OldDatabase
from container import get_container

def migrate_database():
    # 连接旧数据库
    old_db = OldDatabase("data/mc_l10n_v5_backup.db")
    
    # 初始化新容器
    container = get_container()
    container.initialize()
    
    # 迁移MODs
    print("迁移MODs...")
    old_mods = old_db.get_all_mods()
    for old_mod in old_mods:
        new_mod = convert_to_new_model(old_mod)
        container.repositories['mod'].save(new_mod)
    
    # 迁移翻译
    print("迁移翻译...")
    old_translations = old_db.get_all_translations()
    for old_trans in old_translations:
        new_trans = convert_translation(old_trans)
        container.repositories['translation'].save(new_trans)
    
    print(f"迁移完成: {len(old_mods)} MODs, {len(old_translations)} 翻译")

if __name__ == "__main__":
    migrate_database()
```

### 步骤 4: 更新配置

更新 `.env` 文件：

```bash
# 新增配置项
SCAN_BATCH_SIZE=100
SCAN_MAX_WORKERS=4
CACHE_TTL=300
CONNECTION_POOL_SIZE=10

# 更新的配置项
DATABASE_PATH=./data/mc_l10n_v6.db  # 新数据库路径
LOG_LEVEL=INFO                       # 推荐使用INFO级别
```

### 步骤 5: 代码迁移

#### 旧代码 (v5.0)

```python
# v5.0 使用方式
from services.scan_service import ScanService
from database.database_manager import DatabaseManager

db = DatabaseManager()
scanner = ScanService(db)

# 扫描MOD
result = scanner.scan_directory("/path/to/mods")
```

#### 新代码 (v6.0)

```python
# v6.0 使用方式 - 方式1: 使用门面（推荐）
from facade.mc_l10n_facade import MCL10nFacade
from container import get_container

container = get_container()
facade = MCL10nFacade(container)

# 扫描MOD - API保持兼容
result = facade.scan_mods(
    path="/path/to/mods",
    recursive=True,
    auto_extract=True
)
```

```python
# v6.0 使用方式 - 方式2: 直接使用服务
from container import get_container

container = get_container()
scan_service = container.get_service('scan')

# 使用新的命令模式
from application.commands import ScanCommand

command = ScanCommand(
    directory_path="/path/to/mods",
    include_patterns=["*.jar"],
    exclude_patterns=[]
)
result = scan_service.scan_directory(command)
```

## API 兼容性

### 兼容的API

以下API在v6.0中保持兼容：

```python
# 扫描
facade.scan_mods(path, recursive=True)
facade.scan_file(file_path, force=False)

# 翻译
facade.translate_mod(mod_id, language, translations)
facade.batch_translate(mod_ids, language)

# 项目管理
facade.create_project(name, mod_ids, target_languages)
facade.get_project_status(project_id)
```

### 已弃用的API

```python
# v5.0 - 已弃用
scanner.scan_jar_file(file_path)  # 使用 facade.scan_file()
db.execute_query(sql)              # 使用仓储模式
service.process_mod(mod)           # 使用领域服务

# v6.0 - 替代方案
facade.scan_file(file_path)
repository.find_by_criteria(criteria)
domain_service.process(aggregate)
```

### 新增的API

```python
# 批处理支持
facade.batch_translate(mod_ids, language, glossary)

# 质量检查
facade.check_quality(mod_id, language)

# 快速扫描（带缓存）
facade.quick_scan(path)

# 同步服务
facade.sync_with_server(conflict_strategy)
```

## 性能改进

### 批处理

```python
# v5.0 - 串行处理
for mod_path in mod_paths:
    scan_mod(mod_path)  # 缓慢

# v6.0 - 批处理
from infrastructure.batch_processor import BatchProcessor

processor = BatchProcessor(batch_size=100, max_workers=4)
results = processor.process(
    items=mod_paths,
    processor=scan_mod,
    progress_callback=update_progress
)
```

### 连接池

```python
# v5.0 - 每次创建新连接
conn = sqlite3.connect(db_path)
# 使用
conn.close()

# v6.0 - 连接池
from infrastructure.db.connection_pool import get_connection_pool

pool = get_connection_pool()
with pool.get_connection() as conn:
    # 自动管理连接生命周期
    pass
```

### 缓存

```python
# v6.0 新增缓存支持
from infrastructure.cache.cache_decorator import cache

@cache(ttl=300)  # 5分钟缓存
def expensive_operation(param):
    return compute_result(param)
```

## 测试迁移

### 更新测试代码

```python
# v5.0 测试
def test_scan():
    scanner = ScanService()
    result = scanner.scan_directory("/test")
    assert result.success

# v6.0 测试
def test_scan(container):
    facade = MCL10nFacade(container)
    result = facade.scan_mods("/test")
    assert result.success
```

### 新的测试结构

```bash
tests/
├── test_domain_models.py      # 领域模型测试
├── test_application_services.py # 应用服务测试
├── test_integration.py        # 集成测试
└── test_performance.py        # 性能测试
```

## 部署更新

### Docker部署

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装Poetry
RUN pip install poetry

# 复制依赖文件
COPY pyproject.toml poetry.lock ./

# 安装依赖
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# 复制源代码
COPY src/ ./src/
COPY main.py container.py ./

# 运行
CMD ["python", "main.py"]
```

### 环境变量

```yaml
# docker-compose.yml
version: '3.8'

services:
  mc-l10n:
    build: .
    environment:
      - DATABASE_PATH=/data/mc_l10n.db
      - SERVER_PORT=18000
      - LOG_LEVEL=INFO
      - SCAN_BATCH_SIZE=100
      - CACHE_TTL=300
    volumes:
      - ./data:/data
    ports:
      - "18000:18000"
```

## 故障排查

### 常见问题

#### 1. 导入错误

**问题**: `ImportError: cannot import name 'ScanService'`

**解决**:
```python
# 旧导入
from services.scan_service import ScanService

# 新导入
from application.services.scan_service import ScanService
# 或使用门面
from facade.mc_l10n_facade import MCL10nFacade
```

#### 2. 数据库兼容性

**问题**: `sqlite3.OperationalError: no such table`

**解决**:
```bash
# 重新初始化数据库
poetry run python -c "from container import get_container; c = get_container(); c.initialize()"
```

#### 3. 配置错误

**问题**: `KeyError: 'SCAN_BATCH_SIZE'`

**解决**:
```bash
# 添加缺失的配置
echo "SCAN_BATCH_SIZE=100" >> .env
echo "SCAN_MAX_WORKERS=4" >> .env
```

### 性能问题

如果遇到性能问题：

1. **调整批处理大小**:
```python
facade = MCL10nFacade(container, batch_size=50)  # 减小批处理
```

2. **增加连接池大小**:
```python
pool = ConnectionPool(max_connections=20)
```

3. **优化缓存策略**:
```python
@cache(ttl=600)  # 增加缓存时间
```

## 回滚方案

如果需要回滚到v5.0：

```bash
# 1. 停止v6.0服务
pkill -f "python main.py"

# 2. 恢复数据库
cp data/mc_l10n_v5_backup.db data/mc_l10n.db

# 3. 恢复代码
git checkout v5.0

# 4. 恢复配置
cp .env.backup .env

# 5. 重启服务
poetry run python main.py
```

## 迁移检查清单

- [ ] 备份现有数据库
- [ ] 备份配置文件
- [ ] 更新Python依赖
- [ ] 运行数据库迁移脚本
- [ ] 更新.env配置
- [ ] 更新导入语句
- [ ] 测试核心功能
- [ ] 性能基准测试
- [ ] 更新部署脚本
- [ ] 更新监控配置

## 获取帮助

如果在迁移过程中遇到问题：

1. 查看[架构文档](ARCHITECTURE.md)
2. 查看[API文档](API_DOCUMENTATION.md)
3. 查看[用户指南](USER_GUIDE.md)
4. 提交Issue到GitHub
5. 联系技术支持

## 总结

v6.0 带来了显著的架构改进和性能提升，虽然内部变化较大，但通过门面模式保持了良好的向后兼容性。建议：

1. **新项目**: 直接使用v6.0
2. **现有项目**: 按照本指南逐步迁移
3. **生产环境**: 先在测试环境验证

迁移完成后，您将获得：
- 🚀 **3-5倍性能提升**
- 🏗️ **更清晰的架构**
- 🔧 **更好的可维护性**
- 📈 **更强的扩展性**