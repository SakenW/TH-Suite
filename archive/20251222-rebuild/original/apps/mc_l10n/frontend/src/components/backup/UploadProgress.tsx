/**
 * 上传进度组件
 * 显示文件上传进度和状态
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Collapse,
  Paper,
  Grid,
  Button,
  Alert,
} from '@mui/material'
import {
  Cloud,
  UploadCloud,
  CloudOff,
  CheckCircle,
  XCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Pause,
  Play,
  X,
  AlertCircle,
  Zap,
  Clock,
  HardDrive,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { MinecraftCard } from './minecraft/MinecraftCard'
import { MinecraftButton } from './minecraft/MinecraftButton'
import { MinecraftProgress } from './minecraft/MinecraftProgress'
import { minecraftColors } from '../theme/minecraftTheme'
import type { UploadProgress as UploadProgressType } from '../services/transhubService'

interface UploadProgressProps {
  progress: UploadProgressType | null
  onCancel?: () => void
  onRetry?: () => void
  onPause?: () => void
  onResume?: () => void
  showDetails?: boolean
  compact?: boolean
}

export const UploadProgress: React.FC<UploadProgressProps> = ({
  progress,
  onCancel,
  onRetry,
  onPause,
  onResume,
  showDetails = true,
  compact = false,
}) => {
  const [expanded, setExpanded] = useState(!compact)
  const [isPaused, setIsPaused] = useState(false)

  if (!progress) {
    return null
  }

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatTime = (seconds: number): string => {
    if (!seconds || seconds <= 0) return '--:--'
    if (seconds < 60) return `${Math.floor(seconds)}秒`
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}分${secs}秒`
  }

  const formatSpeed = (bytesPerSecond: number): string => {
    if (!bytesPerSecond || bytesPerSecond <= 0) return '-- /秒'
    return `${formatBytes(bytesPerSecond)}/秒`
  }

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'preparing':
        return <RefreshCw size={16} className='animate-spin' />
      case 'uploading':
        return <UploadCloud size={16} />
      case 'completed':
        return <CheckCircle size={16} />
      case 'failed':
        return <XCircle size={16} />
      case 'retrying':
        return <RefreshCw size={16} className='animate-spin' />
      default:
        return <Cloud size={16} />
    }
  }

  const getStatusColor = () => {
    switch (progress.status) {
      case 'completed':
        return minecraftColors.emerald
      case 'failed':
        return minecraftColors.redstoneRed
      case 'retrying':
        return minecraftColors.goldYellow
      case 'uploading':
        return minecraftColors.diamondBlue
      default:
        return minecraftColors.iron
    }
  }

  const getStatusText = () => {
    switch (progress.status) {
      case 'preparing':
        return '准备上传'
      case 'uploading':
        return `上传中 (${progress.currentChunk}/${progress.totalChunks})`
      case 'completed':
        return '上传完成'
      case 'failed':
        return '上传失败'
      case 'retrying':
        return '重试中'
      default:
        return '未知状态'
    }
  }

  if (compact && !expanded) {
    // 紧凑模式
    return (
      <Paper
        sx={{
          p: 1.5,
          bgcolor: 'rgba(15, 23, 42, 0.9)',
          border: '2px solid #2A2A4E',
          borderRadius: 0,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ color: getStatusColor() }}>{getStatusIcon()}</Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant='caption' sx={{ fontFamily: '"Minecraft", monospace' }}>
              {getStatusText()}
            </Typography>
            <LinearProgress
              variant='determinate'
              value={progress.percentage}
              sx={{
                height: 4,
                mt: 0.5,
                bgcolor: 'rgba(255,255,255,0.1)',
                '& .MuiLinearProgress-bar': {
                  bgcolor: getStatusColor(),
                },
              }}
            />
          </Box>
          <Typography variant='caption' sx={{ fontFamily: '"Minecraft", monospace' }}>
            {progress.percentage.toFixed(0)}%
          </Typography>
          <IconButton size='small' onClick={() => setExpanded(!expanded)}>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </IconButton>
        </Box>
      </Paper>
    )
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
      >
        <MinecraftCard
          variant={progress.status === 'failed' ? 'redstone' : 'enchantment'}
          title='上传进度'
          icon={progress.status === 'completed' ? 'emerald' : 'diamond'}
        >
          <Box sx={{ p: 2 }}>
            {/* 状态栏 */}
            <Box
              sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ color: getStatusColor() }}>{getStatusIcon()}</Box>
                <Typography
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    color: getStatusColor(),
                  }}
                >
                  {getStatusText()}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {progress.status === 'uploading' && onPause && (
                  <IconButton
                    size='small'
                    onClick={() => {
                      if (isPaused && onResume) {
                        onResume()
                        setIsPaused(false)
                      } else if (onPause) {
                        onPause()
                        setIsPaused(true)
                      }
                    }}
                  >
                    {isPaused ? <Play size={16} /> : <Pause size={16} />}
                  </IconButton>
                )}
                {progress.status === 'failed' && onRetry && (
                  <IconButton size='small' onClick={onRetry}>
                    <RefreshCw size={16} />
                  </IconButton>
                )}
                {onCancel && progress.status !== 'completed' && (
                  <IconButton size='small' onClick={onCancel}>
                    <X size={16} />
                  </IconButton>
                )}
              </Box>
            </Box>

            {/* 主进度条 */}
            <MinecraftProgress
              value={progress.percentage}
              max={100}
              variant='experience'
              label={`${progress.percentage.toFixed(1)}%`}
              animated
              size='large'
            />

            {/* 错误信息 */}
            {progress.error && (
              <Alert
                severity='error'
                sx={{
                  mt: 2,
                  bgcolor: 'rgba(244, 67, 54, 0.1)',
                  border: '1px solid #F44336',
                }}
              >
                {progress.error}
              </Alert>
            )}

            {/* 详细信息 */}
            {showDetails && (
              <Collapse in={expanded}>
                <Grid container spacing={2} sx={{ mt: 2 }}>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <HardDrive size={20} style={{ color: minecraftColors.iron }} />
                      <Typography variant='caption' color='text.secondary'>
                        已上传
                      </Typography>
                      <Typography variant='body2' sx={{ fontFamily: '"Minecraft", monospace' }}>
                        {formatBytes(progress.bytesUploaded)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Zap size={20} style={{ color: minecraftColors.goldYellow }} />
                      <Typography variant='caption' color='text.secondary'>
                        速度
                      </Typography>
                      <Typography variant='body2' sx={{ fontFamily: '"Minecraft", monospace' }}>
                        {formatSpeed(progress.speed)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Clock size={20} style={{ color: minecraftColors.diamondBlue }} />
                      <Typography variant='caption' color='text.secondary'>
                        剩余时间
                      </Typography>
                      <Typography variant='body2' sx={{ fontFamily: '"Minecraft", monospace' }}>
                        {formatTime(progress.remainingTime)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Cloud size={20} style={{ color: minecraftColors.emerald }} />
                      <Typography variant='caption' color='text.secondary'>
                        分片进度
                      </Typography>
                      <Typography variant='body2' sx={{ fontFamily: '"Minecraft", monospace' }}>
                        {progress.completedChunks}/{progress.totalChunks}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Collapse>
            )}

            {/* 操作按钮 */}
            {progress.status === 'completed' && (
              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <MinecraftButton
                  minecraftStyle='emerald'
                  startIcon={<CheckCircle size={16} />}
                  onClick={onCancel}
                >
                  完成
                </MinecraftButton>
              </Box>
            )}

            {progress.status === 'failed' && (
              <Box sx={{ mt: 2, display: 'flex', gap: 2, justifyContent: 'center' }}>
                <MinecraftButton
                  minecraftStyle='gold'
                  startIcon={<RefreshCw size={16} />}
                  onClick={onRetry}
                >
                  重试
                </MinecraftButton>
                <MinecraftButton minecraftStyle='stone' onClick={onCancel}>
                  取消
                </MinecraftButton>
              </Box>
            )}
          </Box>
        </MinecraftCard>
      </motion.div>
    </AnimatePresence>
  )
}

export default UploadProgress
