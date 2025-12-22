# MC L10n API 文档

## 概述

MC L10n v6.0 采用六边形架构和领域驱动设计，提供了简洁而强大的API接口。

**基础URL**: `http://localhost:18000`  
**API版本**: v6.0  
**认证方式**: Bearer Token（可选）

## 架构说明

### 分层架构

```
┌─────────────────────────────────────┐
│         REST API (FastAPI)          │  <- 外部接口
├─────────────────────────────────────┤
│         Facade (门面层)             │  <- 简化接口
├─────────────────────────────────────┤
│     Application Services (应用层)   │  <- 业务用例
├─────────────────────────────────────┤
│       Domain Layer (领域层)         │  <- 核心业务
├─────────────────────────────────────┤
│    Infrastructure (基础设施层)      │  <- 技术实现
└─────────────────────────────────────┘
```

## API 端点

### 1. 扫描管理

#### 扫描MOD目录

```http
POST /api/v1/scan
```

**请求体**:
```json
{
  "path": "/path/to/mods",
  "recursive": true,
  "auto_extract": true,
  "include_patterns": ["*.jar", "*.zip"],
  "exclude_patterns": ["*backup*", "*.old"]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "total_files": 150,
    "mods_found": 45,
    "translations_found": 1250,
    "errors": [],
    "duration": 12.5
  }
}
```

#### 快速扫描（仅统计）

```http
GET /api/v1/scan/quick?path=/path/to/mods
```

**响应**:
```json
{
  "total_mods": 45,
  "total_jars": 50,
  "total_languages": 8,
  "languages": ["en_us", "zh_cn", "ja_jp"],
  "estimated_translations": 1250
}
```

#### 获取扫描进度

```http
GET /api/v1/scan/progress/{scan_id}
```

**响应**:
```json
{
  "scan_id": "scan_12345",
  "status": "in_progress",
  "progress": 65,
  "current_file": "twilightforest-1.21.1.jar",
  "processed": 30,
  "total": 45,
  "estimated_remaining": 8.5
}
```

### 2. MOD管理

#### 获取MOD列表

```http
GET /api/v1/mods?page=1&size=20&search=twilight
```

**响应**:
```json
{
  "items": [
    {
      "mod_id": "twilightforest",
      "name": "The Twilight Forest",
      "version": "4.7.3196",
      "file_path": "/mods/twilightforest-1.21.1.jar",
      "translation_count": 850,
      "languages": ["en_us", "zh_cn"],
      "last_scanned": "2025-09-06T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "size": 20
}
```

#### 获取MOD详情

```http
GET /api/v1/mods/{mod_id}
```

**响应**:
```json
{
  "mod_id": "twilightforest",
  "metadata": {
    "name": "The Twilight Forest",
    "version": "4.7.3196",
    "author": "TeamTwilight",
    "description": "An enchanted forest dimension"
  },
  "statistics": {
    "total_keys": 850,
    "translated": {
      "zh_cn": 750,
      "ja_jp": 600
    },
    "approved": {
      "zh_cn": 700,
      "ja_jp": 550
    }
  },
  "quality_score": 0.92
}
```

### 3. 翻译管理

#### 提交翻译

```http
POST /api/v1/translations
```

**请求体**:
```json
{
  "mod_id": "twilightforest",
  "language": "zh_cn",
  "translations": {
    "item.twilightforest.naga_scale": "娜迦鳞片",
    "item.twilightforest.naga_chestplate": "娜迦鳞胸甲"
  },
  "translator": "user123",
  "auto_approve": false
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "mod_id": "twilightforest",
    "language": "zh_cn",
    "translated_count": 2,
    "failed_count": 0,
    "progress": 88.2,
    "quality_score": 0.95
  }
}
```

#### 批量翻译

```http
POST /api/v1/translations/batch
```

**请求体**:
```json
{
  "mod_ids": ["mod1", "mod2", "mod3"],
  "language": "zh_cn",
  "glossary_id": "minecraft_terms",
  "quality_threshold": 0.8
}
```

#### 获取翻译状态

```http
GET /api/v1/translations/{mod_id}/{language}
```

