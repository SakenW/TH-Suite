/**
 * V6 API客户端服务
 * 
 * 提供V6架构的完整API访问能力，包括：
 * - 实体管理（Pack、MOD、语言文件、翻译条目）
 * - 同步协议支持（Bloom握手、Entry-Delta处理）
 * - 工作队列管理
 * - 缓存和性能优化
 * - 中间件支持（NDJSON、幂等性、ETag、压缩）
 */

import { BaseApiService } from '../baseApiService'
import { ApiResponse } from '../../types/api'

// ==================== 类型定义 ====================

// 实体类型
export interface V6Pack {
  uid: string
  name: string
  description?: string
  version?: string
  pack_type: 'integration' | 'resource' | 'data'
  created_at: string
  updated_at: string
}

export interface V6Mod {
  uid: string
  mod_id: string
  display_name: string
  version?: string
  mod_loader?: string
  file_path: string
  file_type: 'jar' | 'directory'
  file_hash?: string
  created_at: string
  updated_at: string
}

export interface V6LanguageFile {
  uid: string
  mod_uid: string
  locale: string
  file_path: string
  format: 'json' | 'properties' | 'yaml'
  entry_count: number
  file_hash?: string
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
  status: 'new' | 'reviewing' | 'reviewed' | 'approved' | 'rejected'
  language_file_uid: string
  created_at: string
  updated_at: string
}

// 统计类型
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
}

export interface V6HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy'
  database: {
    connection: boolean
    tables: number
    indexes: number
  }
  queue: {
    active_tasks: number
    pending_tasks: number
    failed_tasks: number
  }
  cache: {
    l1_size: number
    l1_hit_rate: number
    memory_usage_mb: number
  }
  last_check: string
}

// 队列类型
export interface V6WorkItem {
  uid: string
  idempotency_key: string
  task_type: string
  status: 'pending' | 'leased' | 'completed' | 'failed'
  payload: any
  lease_expires_at?: string
  created_at: string
  updated_at: string
}

// 同步协议类型
export interface BloomHandshakeRequest {
  client_id: string
  bloom_filter_bits: string
  capabilities: string[]
  compression: string[]
}

export interface BloomHandshakeResponse {
  session_id: string
  missing_cids: string[]
  server_capabilities: string[]
  preferred_compression: string
  chunk_size: number
}

// 查询参数类型
export interface V6QueryParams {
  page?: number
  limit?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  filters?: Record<string, any>
}

// ==================== V6 API客户端类 ====================

export class V6ApiClient extends BaseApiService {
  private readonly v6Prefix = '/api/v6'
  
  constructor() {
    super()
    
    // 添加V6专用中间件支持
    this.addInterceptor({
      onRequest: async (config) => {
        // 添加幂等性支持
        if (config.method && ['POST', 'PUT', 'PATCH'].includes(config.method)) {
          if (!config.headers!['X-Idempotency-Key']) {
            config.headers!['X-Idempotency-Key'] = this.generateIdempotencyKey()
          }
        }
        
        // 添加ETag支持
        if (config.headers && config.headers['If-Match']) {
          // ETag条件请求已设置
        }
        
        return config
      }
    })
  }

  // ==================== 实体管理API ====================

  /**
   * 获取Pack列表
   */
  async getPacks(params?: V6QueryParams): Promise<ApiResponse<{ packs: V6Pack[], total: number }>> {
    return this.get(`${this.v6Prefix}/packs`, params)
  }

  /**
   * 获取Pack详情
   */
  async getPack(uid: string): Promise<ApiResponse<V6Pack>> {
    return this.get(`${this.v6Prefix}/packs/${uid}`)
  }

  /**
   * 创建Pack
   */
  async createPack(pack: Omit<V6Pack, 'uid' | 'created_at' | 'updated_at'>): Promise<ApiResponse<V6Pack>> {
    return this.post(`${this.v6Prefix}/packs`, pack)
  }

  /**
   * 获取MOD列表
   */
  async getMods(params?: V6QueryParams): Promise<ApiResponse<{ mods: V6Mod[], total: number }>> {
    return this.get(`${this.v6Prefix}/mods`, params)
  }

