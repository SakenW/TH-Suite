/**
 * V6 翻译状态管理
 * 管理翻译条目的状态和操作
 */

import { reactive, computed, readonly } from 'vue'
import { getV6ApiClient } from '../../services'
import type { 
  V6TranslationEntry, 
  V6QueryParams, 
  V6PaginatedResponse,
  V6TranslationStatus
} from '../../services/api/v6Types'

// ==================== 状态类型定义 ====================

interface TranslationStoreState {
  // 数据
  translations: V6TranslationEntry[]
  currentTranslation: V6TranslationEntry | null
  
  // 分页
  currentPage: number
  pageSize: number
  totalTranslations: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
  
  // 加载状态
  loading: {
    list: boolean
    detail: boolean
    update: boolean
    batchUpdate: boolean
    export: boolean
  }
  
  // 错误状态
  error: {
    list: string | null
    detail: string | null
    update: string | null
    batchUpdate: string | null
    export: string | null
  }
  
  // 查询条件
  filters: {
    search?: string
    language_file_uid?: string
    locale?: string
    status?: V6TranslationStatus
    key?: string
    src_text?: string
    dst_text?: string
  }
  
  // UI状态
  selectedTranslationUids: Set<string>
  sortBy: string
  sortOrder: 'asc' | 'desc'
  
  // 编辑状态
  editingTranslations: Map<string, Partial<V6TranslationEntry>>
  
  // 统计数据
  statistics: {
    total_translations: number
    by_status: Record<V6TranslationStatus, number>
    by_locale: Record<string, number>
    by_file: Record<string, number>
    progress_percentage: number
  }
  
  // 导出配置
  exportConfig: {
    format: 'json' | 'ndjson' | 'csv' | 'xlsx'
    include_metadata: boolean
    compression: 'none' | 'gzip' | 'zstd'
  }
}

// ==================== Store实现 ====================

