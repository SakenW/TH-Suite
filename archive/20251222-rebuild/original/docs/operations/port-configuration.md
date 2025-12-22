# TH-Suite 端口配置文档

**创建日期**: 2025-09-05  
**状态**: 已配置并固定  

## 📋 目录
1. [端口分配表](#端口分配表)
2. [配置文件位置](#配置文件位置)
3. [服务管理脚本](#服务管理脚本)
4. [故障排除](#故障排除)
5. [重要说明](#重要说明)

---

## 📌 端口分配表

### MC L10n 应用
| 服务 | 端口 | 地址 | 说明 |
|------|------|------|------|
| 前端开发服务器 | 5173 | http://localhost:5173 | Vite 开发服务器 |
| 后端 API 服务 | 18000 | http://localhost:18000 | FastAPI 服务器 |
| API 文档 | 18000 | http://localhost:18000/docs | Swagger UI |
| ReDoc 文档 | 18000 | http://localhost:18000/redoc | ReDoc UI |

### RW Studio 应用（预留）
| 服务 | 端口 | 地址 | 说明 |
|------|------|------|------|
| 前端开发服务器 | 5174 | http://localhost:5174 | Vite 开发服务器 |
| 后端 API 服务 | 18002 | http://localhost:18002 | FastAPI 服务器 |

---

## 📁 配置文件位置

### 1. 端口配置主文件
```
apps/mc_l10n/ports.config.json
```
- 统一管理所有服务的端口配置
- JSON 格式，易于程序读取

### 2. 前端配置
```
apps/mc_l10n/frontend/vite.config.ts
```
关键配置：
```typescript
server: {
  port: 5173,           // 固定端口
  strictPort: true,     // 强制使用指定端口
  host: 'localhost',
  proxy: {
    '/api': {
      target: 'http://localhost:18000',  // 代理到后端
      changeOrigin: true
    }
  }
}
```

### 3. 后端配置
```
apps/mc_l10n/backend/main.py
```
关键代码（第788行）：
```python
port = int(os.getenv("PORT", "18000"))  # 默认使用18000端口
```

### 4. API 服务配置
```
apps/mc_l10n/frontend/src/services/baseApiService.ts
```
关键代码（第22行）：
```typescript
constructor(baseUrl: string = 'http://localhost:18000') {
  this.baseUrl = baseUrl;
}
```

---

## 🛠️ 服务管理脚本

### 管理脚本位置
```bash
apps/mc_l10n/manage.sh
```

### 使用方法

#### 启动服务
```bash
cd apps/mc_l10n
./manage.sh start
```
- 自动检查端口占用
- 清理残留进程
- 启动前端和后端服务

#### 停止服务
```bash
./manage.sh stop
```
- 停止所有运行的服务
- 清理 PID 文件

#### 重启服务
```bash
./manage.sh restart
```
- 先停止后启动

#### 查看状态
```bash
./manage.sh status
```
- 显示服务运行状态
- 显示进程信息

#### 清理端口
```bash
./manage.sh clean
```
- 强制清理占用的端口
- 杀死残留进程

---

## 🔧 故障排除

### 1. 端口被占用

#### 查看占用情况
```bash
# 查看特定端口
lsof -i :5173    # 前端端口
lsof -i :18000   # 后端端口

# 或使用 netstat
netstat -tlnp | grep -E ':(5173|18000)'
```

#### 手动清理进程
```bash
# 获取占用端口的进程 PID
lsof -t -i :5173

# 杀死进程
kill -9 $(lsof -t -i :5173)
kill -9 $(lsof -t -i :18000)
```

### 2. 服务启动失败

#### 检查日志
```bash
# 查看后端日志
cd apps/mc_l10n/backend
tail -f logs/*.log

# 查看前端控制台
# 在浏览器开发者工具中查看 Console
```

#### 验证依赖
```bash
# 检查 Python 依赖
cd apps/mc_l10n/backend
poetry install

# 检查 Node 依赖
cd apps/mc_l10n/frontend
pnpm install
```

### 3. API 连接失败

#### 测试后端健康状态
```bash
curl http://localhost:18000/health
```

#### 测试 API 响应
```bash
curl http://localhost:18000/docs
```

---

## ⚠️ 重要说明

### 端口选择原则
1. **前端端口 (5173)**
   - Vite 默认端口
   - 避免与其他前端项目冲突

2. **后端端口 (18000)**
   - 选择高端口号避免权限问题
   - 与常见服务端口区分（8000, 8080, 3000等）
   - 为多个后端服务预留端口段（18000-18099）

### 注意事项
1. **不要随意更改端口配置**
   - 所有配置文件已经统一
   - 更改需同时修改多处配置

2. **开发环境专用**
   - 这些配置仅用于本地开发
   - 生产环境需要独立配置

3. **端口冲突处理**
   - 优先使用 manage.sh 脚本
   - 避免手动启动多个实例

4. **跨应用通信**
   - 前端通过代理访问后端
   - 避免直接跨域请求

### 环境变量覆盖
如需临时更改端口，可使用环境变量：
```bash
# 后端端口
PORT=19000 poetry run python main.py

# 前端端口（需修改 vite.config.ts）
VITE_PORT=5174 npm run dev
```

---

## 📝 更新记录

| 日期 | 更改内容 | 修改者 |
|------|----------|--------|
| 2025-09-05 | 初始端口配置，固定所有服务端口 | Claude |
| 2025-09-05 | 创建服务管理脚本 manage.sh | Claude |
| 2025-09-05 | 统一配置文件 ports.config.json | Claude |