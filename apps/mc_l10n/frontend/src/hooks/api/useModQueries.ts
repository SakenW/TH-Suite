/**
 * MOD相关的React Query hooks
 * 提供类型安全的MOD数据查询和变更操作
 */

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions
} from '@tanstack/react-query'
import { 
  ModInfo,
  ModContent,
  ModMetadata,
  ServiceResult,
  PaginatedResponse
} from '../../services/api/types'
import { modApiService } from '../../services/api/ModApiService'
import { queryKeys, cacheConfig } from '../../config/reactQuery'

// ============================================================
// 查询 Hooks
// ============================================================

/**
 * 获取MOD列表
 */
export const useMods = (
  projectId?: string,
  params?: Record<string, any>,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<ModInfo>>>>
) => {
  return useQuery({
    queryKey: queryKeys.mods.list({ projectId, ...params }),
    queryFn: () => modApiService.getMods(projectId, params),
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取MOD详情
 */
export const useMod = (
  modId: string,
  options?: Partial<UseQueryOptions<ServiceResult<ModInfo>>>
) => {
  return useQuery({
    queryKey: queryKeys.mods.detail(modId),
    queryFn: () => modApiService.getMod(modId),
    enabled: !!modId,
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取MOD元数据
 */
export const useModMetadata = (
  modId: string,
  options?: Partial<UseQueryOptions<ServiceResult<ModMetadata>>>
) => {
  return useQuery({
    queryKey: queryKeys.mods.metadata(modId),
    queryFn: () => modApiService.getModMetadata(modId),
    enabled: !!modId,
    ...cacheConfig.static,
    ...options,
  })
}

/**
 * 获取MOD内容
 */
export const useModContents = (
  modId: string,
  params?: Record<string, any>,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<ModContent>>>>
) => {
  return useQuery({
    queryKey: queryKeys.mods.contents(modId),
    queryFn: () => modApiService.getModContents(modId, params),
    enabled: !!modId,
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

// ============================================================
// 变更 Hooks
// ============================================================

/**
 * 更新MOD元数据
 */
export const useUpdateModMetadata = (
  options?: UseMutationOptions<
    ServiceResult<ModMetadata>,
    Error,
    { modId: string; metadata: Partial<ModMetadata> }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ modId, metadata }) =>
      modApiService.updateModMetadata(modId, metadata),
    onSuccess: (data, variables) => {
      if (data.success && data.data) {
        // 更新元数据缓存
        queryClient.setQueryData(
          queryKeys.mods.metadata(variables.modId),
          data
        )
        
        // 无效化MOD详情
        queryClient.invalidateQueries({
          queryKey: queryKeys.mods.detail(variables.modId)
        })
      }
    },
    ...options,
  })
}

/**
 * 删除MOD
 */
export const useDeleteMod = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (modId: string) =>
      modApiService.deleteMod(modId),
    onSuccess: (data, modId) => {
      if (data.success) {
        // 从缓存中移除MOD
        queryClient.removeQueries({
          queryKey: queryKeys.mods.detail(modId)
        })
        
        // 无效化MOD列表
        queryClient.invalidateQueries({
          queryKey: queryKeys.mods.lists()
        })
      }
    },
    ...options,
  })
}