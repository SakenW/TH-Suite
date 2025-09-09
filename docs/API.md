# TH-Suite API 文档

本文档描述了 TH-Suite 的 REST API 接口，提供完整的端点说明、请求/响应格式和使用示例。

## 📋 API 概览

### 基础信息

| 属性 | 值 |
|------|---|
| **协议** | HTTP/1.1, WebSocket |
| **格式** | JSON |
| **认证** | API Key (可选) |
| **编码** | UTF-8 |
| **CORS** | 已启用 |

### 服务端点

| 服务 | 基础URL | 文档 |
|------|---------|------|
| **MC L10n** | `http://localhost:18000` | `/docs` |
| **RW Studio** | `http://localhost:8002` | `/docs` |

### API 版本

| 版本 | 路径前缀 | 状态 | 说明 |
|------|----------|------|------|
| **v1** | `/api/v1` | 已弃用 | 传统API |
| **v2** | `/api/v2` | 当前版本 | 门面API |
| **v3** | `/api/v3` | 计划中 | 微服务API |

## 🔒 认证授权

### API Key 认证（可选）

```http
GET /api/v2/scan/health
X-API-Key: your-api-key-here
Content-Type: application/json
```

### 获取 API Key

```http
POST /api/auth/keys
Content-Type: application/json

{
  "name": "my-app-key",
  "permissions": ["scan", "translate"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**响应:**
```json
{
  "key": "thsuite_1234567890abcdef",
  "name": "my-app-key",
  "permissions": ["scan", "translate"],
  "created_at": "2024-09-09T12:00:00Z",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

## 🔍 扫描 API

### 启动扫描任务

扫描指定路径的 MOD 或整合包，返回任务ID用于跟踪进度。

```http
POST /api/v2/scan/start
Content-Type: application/json

{
  "path": "/path/to/mod.jar",
  "recursive": true,
  "extract_archives": true,
  "file_patterns": ["*.jar", "*.zip"],
  "exclude_patterns": ["*.class", "*.png"]
}
```

**参数说明:**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `path` | string | ✓ | - | 扫描路径 |
| `recursive` | boolean | ✗ | true | 递归扫描子目录 |
| `extract_archives` | boolean | ✗ | true | 提取压缩文件 |
| `file_patterns` | array | ✗ | ["*.jar", "*.zip"] | 文件匹配模式 |
| `exclude_patterns` | array | ✗ | [] | 排除文件模式 |

**响应 (200 OK):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "扫描任务已启动",
  "estimated_duration": 30,
  "created_at": "2024-09-09T12:00:00Z"
}
```

**错误响应:**
```json
// 400 Bad Request
{
  "error": "INVALID_PATH",
  "message": "指定的路径不存在",
  "details": {
    "path": "/invalid/path"
  }
}

// 429 Too Many Requests  
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "扫描请求过于频繁，请稍后重试",
  "retry_after": 60
}
```

### 获取扫描进度

实时获取扫描任务的执行进度。

```http
GET /api/v2/scan/progress/{task_id}
```

**路径参数:**
- `task_id` (string): 扫描任务ID

**响应 (200 OK):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "progress": 0.65,
  "current_step": "正在解析 fabric.mod.json",
  "steps_completed": 13,
  "total_steps": 20,
  "files_processed": 45,
  "total_files": 67,
  "errors": [],
  "warnings": [
    "MOD xyz.jar 缺少语言文件"
  ],
  "started_at": "2024-09-09T12:00:00Z",
  "estimated_completion": "2024-09-09T12:02:30Z"
}
```

**状态值:**
- `pending`: 等待开始
- `in_progress`: 执行中
- `completed`: 已完成
- `failed`: 执行失败
- `cancelled`: 已取消

### 获取扫描结果

获取已完成扫描任务的详细结果。

```http
GET /api/v2/scan/result/{task_id}
```

