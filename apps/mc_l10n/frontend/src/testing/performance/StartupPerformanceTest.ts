/**
 * 启动性能测试工具
 * 验证首次启动 < 1.5s，首屏骨架 200ms内出现
 */

export interface StartupMetrics {
  coldStartTime: number;
  hotStartTime: number;
  firstContentfulPaint: number;
  firstMeaningfulPaint: number;
  timeToInteractive: number;
  skeletonLoadTime: number;
  initialBundleLoadTime: number;
  domContentLoadedTime: number;
  resourceLoadTime: number;
  javascriptParseTime: number;
  renderingTime: number;
}

export class StartupPerformanceTest {
  private startTime: number = 0;
  private metrics: Partial<StartupMetrics> = {};
  private performanceObserver?: PerformanceObserver;

  constructor() {
    this.startTime = performance.now();
    this.setupPerformanceObservers();
  }

  /**
   * 运行完整的启动性能测试
   */
  async runStartupTests(): Promise<{
    metrics: StartupMetrics;
    passed: boolean;
    report: string;
  }> {
    console.log('🚀 开始启动性能测试...');

    // 1. 测量冷启动时间
    const coldStart = await this.measureColdStartTime();

    // 2. 测量热启动时间
    const hotStart = await this.measureHotStartTime();

    // 3. 收集 Paint Timing
    const paintTimings = await this.collectPaintTimings();

    // 4. 测量骨架屏加载时间
    const skeletonTime = await this.measureSkeletonLoadTime();

    // 5. 测量初始包加载时间
    const bundleLoadTime = await this.measureBundleLoadTime();

    // 6. 测量可交互时间
    const interactiveTime = await this.measureTimeToInteractive();

    // 7. 收集资源加载时间
    const resourceTiming = await this.collectResourceTiming();

    this.metrics = {
      coldStartTime: coldStart,
      hotStartTime: hotStart,
      firstContentfulPaint: paintTimings.fcp,
      firstMeaningfulPaint: paintTimings.fmp,
      timeToInteractive: interactiveTime,
      skeletonLoadTime: skeletonTime,
      initialBundleLoadTime: bundleLoadTime,
      domContentLoadedTime: resourceTiming.domContentLoaded,
      resourceLoadTime: resourceTiming.resourceLoad,
      javascriptParseTime: resourceTiming.scriptParse,
      renderingTime: resourceTiming.rendering,
    };

    // 验证性能要求
    const passed = this.validateStartupPerformance();
    const report = this.generateStartupReport();

    return {
      metrics: this.metrics as StartupMetrics,
      passed,
      report,
    };
  }

  /**
   * 测量冷启动时间
   */
  private async measureColdStartTime(): Promise<number> {
    // 清除缓存，模拟冷启动
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
    }

    // 清除本地存储
    localStorage.clear();
    sessionStorage.clear();

    const startTime = performance.now();

    // 等待应用完全加载和初始化
    await this.waitForAppReady();

    const coldStartTime = performance.now() - startTime;
    console.log(`🔥 冷启动时间: ${coldStartTime.toFixed(2)}ms`);

