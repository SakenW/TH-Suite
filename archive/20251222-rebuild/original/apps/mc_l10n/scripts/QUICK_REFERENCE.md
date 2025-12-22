# MC L10n CLI 快速参考

## 🚀 常用命令

```bash
# 启动服务
poetry run python mc_cli.py server start fullstack

# 扫描MOD目录
poetry run python mc_cli.py scan start ~/minecraft/mods --monitor

# 查看数据库统计
poetry run python mc_cli.py db info

# 启动Web查看器
poetry run python mc_cli.py db viewer
```

## 📊 数据库管理

| 命令 | 功能 |
|------|------|
| `db info` | 显示数据库统计信息 |
| `db viewer` | 启动Web管理界面 |
| `db export -o file.json` | 导出数据 |
| `db cleanup` | 清理过期缓存 |
| `db reset --force` | 重置数据库 |

## 🔍 扫描管理

| 命令 | 功能 |
|------|------|
| `scan start <path>` | 开始扫描 |
| `scan start <path> --full` | 全量扫描 |
| `scan start <path> --monitor` | 监控进度 |
| `scan status <id>` | 查看状态 |
| `scan list` | 列出活跃任务 |

## 🖥️ 服务管理

| 命令 | 功能 |
|------|------|
| `server start backend` | 启动后端 (18000) |
| `server start frontend` | 启动前端 (18001) |
| `server start fullstack` | 启动全栈 |
| `server stop` | 停止所有服务 |

## 🌐 访问地址

- **后端API**: http://localhost:18000/docs
- **前端界面**: http://localhost:18001
- **数据库查看器**: http://localhost:8080

## 💡 快速故障排除

```bash
# 服务无法启动 → 强制重启
poetry run python mc_cli.py server start fullstack --kill-old

# 数据库问题 → 查看详情并清理
poetry run python mc_cli.py db info
poetry run python mc_cli.py db cleanup

# 缓存问题 → 清理所有缓存
poetry run python mc_cli.py system cleanup
```

## 📈 当前状态 (最后更新: 2025-09-09)

- ✅ 数据库路径已修复
- ✅ Web查看器功能已集成
- ✅ 所有架构兼容性问题已解决
- 📊 564个MOD，3,573个语言文件，1,604,370个翻译条目