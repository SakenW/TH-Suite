/**
 * 同步相关的React Query hooks
 * 提供类型安全的同步数据查询和变更操作
 */

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions
} from '@tanstack/react-query'
import { 
  ServiceResult
} from '../../services/api/types'
import { syncApiService } from '../../services/api/SyncApiService'
import { queryKeys, cacheConfig } from '../../config/reactQuery'

// ============================================================
// 查询 Hooks
// ============================================================

/**
 * 获取同步状态
 */
export const useSyncStatus = (
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.sync.status(),
    queryFn: () => syncApiService.getSyncStatus(),
    ...cacheConfig.realtime,
    refetchInterval: 5000, // 每5秒刷新同步状态
    ...options,
  })
}

/**
 * 获取同步配置
 */
export const useSyncConfig = (
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.sync.config(),
    queryFn: () => syncApiService.getSyncConfig(),
    ...cacheConfig.static,
    ...options,
  })
}

/**
 * 获取同步历史
 */
export const useSyncHistory = (
  params?: Record<string, any>,
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: [...queryKeys.sync.history(), params],
    queryFn: () => syncApiService.getSyncHistory(params),
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取同步冲突
 */
export const useSyncConflicts = (
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.sync.conflicts(),
    queryFn: () => syncApiService.getSyncConflicts(),
    ...cacheConfig.realtime,
    ...options,
  })
}

// ============================================================
// 变更 Hooks
// ============================================================

/**
 * 启动同步
 */
export const useStartSync = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    any
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (syncRequest: any) =>
      syncApiService.startSync(syncRequest),
    onSuccess: () => {
      // 无效化同步状态查询
      queryClient.invalidateQueries({
        queryKey: queryKeys.sync.status()
      })
    },
    ...options,
  })
}

/**
 * 停止同步
 */
export const useStopSync = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    void
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => syncApiService.stopSync(),
    onSuccess: () => {
      // 无效化同步状态查询
      queryClient.invalidateQueries({
        queryKey: queryKeys.sync.status()
      })
    },
    ...options,
  })
}

/**
 * 更新同步配置
 */
export const useUpdateSyncConfig = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    any
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (config: any) =>
      syncApiService.updateSyncConfig(config),
    onSuccess: (data) => {
      if (data.success) {
        // 更新同步配置缓存
        queryClient.invalidateQueries({
          queryKey: queryKeys.sync.config()
        })
      }
    },
    ...options,
  })
}

/**
 * 解决同步冲突
 */
export const useResolveSyncConflict = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    { conflictId: string; resolution: any }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ conflictId, resolution }) =>
      syncApiService.resolveSyncConflict(conflictId, resolution),
    onSuccess: () => {
      // 无效化冲突查询
      queryClient.invalidateQueries({
        queryKey: queryKeys.sync.conflicts()
      })
      
      // 无效化同步状态
      queryClient.invalidateQueries({
        queryKey: queryKeys.sync.status()
      })
    },
    ...options,
  })
}