# MC L10n 数据库实现文档 v5.0

**版本**: 5.0.0  
**更新日期**: 2025-09-06  
**状态**: 已实现

## 📋 概述

本文档记录MC L10n客户端本地数据库的完整实现，包括所有模块、服务和API接口。

## 🏗️ 架构实现

### 1. 模块结构

```
apps/mc_l10n/backend/database/
├── __init__.py                 # 模块入口，导出所有公共接口
├── init_local_db.py           # 数据库初始化脚本
├── local_database_manager.py  # 本地数据库管理器
├── scan_service.py            # MOD扫描服务
├── sync_service.py            # 数据同步服务  
├── offline_tracker.py         # 离线变更跟踪器
├── database_api.py            # FastAPI路由接口
├── db_cli.py                  # CLI命令行工具
└── README.md                  # 模块文档
```

### 2. 数据库表结构

#### 核心表（10个）

| 表名 | 用途 | 记录数 |
|------|------|--------|
| scan_cache | 扫描结果缓存 | 动态 |
| mod_discoveries | MOD发现记录 | 226+ |
| language_file_cache | 语言文件缓存 | 2,122+ |
| translation_entry_cache | 翻译条目缓存 | 526,520+ |
| work_queue | 后台任务队列 | 动态 |
| offline_changes | 离线变更跟踪 | 动态 |
| local_settings | 本地配置设置 | 10 |
| local_projects | 本地项目管理 | 1+ |
| file_watch | 文件监控配置 | 动态 |
| sync_log | 同步日志记录 | 动态 |

#### 索引优化（21个）

- 扫描缓存索引 (3个)
- MOD发现索引 (3个)
- 语言文件索引 (2个)
- 翻译条目索引 (3个)
- 工作队列索引 (4个)
- 离线变更索引 (2个)
- 文件监控索引 (2个)
- 同步日志索引 (2个)

#### 视图（4个）

- v_cache_statistics - 缓存统计视图
- v_discovery_summary - MOD发现摘要
- v_queue_status - 队列状态视图
- v_sync_history - 同步历史视图

## 🔧 核心服务实现

### 1. LocalDatabaseManager

**文件**: `local_database_manager.py`

**功能**:
- 本地数据库的完整管理
- 缓存策略实现
- 工作队列管理
- 项目配置管理

**关键方法**:
```python
- initialize_database()      # 初始化数据库
- get_scan_cache()           # 获取扫描缓存
- save_mod_discovery()       # 保存MOD发现
- queue_background_task()    # 添加后台任务
- get_offline_changes()      # 获取离线变更
```

### 2. ScanDatabaseService

**文件**: `scan_service.py`

**功能**:
- MOD文件扫描和分析
- 支持Forge/Fabric/Quilt
- 智能缓存机制
- 多线程并发扫描

**核心特性**:
- 基于文件哈希的缓存检查
- TOML/JSON元数据解析
- 语言文件提取（.json/.lang）
- 批量扫描支持

**性能指标**:
- 扫描速度: ~10 MODs/秒
- 缓存命中率: >90%
- 并发线程: 4

### 3. DataSyncService

**文件**: `sync_service.py`

**功能**:
- 与Trans-Hub服务器同步
- 双向数据同步
- 冲突解决机制
- 自动同步循环

**同步类型**:
- 项目同步 (projects)
- MOD同步 (mods)
- 翻译同步 (translations)

**冲突策略**:
- client_wins - 客户端优先
- server_wins - 服务器优先
- newest_wins - 最新优先
- manual - 手动解决

### 4. OfflineChangeTracker

**文件**: `offline_tracker.py`

**功能**:
- 自动跟踪数据变更
- 触发器驱动
- 导入/导出支持
- 批量操作

**跟踪实体**:
- PROJECT - 项目变更
- MOD - 模组变更
- TRANSLATION - 翻译变更
- TERMINOLOGY - 术语变更
- SETTING - 设置变更

**自动触发器**:
- track_translation_update
- track_project_create
- track_project_update

## 🌐 API接口实现

### FastAPI路由

**文件**: `database_api.py`

#### 统计接口
- `GET /api/database/statistics` - 数据库统计
- `GET /api/database/sync/status` - 同步状态
- `GET /api/database/changes/summary` - 变更摘要

#### MOD管理
- `GET /api/database/mods` - MOD列表
- `GET /api/database/mods/{mod_id}` - MOD详情
- `POST /api/database/scan` - 扫描目录

#### 翻译管理
- `GET /api/database/translations/{mod_id}/{language_code}` - 获取翻译
- `PUT /api/database/translations/{entry_id}` - 更新翻译

#### 项目管理
- `POST /api/database/projects` - 创建项目
- `GET /api/database/settings` - 获取设置
- `PUT /api/database/settings/{key}` - 更新设置

#### 同步操作
- `POST /api/database/sync` - 执行同步
- `GET /api/database/changes/pending` - 待同步变更
- `POST /api/database/cache/cleanup` - 清理缓存

