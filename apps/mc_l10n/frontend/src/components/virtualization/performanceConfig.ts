/**
 * 虚拟化性能配置和优化策略
 * 针对不同场景提供最优配置
 */

import { VirtualizerConfig } from './useVirtualizer'
import type { VirtualizedListProps } from './VirtualizedList'
import type { VirtualizedDataTableProps } from './VirtualizedDataTable'
import type { VirtualizedTreeProps } from './VirtualizedTree'

// ============================================================
// 基础性能配置
// ============================================================

export interface PerformancePreset {
  name: string
  description: string
  config: Partial<VirtualizerConfig>
  recommended: {
    minDataSize: number
    maxDataSize: number
    scenarios: string[]
  }
}

// 性能预设配置
export const PERFORMANCE_PRESETS: Record<string, PerformancePreset> = {
  // 超高性能模式 - 适合10万+数据
  ULTRA_PERFORMANCE: {
    name: '超高性能',
    description: '适合超大数据集（10万+），最大化性能，最小化内存占用',
    config: {
      estimateSize: 48,
      overscan: 3,
      enableMeasureCache: true,
      cacheSize: 50,
      scrollMargin: 0,
      paddingStart: 0,
      paddingEnd: 0,
    },
    recommended: {
      minDataSize: 100000,
      maxDataSize: 1000000,
      scenarios: ['大型数据报表', '日志查看器', '文件浏览器']
    }
  },

  // 高性能模式 - 适合1万-10万数据
  HIGH_PERFORMANCE: {
    name: '高性能',
    description: '适合大数据集（1万-10万），平衡性能和功能',
    config: {
      estimateSize: 56,
      overscan: 5,
      enableMeasureCache: true,
      cacheSize: 100,
      scrollMargin: 0,
      paddingStart: 0,
      paddingEnd: 0,
    },
    recommended: {
      minDataSize: 10000,
      maxDataSize: 100000,
      scenarios: ['MOD列表', '文件清单', '数据表格']
    }
  },

  // 平衡模式 - 适合1千-1万数据
  BALANCED: {
    name: '平衡模式',
    description: '适合中等数据集（1千-1万），平衡性能和用户体验',
    config: {
      estimateSize: 64,
      overscan: 8,
      enableMeasureCache: true,
      cacheSize: 150,
      scrollMargin: 4,
      paddingStart: 0,
      paddingEnd: 0,
    },
    recommended: {
      minDataSize: 1000,
      maxDataSize: 10000,
      scenarios: ['项目列表', '搜索结果', '配置项']
    }
  },

  // 流畅模式 - 适合100-1千数据
  SMOOTH: {
    name: '流畅模式',
    description: '适合小到中等数据集（100-1千），优化动画和交互',
    config: {
      estimateSize: 72,
      overscan: 10,
      enableMeasureCache: true,
      cacheSize: 200,
      scrollMargin: 8,
      paddingStart: 0,
      paddingEnd: 0,
    },
    recommended: {
      minDataSize: 100,
      maxDataSize: 1000,
      scenarios: ['菜单', '选项列表', '简单表格']
    }
  },

  // 动画优化模式
  ANIMATION_OPTIMIZED: {
    name: '动画优化',
    description: '优化动画性能，适合需要复杂交互的场景',
    config: {
      estimateSize: 80,
      overscan: 12,
      enableMeasureCache: true,
      cacheSize: 250,
      scrollMargin: 12,
      paddingStart: 8,
      paddingEnd: 8,
    },
    recommended: {
      minDataSize: 10,
      maxDataSize: 5000,
      scenarios: ['卡片网格', '图片画廊', '交互列表']
    }
  }
}

// ============================================================
// 场景特定配置
// ============================================================

// MOD列表优化配置
export const MOD_LIST_CONFIG: Partial<VirtualizedListProps> = {
  virtualizerConfig: {
    ...PERFORMANCE_PRESETS.HIGH_PERFORMANCE.config,
    estimateSize: (index: number) => {
      // 动态行高：紧凑模式 64px，卡片模式 120px
      return 72
    },
    responsive: {
      breakpoints: { xs: 0, sm: 576, md: 768, lg: 992, xl: 1200 },
      estimateSizes: { xs: 56, sm: 64, md: 72, lg: 80, xl: 88 },
    }
  },
  responsive: true,
  showPerformanceStats: (import.meta as any).env?.MODE === 'development',
}

