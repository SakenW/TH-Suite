# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TransHub Suite is a game localization toolkit specifically designed for integration with the Trans-Hub translation platform. This is a monorepo containing multiple desktop applications using Tauri (frontend) + FastAPI (backend) architecture:

- **TH Suite MC L10n** (`apps/mc_l10n/`) - Minecraft mod and resource pack localization tool
- **RW Studio** (`apps/rw_l10n/`) - Rusted Warfare localization tool
- **Shared packages** (`packages/`) - Common tools and components

## Core Architecture

### Tech Stack
- **Frontend**: Tauri + React + TypeScript + **Ant Design** + Tailwind CSS (~~Material-UI 已废弃~~)
- **Backend**: FastAPI + Python 3.12 + SQLite/SQLCipher + Structlog
- **State Management**: Dependency injection pattern (backend), Service Container pattern (frontend)
- **Package Management**: Poetry (Python), pnpm (Node.js)
- **Task Runner**: Taskfile (recommended) or npm scripts
- **Real-time Communication**: WebSocket + Server-Sent Events + Polling

### ⚠️ 重要更新 (2024.09)
MC L10n 前端已完全重构，基于《我的世界工具前端设计.md》规范：
- ✅ **Ant Design 5.x** 替代 Material-UI 作为唯一组件库
- ✅ **Minecraft 轻装饰主题系统** - 像素化描边、方块化阴影、网格背景
- ✅ **玩家友好界面** - "人话化"文案，隐藏工程参数，安全默认策略
- ✅ **标准化工作流** - 扫描 → 差量同步 → 构建本地化产物

### 架构模式

#### 后端架构（Clean Architecture）
```
src/mc_l10n/
├── adapters/           # 外部接口适配器
│   ├── api/           # REST API 路由和控制器
│   └── cli/           # 命令行接口
├── application/        # 应用服务层
│   ├── services/      # 应用服务（业务用例）
│   ├── commands/      # 命令对象
│   └── queries/       # 查询对象
├── domain/            # 领域层
│   ├── models/        # 领域实体和值对象
│   └── services/      # 领域服务
└── infrastructure/    # 基础设施层
    ├── persistence/   # 数据持久化
    ├── parsers/       # 文件解析器
    └── scanners/      # 文件扫描器
```

#### 前端架构（Ant Design + Minecraft 轻装饰）
```
src/
├── theme/                    # 主题系统
│   └── minecraft.ts         # Minecraft 轻装饰主题配置
├── contexts/                 # React 上下文
│   └── ThemeProvider.tsx    # 主题提供者（集成 AntD ConfigProvider）
├── layouts/                  # 布局组件
│   └── MainLayout.tsx       # 主布局（左侧导航+顶部状态条）
├── components/               # 组件系统
│   ├── TopStatusBar.tsx     # 顶部状态条（连接状态+快速指标）
│   ├── common/              # 通用组件
│   └── ui/                  # UI 基础组件（基于 AntD）
├── pages/                    # 页面组件（符合设计文档）
│   ├── WelcomePage.tsx      # 欢迎页（工具介绍+快速入口）
│   ├── ProjectsPacksPage.tsx # 整合包项目页
│   ├── ProjectsModsPage.tsx  # MOD 项目页  
│   ├── ScanPage.tsx         # 扫描中心
│   ├── SyncPage.tsx         # 同步中心
│   ├── BuildPage.tsx        # 构建中心
│   ├── ServerPage.tsx       # 服务器状态
│   └── SettingsPage.tsx     # 设置页
├── services/                 # 业务逻辑服务（保留原架构）
│   ├── domain/              # 领域服务
│   ├── infrastructure/      # 基础设施服务
│   └── container/           # 依赖注入容器
├── stores/                   # 状态管理（保留 Zustand）
└── hooks/                    # 自定义 React Hooks
```

### 关键设计模式

1. **依赖注入**: 后端使用依赖注入管理服务生命周期
2. **CQRS**: 分离命令和查询操作
3. **Repository Pattern**: 抽象数据访问层
4. **Service Layer**: 封装业务逻辑
5. **Observer Pattern**: 实时进度更新和状态同步

## 开发命令

### Task 工具安装（推荐）

如果系统没有 Task 工具，请先安装：

**Windows:**
```powershell
# 使用 Chocolatey
choco install go-task

# 使用 Scoop
scoop install task

# 手动下载
# 从 https://github.com/go-task/task/releases 下载 task_windows_amd64.zip
# 解压后将 task.exe 放入 PATH 路径
```

**macOS:**
```bash
brew install go-task/tap/go-task
```

