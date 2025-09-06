# MC L10n 部署指南

**版本**: 1.0.0  
**更新日期**: 2025-09-06

## 📋 概述

本指南描述如何部署MC L10n应用程序，包括开发环境、测试环境和生产环境的配置。

## 🔧 系统要求

### 最低要求

- **操作系统**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python**: 3.12+
- **Node.js**: 18+
- **内存**: 4GB RAM
- **存储**: 2GB 可用空间
- **网络**: 用于同步功能（可选）

### 推荐配置

- **内存**: 8GB+ RAM
- **存储**: 10GB+ 可用空间（大型MOD包）
- **CPU**: 4核心以上（并发扫描）
- **SSD**: 提升数据库性能

## 🚀 快速部署

### 1. 开发环境

```bash
# 克隆项目
git clone https://github.com/transhub/th-suite.git
cd th-suite

# 安装Python依赖
poetry install

# 安装前端依赖
cd apps/mc_l10n/frontend
pnpm install

# 初始化数据库
cd ../backend
python database/init_local_db.py --reset

# 启动开发服务器
poetry run python main.py  # 后端
npm run tauri:dev          # 前端（另一个终端）
```

### 2. 生产环境

#### 构建桌面应用

```bash
# 构建Tauri应用
cd apps/mc_l10n/frontend
npm run tauri:build

# 输出位置
# Windows: src-tauri/target/release/bundle/msi/
# macOS: src-tauri/target/release/bundle/dmg/
# Linux: src-tauri/target/release/bundle/appimage/
```

#### 构建后端服务

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate      # Windows

# 安装生产依赖
pip install -r requirements.txt

# 运行生产服务器
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📦 Docker部署

### 后端服务

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# 复制应用代码
COPY apps/mc_l10n/backend ./

# 初始化数据库
RUN python database/init_local_db.py

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 构建和运行

```bash
# 构建镜像
docker build -t mc-l10n-backend .

# 运行容器
docker run -d \
  --name mc-l10n \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  mc-l10n-backend
```

## ⚙️ 配置管理

### 环境变量

```bash
# .env文件
# 数据库配置
DATABASE_PATH=mc_l10n_local.db
DATABASE_ENCRYPTION_KEY=your-secret-key

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Trans-Hub连接
TRANSHUB_URL=http://localhost:8001
TRANSHUB_API_KEY=your-api-key

# 缓存配置
CACHE_TTL=86400
MAX_CACHE_SIZE=1073741824

# 同步配置
AUTO_SYNC=false
SYNC_INTERVAL=300
CONFLICT_RESOLUTION=client_wins
```

### 本地设置

通过CLI工具配置：

```bash
# 设置缓存过期时间
python database/db_cli.py set-config cache_ttl 86400

# 启用自动同步
python database/db_cli.py set-config auto_sync true

# 设置同步间隔
python database/db_cli.py set-config sync_interval 300
```

## 🔄 数据库管理

### 初始化

```bash
# 首次初始化
python database/init_local_db.py

# 重置数据库
python database/init_local_db.py --reset
```

### 备份与恢复

```bash
# 备份数据库
cp mc_l10n_local.db mc_l10n_backup_$(date +%Y%m%d).db

# 恢复数据库
cp mc_l10n_backup_20250906.db mc_l10n_local.db

# 导出离线变更
python database/db_cli.py export-changes changes_backup.json

# 导入离线变更
python database/db_cli.py import-changes changes_backup.json
```

### 维护任务

```bash
# 清理过期缓存
python database/db_cli.py cleanup

# 查看数据库统计
python database/db_cli.py stats

# 压缩数据库
sqlite3 mc_l10n_local.db "VACUUM;"
```

## 🌐 网络配置

### 端口配置

| 服务 | 默认端口 | 用途 |
|------|---------|------|
| FastAPI | 8000 | 后端API服务 |
| Tauri Dev | 5173 | 前端开发服务器 |
| WebSocket | 8000 | 实时通信 |
| DB Viewer | 18081 | 数据库查看工具 |

### 防火墙规则

