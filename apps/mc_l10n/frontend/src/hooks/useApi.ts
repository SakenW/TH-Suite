/**
 * API 调用 React Hook
 * 简化组件中的 API 调用和状态管理
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { ApiResponse, ApiErrorResponse, AsyncTask } from '../types/api'
import { handleApiError, isApiSuccess, getApiData, isTaskCompleted } from '../services'

// 基础 API 调用状态
export interface ApiState<T = any> {
  data: T | null
  loading: boolean
  error: string | null
  success: boolean
}

// 异步任务状态
export interface TaskState extends ApiState<AsyncTask> {
  progress: number
  taskId: string | null
  isCompleted: boolean
  isRunning: boolean
}

// 分页数据状态
export interface PaginatedState<T = any> extends ApiState<T[]> {
  total: number
  page: number
  pageSize: number
  totalPages: number
  hasMore: boolean
}

/**
 * 基础 API 调用 Hook
 */
export function useApi<T = any>(
  apiCall?: () => Promise<ApiResponse<T>>,
  immediate: boolean = false,
): ApiState<T> & {
  execute: () => Promise<T | null>
  reset: () => void
} {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
    success: false,
  })

  const isMountedRef = useRef(true)
  const currentRequestRef = useRef<Promise<any> | null>(null)

  // 组件卸载时设置标记
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const execute = useCallback(async (): Promise<T | null> => {
    if (!apiCall) return null

    // 取消之前的请求
    currentRequestRef.current = null

    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const requestPromise = apiCall()
      currentRequestRef.current = requestPromise

      const response = await requestPromise

      // 检查组件是否已卸载或者是否是当前请求
      if (!isMountedRef.current || currentRequestRef.current !== requestPromise) {
        return null
      }

      if (isApiSuccess(response)) {
        const data = getApiData<T>(response)
        setState({
          data,
          loading: false,
          error: null,
          success: true,
        })
        return data
      } else {
        const errorMessage = handleApiError(response)
        setState({
          data: null,
          loading: false,
          error: errorMessage,
          success: false,
        })
        return null
      }
    } catch (error) {
      if (!isMountedRef.current) return null

      const errorMessage = handleApiError(error)
      setState({
        data: null,
        loading: false,
        error: errorMessage,
        success: false,
      })
      return null
    }
  }, [apiCall])

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
      success: false,
    })
    currentRequestRef.current = null
  }, [])

  // 立即执行
  useEffect(() => {
    if (immediate && apiCall) {
      execute()
    }
  }, [execute, immediate, apiCall])

  return {
    ...state,
    execute,
    reset,
  }
}

/**
 * 异步任务 Hook
 */
export function useAsyncTask(): TaskState & {
  startTask: (taskPromise: Promise<ApiResponse<AsyncTask>>) => Promise<AsyncTask | null>
  pollTask: (taskId: string, pollInterval?: number) => Promise<AsyncTask | null>
  cancelTask: () => void
  reset: () => void
} {
  const [state, setState] = useState<TaskState>({
    data: null,
    loading: false,
    error: null,
    success: false,
    progress: 0,
    taskId: null,
    isCompleted: false,
    isRunning: false,
  })

  const isMountedRef = useRef(true)
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null)
  const currentTaskRef = useRef<string | null>(null)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current)
      }
    }
  }, [])

  const startTask = useCallback(
    async (taskPromise: Promise<ApiResponse<AsyncTask>>): Promise<AsyncTask | null> => {
      setState(prev => ({ ...prev, loading: true, error: null }))

      try {
        const response = await taskPromise

        if (!isMountedRef.current) return null

        if (isApiSuccess(response)) {
          const task = getApiData<AsyncTask>(response)
          if (task) {
            currentTaskRef.current = task.id
            setState({
              data: task,
              loading: false,
              error: null,
              success: true,
              progress: task.progress || 0,
              taskId: task.id,
              isCompleted: isTaskCompleted(task.status),
              isRunning: !isTaskCompleted(task.status),
            })

            // 如果任务未完成，开始轮询
            if (!isTaskCompleted(task.status)) {
              pollTask(task.id)
            }

            return task
          }
        } else {
          const errorMessage = handleApiError(response)
          setState(prev => ({
            ...prev,
            loading: false,
            error: errorMessage,
            success: false,
          }))
        }
      } catch (error) {
        if (!isMountedRef.current) return null

        const errorMessage = handleApiError(error)
        setState(prev => ({
          ...prev,
          loading: false,
          error: errorMessage,
          success: false,
        }))
      }

      return null
    },
    [],
  )

  const pollTask = useCallback(
    async (taskId: string, pollInterval: number = 1000): Promise<AsyncTask | null> => {
      // 清除之前的轮询
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current)
      }

      if (!isMountedRef.current || taskId !== currentTaskRef.current) {
        return null
      }

      try {
        // 这里需要注入具体的任务状态查询服务
        // const response = await systemService.getTask(taskId);
        // 暂时模拟实现
        const response: ApiResponse<AsyncTask> = {
          success: true,
          data: {
            id: taskId,
            task_type: 'scan',
            status: 'running',
            progress: 50,
            created_at: new Date().toISOString(),
          },
        }

        if (!isMountedRef.current || taskId !== currentTaskRef.current) {
          return null
        }

        if (isApiSuccess(response)) {
          const task = getApiData<AsyncTask>(response)
          if (task) {
            const isCompleted = isTaskCompleted(task.status)

            setState(prev => ({
              ...prev,
              data: task,
              progress: task.progress || prev.progress,
              isCompleted,
              isRunning: !isCompleted,
              error: task.error || null,
            }))

            // 如果任务未完成，继续轮询
            if (!isCompleted) {
              pollTimerRef.current = setTimeout(() => {
                pollTask(taskId, pollInterval)
              }, pollInterval)
            }

            return task
          }
        }
      } catch (error) {
        console.error('Task polling error:', error)
      }

      return null
    },
    [],
  )

  const cancelTask = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    currentTaskRef.current = null
    setState(prev => ({
      ...prev,
      loading: false,
      isRunning: false,
    }))
  }, [])

  const reset = useCallback(() => {
    cancelTask()
    setState({
      data: null,
      loading: false,
      error: null,
      success: false,
      progress: 0,
      taskId: null,
      isCompleted: false,
      isRunning: false,
    })
  }, [cancelTask])

  return {
    ...state,
    startTask,
    pollTask,
    cancelTask,
    reset,
  }
}

