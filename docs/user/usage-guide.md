# TH Suite 使用指南

## 目录

1. [快速开始](#快速开始)
2. [扫描项目](#扫描项目)
3. [管理补丁](#管理补丁)
4. [质量检查](#质量检查)
5. [Trans-Hub 同步](#trans-hub-同步)
6. [高级功能](#高级功能)
7. [常见问题](#常见问题)

## 快速开始

### 1. 环境准备

#### Windows
```bash
# 安装 Python 3.12+
# 下载地址: https://www.python.org/downloads/

# 安装 Node.js 18+
# 下载地址: https://nodejs.org/

# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装 pnpm
npm install -g pnpm

# 安装 Task (可选)
scoop install task
# 或
choco install go-task
```

#### macOS
```bash
# 使用 Homebrew
brew install python@3.12 node@18 poetry go-task/tap/go-task
npm install -g pnpm
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3-pip nodejs npm
curl -sSL https://install.python-poetry.org | python3 -
npm install -g pnpm
sudo snap install task --classic
```

### 2. 项目安装

```bash
# 克隆仓库
git clone https://github.com/Saken/th-suite.git
cd th-suite

# 安装依赖
task install
# 或手动安装
poetry install
cd apps/mc_l10n/frontend && pnpm install && cd ../../../
```

### 3. 启动应用

```bash
# 使用 Task (推荐)
task dev:mc

# 或分别启动前后端
# 终端 1 - 启动后端
cd apps/mc_l10n/backend
poetry run python main.py

# 终端 2 - 启动前端
cd apps/mc_l10n/frontend
npm run tauri:dev
```

应用启动后：
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端界面: 自动打开 Tauri 窗口

## 扫描项目

### 扫描整合包

1. **打开扫描页面**
   - 启动应用后，点击左侧菜单的 "扫描" 图标
   - 或使用快捷键 `2` 直接跳转

2. **选择项目目录**
   ```
   支持的目录结构：
   ├── mods/              # 模组文件夹
   │   ├── mod1.jar
   │   └── mod2.jar
   ├── resourcepacks/     # 资源包文件夹
   │   └── pack1.zip
   └── manifest.json      # CurseForge/Modrinth 清单
   ```

3. **开始扫描**
   - 点击 "选择文件夹" 按钮
   - 选择整合包根目录
   - 系统自动识别并提取语言文件

4. **查看扫描结果**
   - **总模组数**: 检测到的模组数量
   - **语言文件数**: 提取的语言文件总数
   - **可翻译键数**: 所有可翻译的文本条目
   - **支持的语言**: 检测到的语言列表

### 扫描单个模组

```bash
# 使用 CLI 工具
poetry run python -m mc_l10n scan --path /path/to/mod.jar --output scan_result.json
```

### 批量扫描

```python
# 使用 Python API
from mc_l10n.services import ScanService

scanner = ScanService()
results = scanner.batch_scan([
    "/path/to/mod1.jar",
    "/path/to/mod2.jar",
    "/path/to/modpack/"
])
```

## 管理补丁

### 创建补丁集

1. **进入补丁管理页面**
   - 点击左侧菜单 "补丁" 或按 `3` 键

2. **创建新补丁**
   - 点击 "创建补丁集" 按钮
   - 填写补丁信息：
     - **名称**: 补丁集名称
     - **版本**: 版本号（如 1.0.0）
     - **描述**: 补丁用途说明
     - **目标语言**: 选择目标语言（如 zh_CN）

3. **添加补丁项**
   - 选择要修改的模组/容器
   - 选择合并策略：
     - `OVERLAY`: 仅覆盖存在的键
     - `REPLACE`: 完全替换文件
     - `MERGE`: 合并内容
     - `CREATE_IF_MISSING`: 不存在时创建

4. **编辑翻译内容**
   - 使用内置编辑器修改翻译
   - 支持批量查找替换
   - 实时预览效果

### 应用补丁

```bash
# 应用补丁到项目
task apply-patch --patch-id=patch_001 --target=/path/to/project

# 试运行（不实际修改文件）
task apply-patch --patch-id=patch_001 --target=/path/to/project --dry-run
```

### 回滚补丁

```bash
# 回滚最近的补丁
task rollback-patch --target=/path/to/project

# 回滚到特定版本
task rollback-patch --target=/path/to/project --to-version=1.0.0
```

## 质量检查

### 运行质量检查

1. **自动检查**
   - 在创建或应用补丁时自动运行
   - 检查结果显示在界面右侧面板

2. **手动检查**
   ```bash
   # 检查单个文件
   task quality-check --file=/path/to/lang.json
   
   # 检查整个项目
   task quality-check --project=/path/to/project
   ```

### 质量检查项

#### 占位符一致性
```json
// ❌ 错误示例
{
  "source": "Welcome %s to %s server!",
  "target": "欢迎 %s 来到服务器！"  // 缺少一个 %s
}

// ✅ 正确示例
{
  "source": "Welcome %s to %s server!",
  "target": "欢迎 %s 来到 %s 服务器！"
}
```

#### 颜色代码检查
```json
// ❌ 错误示例
{
  "source": "§aGreen §rtext",
  "target": "绿色文本"  // 丢失颜色代码
}

// ✅ 正确示例
{
  "source": "§aGreen §rtext",
  "target": "§a绿色§r文本"
}
```

#### 长度比例控制
```json
// ⚠️ 警告示例
{
  "source": "OK",
  "target": "确认并继续执行此操作"  // 翻译过长
}

// ✅ 建议
{
  "source": "OK",
  "target": "确认"
}
```

### 自定义验证规则

```python
# 创建自定义验证器
from localization_kit.quality import QualityValidator

class CustomValidator(QualityValidator):
    def validate(self, key: str, source: str, target: str):
        # 自定义验证逻辑
        if "TODO" in target:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message="翻译包含 TODO 标记"
            )
        return ValidationResult(passed=True)

# 注册验证器
quality_service.register_validator(CustomValidator())
```

## Trans-Hub 同步

### 配置 Trans-Hub

1. **获取 API 密钥**
   - 访问 https://trans-hub.net
   - 登录账号后进入个人中心
   - 生成 API 密钥

2. **配置密钥**
   ```bash
   # 编辑配置文件
   cp .env.example .env
   
   # 添加配置
   TRANS_HUB_API_KEY=your_api_key_here
   TRANS_HUB_API_URL=https://api.trans-hub.net
   ```

### 上传待翻译内容

1. **批量上传**
   - 扫描完成后点击 "上传到 Trans-Hub"
   - 选择要上传的语言文件
   - 等待上传完成

2. **增量上传**
   ```python
   # 仅上传新增或修改的内容
   trans_hub_service.incremental_upload(
       project_id="minecraft_mods",
       scan_result=scan_result
   )
   ```

### 下载翻译结果

```bash
# 同步所有翻译
task sync-translations --project-id=minecraft_mods

# 同步特定语言
task sync-translations --project-id=minecraft_mods --locale=zh_CN

# 自动应用翻译
task sync-translations --project-id=minecraft_mods --auto-apply
```

### 实时协作

1. **启用实时同步**
   ```python
   # 启动 WebSocket 连接
   trans_hub_service.enable_realtime_sync(
       project_id="minecraft_mods",
       on_update=handle_translation_update
   )
   ```

2. **协作翻译**
   - 多人同时在线翻译
   - 实时看到其他人的修改
   - 自动解决冲突

## 高级功能

### 批处理脚本

```bash
# 批量处理多个整合包
#!/bin/bash
for pack in /modpacks/*; do
    task scan --path="$pack" --output="$pack/scan.json"
    task quality-check --project="$pack"
    task sync-translations --project="$pack" --auto-apply
done
```

### 自动化工作流

```yaml
# GitHub Actions 示例
name: Auto Translation
on:
  push:
    paths:
      - 'mods/**'
      - 'resourcepacks/**'

jobs:
  translate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup TH Suite
        run: |
          poetry install
          task install
      - name: Scan and Translate
        run: |
          task scan --path=.
          task sync-translations --auto-apply
      - name: Commit translations
        run: |
          git add .
          git commit -m "Auto-update translations"
          git push
```

### 自定义主题

```typescript
// 修改 Minecraft 主题颜色
// apps/mc_l10n/frontend/src/theme/minecraft/colors.ts

export const customColors = {
  ...minecraftColors,
  primary: {
    ...minecraftColors.primary,
    grass: '#00FF00',  // 更亮的绿色
    diamond: '#00FFFF', // 青色钻石
  }
};
```

### 插件开发

```python
# 创建自定义解析器
from localization_kit.parsers import FileParser

class CustomFormatParser(FileParser):
    extensions = ['.custom']
    
    def parse(self, content: str) -> Dict[str, str]:
        # 解析逻辑
        return parsed_data
    
    def serialize(self, data: Dict[str, str]) -> str:
        # 序列化逻辑
        return serialized_content

# 注册解析器
parser_registry.register(CustomFormatParser())
```

## 常见问题

### Q: 扫描时提示权限不足？
**A:** 确保对目标目录有读取权限：
```bash
# Linux/macOS
chmod -R 755 /path/to/modpack

# Windows (管理员权限运行)
icacls "C:\path\to\modpack" /grant Everyone:R
```

### Q: 如何处理大型整合包？
**A:** 使用增量扫描和缓存：
```python
# 启用缓存
scan_service = ScanService(enable_cache=True)

# 增量扫描
scan_service.incremental_scan(
    path="/large/modpack",
    cache_dir="/tmp/scan_cache"
)
```

### Q: 翻译冲突如何解决？
**A:** 系统提供三种冲突解决策略：
1. **使用本地版本**: 保留本地修改
2. **使用远程版本**: 使用 Trans-Hub 版本
3. **手动合并**: 打开合并编辑器

### Q: 如何备份翻译？
**A:** 
```bash
# 导出所有翻译
task export-translations --format=json --output=backup.json

# 导出为 Excel
task export-translations --format=xlsx --output=translations.xlsx

# 定期自动备份
crontab -e
# 添加: 0 2 * * * cd /path/to/th-suite && task backup-translations
```

### Q: 支持哪些文件格式？
**A:** 
- **语言文件**: JSON, Properties, YAML, TOML, Lang
- **压缩包**: JAR, ZIP, 7Z, RAR
- **清单文件**: manifest.json, mods.toml, fabric.mod.json

### Q: 如何提高扫描速度？
**A:** 
1. 使用 SSD 存储
2. 启用多线程扫描：
   ```python
   scan_service = ScanService(
       max_workers=8,  # CPU 核心数
       batch_size=100  # 批处理大小
   )
   ```
3. 排除不需要的文件：
   ```python
   scan_service.scan(
       path="/modpack",
       exclude_patterns=["*.log", "*.tmp", "screenshots/*"]
   )
   ```

## 获取帮助

- **文档**: https://github.com/Saken/th-suite/wiki
- **问题反馈**: https://github.com/Saken/th-suite/issues
- **社区讨论**: https://github.com/Saken/th-suite/discussions
- **Trans-Hub 官网**: https://trans-hub.net

---

最后更新: 2024-01-20
版本: 1.0.0