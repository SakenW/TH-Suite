/**
 * 项目相关的React Query hooks
 * 提供类型安全的项目数据查询和变更操作
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
  Project, 
  ProjectCreateRequest, 
  ProjectUpdateRequest,
  ProjectStatistics,
  PaginatedResponse,
  ServiceResult 
} from '../../services/api/types'
import { ProjectSearchParams, projectApiService } from '../../services/api/ProjectApiService'
import { queryKeys, cacheConfig, invalidateQueries } from '../../config/reactQuery'

// ============================================================
// 查询 Hooks
// ============================================================

/**
 * 获取项目列表
 */
export const useProjects = (
  params?: ProjectSearchParams,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<Project>>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.list(params),
    queryFn: () => projectApiService.getProjects(params),
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取项目详情
 */
export const useProject = (
  projectId: string,
  includeStatistics = false,
  options?: Partial<UseQueryOptions<ServiceResult<Project>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId),
    queryFn: () => projectApiService.getProject(projectId, includeStatistics),
    enabled: !!projectId,
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 搜索项目
 */
export const useProjectSearch = (
  query: string,
  params?: ProjectSearchParams,
  options?: Partial<UseQueryOptions<ServiceResult<PaginatedResponse<Project>>>>
) => {
  return useQuery({
    queryKey: [...queryKeys.projects.lists(), 'search', query, params],
    queryFn: () => projectApiService.searchProjects(query, params),
    enabled: !!query && query.length >= 2,
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

/**
 * 获取最近使用的项目
 */
export const useRecentProjects = (
  limit = 10,
  options?: Partial<UseQueryOptions<ServiceResult<Project[]>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.recent(),
    queryFn: () => projectApiService.getRecentProjects(limit),
    ...cacheConfig.highFrequency,
    ...options,
  })
}

/**
 * 获取项目统计信息
 */
export const useProjectStatistics = (
  projectId: string,
  options?: Partial<UseQueryOptions<ServiceResult<ProjectStatistics>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.statistic(projectId),
    queryFn: () => projectApiService.getProjectStatistics(projectId),
    enabled: !!projectId,
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

/**
 * 获取全局项目统计
 */
export const useGlobalStatistics = (
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.global(),
    queryFn: () => projectApiService.getGlobalStatistics(),
    ...cacheConfig.lowFrequency,
    ...options,
  })
}

/**
 * 获取项目配置
 */
export const useProjectConfig = (
  projectId: string,
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.config(projectId),
    queryFn: () => projectApiService.getProjectConfig(projectId),
    enabled: !!projectId,
    ...cacheConfig.static,
    ...options,
  })
}

/**
 * 检查项目健康状态
 */
export const useProjectHealth = (
  projectId: string,
  options?: Partial<UseQueryOptions<ServiceResult<any>>>
) => {
  return useQuery({
    queryKey: queryKeys.projects.health(projectId),
    queryFn: () => projectApiService.checkProjectHealth(projectId),
    enabled: !!projectId,
    ...cacheConfig.realtime,
    ...options,
  })
}

/**
 * 无限滚动获取项目列表
 */
export const useInfiniteProjects = (
  params?: Omit<ProjectSearchParams, 'page'>,
  options?: Partial<UseInfiniteQueryOptions<ServiceResult<PaginatedResponse<Project>>>>
) => {
  return useInfiniteQuery({
    queryKey: [...queryKeys.projects.lists(), 'infinite', params],
    queryFn: ({ pageParam = 1 }) =>
      projectApiService.getProjects({ ...params, page: pageParam }),
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
 * 创建项目
 */
export const useCreateProject = (
  options?: UseMutationOptions<
    ServiceResult<Project>,
    Error,
    ProjectCreateRequest
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: ProjectCreateRequest) =>
      projectApiService.createProject(request),
    onSuccess: (data) => {
      if (data.success && data.data) {
        // 将新项目添加到缓存
        queryClient.setQueryData(
          queryKeys.projects.detail(data.data.id),
          data
        )
        
        // 无效化项目列表查询
        invalidateQueries.allProjects(queryClient)
      }
    },
    ...options,
  })
}

/**
 * 更新项目
 */
export const useUpdateProject = (
  options?: UseMutationOptions<
    ServiceResult<Project>,
    Error,
    { projectId: string; request: ProjectUpdateRequest }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, request }) =>
      projectApiService.updateProject(projectId, request),
    onSuccess: (data, variables) => {
      if (data.success && data.data) {
        // 更新项目详情缓存
        queryClient.setQueryData(
          queryKeys.projects.detail(variables.projectId),
          data
        )
        
        // 无效化相关查询
        invalidateQueries.allProjects(queryClient)
        invalidateQueries.project(queryClient, variables.projectId)
      }
    },
    ...options,
  })
}

