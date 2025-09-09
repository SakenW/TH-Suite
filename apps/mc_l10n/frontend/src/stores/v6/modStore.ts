/**
 * V6 MOD状态管理
 * 管理模组的状态和操作
 */

import { reactive, computed, readonly } from 'vue'
import { getV6ApiClient } from '../../services'
import type { 
  V6Mod, 
  V6QueryParams, 
  V6PaginatedResponse
} from '../../services/api/v6Types'

// ==================== 状态类型定义 ====================

interface ModStoreState {
  // 数据
  mods: V6Mod[]
  currentMod: V6Mod | null
  modCompatibility: Record<string, any>
  
  // 分页
  currentPage: number
  pageSize: number
  totalMods: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
  
  // 加载状态
  loading: {
    list: boolean
    detail: boolean
    compatibility: boolean
    create: boolean
    update: boolean
    delete: boolean
  }
  
  // 错误状态
  error: {
    list: string | null
    detail: string | null
    compatibility: string | null
    create: string | null
    update: string | null
    delete: string | null
  }
  
  // 查询条件
  filters: {
    search?: string
    pack_uid?: string
    mod_loader?: string
    status?: string
  }
  
  // UI状态
  selectedModUids: Set<string>
  sortBy: string
  sortOrder: 'asc' | 'desc'
  
  // 统计数据
  statistics: {
    total_mods: number
    by_loader: Record<string, number>
    by_status: Record<string, number>
    by_pack: Record<string, number>
  }
}

// ==================== Store实现 ====================

