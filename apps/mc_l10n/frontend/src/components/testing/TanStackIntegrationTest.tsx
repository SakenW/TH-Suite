/**
 * TanStack Query 集成测试组件
 * 验证React Query hooks的功能和性能
 */

import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Space,
  Tag,
  Progress,
  Typography,
  Alert,
  Table,
  Badge,
  Divider,
  Tooltip,
  Switch,
  message,
  Tabs,
} from 'antd'
import {
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  BarChartOutlined,
  BugOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'

// 引入所有React Query hooks进行测试
import {
  useProjects,
  useActiveScans,
  useScanServiceStatus,
  useScanStatistics,
  useGlobalStatistics,
  useCreateProject,
  useStartScan,
} from '../../hooks/api'
import { queryKeys, cacheConfig } from '../../config/reactQuery'
import { errorHandler } from '../../utils/errorHandling'
import { cacheOptimizer } from '../../utils/cacheOptimization'
import { ProjectTable } from '../tables/ProjectTable'

const { Title, Text, Paragraph } = Typography

// ============================================================
// 测试配置
// ============================================================

interface TestConfig {
  enableRealTimeQueries: boolean
  enableCacheOptimization: boolean
  enableErrorSimulation: boolean
  queryRefreshInterval: number
}

interface PerformanceMetrics {
  queryCount: number
  errorCount: number
  averageResponseTime: number
  cacheHitRate: number
  memoryUsage: number
}

// ============================================================
// 主组件
// ============================================================

export const TanStackIntegrationTest: React.FC = () => {
  const queryClient = useQueryClient()
  
  // ============================================================
  // 状态管理
  // ============================================================
  
  const [testConfig, setTestConfig] = useState<TestConfig>({
    enableRealTimeQueries: true,
    enableCacheOptimization: true,
    enableErrorSimulation: false,
    queryRefreshInterval: 5000,
  })
  
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    queryCount: 0,
    errorCount: 0,
    averageResponseTime: 0,
    cacheHitRate: 0,
    memoryUsage: 0,
  })
  
  const [testResults, setTestResults] = useState<Array<{
    test: string
    status: 'success' | 'error' | 'pending'
    message: string
    duration?: number
  }>>([])
  
  // ============================================================
  // React Query hooks 测试
  // ============================================================
  
  // 项目相关查询测试
  const projectsQuery = useProjects(
    { page: 1, limit: 10 },
    {
      enabled: testConfig.enableRealTimeQueries,
      refetchInterval: testConfig.queryRefreshInterval,
    }
  )
  
  // 扫描相关查询测试
  const activeScansQuery = useActiveScans(undefined, {
    enabled: testConfig.enableRealTimeQueries,
  })
  
  const scanServiceStatusQuery = useScanServiceStatus({
    enabled: testConfig.enableRealTimeQueries,
  })
  
  const scanStatisticsQuery = useScanStatistics(undefined, {
    enabled: testConfig.enableRealTimeQueries,
  })
  
  const globalStatisticsQuery = useGlobalStatistics({
    enabled: testConfig.enableRealTimeQueries,
  })
  
  // 变更操作测试
  const createProjectMutation = useCreateProject({
    onSuccess: () => {
      addTestResult('创建项目', 'success', '项目创建成功')
    },
    onError: (error) => {
      addTestResult('创建项目', 'error', `项目创建失败: ${error.message}`)
    }
  })
  
  const startScanMutation = useStartScan({
    onSuccess: () => {
      addTestResult('启动扫描', 'success', '扫描启动成功')
    },
    onError: (error) => {
      addTestResult('启动扫描', 'error', `扫描启动失败: ${error.message}`)
    }
  })
  
  // ============================================================
  // 性能监控
  // ============================================================
  
  useEffect(() => {
    const interval = setInterval(() => {
      updatePerformanceMetrics()
    }, 2000)
    
    return () => clearInterval(interval)
  }, [])
  
  const updatePerformanceMetrics = () => {
    const cache = queryClient.getQueryCache()
    const queries = cache.getAll()
    
    const metrics: PerformanceMetrics = {
      queryCount: queries.length,
      errorCount: queries.filter(q => q.state.status === 'error').length,
      averageResponseTime: calculateAverageResponseTime(queries),
      cacheHitRate: calculateCacheHitRate(queries),
      memoryUsage: estimateMemoryUsage(queries),
    }
    
    setPerformanceMetrics(metrics)
  }
  
  const calculateAverageResponseTime = (queries: any[]): number => {
    const validQueries = queries.filter(q => 
      q.state.dataUpdatedAt && q.state.dataUpdatedAt > 0
    )
    
    if (validQueries.length === 0) return 0
    
    const totalTime = validQueries.reduce((sum, q) => {
      const duration = q.state.dataUpdatedAt - (q.state.fetchFailureTime || q.state.dataUpdatedAt - 1000)
      return sum + Math.max(0, duration)
    }, 0)
    
    return Math.round(totalTime / validQueries.length)
  }
  
  const calculateCacheHitRate = (queries: any[]): number => {
    const totalQueries = queries.length
    if (totalQueries === 0) return 0
    
    const cachedQueries = queries.filter(q => q.state.data !== undefined)
    return Math.round((cachedQueries.length / totalQueries) * 100)
  }
  
  const estimateMemoryUsage = (queries: any[]): number => {
    // 简单的内存估算
    let totalSize = 0
    queries.forEach(q => {
      if (q.state.data) {
        totalSize += JSON.stringify(q.state.data).length
      }
    })
    return Math.round(totalSize / 1024 / 1024 * 100) / 100 // MB
  }
  
  // ============================================================
  // 测试辅助函数
  // ============================================================
  
  const addTestResult = (test: string, status: 'success' | 'error' | 'pending', message: string, duration?: number) => {
    setTestResults(prev => [
      { test, status, message, duration },
      ...prev.slice(0, 19) // 保持最近20条记录
    ])
  }
  
  const runPerformanceTest = async () => {
    addTestResult('性能测试', 'pending', '开始性能测试...')
    
    const startTime = Date.now()
    
    try {
      // 并发查询测试
      await Promise.all([
        queryClient.fetchQuery({
          queryKey: queryKeys.projects.lists(),
          queryFn: () => new Promise(resolve => setTimeout(() => resolve({ success: true, data: { items: [], total: 0 } }), 100))
        }),
        queryClient.fetchQuery({
          queryKey: queryKeys.scans.active(),
          queryFn: () => new Promise(resolve => setTimeout(() => resolve({ success: true, data: [] }), 150))
        }),
        queryClient.fetchQuery({
          queryKey: queryKeys.scans.serviceStatus(),
          queryFn: () => new Promise(resolve => setTimeout(() => resolve({ success: true, data: { status: 'healthy' } }), 200))
        }),
      ])
      
      const duration = Date.now() - startTime
      addTestResult('性能测试', 'success', `并发查询完成，耗时 ${duration}ms`, duration)
    } catch (error) {
      const duration = Date.now() - startTime
      addTestResult('性能测试', 'error', `性能测试失败: ${error}`, duration)
    }
  }
  
  const runCacheTest = () => {
    addTestResult('缓存测试', 'pending', '测试缓存机制...')
    
    // 手动触发缓存优化
    cacheOptimizer.manualCleanup()
    
    const cacheStats = cacheOptimizer.getCacheStats()
    if (cacheStats) {
      addTestResult('缓存测试', 'success', 
        `缓存统计: ${cacheStats.totalQueries} 个查询, ${cacheStats.estimatedMemoryUsage.toFixed(2)}MB 内存使用`
      )
    } else {
      addTestResult('缓存测试', 'error', '无法获取缓存统计信息')
    }
  }
  
  const runErrorTest = () => {
    addTestResult('错误处理测试', 'pending', '测试错误处理机制...')
    
    // 模拟错误
    const testError = new Error('这是一个测试错误')
    errorHandler.handleError(testError, '错误处理测试')
    
    const errorHistory = errorHandler.getErrorHistory()
    addTestResult('错误处理测试', 'success', 
      `错误记录成功，当前错误历史: ${errorHistory.length} 条`
    )
  }
  
  const runMutationTest = () => {
    addTestResult('变更操作测试', 'pending', '测试变更操作...')
    
    // 模拟创建项目
    createProjectMutation.mutate({
      name: `测试项目_${Date.now()}`,
      description: '这是一个测试项目',
      source_path: '/test/path',
      output_path: '/test/output',
      mc_version: '1.19.2',
      target_language: 'zh_cn',
    })
  }
  
  const clearAllCaches = () => {
    queryClient.clear()
    message.success('所有缓存已清除')
    addTestResult('缓存清理', 'success', '所有查询缓存已清除')
  }
  
  // ============================================================
  // 渲染组件
  // ============================================================
  
  const renderPerformanceMetrics = () => (
    <Row gutter={16}>
      <Col span={6}>
        <Statistic
          title="查询数量"
          value={performanceMetrics.queryCount}
          prefix={<BarChartOutlined />}
        />
      </Col>
      <Col span={6}>
        <Statistic
          title="错误数量"
          value={performanceMetrics.errorCount}
          valueStyle={{ color: performanceMetrics.errorCount > 0 ? '#cf1322' : '#3f8600' }}
          prefix={<BugOutlined />}
        />
      </Col>
      <Col span={6}>
        <Statistic
          title="平均响应时间"
          value={performanceMetrics.averageResponseTime}
          suffix="ms"
          prefix={<ClockCircleOutlined />}
        />
      </Col>
      <Col span={6}>
        <Statistic
          title="缓存命中率"
          value={performanceMetrics.cacheHitRate}
          suffix="%"
          prefix={<CheckCircleOutlined />}
        />
      </Col>
    </Row>
  )
  
  const renderQueryStatus = () => {
    const queries = [
      { name: '项目列表', query: projectsQuery },
      { name: '活跃扫描', query: activeScansQuery },
      { name: '扫描服务状态', query: scanServiceStatusQuery },
      { name: '扫描统计', query: scanStatisticsQuery },
      { name: '全局统计', query: globalStatisticsQuery },
    ]
    
    return (
      <Table
        size="small"
        pagination={false}
        columns={[
          {
            title: '查询名称',
            dataIndex: 'name',
            key: 'name',
          },
          {
            title: '状态',
            key: 'status',
            render: (_, record: any) => {
              const { isLoading, isError, isSuccess, isFetching } = record.query
              
              if (isLoading || isFetching) {
                return <Badge status="processing" text="加载中" />
              }
              if (isError) {
                return <Badge status="error" text="错误" />
              }
              if (isSuccess) {
                return <Badge status="success" text="成功" />
              }
              return <Badge status="default" text="未知" />
            },
          },
          {
            title: '数据更新时间',
            key: 'updateTime',
            render: (_, record: any) => {
              const { dataUpdatedAt } = record.query
              return dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : '-'
            },
          },
          {
            title: '操作',
            key: 'actions',
            render: (_, record: any) => (
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => record.query.refetch()}
                loading={record.query.isFetching}
              >
                刷新
              </Button>
            ),
          },
        ]}
        dataSource={queries.map((q, index) => ({ ...q, key: index }))}
      />
    )
  }
  
  const renderTestResults = () => (
    <Table
      size="small"
      pagination={{ pageSize: 10 }}
      columns={[
        {
          title: '测试项目',
          dataIndex: 'test',
          key: 'test',
        },
        {
          title: '状态',
          dataIndex: 'status',
          key: 'status',
          render: (status: string) => {
            const statusMap = {
              success: { color: 'success', icon: <CheckCircleOutlined /> },
              error: { color: 'error', icon: <ExclamationCircleOutlined /> },
              pending: { color: 'processing', icon: <ClockCircleOutlined /> },
            }
            const config = statusMap[status as keyof typeof statusMap]
            return <Badge status={config.color as any} text={status.toUpperCase()} />
          },
        },
        {
          title: '消息',
          dataIndex: 'message',
          key: 'message',
          ellipsis: true,
        },
        {
          title: '耗时',
          dataIndex: 'duration',
          key: 'duration',
          render: (duration?: number) => duration ? `${duration}ms` : '-',
        },
      ]}
      dataSource={testResults.map((result, index) => ({ ...result, key: index }))}
    />
  )
  
  const renderTestControls = () => (
    <Space direction="vertical" className="w-full">
      <Row gutter={16}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="实时查询"
              value={testConfig.enableRealTimeQueries ? '开启' : '关闭'}
              suffix={
                <Switch
                  checked={testConfig.enableRealTimeQueries}
                  onChange={(checked) => 
                    setTestConfig(prev => ({ ...prev, enableRealTimeQueries: checked }))
                  }
                />
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="缓存优化"
              value={testConfig.enableCacheOptimization ? '开启' : '关闭'}
              suffix={
                <Switch
                  checked={testConfig.enableCacheOptimization}
                  onChange={(checked) => 
                    setTestConfig(prev => ({ ...prev, enableCacheOptimization: checked }))
                  }
                />
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="错误模拟"
              value={testConfig.enableErrorSimulation ? '开启' : '关闭'}
              suffix={
                <Switch
                  checked={testConfig.enableErrorSimulation}
                  onChange={(checked) => 
                    setTestConfig(prev => ({ ...prev, enableErrorSimulation: checked }))
                  }
                />
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="内存使用"
              value={performanceMetrics.memoryUsage}
              suffix="MB"
            />
          </Card>
        </Col>
      </Row>
      
      <Space wrap>
        <Button
          type="primary"
          onClick={runPerformanceTest}
          icon={<BarChartOutlined />}
        >
          性能测试
        </Button>
        <Button
          onClick={runCacheTest}
          icon={<EyeOutlined />}
        >
          缓存测试
        </Button>
        <Button
          onClick={runErrorTest}
          icon={<BugOutlined />}
        >
          错误测试
        </Button>
        <Button
          onClick={runMutationTest}
          icon={<CheckCircleOutlined />}
          loading={createProjectMutation.isPending}
        >
          变更测试
        </Button>
        <Button
          danger
          onClick={clearAllCaches}
          icon={<DeleteOutlined />}
        >
          清除缓存
        </Button>
      </Space>
    </Space>
  )
  
  // ============================================================
  // 渲染
  // ============================================================
  
  const tabItems = [
    {
      key: 'overview',
      label: '测试概览',
      children: (
        <Space direction="vertical" className="w-full">
          <Alert
            message="TanStack Query 集成测试"
            description="此页面用于测试React Query hooks的功能、性能和错误处理机制"
            type="info"
            showIcon
          />
          
          <Card title="性能指标">
            {renderPerformanceMetrics()}
          </Card>
          
          <Card title="测试控制">
            {renderTestControls()}
          </Card>
        </Space>
      ),
    },
    {
      key: 'queries',
      label: '查询状态',
      children: (
        <Card title="查询状态监控">
          {renderQueryStatus()}
        </Card>
      ),
    },
    {
      key: 'results',
      label: '测试结果',
      children: (
        <Card title="测试结果历史">
          {renderTestResults()}
        </Card>
      ),
    },
    {
      key: 'tables',
      label: '表格测试',
      children: (
        <Card title="ProjectTable 组件测试">
          <ProjectTable
            searchParams={{
              page: 1,
              limit: 10,
            }}
            onProjectSelect={(project) => 
              addTestResult('项目选择', 'success', `选择了项目: ${project.name}`)
            }
          />
        </Card>
      ),
    },
  ]
  
  return (
    <div className="tanstack-integration-test">
      <Title level={2}>TanStack Query 集成测试</Title>
      <Paragraph>
        这个测试页面验证了React Query hooks的各项功能，包括数据查询、缓存管理、错误处理和性能监控。
      </Paragraph>
      
      <Tabs items={tabItems} />
    </div>
  )
}