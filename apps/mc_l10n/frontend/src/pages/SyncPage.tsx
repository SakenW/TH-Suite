/**
 * 同步中心页面 - 基于v2.1架构的双向同步功能
 * 支持Trans-Hub官方SDK的完整同步流程
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Tabs,
  Table,
  Progress,
  Tag,
  Alert,
  Modal,
  Form,
  Select,
  Switch,
  Input,
  InputNumber,
  Row,
  Col,
  Statistic,
  Timeline,
  Badge,
  Tooltip,
  notification,
  Popconfirm,
  Divider,
  Empty
} from 'antd'
import {
  SyncOutlined,
  CloudUploadOutlined,
  CloudDownloadOutlined,
  SwapOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  HistoryOutlined,
  BarChartOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  EyeOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { syncApiService } from '../services/api/SyncApiService'
import type {
  SyncTask,
  SyncRequest,
  SyncRequestOptions,
  SyncHistory,
  SyncStatistics
} from '../services/api/SyncApiService'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography
const { TabPane } = Tabs
const { Option } = Select
const { TextArea } = Input

interface SyncPageState {
  // 任务管理
  activeTasks: SyncTask[]
  selectedTask: SyncTask | null
  taskLoading: boolean
  
  // 历史记录
  syncHistory: SyncHistory[]
  historyLoading: boolean
  historyPagination: {
    current: number
    pageSize: number
    total: number
  }
  
  // 统计信息
  statistics: SyncStatistics | null
  statisticsLoading: boolean
  
  // 服务状态
  serviceStatus: {
    status: 'healthy' | 'degraded' | 'unavailable'
    active_tasks: number
    queue_size: number
    worker_status: Record<string, string>
    last_heartbeat: string
  } | null
  
  // UI状态
  activeTab: string
  newSyncModalVisible: boolean
  taskDetailModalVisible: boolean
  autoRefresh: boolean
}

export const SyncPage: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  
  const [state, setState] = useState<SyncPageState>({
    activeTasks: [],
    selectedTask: null,
    taskLoading: false,
    syncHistory: [],
    historyLoading: false,
    historyPagination: {
      current: 1,
      pageSize: 10,
      total: 0
    },
    statistics: null,
    statisticsLoading: false,
    serviceStatus: null,
    activeTab: 'tasks',
    newSyncModalVisible: false,
    taskDetailModalVisible: false,
    autoRefresh: true
  })

  // 加载活跃任务
  const loadActiveTasks = useCallback(async () => {
    setState(prev => ({ ...prev, taskLoading: true }))
    
    try {
      const result = await syncApiService.getActiveTasks()
      if (result.success) {
        setState(prev => ({ ...prev, activeTasks: result.data || [] }))
      } else {
        notification.error({ 
          message: '加载同步任务失败', 
          description: result.error?.message 
        })
      }
    } catch (error) {
      notification.error({ 
        message: '加载同步任务失败', 
        description: String(error) 
      })
    } finally {
      setState(prev => ({ ...prev, taskLoading: false }))
    }
  }, [])

  // 加载同步历史
  const loadSyncHistory = useCallback(async (page: number = 1) => {
    setState(prev => ({ ...prev, historyLoading: true }))
    
    try {
      const limit = state.historyPagination.pageSize
      const offset = (page - 1) * limit
      
      const result = await syncApiService.getSyncHistory(undefined, limit, offset)
      if (result.success && result.data) {
        setState(prev => ({
          ...prev,
          syncHistory: result.data.history,
          historyPagination: {
            ...prev.historyPagination,
            current: page,
            total: result.data.total
          }
        }))
      } else {
        notification.error({ 
          message: '加载同步历史失败', 
          description: result.error?.message 
        })
      }
    } catch (error) {
      notification.error({ 
        message: '加载同步历史失败', 
        description: String(error) 
      })
    } finally {
      setState(prev => ({ ...prev, historyLoading: false }))
    }
  }, [state.historyPagination.pageSize])

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    setState(prev => ({ ...prev, statisticsLoading: true }))
    
    try {
      const result = await syncApiService.getSyncStatistics()
      if (result.success) {
        setState(prev => ({ ...prev, statistics: result.data }))
      } else {
        notification.error({ 
          message: '加载统计信息失败', 
          description: result.error?.message 
        })
      }
    } catch (error) {
      notification.error({ 
        message: '加载统计信息失败', 
        description: String(error) 
      })
    } finally {
      setState(prev => ({ ...prev, statisticsLoading: false }))
    }
  }, [])

  // 检查服务状态
  const checkServiceStatus = useCallback(async () => {
    try {
      const result = await syncApiService.checkSyncServiceStatus()
      if (result.success) {
        setState(prev => ({ ...prev, serviceStatus: result.data }))
      }
    } catch (error) {
      console.warn('同步服务状态检查失败:', error)
    }
  }, [])

  // 启动新同步任务
  const startSyncTask = useCallback(async (values: any) => {
    try {
      const syncRequest: SyncRequest = {
        project_id: values.project_id,
        sync_mode: values.sync_mode,
        options: {
          conflict_resolution: values.conflict_resolution,
          batch_size: values.batch_size,
          timeout_seconds: values.timeout_seconds,
          validate_before_sync: values.validate_before_sync,
          generate_backup: values.generate_backup,
          parallel_workers: values.parallel_workers,
          use_compression: values.use_compression
        }
      }

      const result = await syncApiService.startSync(syncRequest)
      if (result.success) {
        notification.success({ message: '同步任务已启动', description: `任务ID: ${result.data?.task_id}` })
        setState(prev => ({ ...prev, newSyncModalVisible: false }))
        form.resetFields()
        loadActiveTasks()
      } else {
        notification.error({ 
          message: '启动同步任务失败', 
          description: result.error?.message 
        })
      }
    } catch (error) {
      notification.error({ 
        message: '启动同步任务失败', 
        description: String(error) 
      })
    }
  }, [form, loadActiveTasks])

  // 任务操作
  const handleTaskAction = useCallback(async (
    action: 'pause' | 'resume' | 'cancel',
    taskId: string
  ) => {
    try {
      let result
      switch (action) {
        case 'pause':
          result = await syncApiService.pauseTask(taskId)
          break
        case 'resume':
          result = await syncApiService.resumeTask(taskId)
          break
        case 'cancel':
          result = await syncApiService.cancelTask(taskId, '用户手动取消')
          break
        default:
          return
      }

      if (result.success) {
        notification.success({ message: `任务${action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : '取消'}成功` })
        loadActiveTasks()
      } else {
        notification.error({ 
          message: `任务${action}失败`, 
          description: result.error?.message 
        })
      }
    } catch (error) {
      notification.error({ 
        message: `任务${action}失败`, 
        description: String(error) 
      })
    }
  }, [loadActiveTasks])

  // 查看任务详情
  const viewTaskDetail = useCallback(async (task: SyncTask) => {
    setState(prev => ({ 
      ...prev, 
      selectedTask: task, 
      taskDetailModalVisible: true 
    }))
  }, [])

  // 快速拉取翻译
  const handleQuickPull = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true }))
    try {
      const syncRequest: SyncRequest = {
        project_id: undefined, // 全项目拉取
        sync_mode: 'pull',
        options: {
          conflict_resolution: 'remote_wins',
          batch_size: 100,
          timeout_seconds: 300,
          validate_before_sync: true,
          generate_backup: true,
          parallel_workers: 4,
          use_compression: true
        }
      }

      const result = await syncApiService.startSync(syncRequest)
      if (result.success) {
        notification.success({ 
          message: '拉取任务已启动', 
          description: '正在从服务器拉取最新翻译，请稍候...'
        })
        loadActiveTasks()
      } else {
        notification.error({ 
          message: '拉取失败', 
          description: result.error?.message || '启动拉取任务失败'
        })
      }
    } catch (error) {
      notification.error({ 
        message: '拉取失败', 
        description: String(error) 
      })
    } finally {
      setState(prev => ({ ...prev, isLoading: false }))
    }
  }, [])

  // 快速推送修改
  const handleQuickPush = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true }))
    try {
      const syncRequest: SyncRequest = {
        project_id: undefined, // 全项目推送
        sync_mode: 'push',
        options: {
          conflict_resolution: 'local_wins',
          batch_size: 50,
          timeout_seconds: 600,
          validate_before_sync: true,
          generate_backup: true,
          parallel_workers: 2,
          use_compression: true
        }
      }

      const result = await syncApiService.startSync(syncRequest)
      if (result.success) {
        notification.success({ 
          message: '推送任务已启动', 
          description: '正在向服务器推送本地修改，请稍候...'
        })
        loadActiveTasks()
      } else {
        notification.error({ 
          message: '推送失败', 
          description: result.error?.message || '启动推送任务失败'
        })
      }
    } catch (error) {
      notification.error({ 
        message: '推送失败', 
        description: String(error) 
      })
    } finally {
      setState(prev => ({ ...prev, isLoading: false }))
    }
  }, [])

  // 初始化加载
  useEffect(() => {
    loadActiveTasks()
    loadSyncHistory()
    loadStatistics()
    checkServiceStatus()
  }, [])

  // 自动刷新
  useEffect(() => {
    if (!state.autoRefresh) return

    const interval = setInterval(() => {
      if (state.activeTab === 'tasks') {
        loadActiveTasks()
        checkServiceStatus()
      }
    }, 5000) // 每5秒刷新一次

    return () => clearInterval(interval)
  }, [state.autoRefresh, state.activeTab, loadActiveTasks, checkServiceStatus])

  // 任务表格列定义
  const taskColumns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      render: (id: string) => (
        <Text code className="text-xs">{id.substring(0, 8)}...</Text>
      )
    },
    {
      title: '同步模式',
      dataIndex: 'sync_mode',
      key: 'sync_mode',
      width: 100,
      render: (mode: string) => {
        const colors = {
          push: 'blue',
          pull: 'green',
          bidirectional: 'purple'
        }
        const icons = {
          push: <CloudUploadOutlined />,
          pull: <CloudDownloadOutlined />,
          bidirectional: <SwapOutlined />
        }
        return (
          <Tag color={colors[mode as keyof typeof colors]} icon={icons[mode as keyof typeof icons]}>
            {mode === 'push' ? '推送' : mode === 'pull' ? '拉取' : '双向'}
          </Tag>
        )
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors = {
          pending: 'default',
          initializing: 'processing',
          running: 'processing',
          completed: 'success',
          failed: 'error',
          cancelled: 'default',
          paused: 'warning'
        }
        return (
          <Badge 
            status={colors[status as keyof typeof colors] as any}
            text={status === 'pending' ? '等待中' : 
                  status === 'initializing' ? '初始化' :
                  status === 'running' ? '运行中' :
                  status === 'completed' ? '已完成' :
                  status === 'failed' ? '失败' :
                  status === 'cancelled' ? '已取消' : '已暂停'}
          />
        )
      }
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number, record: SyncTask) => (
        <div>
          <Progress percent={progress} />
          <Text type="secondary" className="text-xs">
            {record.processed_items}/{record.total_items}
          </Text>
        </div>
      )
    },
    {
      title: '当前阶段',
      dataIndex: 'current_phase',
      key: 'current_phase',
      width: 120,
      render: (phase: string) => phase || '-'
    },
    {
      title: '已用时间',
      dataIndex: 'elapsed_seconds',
      key: 'elapsed_seconds',
      width: 100,
      render: (elapsed: number) => elapsed ? `${Math.round(elapsed)}s` : '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: SyncTask) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
             
              onClick={() => viewTaskDetail(record)}
            />
          </Tooltip>
          {record.status === 'running' && (
            <Tooltip title="暂停">
              <Button 
                type="text" 
                icon={<PauseCircleOutlined />} 
               
                onClick={() => handleTaskAction('pause', record.task_id)}
              />
            </Tooltip>
          )}
          {record.status === 'paused' && (
            <Tooltip title="恢复">
              <Button 
                type="text" 
                icon={<PlayCircleOutlined />} 
               
                onClick={() => handleTaskAction('resume', record.task_id)}
              />
            </Tooltip>
          )}
          {['running', 'paused', 'pending'].includes(record.status) && (
            <Popconfirm
              title="确定要取消这个同步任务吗？"
              onConfirm={() => handleTaskAction('cancel', record.task_id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="取消">
                <Button 
                  type="text" 
                  icon={<StopOutlined />} 
                 
                  danger
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  // 历史记录表格列定义
  const historyColumns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      render: (id: string) => (
        <Text code className="text-xs">{id.substring(0, 8)}...</Text>
      )
    },
    {
      title: '同步模式',
      dataIndex: 'sync_mode',
      key: 'sync_mode',
      width: 100
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Badge 
          status={status === 'completed' ? 'success' : 'error'}
          text={status === 'completed' ? '成功' : '失败'}
        />
      )
    },
    {
      title: '处理项目数',
      dataIndex: 'items_processed',
      key: 'items_processed',
      width: 120,
      render: (count: number) => count.toLocaleString()
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 100,
      render: (rate: number) => `${(rate * 100).toFixed(1)}%`
    },
    {
      title: '持续时间',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (duration: number) => duration ? `${Math.round(duration / 1000)}s` : '-'
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss')
    }
  ]

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">🔄 同步中心</Title>
        <Space>
          <Button 
            type="primary" 
            icon={<CloudDownloadOutlined />}
            onClick={handleQuickPull}
            loading={state.isLoading}
           
          >
            拉取最新翻译
          </Button>
          <Button 
            icon={<CloudUploadOutlined />}
            onClick={handleQuickPush}
            loading={state.isLoading}
          >
            推送本地修改
          </Button>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => {
              loadActiveTasks()
              loadSyncHistory()
              checkServiceStatus()
            }}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* 服务状态警告 */}
      {state.serviceStatus?.status !== 'healthy' && (
        <Alert
          message="同步服务状态异常"
          description={`当前状态: ${state.serviceStatus?.status}, 活跃任务: ${state.serviceStatus?.active_tasks}, 队列大小: ${state.serviceStatus?.queue_size}`}
          type="warning"
          showIcon
          className="mb-4"
        />
      )}

      {/* 快速状态信息 */}
      <Row gutter={16} className="mb-6">
        <Col span={8}>
          <Card className="text-center">
            <div className="text-3xl mb-2">
              {state.activeTasks.length > 0 ? '🔄' : '✅'}
            </div>
            <Text strong>
              {state.activeTasks.length > 0 ? `${state.activeTasks.length} 个任务运行中` : '所有任务已完成'}
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card className="text-center">
            <div className="text-3xl mb-2">
              {state.serviceStatus?.status === 'healthy' ? '🟢' : '🟠'}
            </div>
            <Text strong>
              服务状态: {state.serviceStatus?.status === 'healthy' ? '正常' : '异常'}
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card className="text-center">
            <div className="text-3xl mb-2">📈</div>
            <Text strong>
              {state.statistics?.last_sync_at 
                ? `上次同步: ${dayjs(state.statistics.last_sync_at).fromNow()}`
                : '尚未同步'
              }
            </Text>
          </Card>
        </Col>
      </Row>

      {/* 主要内容区域 */}
      <Card>
        <Tabs 
          activeKey={state.activeTab} 
          onChange={(key) => setState(prev => ({ ...prev, activeTab: key }))}
        >
          <TabPane tab={`活跃任务 (${state.activeTasks.length})`} key="tasks">
            <Table
              columns={taskColumns}
              dataSource={state.activeTasks}
              rowKey="task_id"
              loading={state.taskLoading}
             
              pagination={false}
              locale={{
                emptyText: (
                  <Empty
                    image={<SyncOutlined className="text-6xl text-gray-300" />}
                    description={
                      <div>
                        <Text type="secondary">暂无活跃的同步任务</Text>
                        <br />
                        <Text type="secondary" className="text-sm">
                          点击上方 "拉取最新翻译" 或 "推送本地修改" 开始同步
                        </Text>
                      </div>
                    }
                  />
                )
              }}
            />
          </TabPane>
          
          <TabPane tab="同步历史" key="history">
            <Table
              columns={historyColumns}
              dataSource={state.syncHistory}
              rowKey="history_id"
              loading={state.historyLoading}
             
              pagination={{
                current: state.historyPagination.current,
                pageSize: state.historyPagination.pageSize,
                total: state.historyPagination.total,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 条`,
                onChange: (page) => loadSyncHistory(page)
              }}
            />
          </TabPane>
          
          <TabPane tab="统计报告" key="statistics">
            {state.statistics ? (
              <div>
                <Row gutter={16} className="mb-4">
                  <Col span={12}>
                    <Card title="同步概览">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span>总同步次数:</span>
                          <strong>{state.statistics.total_syncs}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span>成功次数:</span>
                          <span className="text-green-600">{state.statistics.successful_syncs}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>失败次数:</span>
                          <span className="text-red-600">{state.statistics.failed_syncs}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>平均处理项目:</span>
                          <span>{state.statistics.average_items_per_sync.toFixed(1)}</span>
                        </div>
                      </div>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="常见错误">
                      {state.statistics.common_errors.length > 0 ? (
                        <div className="space-y-2">
                          {state.statistics.common_errors.slice(0, 5).map((error, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span className="truncate mr-2">{error.error_type}</span>
                              <span className="text-red-600">{error.count}次</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Text type="secondary">暂无错误记录</Text>
                      )}
                    </Card>
                  </Col>
                </Row>
              </div>
            ) : (
              <Empty description="暂无统计数据" />
            )}
          </TabPane>
        </Tabs>
      </Card>

      {/* 新建同步任务模态框 */}
      <Modal
        title="新建同步任务"
        open={state.newSyncModalVisible}
        onCancel={() => {
          setState(prev => ({ ...prev, newSyncModalVisible: false }))
          form.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={startSyncTask}
          initialValues={{
            sync_mode: 'bidirectional',
            conflict_resolution: 'manual',
            batch_size: 100,
            timeout_seconds: 300,
            validate_before_sync: true,
            generate_backup: true,
            parallel_workers: 4,
            use_compression: true
          }}
        >
          <Form.Item
            name="sync_mode"
            label="同步模式"
            rules={[{ required: true, message: '请选择同步模式' }]}
          >
            <Select>
              <Option value="push">推送到远程 (Push)</Option>
              <Option value="pull">从远程拉取 (Pull)</Option>
              <Option value="bidirectional">双向同步 (Bidirectional)</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="conflict_resolution"
            label="冲突解决策略"
            rules={[{ required: true, message: '请选择冲突解决策略' }]}
          >
            <Select>
              <Option value="local_wins">本地优先</Option>
              <Option value="remote_wins">远程优先</Option>
              <Option value="manual">手动解决</Option>
              <Option value="interactive">交互式解决</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="batch_size"
                label="批处理大小"
              >
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="timeout_seconds"
                label="超时时间(秒)"
              >
                <InputNumber min={30} max={3600} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="parallel_workers"
                label="并行工作线程"
              >
                <InputNumber min={1} max={16} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <div className="pt-8">
                <Form.Item name="use_compression" valuePropName="checked">
                  <Switch checkedChildren="启用压缩" unCheckedChildren="禁用压缩" />
                </Form.Item>
              </div>
            </Col>
          </Row>

          <Form.Item name="validate_before_sync" valuePropName="checked">
            <Switch checkedChildren="同步前验证" unCheckedChildren="跳过验证" />
          </Form.Item>

          <Form.Item name="generate_backup" valuePropName="checked">
            <Switch checkedChildren="生成备份" unCheckedChildren="不备份" />
          </Form.Item>

          <Divider />

          <div className="flex justify-end space-x-2">
            <Button 
              onClick={() => {
                setState(prev => ({ ...prev, newSyncModalVisible: false }))
                form.resetFields()
              }}
            >
              取消
            </Button>
            <Button type="primary" htmlType="submit">
              启动同步
            </Button>
          </div>
        </Form>
      </Modal>

      {/* 任务详情模态框 */}
      <Modal
        title={`任务详情 - ${state.selectedTask?.task_id?.substring(0, 8)}`}
        open={state.taskDetailModalVisible}
        onCancel={() => setState(prev => ({ ...prev, taskDetailModalVisible: false, selectedTask: null }))}
        footer={[
          <Button key="close" onClick={() => setState(prev => ({ ...prev, taskDetailModalVisible: false }))}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {state.selectedTask && (
          <div>
            <Row gutter={16} className="mb-4">
              <Col span={12}>
                <Card title="基本信息">
                  <div className="space-y-2 text-sm">
                    <div><strong>任务ID:</strong> {state.selectedTask.task_id}</div>
                    <div><strong>同步模式:</strong> {state.selectedTask.sync_mode}</div>
                    <div><strong>状态:</strong> {state.selectedTask.status}</div>
                    <div><strong>优先级:</strong> {state.selectedTask.priority}</div>
                    <div><strong>当前阶段:</strong> {state.selectedTask.current_phase || '-'}</div>
                    <div><strong>当前操作:</strong> {state.selectedTask.current_operation || '-'}</div>
                  </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="进度统计">
                  <div className="space-y-2 text-sm">
                    <div><strong>总项目数:</strong> {state.selectedTask.total_items}</div>
                    <div><strong>已处理:</strong> {state.selectedTask.processed_items}</div>
                    <div><strong>失败:</strong> {state.selectedTask.failed_items}</div>
                    <div><strong>跳过:</strong> {state.selectedTask.skipped_items}</div>
                    <div><strong>处理速度:</strong> {state.selectedTask.items_per_second?.toFixed(1) || 0} items/s</div>
                  </div>
                </Card>
              </Col>
            </Row>

            <Card title="时间信息" className="mb-4">
              <Timeline>
                <Timeline.Item color="blue">
                  <strong>创建时间:</strong> {dayjs(state.selectedTask.created_at).format('YYYY-MM-DD HH:mm:ss')}
                </Timeline.Item>
                {state.selectedTask.started_at && (
                  <Timeline.Item color="green">
                    <strong>开始时间:</strong> {dayjs(state.selectedTask.started_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Timeline.Item>
                )}
                {state.selectedTask.completed_at && (
                  <Timeline.Item color="gray">
                    <strong>完成时间:</strong> {dayjs(state.selectedTask.completed_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Timeline.Item>
                )}
                {state.selectedTask.estimated_completion && (
                  <Timeline.Item color="orange">
                    <strong>预计完成:</strong> {dayjs(state.selectedTask.estimated_completion).format('YYYY-MM-DD HH:mm:ss')}
                  </Timeline.Item>
                )}
              </Timeline>
            </Card>

            {/* 错误和警告 */}
            {(state.selectedTask.error || state.selectedTask.warnings.length > 0) && (
              <Card title="错误和警告">
                {state.selectedTask.error && (
                  <Alert
                    message="任务错误"
                    description={state.selectedTask.error}
                    type="error"
                    showIcon
                    className="mb-2"
                  />
                )}
                {state.selectedTask.warnings.map((warning, index) => (
                  <Alert
                    key={index}
                    message={`警告 ${index + 1}`}
                    description={warning}
                    type="warning"
                    showIcon
                    className="mb-2"
                  />
                ))}
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default SyncPage