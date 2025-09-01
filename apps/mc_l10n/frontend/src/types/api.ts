/**
 * API 类型定义
 * 与后端 FastAPI 接口保持一致
 */

// ==================== 通用响应类型 ====================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  request_id?: string;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  request_id?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ==================== 项目管理类型 ====================

export interface Project {
  id: string;
  name: string;
  description?: string;
  source_path: string;
  output_path: string;
  supported_languages: string[];
  default_language: string;
  project_type: 'mod' | 'resource_pack' | 'mixed';
  metadata?: Record<string, any>;
  status: 'active' | 'archived' | 'paused';
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  source_path: string;
  output_path?: string;
  supported_languages?: string[];
  default_language?: string;
  project_type?: 'mod' | 'resource_pack' | 'mixed';
  metadata?: Record<string, any>;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  source_path?: string;
  output_path?: string;
  supported_languages?: string[];
  default_language?: string;
  project_type?: 'mod' | 'resource_pack' | 'mixed';
  metadata?: Record<string, any>;
  status?: 'active' | 'archived' | 'paused';
}

export interface ProjectSearchParams {
  q?: string;
  project_type?: string;
  status?: string;
  language?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ProjectStatistics {
  total_projects: number;
  active_projects: number;
  total_entries: number;
  translated_entries: number;
  translation_progress: number;
  supported_languages: string[];
}

// ==================== 模组管理类型 ====================

export interface ModFile {
  id: string;
  project_id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  file_type: 'jar' | 'folder';
  mod_loader?: 'forge' | 'fabric' | 'quilt' | 'neoforge';
  mod_version?: string;
  minecraft_version?: string;
  language_files: LanguageFile[];
  dependencies?: string[];
  metadata?: Record<string, any>;
  scan_status: 'pending' | 'scanning' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface LanguageFile {
  id: string;
  mod_file_id: string;
  file_path: string;
  language_code: string;
  format: 'json' | 'properties';
  entry_count: number;
  last_modified?: string;
  size_bytes?: number;
  encoding?: string;
}

export interface ScanModRequest {
  file_path: string;
  recursive?: boolean;
  include_patterns?: string[];
  exclude_patterns?: string[];
  deep_scan?: boolean;
}

export interface ModSearchParams {
  q?: string;
  project_id?: string;
  file_type?: 'jar' | 'folder';
  mod_loader?: string;
  minecraft_version?: string;
  scan_status?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ModStatistics {
  total_mods: number;
  total_language_files: number;
  by_loader: Record<string, number>;
  by_minecraft_version: Record<string, number>;
  by_status: Record<string, number>;
}

// ==================== 翻译管理类型 ====================

export interface TranslationEntry {
  id: string;
  project_id: string;
  mod_file_id?: string;
  language_file_id?: string;
  entry_key: string;
  source_text: string;
  translated_text?: string;
  language_code: string;
  context?: string;
  comment?: string;
  status: 'untranslated' | 'translated' | 'reviewed' | 'approved' | 'needs_update';
  translator_id?: string;
  reviewer_id?: string;
  created_at: string;
  updated_at: string;
}

export interface BatchTranslateRequest {
  entry_ids: string[];
  translations: Record<string, string>;
  language_code: string;
  status?: 'translated' | 'reviewed' | 'approved';
}

export interface TranslationSearchParams {
  q?: string;
  project_id?: string;
  mod_file_id?: string;
  language_code?: string;
  status?: string;
  entry_key?: string;
  has_translation?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface TranslationStatistics {
  total_entries: number;
  translated_entries: number;
  untranslated_entries: number;
  needs_update_entries: number;
  translation_progress: number;
  by_language: Record<string, {
    total: number;
    translated: number;
    progress: number;
  }>;
  by_status: Record<string, number>;
}

export interface ExportRequest {
  project_id?: string;
  language_codes?: string[];
  format: 'json' | 'properties' | 'csv' | 'xlsx';
  include_untranslated?: boolean;
  include_metadata?: boolean;
  output_path?: string;
}

export interface ImportRequest {
  project_id: string;
  file_path: string;
  format: 'json' | 'properties' | 'csv' | 'xlsx';
  language_code: string;
  merge_strategy: 'overwrite' | 'merge' | 'skip_existing';
  validate_keys?: boolean;
}

// ==================== 搜索和过滤类型 ====================

export interface SearchParams {
  q?: string;
  filters?: Record<string, any>;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface SearchResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  search_time_ms: number;
  suggestion?: string;
}

// ==================== 异步任务类型 ====================

export interface AsyncTask {
  id: string;
  task_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  message?: string;
  result?: any;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

// ==================== 系统信息类型 ====================

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface SystemInfo {
  service: {
    name: string;
    version: string;
    environment: string;
    debug_mode: boolean;
  };
  system: {
    platform: string;
    python_version: string;
  };
  api: {
    total_routes: number;
    cors_enabled: boolean;
    error_handling: boolean;
    request_logging: boolean;
  };
}