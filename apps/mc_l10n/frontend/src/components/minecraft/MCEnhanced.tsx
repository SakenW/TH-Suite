/**
 * MC 增强组件集
 * 基于 Tailwind CSS + Minecraft 主题的现代化组件
 */

import React, { useState, useEffect, ReactNode } from 'react'
import { Card, Button, Progress, Tag, Badge, Tooltip } from 'antd'
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  LoadingOutlined, 
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  RocketOutlined
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'

// 类型定义
interface MCCardProps {
  children: ReactNode
  title?: string
  variant?: 'default' | 'glass' | 'pixel' | 'floating'
  glow?: boolean
  className?: string
  onClick?: () => void
}

interface MCButtonProps {
  children: ReactNode
  type?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger'
  variant?: 'default' | 'block' | 'pixel' | 'glow'
  size?: 'small' | 'medium' | 'large'
  loading?: boolean
  disabled?: boolean
  onClick?: () => void
  className?: string
}

interface MCProgressProps {
  percent: number
  showInfo?: boolean
  status?: 'normal' | 'success' | 'exception' | 'active'
  variant?: 'exp' | 'health' | 'mana' | 'loading'
  animated?: boolean
  glow?: boolean
  className?: string
}

interface MCStatusProps {
  type: 'success' | 'error' | 'warning' | 'info' | 'loading'
  text: string
  animated?: boolean
  showDot?: boolean
  className?: string
}

// MC 卡片组件
export const MCCard: React.FC<MCCardProps> = ({ 
  children, 
  title, 
  variant = 'default',
  glow = false,
  className = '',
  onClick 
}) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'glass':
        return 'glass-effect backdrop-blur-glass border-white/20'
      case 'pixel':
        return 'minecraft-card pixel-shadow border-2 border-mc-stone/30'
      case 'floating':
        return 'minecraft-card animate-float hover:animate-none hover:-translate-y-1'
      default:
        return 'minecraft-card border border-gray-200/50'
    }
  }

  const motionProps = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    whileHover: onClick ? { y: -2, scale: 1.02 } : {},
    transition: { duration: 0.3, ease: "easeOut" }
  }

  return (
    <motion.div {...motionProps}>
      <Card
        title={title}
        className={`
          ${getVariantClasses()}
          ${glow ? 'animate-glow' : ''}
          ${onClick ? 'cursor-pointer' : ''}
          ${className}
          transition-all duration-300 ease-out
          hover:shadow-depth
          bg-gradient-to-br from-white/5 to-black/5
        `}
        bodyStyle={{ 
          padding: '16px',
          background: 'transparent'
        }}
        onClick={onClick}
      >
        {children}
      </Card>
    </motion.div>
  )
}

