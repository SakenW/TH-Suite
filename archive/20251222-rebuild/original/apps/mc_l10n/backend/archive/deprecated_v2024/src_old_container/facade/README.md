# MC L10n 门面层

门面层提供简化的统一接口，隐藏内部复杂性，方便外部系统集成。

## 🏗️ 架构概览

```
门面层 (Facade Layer)
├── 服务门面 (Service Facade)
│   ├── MCL10nFacade - 统一业务门面
│   └── 业务操作封装 - 一个方法完成复杂流程
│
├── API路由 (API Routes) 
│   ├── facade_routes.py - REST API接口
│   └── 标准化响应格式
│
└── 客户端SDK (Client SDK)
    ├── MCL10nClient - 同步客户端
    ├── AsyncMCL10nClient - 异步客户端
    └── 类型安全的Python接口
```

## 📚 核心组件

### 1. MCL10nFacade - 服务门面

**位置**: `mc_l10n_facade.py`

提供简化的业务接口：
- **扫描相关**: `scan_mods()`, `quick_scan()`
- **翻译相关**: `translate_mod()`, `batch_translate()`
- **项目管理**: `create_project()`, `get_project_status()`
- **同步操作**: `sync_with_server()`
- **质量管理**: `check_quality()`

**特点**:
- 🔄 自动事务管理
- 🛡️ 统一错误处理
- 📊 简化的结果对象
- ⚙️ 合理的默认配置

### 2. 门面API路由

**位置**: `facade_routes.py`

提供RESTful API接口：
- `POST /api/v2/scan` - 扫描MOD目录
- `POST /api/v2/translate` - 翻译MOD
- `POST /api/v2/projects` - 创建翻译项目
- `POST /api/v2/sync` - 同步到服务器
- `GET /api/v2/quality/{mod_id}` - 检查质量

**响应格式**:
```json
{
  "success": true,
  "data": {
    // 实际数据
  },
  "errors": [] // 可选的错误信息
}
```

### 3. 客户端SDK

**位置**: `client_sdk.py`

提供类型安全的Python客户端：

#### 同步客户端
```python
from mc_l10n.facade import create_client

with create_client("http://localhost:18000") as client:
    result = client.scan_mods("/path/to/mods")
    if result.success:
        print(f"找到 {result.mods_found} 个模组")
```

#### 异步客户端
```python
from mc_l10n.facade import create_async_client

async with create_async_client() as client:
    result = await client.scan_mods("/path/to/mods")
    print(f"扫描结果: {result}")
```

## 🚀 快速开始

### 1. 启动服务

```bash
# 在项目根目录运行
cd apps/mc_l10n/backend
poetry run python main.py
```

### 2. 使用REST API

```bash
# 快速扫描
curl -X GET "http://localhost:18000/api/v2/scan/quick?path=/path/to/mods"

# 完整扫描
curl -X POST "http://localhost:18000/api/v2/scan" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/mods", "recursive": true}'
```

### 3. 使用Python SDK

```python
from mc_l10n.facade import create_client

# 基础使用
with create_client() as client:
    # 检查系统状态
    if client.is_server_available():
        print("✅ 服务器可用")
    
    # 扫描模组
    result = client.scan_mods("/path/to/mods")
    print(f"扫描结果: {result}")
    
    # 翻译模组
    translations = {
        "item.sword": "剑",
        "block.stone": "石头"
    }
    
    translate_result = client.translate_mod(
        mod_id="example_mod",
        language="zh_cn", 
        translations=translations
    )
    print(f"翻译成功: {translate_result.translated_count}")
```

## 📖 详细用法

### 扫描操作

#### 快速扫描（仅统计）
```python
stats = client.quick_scan("/path/to/mods")
print(f"发现 {stats['total_mods']} 个模组")
print(f"支持语言: {stats['languages']}")
```

#### 完整扫描（保存到数据库）
```python
result = client.scan_mods(
    path="/path/to/mods",
    recursive=True,        # 递归扫描子目录
    auto_extract=True,     # 自动提取JAR文件
)

if result.success:
    print(f"✅ 扫描成功:")
    print(f"   处理文件: {result.total_files}")
    print(f"   发现模组: {result.mods_found}")
    print(f"   翻译条目: {result.translations_found}")
else:
    print(f"❌ 扫描失败: {result.errors}")
```

### 翻译操作

#### 单个模组翻译
```python
translations = {
    "gui.inventory": "物品栏",
    "item.diamond_sword": "钻石剑",
    "block.oak_wood": "橡木"
}

result = client.translate_mod(
    mod_id="minecraft",
    language="zh_cn",
    translations=translations,
    translator="user123",
    auto_approve=False,    # 需要手动审核
)

print(f"翻译结果:")
print(f"  成功: {result.translated_count}")
print(f"  失败: {result.failed_count}")
print(f"  进度: {result.progress}%")
```

#### 批量翻译
```python
mod_ids = ["mod1", "mod2", "mod3"]
results = client.batch_translate(
    mod_ids=mod_ids,
    language="zh_cn",
    quality_threshold=0.8,
)

for result in results:
    print(f"{result.mod_id}: {result.progress}% 完成")
```

### 项目管理

#### 创建翻译项目
```python
project_id = client.create_project(
    name="我的翻译项目",
    mod_ids=["mod1", "mod2"],
    target_languages=["zh_cn", "ja_jp"],
    auto_assign=True,      # 自动分配任务
)

print(f"项目创建成功: {project_id}")
```

