# 📚 TH-Suite 文档中心

> **TH-Suite v2.0** - Core-First专业适配器，专为Trans-Hub生态系统设计的游戏本地化工具

欢迎访问 TH-Suite 项目文档中心。本文档库包含了项目的完整技术文档、用户指南和开发文档。

## 📖 新文档目录结构 (2025-09-17 重组)

```
docs/
├── specifications/      # 🔧 规格文档 - 项目需求和技术规格
├── design/             # 🎨 设计文档 - UI/UX设计规范
├── architecture/       # 🏗️ 架构文档 - 系统架构设计
├── developer/          # 👨‍💻 开发者文档 - 开发环境和工具
├── reports/archived/   # 📊 历史报告 - 项目开发历程记录
├── projects/           # 🎮 项目文档 (现有)
│   ├── mc-l10n/       # Minecraft本地化工具
│   └── rw-l10n/       # Rusted Warfare本地化工具
├── technical/          # 🔧 技术规范 (现有)
├── user/              # 📘 用户指南 (现有) 
├── deployment/        # 🚀 部署指南 (现有)
└── operations/        # 🔨 运维管理 (现有)
```

## 🗂️ 文档索引

### 🔧 新增规格文档 (Specifications) - **2025-09-17 新增**

| 文档 | 描述 |
|------|------|
| [TH-Suite Core-First适配升级方案](./specifications/TH-Suite_Core-First适配升级方案.md) | **v2.0架构升级完整方案** |
| [TH-Suite修复需求文档](./specifications/TH-Suite_修复需求文档.md) | 系统修复需求规格 |

### 🏗️ 新增架构文档 (Architecture) - **2025-09-17 重组**

| 文档 | 描述 |
|------|------|
| [最优架构总结](./architecture/OPTIMAL_ARCHITECTURE_SUMMARY.md) | 系统架构设计总结 |

### 👨‍💻 新增开发者文档 (Developer) - **2025-09-17 新增**

| 文档 | 描述 |
|------|------|
| [开发者指南](./developer/DEVELOPER_GUIDE.md) | **完整的开发环境设置和最佳实践** |
| [故障排除指南](./developer/TROUBLESHOOTING.md) | 常见问题解决方案 |
| [贡献指南](./developer/CONTRIBUTING.md) | 代码贡献规范和流程 |

### 📊 新增历史报告 (Reports/Archived) - **2025-09-17 归档**

项目开发历程中的重要阶段报告：

| 文档 | 描述 |
|------|------|
| [Phase 2完成报告](./reports/archived/PHASE2_COMPLETION_REPORT.md) | 第二阶段开发总结 |
| [Phase 3完成报告](./reports/archived/PHASE3_COMPLETION_REPORT.md) | 第三阶段开发总结 |
| [React 19兼容性报告](./reports/archived/REACT19_COMPATIBILITY_REPORT.md) | 前端框架升级报告 |
| [重构总结](./reports/archived/REFACTORING_SUMMARY.md) | 架构重构过程总结 |
| [项目结构重构](./reports/archived/PROJECT_STRUCTURE_REFACTOR.md) | 目录结构重构记录 |
| [MC L10n进度报告](./reports/archived/MC-L10N-PROGRESS.md) | Minecraft本地化工具开发进度 |

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

## 🔄 文档重组说明 (2025-09-17)

### ✅ 已完成重组
1. **规格文档迁移**: 将根目录的规格文档移至 `specifications/`
2. **架构文档整理**: 将架构相关文档移至 `architecture/`  
3. **开发者文档集中**: 将开发指南、故障排除等移至 `developer/`
4. **历史报告归档**: 将项目阶段报告移至 `reports/archived/`
5. **索引系统更新**: 更新文档索引以反映新的组织结构

### 📂 新旧目录对应关系
- `TH-Suite_Core-First适配升级方案.md` → `specifications/TH-Suite_Core-First适配升级方案.md`
- `OPTIMAL_ARCHITECTURE_SUMMARY.md` → `architecture/OPTIMAL_ARCHITECTURE_SUMMARY.md`
- `DEVELOPER_GUIDE.md` → `developer/DEVELOPER_GUIDE.md`
- `TROUBLESHOOTING.md` → `developer/TROUBLESHOOTING.md`
- `PHASE*_COMPLETION_REPORT.md` → `reports/archived/PHASE*_COMPLETION_REPORT.md`

## 📝 版本信息

- **文档版本**: 2.0.0 (重组版)
- **重组日期**: 2025-09-17  
- **原始创建**: 2025-09-05
- **维护团队**: TH-Suite Team

---

## 📮 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues
- 项目 Wiki
- 开发者邮箱

---

*本文档持续更新中...*