/**
 * 主题提供者
 * 集成 Ant Design ConfigProvider 和增强的 Minecraft 主题系统
 * 支持亮色/暗色主题、动画配置和响应式设计
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useMemo, useCallback } from 'react'
import { ConfigProvider, theme as antdTheme, App, message } from 'antd'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import zhCN from 'antd/locale/zh_CN'

// 导入新的主题配置
import minecraftTheme, { minecraftDarkTheme, colors, animations, classNames } from '../styles/theme'
import '../styles/minecraft-theme.css'

// 主题类型
export type ThemeMode = 'light' | 'dark' | 'auto'
export type AnimationSpeed = 'none' | 'slow' | 'normal' | 'fast'

// 主题设置接口
export interface ThemeSettings {
  mode: ThemeMode
  animationSpeed: AnimationSpeed
  enableAnimations: boolean
  reducedMotion: boolean
  highContrast: boolean
  fontSize: 'small' | 'normal' | 'large'
}

// 主题上下文类型
interface ThemeContextType {
  // 基础主题
  mode: ThemeMode
  isDark: boolean
  actualTheme: 'light' | 'dark'
  
  // 设置
  settings: ThemeSettings
  updateSettings: (settings: Partial<ThemeSettings>) => void
  
  // 操作方法
  toggleTheme: () => void
  setTheme: (mode: ThemeMode) => void
  
  // 主题资源
  colors: typeof colors
  animations: typeof animations
  classNames: typeof classNames
  
  // 工具方法
  getThemeClass: (baseClass: string) => string
  applyAnimation: (element: HTMLElement, animationType: keyof typeof classNames) => void
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

// 检测用户偏好
const getUserPreferences = (): Partial<ThemeSettings> => {
  if (typeof window === 'undefined') return {}
  
  return {
    reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    highContrast: window.matchMedia('(prefers-contrast: high)').matches,
  }
}

// 计算实际主题
const getActualTheme = (mode: ThemeMode): 'light' | 'dark' => {
  switch (mode) {
    case 'light':
      return 'light'
    case 'dark':
      return 'dark'
    case 'auto':
      return getSystemTheme() ? 'dark' : 'light'
    default:
      return 'light'
  }
}

// 默认设置
const defaultSettings: ThemeSettings = {
  mode: 'auto',
  animationSpeed: 'normal',
  enableAnimations: true,
  reducedMotion: false,
  highContrast: false,
  fontSize: 'normal',
}

interface ThemeProviderProps {
  children: ReactNode
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // 初始化设置
  const [settings, setSettings] = useState<ThemeSettings>(() => {
    try {
      const stored = localStorage.getItem('th-suite-theme-settings')
      const storedSettings = stored ? JSON.parse(stored) : {}
      const userPrefs = getUserPreferences()
      
      return {
        ...defaultSettings,
        ...storedSettings,
        ...userPrefs, // 用户系统偏好优先级最高
      }
    } catch (error) {
      console.warn('Failed to load theme settings:', error)
      return { ...defaultSettings, ...getUserPreferences() }
    }
  })

  // 计算派生状态
  const actualTheme = useMemo(() => getActualTheme(settings.mode), [settings.mode])
  const isDark = actualTheme === 'dark'

  // 监听系统主题变化
  useEffect(() => {
    if (settings.mode !== 'auto') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      // 触发重新计算
      setSettings(prev => ({ ...prev, mode: prev.mode }))
    }

    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [settings.mode])

  // 监听用户偏好变化
  useEffect(() => {
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const contrastQuery = window.matchMedia('(prefers-contrast: high)')

    const motionHandler = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, reducedMotion: e.matches }))
    }

    const contrastHandler = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, highContrast: e.matches }))
    }

    motionQuery.addEventListener('change', motionHandler)
    contrastQuery.addEventListener('change', contrastHandler)

    return () => {
      motionQuery.removeEventListener('change', motionHandler)
      contrastQuery.removeEventListener('change', contrastHandler)
    }
  }, [])

  // 保存设置
  useEffect(() => {
    try {
      // 排除系统自动检测的偏好，只保存用户主动设置
      const settingsToSave = { ...settings }
      delete settingsToSave.reducedMotion
      delete settingsToSave.highContrast
      
      localStorage.setItem('th-suite-theme-settings', JSON.stringify(settingsToSave))
    } catch (error) {
      console.warn('Failed to save theme settings:', error)
    }
  }, [settings])

  // 应用CSS变量和样式
  useEffect(() => {
    const root = document.documentElement

    // 设置主题模式
    root.setAttribute('data-theme', actualTheme)
    
    // 设置字体大小
    const fontSizeMap = {
      small: '12px',
      normal: '14px',
      large: '16px'
    }
    root.style.setProperty('--th-font-size-base', fontSizeMap[settings.fontSize])
    
    // 设置动画速度
    if (settings.reducedMotion || !settings.enableAnimations) {
      root.style.setProperty('--th-transition-fast', '0.01ms')
      root.style.setProperty('--th-transition-normal', '0.01ms')
      root.style.setProperty('--th-transition-slow', '0.01ms')
    } else {
      const speedMap = {
        none: { fast: '0ms', normal: '0ms', slow: '0ms' },
        slow: { fast: '0.2s', normal: '0.4s', slow: '0.6s' },
        normal: { fast: '0.1s', normal: '0.2s', slow: '0.3s' },
        fast: { fast: '0.05s', normal: '0.1s', slow: '0.15s' }
      }
      const speeds = speedMap[settings.animationSpeed]
      root.style.setProperty('--th-transition-fast', speeds.fast)
      root.style.setProperty('--th-transition-normal', speeds.normal)
      root.style.setProperty('--th-transition-slow', speeds.slow)
    }
    
    // 设置高对比度
    if (settings.highContrast) {
      root.classList.add('th-high-contrast')
    } else {
      root.classList.remove('th-high-contrast')
    }
    
    // 设置减少动画
    if (settings.reducedMotion || !settings.enableAnimations) {
      root.classList.add('th-reduced-motion')
    } else {
      root.classList.remove('th-reduced-motion')
    }
  }, [actualTheme, settings])

  // 操作方法
  const updateSettings = useCallback((newSettings: Partial<ThemeSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }))
    
    // 显示设置更新提示
    message.success({
      content: '主题设置已更新',
      duration: 2,
      style: { marginTop: '10vh' }
    })
  }, [])

  const toggleTheme = useCallback(() => {
    const nextMode: ThemeMode = settings.mode === 'light' ? 'dark' : settings.mode === 'dark' ? 'auto' : 'light'
    updateSettings({ mode: nextMode })
  }, [settings.mode, updateSettings])

  const setTheme = useCallback((mode: ThemeMode) => {
    updateSettings({ mode })
  }, [updateSettings])

  // 工具方法
  const getThemeClass = useCallback((baseClass: string) => {
    const themeClass = isDark ? `${baseClass}-dark` : `${baseClass}-light`
    return `${baseClass} ${themeClass}`
  }, [isDark])

  const applyAnimation = useCallback((element: HTMLElement, animationType: keyof typeof classNames) => {
    if (!settings.enableAnimations || settings.reducedMotion) return
    
    const animationClass = classNames[animationType]
    element.classList.add(animationClass)
    
    // 动画完成后移除类名
    const handleAnimationEnd = () => {
      element.classList.remove(animationClass)
      element.removeEventListener('animationend', handleAnimationEnd)
    }
    
    element.addEventListener('animationend', handleAnimationEnd)
  }, [settings.enableAnimations, settings.reducedMotion])

  // 构建主题配置
  const themeConfig = useMemo(() => {
    const baseTheme = isDark ? minecraftDarkTheme : minecraftTheme
    
    // 根据用户设置调整主题
    return {
      ...baseTheme,
      token: {
        ...baseTheme.token,
        // 根据字体大小设置调整
        fontSize: settings.fontSize === 'small' ? 12 : settings.fontSize === 'large' ? 16 : 14,
        // 根据动画设置调整
        motionDurationFast: settings.enableAnimations && !settings.reducedMotion ? '0.1s' : '0.01ms',
        motionDurationMid: settings.enableAnimations && !settings.reducedMotion ? '0.2s' : '0.01ms',
        motionDurationSlow: settings.enableAnimations && !settings.reducedMotion ? '0.3s' : '0.01ms',
      }
    }
  }, [isDark, settings.fontSize, settings.enableAnimations, settings.reducedMotion])

  // 上下文值
  const contextValue: ThemeContextType = useMemo(() => ({
    mode: settings.mode,
    isDark,
    actualTheme,
    settings,
    updateSettings,
    toggleTheme,
    setTheme,
    colors,
    animations,
    classNames,
    getThemeClass,
    applyAnimation,
  }), [
    settings,
    isDark,
    actualTheme,
    updateSettings,
    toggleTheme,
    setTheme,
    getThemeClass,
    applyAnimation,
  ])

  // 配置dayjs
  useEffect(() => {
    dayjs.locale('zh-cn')
  }, [])

  return (
    <ThemeContext.Provider value={contextValue}>
      <ConfigProvider
        theme={themeConfig}
        locale={zhCN}
        componentSize="middle"
        wave={{ disabled: settings.reducedMotion || !settings.enableAnimations }}
      >
        <App>
          {children}
        </App>
      </ConfigProvider>
    </ThemeContext.Provider>
  )
}

// 主题切换Hook
export const useThemeToggle = () => {
  const { toggleTheme, setTheme, mode, isDark } = useTheme()
  
  return {
    toggleTheme,
    setTheme,
    mode,
    isDark,
    // 便捷方法
    setLight: () => setTheme('light'),
    setDark: () => setTheme('dark'),
    setAuto: () => setTheme('auto'),
  }
}

// 动画Hook
export const useAnimation = () => {
  const { applyAnimation, settings, classNames } = useTheme()
  
  const animate = useCallback((
    element: HTMLElement | null, 
    animation: keyof typeof classNames,
    onComplete?: () => void
  ) => {
    if (!element || !settings.enableAnimations || settings.reducedMotion) {
      onComplete?.()
      return
    }
    
    applyAnimation(element, animation)
    
    if (onComplete) {
      const handleAnimationEnd = () => {
        onComplete()
        element.removeEventListener('animationend', handleAnimationEnd)
      }
      element.addEventListener('animationend', handleAnimationEnd)
    }
  }, [applyAnimation, settings.enableAnimations, settings.reducedMotion])
  
  // 批量动画
  const animateSequence = useCallback((
    animations: { element: HTMLElement | null; animation: keyof typeof classNames; delay?: number }[],
    onComplete?: () => void
  ) => {
    if (!settings.enableAnimations || settings.reducedMotion) {
      onComplete?.()
      return
    }

    let completedCount = 0
    const totalAnimations = animations.length

    animations.forEach(({ element, animation, delay = 0 }, index) => {
      setTimeout(() => {
        animate(element, animation, () => {
          completedCount++
          if (completedCount === totalAnimations) {
            onComplete?.()
          }
        })
      }, delay)
    })
  }, [animate, settings.enableAnimations, settings.reducedMotion])

  // 交错动画
  const animateStagger = useCallback((
    elements: HTMLElement[],
    animation: keyof typeof classNames,
    staggerDelay: number = 100,
    onComplete?: () => void
  ) => {
    if (!settings.enableAnimations || settings.reducedMotion) {
      onComplete?.()
      return
    }

    let completedCount = 0
    const totalElements = elements.length

    elements.forEach((element, index) => {
      setTimeout(() => {
        animate(element, animation, () => {
          completedCount++
          if (completedCount === totalElements) {
            onComplete?.()
          }
        })
      }, index * staggerDelay)
    })
  }, [animate, settings.enableAnimations, settings.reducedMotion])

  // 悬浮效果
  const addHoverAnimation = useCallback((
    element: HTMLElement | null,
    hoverAnimation: keyof typeof classNames,
    leaveAnimation?: keyof typeof classNames
  ) => {
    if (!element || !settings.enableAnimations || settings.reducedMotion) return

    const handleMouseEnter = () => applyAnimation(element, hoverAnimation)
    const handleMouseLeave = () => {
      if (leaveAnimation) {
        applyAnimation(element, leaveAnimation)
      }
    }

    element.addEventListener('mouseenter', handleMouseEnter)
    element.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      element.removeEventListener('mouseenter', handleMouseEnter)
      element.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [applyAnimation, settings.enableAnimations, settings.reducedMotion])

  // 点击反馈动画
  const addClickAnimation = useCallback((
    element: HTMLElement | null,
    clickAnimation: keyof typeof classNames = 'bounce'
  ) => {
    if (!element || !settings.enableAnimations || settings.reducedMotion) return

    const handleClick = () => applyAnimation(element, clickAnimation)
    element.addEventListener('click', handleClick)

    return () => element.removeEventListener('click', handleClick)
  }, [applyAnimation, settings.enableAnimations, settings.reducedMotion])

  // 可见性动画
  const animateOnVisible = useCallback((
    element: HTMLElement | null,
    animation: keyof typeof classNames,
    options?: IntersectionObserverInit
  ) => {
    if (!element || !settings.enableAnimations || settings.reducedMotion) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            applyAnimation(element, animation)
            observer.unobserve(element)
          }
        })
      },
      { threshold: 0.1, ...options }
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [applyAnimation, settings.enableAnimations, settings.reducedMotion])
  
  return { 
    animate, 
    animateSequence,
    animateStagger,
    addHoverAnimation,
    addClickAnimation,
    animateOnVisible,
    canAnimate: settings.enableAnimations && !settings.reducedMotion 
  }
}

// 响应式Hook
export const useResponsive = () => {
  const [screenSize, setScreenSize] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'xxl'>('lg')
  
  useEffect(() => {
    const updateSize = () => {
      const width = window.innerWidth
      if (width < 576) setScreenSize('xs')
      else if (width < 768) setScreenSize('sm')
      else if (width < 992) setScreenSize('md')
      else if (width < 1200) setScreenSize('lg')
      else if (width < 1600) setScreenSize('xl')
      else setScreenSize('xxl')
    }
    
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])
  
  return {
    screenSize,
    isXs: screenSize === 'xs',
    isSm: screenSize === 'sm',
    isMd: screenSize === 'md',
    isLg: screenSize === 'lg',
    isXl: screenSize === 'xl',
    isXxl: screenSize === 'xxl',
    isMobile: screenSize === 'xs' || screenSize === 'sm',
    isTablet: screenSize === 'md',
    isDesktop: screenSize === 'lg' || screenSize === 'xl' || screenSize === 'xxl',
  }
}

export default ThemeProvider