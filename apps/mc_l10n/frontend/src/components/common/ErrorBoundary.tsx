import React, { Component, ReactNode } from 'react'
import { Card, Typography, Button, Space } from 'antd'
import { ExclamationCircleOutlined, ReloadOutlined, HomeOutlined, BugOutlined } from '@ant-design/icons'

export interface ErrorBoundaryProps {
  children: ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  errorTitle?: string
  errorDescription?: string
  reloadButtonText?: string
  homeButtonText?: string
  reportButtonText?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  handleReport = () => {
    // 这里可以实现错误报告功能
    console.log('Report error:', this.state.error)
  }

  render() {
    if (this.state.hasError) {
      const {
        errorTitle = '应用出现错误',
        errorDescription = '很抱歉，应用遇到了意外错误。',
        reloadButtonText = '刷新页面',
        homeButtonText = '返回首页',
        reportButtonText = '报告错误',
      } = this.props

      return (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            backgroundColor: '#f5f5f5',
            padding: 16,
          }}
        >
          <Card
            style={{
              padding: 32,
              maxWidth: 500,
              textAlign: 'center',
            }}
          >
            <ExclamationCircleOutlined
              style={{
                fontSize: 64,
                color: '#ff4d4f',
                marginBottom: 16,
              }}
            />
            <Typography.Title level={2} style={{ marginBottom: 16 }}>
              {errorTitle}
            </Typography.Title>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
              {errorDescription}
            </Typography.Text>

            <Space wrap style={{ justifyContent: 'center' }}>
              <Button type="primary" icon={<ReloadOutlined />} onClick={this.handleReload}>
                {reloadButtonText}
              </Button>
              <Button icon={<HomeOutlined />} onClick={this.handleGoHome}>
                {homeButtonText}
              </Button>
              <Button type="text" icon={<BugOutlined />} onClick={this.handleReport}>
                {reportButtonText}
              </Button>
            </Space>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div style={{ marginTop: 24, textAlign: 'left' }}>
                <Typography.Title level={4} style={{ marginBottom: 16 }}>
                  错误详情 (开发模式):
                </Typography.Title>
                <Card
                  style={{
                    padding: 16,
                    backgroundColor: '#f5f5f5',
                    fontFamily: 'monospace',
                    fontSize: 14,
                    overflow: 'auto',
                    maxHeight: 200,
                  }}
                >
                  <pre>{this.state.error.stack}</pre>
                </Card>
              </div>
            )}
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
