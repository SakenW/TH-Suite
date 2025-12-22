# MC L10n V6 API 规范

## 📋 概述

基于V6架构设计的RESTful API，支持键级差量同步、内容寻址、工作队列管理等核心功能。

**核心特性**：
- 键级差量同步 (Entry-Delta)
- Bloom握手 + 内容寻址
- NDJSON/Protobuf流式传输
- 幂等操作 + 断点续传
- 统一分页 + ETag/If-Match

## 🌐 API 基础信息

**Base URL**: `http://localhost:18000/api/v6`  
**Content-Type**: `application/json` | `application/x-ndjson` | `application/x-protobuf`  
**Compression**: `zstd`, `gzip`  
**认证**: Bearer Token (可选)

## 🔄 同步API

### 握手协商
```http
POST /api/v6/sync/handshake
Content-Type: application/json

{
  "client_cap": {
    "zstd": true,
    "dict_ids": ["zh_cn@2025-09", "en_us@2025-09"]
  },
  "bloom": {
    "k": 7,
    "m": 1048576,
    "hashes": ["base64_encoded_bloom_filter"]
  },
  "scope": {
    "locale": "zh_cn",
    "project_uid": "project_123",
    "pack_uid": "pack_456"
  }
}
```

**响应**:
```json
{
  "session_id": "sync_session_789",
  "missing_cids": ["cid_abc", "cid_def"],
  "dict_advice": [
    {
      "dict_id": "zh_cn@2025-09",
      "compression_ratio": 3.2
    }
  ],
  "limits": {
    "max_chunk_mb": 2,
    "max_concurrent": 4
  }
}
```

### 上传分片
```http
PUT /api/v6/sync/chunk/{cid}
Content-Type: application/x-ndjson
Content-Encoding: zstd
X-Idempotency-Key: {cid}
X-Session-Id: {session_id}
Range: bytes=0-1048575

{"entry_uid":"entry_123","language_file_uid":"file_456","key":"block.stone","base_version":"v1","changes":{"dst_text":"石头","status":"reviewed"},"ts":"2025-09-10T12:00:00Z"}
{"entry_uid":"entry_124","language_file_uid":"file_456","key":"block.dirt","base_version":"v1","changes":{"dst_text":"泥土","status":"reviewed"},"ts":"2025-09-10T12:01:00Z"}
```

**响应**:
```json
{
  "received_bytes": 1048576,
  "total_bytes": 2097152,
  "status": "partial",
  "next_offset": 1048576
}
```

### 提交会话
```http
POST /api/v6/sync/commit
Content-Type: application/json

{
  "session_id": "sync_session_789",
  "chunks": [
    {
      "cid": "cid_abc",
      "status": "received"
    }
  ]
}
```

## 📤 导出API

### 流式导出
```http
GET /api/v6/export/ndjson?locale=zh_cn&carrier=mod&after=2025-09-09T00:00:00Z&limit=1000
Accept: application/x-ndjson
Accept-Encoding: zstd
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/x-ndjson
Content-Encoding: zstd
X-TH-DB-Schema: v6.0
ETag: "revision_12345"

{"language_file_uid":"file_123","key":"block.stone","src_text":"Stone","dst_text":"石头","status":"reviewed","qa_flags":{},"version":"v2","updated_at":"2025-09-10T12:00:00Z"}
{"language_file_uid":"file_123","key":"block.dirt","src_text":"Dirt","dst_text":"泥土","status":"reviewed","qa_flags":{},"version":"v2","updated_at":"2025-09-10T12:01:00Z"}
```

### Protobuf导出
```http
GET /api/v6/export/pb?locale=zh_cn&carrier=mod&since_id=12345&limit=1000
Accept: application/x-protobuf
```

## 🗂️ 实体管理API

### 整合包管理

#### 列出整合包
```http
GET /api/v6/packs?platform=modrinth&limit=20&offset=0
```

#### 创建整合包
```http
POST /api/v6/packs
Content-Type: application/json

{
  "platform": "modrinth",
  "slug": "modpack-123",
  "title": "My Modpack",
  "author": "Player",
  "homepage": "https://example.com"
}
```

#### 获取整合包详情
```http
GET /api/v6/packs/{pack_uid}
```

### 整合包版本管理

#### 创建版本
```http
POST /api/v6/pack-versions
Content-Type: application/json

{
  "pack_uid": "pack_456",
  "mc_version": "1.20.1",
  "loader": "forge",
  "manifest_json": {
    "minecraft": {
      "version": "1.20.1"
    },
    "manifestType": "minecraftModpack",
    "files": []
  }
}
```

#### 列出版本
```http
GET /api/v6/pack-versions?pack_uid=pack_456
```

### MOD管理

#### 列出MOD
```http
GET /api/v6/mods?search=create&limit=20
```

#### 创建MOD
```http
POST /api/v6/mods
Content-Type: application/json

{
  "modid": "create",
  "slug": "create",
  "name": "Create",
  "homepage": "https://github.com/Creators-of-Create/Create"
}
```

