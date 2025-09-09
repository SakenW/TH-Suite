/**
 * 状态指示器组件
 * 统一的状态展示组件，支持多种状态类型
 */

import React from 'react'
import { Box, Chip, Typography, Tooltip, alpha } from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  Pause,
  Play,
  Archive,
  Zap,
  Eye,
  Flag,
  Settings,
} from 'lucide-react'

export type StatusType =
  // 项目状态
  | 'active'
  | 'paused'
  | 'archived'
  // 翻译状态
  | 'untranslated'
  | 'translated'
  | 'reviewed'
  | 'approved'
  | 'needs_update'
  // 任务状态
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  // 通用状态
  | 'success'
  | 'error'
  | 'warning'
  | 'info'

interface StatusConfig {
  label: string
  color: string
  bgColor: string
  icon: React.ReactNode
  description?: string
}

interface StatusIndicatorProps {
  status: StatusType
  variant?: 'chip' | 'badge' | 'dot' | 'icon' | 'full'
  size?: 'small' | 'medium' | 'large'
  showIcon?: boolean
  showLabel?: boolean
  customLabel?: string
  tooltip?: string
  pulse?: boolean
  onClick?: () => void
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  variant = 'chip',
  size = 'medium',
  showIcon = true,
  showLabel = true,
  customLabel,
  tooltip,
  pulse = false,
  onClick,
}) => {
  const theme = useTheme()

  const getStatusConfig = (status: StatusType): StatusConfig => {
    const configs: Record<StatusType, StatusConfig> = {
      // 项目状态
      active: {
        label: '活跃',
        color: theme.palette.success.main,
        bgColor: alpha(theme.palette.success.main, 0.1),
        icon: <Play size={16} />,
        description: '项目正在进行中',
      },
      paused: {
        label: '暂停',
        color: theme.palette.warning.main,
        bgColor: alpha(theme.palette.warning.main, 0.1),
        icon: <Pause size={16} />,
        description: '项目已暂停',
      },
      archived: {
        label: '已归档',
        color: theme.palette.action.disabled,
        bgColor: alpha(theme.palette.action.disabled, 0.1),
        icon: <Archive size={16} />,
        description: '项目已归档',
      },

      // 翻译状态
      untranslated: {
        label: '未翻译',
        color: theme.palette.grey[500],
        bgColor: alpha(theme.palette.grey[500], 0.1),
        icon: <Clock size={16} />,
        description: '等待翻译',
      },
      translated: {
        label: '已翻译',
        color: theme.palette.success.main,
        bgColor: alpha(theme.palette.success.main, 0.1),
        icon: <CheckCircle size={16} />,
        description: '翻译完成',
      },
      reviewed: {
        label: '已审核',
        color: theme.palette.info.main,
        bgColor: alpha(theme.palette.info.main, 0.1),
        icon: <Eye size={16} />,
        description: '翻译已审核',
      },
      approved: {
        label: '已批准',
        color: theme.palette.primary.main,
        bgColor: alpha(theme.palette.primary.main, 0.1),
        icon: <Flag size={16} />,
        description: '翻译已批准',
      },
      needs_update: {
        label: '需更新',
        color: theme.palette.warning.main,
        bgColor: alpha(theme.palette.warning.main, 0.1),
        icon: <AlertCircle size={16} />,
        description: '翻译需要更新',
      },

      // 任务状态
      pending: {
        label: '等待中',
        color: theme.palette.grey[500],
        bgColor: alpha(theme.palette.grey[500], 0.1),
        icon: <Clock size={16} />,
        description: '任务等待执行',
      },
      running: {
        label: '运行中',
        color: theme.palette.info.main,
        bgColor: alpha(theme.palette.info.main, 0.1),
        icon: <Settings size={16} />,
        description: '任务正在执行',
      },
      completed: {
        label: '已完成',
        color: theme.palette.success.main,
        bgColor: alpha(theme.palette.success.main, 0.1),
        icon: <CheckCircle size={16} />,
        description: '任务执行成功',
      },
      failed: {
        label: '失败',
        color: theme.palette.error.main,
        bgColor: alpha(theme.palette.error.main, 0.1),
        icon: <XCircle size={16} />,
        description: '任务执行失败',
      },
      cancelled: {
        label: '已取消',
        color: theme.palette.grey[600],
        bgColor: alpha(theme.palette.grey[600], 0.1),
        icon: <XCircle size={16} />,
        description: '任务已取消',
      },

      // 通用状态
      success: {
        label: '成功',
        color: theme.palette.success.main,
        bgColor: alpha(theme.palette.success.main, 0.1),
        icon: <CheckCircle size={16} />,
        description: '操作成功',
      },
      error: {
        label: '错误',
        color: theme.palette.error.main,
        bgColor: alpha(theme.palette.error.main, 0.1),
        icon: <XCircle size={16} />,
        description: '发生错误',
      },
      warning: {
        label: '警告',
        color: theme.palette.warning.main,
        bgColor: alpha(theme.palette.warning.main, 0.1),
        icon: <AlertCircle size={16} />,
        description: '需要注意',
      },
      info: {
        label: '信息',
        color: theme.palette.info.main,
        bgColor: alpha(theme.palette.info.main, 0.1),
        icon: <Zap size={16} />,
        description: '提示信息',
      },
    }

    return configs[status]
  }

  const config = getStatusConfig(status)
  const displayLabel = customLabel || config.label
  const displayTooltip = tooltip || config.description

  const getIconSize = () => {
    switch (size) {
      case 'small':
        return 12
      case 'large':
        return 20
      case 'medium':
      default:
        return 16
    }
  }

  const iconElement = React.cloneElement(config.icon as React.ReactElement, {
    size: getIconSize(),
    color: config.color,
  })

  const pulseAnimation = pulse
    ? {
        animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        '@keyframes pulse': {
          '0%, 100%': {
            opacity: 1,
          },
          '50%': {
            opacity: 0.5,
          },
        },
      }
    : {}

  const renderStatusElement = () => {
    switch (variant) {
      case 'chip':
        return (
          <Chip
            icon={showIcon ? iconElement : undefined}
            label={showLabel ? displayLabel : ''}
            size={size}
            sx={{
              backgroundColor: config.bgColor,
              color: config.color,
              border: `1px solid ${alpha(config.color, 0.3)}`,
              fontWeight: 600,
              cursor: onClick ? 'pointer' : 'default',
              ...pulseAnimation,
              '&:hover': onClick
                ? {
                    backgroundColor: alpha(config.color, 0.2),
                    borderColor: alpha(config.color, 0.5),
                  }
                : {},
            }}
            onClick={onClick}
          />
        )

      case 'badge':
        return (
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 0.5,
              px: 1,
              py: 0.5,
              borderRadius: 2,
              backgroundColor: config.bgColor,
              color: config.color,
              border: `1px solid ${alpha(config.color, 0.3)}`,
              fontSize: size === 'small' ? '0.75rem' : size === 'large' ? '0.95rem' : '0.85rem',
              fontWeight: 600,
              cursor: onClick ? 'pointer' : 'default',
              ...pulseAnimation,
              '&:hover': onClick
                ? {
                    backgroundColor: alpha(config.color, 0.2),
                    borderColor: alpha(config.color, 0.5),
                  }
                : {},
            }}
            onClick={onClick}
          >
            {showIcon && iconElement}
            {showLabel && displayLabel}
          </Box>
        )

      case 'dot':
        return (
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 1,
              cursor: onClick ? 'pointer' : 'default',
            }}
            onClick={onClick}
          >
            <Box
              sx={{
                width: size === 'small' ? 6 : size === 'large' ? 12 : 8,
                height: size === 'small' ? 6 : size === 'large' ? 12 : 8,
                borderRadius: '50%',
                backgroundColor: config.color,
                ...pulseAnimation,
              }}
            />
            {showLabel && (
              <Typography
                variant='body2'
                sx={{
                  color: config.color,
                  fontWeight: 600,
                  fontSize: size === 'small' ? '0.75rem' : size === 'large' ? '0.95rem' : '0.85rem',
                }}
              >
                {displayLabel}
              </Typography>
            )}
          </Box>
        )

      case 'icon':
        return (
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: size === 'small' ? 24 : size === 'large' ? 40 : 32,
              height: size === 'small' ? 24 : size === 'large' ? 40 : 32,
              borderRadius: 1,
              backgroundColor: config.bgColor,
              color: config.color,
              cursor: onClick ? 'pointer' : 'default',
              ...pulseAnimation,
              '&:hover': onClick
                ? {
                    backgroundColor: alpha(config.color, 0.2),
                  }
                : {},
            }}
            onClick={onClick}
          >
            {iconElement}
          </Box>
        )

      case 'full':
        return (
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 1,
              px: 2,
              py: 1,
              borderRadius: 2,
              backgroundColor: config.bgColor,
              color: config.color,
              border: `1px solid ${alpha(config.color, 0.3)}`,
              cursor: onClick ? 'pointer' : 'default',
              ...pulseAnimation,
              '&:hover': onClick
                ? {
                    backgroundColor: alpha(config.color, 0.2),
                    borderColor: alpha(config.color, 0.5),
                  }
                : {},
            }}
            onClick={onClick}
          >
            {showIcon && iconElement}
            <Box>
              {showLabel && (
                <Typography
                  variant='body2'
                  sx={{
                    fontWeight: 600,
                    fontSize:
                      size === 'small' ? '0.75rem' : size === 'large' ? '0.95rem' : '0.85rem',
                    lineHeight: 1.2,
                  }}
                >
                  {displayLabel}
                </Typography>
              )}
              {config.description && (
                <Typography
                  variant='caption'
                  sx={{
                    opacity: 0.8,
                    fontSize:
                      size === 'small' ? '0.65rem' : size === 'large' ? '0.75rem' : '0.7rem',
                    lineHeight: 1.1,
                  }}
                >
                  {config.description}
                </Typography>
              )}
            </Box>
          </Box>
        )

      default:
        return null
    }
  }

  const statusElement = renderStatusElement()

  if (displayTooltip && statusElement) {
    return (
      <Tooltip title={displayTooltip} arrow placement='top'>
        <Box component='span'>{statusElement}</Box>
      </Tooltip>
    )
  }

  return statusElement
}