/**
 * 删除项目
 */
export const useDeleteProject = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    { projectId: string; force?: boolean }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, force = false }) =>
      projectApiService.deleteProject(projectId, force),
    onSuccess: (data, variables) => {
      if (data.success) {
        // 从缓存中移除项目
        queryClient.removeQueries({
          queryKey: queryKeys.projects.detail(variables.projectId)
        })
        
        // 无效化项目列表查询
        invalidateQueries.allProjects(queryClient)
      }
    },
    ...options,
  })
}

/**
 * 归档项目
 */
export const useArchiveProject = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    { projectId: string; reason?: string }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, reason }) =>
      projectApiService.archiveProject(projectId, reason),
    onSuccess: (data, variables) => {
      if (data.success) {
        // 无效化相关查询
        invalidateQueries.project(queryClient, variables.projectId)
        invalidateQueries.allProjects(queryClient)
      }
    },
    ...options,
  })
}

/**
 * 恢复归档项目
 */
export const useUnarchiveProject = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) =>
      projectApiService.unarchiveProject(projectId),
    onSuccess: (data, projectId) => {
      if (data.success) {
        // 无效化相关查询
        invalidateQueries.project(queryClient, projectId)
        invalidateQueries.allProjects(queryClient)
      }
    },
    ...options,
  })
}

/**
 * 刷新项目统计
 */
export const useRefreshProjectStatistics = (
  options?: UseMutationOptions<
    ServiceResult<ProjectStatistics>,
    Error,
    string
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) =>
      projectApiService.refreshProjectStatistics(projectId),
    onSuccess: (data, projectId) => {
      if (data.success && data.data) {
        // 更新统计信息缓存
        queryClient.setQueryData(
          queryKeys.projects.statistic(projectId),
          data
        )
        
        // 无效化全局统计
        queryClient.invalidateQueries({
          queryKey: queryKeys.projects.global()
        })
      }
    },
    ...options,
  })
}

/**
 * 更新项目配置
 */
export const useUpdateProjectConfig = (
  options?: UseMutationOptions<
    ServiceResult<boolean>,
    Error,
    { projectId: string; configUpdate: Record<string, any> }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, configUpdate }) =>
      projectApiService.updateProjectConfig(projectId, configUpdate),
    onSuccess: (data, variables) => {
      if (data.success) {
        // 无效化项目配置缓存
        queryClient.invalidateQueries({
          queryKey: queryKeys.projects.config(variables.projectId)
        })
      }
    },
    ...options,
  })
}

/**
 * 验证项目路径
 */
export const useValidateProjectPaths = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    { sourcePath: string; outputPath: string }
  >
) => {
  return useMutation({
    mutationFn: ({ sourcePath, outputPath }) =>
      projectApiService.validateProjectPaths(sourcePath, outputPath),
    ...options,
  })
}

/**
 * 导出项目配置
 */
export const useExportProjectConfig = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    string
  >
) => {
  return useMutation({
    mutationFn: (projectId: string) =>
      projectApiService.exportProjectConfig(projectId),
    ...options,
  })
}

/**
 * 导入项目配置
 */
export const useImportProjectConfig = (
  options?: UseMutationOptions<
    ServiceResult<any>,
    Error,
    { configData: Record<string, any>; options?: any }
  >
) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ configData, options: importOptions }) =>
      projectApiService.importProjectConfig(configData, importOptions),
    onSuccess: (data) => {
      if (data.success && data.data?.imported_project_id) {
        // 无效化项目列表查询
        invalidateQueries.allProjects(queryClient)
      }
    },
    ...options,
  })
}

// ============================================================
// 辅助 Hooks
// ============================================================

/**
 * 预取项目详情
 */
export const usePrefetchProject = () => {
  const queryClient = useQueryClient()

  return (projectId: string, includeStatistics = false) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.projects.detail(projectId),
      queryFn: () => projectApiService.getProject(projectId, includeStatistics),
      ...cacheConfig.highFrequency,
    })
  }
}

/**
 * 获取项目缓存状态
 */
export const useProjectCacheStatus = (projectId: string) => {
  const queryClient = useQueryClient()
  
  return {
    isCached: queryClient.getQueryData(queryKeys.projects.detail(projectId)) !== undefined,
    isStale: queryClient.getQueryState(queryKeys.projects.detail(projectId))?.isStale ?? true,
  }
}