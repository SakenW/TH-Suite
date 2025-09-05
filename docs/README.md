# 📚 TransHub Suite 文档中心

欢迎访问 TransHub Suite 项目文档中心。本文档库包含了项目的完整技术文档、用户指南和运维手册。

## 📖 文档目录结构

```
docs/
├── projects/         # 具体项目文档
│   ├── mc-l10n/     # Minecraft本地化工具
│   └── rw-l10n/     # Rusted Warfare本地化工具
├── architecture/     # 通用架构设计
├── technical/        # 通用技术规范
├── user/            # 用户使用指南
├── deployment/      # 部署和构建指南
└── operations/      # 运维和管理文档
```

## 🗂️ 文档索引

### 🎮 项目文档 (Projects)

| 项目 | 描述 | 链接 |
|------|------|------|
| **MC L10n** | Minecraft模组本地化工具 | [📁 查看文档](./projects/mc-l10n/README.md) |
| **RW Studio** | Rusted Warfare本地化工具 | [📁 查看文档](./projects/rw-l10n/README.md) |

### 🏗️ 通用架构 (Architecture)

| 文档 | 描述 |
|------|------|
| [架构概览](./architecture/overview.md) | TransHub Suite整体架构设计 |
| [架构设计 v2.0](./architecture/architecture-design-v2.0.0.md) | 详细的架构设计文档 |
| [需求文档](./architecture/requirements.md) | 产品需求规格说明 |

### 🔧 技术规范 (Technical)

| 文档 | 描述 |
|------|------|
| [API文档](./technical/api-documentation.md) | 通用REST API接口规范 |

### 📘 用户指南 (User)

| 文档 | 描述 |
|------|------|
| [使用指南](./user/usage-guide.md) | 用户操作手册 |

### 🚀 部署指南 (Deployment)

| 文档 | 描述 |
|------|------|
| [Tauri构建指南](./deployment/build-guide-tauri.md) | Tauri桌面应用构建说明 |

### 🔨 运维管理 (Operations)

| 文档 | 描述 |
|------|------|
| [端口配置](./operations/port-configuration.md) | 服务端口配置管理 |
| [错误日志](./operations/error-logs.md) | 系统错误日志记录 |
| [开发笔记](./operations/development-notes.md) | 开发过程记录 |
| [待办事项](./operations/todo.md) | 项目待办列表 |

---

## 🌟 核心文档推荐

### 新手入门
1. 📖 [使用指南](./user/usage-guide.md) - 了解如何使用系统
2. 🏗️ [架构概览](./architecture/overview.md) - 理解系统设计
3. 🔧 [API文档](./technical/api-documentation.md) - 接口调用说明

### 开发者必读
1. 💾 [数据库架构](./technical/database-schema.md) - **DDD架构数据库设计**
2. 📐 [领域模型设计](./architecture/mc-domain-model-design.md) - 核心业务模型
3. 🚀 [构建指南](./deployment/build-guide-tauri.md) - 本地开发环境搭建

### 运维人员
1. 🔌 [端口配置](./operations/port-configuration.md) - 服务端口管理
2. 📝 [错误日志](./operations/error-logs.md) - 故障排查指南

---

## 📊 数据库架构亮点

最新的数据库采用 **DDD (Domain-Driven Design)** 架构设计，具有以下特点：

### ✨ 核心特性
- **聚合根设计**: 清晰的领域边界（翻译项目、模组、翻译条目）
- **UPSERT支持**: 避免数据重复，支持增量更新
- **完整性约束**: 外键关联、唯一索引保证数据一致性
- **性能优化**: 合理的索引设计，支持百万级数据查询

### 📋 核心数据表
1. **translation_projects** - 翻译项目管理
2. **mods** - 模组信息存储（唯一性约束）
3. **language_files** - 语言文件管理
4. **translation_entries** - 翻译条目存储
5. **terminology** - 术语库
6. **translation_memory** - 翻译记忆库

### 🔄 数据流程
```
扫描 → 模组识别 → 语言提取 → 翻译管理 → 导出同步
```

详细信息请查看 [数据库架构文档](./technical/database-schema.md)

---

## 🛠️ 文档维护

### 文档规范
- 使用 Markdown 格式
- 包含目录结构
- 提供代码示例
- 保持版本更新

### 命名规范
- 使用小写字母和连字符
- 避免空格和特殊字符
- 保持简洁明了

### 贡献指南
欢迎提交文档改进建议和修正。请遵循以下流程：
1. Fork 项目
2. 创建文档分支
3. 提交 Pull Request

---

## 📝 版本信息

- **文档版本**: 2.0.0
- **更新日期**: 2025-09-05
- **维护团队**: TransHub Suite Team

---

## 📮 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues
- 项目 Wiki
- 开发者邮箱

---

*本文档持续更新中...*