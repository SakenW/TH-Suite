# TH Suite API 文档

## 概述

TH Suite 提供 RESTful API 和 WebSocket 接口，支持完整的本地化工作流程。

- **基础 URL**: `http://localhost:8000/api`
- **认证方式**: Bearer Token (可选)
- **响应格式**: JSON
- **字符编码**: UTF-8

## 认证

### 获取 Token (可选)
```http
POST /api/auth/token
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}
```

响应：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 使用 Token
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## API 端点

### 扫描服务

#### 扫描目录
扫描指定目录，提取所有语言文件。

```http
POST /api/scan/directory
Content-Type: application/json

{
  "path": "/path/to/modpack",
  "options": {
    "recursive": true,
    "include_patterns": ["*.jar", "*.zip"],
    "exclude_patterns": ["*.log", "*.tmp"],
    "max_depth": 10,
    "enable_cache": true
  }
}
```

响应：
```json
{
  "scan_id": "scan_20240120_123456",
  "status": "processing",
  "message": "Scan started successfully"
}
```

#### 获取扫描状态
```http
GET /api/scan/{scan_id}/status
```

响应：
```json
{
  "scan_id": "scan_20240120_123456",
  "status": "processing",
  "progress": {
    "current": 45,
    "total": 100,
    "percentage": 45.0,
    "current_file": "mod_xyz.jar",
    "elapsed_time": 12.5,
    "estimated_remaining": 15.2
  },
  "started_at": "2024-01-20T12:34:56Z",
  "updated_at": "2024-01-20T12:35:08Z"
}
```

状态值：
- `pending`: 等待处理
- `processing`: 正在扫描
- `completed`: 扫描完成
- `failed`: 扫描失败
- `cancelled`: 已取消

#### 获取扫描结果
```http
GET /api/scan/{scan_id}/result
```

响应：
```json
{
  "scan_id": "scan_20240120_123456",
  "project_path": "/path/to/modpack",
  "scan_started_at": "2024-01-20T12:34:56Z",
  "scan_completed_at": "2024-01-20T12:36:23Z",
  "artifacts": [
    {
      "artifact_id": "art_001",
      "artifact_type": "mod_jar",
      "file_path": "mods/example-mod-1.0.0.jar",
      "content_hash": "sha256:abc123...",
      "metadata": {
        "mod_id": "examplemod",
        "version": "1.0.0",
        "mc_version": "1.20.1"
      }
    }
  ],
  "containers": [
    {
      "container_id": "cnt_001",
      "container_type": "MOD",
      "namespace": "examplemod",
      "display_name": "Example Mod",
      "language_files": [
        {
          "locale": "en_us",
          "file_path": "assets/examplemod/lang/en_us.json",
          "entry_count": 150,
          "blob_hash": "sha256:def456..."
        },
        {
          "locale": "zh_cn",
          "file_path": "assets/examplemod/lang/zh_cn.json",
          "entry_count": 150,
          "blob_hash": "sha256:ghi789..."
        }
      ]
    }
  ],
  "statistics": {
    "total_artifacts": 25,
    "total_containers": 30,
    "total_language_files": 120,
    "total_entries": 5000,
    "total_unique_blobs": 100,
    "deduplication_ratio": 0.83,
    "supported_locales": ["en_us", "zh_cn", "ja_jp", "ko_kr"],
    "file_formats": {
      "json": 100,
      "properties": 20
    }
  },
  "warnings": [
    "Missing language file for mod 'xyz': zh_cn"
  ],
  "errors": []
}
```

#### 取消扫描
```http
POST /api/scan/{scan_id}/cancel
```

响应：
```json
{
  "scan_id": "scan_20240120_123456",
  "status": "cancelled",
  "message": "Scan cancelled successfully"
}
```

### 补丁管理

#### 获取补丁列表
```http
GET /api/patches?page=1&limit=20&status=active
```

查询参数：
- `page`: 页码 (默认: 1)
- `limit`: 每页数量 (默认: 20)
- `status`: 状态筛选 (active/archived/all)
- `search`: 搜索关键词

