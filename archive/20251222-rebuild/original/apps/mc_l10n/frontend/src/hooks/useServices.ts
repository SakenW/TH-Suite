/**
 * 服务访问 Hooks - 最优化版本
 * 提供类型安全的服务访问和状态管理
 */

import { useCallback, useMemo } from 'react'
import {
  getProjectService,
  getScanService,
  type ProjectService,
  type ScanService,
  type ServiceResult,
} from '../services'

/**
 * 项目服务 Hook
 */
export function useProject() {
  // 获取服务实例（不是hook调用，是普通函数）
  const service = useMemo(() => getProjectService(), [])

  // 提取所有useCallback到外层
  const createProject = useCallback(
    async (request: any) => {
      return await service.create(request)
    },
    [service],
  )

  const listProjects = useCallback(
    async (options?: any) => {
      return await service.list(options)
    },
    [service],
  )

  const getProject = useCallback(
    async (id: string) => {
      return await service.getById(id)
    },
    [service],
  )

  const updateProject = useCallback(
    async (id: string, data: any) => {
      return await service.update(id, data)
    },
    [service],
  )

  const deleteProject = useCallback(
    async (id: string) => {
      return await service.delete(id)
    },
    [service],
  )

  return useMemo(
    () => ({
      service,
      createProject,
      listProjects,
      getProject,
      updateProject,
      deleteProject,
    }),
    [service, createProject, listProjects, getProject, updateProject, deleteProject],
  )
}

/**
 * 扫描服务 Hook
 */
export function useScan() {
  // 获取服务实例（不是hook调用，是普通函数）
  const service = useMemo(() => getScanService(), [])

  // 提取所有useCallback到外层
  const startScan = useCallback(
    async (directoryOrRequest: string | any) => {
      // 兼容两种调用方式：传入字符串或完整的request对象
      const request =
        typeof directoryOrRequest === 'string'
          ? { directory: directoryOrRequest, incremental: true }
          : directoryOrRequest

      const result = await service.startScan(request)

      // 返回scan_id以兼容旧代码
      if (result.success && result.data) {
        return result.data.scan_id
      }
      return null
    },
    [service],
  )

  const getScanStatus = useCallback(
    async (scanId: string) => {
      return await service.getStatus(scanId)
    },
    [service],
  )

  const getScanResults = useCallback(
    async (scanId: string) => {
      return await service.getResults(scanId)
    },
    [service],
  )

  const waitForCompletion = useCallback(
    async (scanId: string, onProgress?: (status: any) => void) => {
      return await service.waitForScanCompletion(scanId, onProgress)
    },
    [service],
  )

  return useMemo(
    () => ({
      service,
      startScan,
      getScanStatus,
      getScanResults,
      waitForCompletion,
    }),
    [service, startScan, getScanStatus, getScanResults, waitForCompletion],
  )
}

/**
 * 通用服务状态管理 Hook
 */
export function useServiceState<T>(
  serviceCall: () => Promise<ServiceResult<T>>,
  dependencies: any[] = [],
) {
  // TODO: 可以集成 React Query 或 SWR
  // 目前返回基础实现
  return {
    data: null as T | null,
    loading: false,
    error: null as Error | null,
    refetch: serviceCall,
  }
}