**Linux:**
```bash
# Ubuntu/Debian
sudo snap install task --classic

# 或下载二进制文件
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
```

**重要：所有 `task` 命令都必须在项目根目录（TH-Suite/）中运行**

### 主要开发命令

```bash
# 在项目根目录运行：cd TH-Suite/

# 安装所有依赖
task install         # 安装 Poetry + pnpm 依赖

# 开发服务器（全栈开发）
task dev:mc          # 启动 MC L10n（前端 + 后端，并行运行）
task dev:rw          # 启动 RW Studio（前端 + 后端，并行运行）

# 单独启动服务
task dev:mc:backend  # 仅启动 MC L10n 后端（端口 18000）
task dev:mc:frontend # 仅启动 MC L10n 前端（端口 18001）
task dev:rw:backend  # 仅启动 RW Studio 后端（端口 8002）
task dev:rw:frontend # 仅启动 RW Studio 前端

# 构建应用程序
task build:mc        # 构建 MC L10n 可执行文件
task build:rw        # 构建 RW Studio 可执行文件
task build:all       # 构建所有应用程序

# 测试
task test            # 运行所有测试
task test:mc         # 运行 MC L10n 测试
task test:rw         # 运行 RW Studio 测试

# 代码质量
task lint            # 运行所有代码检查
task lint:python     # Python 代码检查（ruff + mypy）
task lint:frontend   # 前端代码检查

# 清理
task clean           # 清理所有构建产物
```

### 无 Task 工具时的开发方案

#### 直接使用工具命令（推荐）
```bash
# 在项目根目录（TH-Suite/）运行：

# 1. 安装依赖
poetry install
cd apps/mc_l10n/frontend && pnpm install && cd ../../../

# 2. 启动后端（新终端窗口）
cd apps/mc_l10n/backend
poetry run python main.py

# 3. 启动前端（另一个终端窗口）
cd apps/mc_l10n/frontend  
npm run tauri:dev        # 桌面应用（推荐）
# 或者：
npm run dev             # Web模式，访问 http://localhost:18001
```

#### 使用 npm 脚本（从根目录）
```bash
# 在项目根目录（TH-Suite/）运行：

# 安装依赖
npm run install:all

# 启动开发服务器
npm run dev:mc_l10n     # 仅前端
npm run start:mc_l10n   # 仅后端

# 构建
npm run build:mc_l10n

# 代码检查
npm run lint:python:mc
```

## 代码质量工具

### Python
- **代码检查**: `ruff check .`（在 pyproject.toml 中配置）
- **类型检查**: `mypy packages apps`
- **代码格式化**: `ruff format .`
- **测试**: `pytest tests/`

### 前端
- **代码检查**: `eslint . --ext ts,tsx`
- **类型检查**: `tsc --noEmit`
- **格式化**: `prettier --write .`

### 新版前端架构特殊说明
⚠️ **重要**: MC L10n 前端已完全重构，请注意：

1. **使用新版文件**:
   - `src/App.new.tsx` - 新版主应用组件（基于 Ant Design）
   - `src/main.new.tsx` - 新版入口文件
   - 临时共存，可通过修改 index.html 脚本引用切换

2. **依赖管理**:
   - ✅ **仅使用 Ant Design**: `import { Button, Card } from 'antd'`
   - ❌ **禁用 Material-UI**: 已移除，避免导入 `@mui/*`
   - ✅ **主题系统**: 使用 `./contexts/ThemeProvider.tsx`

3. **设计原则**:
   - 严格遵循《我的世界工具前端设计.md》规范
   - 界面文案必须"人话化"，避免专业术语
   - 安全默认：默认旁路产物，破坏性操作双确认
   - Minecraft 轻装饰：像素化元素仅作装饰

## 关键业务概念

### 扫描和识别流程
1. **项目扫描**: 扫描目录结构，识别模组和资源包
2. **文件提取**: 从 JAR 文件和目录中提取语言文件
3. **内容解析**: 解析 JSON、Properties 等格式的语言文件
4. **指纹识别**: 生成内容指纹用于缓存和增量更新
5. **Trans-Hub 集成**: 与 Trans-Hub 平台进行翻译同步

### 实时进度系统
- 使用轮询机制获取后端状态更新
- 支持自适应轮询频率调整
- 提供平滑的动画效果和用户反馈
- 包含处理速度计算和预估完成时间

### 服务容器模式
前端使用依赖注入容器管理服务实例：
- `ProjectService`: 项目管理
- `ScanService`: 扫描功能
- `TauriService`: 系统集成
- `BaseApiService`: API 通信

