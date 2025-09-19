# TH-Suite 翻译数据传输架构部署指南

## 📋 部署清单

### 1. 核心服务文件
- ✅ **translation_data_extractor.py** (580行) - 翻译数据提取服务
- ✅ **localized_compression_service.py** (647行) - 本地化压缩服务
- ✅ **file_transfer_service.py** (现有) - 文件传输服务
- ✅ **transfer_controller.py** (687行) - 传输控制器
- ✅ **transfer_resilience_service.py** (694行) - 传输恢复服务
- ✅ **transfer_event_processor.py** (641行) - 传输事件处理器

### 2. API接口文件
- ✅ **transfer_routes.py** (646行) - 传输API路由

### 3. 测试和基准文件
- ✅ **test_translation_transmission_integration.py** (472行) - 集成测试
- ✅ **benchmark_transmission_performance.py** (583行) - 性能基准测试

### 4. 部署配置文件
- ✅ **deploy_transmission_architecture.py** (533行) - 部署配置脚本

### 5. 文档文件
- ✅ **translation-data-transfer-complete-architecture.md** (726行) - 完整架构文档
- ✅ **translation-data-transmission-deployment-guide.md** (本文档) - 部署指南

## 🚀 快速部署步骤

### 步骤1: 验证环境
```bash
cd /home/saken/project/TH-Suite/apps/mc_l10n/backend/

# 检查Python环境
python --version  # 需要 3.12+

# 检查依赖
pip list | grep -E "(fastapi|asyncio|sqlite3|structlog)"
```

### 步骤2: 集成到现有应用
在 `main.py` 中添加传输架构集成：

```python
from deploy_transmission_architecture import integrate_with_fastapi_app
from core.di_container import DIContainer

# 在FastAPI应用初始化后
app = FastAPI(title="TH-Suite MC L10n API")
container = DIContainer()

# 集成传输架构
integrate_with_fastapi_app(app, container)
```

### 步骤3: 数据库迁移
```python
# 在应用启动时自动执行
from deploy_transmission_architecture import deploy_to_existing_application

await deploy_to_existing_application(container)
```

### 步骤4: 验证部署
```bash
# 运行集成测试
python test_translation_transmission_integration.py

# 运行性能基准测试
python benchmark_transmission_performance.py
```

## 🔧 配置选项

### 默认配置
```python
DeploymentConfig(
    enable_transfer_services=True,
    enable_compression=True,
    enable_resilience=True,
    max_concurrent_transfers=8,
    max_concurrent_downloads=12,
    chunk_size_mb=4,
    compression_level="balanced",
    cache_ttl_hours=24,
    retry_max_attempts=3,
    health_check_interval_seconds=60
)
```

### 自定义配置
```python
custom_config = DeploymentConfig(
    max_concurrent_transfers=16,  # 高性能服务器
    chunk_size_mb=8,             # 更大的块大小
    compression_level="high",     # 更高的压缩率
    cache_ttl_hours=48           # 更长的缓存时间
)

await deploy_to_existing_application(container, custom_config)
```

## 📊 监控指标

### 性能监控
```python
# 查看传输统计
GET /api/v1/transfer/stats

# 查看压缩统计
GET /api/v1/transfer/compression/stats

# 健康检查
GET /api/v1/transfer/health
```

### 数据库监控
```sql
-- 活跃传输会话
SELECT COUNT(*) FROM transfer_sessions WHERE status IN ('PENDING', 'UPLOADING', 'DOWNLOADING');

-- 压缩效率统计
SELECT 
    compression_level,
    AVG(compression_ratio) as avg_ratio,
    COUNT(*) as operations
FROM compression_stats 
WHERE created_at > datetime('now', '-24 hours')
GROUP BY compression_level;

-- 传输失败率
SELECT 
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) * 100.0 / COUNT(*) as failure_rate
FROM transfer_sessions 
WHERE created_at > datetime('now', '-24 hours');
```

## 🎯 API端点一览

### 上传API
- `POST /api/v1/transfer/upload/prepare` - 准备上传
- `POST /api/v1/transfer/upload/chunk` - 上传数据块
- `POST /api/v1/transfer/upload/complete` - 完成上传