## 🖥️ CLI工具实现

**文件**: `db_cli.py`

### 命令列表

```bash
# 数据库管理
db_cli.py init [--reset]          # 初始化数据库
db_cli.py stats                   # 显示统计信息
db_cli.py cleanup                 # 清理过期缓存

# MOD管理
db_cli.py scan PATH [--recursive] # 扫描MOD
db_cli.py mods [--limit N]        # 列出MOD
db_cli.py mod-detail MOD_ID       # MOD详情

# 同步管理
db_cli.py sync [--type TYPE]      # 同步数据
db_cli.py changes                 # 显示变更
db_cli.py export-changes FILE     # 导出变更
db_cli.py import-changes FILE     # 导入变更

# 设置管理
db_cli.py settings                # 显示设置
db_cli.py set-config KEY VALUE    # 更新设置
```

## 📊 性能优化

### 1. 缓存策略

- **TTL缓存**: 默认24小时过期
- **哈希缓存**: 基于文件MD5
- **内存缓存**: 热点数据缓存
- **增量更新**: 仅更新变化部分

### 2. 查询优化

- **索引覆盖**: 21个精心设计的索引
- **批量操作**: INSERT OR REPLACE批量插入
- **连接池**: 支持多线程访问
- **WAL模式**: 提高并发性能

### 3. 并发处理

- **多线程扫描**: ThreadPoolExecutor(max_workers=4)
- **异步同步**: aiohttp异步IO
- **事务管理**: 上下文管理器保证原子性
- **锁机制**: 避免并发冲突

## 🔄 数据流程

### 扫描流程

```
1. 用户触发扫描
   ↓
2. 检查缓存（file_hash）
   ↓ (缓存未命中)
3. 提取MOD信息
   ↓
4. 解析语言文件
   ↓
5. 保存到数据库
   ↓
6. 更新缓存
```

### 同步流程

```
1. 收集离线变更
   ↓
2. 检测冲突
   ↓
3. 解决冲突（策略）
   ↓
4. 上传到服务器
   ↓
5. 下载服务器更新
   ↓
6. 更新本地数据
   ↓
7. 标记变更已同步
```

## 📈 实际数据统计

基于实际扫描结果：

| 指标 | 数值 |
|------|------|
| 扫描MOD数 | 226 |
| 语言文件数 | 2,122 |
| 翻译条目数 | 526,520 |
| 平均每MOD语言数 | 9.4 |
| 平均每MOD翻译键 | 2,330 |
| 数据库大小 | ~150 MB |
| 扫描速度 | ~10 MODs/秒 |
| 缓存命中率 | >90% |

## 🚀 使用示例

### Python代码集成

```python
from database import (
    LocalDatabaseManager,
    ScanDatabaseService,
    DataSyncService,
    OfflineChangeTracker
)

# 初始化管理器
manager = LocalDatabaseManager("mc_l10n_local.db")
manager.initialize_database()

# 扫描MOD
scanner = ScanDatabaseService()
results = scanner.scan_directory(Path("/path/to/mods"))

# 同步数据
import asyncio
async def sync():
    service = DataSyncService()
    await service.initialize()
    await service.sync_mod_discoveries()
    await service.close()

asyncio.run(sync())

# 跟踪变更
tracker = OfflineChangeTracker()
tracker.track_change(
    EntityType.TRANSLATION,
    "entry-id",
    ChangeOperation.UPDATE,
    {"translated_text": "新翻译"}
)
```

### FastAPI集成

```python
from fastapi import FastAPI
from database import database_router

app = FastAPI(title="MC L10n API")
app.include_router(database_router)

# 现在可以访问:
# http://localhost:8000/api/database/statistics
# http://localhost:8000/docs
```

## 🛡️ 错误处理

### 异常处理

- 所有数据库操作都有try-catch保护
- 事务回滚机制
- 详细的错误日志
- HTTP状态码正确返回

### 数据完整性

- 外键约束 (PRAGMA foreign_keys = ON)
- 唯一性约束
- 触发器验证
- 事务原子性

## 📝 最佳实践

1. **定期维护**
   - 每天清理过期缓存
   - 每周导出离线变更备份
   - 每月分析性能指标

2. **性能调优**
   - 根据实际调整cache_ttl
   - 优化scan_threads数量
   - 监控sync_interval

3. **数据安全**
   - 定期备份数据库
   - 使用事务保证一致性
   - 启用WAL模式

## 🔮 未来优化

1. **性能提升**
   - 实现内存缓存层
   - 优化批量插入算法
   - 添加查询结果缓存

2. **功能增强**
   - 支持更多MOD格式
   - 添加翻译质量评分
   - 实现智能冲突解决

3. **监控完善**
   - 添加性能监控指标
   - 实现实时同步状态
   - 提供数据分析报表

## 📚 相关文档

- [数据库架构设计 v4.0](./database-architecture-v4.md)
- [API接口文档](./api-documentation.md)
- [模块使用指南](../../../apps/mc_l10n/backend/database/README.md)