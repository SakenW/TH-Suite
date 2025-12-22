/**
 * V6 队列状态管理
 * 管理工作队列任务的状态和操作
 */

import { reactive, computed, readonly } from 'vue'
import { getV6ApiClient } from '../../services'
import type { 
  V6WorkItem, 
  V6QueryParams, 
  V6PaginatedResponse,
  V6TaskStatus
} from '../../services/api/v6Types'

// ==================== 状态类型定义 ====================

interface QueueStoreState {
  // 数据
  tasks: V6WorkItem[]
  currentTask: V6WorkItem | null
  
  // 分页
  currentPage: number
  pageSize: number
  totalTasks: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
  
  // 加载状态
  loading: {
    list: boolean
    detail: boolean
    create: boolean
    lease: boolean
    status: boolean
  }
  
  // 错误状态
  error: {
    list: string | null
    detail: string | null
    create: string | null
    lease: string | null
    status: string | null
  }
  
  // 查询条件
  filters: {
    task_type?: string
    status?: V6TaskStatus
    priority?: number
  }
  
  // UI状态
  selectedTaskUids: Set<string>
  sortBy: string
  sortOrder: 'asc' | 'desc'
  
  // 队列状态
  queueStatus: {
    active_tasks: number
    pending_tasks: number
    failed_tasks: number
    last_updated: string | null
  }
  
  // 统计数据
  statistics: {
    total_tasks: number
    by_status: Record<V6TaskStatus, number>
    by_type: Record<string, number>
    by_priority: Record<number, number>
    average_processing_time: number
    success_rate: number
  }
  
  // 实时更新
  autoRefresh: {
    enabled: boolean
    interval: number
    timerId: number | null
  }
}

// ==================== Store实现 ====================

