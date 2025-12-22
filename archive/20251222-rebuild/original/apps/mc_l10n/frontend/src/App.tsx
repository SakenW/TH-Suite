/**
 * 新版 App 组件
 * 完全基于 Ant Design + Minecraft 轻装饰主题
 */

import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Spin, Result, Button } from 'antd'
import toast, { Toaster } from 'react-hot-toast'

import { ThemeProvider } from './contexts/ThemeProvider'
import MainLayout from './layouts/MainLayout'

// 页面组件 - 新版本
import WelcomePage from './pages/WelcomePage'
import ScanPageWeb from './pages/ScanPageWeb'
import RealDataTestPage from './pages/RealDataTestPage'
// import MinecraftShowcase from './pages/MinecraftShowcase' // 暂时禁用
// import ProjectsPacksPage from './pages/ProjectsPacksPage' 
// import ProjectsModsPage from './pages/ProjectsModsPage'
// import ScanPage from './pages/ScanPageNew' // 暂时禁用 - Tauri依赖问题
// import DataViewPage from './pages/DataViewPage' // 暂时禁用 - 可能有依赖问题
// import SyncPage from './pages/SyncPage'
// import BuildPage from './pages/BuildPageNew'
// import ServerPage from './pages/ServerPageNew'
// import SettingsPage from './pages/SettingsPageNew'

// 临时占位符组件
const PlaceholderPage: React.FC<{ title: string }> = ({ title }) => (
  <div className="flex items-center justify-center h-full">
    <div className="text-center">
      <h2 className="text-2xl font-bold text-gray-600 mb-4">{title}</h2>
      <p className="text-gray-500">页面正在开发中...</p>
    </div>
  </div>
)

// 服务和存储
import { useAppStore } from './stores/appStore'
import { initializeTauri, storageService } from './services'

interface AppProps {
  onReady?: () => void
}

