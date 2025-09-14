/**
 * 扫描页面 - Web版本
 * 集成真实数据和v2.1 API
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Button, Input, Card, Table, Space, Progress, Typography, Tag, App,
  Statistic, Row, Col, Divider, Alert, Select, Tooltip, Spin, Empty,
  Modal, Form, Checkbox
} from 'antd'
import {
  SearchOutlined, FolderOpenOutlined, SyncOutlined, FileTextOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined, PauseCircleOutlined,
  PlayCircleOutlined, StopOutlined, DeleteOutlined, EyeOutlined,
  SettingOutlined, ReloadOutlined
} from '@ant-design/icons'

// 导入新的API服务
import { scanApiService } from '../services/api/ScanApiService'
import { projectApiService } from '../services/api/ProjectApiService'
import type { 
  ScanStatus, 
  ScanResult, 
  ScanOptions, 
  Project,
  ProjectCreateRequest 
} from '../services/api/types'

// 全局状态管理
import { useAppStore } from '../stores/appStore'

const { Title, Text } = Typography
const { Option } = Select

interface ScanPageState {
  // 扫描配置
  scanDirectory: string
  selectedProject?: Project
  
  // 扫描状态
  activeScans: ScanStatus[]
  scanHistory: ScanStatus[]
  currentScan?: ScanStatus
  
  // 项目数据
  projects: Project[]
  
  // 统计信息
  scanStatistics: {
    total_scans: number
    active_scans: number
    success_rate: number
    avg_duration_ms: number
  }
  
  // 加载状态
  loading: boolean
  loadingStats: boolean
  loadingProjects: boolean
}

const ScanPageWeb: React.FC = () => {
  const { notification, modal } = App.useApp()
  
  // 状态管理
  const [state, setState] = useState<ScanPageState>({
    scanDirectory: '/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse/mods',
    activeScans: [],
    scanHistory: [],
    projects: [],
    scanStatistics: {
      total_scans: 0,
      active_scans: 0,
      success_rate: 0,
      avg_duration_ms: 0
    },
    loading: false,
    loadingStats: false,
    loadingProjects: false
  })

  // 智能扫描配置（内置，用户无需选择）
  const getSmartScanOptions = (hasExistingProject: boolean): ScanOptions => ({
    incremental: hasExistingProject, // 已建立项目自动增量扫描
    include_subdirectories: true,    // 扫描整合包需要扫描子目录
    validate_after_scan: true,       // 扫描后必须验证数据完整性
    generate_statistics: true        // 自动生成统计信息
  })

  // 表单实例
  const [form] = Form.useForm()
  const [newProjectForm] = Form.useForm()
  
  // 模态框状态
  const [showScanDetails, setShowScanDetails] = useState(false)
  const [selectedScanForDetails, setSelectedScanForDetails] = useState<ScanStatus | null>(null)

  // ============================================================
  // 数据加载
  // ============================================================

  // 初始化数据加载
  useEffect(() => {
    initializeData()
  }, [])

  const initializeData = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }))
    
    try {
      // 并行加载所有需要的数据
      await Promise.all([
        loadProjects(),
        loadScanStatistics(),
        loadActiveScans(),
        loadScanHistory()
      ])
      
      // 检查是否有进行中的扫描需要恢复
      await checkAndResumeActiveScans()
      
    } catch (error: any) {
      console.error('初始化数据加载失败:', error)
      notification.error({
        message: '数据加载失败',
        description: error.message || '无法加载扫描页面数据',
        duration: 5
      })
    } finally {
      setState(prev => ({ ...prev, loading: false }))
    }
  }, [])

  // 加载项目列表
  const loadProjects = async () => {
    setState(prev => ({ ...prev, loadingProjects: true }))
    
    try {
      const result = await projectApiService.getProjects({
        include_archived: false,
        include_statistics: true,
        limit: 50
      })
      
      if (result.success && result.data?.projects) {
        setState(prev => ({
          ...prev,
          projects: result.data.projects || []
        }))
      } else {
        throw new Error(result.error?.message || '加载项目失败')
      }
    } catch (error: any) {
      console.error('加载项目失败:', error)
      // 确保在错误时projects保持为空数组
      setState(prev => ({ 
        ...prev, 
        projects: []
      }))
    } finally {
      setState(prev => ({ ...prev, loadingProjects: false }))
    }
  }

  // 加载扫描统计
  const loadScanStatistics = async () => {
    setState(prev => ({ ...prev, loadingStats: true }))
    
    try {
      const result = await scanApiService.getScanStatistics(state.selectedProject?.project_id)
      
      if (result.success && result.data) {
        const totalScans = result.data!.total_scans || 0
        const successfulScans = result.data!.successful_scans || 0
        const avgDuration = result.data!.average_scan_duration_ms || 0
        
        setState(prev => ({
          ...prev,
          scanStatistics: {
            total_scans: totalScans,
            active_scans: result.data!.active_scans || 0,
            success_rate: totalScans > 0 ? (successfulScans / totalScans * 100) : 0,
            avg_duration_ms: avgDuration
          }
        }))
      }
    } catch (error: any) {
      console.error('加载扫描统计失败:', error)
    } finally {
      setState(prev => ({ ...prev, loadingStats: false }))
    }
  }

  // 加载活跃扫描
  const loadActiveScans = async () => {
    try {
      const result = await scanApiService.getActiveScans(state.selectedProject?.project_id)
      
      if (result.success && result.data) {
        setState(prev => ({
          ...prev,
          activeScans: result.data!
        }))
      }
    } catch (error: any) {
      console.error('加载活跃扫描失败:', error)
    }
  }

  // 加载扫描历史
  const loadScanHistory = async () => {
    try {
      const result = await scanApiService.getScanHistory(
        state.selectedProject?.project_id,
        1,
        20
      )
      
      if (result.success && result.data?.recent_scans) {
        setState(prev => ({
          ...prev,
          scanHistory: result.data.recent_scans || []
        }))
      } else {
        // API失败时确保scanHistory是空数组
        setState(prev => ({
          ...prev,
          scanHistory: []
        }))
      }
    } catch (error: any) {
      console.error('加载扫描历史失败:', error)
    }
  }

  // 检查并恢复活跃扫描
  const checkAndResumeActiveScans = async () => {
    const runningScans = state.activeScans.filter(scan => 
      scan.status === 'scanning' || scan.status === 'processing'
    )
    
    if (runningScans.length > 0) {
      const latestScan = runningScans[0]
      setState(prev => ({ ...prev, currentScan: latestScan }))
      
      notification.info({
        message: '检测到进行中的扫描',
        description: `正在监控扫描任务: ${latestScan.scan_id}`,
        duration: 3
      })
      
      // 开始轮询扫描状态
      startScanStatusPolling(latestScan.scan_id)
    }
  }

  // ============================================================
  // 扫描操作
  // ============================================================

  // 启动扫描 - 超级简化版本
  const startScan = () => {
    console.log('🔍 startScan 被点击了！')
    alert('扫描按钮被点击了！这是一个测试')
    
    // 简单的扫描逻辑
    const directory = state.scanDirectory || '/tmp'
    console.log('扫描目录:', directory)
    
    // 显示通知
    notification.info({
      message: '扫描功能测试',
      description: `准备扫描目录: ${directory}`,
      duration: 2
    })
    
    // 直接调用API
    setTimeout(async () => {
      try {
        console.log('发送API请求...')
        const response = await fetch('http://localhost:18000/api/v2.1/scan/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            directory: directory,
            incremental: true,
            options: { include_subdirectories: true }
          })
        })
        
        const result = await response.json()
        console.log('API响应:', result)
        
        notification.success({
          message: response.ok ? '扫描请求成功' : '扫描请求失败',
          description: result.message || JSON.stringify(result),
          duration: 5
        })
      } catch (error) {
        console.error('API调用失败:', error)
        notification.error({
          message: 'API调用失败',
          description: error.message,
          duration: 5
        })
      }
    }, 500)
  }

  // 扫描状态轮询
  const startScanStatusPolling = (scanId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const result = await scanApiService.getScanStatus(scanId)
        
        if (result.success && result.data) {
          const scanStatus = result.data
          setState(prev => ({ ...prev, currentScan: scanStatus }))
          
          // 检查扫描是否完成
          if (scanStatus.status === 'completed') {
            clearInterval(pollInterval)
            handleScanCompleted(scanStatus)
          } else if (scanStatus.status === 'failed' || scanStatus.status === 'cancelled') {
            clearInterval(pollInterval)
            handleScanFailed(scanStatus)
          }
        }
      } catch (error) {
        console.error('轮询扫描状态失败:', error)
        clearInterval(pollInterval)
      }
    }, 2000) // 每2秒轮询一次
    
    // 存储轮询ID以便清理
    setState(prev => ({ 
      ...prev, 
      currentScan: { ...prev.currentScan!, scan_id: scanId } as ScanStatus,
      // @ts-ignore - 临时存储轮询ID
      _pollInterval: pollInterval
    }))
  }

  // 扫描完成处理
  const handleScanCompleted = (scanStatus: ScanStatus) => {
    notification.success({
      message: '扫描完成',
      description: `发现 ${scanStatus.total_mods} 个MOD，${scanStatus.total_content_instances} 个内容实例`,
      duration: 5
    })
    
    // 刷新数据
    loadActiveScans()
    loadScanHistory()
    loadScanStatistics()
    
    setState(prev => ({ ...prev, currentScan: undefined }))
  }

  // 扫描失败处理
  const handleScanFailed = (scanStatus: ScanStatus) => {
    notification.error({
      message: scanStatus.status === 'failed' ? '扫描失败' : '扫描已取消',
      description: scanStatus.error || '扫描过程中发生错误',
      duration: 5
    })
    
    setState(prev => ({ ...prev, currentScan: undefined }))
  }

  // 取消扫描
  const cancelCurrentScan = async () => {
    if (!state.currentScan) return
    
    try {
      const result = await scanApiService.cancelScan(state.currentScan.scan_id, '用户手动取消')
      
      if (result.success && result.data) {
        notification.info({
          message: '扫描已取消',
          description: '正在停止扫描进程...'
        })
      } else {
        throw new Error(result.error?.message || '取消扫描失败')
      }
    } catch (error: any) {
      notification.error({
        message: '取消扫描失败',
        description: error.message
      })
    }
  }

  // ============================================================
  // 渲染组件
  // ============================================================

  // 扫描控制区域
  const renderScanControls = () => (
    <Card title="扫描控制">
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* 项目选择 */}
        <div>
          <Text strong>目标项目:</Text>
          <Select
            placeholder="选择项目"
            style={{ width: '100%', marginTop: 8 }}
            value={state.selectedProject?.project_id}
            onChange={(projectId) => {
              const project = state.projects?.find(p => p.project_id === projectId)
              setState(prev => ({ ...prev, selectedProject: project }))
            }}
            loading={state.loadingProjects}
          >
            {state.projects?.map(project => (
              <Option key={project.project_id} value={project.project_id}>
                {project.name} - {project.mc_version}
              </Option>
            )) || []}
          </Select>
          <Text type="secondary">
            扫描识别自动生成项目，无需手动创建
          </Text>
        </div>

        {/* 扫描目录 */}
        <div>
          <Text strong>扫描目录:</Text>
          <Input
            placeholder="输入要扫描的整合包路径..."
            value={state.scanDirectory}
            onChange={(e) => setState(prev => ({ ...prev, scanDirectory: e.target.value }))}
            style={{ marginTop: 8 }}
          />
          <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
            💡 智能扫描模式：{state.selectedProject ? '已有项目，将使用增量扫描' : '新项目，将进行全量扫描'} | 
            自动验证数据完整性 | 自动生成统计信息
          </div>
        </div>

        {/* 扫描按钮 */}
        <Row gutter={8}>
          <Col flex="auto">
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={startScan}
              loading={state.loading}
              disabled={!!state.currentScan}
              block
            >
              {state.currentScan ? '智能扫描进行中...' : '🤖 开始智能扫描'}
            </Button>
          </Col>
          {state.currentScan && (
            <Col>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={cancelCurrentScan}
              >
                取消
              </Button>
            </Col>
          )}
        </Row>
      </Space>
    </Card>
  )

  // 扫描进度区域
  const renderScanProgress = () => {
    if (!state.currentScan) return null

    const scan = state.currentScan
    const progressPercent = Math.round(scan.progress)

    return (
      <Card title="扫描进度">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Progress 
            percent={progressPercent} 
            status={scan.status === 'failed' ? 'exception' : 'active'}
            format={() => `${progressPercent}%`}
          />
          
          <Row gutter={16}>
            <Col span={6}>
              <Statistic 
                title="已处理文件" 
                value={scan.processed_files} 
                suffix={`/ ${scan.total_files}`}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title="发现MOD" 
                value={scan.total_mods}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title="内容实例" 
                value={scan.total_content_instances}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title="处理速度" 
                value={scan.files_per_second || 0}
                precision={1}
                suffix="文件/秒"
              />
            </Col>
          </Row>

          {scan.current_file && (
            <Alert
              message={`当前处理: ${scan.current_file}`}
              type="info"
              showIcon
             
            />
          )}

          {scan.phase_text && (
            <div>
              <Text type="secondary">当前阶段: {scan.phase_text}</Text>
            </div>
          )}
        </Space>
      </Card>
    )
  }

  // 扫描统计区域
  const renderScanStats = () => (
    <Card title="扫描统计" loading={state.loadingStats}>
      <Row gutter={16}>
        <Col span={6}>
          <Statistic
            title="总扫描次数"
            value={state.scanStatistics.total_scans}
            prefix={<FileTextOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="活跃扫描"
            value={state.scanStatistics.active_scans}
            prefix={<SyncOutlined spin={state.scanStatistics.active_scans > 0} />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="成功率"
            value={isNaN(state.scanStatistics.success_rate) ? 0 : state.scanStatistics.success_rate}
            precision={1}
            suffix="%"
            prefix={<CheckCircleOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="平均耗时"
            value={isNaN(state.scanStatistics.avg_duration_ms) ? 0 : (state.scanStatistics.avg_duration_ms / 1000)}
            precision={1}
            suffix="秒"
          />
        </Col>
      </Row>
    </Card>
  )

  // 扫描历史表格
  const renderScanHistory = () => {
    const columns = [
      {
        title: '扫描ID',
        dataIndex: 'scan_id',
        key: 'scan_id',
        width: 120,
        render: (id: string) => (
          <Text code style={{ fontSize: '12px' }}>
            {id.substring(0, 8)}...
          </Text>
        )
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 100,
        render: (status: string) => {
          const colors = {
            completed: 'success',
            failed: 'error',
            cancelled: 'warning',
            scanning: 'processing',
            processing: 'processing'
          }
          return <Tag color={colors[status as keyof typeof colors]}>{status}</Tag>
        }
      },
      {
        title: '进度',
        dataIndex: 'progress',
        key: 'progress',
        width: 100,
        render: (progress: number) => (
          <Progress percent={Math.round(progress)} />
        )
      },
      {
        title: '发现内容',
        key: 'discovered',
        width: 120,
        render: (record: ScanStatus) => (
          <Space>
            <Text>{record.total_mods} MOD</Text>
            <Text>{record.total_content_instances} 项</Text>
          </Space>
        )
      },
      {
        title: '开始时间',
        dataIndex: 'started_at',
        key: 'started_at',
        width: 120,
        render: (time: string) => new Date(time).toLocaleString()
      },
      {
        title: '操作',
        key: 'actions',
        width: 100,
        render: (record: ScanStatus) => (
          <Space>
            <Tooltip title="查看详情">
              <Button
               
                icon={<EyeOutlined />}
                onClick={() => {
                  setSelectedScanForDetails(record)
                  setShowScanDetails(true)
                }}
              />
            </Tooltip>
            {record.status !== 'completed' && record.status !== 'failed' && (
              <Tooltip title="取消扫描">
                <Button
                 
                  danger
                  icon={<StopOutlined />}
                  onClick={() => scanApiService.cancelScan(record.scan_id)}
                />
              </Tooltip>
            )}
          </Space>
        )
      }
    ]

    return (
      <Card 
        title="扫描历史" 
       
        extra={
          <Button 
            
            icon={<ReloadOutlined />}
            onClick={() => {
              loadScanHistory()
              loadActiveScans()
            }}
          >
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={[...(state.activeScans || []), ...(state.scanHistory || [])]}
          rowKey="scan_id"
         
          pagination={{ 
            pageSize: 10,
            showSizeChanger: false,
            showQuickJumper: false
          }}
          locale={{
            emptyText: <Empty description="暂无扫描记录" />
          }}
        />
      </Card>
    )
  }

  // 主渲染
  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>🤖 智能扫描中心</Title>
      <Text type="secondary">
        智能扫描Minecraft整合包，自动识别项目信息、模组版本、加载器类型，并生成项目配置
      </Text>
      
      <Divider />
      
      <Row gutter={[16, 16]}>
        {/* 左侧控制面板 */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {renderScanControls()}
            {renderScanStats()}
          </Space>
        </Col>
        
        {/* 右侧进度和历史 */}
        <Col xs={24} lg={16}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {renderScanProgress()}
            {renderScanHistory()}
          </Space>
        </Col>
      </Row>



      {/* 扫描详情模态框 */}
      <Modal
        title={`扫描详情 - ${selectedScanForDetails?.scan_id.substring(0, 8)}...`}
        open={showScanDetails}
        onCancel={() => setShowScanDetails(false)}
        footer={null}
        width={800}
        destroyOnHidden
      >
        {selectedScanForDetails && (
          <div>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="扫描ID" value={selectedScanForDetails.scan_id} />
              </Col>
              <Col span={12}>
                <Statistic 
                  title="状态" 
                  value={selectedScanForDetails.status}
                  valueRender={() => (
                    <Tag color={
                      selectedScanForDetails.status === 'completed' ? 'success' :
                      selectedScanForDetails.status === 'failed' ? 'error' : 'processing'
                    }>
                      {selectedScanForDetails.status}
                    </Tag>
                  )}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="总文件数" value={selectedScanForDetails.total_files} />
              </Col>
              <Col span={8}>
                <Statistic title="已处理" value={selectedScanForDetails.processed_files} />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="进度" 
                  value={Math.round(selectedScanForDetails.progress)}
                  suffix="%" 
                />
              </Col>
            </Row>
            
            <Divider />
            
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="发现MOD" value={selectedScanForDetails.total_mods} />
              </Col>
              <Col span={8}>
                <Statistic title="内容实例" value={selectedScanForDetails.total_content_instances} />
              </Col>
              <Col span={8}>
                <Statistic title="命名空间" value={selectedScanForDetails.total_namespaces} />
              </Col>
            </Row>
            
            {selectedScanForDetails.error && (
              <>
                <Divider />
                <Alert
                  message="错误信息"
                  description={selectedScanForDetails.error}
                  type="error"
                  showIcon
                />
              </>
            )}
            
            {selectedScanForDetails.warnings.length > 0 && (
              <>
                <Divider />
                <Alert
                  message="警告信息"
                  description={
                    <ul>
                      {selectedScanForDetails.warnings.map((warning, index) => (
                        <li key={index}>{warning}</li>
                      ))}
                    </ul>
                  }
                  type="warning"
                  showIcon
                />
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ScanPageWeb