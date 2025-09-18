# hook trans-hub-sync - TH-Suite Trans-Hub 集成专用

为 TH-Suite 与 Trans-Hub 平台的同步操作提供专用的连接管理、数据验证和冲突解决。

## Usage

```bash
npx claude-flow hook trans-hub-sync [options]
```

## Options

- `--project-id, -p <id>` - Trans-Hub 项目 ID
- `--operation <op>` - 同步操作 (push, pull, sync, validate)
- `--uida-version <ver>` - UIDA 协议版本 (default: 2.1)
- `--batch-size <size>` - 批处理大小 (default: 1000)
- `--conflict-resolution <strategy>` - 冲突解决策略 (manual, auto, skip)
- `--validate-before-sync` - 同步前验证数据 (default: true)
- `--dry-run` - 模拟同步不执行实际操作
- `--retry-count <num>` - 重试次数 (default: 3)
- `--timeout <ms>` - 请求超时时间 (default: 30000)

## TH-Suite Trans-Hub Sync Examples

### 推送本地翻译到 Trans-Hub

```bash
npx claude-flow hook trans-hub-sync \
  --project-id "minecraft-mods-zh-cn" \
  --operation push \
  --batch-size 500 \
  --validate-before-sync
```

### 从 Trans-Hub 拉取最新翻译

```bash
npx claude-flow hook trans-hub-sync \
  -p "example-mod-project" \
  --operation pull \
  --conflict-resolution auto \
  --retry-count 5
```

### 双向同步操作

```bash
npx claude-flow hook trans-hub-sync \
  -p "forge-mods-collection" \
  --operation sync \
  --uida-version 2.1 \
  --conflict-resolution manual
```

### 验证同步状态

```bash
npx claude-flow hook trans-hub-sync \
  -p "fabric-mods-project" \
  --operation validate \
  --dry-run
```

## Specialized Features

### UIDA 协议集成

完整的 UIDA (Unified International Data Architecture) 协议支持：

- **版本兼容性**: 自动检测和适配 UIDA 版本
- **数据格式转换**: Minecraft i18n ↔ UIDA 格式转换
- **完整性校验**: 数据传输完整性验证
- **压缩优化**: 智能数据压缩和传输优化

### 智能冲突解决

多种冲突解决策略：

- **自动合并**: 
  - 基于时间戳的自动合并
  - 智能翻译质量评估
  - 上下文相似性分析
  - 用户贡献权重计算

- **手动解决**:
  - 交互式冲突解决界面
  - 并排对比显示
  - 版本历史追踪
  - 专家评审推荐

- **策略跳过**:
  - 保持本地版本
  - 跳过冲突条目
  - 标记待审核状态

### 批量处理优化

高效的大规模数据同步：

- **智能分批**: 根据网络状况动态调整批大小
- **并发控制**: 多线程同步优化
- **断点续传**: 支持中断后继续同步
- **增量同步**: 仅同步变更的翻译条目

### 数据验证

多层次的数据完整性验证：

- **格式验证**: JSON 格式和结构校验
- **编码检查**: 字符编码一致性验证
- **引用完整性**: 翻译键引用的完整性
- **质量评估**: 翻译质量自动评分

### 连接管理

健壮的网络连接处理：

- **自动重连**: 网络中断自动重连
- **负载均衡**: 多服务器负载分散
- **缓存策略**: 智能本地缓存机制
- **离线模式**: 网络不可用时的离线处理

## Output

返回详细的同步结果：

```json
{
  "projectId": "minecraft-mods-zh-cn",
  "operation": "sync",
  "success": true,
  "uidaVersion": "2.1",
  "sync": {
    "startTime": "2024-12-18T10:30:00Z",
    "endTime": "2024-12-18T10:32:15Z",
    "duration": "2m 15s"
  },
  "statistics": {
    "totalKeys": 2457,
    "pushedKeys": 156,
    "pulledKeys": 89,
    "conflictedKeys": 12,
    "resolvedConflicts": 10,
    "pendingConflicts": 2,
    "unchangedKeys": 2200
  },
  "dataTransfer": {
    "uploadedSize": "245 KB",
    "downloadedSize": "156 KB",
    "compressionRatio": 0.78,
    "transferSpeed": "1.2 MB/s"
  },
  "conflicts": [
    {
      "key": "item.example_mod.magic_sword",
      "local": "魔法剑",
      "remote": "魔法之剑",
      "resolution": "manual",
      "status": "pending",
      "context": "weapon_items",
      "lastModified": {
        "local": "2024-12-17T15:30:00Z",
        "remote": "2024-12-18T09:15:00Z"
      }
    }
  ],
  "validationResults": {
    "formatErrors": 0,
    "encodingIssues": 0,
    "brokenReferences": 1,
    "qualityScore": 0.94,
    "completenessRate": 0.87
  },
  "performance": {
    "apiCalls": 15,
    "averageResponseTime": "245ms",
    "retries": 2,
    "cacheHits": 89,
    "networkEfficiency": 0.92
  },
  "projectInfo": {
    "name": "Minecraft MODs 中文本地化",
    "language": "zh_cn",
    "contributors": 12,
    "lastSync": "2024-12-18T10:32:15Z",
    "totalProgress": "87%"
  },
  "recommendations": [
    "resolve_pending_conflicts_before_next_sync",
    "update_broken_reference_for_key_item.example_mod.broken_key",
    "consider_increasing_batch_size_for_better_performance",
    "review_low_quality_translations_in_magic_items_context"
  ],
  "nextSync": {
    "recommended": "2024-12-19T10:00:00Z",
    "autoScheduled": true,
    "estimatedDuration": "1m 30s"
  }
}
```

## Integration

此 hook 在以下情况自动触发：

- 定时同步任务
- 本地翻译修改后
- 项目构建前
- 用户手动同步请求
- 冲突检测时

## Error Handling

专用的错误处理和恢复机制：

- **网络错误**: 自动重试和降级策略
- **认证失败**: 刷新令牌和重新认证
- **数据损坏**: 数据完整性修复
- **冲突过多**: 批量冲突处理建议
- **服务不可用**: 离线模式切换

## Conflict Resolution Strategies

### 自动策略 (auto)

```javascript
// 自动合并规则示例
{
  "rules": [
    {
      "condition": "remote_newer_and_longer",
      "action": "use_remote",
      "weight": 0.8
    },
    {
      "condition": "local_has_context_improvement", 
      "action": "use_local",
      "weight": 0.7
    },
    {
      "condition": "quality_score_higher",
      "action": "use_higher_quality",
      "weight": 0.9
    }
  ]
}
```

### 手动策略 (manual)

提供详细的冲突信息供用户决策：

- 并排对比显示
- 翻译历史和贡献者信息
- 上下文和使用场景
- 质量评分和推荐理由

## See Also

- `hook uida-validation` - UIDA 协议验证
- `hook pre-task` - 同步前准备
- `hook post-task` - 同步后验证
- `memory usage` - 同步历史记忆
- `performance report` - 同步性能分析