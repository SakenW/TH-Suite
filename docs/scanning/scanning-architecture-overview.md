# MC L10n 扫描架构全览

## 🎯 架构概述

MC L10n 采用三层扫描架构，专门针对不同性能要求和硬件配置优化：

### 📊 三种扫描器对比

| 特性 | 标准扫描器 | 优化扫描器 | 低内存扫描器 |
|------|------------|------------|--------------|
| **内存使用** | 200-800MB | 100-400MB | 50-200MB |
| **处理速度** | 基准 | 2-5x 更快 | 0.8x 稍慢 |
| **并发线程** | 1 | 8 | 1-2 |
| **适用配置** | 8GB+ | 16GB+ | 4GB+ |
| **智能缓存** | 基础 | 高级 | 流式 |
| **内存监控** | ❌ | ⚠️ | ✅ |

## 🏗️ 架构设计原则

### 1. 渐进式优化
- **基础版本**: 保证功能完整性和稳定性
- **性能版本**: 高配置环境下的最佳性能
- **低内存版本**: 确保低配置设备的可用性

### 2. 内存安全优先
- **恒定内存使用**: 低内存扫描器内存使用恒定，不会随文件数量增长
- **主动监控**: 实时监控内存使用，超阈值自动清理
- **流式处理**: 文件内容不在内存中积累

### 3. 智能适配
- **硬件检测**: 自动分析系统配置，推荐合适的扫描器
- **动态调整**: 根据实时性能自动调整参数
- **故障转移**: 高级扫描器失败时自动降级

## 📁 文件结构

```
infrastructure/services/
├── simple_minecraft_scanner.py      # 标准扫描器（基础版）
├── optimized_minecraft_scanner.py   # 优化扫描器（性能版）
└── low_memory_minecraft_scanner.py  # 低内存扫描器（节约版）

api/routes/
├── scan_routes.py                   # 标准扫描API
├── optimized_scan_routes.py         # 优化扫描API
└── low_memory_scan_routes.py        # 低内存扫描API
```

## 🔄 扫描流程

### 通用流程
1. **目录发现** → 递归扫描目标目录
2. **文件过滤** → 识别 JAR/ZIP 文件
3. **MOD识别** → 检查MOD元数据文件
4. **语言提取** → 解析语言文件内容
5. **数据存储** → 写入V5数据库架构

### 各扫描器特色

#### 标准扫描器
- **同步处理**: 顺序处理每个文件
- **简单缓存**: 基于文件修改时间
- **适用场景**: 小型项目、开发测试

#### 优化扫描器  
- **并发处理**: 8线程并行处理JAR文件
- **智能缓存**: BLAKE3哈希 + TTL策略
- **批量数据库**: 批量插入优化性能
- **适用场景**: 大型整合包、生产环境

#### 低内存扫描器
- **流式读取**: 不将完整文件加载到内存
- **内存监控**: 实时监控，超阈值自动GC
- **批量控制**: 动态调整批处理大小
- **适用场景**: 低配置电脑、内存受限环境

## ⚙️ 配置推荐

### 系统配置映射

#### 低配置（4GB内存）
```python
# 推荐：低内存扫描器
{
    "scanner_type": "low_memory",
    "memory_limit_mb": 256,
    "batch_size": 1,
    "max_file_size_mb": 30
}
```

#### 中等配置（8GB内存）  
```python
# 推荐：标准扫描器或低内存扫描器
{
    "scanner_type": "low_memory",  # 保守选择
    "memory_limit_mb": 512,
    "batch_size": 2,
    "max_file_size_mb": 50
}
```

#### 高配置（16GB+内存）
```python
# 推荐：优化扫描器
{
    "scanner_type": "optimized", 
    "max_workers": 8,
    "cache_size": 1000,
    "enable_smart_cache": true
}
```

## 🚀 性能优化技术

### 1. 并发优化
- **异步IO**: 使用 asyncio 处理文件操作
- **线程池**: 多线程并行处理JAR文件
- **信号量控制**: 限制同时处理的文件数量

### 2. 内存优化
- **流式ZIP读取**: 不将整个ZIP内容加载到内存
- **及时释放**: 处理完成后立即释放资源
- **垃圾回收**: 主动触发垃圾回收机制

### 3. 缓存优化
- **多层缓存**: 文件级、内容级、结果级缓存
- **智能失效**: 基于文件哈希和修改时间
- **LRU策略**: 最近最少使用算法管理缓存

## 📈 性能基准

### 测试环境
- **测试目标**: DeceasedCraft 整合包（600+ MOD）
- **文件规模**: ~2GB JAR文件，10,000+ 语言文件

### 性能对比
| 指标 | 标准扫描器 | 优化扫描器 | 低内存扫描器 |
|------|------------|------------|--------------|
| **扫描时间** | 120秒 | 30秒 | 90秒 |
| **内存峰值** | 600MB | 300MB | 150MB |
| **并发线程** | 1 | 8 | 2 |
| **缓存命中率** | 60% | 90% | 75% |

## 🛠️ API 端点

### 标准扫描器
- `POST /api/v1/scan/start` - 启动扫描
- `GET /api/v1/scan/status/{scan_id}` - 获取状态

### 优化扫描器  
- `POST /api/v1/scan-optimized/start` - 启动优化扫描
- `GET /api/v1/scan-optimized/benchmark` - 性能基准测试
- `POST /api/v1/scan-optimized/cache/clear` - 清理缓存

### 低内存扫描器
- `POST /api/v1/scan-low-memory/start` - 启动低内存扫描
- `GET /api/v1/scan-low-memory/memory-recommendations` - 获取内存配置建议
- `GET /api/v1/scan-low-memory/system-memory` - 系统内存分析

## 🔍 监控与调试

### 内存监控
```python
# 获取系统内存信息
GET /api/v1/scan-low-memory/system-memory

# 内存使用测试
POST /api/v1/scan-low-memory/memory-test?memory_limit_mb=512&duration_seconds=30
```

### 性能基准
```python
# 扫描器性能对比
POST /api/v1/scan-optimized/benchmark
{
    "test_directory": "/path/to/modpack",
    "compare_scanners": ["simple", "optimized", "low_memory"]
}
```

## 🚨 故障排除

### 常见问题

#### 1. 扫描无响应
- **原因**: 多个Python进程冲突
- **解决**: `poetry run python main.py --kill-all`

#### 2. 内存不足
- **原因**: 使用了不适合的扫描器
- **解决**: 切换到低内存扫描器

#### 3. 扫描速度慢
- **原因**: 硬件配置vs扫描器不匹配
- **解决**: 根据系统配置选择合适的扫描器

### 调试命令
```bash
# 检查系统内存
GET /api/v1/scan-low-memory/system-memory

# 测试内存使用
POST /api/v1/scan-low-memory/memory-test

# 清理缓存重新开始
POST /api/v1/scan-optimized/cache/clear
```

## 🔮 未来优化方向

1. **GPU加速**: 利用GPU并行处理文件哈希计算
2. **分布式扫描**: 多机器协同扫描大型项目
3. **机器学习**: 基于历史数据预测最佳配置
4. **增量扫描**: 更细粒度的增量更新机制

---

本文档提供了MC L10n扫描架构的完整概览。如需了解具体实现细节，请参考相关源代码文件。