/**
 * 扫描相关的React Query hooks
 * 提供类型安全的扫描数据查询和变更操作
 */

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
  useInfiniteQuery,
  UseInfiniteQueryOptions
} from '@tanstack/react-query'
import { 
  ScanRequest, 
  ScanStatus, 
  ScanResult, 
  ScanOptions,
  PaginatedResponse,
  ServiceResult 
} from '../../services/api/types'
import { scanApiService } from '../../services/api/ScanApiService'
import { queryKeys, cacheConfig, invalidateQueries } from '../../config/reactQuery'

// ============================================================
// 查询 Hooks
// ============================================================

/**
 * 获取扫描状态
 */
export const useScanStatus = (
  scanId: string,
  options?: Partial<UseQueryOptions<ServiceResult<ScanStatus>>>
) => {
  return useQuery({
    queryKey: queryKeys.scans.status(scanId),
    queryFn: () => scanApiService.getScanStatus(scanId),
    enabled: !!scanId,
    ...cacheConfig.realtime,
    refetchInterval: (data) => {
      // 如果扫描还在进行中，定时刷新
      const status = data?.success ? data.data?.status : null
      return status === 'running' || status === 'pending' ? 2000 : false
    },
    ...options,
  })
}

/**
 * 获取扫描结果
 */
export const useScanResults = (
  scanId: string,
  options?: Partial<UseQueryOptions<ServiceResult<ScanResult>>>
) => {
  return useQuery({
    queryKey: queryKeys.scans.results(scanId),
    queryFn: () => scanApiService.getScanResults(scanId),
    enabled: !!scanId,
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

/**
 * 获取活跃扫描列表
 */
export const useActiveScans = (
  projectId?: string,
  options?: Partial<UseQueryOptions<ServiceResult<ScanStatus[]>>>
) => {
  return useQuery({
    queryKey: [...queryKeys.scans.active(), projectId],
    queryFn: () => scanApiService.getActiveScans(projectId),
    ...cacheConfig.realtime,
    refetchInterval: 5000, // 每5秒刷新活跃扫描
    ...options,
  })
}

/**
 * 获取扫描历史
 */
export const useScanHistory = (
  projectId?: string,
  page = 1,
  limit = 20,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<ScanStatus>>>>
) => {
  return useQuery({
    queryKey: [...queryKeys.scans.history(), projectId, page, limit],
    queryFn: () => scanApiService.getScanHistory(projectId, page, limit),
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取扫描统计信息
 */
export const useScanStatistics = (
  projectId?: string,
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: [...queryKeys.scans.statistics(), projectId],
    queryFn: () => scanApiService.getScanStatistics(projectId),
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

/**
 * 检查扫描服务状态
 */
export const useScanServiceStatus = (
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.scans.serviceStatus(),
    queryFn: () => scanApiService.checkScanServiceStatus(),
    ...cacheConfig.realtime,
    refetchInterval: 10000, // 每10秒检查服务状态
    retry: 3,
    ...options,
  })
}

/**
 * 获取扫描预设配置
 */
export const useScanPresets = (
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.scans.presets(),
    queryFn: () => scanApiService.getScanPresets(),
    ...cacheConfig.static,
    ...options,
  })
}

/**
 * 无限滚动获取扫描历史
 */
export const useInfiniteScanHistory = (
  projectId?: string,
  limit = 20,
  options?: Partial<UseInfiniteQueryOptions<ServiceResult<PaginatedResponse<ScanStatus>>>>
) => {
  return useInfiniteQuery({
    queryKey: [...queryKeys.scans.history(), 'infinite', projectId, limit],
    queryFn: ({ pageParam = 1 }) =>
      scanApiService.getScanHistory(projectId, pageParam, limit),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (!lastPage.success || !lastPage.data) return undefined
      const { page, total_pages } = lastPage.data
      return page < total_pages ? page + 1 : undefined
    },
    ...cacheConfig.highFrequency,
    ...options,
  })
}

// ============================================================
// 变更 Hooks
// ============================================================

/**
 * 启动扫描任务
 */
export const useStartScan = (
  options?: UseMutationOptions<
    ServiceResult<{ scan_id: string }>,
    Error,
    ScanRequest
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: ScanRequest) =>
      scanApiService.startScan(request),
    onSuccess: (data) => {
      if (data.success && data.data) {
        // 无效化活跃扫描查询
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.active()
        })
        
        // 无效化扫描历史查询
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.history()
        })
        
        // 开始轮询新扫描的状态
        queryClient.prefetchQuery({
          queryKey: queryKeys.scans.status(data.data.scan_id),
          queryFn: () => scanApiService.getScanStatus(data.data.scan_id),
        })
      }
    },
    ...options,
  })
}

/**
 * 取消扫描任务
 */
export const useCancelScan = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    { scanId: string; reason?: string }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ scanId, reason }) =>
      scanApiService.cancelScan(scanId, reason),
    onSuccess: (data, variables) => {
      if (data.success) {
        // 立即更新扫描状态缓存
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.status(variables.scanId)
        })
        
        // 无效化活跃扫描查询
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.active()
        })
      }
    },
    ...options,
  })
}

/**
 * 暂停扫描任务
 */
export const usePauseScan = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (scanId: string) =>
      scanApiService.pauseScan(scanId),
    onSuccess: (data, scanId) => {
      if (data.success) {
        // 立即更新扫描状态缓存
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.status(scanId)
        })
      }
    },
    ...options,
  })
}

/**
 * 恢复扫描任务
 */
