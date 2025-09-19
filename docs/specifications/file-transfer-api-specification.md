# TH-Suite 统一文件传输API设计规范

## 概述

基于Trans-Hub最佳实践，为TH-Suite设计统一的文件传输API接口系统，支持：
- 大文件分块上传/下载（>1GB）
- 断点续传和失败重试
- 实时进度监控和状态同步
- 完整的错误处理和用户反馈
- 与现有v2.1架构无缝集成

## 核心设计原则

### 1. 统一接口设计
- 所有文件传输操作使用统一的API前缀：`/api/v6/transfer/`
- 标准化的请求/响应格式
- 一致的错误码和状态定义

### 2. 分块传输机制
- 默认分块大小：1MB（可配置1KB-10MB）
- 支持并发分块传输（最大8个并发）
- 智能分块大小自适应调整

### 3. 断点续传支持
- 基于文件BLAKE3哈希的唯一标识
- 分块级别的续传检查
- 传输会话状态持久化

### 4. 实时进度推送
- WebSocket实时进度事件推送
- 详细的传输统计信息
- 性能指标监控

## API端点设计

### 核心传输端点

#### 1. 上传相关

```http
POST /api/v6/transfer/upload/initialize
```
- 初始化文件上传会话
- 返回upload_session_id和分块配置

```http
POST /api/v6/transfer/upload/chunk/{session_id}/{chunk_index}
```
- 上传单个文件分块
- 支持幂等性重试

```http
POST /api/v6/transfer/upload/finalize/{session_id}
```
- 完成文件上传并验证完整性

```http
GET /api/v6/transfer/upload/status/{session_id}
```
- 获取上传会话状态

#### 2. 下载相关

```http
POST /api/v6/transfer/download/initialize
```
- 初始化文件下载会话
- 返回download_session_id和文件元信息

```http
GET /api/v6/transfer/download/chunk/{session_id}/{chunk_index}
```
- 下载单个文件分块
- 支持Range请求

```http
GET /api/v6/transfer/download/status/{session_id}
```
- 获取下载会话状态

#### 3. 会话管理

```http
GET /api/v6/transfer/sessions
```
- 列出当前活跃的传输会话

```http
DELETE /api/v6/transfer/sessions/{session_id}
```
- 取消传输会话

```http
POST /api/v6/transfer/sessions/{session_id}/resume
```
- 恢复中断的传输会话

## 数据模型设计

### 传输会话表

```sql
CREATE TABLE transfer_sessions (
    session_id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL CHECK (session_type IN ('upload', 'download')),
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT NOT NULL,  -- BLAKE3 hash
    chunk_size INTEGER NOT NULL DEFAULT 1048576,  -- 1MB
    total_chunks INTEGER NOT NULL,
    completed_chunks INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('initializing', 'active', 'paused', 'completed', 'failed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    error_message TEXT,
    metadata JSONB
);
```

### 分块状态表

```sql
CREATE TABLE transfer_chunks (
    session_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL,  -- BLAKE3 hash for chunk
    chunk_size INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'uploading', 'completed', 'failed')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMP,
    PRIMARY KEY (session_id, chunk_index),
    FOREIGN KEY (session_id) REFERENCES transfer_sessions(session_id) ON DELETE CASCADE
);
```

### 传输统计表

```sql
CREATE TABLE transfer_stats (
    session_id TEXT PRIMARY KEY,
    bytes_transferred INTEGER NOT NULL DEFAULT 0,
    transfer_rate_bps INTEGER NOT NULL DEFAULT 0,
    estimated_completion TIMESTAMP,
    start_time TIMESTAMP NOT NULL,
    completion_time TIMESTAMP,
    error_count INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES transfer_sessions(session_id) ON DELETE CASCADE
);
```

## 请求/响应格式

### 上传初始化请求

```json
{
  "file_name": "large_modpack.zip",
  "file_size": 2147483648,
  "file_hash": "blake3:a1b2c3d4e5f6...",
  "chunk_size": 1048576,
  "metadata": {
    "content_type": "application/zip",
    "project_id": "proj_123",
    "upload_source": "mod_scanner"
  },
  "options": {
    "enable_compression": true,
    "max_concurrent_chunks": 4,
    "auto_retry": true,
    "max_retries": 3
  }
}
```

### 上传初始化响应

```json
{
  "success": true,
  "data": {
    "session_id": "upload_sess_abc123",
    "total_chunks": 2048,
    "chunk_size": 1048576,
    "expires_at": "2025-09-20T18:00:00Z",
    "upload_urls": [
      "/api/v6/transfer/upload/chunk/upload_sess_abc123/0",
      "/api/v6/transfer/upload/chunk/upload_sess_abc123/1"
    ],
    "resumable": true,
    "compression_enabled": true
  }
}
```

### 传输状态响应

