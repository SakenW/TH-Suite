# 🎮 MC L10n (Minecraft本地化) 项目文档

MC L10n 是 TransHub Suite 中专门用于 Minecraft 模组和资源包本地化的工具模块。

## 📋 文档目录

### 🏗️ 架构设计文档

| 文档 | 描述 | 更新日期 |
|------|------|---------|
| [领域模型设计](./architecture/mc-domain-model-design.md) | DDD领域模型设计，包含聚合根、实体、值对象定义 | 2025-08-30 |
| [业务分析](./architecture/mc-business-analysis.md) | MC本地化业务需求分析，用户故事和功能规划 | 2025-08-29 |
| [Minecraft适配器](./architecture/minecraft-adapter-implementation.md) | Minecraft游戏适配器实现细节 | 2025-08-30 |

### 💾 技术规范文档

| 文档 | 描述 | 版本 |
|------|------|------|
| [数据库架构](./technical/database-schema.md) | **DDD架构数据库完整设计** | v2.0.0 |
| [数据库架构v4](./technical/database-architecture-v4.md) | **客户端-服务器分离架构** | v4.0.0 |
| [数据库实现v5](./technical/database-implementation-v5.md) | **完整实现文档** | v5.0.0 |
| [API接口规范](./technical/api-documentation.md) | RESTful API接口文档 | v1.0.0 |
| WebSocket协议 | 实时通信协议规范 | - |

### 🚀 部署运维文档

| 文档 | 描述 |
|------|------|
| [端口配置](./operations/port-configuration.md) | 服务端口配置和管理 |
| [错误日志](./operations/error-logs.md) | 系统错误记录和解决方案 |
| 部署指南 | 生产环境部署说明 |
| 监控配置 | 系统监控和告警配置 |

---

## 🌟 核心特性

### 1. 扫描引擎
- 🔍 **智能识别**: 自动识别JAR文件中的模组信息
- 📦 **增量扫描**: 通过文件哈希检测变更，避免重复处理
- 🚀 **高性能**: 异步并发处理，支持大规模模组包扫描
- 📊 **实时进度**: WebSocket推送扫描进度

### 2. 数据管理
- 💾 **DDD架构**: 清晰的领域边界，业务逻辑分离
- 🔄 **UPSERT机制**: 智能更新，避免数据重复
- 🔐 **数据完整性**: 外键约束、唯一索引保证一致性
- 📈 **性能优化**: 索引优化，毫秒级查询响应

### 3. 翻译管理
- 📝 **多语言支持**: 支持所有Minecraft语言代码
- 🎯 **术语库**: 统一术语翻译管理
- 🧠 **翻译记忆**: 历史翻译复用
- ✅ **质量控制**: 翻译状态追踪和审核流程

---

## 📊 数据库架构概览

### 本地数据库架构 (v5.0)

本地客户端使用SQLite数据库，负责缓存、离线工作和数据同步：

```
本地数据库 (SQLite)
├── 扫描缓存层
│   ├── scan_cache (扫描缓存)
│   ├── mod_discoveries (MOD发现)
│   └── language_file_cache (语言文件缓存)
├── 工作管理层
│   ├── work_queue (工作队列)
│   ├── offline_changes (离线变更)
│   └── file_watch (文件监控)
└── 配置同步层
    ├── local_settings (本地设置)
    ├── local_projects (本地项目)
    └── sync_log (同步日志)
```

### 服务器数据库架构 (Trans-Hub)

服务器端使用PostgreSQL，管理核心业务数据：

```
服务器数据库 (PostgreSQL)
├── 项目管理
│   ├── translation_projects (翻译项目)
│   └── project_mods (项目模组关联)
├── 翻译管理
│   ├── mods (模组主数据)
│   ├── language_files (语言文件)
│   └── translation_entries (翻译条目)
└── 辅助功能
    ├── terminology (术语库)
    ├── translation_memory (翻译记忆)
    └── domain_events (领域事件)
```

### 关键数据流
```
扫描发现 → 模组识别(UPSERT) → 语言提取 → 翻译管理 → 导出同步
```

---

## 🛠️ 技术栈

### 后端技术
- **框架**: FastAPI + Python 3.12
- **数据库**: SQLite + SQLCipher (加密)
- **架构**: DDD (领域驱动设计)
- **异步**: asyncio + 协程
- **日志**: structlog 结构化日志

### 前端技术
- **框架**: React + TypeScript
- **UI库**: Material-UI + Tailwind CSS
- **桌面**: Tauri
- **状态管理**: Service Container Pattern
- **通信**: WebSocket + SSE + Polling

---

## 📈 项目统计

基于最新扫描数据（2025-09-06）：

| 指标 | 数值 |
|------|------|
| 支持的模组数 | 226 |
| 语言文件 | 2,122 |
| 翻译条目总数 | 526,520 |
| 数据库大小 | ~150 MB |
| 扫描速度 | ~10 MODs/秒 |
| 缓存命中率 | >90% |

---

## 🔧 开发指南

### 快速开始
```bash
# 1. 初始化本地数据库
cd apps/mc_l10n/backend
python database/init_local_db.py --reset

# 2. 启动后端服务
poetry run python main.py

# 3. 启动前端开发服务器
cd frontend && npm run tauri:dev
```

### 数据库CLI工具
```bash
# 扫描MOD目录
python database/db_cli.py scan /path/to/mods

# 查看统计信息
python database/db_cli.py stats

# 同步数据
python database/db_cli.py sync --type mods

# 显示离线变更
python database/db_cli.py changes
```

### API调用示例
```javascript
// 获取数据库统计
GET /api/database/statistics

// 扫描MOD目录
POST /api/database/scan
{
  "scan_path": "/path/to/mods",
  "recursive": true,
  "force_rescan": false
}

// 获取MOD列表
GET /api/database/mods?limit=100&offset=0

// 更新翻译
PUT /api/database/translations/{entry_id}
{
  "translated_text": "新翻译",
  "status": "translated"
}

// 同步数据
POST /api/database/sync
{
  "sync_type": "mods",
  "direction": "upload"
}
```

---

## 📝 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v5.0.0 | 2025-09-06 | 实现完整本地数据库系统，包含扫描、缓存、同步、离线跟踪 |
| v4.0.0 | 2025-09-06 | 设计客户端-服务器分离架构 |
| v2.0.0 | 2025-09-05 | 完全重构为DDD架构，实现UPSERT机制 |
| v1.5.0 | 2025-09-04 | 添加实时进度推送 |
| v1.0.0 | 2025-09-01 | 初始版本发布 |

---

## 🤝 贡献指南

欢迎贡献代码和文档改进！请遵循以下流程：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📮 联系方式

- GitHub Issues: [报告问题](https://github.com/transhub/suite/issues)
- 项目Wiki: [查看Wiki](https://github.com/transhub/suite/wiki)
- 开发团队: TransHub Suite Team

---

## 相关链接

- [返回主文档](../../README.md)
- [TransHub Suite 总体架构](../../architecture/overview.md)
- [RW Studio 项目文档](../rw-l10n/README.md)

---

*本文档持续更新中...*