/**
 * 扫描 API 服务
 * 处理目录扫描、进度监控、结果获取等功能
 */

import { BaseApiClient } from './BaseApiClient'
import { 
  ScanRequest, 
  ScanStatus, 
  ScanResult, 
  ApiResponse,
  RequestConfig 
} from './types'

export class ScanApiService {
  constructor(private client: BaseApiClient) {}

  /**
   * 测试扫描服务连接
   */
  async testConnection(): Promise<{success: boolean}> {
    try {
      // 使用健康检查端点测试连接
      const isHealthy = await this.client.healthCheck()
      return { success: isHealthy }
    } catch {
      return { success: false }
    }
  }

  /**
   * 启动扫描任务
   */
  async startScan(request: ScanRequest, config?: RequestConfig): Promise<{
    scan_id: string
    directory: string
    incremental: boolean
    status: string
  }> {
    const response = await this.client.post('/api/v1/scan/start', request, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '启动扫描失败')
    }

    return response.data
  }

  /**
   * 获取扫描状态
   */
  async getScanStatus(scanId: string, config?: RequestConfig): Promise<ScanStatus> {
    const response = await this.client.get(`/api/v1/scan/status/${scanId}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取扫描状态失败')
    }

    return response.data
  }

  /**
   * 获取扫描结果
   */
  async getScanResults(scanId: string, config?: RequestConfig): Promise<ScanResult> {
    const response = await this.client.get(`/api/v1/scan/results/${scanId}`, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取扫描结果失败')
    }

    return response.data
  }

  /**
   * 取消扫描任务
   */
  async cancelScan(scanId: string, config?: RequestConfig): Promise<{
    scan_id: string
    status: string
  }> {
    const response = await this.client.post(`/api/v1/scan/cancel/${scanId}`, {}, config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '取消扫描失败')
    }

    return response.data
  }

  /**
   * 获取活跃扫描列表
   */
  async getActiveScans(config?: RequestConfig): Promise<{
    active_scans: ScanStatus[]
    total: number
  }> {
    const response = await this.client.get('/api/v1/scan/active', config)
    
    if (!response.success || !response.data) {
      throw new Error(response.message || '获取活跃扫描失败')
    }

    return response.data
  }

  /**
   * 轮询扫描状态（直到完成）
   */
  async pollScanStatus(
    scanId: string, 
    onProgress?: (status: ScanStatus) => void,
    options?: {
      interval?: number
      timeout?: number
      signal?: AbortSignal
    }
  ): Promise<ScanStatus> {
    const interval = options?.interval || 1000
    const timeout = options?.timeout || 300000 // 5分钟
    const startTime = Date.now()

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          // 检查是否超时
          if (Date.now() - startTime > timeout) {
            reject(new Error('扫描状态轮询超时'))
            return
          }

          // 检查是否取消
          if (options?.signal?.aborted) {
            reject(new Error('扫描状态轮询被取消'))
            return
          }

          const status = await this.getScanStatus(scanId)
          
          // 调用进度回调
          if (onProgress) {
            onProgress(status)
          }

          // 检查是否完成
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            resolve(status)
            return
          }

          // 继续轮询
          setTimeout(poll, interval)
        } catch (error) {
          reject(error)
        }
      }

      poll()
    })
  }

  /**
   * 执行完整扫描流程（启动 → 监控 → 获取结果）
   */
  async executeScanWorkflow(
    request: ScanRequest,
    callbacks?: {
      onStart?: (scanId: string) => void
      onProgress?: (status: ScanStatus) => void
      onComplete?: (result: ScanResult) => void
      onError?: (error: Error) => void
    },
    options?: {
      pollInterval?: number
      timeout?: number
      signal?: AbortSignal
    }
  ): Promise<ScanResult> {
    try {
      // 1. 启动扫描
      const startResult = await this.startScan(request)
      const scanId = startResult.scan_id
      
      if (callbacks?.onStart) {
        callbacks.onStart(scanId)
      }

      // 2. 监控进度
      const finalStatus = await this.pollScanStatus(
        scanId,
        callbacks?.onProgress,
        {
          interval: options?.pollInterval,
          timeout: options?.timeout,
          signal: options?.signal,
        }
      )

      // 3. 检查最终状态
      if (finalStatus.status === 'failed') {
        throw new Error('扫描任务失败')
      }

      if (finalStatus.status === 'cancelled') {
        throw new Error('扫描任务被取消')
      }

      // 4. 获取结果
      const result = await this.getScanResults(scanId)
      
      if (callbacks?.onComplete) {
        callbacks.onComplete(result)
      }

      return result
    } catch (error) {
      if (callbacks?.onError) {
        callbacks.onError(error as Error)
      }
      throw error
    }
  }

  /**
   * 批量扫描多个目录
   */
  async batchScan(
    requests: ScanRequest[],
    callbacks?: {
      onBatchStart?: () => void
      onScanStart?: (index: number, scanId: string) => void
      onScanProgress?: (index: number, status: ScanStatus) => void
      onScanComplete?: (index: number, result: ScanResult) => void
      onBatchComplete?: (results: ScanResult[]) => void
      onError?: (index: number, error: Error) => void
    },
    options?: {
      concurrent?: boolean
      maxConcurrency?: number
      signal?: AbortSignal
    }
  ): Promise<ScanResult[]> {
    const results: ScanResult[] = []
    
    if (callbacks?.onBatchStart) {
      callbacks.onBatchStart()
    }

    if (options?.concurrent) {
      // 并发扫描
      const maxConcurrency = options.maxConcurrency || 3
      const chunks: ScanRequest[][] = []
      
      for (let i = 0; i < requests.length; i += maxConcurrency) {
        chunks.push(requests.slice(i, i + maxConcurrency))
      }

      for (const chunk of chunks) {
        const chunkPromises = chunk.map(async (request, chunkIndex) => {
          const globalIndex = chunks.indexOf(chunk) * maxConcurrency + chunkIndex
          
          return this.executeScanWorkflow(
            request,
            {
              onStart: (scanId) => callbacks?.onScanStart?.(globalIndex, scanId),
              onProgress: (status) => callbacks?.onScanProgress?.(globalIndex, status),
              onComplete: (result) => callbacks?.onScanComplete?.(globalIndex, result),
              onError: (error) => callbacks?.onError?.(globalIndex, error),
            },
            { signal: options.signal }
          )
        })

        const chunkResults = await Promise.allSettled(chunkPromises)
        
        for (const result of chunkResults) {
          if (result.status === 'fulfilled') {
            results.push(result.value)
          }
        }
      }
    } else {
      // 顺序扫描
      for (let i = 0; i < requests.length; i++) {
        try {
          const result = await this.executeScanWorkflow(
            requests[i],
            {
              onStart: (scanId) => callbacks?.onScanStart?.(i, scanId),
              onProgress: (status) => callbacks?.onScanProgress?.(i, status),
              onComplete: (result) => callbacks?.onScanComplete?.(i, result),
            },
            { signal: options.signal }
          )
          results.push(result)
        } catch (error) {
          if (callbacks?.onError) {
            callbacks.onError(i, error as Error)
          }
          // 继续处理下一个（或根据策略决定是否中断）
        }
      }
    }

    if (callbacks?.onBatchComplete) {
      callbacks.onBatchComplete(results)
    }

    return results
  }

  /**
   * 获取数据库统计信息
   */
  async getDatabaseStats(): Promise<any> {
    try {
      const response = await this.client.get('/api/v6/database/statistics')
      return response
    } catch (error) {
      console.error('获取数据库统计失败:', error)
      throw error
    }
  }
}

// 创建默认扫描服务实例
import { apiClient } from './BaseApiClient'
export const scanApi = new ScanApiService(apiClient)