**响应 (200 OK):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "summary": {
    "total_files": 67,
    "mods_found": 12,
    "resource_packs_found": 2,
    "languages_detected": ["en_us", "zh_cn", "ja_jp"],
    "translation_keys": 1543,
    "completion_rate": 0.78
  },
  "mods": [
    {
      "mod_id": "example_mod",
      "name": "Example Mod",
      "version": "1.0.0",
      "loader_type": "fabric",
      "file_path": "/mods/example_mod.jar",
      "file_size": 2048576,
      "language_files": [
        {
          "locale": "en_us",
          "file_path": "assets/example_mod/lang/en_us.json",
          "segment_count": 156,
          "file_size": 8192
        }
      ],
      "metadata": {
        "description": "An example mod",
        "authors": ["ModAuthor"],
        "dependencies": ["minecraft", "fabric-api"]
      }
    }
  ],
  "errors": [],
  "warnings": [
    "部分文件编码检测失败，使用默认编码"
  ],
  "performance": {
    "total_duration": 45.2,
    "parsing_duration": 32.1,
    "file_io_duration": 13.1
  }
}
```

### 取消扫描任务

取消正在执行的扫描任务。

```http
DELETE /api/v2/scan/task/{task_id}
```

**响应 (200 OK):**
```json
{
  "message": "扫描任务已取消",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## 📂 项目管理 API

### 创建翻译项目

基于扫描结果创建新的翻译项目。

```http
POST /api/v2/projects
Content-Type: application/json

{
  "name": "我的整合包翻译项目",
  "description": "翻译整合包到简体中文",
  "scan_result_id": "550e8400-e29b-41d4-a716-446655440000",
  "target_languages": ["zh_cn", "ja_jp"],
  "settings": {
    "auto_detect_duplicates": true,
    "merge_similar_keys": true,
    "quality_threshold": 0.8
  }
}
```

**响应 (201 Created):**
```json
{
  "project_id": "proj_1234567890abcdef",
  "name": "我的整合包翻译项目",
  "status": "active",
  "progress": {
    "total_keys": 1543,
    "translated_keys": 0,
    "completion_rate": 0.0
  },
  "created_at": "2024-09-09T12:00:00Z",
  "updated_at": "2024-09-09T12:00:00Z"
}
```

### 获取项目列表

获取用户的所有翻译项目。

```http
GET /api/v2/projects?status=active&limit=20&offset=0
```

**查询参数:**
- `status` (string): 筛选状态 (active, completed, archived)
- `limit` (integer): 返回数量限制 (1-100)
- `offset` (integer): 分页偏移量

**响应 (200 OK):**
```json
{
  "projects": [
    {
      "project_id": "proj_1234567890abcdef",
      "name": "我的整合包翻译项目",
      "status": "active",
      "progress": {
        "completion_rate": 0.45,
        "total_keys": 1543,
        "translated_keys": 694
      },
      "target_languages": ["zh_cn", "ja_jp"],
      "created_at": "2024-09-09T12:00:00Z",
      "updated_at": "2024-09-09T12:15:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_next": false
  }
}
```

### 获取项目详情

获取特定项目的详细信息。

```http
GET /api/v2/projects/{project_id}
```

**响应 (200 OK):**
```json
{
  "project_id": "proj_1234567890abcdef",
  "name": "我的整合包翻译项目",
  "description": "翻译整合包到简体中文",
  "status": "active",
  "progress": {
    "total_keys": 1543,
    "translated_keys": 694,
    "approved_keys": 612,
    "completion_rate": 0.45,
    "approval_rate": 0.88
  },
  "target_languages": ["zh_cn", "ja_jp"],
  "mods": [
    {
      "mod_id": "example_mod",
      "name": "Example Mod",
      "progress": {
        "zh_cn": 0.67,
        "ja_jp": 0.23
      }
    }
  ],
  "settings": {
    "auto_detect_duplicates": true,
    "merge_similar_keys": true,
    "quality_threshold": 0.8
  },
  "statistics": {
    "avg_translation_length": 45.2,
    "most_common_keys": [
      "item.*.name",
      "block.*.tooltip"
    ]
  },
  "created_at": "2024-09-09T12:00:00Z",
  "updated_at": "2024-09-09T12:15:00Z"
}
```

## 🔤 翻译 API

### 获取翻译条目

获取项目中的翻译条目，支持筛选和分页。

```http
GET /api/v2/projects/{project_id}/translations?mod_id=example_mod&language=zh_cn&status=untranslated&limit=50
```

**查询参数:**
- `mod_id` (string): 筛选特定MOD
- `language` (string): 筛选语言
- `status` (string): 翻译状态 (untranslated, translated, approved)
- `search` (string): 搜索关键字
- `limit` (integer): 返回数量 (1-100)
- `offset` (integer): 分页偏移量

**响应 (200 OK):**
```json
{
  "translations": [
    {
      "translation_id": "trans_abcdef123456",
      "mod_id": "example_mod",
      "key": "item.example.sword",
      "source_text": "Example Sword",
      "target_text": "示例之剑",
      "language": "zh_cn",
      "status": "translated",
      "quality_score": 0.92,
      "context": {
        "file_path": "assets/example_mod/lang/en_us.json",
        "category": "item",
        "length": 12
      },
      "metadata": {
        "translator": "user123",
        "translated_at": "2024-09-09T12:10:00Z",
        "approved_by": "reviewer456",
        "approved_at": "2024-09-09T12:12:00Z"
      }
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 50,
    "offset": 0,
    "has_next": true
  }
}
```

### 更新翻译

更新或创建翻译条目。

```http
PUT /api/v2/projects/{project_id}/translations/{translation_id}
Content-Type: application/json

{
  "target_text": "示例之剑",
  "quality_score": 0.95,
  "reviewer_notes": "翻译准确，符合游戏语境"
}
```

**响应 (200 OK):**
```json
{
  "translation_id": "trans_abcdef123456",
  "status": "translated",
  "target_text": "示例之剑",
  "quality_score": 0.95,
  "updated_at": "2024-09-09T12:15:00Z"
}
```

### 批量翻译

批量提交多个翻译条目。

```http
POST /api/v2/projects/{project_id}/translations/batch
Content-Type: application/json

{
  "translations": [
    {
      "key": "item.example.sword",
      "target_text": "示例之剑",
      "language": "zh_cn"
    },
    {
      "key": "item.example.shield",
      "target_text": "示例盾牌",
      "language": "zh_cn"
    }
  ],
  "options": {
    "auto_approve": false,
    "skip_validation": false
  }
}
```

**响应 (200 OK):**
```json
{
  "processed": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "key": "item.example.sword",
      "status": "success",
      "translation_id": "trans_abcdef123456"
    },
    {
      "key": "item.example.shield", 
      "status": "success",
      "translation_id": "trans_abcdef123457"
    }
  ]
}
```

## 🔄 同步 API

### 与 Trans-Hub 同步

将本地翻译数据同步到 Trans-Hub 平台。

```http
POST /api/v2/sync/trans-hub
Content-Type: application/json

{
  "project_id": "proj_1234567890abcdef",
  "sync_mode": "incremental",
  "conflict_resolution": "merge",
  "languages": ["zh_cn"],
  "options": {
    "include_approved_only": true,
    "exclude_low_quality": true,
    "quality_threshold": 0.8
  }
}
```

**参数说明:**
- `sync_mode`: 同步模式 (full, incremental)
- `conflict_resolution`: 冲突解决策略 (overwrite, merge, skip)

**响应 (200 OK):**
```json
{
  "sync_id": "sync_1234567890abcdef",
  "status": "completed",
  "summary": {
    "uploaded": 145,
    "updated": 23,
    "skipped": 12,
    "conflicts": 3
  },
  "conflicts": [
    {
      "key": "item.example.sword",
      "local_text": "示例之剑",
      "remote_text": "样例之剑",
      "resolution": "kept_local"
    }
  ],
  "completed_at": "2024-09-09T12:20:00Z"
}
```

### 获取同步历史

获取项目的同步历史记录。

```http
GET /api/v2/projects/{project_id}/sync-history?limit=10
```

**响应 (200 OK):**
```json
{
  "sync_records": [
    {
      "sync_id": "sync_1234567890abcdef",
      "sync_type": "trans_hub",
      "status": "completed",
      "summary": {
        "uploaded": 145,
        "updated": 23,
        "errors": 0
      },
      "started_at": "2024-09-09T12:18:00Z",
      "completed_at": "2024-09-09T12:20:00Z"
    }
  ]
}
```

## 📊 统计 API

### 获取项目统计

获取项目的详细统计信息。

```http
GET /api/v2/projects/{project_id}/statistics?period=30d
```

**查询参数:**
- `period`: 统计周期 (7d, 30d, 90d, 1y)

**响应 (200 OK):**
```json
{
  "project_id": "proj_1234567890abcdef",
  "period": "30d",
  "overview": {
    "total_keys": 1543,
    "translated_keys": 694,
    "approved_keys": 612,
    "completion_rate": 0.45,
    "approval_rate": 0.88
  },
  "languages": {
    "zh_cn": {
      "completion_rate": 0.67,
      "approval_rate": 0.91,
      "quality_score": 0.89
    },
    "ja_jp": {
      "completion_rate": 0.23,
      "approval_rate": 0.85,
      "quality_score": 0.86
    }
  },
  "trends": {
    "daily_translations": [
      { "date": "2024-09-01", "count": 45 },
      { "date": "2024-09-02", "count": 67 }
    ],
    "quality_trend": [
      { "date": "2024-09-01", "score": 0.85 },
      { "date": "2024-09-02", "score": 0.87 }
    ]
  },
  "top_contributors": [
    {
      "user": "translator1",
      "translations": 234,
      "quality_score": 0.92
    }
  ]
}
```

## 🔍 质量检查 API

### 运行质量检查

对翻译内容执行质量检查。

```http
POST /api/v2/projects/{project_id}/quality-check
Content-Type: application/json

{
  "scope": {
    "languages": ["zh_cn"],
    "mod_ids": ["example_mod"],
    "include_approved": false
  },
  "validators": [
    "placeholder_consistency",
    "length_ratio",
    "terminology",
    "format_tags"
  ],
  "options": {
    "auto_fix": true,
    "report_warnings": true
  }
}
```

**响应 (200 OK):**
```json
{
  "check_id": "qc_1234567890abcdef",
  "status": "completed",
  "summary": {
    "total_checked": 694,
    "passed": 645,
    "warnings": 23,
    "errors": 26,
    "auto_fixed": 12
  },
  "issues": [
    {
      "translation_id": "trans_abcdef123456",
      "key": "item.example.sword",
      "issue_type": "placeholder_mismatch",
      "severity": "error",
      "message": "占位符不匹配: 原文有 %s，译文缺失",
      "suggestion": "请在译文中包含 %s 占位符"
    }
  ],
  "report_url": "/api/v2/quality-reports/qc_1234567890abcdef",
  "completed_at": "2024-09-09T12:25:00Z"
}
```

## 📁 文件导出 API

### 导出翻译文件

导出项目的翻译文件为各种格式。

```http
POST /api/v2/projects/{project_id}/export
Content-Type: application/json

{
  "format": "minecraft_resourcepack",
  "languages": ["zh_cn", "ja_jp"],
  "options": {
    "include_untranslated": false,
    "fallback_language": "en_us",
    "file_structure": "vanilla",
    "compress": true
  },
  "filters": {
    "mod_ids": ["example_mod"],
    "min_quality_score": 0.8,
    "approved_only": true
  }
}
```

**格式选项:**
- `minecraft_resourcepack`: Minecraft 资源包格式
- `json`: JSON 文件格式
- `csv`: CSV 表格格式
- `xliff`: XLIFF 翻译交换格式

**响应 (200 OK):**
```json
{
  "export_id": "exp_1234567890abcdef",
  "status": "completed",
  "download_url": "/api/v2/exports/exp_1234567890abcdef/download",
  "file_info": {
    "filename": "example_mod_translations.zip",
    "size": 2048576,
    "format": "minecraft_resourcepack"
  },
  "summary": {
    "files_created": 12,
    "translations_exported": 456,
    "languages": ["zh_cn", "ja_jp"]
  },
  "expires_at": "2024-09-16T12:30:00Z",
  "created_at": "2024-09-09T12:30:00Z"
}
```

### 下载导出文件

下载已生成的导出文件。

```http
GET /api/v2/exports/{export_id}/download
```

**响应:** 二进制文件流

## 🌐 WebSocket API

### 实时进度订阅

通过 WebSocket 接收实时进度更新。

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://localhost:18000/api/v2/ws/progress');

// 订阅扫描进度
ws.send(JSON.stringify({
  type: 'subscribe',
  topic: 'scan_progress',
  task_id: '550e8400-e29b-41d4-a716-446655440000'
}));

// 接收进度更新
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'progress_update') {
    console.log('进度更新:', data.payload);
  }
};
```

**消息格式:**
```json
{
  "type": "progress_update",
  "topic": "scan_progress",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "progress": 0.75,
    "current_step": "正在处理语言文件",
    "files_processed": 45,
    "total_files": 60
  },
  "timestamp": "2024-09-09T12:35:00Z"
}
```

## 🚨 错误处理

### 标准错误格式

所有 API 错误都遵循统一格式：

```json
{
  "error": "ERROR_CODE",
  "message": "人类可读的错误描述",
  "details": {
    "field": "field_name",
    "value": "invalid_value",
    "constraint": "validation_rule"
  },
  "timestamp": "2024-09-09T12:00:00Z",
  "request_id": "req_1234567890abcdef"
}
```

### 常见错误码

| 错误码 | HTTP状态码 | 说明 |
|-------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求格式错误 |
| `VALIDATION_ERROR` | 422 | 数据验证失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率过高 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 📚 SDK 和客户端库

### Python 客户端

```python
from th_suite_client import MCL10nClient

