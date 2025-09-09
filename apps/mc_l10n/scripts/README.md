# MC L10n Scripts

MC L10n 统一命令行管理工具。

## 安装依赖

```bash
# 在项目根目录运行
task install

# 或手动安装
poetry install
cd ../frontend && pnpm install
```

## 使用方法

所有功能都通过统一的 `mc_cli.py` 工具访问：

```bash
# 使用 poetry 运行（推荐）
poetry run python mc_cli.py --help

# 或直接运行（需要先安装依赖）
python3 mc_cli.py --help

# 或使其可执行
chmod +x mc_cli.py
./mc_cli.py --help
```

## 功能模块

### 1. 服务管理

```bash
# 启动后端服务 (端口 18000)
poetry run python mc_cli.py server start backend

# 启动前端服务 (端口 18001)  
poetry run python mc_cli.py server start frontend

# 启动全栈服务（前端 + 后端）
poetry run python mc_cli.py server start fullstack

# 启动服务前先杀死旧进程
poetry run python mc_cli.py server start backend --kill-old
poetry run python mc_cli.py server start fullstack --kill-old

# 停止所有服务
poetry run python mc_cli.py server stop
```

### 2. 数据库管理

```bash
# 查看数据库信息和统计
python mc_cli.py db info

# 清理数据库（过期缓存 + VACUUM）
python mc_cli.py db cleanup

# 导出数据库内容
python mc_cli.py db export
python mc_cli.py db export -o my_export.json

# 重置数据库（会备份现有数据）
python mc_cli.py db reset
python mc_cli.py db reset --force  # 跳过确认
```

### 3. 扫描管理

```bash
# 启动扫描
python mc_cli.py scan start /path/to/mods
python mc_cli.py scan start /path/to/mods --full      # 全量扫描
python mc_cli.py scan start /path/to/mods --monitor    # 监控进度

# 查看扫描状态
python mc_cli.py scan status <scan_id>
python mc_cli.py scan status <scan_id> --monitor

# 列出活跃的扫描任务
python mc_cli.py scan list
```

### 4. 系统管理

```bash
# 查看系统信息
python mc_cli.py system info

# 清理系统缓存（__pycache__, *.pyc）
python mc_cli.py system cleanup
```

## 快速开始

```bash
# 1. 启动全栈服务
poetry run python mc_cli.py server start fullstack

# 2. 在新终端中扫描MOD目录
poetry run python mc_cli.py scan start ~/minecraft/mods --monitor

# 3. 查看数据库统计
poetry run python mc_cli.py db info
```

## 服务地址

- **后端API**: http://localhost:18000
- **API文档**: http://localhost:18000/docs
- **前端界面**: http://localhost:18001

## 特性

- 🎯 **统一入口**: 所有功能通过一个命令访问
- 🎨 **彩色输出**: 清晰的终端输出和进度显示
- 📊 **实时监控**: 支持扫描进度实时监控
- 💾 **数据管理**: 完整的数据库管理功能
- 🔧 **系统维护**: 缓存清理和系统信息查看

## 示例用例

### 完整的工作流程

```bash
# 1. 检查系统状态
python mc_cli.py system info

# 2. 启动服务
python mc_cli.py server start fullstack

# 3. 扫描MOD目录
python mc_cli.py scan start ~/minecraft/mods --monitor

# 4. 查看结果
python mc_cli.py db info

# 5. 导出数据
python mc_cli.py db export -o mods_data.json

# 6. 定期维护
python mc_cli.py db cleanup
python mc_cli.py system cleanup
```

### 开发调试

```bash
# 单独启动后端进行API开发
python mc_cli.py server start backend

# 单独启动前端进行UI开发
python mc_cli.py server start frontend

# 查看活跃的扫描任务
python mc_cli.py scan list
```

## 故障排除

1. **无法连接到服务器**: 确保后端服务已启动
   ```bash
   python mc_cli.py server start backend
   ```

2. **数据库错误**: 尝试重置数据库
   ```bash
   python mc_cli.py db reset
   ```

3. **缓存问题**: 清理系统缓存
   ```bash
   python mc_cli.py system cleanup
   python mc_cli.py db cleanup
   ```

## 注意事项

- 数据库文件位置: `backend/data/mc_l10n.db`
- 重置数据库前会自动创建备份
- 全栈模式下按 Ctrl+C 会停止所有服务
- 扫描大型MOD目录时建议使用增量模式（默认）

## 已弃用的脚本

旧的独立脚本已移至 `deprecated/` 目录，请使用新的统一CLI工具。