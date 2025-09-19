import '@testing-library/jest-dom'
import { vi } from 'vitest'

// 设置全局测试环境

// Mock Tauri API
const mockTauri = {
  invoke: vi.fn(),
  dialog: {
    open: vi.fn(),
    save: vi.fn(),
    message: vi.fn(),
    ask: vi.fn(),
    confirm: vi.fn(),
  },
  fs: {
    readTextFile: vi.fn(),
    writeTextFile: vi.fn(),
    exists: vi.fn(),
    createDir: vi.fn(),
    removeFile: vi.fn(),
    removeDir: vi.fn(),
  },
  path: {
    join: vi.fn(),
    dirname: vi.fn(),
    basename: vi.fn(),
    extname: vi.fn(),
  },
  shell: {
    open: vi.fn(),
  },
  notification: {
    sendNotification: vi.fn(),
    isPermissionGranted: vi.fn(),
    requestPermission: vi.fn(),
  },
  process: {
    exit: vi.fn(),
  },
  window: {
    getCurrent: vi.fn(),
    getAll: vi.fn(),
  },
}

// 模拟 Tauri API
vi.mock('@tauri-apps/api/tauri', () => mockTauri)
vi.mock('@tauri-apps/plugin-dialog', () => mockTauri.dialog)
vi.mock('@tauri-apps/plugin-fs', () => mockTauri.fs)
vi.mock('@tauri-apps/plugin-shell', () => mockTauri.shell)
vi.mock('@tauri-apps/plugin-notification', () => mockTauri.notification)
vi.mock('@tauri-apps/plugin-process', () => mockTauri.process)

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock scrollTo
Object.defineProperty(window, 'scrollTo', {
  value: vi.fn(),
  writable: true,
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
})

// Mock console methods for testing
global.console = {
  ...console,
  // 在测试中静默一些日志输出
  log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}

// 设置测试超时
vi.setConfig({
  testTimeout: 10000,
  hookTimeout: 10000,
})

// 全局测试工具函数
global.testUtils = {
  // 模拟延迟
  delay: (ms: number) => new Promise(resolve => setTimeout(resolve, ms)),
  
  // 创建模拟用户
  createMockUser: () => ({
    id: '1',
    name: 'Test User',
    email: 'test@example.com',
  }),
  
  // 创建模拟项目
  createMockProject: () => ({
    id: '1',
    name: 'Test Project',
    path: '/test/path',
    type: 'mod' as const,
    status: 'active' as const,
  }),
}

// Ant Design 相关的 mock
vi.mock('antd', async () => {
  const antd = await vi.importActual('antd')
  return {
    ...antd,
    // Mock notification
    notification: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
      open: vi.fn(),
      destroy: vi.fn(),
    },
    // Mock message
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
      loading: vi.fn(),
      destroy: vi.fn(),
    },
    // Mock modal
    Modal: {
      ...antd.Modal,
      confirm: vi.fn(),
      info: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  }
})

export { mockTauri }