// 数据表格优化配置
export const DATA_TABLE_CONFIG: Partial<VirtualizedDataTableProps> = {
  rowHeight: 48,
  overscan: 10,
  headerHeight: 48,
  striped: true,
  bordered: true,
  responsive: true,
  stickyHeader: true,
  showPerformanceStats: (import.meta as any).env?.MODE === 'development',
}

// 文件树优化配置
export const FILE_TREE_CONFIG: Partial<VirtualizedTreeProps> = {
  nodeHeight: 32,
  overscan: 15,
  indent: 20,
  showLine: true,
  showIcon: true,
  responsive: true,
  showPerformanceStats: (import.meta as any).env?.MODE === 'development',
}

// ============================================================
// 设备特定优化
// ============================================================

export interface DeviceOptimization {
  name: string
  condition: () => boolean
  modifications: Partial<VirtualizerConfig>
}

export const DEVICE_OPTIMIZATIONS: DeviceOptimization[] = [
  // 移动设备优化
  {
    name: 'mobile',
    condition: () => window.innerWidth <= 768,
    modifications: {
      overscan: 3, // 减少缓冲区
      cacheSize: 50, // 减少缓存
      estimateSize: 48, // 减小行高
    }
  },

  // 平板设备优化
  {
    name: 'tablet',
    condition: () => window.innerWidth > 768 && window.innerWidth <= 1024,
    modifications: {
      overscan: 5,
      cacheSize: 100,
      estimateSize: 56,
    }
  },

  // 桌面设备优化
  {
    name: 'desktop',
    condition: () => window.innerWidth > 1024,
    modifications: {
      overscan: 8,
      cacheSize: 200,
      estimateSize: 64,
    }
  },

  // 高分辨率屏幕优化
  {
    name: 'high-dpi',
    condition: () => window.devicePixelRatio > 2,
    modifications: {
      estimateSize: (size: number) => size * 1.2, // 增加行高
      scrollMargin: 8,
    }
  },

  // 低内存设备优化
  {
    name: 'low-memory',
    condition: () => (navigator as any).deviceMemory && (navigator as any).deviceMemory < 4,
    modifications: {
      overscan: 2, // 最小缓冲区
      cacheSize: 25, // 最小缓存
      enableMeasureCache: false, // 禁用尺寸缓存
    }
  }
]

// ============================================================
// 自适应配置函数
// ============================================================

/**
 * 根据数据量自动选择性能预设
 */
export function getOptimalPreset(dataSize: number): PerformancePreset {
  for (const preset of Object.values(PERFORMANCE_PRESETS)) {
    if (dataSize >= preset.recommended.minDataSize && dataSize <= preset.recommended.maxDataSize) {
      return preset
    }
  }
  
  // 默认返回平衡模式
  return PERFORMANCE_PRESETS.BALANCED
}

/**
 * 应用设备特定优化
 */
export function applyDeviceOptimizations(config: VirtualizerConfig): VirtualizerConfig {
  let optimizedConfig = { ...config }
  
  for (const optimization of DEVICE_OPTIMIZATIONS) {
    if (optimization.condition()) {
      optimizedConfig = {
        ...optimizedConfig,
        ...optimization.modifications,
      }
    }
  }
  
  return optimizedConfig
}

/**
 * 获取优化后的配置
 */
export function getOptimizedConfig(dataSize: number, customConfig?: Partial<VirtualizerConfig>): VirtualizerConfig {
  // 1. 选择基础预设
  const preset = getOptimalPreset(dataSize)
  
  // 2. 应用设备优化
  const deviceOptimized = applyDeviceOptimizations(preset.config as VirtualizerConfig)
  
  // 3. 应用自定义配置
  const finalConfig: VirtualizerConfig = {
    ...deviceOptimized,
    ...customConfig,
    data: [], // 这个会在使用时覆盖
  }
  
  return finalConfig
}

// ============================================================
// 性能监控和警告
// ============================================================

export interface PerformanceThresholds {
  fps: { good: number; warning: number; error: number }
  memory: { good: number; warning: number; error: number } // MB
  renderTime: { good: number; warning: number; error: number } // ms
  cacheHitRate: { good: number; warning: number; error: number } // %
}

export const DEFAULT_THRESHOLDS: PerformanceThresholds = {
  fps: { good: 55, warning: 45, error: 30 },
  memory: { good: 100, warning: 300, error: 500 },
  renderTime: { good: 16, warning: 33, error: 50 }, // 60fps=16ms, 30fps=33ms
  cacheHitRate: { good: 80, warning: 60, error: 40 }
}