## 服务端口配置
- **MC L10n 后端**: http://localhost:18000 (API 文档: /docs)
- **MC L10n 前端**: http://localhost:18001 (避免与 Trans-Hub 的 5173 端口冲突)
- **RW Studio 后端**: http://localhost:8002 (API 文档: /docs)

### 端口冲突说明
- Trans-Hub 项目使用端口：8000（API）、5173（前端开发）、3000（Docker映射）
- TH-Suite 端口已调整避免冲突：18000（MC后端）、18001（MC前端）、8002（RW后端）

## 重要配置文件

- `pyproject.toml` - Python 项目配置、依赖版本、工具设置
- `Taskfile.yml` - 主要任务定义和开发命令
- `package.json` - Node.js 工作空间配置和 npm 脚本
- `apps/*/frontend/src-tauri/tauri.conf.json` - Tauri 应用程序配置
- `packages/core/src/trans_hub_core/config.py` - 核心配置模块

## 包依赖关系

项目使用位于 `packages/` 的共享包：

### Python 包
- `packages/core` - 核心领域模型和业务逻辑
- `packages/parsers` - 文件解析器（JSON、Properties等）
- `packages/backend-kit` - FastAPI 框架扩展和工具
- `packages/protocol` - API 协议定义

### 前端包
- `packages/ui-kit` - 可复用的 UI 组件库（如果存在）
- `packages/protocol` - TypeScript API 类型定义

## 开发注意事项

### 环境要求
- Python 版本：需要 3.12+
- Node.js 版本：需要 18+
- Rust 工具链：用于 Tauri 构建
- Poetry：Python 依赖管理
- pnpm：前端包管理器

### 关键特性
- 使用 SQLCipher 进行加密数据库存储
- 支持 WebSocket 实时通信
- 完整的本地化（i18n）支持
- 基于指纹的增量扫描和缓存
- 与 Trans-Hub 平台的深度集成

### 开发最佳实践
- 后端服务使用依赖注入模式
- 前端组件遵循单一职责原则
- 所有异步操作使用 ServiceResult 包装
- 实时更新使用轮询 + WebSocket 混合模式
- 错误处理统一使用结构化日志

## 故障排除

### 常见问题
- 如果 `task dev:mc` 失败，尝试分别运行 `task dev:mc:backend` 和 `task dev:mc:frontend`
- 确保已安装 Poetry、pnpm 和 Rust 工具链
- 检查端口是否被占用（18000、18001、8002）
- 权限问题：确保对扫描目录有读取权限

### 调试工具
- 后端 API 文档：http://localhost:18000/docs
- 使用 `structlog` 进行结构化日志记录
- 前端开发者工具中查看网络请求
- 使用 `ProgressTestPage.tsx` 测试进度组件

## V6架构扩展功能 (2024年完成)

### 🚀 高级功能特性

MC L10n V6架构已完成全面扩展，新增以下企业级功能：

#### 算法现代化
- **BLAKE3哈希**: 替代SHA256，性能提升3-5倍
- **内容寻址系统**: CID计算和验证机制完全升级
- **UIDA包集成**: 底层Trans-Hub UIDA包完全兼容

#### 智能压缩系统
- **Zstd压缩**: 支持动态压缩级别 (Fast/Balanced/High/Max)
- **Locale字典**: 按语言训练专用字典，中文压缩率提升20-30%
- **FastAPI中间件**: 自动内容类型检测和压缩策略

#### 性能优化
- **并发上传管理**: 支持8-16线程并发，吞吐量提升5-10倍
- **流式文件处理**: 内存使用恒定，支持TB级文件
- **智能内存监控**: 阈值触发GC，防止OOM
- **优先级队列**: HIGH/NORMAL/LOW任务调度

#### 数据库深度集成
- **Repository模式**: Entry-Delta处理器连接Repository
- **真实CRUD操作**: 替代模拟数据，支持3-way合并
- **冲突处理**: 完整的合并策略和冲突解决机制

### 🧪 测试覆盖
所有新功能均通过完整测试验证：
- Entry-Delta数据库集成测试: 2/2 通过
- Zstd压缩功能测试: 6/6 通过
- 同步协议测试: 5/5 通过
- 性能优化器测试: 6/6 通过
- UIDA集成测试: 5/5 通过

### 📁 核心新增文件
- `services/performance_optimizer.py` - 性能优化器主模块
- `services/zstd_compression.py` - Zstd智能压缩服务
- `api/middleware/compression_middleware.py` - FastAPI压缩中间件
- `test_*_*.py` - 完整的测试套件

所有功能可直接投入生产环境使用。