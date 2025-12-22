import React, { useEffect, useState } from 'react'
import { Box, Typography, IconButton, Portal } from '@mui/material'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Info,
  X,
  Trophy,
  Sparkles,
  Zap,
  Heart,
  Star,
  Package,
  Download,
  Upload,
  Save,
  Shield,
  Sword,
  Gem,
} from 'lucide-react'
import { minecraftColors } from '../../theme/minecraftTheme'
import { MinecraftBlock } from '../MinecraftComponents'

export type NotificationType = 'success' | 'error' | 'warning' | 'info' | 'achievement' | 'system'

export interface NotificationOptions {
  id?: string
  title: string
  message?: string
  type?: NotificationType
  duration?: number
  icon?: React.ReactNode
  position?:
    | 'top-right'
    | 'top-left'
    | 'bottom-right'
    | 'bottom-left'
    | 'top-center'
    | 'bottom-center'
  sound?: boolean
  persistent?: boolean
  actions?: Array<{
    label: string
    onClick: () => void
    style?: 'primary' | 'secondary'
  }>
  onClose?: () => void
  progress?: number
  minecraft?: {
    block?: 'grass' | 'stone' | 'diamond' | 'gold' | 'iron' | 'emerald' | 'redstone'
    particle?: boolean
    glow?: boolean
  }
}

interface MinecraftNotificationProps extends NotificationOptions {
  onRemove: () => void
}

const typeConfig = {
  success: {
    icon: <CheckCircle size={20} />,
    color: minecraftColors.emerald,
    block: 'emerald' as const,
    title: '成功',
  },
  error: {
    icon: <XCircle size={20} />,
    color: minecraftColors.redstoneRed,
    block: 'redstone' as const,
    title: '错误',
  },
  warning: {
    icon: <AlertCircle size={20} />,
    color: minecraftColors.goldYellow,
    block: 'gold' as const,
    title: '警告',
  },
  info: {
    icon: <Info size={20} />,
    color: minecraftColors.diamondBlue,
    block: 'diamond' as const,
    title: '信息',
  },
  achievement: {
    icon: <Trophy size={20} />,
    color: minecraftColors.goldYellow,
    block: 'gold' as const,
    title: '成就解锁',
  },
  system: {
    icon: <Zap size={20} />,
    color: minecraftColors.iron,
    block: 'iron' as const,
    title: '系统',
  },
}

