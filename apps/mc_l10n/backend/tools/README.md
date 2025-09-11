# MC L10n 工具脚本

本目录包含用于 Minecraft 本地化工具的维护和诊断脚本。

## 脚本列表

### 🧪 test_parsing_fix.py
**用途**: 测试 MOD 解析逻辑  
**描述**: 验证文件名智能解析和模板变量解析功能是否正常工作  
**运行**: 
```bash
cd /path/to/TH-Suite/apps/mc_l10n/backend
poetry run python tools/test_parsing_fix.py
```

**输出示例**:
- ✅ AI-Improvements-1.18.2-0.5.2 → 名称='AI-Improvements', 版本='1.18.2-0.5.2'
- ✅ jei-1.19.2-11.5.0.297 → 名称='jei', 版本='1.19.2-11.5.0.297'

### 🧹 cleanup_mod_data.py
**用途**: 清理数据库中错误的 MOD 数据  
**描述**: 修复因解析问题导致的模组名称包含版本号的数据  
**运行**: 
```bash
cd /path/to/TH-Suite/apps/mc_l10n/backend
poetry run python tools/cleanup_mod_data.py
```

**功能**:
- 识别名称中包含版本号的问题模组
- 使用新的智能解析逻辑修复模组名称
- 安全预览模式，需用户确认后执行
- 同时更新 core_mods 和 core_mod_versions 表

### 🔍 check_mod_parsing_fixed.py
**用途**: 检查模组解析状态  
**描述**: 分析数据库中模组数据的解析质量和问题统计  
**运行**: 
```bash
cd /path/to/TH-Suite/apps/mc_l10n/backend
poetry run python tools/check_mod_parsing_fixed.py
```

**输出信息**:
- 数据库表结构概览
- 最新模组解析结果示例
- 问题模组数量统计
- 数据库总体统计信息

## 背景信息

### 问题描述
在早期版本中，MOD 解析器缺少对现代 Forge 模组的 `META-INF/mods.toml` 格式支持，导致：
- 77.5% 的模组名称包含版本号（如 "AI-Improvements-1.18.2-0.5.2"）
- ModID 和名称字段包含冗余的版本信息
- 用户界面显示不规范的模组名称

### 解决方案
1. **增强解析逻辑**: 添加对 `META-INF/mods.toml` 的完整支持
2. **智能文件名解析**: 实现多种文件名模式的自动识别
3. **模板变量支持**: 处理 `${version}` 等动态变量
4. **数据清理工具**: 修复现有错误数据

### 技术细节
- **支持格式**: META-INF/mods.toml (Forge), fabric.mod.json (Fabric), mcmod.info (Legacy)
- **解析模式**: 正则表达式匹配多种命名约定
- **版本提取**: 智能分离模组名称和版本号
- **向后兼容**: 保持对旧数据格式的支持

## 最佳实践

### 运行顺序
1. 首先运行 `test_parsing_fix.py` 验证解析逻辑
2. 运行 `check_mod_parsing_fixed.py` 了解当前状态
3. 如需修复数据，运行 `cleanup_mod_data.py`

### 注意事项
- 清理脚本会修改数据库，建议先备份
- 测试脚本使用内存数据库，不影响实际数据
- 所有脚本都支持相对路径，可从任意位置运行

### 故障排除
- 如果脚本无法找到模块，检查是否在正确的虚拟环境中
- 数据库路径问题可能是由于工作目录不正确导致
- 权限问题可能影响数据库文件的读写

## 更新日志

### 2025-09-11
- 将工具脚本从 `/tmp` 移动到项目 `tools/` 目录
- 修复硬编码路径，使用相对路径引用
- 添加完整的文档说明
- 优化脚本的项目集成度