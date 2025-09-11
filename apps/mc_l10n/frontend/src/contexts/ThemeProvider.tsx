/**
 * 主题提供者
 * 集成 Ant Design ConfigProvider 和 Minecraft 主题系统
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { ConfigProvider, theme as antdTheme, App } from 'antd'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import { getMinecraftTheme, MC_COLORS } from '../theme/minecraft'
import { storageService } from '../services'

// 主题类型
export type ThemeMode = 'light' | 'dark' | 'auto'

// 主题上下文类型
interface ThemeContextType {
  mode: ThemeMode
  isDark: boolean
  toggleTheme: () => void
  setTheme: (mode: ThemeMode) => void
  colors: typeof MC_COLORS
}

// 创建上下文
const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

// Hook：使用主题
export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}

// 检测系统主题
const getSystemTheme = (): boolean => {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

// 计算实际主题
const getActualTheme = (mode: ThemeMode): boolean => {
  switch (mode) {
    case 'light':
      return false
    case 'dark':
      return true
    case 'auto':
      return getSystemTheme()
    default:
      return false
  }
}

interface ThemeProviderProps {
  children: ReactNode
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // 从存储中获取主题设置
  const [mode, setMode] = useState<ThemeMode>(() => {
    try {
      const stored = localStorage.getItem('th-suite-theme') as ThemeMode
      return stored || 'auto'
    } catch {
      return 'auto'
    }
  })

  const [isDark, setIsDark] = useState(() => getActualTheme(mode))

  // 监听系统主题变化
  useEffect(() => {
    if (mode !== 'auto') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      setIsDark(e.matches)
    }

    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [mode])

  // 更新实际主题
  useEffect(() => {
    setIsDark(getActualTheme(mode))
  }, [mode])

  // 保存主题设置
  useEffect(() => {
    try {
      localStorage.setItem('th-suite-theme', mode)
      // 暂时只使用localStorage，避免storageService依赖
    } catch (error) {
      console.warn('Failed to save theme setting:', error)
    }
  }, [mode])

  // 主题操作
  const toggleTheme = () => {
    setMode(prev => {
      switch (prev) {
        case 'light':
          return 'dark'
        case 'dark':
          return 'auto'
        case 'auto':
          return 'light'
        default:
          return 'light'
      }
    })
  }

  const setTheme = (newMode: ThemeMode) => {
    setMode(newMode)
  }

  // Ant Design 主题配置
  const antdThemeConfig = getMinecraftTheme(isDark)

  // 配置 dayjs 本地化
  dayjs.locale('zh-cn')

  const contextValue: ThemeContextType = {
    mode,
    isDark,
    toggleTheme,
    setTheme,
    colors: MC_COLORS,
  }

  return (
    <ThemeContext.Provider value={contextValue}>
      <ConfigProvider
        theme={antdThemeConfig}
        locale={{
          // 中文本地化配置
          locale: 'zh_CN',
          empty: {
            description: '暂无数据',
          },
          global: {
            placeholder: '请选择',
          },
          Table: {
            emptyText: '暂无数据',
            filterTitle: '筛选',
            filterConfirm: '确定',
            filterReset: '重置',
            filterEmptyText: '无筛选项',
            selectAll: '全选当页',
            selectInvert: '反选当页',
            sortTitle: '排序',
          },
          Modal: {
            okText: '确定',
            cancelText: '取消',
            justOkText: '知道了',
          },
          Popconfirm: {
            okText: '确定',
            cancelText: '取消',
          },
          Transfer: {
            itemUnit: '项',
            itemsUnit: '项',
            searchPlaceholder: '搜索内容',
            selectAll: '全选',
            deselect: '取消选择',
          },
          Upload: {
            uploading: '文件上传中',
            removeFile: '删除文件',
            uploadError: '上传错误',
            previewFile: '预览文件',
            downloadFile: '下载文件',
          },
        }}
      >
        <App>
          {children}
        </App>
      </ConfigProvider>
    </ThemeContext.Provider>
  )
}

// 导出默认组件
export default ThemeProvider