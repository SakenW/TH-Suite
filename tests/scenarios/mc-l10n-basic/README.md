# MC L10n 基础场景

此场景演示了Minecraft模组本地化的完整工作流程，包括项目扫描、语言提取、翻译处理和构建打包。

## 场景流程

1. **环境准备** - 初始化测试环境和数据库
2. **项目导入** - 导入测试模组包
3. **扫描分析** - 自动扫描模组结构和语言文件
4. **语言提取** - 提取需要翻译的文本条目
5. **翻译处理** - 模拟翻译流程
6. **构建打包** - 生成本地化后的模组包
7. **验证测试** - 验证结果的正确性
8. **性能监控** - 收集性能指标
9. **环境清理** - 清理测试数据

## 使用方法

```bash
# 运行完整场景
python tests/scenarios/shared/scripts/run_scenario.py tests/scenarios/mc-l10n-basic/manifest.yaml

# 仅运行特定步骤
python tests/scenarios/shared/scripts/run_scenario.py tests/scenarios/mc-l10n-basic/manifest.yaml --step scan
```

## 场景数据

- `inputs/mod_metadata.jsonl` - 模组元数据
- `inputs/language_entries.jsonl` - 语言条目数据
- `inputs/translation_requests.jsonl` - 翻译请求
- `inputs/build_config.jsonl` - 构建配置

## 输出结果

场景运行完成后，结果将保存在 `.artifacts/` 目录中，包括：
- 执行日志
- 性能报告
- 构建产物
- 验证结果