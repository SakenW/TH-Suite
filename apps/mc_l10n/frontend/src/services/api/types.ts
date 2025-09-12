/**
 * API 类型定义
 * 定义后端 API 的请求和响应类型
 * 与后端v2.1模型保持一致
 */

// ============================================================
// 通用类型
// ============================================================

// 通用 API 响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// API 错误类型
export interface ApiError {
  code: string
  message: string
  details?: any
}

// 请求配置类型
export interface RequestConfig {
  timeout?: number
  retries?: number
  signal?: AbortSignal
  params?: Record<string, any>
}

// 分页响应类型
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
  has_next?: boolean
  has_prev?: boolean
}

// 分页请求参数
export interface PaginationParams {
  page?: number
  limit?: number
  offset?: number
}

// 排序参数
export interface SortParams {
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// 过滤参数
export interface FilterParams {
  search?: string
  filters?: Record<string, any>
}

// ============================================================
// 项目相关类型 (与后端v2.1模型一致)
// ============================================================

export interface ProjectBase {
  project_id: string
  name: string
  description?: string
  created_at: string
  updated_at?: string
  is_archived: boolean
  archive_reason?: string
}

export interface Project extends ProjectBase {
  mc_version: string
  target_language: string
  source_path: string
  output_path: string
  statistics?: ProjectStatistics
}

export interface ProjectCreateRequest {
  name: string
  description?: string
  mc_version: string
  target_language: string
  source_path: string
  output_path: string
}

export interface ProjectUpdateRequest {
  name?: string
  description?: string
  mc_version?: string
  target_language?: string
  source_path?: string
  output_path?: string
}

export interface ProjectStatistics {
  project_id: string
  generated_at: string
  total_packs: number
  total_mods: number
  total_content_instances: number
  translation_progress?: {
    total_keys: number
    translated_keys: number
    reviewed_keys: number
    progress_percentage: number
  }
  file_statistics?: {
    total_files: number
    json_files: number
    lang_files: number
    other_files: number
  }
  mod_statistics?: {
    total_mods: number
    analyzed_mods: number
    pending_mods: number
    error_mods: number
  }
}

// ============================================================
// Pack相关类型
// ============================================================

export interface PackBase {
  pack_id: string
  pack_name: string
  pack_type: 'modpack' | 'resource_pack' | 'data_pack' | 'mixed'
  pack_path: string
  created_at: string
  updated_at?: string
}

export interface Pack extends PackBase {
  pack_version_id?: string
  version_name?: string
  mc_version?: string
  total_mods?: number
  total_content_instances?: number
  last_scanned_at?: string
}

export interface PackVersion {
  pack_version_id: string
  pack_id: string
  version_name: string
  mc_version: string
  version_path: string
  mod_loader: 'forge' | 'fabric' | 'quilt' | 'neoforge' | 'vanilla' | 'unknown'
  created_at: string
  updated_at?: string
  is_current: boolean
  statistics?: PackVersionStatistics
}

export interface PackVersionStatistics {
  pack_version_id: string
  generated_at: string
  total_mods: number
  total_content_instances: number
  total_namespaces: number
  total_keys: number
  file_count_by_type: Record<string, number>
  mod_distribution: Array<{
    mod_id: string
    mod_name: string
    content_count: number
    namespace_count: number
  }>
}

// ============================================================
// MOD相关类型
// ============================================================

export interface ModVersionInstance {
  mod_version_instance_id: string
  pack_version_id: string
  mod_id: string
  mod_name: string
  mod_version: string
  mod_file_path: string
  jar_hash: string
  extracted_path?: string
  mod_loader: string
  dependencies: string[]
  metadata: Record<string, any>
  created_at: string
  updated_at?: string
  content_stats?: {
    total_content_instances: number
    namespaces: string[]
    file_types: string[]
  }
}

// ============================================================
// 内容实例类型
// ============================================================

export interface ContentInstance {
  content_instance_id: string
  pack_version_id: string
  mod_version_instance_id?: string
  content_key: string
  namespace: string
  source_text: string
  context_info?: string
  file_path: string
  file_type: 'json' | 'lang' | 'properties' | 'yml' | 'yaml' | 'txt' | 'other'
  content_source: 'mod_jar' | 'resource_pack' | 'data_pack' | 'external_file'
  content_hash: string
  created_at: string
  updated_at?: string
  metadata?: Record<string, any>
}

export interface ContentSearchParams extends PaginationParams, SortParams, FilterParams {
  pack_version_id?: string
  mod_id?: string
  namespace?: string
  file_type?: string
  content_source?: string
  include_metadata?: boolean
}

// ============================================================
// 扫描相关类型 (更新版本)
// ============================================================

export interface ScanRequest {
  directory: string
  project_id?: string
  options?: ScanOptions
}

export interface ScanOptions {
  incremental?: boolean
  include_subdirectories?: boolean
  file_extensions?: string[]
  exclude_patterns?: string[]
  max_file_size?: number
  validate_after_scan?: boolean
  generate_statistics?: boolean
}

export interface ScanStatus {
  scan_id: string
  project_id?: string
  status: 'pending' | 'initializing' | 'scanning' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number // 0-100
  
  // 文件处理进度
  total_files: number
  processed_files: number
  current_file?: string
  
