# TH-Suite Claude Flow 集成

TH-Suite 专为游戏本地化工具优化的 Claude Flow 配置和集成系统。

## 🎮 TH-Suite 特性

### 游戏本地化专用
- **Minecraft MOD 支持**: Forge、Fabric、Quilt、NeoForge 多加载器兼容
- **JAR 文件处理**: 安全的文件修改、备份和恢复机制
- **i18n 提取**: 智能国际化文件解析和提取
- **Trans-Hub 集成**: 与翻译平台的深度集成和同步

### 架构优势
- **Clean Architecture**: 严格的分层架构和依赖方向控制
- **Tauri 跨平台**: 现代桌面应用架构
- **Monorepo 管理**: 多应用和共享包的统一管理
- **SQLCipher 加密**: 敏感数据的安全存储

## 🤖 Claude Flow 集成功能

### 智能代码审查
- **游戏文件安全**: 专用的 JAR 文件安全扫描
- **MOD 兼容性**: 自动检测和验证 MOD 加载器兼容性
- **架构合规**: Clean Architecture 分层验证
- **Trans-Hub 集成**: API 集成质量检查

### 专用 Hooks
- **jar-processing**: JAR 文件处理安全检查
- **trans-hub-sync**: Trans-Hub 同步状态监控
- **mod-compatibility**: MOD 兼容性验证
- **security-scan**: 游戏文件安全扫描

### 性能优化
- **大文件处理**: 优化大型 JAR 文件的处理性能
- **并发处理**: 多文件并行处理优化
- **内存管理**: 智能内存使用和垃圾回收
- **缓存策略**: 减少重复计算和 I/O 操作

## 📁 目录结构

```
TH-Suite/
├── .claude/                    # Claude Flow 配置和命令
│   ├── commands/               # 专用命令定义
│   │   └── hooks/             # TH-Suite 专用 hooks
│   └── helpers/               # 辅助工具和设置脚本
├── .github/workflows/         # CI/CD 工作流
├── .vscode/                   # VS Code 集成配置
├── scripts/                   # Claude Flow 辅助脚本
├── claude-flow.config.json    # Claude Flow 主配置
├── apps/
│   └── mc_l10n/              # Minecraft 本地化工具
│       ├── backend/          # Python + FastAPI 后端
│       └── frontend/         # Tauri + React 前端
└── packages/                  # 共享包和工具
```

## 🚀 快速开始

### 1. 系统检查和安装

```bash
# 检查系统依赖
./.claude/helpers/th-suite-setup.sh check

# 完整安装（推荐）
./.claude/helpers/th-suite-setup.sh full

# 仅安装 Claude Flow
./.claude/helpers/th-suite-setup.sh claude-flow
```

### 2. 初始化开发环境

```bash
# 使用 Task 工具（推荐）
task install           # 安装所有依赖
task dev:mc           # 启动 MC L10n 开发环境

# 使用 npm scripts
npm run install:all
npm run dev:mc_l10n
```

### 3. Claude Flow 集成

```bash
# 初始化 Claude Flow
npm run claude-flow:init

# 运行代码审查
npm run claude-flow:review

# 安全扫描
npm run claude-flow:security

# 生成综合报告
npm run claude-flow:report
```

## 🛠️ 开发工具集成

### VS Code 集成
- 预配置的任务和启动配置
- Python 和 TypeScript 开发环境
- Claude Flow 命令快捷方式
- 代码格式化和 linting

### GitHub Actions CI/CD
- 自动代码审查和质量检查
- 安全扫描和漏洞检测
- 架构合规性验证
- 自动修复和报告生成

### 本地开发脚本
- `./scripts/claude-flow-helpers.sh` - Claude Flow 集成脚本
- `./.claude/helpers/th-suite-setup.sh` - 环境设置脚本

## 📊 Claude Flow 命令

### 基础命令
```bash
# 环境检查
./scripts/claude-flow-helpers.sh check-deps

# 初始化 Swarm
./scripts/claude-flow-helpers.sh init

# 代码审查
./scripts/claude-flow-helpers.sh review
```

### 专用分析
```bash
# 安全扫描（游戏文件特化）
./scripts/claude-flow-helpers.sh security-scan full

# 架构检查（Clean Architecture + Tauri）
./scripts/claude-flow-helpers.sh arch-check

# 性能分析（JAR 处理优化）
./scripts/claude-flow-helpers.sh perf-analysis
```

### 自动化功能
```bash
# 生成测试用例
./scripts/claude-flow-helpers.sh gen-tests unit 85

# 自动修复代码问题
./scripts/claude-flow-helpers.sh autofix

# 游戏本地化工作流
./scripts/claude-flow-helpers.sh game-workflow full
```

## 🎯 TH-Suite 专用功能

### JAR 文件处理
```bash
# JAR 文件安全处理
npx claude-flow hook jar-processing \
  --file-path "./mods/example.jar" \
  --operation extract \
  --safety-check \
  --backup-create
```

### Trans-Hub 同步
```bash
# 与 Trans-Hub 同步翻译
npx claude-flow hook trans-hub-sync \
  --project-id "minecraft-mods-zh-cn" \
  --operation sync \
  --conflict-resolution auto
```

### MOD 兼容性检查
```bash
# 检查 MOD 加载器兼容性
npx claude-flow hook mod-compatibility \
  --mod-path "./mods/" \
  --loaders forge,fabric,quilt \
  --minecraft-version "1.20.1"
```

## 📈 性能优化建议

### JAR 处理优化
- 使用流式处理大型文件
- 启用并发提取和处理
- 配置智能缓存策略
- 优化内存使用模式

### Trans-Hub 集成优化
- 批量处理翻译数据
- 智能冲突解决策略
- 增量同步机制
- 网络连接优化

### 构建和开发优化
- 使用 pnpm 替代 npm
- 启用 TypeScript 项目引用
- 配置 Rust 增量编译
- 优化 Python Poetry 缓存

## 🔧 配置选项

### claude-flow.config.json
```json
{
  "gameLocalization": {
    "supportedGames": ["minecraft", "rusted-warfare"],
    "modLoaders": ["forge", "fabric", "quilt", "neoforge"],
    "transHubIntegration": {
      "uidaProtocol": "2.1",
      "batchSize": 1000
    }
  }
}
```

### package.json Claude Flow 配置
```json
{
  "claudeFlow": {
    "gameLocalization": true,
    "hooks": {
      "jarProcessing": true,
      "transHubSync": true
    }
  }
}
```

## 🚨 故障排除

### 常见问题
1. **依赖缺失**: 运行 `./.claude/helpers/th-suite-setup.sh check`
2. **Claude Flow 连接问题**: 检查网络和代理设置
3. **JAR 处理错误**: 验证文件权限和完整性
4. **Tauri 构建失败**: 确保 Rust 工具链正确安装

### 调试模式
```bash
# 启用 Claude Flow 调试
export CLAUDE_FLOW_DEBUG=1
./scripts/claude-flow-helpers.sh review

# 详细日志输出
export CLAUDE_FLOW_TIMEOUT=60
```

## 📚 更多资源

- [TH-Suite 项目文档](../CLAUDE.md)
- [Claude Flow 官方文档](https://github.com/ruvnet/claude-flow)
- [Tauri 开发指南](https://tauri.app/)
- [Trans-Hub 生态系统](https://trans-hub.net)

## 🤝 贡献指南

1. Fork 项目并创建功能分支
2. 使用 Claude Flow 进行代码审查
3. 确保所有测试通过
4. 遵循 TH-Suite 代码规范
5. 提交 Pull Request

---

*🎮 专为游戏本地化工具优化的 Claude Flow 集成*