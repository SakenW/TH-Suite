# TH-Suite Hooks Commands

TH-Suite 专用的 Claude Flow hooks 命令，针对游戏本地化工具优化。

## Available Commands

- [pre-task](./pre-task.md) - 任务前准备和上下文加载
- [post-task](./post-task.md) - 任务后清理和性能分析
- [pre-edit](./pre-edit.md) - 编辑前准备和安全检查
- [post-edit](./post-edit.md) - 编辑后验证和格式化
- [session-end](./session-end.md) - 会话结束和数据导出

## TH-Suite 特殊 Hooks

### 游戏文件处理 Hooks
- [jar-processing](./jar-processing.md) - JAR 文件处理专用 hook
- [mod-compatibility](./mod-compatibility.md) - MOD 兼容性检查 hook
- [i18n-extraction](./i18n-extraction.md) - 国际化文件提取 hook

### Trans-Hub 集成 Hooks  
- [trans-hub-sync](./trans-hub-sync.md) - Trans-Hub 同步 hook
- [uida-validation](./uida-validation.md) - UIDA 协议验证 hook

### 安全和质量 Hooks
- [security-scan](./security-scan.md) - 安全扫描 hook
- [architecture-check](./architecture-check.md) - 架构合规检查 hook

## Integration with TH-Suite

这些 hooks 专为 TH-Suite 的游戏本地化场景优化：

- **Minecraft MOD 处理**: 自动检测和处理各种 MOD 加载器
- **JAR 文件安全**: 确保文件修改的安全性和完整性  
- **Clean Architecture**: 验证分层架构和依赖方向
- **Tauri 集成**: 前后端 IPC 通信安全检查
- **Trans-Hub 生态**: 与翻译平台的深度集成验证

## Usage Examples

```bash
# 启动 MC L10n 开发任务
npx claude-flow hook pre-task --description "开发 Minecraft MOD 扫描功能"

# 处理 JAR 文件时的安全检查
npx claude-flow hook jar-processing --file-path "./mods/example.jar" --safety-check

# 完成 Trans-Hub 同步任务
npx claude-flow hook post-task --task-id "trans-hub-sync" --export-metrics
```

## Automatic Triggers

这些 hooks 会在以下情况自动触发：

- 检测到 JAR 文件修改时
- Trans-Hub API 调用前后
- MOD 兼容性检查时
- 架构层级违规时
- 安全风险检测时