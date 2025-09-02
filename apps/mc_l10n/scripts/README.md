# MC L10n 启动脚本说明

本目录包含 MC L10n 应用的所有启动脚本，使用统一的日志格式输出。

## 📁 脚本文件列表

| 脚本名称 | 功能说明 | 使用场景 |
|---------|---------|---------|
| `start-all.bat` | 🚀 **完整启动**：后端 + 桌面应用 | 日常开发推荐 |
| `start-all-web.bat` | 🌐 **Web模式**：后端 + 浏览器前端 | 无需 Tauri/Rust |
| `start-backend.bat` | 🔧 仅启动后端服务 | 后端开发/调试 |
| `start-frontend.bat` | 🖥️ 仅启动桌面前端 | 前端开发（需要后端已运行） |
| `start-frontend-web.bat` | 🌏 仅启动Web前端 | 前端开发（浏览器模式） |
| `stop-all.bat` | ⏹️ 停止所有服务 | 清理进程 |

## 🚀 快速开始

### 完整应用启动（推荐）
```bash
cd apps\mc_l10n\scripts
start-all.bat
```
这将：
1. 在新窗口启动后端服务器（端口 8000）
2. 在当前窗口启动桌面应用

### Web模式启动（无需Rust环境）
```bash
cd apps\mc_l10n\scripts
start-all-web.bat
```
然后打开浏览器访问：http://localhost:5173

## 📝 日志格式

所有脚本使用统一的日志格式：
```
[时间] [级别] 消息内容
```

日志级别：
- `[INFO]` - 一般信息
- `[WARN]` - 警告信息
- `[ERROR]` - 错误信息

## 🔍 服务端口

| 服务 | 端口 | 访问地址 |
|-----|------|---------|
| 后端 API | 18000 | http://localhost:18000 |
| API 文档 | 18000 | http://localhost:18000/docs |
| 前端开发服务器 | 15173 | http://localhost:15173 |

## 🛠️ 环境要求

### 后端
- Python 3.12+
- Poetry（依赖管理）

### 前端（桌面模式）
- Node.js 18+
- Rust toolchain（用于 Tauri）
- Visual Studio Build Tools（Windows）

### 前端（Web模式）
- Node.js 18+（仅需要这个）

## 🆘 常见问题

### 1. Poetry 未找到
```
[ERROR] Poetry not found! Please install Poetry first.
```
**解决方案**：安装 Poetry
```bash
# Windows PowerShell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### 2. Node.js 未找到
```
[ERROR] Node.js not found! Please install Node.js first.
```
**解决方案**：从 https://nodejs.org/ 下载安装 Node.js

### 3. 端口被占用
```
[ERROR] Port 8000 is already in use
```
**解决方案**：运行 `stop-all.bat` 清理进程

### 4. Tauri 构建失败
**解决方案**：使用 Web 模式启动（`start-all-web.bat`）

## 📊 进程管理

查看运行中的服务：
```bash
# 查看后端进程
netstat -an | findstr :8000

# 查看前端进程
netstat -an | findstr :5173
```

停止所有服务：
```bash
cd apps\mc_l10n\scripts
stop-all.bat
```

## 🔄 更新依赖

后端依赖更新：
```bash
cd apps\mc_l10n\backend
poetry update
```

前端依赖更新：
```bash
cd apps\mc_l10n\frontend
npm update
```