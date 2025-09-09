/**
 * Minecraft 风格输入框组件
 * 模拟 Minecraft 游戏内的输入框样式
 */

import React, { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { minecraftColors, get3DBorder } from '../../theme/minecraft/colors'
import { typography } from '../../theme/minecraft/typography'

export interface MCInputProps {
  value?: string
  defaultValue?: string
  placeholder?: string
  type?: 'text' | 'password' | 'number' | 'search' | 'email' | 'url'
  variant?: 'default' | 'chat' | 'command' | 'sign'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  readOnly?: boolean
  error?: boolean
  success?: boolean
  fullWidth?: boolean
  multiline?: boolean
  rows?: number
  maxLength?: number
  prefix?: React.ReactNode
  suffix?: React.ReactNode
  label?: string
  helperText?: string
  onChange?: (value: string) => void
  onEnter?: (value: string) => void
  onFocus?: () => void
  onBlur?: () => void
  className?: string
  style?: React.CSSProperties
}

const MCInput: React.FC<MCInputProps> = ({
  value,
  defaultValue,
  placeholder,
  type = 'text',
  variant = 'default',
  size = 'medium',
  disabled = false,
  readOnly = false,
  error = false,
  success = false,
  fullWidth = false,
  multiline = false,
  rows = 3,
  maxLength,
  prefix,
  suffix,
  label,
  helperText,
  onChange,
  onEnter,
  onFocus,
  onBlur,
  className = '',
  style = {},
}) => {
  const [inputValue, setInputValue] = useState(value || defaultValue || '')
  const [isFocused, setIsFocused] = useState(false)
  const [showCursor, setShowCursor] = useState(true)
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null)

  // 同步外部 value
  useEffect(() => {
    if (value !== undefined) {
      setInputValue(value)
    }
  }, [value])

  // 光标闪烁效果
  useEffect(() => {
    if (isFocused && variant === 'chat') {
      const interval = setInterval(() => {
        setShowCursor(prev => !prev)
      }, 500)
      return () => clearInterval(interval)
    }
  }, [isFocused, variant])

  // 获取变体样式
  const getVariantStyles = () => {
    switch (variant) {
      case 'chat':
        return {
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          color: minecraftColors.ui.text.secondary,
          borderColor: 'transparent',
        }
      case 'command':
        return {
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          color: minecraftColors.formatting['§e'],
          borderColor: minecraftColors.ui.border.dark,
        }
      case 'sign':
        return {
          backgroundColor: '#8B6F3D',
          color: minecraftColors.ui.text.primary,
          borderColor: '#6B4F2D',
        }
      default:
        return {
          backgroundColor: minecraftColors.ui.background.primary,
          color: minecraftColors.ui.text.primary,
          borderColor: minecraftColors.ui.border.slot,
        }
    }
  }

  // 获取尺寸样式
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return {
          padding: '4px 8px',
          fontSize: typography.fontSize.small,
          height: multiline ? 'auto' : '28px',
        }
      case 'large':
        return {
          padding: '12px 16px',
          fontSize: typography.fontSize.large,
          height: multiline ? 'auto' : '48px',
        }
      default:
        return {
          padding: '8px 12px',
          fontSize: typography.fontSize.normal,
          height: multiline ? 'auto' : '36px',
        }
    }
  }

  // 获取状态颜色
  const getStatusColor = () => {
    if (error) return minecraftColors.ui.text.enchanted
    if (success) return minecraftColors.primary.emerald
    if (isFocused) return minecraftColors.primary.diamond
    return minecraftColors.ui.border.slot
  }

  const variantStyles = getVariantStyles()
  const sizeStyles = getSizeStyles()
  const borderStyles = get3DBorder(false)
  const statusColor = getStatusColor()

  // 输入框样式
  const inputStyles: React.CSSProperties = {
    width: fullWidth ? '100%' : 'auto',
    ...sizeStyles,
    backgroundColor: variantStyles.backgroundColor,
    color: disabled ? minecraftColors.ui.text.disabled : variantStyles.color,
    border: `2px solid ${statusColor}`,
    ...borderStyles,
    fontFamily: typography.fontFamily.minecraft,
    letterSpacing: typography.letterSpacing.pixel,
    outline: 'none',
    cursor: disabled ? 'not-allowed' : 'text',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.2s',
    imageRendering: 'pixelated',
    resize: multiline ? 'vertical' : 'none',
    minHeight: multiline ? `${rows * 24}px` : 'auto',
    ...style,
  }

  // 处理输入变化
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const newValue = e.target.value
    if (maxLength && newValue.length > maxLength) return

    setInputValue(newValue)
    onChange?.(newValue)
  }

  // 处理回车键
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !multiline) {
      e.preventDefault()
      onEnter?.(inputValue)
    }
  }

  // 处理焦点
  const handleFocus = () => {
    setIsFocused(true)
    onFocus?.()
  }

  // 处理失焦
  const handleBlur = () => {
    setIsFocused(false)
    onBlur?.()
  }

  const InputComponent = multiline ? 'textarea' : 'input'

  return (
    <div className={`mc-input-container ${className}`}>
      {/* 标签 */}
      {label && (
        <label
          style={{
            display: 'block',
            marginBottom: '4px',
            color: minecraftColors.ui.text.primary,
            fontSize: typography.fontSize.label,
            fontFamily: typography.fontFamily.minecraft,
            textShadow: '1px 1px 0px rgba(0, 0, 0, 0.25)',
          }}
        >
          {label}
        </label>
      )}

      {/* 输入框容器 */}
      <div
        style={{
          position: 'relative',
          display: fullWidth ? 'block' : 'inline-block',
          width: fullWidth ? '100%' : 'auto',
        }}
      >
        {/* 前缀 */}
        {prefix && (
          <div
            style={{
              position: 'absolute',
              left: '8px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: minecraftColors.ui.text.disabled,
              pointerEvents: 'none',
            }}
          >
            {prefix}
          </div>
        )}

        {/* 输入框 */}
        <InputComponent
          ref={inputRef as any}
          type={multiline ? undefined : type}
          value={inputValue}
          placeholder={placeholder}
          disabled={disabled}
          readOnly={readOnly}
          maxLength={maxLength}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          style={{
            ...inputStyles,
            paddingLeft: prefix ? '32px' : sizeStyles.padding.split(' ')[1],
            paddingRight: suffix ? '32px' : sizeStyles.padding.split(' ')[1],
          }}
        />

        {/* 后缀 */}
        {suffix && (
          <div
            style={{
              position: 'absolute',
              right: '8px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: minecraftColors.ui.text.disabled,
            }}
          >
            {suffix}
          </div>
        )}

        {/* 聊天模式光标 */}
        {variant === 'chat' && isFocused && (
          <span
            style={{
              position: 'absolute',
              right: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: minecraftColors.ui.text.secondary,
              fontSize: sizeStyles.fontSize,
              fontFamily: typography.fontFamily.minecraft,
              opacity: showCursor ? 1 : 0,
              transition: 'opacity 0.1s',
              pointerEvents: 'none',
            }}
          >
            _
          </span>
        )}

        {/* 命令模式提示 */}
        {variant === 'command' && inputValue.startsWith('/') && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              position: 'absolute',
              bottom: '100%',
              left: 0,
              marginBottom: '4px',
              padding: '4px 8px',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              color: minecraftColors.formatting['§7'],
              fontSize: typography.fontSize.small,
              fontFamily: typography.fontFamily.minecraft,
              whiteSpace: 'nowrap',
            }}
          >
            Press Tab for suggestions
          </motion.div>
        )}
      </div>

      {/* 帮助文本 */}
      {helperText && (
        <div
          style={{
            marginTop: '4px',
            color: error
              ? minecraftColors.ui.text.enchanted
              : success
                ? minecraftColors.primary.emerald
                : minecraftColors.ui.text.disabled,
            fontSize: typography.fontSize.caption,
            fontFamily: typography.fontFamily.minecraft,
          }}
        >
          {helperText}
        </div>
      )}

      {/* 字符计数 */}
      {maxLength && (
        <div
          style={{
            marginTop: '4px',
            textAlign: 'right',
            color:
              inputValue.length >= maxLength
                ? minecraftColors.ui.text.enchanted
                : minecraftColors.ui.text.disabled,
            fontSize: typography.fontSize.caption,
            fontFamily: typography.fontFamily.minecraft,
          }}
        >
          {inputValue.length}/{maxLength}
        </div>
      )}
    </div>
  )
}

