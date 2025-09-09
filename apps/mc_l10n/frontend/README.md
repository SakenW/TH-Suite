# 🎮 TH Suite MC L10n Frontend

TH Suite MC L10n 前端应用，基于 Tauri + React + TypeScript 构建的 Minecraft 风格桌面应用程序。

## ✨ 最新更新 (2025.01)

### Minecraft 主题 UI 重构

- 🎨 **全新 Minecraft 风格界面**: 像素化设计，游戏化体验
- 🎮 **自定义组件库**: MinecraftButton、MinecraftCard、MinecraftProgress 等
- ✨ **动画效果**: 粒子效果、方块动画、游戏化过渡
- 🏆 **成就系统**: 游戏化的进度追踪和成就展示

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **桌面框架**: Tauri
- **UI 库**: Material-UI (MUI) + 自定义 Minecraft 组件
- **主题系统**: Minecraft 主题配置
- **状态管理**: Zustand
- **路由**: React Router DOM
- **动画**: Framer Motion
- **HTTP 客户端**: Axios
- **表单处理**: React Hook Form + Zod
- **通知**: React Hot Toast
- **图标**: Lucide React + Minecraft 图标

## 项目结构

```
src/
├── components/          # 组件
│   ├── minecraft/      # Minecraft 风格组件
│   │   ├── MinecraftButton.tsx     # 游戏风格按钮
│   │   ├── MinecraftCard.tsx       # 游戏风格卡片
│   │   └── MinecraftProgress.tsx   # 游戏风格进度条
│   ├── Layout/         # 布局组件
│   └── common/         # 通用组件
├── pages/              # 页面组件
│   ├── HomePageMinecraft.tsx       # Minecraft 风格首页
│   ├── ScanPageMinecraft.tsx       # Minecraft 风格扫描页
│   └── PlaceholderPage.tsx         # 占位页面
├── services/           # 服务层
│   ├── domain/         # 领域服务
│   └── infrastructure/ # 基础设施服务
├── stores/             # 状态管理
├── theme/              # 主题配置
│   └── minecraftTheme.ts          # Minecraft 主题
├── hooks/              # 自定义 Hooks
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

- 🔍 **模组扫描**: 智能扫描和识别 Minecraft 模组与资源包
- 📦 **资源提取**: 从 JAR 文件和压缩包中提取语言文件
- 🌐 **翻译管理**: 管理和编辑本地化内容
- 🔄 **Trans-Hub 集成**: 与 Trans-Hub 平台实时同步
- 📊 **进度追踪**: 实时显示扫描和处理进度
- 🏆 **成就系统**: 游戏化的任务完成追踪

### Minecraft 主题特性

- 🎮 **游戏化界面**: 完全的 Minecraft 视觉风格
- 🧱 **方块元素**: 草方块、钻石、金块等图标系统
- ⚡ **粒子效果**: 动态粒子和爆炸效果
- 📊 **经验条进度**: 游戏风格的进度显示
- 🎨 **像素化设计**: 像素字体和复古风格
- 💎 **材质按钮**: 不同材质风格的交互按钮

### 界面特性

- 🌟 **沉浸式体验**: 完整的 Minecraft 游戏体验
- 🎯 **快捷操作**: 游戏化的功能导航
- 📈 **实时统计**: 动态更新的数据展示
- ✨ **流畅动画**: 游戏风格的过渡和动效
- 🔔 **游戏通知**: Minecraft 风格的提示信息

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

## Minecraft 组件使用指南

### MinecraftButton

```tsx
import { MinecraftButton } from '@components/minecraft';

// 不同材质风格
<MinecraftButton minecraftStyle="diamond" onClick={handleClick}>
  钻石按钮
</MinecraftButton>

<MinecraftButton minecraftStyle="emerald" glowing>
  发光的绿宝石按钮
</MinecraftButton>

// 可用材质: grass, stone, diamond, gold, iron, emerald, redstone
```

### MinecraftCard

```tsx
import { MinecraftCard } from '@components/minecraft'

// 不同卡片风格
;<MinecraftCard variant='chest' title='宝箱' icon='gold'>
  内容
</MinecraftCard>

// 可用风格: inventory, chest, crafting, enchantment
```

### MinecraftProgress

```tsx
import { MinecraftProgress } from '@components/minecraft'

// 不同进度条风格
;<MinecraftProgress value={75} max={100} variant='experience' label='经验值' animated />

// 可用风格: experience, health, hunger, armor, loading
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
