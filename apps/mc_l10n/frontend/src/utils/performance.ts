/**
 * 性能监控和优化工具
 */

interface PerformanceMetrics {
  fps: number
  memory: number
  loadTime: number
  renderTime: number
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics = {
    fps: 60,
    memory: 0,
    loadTime: 0,
    renderTime: 0,
  }

  private fpsFrames: number[] = []
  private lastFrameTime: number = performance.now()
  private rafId: number | null = null

  /**
   * 开始监控 FPS
   */
  startFPSMonitoring() {
    const measureFPS = () => {
      const now = performance.now()
      const delta = now - this.lastFrameTime
      this.lastFrameTime = now

      // 计算 FPS
      const fps = 1000 / delta
      this.fpsFrames.push(fps)

      // 保持最近 60 帧的数据
      if (this.fpsFrames.length > 60) {
        this.fpsFrames.shift()
      }

      // 计算平均 FPS
      this.metrics.fps = Math.round(
        this.fpsFrames.reduce((a, b) => a + b, 0) / this.fpsFrames.length,
      )

      this.rafId = requestAnimationFrame(measureFPS)
    }

    measureFPS()
  }

  /**
   * 停止监控 FPS
   */
  stopFPSMonitoring() {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId)
      this.rafId = null
    }
  }

  /**
   * 测量内存使用
   */
  measureMemory() {
    if ('memory' in performance) {
      const memory = (performance as any).memory
      this.metrics.memory = Math.round(memory.usedJSHeapSize / 1048576) // MB
    }
  }

  /**
   * 测量页面加载时间
   */
  measureLoadTime() {
    if (performance.timing) {
      const timing = performance.timing
      this.metrics.loadTime = timing.loadEventEnd - timing.navigationStart
    }
  }

  /**
   * 测量组件渲染时间
   */
  measureRenderTime(callback: () => void): number {
    const start = performance.now()
    callback()
    const end = performance.now()
    const renderTime = end - start
    this.metrics.renderTime = renderTime
    return renderTime
  }

  /**
   * 获取当前性能指标
   */
  getMetrics(): PerformanceMetrics {
    this.measureMemory()
    return { ...this.metrics }
  }

  /**
   * 性能优化建议
   */
  getOptimizationSuggestions(): string[] {
    const suggestions: string[] = []

    if (this.metrics.fps < 30) {
      suggestions.push('FPS 较低，考虑减少动画效果或优化渲染')
    }

    if (this.metrics.memory > 100) {
      suggestions.push('内存使用较高，考虑清理未使用的组件或数据')
    }

    if (this.metrics.loadTime > 3000) {
      suggestions.push('页面加载时间较长，考虑使用代码分割或懒加载')
    }

    if (this.metrics.renderTime > 16) {
      suggestions.push('渲染时间超过 16ms，可能导致掉帧')
    }

    return suggestions
  }
}

// 单例实例
export const performanceMonitor = new PerformanceMonitor()

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      func(...args)
    }

    if (timeout !== null) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(later, wait)
  }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle: boolean = false

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}

/**
 * 虚拟列表优化
 */
export interface VirtualListOptions {
  itemHeight: number
  containerHeight: number
  buffer?: number
}

export function calculateVisibleItems<T>(
  items: T[],
  scrollTop: number,
  options: VirtualListOptions,
): {
  visibleItems: T[]
  startIndex: number
  endIndex: number
  totalHeight: number
} {
  const { itemHeight, containerHeight, buffer = 3 } = options

  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - buffer)
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + buffer,
  )

  const visibleItems = items.slice(startIndex, endIndex + 1)
  const totalHeight = items.length * itemHeight

  return {
    visibleItems,
    startIndex,
    endIndex,
    totalHeight,
  }
}

/**
 * 图片懒加载
 */
export function lazyLoadImages(selector: string = 'img[data-lazy]') {
  const images = document.querySelectorAll<HTMLImageElement>(selector)

  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target as HTMLImageElement
        const src = img.dataset.lazy
        if (src) {
          img.src = src
          img.removeAttribute('data-lazy')
          observer.unobserve(img)
        }
      }
    })
  })

  images.forEach(img => imageObserver.observe(img))
}

/**
 * 内存缓存
 */
export class MemoryCache<T> {
  private cache = new Map<string, { data: T; timestamp: number }>()
  private maxSize: number
  private ttl: number

  constructor(maxSize: number = 100, ttl: number = 60000) {
    this.maxSize = maxSize
    this.ttl = ttl
  }

  set(key: string, value: T): void {
    // 清理过期项
    this.cleanExpired()

    // 如果缓存已满，删除最旧的项
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      if (firstKey) {
        this.cache.delete(firstKey)
      }
    }

    this.cache.set(key, {
      data: value,
      timestamp: Date.now(),
    })
  }

  get(key: string): T | undefined {
    const item = this.cache.get(key)

    if (!item) {
      return undefined
    }

    // 检查是否过期
    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key)
      return undefined
    }

    return item.data
  }

  has(key: string): boolean {
    return this.get(key) !== undefined
  }

  delete(key: string): void {
    this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
  }

  private cleanExpired(): void {
    const now = Date.now()
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > this.ttl) {
        this.cache.delete(key)
      }
    }
  }
}

/**
 * Web Worker 池
 */
export class WorkerPool {
  private workers: Worker[] = []
  private queue: Array<{ data: any; resolve: (value: any) => void }> = []
  private busyWorkers = new Set<Worker>()

  constructor(workerScript: string, poolSize: number = 4) {
    for (let i = 0; i < poolSize; i++) {
      const worker = new Worker(workerScript)
      this.workers.push(worker)
    }
  }

  async execute(data: any): Promise<any> {
    return new Promise(resolve => {
      const availableWorker = this.workers.find(w => !this.busyWorkers.has(w))

      if (availableWorker) {
        this.runWorker(availableWorker, data, resolve)
      } else {
        this.queue.push({ data, resolve })
      }
    })
  }

  private runWorker(worker: Worker, data: any, resolve: (value: any) => void) {
    this.busyWorkers.add(worker)

    const handleMessage = (e: MessageEvent) => {
      worker.removeEventListener('message', handleMessage)
      this.busyWorkers.delete(worker)
      resolve(e.data)

      // 处理队列中的下一个任务
      const next = this.queue.shift()
      if (next) {
        this.runWorker(worker, next.data, next.resolve)
      }
    }

    worker.addEventListener('message', handleMessage)
    worker.postMessage(data)
  }

  terminate() {
    this.workers.forEach(worker => worker.terminate())
    this.workers = []
    this.queue = []
    this.busyWorkers.clear()
  }
}

/**
 * 批量操作优化
 */
export function batchOperations<T>(
  items: T[],
  operation: (batch: T[]) => Promise<void>,
  batchSize: number = 50,
  delay: number = 0,
): Promise<void> {
  return new Promise(async (resolve, reject) => {
    try {
      for (let i = 0; i < items.length; i += batchSize) {
        const batch = items.slice(i, i + batchSize)
        await operation(batch)

        if (delay > 0 && i + batchSize < items.length) {
          await new Promise(r => setTimeout(r, delay))
        }
      }
      resolve()
    } catch (error) {
      reject(error)
    }
  })
}
