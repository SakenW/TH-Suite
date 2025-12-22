/**
 * 整合包 API 服务
 * 处理整合包的 CRUD 操作和版本管理
 */

import { BaseApiClient } from './BaseApiClient'
import { 
  PackInfo, 
  PackCreateRequest, 
  PackVersion, 
  PackInstallation,
  PaginatedResponse,
  RequestConfig 
} from './types'

export class PackApiService {
  constructor(private client: BaseApiClient) {}

  /**
   * 创建整合包
   */
  async createPack(request: PackCreateRequest, config?: RequestConfig): Promise<PackInfo> {
    const response = await this.client.post('/api/v6/packs', request, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '创建整合包失败')
    }

    return response.data
  }

  /**
   * 获取整合包列表
   */
  async getPackList(options?: {
    page?: number
    limit?: number
    platform?: string
    search?: string
  }, config?: RequestConfig): Promise<PaginatedResponse<PackInfo>> {
    const params = new URLSearchParams()
    
    if (options?.page) params.append('page', options.page.toString())
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.platform) params.append('platform', options.platform)
    if (options?.search) params.append('search', options.search)

    const url = `/api/v6/packs${params.toString() ? '?' + params.toString() : ''}`
    const response = await this.client.get(url, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取整合包列表失败')
    }

    return response.data
  }

  /**
   * 获取整合包详情
   */
  async getPackById(packId: string, config?: RequestConfig): Promise<PackInfo> {
    const response = await this.client.get(`/api/v6/packs/${packId}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取整合包详情失败')
    }

    return response.data
  }

  /**
   * 更新整合包
   */
  async updatePack(packId: string, updates: Partial<PackCreateRequest>, config?: RequestConfig): Promise<PackInfo> {
    const response = await this.client.put(`/api/v6/packs/${packId}`, updates, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '更新整合包失败')
    }

    return response.data
  }

  /**
   * 删除整合包
   */
  async deletePack(packId: string, config?: RequestConfig): Promise<void> {
    const response = await this.client.delete(`/api/v6/packs/${packId}`, config)
    
    if (!response.success) {
      throw new Error(response.message || '删除整合包失败')
    }
  }

  /**
   * 获取整合包版本列表
   */
  async getPackVersions(packId: string, config?: RequestConfig): Promise<PackVersion[]> {
    const response = await this.client.get(`/api/v6/packs/${packId}/versions`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取整合包版本失败')
    }

    return response.data
  }

  /**
   * 创建整合包版本
   */
  async createPackVersion(version: {
    pack_uid: string
    mc_version: string
    loader: string
    manifest_json: Record<string, any>
  }, config?: RequestConfig): Promise<PackVersion> {
    const response = await this.client.post('/api/v6/packs/versions', version, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '创建整合包版本失败')
    }

    return response.data
  }

  /**
   * 获取整合包安装信息
   */
  async getPackInstallations(packVersionId: string, config?: RequestConfig): Promise<PackInstallation[]> {
    const response = await this.client.get(`/api/v6/packs/versions/${packVersionId}/installations`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取安装信息失败')
    }

    return response.data
  }

  /**
   * 创建整合包安装
   */
  async createPackInstallation(installation: {
    pack_version_uid: string
    root_path?: string
    launcher?: string
    enabled?: boolean
  }, config?: RequestConfig): Promise<PackInstallation> {
    const response = await this.client.post('/api/v6/packs/installations', installation, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '创建安装记录失败')
    }

    return response.data
  }

  /**
   * 更新安装状态
   */
  async updateInstallation(installationId: string, updates: {
    enabled?: boolean
    root_path?: string
  }, config?: RequestConfig): Promise<PackInstallation> {
    const response = await this.client.put(`/api/v6/packs/installations/${installationId}`, updates, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '更新安装状态失败')
    }

    return response.data
  }

  /**
   * 删除安装记录
   */
  async deleteInstallation(installationId: string, config?: RequestConfig): Promise<void> {
    const response = await this.client.delete(`/api/v6/packs/installations/${installationId}`, config)
    
    if (!response.success) {
      throw new Error(response.message || '删除安装记录失败')
    }
  }

  /**
   * 搜索整合包
   */
  async searchPacks(query: string, options?: {
    platform?: string
    limit?: number
  }, config?: RequestConfig): Promise<PackInfo[]> {
    const params = new URLSearchParams()
    params.append('search', query)
    
    if (options?.platform) params.append('platform', options.platform)
    if (options?.limit) params.append('limit', options.limit.toString())

    const response = await this.client.get(`/api/v6/packs/search?${params.toString()}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '搜索整合包失败')
    }

    return response.data
  }

  /**
   * 获取整合包统计信息
   */
  async getPackStats(packId: string, config?: RequestConfig): Promise<{
    total_versions: number
    total_installations: number
    total_mods: number
    last_updated: string
  }> {
    const response = await this.client.get(`/api/v6/packs/${packId}/stats`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取统计信息失败')
    }

    return response.data
  }

  /**
   * 导入整合包清单
   */
  async importManifest(manifest: Record<string, any>, options?: {
    platform?: string
    auto_create_pack?: boolean
  }, config?: RequestConfig): Promise<{
    pack: PackInfo
    version: PackVersion
    imported_mods: number
  }> {
    const response = await this.client.post('/api/v6/packs/import', {
      manifest,
      ...options
    }, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '导入清单失败')
    }

    return response.data
  }

  /**
   * 导出整合包清单
   */
  async exportManifest(packVersionId: string, format?: 'curseforge' | 'modrinth' | 'multimc', config?: RequestConfig): Promise<Record<string, any>> {
    const params = format ? `?format=${format}` : ''
    const response = await this.client.get(`/api/v6/packs/versions/${packVersionId}/export${params}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '导出清单失败')
    }

    return response.data
  }
}

// 创建默认整合包服务实例
import { apiClient } from './BaseApiClient'
export const packApi = new PackApiService(apiClient)