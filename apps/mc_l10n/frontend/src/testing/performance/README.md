# TH-Suite 前端性能测试套件

这是一个专为 TH-Suite 前端重构后设计的全面性能测试套件，用于验证是否达到优化规范要求。

## 🎯 测试目标

验证以下性能规范要求：

1. **启动性能**
   - 首次启动 < 1.5s
   - 首屏骨架 200ms内出现
   - 验证冷启动和热启动性能

2. **表格渲染性能**
   - 1-5万条表格滚动保持60fps
   - 固定行高 + 虚拟化验证
   - 内存使用恒定测试

3. **数据处理性能**
   - 导入1GB资源包：分块断点、失败可恢复
   - 导入后快照可回滚验证
   - 批量事务处理性能

4. **包体积优化**
   - Bundle大小对比重构前后
   - Tree Shaking效果验证
   - 代码分割优化效果

5. **数据库性能**
   - SQLCipher加密性能验证
   - WAL模式并发性能测试
   - 缓存命中率统计

## 🏗️ 架构设计

### 核心组件

```
src/testing/performance/
├── PerformanceTestSuite.ts          # 主测试套件
├── StartupPerformanceTest.ts        # 启动性能测试
├── TablePerformanceTest.ts          # 表格渲染性能测试
├── DataProcessingPerformanceTest.ts # 数据处理性能测试
├── BundleOptimizationTest.ts        # 包体积优化验证
├── WebVitalsCollector.ts            # Web Vitals收集器
├── PerformanceTestRunner.ts         # 测试运行器
├── PerformanceTestPage.tsx          # React测试页面
└── index.ts                         # 入口文件
```

### 测试工具

- **React DevTools Profiler** - 组件渲染性能分析
- **Performance API** - 浏览器性能指标收集
- **Web Vitals** - 核心用户体验指标
- **Memory API** - 内存使用监控
- **Custom Metrics** - 业务特定性能指标

## 🚀 使用方法

### 1. 命令行运行

```bash
# 基础性能测试
npm run test:performance

# 详细输出模式
npm run test:performance:verbose

# CI环境测试
npm run test:performance:ci

# 基准测试（保存详细报告）
npm run benchmark
```

### 2. 程序化使用

```typescript
import { runComprehensivePerformanceTest } from './src/testing/performance';

// 运行完整测试套件
const report = await runComprehensivePerformanceTest();

console.log(`综合评分: ${report.summary.overallScore}/100`);
console.log(`通过率: ${report.summary.passRate}%`);
```

### 3. React组件集成

```typescript
import { PerformanceTestPage } from './src/testing/performance';

// 在应用中添加性能测试页面
function App() {
  return (
    <div>
      <PerformanceTestPage />
    </div>
  );
}
```

### 4. 单独测试模块

```typescript
import { 
  runStartupPerformanceTest,
  runTablePerformanceTest,
  runDataProcessingPerformanceTest,
  runBundleOptimizationTest,
  collectWebVitals
} from './src/testing/performance';

// 运行单个测试
const startupResult = await runStartupPerformanceTest();
const tableResult = await runTablePerformanceTest([1000, 5000, 10000]);
const webVitalsResult = await collectWebVitals();
```

## 📊 性能指标详解

### 启动性能指标

| 指标 | 要求 | 说明 |
|------|------|------|
| 冷启动时间 | < 1500ms | 清空缓存后的首次启动时间 |
| 首屏骨架时间 | < 200ms | 骨架屏组件出现时间 |
| 首次内容绘制(FCP) | < 1000ms | 第一个内容元素渲染时间 |
| 可交互时间(TTI) | < 2000ms | 页面完全可交互时间 |

### 表格性能指标

| 指标 | 要求 | 说明 |
|------|------|------|
| 滚动帧率 | ≥ 60fps | 大数据量滚动的流畅度 |
| 支持行数 | ≥ 50000行 | 单表格最大数据支持量 |
| 内存使用 | < 300MB | 5万行数据的内存占用 |
| 虚拟化效率 | DOM节点 < 数据量10% | 虚拟化实现效果 |

### 数据处理指标

| 指标 | 要求 | 说明 |
|------|------|------|
| 1GB导入时间 | < 5分钟 | 大文件导入性能 |
| 断点续传成功率 | ≥ 90% | 中断恢复可靠性 |
| 数据完整性 | ≥ 95% | 数据处理准确性 |
| 事务吞吐量 | ≥ 100 ops/s | 批量操作性能 |

### Web Vitals 指标

