/**
 * 缓存优化工具
 * 提供智能的数据缓存策略和优化机制
 */

import { QueryClient, QueryKey } from '@tanstack/react-query'
import { queryKeys } from '../config/reactQuery'

// ============================================================
// 缓存策略类型
// ============================================================

export interface CacheStrategy {
  staleTime: number
  gcTime: number
  refetchOnMount?: boolean
  refetchOnWindowFocus?: boolean
  refetchOnReconnect?: boolean
}

export interface CacheOptimizationConfig {
  // 内存使用阈值（MB）
  memoryThreshold: number
  // 自动清理间隔（ms）
  cleanupInterval: number
  // 预取策略
  prefetchStrategy: 'aggressive' | 'conservative' | 'disabled'
  // 后台刷新
  backgroundRefresh: boolean
}

// ============================================================
// 缓存策略定义
// ============================================================

export const cacheStrategies = {
  // 实时数据 - 频繁更新
  realtime: {
    staleTime: 30 * 1000, // 30秒
    gcTime: 5 * 60 * 1000, // 5分钟
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  },
  
  // 高频数据 - 经常访问
  highFrequency: {
    staleTime: 5 * 60 * 1000, // 5分钟
    gcTime: 30 * 60 * 1000, // 30分钟
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  },
  
  // 中频数据 - 偶尔访问
  mediumFrequency: {
    staleTime: 15 * 60 * 1000, // 15分钟
    gcTime: 60 * 60 * 1000, // 1小时
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  },
  
  // 低频数据 - 很少变化
  lowFrequency: {
    staleTime: 30 * 60 * 1000, // 30分钟
    gcTime: 2 * 60 * 60 * 1000, // 2小时
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  },
  
  // 静态数据 - 很少变化
  static: {
    staleTime: 60 * 60 * 1000, // 1小时
    gcTime: 24 * 60 * 60 * 1000, // 24小时
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  },
} as const

// ============================================================
// 缓存优化器
// ============================================================

export class CacheOptimizer {
  private static instance: CacheOptimizer
  private queryClient?: QueryClient
  private config: CacheOptimizationConfig
  private cleanupTimer?: ReturnType<typeof setInterval>
  private memoryUsage = 0
  private accessPatterns = new Map<string, { count: number; lastAccess: number }>()
  
  private constructor(config: Partial<CacheOptimizationConfig> = {}) {
    this.config = {
      memoryThreshold: 100, // 100MB
      cleanupInterval: 5 * 60 * 1000, // 5分钟
      prefetchStrategy: 'conservative',
      backgroundRefresh: true,
      ...config,
    }
  }
  
  static getInstance(config?: Partial<CacheOptimizationConfig>): CacheOptimizer {
    if (!CacheOptimizer.instance) {
      CacheOptimizer.instance = new CacheOptimizer(config)
    }
    return CacheOptimizer.instance
  }
  
  setQueryClient(queryClient: QueryClient) {
    this.queryClient = queryClient
    this.startCleanupTimer()
    this.setupCacheMonitoring()
  }
  
  // ============================================================
  // 智能预取
  // ============================================================
  
  /**
   * 根据访问模式预取数据
   */
  async smartPrefetch(currentQueryKey: QueryKey) {
    if (!this.queryClient || this.config.prefetchStrategy === 'disabled') {
      return
    }
    
    const keyString = JSON.stringify(currentQueryKey)
    this.recordAccess(keyString)
    
    // 基于当前查询预测可能需要的数据
    const relatedQueries = this.getPredictedQueries(currentQueryKey)
    
    for (const queryKey of relatedQueries) {
      await this.prefetchIfWorthwhile(queryKey)
    }
  }
  
