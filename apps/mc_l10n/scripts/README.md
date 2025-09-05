# MC L10n 脚本管理系统 v2.0

本目录包含 MC L10n 应用的统一脚本管理系统，支持跨平台运行。

## 🌟 主要特性

- **统一管理器**: `manager.py` - 跨平台的服务管理工具
- **数据库审计**: `db_audit.py` - Web界面的数据库审计工具
- **跨平台支持**: 同时提供 .bat (Windows) 和 .sh (Linux/Mac) 脚本
- **结构化日志**: 所有脚本使用统一的JSON日志格式

## 📁 脚本文件列表

### 统一管理器 （推荐）

| 脚本名称 | 功能说明 | 支持平台 |
|---------|---------|---------|
| `manager.py` | 🎆 **统一管理器**：完整的服务管理工具 | 全平台 |
| `db_audit.py` | 🔍 **数据库审计**：Web UI 数据库查看器 | 全平台 |

### Windows 脚本

| 脚本名称 | 功能说明 |
|---------|---------|
| `start-all.bat` | 🚀 完整启动（后端 + 桌面应用） |
| `start-all-web.bat` | 🌐 Web模式（后端 + 浏览器） |
| `start-backend.bat` | 🔧 仅启动后端服务 |
| `start-frontend.bat` | 🖥️ 仅启动桌面前端 |
| `start-frontend-web.bat` | 🌏 仅启动Web前端 |
| `stop-all.bat` | ⏹️ 停止所有服务 |

### Linux/Mac 脚本

| 脚本名称 | 功能说明 |
|---------|---------|
| `start-all.sh` | 🚀 完整启动（后端 + 桌面应用） |
| `start-backend.sh` | 🔧 仅启动后端服务 |
| `stop-all.sh` | ⏹️ 停止所有服务 |

## 🚀 快速开始

### 使用统一管理器（最推荐）

```bash
# 检查依赖
python manager.py check

# 启动所有服务（桌面模式）
python manager.py start --mode tauri

# 启动所有服务（Web模式）
python manager.py start --mode web

# 单独启动服务
python manager.py backend       # 仅后端
python manager.py frontend      # 仅前端
python manager.py db-viewer     # 数据库查看器

# 查看服务状态
python manager.py status

# 停止所有服务
python manager.py stop

# 重启所有服务
python manager.py restart
```

### 使用平台特定脚本

#### Windows
```batch
cd apps\mc_l10n\scripts
start-all.bat          # 桌面应用
start-all-web.bat      # Web模式
```

#### Linux/Mac
```bash
cd apps/mc_l10n/scripts
./start-all.sh         # 桌面应用
./start-backend.sh     # 仅后端
```

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
| 前端开发服务器 | 5173 | http://localhost:5173 |
| 数据库查看器 | 18081 | http://localhost:18081 |
| 数据库审计工具 | 18082 | http://localhost:18082 |

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

## 🛠️ 数据库审计工具

### 启动审计工具
```bash
# 使用默认设置
python db_audit.py

# 指定端口和数据库
python db_audit.py --port 18082 --db ../backend/mc_l10n.db
```

### 功能特性
- 📊 实时数据库统计
- 🔍 表数据浏览和搜索
- 📥 数据导出（JSON/CSV）
- 📋 执行SQL查询（只读）
- 🎨 美观的Web界面

### 访问地址
- 默认: http://localhost:18082
- 支持分页、排序、搜索
- 可导出数据为JSON或CSV格式

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

### 使用管理器
```bash
# 查看所有服务状态
python manager.py status

# 停止所有服务
python manager.py stop
```

### 手动检查

#### Windows
```batch
# 查看端口占用
netstat -an | findstr :18000
netstat -an | findstr :5173

# 停止服务
stop-all.bat
```

#### Linux/Mac
```bash
# 查看端口占用
lsof -i:18000
lsof -i:5173

# 停止服务
./stop-all.sh
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