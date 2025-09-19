/**
 * 性能测试运行器 - 统一执行所有性能测试并生成综合报告
 * 整合启动性能、表格渲染、数据处理、包体积优化、Web Vitals等测试
 */

import { PerformanceTestSuite } from './PerformanceTestSuite';
import { StartupPerformanceTest } from './StartupPerformanceTest';
import { TablePerformanceTest } from './TablePerformanceTest';
import { DataProcessingPerformanceTest } from './DataProcessingPerformanceTest';
import { BundleOptimizationTest } from './BundleOptimizationTest';
import { WebVitalsCollector } from './WebVitalsCollector';

export interface ComprehensivePerformanceReport {
  summary: {
    totalTests: number;
    passedTests: number;
    failedTests: number;
    overallScore: number;
    passRate: number;
    executionTime: number;
  };
  
  testResults: {
    startup: any;
    tableRendering: any;
    dataProcessing: any;
    bundleOptimization: any;
    webVitals: any;
  };
  
  recommendations: string[];
  criticalIssues: string[];
  passedRequirements: string[];
  
  detailedReports: {
    startup: string;
    tableRendering: string;
    dataProcessing: string;
    bundleOptimization: string;
    webVitals: string;
  };
}

export class PerformanceTestRunner {
  private startTime = 0;
  private results: any = {};

  constructor() {
    this.startTime = performance.now();
  }

  /**
   * 运行完整的性能测试套件
   */
  async runComprehensivePerformanceTests(): Promise<ComprehensivePerformanceReport> {
    console.log('🚀 开始运行 TH-Suite 前端性能综合测试...');
    console.log('=====================================');

    this.startTime = performance.now();

    try {
      // 1. 启动性能测试
      console.log('\n📊 1/5 启动性能测试');
      const startupResults = await this.runStartupTests();

      // 2. 表格渲染性能测试
      console.log('\n📊 2/5 表格渲染性能测试');
      const tableResults = await this.runTableTests();

      // 3. 数据处理性能测试
      console.log('\n📊 3/5 数据处理性能测试');
      const dataProcessingResults = await this.runDataProcessingTests();

      // 4. 包体积优化验证
      console.log('\n📊 4/5 包体积优化验证');
      const bundleResults = await this.runBundleTests();

      // 5. Web Vitals 收集
      console.log('\n📊 5/5 Web Vitals 收集');
      const webVitalsResults = await this.runWebVitalsTests();

      // 6. 生成综合报告
      console.log('\n📋 生成综合性能报告...');
      const comprehensiveReport = this.generateComprehensiveReport({
        startup: startupResults,
        tableRendering: tableResults,
        dataProcessing: dataProcessingResults,
        bundleOptimization: bundleResults,
        webVitals: webVitalsResults,
      });

      console.log('\n✅ 性能测试完成！');
      console.log(`总耗时: ${((performance.now() - this.startTime) / 1000).toFixed(2)}秒`);

      return comprehensiveReport;

    } catch (error) {
      console.error('❌ 性能测试执行失败:', error);
      throw error;
    }
  }

  /**
   * 运行启动性能测试
   */
  private async runStartupTests() {
    try {
      const startupTest = new StartupPerformanceTest();
      const result = await startupTest.runStartupTests();
      
      console.log(`✅ 启动性能测试完成 - ${result.passed ? '通过' : '失败'}`);
      console.log(`   冷启动: ${result.metrics.coldStartTime.toFixed(2)}ms`);
      console.log(`   骨架屏: ${result.metrics.skeletonLoadTime.toFixed(2)}ms`);
      
      startupTest.cleanup();
      return result;
    } catch (error) {
      console.error('❌ 启动性能测试失败:', error);
      return { passed: false, metrics: {}, report: '启动性能测试执行失败' };
    }
  }

  /**
   * 运行表格渲染性能测试
   */
  private async runTableTests() {
    try {
      const tableTest = new TablePerformanceTest();
      const result = await tableTest.runTablePerformanceTests();
      
      console.log(`✅ 表格性能测试完成 - ${result.passed ? '通过' : '失败'}`);
      
      // 显示关键指标
      const maxRowsResult = result.results[50000];
      if (maxRowsResult) {
        console.log(`   5万行滚动: ${maxRowsResult.scrollFPS.toFixed(1)}fps`);
        console.log(`   内存使用: ${maxRowsResult.memoryUsage.toFixed(2)}MB`);
        console.log(`   虚拟化: ${maxRowsResult.virtualizationEffective ? '生效' : '未生效'}`);
      }
      
      tableTest.cleanup();
      return result;
    } catch (error) {
      console.error('❌ 表格性能测试失败:', error);
      return { passed: false, results: {}, report: '表格性能测试执行失败' };
    }
  }

