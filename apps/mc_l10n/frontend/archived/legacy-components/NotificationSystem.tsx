/**
 * 通知系统组件
 * 提供多种类型的通知展示和管理
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Snackbar,
  Alert,
  AlertTitle,
  IconButton,
  Typography,
  Slide,
  Stack,
  LinearProgress,
  Paper,
  Chip,
  Avatar,
  Divider,
} from '@mui/material'
import { useTheme, alpha } from '@mui/material/styles'
import {
  X,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Info,
  Bell,
  User,
  Settings,
  Download,
  Upload,
  Trash2,
  Clock,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export type NotificationType = 'success' | 'error' | 'warning' | 'info'
export type NotificationVariant = 'toast' | 'banner' | 'inline' | 'floating'

export interface NotificationAction {
  label: string
  onClick: () => void
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
}

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message?: string
  timestamp?: Date
  duration?: number // 持续时间，毫秒，0表示不自动关闭
  actions?: NotificationAction[]
  persistent?: boolean
  progress?: number // 0-100，用于进度提示
  avatar?: React.ReactNode
  icon?: React.ReactNode
  variant?: NotificationVariant
}

interface NotificationSystemProps {
  notifications: Notification[]
  onClose: (id: string) => void
  position?: 'top' | 'bottom' | 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left'
  maxNotifications?: number
  groupSimilar?: boolean
}

interface ToastNotificationProps {
  notification: Notification
  onClose: () => void
  position: string
}

const getNotificationIcon = (type: NotificationType, customIcon?: React.ReactNode) => {
  if (customIcon) return customIcon

  switch (type) {
    case 'success':
      return <CheckCircle size={20} />
    case 'error':
      return <AlertCircle size={20} />
    case 'warning':
      return <AlertTriangle size={20} />
    case 'info':
    default:
      return <Info size={20} />
  }
}

const ToastNotification: React.FC<ToastNotificationProps> = ({
  notification,
  onClose,
  position,
}) => {
  const theme = useTheme()
  const [progress, setProgress] = useState(100)

  // 自动关闭倒计时
  useEffect(() => {
    if (notification.duration && notification.duration > 0) {
      const interval = 50
      const decrement = (interval / notification.duration) * 100

      const timer = setInterval(() => {
        setProgress(prev => {
          if (prev <= 0) {
            onClose()
            return 0
          }
          return prev - decrement
        })
      }, interval)

      return () => clearInterval(timer)
    }
  }, [notification.duration, onClose])

  const getSlideDirection = (position: string) => {
    if (position.includes('right')) return 'left'
    if (position.includes('left')) return 'right'
    if (position.includes('top')) return 'down'
    return 'up'
  }

  return (
    <Slide direction={getSlideDirection(position)} in={true} timeout={300}>
      <Paper
        elevation={8}
        sx={{
          mb: 1,
          borderRadius: 2,
          overflow: 'hidden',
          maxWidth: 400,
          border: `1px solid ${alpha(theme.palette[notification.type].main, 0.3)}`,
          backgroundColor: theme.palette.background.paper,
        }}
      >
        {/* 进度条 */}
        {notification.duration && notification.duration > 0 && (
          <LinearProgress
            variant='determinate'
            value={progress}
            sx={{
              height: 2,
              backgroundColor: alpha(theme.palette[notification.type].main, 0.1),
              '& .MuiLinearProgress-bar': {
                backgroundColor: theme.palette[notification.type].main,
              },
            }}
          />
        )}

        {/* 通知进度 */}
        {notification.progress !== undefined && (
          <LinearProgress
            variant='determinate'
            value={notification.progress}
            sx={{
              height: 3,
              backgroundColor: alpha(theme.palette.primary.main, 0.1),
              '& .MuiLinearProgress-bar': {
                backgroundColor: theme.palette.primary.main,
              },
            }}
          />
        )}

        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
            {/* 头像或图标 */}
            {notification.avatar ? (
              <Avatar sx={{ width: 32, height: 32 }}>{notification.avatar}</Avatar>
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 32,
                  height: 32,
                  borderRadius: 2,
                  backgroundColor: alpha(theme.palette[notification.type].main, 0.1),
                  color: theme.palette[notification.type].main,
                }}
              >
                {getNotificationIcon(notification.type, notification.icon)}
              </Box>
            )}

            <Box sx={{ flex: 1, minWidth: 0 }}>
              {/* 标题和时间 */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 0.5,
                }}
              >
                <Typography
                  variant='subtitle2'
                  sx={{
                    fontWeight: 600,
                    color: theme.palette.text.primary,
                    lineHeight: 1.2,
                  }}
                >
                  {notification.title}
                </Typography>
                {notification.timestamp && (
                  <Typography
                    variant='caption'
                    color='text.secondary'
                    sx={{ ml: 1, flexShrink: 0 }}
                  >
                    {notification.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </Typography>
                )}
              </Box>

              {/* 消息内容 */}
              {notification.message && (
                <Typography
                  variant='body2'
                  color='text.secondary'
                  sx={{
                    mb: notification.actions?.length ? 1.5 : 0,
                    lineHeight: 1.4,
                  }}
                >
                  {notification.message}
                </Typography>
              )}

              {/* 进度信息 */}
              {notification.progress !== undefined && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant='caption' color='text.secondary'>
                    进度: {Math.round(notification.progress)}%
                  </Typography>
                </Box>
              )}

              {/* 操作按钮 */}
              {notification.actions && notification.actions.length > 0 && (
                <Stack direction='row' spacing={1}>
                  {notification.actions.map((action, index) => (
                    <Chip
                      key={index}
                      label={action.label}
                      size='small'
                      clickable
                      onClick={action.onClick}
                      color={action.color || 'primary'}
                      variant='outlined'
                      sx={{
                        fontSize: '0.75rem',
                        height: 24,
                        '&:hover': {
                          backgroundColor: alpha(
                            theme.palette[action.color || 'primary'].main,
                            0.08,
                          ),
                        },
                      }}
                    />
                  ))}
                </Stack>
              )}
            </Box>

            {/* 关闭按钮 */}
            <IconButton
              size='small'
              onClick={onClose}
              sx={{
                color: 'text.secondary',
                '&:hover': {
                  backgroundColor: alpha(theme.palette.action.hover, 0.5),
                },
              }}
            >
              <X size={16} />
            </IconButton>
          </Box>
        </Box>
      </Paper>
    </Slide>
  )
}