function createTranslationStore() {
  const v6Api = getV6ApiClient()
  
  // 响应式状态
  const state = reactive<TranslationStoreState>({
    translations: [],
    currentTranslation: null,
    
    currentPage: 1,
    pageSize: 50, // 翻译条目通常较多，使用更大的页面大小
    totalTranslations: 0,
    totalPages: 0,
    hasNext: false,
    hasPrev: false,
    
    loading: {
      list: false,
      detail: false,
      update: false,
      batchUpdate: false,
      export: false,
    },
    
    error: {
      list: null,
      detail: null,
      update: null,
      batchUpdate: null,
      export: null,
    },
    
    filters: {},
    
    selectedTranslationUids: new Set(),
    sortBy: 'key',
    sortOrder: 'asc',
    
    editingTranslations: new Map(),
    
    statistics: {
      total_translations: 0,
      by_status: {
        new: 0,
        reviewing: 0,
        reviewed: 0,
        approved: 0,
        rejected: 0,
      },
      by_locale: {},
      by_file: {},
      progress_percentage: 0,
    },
    
    exportConfig: {
      format: 'json',
      include_metadata: true,
      compression: 'none',
    }
  })
  
  // ==================== 计算属性 ====================
  
  const isLoading = computed(() => {
    return Object.values(state.loading).some(loading => loading)
  })
  
  const hasError = computed(() => {
    return Object.values(state.error).some(error => error !== null)
  })
  
  const selectedTranslations = computed(() => {
    return state.translations.filter(t => state.selectedTranslationUids.has(t.uid))
  })
  
  const translationsGroupedByStatus = computed(() => {
    const groups: Record<V6TranslationStatus, V6TranslationEntry[]> = {
      new: [],
      reviewing: [],
      reviewed: [],
      approved: [],
      rejected: [],
    }
    
    state.translations.forEach(translation => {
      if (groups[translation.status]) {
        groups[translation.status].push(translation)
      }
    })
    
    return groups
  })
  
  const translationsGroupedByFile = computed(() => {
    const groups: Record<string, V6TranslationEntry[]> = {}
    state.translations.forEach(translation => {
      const fileUid = translation.language_file_uid
      if (!groups[fileUid]) {
        groups[fileUid] = []
      }
      groups[fileUid].push(translation)
    })
    return groups
  })
  
  const hasUnsavedChanges = computed(() => {
    return state.editingTranslations.size > 0
  })
  
  const canBatchUpdate = computed(() => {
    return state.selectedTranslationUids.size > 0 && !state.loading.batchUpdate
  })
  
  // ==================== Actions ====================
  
  /**
   * 加载翻译条目列表
   */
  async function loadTranslations(options: {
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
      
      const response = await v6Api.getTranslations(params)
      
      if (response.success && response.data) {
        const data = response.data as V6PaginatedResponse<V6TranslationEntry>
        
        state.translations = data.items
        state.totalTranslations = data.total
        state.currentPage = data.page
        state.pageSize = data.limit
        state.totalPages = data.pages
        state.hasNext = data.has_next
        state.hasPrev = data.has_prev
        
        // 更新统计数据
        updateStatistics()
        
        // 清理不存在的选中项和编辑项
        const existingUids = new Set(state.translations.map(t => t.uid))
        state.selectedTranslationUids.forEach(uid => {
          if (!existingUids.has(uid)) {
            state.selectedTranslationUids.delete(uid)
            state.editingTranslations.delete(uid)
          }
        })
      } else {
        throw new Error(response.error?.message || 'Failed to load translations')
      }
    } catch (error: any) {
      console.error('加载翻译条目失败:', error)
      state.error.list = error.message || 'Failed to load translations'
      state.translations = []
    } finally {
      state.loading.list = false
    }
  }
  
  /**
   * 开始编辑翻译条目
   */
  function startEditTranslation(uid: string, changes: Partial<V6TranslationEntry>) {
    state.editingTranslations.set(uid, changes)
  }
  
  /**
   * 取消编辑翻译条目
   */
  function cancelEditTranslation(uid: string) {
    state.editingTranslations.delete(uid)
  }
  
  /**
   * 保存单个翻译条目的编辑
   */
  async function saveTranslationEdit(uid: string) {
    const changes = state.editingTranslations.get(uid)
    if (!changes) {
      return false
    }
    
    state.loading.update = true
    state.error.update = null
    
    try {
      // 更新本地数据
      const translationIndex = state.translations.findIndex(t => t.uid === uid)
      if (translationIndex !== -1) {
        state.translations[translationIndex] = {
          ...state.translations[translationIndex],
          ...changes,
          updated_at: new Date().toISOString(),
        }
      }
      
      // 清除编辑状态
      state.editingTranslations.delete(uid)
      
      // 更新统计
      updateStatistics()
      
      return true
    } catch (error: any) {
      console.error('保存翻译编辑失败:', error)
      state.error.update = error.message || 'Failed to save translation'
      return false
    } finally {
      state.loading.update = false
    }
  }
  
  /**
   * 批量更新翻译条目
   */
  async function batchUpdateTranslations(updates: Array<{
    uid: string
    changes: Partial<V6TranslationEntry>
  }>) {
    if (state.loading.batchUpdate || updates.length === 0) {
      return false
    }
    
    state.loading.batchUpdate = true
    state.error.batchUpdate = null
    
    try {
      // 构造批量更新请求
      const batchUpdates = updates.map(update => ({
        uid: update.uid,
        data: update.changes,
      }))
      
      const response = await v6Api.batchUpdateTranslations(batchUpdates)
      
      if (response.success && response.data) {
        // 更新本地数据
        updates.forEach(({ uid, changes }) => {
          const translationIndex = state.translations.findIndex(t => t.uid === uid)
          if (translationIndex !== -1) {
            state.translations[translationIndex] = {
              ...state.translations[translationIndex],
              ...changes,
              updated_at: new Date().toISOString(),
            }
          }
          
          // 清除编辑状态
          state.editingTranslations.delete(uid)
        })
        
        // 更新统计
        updateStatistics()
        
        return true
      } else {
        throw new Error(response.error?.message || 'Failed to batch update translations')
      }
    } catch (error: any) {
      console.error('批量更新翻译条目失败:', error)
      state.error.batchUpdate = error.message || 'Failed to batch update translations'
      return false
    } finally {
      state.loading.batchUpdate = false
    }
  }
  
  /**
   * 批量更新选中的翻译条目
   */
  async function batchUpdateSelected(changes: Partial<V6TranslationEntry>) {
    if (state.selectedTranslationUids.size === 0) {
      return false
    }
    
    const updates = Array.from(state.selectedTranslationUids).map(uid => ({
      uid,
      changes,
    }))
    
    const success = await batchUpdateTranslations(updates)
    
    if (success) {
      state.selectedTranslationUids.clear()
    }
    
    return success
  }
  
  /**
   * 导出翻译条目
   */
  async function exportTranslations() {
    if (state.loading.export) {
      return null
    }
    
    state.loading.export = true
    state.error.export = null
    
    try {
      const params = {
        locale: state.filters.locale,
        format: state.exportConfig.format,
      }
      
      const response = await v6Api.exportTranslationsNDJSON(params)
      
      if (response.success && response.data) {
        return response.data
      } else {
        throw new Error(response.error?.message || 'Failed to export translations')
      }
    } catch (error: any) {
      console.error('导出翻译条目失败:', error)
      state.error.export = error.message || 'Failed to export translations'
      return null
    } finally {
      state.loading.export = false
    }
  }
  
  /**
   * 更新本地统计数据
   */
  function updateStatistics() {
    const byStatus: Record<V6TranslationStatus, number> = {
      new: 0,
      reviewing: 0,
      reviewed: 0,
      approved: 0,
      rejected: 0,
    }
    const byLocale: Record<string, number> = {}
    const byFile: Record<string, number> = {}
    
    state.translations.forEach(translation => {
      // 按状态分组
      byStatus[translation.status]++
      
      // 按文件分组
      const fileUid = translation.language_file_uid
      byFile[fileUid] = (byFile[fileUid] || 0) + 1
      
      // 按语言区域分组（从文件名或其他地方推断）
      // 这里简化处理，实际应该从语言文件信息中获取
      const locale = 'zh_cn' // 临时处理
      byLocale[locale] = (byLocale[locale] || 0) + 1
    })
    
    // 计算进度百分比
    const completedCount = byStatus.approved + byStatus.reviewed
    const progressPercentage = state.translations.length > 0 
      ? (completedCount / state.translations.length) * 100 
      : 0
    
    state.statistics = {
      total_translations: state.translations.length,
      by_status: byStatus,
      by_locale: byLocale,
      by_file: byFile,
      progress_percentage: Math.round(progressPercentage * 100) / 100,
    }
  }
  
  // ==================== UI Actions ====================
  
  /**
   * 设置搜索条件
   */
  function setFilters(filters: Partial<TranslationStoreState['filters']>) {
    Object.assign(state.filters, filters)
    state.currentPage = 1
    loadTranslations({ page: 1, refresh: true })
  }
  
  /**
   * 清除搜索条件
   */
  function clearFilters() {
    state.filters = {}
    state.currentPage = 1
    loadTranslations({ page: 1, refresh: true })
  }
  
  /**
   * 设置排序
   */
  function setSorting(sortBy: string, sortOrder: 'asc' | 'desc' = 'asc') {
    state.sortBy = sortBy
    state.sortOrder = sortOrder
    state.currentPage = 1
    loadTranslations({ page: 1, refresh: true })
  }
  
  /**
   * 切换页面
   */
  function goToPage(page: number) {
    if (page >= 1 && page <= state.totalPages && !state.loading.list) {
      loadTranslations({ page })
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
   * 选择/取消选择翻译条目
   */
  function toggleTranslationSelection(uid: string) {
    if (state.selectedTranslationUids.has(uid)) {
      state.selectedTranslationUids.delete(uid)
    } else {
      state.selectedTranslationUids.add(uid)
    }
  }
  
  /**
   * 全选/取消全选
   */
  function toggleSelectAll() {
    if (state.selectedTranslationUids.size === state.translations.length) {
      state.selectedTranslationUids.clear()
    } else {
      state.selectedTranslationUids.clear()
      state.translations.forEach(t => state.selectedTranslationUids.add(t.uid))
    }
  }
  
  /**
   * 清除选择
   */
  function clearSelection() {
    state.selectedTranslationUids.clear()
  }
  
  /**
   * 设置导出配置
   */
  function setExportConfig(config: Partial<TranslationStoreState['exportConfig']>) {
    Object.assign(state.exportConfig, config)
  }
  
  /**
   * 清除错误
   */
  function clearError(type?: keyof TranslationStoreState['error']) {
    if (type) {
      state.error[type] = null
    } else {
      Object.keys(state.error).forEach(key => {
        state.error[key as keyof TranslationStoreState['error']] = null
      })
    }
  }
  
  /**
   * 重置状态
   */
  function reset() {
    state.translations = []
    state.currentTranslation = null
    state.currentPage = 1
    state.pageSize = 50
    state.totalTranslations = 0
    state.totalPages = 0
    state.hasNext = false
    state.hasPrev = false
    state.filters = {}
    state.selectedTranslationUids.clear()
    state.editingTranslations.clear()
    state.sortBy = 'key'
    state.sortOrder = 'asc'
    
    state.statistics = {
      total_translations: 0,
      by_status: {
        new: 0,
        reviewing: 0,
        reviewed: 0,
        approved: 0,
        rejected: 0,
      },
      by_locale: {},
      by_file: {},
      progress_percentage: 0,
    }
    
    Object.keys(state.loading).forEach(key => {
      state.loading[key as keyof TranslationStoreState['loading']] = false
    })
    
    Object.keys(state.error).forEach(key => {
      state.error[key as keyof TranslationStoreState['error']] = null
    })
  }
  
  // ==================== 返回Store接口 ====================
  
  return {
    // 状态
    state: readonly(state),
    
    // 计算属性
    isLoading,
    hasError,
    selectedTranslations,
    translationsGroupedByStatus,
    translationsGroupedByFile,
    hasUnsavedChanges,
    canBatchUpdate,
    
    // 数据操作
    loadTranslations,
    startEditTranslation,
    cancelEditTranslation,
    saveTranslationEdit,
    batchUpdateTranslations,
    batchUpdateSelected,
    exportTranslations,
    updateStatistics,
    
    // UI操作
    setFilters,
    clearFilters,
    setSorting,
    goToPage,
    nextPage,
    prevPage,
    toggleTranslationSelection,
    toggleSelectAll,
    clearSelection,
    setExportConfig,
    clearError,
    reset,
  }
}

// ==================== 导出 ====================

// 创建全局Store实例
export const translationStore = createTranslationStore()

// 导出类型
export type TranslationStore = ReturnType<typeof createTranslationStore>

export default translationStore