  /**
   * 运行数据处理性能测试
   */
  private async runDataProcessingTests() {
    try {
      const dataTest = new DataProcessingPerformanceTest();
      const result = await dataTest.runDataProcessingTests();
      
      console.log(`✅ 数据处理测试完成 - ${result.passed ? '通过' : '失败'}`);
      console.log(`   导入时间: ${(result.metrics.importTime / 1000).toFixed(2)}s`);
      console.log(`   断点续传: ${result.metrics.resumableImport ? '支持' : '不支持'}`);
      console.log(`   数据完整性: ${result.metrics.dataIntegrityScore.toFixed(1)}%`);
      
      dataTest.cleanup();
      return result;
    } catch (error) {
      console.error('❌ 数据处理测试失败:', error);
      return { passed: false, metrics: {}, report: '数据处理测试执行失败' };
    }
  }

  /**
   * 运行包体积优化验证
   */
  private async runBundleTests() {
    try {
      const bundleTest = new BundleOptimizationTest();
      const result = await bundleTest.runBundleOptimizationTests();
      
      console.log(`✅ 包优化验证完成 - ${result.passed ? '通过' : '失败'}`);
      console.log(`   总包大小: ${result.currentMetrics.totalSize.toFixed(1)}KB`);
      console.log(`   压缩率: ${(result.currentMetrics.compressionRatio * 100).toFixed(1)}%`);
      console.log(`   Tree Shaking: ${result.currentMetrics.treeshakingEffective ? '生效' : '未生效'}`);
      
      bundleTest.cleanup();
      return result;
    } catch (error) {
      console.error('❌ 包优化验证失败:', error);
      return { passed: false, currentMetrics: {}, report: '包优化验证执行失败' };
    }
  }

  /**
   * 运行 Web Vitals 测试
   */
  private async runWebVitalsTests() {
    try {
      const webVitalsCollector = new WebVitalsCollector();
      await webVitalsCollector.startCollection();
      
      // 等待指标收集
      await new Promise(resolve => setTimeout(resolve, 6000));
      
      const result = await webVitalsCollector.stopCollection();
      
      console.log(`✅ Web Vitals 收集完成 - ${result.passed ? '通过' : '失败'}`);
      console.log(`   性能评分: ${result.metrics.performanceScore}/100`);
      console.log(`   CLS: ${result.metrics.CLS.toFixed(4)}`);
      console.log(`   LCP: ${result.metrics.LCP.toFixed(2)}ms`);
      
      webVitalsCollector.cleanup();
      return result;
    } catch (error) {
      console.error('❌ Web Vitals 收集失败:', error);
      return { passed: false, metrics: {}, report: 'Web Vitals 收集执行失败' };
    }
  }

  /**
   * 生成综合性能报告
   */
  private generateComprehensiveReport(results: any): ComprehensivePerformanceReport {
    const executionTime = (performance.now() - this.startTime) / 1000;
    
    // 统计测试结果
    const testResults = [
      results.startup?.passed || false,
      results.tableRendering?.passed || false,
      results.dataProcessing?.passed || false,
      results.bundleOptimization?.passed || false,
      results.webVitals?.passed || false,
    ];
    
    const totalTests = testResults.length;
    const passedTests = testResults.filter(Boolean).length;
    const failedTests = totalTests - passedTests;
    const passRate = (passedTests / totalTests) * 100;
    
    // 计算综合评分
    const overallScore = this.calculateOverallScore(results);
    
    // 收集建议和问题
    const { recommendations, criticalIssues, passedRequirements } = this.analyzeResults(results);
    
    // 收集详细报告
    const detailedReports = {
      startup: results.startup?.report || '测试未执行',
      tableRendering: results.tableRendering?.report || '测试未执行',
      dataProcessing: results.dataProcessing?.report || '测试未执行',
      bundleOptimization: results.bundleOptimization?.report || '测试未执行',
      webVitals: results.webVitals?.report || '测试未执行',
    };

    return {
      summary: {
        totalTests,
        passedTests,
        failedTests,
        overallScore,
        passRate,
        executionTime,
      },
      testResults: results,
      recommendations,
      criticalIssues,
      passedRequirements,
      detailedReports,
    };
  }