// MC 按钮组件
export const MCButton: React.FC<MCButtonProps> = ({
  children,
  type = 'primary',
  variant = 'default',
  size = 'medium',
  loading = false,
  disabled = false,
  onClick,
  className = ''
}) => {
  const getTypeClasses = () => {
    switch (type) {
      case 'primary':
        return 'bg-mc-emerald hover:bg-mc-grass text-white border-mc-emerald/50'
      case 'secondary':
        return 'bg-mc-stone hover:bg-mc-cobblestone text-white border-mc-stone/50'
      case 'success':
        return 'bg-mc-grass hover:bg-mc-forest text-white border-mc-grass/50'
      case 'warning':
        return 'bg-mc-gold hover:bg-yellow-500 text-white border-mc-gold/50'
      case 'danger':
        return 'bg-mc-redstone hover:bg-red-600 text-white border-mc-redstone/50'
      default:
        return 'bg-gray-100 hover:bg-gray-200 text-gray-800 border-gray-300'
    }
  }

  const getVariantClasses = () => {
    switch (variant) {
      case 'block':
        return 'rounded-block shadow-block hover:shadow-pixel active:shadow-inner-pixel'
      case 'pixel':
        return 'rounded-pixel shadow-pixel font-pixel text-pixel'
      case 'glow':
        return 'rounded-lg shadow-glow-emerald hover:shadow-glow-gold animate-glow'
      default:
        return 'rounded-md shadow-md hover:shadow-lg'
    }
  }

  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'px-3 py-1.5 text-sm'
      case 'large':
        return 'px-8 py-3 text-lg'
      default:
        return 'px-6 py-2 text-base'
    }
  }

  return (
    <motion.div
      whileHover={{ scale: disabled ? 1 : 1.05 }}
      whileTap={{ scale: disabled ? 1 : 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <Button
        className={`
          ${getTypeClasses()}
          ${getVariantClasses()}
          ${getSizeClasses()}
          ${className}
          relative overflow-hidden
          before:absolute before:top-0 before:left-[-100%] before:w-full before:h-full
          before:bg-shimmer-gradient before:bg-shimmer
          hover:before:left-[100%] before:transition-all before:duration-500
          transition-all duration-300 ease-out
          border-2 font-medium
          disabled:opacity-50 disabled:cursor-not-allowed
          ${!disabled ? 'hover:-translate-y-0.5 active:translate-y-0' : ''}
        `}
        loading={loading}
        disabled={disabled}
        onClick={onClick}
        style={{ border: 'none' }}
      >
        {children}
      </Button>
    </motion.div>
  )
}

// MC 进度条组件
export const MCProgress: React.FC<MCProgressProps> = ({
  percent,
  showInfo = true,
  status = 'normal',
  variant = 'exp',
  animated = true,
  glow = false,
  className = ''
}) => {
  const [displayPercent, setDisplayPercent] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDisplayPercent(percent)
    }, 100)
    return () => clearTimeout(timer)
  }, [percent])

  const getVariantClasses = () => {
    switch (variant) {
      case 'exp':
        return 'exp-bar'
      case 'health':
        return 'bg-gradient-to-r from-mc-redstone to-red-400 border border-mc-redstone/50'
      case 'mana':
        return 'bg-gradient-to-r from-mc-lapis to-blue-400 border border-mc-lapis/50'
      case 'loading':
        return 'bg-gradient-to-r from-mc-gold to-yellow-400 border border-mc-gold/50 shimmer'
      default:
        return 'bg-gradient-to-r from-mc-emerald to-mc-grass border border-mc-emerald/50'
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined className="text-mc-grass ml-2" />
      case 'exception':
        return <ExclamationCircleOutlined className="text-mc-redstone ml-2" />
      default:
        return null
    }
  }

  return (
    <div className={`relative ${className}`}>
      <div className={`
        w-full h-2 bg-gray-200/50 rounded-pixel overflow-hidden
        ${glow ? 'shadow-glow-emerald' : 'shadow-inner-pixel'}
        relative
      `}>
        <motion.div
          className={`
            h-full rounded-pixel relative overflow-hidden
            ${getVariantClasses()}
            ${animated ? 'transition-all duration-1000 ease-out' : ''}
          `}
          initial={{ width: 0 }}
          animate={{ width: `${displayPercent}%` }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        >
          {variant === 'exp' && (
            <>
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white/40 to-transparent" />
              <div className="absolute top-0 left-0 w-8 h-full bg-gradient-to-r from-transparent via-white/60 to-transparent animate-shimmer" />
            </>
          )}
        </motion.div>
      </div>
      
      {showInfo && (
        <div className="flex items-center justify-between mt-1 text-sm text-gray-600">
          <span className="font-medium">{displayPercent}%</span>
          {getStatusIcon()}
        </div>
      )}
    </div>
  )
}

