# 开发环境配置说明

TH Suite MC L10n 前端开发环境配置指南，基于 **Ant Design 5.x** 架构。

> ✅ **迁移已完成**: Material-UI 已完全移除，现已全面使用 Ant Design 作为唯一 UI 组件库。

## 环境要求

### 系统要求
- **操作系统**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Node.js**: 18.0+ (推荐 18.17.0+)
- **Rust**: 1.60+ (Tauri 要求)
- **包管理器**: pnpm 8.0+ (推荐) 或 npm 9.0+

### 开发工具推荐
- **IDE**: VS Code + Tauri 扩展
- **浏览器**: Chrome/Edge (开发者工具支持最佳)
- **终端**: Windows Terminal / iTerm2

## 环境搭建

### 1. Node.js 和 pnpm 安装

```bash
# 安装 Node.js (使用 nvm 推荐)
# Windows: 下载 Node.js 安装包
# macOS: brew install node
# Linux: 使用包管理器或 nvm

# 验证安装
node --version  # 应该 >= 18.0
npm --version   # 应该 >= 9.0

# 安装 pnpm
npm install -g pnpm

# 验证 pnpm
pnpm --version  # 应该 >= 8.0
```

### 2. Rust 工具链安装

```bash
# 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Windows 用户可从官网下载安装包
# https://forge.rust-lang.org/infra/channel-layout.html

# 验证安装
rustc --version
cargo --version
```

### 3. Tauri CLI 安装

```bash
# 安装 Tauri CLI
pnpm add -g @tauri-apps/cli

# 验证安装
tauri --version
```

### 4. 项目依赖安装

```bash
# 克隆项目
git clone <project-url>
cd TH-Suite/apps/mc_l10n/frontend

# 安装依赖
pnpm install

# 验证依赖
pnpm list
```

## 开发命令

### 基础开发命令

```bash
# 启动前端开发服务器 (Web 模式)
pnpm dev
# 访问: http://localhost:18001

# 启动 Tauri 桌面应用开发模式
pnpm tauri:dev
# 自动打开桌面应用窗口

# 构建前端资源
pnpm build

# 构建 Tauri 桌面应用
pnpm tauri:build
```

### 代码质量命令

```bash
# TypeScript 类型检查
pnpm type-check

# ESLint 代码检查
pnpm lint

# ESLint 自动修复
pnpm lint:fix

# Prettier 代码格式化
pnpm format

# Prettier 格式检查
pnpm format:check

# 运行所有检查
pnpm check:all
```

## 配置文件说明

### 核心配置文件

#### `package.json` - 依赖和脚本配置
```json
{
  "dependencies": {
    "antd": "^5.27.3",           // UI 组件库
    "@ant-design/icons": "^6.0.1", // 图标库
    "react": "^19.1.1",         // React 框架
    "typescript": "5.9.2"       // TypeScript
  },
  "scripts": {
    "dev": "vite",              // 开发服务器
    "tauri:dev": "tauri dev",   // Tauri 开发模式
    "build": "vite build",      // 构建前端
    "tauri:build": "tauri build" // 构建桌面应用
  }
}
```

