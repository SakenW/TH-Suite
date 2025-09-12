/**
 * 同步API服务
 * 集成v2.1同步服务，提供完整的双向同步功能
 */

import { BaseApiClient } from './BaseApiClient'
import { ApiResponse, RequestConfig } from './types'
import { ServiceResult } from '../container/types'

// 同步相关类型定义
export interface SyncRequest {
  project_id?: string
  sync_mode: 'push' | 'pull' | 'bidirectional'
  options?: SyncRequestOptions
}

export interface SyncRequestOptions {
  // 同步选项
  conflict_resolution?: 'local_wins' | 'remote_wins' | 'manual' | 'interactive'
  batch_size?: number
  timeout_seconds?: number
  
  // 内容过滤
  include_namespaces?: string[]
  exclude_namespaces?: string[]
  include_mods?: string[]
  exclude_mods?: string[]
  
  // 验证选项
  validate_before_sync?: boolean
  dry_run?: boolean
  generate_backup?: boolean
  
  // 性能选项
  parallel_workers?: number
  rate_limit_requests_per_second?: number
  use_compression?: boolean
}

export interface SyncTask {
  task_id: string
  project_id: string
  sync_mode: 'push' | 'pull' | 'bidirectional'
  status: 'pending' | 'initializing' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'
  priority: 'low' | 'normal' | 'high'
  
  // 进度信息
  progress: number // 0-100
  total_items: number
  processed_items: number
  failed_items: number
  skipped_items: number
  
  // 当前操作
  current_phase: string
  current_operation?: string
  current_item?: string
  
  // 时间信息
  created_at: string
  started_at?: string
  completed_at?: string
  estimated_completion?: string
  
  // 性能指标
  items_per_second?: number
  elapsed_seconds?: number
  remaining_seconds?: number
  
  // 错误和结果
  error?: string
  warnings: string[]
  result?: SyncTaskResult
}

export interface SyncTaskResult {
  // 统计信息
  total_processed: number
  successful_operations: number
  failed_operations: number
  conflicts_resolved: number
  
  // 详细结果
  push_result?: {
    items_pushed: number
    items_created: number
    items_updated: number
    push_errors: number
  }
  
  pull_result?: {
    items_pulled: number
    items_created: number
    items_updated: number
    pull_errors: number
  }
  
  // 冲突处理
  conflicts?: Array<{
    content_key: string
    conflict_type: 'content_mismatch' | 'metadata_mismatch' | 'version_conflict'
    resolution: 'local_wins' | 'remote_wins' | 'merged' | 'manual'
    local_value?: string
    remote_value?: string
    resolved_value?: string
  }>
  
  // 错误详情
  errors?: Array<{
    item_key: string
    error_type: string
    error_message: string
    retry_count: number
  }>
  
  // 性能指标
  total_duration_ms: number
  network_time_ms: number
  processing_time_ms: number
  validation_time_ms: number
}

export interface SyncHistory {
  history_id: string
  task_id: string
  project_id: string
  sync_mode: string
  status: string
  started_at: string
  completed_at?: string
  duration_ms?: number
  items_processed: number
  success_rate: number
  error_summary?: string
}

export interface SyncStatistics {
  project_id: string
  total_syncs: number
  successful_syncs: number
  failed_syncs: number
  last_sync_at?: string
  last_successful_sync_at?: string
  average_duration_ms: number
  average_items_per_sync: number
  success_rate: number
  common_errors: Array<{
    error_type: string
    count: number
    last_occurred: string
  }>
}

/**
 * 同步API服务类
 */
export class SyncApiService {
  private apiClient: BaseApiClient

  constructor(apiClient?: BaseApiClient) {
    this.apiClient = apiClient || new BaseApiClient()
  }

  // ============================================================
  // 同步任务管理
  // ============================================================