  // 发现的内容统计
  total_mods: number
  total_content_instances: number
  total_namespaces: number
  total_keys: number
  
  // 扫描阶段信息
  scan_phase?: 'discovering' | 'extracting' | 'parsing' | 'indexing' | 'finalizing'
  phase_text?: string
  
  // 时间信息
  started_at: string
  completed_at?: string
  estimated_completion?: string
  
  // 性能信息
  files_per_second?: number
  elapsed_seconds?: number
  remaining_seconds?: number
  
  // 错误和警告
  error?: string
  warnings: string[]
  
  // 详细统计
  detailed_stats?: {
    mod_loaders: Record<string, number>
    file_types: Record<string, number>
    namespaces: Record<string, number>
    errors_by_type: Record<string, number>
  }
}

export interface ScanResult {
  scan_id: string
  project_id?: string
  status: 'completed' | 'failed'
  
  // 扫描统计
  statistics: {
    total_mods: number
    total_content_instances: number
    total_namespaces: number
    total_keys: number
    scan_duration_ms: number
    files_processed: number
  }
  
  // 发现的内容
  discovered_content?: {
    packs: Pack[]
    pack_versions: PackVersion[]
    mod_instances: ModVersionInstance[]
    content_instances: ContentInstance[]
  }
  
  // 错误和警告
  errors: Array<{
    file_path: string
    error_type: string
    error_message: string
  }>
  warnings: Array<{
    file_path: string
    warning_type: string
    warning_message: string
  }>
  
  // 性能指标
  performance_metrics?: {
    avg_files_per_second: number
    peak_memory_usage_mb: number
    total_network_requests: number
    cache_hit_rate: number
  }
}

// ============================================================
// 翻译相关类型
// ============================================================

export interface Translation {
  translation_id: string
  content_instance_id: string
  target_language: string
  translated_text: string
  translation_source: 'manual' | 'auto' | 'imported'
  status: 'draft' | 'translated' | 'reviewed' | 'approved'
  confidence_score?: number
  translator_id?: string
  reviewer_id?: string
  created_at: string
  updated_at?: string
  metadata?: Record<string, any>
}

export interface TranslationExportRequest {
  project_id: string
  target_language: string
  format: 'json' | 'minecraft_lang' | 'properties' | 'csv' | 'xlsx'
  options?: {
    include_untranslated?: boolean
    include_metadata?: boolean
    namespaces?: string[]
    mods?: string[]
  }
}

export interface TranslationExportResult {
  export_id: string
  file_path?: string
  download_url?: string
  exported_count: number
  format: string
  created_at: string
  expires_at?: string
}

// ============================================================
// 任务和队列相关类型
// ============================================================

export interface TaskBase {
  task_id: string
  task_type: string
  project_id?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'normal' | 'high' | 'urgent'
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
}

export interface TaskQueue {
  pending_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  queue_size: number
  worker_count: number
  average_wait_time_ms: number
}

// ============================================================
// 实时状态和监控类型
// ============================================================

export interface ServerStatus {
  status: 'healthy' | 'degraded' | 'unavailable'
  uptime_seconds: number
  version: string
  last_heartbeat: string
  
  // 系统资源
  system_resources?: {
    cpu_usage_percent: number
    memory_usage_mb: number
    disk_usage_mb: number
    active_connections: number
  }
  
  // 服务状态
  services?: {
    database: 'healthy' | 'degraded' | 'unavailable'
    task_queue: 'healthy' | 'degraded' | 'unavailable'
    file_system: 'healthy' | 'degraded' | 'unavailable'
    trans_hub_sdk: 'available' | 'unavailable'
  }
}

export interface RealtimeUpdate {
  event_type: 'scan_progress' | 'sync_progress' | 'task_completed' | 'error_occurred'
  timestamp: string
  data: any
  target_id?: string // scan_id, task_id, etc.
}

// ============================================================
// WebSocket相关类型
// ============================================================

export interface WebSocketMessage {
  type: 'subscription' | 'update' | 'error' | 'ping' | 'pong'
  channel?: string
  data?: any
  error?: string
}

export interface WebSocketSubscription {
  channel: string
  filters?: Record<string, any>
}

// ============================================================
// 配置和设置类型
// ============================================================

export interface AppConfig {
  api_base_url: string
  websocket_url: string
  max_concurrent_requests: number
  request_timeout_ms: number
  enable_debug_logs: boolean
  
  // UI配置
  ui_settings?: {
    theme: 'light' | 'dark' | 'auto'
    language: string
    items_per_page: number
    auto_refresh_interval_ms: number
  }
  
  // 功能开关
  feature_flags?: {
    enable_real_time_sync: boolean
    enable_auto_translation: boolean
    enable_advanced_scanning: boolean
    enable_performance_monitoring: boolean
  }
}

// ============================================================
// 错误和日志类型
// ============================================================

export interface LogEntry {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  context?: Record<string, any>
  source?: string
}

export interface ErrorReport {
  error_id: string
  error_type: string
  error_message: string
  stack_trace?: string
  context: Record<string, any>
  occurred_at: string
  resolved: boolean
}

// ============================================================
// 导出所有类型
// ============================================================

// 重新导出常用类型的简化别名
export type {
  ApiResponse as APIResponse,
  ApiError as APIError,
  RequestConfig as APIConfig,
  PaginatedResponse as PagedResponse
}