/**
 * Minecraft 轻装饰主题系统
 * 基于 Ant Design Token 系统的轻量化 Minecraft 视觉装饰
 */

import { theme } from 'antd'
import { generate } from '@ant-design/colors'

// Minecraft 色彩调色板
export const MC_COLORS = {
  // 主要颜色 - 基于 Minecraft UI
  primary: '#4CAF50',      // 绿宝石绿（经验条颜色）
  success: '#8BC34A',      // 草绿色
  warning: '#FFC107',      // 金锭黄
  error: '#F44336',        // 红石红
  info: '#2196F3',         // 青金石蓝
  
  // 中性色 - 基于方块材质
  stone: '#7F7F7F',        // 石头灰
  cobblestone: '#6B6B6B',  // 圆石灰
  wood: '#8B4513',         // 橡木棕
  glass: 'rgba(255,255,255,0.2)', // 玻璃透明

  // 背景色
  dirt: '#8B6914',         // 泥土棕
  grass: '#7CB342',        // 草方块绿
  bedrock: '#2C2C2C',      // 基岩黑
} as const

// 像素艺术装饰样式
export const MC_PIXEL_STYLES = {
  // 像素化描边
  pixelBorder: '2px solid currentColor',
  pixelShadow: '2px 2px 0 rgba(0,0,0,0.3)',
  pixelRadius: '2px', // 轻微圆角，不完全像素化以保持现代感
  
  // 网格背景
  gridBackground: `
    background-image: 
      linear-gradient(90deg, rgba(0,0,0,0.1) 1px, transparent 1px),
      linear-gradient(rgba(0,0,0,0.1) 1px, transparent 1px);
    background-size: 16px 16px;
  `,
  
  // 方块化阴影
  blockShadow: '4px 4px 0 rgba(0,0,0,0.2), 8px 8px 0 rgba(0,0,0,0.1)',
} as const

// 亮色主题配置
export const minecraftLightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    // 色彩系统
    colorPrimary: MC_COLORS.primary,
    colorSuccess: MC_COLORS.success,
    colorWarning: MC_COLORS.warning,
    colorError: MC_COLORS.error,
    colorInfo: MC_COLORS.info,
    
    // 背景色
    colorBgBase: '#F5F5F5',        // 浅石头色
    colorBgContainer: '#FFFFFF',    // 白色容器
    colorBgElevated: '#FAFAFA',     // 提升背景
    
    // 文本色
    colorTextBase: '#2C2C2C',       // 深色文本
    colorTextSecondary: '#6B6B6B',  // 圆石灰文本
    
    // 边框
    colorBorder: '#E0E0E0',
    colorBorderSecondary: '#F0F0F0',
    
    // 圆角 - 轻微像素化
    borderRadius: 4,
    borderRadiusLG: 6,
    borderRadiusSM: 2,
    
    // 字体
    fontSize: 14,
    fontFamily: `
      -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
      'Helvetica Neue', Arial, 'Noto Sans', sans-serif,
      'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol',
      'Noto Color Emoji'
    `,
  },
  components: {
    // 按钮组件 - 方块化设计
    Button: {
      borderRadius: 4,
      paddingContentHorizontal: 16,
      controlHeight: 32,
      // 主按钮像素装饰
      primaryShadow: MC_PIXEL_STYLES.pixelShadow,
    },
    
    // 卡片组件 - 轻微方块感
    Card: {
      borderRadius: 6,
      paddingLG: 24,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05)',
    },
    
    // 输入框 - 保持现代感
    Input: {
      borderRadius: 4,
      paddingInline: 12,
    },
    
    // 菜单 - 轻装饰
    Menu: {
      itemBorderRadius: 4,
      itemMarginInline: 4,
    },
    
    // 进度条 - 经验条样式
    Progress: {
      colorSuccess: MC_COLORS.primary,
      remainingColor: 'rgba(76, 175, 80, 0.2)',
    },
    
    // 标签 - 像素化装饰
    Tag: {
      borderRadius: 2,
      fontSize: 12,
    },
    
    // 通知 - 方块化设计
    Notification: {
      borderRadius: 6,
      paddingMD: 16,
    },
  },
}

