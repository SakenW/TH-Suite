# hook pre-task - TH-Suite 专用版

为 TH-Suite 游戏本地化任务执行专用的预任务准备和上下文加载。

## Usage

```bash
npx claude-flow hook pre-task [options]
```

## Options

- `--description, -d <text>` - 任务描述，用于上下文分析
- `--auto-spawn-agents` - 自动生成所需代理 (default: true)
- `--load-memory` - 加载相关的历史会话记忆
- `--optimize-topology` - 选择最优的蜂群拓扑
- `--estimate-complexity` - 分析任务复杂度
- `--game-context <game>` - 指定游戏上下文 (minecraft, rusted-warfare)
- `--project-type <type>` - 项目类型 (mc_l10n, rw_l10n, shared)

## TH-Suite Specialized Examples

### Minecraft MOD 本地化任务

```bash
npx claude-flow hook pre-task \
  --description "扫描 Minecraft Forge MOD 并提取 i18n 文件" \
  --game-context minecraft \
  --project-type mc_l10n \
  --optimize-topology
```

### Trans-Hub 集成开发

```bash
npx claude-flow hook pre-task \
  -d "实现 Trans-Hub UIDA 协议同步功能" \
  --load-memory \
  --estimate-complexity
```

### JAR 文件处理开发

```bash
npx claude-flow hook pre-task \
  -d "开发安全的 JAR 文件修改和备份功能" \
  --auto-spawn-agents \
  --game-context minecraft
```

### 架构重构任务

```bash
npx claude-flow hook pre-task \
  -d "重构 Clean Architecture 分层结构" \
  --optimize-topology \
  --estimate-complexity
```

## TH-Suite Specialized Features

### 游戏上下文感知

根据指定的游戏类型自动配置：

- **Minecraft**: 
  - 激活 MOD 加载器检测
  - 配置 JAR 处理管道
  - 加载 Minecraft 特定的内存模式

- **Rusted Warfare**:
  - 配置 RW 文件格式处理
  - 加载 RW 本地化规则

### 智能代理生成

基于任务类型自动选择最适合的代理组合：

- **JAR 处理**: `jar-processor`, `security-scanner`, `backup-manager`
- **MOD 兼容性**: `mod-detector`, `compatibility-checker`, `version-analyzer`  
- **Trans-Hub 集成**: `api-integrator`, `sync-manager`, `protocol-validator`
- **架构开发**: `architect`, `clean-architecture-validator`, `dependency-analyzer`
- **安全开发**: `security-manager`, `crypto-specialist`, `sandbox-coordinator`

### 项目记忆加载

根据项目类型加载相关记忆：

- **技术决策**: 之前的架构选择和实现方案
- **API 设计**: Trans-Hub 集成的接口设计
- **安全策略**: JAR 处理的安全边界和防护措施
- **性能优化**: 大文件处理的优化策略
- **兼容性**: MOD 加载器的兼容性问题和解决方案

### 复杂度评估

针对 TH-Suite 特有的复杂度因素：

- **文件处理规模**: JAR 文件数量和大小
- **MOD 兼容性**: 支持的加载器类型数量
- **安全风险**: 文件修改的安全复杂度
- **集成复杂度**: Trans-Hub API 集成难度
- **性能要求**: 大规模处理的性能约束

## Integration

此 hook 会在以下情况自动调用：

- 开始新的 TH-Suite 开发任务
- 切换不同游戏项目上下文
- 启动复杂的文件处理操作
- 开始 Trans-Hub 集成任务

在代理协调中手动使用：

```bash
# 在 TH-Suite 特定代理中使用
npx claude-flow hook pre-task --description "你的游戏本地化任务" --game-context minecraft
```

## Output

返回针对 TH-Suite 优化的 JSON 格式：

```json
{
  "continue": true,
  "topology": "hierarchical",
  "agentsSpawned": [
    {
      "type": "jar-processor",
      "config": { "safety_mode": true, "backup_enabled": true }
    },
    {
      "type": "mod-detector", 
      "config": { "loaders": ["forge", "fabric", "quilt"] }
    },
    {
      "type": "trans-hub-integrator",
      "config": { "uida_version": "2.1", "batch_size": 1000 }
    }
  ],
  "gameContext": "minecraft",
  "projectType": "mc_l10n",
  "complexity": "high",
  "estimatedMinutes": 45,
  "memoryLoaded": {
    "jarProcessingStrategies": true,
    "modCompatibilityRules": true,
    "transHubApiPatterns": true
  },
  "securityProfile": {
    "jarProcessingSandbox": "enabled",
    "fileSystemRestrictions": "strict",
    "cryptoValidation": "enforced"
  }
}
```

## See Also

- `hook post-task` - TH-Suite 任务后清理
- `hook jar-processing` - JAR 文件处理专用 hook
- `hook trans-hub-sync` - Trans-Hub 同步 hook
- `agent spawn` - 手动创建游戏本地化代理