#### `vite.config.ts` - Vite 构建配置
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 18001,  // 避免与 Trans-Hub 端口冲突
    strictPort: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@pages': path.resolve(__dirname, 'src/pages'),
      '@services': path.resolve(__dirname, 'src/services'),
      '@stores': path.resolve(__dirname, 'src/stores'),
    },
  },
})
```

#### `tsconfig.json` - TypeScript 配置
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@pages/*": ["src/pages/*"],
      "@services/*": ["src/services/*"],
      "@stores/*": ["src/stores/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

#### `src-tauri/tauri.conf.json` - Tauri 应用配置
```json
{
  "build": {
    "beforeDevCommand": "pnpm dev",
    "beforeBuildCommand": "pnpm build",
    "devPath": "http://localhost:18001",
    "distDir": "../dist"
  },
  "package": {
    "productName": "TH Suite MC L10n",
    "version": "0.1.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "all": false,
        "open": true
      },
      "dialog": {
        "all": false,
        "open": true,
        "save": true
      },
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "readDir": true,
        "exists": true
      }
    },
    "bundle": {
      "active": true,
      "targets": "all",
      "identifier": "com.transhub.mc-l10n",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ]
    },
    "security": {
      "csp": null
    },
    "windows": [
      {
        "fullscreen": false,
        "resizable": true,
        "title": "TH Suite MC L10n",
        "width": 1200,
        "height": 800,
        "minWidth": 800,
        "minHeight": 600
      }
    ]
  }
}
```

## Ant Design 架构使用说明

### 1. 当前架构状态

✅ **已完成迁移**: 项目已完全切换到 Ant Design 架构，所有 Material-UI 依赖已移除。

当前使用的主文件：
- `src/main.tsx` - 使用简化版应用入口
- `src/App.simple.tsx` - 基于 Ant Design 的主应用组件
- `src/pages/WelcomeMinimal.tsx` - 生产就绪的欢迎页面

### 2. 开发模式验证

启动开发服务器后，应该看到：

1. **加载界面**: Ant Design Spin 组件的加载动画
2. **主界面**: 左侧导航（使用 Ant Design Menu）+ 顶部状态条（基于 Ant Design Layout）
3. **欢迎页**: 使用 Ant Design Card 和 Typography 组件的工具介绍页面
4. **主题切换**: 基于 Ant Design ConfigProvider 的亮色/暗色主题切换

### 3. 控制台验证

开发模式下控制台应显示：
```
🚀 Starting new app initialization...
🎉 App initialization complete
```

> 注意：简化版架构移除了复杂的服务初始化，直接使用 localStorage 进行状态管理。

## 开发工作流

### 1. 日常开发流程

```bash
# 1. 启动开发环境
pnpm tauri:dev

# 2. 编辑代码
# - 使用 VS Code 编辑
# - 保存时自动热重载

# 3. 验证代码质量
pnpm type-check  # TypeScript 检查
pnpm lint        # ESLint 检查

# 4. 提交前检查
pnpm check:all   # 运行所有检查
```

### 2. 新建页面流程

```bash
# 1. 创建页面组件
# src/pages/MyNewPage.tsx

# 2. 添加路由
# 编辑 src/App.simple.tsx，添加路由配置

# 3. 添加导航
# 编辑 src/layouts/MainLayout.tsx，添加菜单项

# 4. 测试页面
pnpm dev  # 验证页面正常显示
```

### 3. 新建组件流程

```tsx
// 1. 创建组件文件
// src/components/MyComponent.tsx

import React from 'react'
import { Card, Button } from 'antd'
import { useTheme } from '../contexts/ThemeProvider'

interface Props {
  title: string
}

export const MyComponent: React.FC<Props> = ({ title }) => {
  const { colors } = useTheme()
  
  return (
    <Card title={title}>
      {/* 组件内容 */}
    </Card>
  )
}

export default MyComponent

// 2. 导出组件
// 编辑 src/components/index.ts
export { default as MyComponent } from './MyComponent'

// 3. 使用组件
import { MyComponent } from '@components'
```

## 环境变量配置

### 开发环境变量

创建 `.env.local` 文件：
```bash
# API 配置
VITE_API_URL=http://localhost:18000
VITE_WS_URL=ws://localhost:18000

# 功能开关
VITE_ENABLE_MOCK=false
VITE_ENABLE_DEBUG=true

# 主题配置
VITE_DEFAULT_THEME=auto
```

### 生产环境变量

创建 `.env.production` 文件：
```bash
# API 配置
VITE_API_URL=https://api.trans-hub.com
VITE_WS_URL=wss://api.trans-hub.com

# 功能开关
VITE_ENABLE_MOCK=false
VITE_ENABLE_DEBUG=false

