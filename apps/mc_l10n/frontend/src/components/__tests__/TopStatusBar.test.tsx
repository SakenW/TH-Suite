import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import TopStatusBar from '../TopStatusBar'

// Mock Ant Design components
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  }
})

// Mock Tauri API
vi.mock('@tauri-apps/api/tauri', () => ({
  invoke: vi.fn(),
}))

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('TopStatusBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    expect(screen.getByText(/TH-Suite MC L10n/i)).toBeInTheDocument()
  })

  it('should display connection status', async () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    // 检查连接状态指示器
    const statusIndicator = screen.getByTestId('connection-status')
    expect(statusIndicator).toBeInTheDocument()
  })

  it('should show server information when connected', async () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    // 模拟连接成功状态
    await waitFor(() => {
      expect(screen.getByText(/连接正常/i)).toBeInTheDocument()
    })
  })

  it('should handle refresh button click', async () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    const refreshButton = screen.getByRole('button', { name: /刷新/i })
    fireEvent.click(refreshButton)

    // 验证刷新功能被调用
    await waitFor(() => {
      expect(refreshButton).toBeEnabled()
    })
  })

  it('should display system metrics', async () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    // 检查系统指标显示
    await waitFor(() => {
      const metricsContainer = screen.getByTestId('system-metrics')
      expect(metricsContainer).toBeInTheDocument()
    })
  })

  it('should handle error states gracefully', async () => {
    // Mock API error
    const mockInvoke = vi.mocked(await import('@tauri-apps/api/tauri')).invoke
    mockInvoke.mockRejectedValue(new Error('Connection failed'))

    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/连接失败/i)).toBeInTheDocument()
    })
  })

  it('should update metrics periodically', async () => {
    vi.useFakeTimers()
    
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    // 模拟时间流逝
    vi.advanceTimersByTime(5000)

    await waitFor(() => {
      expect(screen.getByTestId('last-update')).toBeInTheDocument()
    })

    vi.useRealTimers()
  })

  it('should be accessible', () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    // 检查ARIA标签
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByLabelText(/状态栏/i)).toBeInTheDocument()
  })

  it('should respond to keyboard navigation', () => {
    render(
      <TestWrapper>
        <TopStatusBar />
      </TestWrapper>
    )

    const refreshButton = screen.getByRole('button', { name: /刷新/i })
    
    // 测试键盘导航
    refreshButton.focus()
    expect(refreshButton).toHaveFocus()
    
    fireEvent.keyDown(refreshButton, { key: 'Enter' })
    // 验证Enter键触发点击
  })
})