# 创建客户端
client = MCL10nClient(
    base_url="http://localhost:18000",
    api_key="your-api-key"
)

# 启动扫描
scan_result = client.start_scan("/path/to/mod.jar")
task_id = scan_result.task_id

# 监控进度
for progress in client.watch_progress(task_id):
    print(f"进度: {progress.progress:.1%}")
    if progress.status == "completed":
        break

# 获取结果
result = client.get_scan_result(task_id)
print(f"发现 {result.summary.mods_found} 个MOD")
```

### JavaScript 客户端

```javascript
import { MCL10nClient } from '@th-suite/client';

const client = new MCL10nClient({
  baseURL: 'http://localhost:18000',
  apiKey: 'your-api-key'
});

// 启动扫描
const { task_id } = await client.scan.start({
  path: '/path/to/mod.jar',
  recursive: true
});

// 监控进度
client.progress.subscribe(task_id, (progress) => {
  console.log(`进度: ${(progress.progress * 100).toFixed(1)}%`);
});

// 获取结果
const result = await client.scan.getResult(task_id);
console.log(`发现 ${result.summary.mods_found} 个MOD`);
```

## 🔧 开发和测试

### API 测试

使用提供的测试集合测试 API：

```bash
# 使用 curl 测试
curl -X POST "http://localhost:18000/api/v2/scan/start" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/test/mod.jar"}'

# 使用 httpie 测试
http POST localhost:18000/api/v2/scan/start \
  path="/path/to/test/mod.jar" \
  recursive:=true
```

### 性能建议

1. **分页**: 大数据集请求使用分页参数
2. **筛选**: 使用查询参数减少不必要的数据传输
3. **缓存**: 合理使用 HTTP 缓存头
4. **批量操作**: 优先使用批量 API 而非多次单个请求
5. **WebSocket**: 实时数据使用 WebSocket 而非轮询

### 速率限制

| 端点类别 | 限制 | 窗口期 |
|----------|------|--------|
| **扫描操作** | 10 requests | 1 minute |
| **翻译操作** | 100 requests | 1 minute |
| **查询操作** | 1000 requests | 1 minute |
| **批量操作** | 5 requests | 1 minute |

---

本文档描述了 TH-Suite 的完整 API 接口。如有疑问或建议，请查阅在线文档或提交 Issue。