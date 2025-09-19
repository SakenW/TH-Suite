# TH-Suite v2.0 部署指南

## 概览

本指南详细介绍 TH-Suite v2.0 的部署流程，包括开发环境、测试环境和生产环境的配置。

## 环境要求

### 系统要求

#### 开发环境
- **操作系统**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **内存**: 最小 8GB，推荐 16GB+
- **存储**: 最小 10GB 可用空间
- **网络**: 宽带网络连接（用于依赖下载）

#### 生产环境
- **操作系统**: Linux (Ubuntu 20.04+ 推荐)
- **内存**: 最小 4GB，推荐 8GB+
- **存储**: 最小 20GB SSD
- **网络**: 稳定的网络连接
- **权限**: 非 root 用户，具有 sudo 权限

### 软件依赖

#### 核心运行时
```bash
# Python 3.12+
python --version  # 应显示 3.12.x

# Node.js 18+
node --version    # 应显示 18.x.x
npm --version     # 应显示 9.x.x

# Rust 工具链（用于 Tauri）
rustc --version  # 应显示 1.70+
```

#### 包管理器
```bash
# Poetry（Python 依赖管理）
curl -sSL https://install.python-poetry.org | python3 -
poetry --version

# pnpm（Node.js 包管理）
npm install -g pnpm
pnpm --version

# 可选：Task（任务运行器）
# 参见项目 CLAUDE.md 中的安装说明
```

## 开发环境部署

### 1. 代码获取

```bash
# 克隆仓库
git clone <repository-url> TH-Suite
cd TH-Suite

# 检查分支
git branch -a
git checkout main  # 或其他目标分支
```

### 2. 依赖安装

#### 使用 Task（推荐）
```bash
# 安装所有依赖
task install

# 这等价于：
# poetry install
# cd apps/mc_l10n/frontend && pnpm install
# cd apps/rw_l10n/frontend && pnpm install
```

#### 手动安装
```bash
# 1. Python 依赖
poetry install

# 2. 前端依赖
cd apps/mc_l10n/frontend
pnpm install
cd ../../../

cd apps/rw_l10n/frontend
pnpm install
cd ../../../
```

### 3. 环境配置

#### 后端配置
```bash
# 创建环境配置文件
cp apps/mc_l10n/backend/.env.example apps/mc_l10n/backend/.env

# 编辑配置文件
nano apps/mc_l10n/backend/.env
```

示例 `.env` 配置：
```env
# 应用配置
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=sqlite:///./data/mc_l10n.db
DATABASE_ENCRYPTION_KEY=your-secret-key-here

# Trans-Hub 集成
TRANS_HUB_API_URL=https://api.trans-hub.net
TRANS_HUB_API_KEY=your-api-key

# 服务端口
API_HOST=127.0.0.1
API_PORT=18000

# 安全配置
SECRET_KEY=your-secret-jwt-key
ALLOWED_ORIGINS=http://localhost:18001,tauri://localhost

# 性能配置
MAX_WORKERS=4
CACHE_TTL=3600
```

#### 前端配置
```bash
# MC L10n 前端配置
cp apps/mc_l10n/frontend/.env.example apps/mc_l10n/frontend/.env.local

# 编辑配置
nano apps/mc_l10n/frontend/.env.local
```

示例前端 `.env.local`：
```env
# API 配置
VITE_API_BASE_URL=http://localhost:18000
VITE_WS_URL=ws://localhost:18000/ws

# 应用配置
VITE_APP_NAME=TH-Suite MC L10n
VITE_APP_VERSION=2.0.0

# 功能开关
VITE_ENABLE_DEBUG=true
VITE_ENABLE_MOCK_DATA=false

# Trans-Hub 配置
VITE_TRANS_HUB_URL=https://trans-hub.net
```

### 4. 启动开发服务

#### 使用 Task（推荐）
```bash
# 启动 MC L10n 完整服务（前端 + 后端）
task dev:mc

# 或分别启动
task dev:mc:backend   # 仅后端，端口 18000
task dev:mc:frontend  # 仅前端，端口 18001（Tauri）
```

#### 手动启动
```bash
# 启动后端（新终端窗口）
cd apps/mc_l10n/backend
poetry run python main.py

# 启动前端（另一个终端窗口）
cd apps/mc_l10n/frontend
pnpm tauri dev        # 桌面应用
# 或者
pnpm dev             # Web 版本，访问 http://localhost:18001
```

### 5. 验证安装

```bash
# 检查后端服务
curl http://localhost:18000/health

# 检查 API 文档
open http://localhost:18000/docs  # 或在浏览器中访问

# 检查前端服务（如果使用 Web 模式）
open http://localhost:18001
```

## 测试环境部署

### 1. 测试准备

