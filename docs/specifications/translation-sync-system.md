# 翻译数据同步系统规范

## 概述

TH-Suite 翻译数据同步系统是一个基于现有架构的高效、可靠的翻译数据同步解决方案。该系统集成了增量检测、三路合并、智能压缩和缓存优化等先进技术，为 Minecraft 本地化工具提供企业级的数据同步能力。

## 系统架构

### 核心组件

#### 1. 翻译同步引擎 (Translation Sync Engine)
- **文件位置**: `infrastructure/services/translation_sync_engine.py`
- **主要功能**:
  - 增量变更检测
  - 三路合并算法
  - 同步会话管理
  - 冲突解决机制

#### 2. 同步优化服务 (Sync Optimization Service)
- **文件位置**: `infrastructure/services/sync_optimization_service.py`
- **主要功能**:
  - 智能压缩传输
  - 批量数据处理
  - CAS缓存集成
  - 性能监控统计

#### 3. API路由控制器
- **文件位置**: `api/routes/translation_sync_routes.py`
- **主要功能**:
  - RESTful API接口
  - 请求验证和处理
  - 响应格式化
  - 错误处理

#### 4. 前端集成服务
- **文件位置**: `frontend/src/services/api/TranslationSyncApiService.ts`
- **主要功能**:
  - API客户端封装
  - 类型定义
  - 实时状态监控
  - 用户界面集成

## 技术特性

### 1. 增量同步检测
- **基于BLAKE3指纹**: 高性能内容哈希算法
- **变更类型识别**: 新增、修改、删除、移动、冲突
- **时间戳比较**: 基于最后修改时间的变更判断
- **批量检测优化**: 支持大规模数据集的高效处理

### 2. 三路合并算法
- **自动合并**: 非冲突变更的智能合并
- **冲突检测**: 准确识别数据冲突情况
- **解决策略**:
  - 本地优先 (LOCAL_WINS)
  - 远程优先 (REMOTE_WINS)
  - 最新优先 (LATEST_WINS)
  - 人工解决 (MANUAL_RESOLVE)
  - 三路合并 (THREE_WAY_MERGE)

### 3. 智能压缩传输
- **Zstd压缩算法**: 高效的压缩性能
- **语言专用字典**: 
  - 中文字典: 针对中文翻译优化，压缩率提升20-30%
  - 英文字典: 标准英文词汇压缩
  - 通用字典: 其他语言的通用压缩
- **动态压缩级别**: 根据数据特征自动调整

### 4. CAS内容寻址缓存
- **内容哈希存储**: 基于BLAKE3的内容寻址
- **去重优化**: 相同内容只存储一次
- **键集指纹缓存**: 翻译键集合的快速查找
- **LRU清理策略**: 自动清理过期缓存

### 5. 批量传输管理
- **智能分批**: 按语言和大小自动分批
- **并发传输**: 支持多线程并行传输
- **断点续传**: 大数据量同步的中断恢复
- **失败重试**: 智能重试和错误恢复

## API接口规范

### 同步准备
```http
POST /api/v1/sync/prepare
Content-Type: application/json

{
  "direction": "bidirectional",
  "language_filters": ["zh_cn", "en_us"],
  "pack_filters": ["minecraft", "jei"],
  "auto_resolve_conflicts": true,
  "conflict_resolution": "latest_wins",
  "batch_size": 100
}
```

### 执行同步
```http
POST /api/v1/sync/execute/{session_id}
Content-Type: application/json

{
  "force": false,
  "dry_run": false
}
```

### 获取状态
```http
GET /api/v1/sync/status/{session_id}
```

### 快速同步
```http
POST /api/v1/sync/quick/push
POST /api/v1/sync/quick/pull
```

## 数据库架构

### 同步会话表
```sql
CREATE TABLE sync_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    total_entries INTEGER DEFAULT 0,
    processed_entries INTEGER DEFAULT 0,
    success_entries INTEGER DEFAULT 0,
    failed_entries INTEGER DEFAULT 0,
    conflicts_entries INTEGER DEFAULT 0,
    config_json TEXT,
    result_json TEXT,
    errors_json TEXT
);
```

### 同步检查点表
```sql
CREATE TABLE sync_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    checkpoint_type TEXT NOT NULL,
    checkpoint_data TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sync_sessions(session_id)
);
```

### 冲突解决记录表
```sql
CREATE TABLE sync_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    local_entry_json TEXT,
    remote_entry_json TEXT,
    base_entry_json TEXT,
    resolution TEXT,
    resolved_entry_json TEXT,
    resolved_at TEXT,
    resolver TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sync_sessions(session_id)
);
```

## 性能指标

### 同步性能目标
- **100MB翻译数据同步**: < 30秒
- **10,000+条目增量同步**: < 10秒
- **并发同步**: 不影响UI响应性
- **压缩比例**: 中文50-70%，英文60-80%

### 缓存命中率
- **键集指纹缓存**: > 85%
- **CAS对象缓存**: > 90%
- **批量传输复用**: > 70%

### 系统资源使用
- **内存使用**: < 512MB (处理1GB翻译数据)
- **CPU使用**: < 50% (单核)
- **磁盘I/O**: 优化顺序读写

## 使用指南

### 后端集成

