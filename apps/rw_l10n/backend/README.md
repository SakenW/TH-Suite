# RW Studio Backend

> 🌐 Rusted Warfare 本地化工具的后端服务

RW Studio Backend 是基于 FastAPI 构建的高性能后端服务，为 Rusted Warfare 游戏本地化和翻译管理提供全面的 API 支持。

## ✨ 功能特性

### 🌐 本地化管理
- **游戏文本提取**: 从游戏文件中提取可翻译文本
- **模组翻译**: Steam Workshop 模组的本地化支持
- **翻译记忆**: 翻译记忆库管理和复用
- **术语管理**: 游戏术语库维护和一致性检查
- **质量保证**: 翻译质量检查和验证工具

### 🔧 技术特性
- **异步处理**: 基于 asyncio 的高性能异步架构
- **实时通信**: WebSocket 支持实时状态更新
- **任务管理**: 后台任务队列和进度跟踪
- **缓存系统**: Redis 缓存提升性能
- **日志系统**: 结构化日志和错误追踪

### 🔌 API 功能
- **RESTful API**: 完整的翻译管理 API
- **WebSocket**: 实时翻译协作和通知
- **文件管理**: 语言文件的上传、下载、管理
- **Steam 集成**: Steam Workshop 模组本地化支持
- **任务队列**: 异步翻译任务处理（Celery）

## 技术栈

- **Web 框架**: FastAPI 0.104+
- **ASGI 服务器**: Uvicorn
- **数据验证**: Pydantic 2.5+
- **数据库**: SQLite/PostgreSQL (SQLAlchemy)
- **缓存**: Redis
- **任务队列**: Celery
- **日志**: Loguru
- **文件处理**: aiofiles
- **HTTP 客户端**: httpx, aiohttp

## 项目结构

```
rw-studio/backend/
├── main.py                 # 应用入口
├── requirements.txt        # Python 依赖
├── config/
│   └── app_config.toml    # 应用配置
├── api/                   # API 路由
│   ├── __init__.py       # 主路由
│   ├── mods.py           # 模组管理 API
│   ├── workshop.py       # Workshop API
│   ├── saves.py          # 存档管理 API
│   ├── config.py         # 配置管理 API
│   └── system.py         # 系统信息 API
├── services/             # 业务逻辑服务
│   ├── __init__.py
│   ├── mod_service.py    # 模组服务
│   ├── workshop_service.py # Workshop 服务
│   ├── save_game_service.py # 存档服务
│   └── config_service.py # 配置服务
├── websocket/            # WebSocket 支持
│   ├── __init__.py      # WebSocket 路由
│   └── manager.py       # 连接管理器
├── dependencies.py       # 依赖注入
├── data/                # 数据目录
├── logs/                # 日志目录
├── temp/                # 临时文件
├── backups/             # 备份目录
└── cache/               # 缓存目录
```

## 快速开始

### 环境要求

- Python 3.9+
- Redis (可选，用于缓存)
- RimWorld 游戏安装

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置设置

1. 复制配置文件:
```bash
cp config/app_config.toml.example config/app_config.toml
```

2. 编辑配置文件 `config/app_config.toml`:
```toml
[app]
port = 8002
host = "127.0.0.1"
debug = true

[game]
default_install_path = "C:/Program Files (x86)/Steam/steamapps/common/RimWorld"

[steam]
api_key = "your-steam-api-key"  # 可选
```

### 启动服务

```bash
# 开发模式
python main.py

# 或使用 uvicorn
uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

服务启动后访问:
- API 文档: http://127.0.0.1:8002/docs
- ReDoc 文档: http://127.0.0.1:8002/redoc
- 健康检查: http://127.0.0.1:8002/api/system/health

## API 接口

### 模组管理

```bash
# 获取模组列表
GET /api/mods

# 安装模组
POST /api/mods/install
{
  "mod_id": "workshop_id_or_local_path",
  "source": "workshop"
}

# 启用/禁用模组
PATCH /api/mods/{mod_id}/toggle
```

### Workshop 管理

```bash
# 搜索 Workshop 内容
GET /api/workshop/search?query=keyword

# 订阅 Workshop 物品
POST /api/workshop/subscribe
{
  "item_id": "workshop_item_id"
}

# 同步 Workshop 内容
POST /api/workshop/sync
```

### 存档管理

```bash
# 获取存档列表
GET /api/saves

# 备份存档
POST /api/saves/{save_id}/backup

# 分析存档
GET /api/saves/{save_id}/analyze
```

### 配置管理

```bash
# 获取配置
GET /api/config?type=app

# 更新配置
PATCH /api/config
{
  "type": "game",
  "data": { "game_path": "/path/to/rimworld" }
}
```

## WebSocket 连接

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://127.0.0.1:8002/ws/client_id');

// 监听消息
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('收到消息:', message);
};

// 发送心跳
ws.send(JSON.stringify({
  type: 'ping',
  data: { timestamp: Date.now() }
}));
```

## 开发指南

### 添加新的 API 端点

1. 在 `api/` 目录下创建或编辑路由文件
2. 在 `services/` 目录下实现业务逻辑
3. 在 `api/__init__.py` 中注册路由

### 添加新的服务

1. 在 `services/` 目录下创建服务类
2. 在 `dependencies.py` 中添加依赖注入
3. 在需要的地方使用 `Depends()` 注入服务

### WebSocket 消息处理

1. 在 `websocket/manager.py` 中定义消息类型
2. 在 `websocket/__init__.py` 中添加消息处理函数
3. 使用 `websocket_manager` 发送消息

## 部署

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### 生产环境

```bash
# 使用 gunicorn + uvicorn workers
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8002
```

## 监控和日志

### 日志配置

日志文件位置: `logs/rw-studio.log`

日志级别:
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 性能监控

```bash
# 获取系统性能指标
GET /api/system/metrics

# 获取任务状态
GET /api/system/tasks
```

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -ano | findstr :8002
   # 修改配置文件中的端口
   ```

2. **Redis 连接失败**
   ```bash
   # 检查 Redis 服务状态
   redis-cli ping
   # 或在配置中禁用 Redis
   ```

3. **游戏路径检测失败**
   ```bash
   # 手动设置游戏路径
   PATCH /api/config
   {
     "type": "game",
     "data": { "game_path": "/path/to/rimworld" }
   }
   ```

4. **模组安装失败**
   - 检查网络连接
   - 验证 Steam API 密钥
   - 确认游戏路径正确

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python main.py
```

## 贡献指南

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交 Pull Request

## 许可证

MIT License - 详见 [LICENSE](../../../LICENSE) 文件。

## 支持

如有问题或建议，请提交 [Issue](https://github.com/your-repo/issues)。