import React, { useState, useEffect } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  alpha,
  useTheme,
} from '@mui/material'
import {
  Server,
  Wifi,
  WifiOff,
  Globe,
  Trash2,
  RefreshCw,
  Settings,
  Clock,
  Database,
  Download,
  Upload,
  CheckCircle,
  AlertCircle,
  Info,
  HardDrive,
  Activity,
  Package,
} from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppStore } from '@stores/appStore'
import { apiService } from '@services/apiService'
import { useMcStudioTranslation } from '@hooks/useTranslation'

interface ServerStatus {
  status: 'healthy' | 'unhealthy' | 'unreachable'
  server_version?: string
  capabilities?: string[]
  response_time_ms?: string
  server_time?: string
  http_status?: number
  error?: string
}

interface ModpackInfo {
  id: string
  name: string
  version: string
  mod_count: number
  translation_progress: number
  supported_languages: string[]
  last_updated: string
}

interface TranslationStats {
  total_mods: number
  translated_mods: number
  total_keys: number
  translated_keys: number
  languages: {
    code: string
    name: string
    progress: number
  }[]
}

interface CacheInfo {
  type: string
  size: string
  entries: number
  last_updated: string
  hit_rate?: number
}

function ServerPage() {
  const theme = useTheme()
  const { t } = useMcStudioTranslation()
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null)
  const [modpacks, setModpacks] = useState<ModpackInfo[]>([])
  const [translationStats, setTranslationStats] = useState<TranslationStats | null>(null)
  const [cacheInfo, setCacheInfo] = useState<CacheInfo[]>([])
  const [loading, setLoading] = useState({
    status: false,
    modpacks: false,
    stats: false,
    cache: false,
  })
  const [serverUrl, setServerUrl] = useState('https://api.mc-studio.com')
  const [showServerDialog, setShowServerDialog] = useState(false)
  const [tempServerUrl, setTempServerUrl] = useState('')

  // 检查服务器状态
  const checkServerStatus = async () => {
    setLoading(prev => ({ ...prev, status: true }))
    try {
      // 这里应该调用实际的API
      // const status = await apiService.checkServerHealth();

      // 模拟API响应
      await new Promise(resolve => setTimeout(resolve, 1000))
      const mockStatus: ServerStatus = {
        status: 'healthy',
        server_version: '1.2.3',
        capabilities: ['translation', 'upload', 'download', 'cache'],
        response_time_ms: '125',
        server_time: new Date().toISOString(),
      }

      setServerStatus(mockStatus)
      toast.success('服务器状态检查完成')
    } catch (error) {
      console.error('Failed to check server status:', error)
      setServerStatus({
        status: 'unreachable',
        error: '无法连接到服务器',
      })
      toast.error('服务器连接失败')
    } finally {
      setLoading(prev => ({ ...prev, status: false }))
    }
  }

  // 获取组合包信息
  const fetchModpacks = async () => {
    setLoading(prev => ({ ...prev, modpacks: true }))
    try {
      // 这里应该调用实际的API
      // const packs = await apiService.getModpacks();

      // 模拟API响应
      await new Promise(resolve => setTimeout(resolve, 800))
      const mockModpacks: ModpackInfo[] = [
        {
          id: 'pack-1',
          name: 'All the Mods 9',
          version: '0.2.59',
          mod_count: 423,
          translation_progress: 85.6,
          supported_languages: ['zh-CN', 'en-US', 'ja-JP'],
          last_updated: '2024-01-15T10:30:00Z',
        },
        {
          id: 'pack-2',
          name: 'FTB Skies',
          version: '1.2.3',
          mod_count: 287,
          translation_progress: 92.3,
          supported_languages: ['zh-CN', 'en-US'],
          last_updated: '2024-01-14T15:20:00Z',
        },
        {
          id: 'pack-3',
          name: 'Create: Above and Beyond',
          version: '1.4.1',
          mod_count: 156,
          translation_progress: 67.8,
          supported_languages: ['zh-CN', 'en-US', 'ja-JP', 'ko-KR'],
          last_updated: '2024-01-10T09:15:00Z',
        },
      ]

      setModpacks(mockModpacks)
    } catch (error) {
      console.error('Failed to fetch modpacks:', error)
      toast.error('获取组合包信息失败')
    } finally {
      setLoading(prev => ({ ...prev, modpacks: false }))
    }
  }

  // 获取翻译统计
  const fetchTranslationStats = async () => {
    setLoading(prev => ({ ...prev, stats: true }))
    try {
      // 这里应该调用实际的API
      // const stats = await apiService.getTranslationStats();

      // 模拟API响应
      await new Promise(resolve => setTimeout(resolve, 600))
      const mockStats: TranslationStats = {
        total_mods: 866,
        translated_mods: 743,
        total_keys: 45672,
        translated_keys: 38945,
        languages: [
          { code: 'zh-CN', name: '简体中文', progress: 95.2 },
          { code: 'en-US', name: 'English (US)', progress: 100.0 },
          { code: 'ja-JP', name: '日本語', progress: 78.4 },
          { code: 'ko-KR', name: '한국어', progress: 45.6 },
          { code: 'fr-FR', name: 'Français', progress: 62.1 },
        ],
      }

      setTranslationStats(mockStats)
    } catch (error) {
      console.error('Failed to fetch translation stats:', error)
      toast.error('获取翻译统计失败')
    } finally {
      setLoading(prev => ({ ...prev, stats: false }))
    }
  }

  // 获取缓存信息
  const fetchCacheInfo = async () => {
    setLoading(prev => ({ ...prev, cache: true }))
    try {
      // 这里应该调用实际的API
      // const cache = await apiService.getCacheInfo();

      // 模拟API响应
      await new Promise(resolve => setTimeout(resolve, 600))
      const mockCache: CacheInfo[] = [
        {
          type: '项目解析缓存',
          size: '45.2 MB',
          entries: 128,
          last_updated: '2024-01-15T12:30:00Z',
          hit_rate: 85.6,
        },
        {
          type: '语言包缓存',
          size: '123.8 MB',
          entries: 45,
          last_updated: '2024-01-15T11:45:00Z',
          hit_rate: 92.3,
        },
        {
          type: '服务器响应缓存',
          size: '12.1 MB',
          entries: 256,
          last_updated: '2024-01-15T13:15:00Z',
          hit_rate: 78.9,
        },
      ]

      setCacheInfo(mockCache)
    } catch (error) {
      console.error('Failed to fetch cache info:', error)
      toast.error('获取缓存信息失败')
    } finally {
      setLoading(prev => ({ ...prev, cache: false }))
    }
  }

  // 清理缓存
  const clearCache = async (cacheType: string) => {
    try {
      // 这里应该调用实际的API
      // await apiService.clearCache(cacheType);

      await new Promise(resolve => setTimeout(resolve, 500))
      toast.success(`${cacheType}已清理`)
      fetchCacheInfo() // 重新获取缓存信息
    } catch (error) {
      console.error('Failed to clear cache:', error)
      toast.error('清理缓存失败')
    }
  }

  // 更新服务器URL
  const updateServerUrl = () => {
    setServerUrl(tempServerUrl)
    setShowServerDialog(false)
    toast.success('服务器地址已更新')
    // 重新检查服务器状态
    checkServerStatus()
  }

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'available':
        return theme.palette.success.main
      case 'partial':
        return theme.palette.warning.main
      case 'unhealthy':
      case 'unavailable':
      case 'unreachable':
        return theme.palette.error.main
      default:
        return theme.palette.grey[500]
    }
  }

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'available':
        return <CheckCircle size={16} />
      case 'partial':
        return <AlertCircle size={16} />
      case 'unhealthy':
      case 'unavailable':
      case 'unreachable':
        return <AlertCircle size={16} />
      default:
        return <Info size={16} />
    }
  }

  // 初始化数据
  useEffect(() => {
    checkServerStatus()
    fetchModpacks()
    fetchTranslationStats()
    fetchCacheInfo()
  }, [])

  return (
    <Box
      sx={{
        p: 3,
        maxWidth: 1200,
        mx: 'auto',
        height: '100vh',
        overflow: 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography variant='h4' gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
          {t('server.title')}
        </Typography>

        <Grid container spacing={3} sx={{ flex: 1, alignItems: 'flex-start' }}>
          {/* 服务器状态卡片 */}
          <Grid item xs={12} lg={6}>
            <Card sx={{ height: 'fit-content', minHeight: 400 }}>
              <CardContent>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 2,
                  }}
                >
                  <Typography variant='h6' sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Server size={20} />
                    {t('server.status.title')}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <IconButton
                      size='small'
                      onClick={() => {
                        setTempServerUrl(serverUrl)
                        setShowServerDialog(true)
                      }}
                    >
                      <Settings size={16} />
                    </IconButton>
                    <IconButton size='small' onClick={checkServerStatus} disabled={loading.status}>
                      <RefreshCw size={16} className={loading.status ? 'animate-spin' : ''} />
                    </IconButton>
                  </Box>
                </Box>

                {loading.status ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <CircularProgress size={20} />
                    <Typography>{t('server.status.checking')}</Typography>
                  </Box>
                ) : serverStatus ? (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Chip
                        icon={getStatusIcon(serverStatus.status)}
                        label={
                          serverStatus.status === 'healthy'
                            ? t('server.status.healthy')
                            : serverStatus.status === 'unhealthy'
                              ? t('server.status.unhealthy')
                              : t('server.status.unreachable')
                        }
                        color={serverStatus.status === 'healthy' ? 'success' : 'error'}
                        size='small'
                      />
                      {serverStatus.status === 'healthy' && (
                        <Typography variant='body2' color='text.secondary'>
                          {t('server.status.responseTime')}: {serverStatus.response_time_ms}ms
                        </Typography>
                      )}
                    </Box>

                    {serverStatus.status === 'healthy' && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant='body2' color='text.secondary' gutterBottom>
                          {t('server.status.serverVersion')}: {serverStatus.server_version}
                        </Typography>
                        <Typography variant='body2' color='text.secondary' gutterBottom>
                          {t('server.status.capabilities')}:
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                          {serverStatus.capabilities?.map(capability => (
                            <Chip
                              key={capability}
                              label={capability}
                              size='small'
                              variant='outlined'
                            />
                          ))}
                        </Box>
                      </Box>
                    )}

                    {serverStatus.error && (
                      <Alert severity='error' sx={{ mt: 2 }}>
                        {serverStatus.error}
                      </Alert>
                    )}
                  </Box>
                ) : (
                  <Typography color='text.secondary'>点击刷新按钮检查服务器状态</Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* 组合包信息卡片 */}
          <Grid item xs={12} lg={6}>
            <Card sx={{ height: 'fit-content', minHeight: 400 }}>
              <CardContent>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 2,
                  }}
                >
                  <Typography variant='h6' sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Package size={20} />
                    组合包信息
                  </Typography>
                  <IconButton size='small' onClick={fetchModpacks} disabled={loading.modpacks}>
                    <RefreshCw size={16} className={loading.modpacks ? 'animate-spin' : ''} />
                  </IconButton>
                </Box>

                {loading.modpacks ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <CircularProgress size={20} />
                    <Typography>加载组合包信息...</Typography>
                  </Box>
                ) : (
                  <List dense>
                    {modpacks.map(pack => (
                      <ListItem key={pack.id} sx={{ px: 0 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              backgroundColor:
                                pack.translation_progress >= 90
                                  ? theme.palette.success.main
                                  : pack.translation_progress >= 70
                                    ? theme.palette.warning.main
                                    : theme.palette.error.main,
                            }}
                          />
                        </ListItemIcon>
                        <ListItemText
                          primary={`${pack.name} v${pack.version}`}
                          secondary={
                            <Box>
                              <Typography variant='caption' display='block'>
                                {pack.mod_count} MODs • {pack.translation_progress.toFixed(1)}%
                                翻译完成
                              </Typography>
                              <Typography variant='caption' color='text.secondary'>
                                支持 {pack.supported_languages.length} 种语言 •{' '}
                                {new Date(pack.last_updated).toLocaleDateString()}
                              </Typography>
                            </Box>
                          }
                        />
                        <Chip
                          label={
                            pack.translation_progress >= 90
                              ? '完成'
                              : pack.translation_progress >= 70
                                ? '进行中'
                                : '待翻译'
                          }
                          size='small'
                          color={
                            pack.translation_progress >= 90
                              ? 'success'
                              : pack.translation_progress >= 70
                                ? 'warning'
                                : 'error'
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* 翻译统计卡片 */}
          <Grid item xs={12} lg={6}>
            <Card sx={{ height: 'fit-content', minHeight: 400 }}>
              <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 2,
                  }}
                >
                  <Typography variant='h6' sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Globe size={20} />
                    翻译统计
                  </Typography>
                  <IconButton onClick={fetchTranslationStats} disabled={loading.stats} size='small'>
                    <RefreshCw size={16} className={loading.stats ? 'animate-spin' : ''} />
                  </IconButton>
                </Box>

                {loading.stats ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress size={24} />
                  </Box>
                ) : translationStats ? (
                  <Box>
                    {/* 整体统计 */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant='body2' color='text.secondary' gutterBottom>
                        整体进度
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
                        <Box>
                          <Typography variant='h4' color='primary'>
                            {translationStats.translated_mods}
                          </Typography>
                          <Typography variant='caption' color='text.secondary'>
                            / {translationStats.total_mods} MODs
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant='h4' color='primary'>
                            {Math.round(
                              (translationStats.translated_keys / translationStats.total_keys) *
                                100,
                            )}
                            %
                          </Typography>
                          <Typography variant='caption' color='text.secondary'>
                            {translationStats.translated_keys.toLocaleString()} /{' '}
                            {translationStats.total_keys.toLocaleString()} 条目
                          </Typography>
                        </Box>
                      </Box>
                    </Box>

                    {/* 语言进度 */}
                    <Typography variant='body2' color='text.secondary' gutterBottom>
                      各语言支持情况
                    </Typography>
                    <Box
                      sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 1,
                        maxHeight: 200,
                        overflow: 'auto',
                      }}
                    >
                      {translationStats.languages.map(lang => (
                        <Box key={lang.code} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Box sx={{ minWidth: 80 }}>
                            <Typography variant='caption'>{lang.name}</Typography>
                          </Box>
                          <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                            <LinearProgress
                              variant='determinate'
                              value={lang.progress}
                              sx={{ flex: 1, height: 6, borderRadius: 3 }}
                              color={
                                lang.progress >= 90
                                  ? 'success'
                                  : lang.progress >= 70
                                    ? 'warning'
                                    : 'error'
                              }
                            />
                            <Typography variant='caption' sx={{ minWidth: 40, textAlign: 'right' }}>
                              {lang.progress.toFixed(1)}%
                            </Typography>
                          </Box>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                ) : null}
              </CardContent>
            </Card>
          </Grid>

          {/* 缓存管理卡片 */}
          <Grid item xs={12}>
            <Card sx={{ height: 'fit-content' }}>
              <CardContent sx={{ overflow: 'auto' }}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 2,
                  }}
                >
                  <Typography variant='h6' sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Database size={20} />
                    {t('server.cache.title')}
                  </Typography>
                  <IconButton size='small' onClick={fetchCacheInfo} disabled={loading.cache}>
                    <RefreshCw size={16} className={loading.cache ? 'animate-spin' : ''} />
                  </IconButton>
                </Box>

                {loading.cache ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <CircularProgress size={20} />
                    <Typography>{t('server.cache.loading')}</Typography>
                  </Box>
                ) : (
                  <TableContainer sx={{ maxHeight: 400, overflow: 'auto' }}>
                    <Table stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell>{t('server.cache.type')}</TableCell>
                          <TableCell align='right'>{t('server.cache.size')}</TableCell>
                          <TableCell align='right'>{t('server.cache.entries')}</TableCell>
                          <TableCell align='right'>{t('server.cache.hitRate')}</TableCell>
                          <TableCell align='right'>{t('server.languages.lastUpdated')}</TableCell>
                          <TableCell align='right'>{t('server.actions.actions')}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {cacheInfo.map(cache => (
                          <TableRow key={cache.type}>
                            <TableCell>{cache.type}</TableCell>
                            <TableCell align='right'>{cache.size}</TableCell>
                            <TableCell align='right'>{cache.entries}</TableCell>
                            <TableCell align='right'>
                              {cache.hit_rate ? `${cache.hit_rate.toFixed(1)}%` : '-'}
                            </TableCell>
                            <TableCell align='right'>
                              {new Date(cache.last_updated).toLocaleDateString()}
                            </TableCell>
                            <TableCell align='right'>
                              <Tooltip title={t('server.actions.clearCache')}>
                                <IconButton
                                  size='small'
                                  onClick={() => clearCache(cache.type)}
                                  color='error'
                                >
                                  <Trash2 size={16} />
                                </IconButton>
                              </Tooltip>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* 服务器设置对话框 */}
        <Dialog
          open={showServerDialog}
          onClose={() => setShowServerDialog(false)}
          maxWidth='sm'
          fullWidth
        >
          <DialogTitle>服务器设置</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              label='服务器地址'
              value={tempServerUrl}
              onChange={e => setTempServerUrl(e.target.value)}
              placeholder='https://api.mc-studio.com'
              sx={{ mt: 2 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowServerDialog(false)}>取消</Button>
            <Button onClick={updateServerUrl} variant='contained'>
              保存
            </Button>
          </DialogActions>
        </Dialog>
      </motion.div>
    </Box>
  )
}

export default ServerPage