```python
# 创建同步引擎
from infrastructure.services.translation_sync_engine import get_translation_sync_engine

sync_engine = get_translation_sync_engine()

# 准备同步
session_id, analysis = await sync_engine.prepare_sync(
    SyncDirection.BIDIRECTIONAL,
    {
        "language_filters": ["zh_cn"],
        "auto_resolve_conflicts": True
    }
)

# 执行同步
success = await sync_engine.execute_sync(session_id)

# 获取状态
status = await sync_engine.get_sync_status(session_id)
```

### 前端集成

```typescript
import { translationSyncApiService } from './services/api/TranslationSyncApiService';

// 准备同步
const analysis = await translationSyncApiService.prepareSync({
  direction: 'bidirectional',
  language_filters: ['zh_cn', 'en_us'],
  auto_resolve_conflicts: true
});

// 执行同步
await translationSyncApiService.executeSync(analysis.session_id, {
  dry_run: false
});

// 监控进度
await translationSyncApiService.pollSyncStatus(
  analysis.session_id,
  (progress) => {
    console.log(`进度: ${progress.progress_percentage}%`);
  }
);
```

## 错误处理

### 常见错误类型
1. **网络连接错误**: 自动重试机制
2. **数据冲突错误**: 冲突解决流程
3. **权限错误**: 用户身份验证
4. **存储空间不足**: 清理缓存策略
5. **数据格式错误**: 数据验证和修复

### 错误恢复策略
- **自动重试**: 网络和临时错误
- **回滚机制**: 数据一致性保证
- **备份恢复**: 严重错误的数据恢复
- **增量修复**: 部分失败的增量同步

## 监控和日志

### 关键指标监控
- 同步成功率
- 平均同步时间
- 数据传输量
- 缓存命中率
- 冲突解决率

### 日志记录
- **操作日志**: 所有同步操作的详细记录
- **性能日志**: 处理时间和资源使用
- **错误日志**: 错误详情和堆栈跟踪
- **审计日志**: 数据变更的审计跟踪

## 安全考虑

### 数据安全
- **传输加密**: HTTPS/TLS加密传输
- **存储加密**: SQLCipher数据库加密
- **访问控制**: 基于角色的权限管理
- **数据验证**: 输入数据的完整性验证

### 操作安全
- **幂等性**: 重复操作的安全性保证
- **原子性**: 事务性操作的一致性
- **备份策略**: 同步前自动备份
- **回滚机制**: 失败操作的安全回滚

## 扩展性

### 水平扩展
- **多服务器部署**: 负载均衡和高可用
- **分布式缓存**: Redis集群支持
- **消息队列**: 异步任务处理
- **微服务架构**: 组件独立部署

### 垂直扩展
- **多线程并发**: CPU多核利用
- **内存池管理**: 大数据集处理
- **I/O优化**: 异步文件操作
- **数据库优化**: 索引和查询优化

## 测试策略

### 单元测试
- 核心算法测试
- 数据处理测试
- 缓存功能测试
- API接口测试

### 集成测试
- 完整同步流程测试
- 多组件协作测试
- 错误恢复测试
- 性能压力测试

### 端到端测试
- 用户场景测试
- 前后端集成测试
- 真实数据测试
- 长期稳定性测试

## 部署和配置

### 环境要求
- **Python 3.12+**
- **Node.js 18+**
- **SQLite 3.38+**
- **内存**: 最少4GB，推荐8GB
- **存储**: SSD推荐，最少10GB可用空间

### 配置参数
```yaml
sync:
  batch_size: 100
  max_concurrency: 3
  compression_level: 3
  cache_ttl: 300
  retry_attempts: 3
  retry_delay: 5

compression:
  algorithm: "zstd"
  dictionary_size: 1024
  train_samples: 100

cache:
  max_size: "1GB"
  cleanup_interval: 3600
  retention_days: 30
```

## 维护和支持

### 定期维护
- **缓存清理**: 定期清理过期缓存
- **数据库优化**: 索引重建和统计更新
- **日志轮转**: 防止日志文件过大
- **性能调优**: 根据使用情况调整参数

### 故障排查
- **状态检查**: 系统健康状态监控
- **日志分析**: 错误模式识别
- **性能分析**: 瓶颈定位和优化
- **数据一致性**: 定期数据完整性检查

## 版本历史

### v1.0.0 (2025-09-20)
- 初始版本发布
- 基础同步功能
- 增量检测算法
- 三路合并实现
- CAS缓存集成
- 智能压缩优化
- API接口完善
- 前端集成支持

### 未来规划

#### v1.1.0
- 实时同步支持
- 更多压缩算法
- 改进的冲突解决界面
- 批量操作优化

#### v1.2.0
- 分布式同步支持
- 高级缓存策略
- 机器学习优化
- 多租户支持

## 结论

TH-Suite 翻译数据同步系统提供了一个完整、高效、可靠的翻译数据同步解决方案。通过集成现有架构的优势，该系统实现了增量同步、智能压缩、自动冲突解决等先进功能，为Minecraft本地化工具提供了企业级的数据同步能力。

系统的模块化设计确保了良好的可扩展性和可维护性，而完善的API接口和前端集成为用户提供了友好的使用体验。通过持续的优化和改进，该系统将继续为TH-Suite生态系统提供强大的数据同步支持。