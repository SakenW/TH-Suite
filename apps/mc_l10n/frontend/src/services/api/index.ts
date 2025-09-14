/**
 * API服务统一导出
 * 管理所有API相关的服务、类型和工具函数
 */

// ==================== API 客户端和服务 ====================
export { BaseApiClient } from './BaseApiClient'
export { ProjectApiService } from './ProjectApiService'
export { ScanApiService } from './ScanApiService'
export { SyncApiService } from './SyncApiService'
export { TransHubSdkService } from './TransHubSdkService'
export { PackApiService } from './PackApiService'
export { ModApiService } from './ModApiService'
export * from './types'

// ==================== 全局API服务实例 ====================
import { BaseApiClient } from './BaseApiClient'
import { PackApiService } from './PackApiService'
import { ModApiService } from './ModApiService'

// 创建全局API客户端实例
const globalApiClient = new BaseApiClient()

// 创建全局服务实例
export const packApi = new PackApiService(globalApiClient)
export const modApi = new ModApiService(globalApiClient)

// ==================== 工具函数 ====================

/**
 * 创建查询参数
 */
export function createQueryParams(
  page: number = 1,
  limit: number = 20,
  options: {
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
    filters?: Record<string, any>
    search?: string
  } = {}
) {
  return {
    page: Math.max(1, page),
    limit: Math.max(1, Math.min(100, limit)),
    sort_by: options.sortBy,
    sort_order: options.sortOrder || 'asc',
    filters: options.filters,
    search: options.search,
  }
}

/**
 * 检查API响应是否成功
 */
export function isApiResponseSuccess<T>(response: any): response is { success: true, data: T } {
  return response && response.success === true && response.data !== undefined
}

/**
 * 从API响应中提取数据
 */
export function extractApiResponseData<T>(response: any): T | null {
  if (isApiResponseSuccess(response)) {
    return response.data
  }
  return null
}

/**
 * 格式化API错误信息
 */
export function formatApiError(error: any): string {
  if (error?.error?.message) {
    return error.error.message
  }
  if (error?.message) {
    return error.message
  }
  return 'Unknown error occurred'
}

/**
 * 生成幂等性键
 */
export function generateIdempotencyKey(): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2)
  return `${timestamp}-${random}`
}

// ==================== 常量 ====================

export const API_ENDPOINTS = {
  // 项目管理
  PROJECTS: '/api/projects',
  
  // 扫描
  SCAN: '/api/scan',
  
  // 同步
  SYNC: '/api/sync',
  
  // Trans-Hub SDK
  SDK: '/api/sdk',
  
  // 包管理
  PACKS: '/api/packs',
  
  // MOD管理
  MODS: '/api/mods',
} as const

export const API_LIMITS = {
  MAX_PAGE_SIZE: 100,
  DEFAULT_PAGE_SIZE: 20,
  MAX_BATCH_SIZE: 1000,
  REQUEST_TIMEOUT: 30000, // 30 seconds
} as const

export const STATUS_COLORS = {
  success: '#52c41a',    // green
  warning: '#fadb14',    // yellow
  error: '#ff4d4f',      // red
  info: '#1890ff',       // blue
  processing: '#722ed1', // purple
} as const