```bash
# 安装测试依赖
poetry install --with dev

# 运行代码质量检查
task lint            # 运行所有检查
task lint:python     # 仅 Python 检查
task lint:frontend   # 仅前端检查
```

### 2. 执行测试

```bash
# 运行所有测试
task test

# 分类运行测试
task test:python     # Python 测试
task test:frontend   # 前端测试
task test:mc         # MC L10n 功能测试

# 运行集成测试
pytest tests/integration/ -v

# 运行性能测试
pytest tests/performance/ -v
```

### 3. 测试环境配置

创建测试专用配置：
```bash
# 测试环境配置
cp apps/mc_l10n/backend/.env.example apps/mc_l10n/backend/.env.test
```

```env
# .env.test
ENVIRONMENT=testing
DEBUG=false
LOG_LEVEL=WARNING

# 使用内存数据库
DATABASE_URL=sqlite:///:memory:
DATABASE_ENCRYPTION_KEY=test-key

# 禁用外部服务
TRANS_HUB_API_URL=http://mock-api.test
TRANS_HUB_API_KEY=test-key

# 测试端口
API_PORT=18080
```

### 4. 持续集成配置

#### GitHub Actions 配置
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: |
        poetry install
        cd apps/mc_l10n/frontend && npm install
    
    - name: Run linting
      run: |
        poetry run ruff check .
        poetry run mypy packages apps
    
    - name: Run tests
      run: |
        poetry run pytest tests/ --cov=apps --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 生产环境部署

### 1. 服务器准备

#### 系统更新
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# 安装必要工具
sudo apt install -y curl wget git build-essential
```

#### 创建应用用户
```bash
# 创建专用用户
sudo useradd -m -s /bin/bash thsuite
sudo usermod -aG sudo thsuite

# 切换到应用用户
sudo su - thsuite
```

#### 安装运行时
```bash
# Python 3.12
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Poetry
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 2. 应用部署

#### 代码部署
```bash
# 创建应用目录
sudo mkdir -p /opt/thsuite
sudo chown thsuite:thsuite /opt/thsuite
cd /opt/thsuite

# 克隆代码
git clone <repository-url> .
git checkout production  # 或 main

# 安装依赖
poetry install --no-dev
cd apps/mc_l10n/frontend
npm ci --production
npm run build
cd ../../../
```

#### 生产配置
```bash
# 创建生产配置
sudo mkdir -p /etc/thsuite
sudo cp apps/mc_l10n/backend/.env.example /etc/thsuite/mc_l10n.env
sudo chown thsuite:thsuite /etc/thsuite/mc_l10n.env
sudo chmod 600 /etc/thsuite/mc_l10n.env

# 编辑生产配置
sudo nano /etc/thsuite/mc_l10n.env
```

生产环境配置示例：
```env
# 生产环境配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=sqlite:///var/lib/thsuite/mc_l10n.db
DATABASE_ENCRYPTION_KEY=<生产密钥-使用安全的随机字符串>

# Trans-Hub 配置
TRANS_HUB_API_URL=https://api.trans-hub.net
TRANS_HUB_API_KEY=<生产API密钥>

# 服务配置
API_HOST=0.0.0.0
API_PORT=18000

# 安全配置
SECRET_KEY=<生产JWT密钥-使用安全的随机字符串>
ALLOWED_ORIGINS=https://yourdomain.com

# 性能配置
MAX_WORKERS=8
CACHE_TTL=7200

# 日志配置
LOG_FILE=/var/log/thsuite/mc_l10n.log
LOG_ROTATION=true
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5
```

#### 创建数据目录
```bash
# 创建数据和日志目录
sudo mkdir -p /var/lib/thsuite
sudo mkdir -p /var/log/thsuite
sudo chown -R thsuite:thsuite /var/lib/thsuite /var/log/thsuite
sudo chmod 755 /var/lib/thsuite /var/log/thsuite
```

### 3. 系统服务配置

#### Systemd 服务单元
```bash
# 创建服务文件
sudo nano /etc/systemd/system/thsuite-mc-l10n.service
```

```ini
[Unit]
Description=TH-Suite MC L10n Backend Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=thsuite
Group=thsuite
WorkingDirectory=/opt/thsuite/apps/mc_l10n/backend
Environment=PYTHONPATH=/opt/thsuite/packages/core/src:/opt/thsuite
EnvironmentFile=/etc/thsuite/mc_l10n.env
ExecStart=/opt/thsuite/.venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/thsuite /var/log/thsuite

# 资源限制
LimitNOFILE=65536
LimitCORE=0

[Install]
WantedBy=multi-user.target
```

#### 启用服务
```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable thsuite-mc-l10n.service

# 启动服务
sudo systemctl start thsuite-mc-l10n.service

# 检查状态
sudo systemctl status thsuite-mc-l10n.service

# 查看日志
sudo journalctl -u thsuite-mc-l10n.service -f
```

### 4. 反向代理配置