响应：
```json
{
  "items": [
    {
      "patch_set_id": "ps_001",
      "name": "简体中文补丁包 v1.0",
      "version": "1.0.0",
      "description": "适用于 ATM9 整合包的完整中文翻译",
      "status": "active",
      "target_locale": "zh_cn",
      "patch_count": 25,
      "created_at": "2024-01-20T10:00:00Z",
      "updated_at": "2024-01-20T12:00:00Z",
      "author": "Saken",
      "signature": "sha256:xyz789..."
    }
  ],
  "total": 45,
  "page": 1,
  "pages": 3
}
```

#### 创建补丁集
```http
POST /api/patches
Content-Type: application/json

{
  "name": "简体中文补丁包",
  "version": "1.0.0",
  "description": "完整的中文翻译补丁",
  "target_locale": "zh_cn",
  "patch_items": [
    {
      "container_id": "cnt_001",
      "namespace": "examplemod",
      "policy": "OVERLAY",
      "content": {
        "item.examplemod.example": "示例物品",
        "block.examplemod.example": "示例方块"
      }
    }
  ]
}
```

响应：
```json
{
  "patch_set_id": "ps_002",
  "name": "简体中文补丁包",
  "version": "1.0.0",
  "status": "active",
  "message": "Patch set created successfully"
}
```

#### 获取补丁详情
```http
GET /api/patches/{patch_set_id}
```

响应：
```json
{
  "patch_set_id": "ps_001",
  "name": "简体中文补丁包 v1.0",
  "version": "1.0.0",
  "description": "详细描述...",
  "status": "active",
  "target_locale": "zh_cn",
  "patch_items": [
    {
      "patch_item_id": "pi_001",
      "container_id": "cnt_001",
      "namespace": "examplemod",
      "policy": "OVERLAY",
      "content": {
        "item.examplemod.example": "示例物品"
      },
      "expected_hash": "sha256:abc123..."
    }
  ],
  "metadata": {
    "total_entries": 500,
    "affected_mods": ["examplemod", "anothermod"],
    "compatibility": {
      "mc_version": "1.20.1",
      "loader": "forge",
      "loader_version": "47.2.0"
    }
  },
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T12:00:00Z"
}
```

#### 应用补丁
```http
PUT /api/patches/{patch_set_id}/apply
Content-Type: application/json

{
  "target_path": "/path/to/modpack",
  "dry_run": false,
  "backup": true,
  "writeback_strategy": "OVERLAY"
}
```

写回策略：
- `OVERLAY`: 创建资源包覆盖
- `JAR_MODIFY`: 直接修改 JAR 文件
- `DIRECTORY`: 写入目录结构

响应：
```json
{
  "patch_set_id": "ps_001",
  "status": "success",
  "applied_items": 25,
  "skipped_items": 2,
  "failed_items": 0,
  "backup_path": "/path/to/modpack/.backups/20240120_123456",
  "details": [
    {
      "container_id": "cnt_001",
      "status": "applied",
      "entries_modified": 50
    }
  ],
  "warnings": [
    "Container 'xyz' not found, skipped"
  ]
}
```

#### 回滚补丁
```http
DELETE /api/patches/{patch_set_id}/rollback
Content-Type: application/json

{
  "target_path": "/path/to/modpack",
  "backup_id": "20240120_123456"
}
```

响应：
```json
{
  "status": "success",
  "message": "Patch rolled back successfully",
  "restored_files": 25
}
```

### 质量检查

#### 运行质量验证
```http
POST /api/quality/validate
Content-Type: application/json

{
  "source_locale": "en_us",
  "target_locale": "zh_cn",
  "entries": [
    {
      "key": "item.example",
      "source": "Example Item %s",
      "target": "示例物品 %s"
    }
  ],
  "validators": ["placeholder", "color_code", "length_ratio"]
}
```

