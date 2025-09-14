import React, { useState, useCallback, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  List as ListIcon,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  LinearProgress,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  CircularProgress,
  useTheme,
  alpha,
  Tabs,
  Tab,
  Divider,
} from '@mui/material'
import {
  Upload,
  Download,
  Pause,
  Play,
  Square,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  FileText,
  Globe,
  Server,
  List,
  Settings,
  Info,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppStore } from '@stores/appStore'
import { apiService } from '@services/apiService'
import { useMcStudioTranslation } from '@hooks/useTranslation'

interface TransferItem {
  id: string
  type: 'upload' | 'download'
  name: string
  language: string
  size: number
  progress: number
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
  speed?: number
  eta?: number
  error?: string
  createdAt: Date
  completedAt?: Date
}

interface QueueStats {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
}

function TransferPage() {
  const theme = useTheme()
  const { t } = useMcStudioTranslation()
  const { currentProject } = useAppStore()

  const [activeTab, setActiveTab] = useState(0)
  const [transferItems, setTransferItems] = useState<TransferItem[]>([])
  const [queueStats, setQueueStats] = useState<QueueStats>({
    total: 0,
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
  })
  const [isQueueRunning, setIsQueueRunning] = useState(false)
  const [maxConcurrent, setMaxConcurrent] = useState(3)
  const [showSettings, setShowSettings] = useState(false)
  const [selectedItems, setSelectedItems] = useState<string[]>([])

  // Load real transfer data from backend
  useEffect(() => {
    // TODO: Fetch real transfer history from backend API
    // For now, initialize with empty array
    setTransferItems([])
  }, [])

  // Calculate stats when transfer items change
  useEffect(() => {
    const stats = transferItems.reduce(
      (acc, item) => {
        acc.total++
        acc[item.status]++
        return acc
      },
      {
        total: 0,
        pending: 0,
        running: 0,
        completed: 0,
        failed: 0,
      } as QueueStats,
    )

    setQueueStats(stats)
    setIsQueueRunning(stats.running > 0)
  }, [transferItems])

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatSpeed = (bytesPerSecond: number): string => {
    return formatFileSize(bytesPerSecond) + '/s'
  }

  const formatETA = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  const getStatusColor = (status: TransferItem['status']) => {
    switch (status) {
      case 'completed':
        return theme.palette.success.main
      case 'running':
        return theme.palette.primary.main
      case 'failed':
        return theme.palette.error.main
      case 'paused':
        return theme.palette.warning.main
      case 'cancelled':
        return theme.palette.text.disabled
      default:
        return theme.palette.text.secondary
    }
  }

  const getStatusIcon = (status: TransferItem['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} />
      case 'running':
        return <CircularProgress size={16} />
      case 'failed':
        return <AlertCircle size={16} />
      case 'paused':
        return <Pause size={16} />
      case 'cancelled':
        return <Square size={16} />
      default:
        return <Clock size={16} />
    }
  }

  const handleStartQueue = () => {
    setIsQueueRunning(true)
    toast.success(t('transfer.queue.started'))
  }

  const handlePauseQueue = () => {
    setIsQueueRunning(false)
    toast.success(t('transfer.queue.paused'))
  }

  const handleClearCompleted = () => {
    setTransferItems(prev => prev.filter(item => item.status !== 'completed'))
    toast.success(t('transfer.queue.clearedCompleted'))
  }

  const handleRetryFailed = () => {
    setTransferItems(prev =>
      prev.map(item =>
        item.status === 'failed' ? { ...item, status: 'pending', error: undefined } : item,
      ),
    )
    toast.success(t('transfer.queue.retriedFailed'))
  }

  const handleItemAction = (id: string, action: 'pause' | 'resume' | 'cancel' | 'retry') => {
    setTransferItems(prev =>
      prev.map(item => {
        if (item.id === id) {
          switch (action) {
            case 'pause':
              return { ...item, status: 'paused' }
            case 'resume':
              return { ...item, status: 'running' }
            case 'cancel':
              return { ...item, status: 'cancelled' }
            case 'retry':
              return { ...item, status: 'pending', error: undefined }
            default:
              return item
          }
        }
        return item
      }),
    )
  }

  const handleBatchAction = (action: 'pause' | 'resume' | 'cancel') => {
    if (selectedItems.length === 0) {
      toast.error(t('transfer.batch.noSelection'))
      return
    }

    setTransferItems(prev =>
      prev.map(item => {
        if (selectedItems.includes(item.id)) {
          switch (action) {
            case 'pause':
              return item.status === 'running' ? { ...item, status: 'paused' } : item
            case 'resume':
              return item.status === 'paused' ? { ...item, status: 'running' } : item
            case 'cancel':
              return ['running', 'paused', 'pending'].includes(item.status)
                ? { ...item, status: 'cancelled' }
                : item
            default:
              return item
          }
        }
        return item
      }),
    )

    setSelectedItems([])
    toast.success(t('transfer.batch.actionCompleted'))
  }

  const filteredItems = transferItems.filter(item => {
    if (activeTab === 0) return true // All
    if (activeTab === 1) return item.type === 'upload'
    if (activeTab === 2) return item.type === 'download'
    if (activeTab === 3) return item.status === 'running'
    if (activeTab === 4) return item.status === 'completed'
    return true
  })

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant='h4' gutterBottom>
        {t('transfer.title')}
      </Typography>

      {/* Queue Statistics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                {t('transfer.queue.title')}
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Box textAlign='center'>
                    <Typography variant='h4' color='primary'>
                      {queueStats.total}
                    </Typography>
                    <Typography variant='body2' color='text.secondary'>
                      {t('transfer.stats.total')}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign='center'>
                    <Typography variant='h4' color='warning.main'>
                      {queueStats.pending}
                    </Typography>
                    <Typography variant='body2' color='text.secondary'>
                      {t('transfer.stats.pending')}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign='center'>
                    <Typography variant='h4' color='info.main'>
                      {queueStats.running}
                    </Typography>
                    <Typography variant='body2' color='text.secondary'>
                      {t('transfer.stats.running')}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign='center'>
                    <Typography variant='h4' color='success.main'>
                      {queueStats.completed}
                    </Typography>
                    <Typography variant='body2' color='text.secondary'>
                      {t('transfer.stats.completed')}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                {t('transfer.queue.controls')}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {isQueueRunning ? (
                  <Button
                    variant='contained'
                    color='warning'
                    startIcon={<Pause size={16} />}
                    onClick={handlePauseQueue}
                    size='small'
                  >
                    {t('transfer.queue.pause')}
                  </Button>
                ) : (
                  <Button
                    variant='contained'
                    color='primary'
                    startIcon={<Play size={16} />}
                    onClick={handleStartQueue}
                    size='small'
                  >
                    {t('transfer.queue.start')}
                  </Button>
                )}

                <Button
                  variant='outlined'
                  startIcon={<Trash2 size={16} />}
                  onClick={handleClearCompleted}
                  size='small'
                >
                  {t('transfer.queue.clearCompleted')}
                </Button>

                <Button
                  variant='outlined'
                  startIcon={<RefreshCw size={16} />}
                  onClick={handleRetryFailed}
                  size='small'
                >
                  {t('transfer.queue.retryFailed')}
                </Button>

                <IconButton onClick={() => setShowSettings(true)} size='small'>
                  <Settings size={16} />
                </IconButton>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Transfer List */}
      <Card>
        <CardContent>
          {/* Tabs */}
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
            <Tab label={`${t('transfer.tabs.all')} (${transferItems.length})`} />
            <Tab
              label={`${t('transfer.tabs.uploads')} (${transferItems.filter(i => i.type === 'upload').length})`}
            />
            <Tab
              label={`${t('transfer.tabs.downloads')} (${transferItems.filter(i => i.type === 'download').length})`}
            />
            <Tab label={`${t('transfer.tabs.active')} (${queueStats.running})`} />
            <Tab label={`${t('transfer.tabs.completed')} (${queueStats.completed})`} />
          </Tabs>

          {/* Batch Actions */}
          {selectedItems.length > 0 && (
            <Box
              sx={{ mb: 2, p: 2, bgcolor: alpha(theme.palette.primary.main, 0.1), borderRadius: 1 }}
            >
              <Typography variant='body2' sx={{ mb: 1 }}>
                {t('transfer.batch.selected', { count: selectedItems.length })}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  size='small'
                  startIcon={<Pause size={14} />}
                  onClick={() => handleBatchAction('pause')}
                >
                  {t('transfer.batch.pause')}
                </Button>
                <Button
                  size='small'
                  startIcon={<Play size={14} />}
                  onClick={() => handleBatchAction('resume')}
                >
                  {t('transfer.batch.resume')}
                </Button>
                <Button
                  size='small'
                  startIcon={<Square size={14} />}
                  onClick={() => handleBatchAction('cancel')}
                  color='error'
                >
                  {t('transfer.batch.cancel')}
                </Button>
              </Box>
            </Box>
          )}

          {/* Transfer Items Table */}
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell padding='checkbox'>{/* Select All Checkbox */}</TableCell>
                  <TableCell>{t('transfer.table.type')}</TableCell>
                  <TableCell>{t('transfer.table.name')}</TableCell>
                  <TableCell>{t('transfer.table.language')}</TableCell>
                  <TableCell>{t('transfer.table.size')}</TableCell>
                  <TableCell>{t('transfer.table.progress')}</TableCell>
                  <TableCell>{t('transfer.table.status')}</TableCell>
                  <TableCell>{t('transfer.table.speed')}</TableCell>
                  <TableCell>{t('transfer.table.eta')}</TableCell>
                  <TableCell>{t('transfer.table.actions')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredItems.map(item => (
                  <TableRow key={item.id}>
                    <TableCell padding='checkbox'>{/* Checkbox for selection */}</TableCell>
                    <TableCell>
                      <Chip
                        icon={
                          item.type === 'upload' ? <Upload size={14} /> : <Download size={14} />
                        }
                        label={t(`transfer.type.${item.type}`)}
                        size='small'
                        color={item.type === 'upload' ? 'primary' : 'secondary'}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FileText size={16} />
                        <Typography variant='body2'>{item.name}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Globe size={14} />
                        <Typography variant='body2'>{item.language}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant='body2'>{formatFileSize(item.size)}</Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
                        <LinearProgress
                          variant='determinate'
                          value={item.progress}
                          sx={{ flexGrow: 1, height: 6, borderRadius: 3 }}
                        />
                        <Typography variant='caption'>{item.progress}%</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(item.status)}
                        label={t(`transfer.status.${item.status}`)}
                        size='small'
                        sx={{ color: getStatusColor(item.status) }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant='body2'>
                        {item.speed ? formatSpeed(item.speed) : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant='body2'>
                        {item.eta ? formatETA(item.eta) : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {item.status === 'running' && (
                          <Tooltip title={t('transfer.actions.pause')}>
                            <IconButton
                              size='small'
                              onClick={() => handleItemAction(item.id, 'pause')}
                            >
                              <Pause size={14} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {item.status === 'paused' && (
                          <Tooltip title={t('transfer.actions.resume')}>
                            <IconButton
                              size='small'
                              onClick={() => handleItemAction(item.id, 'resume')}
                            >
                              <Play size={14} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {item.status === 'failed' && (
                          <Tooltip title={t('transfer.actions.retry')}>
                            <IconButton
                              size='small'
                              onClick={() => handleItemAction(item.id, 'retry')}
                            >
                              <RefreshCw size={14} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {['running', 'paused', 'pending'].includes(item.status) && (
                          <Tooltip title={t('transfer.actions.cancel')}>
                            <IconButton
                              size='small'
                              onClick={() => handleItemAction(item.id, 'cancel')}
                              color='error'
                            >
                              <Square size={14} />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {filteredItems.length === 0 && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <ListIcon size={48} color={theme.palette.text.disabled} />
              <Typography variant='h6' color='text.secondary' sx={{ mt: 2 }}>
                {t('transfer.empty.title')}
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                {t('transfer.empty.description')}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onClose={() => setShowSettings(false)} maxWidth='sm' fullWidth>
        <DialogTitle>{t('transfer.settings.title')}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>{t('transfer.settings.maxConcurrent')}</InputLabel>
              <Select
                value={maxConcurrent}
                onChange={e => setMaxConcurrent(e.target.value as number)}
                label={t('transfer.settings.maxConcurrent')}
              >
                <MenuItem value={1}>1</MenuItem>
                <MenuItem value={2}>2</MenuItem>
                <MenuItem value={3}>3</MenuItem>
                <MenuItem value={4}>4</MenuItem>
                <MenuItem value={5}>5</MenuItem>
              </Select>
            </FormControl>

            <Alert severity='info' sx={{ mt: 2 }}>
              {t('transfer.settings.info')}
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSettings(false)}>{t('common.cancel')}</Button>
          <Button variant='contained' onClick={() => setShowSettings(false)}>
            {t('common.save')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default TransferPage
