/**
 * 性能测试套件入口文件
 * 导出所有性能测试相关的工具和组件
 */

// 主要测试类
export { PerformanceTestSuite } from './PerformanceTestSuite';
export { StartupPerformanceTest, runStartupPerformanceTest } from './StartupPerformanceTest';
export { TablePerformanceTest, runTablePerformanceTest } from './TablePerformanceTest';
export { DataProcessingPerformanceTest, runDataProcessingPerformanceTest } from './DataProcessingPerformanceTest';
export { BundleOptimizationTest, runBundleOptimizationTest } from './BundleOptimizationTest';
export { WebVitalsCollector, collectWebVitals } from './WebVitalsCollector';

// 测试运行器
export { PerformanceTestRunner, runComprehensivePerformanceTest } from './PerformanceTestRunner';

// React 组件
export { PerformanceTestPage } from './PerformanceTestPage';

// 类型定义
export type {
  PerformanceMetrics,
  PerformanceRequirements,
} from './PerformanceTestSuite';

export type {
  StartupMetrics,
} from './StartupPerformanceTest';

export type {
  TablePerformanceMetrics,
  TableTestData,
} from './TablePerformanceTest';

export type {
  DataProcessingMetrics,
  ChunkInfo,
  ImportSession,
} from './DataProcessingPerformanceTest';

export type {
  BundleMetrics,
  BundleAnalysis,
} from './BundleOptimizationTest';

export type {
  WebVitalsMetrics,
  PerformanceEntry,
} from './WebVitalsCollector';

export type {
  ComprehensivePerformanceReport,
} from './PerformanceTestRunner';

/**
 * 快速运行性能测试的便捷函数
 */
export async function quickPerformanceTest() {
  console.log('🚀 运行快速性能测试...');
  
  try {
    const result = await runComprehensivePerformanceTest();
    
    console.log('\n📊 快速测试结果:');
    console.log(`总体评分: ${result.summary.overallScore}/100`);
    console.log(`通过率: ${result.summary.passRate.toFixed(1)}%`);
    console.log(`执行时间: ${result.summary.executionTime.toFixed(2)}秒`);
    
    if (result.summary.overallScore >= 90) {
      console.log('🎉 性能表现优秀！');
    } else if (result.summary.overallScore >= 80) {
      console.log('👍 性能表现良好，建议进一步优化。');
    } else {
      console.log('⚠️ 性能需要重点优化。');
    }
    
    return result;
  } catch (error) {
    console.error('❌ 快速性能测试失败:', error);
    throw error;
  }
}

/**
 * 性能测试配置
 */
export const PerformanceTestConfig = {
  // 启动性能要求
  startup: {
    maxColdStartTime: 1500, // ms
    maxSkeletonTime: 200,   // ms
    maxFCPTime: 1000,       // ms
    maxInteractiveTime: 2000, // ms
  },
  
  // 表格性能要求
  table: {
    minScrollFPS: 60,
    maxRowsSupported: 50000,
    maxMemoryUsageAt50k: 300, // MB
    maxRenderTimeAt10k: 1000, // ms
  },
  
  // 数据处理要求
  dataProcessing: {
    maxImportTimeFor1GB: 300000, // ms (5分钟)
    minResumeSuccessRate: 90,    // %
    maxRollbackTime: 5000,       // ms
    minTransactionThroughput: 100, // ops/s
    minIntegrityScore: 95,       // %
  },
  
  // 包体积要求
  bundle: {
    maxTotalSize: 2048,      // KB
    maxMainChunkSize: 1024,  // KB
    minCompressionRatio: 0.3, // 30%
    minTreeshakingEfficiency: 80, // %
    maxUnusedCodeSize: 100,  // KB
    minCacheEfficiency: 80,  // %
  },
  
  // Web Vitals 要求
  webVitals: {
    maxCLS: 0.1,
    maxFID: 100,     // ms
    maxLCP: 2500,    // ms
    maxFCP: 1800,    // ms
    maxTTFB: 600,    // ms
    minPerformanceScore: 90, // 0-100
  },
} as const;

/**
 * 检查单个性能指标是否达标
 */