  /**
   * 启动同步任务
   */
  async startSync(
    request: SyncRequest,
    config?: RequestConfig
  ): Promise<ServiceResult<SyncTask>> {
    try {
      const response = await this.apiClient.post<SyncTask>(
        '/api/v2.1/sync/start',
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
            code: 'SYNC_START_FAILED',
            message: response.message || '启动同步任务失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '启动同步请求失败'
        }
      }
    }
  }

  /**
   * 获取同步任务状态
   */
  async getTaskStatus(
    taskId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<SyncTask>> {
    try {
      const response = await this.apiClient.get<SyncTask>(
        `/api/v2.1/sync/tasks/${taskId}`,
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
          message: error.message || '获取任务状态失败'
        }
      }
    }
  }

  /**
   * 获取所有活跃的同步任务
   */
  async getActiveTasks(
    projectId?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<SyncTask[]>> {
    try {
      const params = projectId ? { project_id: projectId } : undefined
      const response = await this.apiClient.get<SyncTask[]>(
        '/api/v2.1/sync/tasks/active',
        { ...config, params }
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
            code: 'TASKS_FETCH_FAILED',
            message: response.message || '获取活跃任务失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取活跃任务请求失败'
        }
      }
    }
  }

  /**
   * 取消同步任务
   */
  async cancelTask(
    taskId: string,
    reason?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.post<{ cancelled: boolean }>(
        `/api/v2.1/sync/tasks/${taskId}/cancel`,
        { reason },
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
            message: response.message || '取消任务失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '取消任务请求失败'
        }
      }
    }
  }

  /**
   * 暂停同步任务
   */
  async pauseTask(
    taskId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.post<{ paused: boolean }>(
        `/api/v2.1/sync/tasks/${taskId}/pause`,
        {},
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.paused
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PAUSE_FAILED',
            message: response.message || '暂停任务失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '暂停任务请求失败'
        }
      }
    }
  }

  /**
   * 恢复同步任务
   */
  async resumeTask(
    taskId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.post<{ resumed: boolean }>(
        `/api/v2.1/sync/tasks/${taskId}/resume`,
        {},
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.resumed
        }
      } else {
        return {
          success: false,
          error: {
            code: 'RESUME_FAILED',
            message: response.message || '恢复任务失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '恢复任务请求失败'
        }
      }
    }
  }

  // ============================================================
  // 同步历史和统计
  // ============================================================

  /**
   * 获取同步历史
   */
  async getSyncHistory(
    projectId?: string,
    limit: number = 50,
    offset: number = 0,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    history: SyncHistory[]
    total: number
    has_more: boolean
  }>> {
    try {
      const params = {
        project_id: projectId,
        limit,
        offset
      }

      const response = await this.apiClient.get(
        '/api/v2.1/sync/history',
        { ...config, params }
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
            code: 'HISTORY_FETCH_FAILED',
            message: response.message || '获取同步历史失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取同步历史请求失败'
        }
      }
    }
  }

  /**
   * 获取同步统计
   */
  async getSyncStatistics(
    projectId?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<SyncStatistics>> {
    try {
      const params = projectId ? { project_id: projectId } : undefined
      const response = await this.apiClient.get<SyncStatistics>(
        '/api/v2.1/sync/statistics',
        { ...config, params }
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
            code: 'STATISTICS_FETCH_FAILED',
            message: response.message || '获取同步统计失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取同步统计请求失败'
        }
      }
    }
  }

  // ============================================================
  // 冲突解决
  // ============================================================

  /**
   * 获取待解决的冲突
   */
  async getPendingConflicts(
    taskId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<SyncTaskResult['conflicts']>> {
    try {
      const response = await this.apiClient.get(
        `/api/v2.1/sync/tasks/${taskId}/conflicts`,
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
            code: 'CONFLICTS_FETCH_FAILED',
            message: response.message || '获取冲突列表失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取冲突请求失败'
        }
      }
    }
  }

  /**
   * 解决同步冲突
   */
  async resolveConflict(
    taskId: string,
    contentKey: string,
    resolution: 'local_wins' | 'remote_wins' | 'manual',
    resolvedValue?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.post<{ resolved: boolean }>(
        `/api/v2.1/sync/tasks/${taskId}/conflicts/resolve`,
        {
          content_key: contentKey,
          resolution,
          resolved_value: resolvedValue
        },
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.resolved
        }
      } else {
        return {
          success: false,
          error: {
            code: 'CONFLICT_RESOLVE_FAILED',
            message: response.message || '解决冲突失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '解决冲突请求失败'
        }
      }
    }
  }

  // ============================================================
  // 实用功能
  // ============================================================

  /**
   * 干运行同步（预览更改）
   */
  async dryRunSync(
    request: Omit<SyncRequest, 'options'> & {
      options?: Omit<SyncRequestOptions, 'dry_run'>
    },
    config?: RequestConfig
  ): Promise<ServiceResult<{
    changes_preview: Array<{
      content_key: string
      operation: 'create' | 'update' | 'delete'
      current_value?: string
      new_value?: string
      conflict_detected: boolean
    }>
    estimated_duration_seconds: number
    potential_conflicts: number
  }>> {
    try {
      const dryRunRequest: SyncRequest = {
        ...request,
        options: {
          ...request.options,
          dry_run: true
        }
      }

      const response = await this.apiClient.post(
        '/api/v2.1/sync/dry-run',
        dryRunRequest,
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
            code: 'DRY_RUN_FAILED',
            message: response.message || '预览同步失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '预览同步请求失败'
        }
      }
    }
  }

  /**
   * 检查同步服务状态
   */
  async checkSyncServiceStatus(
    config?: RequestConfig
  ): Promise<ServiceResult<{
    status: 'healthy' | 'degraded' | 'unavailable'
    active_tasks: number
    queue_size: number
    worker_status: Record<string, string>
    last_heartbeat: string
  }>> {
    try {
      const response = await this.apiClient.get(
        '/api/v2.1/sync/service/status',
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
            message: response.message || '同步服务状态检查失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'SYNC_SERVICE_UNAVAILABLE',
          message: '同步服务当前不可用'
        }
      }
    }
  }
}

// 创建全局实例
export const syncApiService = new SyncApiService()

// 导出类型
export type {
  SyncRequest,
  SyncRequestOptions,
  SyncTask,
  SyncTaskResult,
  SyncHistory,
  SyncStatistics
}