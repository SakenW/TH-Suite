/**
 * 性能优化钩子
 * 提供各种性能优化工具和策略
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { debounce, throttle } from 'lodash-es'

// 防抖钩子
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// 节流钩子
export function useThrottle<T>(value: T, delay: number): T {
  const [throttledValue, setThrottledValue] = useState<T>(value)
  const lastUpdated = useRef<number>(0)

  useEffect(() => {
    const now = Date.now()
    if (now - lastUpdated.current >= delay) {
      setThrottledValue(value)
      lastUpdated.current = now
    } else {
      const timeoutId = setTimeout(() => {
        setThrottledValue(value)
        lastUpdated.current = Date.now()
      }, delay - (now - lastUpdated.current))

      return () => clearTimeout(timeoutId)
    }
  }, [value, delay])

  return throttledValue
}

// 防抖回调钩子
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList = []
): T {
  return useCallback(
    debounce(callback, delay),
    [delay, ...deps]
  ) as T
}

// 节流回调钩子
export function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList = []
): T {
  return useCallback(
    throttle(callback, delay, { leading: true, trailing: true }),
    [delay, ...deps]
  ) as T
}

// 虚拟滚动钩子
interface UseVirtualScrollOptions {
  itemHeight: number
  containerHeight: number
  itemCount: number
  overscan?: number
}

interface VirtualScrollResult {
  startIndex: number
  endIndex: number
  visibleItems: number[]
  scrollTop: number
  totalHeight: number
  offsetY: number
}

export function useVirtualScroll({
  itemHeight,
  containerHeight,
  itemCount,
  overscan = 5,
}: UseVirtualScrollOptions): [VirtualScrollResult, (scrollTop: number) => void] {
  const [scrollTop, setScrollTop] = useState(0)

  const result = useMemo(() => {
    const visibleItemCount = Math.ceil(containerHeight / itemHeight)
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan)
    const endIndex = Math.min(itemCount - 1, startIndex + visibleItemCount + overscan * 2)
    
    const visibleItems = Array.from(
      { length: endIndex - startIndex + 1 },
      (_, index) => startIndex + index
    )

    return {
      startIndex,
      endIndex,
      visibleItems,
      scrollTop,
      totalHeight: itemCount * itemHeight,
      offsetY: startIndex * itemHeight,
    }
  }, [itemHeight, containerHeight, itemCount, overscan, scrollTop])

  return [result, setScrollTop]
}

// 懒加载钩子
export function useLazyLoad<T>(
  loadFunc: () => Promise<T>,
  deps: React.DependencyList = []
): {
  data: T | null
  loading: boolean
  error: Error | null
  reload: () => void
} {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const mountedRef = useRef(true)

  const load = useCallback(async () => {
    if (!mountedRef.current) return
    
    setLoading(true)
    setError(null)

    try {
      const result = await loadFunc()
      if (mountedRef.current) {
        setData(result)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err as Error)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, deps)

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    return () => {
      mountedRef.current = false
    }
  }, [])

  return {
    data,
    loading,
    error,
    reload: load,
  }
}

// 内存优化钩子 - 大型列表分页
interface UsePaginatedListOptions<T> {
  data: T[]
  pageSize: number
  prefetchPages?: number
}

export function usePaginatedList<T>({
  data,
  pageSize,
  prefetchPages = 2,
}: UsePaginatedListOptions<T>) {
  const [currentPage, setCurrentPage] = useState(0)
  
  const totalPages = Math.ceil(data.length / pageSize)
  
  // 计算预加载范围
  const visiblePages = useMemo(() => {
    const startPage = Math.max(0, currentPage - prefetchPages)
    const endPage = Math.min(totalPages - 1, currentPage + prefetchPages)
    
    const pages: T[][] = []
    for (let i = startPage; i <= endPage; i++) {
      const start = i * pageSize
      const end = Math.min(start + pageSize, data.length)
      pages[i] = data.slice(start, end)
    }
    
    return pages
  }, [data, currentPage, pageSize, prefetchPages, totalPages])

  const currentPageData = visiblePages[currentPage] || []

  return {
    currentPage,
    currentPageData,
    totalPages,
    hasNextPage: currentPage < totalPages - 1,
    hasPrevPage: currentPage > 0,
    goToPage: setCurrentPage,
    nextPage: () => setCurrentPage(prev => Math.min(prev + 1, totalPages - 1)),
    prevPage: () => setCurrentPage(prev => Math.max(prev - 1, 0)),
  }
}

// 性能监控钩子
interface PerformanceMetrics {
  renderTime: number
  updateCount: number
  lastRenderTime: Date
  averageRenderTime: number
}

export function usePerformanceMonitor(componentName: string): PerformanceMetrics {
  const renderCountRef = useRef(0)
  const renderTimesRef = useRef<number[]>([])
  const startTimeRef = useRef<number>()
  
  // 开始计时
  const startTime = performance.now()
  startTimeRef.current = startTime
  
  useEffect(() => {
    // 结束计时
    const endTime = performance.now()
    const renderTime = endTime - (startTimeRef.current || endTime)
    
    renderCountRef.current += 1
    renderTimesRef.current.push(renderTime)
    
    // 只保留最近100次的渲染时间
    if (renderTimesRef.current.length > 100) {
      renderTimesRef.current = renderTimesRef.current.slice(-100)
    }
    
    // 在开发模式下输出性能警告
    if (process.env.NODE_ENV === 'development' && renderTime > 16) {
      console.warn(
        `Performance warning: ${componentName} took ${renderTime.toFixed(2)}ms to render`
      )
    }
  })

  return {
    renderTime: startTimeRef.current ? performance.now() - startTimeRef.current : 0,
    updateCount: renderCountRef.current,
    lastRenderTime: new Date(),
    averageRenderTime: renderTimesRef.current.length > 0 
      ? renderTimesRef.current.reduce((a, b) => a + b, 0) / renderTimesRef.current.length
      : 0,
  }
}

// 内存泄漏预防钩子
export function useCleanup(cleanup: () => void, deps: React.DependencyList = []) {
  useEffect(() => {
    return cleanup
  }, deps)
}

// 大数据集优化钩子
interface UseLargeDatasetOptions<T> {
  data: T[]
  chunkSize?: number
  processChunk?: (chunk: T[]) => T[]
  onProgress?: (progress: number) => void
}

export function useLargeDataset<T>({
  data,
  chunkSize = 1000,
  processChunk,
  onProgress,
}: UseLargeDatasetOptions<T>) {
  const [processedData, setProcessedData] = useState<T[]>([])
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (data.length === 0) {
      setProcessedData([])
      setProgress(0)
      return
    }

    setProcessing(true)
    setProgress(0)

    // 分块处理大数据集
    const processInChunks = async () => {
      const result: T[] = []
      const totalChunks = Math.ceil(data.length / chunkSize)

      for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSize
        const end = Math.min(start + chunkSize, data.length)
        const chunk = data.slice(start, end)

        const processedChunk = processChunk ? processChunk(chunk) : chunk
        result.push(...processedChunk)

        const currentProgress = ((i + 1) / totalChunks) * 100
        setProgress(currentProgress)
        onProgress?.(currentProgress)

        // 让出控制权，避免阻塞UI
        await new Promise(resolve => setTimeout(resolve, 0))
      }

      setProcessedData(result)
      setProcessing(false)
    }

    processInChunks()
  }, [data, chunkSize, processChunk, onProgress])

  return {
    data: processedData,
    processing,
    progress,
  }
}

// 智能缓存钩子
interface CacheEntry<T> {
  value: T
  timestamp: number
  accessCount: number
}

export function useSmartCache<T>(
  maxSize: number = 100,
  ttl: number = 5 * 60 * 1000 // 5分钟
) {
  const cache = useRef(new Map<string, CacheEntry<T>>())

  const get = useCallback((key: string): T | undefined => {
    const entry = cache.current.get(key)
    
    if (!entry) return undefined
    
    // 检查是否过期
    if (Date.now() - entry.timestamp > ttl) {
      cache.current.delete(key)
      return undefined
    }
    
    // 更新访问计数
    entry.accessCount++
    return entry.value
  }, [ttl])

  const set = useCallback((key: string, value: T) => {
    // 如果缓存已满，删除最少访问的条目
    if (cache.current.size >= maxSize) {
      let leastAccessedKey = ''
      let leastAccessCount = Infinity
      
      for (const [k, entry] of cache.current.entries()) {
        if (entry.accessCount < leastAccessCount) {
          leastAccessCount = entry.accessCount
          leastAccessedKey = k
        }
      }
      
      if (leastAccessedKey) {
        cache.current.delete(leastAccessedKey)
      }
    }

    cache.current.set(key, {
      value,
      timestamp: Date.now(),
      accessCount: 0,
    })
  }, [maxSize])

  const clear = useCallback(() => {
    cache.current.clear()
  }, [])

  const size = cache.current.size

  return { get, set, clear, size }
}