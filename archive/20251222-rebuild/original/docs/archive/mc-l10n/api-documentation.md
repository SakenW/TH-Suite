# MC L10n API 文档

**版本**: 1.0.0  
**基础URL**: `http://localhost:8000`  
**文档URL**: `http://localhost:8000/docs`

## 📋 概述

MC L10n 提供RESTful API接口用于管理本地数据库、扫描MOD、同步数据等功能。

## 🔑 认证

当前版本暂无认证要求，未来版本将添加API密钥认证。

## 📡 API端点

### 统计与监控

#### 获取数据库统计

```http
GET /api/database/statistics
```

**响应示例**:
```json
{
  "mods_total": 226,
  "mods_uploaded": 150,
  "language_files": 2122,
  "translation_entries": 526520,
  "pending_changes": 45,
  "cache_entries": 180
}
```

#### 获取同步状态

```http
GET /api/database/sync/status
```

**响应示例**:
```json
{
  "recent_syncs": [
    {
      "sync_type": "mods",
      "direction": "upload",
      "started_at": "2025-09-06T10:00:00",
      "completed_at": "2025-09-06T10:00:05",
      "entity_count": 50,
      "success_count": 50,
      "error_count": 0,
      "duration": 5.2
    }
  ],
  "pending": {
    "mods": 76,
    "changes": 45
  },
  "settings": {
    "auto_sync": false,
    "sync_interval": 300,
    "conflict_resolution": "client_wins"
  }
}
```

#### 获取变更摘要

```http
GET /api/database/changes/summary
```

**响应示例**:
```json
{
  "by_entity": {
    "translation": {
      "total": 100,
      "pending": 45,
      "synced": 55
    },
    "project": {
      "total": 5,
      "pending": 2,
      "synced": 3
    }
  },
  "by_operation": {
    "create": 10,
    "update": 35,
    "delete": 0
  },
  "recent_changes": [...],
  "total_pending": 47
}
```

### MOD管理

#### 获取MOD列表

```http
GET /api/database/mods?limit=100&offset=0
```

**查询参数**:
- `limit` (integer, 1-1000): 返回数量，默认100
- `offset` (integer, ≥0): 偏移量，默认0

**响应示例**:
```json
[
  {
    "mod_id": "minecraft",
    "mod_name": "Minecraft",
    "display_name": "Minecraft",
    "version": "1.20.1",
    "minecraft_version": "1.20.1",
    "mod_loader": "forge",
    "file_path": "/path/to/minecraft.jar",
    "language_count": 120,
    "total_keys": 5000
  }
]
```

#### 获取MOD详情

```http
GET /api/database/mods/{mod_id}
```

**路径参数**:
- `mod_id` (string): MOD唯一标识符

**响应示例**:
```json
{
  "mod_info": {
    "mod_id": "twilightforest",
    "mod_name": "twilightforest",
    "display_name": "The Twilight Forest",
    "version": "4.3.1893",
    "minecraft_version": "1.20.1",
    "mod_loader": "forge",
    "file_path": "/mods/twilightforest.jar",
    "language_count": 15,
    "total_keys": 1200
  },
  "language_files": [
    {
      "language_code": "en_us",
      "file_path": "assets/twilightforest/lang/en_us.json",
      "entry_count": 1200,
      "cached_at": "2025-09-06T09:00:00"
    },
    {
      "language_code": "zh_cn",
      "file_path": "assets/twilightforest/lang/zh_cn.json",
      "entry_count": 1180,
      "cached_at": "2025-09-06T09:00:00"
    }
  ],
  "metadata": {...}
}
```

#### 扫描目录或文件

```http
POST /api/database/scan
```

**请求体**:
```json
{
  "scan_path": "/path/to/mods",
  "recursive": true,
  "force_rescan": false
}
```

**响应示例**:
```json
{
  "success": true,
  "total_files": 226,
  "successful": 225,
  "failed": 1,
  "mods": [...]
}
```

### 翻译管理

#### 获取翻译条目

```http
GET /api/database/translations/{mod_id}/{language_code}?limit=100&offset=0&status=pending
```

**路径参数**:
- `mod_id` (string): MOD标识符
- `language_code` (string): 语言代码（如zh_cn）

**查询参数**:
- `limit` (integer): 返回数量
- `offset` (integer): 偏移量
- `status` (string): 状态过滤（pending/translated/reviewed）

**响应示例**:
```json
[
  {
    "entry_id": "abc123",
    "translation_key": "item.twilightforest.naga_scale",
    "original_text": "Naga Scale",
    "translated_text": "娜迦鳞片",
    "status": "translated"
  }
]
```

#### 更新翻译

```http
PUT /api/database/translations/{entry_id}
```

**路径参数**:
- `entry_id` (string): 翻译条目ID

**请求体**:
```json
{
  "translated_text": "新的翻译文本",
  "status": "translated"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "Translation updated"
}
```

### 项目管理

#### 创建项目

```http
POST /api/database/projects
```

**请求体**:
```json
{
  "project_name": "我的项目",
  "target_language": "zh_cn",
  "source_language": "en_us",
  "scan_paths": ["/path/to/mods"]
}
```