export const useResumeScan = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (scanId: string) =>
      scanApiService.resumeScan(scanId),
    onSuccess: (data, scanId) => {
      if (data.success) {
        // 立即更新扫描状态缓存
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.status(scanId)
        })
      }
    },
    ...options,
  })
}

/**
 * 删除扫描记录
 */
export const useDeleteScanRecord = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (scanId: string) =>
      scanApiService.deleteScanRecord(scanId),
    onSuccess: (data, scanId) => {
      if (data.success) {
        // 从缓存中移除扫描记录
        queryClient.removeQueries({
          queryKey: queryKeys.scans.detail(scanId)
        })
        
        // 无效化扫描历史查询
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.history()
        })
        
        // 无效化统计信息
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.statistics()
        })
      }
    },
    ...options,
  })
}

/**
 * 验证扫描目录
 */
export const useValidateScanDirectory = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    string
  >
) => {
  return useMutation({
    mutationFn: (directory: string) =>
      scanApiService.validateScanDirectory(directory),
    ...options,
  })
}

/**
 * 批量取消扫描
 */
export const useCancelMultipleScans = (
  options?: UseMutationOptions<
    ServiceResult<any[]>,
    Error,
    { scanIds: string[]; reason?: string }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ scanIds, reason }) =>
      scanApiService.cancelMultipleScans(scanIds, reason),
    onSuccess: (data, variables) => {
      if (data.success) {
        // 无效化所有相关扫描的状态
        variables.scanIds.forEach(scanId => {
          queryClient.invalidateQueries({
            queryKey: queryKeys.scans.status(scanId)
          })
        })
        
        // 无效化活跃扫描查询
        queryClient.invalidateQueries({
          queryKey: queryKeys.scans.active()
        })
      }
    },
    ...options,
  })
}

// ============================================================
// 实时扫描 Hooks
// ============================================================

/**
 * 实时监控扫描进度
 * 集成了状态轮询和智能重试
 */
export const useRealTimeScanProgress = (
  scanId: string,
  options?: {
    onStatusChange?: (status: ScanStatus) => void
    onComplete?: (result: ScanResult) => void
    onError?: (error: any) => void
    pollInterval?: number
  }
) => {
  const { onStatusChange, onComplete, onError, pollInterval = 2000 } = options || {}
  
  const statusQuery = useScanStatus(scanId, {
    refetchInterval: (data) => {
      const status = data?.success ? data.data?.status : null
      
      // 调用状态变化回调
      if (data?.success && data.data) {
        onStatusChange?.(data.data)
      }
      
      // 如果扫描完成，获取结果
      if (status === 'completed') {
        scanApiService.getScanResults(scanId)
          .then(result => {
            if (result.success && result.data) {
              onComplete?.(result.data)
            }
          })
          .catch(onError)
        return false
      }
      
      // 如果扫描失败或取消，停止轮询
      if (status === 'failed' || status === 'cancelled') {
        if (data?.success && data.data?.error) {
          onError?.(new Error(data.data.error))
        }
        return false
      }
      
      // 继续轮询
      return status === 'running' || status === 'pending' ? pollInterval : false
    },
  })
  
  return statusQuery
}

/**
 * 扫描完成等待Hook
 * 提供Promise接口等待扫描完成
 */
export const useScanCompletion = () => {
  return (scanId: string, timeoutMs = 300000) => {
    return scanApiService.waitForScanCompletion(
      scanId,
      undefined, // onProgress回调由实时hook处理
      2000, // 2秒轮询间隔
      timeoutMs
    )
  }
}

// ============================================================
// 辅助 Hooks
// ============================================================

/**
 * 预取扫描结果
 */
export const usePrefetchScanResults = () => {
  const queryClient = useQueryClient()

  return (scanId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.scans.results(scanId),
      queryFn: () => scanApiService.getScanResults(scanId),
      ...cacheConfig.lowFrequency,
    })
  }
}

/**
 * 获取扫描缓存状态
 */
export const useScanCacheStatus = (scanId: string) => {
  const queryClient = useQueryClient()
  
  return {
    isStatusCached: queryClient.getQueryData(queryKeys.scans.status(scanId)) !== undefined,
    isResultsCached: queryClient.getQueryData(queryKeys.scans.results(scanId)) !== undefined,
    isStatusStale: queryClient.getQueryState(queryKeys.scans.status(scanId))?.isStale ?? true,
  }
}

/**
 * 扫描操作组合Hook
 * 提供常用扫描操作的组合接口
 */
export const useScanOperations = (scanId?: string) => {
  const startScan = useStartScan()
  const cancelScan = useCancelScan()
  const pauseScan = usePauseScan()
  const resumeScan = useResumeScan()
  const deleteScan = useDeleteScanRecord()
  
  return {
    start: startScan.mutate,
    cancel: scanId ? (reason?: string) => cancelScan.mutate({ scanId, reason }) : undefined,
    pause: scanId ? () => pauseScan.mutate(scanId) : undefined,
    resume: scanId ? () => resumeScan.mutate(scanId) : undefined,
    delete: scanId ? () => deleteScan.mutate(scanId) : undefined,
    
    // 状态
    isStarting: startScan.isPending,
    isCanceling: cancelScan.isPending,
    isPausing: pauseScan.isPending,
    isResuming: resumeScan.isPending,
    isDeleting: deleteScan.isPending,
    
    // 错误
    startError: startScan.error,
    cancelError: cancelScan.error,
    pauseError: pauseScan.error,
    resumeError: resumeScan.error,
    deleteError: deleteScan.error,
  }
}