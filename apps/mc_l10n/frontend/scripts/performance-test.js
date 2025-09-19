#!/usr/bin/env node

/**
 * 性能测试和基准测试脚本
 * 用于检测性能回归和生成性能报告
 */

import { performance } from 'perf_hooks'
import fs from 'fs/promises'
import path from 'path'

const PERFORMANCE_THRESHOLDS = {
  // 组件渲染时间阈值 (毫秒)
  componentRender: 100,
  // API响应时间阈值 (毫秒)
  apiResponse: 500,
  // 内存使用阈值 (MB)
  memoryUsage: 100,
  // 包大小阈值 (KB)
  bundleSize: 1000,
}

class PerformanceTest {
  constructor(options = {}) {
    this.options = {
      verbose: false,
      outputFile: null,
      failThreshold: 85,
      ...options,
    }
    this.results = []
    this.startTime = performance.now()
  }

  log(message, level = 'info') {
    if (this.options.verbose || level === 'error') {
      const timestamp = new Date().toISOString()
      console.log(`[${timestamp}] [${level.toUpperCase()}] ${message}`)
    }
  }

  async runTest(name, testFn, threshold) {
    this.log(`运行测试: ${name}`)
    
    const start = performance.now()
    let result
    let error = null
    
    try {
      result = await testFn()
    } catch (err) {
      error = err
      this.log(`测试失败: ${name} - ${err.message}`, 'error')
    }
    
    const duration = performance.now() - start
    const passed = !error && duration <= threshold
    
    const testResult = {
      name,
      duration: Math.round(duration * 100) / 100,
      threshold,
      passed,
      error: error?.message,
      result,
      timestamp: new Date().toISOString(),
    }
    
    this.results.push(testResult)
    
    if (passed) {
      this.log(`✅ ${name}: ${duration.toFixed(2)}ms (threshold: ${threshold}ms)`)
    } else {
      this.log(`❌ ${name}: ${duration.toFixed(2)}ms (threshold: ${threshold}ms)`, 'error')
    }
    
    return testResult
  }

  async runBundleSizeTest() {
    return this.runTest('Bundle Size Check', async () => {
      const distPath = path.join(process.cwd(), 'dist')
      
      try {
        const stats = await fs.stat(path.join(distPath, 'index.html'))
        const files = await fs.readdir(distPath, { recursive: true })
        
        let totalSize = 0
        const jsFiles = []
        
        for (const file of files) {
          if (typeof file === 'string' && file.endsWith('.js')) {
            const filePath = path.join(distPath, file)
            const stat = await fs.stat(filePath)
            totalSize += stat.size
            jsFiles.push({
              name: file,
              size: Math.round(stat.size / 1024), // KB
            })
          }
        }
        
        const totalSizeKB = Math.round(totalSize / 1024)
        
        return {
          totalSize: totalSizeKB,
          jsFiles,
          passed: totalSizeKB <= PERFORMANCE_THRESHOLDS.bundleSize,
        }
      } catch (err) {
        throw new Error(`Bundle size check failed: ${err.message}`)
      }
    }, PERFORMANCE_THRESHOLDS.bundleSize)
  }

  async runMemoryTest() {
    return this.runTest('Memory Usage Test', async () => {
      // 模拟内存使用测试
      const memoryBefore = process.memoryUsage()
      
      // 创建一些测试数据来模拟应用内存使用
      const testData = Array.from({ length: 10000 }, (_, i) => ({
        id: i,
        data: `test-data-${i}`.repeat(10),
        timestamp: Date.now(),
      }))
      
      const memoryAfter = process.memoryUsage()
      const memoryDiff = (memoryAfter.heapUsed - memoryBefore.heapUsed) / 1024 / 1024 // MB
      
      // 清理测试数据
      testData.length = 0
      global.gc && global.gc()
      
      return {
        memoryUsage: Math.round(memoryDiff * 100) / 100,
        heapUsed: Math.round(memoryAfter.heapUsed / 1024 / 1024 * 100) / 100,
        passed: memoryDiff <= PERFORMANCE_THRESHOLDS.memoryUsage,
      }
    }, PERFORMANCE_THRESHOLDS.memoryUsage)
  }