// MC 状态指示器
export const MCStatus: React.FC<MCStatusProps> = ({
  type,
  text,
  animated = true,
  showDot = true,
  className = ''
}) => {
  const getStatusConfig = () => {
    switch (type) {
      case 'success':
        return {
          icon: <CheckCircleOutlined />,
          color: 'text-mc-grass',
          bgColor: 'bg-mc-grass/10',
          borderColor: 'border-mc-grass/30',
          dotColor: 'bg-mc-grass'
        }
      case 'error':
        return {
          icon: <ExclamationCircleOutlined />,
          color: 'text-mc-redstone',
          bgColor: 'bg-mc-redstone/10',
          borderColor: 'border-mc-redstone/30',
          dotColor: 'bg-mc-redstone'
        }
      case 'warning':
        return {
          icon: <WarningOutlined />,
          color: 'text-mc-gold',
          bgColor: 'bg-mc-gold/10',
          borderColor: 'border-mc-gold/30',
          dotColor: 'bg-mc-gold'
        }
      case 'info':
        return {
          icon: <InfoCircleOutlined />,
          color: 'text-mc-lapis',
          bgColor: 'bg-mc-lapis/10',
          borderColor: 'border-mc-lapis/30',
          dotColor: 'bg-mc-lapis'
        }
      case 'loading':
        return {
          icon: <LoadingOutlined />,
          color: 'text-mc-stone',
          bgColor: 'bg-mc-stone/10',
          borderColor: 'border-mc-stone/30',
          dotColor: 'bg-mc-stone'
        }
    }
  }

  const config = getStatusConfig()

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={`
        inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
        ${config.color} ${config.bgColor} ${config.borderColor}
        border transition-all duration-300
        ${className}
      `}
    >
      {showDot && (
        <motion.div
          className={`w-2 h-2 rounded-full ${config.dotColor}`}
          animate={animated && type === 'loading' ? { scale: [1, 1.2, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
      {config.icon}
      <span className="uppercase tracking-wide">{text}</span>
    </motion.div>
  )
}

// MC 特效徽章组件
export const MCBadge: React.FC<{
  children: ReactNode
  type?: 'achievement' | 'level' | 'rare' | 'epic' | 'legendary'
  animated?: boolean
  className?: string
}> = ({ children, type = 'achievement', animated = true, className = '' }) => {
  const getTypeConfig = () => {
    switch (type) {
      case 'achievement':
        return {
          bg: 'bg-gradient-to-r from-mc-gold to-yellow-400',
          icon: <TrophyOutlined />,
          glow: 'shadow-glow-gold'
        }
      case 'level':
        return {
          bg: 'bg-gradient-to-r from-mc-emerald to-mc-grass',
          icon: <ThunderboltOutlined />,
          glow: 'shadow-glow-emerald'
        }
      case 'rare':
        return {
          bg: 'bg-gradient-to-r from-blue-500 to-mc-lapis',
          icon: <RocketOutlined />,
          glow: 'shadow-glow-lapis'
        }
      case 'epic':
        return {
          bg: 'bg-gradient-to-r from-purple-500 to-purple-700',
          icon: <TrophyOutlined />,
          glow: 'shadow-purple-500/50'
        }
      case 'legendary':
        return {
          bg: 'bg-gradient-to-r from-orange-500 to-red-500',
          icon: <TrophyOutlined />,
          glow: 'shadow-orange-500/50'
        }
    }
  }

  const config = getTypeConfig()

  return (
    <motion.div
      initial={{ scale: 0, rotate: -180 }}
      animate={{ scale: 1, rotate: 0 }}
      whileHover={{ scale: 1.1, rotate: 5 }}
      transition={{ 
        type: "spring", 
        stiffness: 260, 
        damping: 20 
      }}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-white text-sm font-bold
        ${config.bg} ${config.glow}
        ${animated ? 'animate-glow' : ''}
        ${className}
        shadow-lg
      `}
    >
      {config.icon}
      {children}
    </motion.div>
  )
}

// MC 浮动操作按钮
export const MCFloatingButton: React.FC<{
  icon: ReactNode
  tooltip?: string
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'danger'
  className?: string
}> = ({ icon, tooltip, onClick, variant = 'primary', className = '' }) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'primary':
        return 'bg-mc-emerald hover:bg-mc-grass shadow-glow-emerald'
      case 'secondary':
        return 'bg-mc-lapis hover:bg-blue-600 shadow-glow-lapis'
      case 'danger':
        return 'bg-mc-redstone hover:bg-red-600 shadow-glow-redstone'
      default:
        return 'bg-mc-emerald hover:bg-mc-grass shadow-glow-emerald'
    }
  }

  const button = (
    <motion.button
      whileHover={{ scale: 1.1, rotate: 10 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`
        fixed bottom-6 right-6 z-50
        w-14 h-14 rounded-full text-white text-xl
        ${getVariantClasses()}
        ${className}
        flex items-center justify-center
        transition-all duration-300 ease-out
        hover:shadow-xl
        animate-float
      `}
    >
      {icon}
    </motion.button>
  )

  if (tooltip) {
    return <Tooltip title={tooltip}>{button}</Tooltip>
  }

  return button
}