**响应**:
```json
{
  "mod_id": "twilightforest",
  "language": "zh_cn",
  "progress": 88.2,
  "total_keys": 850,
  "translated": 750,
  "approved": 700,
  "pending": 50,
  "rejected": 0,
  "last_updated": "2025-09-06T12:00:00Z"
}
```

### 4. 项目管理

#### 创建翻译项目

```http
POST /api/v1/projects
```

**请求体**:
```json
{
  "name": "ATM10 本地化项目",
  "description": "All The Mods 10 整合包翻译",
  "mod_ids": ["twilightforest", "ars_nouveau", "create"],
  "target_languages": ["zh_cn", "zh_tw", "ja_jp"],
  "auto_assign": true,
  "deadline": "2025-10-01T00:00:00Z"
}
```

**响应**:
```json
{
  "project_id": "proj_a1b2c3d4",
  "name": "ATM10 本地化项目",
  "status": "active",
  "created_at": "2025-09-06T13:00:00Z"
}
```

#### 获取项目状态

```http
GET /api/v1/projects/{project_id}
```

**响应**:
```json
{
  "project_id": "proj_a1b2c3d4",
  "name": "ATM10 本地化项目",
  "status": "active",
  "progress": {
    "overall": 65.5,
    "by_language": {
      "zh_cn": 75.0,
      "zh_tw": 60.0,
      "ja_jp": 61.5
    }
  },
  "statistics": {
    "total_mods": 3,
    "total_keys": 2500,
    "translated": 1638,
    "approved": 1500,
    "pending": 138
  },
  "estimated_completion": "2025-09-25T00:00:00Z"
}
```

#### 分配翻译任务

```http
POST /api/v1/projects/{project_id}/assign
```

**请求体**:
```json
{
  "translator_id": "user123",
  "language": "zh_cn",
  "mod_ids": ["twilightforest", "create"],
  "priority": "high"
}
```

### 5. 质量管理

#### 质量检查

```http
POST /api/v1/quality/check
```

**请求体**:
```json
{
  "mod_id": "twilightforest",
  "language": "zh_cn",
  "check_types": ["consistency", "terminology", "formatting"]
}
```

**响应**:
```json
{
  "mod_id": "twilightforest",
  "language": "zh_cn",
  "quality_score": 0.92,
  "issues": [
    {
      "type": "consistency",
      "severity": "warning",
      "key": "item.twilightforest.fiery_sword",
      "message": "术语不一致：'Fiery' 在其他地方翻译为'炽热的'"
    }
  ],
  "statistics": {
    "checked": 750,
    "passed": 690,
    "warnings": 50,
    "errors": 10
  }
}
```

#### 批准翻译

```http
POST /api/v1/quality/approve
```

**请求体**:
```json
{
  "mod_id": "twilightforest",
  "language": "zh_cn",
  "keys": ["item.twilightforest.naga_scale"],
  "reviewer": "admin",
  "quality_score": 0.95
}
```

### 6. 同步服务

#### 同步到Trans-Hub

```http
POST /api/v1/sync/transhub
```

**请求体**:
```json
{
  "server_url": "https://api.trans-hub.cn",
  "api_key": "your_api_key",
  "project_id": "proj_a1b2c3d4",
  "conflict_strategy": "keep_highest_quality"
}
```

**响应**:
```json
{
  "success": true,
  "synced_count": 150,
  "conflict_count": 5,
  "error_count": 0,
  "duration": 8.5,
  "conflicts_resolved": {
    "kept_local": 2,
    "kept_remote": 3
  }
}
```

#### 导出翻译

```http
GET /api/v1/export/{mod_id}?format=json&language=zh_cn
```

**响应**:
```json
{
  "mod_id": "twilightforest",
  "language": "zh_cn",
  "format": "json",
  "translations": {
    "item.twilightforest.naga_scale": "娜迦鳞片",
    "item.twilightforest.naga_chestplate": "娜迦鳞胸甲"
  },
  "metadata": {
    "exported_at": "2025-09-06T14:00:00Z",
    "total_keys": 750,
    "quality_score": 0.92
  }
}
```

