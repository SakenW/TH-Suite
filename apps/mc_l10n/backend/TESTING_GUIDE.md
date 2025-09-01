# MC L10n 扫描功能测试指南

本指南介绍如何测试 MC L10n 的扫描功能，包括创建测试数据、运行扫描测试和使用 API。

## 快速开始

### 1. 启动后端服务

在项目根目录运行：

```bash
# 使用 Poetry（推荐）
cd TH-Suite
poetry run python apps/mc-l10n/backend/main.py

# 或直接使用 Python
cd apps/mc-l10n/backend
python main.py
```

服务将在 `http://localhost:8000` 启动

### 2. 访问 API 文档

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. 运行测试脚本

```bash
# 在项目根目录
poetry run python apps/mc-l10n/backend/simple_test.py
```

## API 测试

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 扫描服务健康检查
curl http://localhost:8000/api/scan/health
```

### 创建测试 MOD 文件

可以使用以下 PowerShell 脚本创建测试 MOD：

```powershell
# create_test_mod.ps1
$modPath = "test_fabric_mod.jar"

# 创建临时目录
$tempDir = New-TemporaryFile | %{ rm $_; mkdir $_ }

# 创建 fabric.mod.json
$modInfo = @{
    id = "test_fabric_mod"
    name = "测试 Fabric 模组"
    version = "1.0.0"
    description = "用于测试的 Fabric 模组"
    authors = @("测试作者")
}

$modInfo | ConvertTo-Json -Depth 3 | Out-File "$tempDir/fabric.mod.json" -Encoding UTF8

# 创建语言文件目录
New-Item -ItemType Directory -Path "$tempDir/assets/test_fabric_mod/lang" -Force

# 创建英文语言文件
$enLang = @{
    "item.test_fabric_mod.sword" = "Magic Sword"
    "item.test_fabric_mod.pickaxe" = "Magic Pickaxe"
    "block.test_fabric_mod.ore" = "Magic Ore"
    "itemGroup.test_fabric_mod.items" = "Test Items"
}

$enLang | ConvertTo-Json | Out-File "$tempDir/assets/test_fabric_mod/lang/en_us.json" -Encoding UTF8

# 创建中文语言文件
$zhLang = @{
    "item.test_fabric_mod.sword" = "魔法剑"
    "item.test_fabric_mod.pickaxe" = "魔法镐"
    "block.test_fabric_mod.ore" = "魔法矿石"
    "itemGroup.test_fabric_mod.items" = "测试物品"
}

$zhLang | ConvertTo-Json | Out-File "$tempDir/assets/test_fabric_mod/lang/zh_cn.json" -Encoding UTF8

# 压缩为 JAR 文件
Compress-Archive -Path "$tempDir/*" -DestinationPath $modPath -Force

# 清理临时目录
Remove-Item -Recurse $tempDir

Write-Host "测试 MOD 文件已创建: $modPath"
```

### API 测试命令

#### 1. 扫描单个 MOD 文件

```bash
curl -X POST http://localhost:8000/api/scan/mod \
     -H "Content-Type: application/json" \
     -d '{"path": "C:/path/to/your/test_fabric_mod.jar"}'
```

#### 2. 快速扫描项目

```bash
curl -X POST http://localhost:8000/api/scan/project/quick \
     -H "Content-Type: application/json" \
     -d '{"path": "C:/path/to/your/modpack"}'
```

#### 3. 启动异步扫描

```bash
curl -X POST http://localhost:8000/api/scan/project/start \
     -H "Content-Type: application/json" \
     -d '{"path": "C:/path/to/your/modpack"}'
```

响应示例：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "扫描任务已启动"
}
```

#### 4. 查询扫描进度

```bash
curl http://localhost:8000/api/scan/progress/550e8400-e29b-41d4-a716-446655440000
```

## 测试用例

### 支持的 MOD 类型