function createModStore() {
  const v6Api = getV6ApiClient()
  
  // 响应式状态
  const state = reactive<ModStoreState>({
    mods: [],
    currentMod: null,
    modCompatibility: {},
    
    currentPage: 1,
    pageSize: 20,
    totalMods: 0,
    totalPages: 0,
    hasNext: false,
    hasPrev: false,
    
    loading: {
      list: false,
      detail: false,
      compatibility: false,
      create: false,
      update: false,
      delete: false,
    },
    
    error: {
      list: null,
      detail: null,
      compatibility: null,
      create: null,
      update: null,
      delete: null,
    },
    
    filters: {},
    
    selectedModUids: new Set(),
    sortBy: 'display_name',
    sortOrder: 'asc',
    
    statistics: {
      total_mods: 0,
      by_loader: {},
      by_status: {},
      by_pack: {},
    }
  })
  
  // ==================== 计算属性 ====================
  
  const isLoading = computed(() => {
    return Object.values(state.loading).some(loading => loading)
  })
  
  const hasError = computed(() => {
    return Object.values(state.error).some(error => error !== null)
  })
  
  const selectedMods = computed(() => {
    return state.mods.filter(mod => state.selectedModUids.has(mod.uid))
  })
  
  const modsGroupedByLoader = computed(() => {
    const groups: Record<string, V6Mod[]> = {}
    state.mods.forEach(mod => {
      const loader = mod.mod_loader || 'Unknown'
      if (!groups[loader]) {
        groups[loader] = []
      }
      groups[loader].push(mod)
    })
    return groups
  })
  
  const modsGroupedByPack = computed(() => {
    const groups: Record<string, V6Mod[]> = {}
    state.mods.forEach(mod => {
      const packUid = mod.pack_uid || 'No Pack'
      if (!groups[packUid]) {
        groups[packUid] = []
      }
      groups[packUid].push(mod)
    })
    return groups
  })
  
  // ==================== Actions ====================
  
  /**
   * 加载MOD列表
   */
  async function loadMods(options: {
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
      
      const response = await v6Api.getMods(params)
      
      if (response.success && response.data) {
        const data = response.data as V6PaginatedResponse<V6Mod>
        
        state.mods = data.items
        state.totalMods = data.total
        state.currentPage = data.page
        state.pageSize = data.limit
        state.totalPages = data.pages
        state.hasNext = data.has_next
        state.hasPrev = data.has_prev
        
        // 更新统计数据
        updateStatistics()
        
        // 清理不存在的选中项
        const existingUids = new Set(state.mods.map(mod => mod.uid))
        state.selectedModUids.forEach(uid => {
          if (!existingUids.has(uid)) {
            state.selectedModUids.delete(uid)
          }
        })
      } else {
        throw new Error(response.error?.message || 'Failed to load mods')
      }
    } catch (error: any) {
      console.error('加载MOD列表失败:', error)
      state.error.list = error.message || 'Failed to load mods'
      state.mods = []
    } finally {
      state.loading.list = false
    }
  }
  
  /**
   * 加载MOD详情
   */
  async function loadMod(uid: string) {
    if (state.loading.detail) {
      return
    }
    
    state.loading.detail = true
    state.error.detail = null
    
    try {
      const response = await v6Api.getMod(uid)
      
      if (response.success && response.data) {
        state.currentMod = response.data
      } else {
        throw new Error(response.error?.message || 'Failed to load mod')
      }
    } catch (error: any) {
      console.error('加载MOD详情失败:', error)
      state.error.detail = error.message || 'Failed to load mod'
      state.currentMod = null
    } finally {
      state.loading.detail = false
    }
  }
  
  /**
   * 加载MOD兼容性信息
   */
  async function loadModCompatibility(uid: string) {
    if (state.loading.compatibility) {
      return
    }
    
    state.loading.compatibility = true
    state.error.compatibility = null
    
    try {
      const response = await v6Api.getModCompatibility(uid)
      
      if (response.success && response.data) {
        state.modCompatibility = response.data.compatibility_matrix || {}
      } else {
        throw new Error(response.error?.message || 'Failed to load mod compatibility')
      }
    } catch (error: any) {
      console.error('加载MOD兼容性失败:', error)
      state.error.compatibility = error.message || 'Failed to load mod compatibility'
      state.modCompatibility = {}
    } finally {
      state.loading.compatibility = false
    }
  }
  
  /**
   * 更新本地统计数据
   */
  function updateStatistics() {
    const byLoader: Record<string, number> = {}
    const byStatus: Record<string, number> = {}
    const byPack: Record<string, number> = {}
    
    state.mods.forEach(mod => {
      // 按Loader分组
      const loader = mod.mod_loader || 'Unknown'
      byLoader[loader] = (byLoader[loader] || 0) + 1
      
      // 按状态分组
      const status = mod.status || 'active'
      byStatus[status] = (byStatus[status] || 0) + 1
      
      // 按Pack分组
      const packUid = mod.pack_uid || 'No Pack'
      byPack[packUid] = (byPack[packUid] || 0) + 1
    })
    
    state.statistics = {
      total_mods: state.mods.length,
      by_loader: byLoader,
      by_status: byStatus,
      by_pack: byPack,
    }
  }
  
  // ==================== 查询和过滤 ====================
  
  /**
   * 根据Pack UID查找MOD
   */
  function getModsByPack(packUid: string): V6Mod[] {
    return state.mods.filter(mod => mod.pack_uid === packUid)
  }
  
  /**
   * 根据Loader查找MOD
   */
  function getModsByLoader(loader: string): V6Mod[] {
    return state.mods.filter(mod => mod.mod_loader === loader)
  }
  
  /**
   * 搜索MOD
   */
  function searchMods(query: string): V6Mod[] {
    if (!query.trim()) {
      return state.mods
    }
    
    const lowerQuery = query.toLowerCase()
    return state.mods.filter(mod => 
      mod.display_name.toLowerCase().includes(lowerQuery) ||
      mod.mod_id.toLowerCase().includes(lowerQuery) ||
      (mod.version && mod.version.toLowerCase().includes(lowerQuery))
    )
  }
  
  /**
   * 获取MOD兼容性状态
   */
  function getModCompatibilityStatus(modUid: string): string {
    const compatibility = state.modCompatibility[modUid]
    if (!compatibility) {
      return 'Unknown'
    }
    
    // 简单的兼容性评估逻辑
    const issues = compatibility.issues || []
    if (issues.length === 0) {
      return 'Compatible'
    } else if (issues.some((issue: any) => issue.severity === 'error')) {
      return 'Incompatible'
    } else {
      return 'Warning'
    }
  }
  
  // ==================== UI Actions ====================
  
  /**
   * 设置搜索条件
   */
  function setFilters(filters: Partial<ModStoreState['filters']>) {
    Object.assign(state.filters, filters)
    state.currentPage = 1
    loadMods({ page: 1, refresh: true })
  }
  
  /**
   * 清除搜索条件
   */
  function clearFilters() {
    state.filters = {}
    state.currentPage = 1
    loadMods({ page: 1, refresh: true })
  }
  
  /**
   * 设置排序
   */
  function setSorting(sortBy: string, sortOrder: 'asc' | 'desc' = 'asc') {
    state.sortBy = sortBy
    state.sortOrder = sortOrder
    state.currentPage = 1
    loadMods({ page: 1, refresh: true })
  }
  
  /**
   * 切换页面
   */
  function goToPage(page: number) {
    if (page >= 1 && page <= state.totalPages && !state.loading.list) {
      loadMods({ page })
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
   * 选择/取消选择MOD
   */
  function toggleModSelection(uid: string) {
    if (state.selectedModUids.has(uid)) {
      state.selectedModUids.delete(uid)
    } else {
      state.selectedModUids.add(uid)
    }
  }
  
  /**
   * 全选/取消全选
   */
  function toggleSelectAll() {
    if (state.selectedModUids.size === state.mods.length) {
      state.selectedModUids.clear()
    } else {
      state.selectedModUids.clear()
      state.mods.forEach(mod => state.selectedModUids.add(mod.uid))
    }
  }
  
  /**
   * 清除选择
   */
  function clearSelection() {
    state.selectedModUids.clear()
  }
  
  /**
   * 清除错误
   */
  function clearError(type?: keyof ModStoreState['error']) {
    if (type) {
      state.error[type] = null
    } else {
      Object.keys(state.error).forEach(key => {
        state.error[key as keyof ModStoreState['error']] = null
      })
    }
  }
  
  /**
   * 重置状态
   */
  function reset() {
    state.mods = []
    state.currentMod = null
    state.modCompatibility = {}
    state.currentPage = 1
    state.pageSize = 20
    state.totalMods = 0
    state.totalPages = 0
    state.hasNext = false
    state.hasPrev = false
    state.filters = {}
    state.selectedModUids.clear()
    state.sortBy = 'display_name'
    state.sortOrder = 'asc'
    
    state.statistics = {
      total_mods: 0,
      by_loader: {},
      by_status: {},
      by_pack: {},
    }
    
    Object.keys(state.loading).forEach(key => {
      state.loading[key as keyof ModStoreState['loading']] = false
    })
    
    Object.keys(state.error).forEach(key => {
      state.error[key as keyof ModStoreState['error']] = null
    })
  }
  
  // ==================== 返回Store接口 ====================
  
  return {
    // 状态
    state: readonly(state),
    
    // 计算属性
    isLoading,
    hasError,
    selectedMods,
    modsGroupedByLoader,
    modsGroupedByPack,
    
    // 数据操作
    loadMods,
    loadMod,
    loadModCompatibility,
    updateStatistics,
    
    // 查询和过滤
    getModsByPack,
    getModsByLoader,
    searchMods,
    getModCompatibilityStatus,
    
    // UI操作
    setFilters,
    clearFilters,
    setSorting,
    goToPage,
    nextPage,
    prevPage,
    toggleModSelection,
    toggleSelectAll,
    clearSelection,
    clearError,
    reset,
  }
}

// ==================== 导出 ====================

// 创建全局Store实例
export const modStore = createModStore()

// 导出类型
export type ModStore = ReturnType<typeof createModStore>

export default modStore