# Tauri 应用打包成 exe 文件指南

本文档详细介绍如何将基于 Tauri 的桌面应用程序打包成 Windows exe 可执行文件。

## 目录

- [环境要求](#环境要求)
- [项目准备](#项目准备)
- [构建步骤](#构建步骤)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [高级配置](#高级配置)

## 环境要求

### 必需环境

1. **Node.js**
   - 版本：16.0 或更高
   - 下载地址：[https://nodejs.org/](https://nodejs.org/)
   - 验证安装：`node --version`

2. **Rust**
   - 下载地址：[https://rustup.rs/](https://rustup.rs/)
   - 安装后重启终端
   - 验证安装：`rustc --version`

3. **Microsoft C++ Build Tools**（Windows 必需）
   - Visual Studio Build Tools 或 Visual Studio Community
   - 确保包含 "C++ build tools" 工作负载
   - 或安装 "Desktop development with C++" 工作负载

### 可选工具

- **Git**：用于版本控制
- **VS Code**：推荐的代码编辑器

## 项目准备

### 1. 项目结构

确保你的 Tauri 项目具有以下基本结构：

```
project-root/
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/
│       └── main.rs
├── src/
│   └── (前端源码)
├── dist/
│   └── (构建输出)
└── package.json
```

### 2. 检查配置文件

#### package.json

确保包含必要的脚本：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "tauri": "tauri",
    "tauri:dev": "tauri dev",
    "tauri:build": "tauri build"
  }
}
```

#### tauri.conf.json

关键配置项：

```json
{
  "build": {
    "beforeBuildCommand": "npm run build",
    "beforeDevCommand": "npm run dev",
    "devPath": "http://localhost:5173",
    "distDir": "./dist"
  },
  "package": {
    "productName": "Your App Name",
    "version": "1.0.0"
  },
  "tauri": {
    "bundle": {
      "active": true,
      "targets": "all",
      "identifier": "com.yourcompany.yourapp",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/icon.ico"
      ]
    }
  }
}
```

## 构建步骤

### 1. 安装依赖

```bash
# 安装 Node.js 依赖
npm install

# 如果使用 yarn
yarn install
```

### 2. 构建前端资源

```bash
# 构建前端应用
npm run build

# 验证 dist 目录是否生成
ls dist/
```

### 3. 执行 Tauri 构建

```bash
# 构建 Tauri 应用
npm run tauri:build

# 或直接使用 tauri 命令
tauri build
```

### 4. 查找构建输出

构建完成后，可执行文件位于：

- **主程序**：`src-tauri/target/release/your-app-name.exe`
- **安装包**：`src-tauri/target/release/bundle/msi/your-app-name_1.0.0_x64_en-US.msi`
- **其他格式**：`src-tauri/target/release/bundle/` 目录下

## 配置说明

### 应用图标

1. 准备图标文件：
   - `icon.ico`（Windows）
   - `icon.icns`（macOS）
   - 多种 PNG 尺寸（32x32, 128x128, 256x256 等）

2. 放置在 `src-tauri/icons/` 目录

3. 在 `tauri.conf.json` 中配置：

```json
{
  "tauri": {
    "bundle": {
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ]
    }
  }
}
```

### 应用权限

根据应用需求配置 API 权限：

```json
{
  "tauri": {
    "allowlist": {
      "all": false,
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "readDir": true
      },
      "dialog": {
        "all": false,
        "open": true,
        "save": true
      },
      "shell": {
        "all": false,
        "open": true
      }
    }
  }
}
```

### 窗口配置

```json
{
  "tauri": {
    "windows": [
      {
        "title": "Your App Name",
        "width": 1200,
        "height": 800,
        "minWidth": 800,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false,
        "center": true
      }
    ]
  }
}
```

## 常见问题

### 1. Rust 未安装

**错误信息**：
```
rustc : 无法将"rustc"项识别为 cmdlet、函数、脚本文件或可运行程序的名称
```

**解决方案**：
1. 访问 [https://rustup.rs/](https://rustup.rs/) 安装 Rust
2. 重启终端或命令提示符
3. 验证安装：`rustc --version`

### 2. 构建工具缺失

**错误信息**：
```
link.exe not found
```

**解决方案**：
1. 安装 Visual Studio Build Tools
2. 确保包含 C++ 构建工具
3. 重启系统

### 3. 路径配置错误

**错误信息**：
```
Input watch path is neither a file nor a directory
```

**解决方案**：
1. 检查 `tauri.conf.json` 中的 `distDir` 路径
2. 确保前端构建输出目录存在
3. 使用相对路径：`"./dist"`

### 4. 依赖版本冲突

**错误信息**：
```
Expected "0.25.9" but got "0.18.20"
```

**解决方案**：
1. 清理 npm 缓存：`npm cache clean --force`
2. 删除 `node_modules`：`rm -rf node_modules`
3. 重新安装：`npm install`

### 5. TypeScript 编译错误

**解决方案**：
1. 修复类型错误（推荐）
2. 临时跳过类型检查：修改构建脚本为 `"build": "vite build"`

## 高级配置

### 1. 自定义构建目标

```json
{
  "tauri": {
    "bundle": {
      "targets": ["msi", "nsis"]
    }
  }
}
```

### 2. 代码签名

```json
{
  "tauri": {
    "bundle": {
      "windows": {
        "certificateThumbprint": "YOUR_CERTIFICATE_THUMBPRINT",
        "digestAlgorithm": "sha256",
        "timestampUrl": "http://timestamp.digicert.com"
      }
    }
  }
}
```

### 3. 自动更新

```json
{
  "tauri": {
    "updater": {
      "active": true,
      "endpoints": [
        "https://your-update-server.com/{{target}}/{{current_version}}"
      ],
      "dialog": true,
      "pubkey": "YOUR_PUBLIC_KEY"
    }
  }
}
```

### 4. 系统托盘

```json
{
  "tauri": {
    "systemTray": {
      "iconPath": "icons/icon.png",
      "iconAsTemplate": true
    }
  }
}
```

## 构建优化

### 1. 减小文件大小

在 `Cargo.toml` 中添加：

```toml
[profile.release]
lto = true
codegen-units = 1
panic = "abort"
strip = true
```

### 2. 并行构建

```bash
# 使用多核心构建
cargo build --release --jobs 4
```

### 3. 缓存优化

```bash
# 使用 sccache 加速 Rust 编译
cargo install sccache
export RUSTC_WRAPPER=sccache
```

## 分发建议

1. **测试**：在干净的 Windows 环境中测试 exe 文件
2. **文档**：提供安装和使用说明
3. **签名**：为生产环境的应用程序进行代码签名
4. **更新机制**：考虑实现自动更新功能
5. **错误报告**：集成崩溃报告和错误追踪

## 总结

通过以上步骤，你应该能够成功将 Tauri 应用打包成 Windows exe 文件。关键是确保所有必需的环境都已正确安装，并且项目配置文件设置正确。

如果遇到问题，请检查：
1. 环境安装是否完整
2. 配置文件是否正确
3. 构建日志中的具体错误信息
4. 参考官方文档：[https://tauri.app/](https://tauri.app/)