#### 查看项目状态
```python
project = client.get_project(project_id)
print(f"项目: {project.name}")
print(f"状态: {project.status}")
print(f"进度: {project.progress}")
```

### 质量管理

#### 检查翻译质量
```python
report = client.check_quality("minecraft", "zh_cn")
print(f"质量报告:")
print(f"  总计: {report.total_translations}")
print(f"  通过: {report.approved}")
print(f"  拒绝: {report.rejected}")
print(f"  通过率: {report.approval_rate}%")
print(f"  平均质量: {report.average_quality}")
```

### 错误处理

```python
from mc_l10n.facade import MCL10nConnectionError, MCL10nAPIError

try:
    result = client.scan_mods("/invalid/path")
except MCL10nConnectionError as e:
    print(f"连接失败: {e}")
except MCL10nAPIError as e:
    print(f"API错误 {e.status_code}: {e}")
    if e.response_data:
        print(f"详细信息: {e.response_data}")
```

## 🔧 配置选项

### 客户端配置
```python
client = create_client(
    base_url="http://localhost:18000",  # 服务器地址
    timeout=30.0,                       # 请求超时(秒)
    api_key="your_api_key",            # API密钥(可选)
)
```

### 门面配置
门面服务通过依赖注入容器获取配置，支持：
- 默认目标语言
- 冲突解决策略
- 质量阈值
- 缓存设置

## 🎯 最佳实践

### 1. 使用上下文管理器
```python
# ✅ 推荐 - 自动关闭连接
with create_client() as client:
    result = client.scan_mods("/path")

# ❌ 不推荐 - 需要手动关闭
client = create_client()
result = client.scan_mods("/path")
client.close()  # 容易忘记
```

### 2. 异常处理
```python
# ✅ 推荐 - 具体异常处理
try:
    result = client.translate_mod(...)
except MCL10nConnectionError:
    # 处理连接问题
    pass
except MCL10nAPIError as e:
    if e.status_code == 404:
        # 处理资源不存在
        pass
    else:
        # 处理其他API错误
        pass

# ❌ 不推荐 - 捕获所有异常
try:
    result = client.translate_mod(...)
except Exception as e:
    print(f"出错了: {e}")
```

### 3. 批量操作优化
```python
# ✅ 推荐 - 使用批量接口
results = client.batch_translate(
    mod_ids=["mod1", "mod2", "mod3"],
    language="zh_cn"
)

# ❌ 不推荐 - 循环调用单个接口
results = []
for mod_id in ["mod1", "mod2", "mod3"]:
    result = client.translate_mod(mod_id, "zh_cn", {})
    results.append(result)
```

### 4. 异步并发
```python
# ✅ 推荐 - 异步并发处理
async with create_async_client() as client:
    tasks = [
        client.scan_mods(path) 
        for path in paths
    ]
    results = await asyncio.gather(*tasks)
```

## 📝 示例代码

完整的使用示例请查看 `sdk_examples.py` 文件，包含：

- 🔍 **基础操作示例** - 连接、状态检查
- 📂 **扫描示例** - 快速扫描、完整扫描
- 🌍 **翻译示例** - 单个翻译、批量翻译
- 📋 **项目示例** - 项目创建、状态查询
- ⚡ **异步示例** - 并发操作
- 🚨 **错误处理示例** - 异常捕获
- 🔄 **完整工作流** - 端到端流程

运行示例：
```bash
cd apps/mc_l10n/backend/src/facade
python sdk_examples.py
```

## 🤝 集成指南

### 与前端集成
门面API提供标准REST接口，可直接用于前端调用：

```typescript
// TypeScript 示例
const response = await fetch('/api/v2/scan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    path: '/path/to/mods',
    recursive: true
  })
});

const result = await response.json();
if (result.success) {
  console.log(`Found ${result.data.mods_found} mods`);
}
```

### 与其他Python应用集成
直接使用SDK：

```python
# 在其他Python项目中
from mc_l10n.facade import create_client

def my_translation_workflow():
    with create_client() as mc_client:
        # 扫描
        scan_result = mc_client.scan_mods("/my/mods")
        
        # 翻译
        if scan_result.success:
            # ... 翻译逻辑
            pass
```

### 与命令行工具集成
```bash
# 通过curl调用API
curl -X POST "http://localhost:18000/api/v2/scan" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/mods"}'
```

## 🐛 故障排除

### 常见问题

1. **连接失败**
   ```python
   MCL10nConnectionError: Connection failed
   ```
   - 检查服务器是否启动
   - 验证URL和端口
   - 检查网络连接

2. **API错误**
   ```python
   MCL10nAPIError: API error: 404
   ```
   - 检查资源是否存在
   - 验证请求参数
   - 查看服务器日志

3. **超时错误**
   - 增加timeout参数
   - 检查操作复杂度
   - 考虑使用异步客户端

### 调试建议

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查服务器状态**
   ```python
   if not client.is_server_available():
       print("服务器不可用")
   ```

3. **查看错误详情**
   ```python
   try:
       result = client.scan_mods("/path")
   except MCL10nAPIError as e:
       print(f"错误详情: {e.response_data}")
   ```

## 📈 性能优化

1. **使用批量接口** - 避免大量单独请求
2. **异步并发** - 对于独立操作使用异步客户端
3. **合理超时** - 根据操作复杂度调整超时时间
4. **连接复用** - 在同一会话中复用客户端实例

## 🔮 未来计划

- [ ] GraphQL API支持
- [ ] WebSocket实时通信
- [ ] JavaScript/TypeScript SDK
- [ ] Go语言SDK
- [ ] 更多语言支持