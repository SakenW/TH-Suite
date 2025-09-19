/**
 * React Query 配置
 * 配置全局查询设置、缓存策略、错误处理等
 */

import { QueryClient, DefaultOptions } from '@tanstack/react-query'

/**
 * React Query 默认配置选项
 */
const defaultOptions: DefaultOptions = {
  queries: {
    // 数据缓存策略
    staleTime: 5 * 60 * 1000, // 5分钟内数据视为新鲜
    gcTime: 30 * 60 * 1000, // 30分钟后回收未使用的缓存
    
    // 重试配置
    retry: (failureCount, error: any) => {
      // 4xx 错误不重试
      if (error?.status >= 400 && error?.status < 500) {
        return false
      }
      // 最多重试2次
      return failureCount < 2
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    
    // 重新获取配置
    refetchOnWindowFocus: false, // 窗口聚焦时不自动重新获取
    refetchOnReconnect: true, // 网络重连时重新获取
    refetchOnMount: true, // 组件挂载时重新获取
    
    // 网络模式
    networkMode: 'online',
  },
  mutations: {
    // 变更操作重试配置
    retry: (failureCount, error: any) => {
      // 4xx 错误不重试
      if (error?.status >= 400 && error?.status < 500) {
        return false
      }
      // 最多重试1次
      return failureCount < 1
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    
    // 网络模式
    networkMode: 'online',
  },
}

/**
 * 创建 Query Client 实例
 */
export const createQueryClient = (): QueryClient => {
  return new QueryClient({
    defaultOptions,
    logger: {
      log: console.log,
      warn: console.warn,
      error: (error) => {
        console.error('React Query Error:', error)
        // 可以集成错误报告服务
      },
    },
  })
}

/**
 * Query Key 工厂
 * 统一管理所有查询键，避免重复和冲突
 */
export const queryKeys = {
  // 项目相关查询
  projects: {
    all: ['projects'] as const,
    lists: () => [...queryKeys.projects.all, 'list'] as const,
    list: (params?: Record<string, any>) => 
      [...queryKeys.projects.lists(), params] as const,
    details: () => [...queryKeys.projects.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.projects.details(), id] as const,
    statistics: () => [...queryKeys.projects.all, 'statistics'] as const,
    statistic: (id: string) => [...queryKeys.projects.statistics(), id] as const,
    config: (id: string) => [...queryKeys.projects.all, 'config', id] as const,
    health: (id: string) => [...queryKeys.projects.all, 'health', id] as const,
    recent: () => [...queryKeys.projects.all, 'recent'] as const,
    global: () => [...queryKeys.projects.all, 'global'] as const,
  },
  
  // 扫描相关查询
  scans: {
    all: ['scans'] as const,
    lists: () => [...queryKeys.scans.all, 'list'] as const,
    list: (params?: Record<string, any>) => 
      [...queryKeys.scans.lists(), params] as const,
    details: () => [...queryKeys.scans.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.scans.details(), id] as const,
    status: (id: string) => [...queryKeys.scans.all, 'status', id] as const,
    results: (id: string) => [...queryKeys.scans.all, 'results', id] as const,
    active: () => [...queryKeys.scans.all, 'active'] as const,
    history: () => [...queryKeys.scans.all, 'history'] as const,
    statistics: () => [...queryKeys.scans.all, 'statistics'] as const,
    serviceStatus: () => [...queryKeys.scans.all, 'service-status'] as const,
    presets: () => [...queryKeys.scans.all, 'presets'] as const,
  },
  
  // MOD相关查询
  mods: {
    all: ['mods'] as const,
    lists: () => [...queryKeys.mods.all, 'list'] as const,
    list: (params?: Record<string, any>) => 
      [...queryKeys.mods.lists(), params] as const,
    details: () => [...queryKeys.mods.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.mods.details(), id] as const,
    metadata: (id: string) => [...queryKeys.mods.all, 'metadata', id] as const,
    contents: (id: string) => [...queryKeys.mods.all, 'contents', id] as const,
  },
  
  // 资源包相关查询
  packs: {
    all: ['packs'] as const,
    lists: () => [...queryKeys.packs.all, 'list'] as const,
    list: (params?: Record<string, any>) => 
      [...queryKeys.packs.lists(), params] as const,
    details: () => [...queryKeys.packs.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.packs.details(), id] as const,
    metadata: (id: string) => [...queryKeys.packs.all, 'metadata', id] as const,
    contents: (id: string) => [...queryKeys.packs.all, 'contents', id] as const,
  },
  
  // 同步相关查询
  sync: {
    all: ['sync'] as const,
    status: () => [...queryKeys.sync.all, 'status'] as const,
    config: () => [...queryKeys.sync.all, 'config'] as const,
    history: () => [...queryKeys.sync.all, 'history'] as const,
    conflicts: () => [...queryKeys.sync.all, 'conflicts'] as const,
  },
  
  // 系统相关查询
  system: {
    all: ['system'] as const,
    info: () => [...queryKeys.system.all, 'info'] as const,
    health: () => [...queryKeys.system.all, 'health'] as const,
  },
} as const

/**
 * 无效化查询的辅助函数
 */
export const invalidateQueries = {
  // 无效化所有项目相关查询
  allProjects: (queryClient: QueryClient) => {
    return queryClient.invalidateQueries({ queryKey: queryKeys.projects.all })
  },
  
  // 无效化特定项目查询
  project: (queryClient: QueryClient, projectId: string) => {
    return queryClient.invalidateQueries({ 
      queryKey: queryKeys.projects.detail(projectId) 
    })
  },
  
  // 无效化所有扫描相关查询
  allScans: (queryClient: QueryClient) => {
    return queryClient.invalidateQueries({ queryKey: queryKeys.scans.all })
  },
  
  // 无效化特定扫描查询
  scan: (queryClient: QueryClient, scanId: string) => {
    return queryClient.invalidateQueries({ 
      queryKey: queryKeys.scans.detail(scanId) 
    })
  },
}

/**
 * 预取数据的辅助函数
 */
export const prefetchQueries = {
  // 预取项目列表
  projectList: async (queryClient: QueryClient, params?: Record<string, any>) => {
    // 实现预取逻辑
  },
  
  // 预取项目详情
  projectDetail: async (queryClient: QueryClient, projectId: string) => {
    // 实现预取逻辑
  },
}

/**
 * 缓存优化配置
 */
export const cacheConfig = {
  // 高频查询的缓存时间更长
  highFrequency: {
    staleTime: 10 * 60 * 1000, // 10分钟
    gcTime: 60 * 60 * 1000, // 1小时
  },
  
  // 低频查询的缓存时间适中
  lowFrequency: {
    staleTime: 30 * 60 * 1000, // 30分钟
    gcTime: 2 * 60 * 60 * 1000, // 2小时
  },
  
  // 实时数据的缓存时间较短
  realtime: {
    staleTime: 30 * 1000, // 30秒
    gcTime: 5 * 60 * 1000, // 5分钟
  },
  
  // 静态数据的缓存时间很长
  static: {
    staleTime: 60 * 60 * 1000, // 1小时
    gcTime: 24 * 60 * 60 * 1000, // 24小时
  },
} as const