/**
 * 领域服务类型定义
 * 与后端的 DTO 和 Command/Query 模型保持一致
 */

import { ServiceResult, ServiceError } from '../container/types'

// === 通用类型 ===

export interface PaginationParams {
  page: number
  page_size: number
}

export interface SortParams {
  sort_field: string
  sort_direction: 'asc' | 'desc'
}

export interface FilterParams {
  search_text?: string
  [key: string]: any
}

export interface ListOptions
  extends Partial<PaginationParams>,
    Partial<SortParams>,
    Partial<FilterParams> {
  include_archived?: boolean
  include_statistics?: boolean
}

// === 项目相关类型 ===

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

export interface Project {
  project_id: string
  name: string
  description: string
  mc_version: string
  target_language: string
  source_path: string
  output_path: string
  created_at: Date
  updated_at?: Date
  is_archived: boolean
  archive_reason?: string
  statistics?: ProjectStatistics
}

export interface ProjectStatistics {
  project_id: string
  generated_at: Date
  translation_progress?: any
  file_statistics?: any
  mod_statistics?: any
}

export interface ProjectListOptions extends ListOptions {
  mc_version_filter?: string
  language_filter?: string
}

// === 模组相关类型 ===

export interface Mod {
  mod_id: string
  name: string
  version: string
  description?: string
  authors?: string[]
  file_path: string
  file_size: number
  language_files: LanguageFile[]
  metadata?: any
}

export interface LanguageFile {
  file_path: string
  locale: string
  key_count: number
  namespace: string
  content?: Record<string, string>
}

export interface ModSearchOptions extends ListOptions {
  name_filter?: string
  version_filter?: string
  author_filter?: string
  has_language_files?: boolean
}

// === 扫描相关类型 ===

export interface ScanRequest {
  directory: string
  incremental?: boolean
  scan_options?: ScanOptions
}

export interface ScanOptions {
  include_subdirectories?: boolean
  file_extensions?: string[]
  exclude_patterns?: string[]
  max_file_size?: number
}

export interface ScanStatus {
  scan_id: string
  status: 'pending' | 'scanning' | 'completed' | 'failed' | 'cancelled'
  progress: number
  total_files: number
  processed_files: number
  current_file?: string
  total_mods: number
  total_language_files: number
  total_keys: number
  scan_mode: '增量' | '全量'
  started_at: Date
  completed_at?: Date
  error?: string
  // 新增的详细进度信息
  scan_phase?: 'discovering' | 'processing' | 'finalizing'
  phase_text?: string
  current_batch?: number
  total_batches?: number
  batch_progress?: number
  files_per_second?: number
  estimated_remaining_seconds?: number
  elapsed_seconds?: number
}

export interface ScanResult {
  scan_id: string
  mods: Mod[]
  language_files: LanguageFile[]
  statistics: {
    total_mods: number
    total_language_files: number
    total_keys: number
    scan_duration_ms: number
  }
}

// === 翻译相关类型 ===

export interface TranslationEntry {
  key: string
  source_text: string
  translated_text?: string
  context?: string
  namespace: string
  mod_id: string
  locale: string
  status: 'pending' | 'translated' | 'reviewed' | 'approved'
  metadata?: any
}

export interface TranslationExportOptions {
  project_id: string
  format: 'json' | 'lang' | 'csv' | 'xlsx' | 'po'
  include_untranslated?: boolean
  locale?: string
  namespaces?: string[]
  output_path?: string
}

export interface TranslationImportOptions {
  project_id: string
  file_path: string
  format: 'json' | 'lang' | 'csv' | 'xlsx' | 'po'
  locale: string
  overwrite_existing?: boolean
  validate_keys?: boolean
}

// === 服务接口定义 ===

export interface ProjectServiceInterface {
  create(request: ProjectCreateRequest): Promise<ServiceResult<{ project_id: string }>>
  update(projectId: string, request: ProjectUpdateRequest): Promise<ServiceResult<boolean>>
  delete(projectId: string, force?: boolean): Promise<ServiceResult<boolean>>
  archive(projectId: string, reason?: string): Promise<ServiceResult<boolean>>
  getById(projectId: string, includeStatistics?: boolean): Promise<ServiceResult<Project>>
  list(
    options?: ProjectListOptions,
  ): Promise<ServiceResult<{ projects: Project[]; pagination: any }>>
  search(
    query: string,
    options?: ListOptions,
  ): Promise<ServiceResult<{ projects: Project[]; pagination: any }>>
  getStatistics(projectId: string): Promise<ServiceResult<ProjectStatistics>>
}

export interface ScanServiceInterface {
  startScan(request: ScanRequest): Promise<ServiceResult<{ scan_id: string }>>
  getStatus(scanId: string): Promise<ServiceResult<ScanStatus>>
  getResults(scanId: string): Promise<ServiceResult<ScanResult>>
  cancelScan(scanId: string): Promise<ServiceResult<boolean>>
  listScans(options?: ListOptions): Promise<ServiceResult<{ scans: ScanStatus[]; pagination: any }>>
}

export interface ModServiceInterface {
  search(options: ModSearchOptions): Promise<ServiceResult<{ mods: Mod[]; pagination: any }>>
  getById(modId: string): Promise<ServiceResult<Mod>>
  getLanguageFiles(modId: string): Promise<ServiceResult<LanguageFile[]>>
  extractLanguageContent(
    modId: string,
    locale: string,
  ): Promise<ServiceResult<Record<string, string>>>
}

export interface TranslationServiceInterface {
  export(options: TranslationExportOptions): Promise<ServiceResult<{ file_path: string }>>
  import(options: TranslationImportOptions): Promise<ServiceResult<{ imported_count: number }>>
  getEntries(
    projectId: string,
    filters?: any,
  ): Promise<ServiceResult<{ entries: TranslationEntry[]; pagination: any }>>
  updateEntry(entryId: string, translatedText: string): Promise<ServiceResult<boolean>>
  batchUpdate(
    updates: Array<{ entryId: string; translatedText: string }>,
  ): Promise<ServiceResult<{ updated_count: number }>>
}
