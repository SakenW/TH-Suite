/**
 * 虚拟化Hook - 基于@tanstack/react-virtual
 * 提供高性能大数据虚拟化渲染能力
 */

import { useMemo, useRef, useCallback, useState, useEffect } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

// ============================================================
// 类型定义
// ============================================================

export interface VirtualizerConfig<T = any> {
  // 基础配置
  data: T[]
  estimateSize?: number | ((index: number) => number)
  overscan?: number
  
  // 容器配置
  scrollMargin?: number
  paddingStart?: number
  paddingEnd?: number
  
  // 性能优化
  measureElement?: (element: Element) => number
  getItemKey?: (index: number, item: T) => string | number
  
  // 缓存配置
  cacheSize?: number
  enableMeasureCache?: boolean
  
  // 滚动配置
  initialOffset?: number
  scrollBehavior?: ScrollBehavior
  
  // 响应式配置
  responsive?: {
    breakpoints: Record<string, number>
    estimateSizes: Record<string, number>
  }
}

export interface VirtualItem<T = any> {
  key: string | number
  index: number
  start: number
  size: number
  end: number
  item: T
}

export interface VirtualizerResult<T = any> {
  // 虚拟化实例
  virtualizer: ReturnType<typeof useVirtualizer>
  
  // 渲染项目
  virtualItems: VirtualItem<T>[]
  
  // 容器引用
  parentRef: React.RefObject<HTMLElement>
  
  // 控制方法
  scrollToIndex: (index: number, options?: { align?: 'start' | 'center' | 'end', behavior?: ScrollBehavior }) => void
  scrollToTop: () => void
  scrollToBottom: () => void
  
  // 状态信息
  totalSize: number
  isScrolling: boolean
  
  // 性能统计
  stats: {
    visibleRange: [number, number]
    totalCount: number
    renderedCount: number
    cacheHitRate: number
  }
}

// ============================================================
// 主Hook
// ============================================================