export function checkPerformanceRequirement(
  category: keyof typeof PerformanceTestConfig,
  metric: string,
  value: number
): boolean {
  const config = PerformanceTestConfig[category] as any;
  
  if (!config || !(metric in config)) {
    console.warn(`未知的性能指标: ${category}.${metric}`);
    return false;
  }
  
  const requirement = config[metric];
  
  // 根据指标名称判断是最大值还是最小值要求
  if (metric.startsWith('max')) {
    return value <= requirement;
  } else if (metric.startsWith('min')) {
    return value >= requirement;
  } else {
    // 默认作为最大值要求处理
    return value <= requirement;
  }
}

/**
 * 获取性能要求的描述文本
 */
export function getPerformanceRequirementText(
  category: keyof typeof PerformanceTestConfig,
  metric: string
): string {
  const config = PerformanceTestConfig[category] as any;
  
  if (!config || !(metric in config)) {
    return '未知要求';
  }
  
  const requirement = config[metric];
  
  if (metric.startsWith('max')) {
    if (metric.includes('Time')) {
      return `≤ ${requirement}ms`;
    } else if (metric.includes('Size')) {
      return `≤ ${requirement}KB`;
    } else if (metric.includes('Rate') || metric.includes('Ratio')) {
      return `≤ ${(requirement * 100).toFixed(1)}%`;
    } else {
      return `≤ ${requirement}`;
    }
  } else if (metric.startsWith('min')) {
    if (metric.includes('Rate') || metric.includes('Ratio') || metric.includes('Score')) {
      return `≥ ${typeof requirement === 'number' && requirement < 1 ? (requirement * 100).toFixed(1) + '%' : requirement}`;
    } else if (metric.includes('FPS')) {
      return `≥ ${requirement}fps`;
    } else {
      return `≥ ${requirement}`;
    }
  } else {
    return `${requirement}`;
  }
}

/**
 * 性能测试工具类
 */
export class PerformanceTestUtils {
  /**
   * 格式化时间
   */
  static formatTime(ms: number): string {
    if (ms < 1000) {
      return `${ms.toFixed(2)}ms`;
    } else if (ms < 60000) {
      return `${(ms / 1000).toFixed(2)}s`;
    } else {
      const minutes = Math.floor(ms / 60000);
      const seconds = ((ms % 60000) / 1000).toFixed(0);
      return `${minutes}m ${seconds}s`;
    }
  }
  
  /**
   * 格式化文件大小
   */
  static formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes}B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)}KB`;
    } else if (bytes < 1024 * 1024 * 1024) {
      return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
    } else {
      return `${(bytes / 1024 / 1024 / 1024).toFixed(1)}GB`;
    }
  }
  
  /**
   * 格式化百分比
   */
  static formatPercentage(value: number, precision = 1): string {
    return `${value.toFixed(precision)}%`;
  }
  
  /**
   * 获取性能等级
   */
  static getPerformanceGrade(score: number): {
    grade: string;
    color: string;
    description: string;
  } {
    if (score >= 90) {
      return {
        grade: 'A',
        color: '#52c41a',
        description: '优秀',
      };
    } else if (score >= 80) {
      return {
        grade: 'B',
        color: '#1890ff',
        description: '良好',
      };
    } else if (score >= 70) {
      return {
        grade: 'C',
        color: '#fa8c16',
        description: '一般',
      };
    } else if (score >= 60) {
      return {
        grade: 'D',
        color: '#faad14',
        description: '较差',
      };
    } else {
      return {
        grade: 'F',
        color: '#ff4d4f',
        description: '不及格',
      };
    }
  }
  
  /**
   * 计算性能改善程度
   */
  static calculateImprovement(oldValue: number, newValue: number, isLowerBetter = true): {
    percentage: number;
    isImprovement: boolean;
    description: string;
  } {
    const percentage = ((oldValue - newValue) / oldValue) * 100;
    const isImprovement = isLowerBetter ? newValue < oldValue : newValue > oldValue;
    
    let description: string;
    if (Math.abs(percentage) < 1) {
      description = '基本无变化';
    } else if (isImprovement) {
      description = `提升 ${Math.abs(percentage).toFixed(1)}%`;
    } else {
      description = `下降 ${Math.abs(percentage).toFixed(1)}%`;
    }
    
    return {
      percentage: isLowerBetter ? percentage : -percentage,
      isImprovement,
      description,
    };
  }
}