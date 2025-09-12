/**
 * TH-Suite MC L10n 主题配置
 * 专业的Minecraft轻装饰主题系统
 */

import { ThemeConfig } from 'antd'
import { AliasToken } from 'antd/es/theme/internal'

// 自定义颜色配置
export const colors = {
  // 主色调 - Minecraft绿色系
  primary: {
    50: '#f0f9f0',
    100: '#dcf2dc', 
    200: '#bde5bd',
    300: '#91d091',
    400: '#4fb84f',  // 主色
    500: '#389e38',
    600: '#2d7d2d',
    700: '#266226',
    800: '#1f4f1f',
    900: '#1a421a',
  },
  
  // 辅助色 - 土黄/棕色系
  secondary: {
    50: '#fdf6e3',
    100: '#f9edc7',
    200: '#f3db91',
    300: '#edc555',
    400: '#d4ac0d',  // 辅助色
    500: '#b8860b',
    600: '#9a6a0a',
    700: '#7d5309',
    800: '#664208',
    900: '#543608',
  },
  
  // 状态颜色
  status: {
    success: '#52c41a',
    warning: '#fadb14', 
    error: '#ff4d4f',
    info: '#1890ff',
    processing: '#722ed1',
  },
  
  // 背景色
  background: {
    primary: '#ffffff',
    secondary: '#f5f5f5',
    tertiary: '#fafafa',
    card: '#ffffff',
    hover: '#f0f9f0',
  },
  
  // 文本颜色
  text: {
    primary: '#000000d9',
    secondary: '#00000073',
    disabled: '#00000040',
    inverse: '#ffffff',
  },
  
  // 边框色
  border: {
    primary: '#d9d9d9',
    secondary: '#f0f0f0',
    active: '#4fb84f',
  }
}

// Minecraft风格的阴影配置
export const shadows = {
  card: '0 2px 8px rgba(0, 0, 0, 0.09)',
  cardHover: '0 4px 16px rgba(0, 0, 0, 0.12)',
  modal: '0 6px 24px rgba(0, 0, 0, 0.15)',
  dropdown: '0 2px 8px rgba(0, 0, 0, 0.15)',
  pixel: '2px 2px 0px rgba(0, 0, 0, 0.2)', // Minecraft像素风格阴影
}

// 动画配置
export const animations = {
  duration: {
    fast: '0.1s',
    normal: '0.2s',
    slow: '0.3s',
  },
  easing: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  }
}

// 自定义token配置
const customToken: Partial<AliasToken> = {
  // 主色配置
  colorPrimary: colors.primary[400],
  colorSuccess: colors.status.success,
  colorWarning: colors.status.warning,
  colorError: colors.status.error,
  colorInfo: colors.status.info,
  
  // 背景色
  colorBgBase: colors.background.primary,
  colorBgContainer: colors.background.card,
  colorBgElevated: colors.background.card,
  colorBgLayout: colors.background.secondary,
  
  // 文本色
  colorText: colors.text.primary,
  colorTextSecondary: colors.text.secondary,
  colorTextDisabled: colors.text.disabled,
  
  // 边框
  colorBorder: colors.border.primary,
  colorBorderSecondary: colors.border.secondary,
  
  // 圆角 - 轻微减少以配合Minecraft风格
  borderRadius: 6,
  borderRadiusLG: 8,
  borderRadiusSM: 4,
  borderRadiusXS: 2,
  
  // 间距
  padding: 16,
  paddingLG: 24,
  paddingSM: 12,
  paddingXS: 8,
  paddingXXS: 4,
  
  // 字体
  fontSize: 14,
  fontSizeLG: 16,
  fontSizeSM: 12,
  fontSizeXL: 20,
  fontSizeHeading1: 38,
  fontSizeHeading2: 30,
  fontSizeHeading3: 24,
  fontSizeHeading4: 20,
  fontSizeHeading5: 16,
  
  // 行高
  lineHeight: 1.5714,
  lineHeightLG: 1.5,
  lineHeightSM: 1.66,
  
  // 控件高度
  controlHeight: 32,
  controlHeightLG: 40,
  controlHeightSM: 24,
  
  // 阴影
  boxShadow: shadows.card,
  boxShadowSecondary: shadows.cardHover,
}

