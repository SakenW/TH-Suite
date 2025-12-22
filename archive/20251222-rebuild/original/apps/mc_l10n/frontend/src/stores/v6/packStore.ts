/**
 * V6 Pack状态管理
 * 管理整合包的状态和操作
 */

import { reactive, computed, ref } from 'vue'
import { getV6ApiClient } from '../../services'
import type { 
  V6Pack, 
  V6QueryParams, 
  V6PaginatedResponse, 
  V6Response 
} from '../../services/api/v6Types'

// ==================== 状态类型定义 ====================

interface PackStoreState {
  // 数据
  packs: V6Pack[]
  currentPack: V6Pack | null
  
  // 分页
  currentPage: number
  pageSize: number
  totalPacks: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
  
  // 加载状态
  loading: {
    list: boolean
    detail: boolean
    create: boolean
    update: boolean
    delete: boolean
  }
  
  // 错误状态
  error: {
    list: string | null
    detail: string | null
    create: string | null
    update: string | null
    delete: string | null
  }
  
  // 查询条件
  filters: {
    search?: string
    pack_type?: string
    status?: string
  }
  
  // UI状态
  selectedPackUids: Set<string>
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

// ==================== Store实现 ====================

function createPackStore() {
  const v6Api = getV6ApiClient()
  
  // 响应式状态
  const state = reactive<PackStoreState>({
    packs: [],
    currentPack: null,
    
    currentPage: 1,
    pageSize: 20,
    totalPacks: 0,
    totalPages: 0,
    hasNext: false,
    hasPrev: false,
    
    loading: {
      list: false,
      detail: false,
      create: false,
      update: false,
      delete: false,
    },
    
    error: {
      list: null,
      detail: null,
      create: null,
      update: null,
      delete: null,
    },
    
    filters: {},
    
    selectedPackUids: new Set(),
    sortBy: 'created_at',
    sortOrder: 'desc',
  })
  
  // ==================== 计算属性 ====================
  
  const isLoading = computed(() => {
    return Object.values(state.loading).some(loading => loading)
  })
  
  const hasError = computed(() => {
    return Object.values(state.error).some(error => error !== null)
  })
  
  const selectedPacks = computed(() => {
    return state.packs.filter(pack => state.selectedPackUids.has(pack.uid))
  })
  
  const canCreatePack = computed(() => {
    return !state.loading.create
  })
  
  const canDeleteSelected = computed(() => {
    return state.selectedPackUids.size > 0 && !state.loading.delete
  })
  
  // ==================== Actions ====================
  
  /**
   * 加载Pack列表
   */
  async function loadPacks(options: {
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
      
      const response = await v6Api.getPacks(params)
      
      if (response.success && response.data) {
        const data = response.data as V6PaginatedResponse<V6Pack>
        
        state.packs = data.items
        state.totalPacks = data.total
        state.currentPage = data.page
        state.pageSize = data.limit
        state.totalPages = data.pages
        state.hasNext = data.has_next
        state.hasPrev = data.has_prev
        
        // 清理不存在的选中项
        const existingUids = new Set(state.packs.map(pack => pack.uid))
        state.selectedPackUids.forEach(uid => {
          if (!existingUids.has(uid)) {
            state.selectedPackUids.delete(uid)
          }
        })
      } else {
        throw new Error(response.error?.message || 'Failed to load packs')
      }
    } catch (error: any) {
      console.error('加载Pack列表失败:', error)
      state.error.list = error.message || 'Failed to load packs'
      state.packs = []
    } finally {
      state.loading.list = false
    }
  }
  
  /**
   * 加载Pack详情
   */
  async function loadPack(uid: string) {
    if (state.loading.detail) {
      return
    }
    
    state.loading.detail = true
    state.error.detail = null
    
    try {
      const response = await v6Api.getPack(uid)
      
      if (response.success && response.data) {
        state.currentPack = response.data
      } else {
        throw new Error(response.error?.message || 'Failed to load pack')
      }
    } catch (error: any) {
      console.error('加载Pack详情失败:', error)
      state.error.detail = error.message || 'Failed to load pack'
      state.currentPack = null
    } finally {
      state.loading.detail = false
    }
  }
  
  /**
   * 创建新Pack
   */
  async function createPack(packData: Omit<V6Pack, 'uid' | 'created_at' | 'updated_at'>) {
    if (state.loading.create) {
      return false
    }
    
    state.loading.create = true
    state.error.create = null
    
    try {
      const response = await v6Api.createPack(packData)
      
      if (response.success && response.data) {
        const newPack = response.data
        
        // 如果是第一页，直接添加到列表开头
        if (state.currentPage === 1) {
          state.packs.unshift(newPack)
          
          // 如果超过页面大小，移除最后一个
          if (state.packs.length > state.pageSize) {
            state.packs.pop()
          }
          
          state.totalPacks += 1
        }
        
        state.currentPack = newPack
        return true
      } else {
        throw new Error(response.error?.message || 'Failed to create pack')
      }
    } catch (error: any) {
      console.error('创建Pack失败:', error)
      state.error.create = error.message || 'Failed to create pack'
      return false
    } finally {
      state.loading.create = false
    }
  }
  
  /**
   * 更新Pack
   */
  async function updatePack(uid: string, updates: Partial<V6Pack>) {
    if (state.loading.update) {
      return false
    }
    
    state.loading.update = true
    state.error.update = null
    
    try {
      // 这里应该调用更新API，但V6ApiClient中暂未实现
      // 先模拟更新本地数据
      const packIndex = state.packs.findIndex(pack => pack.uid === uid)
      if (packIndex !== -1) {
        state.packs[packIndex] = { ...state.packs[packIndex], ...updates }
      }
      
      if (state.currentPack && state.currentPack.uid === uid) {
        state.currentPack = { ...state.currentPack, ...updates }
      }
      
      return true
    } catch (error: any) {
      console.error('更新Pack失败:', error)
      state.error.update = error.message || 'Failed to update pack'
      return false
    } finally {
      state.loading.update = false
    }
  }
  
  /**
   * 删除Pack
   */
  async function deletePack(uid: string) {
    if (state.loading.delete) {
      return false
    }
    
    state.loading.delete = true
    state.error.delete = null
    
    try {
      // 这里应该调用删除API，但V6ApiClient中暂未实现
      // 先模拟删除本地数据
      const packIndex = state.packs.findIndex(pack => pack.uid === uid)
      if (packIndex !== -1) {
        state.packs.splice(packIndex, 1)
        state.totalPacks -= 1
      }
      
      if (state.currentPack && state.currentPack.uid === uid) {
        state.currentPack = null
      }
      
      state.selectedPackUids.delete(uid)
      
      return true
    } catch (error: any) {
      console.error('删除Pack失败:', error)
      state.error.delete = error.message || 'Failed to delete pack'
      return false
    } finally {
      state.loading.delete = false
    }
  }
  
  /**
   * 批量删除选中的Pack
   */
  async function deleteSelectedPacks() {
    if (state.selectedPackUids.size === 0 || state.loading.delete) {
      return false
    }
    
    state.loading.delete = true
    state.error.delete = null
    
    try {
      const uidsToDelete = Array.from(state.selectedPackUids)
      
      for (const uid of uidsToDelete) {
        const packIndex = state.packs.findIndex(pack => pack.uid === uid)
        if (packIndex !== -1) {
          state.packs.splice(packIndex, 1)
          state.totalPacks -= 1
        }
      }
      
      if (state.currentPack && uidsToDelete.includes(state.currentPack.uid)) {
        state.currentPack = null
      }
      
      state.selectedPackUids.clear()
      
      return true
    } catch (error: any) {
      console.error('批量删除Pack失败:', error)
      state.error.delete = error.message || 'Failed to delete selected packs'
      return false
    } finally {
      state.loading.delete = false
    }
  }
  
  // ==================== UI Actions ====================
  
  /**
   * 设置搜索条件
   */
  function setFilters(filters: Partial<PackStoreState['filters']>) {
    Object.assign(state.filters, filters)
    state.currentPage = 1
    loadPacks({ page: 1, refresh: true })
  }
  
  /**
   * 清除搜索条件
   */
  function clearFilters() {
    state.filters = {}
    state.currentPage = 1
    loadPacks({ page: 1, refresh: true })
  }
  
  /**
   * 设置排序
   */
  function setSorting(sortBy: string, sortOrder: 'asc' | 'desc' = 'asc') {
    state.sortBy = sortBy
    state.sortOrder = sortOrder
    state.currentPage = 1
    loadPacks({ page: 1, refresh: true })
  }
  
  /**
   * 切换页面
   */
  function goToPage(page: number) {
    if (page >= 1 && page <= state.totalPages && !state.loading.list) {
      loadPacks({ page })
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
   * 选择/取消选择Pack
   */
  function togglePackSelection(uid: string) {
    if (state.selectedPackUids.has(uid)) {
      state.selectedPackUids.delete(uid)
    } else {
      state.selectedPackUids.add(uid)
    }
  }
  
  /**
   * 全选/取消全选
   */
  function toggleSelectAll() {
    if (state.selectedPackUids.size === state.packs.length) {
      state.selectedPackUids.clear()
    } else {
      state.selectedPackUids.clear()
      state.packs.forEach(pack => state.selectedPackUids.add(pack.uid))
    }
  }
  
  /**
   * 清除选择
   */
  function clearSelection() {
    state.selectedPackUids.clear()
  }
  
  /**
   * 清除错误
   */
  function clearError(type?: keyof PackStoreState['error']) {
    if (type) {
      state.error[type] = null
    } else {
      Object.keys(state.error).forEach(key => {
        state.error[key as keyof PackStoreState['error']] = null
      })
    }
  }
  
  /**
   * 重置状态
   */
  function reset() {
    state.packs = []
    state.currentPack = null
    state.currentPage = 1
    state.pageSize = 20
    state.totalPacks = 0
    state.totalPages = 0
    state.hasNext = false
    state.hasPrev = false
    state.filters = {}
    state.selectedPackUids.clear()
    state.sortBy = 'created_at'
    state.sortOrder = 'desc'
    
    Object.keys(state.loading).forEach(key => {
      state.loading[key as keyof PackStoreState['loading']] = false
    })
    
    Object.keys(state.error).forEach(key => {
      state.error[key as keyof PackStoreState['error']] = null
    })
  }
  
  // ==================== 返回Store接口 ====================
  
  return {
    // 状态
    state: readonly(state),
    
    // 计算属性
    isLoading,
    hasError,
    selectedPacks,
    canCreatePack,
    canDeleteSelected,
    
    // 数据操作
    loadPacks,
    loadPack,
    createPack,
    updatePack,
    deletePack,
    deleteSelectedPacks,
    
    // UI操作
    setFilters,
    clearFilters,
    setSorting,
    goToPage,
    nextPage,
    prevPage,
    togglePackSelection,
    toggleSelectAll,
    clearSelection,
    clearError,
    reset,
  }
}

// ==================== 导出 ====================

// 创建全局Store实例
export const packStore = createPackStore()

// 导出类型
export type PackStore = ReturnType<typeof createPackStore>

export default packStore