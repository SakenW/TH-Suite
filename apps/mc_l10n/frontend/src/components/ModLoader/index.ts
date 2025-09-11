/**
 * MOD加载器组件模块
 * 提供完整的多MOD加载器支持界面组件
 */

export { ModInfoCard } from './ModInfoCard'
export { ModLoaderStats } from './ModLoaderStats' 
export { ModList } from './ModList'
export { ModDependencyGraph } from './ModDependencyGraph'
export { ModLoaderManager } from './ModLoaderManager'

export type { ModInfo } from './ModInfoCard'
export type { ModLoaderStatistics } from './ModLoaderStats'
export type { DependencyAnalysis } from './ModDependencyGraph'

// 重新导出常用类型
export interface ModLoaderComponents {
  ModInfoCard: typeof import('./ModInfoCard').ModInfoCard
  ModLoaderStats: typeof import('./ModLoaderStats').ModLoaderStats
  ModList: typeof import('./ModList').ModList
  ModDependencyGraph: typeof import('./ModDependencyGraph').ModDependencyGraph
  ModLoaderManager: typeof import('./ModLoaderManager').ModLoaderManager
}