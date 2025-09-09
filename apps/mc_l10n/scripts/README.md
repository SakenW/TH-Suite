# MC L10n Scripts

MC L10n 统一命令行管理工具 - 提供完整的项目管理、扫描、数据库操作和系统维护功能。

📋 **快速开始**: [查看快速参考](./QUICK_REFERENCE.md) | 📖 **详细文档**: 继续阅读下方内容

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

# 🆕 启动数据库Web查看器
python mc_cli.py db viewer
python mc_cli.py db viewer --port 8080
python mc_cli.py db viewer --no-browser  # 不自动打开浏览器
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

# 清理系统缓存（__pycache__、*.pyc 文件）
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
- **数据库查看器**: http://localhost:8080 (可配置端口)

## 特性

- 🎯 **统一入口**: 所有功能通过一个命令访问
- 🎨 **彩色输出**: 清晰的终端输出和进度显示
- 📊 **实时监控**: 支持扫描进度实时监控
- 💾 **数据管理**: 完整的数据库管理功能
- 🌐 **Web界面**: 高级数据库Web查看器
- 🔧 **系统维护**: 缓存清理和系统信息查看
- 📈 **统计分析**: 详细的MOD、语言文件和翻译条目统计

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

# 5. 启动Web查看器进行详细分析
python mc_cli.py db viewer

# 6. 导出数据
python mc_cli.py db export -o mods_data.json

# 7. 定期维护
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

- 数据库文件位置: `backend/mc_l10n.db` (主数据库)
- 重置数据库前会自动创建备份
- 全栈模式下按 Ctrl+C 会停止所有服务
- 扫描大型MOD目录时建议使用增量模式（默认）
- 数据库查看器提供完整的Web管理界面

## 数据库Web查看器功能

通过 `python mc_cli.py db viewer` 启动的Web界面提供：

- 📊 **完整统计**: MOD数量、语言文件、翻译条目统计
- 🔍 **数据浏览**: 表格化浏览所有数据表
- 📈 **可视化分析**: 图表展示数据分布
- 🛠️ **管理工具**: 数据操作和维护功能
- 📁 **项目管理**: 扫描历史和项目组织
- 🌍 **多语言支持**: 语言文件和翻译状态管理

### Web查看器使用示例

```bash
# 启动查看器（默认端口8080）
python mc_cli.py db viewer

# 使用自定义端口
python mc_cli.py db viewer --port 9000

# 后台模式（不打开浏览器）
python mc_cli.py db viewer --no-browser
```

## 最新更新 (2025-09-09)

### 🔧 修复内容
- ✅ 修复数据库路径配置错误
- ✅ 解决 "no such column: language_code" 错误
- ✅ 统计计算中的 NoneType 除法错误修复
- ✅ 数据库查看器路径更新

### 🆕 新增功能
- ✅ 集成数据库Web查看器命令
- ✅ 自动浏览器打开功能
- ✅ 可配置端口和主机设置
- ✅ 完善的命令行帮助信息

### 📊 当前数据统计
- MOD数量: 564个
- 语言文件: 3,573个
- 翻译条目: 1,604,370个
- 数据库大小: 616.70 MB

## 已弃用的脚本

旧的独立脚本已移至 `deprecated/` 目录，请使用新的统一CLI工具。