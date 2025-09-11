/**
 * API 类型定义
 * 定义后端 API 的请求和响应类型
 */

// 通用 API 响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// 分页响应类型
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
}

// 扫描相关类型
export interface ScanRequest {
  directory: string
  incremental?: boolean
  project_id?: string
}

export interface ScanStatus {
  scan_id: string
  status: 'scanning' | 'completed' | 'failed' | 'cancelled'
  progress: number
  current_file?: string
  processed_files: number
  total_files: number
  started_at?: string
  statistics?: {
    total_mods: number
    total_language_files: number
    total_keys: number
  }
}

export interface ScanResult {
  scan_id: string
  status: 'completed' | 'failed'
  statistics: {
    total_mods: number
    total_language_files: number
    total_keys: number
    scan_duration_ms: number
  }
  mods: ModInfo[]
  language_files: LanguageFileInfo[]
  errors: string[]
  warnings: string[]
}

// 模组相关类型
export interface ModInfo {
  uid: string
  mod_id: string
  name: string
  version: string
  file_path: string
  hash: string
  size: number
  platform?: string
  created_at: string
  updated_at: string
}

// 语言文件相关类型
export interface LanguageFileInfo {
  uid: string
  mod_uid: string
  file_path: string
  locale: string
  format: 'json' | 'properties' | 'lang'
  content_hash: string
  key_count: number
  created_at: string
  updated_at: string
}

// 整合包相关类型
export interface PackInfo {
  uid: string
  platform: 'modrinth' | 'curseforge' | 'custom'
  slug: string
  title: string
  author?: string
  homepage?: string
  created_at: string
  updated_at: string
}

export interface PackCreateRequest {
  platform: 'modrinth' | 'curseforge' | 'custom'
  slug: string
  title: string
  author?: string
  homepage?: string
}

export interface PackVersion {
  uid: string
  pack_uid: string
  mc_version: string
  loader: 'forge' | 'neoforge' | 'fabric' | 'quilt' | 'multi' | 'unknown'
  manifest_json: Record<string, any>
  created_at: string
  updated_at: string
}

export interface PackInstallation {
  uid: string
  pack_version_uid: string
  root_path?: string
  launcher?: 'curseforge' | 'modrinth' | 'vanilla' | 'custom'
  enabled: boolean
  created_at: string
  updated_at: string
}

// 翻译相关类型
export interface Translation {
  uid: string
  source_key: string
  source_text: string
  target_text?: string
  locale: string
  status: 'pending' | 'translated' | 'reviewed' | 'approved'
  confidence?: number
  translator?: string
  reviewer?: string
  created_at: string
  updated_at: string
}

// 统计信息类型
export interface DatabaseStats {
  total_mods: number
  total_packs: number
  total_language_files: number
  total_translations: number
  total_keys: number
  last_scan_time?: string
  last_sync_time?: string
}

// 队列任务类型
export interface QueueTask {
  uid: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  priority: number
  progress: number
  payload: Record<string, any>
  result?: Record<string, any>
  error?: string
  created_at: string
  updated_at: string
}

// 错误类型
export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
}

// 请求配置类型
export interface RequestConfig {
  timeout?: number
  retries?: number
  signal?: AbortSignal
}

// 实时状态类型
export interface RealtimeStatus {
  is_online: boolean
  active_scans: number
  pending_tasks: number
  last_activity: string
}