1. **Fabric MOD**
   - 包含 `fabric.mod.json`
   - JSON 格式语言文件

2. **Forge MOD**
   - 包含 `mcmod.info` 或 `META-INF/mods.toml`
   - `.lang` 格式语言文件

3. **Quilt MOD**
   - 包含 `quilt.mod.json`
   - JSON 格式语言文件

4. **NeoForge MOD**
   - 包含 `META-INF/neoforge.mods.toml`

### 支持的整合包类型

1. **CurseForge 整合包**
   - 包含 `manifest.json`
   - `mods/` 目录

2. **MultiMC 实例**
   - 包含 `instance.cfg`
   - `minecraft/mods/` 目录

3. **自定义整合包**
   - 包含 MOD 文件的目录结构

### 语言文件格式

1. **JSON 格式** (`.json`)
```json
{
  "item.modid.sword": "Magic Sword",
  "block.modid.ore": "Magic Ore"
}
```

2. **Lang 格式** (`.lang`)
```
item.modid.sword.name=Magic Sword
block.modid.ore.name=Magic Ore
```

## 预期响应

### 成功扫描 MOD 响应

```json
{
  "mod_id": "test_fabric_mod",
  "name": "测试 Fabric 模组",
  "version": "1.0.0",
  "description": "用于测试的 Fabric 模组",
  "authors": ["测试作者"],
  "file_path": "C:/path/to/test_fabric_mod.jar",
  "file_size": 1024,
  "loader_type": "fabric"
}
```

### 成功扫描项目响应

```json
{
  "success": true,
  "project_info": {
    "name": "测试整合包",
    "path": "C:/path/to/modpack",
    "project_type": "modpack",
    "loader_type": "fabric",
    "total_mods": 5,
    "estimated_segments": 150,
    "supported_locales": ["en_us", "zh_cn"],
    "fingerprint": "abc123def456"
  },
  "errors": []
}
```

### 扫描进度响应

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "progress": 0.65,
  "current_step": "扫描MOD文件",
  "error_message": null
}
```

## 常见问题

### 1. 路径问题
- Windows 路径使用正斜杠 `/` 或双反斜杠 `\\\\`
- 确保路径指向实际存在的文件或目录

### 2. 编码问题
- MOD 中的语言文件应使用 UTF-8 编码
- 中文内容需要正确的编码处理

### 3. 文件格式问题
- MOD 文件必须是有效的 ZIP/JAR 格式
- 元数据文件格式必须正确

### 4. 权限问题
- 确保应用有读取目标文件/目录的权限

## 性能测试

### 大型整合包测试

可以使用包含 100+ MOD 的整合包测试性能：

```bash
curl -X POST http://localhost:8000/api/scan/project/start \
     -H "Content-Type: application/json" \
     -d '{"path": "C:/path/to/large/modpack"}'
```

监控以下指标：
- 扫描时间
- 内存使用
- CPU 使用
- 扫描准确性

### 并发测试

可以同时启动多个扫描任务测试并发处理：

```bash
# 启动多个并发扫描
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/scan/project/start \
       -H "Content-Type: application/json" \
       -d "{\"path\": \"C:/path/to/modpack$i\"}" &
done
```

## 调试

### 启用详细日志

修改 `main.py` 中的日志级别：

```python
uvicorn.run(
    "main:app",
    host="127.0.0.1",
    port=8000,
    reload=True,
    log_level="debug"  # 改为 debug
)
```

### 查看扫描详情

在测试脚本中添加更详细的输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 总结

这个测试指南涵盖了 MC L10n 扫描功能的完整测试流程。通过这些测试，你可以验证：

- MOD 文件的正确识别和解析
- 语言文件的提取和分析
- 项目类型的准确检测
- API 端点的正常工作
- 异步任务的状态管理
- 错误处理的完整性

如果遇到问题，请检查控制台输出和日志，大多数问题都会有详细的错误信息。