// 暗色主题配置  
export const minecraftDarkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    // 色彩系统 - 暗色调整
    colorPrimary: '#5CBF60',        // 稍亮的绿色
    colorSuccess: '#9CCC65',
    colorWarning: '#FFD54F', 
    colorError: '#EF5350',
    colorInfo: '#42A5F5',
    
    // 背景色 - 基岩主题
    colorBgBase: '#1F1F1F',         // 基岩色
    colorBgContainer: '#2A2A2A',    // 深石头色
    colorBgElevated: '#333333',     // 提升背景
    
    // 文本色
    colorTextBase: '#E0E0E0',       // 浅色文本
    colorTextSecondary: '#AAAAAA',  // 次要文本
    
    // 边框
    colorBorder: '#404040',
    colorBorderSecondary: '#333333',
    
    // 继承亮色主题的其他配置
    borderRadius: 4,
    borderRadiusLG: 6,
    borderRadiusSM: 2,
    fontSize: 14,
    fontFamily: minecraftLightTheme.token.fontFamily,
  },
  components: {
    ...minecraftLightTheme.components,
    
    // 暗色特定调整
    Card: {
      ...minecraftLightTheme.components.Card,
      boxShadow: '0 2px 8px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.05)',
    },
  },
}

// 主题切换工具
export const getMinecraftTheme = (isDark: boolean) => {
  return isDark ? minecraftDarkTheme : minecraftLightTheme
}