**响应示例**:
```json
{
  "success": true,
  "project_id": "uuid-here",
  "message": "Project created"
}
```

### 数据同步

#### 执行同步

```http
POST /api/database/sync
```

**请求体**:
```json
{
  "sync_type": "mods",
  "direction": "upload"
}
```

**参数说明**:
- `sync_type`: projects | mods | translations
- `direction`: upload | download | bidirectional

**响应示例**:
```json
{
  "success": true,
  "message": "Sync mods completed"
}
```

#### 获取待同步变更

```http
GET /api/database/changes/pending?entity_type=translation&limit=100
```

**查询参数**:
- `entity_type` (string): 实体类型过滤
- `limit` (integer): 返回数量

**响应示例**:
```json
[
  {
    "change_id": "change123",
    "entity_type": "translation",
    "entity_id": "entry456",
    "operation": "update",
    "change_data": {...},
    "created_at": "2025-09-06T10:00:00"
  }
]
```

### 缓存管理

#### 清理过期缓存

```http
POST /api/database/cache/cleanup
```

**响应示例**:
```json
{
  "success": true,
  "message": "Cache cleanup completed"
}
```

### 设置管理

#### 获取所有设置

```http
GET /api/database/settings
```

**响应示例**:
```json
{
  "cache_ttl": {
    "value": "86400",
    "type": "integer",
    "description": "缓存过期时间（秒）"
  },
  "auto_sync": {
    "value": "false",
    "type": "boolean",
    "description": "自动同步开关"
  }
}
```

#### 更新设置

```http
PUT /api/database/settings/{key}
```

**路径参数**:
- `key` (string): 设置键名

**请求体**: 纯文本值
```
true
```

**响应示例**:
```json
{
  "success": true,
  "message": "Setting updated"
}
```

## 📊 数据模型

### ModInfo

```typescript
interface ModInfo {
  mod_id: string;
  mod_name: string;
  display_name?: string;
  version?: string;
  minecraft_version?: string;
  mod_loader?: string;
  file_path: string;
  language_count: number;
  total_keys: number;
}
```

### TranslationEntry

```typescript
interface TranslationEntry {
  entry_id: string;
  translation_key: string;
  original_text?: string;
  translated_text?: string;
  status: "pending" | "translated" | "reviewed" | "approved";
}
```

### ScanRequest

```typescript
interface ScanRequest {
  scan_path: string;
  recursive?: boolean;
  force_rescan?: boolean;
}
```

### SyncRequest

```typescript
interface SyncRequest {
  sync_type: "projects" | "mods" | "translations";
  direction?: "upload" | "download" | "bidirectional";
}
```

## 🔴 错误处理

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误详细信息"
}
```

## 🔄 WebSocket接口

### 实时进度更新

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/progress');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress);
  console.log('Message:', data.message);
};
```

### 消息格式

```json
{
  "type": "scan_progress",
  "progress": 45,
  "current": 100,
  "total": 226,
  "message": "正在扫描: twilightforest.jar"
}
```

## 🚀 使用示例

### JavaScript/TypeScript

```typescript
// 获取MOD列表
const response = await fetch('http://localhost:8000/api/database/mods');
const mods = await response.json();

// 更新翻译
await fetch(`http://localhost:8000/api/database/translations/${entryId}`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    translated_text: '新翻译',
    status: 'translated'
  })
});

// 执行扫描
await fetch('http://localhost:8000/api/database/scan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    scan_path: '/path/to/mods',
    recursive: true
  })
});
```

### Python

```python
import requests

# 获取统计信息
response = requests.get('http://localhost:8000/api/database/statistics')
stats = response.json()

# 同步数据
response = requests.post(
    'http://localhost:8000/api/database/sync',
    json={
        'sync_type': 'mods',
        'direction': 'upload'
    }
)

# 获取变更摘要
response = requests.get('http://localhost:8000/api/database/changes/summary')
summary = response.json()
```

### cURL

```bash
# 获取MOD列表
curl http://localhost:8000/api/database/mods?limit=10

# 更新设置
curl -X PUT http://localhost:8000/api/database/settings/auto_sync \
  -H "Content-Type: text/plain" \
  -d "true"

# 清理缓存
curl -X POST http://localhost:8000/api/database/cache/cleanup
```

## 📈 性能建议

1. **分页查询**: 对于大量数据，始终使用limit和offset参数
2. **缓存利用**: 充分利用缓存机制，避免重复扫描
3. **批量操作**: 尽可能批量更新而非单个操作
4. **异步处理**: 长时间操作使用WebSocket获取进度

## 🔒 安全考虑

1. **输入验证**: 所有输入都经过Pydantic模型验证
2. **SQL注入防护**: 使用参数化查询
3. **路径遍历防护**: 验证所有文件路径
4. **速率限制**: 未来版本将添加API速率限制

## 📚 相关文档

- [数据库架构文档](./database-architecture-v4.md)
- [数据库实现文档](./database-implementation-v5.md)
- [WebSocket协议](./websocket-protocol.md)