  /**
   * 获取相关查询预测
   */
  private getPredictedQueries(currentQueryKey: QueryKey): QueryKey[] {
    const predictions: QueryKey[] = []
    const [resource, ...params] = currentQueryKey
    
    // 基于当前资源类型预测相关查询
    switch (resource) {
      case 'projects':
        if (params[0] === 'detail' && params[1]) {
          // 项目详情 -> 预取统计信息
          predictions.push(queryKeys.projects.statistic(params[1] as string))
          // 项目详情 -> 预取配置信息
          predictions.push(queryKeys.projects.config(params[1] as string))
        }
        if (params[0] === 'list') {
          // 项目列表 -> 预取最近项目
          predictions.push(queryKeys.projects.recent())
        }
        break
        
      case 'scans':
        if (params[0] === 'status' && params[1]) {
          // 扫描状态 -> 可能需要结果
          predictions.push(queryKeys.scans.results(params[1] as string))
        }
        break
        
      case 'mods':
        if (params[0] === 'detail' && params[1]) {
          // MOD详情 -> 预取元数据
          predictions.push(queryKeys.mods.metadata(params[1] as string))
          // MOD详情 -> 预取内容
          predictions.push(queryKeys.mods.contents(params[1] as string))
        }
        break
    }
    
    return predictions
  }
  
  /**
   * 判断是否值得预取
   */
  private async prefetchIfWorthwhile(queryKey: QueryKey) {
    if (!this.queryClient) return
    
    const keyString = JSON.stringify(queryKey)
    const access = this.accessPatterns.get(keyString)
    
    // 策略判断
    const shouldPrefetch = 
      this.config.prefetchStrategy === 'aggressive' ||
      (this.config.prefetchStrategy === 'conservative' && access && access.count > 2)
    
    if (shouldPrefetch && this.memoryUsage < this.config.memoryThreshold) {
      try {
        await this.queryClient.prefetchQuery({
          queryKey,
          staleTime: cacheStrategies.mediumFrequency.staleTime,
        })
      } catch (error) {
        console.warn('Prefetch failed:', keyString, error)
      }
    }
  }
  
  // ============================================================
  // 内存管理
  // ============================================================
  
  /**
   * 智能缓存清理
   */
  private performIntelligentCleanup() {
    if (!this.queryClient) return
    
    const cache = this.queryClient.getQueryCache()
    const queries = cache.getAll()
    
    // 计算当前缓存大小
    this.estimateMemoryUsage(queries)
    
    if (this.memoryUsage > this.config.memoryThreshold) {
      // 按优先级清理缓存
      this.cleanupByPriority(queries)
    }
    
    // 清理过期的访问模式记录
    this.cleanupAccessPatterns()
  }
  
  /**
   * 估算内存使用量
   */
  private estimateMemoryUsage(queries: any[]) {
    // 简单的内存估算（实际项目中可以使用更精确的方法）
    let totalSize = 0
    
    queries.forEach(query => {
      if (query.state.data) {
        // 粗略估算：每个查询结果约占 1KB
        totalSize += JSON.stringify(query.state.data).length / 1024
      }
    })
    
    this.memoryUsage = totalSize / 1024 // 转换为 MB
  }
  
  /**
   * 按优先级清理缓存
   */
  private cleanupByPriority(queries: any[]) {
    // 计算每个查询的优先级分数
    const scoredQueries = queries.map(query => ({
      query,
      score: this.calculateCleanupScore(query),
    }))
    
    // 按分数排序（分数越低越容易被清理）
    scoredQueries.sort((a, b) => a.score - b.score)
    
    // 清理低优先级的缓存
    const toClean = scoredQueries.slice(0, Math.ceil(scoredQueries.length * 0.3))
    
    toClean.forEach(({ query }) => {
      this.queryClient?.removeQueries({ queryKey: query.queryKey })
    })
    
    console.log(`Cleaned up ${toClean.length} cache entries`)
  }
  
  /**
   * 计算清理优先级分数
   */
  private calculateCleanupScore(query: any): number {
    const keyString = JSON.stringify(query.queryKey)
    const access = this.accessPatterns.get(keyString)
    const now = Date.now()
    
    let score = 0
    
    // 访问频率分数（访问越频繁，分数越高）
    if (access) {
      score += access.count * 10
      
      // 最近访问时间分数（越近访问，分数越高）
      const timeSinceAccess = now - access.lastAccess
      score += Math.max(0, 100 - timeSinceAccess / (60 * 1000)) // 1分钟内访问得高分
    }
    
    // 数据新鲜度分数（越新鲜，分数越高）
    if (query.state.dataUpdatedAt) {
      const dataAge = now - query.state.dataUpdatedAt
      score += Math.max(0, 50 - dataAge / (5 * 60 * 1000)) // 5分钟内的数据得高分
    }
    
    // 查询类型分数（重要查询得高分）
    const [resource] = query.queryKey
    switch (resource) {
      case 'projects':
        score += 30 // 项目相关查询较重要
        break
      case 'scans':
        score += 20 // 扫描相关查询次重要
        break
      default:
        score += 10
    }
    
    return score
  }
  
