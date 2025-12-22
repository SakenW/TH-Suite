/**
 * 空状态组件
 * 用于展示无数据、无搜索结果等空状态场景
 */

import React from 'react'
import { Box, Typography, Button, Stack, Paper, alpha } from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  Search,
  FolderOpen,
  Plus,
  RefreshCw,
  FileText,
  Archive,
  Inbox,
  AlertCircle,
  Wifi,
  Database,
  Filter,
  Globe,
} from 'lucide-react'
import { motion } from 'framer-motion'

export type EmptyStateType =
  | 'no-data'
  | 'no-results'
  | 'no-projects'
  | 'no-translations'
  | 'no-files'
  | 'error'
  | 'offline'
  | 'loading-failed'
  | 'permission-denied'
  | 'filtered-empty'
  | 'archived'
  | 'maintenance'

interface EmptyStateConfig {
  icon: React.ReactNode
  title: string
  description: string
  primaryAction?: {
    label: string
    action: () => void
  }
  secondaryAction?: {
    label: string
    action: () => void
  }
}

interface EmptyStateProps {
  type: EmptyStateType
  title?: string
  description?: string
  icon?: React.ReactNode
  actions?: Array<{
    label: string
    onClick: () => void
    variant?: 'contained' | 'outlined' | 'text'
    color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
    startIcon?: React.ReactNode
  }>
  illustration?: React.ReactNode
  size?: 'small' | 'medium' | 'large'
  animate?: boolean
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  type,
  title: customTitle,
  description: customDescription,
  icon: customIcon,
  actions = [],
  illustration,
  size = 'medium',
  animate = true,
}) => {
  const theme = useTheme()

  const getEmptyStateConfig = (type: EmptyStateType): EmptyStateConfig => {
    const configs: Record<EmptyStateType, EmptyStateConfig> = {
      'no-data': {
        icon: <Inbox size={48} />,
        title: '暂无数据',
        description: '这里还没有任何内容，开始添加一些数据吧。',
        primaryAction: {
          label: '开始使用',
          action: () => {},
        },
      },
      'no-results': {
        icon: <Search size={48} />,
        title: '未找到搜索结果',
        description: '尝试调整搜索条件或使用不同的关键词。',
        primaryAction: {
          label: '清除搜索',
          action: () => {},
        },
        secondaryAction: {
          label: '重新搜索',
          action: () => {},
        },
      },
      'no-projects': {
        icon: <FolderOpen size={48} />,
        title: '还没有项目',
        description: '创建您的第一个本地化项目，开始管理翻译工作。',
        primaryAction: {
          label: '创建项目',
          action: () => {},
        },
      },
      'no-translations': {
        icon: <Globe size={48} />,
        title: '暂无翻译内容',
        description: '导入语言文件或开始手动添加翻译条目。',
        primaryAction: {
          label: '导入文件',
          action: () => {},
        },
        secondaryAction: {
          label: '手动添加',
          action: () => {},
        },
      },
      'no-files': {
        icon: <FileText size={48} />,
        title: '没有找到文件',
        description: '该目录中没有找到任何支持的文件格式。',
        primaryAction: {
          label: '刷新',
          action: () => {},
        },
      },
      error: {
        icon: <AlertCircle size={48} />,
        title: '出现错误',
        description: '加载数据时发生错误，请稍后重试。',
        primaryAction: {
          label: '重试',
          action: () => {},
        },
      },
      offline: {
        icon: <Wifi size={48} />,
        title: '网络连接断开',
        description: '请检查您的网络连接并重试。',
        primaryAction: {
          label: '重新连接',
          action: () => {},
        },
      },
      'loading-failed': {
        icon: <Database size={48} />,
        title: '加载失败',
        description: '无法加载数据，请检查网络连接或稍后重试。',
        primaryAction: {
          label: '重新加载',
          action: () => {},
        },
      },
      'permission-denied': {
        icon: <AlertCircle size={48} />,
        title: '访问被拒绝',
        description: '您没有权限访问此内容。',
        secondaryAction: {
          label: '联系管理员',
          action: () => {},
        },
      },
      'filtered-empty': {
        icon: <Filter size={48} />,
        title: '筛选结果为空',
        description: '当前筛选条件下没有找到匹配的内容。',
        primaryAction: {
          label: '清除筛选',
          action: () => {},
        },
      },
      archived: {
        icon: <Archive size={48} />,
        title: '内容已归档',
        description: '这些内容已被归档，您可以在归档区域查看。',
        primaryAction: {
          label: '查看归档',
          action: () => {},
        },
      },
      maintenance: {
        icon: <AlertCircle size={48} />,
        title: '维护中',
        description: '系统正在维护中，请稍后再试。',
        primaryAction: {
          label: '刷新页面',
          action: () => {},
        },
      },
    }

    return configs[type]
  }

  const config = getEmptyStateConfig(type)
  const finalTitle = customTitle || config.title
  const finalDescription = customDescription || config.description
  const finalIcon = customIcon || config.icon

  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return {
          iconSize: 32,
          titleVariant: 'h6' as const,
          spacing: 2,
          maxWidth: 300,
        }
      case 'large':
        return {
          iconSize: 64,
          titleVariant: 'h4' as const,
          spacing: 4,
          maxWidth: 500,
        }
      case 'medium':
      default:
        return {
          iconSize: 48,
          titleVariant: 'h5' as const,
          spacing: 3,
          maxWidth: 400,
        }
    }
  }

  const sizeStyles = getSizeStyles()

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4 },
    },
  }

  const iconElement = React.cloneElement(finalIcon as React.ReactElement, {
    size: sizeStyles.iconSize,
    color: alpha(theme.palette.text.secondary, 0.6),
  })

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        py: sizeStyles.spacing * 2,
        px: 3,
        minHeight: size === 'large' ? 400 : size === 'medium' ? 300 : 200,
      }}
    >
      <motion.div
        variants={containerVariants}
        initial={animate ? 'hidden' : 'visible'}
        animate='visible'
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          maxWidth: sizeStyles.maxWidth,
          width: '100%',
        }}
      >
        {/* 插图或图标 */}
        <motion.div variants={itemVariants}>
          {illustration ? (
            <Box sx={{ mb: sizeStyles.spacing }}>{illustration}</Box>
          ) : (
            <Box
              sx={{
                mb: sizeStyles.spacing,
                p: 2,
                borderRadius: 3,
                backgroundColor: alpha(theme.palette.primary.main, 0.05),
                border: `1px dashed ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              {iconElement}
            </Box>
          )}
        </motion.div>

        {/* 标题 */}
        <motion.div variants={itemVariants}>
          <Typography
            variant={sizeStyles.titleVariant}
            sx={{
              fontWeight: 600,
              color: theme.palette.text.primary,
              mb: 1,
            }}
          >
            {finalTitle}
          </Typography>
        </motion.div>

        {/* 描述 */}
        <motion.div variants={itemVariants}>
          <Typography
            variant='body1'
            color='text.secondary'
            sx={{
              mb: sizeStyles.spacing,
              lineHeight: 1.6,
              maxWidth: '100%',
            }}
          >
            {finalDescription}
          </Typography>
        </motion.div>

        {/* 操作按钮 */}
        {actions.length > 0 && (
          <motion.div variants={itemVariants}>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              alignItems='center'
              sx={{ width: '100%' }}
            >
              {actions.map((action, index) => (
                <Button
                  key={index}
                  variant={action.variant || 'contained'}
                  color={action.color || 'primary'}
                  onClick={action.onClick}
                  startIcon={action.startIcon}
                  sx={{
                    minWidth: { xs: '100%', sm: 120 },
                    borderRadius: 2,
                    textTransform: 'none',
                    fontWeight: 600,
                  }}
                >
                  {action.label}
                </Button>
              ))}
            </Stack>
          </motion.div>
        )}

        {/* 默认操作按钮 */}
        {actions.length === 0 && (config.primaryAction || config.secondaryAction) && (
          <motion.div variants={itemVariants}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems='center'>
              {config.primaryAction && (
                <Button
                  variant='contained'
                  onClick={config.primaryAction.action}
                  sx={{
                    minWidth: { xs: '100%', sm: 120 },
                    borderRadius: 2,
                    textTransform: 'none',
                    fontWeight: 600,
                  }}
                >
                  {config.primaryAction.label}
                </Button>
              )}
              {config.secondaryAction && (
                <Button
                  variant='outlined'
                  onClick={config.secondaryAction.action}
                  sx={{
                    minWidth: { xs: '100%', sm: 120 },
                    borderRadius: 2,
                    textTransform: 'none',
                  }}
                >
                  {config.secondaryAction.label}
                </Button>
              )}
            </Stack>
          </motion.div>
        )}
      </motion.div>
    </Box>
  )
}