// CSS-in-JS 装饰样式
export const mcDecorationStyles = {
  // 像素化卡片
  pixelCard: {
    border: `2px solid currentColor`,
    boxShadow: MC_PIXEL_STYLES.blockShadow,
    background: 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.1) 100%)',
    position: 'relative' as const,
    borderRadius: '4px',
    overflow: 'hidden',
    
    '&::before': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: 0, 
      right: 0,
      bottom: 0,
      background: MC_PIXEL_STYLES.gridBackground,
      zIndex: -1,
      opacity: 0.1,
    },
    
    '&::after': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: '-100%',
      width: '100%',
      height: '100%',
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
      transition: 'left 0.6s ease',
      zIndex: 1,
      pointerEvents: 'none',
    },
    
    '&:hover::after': {
      left: '100%',
    },
  },
  
  // 经验条样式 
  expBar: {
    height: '6px',
    background: 'linear-gradient(90deg, #4CAF50 0%, #8BC34A 50%, #66BB6A 100%)',
    border: '1px solid rgba(0,0,0,0.2)',
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.2), 0 1px 3px rgba(76, 175, 80, 0.3)',
    borderRadius: '2px',
    position: 'relative' as const,
    overflow: 'hidden',
    
    '&::before': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: 0,
      right: 0,
      height: '2px',
      background: 'linear-gradient(90deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.2) 100%)',
    },
    
    '&::after': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: '-100%',
      width: '30%',
      height: '100%',
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent)',
      animation: 'shimmer 2s infinite',
    },
  },
  
  // 方块化按钮
  blockButton: {
    borderRadius: '4px !important',
    boxShadow: `${MC_PIXEL_STYLES.pixelShadow}, inset 0 1px 0 rgba(255,255,255,0.2)`,
    textShadow: '1px 1px 0 rgba(0,0,0,0.3)',
    position: 'relative' as const,
    overflow: 'hidden',
    border: '2px solid rgba(0,0,0,0.1)',
    background: 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.05) 100%)',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    
    '&::before': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: '-100%',
      width: '100%',
      height: '100%',
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
      transition: 'left 0.5s ease',
      zIndex: 1,
    },
    
    '&:hover': {
      transform: 'translate(-1px, -1px)',
      boxShadow: `3px 3px 0 rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.3), 0 4px 12px rgba(76, 175, 80, 0.2)`,
    },
    
    '&:hover::before': {
      left: '100%',
    },
    
    '&:active': {
      transform: 'translate(1px, 1px)',
      boxShadow: `1px 1px 0 rgba(0,0,0,0.3), inset 0 1px 2px rgba(0,0,0,0.2)`,
    },
  },
  
  // 玻璃效果卡片
  glassCard: {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '8px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
    position: 'relative' as const,
    
    '&::before': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: 0,
      right: 0,
      height: '1px',
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent)',
    },
  },
  
  // 发光效果
  glowEffect: {
    position: 'relative' as const,
    
    '&::after': {
      content: '""',
      position: 'absolute' as const,
      top: '-2px',
      left: '-2px',
      right: '-2px',
      bottom: '-2px',
      background: 'linear-gradient(45deg, #4CAF50, #8BC34A, #2196F3, #4CAF50)',
      borderRadius: 'inherit',
      opacity: 0,
      filter: 'blur(8px)',
      zIndex: -1,
      transition: 'opacity 0.3s ease',
    },
    
    '&:hover::after': {
      opacity: 0.7,
      animation: 'glow-rotate 2s linear infinite',
    },
  },
  
  // 浮动动画卡片
  floatingCard: {
    animation: 'float 3s ease-in-out infinite',
    transition: 'transform 0.3s ease',
    
    '&:hover': {
      animationPlayState: 'paused',
      transform: 'translateY(-4px)',
    },
  },
  
  // 网格背景
  gridBackground: {
    backgroundImage: MC_PIXEL_STYLES.gridBackground,
    backgroundSize: '16px 16px',
    position: 'relative' as const,
    
    '&::before': {
      content: '""',
      position: 'absolute' as const,
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'linear-gradient(135deg, rgba(76, 175, 80, 0.05) 0%, rgba(33, 150, 243, 0.05) 100%)',
    },
  },
  
  // 进度指示器
  progressIndicator: {
    height: '8px',
    background: 'rgba(0, 0, 0, 0.1)',
    borderRadius: '4px',
    overflow: 'hidden',
    position: 'relative' as const,
    
    '& .progress-fill': {
      height: '100%',
      background: 'linear-gradient(90deg, #4CAF50 0%, #8BC34A 50%, #66BB6A 100%)',
      borderRadius: 'inherit',
      position: 'relative' as const,
      transition: 'width 0.3s ease',
      
      '&::after': {
        content: '""',
        position: 'absolute' as const,
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
        animation: 'shimmer 1.5s infinite',
      },
    },
  },
  
  // 状态指示器
  statusIndicator: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    
    '&.success': {
      background: 'linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(139, 195, 74, 0.1) 100%)',
      color: '#4CAF50',
      border: '1px solid rgba(76, 175, 80, 0.3)',
      
      '&::before': {
        content: '""',
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: '#4CAF50',
        boxShadow: '0 0 8px rgba(76, 175, 80, 0.6)',
        animation: 'pulse 2s infinite',
      },
    },
    
    '&.error': {
      background: 'linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(229, 57, 53, 0.1) 100%)',
      color: '#F44336',
      border: '1px solid rgba(244, 67, 54, 0.3)',
      
      '&::before': {
        content: '""',
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: '#F44336',
        boxShadow: '0 0 8px rgba(244, 67, 54, 0.6)',
      },
    },
    
    '&.warning': {
      background: 'linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 152, 0, 0.1) 100%)',
      color: '#FF9800',
      border: '1px solid rgba(255, 193, 7, 0.3)',
      
      '&::before': {
        content: '""',
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: '#FF9800',
        boxShadow: '0 0 8px rgba(255, 152, 0, 0.6)',
      },
    },
    
    '&.info': {
      background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(30, 136, 229, 0.1) 100%)',
      color: '#2196F3',
      border: '1px solid rgba(33, 150, 243, 0.3)',
      
      '&::before': {
        content: '""',
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: '#2196F3',
        boxShadow: '0 0 8px rgba(33, 150, 243, 0.6)',
      },
    },
  },
}

// 工具函数：生成调色板
export const generateMCPalette = (color: string) => {
  return generate(color, {
    theme: 'default',
    backgroundColor: '#ffffff',
  })
}

// 导出默认配置
export default {
  light: minecraftLightTheme,
  dark: minecraftDarkTheme,
  colors: MC_COLORS,
  styles: mcDecorationStyles,
  utils: {
    getTheme: getMinecraftTheme,
    generatePalette: generateMCPalette,
  },
}