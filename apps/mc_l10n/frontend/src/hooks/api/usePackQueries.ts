/**
 * 资源包相关的React Query hooks
 * 提供类型安全的资源包数据查询和变更操作
 */

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions
} from '@tanstack/react-query'
import { 
  PackInfo,
  PackContent,
  PackMetadata,
  ServiceResult,
  PaginatedResponse
} from '../../services/api/types'
import { packApiService } from '../../services/api/PackApiService'
import { queryKeys, cacheConfig } from '../../config/reactQuery'

// ============================================================
// 查询 Hooks
// ============================================================

/**
 * 获取资源包列表
 */
export const usePacks = (
  projectId?: string,
  params?: Record<string, any>,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<PackInfo>>>>
) => {
  return useQuery({
    queryKey: queryKeys.packs.list({ projectId, ...params }),
    queryFn: () => packApiService.getPacks(projectId, params),
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取资源包详情
 */
export const usePack = (
  packId: string,
  options?: Partial<UseQueryOptions<ServiceResult<PackInfo>>>
) => {
  return useQuery({
    queryKey: queryKeys.packs.detail(packId),
    queryFn: () => packApiService.getPack(packId),
    enabled: !!packId,
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取资源包元数据
 */
export const usePackMetadata = (
  packId: string,
  options?: Partial<UseQueryOptions<ServiceResult<PackMetadata>>>
) => {
  return useQuery({
    queryKey: queryKeys.packs.metadata(packId),
    queryFn: () => packApiService.getPackMetadata(packId),
    enabled: !!packId,
    ...cacheConfig.static,
    ...options,
  })
}

/**
 * 获取资源包内容
 */
export const usePackContents = (
  packId: string,
  params?: Record<string, any>,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<PackContent>>>>
) => {
  return useQuery({
    queryKey: queryKeys.packs.contents(packId),
    queryFn: () => packApiService.getPackContents(packId, params),
    enabled: !!packId,
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

// ============================================================
// 变更 Hooks
// ============================================================

/**
 * 更新资源包元数据
 */
export const useUpdatePackMetadata = (
  options?: UseMutationOptions<
    ServiceResult<PackMetadata>,
    Error,
    { packId: string; metadata: Partial<PackMetadata> }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ packId, metadata }) =>
      packApiService.updatePackMetadata(packId, metadata),
    onSuccess: (data, variables) => {
      if (data.success && data.data) {
        // 更新元数据缓存
        queryClient.setQueryData(
          queryKeys.packs.metadata(variables.packId),
          data
        )
        
        // 无效化资源包详情
        queryClient.invalidateQueries({
          queryKey: queryKeys.packs.detail(variables.packId)
        })
      }
    },
    ...options,
  })
}

/**
 * 删除资源包
 */
export const useDeletePack = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (packId: string) =>
      packApiService.deletePack(packId),
    onSuccess: (data, packId) => {
      if (data.success) {
        // 从缓存中移除资源包
        queryClient.removeQueries({
          queryKey: queryKeys.packs.detail(packId)
        })
        
        // 无效化资源包列表
        queryClient.invalidateQueries({
          queryKey: queryKeys.packs.lists()
        })
      }
    },
    ...options,
  })
}