### 7. 系统管理

#### 健康检查

```http
GET /api/v1/health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "6.0.0",
  "uptime": 3600,
  "checks": {
    "database": "ok",
    "cache": "ok",
    "scanner": "ok"
  },
  "statistics": {
    "total_mods": 150,
    "total_translations": 25000,
    "active_projects": 5
  }
}
```

#### 获取系统统计

```http
GET /api/v1/stats
```

**响应**:
```json
{
  "performance": {
    "cache_hit_rate": 0.85,
    "avg_scan_time": 0.25,
    "db_connections": {
      "active": 3,
      "idle": 7,
      "total": 10
    }
  },
  "usage": {
    "api_calls_today": 1250,
    "translations_today": 500,
    "active_users": 15
  }
}
```

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "MOD_NOT_FOUND",
    "message": "指定的MOD不存在",
    "details": {
      "mod_id": "invalid_mod"
    }
  },
  "timestamp": "2025-09-06T15:00:00Z"
}
```

### 常见错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `MOD_NOT_FOUND` | 404 | MOD不存在 |
| `INVALID_LANGUAGE` | 400 | 无效的语言代码 |
| `TRANSLATION_LOCKED` | 423 | 翻译已被锁定 |
| `QUALITY_CHECK_FAILED` | 422 | 质量检查未通过 |
| `SYNC_CONFLICT` | 409 | 同步冲突 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |

## 性能优化

### 缓存策略

- **快速扫描**: 5分钟缓存
- **MOD列表**: 1分钟缓存
- **翻译统计**: 30秒缓存
- **质量报告**: 10分钟缓存

### 批处理支持

多个API支持批处理以提高性能：

```http
POST /api/v1/batch
```

**请求体**:
```json
{
  "operations": [
    {
      "method": "GET",
      "path": "/api/v1/mods/mod1"
    },
    {
      "method": "GET",
      "path": "/api/v1/mods/mod2"
    }
  ]
}
```

### 速率限制

- **默认限制**: 100请求/分钟
- **批量操作**: 10请求/分钟
- **导出操作**: 20请求/小时

## WebSocket 实时更新

### 连接

```javascript
const ws = new WebSocket('ws://localhost:18000/ws');
```

### 订阅事件

```json
{
  "action": "subscribe",
  "events": ["scan_progress", "translation_update"]
}
```

### 接收更新

```json
{
  "event": "scan_progress",
  "data": {
    "scan_id": "scan_12345",
    "progress": 75,
    "current_file": "create-1.21.1.jar"
  }
}
```

## SDK 示例

### Python

```python
from mc_l10n_client import MCL10nClient

client = MCL10nClient(base_url="http://localhost:18000")

# 扫描MODs
result = client.scan_mods(
    path="/path/to/mods",
    recursive=True
)

# 提交翻译
client.submit_translation(
    mod_id="twilightforest",
    language="zh_cn",
    translations={
        "item.twilightforest.naga_scale": "娜迦鳞片"
    }
)
```

### JavaScript/TypeScript

```typescript
import { MCL10nClient } from '@mc-l10n/client';

const client = new MCL10nClient({
  baseUrl: 'http://localhost:18000'
});

// 扫描MODs
const result = await client.scanMods({
  path: '/path/to/mods',
  recursive: true
});

// 监听实时更新
client.on('scanProgress', (data) => {
  console.log(`Progress: ${data.progress}%`);
});
```

## 最佳实践

1. **使用批处理**: 合并多个请求以减少网络开销
2. **启用缓存**: 利用HTTP缓存头减少重复请求
3. **异步处理**: 对长时间操作使用WebSocket监听进度
4. **错误重试**: 实现指数退避的重试机制
5. **资源分页**: 使用分页避免一次加载过多数据

## 版本历史

- **v6.0.0** (2025-09-06)
  - 采用六边形架构重构
  - 添加门面模式简化API
  - 实现批处理和缓存优化
  - 支持WebSocket实时更新

- **v5.0.0** (2025-08-01)
  - 初始版本发布
  - 基础扫描和翻译功能
  - SQLite本地数据库支持