/**
 * 构建中心页面 - Minecraft 整合包和MOD的构建和导出功能
 * 支持JAR修改、语言文件注入和安全备份
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Steps,
  Form,
  Input,
  Select,
  Switch,
  Alert,
  Progress,
  Table,
  Tag,
  Modal,
  Tabs,
  Row,
  Col,
  Statistic,
  Timeline,
  Badge,
  Tooltip,
  notification,
  Popconfirm,
  Divider,
  Empty,
  Upload,
  List,
  Checkbox
} from 'antd'
import {
  BuildOutlined,
  RocketOutlined,
  SettingOutlined,
  FileZipOutlined,
  FolderOutlined,
  ExportOutlined,
  ImportOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  DownloadOutlined,
  UploadOutlined,
  CopyOutlined,
  DeleteOutlined,
  EyeOutlined,
  HistoryOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography
const { Step } = Steps
const { TabPane } = Tabs
const { Option } = Select
const { TextArea } = Input
const { Dragger } = Upload

// 构建相关类型定义
interface BuildTask {
  task_id: string
  project_id?: string
  build_type: 'modpack' | 'single_mod' | 'resource_pack' | 'language_pack'
  status: 'pending' | 'preparing' | 'building' | 'packaging' | 'completed' | 'failed' | 'cancelled'
  
  // 构建配置
  config: {
    source_path: string
    output_path: string
    target_languages: string[]
    include_original: boolean
    compress_output: boolean
    create_backup: boolean
    validate_jar_integrity: boolean
    overwrite_existing: boolean
  }
  
  // 进度信息
  progress: number
  current_step: string
  total_files: number
  processed_files: number
  
  // 结果信息
  output_files?: string[]
  backup_location?: string
  build_size_mb?: number
  
  // 时间信息
  created_at: string
  started_at?: string
  completed_at?: string
  
  // 错误和警告
  error?: string
  warnings: string[]
}

interface BuildConfig {
  build_type: 'modpack' | 'single_mod' | 'resource_pack' | 'language_pack'
  source_path: string
  output_path: string
  target_languages: string[]
  include_original: boolean
  compress_output: boolean
  create_backup: boolean
  validate_jar_integrity: boolean
  overwrite_existing: boolean
  
  // 高级选项
  advanced_options?: {
    compression_level: number
    exclude_patterns: string[]
    custom_manifest?: Record<string, any>
    sign_jar?: boolean
    strip_debug_info?: boolean
  }
}

interface BuildHistory {
  task_id: string
  build_type: string
  status: string
  created_at: string
  completed_at?: string
  duration_ms?: number
  output_size_mb?: number
  success_rate: number
  error_summary?: string
}

interface BuildPageState {
  // 构建任务
  activeTasks: BuildTask[]
  selectedTask: BuildTask | null
  taskLoading: boolean
  
  // 构建配置
  currentConfig: BuildConfig | null
  
  // 历史记录
  buildHistory: BuildHistory[]
  historyLoading: boolean
  
  // UI状态
  activeTab: string
  newBuildModalVisible: boolean
  taskDetailModalVisible: boolean
  configStep: number
  
  // 文件选择
  selectedFiles: string[]
  availableLanguages: typeof AVAILABLE_LANGUAGES
  
  // 模板选择
  selectedTemplate: string | null
  showTemplateSelector: boolean
}

const AVAILABLE_LANGUAGES = [
  { label: '简体中文', value: 'zh_cn', flag: '🇨🇳' },
  { label: 'English (US)', value: 'en_us', flag: '🇺🇸' },
  { label: '繁體中文', value: 'zh_tw', flag: '🇹🇼' },
  { label: '日本語', value: 'ja_jp', flag: '🇯🇵' },
  { label: '한국어', value: 'ko_kr', flag: '🇰🇷' },
  { label: 'Français', value: 'fr_fr', flag: '🇫🇷' },
  { label: 'Deutsch', value: 'de_de', flag: '🇩🇪' },
  { label: 'Español', value: 'es_es', flag: '🇪🇸' },
  { label: 'Português', value: 'pt_br', flag: '🇧🇷' },
  { label: 'Русский', value: 'ru_ru', flag: '🇷🇺' }
]

// 构建模板预设
const BUILD_TEMPLATES = [
  {
    id: 'quick_chinese',
    name: '🇨🇳 快速中文化',
    description: '快速为整合包添加中文翻译，保留英文原版',
    icon: '⚡',
    config: {
      target_languages: ['zh_cn', 'en_us'],
      include_original: true,
      compress_output: true,
      create_backup: true,
      validate_jar_integrity: true,
      overwrite_existing: false
    },
    popular: true
  },
  {
    id: 'full_multilang',
    name: '🌍 多语言完整版',
    description: '包含主流语言的完整版本，适合国际化发布',
    icon: '🎯',
    config: {
      target_languages: ['zh_cn', 'en_us', 'ja_jp', 'ko_kr', 'fr_fr'],
      include_original: true,
      compress_output: true,
      create_backup: true,
      validate_jar_integrity: true,
      overwrite_existing: false
    }
  },
  {
    id: 'chinese_only',
    name: '🎌 纯中文版',
    description: '只保留中文翻译，文件体积最小',
    icon: '💎',
    config: {
      target_languages: ['zh_cn'],
      include_original: false,
      compress_output: true,
      create_backup: true,
      validate_jar_integrity: true,
      overwrite_existing: false
    }
  },
  {
    id: 'custom',
    name: '⚙️ 自定义配置',
    description: '完全自定义构建选项，适合高级用户',
    icon: '🔧',
    config: {
      target_languages: ['zh_cn'],
      include_original: true,
      compress_output: true,
      create_backup: true,
      validate_jar_integrity: true,
      overwrite_existing: false
    }
  }
]

const BUILD_STEPS = [
  {
    title: '选择源文件',
    description: '选择要构建的MOD或整合包'
  },
  {
    title: '配置构建选项',
    description: '设置输出路径和构建参数'
  },
  {
    title: '选择语言',
    description: '选择要包含的目标语言'
  },
  {
    title: '确认构建',
    description: '检查配置并开始构建'
  }
]

export const BuildPage: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  
  const [state, setState] = useState<BuildPageState>({
    activeTasks: [],
    selectedTask: null,
    taskLoading: false,
    currentConfig: null,
    buildHistory: [],
    historyLoading: false,
    activeTab: 'tasks',
    newBuildModalVisible: false,
    taskDetailModalVisible: false,
    configStep: 0,
    selectedFiles: [],
    availableLanguages: AVAILABLE_LANGUAGES,
    selectedTemplate: null,
    showTemplateSelector: true
  })

  // 模拟加载活跃任务
  const loadActiveTasks = useCallback(async () => {
    setState(prev => ({ ...prev, taskLoading: true }))
    
    // 模拟数据
    setTimeout(() => {
      const mockTasks: BuildTask[] = [
        {
          task_id: 'build_001',
          project_id: 'project_123',
          build_type: 'modpack',
          status: 'building',
          config: {
            source_path: '/path/to/modpack',
            output_path: '/output/built_modpack.zip',
            target_languages: ['zh_cn', 'en_us'],
            include_original: true,
            compress_output: true,
            create_backup: true,
            validate_jar_integrity: true,
            overwrite_existing: false
          },
          progress: 65,
          current_step: '正在注入语言文件...',
          total_files: 120,
          processed_files: 78,
          created_at: '2025-09-13T00:30:00Z',
          started_at: '2025-09-13T00:32:00Z',
          warnings: ['某些MOD缺少中文翻译']
        }
      ]
      
      setState(prev => ({ 
        ...prev, 
        activeTasks: mockTasks, 
        taskLoading: false 
      }))
    }, 1000)
  }, [])

  // 模拟加载历史
  const loadBuildHistory = useCallback(async () => {
    setState(prev => ({ ...prev, historyLoading: true }))
    
    setTimeout(() => {
      const mockHistory: BuildHistory[] = [
        {
          task_id: 'build_h001',
          build_type: 'modpack',
          status: 'completed',
          created_at: '2025-09-12T15:30:00Z',
          completed_at: '2025-09-12T15:45:00Z',
          duration_ms: 900000,
          output_size_mb: 245.6,
          success_rate: 0.95
        },
        {
          task_id: 'build_h002',
          build_type: 'single_mod',
          status: 'completed',
          created_at: '2025-09-11T10:20:00Z',
          completed_at: '2025-09-11T10:22:00Z',
          duration_ms: 120000,
          output_size_mb: 12.3,
          success_rate: 1.0
        }
      ]
      
      setState(prev => ({ 
        ...prev, 
        buildHistory: mockHistory, 
        historyLoading: false 
      }))
    }, 800)
  }, [])

  // 启动新构建任务
  const startBuildTask = useCallback(async (config: BuildConfig) => {
    try {
      // 这里将调用真实的API
      notification.success({ 
        message: '构建任务已启动', 
        description: '正在准备构建环境...' 
      })
      
      setState(prev => ({ ...prev, newBuildModalVisible: false, configStep: 0 }))
      form.resetFields()
      loadActiveTasks()
    } catch (error) {
      notification.error({ 
        message: '启动构建任务失败', 
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
      // 这里将调用真实的API
      notification.success({ 
        message: `任务${action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : '取消'}成功` 
      })
      loadActiveTasks()
    } catch (error) {
      notification.error({ 
        message: `任务${action}失败`, 
        description: String(error) 
      })
    }
  }, [loadActiveTasks])

  // 查看任务详情
  const viewTaskDetail = useCallback((task: BuildTask) => {
    setState(prev => ({ 
      ...prev, 
      selectedTask: task, 
      taskDetailModalVisible: true 
    }))
  }, [])

  // 文件选择处理
  const handleFileSelection = useCallback(async () => {
    try {
      // 检查是否在Tauri环境中
      if (typeof window !== 'undefined' && (window as any).__TAURI__ && (window as any).__TAURI__.dialog) {
        // 使用Tauri全局API
        const selected = await (window as any).__TAURI__.dialog.open({
          multiple: true,
          filters: [{
            name: 'Minecraft Files',
            extensions: ['jar', 'zip', 'mcmeta']
          }]
        })
        
        if (selected && Array.isArray(selected)) {
          setState(prev => ({ ...prev, selectedFiles: selected }))
        } else if (selected) {
          setState(prev => ({ ...prev, selectedFiles: [selected as string] }))
        }
      } else {
        // Web环境下的模拟选择
        setState(prev => ({ 
          ...prev, 
          selectedFiles: ['/path/to/example/modpack.zip'] 
        }))
        notification.info({ message: '文件选择功能仅在桌面应用中可用，已使用示例路径' })
      }
    } catch (error) {
      notification.error({ message: '文件选择失败', description: String(error) })
    }
  }, [])

  // 初始化加载
  useEffect(() => {
    loadActiveTasks()
    loadBuildHistory()
  }, [])

  // 任务表格列定义
  const taskColumns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 120,
      render: (id: string) => (
        <Text code className="text-xs">{id}</Text>
      )
    },
    {
      title: '构建类型',
      dataIndex: 'build_type',
      key: 'build_type',
      width: 100,
      render: (type: string) => {
        const typeLabels = {
          modpack: '整合包',
          single_mod: '单个MOD',
          resource_pack: '资源包',
          language_pack: '语言包'
        }
        const colors = {
          modpack: 'blue',
          single_mod: 'green',
          resource_pack: 'orange',
          language_pack: 'purple'
        }
        return (
          <Tag color={colors[type as keyof typeof colors]}>
            {typeLabels[type as keyof typeof typeLabels] || type}
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
        const statusLabels = {
          pending: '等待中',
          preparing: '准备中',
          building: '构建中',
          packaging: '打包中',
          completed: '已完成',
          failed: '失败',
          cancelled: '已取消'
        }
        const colors = {
          pending: 'default',
          preparing: 'processing',
          building: 'processing',
          packaging: 'processing',
          completed: 'success',
          failed: 'error',
          cancelled: 'default'
        }
        return (
          <Badge 
            status={colors[status as keyof typeof colors] as any}
            text={statusLabels[status as keyof typeof statusLabels] || status}
          />
        )
      }
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number, record: BuildTask) => (
        <div>
          <Progress percent={progress} />
          <Text type="secondary" className="text-xs">
            {record.processed_files}/{record.total_files} 文件
          </Text>
        </div>
      )
    },
    {
      title: '当前步骤',
      dataIndex: 'current_step',
      key: 'current_step',
      width: 150,
      render: (step: string) => (
        <Text className="text-sm">{step || '-'}</Text>
      )
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 120,
      render: (date: string) => date ? dayjs(date).fromNow() : '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record: BuildTask) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
             
              onClick={() => viewTaskDetail(record)}
            />
          </Tooltip>
          {record.status === 'building' && (
            <Tooltip title="暂停">
              <Button 
                type="text" 
                icon={<PauseCircleOutlined />} 
               
                onClick={() => handleTaskAction('pause', record.task_id)}
              />
            </Tooltip>
          )}
          {['building', 'preparing', 'pending'].includes(record.status) && (
            <Popconfirm
              title="确定要取消这个构建任务吗？"
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
          {record.status === 'completed' && record.output_files && (
            <Tooltip title="下载结果">
              <Button 
                type="text" 
                icon={<DownloadOutlined />} 
               
                onClick={() => {
                  // 这里将实现下载功能
                  notification.info({ message: '正在准备下载...' })
                }}
              />
            </Tooltip>
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
      width: 120,
      render: (id: string) => (
        <Text code className="text-xs">{id}</Text>
      )
    },
    {
      title: '构建类型',
      dataIndex: 'build_type',
      key: 'build_type',
      width: 100
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Badge 
          status={status === 'completed' ? 'success' : 'error'}
          text={status === 'completed' ? '成功' : '失败'}
        />
      )
    },
    {
      title: '文件大小',
      dataIndex: 'output_size_mb',
      key: 'output_size_mb',
      width: 100,
      render: (size: number) => size ? `${size.toFixed(1)} MB` : '-'
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
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 120,
      render: (date: string) => date ? dayjs(date).fromNow() : '-'
    }
  ]

  // 构建配置表单渲染
  const renderConfigStep = () => {
    switch (state.configStep) {
      case 0: // 选择源文件
        return (
          <div className="space-y-4">
            <div className="text-center">
              <Button 
                type="dashed" 
                icon={<FolderOutlined />} 
               
                onClick={handleFileSelection}
                className="h-32 w-full"
              >
                <div>
                  <div className="text-lg mb-2">选择源文件</div>
                  <div className="text-sm text-gray-500">支持 .jar, .zip, .mcmeta 文件</div>
                </div>
              </Button>
            </div>
            
            {state.selectedFiles.length > 0 && (
              <div>
                <Text strong>已选择文件:</Text>
                <List
                 
                  dataSource={state.selectedFiles}
                  renderItem={(file, index) => (
                    <List.Item key={index}>
                      <Text className="text-sm">{file}</Text>
                    </List.Item>
                  )}
                />
              </div>
            )}
          </div>
        )
      
      case 1: // 配置构建选项
        return (
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              build_type: 'modpack',
              include_original: true,
              compress_output: true,
              create_backup: true,
              validate_jar_integrity: true,
              overwrite_existing: false
            }}
          >
            <Form.Item
              name="build_type"
              label="构建类型"
              rules={[{ required: true, message: '请选择构建类型' }]}
            >
              <Select>
                <Option value="modpack">整合包</Option>
                <Option value="single_mod">单个MOD</Option>
                <Option value="resource_pack">资源包</Option>
                <Option value="language_pack">语言包</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="output_path"
              label="输出路径"
              rules={[{ required: true, message: '请输入输出路径' }]}
            >
              <Input placeholder="/path/to/output/" />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="include_original" valuePropName="checked">
                  <Checkbox>包含原始文件</Checkbox>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="compress_output" valuePropName="checked">
                  <Checkbox>压缩输出</Checkbox>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="create_backup" valuePropName="checked">
                  <Checkbox>创建备份</Checkbox>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="validate_jar_integrity" valuePropName="checked">
                  <Checkbox>验证JAR完整性</Checkbox>
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="overwrite_existing" valuePropName="checked">
              <Checkbox>覆盖已存在文件</Checkbox>
            </Form.Item>
          </Form>
        )
      
      case 2: // 选择语言
        return (
          <div className="space-y-4">
            <Text strong>选择要包含的目标语言:</Text>
            <Checkbox.Group
              value={state.currentConfig?.target_languages || []}
              onChange={(languages) => {
                setState(prev => ({
                  ...prev,
                  currentConfig: prev.currentConfig ? {
                    ...prev.currentConfig,
                    target_languages: languages as string[]
                  } : null
                }))
              }}
              className="grid grid-cols-2 gap-2"
            >
              {AVAILABLE_LANGUAGES.map(lang => (
                <Checkbox key={lang.value} value={lang.value}>
                  {lang.flag} {lang.label}
                </Checkbox>
              ))}
            </Checkbox.Group>
          </div>
        )
      
      case 3: // 确认构建
        return (
          <div className="space-y-4">
            <Alert
              message="构建配置检查"
              description="请确认以下配置信息无误后点击开始构建"
              type="info"
              showIcon
            />
            
            <Card title="构建概要">
              <div className="space-y-2 text-sm">
                <div><strong>选择文件:</strong> {state.selectedFiles.length} 个文件</div>
                <div><strong>构建类型:</strong> {form.getFieldValue('build_type')}</div>
                <div><strong>目标语言:</strong> {state.currentConfig?.target_languages?.join(', ') || '无'}</div>
                <div><strong>输出路径:</strong> {form.getFieldValue('output_path')}</div>
              </div>
            </Card>
            
            <Card title="构建选项">
              <div className="space-y-1 text-sm">
                <div>• {form.getFieldValue('include_original') ? '包含原始文件' : '不包含原始文件'}</div>
                <div>• {form.getFieldValue('compress_output') ? '启用压缩' : '禁用压缩'}</div>
                <div>• {form.getFieldValue('create_backup') ? '创建备份' : '不创建备份'}</div>
                <div>• {form.getFieldValue('validate_jar_integrity') ? '验证JAR完整性' : '跳过验证'}</div>
              </div>
            </Card>
          </div>
        )
      
      default:
        return null
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">🚀 构建中心</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => {
            loadActiveTasks()
            loadBuildHistory()
          }}>
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<RocketOutlined />}
            onClick={() => setState(prev => ({ ...prev, newBuildModalVisible: true }))}
          >
            新建构建任务
          </Button>
        </Space>
      </div>

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
                    image={<BuildOutlined className="text-6xl text-gray-300" />}
                    description={
                      <div>
                        <Text type="secondary">暂无活跃的构建任务</Text>
                        <br />
                        <Button 
                          type="link" 
                          onClick={() => setState(prev => ({ ...prev, newBuildModalVisible: true }))}
                        >
                          创建新的构建任务
                        </Button>
                      </div>
                    }
                  />
                )
              }}
            />
          </TabPane>
          
          <TabPane tab="构建历史" key="history">
            <Table
              columns={historyColumns}
              dataSource={state.buildHistory}
              rowKey="task_id"
              loading={state.historyLoading}
             
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 条`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 新建构建任务模态框 */}
      <Modal
        title="新建构建任务"
        open={state.newBuildModalVisible}
        onCancel={() => {
          setState(prev => ({ ...prev, newBuildModalVisible: false, configStep: 0 }))
          form.resetFields()
        }}
        footer={null}
        width={700}
      >
        <div className="mb-6">
          <Steps current={state.configStep} items={BUILD_STEPS} />
        </div>
        
        <div className="mb-6">
          {renderConfigStep()}
        </div>
        
        <div className="flex justify-between">
          <Button 
            disabled={state.configStep === 0}
            onClick={() => setState(prev => ({ ...prev, configStep: Math.max(0, prev.configStep - 1) }))}
          >
            上一步
          </Button>
          
          <Space>
            <Button 
              onClick={() => {
                setState(prev => ({ ...prev, newBuildModalVisible: false, configStep: 0 }))
                form.resetFields()
              }}
            >
              取消
            </Button>
            
            {state.configStep < BUILD_STEPS.length - 1 ? (
              <Button 
                type="primary"
                disabled={state.configStep === 0 && state.selectedFiles.length === 0}
                onClick={() => {
                  if (state.configStep === 1) {
                    form.validateFields().then(() => {
                      setState(prev => ({ ...prev, configStep: prev.configStep + 1 }))
                    })
                  } else {
                    setState(prev => ({ ...prev, configStep: prev.configStep + 1 }))
                  }
                }}
              >
                下一步
              </Button>
            ) : (
              <Button 
                type="primary"
                disabled={!state.currentConfig?.target_languages?.length}
                onClick={() => {
                  const formValues = form.getFieldsValue()
                  const config: BuildConfig = {
                    ...formValues,
                    source_path: state.selectedFiles[0] || '',
                    target_languages: state.currentConfig?.target_languages || []
                  }
                  startBuildTask(config)
                }}
              >
                开始构建
              </Button>
            )}
          </Space>
        </div>
      </Modal>

      {/* 任务详情模态框 */}
      <Modal
        title={`构建任务详情 - ${state.selectedTask?.task_id}`}
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
                    <div><strong>构建类型:</strong> {state.selectedTask.build_type}</div>
                    <div><strong>状态:</strong> {state.selectedTask.status}</div>
                    <div><strong>当前步骤:</strong> {state.selectedTask.current_step || '-'}</div>
                  </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="进度信息">
                  <div className="space-y-2 text-sm">
                    <div><strong>进度:</strong> {state.selectedTask.progress}%</div>
                    <div><strong>总文件数:</strong> {state.selectedTask.total_files}</div>
                    <div><strong>已处理:</strong> {state.selectedTask.processed_files}</div>
                    <div><strong>剩余:</strong> {state.selectedTask.total_files - state.selectedTask.processed_files}</div>
                  </div>
                </Card>
              </Col>
            </Row>

            {/* 配置信息 */}
            <Card title="构建配置" className="mb-4">
              <div className="space-y-2 text-sm">
                <div><strong>源路径:</strong> {state.selectedTask.config.source_path}</div>
                <div><strong>输出路径:</strong> {state.selectedTask.config.output_path}</div>
                <div><strong>目标语言:</strong> {state.selectedTask.config.target_languages.join(', ')}</div>
                <div><strong>选项:</strong> 
                  {state.selectedTask.config.include_original && '• 包含原始文件 '}
                  {state.selectedTask.config.compress_output && '• 启用压缩 '}
                  {state.selectedTask.config.create_backup && '• 创建备份 '}
                  {state.selectedTask.config.validate_jar_integrity && '• 验证完整性'}
                </div>
              </div>
            </Card>

            {/* 时间信息 */}
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
              </Timeline>
            </Card>

            {/* 警告和错误 */}
            {(state.selectedTask.error || state.selectedTask.warnings.length > 0) && (
              <Card title="警告和错误">
                {state.selectedTask.error && (
                  <Alert
                    message="构建错误"
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

export default BuildPage