#### MOD版本管理
```http
GET /api/v6/mod-versions?mod_uid=mod_123&mc_version=1.20.1
POST /api/v6/mod-versions
```

### 语言文件管理

#### 获取语言文件
```http
GET /api/v6/language-files?carrier=mod&carrier_uid=mod_123&locale=zh_cn
```

#### 创建语言文件
```http
POST /api/v6/language-files
Content-Type: application/json

{
  "carrier_type": "mod",
  "carrier_uid": "mod_123",
  "locale": "zh_cn",
  "rel_path": "assets/create/lang/zh_cn.json",
  "format": "json"
}
```

### 翻译条目管理

#### 获取翻译条目
```http
GET /api/v6/translations?language_file_uid=file_123&status=new&limit=100&after=entry_456
```

#### 更新翻译条目
```http
PUT /api/v6/translations/{entry_uid}
Content-Type: application/json
If-Match: "version_789"
X-Idempotency-Key: "update_12345"

{
  "dst_text": "石头",
  "status": "reviewed",
  "qa_flags": {
    "placeholder_check": "pass",
    "length_check": "pass"
  }
}
```

#### 批量更新翻译
```http
POST /api/v6/translations/batch
Content-Type: application/x-ndjson

{"entry_uid":"entry_123","dst_text":"石头","status":"reviewed"}
{"entry_uid":"entry_124","dst_text":"泥土","status":"reviewed"}
```

## 📊 统计和监控API

### 数据库统计
```http
GET /api/v6/database/statistics
```

**响应**:
```json
{
  "database": {
    "size_mb": 150.5,
    "page_count": 38528,
    "freelist_count": 0,
    "wal_frames": 0,
    "cache_hit_ratio": 0.95,
    "busy_retries": 0
  },
  "sync": {
    "bloom_miss_rate": 0.05,
    "cas_hit_rate": 0.85,
    "avg_chunk_size_mb": 1.2,
    "upload_throughput_mbps": 5.6,
    "download_throughput_mbps": 8.3,
    "failure_retry_rate": 0.008
  },
  "queue": {
    "depth": 12,
    "lag_ms": 45,
    "error_rate": 0.001,
    "avg_processing_time_ms": 150
  },
  "qa": {
    "placeholder_mismatch_rate": 0.02,
    "empty_string_rate": 0.001,
    "duplicate_key_rate": 0.0
  },
  "entities": {
    "packs": 5,
    "pack_versions": 12,
    "mods": 225,
    "mod_versions": 450,
    "language_files": 2122,
    "translation_entries": 526520
  }
}
```

### 缓存状态
```http
GET /api/v6/cache/status
```

### 队列状态
```http
GET /api/v6/queue/status
```

### 同步历史
```http
GET /api/v6/sync/history?limit=50
```

## 🔧 管理API

### 工作队列管理

#### 列出队列任务
```http
GET /api/v6/queue/tasks?state=pending&type=import_delta_block
```

#### 创建任务
```http
POST /api/v6/queue/tasks
Content-Type: application/json

{
  "type": "import_delta_block",
  "payload_json": {
    "chunk_cid": "cid_abc",
    "session_id": "sync_session_789"
  },
  "priority": 10,
  "dedupe_key": "import_cid_abc"
}
```

#### 租用任务
```http
POST /api/v6/queue/tasks/{task_id}/lease
Content-Type: application/json

{
  "lease_owner": "worker_001",
  "lease_duration_seconds": 300
}
```

#### 完成任务
```http
POST /api/v6/queue/tasks/{task_id}/complete
Content-Type: application/json

{
  "result": "success",
  "output": {}
}
```

### 配置管理

#### 获取配置
```http
GET /api/v6/settings
GET /api/v6/settings/{key}
```

#### 更新配置
```http
PUT /api/v6/settings/{key}
Content-Type: application/json

{
  "value": {
    "sync_interval_seconds": 300,
    "chunk_size_mb": 2
  }
}
```

### 缓存管理

#### 清理过期缓存
```http
POST /api/v6/cache/cleanup
```

#### 预热缓存
```http
POST /api/v6/cache/warmup
Content-Type: application/json

{
  "carrier_types": ["mod"],
  "locales": ["zh_cn", "en_us"]
}
```

## 📝 通用约定

### 分页
```http
# 基于偏移量
GET /api/v6/translations?limit=100&offset=200

# 基于游标
GET /api/v6/translations?limit=100&after=entry_456
```

### 错误响应
```json
{
  "error": "validation_failed",
  "message": "Invalid locale format",
  "details": {
    "field": "locale",
    "expected": "lowercase_underscore",
    "received": "zh-CN"
  },
  "request_id": "req_12345"
}
```

### 幂等性
- 使用 `X-Idempotency-Key` 头
- 支持60分钟幂等窗口
- 相同键返回相同结果

### 版本控制
- 使用 `ETag` / `If-Match` 进行版本控制
- 并发更新冲突返回 409 Conflict
- 支持乐观锁机制

---

**版本**: V6.0  
**创建时间**: 2025-09-10  
**状态**: 🚀 设计完成