#### Nginx 配置
```bash
# 安装 Nginx
sudo apt install -y nginx

# 创建站点配置
sudo nano /etc/nginx/sites-available/thsuite
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 配置
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # 前端静态文件
    location / {
        root /opt/thsuite/apps/mc_l10n/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # 缓存配置
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:18000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:18000/health;
        access_log off;
    }

    # 限制上传大小
    client_max_body_size 100M;

    # 日志配置
    access_log /var/log/nginx/thsuite_access.log;
    error_log /var/log/nginx/thsuite_error.log;
}
```

#### 启用站点
```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/thsuite /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 5. SSL 证书配置

#### Let's Encrypt 证书
```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 6. 监控和日志

#### 日志轮转配置
```bash
# 创建日志轮转配置
sudo nano /etc/logrotate.d/thsuite
```

```
/var/log/thsuite/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0644 thsuite thsuite
    postrotate
        systemctl reload thsuite-mc-l10n.service
    endscript
}
```

#### 系统监控
```bash
# 安装监控工具
sudo apt install -y htop iotop nethogs

# 创建监控脚本
nano /opt/thsuite/scripts/monitor.sh
```

```bash
#!/bin/bash
# 系统监控脚本

LOG_FILE="/var/log/thsuite/monitor.log"

# 检查服务状态
check_service() {
    if systemctl is-active --quiet thsuite-mc-l10n.service; then
        echo "$(date): Service is running" >> $LOG_FILE
    else
        echo "$(date): Service is down, attempting restart" >> $LOG_FILE
        systemctl restart thsuite-mc-l10n.service
    fi
}

# 检查磁盘空间
check_disk() {
    USAGE=$(df /var/lib/thsuite | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $USAGE -gt 80 ]; then
        echo "$(date): Disk usage high: ${USAGE}%" >> $LOG_FILE
    fi
}

# 检查内存使用
check_memory() {
    USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ $USAGE -gt 80 ]; then
        echo "$(date): Memory usage high: ${USAGE}%" >> $LOG_FILE
    fi
}

check_service
check_disk
check_memory
```

```bash
# 设置定时任务
crontab -e
# 添加：
# */5 * * * * /opt/thsuite/scripts/monitor.sh
```

## 容器化部署

### 1. Docker 配置

#### 后端 Dockerfile
```dockerfile
# apps/mc_l10n/backend/Dockerfile
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install poetry

# 复制依赖文件
COPY pyproject.toml poetry.lock ./
COPY packages/ ./packages/

# 安装 Python 依赖
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# 复制应用代码
COPY apps/mc_l10n/backend/ ./

# 创建非 root 用户
RUN useradd -m -s /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 18000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18000/health || exit 1

# 启动命令
CMD ["python", "main.py"]
```

#### 前端 Dockerfile
```dockerfile
# apps/mc_l10n/frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./
RUN npm ci

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产镜像
FROM nginx:alpine

# 复制构建文件
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### 2. Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: apps/mc_l10n/backend/Dockerfile
    container_name: thsuite-backend
    restart: unless-stopped
    ports:
      - "18000:18000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=sqlite:///data/mc_l10n.db
      - DATABASE_ENCRYPTION_KEY=${DATABASE_ENCRYPTION_KEY}
      - TRANS_HUB_API_KEY=${TRANS_HUB_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - thsuite_data:/app/data
      - thsuite_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: .
      dockerfile: apps/mc_l10n/frontend/Dockerfile
    container_name: thsuite-frontend
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      backend:
        condition: service_healthy
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 可选：数据库（如果使用 PostgreSQL）
  # database:
  #   image: postgres:15
  #   container_name: thsuite-db
  #   restart: unless-stopped
  #   environment:
  #     POSTGRES_DB: thsuite
  #     POSTGRES_USER: thsuite
  #     POSTGRES_PASSWORD: ${DB_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   healthcheck:
  #     test: ["CMD-SHELL", "pg_isready -U thsuite"]
  #     interval: 10s
  #     timeout: 5s
  #     retries: 5

volumes:
  thsuite_data:
  thsuite_logs:
  # postgres_data:

networks:
  default:
    name: thsuite_network
```

### 3. 环境变量配置

```bash
# .env
# 数据库加密密钥
DATABASE_ENCRYPTION_KEY=your-production-encryption-key

# Trans-Hub API 密钥
TRANS_HUB_API_KEY=your-trans-hub-api-key

# JWT 密钥
SECRET_KEY=your-jwt-secret-key

# 可选：数据库密码（如果使用 PostgreSQL）
# DB_PASSWORD=your-database-password
```

### 4. 部署命令

```bash
# 构建和启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 更新服务
docker-compose pull
docker-compose up -d

# 备份数据
docker run --rm -v thsuite_data:/data -v $(pwd):/backup alpine tar czf /backup/thsuite_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# 恢复数据
docker run --rm -v thsuite_data:/data -v $(pwd):/backup alpine tar xzf /backup/backup_file.tar.gz -C /data
```

