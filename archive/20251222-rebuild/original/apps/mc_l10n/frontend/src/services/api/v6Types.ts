/**
 * V6 API类型定义
 * 
 * 定义V6架构相关的所有TypeScript类型
 * 与后端API保持一致的类型定义
 */

// ==================== 基础类型 ====================

export type V6EntityStatus = 'active' | 'inactive' | 'archived'
export type V6PackType = 'integration' | 'resource' | 'data'
export type V6FileFormat = 'json' | 'properties' | 'yaml'
export type V6TranslationStatus = 'new' | 'reviewing' | 'reviewed' | 'approved' | 'rejected'
export type V6TaskStatus = 'pending' | 'leased' | 'completed' | 'failed'
export type V6HealthStatus = 'healthy' | 'degraded' | 'unhealthy'

// ==================== 核心实体类型 ====================

export interface V6Pack {
  uid: string
  name: string
  description?: string
  version?: string
  pack_type: V6PackType
  status: V6EntityStatus
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface V6Mod {
  uid: string
  pack_uid?: string
  mod_id: string
  display_name: string
  version?: string
  mod_loader?: string
  file_path: string
  file_type: 'jar' | 'directory'
  file_hash?: string
  status: V6EntityStatus
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface V6LanguageFile {
  uid: string
  mod_uid: string
  locale: string
  file_path: string
  format: V6FileFormat
  entry_count: number
  file_hash?: string
  status: V6EntityStatus
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface V6TranslationEntry {
  uid: string
  uida_keys_b64: string
  uida_sha256_hex: string
  key: string
  src_text: string
  dst_text: string
  status: V6TranslationStatus
  language_file_uid: string
  reviewer_notes?: string
  qa_issues?: string[]
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

// ==================== 操作实体类型 ====================

export interface V6ScanSession {
  uid: string
  project_path: string
  scan_type: 'full' | 'incremental'
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  discovered_mods: number
  discovered_languages: number
  discovered_entries: number
  error_message?: string
  metadata?: Record<string, any>
  started_at: string
  completed_at?: string
}

export interface V6WorkItem {
  uid: string
  idempotency_key: string
  task_type: string
  status: V6TaskStatus
  priority: number
  max_retries: number
  retry_count: number
  payload: Record<string, any>
  result?: Record<string, any>
  error_message?: string
  lease_expires_at?: string
  created_at: string
  updated_at: string
}

export interface V6OutboxEntry {
  uid: string
  entity_type: string
  entity_uid: string
  change_type: 'create' | 'update' | 'delete'
  old_values?: Record<string, any>
  new_values?: Record<string, any>
  processed: boolean
  created_at: string
  processed_at?: string
}

// ==================== 统计和监控类型 ====================

export interface V6DatabaseStatistics {
  core_entities: {
    packs: number
    mods: number
    language_files: number
    translation_entries: number
  }
  operational: {
    scan_sessions: number
    work_items: number
    outbox_entries: number
  }
  configuration: {
    settings: number
  }
  cache: {
    file_hashes: number
  }
  total_records: number
  database_size_mb: number
  last_updated: string
}

export interface V6CacheStatistics {
  l1_translations: {
    size: number
    capacity: number
    hit_rate: number
    miss_count: number
  }
  l2_language_files: {
    size: number
    capacity: number
    hit_rate: number
    miss_count: number
  }
  l3_mods: {
    size: number
    capacity: number
    hit_rate: number
    miss_count: number
  }
  l4_statistics: {
    size: number
    capacity: number
    hit_rate: number
    miss_count: number
  }
  memory_usage_mb: number
  total_operations: number
}

export interface V6HealthCheck {
  status: V6HealthStatus
  database: {
    connection: boolean
    tables: number
    indexes: number
    last_backup?: string
  }
  queue: {
    active_tasks: number
    pending_tasks: number
    failed_tasks: number
    dead_letter_count: number
  }
  cache: {
    l1_size: number
    l1_hit_rate: number
    memory_usage_mb: number
    health_score: number
  }
  disk: {
    available_space_gb: number
    database_size_mb: number
    temp_files_mb: number
  }
  last_check: string
  response_time_ms: number
}

// ==================== 同步协议类型 ====================

export interface BloomHandshakeRequest {
  client_id: string
  bloom_filter_bits: string // Base64编码的Bloom过滤器
  capabilities: string[]
  compression: string[] // 支持的压缩算法
  protocol_version: string
}

export interface BloomHandshakeResponse {
  session_id: string
  missing_cids: string[] // 服务端缺少的CID列表
  server_capabilities: string[]
  preferred_compression: string
  chunk_size: number
  protocol_version: string
  session_expires_at: string
}

export interface EntryDelta {
  entry_uid: string
  operation: 'create' | 'update' | 'delete'
  uida_keys_b64: string
  uida_sha256_hex: string
  key?: string
  src_text?: string
  dst_text?: string
  status?: V6TranslationStatus
  language_file_uid?: string
  timestamp: string
}

export interface SyncSession {
  session_id: string
  client_id: string
  status: 'active' | 'committing' | 'committed' | 'aborted'
  total_chunks: number
  uploaded_chunks: number
  conflicts: number
  progress: number
  created_at: string
  expires_at: string
  committed_at?: string
}

// ==================== 查询和分页类型 ====================

export interface V6QueryParams {
  page?: number
  limit?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  filters?: Record<string, any>
  search?: string
  locale?: string
  status?: string
}

export interface V6PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

// ==================== 批量操作类型 ====================

export interface V6BatchUpdateRequest<T> {
  updates: Array<{
    uid: string
    data: Partial<T>
    version?: string // ETag版本控制
  }>
  idempotency_key?: string
}

export interface V6BatchUpdateResponse {
  updated_count: number
  failed_count: number
  conflicts: Array<{
    uid: string
    error: string
    current_version: string
  }>
}

// ==================== 导入导出类型 ====================

export interface V6ExportRequest {
  format: 'json' | 'ndjson' | 'csv' | 'xlsx'
  filters?: V6QueryParams
  include_metadata?: boolean
  compression?: 'none' | 'gzip' | 'zstd'
}

export interface V6ImportRequest {
  format: 'json' | 'ndjson' | 'csv' | 'xlsx'
  data: string | File
  merge_strategy?: 'overwrite' | 'merge' | 'skip_existing'
  validate_schema?: boolean
}

export interface V6ImportResult {
  imported_count: number
  skipped_count: number
  error_count: number
  errors: Array<{
    line: number
    message: string
    data?: any
  }>
}

// ==================== 配置类型 ====================

export interface V6Setting {
  key: string
  value: any
  type: 'string' | 'number' | 'boolean' | 'json'
  description?: string
  default_value?: any
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface V6MiddlewareConfig {
  enable_idempotency: boolean
  enable_ndjson: boolean
  enable_etag: boolean
  enable_compression: boolean
  idempotency_ttl: number
  compression_level: number
  min_compression_size: number
}

// ==================== QA规则类型 ====================

export interface V6QAIssue {
  rule_name: string
  severity: 'error' | 'warning' | 'info'
  message: string
  suggestion?: string
  location?: {
    field: string
    position?: number
  }
}

export interface V6QAReport {
  entry_uid: string
  issues: V6QAIssue[]
  overall_score: number
  passed_rules: string[]
  failed_rules: string[]
  timestamp: string
}

// ==================== 错误类型 ====================

export interface V6ApiError {
  code: string
  message: string
  details?: Record<string, any>
  trace_id?: string
  timestamp: string
}

export interface V6ConflictError extends V6ApiError {
  current_version: string
  provided_version: string
  conflicting_fields: string[]
}

// ==================== 事件类型 ====================

export interface V6SystemEvent {
  event_id: string
  event_type: string
  entity_type?: string
  entity_uid?: string
  payload: Record<string, any>
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical'
  timestamp: string
}

// ==================== 工具类型 ====================

export type V6EntityUID = string
export type V6Timestamp = string
export type V6Hash = string
export type V6Base64 = string

// 响应包装类型
export interface V6Response<T = any> {
  success: boolean
  data?: T
  error?: V6ApiError
  metadata?: {
    request_id: string
    response_time_ms: number
    cache_hit?: boolean
    version?: string
  }
}

// 工具函数类型
export type V6EntityFactory<T> = (data: Partial<T>) => T
export type V6EntityValidator<T> = (entity: T) => V6QAIssue[]
export type V6EntityTransformer<T, U> = (input: T) => U