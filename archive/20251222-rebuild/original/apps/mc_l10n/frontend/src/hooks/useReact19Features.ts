/**
 * React 19 新特性Hook集合
 * 展示use、useActionState、useOptimistic等新API的使用
 */

import { use, useOptimistic, useActionState, useState, useTransition } from 'react'

// 类型定义
interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

interface OptimisticUpdate<T> {
  id: string
  type: 'add' | 'update' | 'delete'
  data: T
}

interface ActionResult {
  success: boolean
  message: string
  data?: any
}

/**
 * use Hook 演示 - 处理Promise和Context
 */
export function useAsyncData<T>(promiseOrResource: Promise<T> | (() => Promise<T>)) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  // 在React 19中，use可以直接处理Promise
  try {
    const promise =
      typeof promiseOrResource === 'function' ? promiseOrResource() : promiseOrResource

    // use Hook会暂停组件直到Promise解决
    const data = use(promise)
    return { data, loading: false, error: null }
  } catch (error) {
    return {
      data: null,
      loading: false,
      error: error instanceof Error ? error : new Error('Unknown error'),
    }
  }
}

/**
 * useActionState Hook 演示 - 表单状态管理
 */
export function useScanAction() {
  const scanProject = async (
    prevState: ActionResult,
    formData: FormData,
  ): Promise<ActionResult> => {
    try {
      const projectPath = formData.get('projectPath') as string

      // 模拟异步扫描操作
      await new Promise(resolve => setTimeout(resolve, 1000))

      // 实际会调用扫描API
      return {
        success: true,
        message: `成功扫描项目: ${projectPath}`,
        data: { filesScanned: 42, modsFound: 15 },
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : '扫描失败',
      }
    }
  }

  const initialState: ActionResult = {
    success: false,
    message: '',
  }

  const [state, action, isPending] = useActionState(scanProject, initialState)

  return { state, action, isPending }
}

/**
 * useOptimistic Hook 演示 - 乐观更新
 */
export function useOptimisticTranslations<T>(
  initialTranslations: T[],
  updateFn: (translations: T[], update: OptimisticUpdate<T>) => T[],
) {
  const [optimisticTranslations, addOptimistic] = useOptimistic(initialTranslations, updateFn)

  const [isPending, startTransition] = useTransition()

  const updateTranslation = async (update: OptimisticUpdate<T>) => {
    // 立即应用乐观更新
    addOptimistic(update)

    // 异步发送到服务器
    startTransition(async () => {
      try {
        // 实际的API调用会在这里
        await new Promise(resolve => setTimeout(resolve, 500))
        // 如果成功，React会自动使用服务器返回的数据
      } catch (error) {
        // 如果失败，React会回滚乐观更新
        console.error('Translation update failed:', error)
      }
    })
  }

  return {
    translations: optimisticTranslations,
    updateTranslation,
    isPending,
  }
}

/**
 * 扫描进度的乐观更新Hook
 */
export function useOptimisticScanProgress() {
  interface ScanProgress {
    current: number
    total: number
    currentFile: string
    completed: boolean
  }

  const initialProgress: ScanProgress = {
    current: 0,
    total: 0,
    currentFile: '',
    completed: false,
  }

  const [optimisticProgress, addOptimistic] = useOptimistic(
    initialProgress,
    (state: ScanProgress, newProgress: Partial<ScanProgress>) => ({
      ...state,
      ...newProgress,
    }),
  )

  const updateProgress = (progress: Partial<ScanProgress>) => {
    // 立即更新UI显示
    addOptimistic(progress)
  }

  return {
    progress: optimisticProgress,
    updateProgress,
  }
}

/**
 * 项目操作的Action Hook集合
 */
export function useProjectActions() {
  const createProject = async (
    prevState: ActionResult,
    formData: FormData,
  ): Promise<ActionResult> => {
    try {
      const projectName = formData.get('projectName') as string
      const projectPath = formData.get('projectPath') as string

      // 模拟创建项目
      await new Promise(resolve => setTimeout(resolve, 800))

      return {
        success: true,
        message: `项目 "${projectName}" 创建成功`,
        data: { projectId: Date.now().toString() },
      }
    } catch (error) {
      return {
        success: false,
        message: '项目创建失败',
      }
    }
  }

  const deleteProject = async (
    prevState: ActionResult,
    formData: FormData,
  ): Promise<ActionResult> => {
    try {
      const projectId = formData.get('projectId') as string

      // 模拟删除操作
      await new Promise(resolve => setTimeout(resolve, 500))

      return {
        success: true,
        message: '项目删除成功',
      }
    } catch (error) {
      return {
        success: false,
        message: '项目删除失败',
      }
    }
  }

  const [createState, createAction, isCreating] = useActionState(createProject, {
    success: false,
    message: '',
  })

  const [deleteState, deleteAction, isDeleting] = useActionState(deleteProject, {
    success: false,
    message: '',
  })

  return {
    create: { state: createState, action: createAction, isPending: isCreating },
    delete: { state: deleteState, action: deleteAction, isPending: isDeleting },
  }
}

/**
 * 结合所有React 19特性的综合Hook
 */
export function useReact19Enhanced<T>() {
  const [data, setData] = useState<T[]>([])
  const [isPending, startTransition] = useTransition()

  // 乐观更新
  const [optimisticData, addOptimistic] = useOptimistic(
    data,
    (currentData: T[], optimisticUpdate: { type: string; payload: any }) => {
      switch (optimisticUpdate.type) {
        case 'ADD':
          return [...currentData, optimisticUpdate.payload]
        case 'UPDATE':
          return currentData.map(item =>
            (item as any).id === optimisticUpdate.payload.id ? optimisticUpdate.payload : item,
          )
        case 'DELETE':
          return currentData.filter(item => (item as any).id !== optimisticUpdate.payload.id)
        default:
          return currentData
      }
    },
  )

  // 行动状态管理
  const processAction = async (
    prevState: ActionResult,
    formData: FormData,
  ): Promise<ActionResult> => {
    try {
      const action = formData.get('action') as string
      const payload = JSON.parse((formData.get('payload') as string) || '{}')

      // 立即应用乐观更新
      addOptimistic({ type: action, payload })

      // 异步处理
      await new Promise(resolve => setTimeout(resolve, 1000))

      return {
        success: true,
        message: `操作 ${action} 完成`,
        data: payload,
      }
    } catch (error) {
      return {
        success: false,
        message: '操作失败',
      }
    }
  }

  const [actionState, actionDispatch, isActionPending] = useActionState(processAction, {
    success: false,
    message: '',
  })

  return {
    data: optimisticData,
    actionState,
    actionDispatch,
    isPending: isPending || isActionPending,
    startTransition,
    addOptimistic,
  }
}
