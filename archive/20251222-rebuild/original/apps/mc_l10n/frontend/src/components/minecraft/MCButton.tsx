/**
 * Minecraft 风格按钮组件
 * 模拟 Minecraft 游戏内的按钮样式
 */

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { minecraftColors, get3DBorder, getPixelShadow } from '../../theme/minecraft/colors'
import { typography, textStyles } from '../../theme/minecraft/typography'

export interface MCButtonProps {
  children: React.ReactNode
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
  variant?: 'default' | 'primary' | 'success' | 'danger' | 'warning' | 'enchanted'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  fullWidth?: boolean
  loading?: boolean
  icon?: React.ReactNode
  sound?: boolean // 是否播放音效
  tooltip?: string
  className?: string
  style?: React.CSSProperties
}

const MCButton: React.FC<MCButtonProps> = ({
  children,
  onClick,
  variant = 'default',
  size = 'medium',
  disabled = false,
  fullWidth = false,
  loading = false,
  icon,
  sound = true,
  tooltip,
  className = '',
  style = {},
}) => {
  const [isPressed, setIsPressed] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)

  // 播放音效
  const playSound = (type: 'hover' | 'click') => {
    if (!sound) return
    // 这里可以添加实际的音效播放逻辑
    // const audio = new Audio(`/sounds/button_${type}.ogg`);
    // audio.play();
  }

  // 获取变体颜色
  const getVariantColors = () => {
    switch (variant) {
      case 'primary':
        return {
          bg: minecraftColors.primary.grass,
          hover: minecraftColors.primary.emerald,
          text: minecraftColors.ui.text.secondary,
        }
      case 'success':
        return {
          bg: minecraftColors.ui.button.success,
          hover: minecraftColors.primary.emerald,
          text: minecraftColors.ui.text.secondary,
        }
      case 'danger':
        return {
          bg: minecraftColors.ui.button.danger,
          hover: minecraftColors.primary.redstone,
          text: minecraftColors.ui.text.secondary,
        }
      case 'warning':
        return {
          bg: minecraftColors.primary.gold,
          hover: minecraftColors.formatting['§6'],
          text: minecraftColors.ui.text.primary,
        }
      case 'enchanted':
        return {
          bg: minecraftColors.ui.text.enchanted,
          hover: minecraftColors.rarity.epic,
          text: minecraftColors.ui.text.secondary,
        }
      default:
        return {
          bg: minecraftColors.ui.button.default,
          hover: minecraftColors.ui.button.hover,
          text: minecraftColors.ui.text.secondary,
        }
    }
  }

  // 获取尺寸样式
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return {
          padding: '6px 12px',
          fontSize: typography.fontSize.small,
          height: '28px',
        }
      case 'large':
        return {
          padding: '12px 24px',
          fontSize: typography.fontSize.large,
          height: '48px',
        }
      default:
        return {
          padding: '8px 16px',
          fontSize: typography.fontSize.button,
          height: '36px',
        }
    }
  }

  const colors = getVariantColors()
  const sizeStyles = getSizeStyles()
  const borderStyles = get3DBorder(!isPressed)

  // 基础样式
  const baseStyles: React.CSSProperties = {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    width: fullWidth ? '100%' : 'auto',
    ...sizeStyles,
    backgroundColor: isHovered && !disabled ? colors.hover : colors.bg,
    color: disabled ? minecraftColors.ui.text.disabled : colors.text,
    ...borderStyles,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.wide,
    textShadow: disabled ? 'none' : getPixelShadow(),
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.6 : 1,
    transition: 'all 0.1s ease',
    imageRendering: 'pixelated',
    outline: 'none',
    userSelect: 'none',
    transform: isPressed ? 'translateY(2px)' : 'translateY(0)',
    ...style,
  }

  // 处理点击
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || loading) return
    playSound('click')
    onClick?.(e)
  }

  // 处理鼠标进入
  const handleMouseEnter = () => {
    if (disabled) return
    setIsHovered(true)
    playSound('hover')
  }

  // 处理鼠标离开
  const handleMouseLeave = () => {
    setIsHovered(false)
    setIsPressed(false)
  }

  // 处理鼠标按下
  const handleMouseDown = () => {
    if (disabled) return
    setIsPressed(true)
  }

  // 处理鼠标释放
  const handleMouseUp = () => {
    setIsPressed(false)
  }

  // 附魔效果动画
  const enchantedAnimation =
    variant === 'enchanted'
      ? {
          animate: {
            textShadow: [
              '0 0 5px #9C6BFF, 2px 2px 0px rgba(0, 0, 0, 0.5)',
              '0 0 10px #9C6BFF, 2px 2px 0px rgba(0, 0, 0, 0.5)',
              '0 0 5px #9C6BFF, 2px 2px 0px rgba(0, 0, 0, 0.5)',
            ],
          },
          transition: {
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          },
        }
      : {}

  return (
    <>
      <motion.button
        ref={buttonRef}
        className={`mc-button ${className}`}
        style={baseStyles}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        disabled={disabled || loading}
        whileHover={!disabled ? { scale: 1.02 } : {}}
        whileTap={!disabled ? { scale: 0.98 } : {}}
        {...enchantedAnimation}
      >
        {/* 加载动画 */}
        {loading && (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            style={{
              width: '16px',
              height: '16px',
              border: `2px solid ${colors.text}`,
              borderTopColor: 'transparent',
              borderRadius: '50%',
            }}
          />
        )}

        {/* 图标 */}
        {icon && !loading && <span style={{ display: 'flex', alignItems: 'center' }}>{icon}</span>}

        {/* 文本 */}
        {!loading && <span style={{ display: 'flex', alignItems: 'center' }}>{children}</span>}

        {/* 附魔闪光效果 */}
        {variant === 'enchanted' && !disabled && (
          <motion.div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background:
                'linear-gradient(135deg, transparent 0%, rgba(156, 107, 255, 0.3) 50%, transparent 100%)',
              pointerEvents: 'none',
            }}
            animate={{
              x: ['-100%', '200%'],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        )}
      </motion.button>

      {/* 工具提示 */}
      <AnimatePresence>
        {tooltip && isHovered && !disabled && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '8px',
              padding: '4px 8px',
              backgroundColor: minecraftColors.ui.background.tooltip,
              color: minecraftColors.ui.text.secondary,
              border: `1px solid ${minecraftColors.ui.border.dark}`,
              fontSize: typography.fontSize.tooltip,
              fontFamily: typography.fontFamily.minecraft,
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              zIndex: 1000,
            }}
          >
            {tooltip}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

// 按钮组组件
export interface MCButtonGroupProps {
  children: React.ReactNode
  orientation?: 'horizontal' | 'vertical'
  spacing?: number
  className?: string
  style?: React.CSSProperties
}

export const MCButtonGroup: React.FC<MCButtonGroupProps> = ({
  children,
  orientation = 'horizontal',
  spacing = 8,
  className = '',
  style = {},
}) => {
  const groupStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: orientation === 'horizontal' ? 'row' : 'column',
    gap: `${spacing}px`,
    ...style,
  }

  return (
    <div className={`mc-button-group ${className}`} style={groupStyles}>
      {children}
    </div>
  )
}

export default MCButton