  /**
   * 获取MOD详情
   */
  async getMod(uid: string): Promise<ApiResponse<V6Mod>> {
    return this.get(`${this.v6Prefix}/mods/${uid}`)
  }

  /**
   * 获取MOD兼容性信息
   */
  async getModCompatibility(uid: string): Promise<ApiResponse<{ compatibility_matrix: any }>> {
    return this.get(`${this.v6Prefix}/mods/${uid}/compatibility`)
  }

  /**
   * 获取语言文件列表
   */
  async getLanguageFiles(params?: V6QueryParams): Promise<ApiResponse<{ language_files: V6LanguageFile[], total: number }>> {
    return this.get(`${this.v6Prefix}/language-files`, params)
  }

  /**
   * 获取可用语言区域列表
   */
  async getAvailableLocales(): Promise<ApiResponse<{ locales: string[] }>> {
    return this.get(`${this.v6Prefix}/language-files/locales`)
  }

  /**
   * 获取翻译条目列表
   */
  async getTranslations(params?: V6QueryParams): Promise<ApiResponse<{ translations: V6TranslationEntry[], total: number }>> {
    return this.get(`${this.v6Prefix}/translations`, params)
  }

  /**
   * 批量更新翻译条目
   */
  async batchUpdateTranslations(updates: Partial<V6TranslationEntry>[]): Promise<ApiResponse<{ updated_count: number }>> {
    return this.post(`${this.v6Prefix}/translations/batch`, { updates })
  }

  /**
   * 导出翻译为NDJSON格式
   */
  async exportTranslationsNDJSON(params?: { locale?: string, format?: string }): Promise<ApiResponse<string>> {
    return this.get(`${this.v6Prefix}/translations/export/ndjson`, params)
  }

  // ==================== 统计和监控API ====================

  /**
   * 获取数据库统计信息
   */
  async getDatabaseStatistics(): Promise<ApiResponse<V6DatabaseStatistics>> {
    return this.get(`${this.v6Prefix}/database/statistics`)
  }

  /**
   * 获取数据库健康检查
   */
  async getDatabaseHealth(): Promise<ApiResponse<V6HealthCheck>> {
    return this.get(`${this.v6Prefix}/database/health`)
  }

  /**
   * 获取缓存状态
   */
  async getCacheStatus(): Promise<ApiResponse<{ cache_stats: any, performance_metrics: any }>> {
    return this.get(`${this.v6Prefix}/cache/status`)
  }

  /**
   * 获取队列状态
   */
  async getQueueStatus(): Promise<ApiResponse<{ active_tasks: number, pending_tasks: number, failed_tasks: number }>> {
    return this.get(`${this.v6Prefix}/queue/status`)
  }

  // ==================== 队列管理API ====================

  /**
   * 获取队列任务列表
   */
  async getQueueTasks(params?: V6QueryParams): Promise<ApiResponse<{ tasks: V6WorkItem[], total: number }>> {
    return this.get(`${this.v6Prefix}/queue/tasks`, params)
  }

  /**
   * 创建队列任务
   */
  async createQueueTask(task: { task_type: string, payload: any, idempotency_key?: string }): Promise<ApiResponse<V6WorkItem>> {
    return this.post(`${this.v6Prefix}/queue/tasks`, task)
  }

  /**
   * 租用队列任务
   */
  async leaseQueueTask(taskId: string, leaseDuration?: number): Promise<ApiResponse<{ leased: boolean, lease_expires_at: string }>> {
    return this.post(`${this.v6Prefix}/queue/tasks/${taskId}/lease`, { lease_duration: leaseDuration })
  }

  // ==================== 缓存管理API ====================

  /**
   * 清理缓存
   */
  async cleanupCache(): Promise<ApiResponse<{ cleaned_entries: number, reclaimed_memory_mb: number }>> {
    return this.post(`${this.v6Prefix}/cache/cleanup`)
  }

  /**
   * 缓存预热
   */
  async warmupCache(targets?: string[]): Promise<ApiResponse<{ warmed_entries: number, estimated_time_ms: number }>> {
    return this.post(`${this.v6Prefix}/cache/warmup`, { targets })
  }

