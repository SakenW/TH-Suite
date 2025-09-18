# MC L10n 三层扫描系统文档

本目录包含 MC L10n 三层扫描系统的完整技术文档，涵盖从架构设计到实际使用的所有方面。

## 🚀 三层扫描架构

MC L10n 实现了革命性的三层扫描架构，为不同硬件配置提供最优解决方案：

- **🔧 标准扫描器**：稳定可靠，适合开发测试
- **⚡ 优化扫描器**：高性能并发，适合生产环境  
- **🔋 低内存扫描器**：内存安全，适合资源受限环境

## 📚 文档结构

### 1. [三层扫描架构概览](./scanning-architecture-overview.md)
- **核心架构设计理念**：性能分层、内存安全、用户体验优先
- **三层扫描器详细对比**：技术特点、性能指标、适用场景
- **统一API接口规范**：一致的调用接口，无缝切换
- **实时进度系统**：细粒度进度跟踪和状态监控
- **错误处理和恢复**：自动重试、中断恢复、回滚机制

### 2. [扫描器对比使用指南](./scanner-comparison-guide.md)  
- **智能选择决策树**：基于系统资源的自动推荐
- **详细性能对比表**：内存使用、处理速度、缓存效率
- **配置参数映射**：保守、中等、高性能三套方案
- **实际测试数据**：DeceasedCraft 整合包基准测试结果
- **运行时切换策略**：动态扫描器切换和自动降级

### 3. [低内存优化配置指南](./low-memory-optimization-guide.md)
- **内存优化核心技术**：流式处理、自动GC、分批处理
- **硬件配置推荐**：4GB/8GB/16GB+ 不同方案
- **实时配置调优API**：系统推荐、内存分析、压力测试
- **监控告警系统**：实时监控脚本和自动化告警
- **故障排除指南**：内存问题诊断和性能优化技巧

### 4. [API使用示例](./api-usage-examples.md)
- **三种扫描器完整示例**：启动、监控、状态查询
- **高级功能演示**：缓存管理、性能基准、内存测试
- **批量自动化脚本**：多目录扫描、实时监控、错误处理
- **配置文件驱动方案**：开发/生产/低内存环境配置
- **性能监控工具**：实时指标收集和可视化报告

### 5. [性能测试与故障排除](./performance-testing-troubleshooting.md)
- **综合基准测试框架**：自动化性能对比和分析
- **系统诊断工具**：内存分析、性能监控、健康检查
- **常见问题解决方案**：扫描卡顿、内存不足、数据库冲突
- **自动化故障排除**：智能诊断脚本和恢复策略
- **性能优化建议**：系统级和应用级调优指南

## 🚀 快速开始

### 选择合适的扫描器

根据您的系统配置选择：

```bash
# 4GB内存系统（推荐低内存扫描器）
curl -X POST "http://localhost:18000/api/v1/scan-low-memory/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/modpack",
    "memory_limit_mb": 256,
    "batch_size": 1
  }'

# 8GB+内存系统（推荐优化扫描器）
curl -X POST "http://localhost:18000/api/v1/scan-optimized/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/modpack",
    "max_workers": 8,
    "enable_smart_cache": true
  }'
```

### 系统健康检查

```bash
# 下载健康检查脚本
wget https://raw.githubusercontent.com/your-org/th-suite/main/scripts/scan_health_check.sh
chmod +x scan_health_check.sh

# 运行检查
./scan_health_check.sh
```

### 获取配置建议

```bash
# 获取系统推荐配置
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/memory-recommendations"

# 分析系统内存状况
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/system-memory"
```

## 🎯 使用场景

### 开发环境
- **扫描器**: 标准扫描器
- **特点**: 简单稳定，便于调试
- **适用**: 小型项目，代码开发

### 生产环境  
- **扫描器**: 优化扫描器
- **特点**: 高性能，智能缓存
- **适用**: 大型整合包，批量处理

### 低配置环境
- **扫描器**: 低内存扫描器  
- **特点**: 内存安全，自适应
- **适用**: 老旧硬件，资源受限

## 🔧 故障排除快速指南

### 常见问题及解决方案

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| 扫描无响应 | API调用无反应 | `poetry run python main.py --kill-all` |
| 内存不足 | 系统卡顿，OOM | 切换到低内存扫描器 |
| 速度过慢 | 进度更新缓慢 | 切换到优化扫描器 |
| 数据库无数据 | 扫描完成但无记录 | 重新初始化数据库 |

### 应急命令

```bash
# 清理冲突进程
poetry run python main.py --kill-all

# 重启服务
cd /home/saken/project/TH-Suite/apps/mc_l10n/backend
poetry run python main.py

# 重建数据库
rm -f app.db
poetry run python -c "from infrastructure.db_initializer import initialize_database; initialize_database()"
```

## 📊 性能基准

基于 DeceasedCraft 整合包（628个MOD，2.1GB）的测试结果：

| 指标 | 标准扫描器 | 优化扫描器 | 低内存扫描器 |
|------|------------|------------|--------------|
| **平均耗时** | 198秒 | 47秒 | 156秒 |
| **内存峰值** | 847MB | 312MB | 178MB |
| **吞吐量** | 398 文件/分钟 | 1435 文件/分钟 | 524 文件/分钟 |
| **成功率** | 100% | 100% | 100% |

## 🛠️ 开发者资源

### API端点总览

#### 标准扫描器
- `POST /api/v1/scan/start` - 启动扫描
- `GET /api/v1/scan/status/{scan_id}` - 获取状态
- `POST /api/v1/scan/cancel/{scan_id}` - 取消扫描

#### 优化扫描器
- `POST /api/v1/scan-optimized/start` - 启动优化扫描
- `GET /api/v1/scan-optimized/status/{scan_id}` - 获取详细状态
- `POST /api/v1/scan-optimized/benchmark` - 性能基准测试
- `POST /api/v1/scan-optimized/cache/clear` - 清理缓存

#### 低内存扫描器
- `POST /api/v1/scan-low-memory/start` - 启动低内存扫描
- `GET /api/v1/scan-low-memory/memory-recommendations` - 配置推荐
- `GET /api/v1/scan-low-memory/system-memory` - 系统内存分析
- `POST /api/v1/scan-low-memory/memory-test` - 内存压力测试

### 工具脚本

```bash
# 性能监控
python3 scripts/performance_monitor.py SCAN_ID optimized

# 性能诊断
python3 scripts/performance_diagnostic.py

# 批量测试
python3 scripts/performance_test.py /path/to/modpack --iterations 5
```

## 📝 技术栈

- **后端**: FastAPI + Python 3.12
- **数据库**: SQLite + V5 SSOT架构
- **并发**: asyncio + 线程池
- **内存管理**: psutil + gc
- **缓存**: BLAKE3哈希 + TTL策略
- **压缩**: zipfile + 流式处理

## 🔗 相关文档

- [V5 数据库架构设计](../architecture/database/v5-ssot-database-design.md)
- [Clean Architecture 实现](../architecture/clean-architecture.md)
- [API 规范文档](../api/api-specification.md)
- [部署指南](../deployment/deployment-guide.md)

## 📞 技术支持

如果您在使用过程中遇到问题：

1. 首先查看对应的文档章节
2. 运行系统健康检查脚本
3. 查看后端日志输出
4. 在 GitHub Issues 中报告问题

---

本文档持续更新，最后更新时间：2024年12月16日