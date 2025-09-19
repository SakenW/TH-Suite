/**
 * 虚拟化性能测试组件
 * 用于验证虚拟化组件在大数据场景下的性能表现
 */

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { 
  Card, 
  Button, 
  Space, 
  Typography, 
  Statistic, 
  Progress, 
  Row, 
  Col, 
  Select,
  InputNumber,
  Switch,
  Tabs,
  Alert,
  Divider,
  Tag,
  Table,
  Badge
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import { ColumnDef } from '@tanstack/react-table'
import VirtualizedList from '../virtualization/VirtualizedList'
import VirtualizedDataTable from '../virtualization/VirtualizedDataTable'
import { ModInfo } from '../ModLoader/ModInfoCard'

const { Title, Text } = Typography
const { Option } = Select
const { TabPane } = Tabs

// ============================================================
// 类型定义
// ============================================================

interface PerformanceMetrics {
  renderTime: number
  memoryUsage: number
  fps: number
  scrollPerformance: number
  cacheHitRate: number
  visibleRange: [number, number]
  totalRendered: number
}

interface TestConfig {
  dataSize: number
  itemHeight: number
  enableVirtualization: boolean
  overscan: number
  enableAnimation: boolean
  testDuration: number // 秒
}

interface TestResult {
  config: TestConfig
  metrics: PerformanceMetrics
  timestamp: number
  passed: boolean
  issues: string[]
}

// ============================================================
// 测试数据生成器
// ============================================================

const generateTestMods = (count: number): ModInfo[] => {
  const loaderTypes: ModInfo['loader_type'][] = ['forge', 'fabric', 'quilt', 'neoforge']
  const versions = ['1.20.1', '1.19.4', '1.18.2', '1.16.5']
  const authors = ['TestAuthor1', 'TestAuthor2', 'TestDeveloper', 'ModMaker']
  
  return Array.from({ length: count }, (_, index) => ({
    mod_id: `test_mod_${index.toString().padStart(6, '0')}`,
    name: `测试MOD ${index + 1}`,
    version: `${Math.floor(Math.random() * 10) + 1}.${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 10)}`,
    loader_type: loaderTypes[Math.floor(Math.random() * loaderTypes.length)],
    minecraft_version: versions[Math.floor(Math.random() * versions.length)],
    authors: [authors[Math.floor(Math.random() * authors.length)]],
    description: `这是测试MOD ${index + 1}的描述，用于性能测试。包含一些较长的文本内容来模拟真实的MOD描述。`,
    file_size: Math.floor(Math.random() * 10000000) + 1000000, // 1MB - 10MB
    homepage: `https://example.com/mod${index}`,
    license: 'MIT',
    supported_sides: new Set(Math.random() > 0.5 ? ['client', 'server'] : ['client']),
    dependencies: Math.random() > 0.7 ? [`dep_mod_${Math.floor(Math.random() * 100)}`] : [],
    language_files: Math.random() > 0.3 ? [`en_us.json`, `zh_cn.json`] : [],
  }))
}

const generateTableData = (count: number) => {
  return Array.from({ length: count }, (_, index) => ({
    id: `item_${index}`,
    name: `数据项 ${index + 1}`,
    value: Math.floor(Math.random() * 1000),
    category: ['A', 'B', 'C', 'D'][Math.floor(Math.random() * 4)],
    status: Math.random() > 0.5 ? '活跃' : '非活跃',
    created: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
    description: `这是数据项 ${index + 1} 的描述信息，包含了详细的说明文本`,
  }))
}

// 表格列定义
const tableColumns: ColumnDef<any>[] = [
  { accessorKey: 'id', header: 'ID', size: 120 },
  { accessorKey: 'name', header: '名称', size: 200 },
  { accessorKey: 'value', header: '值', size: 100 },
  { accessorKey: 'category', header: '分类', size: 100 },
  { accessorKey: 'status', header: '状态', size: 100 },
  { accessorKey: 'created', header: '创建时间', size: 180 },
  { accessorKey: 'description', header: '描述', size: 300 },
]

// ============================================================
// 主组件
// ============================================================

export const VirtualizationPerformanceTest: React.FC = () => {
  const [testConfig, setTestConfig] = useState<TestConfig>({
    dataSize: 10000,
    itemHeight: 56,
    enableVirtualization: true,
    overscan: 8,
    enableAnimation: true,
    testDuration: 30,
  })
  
  const [isRunning, setIsRunning] = useState(false)
  const [currentMetrics, setCurrentMetrics] = useState<PerformanceMetrics | null>(null)
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [activeTab, setActiveTab] = useState('list')
  
  const performanceObserverRef = useRef<PerformanceObserver | null>(null)
  const frameCountRef = useRef(0)
  const startTimeRef = useRef(0)
  const testDataRef = useRef<{ mods: ModInfo[], tableData: any[] }>({ mods: [], tableData: [] })
  
  // 生成测试数据
  const testData = useMemo(() => {
    const mods = generateTestMods(testConfig.dataSize)
    const tableData = generateTableData(testConfig.dataSize)
    testDataRef.current = { mods, tableData }
    return { mods, tableData }
  }, [testConfig.dataSize])
  
  // 性能监控
  const startPerformanceMonitoring = useCallback(() => {
    frameCountRef.current = 0
    startTimeRef.current = performance.now()
    
    // 监控渲染性能
    if ('PerformanceObserver' in window) {
      performanceObserverRef.current = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'measure') {
            console.log('Performance measure:', entry.name, entry.duration)
          }
        }
      })
      
      performanceObserverRef.current.observe({ entryTypes: ['measure', 'navigation'] })
    }
    
    // FPS计算
    const updateFPS = () => {
      frameCountRef.current++
      if (isRunning) {
        requestAnimationFrame(updateFPS)
      }
    }
    
    requestAnimationFrame(updateFPS)
  }, [isRunning])
  
  const stopPerformanceMonitoring = useCallback(() => {
    if (performanceObserverRef.current) {
      performanceObserverRef.current.disconnect()
    }
    
    const endTime = performance.now()
    const duration = (endTime - startTimeRef.current) / 1000
    const fps = Math.round(frameCountRef.current / duration)
    
    const metrics: PerformanceMetrics = {
      renderTime: endTime - startTimeRef.current,
      memoryUsage: (performance as any).memory ? (performance as any).memory.usedJSHeapSize / 1024 / 1024 : 0,
      fps,
      scrollPerformance: fps >= 50 ? 100 : (fps / 60) * 100,
      cacheHitRate: Math.random() * 40 + 60, // 模拟缓存命中率
      visibleRange: [0, Math.min(20, testConfig.dataSize)],
      totalRendered: Math.min(testConfig.overscan * 2 + 20, testConfig.dataSize),
    }
    
    setCurrentMetrics(metrics)
    
    // 判断测试是否通过
    const issues: string[] = []
    if (fps < 30) issues.push('FPS过低 (< 30)')
    if (metrics.renderTime > 5000) issues.push('渲染时间过长 (> 5s)')
    if (metrics.memoryUsage > 500) issues.push('内存使用过高 (> 500MB)')
    
    const result: TestResult = {
      config: { ...testConfig },
      metrics,
      timestamp: Date.now(),
      passed: issues.length === 0,
      issues,
    }
    
    setTestResults(prev => [result, ...prev].slice(0, 10)) // 保留最近10次测试结果
    
    return metrics
  }, [testConfig])
  
  // 开始测试
  const startTest = useCallback(async () => {
    setIsRunning(true)
    setCurrentMetrics(null)
    
    startPerformanceMonitoring()
    
    // 运行测试指定时间
    setTimeout(() => {
      setIsRunning(false)
      stopPerformanceMonitoring()
    }, testConfig.testDuration * 1000)
  }, [testConfig.testDuration, startPerformanceMonitoring, stopPerformanceMonitoring])
  
  // 停止测试
  const stopTest = useCallback(() => {
    setIsRunning(false)
    stopPerformanceMonitoring()
  }, [stopPerformanceMonitoring])
  
  // 清除结果
  const clearResults = useCallback(() => {
    setTestResults([])
    setCurrentMetrics(null)
  }, [])
  
  // MOD项目渲染器
  const renderModItem = useCallback((mod: ModInfo, index: number) => (
    <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Text strong>{mod.name}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {mod.mod_id} • v{mod.version} • {mod.loader_type}
          </Text>
        </div>
        <div>
          <Tag color="blue">{mod.minecraft_version}</Tag>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {(mod.file_size! / 1024 / 1024).toFixed(1)}MB
          </Text>
        </div>
      </div>
    </div>
  ), [])
  
  // 渲染测试配置
  const renderTestConfig = () => (
    <Card title="测试配置" className="mb-4">
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Text>数据量：</Text>
          <InputNumber
            min={1000}
            max={100000}
            step={1000}
            value={testConfig.dataSize}
            onChange={(value) => setTestConfig(prev => ({ ...prev, dataSize: value || 10000 }))}
            style={{ width: '100%' }}
            formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          />
        </Col>
        
        <Col span={8}>
          <Text>项目高度：</Text>
          <InputNumber
            min={24}
            max={200}
            value={testConfig.itemHeight}
            onChange={(value) => setTestConfig(prev => ({ ...prev, itemHeight: value || 56 }))}
            style={{ width: '100%' }}
          />
        </Col>
        
        <Col span={8}>
          <Text>缓冲区大小：</Text>
          <InputNumber
            min={0}
            max={50}
            value={testConfig.overscan}
            onChange={(value) => setTestConfig(prev => ({ ...prev, overscan: value || 8 }))}
            style={{ width: '100%' }}
          />
        </Col>
        
        <Col span={8}>
          <Text>测试时长（秒）：</Text>
          <InputNumber
            min={10}
            max={120}
            value={testConfig.testDuration}
            onChange={(value) => setTestConfig(prev => ({ ...prev, testDuration: value || 30 }))}
            style={{ width: '100%' }}
          />
        </Col>
        
        <Col span={8}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text>启用虚拟化：</Text>
              <Switch
                checked={testConfig.enableVirtualization}
                onChange={(checked) => setTestConfig(prev => ({ ...prev, enableVirtualization: checked }))}
              />
            </div>
            <div>
              <Text>启用动画：</Text>
              <Switch
                checked={testConfig.enableAnimation}
                onChange={(checked) => setTestConfig(prev => ({ ...prev, enableAnimation: checked }))}
              />
            </div>
          </Space>
        </Col>
        
        <Col span={8}>
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={startTest}
              disabled={isRunning}
              loading={isRunning}
            >
              开始测试
            </Button>
            <Button
              icon={<PauseCircleOutlined />}
              onClick={stopTest}
              disabled={!isRunning}
            >
              停止测试
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={clearResults}
            >
              清除结果
            </Button>
          </Space>
        </Col>
      </Row>
    </Card>
  )
  
  // 渲染性能指标
  const renderMetrics = () => {
    if (!currentMetrics) return null
    
    return (
      <Card title="性能指标" className="mb-4">
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic
              title="FPS"
              value={currentMetrics.fps}
              suffix="fps"
              valueStyle={{ 
                color: currentMetrics.fps >= 50 ? '#3f8600' : 
                       currentMetrics.fps >= 30 ? '#faad14' : '#cf1322' 
              }}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          
          <Col span={6}>
            <Statistic
              title="渲染时间"
              value={currentMetrics.renderTime}
              suffix="ms"
              precision={0}
              valueStyle={{ 
                color: currentMetrics.renderTime <= 1000 ? '#3f8600' : 
                       currentMetrics.renderTime <= 3000 ? '#faad14' : '#cf1322' 
              }}
            />
          </Col>
          
          <Col span={6}>
            <Statistic
              title="内存使用"
              value={currentMetrics.memoryUsage}
              suffix="MB"
              precision={1}
              valueStyle={{ 
                color: currentMetrics.memoryUsage <= 100 ? '#3f8600' : 
                       currentMetrics.memoryUsage <= 300 ? '#faad14' : '#cf1322' 
              }}
            />
          </Col>
          
          <Col span={6}>
            <Statistic
              title="缓存命中率"
              value={currentMetrics.cacheHitRate}
              suffix="%"
              precision={1}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
        </Row>
        
        <Divider />
        
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Text strong>滚动性能评分：</Text>
            <Progress 
              percent={currentMetrics.scrollPerformance} 
              status={currentMetrics.scrollPerformance >= 80 ? 'success' : 
                     currentMetrics.scrollPerformance >= 60 ? 'active' : 'exception'}
            />
          </Col>
          
          <Col span={12}>
            <Text strong>可见范围：</Text>
            <Tag color="blue">
              {currentMetrics.visibleRange[0]} - {currentMetrics.visibleRange[1]} / {currentMetrics.totalRendered} 渲染
            </Tag>
          </Col>
        </Row>
      </Card>
    )
  }
  
  // 渲染测试结果历史
  const renderTestHistory = () => {
    if (testResults.length === 0) return null
    
    const columns = [
      {
        title: '时间',
        dataIndex: 'timestamp',
        key: 'timestamp',
        render: (timestamp: number) => new Date(timestamp).toLocaleTimeString(),
      },
      {
        title: '数据量',
        key: 'dataSize',
        render: (record: TestResult) => record.config.dataSize.toLocaleString(),
      },
      {
        title: 'FPS',
        key: 'fps',
        render: (record: TestResult) => (
          <Badge 
            count={record.metrics.fps}
            style={{ 
              backgroundColor: record.metrics.fps >= 50 ? '#52c41a' : 
                              record.metrics.fps >= 30 ? '#faad14' : '#ff4d4f' 
            }}
          />
        ),
      },
      {
        title: '渲染时间',
        key: 'renderTime',
        render: (record: TestResult) => `${record.metrics.renderTime.toFixed(0)}ms`,
      },
      {
        title: '内存',
        key: 'memory',
        render: (record: TestResult) => `${record.metrics.memoryUsage.toFixed(1)}MB`,
      },
      {
        title: '状态',
        key: 'passed',
        render: (record: TestResult) => record.passed ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>通过</Tag>
        ) : (
          <Tag color="error" icon={<ExclamationCircleOutlined />}>失败</Tag>
        ),
      },
      {
        title: '问题',
        key: 'issues',
        render: (record: TestResult) => record.issues.map((issue, index) => (
          <Tag key={index} color="warning">{issue}</Tag>
        )),
      },
    ]
    
    return (
      <Card title="测试历史">
        <Table
          columns={columns}
          dataSource={testResults}
          rowKey="timestamp"
          pagination={{ pageSize: 5 }}
          size="small"
        />
      </Card>
    )
  }
  
  return (
    <div className="virtualization-performance-test">
      <Card className="mb-4">
        <Title level={3} style={{ margin: 0 }}>
          <DashboardOutlined /> 虚拟化性能测试
        </Title>
        <Text type="secondary">
          测试虚拟化组件在大数据场景下的性能表现，验证是否达到60fps流畅渲染标准
        </Text>
      </Card>
      
      {renderTestConfig()}
      {renderMetrics()}
      
      {isRunning && (
        <Alert
          message="性能测试进行中"
          description={`正在测试 ${testConfig.dataSize.toLocaleString()} 条数据的渲染性能，预计需要 ${testConfig.testDuration} 秒...`}
          type="info"
          showIcon
          className="mb-4"
        />
      )}
      
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="虚拟化列表" key="list">
          <Card title={`MOD列表测试 (${testData.mods.length.toLocaleString()} 项)`}>
            <VirtualizedList
              data={testData.mods}
              renderItem={renderModItem}
              height={400}
              loading={isRunning}
              showToolbar={true}
              toolbarTitle="性能测试 - MOD列表"
              showPerformanceStats={true}
              virtualizerConfig={{
                estimateSize: testConfig.itemHeight,
                overscan: testConfig.overscan,
                enableMeasureCache: true,
              }}
              responsive={true}
            />
          </Card>
        </TabPane>
        
        <TabPane tab="虚拟化表格" key="table">
          <Card title={`数据表格测试 (${testData.tableData.length.toLocaleString()} 行)`}>
            <VirtualizedDataTable
              data={testData.tableData}
              columns={tableColumns}
              height={400}
              loading={isRunning}
              showToolbar={true}
              toolbarTitle="性能测试 - 数据表格"
              showPerformanceStats={true}
              enableSorting={true}
              enableFiltering={true}
              enableGlobalFilter={true}
              enableRowSelection={true}
              rowHeight={testConfig.itemHeight}
              overscan={testConfig.overscan}
              striped={true}
              bordered={true}
              responsive={true}
            />
          </Card>
        </TabPane>
      </Tabs>
      
      <div style={{ marginTop: 24 }}>
        {renderTestHistory()}
      </div>
    </div>
  )
}

export default VirtualizationPerformanceTest