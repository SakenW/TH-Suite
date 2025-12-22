/**
 * 主布局组件
 * 基于设计文档的左侧导航 + 顶部状态条布局
 */

import React, { useState, useEffect } from 'react'
import {
  Layout,
  Menu,
  Badge,
  Typography,
  Space,
  Divider,
  Button,
  Tooltip,
} from 'antd'
import {
  HomeOutlined,
  FolderOutlined,
  ScanOutlined,
  SyncOutlined,
  BuildOutlined,
  CloudServerOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeProvider'
import { TopStatusBar } from '../components/TopStatusBar'
import { useAppStore } from '../stores/appStore'

const { Sider, Content } = Layout
const { Text } = Typography

// 导航菜单配置
const MENU_ITEMS = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: '欢迎页',
    path: '/',
  },
  {
    key: 'projects',
    label: '项目',
    icon: <FolderOutlined />,
    children: [
      {
        key: '/projects/packs',
        label: '整合包',
        path: '/projects/packs',
      },
      {
        key: '/projects/mods',
        label: 'MOD',
        path: '/projects/mods',
      },
    ],
  },
  {
    key: '/scan',
    icon: <ScanOutlined />,
    label: '扫描中心',
    path: '/scan',
  },
  {
    key: '/sync',
    icon: <SyncOutlined />,
    label: '同步中心',
    path: '/sync',
  },
  {
    key: '/build',
    icon: <BuildOutlined />,
    label: '构建中心',
    path: '/build',
  },
  {
    key: '/server',
    icon: <CloudServerOutlined />,
    label: '服务器状态',
    path: '/server',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '设置',
    path: '/settings',
  },
]

interface MainLayoutProps {
  children: React.ReactNode
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { isDark } = useTheme()
  const [collapsed, setCollapsed] = useState(false)
  
  // 从 store 获取状态 - 临时使用假数据
  const isOnline = true // useAppStore(state => state.isOnline) || false
  const recentProjects: any[] = [] // useAppStore(state => state.recentProjects) || []

  // 菜单点击处理
  const handleMenuClick = ({ key }: { key: string }) => {
    // 查找对应的路径
    const findPath = (items: typeof MENU_ITEMS, targetKey: string): string | null => {
      for (const item of items) {
        if (item.key === targetKey && item.path) {
          return item.path
        }
        if (item.children) {
          const childPath = findPath(item.children, targetKey)
          if (childPath) return childPath
        }
      }
      return null
    }

    const path = findPath(MENU_ITEMS, key)
    if (path) {
      navigate(path)
    }
  }

  // 获取当前选中的菜单项
  const getSelectedKeys = (): string[] => {
    const currentPath = location.pathname
    
    // 精确匹配
    for (const item of MENU_ITEMS) {
      if (item.path === currentPath) {
        return [item.key]
      }
      if (item.children) {
        for (const child of item.children) {
          if (child.path === currentPath) {
            return [child.key]
          }
        }
      }
    }

    // 模糊匹配
    if (currentPath.startsWith('/projects/')) {
      if (currentPath.includes('pack')) return ['/projects/packs']
      if (currentPath.includes('mod')) return ['/projects/mods']
      return ['projects']
    }

    return ['/']
  }

  // 获取展开的菜单项
  const getOpenKeys = (): string[] => {
    const currentPath = location.pathname
    
    if (currentPath.startsWith('/projects/')) {
      return ['projects']
    }

    return []
  }

  // 侧边栏宽度
  const siderWidth = collapsed ? 80 : 240

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 左侧导航栏 */}
      <Sider 
        width={240}
        collapsed={collapsed}
        theme={isDark ? 'dark' : 'light'}
        style={{
          background: isDark ? '#1F1F1F' : '#FFFFFF',
          borderRight: `1px solid ${isDark ? '#404040' : '#E0E0E0'}`,
          position: 'relative',
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            margin: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            borderRadius: 6,
            background: isDark 
              ? 'linear-gradient(145deg, rgba(92, 191, 96, 0.1), rgba(139, 195, 74, 0.1))'
              : 'linear-gradient(145deg, rgba(76, 175, 80, 0.1), rgba(139, 195, 74, 0.1))',
            border: `2px solid ${isDark ? '#5CBF60' : '#4CAF50'}`,
            boxShadow: '2px 2px 0 rgba(0,0,0,0.1)',
            position: 'relative',
          }}
        >
          {!collapsed ? (
            <Space direction="vertical" size={0}>
              <Text 
                strong 
                style={{ 
                  fontSize: 16, 
                  color: isDark ? '#5CBF60' : '#4CAF50',
                  textShadow: '1px 1px 0 rgba(0,0,0,0.1)',
                }}
              >
                🎮 MC L10n
              </Text>
              <Text 
                type="secondary" 
                style={{ 
                  fontSize: 10, 
                  lineHeight: 1,
                  opacity: 0.8,
                }}
              >
                本地化工具
              </Text>
            </Space>
          ) : (
            <Text style={{ fontSize: 20 }}>🎮</Text>
          )}
        </div>

        {/* 折叠按钮 */}
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => setCollapsed(!collapsed)}
          style={{
            position: 'absolute',
            top: 20,
            right: 8,
            zIndex: 10,
            width: 24,
            height: 24,
            minWidth: 24,
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 2,
          }}
        />

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          items={MENU_ITEMS.map(item => ({
            ...item,
            label: (
              <Space>
                {item.label}
                {/* 状态徽章 */}
                {item.key === '/sync' && !isOnline && (
                  <Badge status="warning" />
                )}
                {item.key === 'projects' && recentProjects.length > 0 && (
                  <Badge count={recentProjects.length} size="small" />
                )}
              </Space>
            ),
            children: item.children?.map(child => ({
              ...child,
              label: child.label,
            })),
          }))}
          onClick={handleMenuClick}
          style={{
            border: 'none',
            marginTop: 8,
          }}
        />

        {/* 底部信息 */}
        {!collapsed && (
          <div
            style={{
              position: 'absolute',
              bottom: 16,
              left: 16,
              right: 16,
            }}
          >
            <Divider style={{ margin: '8px 0' }} />
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Space>
                <Badge 
                  status={isOnline ? 'success' : 'error'} 
                  text={
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {isOnline ? '已连接' : '离线'}
                    </Text>
                  }
                />
              </Space>
              <Text type="secondary" style={{ fontSize: 11, opacity: 0.6 }}>
                v6.0.0 | Trans-Hub Suite
              </Text>
            </Space>
          </div>
        )}
      </Sider>

      {/* 主内容区域 */}
      <Layout>
        {/* 顶部状态条 */}
        <TopStatusBar />

        {/* 内容区域 */}
        <Content
          style={{
            padding: 0,
            minHeight: 'calc(100vh - 64px)', // 减去顶部状态条高度
            background: isDark ? '#1F1F1F' : '#F5F5F5',
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout