/**
 * 欢迎页
 * 基于设计文档规范：工具介绍 + 快速入口 + 最近任务 + 连接卡片
 */

import React, { useEffect, useState } from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Typography,
  Badge,
  Divider,
  Progress,
  List,
  Tag,
  Tooltip,
  Empty,
  Statistic,
  Alert,
} from 'antd'
import {
  ScanOutlined,
  SyncOutlined,
  BuildOutlined,
  FolderOpenOutlined,
  CloudServerOutlined,
  RocketOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeProvider'
import { useAppStore } from '../stores/appStore'
import { mcDecorationStyles } from '../theme/minecraft'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

// 启用相对时间插件
dayjs.extend(relativeTime)

const { Title, Text, Paragraph } = Typography

export const WelcomePage: React.FC = () => {
  const navigate = useNavigate()
  const { isDark, colors } = useTheme()
  
  // Store 状态 - 使用假数据或安全访问
  const isOnline = true // useAppStore(state => state.isOnline) || false
  const recentProjects: any[] = [] // useAppStore(state => state.recentProjects) || []
  const lastScanTime = null // useAppStore(state => state.lastScanTime)
  const lastSyncTime = null // useAppStore(state => state.lastSyncTime)
  const scanStats = { total: 0, translated: 0 } // useAppStore(state => state.scanStats)
  const syncStats = { pullable: 0, pushable: 0 } // useAppStore(state => state.syncStats)

  // 最近任务数据 (真实数据)
  const [recentTasks] = useState([])

  // 快速入口操作
  const quickActions = [
    {
      key: 'new-project',
      title: '① 新建项目并扫描',
      description: '选择整合包或 MOD 开始扫描',
      icon: <ScanOutlined />,
      color: colors.primary,
      action: () => navigate('/scan'),
      primary: true,
    },
    {
      key: 'rescan',
      title: '② 重扫最近项目',
      description: '重新扫描最近打开的项目',
      icon: <FolderOpenOutlined />,
      color: colors.info,
      action: () => {
        // TODO: 实现重扫逻辑
        navigate('/projects/packs')
      },
      disabled: recentProjects.length === 0,
    },
    {
      key: 'sync',
      title: '③ 去同步',
      description: '与服务器同步翻译内容',
      icon: <SyncOutlined />,
      color: colors.warning,
      action: () => navigate('/sync'),
      disabled: !isOnline,
    },
    {
      key: 'build',
      title: '④ 去构建',
      description: '生成本地化产物文件',
      icon: <BuildOutlined />,
      color: colors.success,
      action: () => navigate('/build'),
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-green-50 to-yellow-50 mc-grid-bg">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {/* 主欢迎区 */}
        <div className="mb-8">
          <Card
            className="minecraft-card bg-gradient-to-br from-mc-emerald/10 to-mc-grass/5 border-2 border-mc-emerald/30 animate-float"
            style={{ 
              background: isDark 
                ? 'linear-gradient(145deg, rgba(92, 191, 96, 0.1), rgba(139, 195, 74, 0.05))'
                : 'linear-gradient(145deg, rgba(76, 175, 80, 0.1), rgba(139, 195, 74, 0.05))',
              ...mcDecorationStyles.pixelCard,
            }}
          >
            <div className="text-center py-8">
              <div className="text-6xl mb-6 animate-float">🎮</div>
              <Title 
                level={1} 
                className="text-mc-emerald neon-glow mb-6"
                style={{ 
                  margin: '0 0 24px 0',
                  textShadow: '2px 2px 0 rgba(0,0,0,0.1)',
                }}
              >
                Trans-Hub MC 本地化工具
              </Title>
              <div className="mb-8">
                <Paragraph className="text-lg leading-relaxed text-gray-700">
                  这是一把"找翻译→对齐服务器→拉回结果→生成本地化文件"的顺手小工具。
                  <br />
                  服务器（Trans-Hub）负责去重、审核、回传。你专心"扫描→同步→构建"即可。
                </Paragraph>
              </div>

              {/* 快速统计 - 使用响应式网格 */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6 justify-center">
                <div className="glass-effect p-4 rounded-block text-center animate-pixel-fade">
                  <div className="text-3xl text-mc-emerald mb-2">
                    <FolderOpenOutlined />
                  </div>
                  <Statistic
                    title="最近项目"
                    value={recentProjects.length}
                    suffix="个"
                    valueStyle={{ color: colors.primary, fontSize: '24px' }}
                  />
                </div>
                
                <div className="glass-effect p-4 rounded-block text-center animate-pixel-fade">
                  <div className="text-3xl text-mc-lapis mb-2">
                    <SyncOutlined />
                  </div>
                  <Statistic
                    title="可拉取"
                    value={syncStats?.pullable || 0}
                    suffix="条"
                    valueStyle={{ color: colors.info, fontSize: '24px' }}
                  />
                </div>
                
                <div className="glass-effect p-4 rounded-block text-center animate-pixel-fade">
                  <div className="text-3xl text-mc-gold mb-2">
                    <CloudServerOutlined />
                  </div>
                  <Statistic
                    title="待上传"
                    value={syncStats?.pushable || 0}
                    suffix="条"
                    valueStyle={{ color: colors.warning, fontSize: '24px' }}
                  />
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* 主要内容区域 - 使用响应式网格 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
          {/* 快速入口 */}
          <div className="lg:col-span-2">
            <Card 
              title={
                <Space className="text-lg">
                  <RocketOutlined className="text-mc-emerald" />
                  <Text strong className="text-mc-emerald">快速入口</Text>
                </Space>
              }
              className="minecraft-card mb-6 shadow-depth"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {quickActions.map((action, index) => (
                  <div
                    key={action.key}
                    className={`
                      p-4 rounded-block border-2 transition-all duration-300 cursor-pointer
                      ${action.disabled ? 'opacity-60 cursor-not-allowed' : 'hover:-translate-y-1 hover:shadow-block'}
                      ${action.primary 
                        ? 'border-mc-emerald bg-mc-emerald/10 mc-block-shadow' 
                        : 'border-gray-200 hover:border-mc-emerald/50'
                      }
                    `}
                    onClick={action.disabled ? undefined : action.action}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center gap-3">
                        <div 
                          className={`text-2xl ${action.primary ? 'animate-glow' : ''}`}
                          style={{ color: action.color }}
                        >
                          {action.icon}
                        </div>
                        <div className="flex-1">
                          <Text 
                            strong 
                            className={`block ${action.primary ? 'text-mc-emerald text-lg' : 'text-base'}`}
                          >
                            {action.title}
                          </Text>
                          {action.primary && (
                            <Tag 
                              color="success" 
                              size="small" 
                              className="mt-1 animate-pulse-slow"
                            >
                              推荐
                            </Tag>
                          )}
                        </div>
                      </div>
                      
                      <Text type="secondary" className="text-sm block">
                        {action.description}
                      </Text>
                      
                      {action.disabled && (
                        <Text type="secondary" className="text-xs opacity-60 block">
                          {action.key === 'rescan' && '暂无最近项目'}
                          {action.key === 'sync' && '需要网络连接'}
                        </Text>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* 三步引导（空态时显示） */}
              {recentProjects.length === 0 && (
                <div className="mt-6">
                  <Divider />
                  <Alert
                    message="新用户指引"
                    description={
                      <div>
                        <Text>首次使用？跟着这三步开始：</Text>
                        <ol className="mt-2 mb-0 text-sm">
                          <li>选一个整合包或 MOD 文件夹</li>
                          <li>一键扫描识别语言文件</li>
                          <li>拉取翻译并生成本地化文件</li>
                        </ol>
                      </div>
                    }
                    type="info"
                    showIcon
                    icon={<InfoCircleOutlined />}
                    className="rounded-block border-mc-lapis/30 bg-mc-lapis/5"
                  />
                </div>
              )}
            </Card>
          </div>

          {/* 右侧信息栏 */}
          <div className="space-y-6">
            {/* 连接状态卡片 */}
            <Card
              title={
                <Space className="text-lg">
                  <CloudServerOutlined className="text-mc-lapis" />
                  <Text strong className="text-mc-lapis">连接状态</Text>
                </Space>
              }
              className="minecraft-card shadow-depth"
            >
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className={`status-dot ${isOnline ? 'online' : 'offline'}`}></div>
                  <Text 
                    strong 
                    className={`text-lg ${isOnline ? 'text-mc-grass' : 'text-mc-stone'}`}
                  >
                    {isOnline ? '在线' : '离线'}
                  </Text>
                </div>
                
                {isOnline ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Text type="secondary">服务器版本:</Text>
                      <Text strong className="text-mc-emerald">V6.0.0</Text>
                    </div>
                    <div className="flex items-center gap-2">
                      <Text type="secondary">可拉取/待上传:</Text>
                      <Text className="text-mc-lapis font-bold">{syncStats?.pullable || 0}</Text>
                      <Text type="secondary">/</Text>
                      <Text className="text-mc-gold font-bold">{syncStats?.pushable || 0}</Text>
                    </div>
                  </div>
                ) : (
                  <Text type="secondary" className="block">
                    离线模式，部分功能受限
                  </Text>
                )}
              </div>
            </Card>

            {/* 最近任务 */}
            <Card
              title={
                <Space className="text-lg">
                  <HistoryOutlined className="text-mc-gold" />
                  <Text strong className="text-mc-gold">最近任务</Text>
                </Space>
              }
              className="minecraft-card shadow-depth"
            >
              {recentTasks.length > 0 ? (
                <div className="space-y-4">
                  {recentTasks.map((task) => (
                    <div 
                      key={task.id}
                      className="p-3 rounded-pixel bg-gray-50/50 border border-gray-200/50 hover:bg-gray-100/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <div className="text-mc-emerald">
                              {task.type === 'scan' && <ScanOutlined />}
                              {task.type === 'sync' && <SyncOutlined />}
                              {task.type === 'build' && <BuildOutlined />}
                            </div>
                            <Text className="text-sm font-medium line-clamp-1">
                              {task.title}
                            </Text>
                            <CheckCircleOutlined className="text-mc-grass" />
                          </div>
                          <Text 
                            type="secondary" 
                            className="text-xs block line-clamp-2"
                          >
                            {task.details}
                          </Text>
                        </div>
                        <div className="text-right min-w-16">
                          <Text type="secondary" className="text-xs">
                            {dayjs(task.time).fromNow()}
                          </Text>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="暂无最近任务"
                  className="py-8"
                />
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WelcomePage