/**
 * 评估性能状态
 */
export function evaluatePerformance(
  metrics: {
    fps: number
    memoryUsage: number
    renderTime: number
    cacheHitRate: number
  },
  thresholds = DEFAULT_THRESHOLDS
) {
  const results = {
    overall: 'good' as 'good' | 'warning' | 'error',
    details: {} as Record<string, 'good' | 'warning' | 'error'>,
    suggestions: [] as string[]
  }
  
  // FPS评估
  if (metrics.fps >= thresholds.fps.good) {
    results.details.fps = 'good'
  } else if (metrics.fps >= thresholds.fps.warning) {
    results.details.fps = 'warning'
    results.suggestions.push('考虑减少overscan或禁用动画以提高FPS')
  } else {
    results.details.fps = 'error'
    results.suggestions.push('FPS过低，建议使用ULTRA_PERFORMANCE模式')
  }
  
  // 内存评估
  if (metrics.memoryUsage <= thresholds.memory.good) {
    results.details.memory = 'good'
  } else if (metrics.memoryUsage <= thresholds.memory.warning) {
    results.details.memory = 'warning'
    results.suggestions.push('内存使用较高，考虑减少cacheSize')
  } else {
    results.details.memory = 'error'
    results.suggestions.push('内存使用过高，建议禁用缓存或减少数据量')
  }
  
  // 渲染时间评估
  if (metrics.renderTime <= thresholds.renderTime.good) {
    results.details.renderTime = 'good'
  } else if (metrics.renderTime <= thresholds.renderTime.warning) {
    results.details.renderTime = 'warning'
    results.suggestions.push('渲染时间较长，考虑简化项目渲染逻辑')
  } else {
    results.details.renderTime = 'error'
    results.suggestions.push('渲染时间过长，建议优化组件或使用更高性能预设')
  }
  
  // 缓存命中率评估
  if (metrics.cacheHitRate >= thresholds.cacheHitRate.good) {
    results.details.cacheHitRate = 'good'
  } else if (metrics.cacheHitRate >= thresholds.cacheHitRate.warning) {
    results.details.cacheHitRate = 'warning'
    results.suggestions.push('缓存命中率较低，考虑增加cacheSize')
  } else {
    results.details.cacheHitRate = 'error'
    results.suggestions.push('缓存命中率过低，检查数据变化频率')
  }
  
  // 计算总体状态
  const errorCount = Object.values(results.details).filter(s => s === 'error').length
  const warningCount = Object.values(results.details).filter(s => s === 'warning').length
  
  if (errorCount > 0) {
    results.overall = 'error'
  } else if (warningCount > 0) {
    results.overall = 'warning'
  }
  
  return results
}

// ============================================================
// 导出便捷函数
// ============================================================

/**
 * 创建MOD列表配置
 */
export function createModListConfig(dataSize: number, customConfig?: Partial<VirtualizedListProps>): Partial<VirtualizedListProps> {
  const optimizedConfig = getOptimizedConfig(dataSize)
  
  return {
    ...MOD_LIST_CONFIG,
    virtualizerConfig: {
      ...MOD_LIST_CONFIG.virtualizerConfig,
      ...optimizedConfig,
    },
    ...customConfig,
  }
}

/**
 * 创建数据表格配置
 */
export function createDataTableConfig(dataSize: number, customConfig?: Partial<VirtualizedDataTableProps>): Partial<VirtualizedDataTableProps> {
  const optimizedConfig = getOptimizedConfig(dataSize)
  
  return {
    ...DATA_TABLE_CONFIG,
    overscan: optimizedConfig.overscan,
    rowHeight: typeof optimizedConfig.estimateSize === 'number' ? optimizedConfig.estimateSize : 48,
    ...customConfig,
  }
}

/**
 * 创建文件树配置
 */
export function createFileTreeConfig(dataSize: number, customConfig?: Partial<VirtualizedTreeProps>): Partial<VirtualizedTreeProps> {
  const optimizedConfig = getOptimizedConfig(dataSize)
  
  return {
    ...FILE_TREE_CONFIG,
    overscan: optimizedConfig.overscan,
    nodeHeight: typeof optimizedConfig.estimateSize === 'number' ? optimizedConfig.estimateSize : 32,
    ...customConfig,
  }
}