// 组件样式配置
const componentConfig = {
  Card: {
    boxShadow: shadows.card,
    boxShadowHover: shadows.cardHover,
    borderRadius: 8,
    paddingLG: 24,
  },
  
  Button: {
    borderRadius: 6,
    paddingInline: 16,
    primaryShadow: 'none',
    defaultShadow: 'none',
    // Minecraft风格按钮效果
    primaryColor: colors.primary[400],
    algorithm: true,
  },
  
  Input: {
    borderRadius: 6,
    paddingInline: 12,
    activeBorderColor: colors.primary[400],
    hoverBorderColor: colors.primary[300],
  },
  
  Select: {
    borderRadius: 6,
    optionSelectedBg: colors.background.hover,
  },
  
  Table: {
    headerBg: colors.background.tertiary,
    headerColor: colors.text.primary,
    rowHoverBg: colors.background.hover,
    borderRadius: 8,
  },
  
  Progress: {
    defaultColor: colors.primary[400],
    remainingColor: colors.background.secondary,
    lineCap: 'round',
  },
  
  Tag: {
    borderRadius: 4,
    paddingInline: 8,
  },
  
  Modal: {
    borderRadius: 12,
    boxShadow: shadows.modal,
    paddingLG: 24,
  },
  
  Notification: {
    borderRadius: 8,
    boxShadow: shadows.dropdown,
  },
  
  Tooltip: {
    borderRadius: 6,
    boxShadow: shadows.dropdown,
  },
  
  Divider: {
    colorSplit: colors.border.secondary,
  }
}

// 主主题配置
export const minecraftTheme: ThemeConfig = {
  token: customToken,
  components: componentConfig,
  
  // CSS变量配置
  cssVar: {
    prefix: 'th-suite',
    key: 'minecraft-theme'
  },
  
  algorithm: [
    // 可以添加算法来动态计算颜色
  ],
}

// 暗色主题配置
const darkToken: Partial<AliasToken> = {
  ...customToken,
  
  // 暗色背景
  colorBgBase: '#141414',
  colorBgContainer: '#1f1f1f',
  colorBgElevated: '#262626',
  colorBgLayout: '#000000',
  
  // 暗色文本
  colorText: '#ffffffd9',
  colorTextSecondary: '#ffffff73',
  colorTextDisabled: '#ffffff40',
  
  // 暗色边框
  colorBorder: '#434343',
  colorBorderSecondary: '#303030',
}

export const minecraftDarkTheme: ThemeConfig = {
  ...minecraftTheme,
  token: darkToken,
  cssVar: {
    prefix: 'th-suite',
    key: 'minecraft-dark-theme'
  }
}

// 响应式断点
export const breakpoints = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const

// 工具函数
export const getResponsiveValue = <T>(
  values: Partial<Record<keyof typeof breakpoints, T>>,
  defaultValue: T
): T => {
  // 简化版响应式值获取，实际使用时需要结合媒体查询
  return values.lg || values.md || values.sm || values.xs || defaultValue
}

// 自定义CSS类名
export const classNames = {
  // Minecraft风格装饰
  pixelBorder: 'th-pixel-border',
  minecraftCard: 'th-minecraft-card',
  glowEffect: 'th-glow-effect',
  
  // 基础动画类
  fadeIn: 'th-fade-in',
  slideIn: 'th-slide-in',
  scaleIn: 'th-scale-in',
  
  // 滑动动画类
  slideInLeft: 'th-slide-in-left',
  slideInRight: 'th-slide-in-right',
  slideInUp: 'th-slide-in-up',
  slideInDown: 'th-slide-in-down',
  
  // 缩放动画类
  zoomIn: 'th-zoom-in',
  zoomOut: 'th-zoom-out',
  
  // 翻转动画类
  flipInX: 'th-flip-in-x',
  flipInY: 'th-flip-in-y',
  
  // 弹跳动画类
  bounceIn: 'th-bounce-in',
  bounceInUp: 'th-bounce-in-up',
  
  // 弹性动画类
  elasticIn: 'th-elastic-in',
  rubberBand: 'th-rubber-band',
  
  // 摆动动画类
  swing: 'th-swing',
  wobble: 'th-wobble',
  tada: 'th-tada',
  jello: 'th-jello',
  
  // 心跳和脉冲
  heartBeat: 'th-heart-beat',
  pulseScale: 'th-pulse-scale',
  
  // 浮动和旋转
  float: 'th-float',
  spinClockwise: 'th-spin-clockwise',
  spinCounterClockwise: 'th-spin-counter-clockwise',
  
  // 震动和闪烁
  shake: 'th-shake',
  flash: 'th-flash',
  
  // 旋转进出
  rotateIn: 'th-rotate-in',
  rotateOut: 'th-rotate-out',
  
  // 布局类
  fullHeight: 'th-full-height',
  centeredContent: 'th-centered-content',
  scrollContainer: 'th-scroll-container',
  
  // 状态类
  loading: 'th-loading',
  disabled: 'th-disabled',
  active: 'th-active',
  
  // 特效类
  shimmer: 'th-shimmer',
  pulse: 'th-pulse',
  bounce: 'th-bounce',
  progressShine: 'th-progress-shine',
  typing: 'th-typing',
  blink: 'th-blink',
}

// 导出默认主题
export default minecraftTheme