响应：
```json
{
  "validation_id": "val_001",
  "overall_status": "passed",
  "total_entries": 1,
  "passed": 1,
  "warnings": 0,
  "errors": 0,
  "results": [
    {
      "key": "item.example",
      "status": "passed",
      "validators": {
        "placeholder": {
          "passed": true,
          "message": "Placeholders match"
        },
        "color_code": {
          "passed": true,
          "message": "No color codes detected"
        },
        "length_ratio": {
          "passed": true,
          "ratio": 0.95,
          "message": "Length ratio within acceptable range"
        }
      }
    }
  ]
}
```

#### 获取质量报告
```http
GET /api/quality/reports/{project_id}
```

响应：
```json
{
  "project_id": "proj_001",
  "generated_at": "2024-01-20T15:00:00Z",
  "summary": {
    "total_entries": 5000,
    "validated_entries": 4800,
    "pass_rate": 0.96,
    "warning_rate": 0.03,
    "error_rate": 0.01
  },
  "by_validator": {
    "placeholder": {
      "passed": 4700,
      "warnings": 50,
      "errors": 50
    },
    "color_code": {
      "passed": 4750,
      "warnings": 30,
      "errors": 20
    }
  },
  "by_container": [
    {
      "container_id": "cnt_001",
      "name": "Example Mod",
      "pass_rate": 0.98,
      "issues": [
        {
          "key": "item.broken",
          "type": "error",
          "validator": "placeholder",
          "message": "Missing placeholder %s"
        }
      ]
    }
  ],
  "recommendations": [
    "Consider reviewing entries with length ratio > 2.0",
    "5 entries contain untranslated TODO markers"
  ]
}
```

#### 获取可用验证器
```http
GET /api/quality/validators
```

响应：
```json
{
  "validators": [
    {
      "id": "placeholder",
      "name": "占位符验证器",
      "description": "检查占位符一致性",
      "severity": "error",
      "configurable": true,
      "config_schema": {
        "strict_mode": {
          "type": "boolean",
          "default": false,
          "description": "严格模式下占位符顺序也必须一致"
        }
      }
    },
    {
      "id": "color_code",
      "name": "颜色代码验证器",
      "description": "检查 Minecraft 颜色代码",
      "severity": "warning"
    },
    {
      "id": "length_ratio",
      "name": "长度比例验证器",
      "description": "检查翻译长度比例",
      "severity": "warning",
      "configurable": true,
      "config_schema": {
        "max_ratio": {
          "type": "number",
          "default": 2.0,
          "description": "最大长度比例"
        }
      }
    }
  ]
}
```

### Trans-Hub 集成

#### 同步项目
```http
POST /api/trans-hub/sync
Content-Type: application/json
Authorization: Bearer {trans_hub_token}

{
  "project_id": "minecraft_atm9",
  "scan_result_id": "scan_20240120_123456",
  "options": {
    "upload_missing": true,
    "download_existing": true,
    "auto_apply": false,
    "conflict_resolution": "use_remote"
  }
}
```

响应：
```json
{
  "sync_id": "sync_001",
  "status": "processing",
  "uploaded": 0,
  "downloaded": 0,
  "conflicts": 0,
  "message": "Synchronization started"
}
```

#### 获取同步状态
```http
GET /api/trans-hub/sync/{sync_id}/status
```

响应：
```json
{
  "sync_id": "sync_001",
  "status": "processing",
  "progress": {
    "uploaded": 150,
    "downloaded": 300,
    "total": 500,
    "percentage": 90.0
  },
  "conflicts": [
    {
      "key": "item.example",
      "local": "本地翻译",
      "remote": "远程翻译",
      "resolution": "pending"
    }
  ],
  "started_at": "2024-01-20T16:00:00Z",
  "estimated_completion": "2024-01-20T16:05:00Z"
}
```

#### 上传待翻译内容
```http
POST /api/trans-hub/upload
Content-Type: application/x-ndjson
Authorization: Bearer {trans_hub_token}

{"key":"item.example","source":"Example Item","context":"minecraft:items"}
{"key":"block.example","source":"Example Block","context":"minecraft:blocks"}
```

响应：
```json
{
  "upload_id": "upl_001",
  "received": 2,
  "accepted": 2,
  "rejected": 0,
  "message": "Content uploaded successfully"
}
```