export function useVirtualized<T = any>({
  data,
  estimateSize = 50,
  overscan = 5,
  scrollMargin = 0,
  paddingStart = 0,
  paddingEnd = 0,
  measureElement,
  getItemKey,
  cacheSize = 100,
  enableMeasureCache = true,
  initialOffset = 0,
  scrollBehavior = 'auto',
  responsive,
}: VirtualizerConfig<T>): VirtualizerResult<T> {
  
  const parentRef = useRef<HTMLElement>(null)
  const [isScrolling, setIsScrolling] = useState(false)
  const [cacheHits, setCacheHits] = useState(0)
  const [totalRequests, setTotalRequests] = useState(0)
  
  // 响应式尺寸计算
  const currentEstimateSize = useMemo(() => {
    if (!responsive) return estimateSize
    
    const width = window.innerWidth
    for (const [breakpoint, size] of Object.entries(responsive.estimateSizes)) {
      const breakpointWidth = responsive.breakpoints[breakpoint]
      if (width >= breakpointWidth) {
        return size
      }
    }
    return typeof estimateSize === 'function' ? estimateSize : estimateSize
  }, [estimateSize, responsive])
  
  // 尺寸缓存
  const sizeCache = useMemo(() => {
    if (!enableMeasureCache) return null
    return new Map<number, number>()
  }, [enableMeasureCache])
  
  // 优化的尺寸估算函数
  const optimizedEstimateSize = useCallback((index: number) => {
    // 缓存检查
    if (sizeCache?.has(index)) {
      setCacheHits(prev => prev + 1)
      return sizeCache.get(index)!
    }
    
    setTotalRequests(prev => prev + 1)
    
    if (typeof currentEstimateSize === 'function') {
      const size = currentEstimateSize(index)
      if (sizeCache && sizeCache.size < cacheSize) {
        sizeCache.set(index, size)
      }
      return size
    }
    
    return currentEstimateSize
  }, [currentEstimateSize, sizeCache, cacheSize])
  
  // 自定义测量函数
  const customMeasureElement = useCallback((element: Element) => {
    const height = measureElement ? measureElement(element) : element.getBoundingClientRect().height
    
    // 更新缓存
    if (sizeCache && element.getAttribute('data-index')) {
      const index = parseInt(element.getAttribute('data-index')!, 10)
      sizeCache.set(index, height)
    }
    
    return height
  }, [measureElement, sizeCache])
  
  // 创建虚拟化实例
  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: optimizedEstimateSize,
    overscan,
    scrollMargin,
    paddingStart,
    paddingEnd,
    measureElement: measureElement ? customMeasureElement : undefined,
    initialOffset,
    scrollBehavior,
    
    // 滚动监听
    onChange: (instance) => {
      setIsScrolling(instance.isScrolling)
    },
  })
  
  // 生成虚拟项目
  const virtualItems = useMemo((): VirtualItem<T>[] => {
    return virtualizer.getVirtualItems().map((virtualItem) => ({
      key: getItemKey ? getItemKey(virtualItem.index, data[virtualItem.index]) : virtualItem.key,
      index: virtualItem.index,
      start: virtualItem.start,
      size: virtualItem.size,
      end: virtualItem.end,
      item: data[virtualItem.index],
    }))
  }, [virtualizer, data, getItemKey])
  
  // 控制方法
  const scrollToIndex = useCallback((
    index: number, 
    options: { align?: 'start' | 'center' | 'end', behavior?: ScrollBehavior } = {}
  ) => {
    virtualizer.scrollToIndex(index, {
      align: options.align || 'start',
      behavior: options.behavior || scrollBehavior,
    })
  }, [virtualizer, scrollBehavior])
  
  const scrollToTop = useCallback(() => {
    scrollToIndex(0, { align: 'start' })
  }, [scrollToIndex])
  
  const scrollToBottom = useCallback(() => {
    scrollToIndex(data.length - 1, { align: 'end' })
  }, [scrollToIndex, data.length])
  
  // 性能统计
  const stats = useMemo(() => {
    const visibleRange = virtualItems.length > 0 
      ? [virtualItems[0].index, virtualItems[virtualItems.length - 1].index] as [number, number]
      : [0, 0] as [number, number]
    
    const cacheHitRate = totalRequests > 0 ? (cacheHits / totalRequests) * 100 : 0
    
    return {
      visibleRange,
      totalCount: data.length,
      renderedCount: virtualItems.length,
      cacheHitRate,
    }
  }, [virtualItems, data.length, cacheHits, totalRequests])
  
  // 响应式更新
  useEffect(() => {
    if (!responsive) return
    
    const handleResize = () => {
      // 清除缓存，重新计算尺寸
      sizeCache?.clear()
      setCacheHits(0)
      setTotalRequests(0)
      virtualizer.measure()
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [responsive, sizeCache, virtualizer])
  
  return {
    virtualizer,
    virtualItems,
    parentRef,
    scrollToIndex,
    scrollToTop,
    scrollToBottom,
    totalSize: virtualizer.getTotalSize(),
    isScrolling,
    stats,
  }
}

// ============================================================
// 预设配置
// ============================================================

// 表格行配置
export const TABLE_ROW_CONFIG: Partial<VirtualizerConfig> = {
  estimateSize: 56,
  overscan: 10,
  scrollMargin: 0,
  enableMeasureCache: true,
  cacheSize: 200,
}

// 列表项配置
export const LIST_ITEM_CONFIG: Partial<VirtualizerConfig> = {
  estimateSize: 72,
  overscan: 8,
  scrollMargin: 8,
  enableMeasureCache: true,
  cacheSize: 150,
}

// 树节点配置
export const TREE_NODE_CONFIG: Partial<VirtualizerConfig> = {
  estimateSize: 32,
  overscan: 15,
  scrollMargin: 4,
  enableMeasureCache: true,
  cacheSize: 300,
}

// 卡片配置
export const CARD_CONFIG: Partial<VirtualizerConfig> = {
  estimateSize: 120,
  overscan: 5,
  scrollMargin: 12,
  enableMeasureCache: true,
  cacheSize: 100,
}

// 响应式配置示例
export const RESPONSIVE_CONFIG = {
  breakpoints: {
    xs: 0,
    sm: 576,
    md: 768,
    lg: 992,
    xl: 1200,
    xxl: 1600,
  },
  estimateSizes: {
    xs: 48,
    sm: 56,
    md: 64,
    lg: 72,
    xl: 80,
    xxl: 88,
  },
}