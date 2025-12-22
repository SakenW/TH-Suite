# MC L10n Scripts

MC L10n 简化命令行管理工具 - 提供核心功能，去除冗余特性。

## 安装依赖

```bash
# 在项目根目录运行
task install

# 或手动安装
poetry install
cd ../frontend && pnpm install
```

## 使用方法

所有功能都通过简化的 `mc_cli.py` 工具访问：

```bash
# 使用 poetry 运行（推荐）
poetry run python mc_cli.py --help

# 或直接运行（需要先安装依赖）
python3 mc_cli.py --help

# 或使其可执行
chmod +x mc_cli.py
./mc_cli.py --help
```

## 核心功能

### 1. 服务管理

```bash
# 启动后端服务 (端口 18000)
poetry run python mc_cli.py start backend

# 启动前端服务 (端口 18001)  
poetry run python mc_cli.py start frontend

# 启动全栈服务（前端 + 后端）
poetry run python mc_cli.py start fullstack

# 停止所有服务
poetry run python mc_cli.py stop
```

### 2. 数据库状态

```bash
# 查看数据库基本状态
python mc_cli.py db

# 启动数据库Web查看器
python mc_cli.py viewer
```

## 快速开始

```bash
# 1. 启动全栈服务
poetry run python mc_cli.py start fullstack

# 2. 查看数据库状态
python mc_cli.py db

# 3. 启动数据库查看器
python mc_cli.py viewer
```

## 服务地址

- **后端API**: http://localhost:18000
- **API文档**: http://localhost:18000/docs
- **前端界面**: http://localhost:18001
- **数据库查看器**: http://localhost:8080 (默认端口)

## 简化特性

- 🎯 **简洁命令**: 核心功能简化为4个主要命令
- 🎨 **彩色输出**: 清晰的终端状态显示
- 🌐 **Web界面**: 数据库Web查看器
- 📊 **基础统计**: 数据库表和大小信息

## 故障排除

1. **无法连接到服务器**: 确保后端服务已启动
   ```bash
   python mc_cli.py start backend
   ```

2. **端口占用**: 停止所有服务后重新启动
   ```bash
   python mc_cli.py stop
   python mc_cli.py start fullstack
   ```

## 注意事项

- 数据库文件位置: `backend/data/mc_l10n_v6.db` (V6架构数据库)
- 全栈模式下按 Ctrl+C 会停止所有服务
- 数据库查看器默认端口8080

## 备份文件

复杂的原版CLI工具已保存为 `mc_cli_complex_backup.py`，如需高级功能可参考使用。