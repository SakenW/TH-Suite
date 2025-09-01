# TH Suite MC L10n Frontend

TH Suite MC L10n 前端应用，基于 Tauri + React + TypeScript 构建的桌面应用程序。

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **桌面框架**: Tauri
- **UI 库**: Material-UI (MUI)
- **状态管理**: Zustand
- **路由**: React Router DOM
- **动画**: Framer Motion
- **HTTP 客户端**: Axios
- **表单处理**: React Hook Form + Zod
- **通知**: React Hot Toast
- **图标**: Lucide React

## 项目结构

```
src/
├── components/          # 组件
│   ├── Layout/         # 布局组件
│   └── common/         # 通用组件
├── pages/              # 页面组件
├── services/           # 服务层
├── stores/             # 状态管理
├── App.tsx            # 主应用组件
├── main.tsx           # 应用入口
└── index.css          # 全局样式

src-tauri/              # Tauri 后端
├── src/
│   └── main.rs        # Rust 主文件
├── Cargo.toml         # Rust 依赖配置
├── tauri.conf.json    # Tauri 配置
└── icons/             # 应用图标
```

## 功能特性

### 核心功能
- 🔍 **资源扫描**: 扫描 Minecraft 资源文件和数据包
- 📦 **资源提取**: 从压缩包中提取资源文件
- 🔨 **项目构建**: 构建资源包和数据包
- ⚙️ **设置管理**: 应用配置和偏好设置

### 界面特性
- 🎨 **现代化 UI**: 基于 Material Design 的美观界面
- 🌙 **主题支持**: 支持浅色/深色/跟随系统主题
- 📱 **响应式设计**: 适配不同屏幕尺寸
- ✨ **流畅动画**: 使用 Framer Motion 提供流畅的交互动画
- 🔔 **实时通知**: 操作状态和结果的实时反馈

### 技术特性
- 🚀 **高性能**: Tauri 提供原生性能
- 🔒 **安全**: 严格的 CSP 策略和权限控制
- 💾 **数据持久化**: 本地存储用户设置和项目历史
- 🔄 **实时通信**: WebSocket 与后端实时通信
- 📁 **文件操作**: 完整的文件系统访问能力

## 开发环境设置

### 前置要求

- Node.js 18+
- Rust 1.60+
- Tauri CLI

### 安装依赖

```bash
# 安装 Node.js 依赖
npm install

# 安装 Tauri CLI（如果还没有安装）
npm install -g @tauri-apps/cli
```

### 开发模式

```bash
# 启动开发服务器
npm run tauri dev
```

### 构建应用

```bash
# 构建生产版本
npm run tauri build
```

## 可用脚本

- `npm run dev` - 启动 Vite 开发服务器
- `npm run build` - 构建前端资源
- `npm run preview` - 预览构建结果
- `npm run tauri dev` - 启动 Tauri 开发模式
- `npm run tauri build` - 构建 Tauri 应用
- `npm run lint` - 运行 ESLint 检查
- `npm run type-check` - 运行 TypeScript 类型检查

## 配置说明

### Tauri 配置

主要配置文件 `tauri.conf.json` 包含：

- **构建配置**: 前端资源路径、构建命令
- **应用信息**: 名称、版本、描述
- **权限配置**: 文件系统、网络、通知等权限
- **窗口配置**: 窗口大小、标题、图标
- **安全策略**: CSP 规则

### 环境变量

- `VITE_API_URL` - 后端 API 地址
- `VITE_WS_URL` - WebSocket 地址

## 部署

### 开发版本

开发版本会自动打开开发者工具，包含调试信息。

### 生产版本

生产版本经过优化，体积更小，性能更好：

```bash
npm run tauri build
```

构建产物位于 `src-tauri/target/release/bundle/` 目录。

## 故障排除

### 常见问题

1. **Tauri 构建失败**
   - 确保已安装 Rust 和必要的系统依赖
   - 检查 `Cargo.toml` 中的依赖版本

2. **前端资源加载失败**
   - 检查 `tauri.conf.json` 中的 `distDir` 配置
   - 确保前端资源已正确构建

3. **权限错误**
   - 检查 `tauri.conf.json` 中的权限配置
   - 确保应用有必要的系统权限

### 调试

- 开发模式下可以使用浏览器开发者工具
- Rust 后端日志会输出到控制台
- 使用 `console.log` 进行前端调试

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