export const NotificationSystem: React.FC<NotificationSystemProps> = ({
  notifications,
  onClose,
  position = 'top-right',
  maxNotifications = 5,
  groupSimilar = true,
}) => {
  const theme = useTheme()

  // 根据位置获取容器样式
  const getPositionStyles = () => {
    const base = {
      position: 'fixed' as const,
      zIndex: theme.zIndex.snackbar + 1,
      pointerEvents: 'none' as const,
    }

    switch (position) {
      case 'top-right':
        return { ...base, top: 24, right: 24 }
      case 'top-left':
        return { ...base, top: 24, left: 24 }
      case 'bottom-right':
        return { ...base, bottom: 24, right: 24 }
      case 'bottom-left':
        return { ...base, bottom: 24, left: 24 }
      case 'top':
        return { ...base, top: 24, left: '50%', transform: 'translateX(-50%)' }
      case 'bottom':
        return { ...base, bottom: 24, left: '50%', transform: 'translateX(-50%)' }
      default:
        return { ...base, top: 24, right: 24 }
    }
  }

  // 处理通知分组
  const processedNotifications = groupSimilar
    ? notifications.reduce((acc, notification) => {
        const existing = acc.find(
          n => n.title === notification.title && n.type === notification.type && !n.persistent,
        )

        if (existing && !notification.persistent) {
          // 更新现有通知的时间戳和消息
          existing.timestamp = notification.timestamp
          existing.message = notification.message
          return acc
        }

        return [...acc, notification]
      }, [] as Notification[])
    : notifications

  // 限制通知数量
  const visibleNotifications = processedNotifications.slice(0, maxNotifications)

  return (
    <Box sx={getPositionStyles()}>
      <AnimatePresence mode='sync'>
        {visibleNotifications.map((notification, index) => (
          <motion.div
            key={notification.id}
            layout
            initial={{ opacity: 0, y: position.includes('bottom') ? 50 : -50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{
              opacity: 0,
              y: position.includes('bottom') ? 50 : -50,
              scale: 0.9,
              transition: { duration: 0.2 },
            }}
            transition={{
              duration: 0.3,
              delay: index * 0.05,
              layout: { duration: 0.2 },
            }}
            style={{ pointerEvents: 'auto' }}
          >
            {notification.variant === 'toast' || !notification.variant ? (
              <ToastNotification
                notification={notification}
                onClose={() => onClose(notification.id)}
                position={position}
              />
            ) : (
              // 其他变体的通知可以在这里实现
              <ToastNotification
                notification={notification}
                onClose={() => onClose(notification.id)}
                position={position}
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* 显示更多通知的提示 */}
      {notifications.length > maxNotifications && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ pointerEvents: 'auto' }}
        >
          <Paper
            elevation={4}
            sx={{
              p: 1.5,
              mt: 1,
              borderRadius: 2,
              backgroundColor: alpha(theme.palette.background.paper, 0.9),
              backdropFilter: 'blur(8px)',
              border: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Typography variant='caption' color='text.secondary' textAlign='center' display='block'>
              还有 {notifications.length - maxNotifications} 条通知未显示
            </Typography>
          </Paper>
        </motion.div>
      )}
    </Box>
  )
}
