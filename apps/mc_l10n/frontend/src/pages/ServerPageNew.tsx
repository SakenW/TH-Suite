/**
 * 服务器状态页面 - 监控后端服务、系统资源和实时状态
 * 支持服务重启、系统监控和日志查看
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Progress,
  Alert,
  Table,
  Tag,
  Badge,
  Timeline,
  Tabs,
  List,
  Tooltip,
  notification,
  Modal,
  Popconfirm,
  Switch,
  Select,
  Input,
  Divider,
  Empty
} from 'antd'
import {
  CloudServerOutlined,
  ReloadOutlined,
  StopOutlined,
  PlayCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  DownloadOutlined,
  DeleteOutlined,
  SettingOutlined,
  BugOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  HddOutlined,
  WifiOutlined,
  ClockCircleOutlined,
  HeartOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text, Paragraph } = Typography
const { TabPane } = Tabs
const { Option } = Select
const { Search } = Input

// 服务器状态相关类型定义
interface ServerStatus {
  status: 'healthy' | 'degraded' | 'unavailable'
  uptime_seconds: number
  version: string
  last_heartbeat: string
  
  // 系统资源
  system_resources: {
    cpu_usage_percent: number
    memory_usage_mb: number
    memory_total_mb: number
    disk_usage_mb: number
    disk_total_mb: number
    active_connections: number
  }
  
  // 服务状态
  services: {
    database: 'healthy' | 'degraded' | 'unavailable'
    task_queue: 'healthy' | 'degraded' | 'unavailable'
    file_system: 'healthy' | 'degraded' | 'unavailable'
    trans_hub_sdk: 'available' | 'unavailable'
  }
  
  // 性能指标
  performance_metrics?: {
    requests_per_second: number
    average_response_time_ms: number
    error_rate_percent: number
    active_tasks: number
    queue_size: number
  }
}

interface LogEntry {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  context?: Record<string, any>
  source?: string
}

interface ServiceInfo {
  name: string
  status: 'running' | 'stopped' | 'error'
  port?: number
  version?: string
  last_restart?: string
  memory_usage_mb?: number
  cpu_usage_percent?: number
}

interface SystemAlert {
  id: string
  type: 'warning' | 'error' | 'info'
  title: string
  message: string
  timestamp: string
  resolved: boolean
  source: string
}

interface ServerPageState {
  // 服务器状态
  serverStatus: ServerStatus | null
  statusLoading: boolean
  
  // 系统日志
  logs: LogEntry[]
  logsLoading: boolean
  logLevel: string
  logSource: string
  
  // 服务信息
  services: ServiceInfo[]
  servicesLoading: boolean
  
  // 系统警告
  alerts: SystemAlert[]
  alertsLoading: boolean
  
  // UI状态
  activeTab: string
  autoRefresh: boolean
  logDetailModalVisible: boolean
  selectedLog: LogEntry | null
}

export const ServerPage: React.FC = () => {
  const navigate = useNavigate()
  
  const [state, setState] = useState<ServerPageState>({
    serverStatus: null,
    statusLoading: false,
    logs: [],
    logsLoading: false,
    logLevel: 'all',
    logSource: 'all',
    services: [],
    servicesLoading: false,
    alerts: [],
    alertsLoading: false,
    activeTab: 'overview',
    autoRefresh: true,
    logDetailModalVisible: false,
    selectedLog: null
  })

  // 加载服务器状态
  const loadServerStatus = useCallback(async () => {
    setState(prev => ({ ...prev, statusLoading: true }))
    
    try {
      // 模拟 API 调用
      const mockStatus: ServerStatus = {
        status: 'healthy',
        uptime_seconds: 86400 * 3 + 7200, // 3天3.2小时
        version: 'v2.1.0',
        last_heartbeat: new Date().toISOString(),
        system_resources: {
          cpu_usage_percent: 35.2,
          memory_usage_mb: 1024,
          memory_total_mb: 4096,
          disk_usage_mb: 15360,
          disk_total_mb: 51200,
          active_connections: 12
        },
        services: {
          database: 'healthy',
          task_queue: 'healthy',
          file_system: 'healthy',
          trans_hub_sdk: 'available'
        },
        performance_metrics: {
          requests_per_second: 24.5,
          average_response_time_ms: 185,
          error_rate_percent: 0.12,
          active_tasks: 3,
          queue_size: 8
        }
      }
      
      // 模拟延迟
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          serverStatus: mockStatus, 
          statusLoading: false 
        }))
      }, 500)
    } catch (error) {
      notification.error({ 
        message: '加载服务器状态失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, statusLoading: false }))
    }
  }, [])

  // 加载系统日志
  const loadSystemLogs = useCallback(async (level?: string, source?: string) => {
    setState(prev => ({ ...prev, logsLoading: true }))
    
    try {
      // 模拟日志数据
      const mockLogs: LogEntry[] = [
        {
          timestamp: new Date(Date.now() - 60000).toISOString(),
          level: 'info',
          message: '同步任务已完成',
          context: { task_id: 'sync_001', items_processed: 150 },
          source: 'sync_service'
        },
        {
          timestamp: new Date(Date.now() - 300000).toISOString(),
          level: 'warning',
          message: '数据库连接池接近上限',
          context: { pool_size: 18, max_size: 20 },
          source: 'database'
        },
        {
          timestamp: new Date(Date.now() - 600000).toISOString(),
          level: 'error',
          message: '文件解析失败',
          context: { file_path: '/mod/example.jar', error: 'corrupted_file' },
          source: 'scan_service'
        },
        {
          timestamp: new Date(Date.now() - 900000).toISOString(),
          level: 'info',
          message: '新的扫描任务已启动',
          context: { scan_id: 'scan_002', directory: '/minecraft/mods' },
          source: 'scan_service'
        }
      ]
      
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          logs: mockLogs, 
          logsLoading: false 
        }))
      }, 300)
    } catch (error) {
      notification.error({ 
        message: '加载系统日志失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, logsLoading: false }))
    }
  }, [])

  // 加载服务信息
  const loadServices = useCallback(async () => {
    setState(prev => ({ ...prev, servicesLoading: true }))
    
    try {
      const mockServices: ServiceInfo[] = [
        {
          name: 'FastAPI 主服务',
          status: 'running',
          port: 18000,
          version: '0.104.1',
          last_restart: new Date(Date.now() - 86400000 * 3).toISOString(),
          memory_usage_mb: 256,
          cpu_usage_percent: 12.5
        },
        {
          name: '数据库服务',
          status: 'running',
          port: 5432,
          version: 'SQLite 3.42',
          memory_usage_mb: 128,
          cpu_usage_percent: 3.2
        },
        {
          name: '任务队列处理器',
          status: 'running',
          memory_usage_mb: 64,
          cpu_usage_percent: 8.7
        },
        {
          name: 'Trans-Hub SDK',
          status: 'running',
          version: '2.1.0',
          memory_usage_mb: 32,
          cpu_usage_percent: 1.2
        }
      ]
      
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          services: mockServices, 
          servicesLoading: false 
        }))
      }, 400)
    } catch (error) {
      notification.error({ 
        message: '加载服务信息失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, servicesLoading: false }))
    }
  }, [])

  // 加载系统警告
  const loadAlerts = useCallback(async () => {
    setState(prev => ({ ...prev, alertsLoading: true }))
    
    try {
      const mockAlerts: SystemAlert[] = [
        {
          id: 'alert_001',
          type: 'warning',
          title: '内存使用率较高',
          message: '系统内存使用率达到 75%，建议监控内存泄漏',
          timestamp: new Date(Date.now() - 1800000).toISOString(),
          resolved: false,
          source: 'system_monitor'
        },
        {
          id: 'alert_002',
          type: 'info',
          title: '系统更新可用',
          message: 'TH-Suite v2.1.1 已发布，包含性能优化和错误修复',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          resolved: false,
          source: 'update_service'
        }
      ]
      
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          alerts: mockAlerts, 
          alertsLoading: false 
        }))
      }, 200)
    } catch (error) {
      notification.error({ 
        message: '加载系统警告失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, alertsLoading: false }))
    }
  }, [])

  // 重启服务
  const restartService = useCallback(async (serviceName: string) => {
    try {
      notification.info({ message: `正在重启 ${serviceName}...` })
      // 这里将调用真实的API
      setTimeout(() => {
        notification.success({ message: `${serviceName} 重启成功` })
        loadServices()
      }, 2000)
    } catch (error) {
      notification.error({ 
        message: '重启服务失败', 
        description: String(error) 
      })
    }
  }, [loadServices])

  // 解决警告
  const resolveAlert = useCallback(async (alertId: string) => {
    try {
      setState(prev => ({
        ...prev,
        alerts: prev.alerts.map(alert => 
          alert.id === alertId ? { ...alert, resolved: true } : alert
        )
      }))
      notification.success({ message: '警告已标记为已解决' })
    } catch (error) {
      notification.error({ 
        message: '解决警告失败', 
        description: String(error) 
      })
    }
  }, [])

  // 查看日志详情
  const viewLogDetail = useCallback((log: LogEntry) => {
    setState(prev => ({ 
      ...prev, 
      selectedLog: log, 
      logDetailModalVisible: true 
    }))
  }, [])

  // 初始化加载
  useEffect(() => {
    loadServerStatus()
    loadSystemLogs()
    loadServices()
    loadAlerts()
  }, [])

  // 自动刷新
  useEffect(() => {
    if (!state.autoRefresh) return

    const interval = setInterval(() => {
      loadServerStatus()
      if (state.activeTab === 'logs') {
        loadSystemLogs(state.logLevel, state.logSource)
      }
    }, 10000) // 每10秒刷新一次

    return () => clearInterval(interval)
  }, [state.autoRefresh, state.activeTab, state.logLevel, state.logSource, loadServerStatus, loadSystemLogs])

  // 服务表格列定义
  const serviceColumns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors = {
          running: 'success',
          stopped: 'default',
          error: 'error'
        }
        const labels = {
          running: '运行中',
          stopped: '已停止',
          error: '错误'
        }
        return (
          <Badge 
            status={colors[status as keyof typeof colors] as any}
            text={labels[status as keyof typeof labels] || status}
          />
        )
      }
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 80,
      render: (port: number) => port || '-'
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (version: string) => version || '-'
    },
    {
      title: 'CPU',
      dataIndex: 'cpu_usage_percent',
      key: 'cpu_usage_percent',
      width: 80,
      render: (usage: number) => usage ? `${usage.toFixed(1)}%` : '-'
    },
    {
      title: '内存',
      dataIndex: 'memory_usage_mb',
      key: 'memory_usage_mb',
      width: 80,
      render: (usage: number) => usage ? `${usage}MB` : '-'
    },
    {
      title: '最后重启',
      dataIndex: 'last_restart',
      key: 'last_restart',
      width: 120,
      render: (date: string) => date ? dayjs(date).fromNow() : '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, record: ServiceInfo) => (
        <Space>
          {record.status === 'running' && (
            <Popconfirm
              title={`确定要重启 ${record.name} 吗？`}
              onConfirm={() => restartService(record.name)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="重启服务">
                <Button type="text" icon={<ReloadOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  // 日志表格列定义
  const logColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp: string) => dayjs(timestamp).format('MM-DD HH:mm:ss')
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level: string) => {
        const colors = {
          debug: 'default',
          info: 'blue',
          warning: 'orange',
          error: 'red'
        }
        return <Tag color={colors[level as keyof typeof colors]}>{level.toUpperCase()}</Tag>
      }
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 120,
      render: (source: string) => source || '-'
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      render: (message: string) => (
        <Text ellipsis={{ tooltip: message }} className="max-w-md">
          {message}
        </Text>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record: LogEntry) => (
        <Tooltip title="查看详情">
          <Button 
            type="text" 
            icon={<EyeOutlined />} 
           
            onClick={() => viewLogDetail(record)}
          />
        </Tooltip>
      )
    }
  ]

  // 获取状态指示器颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#52c41a'
      case 'degraded': return '#faad14'
      case 'unavailable': return '#f5222d'
      default: return '#d9d9d9'
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">💻 服务器状态</Title>
        <Space>
          <Switch
            checked={state.autoRefresh}
            onChange={(checked) => setState(prev => ({ ...prev, autoRefresh: checked }))}
            checkedChildren="自动刷新"
            unCheckedChildren="手动刷新"
          />
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => {
              loadServerStatus()
              loadSystemLogs()
              loadServices()
              loadAlerts()
            }}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* 系统警告 */}
      {state.alerts.filter(alert => !alert.resolved).length > 0 && (
        <div className="mb-4">
          {state.alerts.filter(alert => !alert.resolved).map(alert => (
            <Alert
              key={alert.id}
              message={alert.title}
              description={alert.message}
              type={alert.type}
              showIcon
              closable
              onClose={() => resolveAlert(alert.id)}
              className="mb-2"
            />
          ))}
        </div>
      )}

      {/* 概览信息 */}
      {state.serverStatus && (
        <div className="mb-6">
          {/* 系统状态 */}
          <Row gutter={16} className="mb-4">
            <Col span={6}>
              <Card>
                <Statistic
                  title="系统状态"
                  value={state.serverStatus.status === 'healthy' ? '健康' : state.serverStatus.status === 'degraded' ? '降级' : '不可用'}
                  prefix={<HeartOutlined style={{ color: getStatusColor(state.serverStatus.status) }} />}
                  valueStyle={{ color: getStatusColor(state.serverStatus.status) }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="运行时间"
                  value={Math.floor(state.serverStatus.uptime_seconds / 86400)}
                  suffix="天"
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="版本"
                  value={state.serverStatus.version}
                  prefix={<InfoCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="活跃连接"
                  value={state.serverStatus.system_resources.active_connections}
                  prefix={<WifiOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* 系统资源 */}
          <Row gutter={16} className="mb-4">
            <Col span={6}>
              <Card title="CPU 使用率">
                <Progress 
                  percent={state.serverStatus.system_resources.cpu_usage_percent} 
                  status={state.serverStatus.system_resources.cpu_usage_percent > 80 ? 'exception' : 'normal'}
                  format={percent => `${percent}%`}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card title="内存使用">
                <Progress 
                  percent={(state.serverStatus.system_resources.memory_usage_mb / state.serverStatus.system_resources.memory_total_mb) * 100} 
                  status={(state.serverStatus.system_resources.memory_usage_mb / state.serverStatus.system_resources.memory_total_mb) > 0.8 ? 'exception' : 'normal'}
                  format={() => `${state.serverStatus?.system_resources.memory_usage_mb}MB / ${state.serverStatus?.system_resources.memory_total_mb}MB`}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card title="磁盘使用">
                <Progress 
                  percent={(state.serverStatus.system_resources.disk_usage_mb / state.serverStatus.system_resources.disk_total_mb) * 100} 
                  status={(state.serverStatus.system_resources.disk_usage_mb / state.serverStatus.system_resources.disk_total_mb) > 0.9 ? 'exception' : 'normal'}
                  format={() => `${(state.serverStatus?.system_resources.disk_usage_mb / 1024).toFixed(1)}GB / ${(state.serverStatus?.system_resources.disk_total_mb / 1024).toFixed(1)}GB`}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card title="性能指标">
                <div className="space-y-1 text-sm">
                  <div>RPS: {state.serverStatus.performance_metrics?.requests_per_second.toFixed(1)}</div>
                  <div>RT: {state.serverStatus.performance_metrics?.average_response_time_ms}ms</div>
                  <div>错误率: {state.serverStatus.performance_metrics?.error_rate_percent}%</div>
                  <div>任务: {state.serverStatus.performance_metrics?.active_tasks}</div>
                </div>
              </Card>
            </Col>
          </Row>

          {/* 服务状态 */}
          <Card title="服务状态" className="mb-4">
            <Row gutter={16}>
              {Object.entries(state.serverStatus.services).map(([service, status]) => {
                const serviceLabels = {
                  database: '数据库',
                  task_queue: '任务队列',
                  file_system: '文件系统',
                  trans_hub_sdk: 'Trans-Hub SDK'
                }
                const statusLabels = {
                  healthy: '健康',
                  degraded: '降级',
                  unavailable: '不可用',
                  available: '可用'
                }
                return (
                  <Col span={6} key={service}>
                    <div className="text-center p-2">
                      <Badge 
                        status={status === 'healthy' || status === 'available' ? 'success' : status === 'degraded' ? 'warning' : 'error'}
                        text={serviceLabels[service as keyof typeof serviceLabels]}
                      />
                      <div className="text-xs text-gray-500 mt-1">
                        {statusLabels[status as keyof typeof statusLabels] || status}
                      </div>
                    </div>
                  </Col>
                )
              })}
            </Row>
          </Card>
        </div>
      )}

      {/* 主要内容区域 */}
      <Card>
        <Tabs 
          activeKey={state.activeTab} 
          onChange={(key) => setState(prev => ({ ...prev, activeTab: key }))}
        >
          <TabPane tab="服务管理" key="services">
            <Table
              columns={serviceColumns}
              dataSource={state.services}
              rowKey="name"
              loading={state.servicesLoading}
             
              pagination={false}
            />
          </TabPane>
          
          <TabPane tab="系统日志" key="logs">
            <div className="mb-4 flex justify-between items-center">
              <Space>
                <Select
                  value={state.logLevel}
                  onChange={(value) => {
                    setState(prev => ({ ...prev, logLevel: value }))
                    loadSystemLogs(value, state.logSource)
                  }}
                  style={{ width: 120 }}
                >
                  <Option value="all">所有级别</Option>
                  <Option value="error">错误</Option>
                  <Option value="warning">警告</Option>
                  <Option value="info">信息</Option>
                  <Option value="debug">调试</Option>
                </Select>
                
                <Select
                  value={state.logSource}
                  onChange={(value) => {
                    setState(prev => ({ ...prev, logSource: value }))
                    loadSystemLogs(state.logLevel, value)
                  }}
                  style={{ width: 150 }}
                >
                  <Option value="all">所有源</Option>
                  <Option value="scan_service">扫描服务</Option>
                  <Option value="sync_service">同步服务</Option>
                  <Option value="database">数据库</Option>
                  <Option value="system_monitor">系统监控</Option>
                </Select>
              </Space>
              
              <Button 
                icon={<DownloadOutlined />}
                onClick={() => {
                  notification.info({ message: '正在准备下载日志文件...' })
                }}
              >
                导出日志
              </Button>
            </div>
            
            <Table
              columns={logColumns}
              dataSource={state.logs}
              rowKey={(record, index) => `${record.timestamp}-${index}`}
              loading={state.logsLoading}
             
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 条`,
              }}
            />
          </TabPane>
          
          <TabPane tab={`系统警告 (${state.alerts.filter(alert => !alert.resolved).length})`} key="alerts">
            <List
              dataSource={state.alerts}
              loading={state.alertsLoading}
              renderItem={(alert) => (
                <List.Item
                  actions={[
                    !alert.resolved && (
                      <Button 
                        key="resolve"
                        type="link" 
                       
                        onClick={() => resolveAlert(alert.id)}
                      >
                        标记为已解决
                      </Button>
                    )
                  ].filter(Boolean)}
                  className={alert.resolved ? 'opacity-50' : ''}
                >
                  <List.Item.Meta
                    avatar={
                      alert.type === 'error' ? <ExclamationCircleOutlined className="text-red-500" /> :
                      alert.type === 'warning' ? <WarningOutlined className="text-orange-500" /> :
                      <InfoCircleOutlined className="text-blue-500" />
                    }
                    title={
                      <div className="flex items-center space-x-2">
                        <span>{alert.title}</span>
                        {alert.resolved && <Tag color="green">已解决</Tag>}
                      </div>
                    }
                    description={
                      <div>
                        <div>{alert.message}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {dayjs(alert.timestamp).fromNow()} · {alert.source}
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
              locale={{
                emptyText: (
                  <Empty
                    image={<CheckCircleOutlined className="text-6xl text-green-300" />}
                    description="暂无系统警告"
                  />
                )
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 日志详情模态框 */}
      <Modal
        title="日志详情"
        open={state.logDetailModalVisible}
        onCancel={() => setState(prev => ({ ...prev, logDetailModalVisible: false, selectedLog: null }))}
        footer={[
          <Button key="close" onClick={() => setState(prev => ({ ...prev, logDetailModalVisible: false }))}>
            关闭
          </Button>
        ]}
        width={600}
      >
        {state.selectedLog && (
          <div className="space-y-4">
            <div>
              <Text strong>时间:</Text> {dayjs(state.selectedLog.timestamp).format('YYYY-MM-DD HH:mm:ss')}
            </div>
            <div>
              <Text strong>级别:</Text> 
              <Tag color={{
                debug: 'default',
                info: 'blue', 
                warning: 'orange',
                error: 'red'
              }[state.selectedLog.level]} className="ml-2">
                {state.selectedLog.level.toUpperCase()}
              </Tag>
            </div>
            {state.selectedLog.source && (
              <div>
                <Text strong>来源:</Text> {state.selectedLog.source}
              </div>
            )}
            <div>
              <Text strong>消息:</Text>
              <Paragraph className="mt-2 p-3 bg-gray-50 border rounded">
                {state.selectedLog.message}
              </Paragraph>
            </div>
            {state.selectedLog.context && Object.keys(state.selectedLog.context).length > 0 && (
              <div>
                <Text strong>上下文信息:</Text>
                <pre className="mt-2 p-3 bg-gray-50 border rounded text-sm overflow-auto">
                  {JSON.stringify(state.selectedLog.context, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ServerPage