/**
 * 性能测试页面组件
 * 提供UI界面来运行性能测试并展示结果
 */

import React, { useState, useCallback } from 'react';
import { Button, Card, Progress, Tabs, Alert, Spin, Row, Col, Statistic, Timeline, Table } from 'antd';
import { PlayCircleOutlined, DownloadOutlined, ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { runComprehensivePerformanceTest, ComprehensivePerformanceReport } from './PerformanceTestRunner';

const { TabPane } = Tabs;

export const PerformanceTestPage: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTest, setCurrentTest] = useState('');
  const [report, setReport] = useState<ComprehensivePerformanceReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * 运行性能测试
   */
  const handleRunTests = useCallback(async () => {
    setIsRunning(true);
    setProgress(0);
    setCurrentTest('');
    setError(null);
    setReport(null);

    try {
      // 模拟进度更新
      const progressSteps = [
        { progress: 20, test: '启动性能测试' },
        { progress: 40, test: '表格渲染性能测试' },
        { progress: 60, test: '数据处理性能测试' },
        { progress: 80, test: '包体积优化验证' },
        { progress: 90, test: 'Web Vitals 收集' },
        { progress: 100, test: '生成报告' },
      ];

      // 模拟测试进度
      for (const step of progressSteps) {
        setProgress(step.progress);
        setCurrentTest(step.test);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      // 运行实际测试
      const testReport = await runComprehensivePerformanceTest();
      setReport(testReport);

    } catch (err) {
      console.error('性能测试失败:', err);
      setError(err instanceof Error ? err.message : '性能测试执行失败');
    } finally {
      setIsRunning(false);
      setProgress(100);
      setCurrentTest('');
    }
  }, []);

  /**
   * 导出报告
   */
  const handleExportReport = useCallback(() => {
    if (!report) return;

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `th-suite-performance-report-${timestamp}.json`;
    
    const dataStr = JSON.stringify(report, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    
    URL.revokeObjectURL(url);
  }, [report]);

  /**
   * 渲染测试概览
   */
  const renderTestSummary = () => {
    if (!report) return null;

    const { summary } = report;
    const overallStatus = summary.overallScore >= 90 ? 'success' : 
                         summary.overallScore >= 80 ? 'warning' : 'error';

    return (
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="综合评分"
              value={summary.overallScore}
              suffix="/ 100"
              valueStyle={{ 
                color: overallStatus === 'success' ? '#3f8600' : 
                       overallStatus === 'warning' ? '#cf1322' : '#cf1322' 
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="通过率"
              value={summary.passRate}
              suffix="%"
              precision={1}
              valueStyle={{ 
                color: summary.passRate >= 80 ? '#3f8600' : '#cf1322' 
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="测试项目"
              value={summary.passedTests}
              suffix={`/ ${summary.totalTests}`}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="执行时间"
              value={summary.executionTime}
              suffix="秒"
              precision={2}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  /**
   * 渲染测试结果表格
   */
  const renderTestResultsTable = () => {
    if (!report) return null;

    const { testResults } = report;
    
    const dataSource = [
      {
        key: '1',
        testName: '启动性能',
        status: testResults.startup?.passed,
        keyMetric: testResults.startup?.metrics?.coldStartTime ? 
          `${testResults.startup.metrics.coldStartTime.toFixed(2)}ms` : 'N/A',
        requirement: '< 1500ms',
      },
      {
        key: '2',
        testName: '表格渲染',
        status: testResults.tableRendering?.passed,
        keyMetric: testResults.tableRendering?.results?.[50000]?.scrollFPS ? 
          `${testResults.tableRendering.results[50000].scrollFPS.toFixed(1)}fps` : 'N/A',
        requirement: '≥ 60fps',
      },
      {
        key: '3',
        testName: '数据处理',
        status: testResults.dataProcessing?.passed,
        keyMetric: testResults.dataProcessing?.metrics?.importTime ? 
          `${(testResults.dataProcessing.metrics.importTime / 1000).toFixed(2)}s` : 'N/A',
        requirement: '< 300s (1GB)',
      },
      {
        key: '4',
        testName: '包体积优化',
        status: testResults.bundleOptimization?.passed,
        keyMetric: testResults.bundleOptimization?.currentMetrics?.totalSize ? 
          `${testResults.bundleOptimization.currentMetrics.totalSize.toFixed(1)}KB` : 'N/A',
        requirement: '< 2048KB',
      },
      {
        key: '5',
        testName: 'Web Vitals',
        status: testResults.webVitals?.passed,
        keyMetric: testResults.webVitals?.metrics?.performanceScore ? 
          `${testResults.webVitals.metrics.performanceScore}/100` : 'N/A',
        requirement: '≥ 90/100',
      },
    ];

    const columns = [
      {
        title: '测试项目',
        dataIndex: 'testName',
        key: 'testName',
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (status: boolean) => (
          status ? (
            <span style={{ color: '#52c41a' }}>
              <CheckCircleOutlined /> 通过
            </span>
          ) : (
            <span style={{ color: '#ff4d4f' }}>
              <CloseCircleOutlined /> 失败
            </span>
          )
        ),
      },
      {
        title: '关键指标',
        dataIndex: 'keyMetric',
        key: 'keyMetric',
      },
      {
        title: '要求',
        dataIndex: 'requirement',
        key: 'requirement',
      },
    ];

    return (
      <Table 
        dataSource={dataSource} 
        columns={columns} 
        pagination={false}
        size="small"
      />
    );
  };

  /**
   * 渲染优化建议
   */
  const renderRecommendations = () => {
    if (!report) return null;

    const { recommendations, criticalIssues, passedRequirements } = report;

    return (
      <div>
        {passedRequirements.length > 0 && (
          <Alert
            type="success"
            showIcon
            message="达标项目"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {passedRequirements.map((req, index) => (
                  <li key={index}>{req}</li>
                ))}
              </ul>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        {criticalIssues.length > 0 && (
          <Alert
            type="error"
            showIcon
            message="关键问题"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {criticalIssues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        {recommendations.length > 0 && (
          <Alert
            type="info"
            showIcon
            message="优化建议"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {recommendations.map((rec, index) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            }
          />
        )}
      </div>
    );
  };

  /**
   * 渲染详细指标
   */
  const renderDetailedMetrics = () => {
    if (!report) return null;

    const { testResults } = report;

    return (
      <Row gutter={[16, 16]}>
        {/* 启动性能指标 */}
        <Col span={12}>
          <Card title="启动性能指标" size="small">
            {testResults.startup?.metrics && (
              <div>
                <p>冷启动时间: {testResults.startup.metrics.coldStartTime?.toFixed(2)}ms</p>
                <p>骨架屏时间: {testResults.startup.metrics.skeletonLoadTime?.toFixed(2)}ms</p>
                <p>首次内容绘制: {testResults.startup.metrics.firstContentfulPaint?.toFixed(2)}ms</p>
                <p>可交互时间: {testResults.startup.metrics.timeToInteractive?.toFixed(2)}ms</p>
              </div>
            )}
          </Card>
        </Col>

        {/* 表格性能指标 */}
        <Col span={12}>
          <Card title="表格性能指标" size="small">
            {testResults.tableRendering?.results?.[50000] && (
              <div>
                <p>滚动帧率: {testResults.tableRendering.results[50000].scrollFPS?.toFixed(1)}fps</p>
                <p>内存使用: {testResults.tableRendering.results[50000].memoryUsage?.toFixed(2)}MB</p>
                <p>虚拟化: {testResults.tableRendering.results[50000].virtualizationEffective ? '生效' : '未生效'}</p>
                <p>DOM节点数: {testResults.tableRendering.results[50000].domNodeCount?.toLocaleString()}</p>
              </div>
            )}
          </Card>
        </Col>

        {/* 数据处理指标 */}
        <Col span={12}>
          <Card title="数据处理指标" size="small">
            {testResults.dataProcessing?.metrics && (
              <div>
                <p>导入时间: {(testResults.dataProcessing.metrics.importTime / 1000)?.toFixed(2)}s</p>
                <p>断点续传: {testResults.dataProcessing.metrics.resumableImport ? '支持' : '不支持'}</p>
                <p>成功率: {testResults.dataProcessing.metrics.resumeSuccessRate?.toFixed(1)}%</p>
                <p>数据完整性: {testResults.dataProcessing.metrics.dataIntegrityScore?.toFixed(1)}%</p>
              </div>
            )}
          </Card>
        </Col>

        {/* Web Vitals 指标 */}
        <Col span={12}>
          <Card title="Web Vitals 指标" size="small">
            {testResults.webVitals?.metrics && (
              <div>
                <p>CLS: {testResults.webVitals.metrics.CLS?.toFixed(4)}</p>
                <p>FID: {testResults.webVitals.metrics.FID?.toFixed(2)}ms</p>
                <p>LCP: {testResults.webVitals.metrics.LCP?.toFixed(2)}ms</p>
                <p>性能评分: {testResults.webVitals.metrics.performanceScore}/100</p>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1>TH-Suite 前端性能测试</h1>
        <p>验证前端重构后的性能是否达到优化规范要求</p>
      </div>

      {/* 控制按钮 */}
      <div style={{ marginBottom: 24 }}>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleRunTests}
          disabled={isRunning}
          size="large"
          style={{ marginRight: 16 }}
        >
          {isRunning ? '运行中...' : '开始性能测试'}
        </Button>

        {report && (
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExportReport}
            style={{ marginRight: 16 }}
          >
            导出报告
          </Button>
        )}

        {report && (
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRunTests}
            disabled={isRunning}
          >
            重新测试
          </Button>
        )}
      </div>

      {/* 测试进度 */}
      {isRunning && (
        <Card style={{ marginBottom: 24 }}>
          <Spin spinning={isRunning}>
            <div style={{ textAlign: 'center', padding: 20 }}>
              <p style={{ marginBottom: 16, fontSize: 16 }}>
                {currentTest || '准备测试...'}
              </p>
              <Progress 
                percent={progress} 
                status={isRunning ? 'active' : 'success'}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </div>
          </Spin>
        </Card>
      )}

      {/* 错误信息 */}
      {error && (
        <Alert
          type="error"
          showIcon
          message="测试执行失败"
          description={error}
          style={{ marginBottom: 24 }}
        />
      )}

      {/* 测试结果 */}
      {report && (
        <>
          {/* 概览统计 */}
          {renderTestSummary()}

          {/* 详细结果标签页 */}
          <Tabs defaultActiveKey="1">
            <TabPane tab="测试结果" key="1">
              {renderTestResultsTable()}
            </TabPane>

            <TabPane tab="详细指标" key="2">
              {renderDetailedMetrics()}
            </TabPane>

            <TabPane tab="优化建议" key="3">
              {renderRecommendations()}
            </TabPane>

            <TabPane tab="详细报告" key="4">
              <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 6 }}>
                <h3>启动性能测试报告</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {report.detailedReports.startup}
                </pre>

                <h3>表格渲染性能测试报告</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {report.detailedReports.tableRendering}
                </pre>

                <h3>数据处理性能测试报告</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {report.detailedReports.dataProcessing}
                </pre>

                <h3>包体积优化验证报告</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {report.detailedReports.bundleOptimization}
                </pre>

                <h3>Web Vitals 性能报告</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {report.detailedReports.webVitals}
                </pre>
              </div>
            </TabPane>
          </Tabs>
        </>
      )}

      {/* 使用说明 */}
      {!report && !isRunning && (
        <Card title="性能测试说明" style={{ marginTop: 24 }}>
          <Timeline>
            <Timeline.Item color="blue">
              <strong>启动性能测试</strong>：验证冷启动时间 &lt; 1.5s，首屏骨架 200ms 内出现
            </Timeline.Item>
            <Timeline.Item color="blue">
              <strong>表格渲染性能</strong>：验证 1-5万条数据滚动保持 60fps，虚拟化有效
            </Timeline.Item>
            <Timeline.Item color="blue">
              <strong>数据处理性能</strong>：验证 1GB 资源包导入支持分块断点续传
            </Timeline.Item>
            <Timeline.Item color="blue">
              <strong>包体积优化</strong>：验证 Bundle 大小控制，Tree Shaking 效果
            </Timeline.Item>
            <Timeline.Item color="blue">
              <strong>Web Vitals 收集</strong>：收集 CLS、FID、LCP 等核心性能指标
            </Timeline.Item>
          </Timeline>

          <Alert
            type="info"
            showIcon
            message="注意事项"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>测试过程中请避免其他操作，以确保结果准确性</li>
                <li>测试可能需要几分钟时间，请耐心等待</li>
                <li>建议在生产环境配置下运行测试以获得最准确的结果</li>
                <li>可以导出详细报告用于后续分析和优化</li>
              </ul>
            }
            style={{ marginTop: 16 }}
          />
        </Card>
      )}
    </div>
  );
};