| 指标 | 要求 | 说明 |
|------|------|------|
| CLS | ≤ 0.1 | 累积布局偏移 |
| FID | ≤ 100ms | 首次输入延迟 |
| LCP | ≤ 2500ms | 最大内容绘制 |
| 性能评分 | ≥ 90/100 | Lighthouse性能评分 |

## 🔧 配置选项

### 测试配置

```typescript
export const PerformanceTestConfig = {
  startup: {
    maxColdStartTime: 1500,    // 最大冷启动时间(ms)
    maxSkeletonTime: 200,      // 最大骨架屏时间(ms)
  },
  table: {
    minScrollFPS: 60,          // 最小滚动帧率
    maxRowsSupported: 50000,   // 最大支持行数
  },
  dataProcessing: {
    maxImportTimeFor1GB: 300000, // 1GB导入最大时间(ms)
    minResumeSuccessRate: 90,    // 最小续传成功率(%)
  },
  // ... 更多配置
};
```

### 命令行选项

```bash
# 详细输出
--verbose, -v

# 指定输出文件
--output=report.json

# 设置失败阈值
--fail-threshold=85

# 显示帮助
--help, -h
```

## 📈 报告格式

### 控制台输出

```
🎯 TH-Suite 前端性能测试报告
=====================================

📊 测试概览:
   总测试数: 5
   通过测试: 4
   失败测试: 1
   通过率: 80.0%
   综合评分: 85/100

📋 详细结果:
   启动性能: ✅ 通过
   表格渲染: ✅ 通过
   数据处理: ❌ 失败
   包体积优化: ✅ 通过
   Web Vitals: ✅ 通过
```

### JSON 报告

```json
{
  "summary": {
    "totalTests": 5,
    "passedTests": 4,
    "failedTests": 1,
    "overallScore": 85,
    "passRate": 80.0,
    "executionTime": 45.2
  },
  "testResults": {
    "startup": { "passed": true, "metrics": {...} },
    "tableRendering": { "passed": true, "results": {...} },
    "dataProcessing": { "passed": false, "metrics": {...} },
    "bundleOptimization": { "passed": true, "currentMetrics": {...} },
    "webVitals": { "passed": true, "metrics": {...} }
  },
  "recommendations": [...],
  "criticalIssues": [...],
  "detailedReports": {...}
}
```

## 🔄 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: npm run build
      - run: npm run test:performance:ci
      - uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: test-results/
```

### 失败阈值设置

```bash
# 不同环境的阈值建议
npm run test:performance:ci --fail-threshold=90  # 生产环境
npm run test:performance:ci --fail-threshold=85  # 预发布环境
npm run test:performance:ci --fail-threshold=80  # 开发环境
```

## 🐛 故障排除

### 常见问题

1. **测试运行失败**
   ```bash
   # 检查依赖是否完整
   npm install
   
   # 检查构建是否成功
   npm run build
   
   # 运行详细模式查看错误
   npm run test:performance:verbose
   ```

2. **性能指标异常**
   ```bash
   # 清理缓存重新测试
   rm -rf node_modules/.cache
   npm run test:performance
   
   # 检查系统资源使用情况
   htop  # Linux/Mac
   ```

3. **Web Vitals 收集失败**
   - 确保在真实浏览器环境中运行
   - 检查 Performance API 支持情况
   - 避免在 headless 模式下收集某些指标

### 调试技巧

```typescript
// 启用详细日志
localStorage.setItem('performance-debug', 'true');

// 手动触发单个测试
import { runStartupPerformanceTest } from './src/testing/performance';
const result = await runStartupPerformanceTest();
console.log(result);
```

## 🤝 贡献指南

### 添加新的性能测试

1. 创建测试类文件
2. 实现 `run*Tests()` 方法
3. 添加到 `PerformanceTestRunner`
4. 更新配置和类型定义
5. 编写测试用例

### 性能基准更新

当应用性能有显著改进时，可以更新性能基准：

```typescript
// 更新 PerformanceTestConfig
export const PerformanceTestConfig = {
  startup: {
    maxColdStartTime: 1200, // 从1500ms优化到1200ms
    // ...
  }
};
```

## 📚 参考资料

- [Web Vitals](https://web.dev/vitals/)
- [Performance API](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
- [React DevTools Profiler](https://reactjs.org/blog/2018/09/10/introducing-the-react-profiler.html)
- [Lighthouse Performance](https://developers.google.com/web/tools/lighthouse/v3/scoring)

## 📄 许可证

此测试套件遵循项目的开源许可证。