# 主题配置
VITE_DEFAULT_THEME=auto
```

## VS Code 配置

### 推荐扩展

创建 `.vscode/extensions.json`：
```json
{
  "recommendations": [
    "tauri-apps.tauri-vscode",      // Tauri 支持
    "rust-lang.rust-analyzer",      // Rust 语言支持
    "bradlc.vscode-tailwindcss",    // Tailwind CSS 支持
    "esbenp.prettier-vscode",       // Prettier 格式化
    "dbaeumer.vscode-eslint",       // ESLint 检查
    "ms-vscode.vscode-typescript-next", // TypeScript 支持
    "antfu.iconify"                 // 图标预览
  ]
}
```

### 工作区设置

创建 `.vscode/settings.json`：
```json
{
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "files.associations": {
    "*.css": "tailwindcss"
  },
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ]
}
```

### 调试配置

创建 `.vscode/launch.json`：
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Tauri Development Debug",
      "type": "lldb",
      "request": "launch",
      "program": "${workspaceFolder}/src-tauri/target/debug/th-suite-mc-l10n",
      "args": [],
      "cwd": "${workspaceFolder}",
      "env": {
        "RUST_LOG": "debug"
      }
    }
  ]
}
```

## 性能优化

### 开发模式优化

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    hmr: {
      overlay: false  // 关闭错误遮罩层
    }
  },
  optimizeDeps: {
    include: ['antd', 'react', 'react-dom']  // 预构建依赖
  }
})
```

### 构建优化

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          antd: ['antd', '@ant-design/icons'],
        }
      }
    }
  }
})
```

## 故障排除

### 常见问题

#### 1. Tauri 开发模式启动失败
```bash
# 问题：Rust 编译错误
# 解决：
rustup update
cargo clean
pnpm tauri:dev
```

#### 2. 前端热重载不工作
```bash
# 问题：端口冲突
# 解决：
netstat -tulpn | grep 18001  # 检查端口占用
# 修改 vite.config.ts 中的端口配置
```

#### 3. TypeScript 类型错误
```bash
# 问题：组件类型不匹配或导入错误
# 解决：
pnpm add @types/node -D
pnpm type-check

# 确保使用正确的 Ant Design 组件导入
# 正确: import { Button, Card } from 'antd'
# 错误: import Button from '@mui/material/Button'
```

#### 4. 构建失败
```bash
# 问题：依赖版本冲突
# 解决：
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

#### 5. Material-UI 迁移相关问题
```bash
# 问题：仍然存在 Material-UI 相关错误
# 解决：
# 1. 检查是否有遗留的 MUI 导入
grep -r "@mui" src/
grep -r "material-ui" src/

# 2. 确保移除所有 MUI 依赖
pnpm remove @mui/material @mui/icons-material @emotion/react @emotion/styled

# 3. 清理缓存重新安装
rm -rf node_modules pnpm-lock.yaml
pnpm install

# 4. 检查 vite.config.ts 中的 Emotion 配置
# 确保移除: jsxImportSource: '@emotion/react'
```

### 调试技巧

#### 1. 前端调试
```tsx
// 在组件中添加调试信息
console.log('Component render:', { props, state })

// 使用 React DevTools
// 浏览器扩展：React Developer Tools
```

#### 2. Tauri 后端调试
```rust
// src-tauri/src/main.rs
#[tauri::command]
fn my_command() {
    println!("Debug: command called");  // 控制台输出
}
```

#### 3. 网络请求调试
```typescript
// 在 services 中添加日志
const response = await api.get('/endpoint')
console.log('API Response:', response)
```

## 部署准备

### 开发构建
```bash
# 构建前端资源
pnpm build

# 构建 Tauri 应用（开发版）
pnpm tauri:build --debug
```

### 生产构建
```bash
# 设置生产环境
export NODE_ENV=production

# 构建前端资源
pnpm build

# 构建 Tauri 应用（生产版）
pnpm tauri:build
```

构建产物位置：
- **前端资源**: `dist/`
- **桌面应用**: `src-tauri/target/release/bundle/`

## 相关文档

- [前端 README](./README.md) - 完整的前端文档
- [组件使用指南](./COMPONENTS.md) - 组件开发规范
- [迁移指南](./MIGRATION.md) - 架构迁移说明
- [Tauri 官方文档](https://tauri.app/v1/guides/) - Tauri 开发指南
- [Ant Design 文档](https://ant.design/) - UI 组件库文档