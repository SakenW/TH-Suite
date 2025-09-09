/**
 * React 19 增强版扫描页面
 * 使用 useActionState 优化表单状态管理
 * 使用 useOptimistic 提供即时反馈
 */

import React, { useActionState, useOptimistic, useTransition, use } from 'react'
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Card,
  CardContent,
} from '@mui/material'
import {
  FolderOpen,
  Play,
  CheckCircle,
  AlertCircle,
  FileText,
  Package,
  Languages,
  Clock,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { RealTimeProgressIndicatorReact19 } from './common/RealTimeProgressIndicatorReact19'

// 类型定义
interface ScanResult {
  id: string
  projectPath: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  filesFound: number
  modsFound: number
  languageFiles: number
  translationKeys: number
  startTime: Date
  duration?: number
  error?: string
}

interface ScanFormState {
  success: boolean
  message: string
  scanId?: string
  error?: string
}

interface OptimisticScanUpdate {
  type: 'start' | 'progress' | 'complete' | 'error'
  scanId: string
  payload: any
}

interface ScanPageProps {
  onScanComplete?: (result: ScanResult) => void
}

export const ScanPageReact19Enhanced: React.FC<ScanPageProps> = ({ onScanComplete }) => {
  // 初始扫描结果状态
  const initialScans: ScanResult[] = []

  // React 19 useOptimistic: 乐观更新扫描列表
  const [optimisticScans, addOptimisticScan] = useOptimistic(
    initialScans,
    (currentScans: ScanResult[], update: OptimisticScanUpdate): ScanResult[] => {
      switch (update.type) {
        case 'start':
          return [
            ...currentScans,
            {
              id: update.scanId,
              projectPath: update.payload.projectPath,
              status: 'running',
              progress: 0,
              filesFound: 0,
              modsFound: 0,
              languageFiles: 0,
              translationKeys: 0,
              startTime: new Date(),
            },
          ]

        case 'progress':
          return currentScans.map(scan =>
            scan.id === update.scanId ? { ...scan, ...update.payload } : scan,
          )

        case 'complete':
          return currentScans.map(scan =>
            scan.id === update.scanId
              ? {
                  ...scan,
                  status: 'completed',
                  progress: 100,
                  duration: Date.now() - scan.startTime.getTime(),
                  ...update.payload,
                }
              : scan,
          )

        case 'error':
          return currentScans.map(scan =>
            scan.id === update.scanId
              ? {
                  ...scan,
                  status: 'failed',
                  error: update.payload.message,
                }
              : scan,
          )

        default:
          return currentScans
      }
    },
  )

  // React 19 useActionState: 扫描表单状态管理
  const startScan = async (
    prevState: ScanFormState,
    formData: FormData,
  ): Promise<ScanFormState> => {
    try {
      const projectPath = formData.get('projectPath') as string

      if (!projectPath) {
        return {
          success: false,
          message: '请选择项目路径',
          error: 'PROJECT_PATH_REQUIRED',
        }
      }

      // 生成扫描ID
      const scanId = `scan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

      // 立即应用乐观更新 - 开始扫描
      addOptimisticScan({
        type: 'start',
        scanId,
        payload: { projectPath },
      })

      // 模拟异步扫描过程
      setTimeout(() => {
        // 模拟进度更新
        const progressInterval = setInterval(() => {
          const currentScan = optimisticScans.find(s => s.id === scanId)
          if (currentScan && currentScan.progress < 100) {
            addOptimisticScan({
              type: 'progress',
              scanId,
              payload: {
                progress: Math.min(currentScan.progress + Math.random() * 15, 95),
                filesFound: Math.floor(Math.random() * 100),
                modsFound: Math.floor(Math.random() * 20),
              },
            })
          } else {
            clearInterval(progressInterval)
            // 完成扫描
            addOptimisticScan({
              type: 'complete',
              scanId,
              payload: {
                filesFound: 156,
                modsFound: 23,
                languageFiles: 45,
                translationKeys: 2847,
              },
            })

            if (onScanComplete) {
              const finalResult = optimisticScans.find(s => s.id === scanId)
              if (finalResult) {
                onScanComplete(finalResult)
              }
            }
          }
        }, 500)
      }, 100)

      return {
        success: true,
        message: '扫描已开始',
        scanId,
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : '扫描启动失败',
        error: 'SCAN_START_FAILED',
      }
    }
  }

  const [scanFormState, scanAction, isScanPending] = useActionState(startScan, {
    success: false,
    message: '',
  })

  // React 19 useTransition: 处理非紧急更新
  const [isPending, startTransition] = useTransition()

  // 选择项目文件夹
  const handleSelectFolder = async () => {
    startTransition(async () => {
      try {
        // 在实际应用中会调用Tauri的文件对话框
        console.log('打开文件夹选择对话框...')
      } catch (error) {
        console.error('文件夹选择失败:', error)
      }
    })
  }

  // 获取最新的扫描任务
  const activeScan = optimisticScans.find(scan => scan.status === 'running')
  const completedScans = optimisticScans.filter(scan => scan.status === 'completed')

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant='h4' gutterBottom sx={{ mb: 4 }}>
        🚀 项目扫描 (React 19 增强版)
      </Typography>

      {/* 扫描表单 */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant='h6' gutterBottom>
          新建扫描任务
        </Typography>

        <form action={scanAction}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end', mb: 2 }}>
            <TextField
              name='projectPath'
              label='项目路径'
              placeholder='/path/to/minecraft/mods'
              fullWidth
              disabled={isScanPending || isPending}
              InputProps={{
                endAdornment: (
                  <Button
                    variant='outlined'
                    startIcon={<FolderOpen />}
                    onClick={handleSelectFolder}
                    disabled={isPending}
                    sx={{ ml: 1 }}
                  >
                    浏览
                  </Button>
                ),
              }}
            />

            <Button
              type='submit'
              variant='contained'
              size='large'
              startIcon={<Play />}
              disabled={isScanPending || isPending}
              sx={{ minWidth: 120 }}
            >
              {isScanPending ? '启动中...' : '开始扫描'}
            </Button>
          </Box>
        </form>

        {/* 表单状态反馈 */}
        <AnimatePresence>
          {scanFormState.message && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <Alert severity={scanFormState.success ? 'success' : 'error'} sx={{ mt: 2 }}>
                {scanFormState.message}
                {scanFormState.scanId && (
                  <Chip
                    label={`ID: ${scanFormState.scanId.slice(-8)}`}
                    size='small'
                    sx={{ ml: 1 }}
                  />
                )}
              </Alert>
            </motion.div>
          )}
        </AnimatePresence>
      </Paper>

      {/* 当前扫描进度 */}
      <AnimatePresence>
        {activeScan && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.4 }}
          >
            <Box sx={{ mb: 3 }}>
              <RealTimeProgressIndicatorReact19
                scanId={activeScan.id}
                initialProgress={activeScan.progress}
                initialStatistics={{
                  total_files: activeScan.filesFound + 50, // 模拟总文件数
                  processed_files: activeScan.filesFound,
                  total_mods: activeScan.modsFound,
                  total_language_files: activeScan.languageFiles,
                  total_keys: activeScan.translationKeys,
                  scan_phase: 'processing',
                  phase_text: '正在扫描项目文件',
                }}
                onCancel={() => {
                  addOptimisticScan({
                    type: 'error',
                    scanId: activeScan.id,
                    payload: { message: '扫描已被用户取消' },
                  })
                }}
                animated
                showDetails
              />
            </Box>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 扫描历史 */}
      {completedScans.length > 0 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant='h6' gutterBottom>
            扫描历史
          </Typography>

          <List>
            <AnimatePresence>
              {completedScans.map(scan => (
                <motion.div
                  key={scan.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3 }}
                >
                  <ListItem
                    sx={{
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 2,
                      mb: 1,
                      backgroundColor:
                        scan.status === 'completed' ? 'success.light' : 'error.light',
                      '&:hover': { backgroundColor: 'action.hover' },
                    }}
                  >
                    <ListItemIcon>
                      {scan.status === 'completed' ? (
                        <CheckCircle color='success' />
                      ) : (
                        <AlertCircle color='error' />
                      )}
                    </ListItemIcon>

                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant='subtitle1'>{scan.projectPath}</Typography>
                          <Chip label={scan.id.slice(-8)} size='small' variant='outlined' />
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 1 }}>
                          <Typography variant='body2' color='text.secondary'>
                            开始时间: {scan.startTime.toLocaleString()}
                          </Typography>
                          {scan.duration && (
                            <Typography variant='body2' color='text.secondary'>
                              耗时: {Math.round(scan.duration / 1000)}秒
                            </Typography>
                          )}
                          <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                            <Chip
                              icon={<FileText />}
                              label={`${scan.filesFound} 文件`}
                              size='small'
                            />
                            <Chip
                              icon={<Package />}
                              label={`${scan.modsFound} 模组`}
                              size='small'
                            />
                            <Chip
                              icon={<Languages />}
                              label={`${scan.languageFiles} 语言文件`}
                              size='small'
                            />
                          </Box>
                        </Box>
                      }
                    />
                  </ListItem>
                </motion.div>
              ))}
            </AnimatePresence>
          </List>
        </Paper>
      )}

      {/* React 19 特性说明 */}
      <Card sx={{ mt: 3, backgroundColor: 'info.light' }}>
        <CardContent>
          <Typography variant='h6' gutterBottom>
            🎉 React 19 新特性展示
          </Typography>
          <List dense>
            <ListItem>
              <ListItemText
                primary='useActionState'
                secondary='管理扫描表单的提交状态，提供内置的pending状态'
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary='useOptimistic'
                secondary='立即更新UI显示扫描进度，无需等待服务器响应'
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary='useTransition'
                secondary='将文件夹选择等操作标记为非紧急更新，保持UI响应性'
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary='Concurrent Features'
                secondary='改进的并发渲染，更好的用户体验和性能'
              />
            </ListItem>
          </List>
        </CardContent>
      </Card>
    </Box>
  )
}

export default ScanPageReact19Enhanced
