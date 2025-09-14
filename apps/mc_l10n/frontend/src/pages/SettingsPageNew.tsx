/**
 * 设置页面 - 应用配置、用户偏好和系统设置
 * 支持主题设置、语言配置、数据管理和高级选项
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Tabs,
  Form,
  Input,
  Select,
  Switch,
  Slider,
  InputNumber,
  Upload,
  Alert,
  Modal,
  Table,
  Tag,
  Badge,
  Tooltip,
  notification,
  Popconfirm,
  Divider,
  Row,
  Col,
  List,
  Avatar,
  Progress,
  Radio,
  Checkbox,
  ColorPicker
} from 'antd'
import {
  SettingOutlined,
  UserOutlined,
  BgColorsOutlined,
  TranslationOutlined,
  DatabaseOutlined,
  SecurityScanOutlined,
  ExperimentOutlined,
  SaveOutlined,
  ReloadOutlined,
  ExportOutlined,
  ImportOutlined,
  DeleteOutlined,
  FolderOutlined,
  CloudOutlined,
  BellOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'

const { Title, Text, Paragraph } = Typography
const { TabPane } = Tabs
const { Option } = Select
const { TextArea } = Input
const { Dragger } = Upload

// 设置相关类型定义
interface AppSettings {
  // 基本设置
  theme: 'light' | 'dark' | 'auto'
  language: string
  timezone: string
  
  // 界面设置
  ui: {
    sidebar_collapsed: boolean
    items_per_page: number
    auto_refresh_interval: number
    show_notifications: boolean
    compact_mode: boolean
    accent_color: string
  }
  
  // 扫描设置
  scanning: {
    max_concurrent_scans: number
    default_scan_depth: number
    cache_scan_results: boolean
    auto_detect_mod_loader: boolean
    exclude_patterns: string[]
    include_patterns: string[]
  }
  
  // 同步设置
  sync: {
    auto_sync_enabled: boolean
    sync_interval_minutes: number
    conflict_resolution: 'local_wins' | 'remote_wins' | 'manual'
    batch_size: number
    timeout_seconds: number
    use_compression: boolean
  }
  
  // 构建设置
  build: {
    default_output_path: string
    auto_backup: boolean
    validate_jar_integrity: boolean
    compression_level: number
    max_parallel_builds: number
    keep_build_history: number
  }
  
  // 高级设置
  advanced: {
    debug_mode: boolean
    log_level: 'debug' | 'info' | 'warning' | 'error'
    max_log_size_mb: number
    enable_telemetry: boolean
    gpu_acceleration: boolean
    memory_limit_mb: number
  }
}

interface DataManagement {
  projects_count: number
  packs_count: number
  mods_count: number
  total_size_mb: number
  cache_size_mb: number
  log_size_mb: number
  last_backup?: string
  database_version: string
}

interface SettingsPageState {
  // 设置数据
  settings: AppSettings | null
  settingsLoading: boolean
  
  // 数据管理
  dataInfo: DataManagement | null
  dataLoading: boolean
  
  // UI状态
  activeTab: string
  hasUnsavedChanges: boolean
  saving: boolean
  resetModalVisible: boolean
  exportModalVisible: boolean
  importModalVisible: boolean
  
  // 表单实例
  formRef: any
}

const DEFAULT_SETTINGS: AppSettings = {
  theme: 'auto',
  language: 'zh_cn',
  timezone: 'Asia/Shanghai',
  ui: {
    sidebar_collapsed: false,
    items_per_page: 20,
    auto_refresh_interval: 5000,
    show_notifications: true,
    compact_mode: false,
    accent_color: '#1890ff'
  },
  scanning: {
    max_concurrent_scans: 3,
    default_scan_depth: 5,
    cache_scan_results: true,
    auto_detect_mod_loader: true,
    exclude_patterns: ['*.tmp', '*.bak', '*~'],
    include_patterns: ['*.jar', '*.zip', '*.json']
  },
  sync: {
    auto_sync_enabled: false,
    sync_interval_minutes: 30,
    conflict_resolution: 'manual',
    batch_size: 100,
    timeout_seconds: 300,
    use_compression: true
  },
  build: {
    default_output_path: './output',
    auto_backup: true,
    validate_jar_integrity: true,
    compression_level: 6,
    max_parallel_builds: 2,
    keep_build_history: 10
  },
  advanced: {
    debug_mode: false,
    log_level: 'info',
    max_log_size_mb: 100,
    enable_telemetry: true,
    gpu_acceleration: false,
    memory_limit_mb: 2048
  }
}

const LANGUAGE_OPTIONS = [
  { value: 'zh_cn', label: '简体中文' },
  { value: 'zh_tw', label: '繁體中文' },
  { value: 'en_us', label: 'English (US)' },
  { value: 'ja_jp', label: '日本語' },
  { value: 'ko_kr', label: '한국어' }
]

const TIMEZONE_OPTIONS = [
  { value: 'Asia/Shanghai', label: '中国标准时间 (UTC+8)' },
  { value: 'Asia/Tokyo', label: '日本标准时间 (UTC+9)' },
  { value: 'America/New_York', label: '东部标准时间 (UTC-5)' },
  { value: 'Europe/London', label: '格林威治标准时间 (UTC+0)' },
  { value: 'UTC', label: '协调世界时 (UTC)' }
]

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  
  const [state, setState] = useState<SettingsPageState>({
    settings: null,
    settingsLoading: false,
    dataInfo: null,
    dataLoading: false,
    activeTab: 'general',
    hasUnsavedChanges: false,
    saving: false,
    resetModalVisible: false,
    exportModalVisible: false,
    importModalVisible: false,
    formRef: form
  })

  // 加载设置
  const loadSettings = useCallback(async () => {
    setState(prev => ({ ...prev, settingsLoading: true }))
    
    try {
      // 模拟加载设置，实际中会从存储或API加载
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          settings: DEFAULT_SETTINGS, 
          settingsLoading: false 
        }))
        form.setFieldsValue(DEFAULT_SETTINGS)
      }, 500)
    } catch (error) {
      notification.error({ 
        message: '加载设置失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, settingsLoading: false }))
    }
  }, [form])

  // 加载数据信息
  const loadDataInfo = useCallback(async () => {
    setState(prev => ({ ...prev, dataLoading: true }))
    
    try {
      // 模拟数据信息
      const mockDataInfo: DataManagement = {
        projects_count: 12,
        packs_count: 8,
        mods_count: 156,
        total_size_mb: 2048.5,
        cache_size_mb: 512.3,
        log_size_mb: 89.7,
        last_backup: '2025-09-12T10:30:00Z',
        database_version: '2.1.0'
      }
      
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          dataInfo: mockDataInfo, 
          dataLoading: false 
        }))
      }, 300)
    } catch (error) {
      notification.error({ 
        message: '加载数据信息失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, dataLoading: false }))
    }
  }, [])

  // 保存设置
  const saveSettings = useCallback(async () => {
    setState(prev => ({ ...prev, saving: true }))
    
    try {
      const values = await form.validateFields()
      
      // 模拟保存设置
      setTimeout(() => {
        setState(prev => ({ 
          ...prev, 
          settings: values, 
          hasUnsavedChanges: false, 
          saving: false 
        }))
        notification.success({ message: '设置已保存' })
      }, 1000)
    } catch (error) {
      notification.error({ 
        message: '保存设置失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, saving: false }))
    }
  }, [form])

  // 重置设置
  const resetSettings = useCallback(async () => {
    try {
      form.setFieldsValue(DEFAULT_SETTINGS)
      setState(prev => ({ 
        ...prev, 
        settings: DEFAULT_SETTINGS, 
        hasUnsavedChanges: true,
        resetModalVisible: false 
      }))
      notification.success({ message: '设置已重置为默认值' })
    } catch (error) {
      notification.error({ 
        message: '重置设置失败', 
        description: String(error) 
      })
    }
  }, [form])

  // 数据操作
  const clearCache = useCallback(async () => {
    try {
      notification.info({ message: '正在清理缓存...' })
      // 模拟清理缓存
      setTimeout(() => {
        notification.success({ message: '缓存清理完成' })
        loadDataInfo()
      }, 2000)
    } catch (error) {
      notification.error({ 
        message: '清理缓存失败', 
        description: String(error) 
      })
    }
  }, [loadDataInfo])

  const createBackup = useCallback(async () => {
    try {
      notification.info({ message: '正在创建备份...' })
      // 模拟创建备份
      setTimeout(() => {
        notification.success({ message: '备份已创建' })
        loadDataInfo()
      }, 3000)
    } catch (error) {
      notification.error({ 
        message: '创建备份失败', 
        description: String(error) 
      })
    }
  }, [loadDataInfo])

  const exportSettings = useCallback(async () => {
    try {
      const settings = form.getFieldsValue()
      const exportData = {
        version: '2.1.0',
        exported_at: new Date().toISOString(),
        settings
      }
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json'
      })
      
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `th-suite-settings-${dayjs().format('YYYY-MM-DD')}.json`
      a.click()
      URL.revokeObjectURL(url)
      
      setState(prev => ({ ...prev, exportModalVisible: false }))
      notification.success({ message: '设置已导出' })
    } catch (error) {
      notification.error({ 
        message: '导出设置失败', 
        description: String(error) 
      })
    }
  }, [form])

  // 监听表单变化
  const handleFormChange = useCallback(() => {
    setState(prev => ({ ...prev, hasUnsavedChanges: true }))
  }, [])

  // 初始化加载
  useEffect(() => {
    loadSettings()
    loadDataInfo()
  }, [])

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">⚙️ 设置</Title>
        <Space>
          {state.hasUnsavedChanges && (
            <Badge status="warning" text="有未保存的更改" />
          )}
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => {
              loadSettings()
              loadDataInfo()
            }}
          >
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<SaveOutlined />}
            loading={state.saving}
            disabled={!state.hasUnsavedChanges}
            onClick={saveSettings}
          >
            保存设置
          </Button>
        </Space>
      </div>

      <Card>
        <Tabs 
          activeKey={state.activeTab} 
          onChange={(key) => setState(prev => ({ ...prev, activeTab: key }))}
        >
          {/* 基本设置 */}
          <TabPane tab="基本设置" key="general">
            <Form
              form={form}
              layout="vertical"
              onValuesChange={handleFormChange}
              className="max-w-2xl"
            >
              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name="theme"
                    label="界面主题"
                    tooltip="选择明亮或暗黑主题，或跟随系统设置"
                  >
                    <Radio.Group>
                      <Radio value="light">明亮</Radio>
                      <Radio value="dark">暗黑</Radio>
                      <Radio value="auto">跟随系统</Radio>
                    </Radio.Group>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="language"
                    label="界面语言"
                  >
                    <Select>
                      {LANGUAGE_OPTIONS.map(lang => (
                        <Option key={lang.value} value={lang.value}>
                          {lang.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name="timezone"
                    label="时区"
                  >
                    <Select>
                      {TIMEZONE_OPTIONS.map(tz => (
                        <Option key={tz.value} value={tz.value}>
                          {tz.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['ui', 'accent_color']}
                    label="主色调"
                  >
                    <ColorPicker showText />
                  </Form.Item>
                </Col>
              </Row>

              <Divider>界面偏好</Divider>

              <Row gutter={24}>
                <Col span={8}>
                  <Form.Item
                    name={['ui', 'items_per_page']}
                    label="每页显示数量"
                  >
                    <Select>
                      <Option value={10}>10</Option>
                      <Option value={20}>20</Option>
                      <Option value={50}>50</Option>
                      <Option value={100}>100</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name={['ui', 'auto_refresh_interval']}
                    label="自动刷新间隔(秒)"
                  >
                    <InputNumber min={3} max={60} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <div className="pt-8">
                    <Form.Item name={['ui', 'compact_mode']} valuePropName="checked">
                      <Switch checkedChildren="紧凑模式" unCheckedChildren="宽松模式" />
                    </Form.Item>
                  </div>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item name={['ui', 'sidebar_collapsed']} valuePropName="checked">
                    <Switch checkedChildren="侧边栏折叠" unCheckedChildren="侧边栏展开" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name={['ui', 'show_notifications']} valuePropName="checked">
                    <Switch checkedChildren="显示通知" unCheckedChildren="隐藏通知" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </TabPane>

          {/* 扫描设置 */}
          <TabPane tab="扫描设置" key="scanning">
            <Form form={form} layout="vertical" className="max-w-2xl">
              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name={['scanning', 'max_concurrent_scans']}
                    label="最大并发扫描数"
                    tooltip="同时进行的扫描任务数量，较高值可能影响系统性能"
                  >
                    <Slider min={1} max={8} marks={{ 1: '1', 4: '4', 8: '8' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['scanning', 'default_scan_depth']}
                    label="默认扫描深度"
                    tooltip="目录递归扫描的最大深度"
                  >
                    <Slider min={1} max={10} marks={{ 1: '1', 5: '5', 10: '10' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item name={['scanning', 'cache_scan_results']} valuePropName="checked">
                    <Switch checkedChildren="缓存扫描结果" unCheckedChildren="不缓存" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name={['scanning', 'auto_detect_mod_loader']} valuePropName="checked">
                    <Switch checkedChildren="自动检测MOD加载器" unCheckedChildren="手动指定" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name={['scanning', 'exclude_patterns']}
                label="排除模式"
                tooltip="不会被扫描的文件模式，每行一个"
              >
                <TextArea rows={3} placeholder="*.tmp
*.bak
*~" />
              </Form.Item>

              <Form.Item
                name={['scanning', 'include_patterns']}
                label="包含模式"
                tooltip="会被扫描的文件模式，每行一个"
              >
                <TextArea rows={3} placeholder="*.jar
*.zip
*.json" />
              </Form.Item>
            </Form>
          </TabPane>

          {/* 同步设置 */}
          <TabPane tab="同步设置" key="sync">
            <Form form={form} layout="vertical" className="max-w-2xl">
              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item name={['sync', 'auto_sync_enabled']} valuePropName="checked">
                    <Switch checkedChildren="启用自动同步" unCheckedChildren="禁用自动同步" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['sync', 'sync_interval_minutes']}
                    label="同步间隔(分钟)"
                  >
                    <InputNumber min={5} max={1440} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name={['sync', 'conflict_resolution']}
                    label="冲突解决策略"
                  >
                    <Select>
                      <Option value="local_wins">本地优先</Option>
                      <Option value="remote_wins">远程优先</Option>
                      <Option value="manual">手动解决</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['sync', 'batch_size']}
                    label="批处理大小"
                  >
                    <InputNumber min={10} max={1000} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name={['sync', 'timeout_seconds']}
                    label="超时时间(秒)"
                  >
                    <InputNumber min={30} max={3600} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <div className="pt-8">
                    <Form.Item name={['sync', 'use_compression']} valuePropName="checked">
                      <Switch checkedChildren="启用压缩" unCheckedChildren="禁用压缩" />
                    </Form.Item>
                  </div>
                </Col>
              </Row>
            </Form>
          </TabPane>

          {/* 构建设置 */}
          <TabPane tab="构建设置" key="build">
            <Form form={form} layout="vertical" className="max-w-2xl">
              <Form.Item
                name={['build', 'default_output_path']}
                label="默认输出路径"
              >
                <Input placeholder="./output" addonAfter={
                  <FolderOutlined 
                    className="cursor-pointer" 
                    onClick={() => {
                      // 这里将调用文件选择器
                      notification.info({ message: '文件选择器仅在桌面应用中可用' })
                    }}
                  />
                } />
              </Form.Item>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name={['build', 'compression_level']}
                    label="压缩级别"
                    tooltip="较高的压缩级别可以减小文件大小，但会增加构建时间"
                  >
                    <Slider min={1} max={9} marks={{ 1: '快速', 6: '平衡', 9: '最小' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['build', 'max_parallel_builds']}
                    label="最大并行构建数"
                  >
                    <InputNumber min={1} max={8} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={8}>
                  <Form.Item name={['build', 'auto_backup']} valuePropName="checked">
                    <Switch checkedChildren="自动备份" unCheckedChildren="不备份" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name={['build', 'validate_jar_integrity']} valuePropName="checked">
                    <Switch checkedChildren="验证JAR完整性" unCheckedChildren="跳过验证" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name={['build', 'keep_build_history']}
                    label="保留构建历史数"
                  >
                    <InputNumber min={1} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </TabPane>

          {/* 高级设置 */}
          <TabPane tab="高级设置" key="advanced">
            <Alert
              message="高级设置警告"
              description="修改这些设置可能会影响应用程序的稳定性和性能，请谨慎操作。"
              type="warning"
              showIcon
              className="mb-6"
            />
            
            <Form form={form} layout="vertical" className="max-w-2xl">
              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name={['advanced', 'log_level']}
                    label="日志级别"
                  >
                    <Select>
                      <Option value="debug">调试 (Debug)</Option>
                      <Option value="info">信息 (Info)</Option>
                      <Option value="warning">警告 (Warning)</Option>
                      <Option value="error">错误 (Error)</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['advanced', 'max_log_size_mb']}
                    label="最大日志大小(MB)"
                  >
                    <InputNumber min={10} max={1000} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={12}>
                  <Form.Item
                    name={['advanced', 'memory_limit_mb']}
                    label="内存限制(MB)"
                    tooltip="限制应用程序的最大内存使用量"
                  >
                    <InputNumber min={512} max={8192} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <div className="space-y-4 pt-4">
                    <Form.Item name={['advanced', 'debug_mode']} valuePropName="checked">
                      <Switch checkedChildren="调试模式" unCheckedChildren="正常模式" />
                    </Form.Item>
                  </div>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col span={8}>
                  <Form.Item name={['advanced', 'enable_telemetry']} valuePropName="checked">
                    <Switch checkedChildren="启用遥测" unCheckedChildren="禁用遥测" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name={['advanced', 'gpu_acceleration']} valuePropName="checked">
                    <Switch checkedChildren="GPU加速" unCheckedChildren="CPU模式" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </TabPane>

          {/* 数据管理 */}
          <TabPane tab="数据管理" key="data">
            {state.dataInfo && (
              <div className="space-y-6">
                {/* 数据统计 */}
                <Card title="数据统计">
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic title="项目数" value={state.dataInfo.projects_count} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="整合包数" value={state.dataInfo.packs_count} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="MOD数" value={state.dataInfo.mods_count} />
                    </Col>
                    <Col span={6}>
                      <Statistic 
                        title="数据大小" 
                        value={state.dataInfo.total_size_mb} 
                        precision={1}
                        suffix="MB" 
                      />
                    </Col>
                  </Row>
                </Card>

                {/* 缓存管理 */}
                <Card title="缓存管理">
                  <Row gutter={16} className="mb-4">
                    <Col span={8}>
                      <Statistic 
                        title="缓存大小" 
                        value={state.dataInfo.cache_size_mb} 
                        precision={1}
                        suffix="MB" 
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic 
                        title="日志大小" 
                        value={state.dataInfo.log_size_mb} 
                        precision={1}
                        suffix="MB" 
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic 
                        title="数据库版本" 
                        value={state.dataInfo.database_version} 
                      />
                    </Col>
                  </Row>
                  
                  <Space>
                    <Popconfirm
                      title="确定要清理所有缓存吗？"
                      description="清理后需要重新扫描才能恢复数据"
                      onConfirm={clearCache}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button icon={<DeleteOutlined />}>清理缓存</Button>
                    </Popconfirm>
                    <Button icon={<ReloadOutlined />} onClick={loadDataInfo}>刷新统计</Button>
                  </Space>
                </Card>

                {/* 备份管理 */}
                <Card title="备份管理">
                  <div className="mb-4">
                    <Text>最后备份时间: </Text>
                    <Text strong>
                      {state.dataInfo.last_backup ? 
                        dayjs(state.dataInfo.last_backup).format('YYYY-MM-DD HH:mm:ss') : 
                        '从未备份'
                      }
                    </Text>
                  </div>
                  
                  <Space>
                    <Button 
                      type="primary" 
                      icon={<ExportOutlined />}
                      onClick={createBackup}
                    >
                      创建备份
                    </Button>
                    <Button icon={<ImportOutlined />}>恢复备份</Button>
                  </Space>
                </Card>
              </div>
            )}
          </TabPane>

          {/* 关于 */}
          <TabPane tab="关于" key="about">
            <div className="max-w-2xl space-y-6">
              <Card title="TH Suite MC L10n">
                <div className="space-y-2">
                  <div><strong>版本:</strong> v2.1.0</div>
                  <div><strong>构建日期:</strong> 2025-09-13</div>
                  <div><strong>架构:</strong> Core-First 投影适配器</div>
                  <div><strong>技术栈:</strong> Tauri + React + TypeScript + FastAPI + Python 3.12</div>
                </div>
              </Card>

              <Card title="系统信息">
                <div className="space-y-2">
                  <div><strong>操作系统:</strong> {navigator.platform}</div>
                  <div><strong>浏览器:</strong> {navigator.userAgent.split(' ').slice(-2).join(' ')}</div>
                  <div><strong>语言:</strong> {navigator.language}</div>
                  <div><strong>时区:</strong> {Intl.DateTimeFormat().resolvedOptions().timeZone}</div>
                </div>
              </Card>

              <Card title="许可信息">
                <Paragraph>
                  TH Suite 是一个专为 Trans-Hub 生态系统设计的游戏本地化工具。
                  通过投影适配器系统与 Trans-Hub Core 深度集成，提供专业级的 Minecraft 本地化工作流。
                </Paragraph>
                <Text type="secondary">
                  Copyright © 2025 Trans-Hub Team. All rights reserved.
                </Text>
              </Card>
              
              <Space>
                <Button 
                  icon={<ExportOutlined />}
                  onClick={() => setState(prev => ({ ...prev, exportModalVisible: true }))}
                >
                  导出设置
                </Button>
                <Button 
                  icon={<ImportOutlined />}
                  onClick={() => setState(prev => ({ ...prev, importModalVisible: true }))}
                >
                  导入设置
                </Button>
                <Popconfirm
                  title="确定要重置所有设置吗？"
                  description="所有设置将被重置为默认值，该操作不可撤销"
                  onConfirm={() => setState(prev => ({ ...prev, resetModalVisible: true }))}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button danger icon={<WarningOutlined />}>重置设置</Button>
                </Popconfirm>
              </Space>
            </div>
          </TabPane>
        </Tabs>
      </Card>

      {/* 重置设置确认模态框 */}
      <Modal
        title="重置设置"
        open={state.resetModalVisible}
        onCancel={() => setState(prev => ({ ...prev, resetModalVisible: false }))}
        footer={[
          <Button key="cancel" onClick={() => setState(prev => ({ ...prev, resetModalVisible: false }))}>
            取消
          </Button>,
          <Button key="confirm" type="primary" danger onClick={resetSettings}>
            确定重置
          </Button>
        ]}
      >
        <Alert
          message="警告"
          description="重置操作将清除所有自定义设置，并恢复为默认配置。该操作不可撤销，请确认您确实需要执行此操作。"
          type="warning"
          showIcon
        />
      </Modal>

      {/* 导出设置模态框 */}
      <Modal
        title="导出设置"
        open={state.exportModalVisible}
        onCancel={() => setState(prev => ({ ...prev, exportModalVisible: false }))}
        footer={[
          <Button key="cancel" onClick={() => setState(prev => ({ ...prev, exportModalVisible: false }))}>
            取消
          </Button>,
          <Button key="export" type="primary" onClick={exportSettings}>
            导出
          </Button>
        ]}
      >
        <div className="space-y-4">
          <Paragraph>
            将当前设置导出为 JSON 文件，您可以在其他设备上导入这些设置。
          </Paragraph>
          <Alert
            message="导出内容"
            description="导出文件将包含所有应用设置，但不包含敏感信息和用户数据。"
            type="info"
            showIcon
          />
        </div>
      </Modal>

      {/* 导入设置模态框 */}
      <Modal
        title="导入设置"
        open={state.importModalVisible}
        onCancel={() => setState(prev => ({ ...prev, importModalVisible: false }))}
        footer={[
          <Button key="cancel" onClick={() => setState(prev => ({ ...prev, importModalVisible: false }))}>
            取消
          </Button>
        ]}
      >
        <div className="space-y-4">
          <Paragraph>
            选择之前导出的设置文件进行导入。导入后将覆盖当前设置。
          </Paragraph>
          <Dragger
            accept=".json"
            beforeUpload={(file) => {
              const reader = new FileReader()
              reader.onload = (e) => {
                try {
                  const content = JSON.parse(e.target?.result as string)
                  if (content.settings) {
                    form.setFieldsValue(content.settings)
                    setState(prev => ({ 
                      ...prev, 
                      hasUnsavedChanges: true,
                      importModalVisible: false 
                    }))
                    notification.success({ message: '设置导入成功' })
                  } else {
                    notification.error({ message: '无效的设置文件格式' })
                  }
                } catch (error) {
                  notification.error({ message: '文件解析失败', description: String(error) })
                }
              }
              reader.readAsText(file)
              return false // 阻止自动上传
            }}
          >
            <p className="ant-upload-drag-icon">
              <ImportOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域</p>
            <p className="ant-upload-hint">支持 .json 格式的设置文件</p>
          </Dragger>
        </div>
      </Modal>
    </div>
  )
}

export default SettingsPage