function createQueueStore() {
  const v6Api = getV6ApiClient()
  
  // 响应式状态
  const state = reactive<QueueStoreState>({
    tasks: [],
    currentTask: null,
    
    currentPage: 1,
    pageSize: 20,
    totalTasks: 0,
    totalPages: 0,
    hasNext: false,
    hasPrev: false,
    
    loading: {
      list: false,
      detail: false,
      create: false,
      lease: false,
      status: false,
    },
    
    error: {
      list: null,
      detail: null,
      create: null,
      lease: null,
      status: null,
    },
    
    filters: {},
    
    selectedTaskUids: new Set(),
    sortBy: 'created_at',
    sortOrder: 'desc',
    
    queueStatus: {
      active_tasks: 0,
      pending_tasks: 0,
      failed_tasks: 0,
      last_updated: null,
    },
    
    statistics: {
      total_tasks: 0,
      by_status: {
        pending: 0,
        leased: 0,
        completed: 0,
        failed: 0,
      },
      by_type: {},
      by_priority: {},
      average_processing_time: 0,
      success_rate: 0,
    },
    
    autoRefresh: {
      enabled: false,
      interval: 5000, // 5秒刷新间隔
      timerId: null,
    }
  })
  
  // ==================== 计算属性 ====================
  
  const isLoading = computed(() => {
    return Object.values(state.loading).some(loading => loading)
  })
  
  const hasError = computed(() => {
    return Object.values(state.error).some(error => error !== null)
  })
  
  const selectedTasks = computed(() => {
    return state.tasks.filter(task => state.selectedTaskUids.has(task.uid))
  })
  
  const tasksGroupedByStatus = computed(() => {
    const groups: Record<V6TaskStatus, V6WorkItem[]> = {
      pending: [],
      leased: [],
      completed: [],
      failed: [],
    }
    
    state.tasks.forEach(task => {
      if (groups[task.status]) {
        groups[task.status].push(task)
      }
    })
    
    return groups
  })
  
  const tasksGroupedByType = computed(() => {
    const groups: Record<string, V6WorkItem[]> = {}
    state.tasks.forEach(task => {
      if (!groups[task.task_type]) {
        groups[task.task_type] = []
      }
      groups[task.task_type].push(task)
    })
    return groups
  })
  
  const pendingTasks = computed(() => {
    return state.tasks.filter(task => task.status === 'pending')
  })
  
  const activeTasks = computed(() => {
    return state.tasks.filter(task => task.status === 'leased')
  })
  
  const completedTasks = computed(() => {
    return state.tasks.filter(task => task.status === 'completed')
  })
  
  const failedTasks = computed(() => {
    return state.tasks.filter(task => task.status === 'failed')
  })
  
  const canCreateTask = computed(() => {
    return !state.loading.create
  })
  
  // ==================== Actions ====================
  
  /**
   * 加载任务列表
   */
  async function loadTasks(options: {
    page?: number
    pageSize?: number
    refresh?: boolean
  } = {}) {
    const { page = state.currentPage, pageSize = state.pageSize, refresh = false } = options
    
    if (!refresh && state.loading.list) {
      return
    }
    
    state.loading.list = true
    state.error.list = null
    
    try {
      const params: V6QueryParams = {
        page,
        limit: pageSize,
        sort_by: state.sortBy,
        sort_order: state.sortOrder,
        ...state.filters,
      }
      
      const response = await v6Api.getQueueTasks(params)
      
      if (response.success && response.data) {
        const data = response.data as V6PaginatedResponse<V6WorkItem>
        
        state.tasks = data.items
        state.totalTasks = data.total
        state.currentPage = data.page
        state.pageSize = data.limit
        state.totalPages = data.pages
        state.hasNext = data.has_next
        state.hasPrev = data.has_prev
        
        // 更新统计数据
        updateStatistics()
        
        // 清理不存在的选中项
        const existingUids = new Set(state.tasks.map(task => task.uid))
        state.selectedTaskUids.forEach(uid => {
          if (!existingUids.has(uid)) {
            state.selectedTaskUids.delete(uid)
          }
        })
      } else {
        throw new Error(response.error?.message || 'Failed to load tasks')
      }
    } catch (error: any) {
      console.error('加载任务列表失败:', error)
      state.error.list = error.message || 'Failed to load tasks'
      state.tasks = []
    } finally {
      state.loading.list = false
    }
  }
  
  /**
   * 加载队列状态
   */
  async function loadQueueStatus() {
    if (state.loading.status) {
      return
    }
    
    state.loading.status = true
    state.error.status = null
    
    try {
      const response = await v6Api.getQueueStatus()
      
      if (response.success && response.data) {
        state.queueStatus = {
          ...response.data,
          last_updated: new Date().toISOString(),
        }
      } else {
        throw new Error(response.error?.message || 'Failed to load queue status')
      }
    } catch (error: any) {
      console.error('加载队列状态失败:', error)
      state.error.status = error.message || 'Failed to load queue status'
    } finally {
      state.loading.status = false
    }
  }
  
  /**
   * 创建新任务
   */
  async function createTask(taskData: {
    task_type: string
    payload: any
    priority?: number
    idempotency_key?: string
  }) {
    if (state.loading.create) {
      return false
    }
    
    state.loading.create = true
    state.error.create = null
    
    try {
      const response = await v6Api.createQueueTask(taskData)
      
      if (response.success && response.data) {
        const newTask = response.data
        
        // 如果是第一页，直接添加到列表开头
        if (state.currentPage === 1) {
          state.tasks.unshift(newTask)
          
          // 如果超过页面大小，移除最后一个
          if (state.tasks.length > state.pageSize) {
            state.tasks.pop()
          }
          
          state.totalTasks += 1
        }
        
        // 更新队列状态
        state.queueStatus.pending_tasks += 1
        
        return true
      } else {
        throw new Error(response.error?.message || 'Failed to create task')
      }
    } catch (error: any) {
      console.error('创建任务失败:', error)
      state.error.create = error.message || 'Failed to create task'
      return false
    } finally {
      state.loading.create = false
    }
  }
  
  /**
   * 租用任务
   */
  async function leaseTask(taskId: string, leaseDuration?: number) {
    if (state.loading.lease) {
      return false
    }
    
    state.loading.lease = true
    state.error.lease = null
    
    try {
      const response = await v6Api.leaseQueueTask(taskId, leaseDuration)
      
      if (response.success && response.data) {
        // 更新本地任务状态
        const taskIndex = state.tasks.findIndex(task => task.uid === taskId)
        if (taskIndex !== -1) {
          state.tasks[taskIndex] = {
            ...state.tasks[taskIndex],
            status: 'leased',
            lease_expires_at: response.data.lease_expires_at,
          }
        }
        
        // 更新队列状态
        state.queueStatus.pending_tasks -= 1
        state.queueStatus.active_tasks += 1
        
        return true
      } else {
        throw new Error(response.error?.message || 'Failed to lease task')
      }
    } catch (error: any) {
      console.error('租用任务失败:', error)
      state.error.lease = error.message || 'Failed to lease task'
      return false
    } finally {
      state.loading.lease = false
    }
  }
  
  /**
   * 更新本地统计数据
   */
  function updateStatistics() {
    const byStatus: Record<V6TaskStatus, number> = {
      pending: 0,
      leased: 0,
      completed: 0,
      failed: 0,
    }
    const byType: Record<string, number> = {}
    const byPriority: Record<number, number> = {}
    
    let totalProcessingTime = 0
    let completedCount = 0
    
    state.tasks.forEach(task => {
      // 按状态分组
      byStatus[task.status]++
      
      // 按类型分组
      byType[task.task_type] = (byType[task.task_type] || 0) + 1
      
      // 按优先级分组
      byPriority[task.priority] = (byPriority[task.priority] || 0) + 1
      
      // 计算处理时间（简化处理）
      if (task.status === 'completed') {
        const created = new Date(task.created_at)
        const updated = new Date(task.updated_at)
        totalProcessingTime += updated.getTime() - created.getTime()
        completedCount++
      }
    })
    
    const averageProcessingTime = completedCount > 0 ? totalProcessingTime / completedCount : 0
    const totalFinished = byStatus.completed + byStatus.failed
    const successRate = totalFinished > 0 ? (byStatus.completed / totalFinished) * 100 : 0
    
    state.statistics = {
      total_tasks: state.tasks.length,
      by_status: byStatus,
      by_type: byType,
      by_priority: byPriority,
      average_processing_time: Math.round(averageProcessingTime),
      success_rate: Math.round(successRate * 100) / 100,
    }
  }
  
  // ==================== 实时更新 ====================
  
  /**
   * 启用自动刷新
   */
  function enableAutoRefresh(interval: number = 5000) {
    if (state.autoRefresh.timerId) {
      clearInterval(state.autoRefresh.timerId)
    }
    
    state.autoRefresh.enabled = true
    state.autoRefresh.interval = interval
    state.autoRefresh.timerId = window.setInterval(() => {
      loadTasks({ refresh: true })
      loadQueueStatus()
    }, interval)
  }
  
  /**
   * 禁用自动刷新
   */
  function disableAutoRefresh() {
    if (state.autoRefresh.timerId) {
      clearInterval(state.autoRefresh.timerId)
      state.autoRefresh.timerId = null
    }
    
    state.autoRefresh.enabled = false
  }
  
  // ==================== UI Actions ====================
  
  /**
   * 设置搜索条件
   */
  function setFilters(filters: Partial<QueueStoreState['filters']>) {
    Object.assign(state.filters, filters)
    state.currentPage = 1
    loadTasks({ page: 1, refresh: true })
  }
  
  /**
   * 清除搜索条件
   */
  function clearFilters() {
    state.filters = {}
    state.currentPage = 1
    loadTasks({ page: 1, refresh: true })
  }
  
  /**
   * 设置排序
   */
  function setSorting(sortBy: string, sortOrder: 'asc' | 'desc' = 'asc') {
    state.sortBy = sortBy
    state.sortOrder = sortOrder
    state.currentPage = 1
    loadTasks({ page: 1, refresh: true })
  }
  
  /**
   * 切换页面
   */
  function goToPage(page: number) {
    if (page >= 1 && page <= state.totalPages && !state.loading.list) {
      loadTasks({ page })
    }
  }
  
  /**
   * 下一页
   */
  function nextPage() {
    if (state.hasNext) {
      goToPage(state.currentPage + 1)
    }
  }
  
  /**
   * 上一页
   */
  function prevPage() {
    if (state.hasPrev) {
      goToPage(state.currentPage - 1)
    }
  }
  
  /**
   * 选择/取消选择任务
   */
  function toggleTaskSelection(uid: string) {
    if (state.selectedTaskUids.has(uid)) {
      state.selectedTaskUids.delete(uid)
    } else {
      state.selectedTaskUids.add(uid)
    }
  }
  
  /**
   * 全选/取消全选
   */
  function toggleSelectAll() {
    if (state.selectedTaskUids.size === state.tasks.length) {
      state.selectedTaskUids.clear()
    } else {
      state.selectedTaskUids.clear()
      state.tasks.forEach(task => state.selectedTaskUids.add(task.uid))
    }
  }
  
  /**
   * 清除选择
   */
  function clearSelection() {
    state.selectedTaskUids.clear()
  }
  
  /**
   * 清除错误
   */
  function clearError(type?: keyof QueueStoreState['error']) {
    if (type) {
      state.error[type] = null
    } else {
      Object.keys(state.error).forEach(key => {
        state.error[key as keyof QueueStoreState['error']] = null
      })
    }
  }
  
  /**
   * 重置状态
   */
  function reset() {
    // 清理自动刷新
    disableAutoRefresh()
    
    state.tasks = []
    state.currentTask = null
    state.currentPage = 1
    state.pageSize = 20
    state.totalTasks = 0
    state.totalPages = 0
    state.hasNext = false
    state.hasPrev = false
    state.filters = {}
    state.selectedTaskUids.clear()
    state.sortBy = 'created_at'
    state.sortOrder = 'desc'
    
    state.queueStatus = {
      active_tasks: 0,
      pending_tasks: 0,
      failed_tasks: 0,
      last_updated: null,
    }
    
    state.statistics = {
      total_tasks: 0,
      by_status: {
        pending: 0,
        leased: 0,
        completed: 0,
        failed: 0,
      },
      by_type: {},
      by_priority: {},
      average_processing_time: 0,
      success_rate: 0,
    }
    
    Object.keys(state.loading).forEach(key => {
      state.loading[key as keyof QueueStoreState['loading']] = false
    })
    
    Object.keys(state.error).forEach(key => {
      state.error[key as keyof QueueStoreState['error']] = null
    })
  }
  
  // ==================== 返回Store接口 ====================
  
  return {
    // 状态
    state: readonly(state),
    
    // 计算属性
    isLoading,
    hasError,
    selectedTasks,
    tasksGroupedByStatus,
    tasksGroupedByType,
    pendingTasks,
    activeTasks,
    completedTasks,
    failedTasks,
    canCreateTask,
    
    // 数据操作
    loadTasks,
    loadQueueStatus,
    createTask,
    leaseTask,
    updateStatistics,
    
    // 实时更新
    enableAutoRefresh,
    disableAutoRefresh,
    
    // UI操作
    setFilters,
    clearFilters,
    setSorting,
    goToPage,
    nextPage,
    prevPage,
    toggleTaskSelection,
    toggleSelectAll,
    clearSelection,
    clearError,
    reset,
  }
}

// ==================== 导出 ====================

// 创建全局Store实例
export const queueStore = createQueueStore()

// 导出类型
export type QueueStore = ReturnType<typeof createQueueStore>

export default queueStore