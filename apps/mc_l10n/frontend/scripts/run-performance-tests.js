#!/usr/bin/env node

/**
 * 性能测试命令行脚本
 * 用于在CI/CD环境中运行性能测试
 * 
 * 使用方法:
 * npm run test:performance
 * 或
 * node scripts/run-performance-tests.js
 */

import { runComprehensivePerformanceTest } from '../src/testing/performance/index.js';
import fs from 'fs/promises';
import path from 'path';

// 命令行参数解析
const args = process.argv.slice(2);
const isVerbose = args.includes('--verbose') || args.includes('-v');
const outputFile = args.find(arg => arg.startsWith('--output='))?.split('=')[1];
const failThreshold = parseInt(args.find(arg => arg.startsWith('--fail-threshold='))?.split('=')[1] || '80');

// ANSI 颜色代码
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

/**
 * 带颜色的控制台输出
 */
function colorLog(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

/**
 * 格式化时间
 */
function formatTime(ms) {
  if (ms < 1000) {
    return `${ms.toFixed(2)}ms`;
  } else {
    return `${(ms / 1000).toFixed(2)}s`;
  }
}

/**
 * 打印性能报告摘要
 */
function printSummary(report) {
  colorLog('\n🎯 TH-Suite 前端性能测试报告', 'bright');
  colorLog('=====================================', 'cyan');
  
  const { summary } = report;
  
  // 基本信息
  colorLog(`\n📊 测试概览:`, 'blue');
  console.log(`   总测试数: ${summary.totalTests}`);
  console.log(`   通过测试: ${summary.passedTests}`);
  console.log(`   失败测试: ${summary.failedTests}`);
  console.log(`   通过率: ${summary.passRate.toFixed(1)}%`);
  console.log(`   执行时间: ${formatTime(summary.executionTime * 1000)}`);
  
  // 综合评分
  const scoreColor = summary.overallScore >= 90 ? 'green' : 
                    summary.overallScore >= 80 ? 'yellow' : 'red';
  colorLog(`\n🏆 综合评分: ${summary.overallScore}/100`, scoreColor);
  
  // 测试结果详情
  colorLog(`\n📋 详细结果:`, 'blue');
  const tests = [
    { name: '启动性能', passed: report.testResults.startup?.passed },
    { name: '表格渲染', passed: report.testResults.tableRendering?.passed },
    { name: '数据处理', passed: report.testResults.dataProcessing?.passed },
    { name: '包体积优化', passed: report.testResults.bundleOptimization?.passed },
    { name: 'Web Vitals', passed: report.testResults.webVitals?.passed },
  ];
  
  tests.forEach(test => {
    const status = test.passed ? '✅ 通过' : '❌ 失败';
    const statusColor = test.passed ? 'green' : 'red';
    console.log(`   ${test.name}: `, end='');
    colorLog(status, statusColor);
  });
  
  // 关键问题
  if (report.criticalIssues.length > 0) {
    colorLog(`\n❌ 关键问题:`, 'red');
    report.criticalIssues.forEach(issue => {
      console.log(`   ${issue}`);
    });
  }
  
  // 优化建议
  if (report.recommendations.length > 0 && isVerbose) {
    colorLog(`\n💡 优化建议:`, 'yellow');
    report.recommendations.forEach(rec => {
      console.log(`   ${rec}`);
    });
  }
  
  // 达标项目
  if (report.passedRequirements.length > 0 && isVerbose) {
    colorLog(`\n✅ 达标项目:`, 'green');
    report.passedRequirements.forEach(req => {
      console.log(`   ${req}`);
    });
  }
}

/**
 * 生成JUnit格式的测试报告
 */
function generateJUnitReport(report) {
  const { summary, testResults } = report;
  
  const tests = [
    { name: 'startup-performance', passed: testResults.startup?.passed, time: 0.1 },
    { name: 'table-rendering-performance', passed: testResults.tableRendering?.passed, time: 0.2 },
    { name: 'data-processing-performance', passed: testResults.dataProcessing?.passed, time: 0.3 },
    { name: 'bundle-optimization', passed: testResults.bundleOptimization?.passed, time: 0.1 },
    { name: 'web-vitals', passed: testResults.webVitals?.passed, time: 0.1 },
  ];
  
  const failedCount = tests.filter(test => !test.passed).length;
  const totalTime = summary.executionTime;
  
  let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
  xml += `<testsuites name="TH-Suite Performance Tests" tests="${summary.totalTests}" failures="${failedCount}" time="${totalTime}">\n`;
  xml += `  <testsuite name="Performance Tests" tests="${summary.totalTests}" failures="${failedCount}" time="${totalTime}">\n`;
  
  tests.forEach(test => {
    xml += `    <testcase classname="PerformanceTest" name="${test.name}" time="${test.time}">\n`;
    if (!test.passed) {
      xml += `      <failure message="Performance test failed">Test ${test.name} did not meet performance requirements</failure>\n`;
    }
    xml += `    </testcase>\n`;
  });
  
  xml += `  </testsuite>\n`;
  xml += `</testsuites>\n`;
  
  return xml;
}

/**
 * 保存报告到文件
 */
async function saveReport(report, filename) {
  try {
    const dir = path.dirname(filename);
    await fs.mkdir(dir, { recursive: true });
    
    if (filename.endsWith('.xml')) {
      const junitReport = generateJUnitReport(report);
      await fs.writeFile(filename, junitReport, 'utf8');
    } else {
      const jsonReport = JSON.stringify(report, null, 2);
      await fs.writeFile(filename, jsonReport, 'utf8');
    }
    
    colorLog(`\n📄 报告已保存到: ${filename}`, 'green');
  } catch (error) {
    colorLog(`\n❌ 保存报告失败: ${error.message}`, 'red');
  }
}

/**
 * 主函数
 */
async function main() {
  try {
    colorLog('🚀 开始运行 TH-Suite 前端性能测试...', 'bright');
    
    if (isVerbose) {
      colorLog('详细模式已启用', 'cyan');
    }
    
    if (failThreshold !== 80) {
      colorLog(`失败阈值设置为: ${failThreshold}%`, 'cyan');
    }
    
    // 运行性能测试
    const startTime = Date.now();
    const report = await runComprehensivePerformanceTest();
    const endTime = Date.now();
    
    // 更新执行时间
    report.summary.executionTime = (endTime - startTime) / 1000;
    
    // 打印报告
    printSummary(report);
    
    // 保存报告到文件
    if (outputFile) {
      await saveReport(report, outputFile);
    }
    
    // 在CI环境中自动保存JUnit报告
    if (process.env.CI) {
      const junitFile = 'test-results/performance-tests.xml';
      await saveReport(report, junitFile);
      colorLog(`\n📊 CI报告已保存到: ${junitFile}`, 'cyan');
    }
    
    // 根据综合评分决定退出代码
    if (report.summary.overallScore < failThreshold) {
      colorLog(`\n❌ 性能测试失败: 综合评分 ${report.summary.overallScore} 低于阈值 ${failThreshold}`, 'red');
      process.exit(1);
    } else {
      colorLog(`\n✅ 性能测试通过: 综合评分 ${report.summary.overallScore}`, 'green');
      process.exit(0);
    }
    
  } catch (error) {
    colorLog(`\n❌ 性能测试执行失败: ${error.message}`, 'red');
    
    if (isVerbose) {
      console.error(error);
    }
    
    process.exit(1);
  }
}

/**
 * 显示帮助信息
 */
function showHelp() {
  console.log(`
TH-Suite 前端性能测试工具

使用方法:
  node scripts/run-performance-tests.js [选项]

选项:
  -v, --verbose              显示详细输出
  --output=<文件路径>        保存报告到指定文件 (.json 或 .xml)
  --fail-threshold=<阈值>    设置失败阈值 (默认: 80)
  -h, --help                显示此帮助信息

示例:
  node scripts/run-performance-tests.js
  node scripts/run-performance-tests.js --verbose --output=report.json
  node scripts/run-performance-tests.js --fail-threshold=90
  
环境变量:
  CI                        在CI环境中自动生成JUnit报告
`);
}

// 处理帮助参数
if (args.includes('--help') || args.includes('-h')) {
  showHelp();
  process.exit(0);
}

// 运行主函数
main().catch(error => {
  colorLog(`未处理的错误: ${error.message}`, 'red');
  process.exit(1);
});