const App: React.FC<AppProps> = ({ onReady }) => {
  const [initError, setInitError] = useState<string | null>(null)
  
  // Store 状态
  const isInitialized = useAppStore(state => state.isInitialized)
  const isLoading = useAppStore(state => state.isLoading)
  const loadingMessage = useAppStore(state => state.loadingMessage)
  const initialize = useAppStore(state => state.initialize)

  // 初始化应用
  useEffect(() => {
    // 防止重复初始化
    if (isInitialized) {
      console.log('🔄 App already initialized, skipping...')
      onReady?.()
      return
    }

    let isCancelled = false

    const initApp = async () => {
      if (isCancelled || isInitialized) return

      try {
        console.log('🚀 Starting new app initialization...')

        // 1. 初始化 Tauri APIs
        console.log('📱 Initializing Tauri APIs...')
        await initializeTauri()
        if (isCancelled || isInitialized) return

        // 2. 初始化存储服务
        console.log('💾 Initializing storage service...')
        await storageService.init()
        if (isCancelled || isInitialized) return

        // 3. 初始化应用状态
        console.log('🏪 Initializing app store...')
        await initialize()
        if (isCancelled || isInitialized) return

        console.log('✅ App initialization complete')
        onReady?.()

        // 显示欢迎消息
        setTimeout(() => {
          toast.success('🎮 MC L10n 工具已就绪！', {
            duration: 3000,
            position: 'top-center',
          })
        }, 500)

      } catch (error) {
        if (!isCancelled) {
          console.error('❌ App initialization failed:', error)
          setInitError(error instanceof Error ? error.message : '未知错误')
          onReady?.() // 仍然调用以移除 HTML 加载器
        }
      }
    }

    initApp()

    return () => {
      isCancelled = true
    }
  }, [isInitialized, initialize, onReady])

  // 错误状态
  if (initError) {
    return (
      <ThemeProvider>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          minHeight: '100vh',
          padding: 24,
        }}>
          <Result
            status="error"
            title="应用初始化失败"
            subTitle={`初始化过程中发生错误: ${initError}`}
            extra={[
              <Button type="primary" key="retry" onClick={() => {
                setInitError(null)
                window.location.reload()
              }}>
                重新尝试
              </Button>,
              <Button key="details" onClick={() => {
                console.error('App initialization error:', initError)
                toast.error('错误详情已输出到控制台')
              }}>
                查看详情
              </Button>,
            ]}
          />
        </div>
      </ThemeProvider>
    )
  }

  // 加载状态
  if (!isInitialized) {
    return (
      <ThemeProvider>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          background: 'linear-gradient(145deg, #f5f5f5, #e8f5e8)',
        }}>
          {/* Logo 区域 */}
          <div style={{
            textAlign: 'center',
            marginBottom: 32,
            padding: 24,
            borderRadius: 8,
            background: 'rgba(76, 175, 80, 0.1)',
            border: '2px solid #4CAF50',
            boxShadow: '2px 2px 0 rgba(0,0,0,0.1)',
          }}>
            <h1 style={{
              fontSize: 32,
              margin: '0 0 8px 0',
              color: '#4CAF50',
              textShadow: '2px 2px 0 rgba(0,0,0,0.1)',
            }}>
              🎮 TH Suite MC L10n
            </h1>
            <p style={{
              fontSize: 16,
              margin: 0,
              color: '#666',
            }}>
              Minecraft 本地化工具
            </p>
          </div>

          {/* 加载指示器 */}
          <div style={{ textAlign: 'center' }}>
            <Spin size="large" />
            <div style={{ 
              marginTop: 16, 
              textAlign: 'center',
              color: '#666',
            }}>
              <div style={{ fontSize: 16, marginBottom: 4 }}>
                {loadingMessage || '正在初始化应用...'}
              </div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>
                首次启动可能需要几秒钟
              </div>
            </div>
          </div>

          {/* 调试信息 */}
          {true && (
            <div style={{
              position: 'fixed',
              bottom: 16,
              left: 16,
              padding: 12,
              background: 'rgba(0,0,0,0.8)',
              color: 'white',
              borderRadius: 4,
              fontSize: 12,
              fontFamily: 'monospace',
            }}>
              <div>initialized: {isInitialized.toString()}</div>
              <div>loading: {isLoading.toString()}</div>
              <div>message: {loadingMessage || 'null'}</div>
            </div>
          )}
        </div>
      </ThemeProvider>
    )
  }

  // 主应用界面
  return (
    <ThemeProvider>
      <BrowserRouter>
        <MainLayout>
          <Routes>
            {/* 主要路由 */}
            <Route path="/" element={<WelcomePage />} />
            {/* <Route path="/showcase" element={<MinecraftShowcase />} /> */}
            
            {/* 项目路由 */}
            <Route path="/projects/packs" element={<PlaceholderPage title="整合包项目" />} />
            <Route path="/projects/mods" element={<PlaceholderPage title="MOD 项目" />} />
            
            {/* 功能路由 */}
            <Route path="/scan" element={<ScanPageWeb />} />
            <Route path="/test" element={<RealDataTestPage />} />
            <Route path="/data" element={<PlaceholderPage title="数据查看" />} />
            <Route path="/sync" element={<PlaceholderPage title="同步中心" />} />
            <Route path="/build" element={<PlaceholderPage title="构建中心" />} />
            
            {/* 管理路由 */}
            <Route path="/server" element={<PlaceholderPage title="服务器状态" />} />
            <Route path="/settings" element={<PlaceholderPage title="设置" />} />
            
            {/* 重定向和 404 */}
            <Route path="/projects" element={<Navigate to="/projects/packs" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MainLayout>

        {/* 全局通知系统 */}
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#fff',
              color: '#333',
              border: '1px solid #ddd',
              borderRadius: '6px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            },
            success: {
              iconTheme: {
                primary: '#52C41A',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#FF4D4F',
                secondary: '#fff',
              },
            },
          }}
        />
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App