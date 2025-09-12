/**
 * Trans-Hub SDK 前端集成服务
 * 包装后端SDK功能，提供前端友好的API调用接口
 */

import { BaseApiClient } from './BaseApiClient'
import { ApiResponse, RequestConfig } from './types'
import { ServiceResult } from '../container/types'

// SDK相关类型定义
export interface SdkProjectInfo {
  project_id: string
  name: string
  description?: string
  created_at: string
  updated_at?: string
  metadata?: Record<string, any>
}

export interface SdkContentItem {
  content_key: string
  source_text: string
  context?: string
  namespace: string
  uida?: string
  metadata?: Record<string, any>
}

export interface SdkIngestionRequest {
  project_id: string
  content_items: SdkContentItem[]
  batch_id?: string
  options?: {
    overwrite_existing?: boolean
    validate_content?: boolean
    generate_uida?: boolean
  }
}

export interface SdkIngestionResult {
  batch_id: string
  ingested_count: number
  failed_count: number
  validation_errors?: Array<{
    content_key: string
    error: string
  }>
  processing_time_ms: number
}

export interface SdkTranslationExportRequest {
  project_id: string
  target_language: string
  format: 'json' | 'minecraft_lang' | 'properties'
  include_untranslated?: boolean
  namespaces?: string[]
}

export interface SdkTranslationExportResult {
  export_id: string
  download_url?: string
  file_path?: string
  exported_count: number
  format: string
  created_at: string
}

export interface SdkSyncOptions {
  mode: 'push' | 'pull' | 'bidirectional'
  conflict_resolution: 'local_wins' | 'remote_wins' | 'manual'
  batch_size?: number
  include_metadata?: boolean
  validate_before_sync?: boolean
}

export interface SdkSyncTask {
  task_id: string
  project_id: string
  sync_mode: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  total_items: number
  processed_items: number
  current_operation?: string
  started_at: string
  completed_at?: string
  error?: string
  result?: {
    synced_count: number
    conflicts_count: number
    errors_count: number
  }
}

/**
 * Trans-Hub SDK 服务类
 * 提供与后端SDK集成的所有功能
 */
export class TransHubSdkService {
  private apiClient: BaseApiClient

  constructor(apiClient?: BaseApiClient) {
    this.apiClient = apiClient || new BaseApiClient()
  }

  // ============================================================
  // 项目管理功能
  // ============================================================

