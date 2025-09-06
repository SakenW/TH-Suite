# MC L10n 数据库模块

本模块提供MC L10n客户端的完整本地数据库功能，包括扫描缓存、离线工作、数据同步等。

## 📋 功能概览

### 核心功能
- **本地数据库管理** - SQLite数据库的初始化和管理
- **MOD扫描服务** - 扫描和分析Minecraft MOD文件
- **缓存机制** - 智能缓存扫描结果，提高性能
- **离线变更跟踪** - 记录离线状态下的所有数据变更
- **数据同步** - 与Trans-Hub服务器双向同步数据
- **API接口** - 提供RESTful API接口访问数据

## 🚀 快速开始

### 1. 初始化数据库

```bash
# 初始化新数据库
python database/init_local_db.py

# 重置数据库（删除旧数据）
python database/init_local_db.py --reset
```

### 2. 扫描MOD文件

```bash
# 扫描单个JAR文件
python database/scan_service.py /path/to/mod.jar

# 扫描整个目录
python database/scan_service.py /path/to/mods/directory
```

### 3. 使用CLI工具

```bash
# 查看帮助
python database/db_cli.py --help

# 初始化数据库
python database/db_cli.py init

# 扫描MOD
python database/db_cli.py scan /path/to/mods

# 查看统计
python database/db_cli.py stats

# 列出MOD
python database/db_cli.py mods

# 同步数据
python database/db_cli.py sync --type mods --direction upload
```

## 📁 文件结构

```
database/
├── __init__.py                 # 模块入口
├── init_local_db.py           # 数据库初始化脚本
├── local_database_manager.py  # 本地数据库管理器
├── scan_service.py            # MOD扫描服务
├── sync_service.py            # 数据同步服务
├── offline_tracker.py         # 离线变更跟踪器
├── database_api.py            # FastAPI接口定义
├── db_cli.py                  # CLI命令行工具
└── README.md                  # 本文档
```

## 💾 数据库架构

### 核心表

1. **mod_discoveries** - MOD发现记录
   - 存储扫描发现的MOD信息
   - 包含元数据、版本、语言统计等

2. **language_file_cache** - 语言文件缓存
   - 缓存提取的语言文件
   - 支持JSON和Properties格式

3. **translation_entry_cache** - 翻译条目缓存
   - 存储具体的翻译键值对
   - 跟踪翻译状态

4. **offline_changes** - 离线变更跟踪
   - 记录所有离线状态下的数据变更
   - 支持冲突解决策略

5. **work_queue** - 工作队列
   - 管理后台任务
   - 支持优先级和重试机制

## 🔧 API接口

### FastAPI集成

```python
from fastapi import FastAPI
from database import database_router

app = FastAPI()
app.include_router(database_router)
```

### 主要端点

- `GET /api/database/statistics` - 获取统计信息
- `GET /api/database/mods` - 获取MOD列表
- `GET /api/database/mods/{mod_id}` - 获取MOD详情
- `POST /api/database/scan` - 扫描目录或文件
- `POST /api/database/sync` - 同步数据
- `GET /api/database/changes/summary` - 获取变更摘要

## 🔄 数据同步

### 同步方向

- **上传（Upload）** - 本地数据上传到服务器
- **下载（Download）** - 从服务器下载数据
- **双向（Bidirectional）** - 双向同步，自动解决冲突

### 冲突解决策略

- `client_wins` - 客户端数据优先
- `server_wins` - 服务器数据优先
- `newest_wins` - 最新数据优先
- `manual` - 手动解决冲突

### 使用示例

```python
import asyncio
from database import DataSyncService, SyncDirection

async def sync_data():
    service = DataSyncService()
    await service.initialize()
    
    # 同步项目
    await service.sync_projects(SyncDirection.BIDIRECTIONAL)
    
    # 同步MOD发现
    await service.sync_mod_discoveries()
    
    # 同步翻译
    await service.sync_translations('project-id')
    
    await service.close()

asyncio.run(sync_data())
```

## 📊 离线变更跟踪

### 自动跟踪

数据库触发器会自动跟踪以下变更：
- 翻译条目更新
- 项目创建和更新
- MOD信息变更

### 手动跟踪

```python
from database import OfflineChangeTracker, EntityType, ChangeOperation

tracker = OfflineChangeTracker()

# 跟踪单个变更
tracker.track_change(
    EntityType.TRANSLATION,
    "entry-id",
    ChangeOperation.UPDATE,
    {"key": "value"}
)

# 批量跟踪
changes = [
    {
        'entity_type': 'project',
        'entity_id': 'project-id',
        'operation': 'create',
        'change_data': {'name': '项目名'}
    }
]
tracker.batch_track_changes(changes)
```

## 🧹 缓存管理

### TTL设置

缓存默认24小时过期，可通过设置修改：

```bash
python database/db_cli.py set-config cache_ttl 86400
```

### 清理过期缓存

```bash
python database/db_cli.py cleanup
```

或使用API：

```python
from database import ScanDatabaseService

service = ScanDatabaseService()
service.cleanup_expired_cache()
```

## 📈 性能优化

1. **智能缓存** - 基于文件哈希的缓存机制
2. **批量操作** - 支持批量插入和更新
3. **索引优化** - 21个索引提升查询性能
4. **连接池** - 支持多线程安全访问
5. **异步IO** - 同步服务使用异步操作

## 🛠️ 开发指南

### 扩展服务

```python
from database import LocalDatabaseManager

class CustomService(LocalDatabaseManager):
    def custom_method(self):
        # 自定义逻辑
        pass
```

### 添加新表

1. 在 `init_local_db.py` 中添加表定义
2. 创建相应的索引
3. 更新服务类添加操作方法

## 📝 最佳实践

1. **定期清理缓存** - 避免数据库过大
2. **使用事务** - 保证数据一致性
3. **启用自动同步** - 保持数据最新
4. **监控工作队列** - 及时处理失败任务
5. **导出重要变更** - 定期备份离线变更

## 🐛 故障排除

### 常见问题

1. **数据库锁定**
   ```bash
   # 关闭所有连接后重试
   ```

2. **同步失败**
   - 检查网络连接
   - 验证服务器地址
   - 查看同步日志

3. **扫描缓慢**
   - 增加扫描线程数
   - 清理过期缓存
   - 使用SSD存储

## 📚 相关文档

- [数据库架构设计](../../../docs/projects/mc-l10n/technical/database-architecture-v4.md)
- [API文档](../../../docs/projects/mc-l10n/technical/api-documentation.md)
- [同步协议](../../../docs/projects/mc-l10n/technical/sync-protocol.md)