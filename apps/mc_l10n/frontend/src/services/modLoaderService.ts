/**
 * MOD加载器服务
 * 提供前端与后端MOD加载器系统的接口
 */

import { apiClient } from './apiClient'
import type { ModInfo, ModLoaderStatistics, DependencyAnalysis } from '../components/ModLoader'

export interface ScanProgress {
  current_file: string
  processed_files: number
  total_files: number
  current_phase: string
  progress_percentage: number
}

export interface ScanRequest {
  target_path: string
  scan_type?: 'auto' | 'modpack' | 'mods_folder' | 'single_mod'
  recursive?: boolean
}

export interface ScanResult {
  scan_id: string
  scan_type: string
  target_path: string
  mods_found: ModInfo[]
  language_files: Array<{
    file_path: string
    locale: string
    format: string
    entries_count: number
    file_size: number
  }>
  scan_statistics: ModLoaderStatistics
  dependency_analysis: DependencyAnalysis
  is_success: boolean
  error_message?: string
}

export interface ModValidationResult {
  valid_mods: string[]
  invalid_mods: Array<{
    file_path: string
    error: string
  }>
}

export interface LoaderDetectionResult {
  [filePath: string]: {
    loader_type: string
    version: string
    minecraft_version: string
    loader_name: string
    capabilities: string[]
  } | null
}

class ModLoaderService {
  private baseUrl = '/api/v1/mod-loader'

  /**
   * 扫描MOD目录
   */
  async scanModDirectory(request: ScanRequest): Promise<{ scan_id: string }> {
    try {
      const response = await apiClient.post(`${this.baseUrl}/scan`, request)
      return response.data
    } catch (error) {
      console.error('扫描MOD目录失败:', error)
      throw new Error('扫描请求失败')
    }
  }

