# TH-Suite 项目结构重组计划

## 当前问题

1. **文档分散**
   - 文档分布在多个目录：根目录、docs/、apps/mc_l10n/docs/ 等
   - 存在重复和过时的文档

2. **工具程序重复**
   - 数据库查看工具有多个版本：
     - `apps/mc_l10n/scripts/db_audit.py`
     - `apps/mc_l10n/backend/tools/db_viewer/` (4个不同文件)
     - `tools/db_viewer/` (旧版本)

3. **辅助脚本分散**
   - 初始化脚本分散在不同位置
   - 启动脚本在 scripts/ 目录
   - 没有统一的管理方式

## 建议的新结构

```
TH-Suite/
├── apps/                        # 应用程序
│   ├── mc_l10n/                # Minecraft 本地化工具
│   │   ├── backend/            # 后端代码
│   │   │   ├── src/           # 源代码
│   │   │   └── tests/         # 测试
│   │   └── frontend/          # 前端代码
│   │       ├── src/          # 源代码
│   │       └── tests/        # 测试
│   └── rw_l10n/               # Rusted Warfare 工具
│
├── packages/                   # 共享包
│   ├── core/                  # 核心功能
│   ├── parsers/               # 解析器
│   └── backend-kit/           # 后端工具包
│
├── tools/                      # 开发和管理工具（统一位置）
│   ├── database/              # 数据库工具
│   │   ├── viewer/           # 数据库查看器（合并版本）
│   │   ├── migrations/       # 数据库迁移脚本
│   │   └── init/            # 初始化脚本
│   ├── scripts/               # 辅助脚本
│   │   ├── start/           # 启动脚本
│   │   ├── build/           # 构建脚本
│   │   └── deploy/          # 部署脚本
│   └── dev/                  # 开发工具
│       ├── debug/           # 调试工具
│       └── test/            # 测试工具
│
├── docs/                       # 统一文档目录
│   ├── README.md              # 项目主文档
│   ├── architecture/          # 架构文档
│   │   ├── overview.md
│   │   └── design-patterns.md
│   ├── api/                  # API文档
│   │   └── rest-api.md
│   ├── guides/               # 使用指南
│   │   ├── getting-started.md
│   │   ├── development.md
│   │   └── deployment.md
│   └── projects/             # 子项目文档
│       ├── mc-l10n/
│       └── rw-studio/
│
├── tests/                     # 端到端测试
│   └── e2e/
│
├── .github/                   # GitHub 相关
│   ├── workflows/            # CI/CD
│   └── ISSUE_TEMPLATE/
│
├── Taskfile.yml              # 任务定义
├── pyproject.toml            # Python 配置
├── package.json              # Node.js 配置
├── CLAUDE.md                 # AI 助手指南
└── README.md                 # 项目介绍
```

## 重组步骤

### 第一步：整理文档

1. 将所有文档移动到 `docs/` 目录
2. 删除重复的文档
3. 更新过时的内容
4. 创建统一的文档索引

### 第二步：合并数据库工具

1. 分析各版本数据库查看工具的功能
2. 整合最佳功能到一个统一版本
3. 移动到 `tools/database/viewer/`
4. 删除旧版本

### 第三步：整理辅助脚本

1. 将所有脚本移动到 `tools/scripts/`
2. 按功能分类（启动、构建、部署）
3. 更新脚本路径引用

### 第四步：清理冗余文件

1. 删除临时文件
2. 删除测试产生的文件
3. 清理缓存目录

## 数据库工具整合方案

### 需要合并的工具
1. `db_audit.py` - 基础审查功能
2. `db_web_viewer.py` - Web界面
3. `db_web_advanced.py` - 高级Web界面
4. `view_database.py` - 命令行查看
5. `view_db_simple.py` - 简单查看

### 整合后的工具
- **mc-db-manager** - 统一的数据库管理工具
  - Web界面（包含所有高级功能）
  - 命令行界面
  - API接口
  - 数据导出功能
  - 统计分析功能

## 优先级

1. **高优先级**
   - 整理文档（影响开发效率）
   - 合并数据库工具（当前有冲突）

2. **中优先级**
   - 整理脚本
   - 更新配置文件

3. **低优先级**
   - 清理临时文件
   - 优化目录结构

## 预期效果

- **提高可维护性**：清晰的目录结构
- **减少重复**：统一的工具和文档
- **提升开发效率**：快速找到需要的文件
- **更好的协作**：清晰的项目组织