  // ============================================================
  // 访问模式跟踪
  // ============================================================
  
  /**
   * 记录查询访问
   */
  private recordAccess(queryKey: string) {
    const now = Date.now()
    const existing = this.accessPatterns.get(queryKey)
    
    if (existing) {
      existing.count++
      existing.lastAccess = now
    } else {
      this.accessPatterns.set(queryKey, {
        count: 1,
        lastAccess: now,
      })
    }
  }
  
  /**
   * 清理过期的访问模式记录
   */
  private cleanupAccessPatterns() {
    const now = Date.now()
    const maxAge = 24 * 60 * 60 * 1000 // 24小时
    
    for (const [key, access] of this.accessPatterns.entries()) {
      if (now - access.lastAccess > maxAge) {
        this.accessPatterns.delete(key)
      }
    }
  }
  
  // ============================================================
  // 监控和定时器
  // ============================================================
  
  /**
   * 启动清理定时器
   */
  private startCleanupTimer() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
    }
    
    this.cleanupTimer = setInterval(() => {
      this.performIntelligentCleanup()
    }, this.config.cleanupInterval)
  }
  
  /**
   * 设置缓存监控
   */
  private setupCacheMonitoring() {
    if (!this.queryClient) return
    
    // 监听查询状态变化
    this.queryClient.getQueryCache().subscribe((event) => {
      if (event.type === 'added') {
        this.recordAccess(JSON.stringify(event.query.queryKey))
      }
    })
  }
  
  /**
   * 获取缓存统计信息
   */
  getCacheStats() {
    if (!this.queryClient) return null
    
    const cache = this.queryClient.getQueryCache()
    const queries = cache.getAll()
    
    return {
      totalQueries: queries.length,
      activeQueries: queries.filter(q => q.getObserversCount() > 0).length,
      staleQueries: queries.filter(q => q.isStale()).length,
      errorQueries: queries.filter(q => q.state.status === 'error').length,
      estimatedMemoryUsage: this.memoryUsage,
      accessPatterns: this.accessPatterns.size,
    }
  }
  
  /**
   * 手动清理缓存
   */
  manualCleanup() {
    this.performIntelligentCleanup()
  }
  
  /**
   * 销毁实例
   */
  destroy() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
    }
    this.accessPatterns.clear()
  }
}

// ============================================================
// 缓存实用工具
// ============================================================

/**
 * 获取推荐的缓存策略
 */
export const getRecommendedCacheStrategy = (queryKey: QueryKey): CacheStrategy => {
  const [resource, operation] = queryKey
  
  // 根据资源类型和操作推荐策略
  switch (resource) {
    case 'projects':
      if (operation === 'list' || operation === 'recent') {
        return cacheStrategies.highFrequency
      }
      if (operation === 'statistics' || operation === 'health') {
        return cacheStrategies.realtime
      }
      if (operation === 'config' || operation === 'global') {
        return cacheStrategies.static
      }
      return cacheStrategies.mediumFrequency
      
    case 'scans':
      if (operation === 'status' || operation === 'active' || operation === 'service-status') {
        return cacheStrategies.realtime
      }
      if (operation === 'history' || operation === 'statistics') {
        return cacheStrategies.highFrequency
      }
      if (operation === 'presets') {
        return cacheStrategies.static
      }
      return cacheStrategies.mediumFrequency
      
    case 'sync':
      if (operation === 'status' || operation === 'conflicts') {
        return cacheStrategies.realtime
      }
      if (operation === 'config') {
        return cacheStrategies.static
      }
      return cacheStrategies.mediumFrequency
      
    default:
      return cacheStrategies.mediumFrequency
  }
}

/**
 * 创建优化的查询选项
 */
export const createOptimizedQueryOptions = (queryKey: QueryKey) => {
  const strategy = getRecommendedCacheStrategy(queryKey)
  
  return {
    ...strategy,
    meta: {
      cacheStrategy: strategy,
      optimized: true,
    },
  }
}

// ============================================================
// 导出单例实例
// ============================================================

export const cacheOptimizer = CacheOptimizer.getInstance()