  /**
   * 确保Minecraft项目存在
   */
  async ensureMinecraftProject(
    config?: RequestConfig
  ): Promise<ServiceResult<SdkProjectInfo>> {
    try {
      const response = await this.apiClient.post<SdkProjectInfo>(
        '/api/v2.1/sdk/projects/ensure-minecraft',
        {},
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_CREATION_FAILED',
            message: response.message || '创建Minecraft项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '网络请求失败'
        }
      }
    }
  }

  /**
   * 获取项目信息
   */
  async getProjectInfo(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<SdkProjectInfo>> {
    try {
      const response = await this.apiClient.get<SdkProjectInfo>(
        `/api/v2.1/sdk/projects/${projectId}`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_NOT_FOUND',
            message: response.message || '项目未找到'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取项目信息失败'
        }
      }
    }
  }

  // ============================================================
  // 内容摄入功能
  // ============================================================

  /**
   * 摄入Minecraft内容
   */
  async ingestMinecraftContent(
    request: SdkIngestionRequest,
    config?: RequestConfig
  ): Promise<ServiceResult<SdkIngestionResult>> {
    try {
      const response = await this.apiClient.post<SdkIngestionResult>(
        '/api/v2.1/sdk/content/ingest-minecraft',
        request,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'INGESTION_FAILED',
            message: response.message || '内容摄入失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '内容摄入请求失败'
        }
      }
    }
  }

  /**
   * 批量摄入内容
   */
  async batchIngestContent(
    projectId: string,
    contentItems: SdkContentItem[],
    options?: SdkIngestionRequest['options'],
    config?: RequestConfig
  ): Promise<ServiceResult<SdkIngestionResult>> {
    const request: SdkIngestionRequest = {
      project_id: projectId,
      content_items: contentItems,
      batch_id: `batch_${Date.now()}`,
      options
    }

    return this.ingestMinecraftContent(request, config)
  }

  // ============================================================
  // 翻译导出功能
  // ============================================================

  /**
   * 导出翻译内容
   */
  async exportTranslations(
    request: SdkTranslationExportRequest,
    config?: RequestConfig
  ): Promise<ServiceResult<SdkTranslationExportResult>> {
    try {
      const response = await this.apiClient.post<SdkTranslationExportResult>(
        '/api/v2.1/sdk/translations/export',
        request,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'EXPORT_FAILED',
            message: response.message || '翻译导出失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '翻译导出请求失败'
        }
      }
    }
  }

  /**
   * 流式导出翻译内容
   */
  async streamExportTranslations(
    request: SdkTranslationExportRequest,
    onProgress?: (progress: number) => void,
    config?: RequestConfig
  ): Promise<ServiceResult<ReadableStream>> {
    try {
      const stream = await this.apiClient.stream(
        '/api/v2.1/sdk/translations/export-stream',
        {
          method: 'POST',
          data: request,
          timeout: config?.timeout || 300000, // 5分钟超时
          onDownloadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
              const progress = (progressEvent.loaded / progressEvent.total) * 100
              onProgress(Math.round(progress))
            }
          }
        }
      )

      return {
        success: true,
        data: stream
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'STREAM_ERROR',
          message: error.message || '流式导出失败'
        }
      }
    }
  }

  // ============================================================
  // 同步功能
  // ============================================================

  /**
   * 执行同步任务
   */
  async executeSync(
    projectId: string,
    options: SdkSyncOptions,
    config?: RequestConfig
  ): Promise<ServiceResult<SdkSyncTask>> {
    try {
      const response = await this.apiClient.post<SdkSyncTask>(
        '/api/v2.1/sdk/sync/execute',
        {
          project_id: projectId,
          ...options
        },
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'SYNC_FAILED',
            message: response.message || '同步任务启动失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '同步请求失败'
        }
      }
    }
  }

  /**
   * 获取同步任务状态
   */
  async getSyncTaskStatus(
    taskId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<SdkSyncTask>> {
    try {
      const response = await this.apiClient.get<SdkSyncTask>(
        `/api/v2.1/sdk/sync/tasks/${taskId}`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'TASK_NOT_FOUND',
            message: response.message || '同步任务未找到'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取同步状态失败'
        }
      }
    }
  }

  /**
   * 取消同步任务
   */
  async cancelSyncTask(
    taskId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.post<{ cancelled: boolean }>(
        `/api/v2.1/sdk/sync/tasks/${taskId}/cancel`,
        {},
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.cancelled
        }
      } else {
        return {
          success: false,
          error: {
            code: 'CANCEL_FAILED',
            message: response.message || '取消同步任务失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '取消同步请求失败'
        }
      }
    }
  }

  // ============================================================
  // 健康检查和状态
  // ============================================================

  /**
   * 检查SDK服务状态
   */
  async checkSdkStatus(config?: RequestConfig): Promise<ServiceResult<{
    status: 'available' | 'unavailable' | 'degraded'
    version?: string
    features: string[]
    last_check: string
  }>> {
    try {
      const response = await this.apiClient.get(
        '/api/v2.1/sdk/status',
        { ...config, timeout: 5000 }
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'STATUS_CHECK_FAILED',
            message: response.message || 'SDK状态检查失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'SDK_UNAVAILABLE',
          message: 'SDK服务当前不可用'
        }
      }
    }
  }

  /**
   * 获取SDK配置信息
   */
  async getSdkConfig(config?: RequestConfig): Promise<ServiceResult<{
    base_url: string
    project_id: string
    features_enabled: string[]
    rate_limits?: Record<string, number>
  }>> {
    try {
      const response = await this.apiClient.get('/api/v2.1/sdk/config', config)

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'CONFIG_UNAVAILABLE',
            message: 'SDK配置获取失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取SDK配置失败'
        }
      }
    }
  }
}

// 创建全局实例
export const transHubSdkService = new TransHubSdkService()

// 导出类型
export type {
  SdkProjectInfo,
  SdkContentItem,
  SdkIngestionRequest,
  SdkIngestionResult,
  SdkTranslationExportRequest,
  SdkTranslationExportResult,
  SdkSyncOptions,
  SdkSyncTask
}