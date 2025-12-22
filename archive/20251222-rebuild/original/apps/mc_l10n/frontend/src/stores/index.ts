/**
 * 状态管理统一导出
 * 整合传统Store和V6 Store
 */

// ==================== V6状态管理 ====================
export * from './v6'
export { default as v6Stores } from './v6'

// ==================== 传统状态管理 ====================
// 如果有传统的Store，在这里导出
// export * from './legacy'

// ==================== 统一状态管理接口 ====================

import { getV6Stores, type V6Stores } from './v6'

/**
 * 应用程序所有状态管理的集合
 */
export interface AppStores {
  v6: V6Stores
  // legacy?: LegacyStores
}

/**
 * 获取所有应用状态管理
 */
export function getAppStores(): AppStores {
  return {
    v6: getV6Stores(),
    // legacy: getLegacyStores(),
  }
}

/**
 * 全局状态管理实例
 */
export const appStores = getAppStores()

// ==================== 全局操作 ====================

/**
 * 重置所有状态
 */
export function resetAllStores() {
  // 重置V6状态
  appStores.v6.pack.reset()
  appStores.v6.mod.reset()
  appStores.v6.translation.reset()
  appStores.v6.queue.reset()
  
  // 重置传统状态（如果有）
  // ...
}

/**
 * 清除所有错误
 */
export function clearAllErrors() {
  // 清除V6错误
  appStores.v6.pack.clearError()
  appStores.v6.mod.clearError()
  appStores.v6.translation.clearError()
  appStores.v6.queue.clearError()
  
  // 清除传统错误（如果有）
  // ...
}

/**
 * 检查全局加载状态
 */
export function isGlobalLoading(): boolean {
  return (
    appStores.v6.pack.isLoading.value ||
    appStores.v6.mod.isLoading.value ||
    appStores.v6.translation.isLoading.value ||
    appStores.v6.queue.isLoading.value
  )
}

/**
 * 检查全局错误状态
 */
export function hasGlobalError(): boolean {
  return (
    appStores.v6.pack.hasError.value ||
    appStores.v6.mod.hasError.value ||
    appStores.v6.translation.hasError.value ||
    appStores.v6.queue.hasError.value
  )
}

// ==================== 默认导出 ====================
export default appStores