  /**
   * 获取扫描进度
   */
  async getScanProgress(scanId: string): Promise<ScanProgress | null> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/scan/${scanId}/progress`)
      return response.data
    } catch (error) {
      console.error('获取扫描进度失败:', error)
      return null
    }
  }

  /**
   * 获取扫描结果
   */
  async getScanResult(scanId: string): Promise<ScanResult> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/scan/${scanId}/result`)
      return response.data
    } catch (error) {
      console.error('获取扫描结果失败:', error)
      throw new Error('获取扫描结果失败')
    }
  }

  /**
   * 取消扫描
   */
  async cancelScan(scanId: string): Promise<void> {
    try {
      await apiClient.post(`${this.baseUrl}/scan/${scanId}/cancel`)
    } catch (error) {
      console.error('取消扫描失败:', error)
      throw new Error('取消扫描失败')
    }
  }

  /**
   * 验证MOD文件
   */
  async validateModFiles(filePaths: string[]): Promise<ModValidationResult> {
    try {
      const response = await apiClient.post(`${this.baseUrl}/validate`, {
        file_paths: filePaths
      })
      return response.data
    } catch (error) {
      console.error('验证MOD文件失败:', error)
      throw new Error('MOD文件验证失败')
    }
  }

  /**
   * 批量检测MOD加载器类型
   */
  async detectModLoaders(filePaths: string[]): Promise<LoaderDetectionResult> {
    try {
      const response = await apiClient.post(`${this.baseUrl}/detect`, {
        file_paths: filePaths
      })
      return response.data
    } catch (error) {
      console.error('检测MOD加载器类型失败:', error)
      throw new Error('MOD加载器检测失败')
    }
  }

  /**
   * 获取支持的加载器列表
   */
  async getSupportedLoaders(): Promise<string[]> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/supported-loaders`)
      return response.data.loaders
    } catch (error) {
      console.error('获取支持的加载器列表失败:', error)
      throw new Error('获取加载器列表失败')
    }
  }

  /**
   * 获取加载器能力
   */
  async getLoaderCapabilities(loaderType: string): Promise<string[]> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/loader/${loaderType}/capabilities`)
      return response.data.capabilities
    } catch (error) {
      console.error('获取加载器能力失败:', error)
      throw new Error('获取加载器能力失败')
    }
  }

  /**
   * 分析依赖关系
   */
  async analyzeDependencies(scanId: string): Promise<DependencyAnalysis> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/scan/${scanId}/dependencies`)
      return response.data
    } catch (error) {
      console.error('分析依赖关系失败:', error)
      throw new Error('依赖关系分析失败')
    }
  }

  /**
   * 导出MOD信息
   */
  async exportModInfo(
    scanId: string, 
    format: 'json' | 'csv' | 'xlsx' = 'json'
  ): Promise<Blob> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/scan/${scanId}/export`, {
        params: { format },
        responseType: 'blob'
      })
      return response.data
    } catch (error) {
      console.error('导出MOD信息失败:', error)
      throw new Error('导出失败')
    }
  }

  /**
   * 获取扫描历史
   */
  async getScanHistory(limit: number = 10): Promise<Array<{
    scan_id: string
    target_path: string
    scan_time: string
    mods_count: number
    status: string
  }>> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/scans/history`, {
        params: { limit }
      })
      return response.data.scans
    } catch (error) {
      console.error('获取扫描历史失败:', error)
      throw new Error('获取扫描历史失败')
    }
  }

  /**
   * 删除扫描记录
   */
  async deleteScanRecord(scanId: string): Promise<void> {
    try {
      await apiClient.delete(`${this.baseUrl}/scan/${scanId}`)
    } catch (error) {
      console.error('删除扫描记录失败:', error)
      throw new Error('删除扫描记录失败')
    }
  }

  /**
   * 轮询扫描进度直到完成
   */
  async pollScanProgress(
    scanId: string,
    onProgress?: (progress: ScanProgress) => void,
    onComplete?: (result: ScanResult) => void,
    onError?: (error: Error) => void,
    pollInterval: number = 1000
  ): Promise<ScanResult> {
    return new Promise((resolve, reject) => {
      const pollTimer = setInterval(async () => {
        try {
          const progress = await this.getScanProgress(scanId)
          
          if (progress) {
            onProgress?.(progress)
            
            if (progress.progress_percentage >= 100) {
              clearInterval(pollTimer)
              
              // 获取最终结果
              const result = await this.getScanResult(scanId)
              onComplete?.(result)
              resolve(result)
            }
          } else {
            // 进度为空，可能扫描完成或出错
            clearInterval(pollTimer)
            
            try {
              const result = await this.getScanResult(scanId)
              onComplete?.(result)
              resolve(result)
            } catch (resultError) {
              const error = new Error('扫描进度查询失败')
              onError?.(error)
              reject(error)
            }
          }
        } catch (error) {
          clearInterval(pollTimer)
          const scanError = new Error(`扫描进度查询失败: ${error}`)
          onError?.(scanError)
          reject(scanError)
        }
      }, pollInterval)

      // 设置超时保护（30分钟）
      setTimeout(() => {
        clearInterval(pollTimer)
        const timeoutError = new Error('扫描超时')
        onError?.(timeoutError)
        reject(timeoutError)
      }, 30 * 60 * 1000)
    })
  }
}

// 创建单例实例
export const modLoaderService = new ModLoaderService()

// 便捷函数
export const scanModDirectory = (request: ScanRequest) => 
  modLoaderService.scanModDirectory(request)

export const getScanProgress = (scanId: string) => 
  modLoaderService.getScanProgress(scanId)

export const getScanResult = (scanId: string) => 
  modLoaderService.getScanResult(scanId)

export const validateModFiles = (filePaths: string[]) => 
  modLoaderService.validateModFiles(filePaths)

export const detectModLoaders = (filePaths: string[]) => 
  modLoaderService.detectModLoaders(filePaths)

export const analyzeDependencies = (scanId: string) => 
  modLoaderService.analyzeDependencies(scanId)

export const pollScanProgress = (
  scanId: string,
  onProgress?: (progress: ScanProgress) => void,
  onComplete?: (result: ScanResult) => void,
  onError?: (error: Error) => void
) => modLoaderService.pollScanProgress(scanId, onProgress, onComplete, onError)

export default modLoaderService