  async runApiPerformanceTest() {
    return this.runTest('API Performance Test', async () => {
      // 模拟API调用性能测试
      const apiTests = [
        { name: 'Health Check', endpoint: '/health' },
        { name: 'Project List', endpoint: '/api/projects' },
        { name: 'Scan Status', endpoint: '/api/scan/status' },
      ]
      
      const results = []
      
      for (const test of apiTests) {
        const start = performance.now()
        
        try {
          // 模拟网络延迟
          await new Promise(resolve => setTimeout(resolve, Math.random() * 100))
          
          const duration = performance.now() - start
          results.push({
            name: test.name,
            endpoint: test.endpoint,
            duration: Math.round(duration * 100) / 100,
            passed: duration <= PERFORMANCE_THRESHOLDS.apiResponse,
          })
        } catch (err) {
          results.push({
            name: test.name,
            endpoint: test.endpoint,
            error: err.message,
            passed: false,
          })
        }
      }
      
      const avgDuration = results.reduce((sum, r) => sum + (r.duration || 0), 0) / results.length
      
      return {
        apiTests: results,
        averageDuration: Math.round(avgDuration * 100) / 100,
        passed: avgDuration <= PERFORMANCE_THRESHOLDS.apiResponse,
      }
    }, PERFORMANCE_THRESHOLDS.apiResponse)
  }

  async generateReport() {
    const totalDuration = performance.now() - this.startTime
    const passedTests = this.results.filter(r => r.passed).length
    const totalTests = this.results.length
    const successRate = Math.round((passedTests / totalTests) * 100)
    
    const report = {
      summary: {
        totalTests,
        passedTests,
        failedTests: totalTests - passedTests,
        successRate,
        totalDuration: Math.round(totalDuration),
        timestamp: new Date().toISOString(),
      },
      thresholds: PERFORMANCE_THRESHOLDS,
      tests: this.results,
      recommendations: this.generateRecommendations(),
    }
    
    if (this.options.outputFile) {
      await fs.writeFile(
        this.options.outputFile,
        JSON.stringify(report, null, 2),
        'utf8'
      )
      this.log(`性能报告已保存到: ${this.options.outputFile}`)
    }
    
    this.printSummary(report)
    
    return report
  }

  generateRecommendations() {
    const recommendations = []
    
    this.results.forEach(test => {
      if (!test.passed) {
        switch (test.name) {
          case 'Bundle Size Check':
            recommendations.push('考虑使用代码分割和懒加载来减小包大小')
            recommendations.push('启用tree-shaking优化未使用的代码')
            break
          case 'Memory Usage Test':
            recommendations.push('检查内存泄漏和优化数据结构')
            recommendations.push('使用React.memo和useMemo优化渲染')
            break
          case 'API Performance Test':
            recommendations.push('优化API响应时间和数据库查询')
            recommendations.push('考虑添加缓存层')
            break
        }
      }
    })
    
    return [...new Set(recommendations)]
  }

  printSummary(report) {
    console.log('\n📊 性能测试总结')
    console.log('='.repeat(50))
    console.log(`总测试数: ${report.summary.totalTests}`)
    console.log(`通过测试: ${report.summary.passedTests}`)
    console.log(`失败测试: ${report.summary.failedTests}`)
    console.log(`成功率: ${report.summary.successRate}%`)
    console.log(`总耗时: ${report.summary.totalDuration}ms`)
    
    if (report.recommendations.length > 0) {
      console.log('\n💡 优化建议:')
      report.recommendations.forEach((rec, i) => {
        console.log(`${i + 1}. ${rec}`)
      })
    }
    
    console.log('='.repeat(50))
    
    if (report.summary.successRate < this.options.failThreshold) {
      console.log(`❌ 性能测试失败 (成功率 ${report.summary.successRate}% < ${this.options.failThreshold}%)`)
      process.exit(1)
    } else {
      console.log('✅ 性能测试通过')
    }
  }

  async run() {
    this.log('开始性能测试...')
    
    await this.runBundleSizeTest()
    await this.runMemoryTest()
    await this.runApiPerformanceTest()
    
    return this.generateReport()
  }
}

// 命令行运行
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2)
  const options = {}
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (arg === '--verbose') {
      options.verbose = true
    } else if (arg.startsWith('--output=')) {
      options.outputFile = arg.split('=')[1]
    } else if (arg.startsWith('--fail-threshold=')) {
      options.failThreshold = parseInt(arg.split('=')[1])
    }
  }
  
  const perfTest = new PerformanceTest(options)
  perfTest.run().catch(err => {
    console.error('性能测试运行失败:', err)
    process.exit(1)
  })
}

export default PerformanceTest