/**
 * 扫描 API 服务
 * 处理目录扫描、进度监控、结果获取等功能
 * 集成v2.1扫描引擎和真实数据操作
 */

import { BaseApiClient } from './BaseApiClient'
import { 
  ScanRequest, 
  ScanStatus, 
  ScanResult, 
  ScanOptions,
  ApiResponse,
  RequestConfig,
  PaginatedResponse
} from './types'
import { ServiceResult } from '../container/types'

export class ScanApiService {
  private client: BaseApiClient

  constructor(client?: BaseApiClient) {
    this.client = client || new BaseApiClient()
  }

  // ============================================================
  // 扫描任务管理
  // ============================================================

  /**
   * 启动扫描任务
   */
  async startScan(
    request: ScanRequest,
    config?: RequestConfig
  ): Promise<ServiceResult<{ scan_id: string }>> {
    try {
      const response = await this.client.post<{ scan_id: string }>(
        '/api/v2.1/scan/start',
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
            code: 'SCAN_START_FAILED',
            message: response.message || '启动扫描失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '启动扫描请求失败'
        }
      }
    }
  }

  /**
   * 获取扫描状态
   */
  async getScanStatus(
    scanId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<ScanStatus>> {
    try {
      const response = await this.client.get<ScanStatus>(
        `/api/v2.1/scan/status/${scanId}`,
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
            code: 'SCAN_STATUS_FAILED',
            message: response.message || '获取扫描状态失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取扫描状态请求失败'
        }
      }
    }
  }

  /**
   * 获取扫描结果
   */
  async getScanResults(
    scanId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<ScanResult>> {
    try {
      const response = await this.client.get<ScanResult>(
        `/api/v2.1/scan/results/${scanId}`,
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
            code: 'SCAN_RESULTS_FAILED',
            message: response.message || '获取扫描结果失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取扫描结果请求失败'
        }
      }
    }
  }

  /**
   * 取消扫描任务
   */
  async cancelScan(
    scanId: string,
    reason?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.post<{ cancelled: boolean }>(
        `/api/v2.1/scan/cancel/${scanId}`,
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
            code: 'SCAN_CANCEL_FAILED',
            message: response.message || '取消扫描失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '取消扫描请求失败'
        }
      }
    }
  }

  /**
   * 暂停扫描任务
   */
  async pauseScan(
    scanId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.post<{ paused: boolean }>(
        `/api/v2.1/scan/pause/${scanId}`,
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
            code: 'SCAN_PAUSE_FAILED',
            message: response.message || '暂停扫描失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '暂停扫描请求失败'
        }
      }
    }
  }

  /**
   * 恢复扫描任务
   */
  async resumeScan(
    scanId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.post<{ resumed: boolean }>(
        `/api/v2.1/scan/resume/${scanId}`,
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
            code: 'SCAN_RESUME_FAILED',
            message: response.message || '恢复扫描失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '恢复扫描请求失败'
        }
      }
    }
  }

  // ============================================================
  // 扫描历史和管理
  // ============================================================

  /**
   * 获取活跃扫描列表
   */
  async getActiveScans(
    projectId?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<ScanStatus[]>> {
    try {
      const params = projectId ? { project_id: projectId } : undefined
      const response = await this.client.get<ScanStatus[]>(
        '/api/v2.1/scan/active',
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
            code: 'ACTIVE_SCANS_FAILED',
            message: response.message || '获取活跃扫描失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取活跃扫描请求失败'
        }
      }
    }
  }

  /**
   * 获取扫描历史
   */
  async getScanHistory(
    projectId?: string,
    page: number = 1,
    limit: number = 20,
    config?: RequestConfig
  ): Promise<ServiceResult<PaginatedResponse<ScanStatus>>> {
    try {
      const params = {
        project_id: projectId,
        page,
        limit
      }

      const response = await this.client.get<PaginatedResponse<ScanStatus>>(
        '/api/v2.1/scan/history',
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
            code: 'SCAN_HISTORY_FAILED',
            message: response.message || '获取扫描历史失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取扫描历史请求失败'
        }
      }
    }
  }

  /**
   * 删除扫描记录
   */
  async deleteScanRecord(
    scanId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.delete<{ deleted: boolean }>(
        `/api/v2.1/scan/records/${scanId}`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.deleted
        }
      } else {
        return {
          success: false,
          error: {
            code: 'SCAN_DELETE_FAILED',
            message: response.message || '删除扫描记录失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '删除扫描记录请求失败'
        }
      }
    }
  }

  // ============================================================
  // 扫描配置和选项
  // ============================================================

  /**
   * 获取扫描预设配置
   */
  async getScanPresets(
    config?: RequestConfig
  ): Promise<ServiceResult<Array<{
    preset_id: string
    name: string
    description: string
    options: ScanOptions
    is_default: boolean
  }>>> {
    try {
      const response = await this.client.get(
        '/api/v2.1/scan/presets',
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
            code: 'SCAN_PRESETS_FAILED',
            message: response.message || '获取扫描预设失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取扫描预设请求失败'
        }
      }
    }
  }

  /**
   * 验证扫描目录
   */
  async validateScanDirectory(
    directory: string,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    is_valid: boolean
    directory_type: 'modpack' | 'resource_pack' | 'data_pack' | 'mixed' | 'unknown'
    detected_files: number
    estimated_scan_time_seconds: number
    warnings: string[]
  }>> {
    try {
      const response = await this.client.post(
        '/api/v2.1/scan/validate-directory',
        { directory },
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
            code: 'DIRECTORY_VALIDATION_FAILED',
            message: response.message || '目录验证失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '目录验证请求失败'
        }
      }
    }
  }

  // ============================================================
  // 扫描统计和监控
  // ============================================================

  /**
   * 获取扫描统计信息
   */
  async getScanStatistics(
    projectId?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    total_scans: number
    successful_scans: number
    failed_scans: number
    active_scans: number
    average_scan_duration_ms: number
    total_files_scanned: number
    total_mods_discovered: number
    total_content_instances: number
    last_scan_at?: string
    scan_trends: Array<{
      date: string
      scan_count: number
      success_rate: number
      avg_duration_ms: number
    }>
  }>> {
    try {
      const params = projectId ? { project_id: projectId } : undefined
      const response = await this.client.get(
        '/api/v2.1/scan/statistics',
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
            code: 'SCAN_STATISTICS_FAILED',
            message: response.message || '获取扫描统计失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取扫描统计请求失败'
        }
      }
    }
  }

  /**
   * 检查扫描服务状态
   */
  async checkScanServiceStatus(
    config?: RequestConfig
  ): Promise<ServiceResult<{
    status: 'healthy' | 'degraded' | 'unavailable'
    active_scans: number
    queue_size: number
    worker_status: Array<{
      worker_id: string
      status: 'idle' | 'busy' | 'error'
      current_task?: string
      uptime_seconds: number
    }>
    performance_metrics: {
      avg_scan_speed_files_per_second: number
      peak_memory_usage_mb: number
      cache_hit_rate: number
    }
    last_heartbeat: string
  }>> {
    try {
      const response = await this.client.get(
        '/api/v2.1/scan/service/status',
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
            code: 'SCAN_SERVICE_STATUS_FAILED',
            message: response.message || '扫描服务状态检查失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'SCAN_SERVICE_UNAVAILABLE',
          message: '扫描服务当前不可用'
        }
      }
    }
  }

  // ============================================================
  // 实用方法
  // ============================================================

  /**
   * 等待扫描完成
   * 轮询扫描状态直到完成或失败
   */
  async waitForScanCompletion(
    scanId: string,
    onProgress?: (status: ScanStatus) => void,
    pollIntervalMs: number = 1000,
    timeoutMs: number = 300000, // 5分钟超时
    config?: RequestConfig
  ): Promise<ServiceResult<ScanResult>> {
    const startTime = Date.now()
    
    while (Date.now() - startTime < timeoutMs) {
      const statusResult = await this.getScanStatus(scanId, config)
      
      if (!statusResult.success) {
        return statusResult as ServiceResult<ScanResult>
      }
      
      const status = statusResult.data!
      onProgress?.(status)
      
      if (status.status === 'completed') {
        return await this.getScanResults(scanId, config)
      }
      
      if (status.status === 'failed' || status.status === 'cancelled') {
        return {
          success: false,
          error: {
            code: 'SCAN_FAILED',
            message: status.error || `扫描${status.status === 'failed' ? '失败' : '已取消'}`
          }
        }
      }
      
      // 等待下次轮询
      await new Promise(resolve => setTimeout(resolve, pollIntervalMs))
    }
    
    return {
      success: false,
      error: {
        code: 'SCAN_TIMEOUT',
        message: '扫描超时'
      }
    }
  }

  /**
   * 批量取消扫描
   */
  async cancelMultipleScans(
    scanIds: string[],
    reason?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<Array<{
    scan_id: string
    cancelled: boolean
    error?: string
  }>>> {
    const results = await Promise.allSettled(
      scanIds.map(scanId => this.cancelScan(scanId, reason, config))
    )
    
    const cancelResults = results.map((result, index) => ({
      scan_id: scanIds[index],
      cancelled: result.status === 'fulfilled' && result.value.success ? result.value.data! : false,
      error: result.status === 'rejected' 
        ? result.reason.message 
        : (result.value.success ? undefined : result.value.error?.message)
    }))
    
    return {
      success: true,
      data: cancelResults
    }
  }
}

// 创建全局实例
export const scanApiService = new ScanApiService()

// 导出类型
export type { ScanRequest, ScanStatus, ScanResult, ScanOptions }