/**
 * 分页数据 Hook
 */
export function usePaginatedApi<T = any>(
  apiCall?: (
    params: any,
  ) => Promise<
    ApiResponse<{ items: T[]; total: number; page: number; page_size: number; total_pages: number }>
  >,
  initialPage: number = 1,
  initialPageSize: number = 20,
): PaginatedState<T> & {
  loadPage: (page: number) => Promise<T[] | null>
  loadMore: () => Promise<T[] | null>
  refresh: () => Promise<T[] | null>
  setPageSize: (size: number) => void
  reset: () => void
} {
  const [state, setState] = useState<PaginatedState<T>>({
    data: [],
    loading: false,
    error: null,
    success: false,
    total: 0,
    page: initialPage,
    pageSize: initialPageSize,
    totalPages: 0,
    hasMore: false,
  })

  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const loadPage = useCallback(
    async (page: number): Promise<T[] | null> => {
      if (!apiCall) return null

      setState(prev => ({ ...prev, loading: true, error: null }))

      try {
        const response = await apiCall({
          page,
          page_size: state.pageSize,
        })

        if (!isMountedRef.current) return null

        if (isApiSuccess(response)) {
          const data = getApiData(response)
          if (data) {
            const newState: PaginatedState<T> = {
              data: data.items || [],
              loading: false,
              error: null,
              success: true,
              total: data.total || 0,
              page: data.page || page,
              pageSize: data.page_size || state.pageSize,
              totalPages: data.total_pages || 0,
              hasMore: (data.page || page) < (data.total_pages || 0),
            }
            setState(newState)
            return data.items || []
          }
        } else {
          const errorMessage = handleApiError(response)
          setState(prev => ({
            ...prev,
            loading: false,
            error: errorMessage,
            success: false,
          }))
        }
      } catch (error) {
        if (!isMountedRef.current) return null

        const errorMessage = handleApiError(error)
        setState(prev => ({
          ...prev,
          loading: false,
          error: errorMessage,
          success: false,
        }))
      }

      return null
    },
    [apiCall, state.pageSize],
  )

  const loadMore = useCallback(async (): Promise<T[] | null> => {
    if (!state.hasMore) return null
    return loadPage(state.page + 1)
  }, [loadPage, state.hasMore, state.page])

  const refresh = useCallback(async (): Promise<T[] | null> => {
    return loadPage(state.page)
  }, [loadPage, state.page])

  const setPageSize = useCallback((size: number) => {
    setState(prev => ({ ...prev, pageSize: size, page: 1 }))
  }, [])

  const reset = useCallback(() => {
    setState({
      data: [],
      loading: false,
      error: null,
      success: false,
      total: 0,
      page: initialPage,
      pageSize: initialPageSize,
      totalPages: 0,
      hasMore: false,
    })
  }, [initialPage, initialPageSize])

  return {
    ...state,
    loadPage,
    loadMore,
    refresh,
    setPageSize,
    reset,
  }
}

/**
 * 防抖 API 调用 Hook
 */
export function useDebouncedApi<T = any>(
  apiCall: () => Promise<ApiResponse<T>>,
  delay: number = 300,
  deps: React.DependencyList = [],
): ApiState<T> {
  const { data, loading, error, success, execute } = useApi(apiCall, false)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    timerRef.current = setTimeout(() => {
      execute()
    }, delay)

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [...deps, execute, delay])

  return { data, loading, error, success }
}
