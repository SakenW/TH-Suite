# TH-Suite v2.0 - Core-First专业适配器

> 🌐 **专业游戏本地化适配器** - Trans-Hub生态系统的Minecraft专业工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Tauri](https://img.shields.io/badge/Tauri-2.8+-orange.svg)](https://tauri.app/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-red.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-blue.svg)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19.1+-61dafb.svg)](https://reactjs.org/)
[![Ant Design](https://img.shields.io/badge/Ant%20Design-5.27+-0170fe.svg)](https://ant.design/)

## 📖 项目简介

TH-Suite v2.0是完全重构的Core-First专业适配器，专为Trans-Hub生态系统设计的Minecraft本地化工具。通过投影适配器系统与Trans-Hub Core深度集成，删除了15,000+行重复基础设施代码，专注于Minecraft特定的用户体验优化。

**🚀 Core-First架构优势**：
- **零重复基础设施** - 依赖Trans-Hub Core提供翻译引擎、存储、同步等核心服务  
- **投影适配系统** - UIDA双向转换，确保数据一致性和可追溯性
- **多MOD加载器支持** - 智能识别Forge、Fabric、Quilt、NeoForge
- **专业化界面** - 游戏玩家友好的"人话化"设计

**🎯 目标用户**：
- Minecraft整合包制作者和本地化团队
- MOD开发者需要多语言支持
- 游戏玩家希望获得高质量中文体验

## ✨ v2.0 核心特性

### 🔧 Core-First架构重构  
- **投影适配系统**: Minecraft ↔ UIDA双向转换，数据一致性保证
- **Trans-Hub客户端**: 完整的HTTP API集成，支持摄入、翻译、同步工作流
- **零冗余代码**: 删除15,000+行重复基础设施，仅保留Minecraft特定逻辑  
- **Clean Architecture**: DDD六边形架构，适配器-领域-服务清晰分层

### 🎮 多MOD加载器支持
- **智能检测**: 自动识别Forge、NeoForge、Fabric、Quilt MOD类型
- **元数据提取**: 完整解析mods.toml、fabric.mod.json、quilt.mod.json  
- **依赖分析**: 可视化MOD依赖关系，自动检测缺失和冲突
- **版本兼容**: 支持各加载器的版本需求检查和兼容性验证

### 🛠️ 高级JAR处理能力
- **安全修改**: 自动备份、完整性检查、签名验证  
- **冲突解决**: 智能检测翻译冲突，支持自动合并和手动解决
- **多策略构建**: Resource Pack、JAR直接修改、Overlay包三种输出模式
- **回滚机制**: 一键回滚到任意备份版本，保障数据安全

### 🎨 现代化用户界面  
- **Minecraft轻装饰主题**: 像素化描边、方块阴影、网格背景
- **Ant Design 5.x**: 专业UI组件库，替代废弃的Material-UI
- **玩家友好设计**: "人话化"文案，隐藏技术参数，安全默认策略
- **响应式布局**: 适配桌面和移动设备，保持一致体验

### 🔄 完整本地化工作流
```
扫描MOD → 提取语言文件 → 投影转换 → 摄入Trans-Hub → 
自动翻译 → 同步回本地 → 冲突解决 → 构建本地化包
```

### 📊 智能分析与统计
- **加载器分布**: 可视化Forge/Fabric/Quilt/NeoForge占比
- **版本兼容性**: Minecraft版本支持情况统计  
- **翻译覆盖率**: 各语言翻译完成度和质量评分
- **依赖关系图**: 树形结构展示MOD依赖，循环依赖检测
- **增量扫描**: 基于指纹的智能缓存，仅处理变更部分
- **多格式支持**: JSON、Properties、YAML、TOML 等格式自动识别

#### 🔧 补丁系统
- **多种合并策略**: OVERLAY（覆盖）、REPLACE（替换）、MERGE（合并）、CREATE_IF_MISSING（按需创建）
- **冲突检测**: 自动识别并报告补丁冲突
- **版本控制**: 补丁集版本管理，支持回滚和历史追踪
- **数字签名**: 补丁内容签名验证，确保内容完整性

#### 🔐 安全管理
- **用户权限控制**: 基于角色的访问控制（RBAC）
- **数据加密**: AES-256 加密存储，TLS 传输加密
- **API 密钥管理**: 安全的密钥生成、撤销和权限管理
- **审计日志**: 完整的操作日志和安全事件追踪

#### 🌐 服务器集成
- **Trans-Hub 连接**: 实时连接状态监控和自动重连
- **智能同步**: 增量同步、冲突解决、压缩传输
- **性能优化**: 连接池、请求限流、缓存策略
- **离线模式**: 支持离线工作，上线后自动同步

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

### 📋 系统要求

- **Python**: 3.12+ (推荐3.12.7)
- **Node.js**: 18+ (推荐18.19.0)
- **Rust**: 1.70+ (Tauri构建需要)
- **Trans-Hub Core**: v1.0+ (依赖服务)
- **操作系统**: Windows 10+, macOS 12+, Linux (Ubuntu 20.04+)

### 🛠️ v2.0技术架构

#### Core-First后端 (Python 3.12)
- **FastAPI 0.115+**: RESTful API服务
- **投影适配器**: Minecraft ↔ UIDA双向转换
- **多加载器支持**: Forge、Fabric、Quilt、NeoForge智能识别
- **工作流引擎**: 完整的本地化流水线
- **JAR处理器**: 安全修改、备份、回滚机制

#### 现代化前端 (TypeScript 5.9)
- **React 19.1+**: 现代化UI框架
- **Tauri 2.8+**: 高性能桌面应用
- **Ant Design 5.27+**: 专业UI组件库 (替代Material-UI)
- **Minecraft轻装饰主题**: 像素化风格、方块阴影
- **响应式设计**: 桌面和移动设备适配

#### 核心依赖服务
- **Trans-Hub Core**: 翻译引擎、内容寻址存储
- **UIDA系统**: 统一标识符和寻址规范
- **投影规范**: YAML配置驱动的数据映射

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
│   ├── database-schema.md        # 数据库架构文档
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

- **TH Suite MC L10n API**: http://localhost:18000/docs (FastAPI 自动生成)
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
   poetry run uvicorn apps.mc_l10n.backend.main:app --host 0.0.0.0 --port 18000
   poetry run uvicorn apps.rw_l10n.backend.main:app --host 0.0.0.0 --port 8002
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

## 📚 相关文档

- **[完整开发指南](DEVELOPER_GUIDE.md)** - 详细的开发环境配置和工作流程
- **[数据库架构文档](docs/database-schema.md)** - 完整的数据库表结构和设计说明
- **[项目架构设计](docs/ARCHITECTURE.md)** - Core-First架构设计文档
- **[API接口文档](docs/API.md)** - RESTful API详细规范
- **[使用指南](docs/USAGE.md)** - 用户操作手册和最佳实践

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