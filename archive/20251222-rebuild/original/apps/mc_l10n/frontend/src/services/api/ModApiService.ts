/**
 * 模组 API 服务
 * 处理模组的管理和语言文件相关操作
 */

import { BaseApiClient } from './BaseApiClient'
import { 
  ModInfo, 
  LanguageFileInfo,
  PaginatedResponse,
  RequestConfig 
} from './types'

export class ModApiService {
  constructor(private client: BaseApiClient) {}

  /**
   * 获取模组列表
   */
  async getModList(options?: {
    page?: number
    limit?: number
    search?: string
    platform?: string
    has_language_files?: boolean
  }, config?: RequestConfig): Promise<PaginatedResponse<ModInfo>> {
    const params = new URLSearchParams()
    
    if (options?.page) params.append('page', options.page.toString())
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.search) params.append('search', options.search)
    if (options?.platform) params.append('platform', options.platform)
    if (options?.has_language_files !== undefined) {
      params.append('has_language_files', options.has_language_files.toString())
    }

    const url = `/api/v6/mods${params.toString() ? '?' + params.toString() : ''}`
    const response = await this.client.get(url, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取模组列表失败')
    }

    return response.data
  }

  /**
   * 获取模组详情
   */
  async getModById(modId: string, config?: RequestConfig): Promise<ModInfo> {
    const response = await this.client.get(`/api/v6/mods/${modId}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取模组详情失败')
    }

    return response.data
  }

  /**
   * 更新模组信息
   */
  async updateMod(modId: string, updates: Partial<{
    name: string
    version: string
    platform: string
  }>, config?: RequestConfig): Promise<ModInfo> {
    const response = await this.client.put(`/api/v6/mods/${modId}`, updates, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '更新模组失败')
    }

    return response.data
  }

  /**
   * 删除模组
   */
  async deleteMod(modId: string, config?: RequestConfig): Promise<void> {
    const response = await this.client.delete(`/api/v6/mods/${modId}`, config)
    
    if (!response.success) {
      throw new Error(response.message || '删除模组失败')
    }
  }

  /**
   * 获取模组的语言文件列表
   */
  async getModLanguageFiles(modId: string, options?: {
    locale?: string
    format?: string
  }, config?: RequestConfig): Promise<LanguageFileInfo[]> {
    const params = new URLSearchParams()
    
    if (options?.locale) params.append('locale', options.locale)
    if (options?.format) params.append('format', options.format)

    const url = `/api/v6/mods/${modId}/language-files${params.toString() ? '?' + params.toString() : ''}`
    const response = await this.client.get(url, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取语言文件失败')
    }

    return response.data
  }

  /**
   * 获取语言文件详情
   */
  async getLanguageFileById(fileId: string, config?: RequestConfig): Promise<LanguageFileInfo> {
    const response = await this.client.get(`/api/v6/language-files/${fileId}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取语言文件详情失败')
    }

    return response.data
  }

  /**
   * 获取语言文件内容
   */
  async getLanguageFileContent(fileId: string, config?: RequestConfig): Promise<{
    content: Record<string, string>
    format: string
    encoding: string
  }> {
    const response = await this.client.get(`/api/v6/language-files/${fileId}/content`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取语言文件内容失败')
    }

    return response.data
  }

  /**
   * 搜索模组
   */
  async searchMods(query: string, options?: {
    platform?: string
    limit?: number
    include_language_files?: boolean
  }, config?: RequestConfig): Promise<ModInfo[]> {
    const params = new URLSearchParams()
    params.append('search', query)
    
    if (options?.platform) params.append('platform', options.platform)
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.include_language_files) params.append('include_language_files', 'true')

    const response = await this.client.get(`/api/v6/mods/search?${params.toString()}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '搜索模组失败')
    }

    return response.data
  }

  /**
   * 获取模组统计信息
   */
  async getModStats(modId: string, config?: RequestConfig): Promise<{
    total_language_files: number
    supported_locales: string[]
    total_keys: number
    translation_coverage: Record<string, number>
    last_updated: string
  }> {
    const response = await this.client.get(`/api/v6/mods/${modId}/stats`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取模组统计失败')
    }

    return response.data
  }

  /**
   * 重新扫描模组
   */
  async rescanMod(modId: string, config?: RequestConfig): Promise<{
    scan_id: string
    status: string
  }> {
    const response = await this.client.post(`/api/v6/mods/${modId}/rescan`, {}, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '重新扫描模组失败')
    }

    return response.data
  }

  /**
   * 批量操作模组
   */
  async batchUpdateMods(operations: Array<{
    mod_id: string
    operation: 'update' | 'delete' | 'rescan'
    data?: any
  }>, config?: RequestConfig): Promise<{
    success_count: number
    failed_count: number
    results: Array<{
      mod_id: string
      status: 'success' | 'failed'
      error?: string
    }>
  }> {
    const response = await this.client.post('/api/v6/mods/batch', { operations }, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '批量操作失败')
    }

    return response.data
  }

  /**
   * 获取模组依赖关系
   */
  async getModDependencies(modId: string, config?: RequestConfig): Promise<{
    dependencies: Array<{
      mod_id: string
      name: string
      version_requirement: string
      type: 'required' | 'optional' | 'incompatible'
    }>
    dependents: Array<{
      mod_id: string
      name: string
    }>
  }> {
    const response = await this.client.get(`/api/v6/mods/${modId}/dependencies`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取依赖关系失败')
    }

    return response.data
  }

  /**
   * 导出模组信息
   */
  async exportModInfo(modId: string, format?: 'json' | 'csv' | 'xml', config?: RequestConfig): Promise<Blob> {
    const params = format ? `?format=${format}` : ''
    const response = await this.client.get(`/api/v6/mods/${modId}/export${params}`, {
      ...config,
      // 注意：这里需要特殊处理二进制响应
    })
    
    // TODO: 处理 Blob 响应
    throw new Error('导出功能尚未实现')
  }

  /**
   * 验证模组文件
   */
  async validateModFile(modId: string, config?: RequestConfig): Promise<{
    is_valid: boolean
    file_exists: boolean
    hash_matches: boolean
    size_matches: boolean
    errors: string[]
    warnings: string[]
  }> {
    const response = await this.client.post(`/api/v6/mods/${modId}/validate`, {}, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '验证模组文件失败')
    }

    return response.data
  }
}

// 创建默认模组服务实例
import { apiClient } from './BaseApiClient'
export const modApi = new ModApiService(apiClient)