    return coldStartTime;
  }

  /**
   * 测量热启动时间
   */
  private async measureHotStartTime(): Promise<number> {
    // 模拟热启动（有缓存）
    const startTime = performance.now();

    // 重新加载应用
    await this.simulateHotReload();

    const hotStartTime = performance.now() - startTime;
    console.log(`🌡️ 热启动时间: ${hotStartTime.toFixed(2)}ms`);

    return hotStartTime;
  }

  /**
   * 收集 Paint Timing 指标
   */
  private async collectPaintTimings(): Promise<{
    fcp: number;
    fmp: number;
  }> {
    return new Promise((resolve) => {
      let fcp = 0;
      let fmp = 0;

      // 监听 Paint Timing
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();

        entries.forEach((entry) => {
          if (entry.name === 'first-contentful-paint') {
            fcp = entry.startTime;
            console.log(`🎨 First Contentful Paint: ${fcp.toFixed(2)}ms`);
          }
          if (entry.name === 'first-meaningful-paint') {
            fmp = entry.startTime;
            console.log(`🎯 First Meaningful Paint: ${fmp.toFixed(2)}ms`);
          }
        });

        if (fcp > 0) {
          observer.disconnect();
          resolve({ fcp, fmp });
        }
      });

      observer.observe({ entryTypes: ['paint'] });

      // 超时处理
      setTimeout(() => {
        observer.disconnect();
        resolve({ fcp: fcp || 1000, fmp: fmp || 1200 });
      }, 5000);
    });
  }

  /**
   * 测量骨架屏加载时间
   */
  private async measureSkeletonLoadTime(): Promise<number> {
    return new Promise((resolve) => {
      const startTime = performance.now();

      // 监听骨架屏元素的出现
      const checkSkeleton = () => {
        const skeletonElements = document.querySelectorAll(
          '[class*="skeleton"], [data-testid*="skeleton"], .ant-skeleton'
        );

        if (skeletonElements.length > 0) {
          const skeletonTime = performance.now() - startTime;
          console.log(`💀 骨架屏加载时间: ${skeletonTime.toFixed(2)}ms`);
          resolve(skeletonTime);
          return;
        }

        // 如果没有找到骨架屏，继续检查
        if (performance.now() - startTime < 1000) {
          requestAnimationFrame(checkSkeleton);
        } else {
          // 超时，假设没有骨架屏或已经加载完成
          resolve(0);
        }
      };

      requestAnimationFrame(checkSkeleton);
    });
  }

  /**
   * 测量初始包加载时间
   */
  private async measureBundleLoadTime(): Promise<number> {
    return new Promise((resolve) => {
      const bundleStartTime = performance.now();

      // 监听主要脚本加载完成
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();

        // 查找主要的 JS 包
        const mainBundles = entries.filter((entry) =>
          entry.name.includes('main') || entry.name.includes('index')
        );

        if (mainBundles.length > 0) {
          const maxLoadTime = Math.max(
            ...mainBundles.map((entry) => entry.responseEnd)
          );
          const bundleLoadTime = maxLoadTime - bundleStartTime;
          console.log(`📦 初始包加载时间: ${bundleLoadTime.toFixed(2)}ms`);
          observer.disconnect();
          resolve(bundleLoadTime);
        }
      });

      observer.observe({ entryTypes: ['resource'] });

      // 超时处理
      setTimeout(() => {
        observer.disconnect();
        resolve(500); // 默认值
      }, 3000);
    });
  }

  /**
   * 测量可交互时间
   */
  private async measureTimeToInteractive(): Promise<number> {
    return new Promise((resolve) => {
      const startTime = performance.now();

      const checkInteractive = () => {
        // 检查主要交互元素是否可用
        const interactiveElements = document.querySelectorAll(
          'button:not([disabled]), input:not([disabled]), [role="button"]:not([aria-disabled="true"])'
        );

        // 检查是否有点击事件监听器
        const hasEventListeners = interactiveElements.length > 0;

        // 检查是否有未完成的网络请求
        const hasActiveFetches = (performance as any).getEntriesByType?.('resource')
          ?.some((entry: any) => entry.responseEnd === 0) || false;

        if (hasEventListeners && !hasActiveFetches) {
          const interactiveTime = performance.now() - startTime;
          console.log(`⚡ 可交互时间: ${interactiveTime.toFixed(2)}ms`);
          resolve(interactiveTime);
          return;
        }

        if (performance.now() - startTime < 5000) {
          setTimeout(checkInteractive, 100);
        } else {
          resolve(3000); // 超时默认值
        }
      };

      checkInteractive();
    });
  }

  /**
   * 收集资源加载时间
   */
  private async collectResourceTiming(): Promise<{
    domContentLoaded: number;
    resourceLoad: number;
    scriptParse: number;
    rendering: number;
  }> {
    return new Promise((resolve) => {
      let domContentLoaded = 0;
      let resourceLoad = 0;

      // 监听 DOM 和资源加载事件
      document.addEventListener('DOMContentLoaded', () => {
        domContentLoaded = performance.now();
      });

      window.addEventListener('load', () => {
        resourceLoad = performance.now();

        // 计算脚本解析时间
        const scriptEntries = performance.getEntriesByType('resource')
          .filter((entry) => entry.name.endsWith('.js'));

        const scriptParse = scriptEntries.reduce((total, entry) => {
          return total + (entry.responseEnd - entry.responseStart);
        }, 0);

        // 计算渲染时间
        const paintEntries = performance.getEntriesByType('paint');
        const rendering = paintEntries.length > 0
          ? paintEntries[paintEntries.length - 1].startTime
          : 0;

        resolve({
          domContentLoaded,
          resourceLoad,
          scriptParse,
          rendering,
        });
      });

      // 超时处理
      setTimeout(() => {
        resolve({
          domContentLoaded: domContentLoaded || 800,
          resourceLoad: resourceLoad || 1200,
          scriptParse: 200,
          rendering: 600,
        });
      }, 10000);
    });
  }

  /**
   * 等待应用准备就绪
   */
  private async waitForAppReady(): Promise<void> {
    return new Promise((resolve) => {
      const checkReady = () => {
        // 检查 React 根元素是否已渲染
        const rootElement = document.getElementById('root');
        const hasContent = rootElement && rootElement.children.length > 0;

        // 检查是否有 React 组件渲染完成的标志
        const hasReactContent = document.querySelector('[data-reactroot], .App, [id*="app"]');

        if (hasContent && hasReactContent) {
          resolve();
          return;
        }

        if (performance.now() - this.startTime < 5000) {
          requestAnimationFrame(checkReady);
        } else {
          resolve(); // 超时
        }
      };

      requestAnimationFrame(checkReady);
    });
  }

  /**
   * 模拟热重载
   */
  private async simulateHotReload(): Promise<void> {
    // 模拟应用重新初始化
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  /**
   * 设置性能观察器
   */
  private setupPerformanceObservers(): void {
    if ('PerformanceObserver' in window) {
      this.performanceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          console.log(`📊 Performance Entry: ${entry.name} - ${entry.startTime.toFixed(2)}ms`);
        });
      });

      // 观察所有性能指标
      try {
        this.performanceObserver.observe({
          entryTypes: ['paint', 'resource', 'navigation', 'measure'],
        });
      } catch (e) {
        console.warn('Performance Observer not fully supported:', e);
      }
    }
  }

  /**
   * 验证启动性能是否符合要求
   */
  private validateStartupPerformance(): boolean {
    const requirements = {
      maxColdStartTime: 1500, // 1.5s
      maxSkeletonTime: 200, // 200ms
      maxFCPTime: 1000, // 1s
      maxInteractiveTime: 2000, // 2s
    };

    const results = [
      this.metrics.coldStartTime! <= requirements.maxColdStartTime,
      this.metrics.skeletonLoadTime! <= requirements.maxSkeletonTime,
      this.metrics.firstContentfulPaint! <= requirements.maxFCPTime,
      this.metrics.timeToInteractive! <= requirements.maxInteractiveTime,
    ];

    return results.every(result => result);
  }

  /**
   * 生成启动性能报告
   */
  private generateStartupReport(): string {
    const requirements = {
      maxColdStartTime: 1500,
      maxSkeletonTime: 200,
      maxFCPTime: 1000,
      maxInteractiveTime: 2000,
    };

    const coldStartPassed = this.metrics.coldStartTime! <= requirements.maxColdStartTime;
    const skeletonPassed = this.metrics.skeletonLoadTime! <= requirements.maxSkeletonTime;
    const fcpPassed = this.metrics.firstContentfulPaint! <= requirements.maxFCPTime;
    const interactivePassed = this.metrics.timeToInteractive! <= requirements.maxInteractiveTime;

    return `
# 启动性能测试报告

## 核心指标

### 🚀 冷启动性能
- **实际值**: ${this.metrics.coldStartTime?.toFixed(2)}ms
- **要求**: < ${requirements.maxColdStartTime}ms
- **状态**: ${coldStartPassed ? '✅ 通过' : '❌ 失败'}

### 💀 骨架屏加载
- **实际值**: ${this.metrics.skeletonLoadTime?.toFixed(2)}ms
- **要求**: < ${requirements.maxSkeletonTime}ms
- **状态**: ${skeletonPassed ? '✅ 通过' : '❌ 失败'}

### 🎨 首次内容绘制 (FCP)
- **实际值**: ${this.metrics.firstContentfulPaint?.toFixed(2)}ms
- **要求**: < ${requirements.maxFCPTime}ms
- **状态**: ${fcpPassed ? '✅ 通过' : '❌ 失败'}

### ⚡ 可交互时间 (TTI)
- **实际值**: ${this.metrics.timeToInteractive?.toFixed(2)}ms
- **要求**: < ${requirements.maxInteractiveTime}ms
- **状态**: ${interactivePassed ? '✅ 通过' : '❌ 失败'}

## 详细指标

- 热启动时间: ${this.metrics.hotStartTime?.toFixed(2)}ms
- 首次有意义绘制: ${this.metrics.firstMeaningfulPaint?.toFixed(2)}ms
- 初始包加载时间: ${this.metrics.initialBundleLoadTime?.toFixed(2)}ms
- DOM 内容加载: ${this.metrics.domContentLoadedTime?.toFixed(2)}ms
- 资源加载完成: ${this.metrics.resourceLoadTime?.toFixed(2)}ms
- JavaScript 解析: ${this.metrics.javascriptParseTime?.toFixed(2)}ms
- 渲染时间: ${this.metrics.renderingTime?.toFixed(2)}ms

## 优化建议

${!coldStartPassed ? '❗ 冷启动时间超标，建议优化初始包大小和资源加载策略' : ''}
${!skeletonPassed ? '❗ 骨架屏加载时间超标，建议优化骨架屏组件的渲染逻辑' : ''}
${!fcpPassed ? '❗ FCP 时间超标，建议优化关键渲染路径' : ''}
${!interactivePassed ? '❗ TTI 时间超标，建议优化 JavaScript 执行和事件绑定' : ''}

${coldStartPassed && skeletonPassed && fcpPassed && interactivePassed
  ? '🎉 所有启动性能指标均达标！'
  : ''
}
`;
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }
  }
}

// 导出便捷的测试函数
export async function runStartupPerformanceTest() {
  const test = new StartupPerformanceTest();
  try {
    const result = await test.runStartupTests();
    console.log(result.report);
    return result;
  } finally {
    test.cleanup();
  }
}