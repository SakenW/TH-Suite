import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Box, Typography, Button, Paper, Alert } from '@mui/material'
import { AlertCircle, RefreshCw, Home, Bug } from 'lucide-react'
import { MinecraftButton, MinecraftCard } from '@components/minecraft'
import { minecraftColors } from '../../theme/minecraftTheme'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  errorCount: number
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)

    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1,
    }))

    // 可以在这里发送错误报告到服务器
    this.logErrorToService(error, errorInfo)
  }

  logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    // 实际应用中，这里可以将错误发送到错误追踪服务
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    }

    console.log('Error logged:', errorData)

    // 如果是开发环境，显示更详细的错误信息
    if (process.env.NODE_ENV === 'development') {
      console.group('🔴 Error Details')
      console.error('Error:', error)
      console.error('Error Info:', errorInfo)
      console.error('Component Stack:', errorInfo.componentStack)
      console.groupEnd()
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })

    // 可选：重新加载页面
    // window.location.reload();
  }

  handleGoHome = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
    window.location.href = '/'
  }

  handleReportBug = () => {
    const { error, errorInfo } = this.state
    const bugReportUrl = `https://github.com/your-repo/issues/new?title=${encodeURIComponent(
      `Error: ${error?.message || 'Unknown error'}`,
    )}&body=${encodeURIComponent(
      `## Error Details\n\n**Message:** ${error?.message}\n\n**Stack:**\n\`\`\`\n${error?.stack}\n\`\`\`\n\n**Component Stack:**\n\`\`\`\n${errorInfo?.componentStack}\n\`\`\``,
    )}`
    window.open(bugReportUrl, '_blank')
  }

  render() {
    const { hasError, error, errorInfo, errorCount } = this.state
    const { children, fallback } = this.props

    if (hasError) {
      // 如果提供了自定义的 fallback 组件
      if (fallback) {
        return <>{fallback}</>
      }

      // 默认的错误界面（Minecraft 风格）
      return (
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #0A0E27 0%, #0F172A 100%)',
            p: 3,
          }}
        >
          <MinecraftCard variant='enchantment'>
            <Box sx={{ p: 4, maxWidth: 600, textAlign: 'center' }}>
              {/* 错误图标 */}
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  margin: '0 auto 24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: `linear-gradient(135deg, ${minecraftColors.redstoneRed}33 0%, ${minecraftColors.redstoneRed}66 100%)`,
                  border: `3px solid ${minecraftColors.redstoneRed}`,
                  borderRadius: 0,
                  animation: 'pulse 2s infinite',
                }}
              >
                <AlertCircle size={40} style={{ color: minecraftColors.redstoneRed }} />
              </Box>

              {/* 错误标题 */}
              <Typography
                variant='h4'
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  color: '#FFFFFF',
                  mb: 2,
                }}
              >
                哎呀！出错了
              </Typography>

              {/* 错误描述 */}
              <Typography
                variant='body1'
                sx={{
                  color: 'text.secondary',
                  mb: 3,
                }}
              >
                应用程序遇到了一个意外错误。别担心，您的数据是安全的。
              </Typography>

              {/* 错误详情（开发模式） */}
              {process.env.NODE_ENV === 'development' && error && (
                <Paper
                  sx={{
                    p: 2,
                    mb: 3,
                    bgcolor: 'rgba(0,0,0,0.4)',
                    border: '1px solid #2A2A4E',
                    borderRadius: 0,
                    textAlign: 'left',
                  }}
                >
                  <Typography
                    variant='caption'
                    sx={{
                      fontFamily: 'monospace',
                      color: minecraftColors.redstoneRed,
                      display: 'block',
                      mb: 1,
                    }}
                  >
                    错误信息:
                  </Typography>
                  <Typography
                    variant='caption'
                    sx={{
                      fontFamily: 'monospace',
                      color: 'text.secondary',
                      wordBreak: 'break-word',
                    }}
                  >
                    {error.message}
                  </Typography>

                  {error.stack && (
                    <details style={{ marginTop: 8 }}>
                      <summary style={{ cursor: 'pointer', color: '#9CA3AF' }}>
                        查看堆栈跟踪
                      </summary>
                      <pre
                        style={{
                          fontSize: '10px',
                          color: '#6B7280',
                          overflow: 'auto',
                          maxHeight: '200px',
                          marginTop: '8px',
                        }}
                      >
                        {error.stack}
                      </pre>
                    </details>
                  )}
                </Paper>
              )}

              {/* 错误次数警告 */}
              {errorCount > 2 && (
                <Alert
                  severity='warning'
                  sx={{
                    mb: 3,
                    bgcolor: 'rgba(255, 152, 0, 0.1)',
                    border: '1px solid #FF9800',
                    '& .MuiAlert-icon': {
                      color: '#FF9800',
                    },
                  }}
                >
                  该错误已发生 {errorCount} 次。建议刷新页面或联系技术支持。
                </Alert>
              )}

              {/* 操作按钮 */}
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                <MinecraftButton
                  minecraftStyle='emerald'
                  onClick={this.handleReset}
                  startIcon={<RefreshCw size={16} />}
                >
                  重试
                </MinecraftButton>

                <MinecraftButton
                  minecraftStyle='diamond'
                  onClick={this.handleGoHome}
                  startIcon={<Home size={16} />}
                >
                  返回首页
                </MinecraftButton>

                {process.env.NODE_ENV === 'development' && (
                  <MinecraftButton
                    minecraftStyle='redstone'
                    onClick={this.handleReportBug}
                    startIcon={<Bug size={16} />}
                  >
                    报告问题
                  </MinecraftButton>
                )}
              </Box>

              {/* 提示信息 */}
              <Typography
                variant='caption'
                sx={{
                  color: 'text.secondary',
                  mt: 3,
                  display: 'block',
                }}
              >
                如果问题持续存在，请尝试清除浏览器缓存或联系管理员
              </Typography>
            </Box>
          </MinecraftCard>
        </Box>
      )
    }

    return children
  }
}

// 用于包装特定组件的错误边界 HOC
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
): React.ComponentType<P> {
  return (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  )
}

// 错误恢复组件
export const ErrorFallback: React.FC<{
  error?: Error
  resetError?: () => void
}> = ({ error, resetError }) => {
  return (
    <Box
      sx={{
        p: 4,
        textAlign: 'center',
        bgcolor: 'background.paper',
        borderRadius: 1,
        border: '2px solid',
        borderColor: 'error.main',
      }}
    >
      <AlertCircle size={48} style={{ color: minecraftColors.redstoneRed, marginBottom: 16 }} />
      <Typography variant='h6' gutterBottom>
        组件加载失败
      </Typography>
      {error && (
        <Typography variant='body2' color='text.secondary' sx={{ mb: 2 }}>
          {error.message}
        </Typography>
      )}
      {resetError && (
        <Button variant='contained' onClick={resetError} startIcon={<RefreshCw size={16} />}>
          重新加载
        </Button>
      )}
    </Box>
  )
}

// 异步组件错误边界
export const AsyncBoundary: React.FC<{
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}> = ({ children, fallback, onError }) => {
  return <ErrorBoundary fallback={fallback || <ErrorFallback />}>{children}</ErrorBoundary>
}

export default ErrorBoundary
