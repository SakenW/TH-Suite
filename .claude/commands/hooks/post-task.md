# hook post-task - TH-Suite 专用版

为 TH-Suite 游戏本地化任务执行专用的任务后清理、性能分析和记忆存储。

## Usage

```bash
npx claude-flow hook post-task [options]
```

## Options

- `--task-id, -t <id>` - 任务标识符，用于跟踪
- `--analyze-performance` - 生成性能指标 (default: true)
- `--store-decisions` - 保存任务决策到记忆库
- `--export-learnings` - 导出神经模式学习结果
- `--generate-report` - 创建任务完成报告
- `--game-context <game>` - 游戏上下文 (minecraft, rusted-warfare)
- `--validate-output` - 验证输出文件完整性
- `--security-scan` - 执行安全扫描

## TH-Suite Specialized Examples

### JAR 处理任务完成

```bash
npx claude-flow hook post-task \
  --task-id "jar-processing-forge-mods" \
  --game-context minecraft \
  --validate-output \
  --security-scan
```

### Trans-Hub 同步任务

```bash
npx claude-flow hook post-task \
  -t "trans-hub-sync-project-123" \
  --analyze-performance \
  --store-decisions \
  --export-learnings
```

### MOD 兼容性检测完成

```bash
npx claude-flow hook post-task \
  -t "mod-compatibility-scan" \
  --game-context minecraft \
  --generate-report \
  --validate-output
```

### 架构重构任务完成

```bash
npx claude-flow hook post-task \
  -t "clean-architecture-refactor" \
  --analyze-performance \
  --store-decisions
```

## TH-Suite Specialized Features

### 游戏文件验证

根据游戏类型执行专用验证：

- **Minecraft JAR 验证**:
  - 文件完整性校验
  - MOD 签名验证
  - 资源包格式检查
  - 语言文件编码验证

- **Rusted Warfare 验证**:
  - 游戏文件格式检查
  - 本地化文件完整性
  - 资源引用验证

### 性能分析

针对 TH-Suite 特有的性能指标：

- **文件处理性能**:
  - JAR 解压缩速度
  - 文件扫描效率
  - 内存使用优化
  - 并发处理性能

- **MOD 处理性能**:
  - 兼容性检测速度
  - 批量处理效率
  - 缓存命中率
  - 错误恢复时间

- **Trans-Hub 集成性能**:
  - API 调用延迟
  - 数据传输效率
  - 同步成功率
  - 重试机制性能

### 安全扫描

游戏本地化特有的安全检查：

- **JAR 文件安全**:
  - 恶意代码检测
  - 文件权限验证
  - 路径遍历防护
  - 完整性校验

- **MOD 安全性**:
  - 数字签名验证
  - 沙盒逃逸检测
  - 权限滥用扫描
  - 恶意行为分析

### 决策存储

保存 TH-Suite 特有的决策记录：

- **技术选择**:
  - MOD 加载器支持策略
  - 文件格式处理方案
  - 兼容性解决方案
  - 性能优化策略

- **安全策略**:
  - JAR 处理安全边界
  - 文件访问权限设置
  - 加密算法选择
  - 沙盒配置参数

- **集成方案**:
  - Trans-Hub API 使用模式
  - UIDA 协议实现细节
  - 错误处理策略
  - 数据同步方案

## Integration

此 hook 会在以下情况自动调用：

- 完成 JAR 文件处理任务
- 结束 Trans-Hub 同步操作
- 完成 MOD 兼容性检测
- 结束架构重构工作
- 完成安全扫描任务

在代理协调中手动使用：

```bash
# 在 TH-Suite 特定代理中使用
npx claude-flow hook post-task --task-id "你的任务ID" --game-context minecraft
```

## Output

返回针对 TH-Suite 优化的 JSON 格式：

```json
{
  "taskId": "jar-processing-forge-mods",
  "gameContext": "minecraft",
  "duration": 2400000,
  "tokensUsed": 52000,
  "filesProcessed": {
    "jarFiles": 15,
    "extractedFiles": 342,
    "i18nFiles": 89,
    "modifiedFiles": 12
  },
  "performanceMetrics": {
    "jarExtractionSpeed": "8.5 MB/s",
    "fileProcessingRate": "245 files/min",
    "memoryPeakUsage": "512 MB",
    "cacheHitRate": 0.76
  },
  "securityScan": {
    "maliciousFilesDetected": 0,
    "permissionViolations": 0,
    "integrityChecksums": "all_passed",
    "sandboxBreaches": 0
  },
  "gameSpecificMetrics": {
    "modLoadersDetected": ["forge", "fabric"],
    "compatibilityIssues": 2,
    "backupFilesCreated": 15,
    "translationKeysExtracted": 1247
  },
  "transHubIntegration": {
    "apiCallsSuccessful": 23,
    "syncedTranslations": 1189,
    "conflictsResolved": 8,
    "uidaProtocolVersion": "2.1"
  },
  "decisionsStored": [
    "forge_mod_processing_strategy",
    "jar_backup_retention_policy", 
    "translation_key_extraction_rules",
    "compatibility_conflict_resolution"
  ],
  "learningsExported": true,
  "reportPath": "/reports/task-jar-processing-forge-mods.md",
  "outputValidation": {
    "jarIntegrity": "verified",
    "translationCompleteness": "98.7%",
    "formatCompliance": "passed",
    "filePermissions": "secure"
  },
  "recommendedFollowUp": [
    "run_compatibility_tests_with_target_minecraft_version",
    "validate_modified_jars_in_sandbox_environment",
    "backup_original_files_to_secure_location"
  ]
}
```

## See Also

- `hook pre-task` - TH-Suite 任务前准备
- `hook jar-processing` - JAR 文件处理验证
- `hook security-scan` - 安全扫描详情
- `performance report` - 详细性能指标
- `memory usage` - 记忆管理
- `neural patterns` - 模式分析