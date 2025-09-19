/**
 * 新版主入口文件
 * 集成 Ant Design + 新主题系统
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import '@ant-design/v5-patch-for-react-19'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

import App from './App'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { createQueryClient } from './config/reactQuery'
import { errorHandler, queryErrorHandler, mutationErrorHandler } from './utils/errorHandling'
import { cacheOptimizer } from './utils/cacheOptimization'
import './index.css'

// 创建优化的 React Query 客户端
const queryClient = createQueryClient()

// 设置全局错误处理
queryClient.setQueryDefaults(['*'], {
  onError: queryErrorHandler,
})

queryClient.setMutationDefaults({
  onError: mutationErrorHandler,
})

// 初始化错误处理器和缓存优化器
errorHandler.setQueryClient(queryClient)
cacheOptimizer.setQueryClient(queryClient)

// 开发环境配置
const isDevelopment = import.meta.env.DEV
const DISABLE_STRICT_MODE = true // 避免 Strict Mode 的副作用

// 移除初始加载动画
const removeLoadingSpinner = () => {
  // 添加样式类表示应用已就绪
  document.body.classList.add('app-ready')
  
  // 移除 HTML 中的加载动画
  const loadingElement = document.getElementById('app-loading')
  if (loadingElement) {
    loadingElement.style.opacity = '0'
    setTimeout(() => loadingElement.remove(), 300)
  }
  
  console.log('🎉 App is ready - loading spinner removed')
}

// 应用内容组件
const AppContent = () => (
  <ErrorBoundary
    onError={(error, errorInfo) => {
      console.error('🚨 Application error:', error, errorInfo)
      // 可以集成错误报告服务
    }}
    errorTitle="应用出现错误"
    errorDescription="很抱歉，TH Suite MC L10n 遇到了意外错误。"
    reloadButtonText="刷新页面"
    homeButtonText="返回首页"  
    reportButtonText="报告错误"
  >
    <QueryClientProvider client={queryClient}>
      <App onReady={removeLoadingSpinner} />
      {isDevelopment && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  </ErrorBoundary>
)

// 渲染应用
const root = ReactDOM.createRoot(document.getElementById('root')!)

if (isDevelopment && !DISABLE_STRICT_MODE) {
  root.render(
    <React.StrictMode>
      <AppContent />
    </React.StrictMode>
  )
} else {
  root.render(<AppContent />)
}

// 开发环境额外配置
if (isDevelopment) {
  // 热重载时的处理
  if (import.meta.hot) {
    import.meta.hot.accept()
  }

  // 开发工具
  console.log('🔧 Development mode active')
  console.log('📦 Available services:', {
    QueryClient: !!queryClient,
    ErrorBoundary: 'enabled',
  })
}