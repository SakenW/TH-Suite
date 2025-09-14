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

  // 快速入口操作 - 优化后的工作流程
  const quickActions = [
    {
      key: 'new-project',
      title: '📂 新建项目',
      description: '选择整合包或 MOD 文件夹开始',
      icon: <ScanOutlined />,
      color: colors.primary,
      action: () => navigate('/scan'),
      primary: true,
      badge: '推荐',
      steps: ['选择文件夹', '自动扫描', '查看结果']
    },
    {
      key: 'continue-project',
      title: '📋 管理项目',
      description: '查看和管理已扫描的项目',
      icon: <FolderOpenOutlined />,
      color: colors.info,
      action: () => navigate('/projects/packs'),
      disabled: false, // 总是可用，即使没有项目也能查看空状态
      badge: recentProjects.length > 0 ? `${recentProjects.length}个项目` : '暂无项目'
    },
    {
      key: 'sync',
      title: '🔄 同步翻译',
      description: '与服务器同步获取最新翻译',
      icon: <SyncOutlined />,
      color: colors.warning,
      action: () => navigate('/sync'),
      disabled: !isOnline,
      badge: isOnline ? (syncStats?.pullable > 0 ? `${syncStats.pullable}条待拉取` : '已同步') : '离线',
      steps: ['检查更新', '拉取翻译', '应用修改']
    },
    {
      key: 'build',
      title: '🔨 构建文件',
      description: '生成最终的本地化文件',
      icon: <BuildOutlined />,
      color: colors.success,
      action: () => navigate('/build'),
      badge: '最后一步',
      steps: ['选择语言', '配置选项', '生成文件']
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
                      relative p-5 rounded-block border-2 transition-all duration-300 cursor-pointer
                      ${action.disabled ? 'opacity-60 cursor-not-allowed' : 'hover:-translate-y-1 hover:shadow-block'}
                      ${action.primary 
                        ? 'border-mc-emerald bg-mc-emerald/10 mc-block-shadow' 
                        : 'border-gray-200 hover:border-mc-emerald/50'
                      }
                    `}
                    onClick={action.disabled ? undefined : action.action}
                  >
                    {/* 角标徽章 */}
                    {action.badge && (
                      <div className={`absolute -top-2 -right-2 px-2 py-1 rounded-full text-xs font-medium
                        ${action.primary ? 'bg-mc-emerald text-white' : 'bg-blue-500 text-white'}
                      `}>
                        {action.badge}
                      </div>
                    )}

                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <div 
                          className={`text-3xl ${action.primary ? 'animate-glow' : ''}`}
                          style={{ color: action.color }}
                        >
                          {action.icon}
                        </div>
                        <div className="flex-1">
                          <Text 
                            strong 
                            className={`block ${action.primary ? 'text-mc-emerald text-xl' : 'text-lg'}`}
                          >
                            {action.title}
                          </Text>
                        </div>
                      </div>
                      
                      <Text type="secondary" className="text-sm block leading-relaxed">
                        {action.description}
                      </Text>

                      {/* 步骤提示 */}
                      {action.steps && !action.disabled && (
                        <div className="pt-2 border-t border-gray-100">
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            <ClockCircleOutlined />
                            <span>步骤:</span>
                            {action.steps.map((step, i) => (
                              <span key={i}>
                                {i > 0 && ' → '}
                                <span className="px-1.5 py-0.5 bg-gray-100 rounded">{step}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {action.disabled && (
                        <div className="pt-2 border-t border-gray-100">
                          <div className="flex items-center gap-2 text-xs text-orange-500">
                            <WarningOutlined />
                            <span>
                              {action.key === 'sync' && '需要网络连接'}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* 新手引导和工作流程说明 */}
              <div className="mt-8">
                <Divider>
                  <Text className="text-mc-emerald font-medium">🎯 工作流程指引</Text>
                </Divider>
                
                {recentProjects.length === 0 ? (
                  <Alert
                    message="欢迎使用 Trans-Hub MC 本地化工具！"
                    description={
                      <div className="space-y-3">
                        <Text>这是一个简单易用的本地化工具，只需三个步骤就能完成翻译工作：</Text>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                            <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">1</div>
                            <div>
                              <div className="font-medium text-blue-700">选择并扫描</div>
                              <div className="text-sm text-gray-600">选择整合包或MOD文件夹</div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
                            <div className="w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">2</div>
                            <div>
                              <div className="font-medium text-orange-700">同步翻译</div>
                              <div className="text-sm text-gray-600">从服务器获取最新翻译</div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                            <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">3</div>
                            <div>
                              <div className="font-medium text-green-700">构建文件</div>
                              <div className="text-sm text-gray-600">生成本地化资源文件</div>
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 p-3 bg-gradient-to-r from-mc-emerald/10 to-mc-grass/10 rounded-lg border border-mc-emerald/20">
                          <Text className="text-mc-emerald font-medium">💡 小贴士：</Text>
                          <Text className="text-sm text-gray-600 ml-2">
                            点击上方的 "📂 新建项目" 开始您的第一个本地化项目
                          </Text>
                        </div>
                      </div>
                    }
                    type="info"
                    showIcon
                    icon={<RocketOutlined />}
                    className="border-mc-lapis/30 bg-gradient-to-br from-blue-50 to-green-50"
                  />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="text-center">
                      <div className="text-2xl mb-2">✅</div>
                      <Text strong>项目已扫描</Text>
                      <br />
                      <Text type="secondary" className="text-sm">
                        {recentProjects.length} 个项目已准备就绪
                      </Text>
                    </Card>
                    
                    <Card className="text-center">
                      <div className="text-2xl mb-2">
                        {syncStats?.pullable > 0 ? '🔄' : '✅'}
                      </div>
                      <Text strong>翻译同步</Text>
                      <br />
                      <Text type="secondary" className="text-sm">
                        {syncStats?.pullable > 0 ? `${syncStats.pullable} 条待同步` : '已同步最新'}
                      </Text>
                    </Card>
                    
                    <Card className="text-center">
                      <div className="text-2xl mb-2">🔨</div>
                      <Text strong>准备构建</Text>
                      <br />
                      <Text type="secondary" className="text-sm">
                        可随时生成本地化文件
                      </Text>
                    </Card>
                  </div>
                )}
              </div>
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

            {/* 快速操作和最近任务 */}
            <Card
              title={
                <Space className="text-lg">
                  <HistoryOutlined className="text-mc-gold" />
                  <Text strong className="text-mc-gold">快速操作</Text>
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
                <div className="space-y-3">
                  <div className="text-center py-4">
                    <div className="text-4xl mb-2">🚀</div>
                    <Text type="secondary" className="text-sm">
                      还没有完成任务
                    </Text>
                  </div>
                  
                  <div className="space-y-2">
                    <Button 
                      block 
                      icon={<ScanOutlined />}
                      onClick={() => navigate('/scan')}
                      className="text-left"
                    >
                      新建扫描项目
                    </Button>
                    
                    <Button 
                      block 
                      icon={<FolderOpenOutlined />}
                      onClick={() => navigate('/projects/packs')}
                      variant="outline"
                      className="text-left"
                    >
                      查看现有项目
                    </Button>
                    
                    {isOnline && (
                      <Button 
                        block 
                        icon={<SyncOutlined />}
                        onClick={() => navigate('/sync')}
                        variant="outline"
                        disabled={!isOnline}
                        className="text-left"
                      >
                        同步翻译内容
                      </Button>
                    )}
                  </div>

                  <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <Text className="text-blue-700 font-medium text-sm">💡 使用提示</Text>
                    <div className="mt-2 text-xs text-blue-600 space-y-1">
                      <div>• 支持整合包和单独MOD文件夹</div>
                      <div>• 自动识别多种语言文件格式</div>
                      <div>• 实时同步最新翻译内容</div>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WelcomePage