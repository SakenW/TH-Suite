/**
 * 顶部状态条组件
 * 显示连接状态、快速指标、时间等信息
 */

import React from 'react'
import { 
  Layout, 
  Space, 
  Badge, 
  Typography, 
  Tag, 
  Tooltip, 
  Button,
  Divider 
} from 'antd'
import {
  CloudServerOutlined,
  UploadOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useTheme } from '../contexts/ThemeProvider'
import { useAppStore } from '../stores/appStore'
import dayjs from 'dayjs'

const { Header } = Layout
const { Text } = Typography

export const TopStatusBar: React.FC = () => {
  const { isDark, toggleTheme } = useTheme()
  
  // 真实状态数据
  const [isOnline, setIsOnline] = React.useState<boolean>(false)
  const [scanStats, setScanStats] = React.useState({ total: 0, translated: 0, isScanning: false })
  const [syncStats, setSyncStats] = React.useState({ pullable: 0, pushable: 0, isSyncing: false })
  const [lastScanTime, setLastScanTime] = React.useState<number | null>(null)
  const [lastSyncTime, setLastSyncTime] = React.useState<number | null>(null)

  // 检查连接状态和加载数据
  React.useEffect(() => {
    const checkStatus = async () => {
      try {
        const { ScanApiService, ModApiService } = await import('../services/api')
        const scanApi = new ScanApiService()
        const modApi = new ModApiService()
        
        // 测试连接 - 使用简单的测试端点
        const isConnected = await fetch('http://localhost:18000/api/v2.1/scan/test').then(r => r.ok).catch(() => false)
        setIsOnline(isConnected)
        
        if (isConnected) {
          // 获取快速统计 - 使用实际的API方法
          const [modsResponse, activeScans] = await Promise.allSettled([
            modApi.getModList({ page: 1, limit: 1 }),
            scanApi.getActiveScans()
          ])
          
          // 注意：ModApiService.getModList 直接返回 PaginatedResponse<ModInfo>，结构是 { items: ModInfo[], total, page, limit }
          const totalMods = modsResponse.status === 'fulfilled' ? (modsResponse.value?.items?.length || 0) : 0
          
          // 检查是否有真正在运行的扫描
          let actuallyScanning = false
          // 注意：ScanApiService.getActiveScans 返回 ServiceResult<ScanStatus[]>
          if (activeScans.status === 'fulfilled' && activeScans.value?.success && activeScans.value.data) {
            actuallyScanning = activeScans.value.data.some((scan: any) => 
              ['running', 'scanning', 'in_progress', 'queued'].includes(scan.status)
            )
          }
          
          setScanStats({
            total: totalMods,
            translated: 0, // 真实数据，无翻译
            isScanning: actuallyScanning
          })
          
          setSyncStats({
            pullable: 0, // 真实数据，无可拉取
            pushable: 0, // 真实数据，无待上传
            isSyncing: false
          })
          
          setLastScanTime(null) // 真实数据，无扫描记录
          setLastSyncTime(null) // 真实数据，无同步记录
        }
      } catch (error) {
        console.error('Failed to check status:', error)
        setIsOnline(false)
      }
    }
    
    checkStatus()
    const interval = setInterval(checkStatus, 10000) // 每10秒更新
    return () => clearInterval(interval)
  }, [])

  // 格式化时间显示
  const formatTime = (timestamp: number | null) => {
    if (!timestamp) return '从未'
    
    const now = dayjs()
    const time = dayjs(timestamp)
    const diff = now.diff(time, 'minute')
    
    if (diff < 1) return '刚刚'
    if (diff < 60) return `${diff}分钟前`
    if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
    if (diff < 10080) return `${Math.floor(diff / 1440)}天前`
    
    return time.format('MM-DD HH:mm')
  }

  return (
    <Header
      style={{
        background: isDark ? '#2A2A2A' : '#FFFFFF',
        borderBottom: `1px solid ${isDark ? '#404040' : '#E0E0E0'}`,
        padding: '0 24px',
        height: 64,
        lineHeight: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      }}
    >
      {/* 左侧：连接状态和快速指标 */}
      <Space size={24} align="center">
        {/* 连接状态 */}
        <Space>
          <Badge 
            status={isOnline ? 'success' : 'error'}
            dot
            style={{ 
              backgroundColor: isOnline ? '#52C41A' : '#FF4D4F',
              boxShadow: `0 0 4px ${isOnline ? '#52C41A' : '#FF4D4F'}`,
            }}
          />
          <Text strong style={{ color: isOnline ? '#52C41A' : '#FF4D4F' }}>
            {isOnline ? '✅ 已连接' : '⛔ 离线'}
          </Text>
        </Space>

        <Divider type="vertical" />

        {/* 快速指标 */}
        <Space size={16}>
          {/* 可拉取数量 */}
          <Tooltip title="服务器上可拉取的翻译数量">
            <Space size={4}>
              <DownloadOutlined style={{ color: '#1890FF' }} />
              <Text>
                可拉取 <Text type="success">{syncStats?.pullable || 0}</Text>
              </Text>
            </Space>
          </Tooltip>

          <Divider type="vertical" />

          {/* 待上传数量 */}
          <Tooltip title="本地待上传到服务器的内容数量">
            <Space size={4}>
              <UploadOutlined style={{ color: '#FF7A00' }} />
              <Text>
                待上传 <Text type="warning">{syncStats?.pushable || 0}</Text>
              </Text>
            </Space>
          </Tooltip>
        </Space>
      </Space>

      {/* 右侧：时间信息和操作按钮 */}
      <Space size={24} align="center">
        {/* 时间信息 */}
        <Space size={16}>
          <Tooltip title={`上次扫描时间：${lastScanTime ? dayjs(lastScanTime).format('YYYY-MM-DD HH:mm:ss') : '从未扫描'}`}>
            <Space size={4}>
              <ClockCircleOutlined style={{ color: '#666' }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                上次扫描 {formatTime(lastScanTime)}
              </Text>
            </Space>
          </Tooltip>

          <Divider type="vertical" />

          <Tooltip title={`上次同步时间：${lastSyncTime ? dayjs(lastSyncTime).format('YYYY-MM-DD HH:mm:ss') : '从未同步'}`}>
            <Space size={4}>
              <SyncOutlined style={{ color: '#666' }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                上次同步 {formatTime(lastSyncTime)}
              </Text>
            </Space>
          </Tooltip>
        </Space>

        {/* 主题切换按钮 */}
        <Tooltip title={`当前主题：${isDark ? '暗色' : '亮色'}，点击切换`}>
          <Button
            type="text"
            icon={isDark ? '🌙' : '☀️'}
            onClick={toggleTheme}
            style={{
              borderRadius: 4,
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
            }}
          />
        </Tooltip>

        {/* 状态指示器组 */}
        <Space>
          {/* 扫描状态 */}
          {scanStats?.isScanning && (
            <Tag color="processing" icon={<SyncOutlined spin />}>
              扫描中
            </Tag>
          )}

          {/* 同步状态 */}
          {syncStats?.isSyncing && (
            <Tag color="processing" icon={<SyncOutlined spin />}>
              同步中
            </Tag>
          )}

          {/* 服务器状态 */}
          {!isOnline && (
            <Tag color="error" icon={<CloudServerOutlined />}>
              离线模式
            </Tag>
          )}
        </Space>
      </Space>
    </Header>
  )
}

export default TopStatusBar