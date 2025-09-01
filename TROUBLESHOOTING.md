# TH Suite MC L10n - 故障排除指南

## 🚨 常见问题和解决方案

### 1. 应用卡在启动界面 "Minecraft 本地化工具正在启动..."

**症状**: 
- 桌面应用或Web版本显示启动界面但无法进入主界面
- 控制台可能显示导出错误或端口连接问题

**可能原因**: 
- 前端服务导出错误
- 端口配置不一致
- 前端初始化逻辑问题

**解决步骤**:

1. **检查控制台错误**:
   - 在应用中按 F12 打开开发者工具
   - 查看 Console 选项卡中的红色错误信息
   - 常见错误：`The requested module does not provide an export named 'SystemService'`

2. **端口配置问题**:
   - 确认后端运行在 `http://localhost:8000`
   - 确认前端运行在正确端口（通常是 3456）
   - 检查 `vite.config.ts` 和 `tauri.conf.json` 中的端口配置是否一致

3. **重启开发服务器**:
   ```bash
   # 在项目根目录运行
   task dev:mc
   # 或者分别启动
   task dev:mc:backend  # 终端1
   task dev:mc:frontend # 终端2
   ```

### 2. 模块导出错误

**症状**:
```
Uncaught SyntaxError: The requested module does not provide an export named 'SystemService'
```

**解决方案**:
确保服务类正确导出：

```typescript
// 在服务文件末尾添加类导出
export { SystemService };
export { FileService };

// 创建单例实例
const systemService = new SystemService();
export { systemService };
export default systemService;
```

### 3. 端口冲突问题

**症状**:
```
GET http://127.0.0.1:3456/ net::ERR_CONNECTION_REFUSED
```

**解决方案**:
1. 检查端口配置：
   ```typescript
   // vite.config.ts
   server: {
     port: 3456,
     strictPort: true, // 确保严格端口模式
     host: '127.0.0.1',
   }
   ```

2. 检查 Tauri 配置：
   ```json
   // src-tauri/tauri.conf.json
   {
     "build": {
       "devUrl": "http://127.0.0.1:3456"
     }
   }
   ```

3. 如果端口被占用，杀死占用进程或更换端口

### 4. 前端初始化卡死

**症状**:
- 应用停留在加载状态
- 调试信息显示 `isInitialized: false`

**解决方案**:
检查 appStore 的初始化逻辑，确保：
1. `initialize` 方法正确设置 `isInitialized = true`
2. 异步操作有适当的错误处理
3. Zustand 状态更新触发重新渲染

### 5. 后端连接问题

**症状**:
- 前端无法连接到后端API
- 健康检查失败

**解决方案**:
1. 验证后端服务状态：
   ```bash
   curl http://localhost:8000/health
   ```

2. 检查 CORS 配置
3. 确认 API 基础 URL 配置正确

## 🛠 开发环境设置

### 必需工具
- **Python 3.12+** 
- **Node.js 18+** 
- **Poetry** (Python包管理)
- **pnpm** (Node.js包管理)
- **Rust** (Tauri需要)
- **Task** (推荐，用于任务运行)

### 环境变量
创建 `.env` 文件：
```bash
# 后端配置
API_PORT=8000
LOG_LEVEL=INFO

# 前端配置
VITE_API_URL=http://localhost:8000
```

## 🔍 调试技巧

### 1. 查看详细日志
- 后端日志会显示在后端终端
- 前端日志在浏览器控制台
- 修改后的初始化逻辑包含详细的调试信息

### 2. 健康检查
```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端页面检查
curl http://127.0.0.1:3456
```

### 3. 网络问题诊断
```bash
# 检查端口占用
netstat -an | findstr 3456
netstat -an | findstr 8000

# 杀死占用端口的进程
taskkill /F /PID <PID>
```

## 🚀 快速修复脚本

创建 `fix-common-issues.bat` 文件：
```batch
@echo off
echo 正在修复常见问题...

echo 1. 重启开发服务器...
taskkill /F /IM node.exe /T 2>nul
taskkill /F /IM python.exe /T 2>nul

echo 2. 清理端口...
netstat -ano | findstr :3456 | findstr LISTENING
netstat -ano | findstr :8000 | findstr LISTENING

echo 3. 重新启动服务...
start cmd /k "task dev:mc:backend"
timeout /t 3 /nobreak >nul
start cmd /k "task dev:mc:frontend"

echo 修复完成！
```

## 📞 获取帮助

如果问题仍然存在：

1. **查看日志**: 检查控制台输出和错误信息
2. **重启服务**: 完全重启前后端服务
3. **检查环境**: 确认所有依赖正确安装
4. **清理缓存**: 删除 `node_modules` 和 `__pycache__` 后重新安装

## 🔄 最新修复 (2024-09-01)

### 已修复问题:
1. ✅ SystemService 和 FileService 导出错误
2. ✅ Vite 和 Tauri 端口配置不一致
3. ✅ 前端初始化卡死问题
4. ✅ 缺少调试信息和错误反馈

### 新增功能:
- 详细的初始化调试日志
- 改进的加载界面，包含状态信息
- 自动后端连接测试
- 用户友好的错误提示

应用现在应该能正常启动并进入主界面。如果遇到问题，请按照上述指南进行排查。