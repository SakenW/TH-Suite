/**
 * 更新的项目扫描组件
 * 集成TanStack Query进行数据管理和状态处理
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Button,
  Progress,
  Badge,
  Tabs,
  Alert,
  Divider,
  Form,
  Input,
  Select,
  Space,
  Typography,
  Statistic,
  Row,
  Col,
  Tooltip,
  message,
} from 'antd'
import type { TabsProps } from 'antd'
import {
  FolderOpen,
  Scan,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Package,
  FileText,
  Globe,
  Settings,
  Loader2,
  RefreshCw,
  PlayCircle,
  StopCircle,
  PauseCircle,
} from 'lucide-react'
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import { open } from '@tauri-apps/plugin-dialog'
import { useTranslation } from 'react-i18next'

// 引入新的React Query hooks
import {
  useStartScan,
  useCancelScan,
  usePauseScan,
  useResumeScan,
  useRealTimeScanProgress,
  useScanServiceStatus,
  useValidateScanDirectory,
  useScanPresets,
} from '../hooks/api'
import { useErrorHandler } from '../utils/errorHandling'
import { ScanRequest } from '../services/api/types'

const { Text, Title } = Typography
const { Option } = Select

// ============================================================
// 类型定义
// ============================================================

interface ScanProgress {
  scan_id: string
  phase: string
  progress: number
  message: string
  current_file?: string
  processed_files: number
  total_files: number
  estimated_remaining?: number
  updated_at: string
}

interface ScanFormData {
  selectedPath: string
  scanPreset: string
  targetLanguage: string
  includeSubdirectories: boolean
  excludePatterns: string[]
}

// ============================================================
// 主组件
// ============================================================

export const ProjectScanUpdated: React.FC = () => {
  const { t } = useTranslation()
  const { handleError } = useErrorHandler()
  
  // ============================================================
  // 状态管理
  // ============================================================
  
  const [form] = Form.useForm<ScanFormData>()
  const [selectedPath, setSelectedPath] = useState('')
  const [activeScanId, setActiveScanId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  
  // ============================================================
  // React Query hooks
  // ============================================================
  
  // 扫描操作
  const startScanMutation = useStartScan({
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveScanId(result.data.scan_id)
        message.success('扫描已开始')
      } else {
        handleError(result.error, '启动扫描失败')
      }
    },
    onError: (error) => {
      handleError(error, '启动扫描失败')
    }
  })
  
  const cancelScanMutation = useCancelScan({
    onSuccess: (result) => {
      if (result.success) {
        setActiveScanId(null)
        message.success('扫描已取消')
      }
    }
  })
  
  const pauseScanMutation = usePauseScan({
    onSuccess: (result) => {
      if (result.success) {
        message.success('扫描已暂停')
      }
    }
  })
  
  const resumeScanMutation = useResumeScan({
    onSuccess: (result) => {
      if (result.success) {
        message.success('扫描已恢复')
      }
    }
  })
  
  // 扫描状态查询
  const {
    data: scanStatusResult,
    isLoading: isScanStatusLoading,
  } = useRealTimeScanProgress(activeScanId || '', {
    onStatusChange: (status) => {
      console.log('Scan status updated:', status)
    },
    onComplete: (result) => {
      message.success('扫描完成')
      setActiveScanId(null)
    },
    onError: (error) => {
      handleError(error, '扫描过程中出现错误')
      setActiveScanId(null)
    }
  })
  
  // 服务状态查询
  const {
    data: serviceStatusResult,
    isLoading: isServiceStatusLoading,
    error: serviceStatusError,
  } = useScanServiceStatus()
  
  // 扫描预设查询
  const {
    data: presetsResult,
    isLoading: isPresetsLoading,
  } = useScanPresets()
  
  // 目录验证
  const validateDirectoryMutation = useValidateScanDirectory({
    onSuccess: (result) => {
      if (result.success && result.data) {
        const validation = result.data
        if (validation.is_valid) {
          message.success(`检测到 ${validation.detected_files} 个文件，预计扫描时间 ${Math.ceil(validation.estimated_scan_time_seconds / 60)} 分钟`)
        } else {
          message.warning('选择的目录可能不包含有效的项目文件')
        }
      }
    }
  })
  
  // ============================================================
  // 事件处理
  // ============================================================
  
  const handleSelectPath = async () => {
    try {
      const isTauri = typeof window !== 'undefined' && '__TAURI__' in window
      
      if (isTauri) {
        const selected = await open({
          directory: true,
          multiple: false,
          title: '选择项目目录',
        })
        
        if (selected && typeof selected === 'string') {
          setSelectedPath(selected)
          form.setFieldValue('selectedPath', selected)
          
          // 自动验证目录
          validateDirectoryMutation.mutate(selected)
        }
      } else {
        const path = prompt('请输入项目路径:')
        if (path && path.trim()) {
          const trimmedPath = path.trim()
          setSelectedPath(trimmedPath)
          form.setFieldValue('selectedPath', trimmedPath)
          validateDirectoryMutation.mutate(trimmedPath)
        }
      }
    } catch (error) {
      handleError(error, '选择路径失败')
    }
  }
  
  const handleStartScan = useCallback(async () => {
    try {
      const formData = await form.validateFields()
      
      const scanRequest: ScanRequest = {
        source_path: formData.selectedPath,
        target_language: formData.targetLanguage || 'zh_cn',
        options: {
          include_subdirectories: formData.includeSubdirectories !== false,
          exclude_patterns: formData.excludePatterns || [],
          preset_id: formData.scanPreset,
        }
      }
      
      startScanMutation.mutate(scanRequest)
    } catch (error) {
      console.error('Form validation failed:', error)
    }
  }, [form, startScanMutation])
  
  const handleCancelScan = useCallback(() => {
    if (activeScanId) {
      cancelScanMutation.mutate({
        scanId: activeScanId,
        reason: '用户取消'
      })
    }
  }, [activeScanId, cancelScanMutation])
  
  const handlePauseScan = useCallback(() => {
    if (activeScanId) {
      pauseScanMutation.mutate(activeScanId)
    }
  }, [activeScanId, pauseScanMutation])
  
  const handleResumeScan = useCallback(() => {
    if (activeScanId) {
      resumeScanMutation.mutate(activeScanId)
    }
  }, [activeScanId, resumeScanMutation])
  
  // ============================================================
  // 渲染辅助函数
  // ============================================================
  
  const renderServiceStatus = () => {
    if (isServiceStatusLoading) {
      return <Badge status="processing" text="检查服务状态..." />
    }
    
    if (serviceStatusError || !serviceStatusResult?.success) {
      return <Badge status="error" text="扫描服务不可用" />
    }
    
    const status = serviceStatusResult.data
    const statusMap = {
      healthy: { status: 'success' as const, text: '服务正常' },
      degraded: { status: 'warning' as const, text: '服务降级' },
      unavailable: { status: 'error' as const, text: '服务不可用' },
    }
    
    const statusInfo = statusMap[status.status] || statusMap.unavailable
    
    return (
      <Tooltip title={`活跃扫描: ${status.active_scans}, 队列大小: ${status.queue_size}`}>
        <Badge status={statusInfo.status} text={statusInfo.text} />
      </Tooltip>
    )
  }
  
  const renderScanProgress = () => {
    if (!activeScanId || !scanStatusResult?.success) {
      return null
    }
    
    const status = scanStatusResult.data
    const isActive = ['pending', 'running'].includes(status.status)
    
    return (
      <Card title="扫描进度" className="mb-4">
        <Space direction="vertical" className="w-full">
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title="当前阶段"
                value={status.current_phase || '准备中'}
                prefix={isActive ? <Loader2 className="animate-spin" size={16} /> : undefined}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="处理文件"
                value={`${status.processed_files || 0}/${status.total_files || 0}`}
                suffix="个"
              />
            </Col>
          </Row>
          
          <Progress
            percent={Math.round((status.progress || 0) * 100)}
            status={status.status === 'failed' ? 'exception' : status.status === 'completed' ? 'success' : 'active'}
            strokeColor={{
              '0%': '#ff4d4f',
              '50%': '#faad14', 
              '100%': '#52c41a',
            }}
          />
          
          {status.current_file && (
            <Text type="secondary" className="text-sm">
              正在处理: {status.current_file}
            </Text>
          )}
          
          {status.estimated_remaining && (
            <Text type="secondary" className="text-sm">
              预计剩余: {Math.ceil(status.estimated_remaining / 60)} 分钟
            </Text>
          )}
          
          <Space>
            <Button
              icon={<PauseCircle size={16} />}
              onClick={handlePauseScan}
              loading={pauseScanMutation.isPending}
              disabled={!isActive}
            >
              暂停
            </Button>
            <Button
              icon={<PlayCircle size={16} />}
              onClick={handleResumeScan}
              loading={resumeScanMutation.isPending}
              disabled={status.status !== 'paused'}
            >
              恢复
            </Button>
            <Button
              danger
              icon={<StopCircle size={16} />}
              onClick={handleCancelScan}
              loading={cancelScanMutation.isPending}
              disabled={!isActive && status.status !== 'paused'}
            >
              取消
            </Button>
          </Space>
        </Space>
      </Card>
    )
  }
  
  const renderScanForm = () => {
    const isScanning = !!activeScanId
    const presets = presetsResult?.success ? presetsResult.data : []
    
    return (
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          targetLanguage: 'zh_cn',
          includeSubdirectories: true,
          excludePatterns: [],
        }}
      >
        <Form.Item
          label="项目路径"
          name="selectedPath"
          rules={[{ required: true, message: '请选择项目路径' }]}
        >
          <Input
            placeholder="选择要扫描的项目目录"
            value={selectedPath}
            readOnly
            suffix={
              <Button
                type="text"
                icon={<FolderOpen size={16} />}
                onClick={handleSelectPath}
                loading={validateDirectoryMutation.isPending}
              >
                浏览
              </Button>
            }
          />
        </Form.Item>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="扫描预设"
              name="scanPreset"
            >
              <Select
                placeholder="选择扫描预设"
                loading={isPresetsLoading}
                allowClear
              >
                {presets.map((preset: any) => (
                  <Option key={preset.preset_id} value={preset.preset_id}>
                    {preset.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="目标语言"
              name="targetLanguage"
            >
              <Select placeholder="选择目标语言">
                <Option value="zh_cn">简体中文</Option>
                <Option value="zh_tw">繁体中文</Option>
                <Option value="en_us">English</Option>
                <Option value="ja_jp">日本語</Option>
                <Option value="ko_kr">한국어</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
        
        <Form.Item>
          <Space>
            <Button
              type="primary"
              size="large"
              icon={<Scan size={16} />}
              onClick={handleStartScan}
              loading={startScanMutation.isPending}
              disabled={isScanning || !selectedPath}
            >
              开始扫描
            </Button>
            <Button
              icon={<RefreshCw size={16} />}
              onClick={() => {
                form.resetFields()
                setSelectedPath('')
              }}
              disabled={isScanning}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    )
  }
  
  // ============================================================
  // 渲染
  // ============================================================
  
  const tabItems: TabsProps['items'] = [
    {
      key: 'overview',
      label: '扫描概览',
      children: (
        <div>
          <div className="mb-4 flex justify-between items-center">
            <Title level={4}>项目扫描</Title>
            {renderServiceStatus()}
          </div>
          
          {renderScanProgress()}
          
          <Card title="扫描设置">
            {renderScanForm()}
          </Card>
        </div>
      ),
    },
    {
      key: 'results',
      label: '扫描结果',
      children: (
        <Card>
          {activeScanId ? (
            <Alert
              message="扫描进行中"
              description="请等待扫描完成后查看结果"
              type="info"
              showIcon
            />
          ) : (
            <Alert
              message="暂无扫描结果"
              description="请先开始一次扫描操作"
              type="warning"
              showIcon
            />
          )}
        </Card>
      ),
    },
  ]
  
  return (
    <div className="project-scan-updated">
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
      />
    </div>
  )
}