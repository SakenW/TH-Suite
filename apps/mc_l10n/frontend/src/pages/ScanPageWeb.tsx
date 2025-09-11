import React, { useState, useEffect } from 'react'
import {
  Button, Input, Card, Table, Space, Progress, Typography, Tag, App,
  Statistic, Row, Col, Divider, Alert
} from 'antd'
import {
  SearchOutlined, FolderOpenOutlined, SyncOutlined, FileTextOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined
} from '@ant-design/icons'
import { useAppStore } from '../stores/appStore'
import { scanApi, v6ApiClient } from '../services/api'

const { Title, Text } = Typography

interface ProjectInfo {
  id: string
  name: string
  type: 'mod' | 'resourcepack'
  files_count: number
  entries_count: number
  status: 'scanned' | 'scanning' | 'error'
}

const ScanPageWeb: React.FC = () => {
  const { notification } = App.useApp()
  const [scanPath, setScanPath] = useState('/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse/mods')
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [stats, setStats] = useState({
    totalProjects: 0,
    totalFiles: 0,
    totalEntries: 0
  })

  // 使用全局状态管理
  const scanState = useAppStore(state => state.scanState)
  const startScan = useAppStore(state => state.startScan)
  const updateScanProgress = useAppStore(state => state.updateScanProgress)
  const completeScan = useAppStore(state => state.completeScan)
  const cancelScan = useAppStore(state => state.cancelScan)
  const clearScan = useAppStore(state => state.clearScan)
  const setScanStatus = useAppStore(state => state.setScanStatus)

  // 从状态中提取需要的值
  const isScanning = scanState.isScanning
  const scanProgress = scanState.progress
  const activeScanId = scanState.scanId

  // 加载初始数据
  useEffect(() => {
    loadRealData()
    checkActiveScans()
  }, [])

  // 监听扫描状态变化
  useEffect(() => {
    if (scanState.scanId && scanState.isScanning) {
      pollScanStatus(scanState.scanId)
    }
  }, [scanState.scanId, scanState.isScanning])

  // 检查后台活跃扫描任务
  const checkActiveScans = async () => {
    try {
      const activeScansResponse = await scanApi.getActiveScans()
      if (activeScansResponse.success && activeScansResponse.active_scans?.length > 0) {
        const runningScans = activeScansResponse.active_scans.filter((scan: any) => 
          scan.status === 'scanning' || scan.status === 'running'
        )
        
        if (runningScans.length > 0) {
          const latestScan = runningScans[runningScans.length - 1]
          console.log('🔄 恢复活跃扫描:', latestScan.id)
          
          // 恢复扫描状态
          startScan(latestScan.id, latestScan.directory || scanPath)
          
          notification.info({
            message: '检测到进行中的扫描',
            description: `正在恢复扫描任务: ${latestScan.id}`,
            duration: 3
          })
        }
      }
    } catch (error) {
      console.log('ℹ️ 无活跃扫描任务需要恢复')
    }
  }

  const loadRealData = async () => {
    try {
      // 1. 测试后端连接
      const connectionTest = await scanApi.testConnection()
      if (!connectionTest.success) {
        throw new Error('后端连接失败')
      }

      // 2. 加载MOD列表 (暂时跳过统计数据，因为有错误)
      const modsResponse = await v6ApiClient.getMods({ page: 1, limit: 5 })

      console.log('📦 模组数据:', modsResponse)

      if (!modsResponse || !modsResponse.mods) {
        throw new Error('数据加载失败')
      }

      // 3. 获取显示数据（更多MOD）
      const displayModsResponse = await v6ApiClient.getMods({ page: 1, limit: 20 })

      // 转换MOD数据为ProjectInfo格式
      const realProjects: ProjectInfo[] = displayModsResponse.mods ? displayModsResponse.mods.map(mod => ({
        id: mod.uid,
        name: mod.name || mod.modid,
        type: 'mod' as const,
        files_count: 0,
        entries_count: 0,
        status: 'scanned' as const
      })) : []

      // 4. 设置状态
      const stats = {
        totalProjects: displayModsResponse.pagination?.total || realProjects.length,
        totalFiles: 0, // 暂时设为0，因为统计端点有错误
        totalEntries: 0  // 暂时设为0，因为统计端点有错误
      }

      setProjects(realProjects)
      setStats(stats)
      
      console.log('✅ 数据加载完成')

    } catch (error) {
      console.error('❌ 数据加载失败:', error)
      
      // 显示错误通知
      notification.error({
        message: '数据加载失败',
        description: `无法从后端加载数据: ${error instanceof Error ? error.message : '未知错误'}`,
        duration: 5
      })

      // 加载fallback数据
      loadFallbackData()
    }
  }

  const loadFallbackData = () => {
    // 不再显示演示数据，显示真实的空状态
    setProjects([])
    setStats({ totalProjects: 0, totalFiles: 0, totalEntries: 0 })
  }

  // 轮询扫描状态
  const pollScanStatus = async (scanId: string) => {
    const pollStatus = async () => {
      try {
        const status = await scanApi.getScanStatus(scanId)
        
        if (status.status === 'completed') {
          // 扫描完成
          completeScan(status)
          await loadRealData() // 刷新数据
          
          notification.success({
            message: '扫描完成！',
            description: `找到 ${status.stats?.mods || 0} 个模组，${status.stats?.language_files || 0} 个语言文件`,
            duration: 5
          })
          
          return // 停止轮询
        } else if (status.status === 'failed') {
          // 扫描失败
          cancelScan()
          
          notification.error({
            message: '扫描失败',
            description: status.error || '扫描过程中发生错误',
            duration: 5
          })
          
        } else if (status.status === 'scanning' || status.status === 'running') {
          // 继续扫描，更新进度
          updateScanProgress(status.progress || 0, status.current_file, status)
        }
      } catch (error) {
        console.error('获取扫描状态失败:', error)
        
        // 扫描状态获取失败，停止轮询
        cancelScan()
        notification.error({
          message: '扫描状态更新失败',
          description: '无法获取扫描进度，请检查网络连接',
          duration: 3
        })
      }
    }

    // 立即执行一次，然后每2秒轮询一次
    await pollStatus()
    const interval = setInterval(pollStatus, 2000)
    
    // 在组件卸载时清理定时器
    return () => clearInterval(interval)
  }

  // 开始扫描
  const handleScan = async () => {
    if (!scanPath.trim()) {
      notification.error({
        message: '路径不能为空',
        description: '请输入要扫描的目录路径'
      })
      return
    }

    try {
      console.log('🔍 开始扫描:', scanPath)

      // 准备扫描请求
      const scanRequest = {
        directory: scanPath.trim(),
        incremental: true
      }

      console.log('📝 扫描请求:', scanRequest)

      // 发送扫描请求
      const scanResult = await scanApi.startScan(scanRequest)

      if (!scanResult.scan_id) {
        throw new Error('扫描启动失败：未返回扫描ID')
      }

      const scanId = scanResult.scan_id

      // 更新状态
      startScan(scanId, scanPath)

      notification.success({
        message: '扫描已启动',
        description: `扫描ID: ${scanId}`,
        duration: 3
      })

      // 开始轮询扫描状态
      pollScanStatus(scanId)

    } catch (error) {
      console.error('❌ 扫描启动失败:', error)
      
      notification.error({
        message: '扫描启动失败',
        description: error instanceof Error ? error.message : '未知错误',
        duration: 5
      })
    }
  }

  // 在Web版本中提供文件夹选择的替代方案
  const handleSelectFolder = () => {
    // 在Web环境中，我们可以提供一些常用路径的快捷选择
    const commonPaths = [
      '/tmp/test_mods', // 测试路径
      '/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse/mods', // 真实Minecraft模组目录
      '/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse', // 真实Minecraft实例目录
      '/home/saken/minecraft/mods',
      '/home/saken/Downloads/mods'
    ]
    
    // 简单的路径选择
    setScanPath(commonPaths[Math.floor(Math.random() * commonPaths.length)])
  }

  const columns = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: ProjectInfo) => (
        <Space>
          <FileTextOutlined />
          <span>{text}</span>
          <Tag color={record.type === 'mod' ? 'blue' : 'green'}>
            {record.type === 'mod' ? 'MOD' : '资源包'}
          </Tag>
        </Space>
      )
    },
    {
      title: '文件数量',
      dataIndex: 'files_count',
      key: 'files_count',
      render: (count: number) => <Text strong>{count}</Text>
    },
    {
      title: '翻译条目',
      dataIndex: 'entries_count', 
      key: 'entries_count',
      render: (count: number) => <Text type="success">{count.toLocaleString()}</Text>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = {
          scanned: { color: 'success', icon: <CheckCircleOutlined />, text: '已扫描' },
          scanning: { color: 'processing', icon: <SyncOutlined spin />, text: '扫描中' },
          error: { color: 'error', icon: <ExclamationCircleOutlined />, text: '错误' }
        }[status] || { color: 'default', icon: null, text: status }
        
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        )
      }
    }
  ]

  return (
    <div className="p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <Title level={2}>📂 扫描中心</Title>
        <Text type="secondary">
          扫描 Minecraft MOD 和资源包，提取翻译文件进行本地化处理
        </Text>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} className="mb-6">
        <Col span={8}>
          <Card>
            <Statistic 
              title="项目总数" 
              value={stats.totalProjects}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic 
              title="语言文件" 
              value={stats.totalFiles}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic 
              title="翻译条目" 
              value={stats.totalEntries}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 扫描控制 */}
      <Card title="扫描控制" className="mb-6">
        <Space.Compact className="w-full mb-4">
          <Input
            placeholder="输入要扫描的目录路径"
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
            className="flex-1"
          />
          <Button 
            icon={<FolderOpenOutlined />}
            onClick={handleSelectFolder}
            title="选择常用路径"
          >
            选择
          </Button>
        </Space.Compact>
        
        <Space>
          <Button
            type="primary"
            icon={isScanning ? <SyncOutlined spin /> : <SearchOutlined />}
            onClick={handleScan}
            loading={isScanning}
            disabled={isScanning || !scanPath.trim()}
          >
            {isScanning ? '扫描中...' : '开始扫描'}
          </Button>
          
          {isScanning && (
            <Button
              onClick={() => cancelScan()}
              disabled={!isScanning}
            >
              取消扫描
            </Button>
          )}
        </Space>

        {/* 扫描进度 */}
        {isScanning && (
          <div className="mt-4">
            <Text className="block mb-2">扫描进度：</Text>
            <Progress
              percent={Math.round(scanProgress)}
              status={scanProgress >= 100 ? 'success' : 'active'}
            />
            <Text type="secondary" className="block mt-2">
              扫描ID: {activeScanId} | 当前文件: {scanState.currentFile || '准备中...'}
            </Text>
          </div>
        )}
      </Card>

      {/* 项目列表 */}
      <Card title="项目列表">
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `显示 ${range[0]}-${range[1]} 条，共 ${total} 条项目`
          }}
        />
      </Card>
    </div>
  )
}

export default ScanPageWeb