  // ==================== 配置管理API ====================

  /**
   * 获取配置项列表
   */
  async getSettings(): Promise<ApiResponse<{ settings: Record<string, any> }>> {
    return this.get(`${this.v6Prefix}/settings`)
  }

  /**
   * 更新配置项
   */
  async updateSetting(key: string, value: any): Promise<ApiResponse<{ updated: boolean }>> {
    return this.put(`${this.v6Prefix}/settings/${key}`, { value })
  }

  /**
   * 批量更新配置
   */
  async batchUpdateSettings(settings: Record<string, any>): Promise<ApiResponse<{ updated_count: number }>> {
    return this.post(`${this.v6Prefix}/settings/batch`, { settings })
  }

  /**
   * 重置配置为默认值
   */
  async resetSettings(): Promise<ApiResponse<{ reset_count: number }>> {
    return this.post(`${this.v6Prefix}/settings/reset`)
  }

  // ==================== 同步协议API ====================

  /**
   * Bloom握手协商
   */
  async bloomHandshake(request: BloomHandshakeRequest): Promise<ApiResponse<BloomHandshakeResponse>> {
    return this.post(`${this.v6Prefix}/sync/handshake`, request)
  }

  /**
   * 上传Entry-Delta分片
   */
  async uploadChunk(cid: string, chunk: Blob, offset?: number): Promise<ApiResponse<{ uploaded: boolean, next_offset?: number }>> {
    const formData = new FormData()
    formData.append('chunk', chunk)
    if (offset !== undefined) {
      formData.append('offset', offset.toString())
    }
    
    return this.postFormData(`${this.v6Prefix}/sync/chunk/${cid}`, formData)
  }

  /**
   * 提交同步会话
   */
  async commitSyncSession(sessionId: string, summary?: any): Promise<ApiResponse<{ committed: boolean, conflicts?: any[] }>> {
    return this.post(`${this.v6Prefix}/sync/commit`, { session_id: sessionId, summary })
  }

  /**
   * 获取同步会话状态
   */
  async getSyncSessionStatus(sessionId: string): Promise<ApiResponse<{ status: string, progress: number, conflicts?: any[] }>> {
    return this.get(`${this.v6Prefix}/sync/session/${sessionId}/status`)
  }

  // ==================== V6特有功能 ====================

  /**
   * 获取V6 API信息
   */
  async getV6ApiInfo(): Promise<ApiResponse<{ name: string, version: string, features: string[], endpoints: Record<string, string> }>> {
    return this.get(`${this.v6Prefix}/`)
  }

  /**
   * V6健康检查
   */
  async getV6Health(): Promise<ApiResponse<{ status: string, version: string, components: Record<string, string> }>> {
    return this.get(`${this.v6Prefix}/health`)
  }

  /**
   * 启用流式NDJSON处理
   */
  async enableNDJSONStreaming(): Promise<void> {
    this.addInterceptor({
      onRequest: async (config) => {
        // 为支持NDJSON的端点添加Accept头
        if (config.url?.includes('/export/ndjson') || config.headers?.['Accept']?.includes('application/x-ndjson')) {
          config.headers!['Accept'] = 'application/x-ndjson'
        }
        return config
      }
    })
  }

  // ==================== 工具方法 ====================

  /**
   * 生成幂等性键
   */
  private generateIdempotencyKey(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2)}`
  }

  /**
   * 设置ETag条件请求
   */
  setETagHeader(etag: string): void {
    this.addInterceptor({
      onRequest: async (config) => {
        config.headers!['If-Match'] = etag
        return config
      }
    })
  }

  /**
   * 启用压缩支持
   */
  enableCompression(): void {
    this.addInterceptor({
      onRequest: async (config) => {
        config.headers!['Accept-Encoding'] = 'zstd, gzip, deflate'
        return config
      }
    })
  }
}

// ==================== 导出 ====================

// 创建单例实例
export const v6ApiClient = new V6ApiClient()

// 导出类和实例
export default V6ApiClient