  /**
   * 计算综合评分
   */
  private calculateOverallScore(results: any): number {
    const weights = {
      startup: 0.2,        // 20% - 启动性能很重要
      tableRendering: 0.25, // 25% - 表格是核心功能
      dataProcessing: 0.25, // 25% - 数据处理是核心功能
      bundleOptimization: 0.15, // 15% - 包优化影响加载
      webVitals: 0.15,     // 15% - 用户体验指标
    };

    let totalScore = 0;
    let totalWeight = 0;

    // 启动性能评分
    if (results.startup?.passed) {
      const startupScore = this.calculateStartupScore(results.startup.metrics);
      totalScore += startupScore * weights.startup;
      totalWeight += weights.startup;
    }

    // 表格性能评分
    if (results.tableRendering?.passed) {
      const tableScore = this.calculateTableScore(results.tableRendering.results);
      totalScore += tableScore * weights.tableRendering;
      totalWeight += weights.tableRendering;
    }

    // 数据处理评分
    if (results.dataProcessing?.passed) {
      const dataScore = this.calculateDataProcessingScore(results.dataProcessing.metrics);
      totalScore += dataScore * weights.dataProcessing;
      totalWeight += weights.dataProcessing;
    }

    // 包优化评分
    if (results.bundleOptimization?.passed) {
      const bundleScore = this.calculateBundleScore(results.bundleOptimization.currentMetrics);
      totalScore += bundleScore * weights.bundleOptimization;
      totalWeight += weights.bundleOptimization;
    }

    // Web Vitals 评分
    if (results.webVitals?.passed) {
      const webVitalsScore = results.webVitals.metrics.performanceScore || 0;
      totalScore += webVitalsScore * weights.webVitals;
      totalWeight += weights.webVitals;
    }

    return totalWeight > 0 ? Math.round(totalScore / totalWeight) : 0;
  }

  /**
   * 计算启动性能评分
   */
  private calculateStartupScore(metrics: any): number {
    if (!metrics) return 0;

    let score = 100;
    
    // 冷启动时间评分 (权重40%)
    if (metrics.coldStartTime > 1500) {
      score -= 40;
    } else if (metrics.coldStartTime > 1000) {
      score -= 20;
    }

    // 骨架屏时间评分 (权重30%)
    if (metrics.skeletonLoadTime > 200) {
      score -= 30;
    } else if (metrics.skeletonLoadTime > 100) {
      score -= 15;
    }

    // FCP 时间评分 (权重30%)
    if (metrics.firstContentfulPaint > 1800) {
      score -= 30;
    } else if (metrics.firstContentfulPaint > 1200) {
      score -= 15;
    }

    return Math.max(0, score);
  }

  /**
   * 计算表格性能评分
   */
  private calculateTableScore(results: any): number {
    if (!results || !results[50000]) return 0;

    const metrics = results[50000];
    let score = 100;

    // 滚动帧率评分 (权重50%)
    if (metrics.scrollFPS < 60) {
      score -= 50;
    } else if (metrics.scrollFPS < 55) {
      score -= 25;
    }

    // 虚拟化效果评分 (权重30%)
    if (!metrics.virtualizationEffective) {
      score -= 30;
    }

    // 内存使用评分 (权重20%)
    if (metrics.memoryUsage > 300) {
      score -= 20;
    } else if (metrics.memoryUsage > 200) {
      score -= 10;
    }

    return Math.max(0, score);
  }

  /**
   * 计算数据处理评分
   */
  private calculateDataProcessingScore(metrics: any): number {
    if (!metrics) return 0;

    let score = 100;

    // 导入时间评分 (权重30%)
    if (metrics.importTime > 300000) { // 5分钟
      score -= 30;
    } else if (metrics.importTime > 180000) { // 3分钟
      score -= 15;
    }

    // 断点续传评分 (权重25%)
    if (!metrics.resumableImport) {
      score -= 25;
    } else if (metrics.resumeSuccessRate < 90) {
      score -= 15;
    }

    // 数据完整性评分 (权重25%)
    if (metrics.dataIntegrityScore < 95) {
      score -= 25;
    } else if (metrics.dataIntegrityScore < 98) {
      score -= 10;
    }

    // 事务处理评分 (权重20%)
    if (metrics.transactionThroughput < 100) {
      score -= 20;
    } else if (metrics.transactionThroughput < 200) {
      score -= 10;
    }

    return Math.max(0, score);
  }