```json
{
  "success": true,
  "data": {
    "session_id": "upload_sess_abc123",
    "status": "active",
    "progress": {
      "percentage": 45.2,
      "bytes_transferred": 967458816,
      "total_bytes": 2147483648,
      "completed_chunks": 924,
      "total_chunks": 2048,
      "transfer_rate_bps": 10485760,
      "estimated_completion": "2025-09-19T18:15:30Z",
      "elapsed_seconds": 125.5
    },
    "current_chunk": 924,
    "failed_chunks": [156, 342],
    "retry_count": 2,
    "last_activity": "2025-09-19T18:10:15Z"
  }
}
```

## WebSocket事件推送

### 连接端点
```
ws://localhost:18000/api/v6/transfer/ws
```

### 事件类型

#### 进度更新事件
```json
{
  "event_type": "transfer_progress",
  "session_id": "upload_sess_abc123",
  "timestamp": "2025-09-19T18:10:15Z",
  "data": {
    "progress_percentage": 45.2,
    "bytes_transferred": 967458816,
    "transfer_rate_bps": 10485760,
    "current_chunk": 924,
    "estimated_completion": "2025-09-19T18:15:30Z"
  }
}
```

#### 状态变更事件
```json
{
  "event_type": "transfer_status_changed",
  "session_id": "upload_sess_abc123",
  "timestamp": "2025-09-19T18:10:15Z",
  "data": {
    "old_status": "active",
    "new_status": "completed",
    "completion_time": "2025-09-19T18:10:15Z",
    "final_stats": {
      "total_bytes": 2147483648,
      "transfer_duration_seconds": 245.8,
      "average_rate_bps": 8734567,
      "retry_count": 3
    }
  }
}
```

#### 错误事件
```json
{
  "event_type": "transfer_error",
  "session_id": "upload_sess_abc123",
  "timestamp": "2025-09-19T18:10:15Z",
  "data": {
    "error_type": "chunk_upload_failed",
    "error_message": "Chunk 156 upload failed: network timeout",
    "chunk_index": 156,
    "retry_count": 2,
    "max_retries": 3,
    "auto_retry": true
  }
}
```

## 错误处理规范

### 错误代码定义

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| TRANSFER_SESSION_NOT_FOUND | 404 | 传输会话不存在 |
| TRANSFER_SESSION_EXPIRED | 410 | 传输会话已过期 |
| CHUNK_INDEX_INVALID | 400 | 分块索引无效 |
| CHUNK_HASH_MISMATCH | 422 | 分块哈希校验失败 |
| FILE_SIZE_EXCEEDED | 413 | 文件大小超过限制 |
| CONCURRENT_LIMIT_EXCEEDED | 429 | 并发传输数量超过限制 |
| STORAGE_QUOTA_EXCEEDED | 507 | 存储配额不足 |
| NETWORK_TIMEOUT | 504 | 网络超时 |
| COMPRESSION_FAILED | 500 | 压缩处理失败 |

### 重试策略

#### 指数退避重试
- 初始延迟：1秒
- 最大延迟：30秒
- 退避系数：2.0
- 最大重试次数：3次

#### 重试条件
- 网络超时（5xx错误）
- 临时服务不可用（503错误）
- 分块哈希校验失败
- 存储临时错误

## 性能优化策略

### 1. 并发控制
- 客户端最大并发分块：8个
- 服务端连接池：每用户最大20个连接
- 全局并发限制：200个活跃会话

### 2. 缓存策略
- 分块元数据缓存：Redis，TTL 1小时
- 文件哈希缓存：本地LRU缓存，最大1000项
- 传输会话缓存：内存缓存，TTL 24小时

### 3. 压缩优化
- 自动检测文件类型
- ZIP/JAR文件：不压缩（已压缩）
- JSON/文本文件：Zstd压缩
- 图片文件：不压缩

### 4. 存储优化
- 临时文件：分块存储，定期清理
- 完成文件：移动到最终位置
- 垃圾回收：每小时清理过期会话

## 安全考虑

### 1. 认证授权
- JWT token验证
- 基于角色的访问控制
- 传输会话绑定用户

### 2. 数据安全
- 传输中加密：TLS 1.3
- 存储加密：AES-256
- 哈希验证：BLAKE3完整性校验

### 3. 限制保护
- 文件大小限制：单文件最大10GB
- 上传速率限制：每用户100MB/s
- 会话数量限制：每用户最大10个并发

## 监控指标

### 传输性能指标
- 平均传输速度
- 传输成功率
- 平均完成时间
- 并发会话数量

### 系统资源指标
- 磁盘I/O使用率
- 内存使用量
- 网络带宽使用
- CPU使用率

### 业务指标
- 日传输文件数量
- 总传输数据量
- 失败传输比率
- 用户活跃度

## 集成接口

### Trans-Hub同步集成
- 支持Trans-Hub UIDA协议
- 自动同步传输状态
- 兼容现有同步流程

### 扫描系统集成
- 扫描结果自动上传
- 进度状态统一推送
- 错误日志集中处理

### 项目管理集成
- 项目文件自动归档
- 版本控制集成
- 备份恢复支持