# hook jar-processing - TH-Suite JAR 文件处理专用

为 TH-Suite JAR 文件处理任务提供专用的安全检查、完整性验证和性能监控。

## Usage

```bash
npx claude-flow hook jar-processing [options]
```

## Options

- `--file-path, -f <path>` - JAR 文件路径
- `--operation <op>` - 操作类型 (extract, modify, repack, validate)
- `--safety-check` - 执行安全检查 (default: true)
- `--integrity-check` - 执行完整性校验 (default: true)
- `--backup-create` - 创建备份文件 (default: true)
- `--mod-loader <loader>` - MOD 加载器类型 (forge, fabric, quilt, neoforge)
- `--sandbox-mode` - 启用沙盒模式 (default: true)
- `--performance-monitor` - 启用性能监控 (default: true)

## TH-Suite JAR Processing Examples

### 提取 Minecraft Forge MOD

```bash
npx claude-flow hook jar-processing \
  --file-path "./mods/example-mod-1.20.1.jar" \
  --operation extract \
  --mod-loader forge \
  --safety-check \
  --backup-create
```

### 修改 JAR 文件中的 i18n

```bash
npx claude-flow hook jar-processing \
  -f "./mods/target-mod.jar" \
  --operation modify \
  --integrity-check \
  --sandbox-mode \
  --performance-monitor
```

### 重新打包 MOD 文件

```bash
npx claude-flow hook jar-processing \
  -f "./temp/modified-mod/" \
  --operation repack \
  --mod-loader fabric \
  --safety-check
```

### 验证 JAR 文件完整性

```bash
npx claude-flow hook jar-processing \
  -f "./output/localized-mod.jar" \
  --operation validate \
  --integrity-check
```

## Specialized Features

### 安全检查

针对游戏 MOD 文件的安全验证：

- **恶意代码检测**: 扫描已知的恶意模式和代码注入
- **路径遍历防护**: 检查解压路径的安全性
- **文件权限验证**: 确保文件权限设置正确
- **数字签名校验**: 验证 MOD 文件的数字签名

### MOD 加载器兼容性检查

根据指定的加载器类型进行专用检查：

- **Forge**: 
  - `mcmod.info` 文件验证
  - Forge 版本兼容性检查
  - 依赖 MOD 分析

- **Fabric**:
  - `fabric.mod.json` 文件验证
  - Fabric API 兼容性
  - Mixin 配置检查

- **Quilt**:
  - `quilt.mod.json` 文件验证
  - Quilt 特有功能检查
  - 向后兼容性验证

- **NeoForge**:
  - NeoForge 特有配置验证
  - 版本迁移检查
  - 兼容性层验证

### 完整性校验

多层次的文件完整性验证：

- **文件结构检查**: 验证 JAR 内部结构完整性
- **CRC 校验**: 计算和验证文件校验和
- **压缩完整性**: 检查 ZIP/JAR 压缩格式正确性
- **资源引用**: 验证内部资源引用的完整性

### 沙盒模式

安全的文件处理环境：

- **隔离执行**: 在受控环境中处理 JAR 文件
- **权限限制**: 限制文件系统访问权限
- **资源监控**: 监控内存和 CPU 使用
- **自动清理**: 处理完成后清理临时文件

### 性能监控

实时性能指标收集：

- **处理速度**: JAR 解压和压缩速度
- **内存使用**: 峰值内存使用量
- **I/O 性能**: 文件读写性能指标
- **并发效率**: 多文件并发处理性能

## Output

返回详细的 JAR 处理结果：

```json
{
  "filePath": "./mods/example-mod-1.20.1.jar",
  "operation": "extract",
  "success": true,
  "modLoader": "forge",
  "securityScan": {
    "maliciousPatterns": 0,
    "suspiciousFiles": [],
    "pathTraversalRisk": false,
    "signatureValid": true,
    "riskLevel": "low"
  },
  "integrityCheck": {
    "structureValid": true,
    "crcMatches": true,
    "compressionValid": true,
    "resourceReferences": "complete",
    "corruptedFiles": []
  },
  "modInformation": {
    "modId": "example-mod",
    "version": "1.20.1-2.5.0",
    "mcVersion": "1.20.1",
    "forgeVersion": "47.2.0",
    "dependencies": ["forge", "jei"],
    "optionalDependencies": ["waila"]
  },
  "extractedFiles": {
    "total": 247,
    "i18nFiles": {
      "en_us.json": {
        "keys": 156,
        "size": "12.3 KB",
        "encoding": "UTF-8"
      },
      "zh_cn.json": {
        "keys": 98,
        "size": "15.7 KB",
        "encoding": "UTF-8"
      }
    },
    "assetFiles": 89,
    "classFiles": 134,
    "configFiles": 4
  },
  "performance": {
    "extractionTime": "2.4s",
    "peakMemory": "45 MB",
    "ioThroughput": "15.2 MB/s",
    "filesPerSecond": 103
  },
  "backup": {
    "created": true,
    "path": "./backups/example-mod-1.20.1.jar.backup",
    "size": "2.1 MB",
    "timestamp": "2024-12-18T10:30:45Z"
  },
  "sandbox": {
    "enabled": true,
    "temporaryDir": "/tmp/th-suite-sandbox-abc123",
    "cleanedUp": true,
    "isolationLevel": "strict"
  },
  "recommendations": [
    "consider_updating_forge_version_for_better_compatibility",
    "add_missing_translation_keys_for_zh_cn",
    "optimize_texture_sizes_for_better_performance"
  ]
}
```

## Integration

此 hook 在以下情况自动触发：

- 检测到 JAR 文件操作
- MOD 扫描过程中
- 文件修改任务开始前
- 重新打包操作时
- 完整性验证需要时

## Error Handling

专用的错误处理和恢复机制：

- **文件损坏**: 自动尝试修复或使用备份
- **权限错误**: 提供权限修复建议
- **兼容性问题**: 提供替代方案
- **沙盒错误**: 降级到安全模式
- **性能问题**: 调整处理策略

## See Also

- `hook mod-compatibility` - MOD 兼容性检查
- `hook security-scan` - 安全扫描
- `hook pre-task` - 任务前准备
- `hook post-task` - 任务后验证