// 搜索框组件
export interface MCSearchBoxProps {
  value?: string
  placeholder?: string
  onSearch?: (value: string) => void
  onChange?: (value: string) => void
  size?: 'small' | 'medium' | 'large'
  fullWidth?: boolean
  className?: string
  style?: React.CSSProperties
}

export const MCSearchBox: React.FC<MCSearchBoxProps> = ({
  value,
  placeholder = 'Search...',
  onSearch,
  onChange,
  size = 'medium',
  fullWidth = false,
  className = '',
  style = {},
}) => {
  const [searchValue, setSearchValue] = useState(value || '')

  const handleChange = (newValue: string) => {
    setSearchValue(newValue)
    onChange?.(newValue)
  }

  const handleSearch = () => {
    onSearch?.(searchValue)
  }

  return (
    <div
      className={`mc-search-box ${className}`}
      style={{
        display: 'flex',
        gap: '8px',
        width: fullWidth ? '100%' : 'auto',
        ...style,
      }}
    >
      <MCInput
        value={searchValue}
        placeholder={placeholder}
        type='search'
        size={size}
        fullWidth
        prefix={<span>🔍</span>}
        onChange={handleChange}
        onEnter={handleSearch}
        style={{ flex: 1 }}
      />
      <MCButton onClick={handleSearch} variant='primary' size={size}>
        Search
      </MCButton>
    </div>
  )
}

// 导入必要的组件
import MCButton from './MCButton'

export default MCInput
