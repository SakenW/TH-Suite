/**
 * API服务统一导出
 * 管理所有API相关的服务、类型和工具函数
 */

// ==================== V6 API ====================
export { V6ApiClient, v6ApiClient } from './V6ApiClient'
export type * from './v6Types'

// ==================== 工具函数 ====================

/**
 * 创建V6查询参数
 */
export function createV6QueryParams(
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
 * 检查V6响应是否成功
 */
export function isV6ResponseSuccess<T>(response: any): response is { success: true, data: T } {
  return response && response.success === true && response.data !== undefined
}

/**
 * 从V6响应中提取数据
 */
export function extractV6ResponseData<T>(response: any): T | null {
  if (isV6ResponseSuccess(response)) {
    return response.data
  }
  return null
}

/**
 * 格式化V6错误信息
 */
export function formatV6Error(error: any): string {
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

/**
 * V6实体状态检查工具
 */
export const V6EntityUtils = {
  isActive: (status: string) => status === 'active',
  isInactive: (status: string) => status === 'inactive',
  isArchived: (status: string) => status === 'archived',
  
  canEdit: (status: string) => status === 'active',
  canDelete: (status: string) => ['active', 'inactive'].includes(status),
  canArchive: (status: string) => ['active', 'inactive'].includes(status),
}

/**
 * V6翻译状态检查工具
 */
export const V6TranslationUtils = {
  isNew: (status: string) => status === 'new',
  isReviewing: (status: string) => status === 'reviewing',
  isReviewed: (status: string) => status === 'reviewed',
  isApproved: (status: string) => status === 'approved',
  isRejected: (status: string) => status === 'rejected',
  
  canReview: (status: string) => ['new', 'reviewing'].includes(status),
  canApprove: (status: string) => status === 'reviewed',
  canReject: (status: string) => ['new', 'reviewing', 'reviewed'].includes(status),
  
  isCompleted: (status: string) => ['approved', 'rejected'].includes(status),
  needsAttention: (status: string) => ['new', 'reviewing'].includes(status),
}

/**
 * V6任务状态检查工具
 */
export const V6TaskUtils = {
  isPending: (status: string) => status === 'pending',
  isLeased: (status: string) => status === 'leased',
  isCompleted: (status: string) => status === 'completed',
  isFailed: (status: string) => status === 'failed',
  
  isRunning: (status: string) => status === 'leased',
  isFinished: (status: string) => ['completed', 'failed'].includes(status),
  isActive: (status: string) => ['pending', 'leased'].includes(status),
  
  canRetry: (status: string) => status === 'failed',
  canCancel: (status: string) => ['pending', 'leased'].includes(status),
}

/**
 * V6健康状态检查工具
 */
export const V6HealthUtils = {
  isHealthy: (status: string) => status === 'healthy',
  isDegraded: (status: string) => status === 'degraded',
  isUnhealthy: (status: string) => status === 'unhealthy',
  
  needsAttention: (status: string) => ['degraded', 'unhealthy'].includes(status),
  isCritical: (status: string) => status === 'unhealthy',
}

/**
 * V6缓存统计工具
 */
export const V6CacheUtils = {
  calculateOverallHitRate: (stats: any) => {
    if (!stats) return 0
    const total = Object.values(stats).reduce((sum: number, layer: any) => {
      return sum + (layer.hit_rate || 0)
    }, 0)
    return total / Object.keys(stats).length
  },
  
  isPerformanceGood: (hitRate: number) => hitRate >= 0.8,
  isPerformanceFair: (hitRate: number) => hitRate >= 0.6,
  isPerformancePoor: (hitRate: number) => hitRate < 0.6,
}

// ==================== 常量 ====================

export const V6_ENDPOINTS = {
  // 实体管理
  PACKS: '/api/v6/packs',
  MODS: '/api/v6/mods',
  LANGUAGE_FILES: '/api/v6/language-files',
  TRANSLATIONS: '/api/v6/translations',
  
  // 统计和监控
  DATABASE_STATISTICS: '/api/v6/database/statistics',
  DATABASE_HEALTH: '/api/v6/database/health',
  CACHE_STATUS: '/api/v6/cache/status',
  QUEUE_STATUS: '/api/v6/queue/status',
  
  // 队列管理
  QUEUE_TASKS: '/api/v6/queue/tasks',
  
  // 缓存管理
  CACHE_CLEANUP: '/api/v6/cache/cleanup',
  CACHE_WARMUP: '/api/v6/cache/warmup',
  
  // 配置管理
  SETTINGS: '/api/v6/settings',
  
  // 同步协议
  SYNC_HANDSHAKE: '/api/v6/sync/handshake',
  SYNC_CHUNK_UPLOAD: '/api/v6/sync/chunk',
  SYNC_COMMIT: '/api/v6/sync/commit',
  
  // V6信息
  V6_INFO: '/api/v6/',
  V6_HEALTH: '/api/v6/health',
} as const

export const V6_LIMITS = {
  MAX_PAGE_SIZE: 100,
  DEFAULT_PAGE_SIZE: 20,
  MAX_BATCH_SIZE: 1000,
  IDEMPOTENCY_TTL: 3600, // 1 hour
  CACHE_WARMUP_BATCH_SIZE: 50,
} as const

export const V6_STATUS_COLORS = {
  // 实体状态
  active: '#10b981',    // green-500
  inactive: '#f59e0b',  // amber-500
  archived: '#6b7280',  // gray-500
  
  // 翻译状态
  new: '#3b82f6',       // blue-500
  reviewing: '#f59e0b', // amber-500
  reviewed: '#8b5cf6',  // violet-500
  approved: '#10b981',  // green-500
  rejected: '#ef4444',  // red-500
  
  // 任务状态
  pending: '#6b7280',   // gray-500
  leased: '#f59e0b',    // amber-500
  completed: '#10b981', // green-500
  failed: '#ef4444',    // red-500
  
  // 健康状态
  healthy: '#10b981',   // green-500
  degraded: '#f59e0b',  // amber-500
  unhealthy: '#ef4444', // red-500
} as const