#### 获取项目列表
```http
GET /api/trans-hub/projects
Authorization: Bearer {trans_hub_token}
```

响应：
```json
{
  "projects": [
    {
      "project_id": "minecraft_atm9",
      "name": "All The Mods 9",
      "description": "ATM9 整合包翻译项目",
      "languages": ["en_us", "zh_cn", "ja_jp"],
      "statistics": {
        "total_entries": 10000,
        "translated": {
          "zh_cn": 8500,
          "ja_jp": 6000
        },
        "completion": {
          "zh_cn": 0.85,
          "ja_jp": 0.60
        }
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-20T12:00:00Z"
    }
  ]
}
```

### WebSocket 接口

#### 连接建立
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  // 订阅事件
  ws.send(JSON.stringify({
    type: 'subscribe',
    events: ['scan.progress', 'patch.applied', 'sync.update']
  }));
};
```

#### 事件类型

##### 扫描进度
```json
{
  "type": "scan.progress",
  "data": {
    "scan_id": "scan_001",
    "current": 50,
    "total": 100,
    "current_file": "mod.jar",
    "percentage": 50.0
  }
}
```

##### 补丁应用
```json
{
  "type": "patch.applied",
  "data": {
    "patch_set_id": "ps_001",
    "container_id": "cnt_001",
    "entries_modified": 50,
    "status": "success"
  }
}
```

##### 同步更新
```json
{
  "type": "sync.update",
  "data": {
    "sync_id": "sync_001",
    "action": "downloaded",
    "key": "item.example",
    "value": "示例物品"
  }
}
```

##### 错误通知
```json
{
  "type": "error",
  "data": {
    "code": "SCAN_FAILED",
    "message": "Failed to read file: permission denied",
    "details": {
      "file": "/path/to/file.jar"
    }
  }
}
```

## 错误处理

### 错误响应格式
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "field": "path",
      "reason": "Path does not exist"
    }
  },
  "timestamp": "2024-01-20T12:00:00Z",
  "request_id": "req_123456"
}
```

### 错误代码

| 代码 | HTTP 状态 | 描述 |
|------|-----------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| UNAUTHORIZED | 401 | 未授权访问 |
| FORBIDDEN | 403 | 无权限访问 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| RATE_LIMITED | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 503 | 服务暂时不可用 |

## 限流策略

- **默认限制**: 100 请求/分钟
- **扫描接口**: 10 请求/分钟
- **上传接口**: 50 请求/分钟
- **WebSocket**: 最多 10 个并发连接

超出限制时返回：
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "retry_after": 30
  }
}
```

## SDK 示例

### Python SDK
```python
from th_suite import THSuiteClient

# 初始化客户端
client = THSuiteClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# 扫描项目
scan_result = client.scan_directory(
    path="/path/to/modpack",
    recursive=True
)

# 创建补丁
patch = client.create_patch(
    name="Chinese Translation",
    target_locale="zh_cn",
    items=[...]
)

# 应用补丁
client.apply_patch(
    patch_id=patch.id,
    target_path="/path/to/modpack"
)
```

### JavaScript/TypeScript SDK
```typescript
import { THSuiteClient } from '@th-suite/client';

const client = new THSuiteClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your_api_key'
});

// 扫描项目
const scanResult = await client.scanDirectory({
  path: '/path/to/modpack',
  recursive: true
});

// 监听实时进度
client.on('scan.progress', (progress) => {
  console.log(`Progress: ${progress.percentage}%`);
});

// 创建补丁
const patch = await client.createPatch({
  name: 'Chinese Translation',
  targetLocale: 'zh_cn',
  items: [...]
});
```

## 版本管理

### API 版本
- 当前版本: v1
- 版本路径: `/api/v1/`
- 向后兼容: 至少 6 个月

### 版本协商
```http
Accept: application/vnd.th-suite.v1+json
```

### 废弃通知
废弃的端点会在响应头中包含：
```http
X-Deprecated: true
X-Sunset-Date: 2024-07-20
```

---

最后更新: 2024-01-20
API 版本: 1.0.0