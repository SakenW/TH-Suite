/**
 * V6状态管理统一导出
 * 提供所有V6相关的状态管理Store和工具函数
 */

// ==================== Store导出 ====================
export { default as packStore } from './packStore'
export { default as modStore } from './modStore'
export { default as translationStore } from './translationStore'
export { default as queueStore } from './queueStore'

// 导出Store实例（便于直接使用）
export { packStore } from './packStore'
export { modStore } from './modStore'
export { translationStore } from './translationStore'
export { queueStore } from './queueStore'

// ==================== 类型导出 ====================
export type { PackStore } from './packStore'
export type { ModStore } from './modStore'
export type { TranslationStore } from './translationStore'
export type { QueueStore } from './queueStore'

// ==================== 统一Store接口 ====================

/**
 * V6所有Store的集合接口
 */
export interface V6Stores {
  pack: typeof packStore
  mod: typeof modStore
  translation: typeof translationStore
  queue: typeof queueStore
}

/**
 * 获取所有V6 Store
 */
export function getV6Stores(): V6Stores {
  return {
    pack: packStore,
    mod: modStore,
    translation: translationStore,
    queue: queueStore,
  }
}

// ==================== 工具函数 ====================

/**
 * 重置所有V6 Store状态
 */
export function resetAllV6Stores() {
  packStore.reset()
  modStore.reset()
  translationStore.reset()
  queueStore.reset()
}

/**
 * 清除所有V6 Store错误
 */
export function clearAllV6Errors() {
  packStore.clearError()
  modStore.clearError()
  translationStore.clearError()
  queueStore.clearError()
}

/**
 * 检查所有V6 Store是否有加载状态
 */
export function isAnyV6StoreLoading(): boolean {
  return (
    packStore.isLoading.value ||
    modStore.isLoading.value ||
    translationStore.isLoading.value ||
    queueStore.isLoading.value
  )
}

/**
 * 检查所有V6 Store是否有错误
 */
export function hasAnyV6StoreError(): boolean {
  return (
    packStore.hasError.value ||
    modStore.hasError.value ||
    translationStore.hasError.value ||
    queueStore.hasError.value
  )
}

/**
 * 获取所有V6 Store的错误信息
 */
export function getAllV6StoreErrors(): Array<{ store: string, errors: Record<string, string | null> }> {
  return [
    { store: 'pack', errors: packStore.state.error },
    { store: 'mod', errors: modStore.state.error },
    { store: 'translation', errors: translationStore.state.error },
    { store: 'queue', errors: queueStore.state.error },
  ].filter(item => Object.values(item.errors).some(error => error !== null))
}

// ==================== Store操作组合 ====================

/**
 * 批量加载所有基础数据
 */
export async function loadAllV6BaseData() {
  try {
    await Promise.allSettled([
      packStore.loadPacks({ refresh: true }),
      modStore.loadMods({ refresh: true }),
      queueStore.loadQueueStatus(),
    ])
  } catch (error) {
    console.error('批量加载V6基础数据失败:', error)
  }
}

/**
 * 按Pack加载相关数据
 */
export async function loadDataByPack(packUid: string) {
  try {
    // 加载Pack详情
    await packStore.loadPack(packUid)
    
    // 加载该Pack下的MOD
    modStore.setFilters({ pack_uid: packUid })
    await modStore.loadMods({ refresh: true })
    
    // 可以继续加载翻译等相关数据
    // ...
  } catch (error) {
    console.error(`加载Pack ${packUid} 相关数据失败:`, error)
  }
}

/**
 * 按MOD加载相关数据
 */
export async function loadDataByMod(modUid: string) {
  try {
    // 加载MOD详情
    await modStore.loadMod(modUid)
    
    // 加载MOD兼容性信息
    await modStore.loadModCompatibility(modUid)
    
    // 加载该MOD的语言文件和翻译
    // translationStore.setFilters({ mod_uid: modUid })
    // await translationStore.loadTranslations({ refresh: true })
  } catch (error) {
    console.error(`加载MOD ${modUid} 相关数据失败:`, error)
  }
}

// ==================== 实时更新管理 ====================

/**
 * 启用所有Store的实时更新
 */
export function enableAllRealTimeUpdates(interval: number = 5000) {
  // 只有队列需要频繁更新
  queueStore.enableAutoRefresh(interval)
  
  // 其他Store可以使用较长的更新间隔
  const longInterval = interval * 6 // 30秒
  
  const refreshTimer = setInterval(() => {
    // 静默刷新，不显示加载状态
    packStore.loadPacks({ refresh: true })
    modStore.loadMods({ refresh: true })
  }, longInterval)
  
  return () => {
    queueStore.disableAutoRefresh()
    clearInterval(refreshTimer)
  }
}

/**
 * 禁用所有Store的实时更新
 */
export function disableAllRealTimeUpdates() {
  queueStore.disableAutoRefresh()
  // 其他Store的更新timer通过返回的cleanup函数处理
}

// ==================== 数据同步工具 ====================

/**
 * 同步Pack和MOD的关联关系
 */
export function syncPackModRelations() {
  const packs = packStore.state.packs
  const mods = modStore.state.mods
  
  // 为没有Pack关联的MOD提供Pack信息
  const packMap = new Map(packs.map(pack => [pack.uid, pack]))
  
  mods.forEach(mod => {
    if (mod.pack_uid && packMap.has(mod.pack_uid)) {
      // 可以在这里添加额外的关联信息处理
    }
  })
}

/**
 * 检查数据一致性
 */
export function checkV6DataConsistency(): {
  issues: Array<{ type: string, message: string, data?: any }>
  isConsistent: boolean
} {
  const issues: Array<{ type: string, message: string, data?: any }> = []
  
  // 检查Pack-MOD关联
  const packUids = new Set(packStore.state.packs.map(pack => pack.uid))
  const modsWithInvalidPack = modStore.state.mods.filter(mod => 
    mod.pack_uid && !packUids.has(mod.pack_uid)
  )
  
  if (modsWithInvalidPack.length > 0) {
    issues.push({
      type: 'invalid_pack_reference',
      message: `${modsWithInvalidPack.length} MOD(s) reference non-existent Pack`,
      data: modsWithInvalidPack.map(mod => ({ mod_uid: mod.uid, pack_uid: mod.pack_uid }))
    })
  }
  
  // 可以添加更多一致性检查...
  
  return {
    issues,
    isConsistent: issues.length === 0
  }
}

// ==================== 性能优化工具 ====================

/**
 * 预加载常用数据
 */
export async function preloadCommonData() {
  try {
    // 预加载第一页的基础数据
    await Promise.allSettled([
      packStore.loadPacks({ page: 1, pageSize: 10 }),
      modStore.loadMods({ page: 1, pageSize: 20 }),
      queueStore.loadQueueStatus(),
    ])
  } catch (error) {
    console.error('预加载常用数据失败:', error)
  }
}

/**
 * 内存优化：清理不必要的缓存数据
 */
export function optimizeV6StoreMemory() {
  // 清理选中状态
  packStore.clearSelection()
  modStore.clearSelection()
  translationStore.clearSelection()
  queueStore.clearSelection()
  
  // 清理编辑状态
  if (translationStore.state.editingTranslations.size > 0) {
    translationStore.state.editingTranslations.clear()
  }
}

// ==================== 默认导出 ====================
export default getV6Stores()