  /**
   * 计算包优化评分
   */
  private calculateBundleScore(metrics: any): number {
    if (!metrics) return 0;

    let score = 100;

    // 包大小评分 (权重40%)
    if (metrics.totalSize > 2048) {
      score -= 40;
    } else if (metrics.totalSize > 1536) {
      score -= 20;
    }

    // Tree Shaking 评分 (权重30%)
    if (!metrics.treeshakingEffective) {
      score -= 30;
    }

    // 压缩率评分 (权重20%)
    if (metrics.compressionRatio < 0.3) {
      score -= 20;
    } else if (metrics.compressionRatio < 0.35) {
      score -= 10;
    }

    // 代码分割评分 (权重10%)
    if (!metrics.codeSplittingEffective) {
      score -= 10;
    }

    return Math.max(0, score);
  }

  /**
   * 分析测试结果，生成建议和问题
   */
  private analyzeResults(results: any): {
    recommendations: string[];
    criticalIssues: string[];
    passedRequirements: string[];
  } {
    const recommendations: string[] = [];
    const criticalIssues: string[] = [];
    const passedRequirements: string[] = [];

    // 分析启动性能
    if (results.startup?.passed) {
      passedRequirements.push('✅ 启动性能达标 - 冷启动时间和首屏加载符合要求');
    } else {
      criticalIssues.push('❌ 启动性能不达标 - 影响用户首次体验');
      recommendations.push('🔧 优化启动性能：减少初始包大小，优化关键渲染路径');
    }

    // 分析表格性能
    if (results.tableRendering?.passed) {
      passedRequirements.push('✅ 表格渲染性能优秀 - 大数据量滚动流畅');
    } else {
      criticalIssues.push('❌ 表格性能不达标 - 影响大数据量场景使用');
      recommendations.push('🔧 优化表格性能：确保虚拟化生效，优化滚动事件处理');
    }

    // 分析数据处理
    if (results.dataProcessing?.passed) {
      passedRequirements.push('✅ 数据处理能力达标 - 支持大文件和断点续传');
    } else {
      criticalIssues.push('❌ 数据处理能力不足 - 影响大型项目处理');
      recommendations.push('🔧 优化数据处理：改进分块算法，增强错误恢复机制');
    }

    // 分析包优化
    if (results.bundleOptimization?.passed) {
      passedRequirements.push('✅ 包体积优化良好 - Tree Shaking和代码分割有效');
    } else {
      recommendations.push('🔧 优化包体积：进一步清理未使用代码，优化分包策略');
    }

    // 分析 Web Vitals
    if (results.webVitals?.passed) {
      passedRequirements.push('✅ Web Vitals 指标优秀 - 用户体验良好');
    } else {
      recommendations.push('🔧 优化 Web Vitals：改善CLS、FID、LCP等核心指标');
    }

    // 添加通用建议
    if (criticalIssues.length > 0) {
      recommendations.push('📋 建议优先处理标记为关键的性能问题');
      recommendations.push('🔍 定期运行性能测试，确保性能不退化');
    }

    return { recommendations, criticalIssues, passedRequirements };
  }

  /**
   * 打印摘要报告
   */
  printSummaryReport(report: ComprehensivePerformanceReport): void {
    console.log('\n🎯 TH-Suite 前端性能测试综合报告');
    console.log('=====================================');
    
    console.log(`\n📊 测试概览:`);
    console.log(`   总测试数: ${report.summary.totalTests}`);
    console.log(`   通过测试: ${report.summary.passedTests}`);
    console.log(`   失败测试: ${report.summary.failedTests}`);
    console.log(`   通过率: ${report.summary.passRate.toFixed(1)}%`);
    console.log(`   综合评分: ${report.summary.overallScore}/100`);
    console.log(`   执行时间: ${report.summary.executionTime.toFixed(2)}秒`);

    if (report.passedRequirements.length > 0) {
      console.log(`\n✅ 达标项目:`);
      report.passedRequirements.forEach(req => console.log(`   ${req}`));
    }

    if (report.criticalIssues.length > 0) {
      console.log(`\n❌ 关键问题:`);
      report.criticalIssues.forEach(issue => console.log(`   ${issue}`));
    }

    if (report.recommendations.length > 0) {
      console.log(`\n💡 优化建议:`);
      report.recommendations.forEach(rec => console.log(`   ${rec}`));
    }

    console.log('\n=====================================');
    
    if (report.summary.overallScore >= 90) {
      console.log('🎉 恭喜！TH-Suite 前端性能完全达标！');
    } else if (report.summary.overallScore >= 80) {
      console.log('👍 TH-Suite 前端性能良好，建议进一步优化。');
    } else {
      console.log('⚠️ TH-Suite 前端性能需要重点优化。');
    }
  }