### 下载API
- `POST /api/v1/transfer/download/prepare` - 准备下载
- `GET /api/v1/transfer/download/chunk` - 下载数据块
- `POST /api/v1/transfer/download/complete` - 完成下载

### 管理API
- `GET /api/v1/transfer/sessions` - 查看传输会话
- `GET /api/v1/transfer/status/{session_id}` - 查看传输状态
- `POST /api/v1/transfer/batch/upload` - 批量上传
- `POST /api/v1/transfer/batch/download` - 批量下载

### 压缩API
- `POST /api/v1/transfer/compress` - 压缩文件
- `POST /api/v1/transfer/decompress` - 解压文件

## 🔍 故障排除

### 常见问题

1. **数据库表创建失败**
   ```bash
   # 检查数据库权限
   ls -la data/mc_l10n.db
   
   # 手动运行迁移
   python -c "
   from deploy_transmission_architecture import TransmissionArchitectureDeployer
   deployer = TransmissionArchitectureDeployer(config)
   deployer._migrate_database()
   "
   ```

2. **服务注册失败**
   ```python
   # 检查依赖注入容器
   container = DIContainer()
   print(container.get(TranslationDataExtractor))
   ```

3. **传输会话创建失败**
   ```bash
   # 检查磁盘空间
   df -h
   
   # 检查文件权限
   ls -la /path/to/transfer/files
   ```

### 性能优化

1. **并发设置优化**
   ```python
   # 根据系统资源调整
   import psutil
   
   cpu_count = psutil.cpu_count()
   memory_gb = psutil.virtual_memory().total / 1024**3
   
   # 推荐配置
   max_concurrent_transfers = min(cpu_count * 2, 16)
   chunk_size_mb = max(4, int(memory_gb / 100))
   ```

2. **压缩级别选择**
   ```python
   # 不同场景的推荐配置
   configs = {
       "fast_upload": CompressionLevel.FAST,        # 快速上传
       "storage_optimization": CompressionLevel.HIGH, # 存储优化
       "balanced": CompressionLevel.BALANCED        # 平衡模式
   }
   ```

## 📈 性能基准

### 预期性能指标
- **数据提取**: 50,000+ 记录/秒
- **压缩吞吐量**: 50+ MB/秒
- **传输吞吐量**: 100+ MB/秒（并发）
- **压缩率**: 30-60%（取决于语言）
- **端到端延迟**: <2秒（10MB文件）

### 基准测试结果
运行 `benchmark_transmission_performance.py` 查看详细性能报告。

## 🔄 更新和维护

### 定期维护任务
1. **数据库清理** - 自动运行（每小时）
2. **压缩统计收集** - 自动运行（每30分钟）
3. **健康检查** - 自动运行（每分钟）

### 手动维护
```bash
# 清理过期传输会话
sqlite3 data/mc_l10n.db "DELETE FROM transfer_sessions WHERE status='COMPLETED' AND created_at < datetime('now', '-7 days');"

# 重建索引
sqlite3 data/mc_l10n.db "REINDEX;"

# 压缩数据库
sqlite3 data/mc_l10n.db "VACUUM;"
```

## 🛡️ 安全考虑

### 文件安全
- 所有上传文件进行BLAKE3完整性验证
- 传输过程中支持加密（HTTPS）
- 文件路径验证防止目录遍历攻击

### 访问控制
- API端点需要适当的身份验证
- 传输会话ID使用UUID确保不可预测
- 文件访问权限检查

### 资源保护
- 并发限制防止资源滥用
- 文件大小限制
- 传输超时保护

## 🎉 部署完成验证

部署完成后，访问以下端点验证：

1. **健康检查**: `GET /api/v1/transfer/health`
2. **API文档**: `GET /docs#/transfer`
3. **系统状态**: `GET /api/v1/transfer/stats`

预期响应：
```json
{
  "status": "healthy",
  "services": {
    "translation_extractor": "active",
    "compression_service": "active", 
    "transfer_controller": "active",
    "resilience_service": "active"
  },
  "metrics": {
    "active_sessions": 0,
    "total_transfers": 0,
    "cache_hit_rate": 0.0
  }
}
```

---

🎯 **传输架构部署完成！** 您现在可以使用TH-Suite的高性能翻译数据传输功能了。