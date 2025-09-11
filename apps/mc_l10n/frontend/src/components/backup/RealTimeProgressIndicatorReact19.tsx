/**
 * React 19 增强版实时进度指示器
 * 使用 useOptimistic 和 useActionState 优化用户体验
 */

import React, { useOptimistic, useActionState, use, useTransition } from 'react'
import {
  Box,
  Typography,
  LinearProgress,
  Card,
  CardContent,
  Chip,
  Alert,
  IconButton,
} from '@mui/material'
import { useTheme, alpha } from '@mui/material/styles'
import {
  Play,
  Pause,
  CheckCircle,
  AlertCircle,
  Clock,
  Files,
  Package,
  Languages,
  Key,
  TrendingUp,
  Expand,
  Minimize2,
  Zap,
  X,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// 类型定义
interface ScanStatistics {
  total_files: number
  processed_files: number
  total_mods: number
  total_language_files: number
  total_keys: number
  scan_duration_ms?: number
  scan_phase?: 'discovering' | 'processing' | 'finalizing'
  phase_text?: string
  current_batch?: number
  total_batches?: number
  batch_progress?: number
  files_per_second?: number
  estimated_remaining_seconds?: number
  elapsed_seconds?: number
}

interface ProgressUpdate {
  type: 'progress' | 'phase' | 'file' | 'statistics' | 'complete' | 'error'
  payload: any
}

interface ProgressState {
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  currentFile?: string
  statistics: ScanStatistics
  error?: string
}

interface CancelResult {
  success: boolean
  message: string
}

interface React19ProgressProps {
  scanId?: string
  initialProgress?: number
  initialStatistics?: ScanStatistics
  onCancel?: () => void
  animated?: boolean
  compact?: boolean
  showDetails?: boolean
  // React 19 新特性：Promise数据源
  progressStream?: Promise<AsyncIterable<ProgressUpdate>>
}

export const RealTimeProgressIndicatorReact19: React.FC<React19ProgressProps> = ({
  scanId,
  initialProgress = 0,
  initialStatistics = {
    total_files: 0,
    processed_files: 0,
    total_mods: 0,
    total_language_files: 0,
    total_keys: 0,
  },
  onCancel,
  animated = true,
  compact = false,
  showDetails = true,
  progressStream,
}) => {
  const theme = useTheme()

  // React 19 useOptimistic: 乐观更新进度状态
  const initialState: ProgressState = {
    progress: initialProgress,
    status: 'pending',
    statistics: initialStatistics,
  }

  const [optimisticState, addOptimisticUpdate] = useOptimistic(
    initialState,
    (currentState: ProgressState, update: ProgressUpdate): ProgressState => {
      switch (update.type) {
        case 'progress':
          return {
            ...currentState,
            progress: update.payload.progress,
            status: 'running',
          }

        case 'phase':
          return {
            ...currentState,
            statistics: {
              ...currentState.statistics,
              scan_phase: update.payload.phase,
              phase_text: update.payload.text,
            },
          }

        case 'file':
          return {
            ...currentState,
            currentFile: update.payload.filename,
            statistics: {
              ...currentState.statistics,
              processed_files: currentState.statistics.processed_files + 1,
            },
          }

        case 'statistics':
          return {
            ...currentState,
            statistics: { ...currentState.statistics, ...update.payload },
          }

        case 'complete':
          return {
            ...currentState,
            progress: 100,
            status: 'completed',
            statistics: { ...currentState.statistics, ...update.payload },
          }

        case 'error':
          return {
            ...currentState,
            status: 'failed',
            error: update.payload.message,
          }

        default:
          return currentState
      }
    },
  )

  // React 19 useActionState: 取消操作的状态管理
  const cancelScan = async (prevState: CancelResult, formData: FormData): Promise<CancelResult> => {
    try {
      const scanId = formData.get('scanId') as string

      // 立即应用乐观更新
      addOptimisticUpdate({
        type: 'progress',
        payload: { progress: optimisticState.progress, status: 'cancelled' },
      })

      // 实际取消操作
      if (onCancel) {
        onCancel()
      }

      return {
        success: true,
        message: '扫描已取消',
      }
    } catch (error) {
      return {
        success: false,
        message: '取消失败',
      }
    }
  }

  const [cancelState, cancelAction, isCancelling] = useActionState(cancelScan, {
    success: false,
    message: '',
  })

  // React 19 use Hook: 处理进度流
  const [isPending, startTransition] = useTransition()

  // 模拟进度更新（在实际使用中会从WebSocket或SSE获取）
  React.useEffect(() => {
    if (!progressStream) return

    startTransition(async () => {
      try {
        const stream = await progressStream
        for await (const update of stream) {
          addOptimisticUpdate(update)
        }
      } catch (error) {
        addOptimisticUpdate({
          type: 'error',
          payload: { message: '进度流连接失败' },
        })
      }
    })
  }, [progressStream])

  // 获取状态配置
  const getStatusConfig = () => {
    switch (optimisticState.status) {
      case 'completed':
        return {
          color: theme.palette.success.main,
          icon: <CheckCircle size={20} />,
          label: '完成',
          bgColor: alpha(theme.palette.success.main, 0.1),
        }
      case 'failed':
        return {
          color: theme.palette.error.main,
          icon: <AlertCircle size={20} />,
          label: '失败',
          bgColor: alpha(theme.palette.error.main, 0.1),
        }
      case 'cancelled':
        return {
          color: theme.palette.warning.main,
          icon: <X size={20} />,
          label: '已取消',
          bgColor: alpha(theme.palette.warning.main, 0.1),
        }
      case 'running':
        return {
          color: theme.palette.info.main,
          icon: <Play size={20} />,
          label: '运行中',
          bgColor: alpha(theme.palette.info.main, 0.1),
        }
      default:
        return {
          color: theme.palette.grey[500],
          icon: <Clock size={20} />,
          label: '等待中',
          bgColor: alpha(theme.palette.grey[500], 0.1),
        }
    }
  }

  const statusConfig = getStatusConfig()

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
          <motion.div
            animate={{
              rotate: optimisticState.status === 'running' ? 360 : 0,
              scale: isPending ? 1.1 : 1,
            }}
            transition={{
              rotate: {
                duration: 2,
                repeat: optimisticState.status === 'running' ? Infinity : 0,
                ease: 'linear',
              },
              scale: { duration: 0.2 },
            }}
          >
            {statusConfig.icon}
          </motion.div>

          <Box sx={{ flexGrow: 1, minWidth: 100 }}>
            <LinearProgress
              variant='determinate'
              value={optimisticState.progress}
              sx={{
                height: 6,
                borderRadius: 3,
                backgroundColor: alpha(statusConfig.color, 0.2),
                '& .MuiLinearProgress-bar': {
                  backgroundColor: statusConfig.color,
                  borderRadius: 3,
                },
              }}
            />
          </Box>

          <Typography variant='body2' sx={{ fontWeight: 600, minWidth: 45, textAlign: 'right' }}>
            {Math.round(optimisticState.progress)}%
          </Typography>
        </Box>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card
        elevation={2}
        sx={{
          borderRadius: 3,
          background: `linear-gradient(135deg, ${statusConfig.bgColor} 0%, ${alpha(statusConfig.color, 0.05)} 100%)`,
          border: `1px solid ${alpha(statusConfig.color, 0.2)}`,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* 顶部进度条 */}
        <motion.div
          initial={{ width: '0%' }}
          animate={{ width: `${optimisticState.progress}%` }}
          transition={{ duration: animated ? 0.5 : 0, ease: 'easeOut' }}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: 3,
            background: `linear-gradient(90deg, ${statusConfig.color}, ${alpha(statusConfig.color, 0.7)})`,
            borderRadius: '0 3px 3px 0',
          }}
        />

        <CardContent sx={{ pt: 2 }}>
          {/* 状态标题行 */}
          <Box
            sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <motion.div
                animate={{
                  rotate: optimisticState.status === 'running' ? 360 : 0,
                  scale: optimisticState.status === 'running' && isPending ? [1, 1.1, 1] : 1,
                }}
                transition={{
                  rotate: {
                    duration: 2,
                    repeat: optimisticState.status === 'running' ? Infinity : 0,
                    ease: 'linear',
                  },
                  scale: { duration: 2, repeat: isPending ? Infinity : 0 },
                }}
              >
                <Box
                  sx={{
                    p: 1,
                    borderRadius: 2,
                    backgroundColor: alpha(statusConfig.color, 0.1),
                    color: statusConfig.color,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  {statusConfig.icon}
                </Box>
              </motion.div>

              <Box>
                <Typography
                  variant='h6'
                  sx={{
                    fontWeight: 700,
                    color: statusConfig.color,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                  }}
                >
                  {optimisticState.statistics.phase_text || '扫描进度'}{' '}
                  {scanId && (
                    <Chip label={`#${scanId.slice(-8)}`} size='small' variant='outlined' />
                  )}
                  {isPending && <Chip label='实时更新' size='small' color='info' />}
                </Typography>
                <Typography variant='caption' color='text.secondary'>
                  React 19 增强版 - 乐观更新 + 实时流
                </Typography>
              </Box>
            </Box>

            <Box sx={{ textAlign: 'right' }}>
              <Typography variant='h5' sx={{ fontWeight: 700, color: statusConfig.color }}>
                {optimisticState.statistics.processed_files.toLocaleString()} /{' '}
                {optimisticState.statistics.total_files.toLocaleString()}
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                文件 ({Math.round(optimisticState.progress)}%)
              </Typography>
            </Box>
          </Box>

          {/* 主进度条 */}
          <Box sx={{ mb: 3 }}>
            <LinearProgress
              variant='determinate'
              value={optimisticState.progress}
              sx={{
                height: 12,
                borderRadius: 6,
                backgroundColor: alpha(statusConfig.color, 0.1),
                '& .MuiLinearProgress-bar': {
                  backgroundColor: statusConfig.color,
                  borderRadius: 6,
                  background: `linear-gradient(90deg, ${statusConfig.color}, ${alpha(statusConfig.color, 0.8)})`,
                },
              }}
            />
          </Box>

          {/* 当前文件显示 */}
          <AnimatePresence>
            {optimisticState.currentFile && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Box
                  sx={{
                    mb: 2,
                    p: 2,
                    backgroundColor: alpha(theme.palette.info.main, 0.05),
                    borderRadius: 2,
                    border: `1px dashed ${alpha(theme.palette.info.main, 0.2)}`,
                  }}
                >
                  <Typography variant='caption' color='text.secondary'>
                    当前处理: {optimisticState.currentFile}
                  </Typography>
                </Box>
              </motion.div>
            )}
          </AnimatePresence>

          {/* 错误信息 */}
          <AnimatePresence>
            {optimisticState.error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Alert severity='error' sx={{ mb: 2 }}>
                  <strong>错误:</strong> {optimisticState.error}
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>

          {/* 取消按钮 - 使用React 19 useActionState */}
          {optimisticState.status === 'running' && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
              <form action={cancelAction}>
                <input type='hidden' name='scanId' value={scanId} />
                <motion.button
                  type='submit'
                  disabled={isCancelling}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  style={{
                    background: 'none',
                    border: `2px solid ${theme.palette.error.main}`,
                    borderRadius: 8,
                    padding: '8px 16px',
                    color: theme.palette.error.main,
                    cursor: isCancelling ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '0.875rem',
                    opacity: isCancelling ? 0.6 : 1,
                  }}
                >
                  {isCancelling ? '取消中...' : '取消扫描'}
                </motion.button>
              </form>
            </Box>
          )}

          {/* 取消操作反馈 */}
          <AnimatePresence>
            {cancelState.message && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
              >
                <Alert severity={cancelState.success ? 'success' : 'error'} sx={{ mt: 2 }}>
                  {cancelState.message}
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default RealTimeProgressIndicatorReact19
