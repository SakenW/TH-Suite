# TransHub Suite

> 🌐 **T**rans-**H**ub Tools - 接入 Trans-Hub 项目的我的世界本地化本地运行工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Tauri](https://img.shields.io/badge/Tauri-1.5+-orange.svg)](https://tauri.app/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red.svg)](https://fastapi.tiangolo.com/)

## 📖 项目简介

TransHub Suite 是一个专门接入 [Trans-Hub](https://trans-hub.net) 项目的游戏本地化工具套件。基于 Tauri + FastAPI 架构，为游戏玩家和开发者提供专业的本地化管理解决方案。通过与 Trans-Hub 云端翻译平台的深度集成，实现自动提取、检测、翻译、回写的完整本地化工作流程。

当前包含的应用模块：

- **🎮 TH Suite MC L10n** - Minecraft 本地化套件（主要功能）
- **🏠 RW Studio** - Rusted Warfare 本地化工具（扩展功能）

## ✨ 核心特性

### 🏗️ 架构特点
- **Clean Architecture**: 领域驱动设计，业务逻辑与技术细节分离
- **双层数据模型**: Artifact/Container 架构，支持灵活的物理/逻辑映射
- **内容寻址存储**: 基于 SHA256 的 Blob 去重系统，大幅减少存储空间
- **Minecraft 主题 UI**: 完全仿真的 MC 风格界面，包括像素渲染、3D 边框、附魔效果
- **实时进度系统**: WebSocket + 轮询混合模式，提供流畅的实时反馈
- **全链路追踪**: 分布式链路追踪系统，完整的操作可观测性

### 🔄 自动化翻译工作流程
- **智能提取**: 自动提取整合包或模组中的可翻译文本
- **在线检测**: 检测 Trans-Hub 数据库中是否存在对应翻译
- **自动翻译**: 不存在的文本自动写入数据库，由 TH 进行翻译
- **本地同步**: 翻译完成后自动拉回本地，写入相应文件
- **版本管理**: 支持翻译版本控制和增量更新

### 🎮 TH Suite MC L10n 核心功能

#### 📦 内容管理
- **Artifact/Container 双层架构**: 物理载体与逻辑容器分离，灵活管理复杂结构
- **Blob 去重存储**: SHA256 哈希内容寻址，相同内容仅存储一次
- **增量扫描**: 基于指纹的智能缓存，仅处理变更部分
- **多格式支持**: JSON、Properties、YAML、TOML 等格式自动识别

#### 🔧 补丁系统
- **多种合并策略**: OVERLAY（覆盖）、REPLACE（替换）、MERGE（合并）、CREATE_IF_MISSING（按需创建）
- **冲突检测**: 自动识别并报告补丁冲突
- **版本控制**: 补丁集版本管理，支持回滚和历史追踪
- **数字签名**: 补丁内容签名验证，确保内容完整性

#### ✅ 质量保证
- **占位符验证**: 检查翻译中占位符一致性（%s、{0} 等）
- **颜色代码检查**: MC 颜色代码（§）完整性验证
- **长度比例控制**: 翻译文本长度合理性检查
- **格式化标签**: HTML/XML 标签正确性验证
- **术语一致性**: 基于术语表的翻译一致性检查

#### 🎨 Minecraft 主题界面
- **像素完美渲染**: `imageRendering: 'pixelated'` 还原游戏质感
- **3D 边框系统**: 动态光影边框，按钮按下效果
- **游戏纹理背景**: 石头、木板、泥土等材质纹理
- **附魔闪烁效果**: 史诗和传奇物品的动态光效
- **物品稀有度颜色**: 普通、罕见、稀有、史诗、传奇五级颜色系统
- **快捷栏交互**: 1-9 数字键快速操作，ESC 菜单切换

### 🏠 RW Studio 功能
- **Steam Workshop 集成**: 自动处理 Workshop 模组的本地化
- **游戏文件解析**: 智能识别和提取游戏中的可翻译文本
- **翻译记忆库**: 与 Trans-Hub 同步的翻译记忆管理
- **质量保证**: 自动化的翻译质量检查和验证

## 🚀 快速开始

### 📋 环境要求

- **Python**: 3.9 或更高版本
- **Node.js**: 18 或更高版本
- **Rust**: 1.70 或更高版本（用于 Tauri）
- **Poetry**: Python 依赖管理
- **pnpm**: Node.js 包管理器
- **Task**: 任务运行器（可选，推荐）

### 🛠️ 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/th-suite.git
cd th-suite
   ```

2. **安装依赖**
   ```bash
   # 使用 Task（推荐）
   task install
   
   # 或手动安装
   poetry install
   cd apps/mc-l10n/frontend && pnpm install
   cd ../../../apps/rw-studio/frontend && pnpm install
   ```

3. **配置环境**
   ```bash
   # 复制环境变量模板
   cp .env.example .env
   
   # 编辑 .env 文件，填入你的配置
   # 至少需要配置游戏路径和翻译服务 API Key
   ```

4. **启动开发服务器**
   ```bash
   # 启动 TH Suite MC L10n
   task dev:mc
   
   # 启动 RW Studio
   task dev:rw
   
   # 或同时启动所有服务
   task dev
   ```

### 🐳 Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📁 项目结构

```
th-suite/
├── apps/                          # 应用程序
│   ├── mc_l10n/                   # TH Suite MC L10n 应用
│   │   ├── backend/               # Python FastAPI 后端
│   │   │   └── src/              
│   │   │       ├── adapters/     # 外部接口适配器
│   │   │       ├── application/  # 应用服务层
│   │   │       ├── domain/       # 领域模型
│   │   │       └── infrastructure/ # 基础设施
│   │   └── frontend/              # Tauri + React 前端
│   │       └── src/
│   │           ├── components/    # React 组件
│   │           │   └── minecraft/ # MC 主题组件
│   │           ├── pages/         # 页面组件
│   │           ├── services/      # 服务层
│   │           └── i18n/          # 国际化
│   └── rw_l10n/                   # RW Studio 应用
│       ├── backend/               # Python FastAPI 后端
│       └── frontend/              # Tauri + React 前端
├── packages/                      # 共享包（通用组件）
│   ├── localization-kit/         # 本地化核心库
│   │   ├── models/                # 数据模型
│   │   ├── services/              # 核心服务
│   │   ├── quality/               # 质量检查
│   │   ├── observability/         # 可观测性
│   │   └── trans_hub/             # Trans-Hub 集成
│   ├── parsers/                   # 文件解析器
│   ├── backend-kit/               # FastAPI 工具集
│   └── protocol/                  # API 协议定义
├── docs/                          # 文档
│   ├── ARCHITECTURE.md           # 架构设计文档
│   ├── API.md                     # API 接口文档
│   └── USAGE.md                   # 使用指南
├── tests/                         # 测试文件
├── docker-compose.yml             # Docker 编排
├── Taskfile.yml                   # 任务定义
├── pyproject.toml                 # Python 项目配置
├── package.json                   # Node.js 项目配置
├── CLAUDE.md                      # AI 助手配置
└── README.md                      # 项目说明
```

## 🔧 开发指南

### 📝 可用命令

```bash
# 开发
task dev              # 启动所有开发服务器
task dev:mc           # 启动 TH Suite MC L10n
task dev:rw           # 启动 RW Studio

# 构建
task build            # 构建所有应用
task build:mc         # 构建 TH Suite MC L10n
task build:rw         # 构建 RW Studio

# 测试
task test             # 运行所有测试
task test:mc          # 测试 TH Suite MC L10n
task test:rw          # 测试 RW Studio

# 代码质量
task lint             # 代码检查
task format           # 代码格式化

# 清理
task clean            # 清理构建产物

# 工具
task status           # 查看项目状态
task health           # 健康检查
task logs             # 查看日志
```

### 🧪 测试

```bash
# 运行所有测试
task test

# 运行特定测试
task test:python      # Python 测试
task test:frontend    # 前端测试
task test:mc          # TH Suite MC L10n 黄金测试
task test:rw          # RW Studio 黄金测试

# 测试覆盖率
poetry run pytest --cov=apps --cov-report=html
```

### 📊 代码质量

```bash
# 代码检查
task lint

# 自动格式化
task format

# 类型检查
poetry run mypy apps packages
```

## 📚 API 文档

启动开发服务器后，可以访问以下地址查看 API 文档：

- **TH Suite MC L10n API**: http://localhost:8000/docs (FastAPI 自动生成)
- **RW Studio API**: http://localhost:8002/docs (FastAPI 自动生成)

### 核心 API 端点

#### 扫描相关
- `POST /api/scan/directory` - 扫描目录提取语言文件
- `GET /api/scan/{scan_id}/status` - 获取扫描进度
- `GET /api/scan/{scan_id}/result` - 获取扫描结果

#### 补丁管理
- `GET /api/patches` - 获取补丁列表
- `POST /api/patches` - 创建新补丁集
- `PUT /api/patches/{patch_id}/apply` - 应用补丁
- `DELETE /api/patches/{patch_id}/rollback` - 回滚补丁

#### 质量检查
- `POST /api/quality/validate` - 运行质量验证
- `GET /api/quality/reports` - 获取质量报告
- `GET /api/quality/validators` - 获取可用验证器列表

#### Trans-Hub 集成
- `POST /api/trans-hub/sync` - 同步翻译数据
- `GET /api/trans-hub/projects` - 获取项目列表
- `POST /api/trans-hub/upload` - 上传待翻译内容

## 🔌 翻译引擎插件开发

### Python 翻译引擎插件

```python
from packages.core import TranslationEngine, EngineManager

class MyTranslationEngine(TranslationEngine):
    name = "my-translation-engine"
    version = "1.0.0"
    
    def initialize(self):
        # 翻译引擎初始化逻辑
        pass
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        # 翻译逻辑实现
        return translated_text

# 注册翻译引擎
EngineManager.register(MyTranslationEngine)
```

### TypeScript 解析器插件

```typescript
import { FileParser, ParserManager } from '@th-suite/parsers';

class MyFileParser extends FileParser {
  name = 'my-file-parser';
  version = '1.0.0';
  supportedExtensions = ['.custom'];
  
  parse(content: string): TranslationUnit[] {
    // 文件解析逻辑
    return translationUnits;
  }
  
  serialize(units: TranslationUnit[]): string {
    // 文件序列化逻辑
    return serializedContent;
  }
}

// 注册解析器
ParserManager.register(MyFileParser);
```

## 🚀 部署

### 生产环境部署

1. **构建应用**
   ```bash
   task build
   ```

2. **配置环境变量**
   ```bash
   export ENVIRONMENT=production
   export DEBUG=false
   # 其他生产环境配置...
   ```

3. **启动服务**
   ```bash
   # 使用 Docker
   docker-compose -f docker-compose.prod.yml up -d
   
   # 或直接运行
   poetry run uvicorn apps.mc_studio.backend.main:app --host 0.0.0.0 --port 8001
   poetry run uvicorn apps.rw_studio.backend.main:app --host 0.0.0.0 --port 8002
   ```

### 桌面应用分发

```bash
# 构建桌面应用
task build:mc
task build:rw

# 生成的可执行文件位于：
# apps/mc-l10n/frontend/src-tauri/target/release/
# apps/rw-studio/frontend/src-tauri/target/release/
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 🐛 报告问题

如果你发现了 bug 或有功能建议，请在 [GitHub Issues](https://github.com/your-username/th-suite/issues) 中创建一个 issue。

### 🔧 提交代码

1. Fork 这个仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Tauri](https://tauri.app/) - 跨平台桌面应用框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://reactjs.org/) - 用户界面库
- [Tailwind CSS](https://tailwindcss.com/) - CSS 框架
- [Poetry](https://python-poetry.org/) - Python 依赖管理
- [Task](https://taskfile.dev/) - 任务运行器

## 📞 联系我们

- **官方网站**: https://trans-hub.net
- **项目主页**: https://github.com/Saken/th-suite
- **问题反馈**: https://github.com/Saken/th-suite/issues
- **讨论区**: https://github.com/Saken/th-suite/discussions
- **Discord 社区**: 即将开放
- **QQ 群**: 即将开放
- **Telegram**: 即将开放

## 👨‍💻 作者

**Saken** - *项目创建者和维护者*

- 官网: [trans-hub.net](https://trans-hub.net)
- GitHub: [@Saken](https://github.com/Saken)

---

<div align="center">
  <p>用 ❤️ 制作，为 Minecraft 本地化社区服务</p>
  <p>© 2024 Trans-Hub Tools by Saken. All rights reserved.</p>
</div>