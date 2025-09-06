# MC L10n Scripts - 管理工具集

本目录包含MC L10n项目的所有管理脚本和工具。

## 🚀 快速开始

### mc_l10n.py - 统一入口管理器（新增）

所有工具都可以通过 `mc_l10n.py` 统一入口访问：

```bash
# 查看所有可用工具
python3 mc_l10n.py --list

# 检查环境配置
python3 mc_l10n.py --check

# 启动全栈服务
python3 mc_l10n.py start
```

### manage.py - 服务管理器

兼容旧版的服务管理入口：

```bash
# 启动后端服务 (端口 18000)
python manage.py backend

# 启动前端服务 (端口 5173)
python manage.py frontend

# 启动全栈服务
python manage.py fullstack
```

## 📋 常用命令

### 1. 扫描管理

```bash
# 启动扫描并监控进度
python3 mc_l10n.py scan start /path/to/mods --monitor

# 查看活跃的扫描任务
python3 mc_l10n.py scan list

# 获取扫描状态
python3 mc_l10n.py scan status <scan_id>
```

### 2. 数据库操作

```bash
# 查看数据库统计
python3 mc_l10n.py db stats

# 列出所有模组
python3 mc_l10n.py db list

# 搜索翻译
python3 mc_l10n.py db search "关键词"

# 导出模组翻译
python3 mc_l10n.py db export <mod_id>
```

### 3. 数据库传输

```bash
# 备份数据库
python3 mc_l10n.py db-transfer backup

# 导出到JSON
python3 mc_l10n.py db-transfer export-json

# 导出翻译到CSV（便于编辑）
python3 mc_l10n.py db-transfer export-csv
```

## 🎯 服务地址

- **前端**: http://localhost:5173
- **后端**: http://localhost:18000  
- **API 文档**: http://localhost:18000/docs

## 💡 使用建议

### 扫描最佳实践

1. **首次扫描**：使用全量模式
   ```bash
   python3 mc_l10n.py scan start /path/to/mods --full --monitor
   ```

2. **增量扫描**：后续使用增量模式（默认）
   ```bash
   python3 mc_l10n.py scan start /path/to/mods --monitor
   ```

3. **检查扫描结果**：
   ```bash
   # 查看数据库统计
   python3 mc_l10n.py db stats
   
   # 列出扫描到的模组
   python3 mc_l10n.py db list
   ```

### 数据库维护

1. **定期备份**
   ```bash
   python3 mc_l10n.py db-transfer backup
   ```

2. **导出数据**
   ```bash
   python3 mc_l10n.py db-transfer export-json
   ```

## 🐛 常见问题

### Q: 扫描显示成功但数据库为空？

A: 这通常是因为扫描结果没有正确保存到数据库。检查：

1. **确认扫描找到了JAR文件**
   ```bash
   # 查看后端日志
   tail -f ../backend/logs/*.log
   ```

2. **检查数据库表结构**
   ```bash
   python3 mc_l10n.py db-audit
   ```

3. **手动触发扫描并观察日志**
   ```bash
   python3 mc_l10n.py scan start /your/mods/path --monitor
   ```

4. **检查数据库文件权限**
   ```bash
   ls -la ../backend/mc_l10n.db
   ```

### Q: 前端显示扫描进度但没有结果？

A: 可能是前后端数据同步问题：

1. 重启后端服务
2. 清除浏览器缓存
3. 检查网络请求是否正常

---
## 📂 工具文件说明

  已成功统一并整理了所有启动脚本：

  📂 新的统一结构：

  /home/saken/project/TH-Suite/apps/mc_l10n/scripts/
  ├── 🎯 manage.py          # 主管理器 (推荐使用)
  ├── 🚀 start_backend.py   # 智能后端启动器
  ├── 🎨 start_frontend.py  # 前端启动器
  ├── 📦 start_fullstack.py # 全栈启动器
  ├── 🧹 cleanup.py         # 进程清理器
  ├── 📖 README.md          # 使用说明
  └── deprecated/           # 已弃用的旧脚本

  🎯 统一使用方式：

  cd /home/saken/project/TH-Suite/apps/mc_l10n/scripts

  # 🚀 启动全栈开发环境 (推荐)
  python manage.py fullstack

  # 🔧 仅启动后端
  python manage.py backend

  # 🎨 仅启动前端  
  python manage.py frontend

  # 🧹 清理所有进程
  python manage.py cleanup

  # ❓ 查看帮助
  python manage.py help

  ✅ 解决的问题：

  1. ✅ 去重: 移除了 6 个重复的启动脚本
  2. ✅ 统一: 所有脚本集中在 scripts/ 目录
  3. ✅ 智能: 自动检测和清理卡死进程
  4. ✅ 固定端口: 默认端口不再随机改变
    - 后端: 18000 (固定)
    - 前端: 5173 (固定)
  5. ✅ 简化: 一个命令搞定所有启动场景

  现在你可以使用统一的管理器来启动服务，不再需要记忆多个不同的脚本名称！