```bash
# Linux (ufw)
sudo ufw allow 8000/tcp

# Windows (PowerShell管理员)
New-NetFirewallRule -DisplayName "MC L10n API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### 反向代理 (Nginx)

```nginx
server {
    listen 80;
    server_name mc-l10n.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

## 📊 监控和日志

### 日志配置

```python
# 日志级别设置
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mc_l10n.log'),
        logging.StreamHandler()
    ]
)
```

### 性能监控

```bash
# 监控数据库大小
du -sh mc_l10n_local.db

# 监控内存使用
ps aux | grep python | grep main.py

# 监控API响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/database/statistics
```

### 健康检查

```bash
# API健康检查
curl http://localhost:8000/health

# 数据库健康检查
python -c "
import sqlite3
conn = sqlite3.connect('mc_l10n_local.db')
print('Database OK')
conn.close()
"
```

## 🔒 安全配置

### 数据库加密

```python
# 使用SQLCipher加密数据库
import sqlcipher3
conn = sqlcipher3.connect('mc_l10n_encrypted.db')
conn.execute("PRAGMA key = 'your-encryption-key'")
```

### API认证

```python
# 添加API密钥认证
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != "your-secure-api-key":
        raise HTTPException(status_code=403, detail="Invalid API Key")
```

### HTTPS配置

```bash
# 生成自签名证书（开发环境）
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 使用HTTPS运行
uvicorn main:app --ssl-keyfile=./key.pem --ssl-certfile=./cert.pem
```

## 🚨 故障排除

### 常见问题

#### 1. 数据库锁定错误

```bash
# 错误: database is locked
# 解决方案:
killall python  # 终止所有Python进程
rm mc_l10n_local.db-journal  # 删除日志文件
```

#### 2. 端口被占用

```bash
# 错误: [Errno 48] Address already in use
# 查找占用进程
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# 终止进程
kill -9 <PID>  # Linux/macOS
taskkill /F /PID <PID>  # Windows
```

#### 3. 内存不足

```bash
# 增加Python内存限制
export PYTHONMAXMEM=2G

# 或调整工作线程数
python database/db_cli.py set-config scan_threads 2
```

### 日志分析

```bash
# 查看错误日志
grep ERROR mc_l10n.log | tail -20

# 查看慢查询
grep "duration.*[0-9]{4,}" mc_l10n.log

# 统计错误类型
grep ERROR mc_l10n.log | cut -d':' -f4 | sort | uniq -c
```

## 📈 性能优化

### 数据库优化

```sql
-- 重建索引
REINDEX;

-- 分析查询计划
EXPLAIN QUERY PLAN SELECT * FROM mod_discoveries WHERE is_uploaded = 0;

-- 优化查询缓存
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
```

### 应用优化

```python
# 增加连接池大小
database_pool = ConnectionPool(max_connections=20)

# 启用查询缓存
from cachetools import TTLCache
query_cache = TTLCache(maxsize=1000, ttl=300)

# 批量操作
BATCH_SIZE = 1000
```

## 🔄 升级指南

### 版本升级

```bash
# 备份当前版本
cp -r apps/mc_l10n apps/mc_l10n_backup

# 拉取新版本
git pull origin main

# 更新依赖
poetry update
cd frontend && pnpm update

# 运行迁移脚本（如果有）
python scripts/migrate_v4_to_v5.py

# 重启服务
systemctl restart mc-l10n
```

### 数据迁移

```python
# 数据库迁移脚本示例
import sqlite3

def migrate_v4_to_v5():
    conn = sqlite3.connect('mc_l10n_local.db')
    
    # 添加新字段
    conn.execute("ALTER TABLE mods ADD COLUMN new_field TEXT")
    
    # 迁移数据
    conn.execute("UPDATE mods SET new_field = 'default'")
    
    conn.commit()
    conn.close()
```

## 📚 相关文档

- [API文档](../technical/api-documentation.md)
- [数据库架构](../technical/database-architecture-v4.md)
- [开发指南](../README.md)
- [故障排除](../operations/error-logs.md)