export const MinecraftNotification: React.FC<MinecraftNotificationProps> = ({
  title,
  message,
  type = 'info',
  duration = 5000,
  icon,
  persistent = false,
  actions,
  onClose,
  onRemove,
  progress,
  minecraft = {},
}) => {
  const [isHovered, setIsHovered] = useState(false)
  const [timeLeft, setTimeLeft] = useState(duration)
  const config = typeConfig[type]
  const displayIcon = icon || config.icon
  const blockType = minecraft.block || config.block

  useEffect(() => {
    if (!persistent && !isHovered && timeLeft > 0) {
      const timer = setTimeout(() => {
        setTimeLeft(prev => prev - 100)
      }, 100)

      if (timeLeft <= 100) {
        onRemove()
      }

      return () => clearTimeout(timer)
    }
  }, [persistent, isHovered, timeLeft, onRemove])

  const progressPercentage = persistent ? 0 : ((duration - timeLeft) / duration) * 100

  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 500, damping: 40 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ width: 360 }}
    >
      <Box
        sx={{
          position: 'relative',
          bgcolor: 'rgba(15, 23, 42, 0.98)',
          border: `3px solid ${config.color}`,
          borderRadius: 0,
          overflow: 'hidden',
          boxShadow: `0 0 20px ${config.color}33, inset 0 0 20px rgba(0,0,0,0.5)`,
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '3px',
            background: `linear-gradient(90deg, transparent, ${config.color}, transparent)`,
            animation: minecraft.glow ? 'shimmer 2s infinite' : 'none',
          },
          '@keyframes shimmer': {
            '0%': { transform: 'translateX(-100%)' },
            '100%': { transform: 'translateX(100%)' },
          },
        }}
      >
        {/* 进度条 */}
        {!persistent && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              height: 3,
              width: `${100 - progressPercentage}%`,
              bgcolor: config.color,
              opacity: 0.5,
              transition: 'width 0.1s linear',
            }}
          />
        )}

        {/* 内容区域 */}
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
            {/* 图标区域 */}
            <Box
              sx={{
                width: 40,
                height: 40,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: `${config.color}22`,
                border: `2px solid ${config.color}`,
                borderRadius: 0,
                flexShrink: 0,
                position: 'relative',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  inset: -2,
                  border: `1px solid ${config.color}44`,
                  borderRadius: 0,
                  pointerEvents: 'none',
                },
              }}
            >
              {type === 'achievement' ? (
                <MinecraftBlock type={blockType} size={24} animated />
              ) : (
                <Box sx={{ color: config.color }}>{displayIcon}</Box>
              )}
            </Box>

            {/* 文本内容 */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography
                variant='subtitle2'
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  color: '#FFFFFF',
                  mb: message ? 0.5 : 0,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                {title}
                {type === 'achievement' && (
                  <Sparkles size={14} style={{ color: minecraftColors.goldYellow }} />
                )}
              </Typography>
              {message && (
                <Typography
                  variant='caption'
                  sx={{
                    color: 'rgba(255,255,255,0.7)',
                    display: 'block',
                    lineHeight: 1.4,
                  }}
                >
                  {message}
                </Typography>
              )}

              {/* 自定义进度 */}
              {progress !== undefined && (
                <Box sx={{ mt: 1 }}>
                  <Box
                    sx={{
                      height: 4,
                      bgcolor: 'rgba(255,255,255,0.1)',
                      borderRadius: 0,
                      overflow: 'hidden',
                    }}
                  >
                    <Box
                      sx={{
                        height: '100%',
                        width: `${progress}%`,
                        bgcolor: config.color,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </Box>
                  <Typography
                    variant='caption'
                    sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '10px' }}
                  >
                    {progress}%
                  </Typography>
                </Box>
              )}

              {/* 操作按钮 */}
              {actions && actions.length > 0 && (
                <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                  {actions.map((action, index) => (
                    <Box
                      key={index}
                      component='button'
                      onClick={action.onClick}
                      sx={{
                        px: 1.5,
                        py: 0.5,
                        bgcolor: action.style === 'primary' ? `${config.color}33` : 'transparent',
                        border: `1px solid ${config.color}`,
                        borderRadius: 0,
                        color: '#FFFFFF',
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '11px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        '&:hover': {
                          bgcolor: `${config.color}44`,
                          transform: 'translateY(-1px)',
                        },
                      }}
                    >
                      {action.label}
                    </Box>
                  ))}
                </Box>
              )}
            </Box>

            {/* 关闭按钮 */}
            {(persistent || isHovered) && (
              <IconButton
                size='small'
                onClick={() => {
                  onClose?.()
                  onRemove()
                }}
                sx={{
                  color: 'rgba(255,255,255,0.5)',
                  '&:hover': {
                    color: '#FFFFFF',
                    bgcolor: 'rgba(255,255,255,0.1)',
                  },
                }}
              >
                <X size={16} />
              </IconButton>
            )}
          </Box>
        </Box>

        {/* 成就特效 */}
        {type === 'achievement' && minecraft.particle && (
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none',
              '&::before, &::after': {
                content: '""',
                position: 'absolute',
                width: 4,
                height: 4,
                bgcolor: minecraftColors.goldYellow,
                borderRadius: '50%',
                animation: 'particle 2s infinite',
              },
              '&::before': {
                animationDelay: '0s',
              },
              '&::after': {
                animationDelay: '1s',
              },
              '@keyframes particle': {
                '0%': {
                  transform: 'translate(0, 0) scale(0)',
                  opacity: 1,
                },
                '50%': {
                  transform: 'translate(30px, -30px) scale(1)',
                  opacity: 0.5,
                },
                '100%': {
                  transform: 'translate(60px, -60px) scale(0)',
                  opacity: 0,
                },
              },
            }}
          />
        )}
      </Box>
    </motion.div>
  )
}

// 通知容器组件
interface NotificationContainerProps {
  notifications: NotificationOptions[]
  position?: NotificationOptions['position']
  onRemove: (id: string) => void
}

export const NotificationContainer: React.FC<NotificationContainerProps> = ({
  notifications,
  position = 'top-right',
  onRemove,
}) => {
  const positionStyles = {
    'top-right': { top: 80, right: 20 },
    'top-left': { top: 80, left: 20 },
    'bottom-right': { bottom: 20, right: 20 },
    'bottom-left': { bottom: 20, left: 20 },
    'top-center': { top: 80, left: '50%', transform: 'translateX(-50%)' },
    'bottom-center': { bottom: 20, left: '50%', transform: 'translateX(-50%)' },
  }

  return (
    <Portal>
      <Box
        sx={{
          position: 'fixed',
          ...positionStyles[position],
          zIndex: 9999,
          display: 'flex',
          flexDirection: position.includes('bottom') ? 'column-reverse' : 'column',
          gap: 1.5,
          pointerEvents: 'none',
          '& > *': {
            pointerEvents: 'auto',
          },
        }}
      >
        <AnimatePresence>
          {notifications.map(notification => (
            <MinecraftNotification
              key={notification.id}
              {...notification}
              onRemove={() => onRemove(notification.id!)}
            />
          ))}
        </AnimatePresence>
      </Box>
    </Portal>
  )
}