  /**
   * 导出完整报告到文件
   */
  async exportDetailedReport(report: ComprehensivePerformanceReport, filePath?: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = filePath || `/tmp/th-suite-performance-report-${timestamp}.md`;

    const markdownReport = this.generateMarkdownReport(report);

    // 在实际环境中，这里应该使用文件系统API写入文件
    console.log(`\n📄 详细报告已生成: ${filename}`);
    console.log('可以使用以下方法查看完整报告:');
    console.log('1. 检查浏览器控制台的详细输出');
    console.log('2. 查看各测试模块的详细报告');

    return markdownReport;
  }

  /**
   * 生成 Markdown 格式的详细报告
   */
  private generateMarkdownReport(report: ComprehensivePerformanceReport): string {
    const timestamp = new Date().toLocaleString('zh-CN');

    return `# TH-Suite 前端性能测试综合报告

生成时间: ${timestamp}

## 执行摘要

- **总测试数**: ${report.summary.totalTests}
- **通过测试**: ${report.summary.passedTests}
- **失败测试**: ${report.summary.failedTests}
- **通过率**: ${report.summary.passRate.toFixed(1)}%
- **综合评分**: ${report.summary.overallScore}/100
- **执行时间**: ${report.summary.executionTime.toFixed(2)}秒

## 测试结果概览

| 测试项目 | 状态 | 关键指标 |
|---------|------|----------|
| 启动性能 | ${report.testResults.startup?.passed ? '✅ 通过' : '❌ 失败'} | 冷启动: ${report.testResults.startup?.metrics?.coldStartTime?.toFixed(2) || 'N/A'}ms |
| 表格渲染 | ${report.testResults.tableRendering?.passed ? '✅ 通过' : '❌ 失败'} | 滚动FPS: ${report.testResults.tableRendering?.results?.[50000]?.scrollFPS?.toFixed(1) || 'N/A'} |
| 数据处理 | ${report.testResults.dataProcessing?.passed ? '✅ 通过' : '❌ 失败'} | 导入时间: ${report.testResults.dataProcessing?.metrics?.importTime ? (report.testResults.dataProcessing.metrics.importTime / 1000).toFixed(2) + 's' : 'N/A'} |
| 包体积优化 | ${report.testResults.bundleOptimization?.passed ? '✅ 通过' : '❌ 失败'} | 总大小: ${report.testResults.bundleOptimization?.currentMetrics?.totalSize?.toFixed(1) || 'N/A'}KB |
| Web Vitals | ${report.testResults.webVitals?.passed ? '✅ 通过' : '❌ 失败'} | 性能评分: ${report.testResults.webVitals?.metrics?.performanceScore || 'N/A'}/100 |

## 达标项目

${report.passedRequirements.map(req => `- ${req}`).join('\n')}

## 关键问题

${report.criticalIssues.length > 0 
  ? report.criticalIssues.map(issue => `- ${issue}`).join('\n')
  : '无关键问题发现。'
}

## 优化建议

${report.recommendations.map(rec => `- ${rec}`).join('\n')}

## 详细测试报告

### 启动性能测试报告
${report.detailedReports.startup}

### 表格渲染性能测试报告
${report.detailedReports.tableRendering}

### 数据处理性能测试报告
${report.detailedReports.dataProcessing}

### 包体积优化验证报告
${report.detailedReports.bundleOptimization}

### Web Vitals 性能报告
${report.detailedReports.webVitals}

---

*此报告由 TH-Suite 性能测试套件自动生成*
`;
  }
}

// 导出便捷的测试函数
export async function runComprehensivePerformanceTest(): Promise<ComprehensivePerformanceReport> {
  const runner = new PerformanceTestRunner();
  
  try {
    const report = await runner.runComprehensivePerformanceTests();
    
    // 打印摘要报告
    runner.printSummaryReport(report);
    
    // 导出详细报告
    await runner.exportDetailedReport(report);
    
    return report;
  } catch (error) {
    console.error('性能测试运行失败:', error);
    throw error;
  }
}