## 维护和故障排除

### 1. 常见问题

#### 服务无法启动
```bash
# 检查服务状态
sudo systemctl status thsuite-mc-l10n.service

# 查看详细日志
sudo journalctl -u thsuite-mc-l10n.service -n 50

# 检查配置文件
poetry run python -c "from main import create_app; create_app()"
```

#### 数据库问题
```bash
# 检查数据库文件权限
ls -la /var/lib/thsuite/

# 验证数据库连接
cd /opt/thsuite/apps/mc_l10n/backend
poetry run python -c "
from infrastructure.db_initializer import DatabaseInitializer
db = DatabaseInitializer()
print('Database connection:', db.check_connection())
"
```

#### 端口冲突
```bash
# 检查端口占用
sudo netstat -tlnp | grep :18000
sudo lsof -i :18000

# 更改端口配置
sudo nano /etc/thsuite/mc_l10n.env
# 修改 API_PORT=18001
sudo systemctl restart thsuite-mc-l10n.service
```

### 2. 性能调优

#### 系统优化
```bash
# 增加文件描述符限制
echo "thsuite soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "thsuite hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化内存设置
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### 应用优化
```bash
# 调整工作进程数
sudo nano /etc/thsuite/mc_l10n.env
# 设置 MAX_WORKERS=<CPU核心数>

# 启用缓存
# 设置 CACHE_TTL=7200

# 重启服务应用更改
sudo systemctl restart thsuite-mc-l10n.service
```

### 3. 备份策略

#### 自动备份脚本
```bash
# 创建备份脚本
sudo nano /opt/thsuite/scripts/backup.sh
```

```bash
#!/bin/bash
# TH-Suite 备份脚本

BACKUP_DIR="/var/backups/thsuite"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="thsuite_backup_${DATE}.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 停止服务（可选，用于一致性备份）
# systemctl stop thsuite-mc-l10n.service

# 备份数据库和配置
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    -C /var/lib/thsuite . \
    -C /etc/thsuite . \
    -C /opt/thsuite/apps/mc_l10n/backend/logs .

# 重启服务
# systemctl start thsuite-mc-l10n.service

# 保留最近 30 天的备份
find $BACKUP_DIR -name "thsuite_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/$BACKUP_FILE"
```

```bash
# 设置执行权限
sudo chmod +x /opt/thsuite/scripts/backup.sh

# 设置定时备份
sudo crontab -e
# 添加：每天凌晨 2 点备份
# 0 2 * * * /opt/thsuite/scripts/backup.sh
```

### 4. 安全维护

#### 定期安全更新
```bash
# 系统更新
sudo apt update && sudo apt upgrade -y

# Python 依赖更新
cd /opt/thsuite
poetry update

# Node.js 依赖更新
cd apps/mc_l10n/frontend
npm audit fix
npm update
```

#### 安全检查清单
- [ ] 定期更新系统和依赖
- [ ] 检查日志中的异常活动
- [ ] 验证 SSL 证书有效性
- [ ] 审查用户权限
- [ ] 备份数据完整性验证
- [ ] 防火墙规则检查
- [ ] 监控系统资源使用

## 升级指南

### 1. 应用升级

```bash
# 备份当前版本
/opt/thsuite/scripts/backup.sh

# 停止服务
sudo systemctl stop thsuite-mc-l10n.service

# 更新代码
cd /opt/thsuite
git fetch origin
git checkout <new-version-tag>

# 更新依赖
poetry install --no-dev
cd apps/mc_l10n/frontend
npm ci --production
npm run build

# 运行数据库迁移（如果需要）
cd /opt/thsuite/apps/mc_l10n/backend
poetry run python -m migrations.migrate

# 重启服务
sudo systemctl start thsuite-mc-l10n.service

# 验证升级
curl http://localhost:18000/health
```

### 2. 回滚程序

```bash
# 如果升级失败，回滚到之前版本
cd /opt/thsuite
git checkout <previous-version-tag>

# 恢复依赖
poetry install --no-dev

# 恢复数据（如果需要）
# tar -xzf /var/backups/thsuite/backup_file.tar.gz -C /var/lib/thsuite/

# 重启服务
sudo systemctl restart thsuite-mc-l10n.service
```

## 总结

本部署指南提供了 TH-Suite v2.0 在不同环境下的完整部署流程。请根据实际需求选择合适的部署方式：

- **开发环境**: 使用 Task 工具快速启动
- **测试环境**: 完整的测试流程和 CI/CD 配置
- **生产环境**: 安全、稳定的生产部署配置
- **容器化**: 使用 Docker 进行容器化部署

记住定期进行备份、监控和安全更新，确保系统的稳定运行。