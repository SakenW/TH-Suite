import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Box } from '@mui/material'

import LayoutMinecraft from '@components/Layout/LayoutMinecraft'
import { useAppStore } from '@stores/appStore'
import { initializeTauri } from '@services'
import { lazyLoad, preloadComponents } from '@utils/lazyLoad'

// 立即加载的核心页面
import HomePageMinecraft from '@pages/HomePageMinecraft'

// 懒加载其他页面
const ScanPageMinecraft = lazyLoad(() => import('@pages/ScanPageMinecraft'))
const ProjectPageMinecraft = lazyLoad(() => import('@pages/ProjectPageMinecraft'))
const SettingsPageMinecraft = lazyLoad(() => import('@pages/SettingsPageMinecraft'))
const ExtractPageMinecraft = lazyLoad(() => import('@pages/ExtractPageMinecraft'))
const ExportPageMinecraft = lazyLoad(() => import('@pages/ExportPageMinecraft'))
const TransferPageMinecraft = lazyLoad(() => import('@pages/TransferPageMinecraft'))
const BuildPageMinecraft = lazyLoad(() => import('@pages/BuildPageMinecraft'))
const LocalDataPageMinecraft = lazyLoad(() => import('@pages/LocalDataPageMinecraft'))
const SecurityPageMinecraft = lazyLoad(() => import('@pages/SecurityPageMinecraft'))
const ServerPageMinecraft = lazyLoad(() => import('@pages/ServerPageMinecraft'))
const ProgressTestPage = lazyLoad(() => import('@pages/ProgressTestPage'))

interface AppProps {
  onReady?: () => void
}

function App({ onReady }: AppProps) {
  const isInitialized = useAppStore(state => state.isInitialized)
  const isLoading = useAppStore(state => state.isLoading)
  const loadingMessage = useAppStore(state => state.loadingMessage)
  const initialize = useAppStore(state => state.initialize)

  useEffect(() => {
    // 预加载常用页面
    if (isInitialized) {
      preloadComponents([
        () => import('@pages/ScanPageMinecraft'),
        () => import('@pages/ProjectPageMinecraft'),
        () => import('@pages/SettingsPageMinecraft'),
      ])
    }
  }, [isInitialized])

  useEffect(() => {
    if (isInitialized) {
      onReady?.()
      return
    }

    let isCancelled = false

    const initApp = async () => {
      if (isCancelled || isInitialized) return

      try {
        await initializeTauri()
        if (isCancelled || isInitialized) return

        const result = await initialize()
        if (isCancelled || isInitialized) return

        onReady?.()
      } catch (error) {
        if (!isCancelled) {
          console.error('Failed to initialize app:', error)
          onReady?.()
        }
      }
    }

    initApp()

    return () => {
      isCancelled = true
    }
  }, [isInitialized, initialize, onReady])

  if (!isInitialized) {
    return (
      <Box
        display='flex'
        flexDirection='column'
        justifyContent='center'
        alignItems='center'
        height='100vh'
        bgcolor='background.default'
        sx={{ color: 'text.primary' }}
      >
        <Box textAlign='center' mb={2}>
          <h2>🎮 TH Suite MC L10n</h2>
          <p>Minecraft 本地化工具</p>
        </Box>

        {isLoading ? (
          <Box textAlign='center'>
            <div
              className='loading-spinner'
              style={{
                width: '40px',
                height: '40px',
                border: '4px solid rgba(255, 255, 255, 0.3)',
                borderTop: '4px solid white',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 20px',
              }}
            />
            <p>{loadingMessage || '正在初始化应用...'}</p>
          </Box>
        ) : (
          <Box textAlign='center'>
            <p>⚠️ 应用初始化可能失败</p>
            <p>请检查控制台日志或刷新页面重试</p>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '8px 16px',
                background: '#1976d2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                marginTop: '10px',
              }}
            >
              刷新页面
            </button>
          </Box>
        )}
      </Box>
    )
  }

  return (
    <LayoutMinecraft>
      <Routes>
        <Route path='/' element={<HomePageMinecraft />} />
        <Route path='/home' element={<HomePageMinecraft />} />
        <Route path='/project' element={<ProjectPageMinecraft />} />
        <Route path='/scan' element={<ScanPageMinecraft />} />
        <Route path='/progress-test' element={<ProgressTestPage />} />
        <Route path='/extract' element={<ExtractPageMinecraft />} />
        <Route path='/export' element={<ExportPageMinecraft />} />
        <Route path='/transfer' element={<TransferPageMinecraft />} />
        <Route path='/build' element={<BuildPageMinecraft />} />
        <Route path='/security' element={<SecurityPageMinecraft />} />
        <Route path='/server' element={<ServerPageMinecraft />} />
        <Route path='/settings' element={<SettingsPageMinecraft />} />
        <Route path='/local-data' element={<LocalDataPageMinecraft />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Routes>
    </LayoutMinecraft>
  )
}

export default App
