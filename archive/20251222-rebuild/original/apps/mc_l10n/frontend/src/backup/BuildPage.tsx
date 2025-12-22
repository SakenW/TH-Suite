import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Checkbox,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  LinearProgress,
  Alert,
  Divider,
  Grid,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
} from '@mui/material'
import {
  FolderOpen,
  FileText,
  Settings,
  Play,
  Pause,
  Square,
  Trash2,
  Plus,
  Package,
  Download,
  Upload,
  CheckCircle,
  AlertCircle,
  Info,
  ChevronDown,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppStore } from '@stores/appStore'
import { tauriService } from '@services'
import { useMcStudioTranslation } from '@hooks/useTranslation'

interface BuildTarget {
  id: string
  name: string
  path: string
  type: 'resourcepack' | 'datapack' | 'mod' | 'plugin'
  version: string
  description?: string
}

interface BuildOptions {
  outputFormat: 'zip' | 'folder'
  compressionLevel: number
  includeMetadata: boolean
  validateStructure: boolean
  optimizeAssets: boolean
  generateManifest: boolean
  customName?: string
  outputPath?: string
}

interface BuildResult {
  id: string
  target: string
  status: 'success' | 'error' | 'warning'
  message: string
  outputPath?: string
  size?: number
  duration?: number
}

const BuildPage: React.FC = () => {
  const { currentProject } = useAppStore()
  const { t } = useMcStudioTranslation()
  const [buildTargets, setBuildTargets] = useState<BuildTarget[]>([])
  const [buildOptions, setBuildOptions] = useState<BuildOptions>({
    outputFormat: 'zip',
    compressionLevel: 6,
    includeMetadata: true,
    validateStructure: true,
    optimizeAssets: false,
    generateManifest: true,
  })
  const [isBuilding, setIsBuilding] = useState(false)
  const [buildProgress, setBuildProgress] = useState(0)
  const [buildResults, setBuildResults] = useState<BuildResult[]>([])
  const [currentBuildTarget, setCurrentBuildTarget] = useState<string>('')

  useEffect(() => {
    // 加载构建目标
    loadBuildTargets()
  }, [currentProject])

  const loadBuildTargets = async () => {
    if (!currentProject) return

    try {
      // 这里应该从项目配置或扫描结果中加载构建目标
      // 暂时使用模拟数据
      const mockTargets: BuildTarget[] = [
        {
          id: '1',
          name: 'My Resource Pack',
          path: '/path/to/resourcepack',
          type: 'resourcepack',
          version: '1.20.1',
          description: 'Custom textures and models',
        },
        {
          id: '2',
          name: 'Data Pack',
          path: '/path/to/datapack',
          type: 'datapack',
          version: '1.20.1',
          description: 'Custom recipes and loot tables',
        },
      ]
      setBuildTargets(mockTargets)
    } catch (error) {
      console.error('Failed to load build targets:', error)
      toast.error('加载构建目标失败')
    }
  }

  const handleAddTarget = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory()
      if (!selectedPath) return

      // 检测目标类型
      const targetType = await detectTargetType(selectedPath)
      if (!targetType) {
        toast.error(t('build.messages.unknownProjectType'))
        return
      }

      const newTarget: BuildTarget = {
        id: Date.now().toString(),
        name: selectedPath.split('/').pop() || 'Unknown',
        path: selectedPath,
        type: targetType,
        version: '1.20.1',
      }

      setBuildTargets(prev => [...prev, newTarget])
      toast.success(t('build.messages.addTargetSuccess'))
    } catch (error) {
      console.error(t('build.messages.addTargetFailed'), error)
      toast.error(t('build.messages.addTargetFailed'))
    }
  }

  const detectTargetType = async (path: string): Promise<BuildTarget['type'] | null> => {
    try {
      // 检查特征文件来确定项目类型
      if (await tauriService.fileExists(`${path}/pack.mcmeta`)) return 'resourcepack'
      if (await tauriService.fileExists(`${path}/data`)) return 'datapack'
      if (await tauriService.fileExists(`${path}/META-INF/mods.toml`)) return 'mod'
      if (await tauriService.fileExists(`${path}/plugin.yml`)) return 'plugin'
      return null
    } catch (error) {
      console.error('Failed to detect target type:', error)
      return null
    }
  }

  const handleRemoveTarget = (targetId: string) => {
    setBuildTargets(prev => prev.filter(target => target.id !== targetId))
    toast.success(t('build.messages.removeTargetSuccess'))
  }

  const handleSelectOutputPath = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory()
      if (selectedPath) {
        setBuildOptions(prev => ({ ...prev, outputPath: selectedPath }))
      }
    } catch (error) {
      console.error('Failed to select output path:', error)
      toast.error(t('build.messages.selectOutputPath'))
    }
  }

  const handleStartBuild = async () => {
    if (buildTargets.length === 0) {
      toast.error(t('build.messages.noTargets'))
      return
    }

    setIsBuilding(true)
    setBuildProgress(0)
    setBuildResults([])

    try {
      for (let i = 0; i < buildTargets.length; i++) {
        const target = buildTargets[i]
        setCurrentBuildTarget(target.name)

        // 模拟构建过程
        await simulateBuild(target)

        setBuildProgress(((i + 1) / buildTargets.length) * 100)
      }

      toast.success(t('build.messages.buildComplete'))
    } catch (error) {
      console.error('Build failed:', error)
      toast.error(t('build.messages.buildFailed'))
    } finally {
      setIsBuilding(false)
      setCurrentBuildTarget('')
    }
  }

  const simulateBuild = async (target: BuildTarget): Promise<void> => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const success = Math.random() > 0.2 // 80% 成功率

        const result: BuildResult = {
          id: Date.now().toString(),
          target: target.name,
          status: success ? 'success' : 'error',
          message: success
            ? t('build.results.success')
            : `${t('build.results.error')}：${t('build.messages.fileCorrupted')}`,
          outputPath: success ? `/output/${target.name}.zip` : undefined,
          size: success ? Math.floor(Math.random() * 10000000) : undefined,
          duration: Math.floor(Math.random() * 5000) + 1000,
        }

        setBuildResults(prev => [...prev, result])

        if (success) {
          resolve()
        } else {
          reject(new Error(result.message))
        }
      }, 2000)
    })
  }

  const handleStopBuild = () => {
    setIsBuilding(false)
    setBuildProgress(0)
    setCurrentBuildTarget('')
    toast.success(t('build.messages.buildStopped'))
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getTargetTypeColor = (type: BuildTarget['type']) => {
    switch (type) {
      case 'resourcepack':
        return 'primary'
      case 'datapack':
        return 'secondary'
      case 'mod':
        return 'success'
      case 'plugin':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getTargetTypeIcon = (type: BuildTarget['type']) => {
    switch (type) {
      case 'resourcepack':
        return <Package size={16} />
      case 'datapack':
        return <FileText size={16} />
      case 'mod':
        return <Settings size={16} />
      case 'plugin':
        return <Upload size={16} />
      default:
        return <FileText size={16} />
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography variant='h4' gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
          {t('build.title')}
        </Typography>

        <Grid container spacing={3}>
          {/* 构建目标 */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: 'fit-content' }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 2,
                }}
              >
                <Typography variant='h6'>{t('build.targets.title')}</Typography>
                <Button
                  variant='outlined'
                  startIcon={<Plus size={16} />}
                  onClick={handleAddTarget}
                  size='small'
                >
                  {t('build.targets.add')}
                </Button>
              </Box>

              <List>
                <AnimatePresence>
                  {buildTargets.map(target => (
                    <motion.div
                      key={target.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ duration: 0.3 }}
                    >
                      <ListItem
                        sx={{
                          border: 1,
                          borderColor: 'divider',
                          borderRadius: 1,
                          mb: 1,
                        }}
                      >
                        <Box sx={{ mr: 2 }}>{getTargetTypeIcon(target.type)}</Box>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant='subtitle2'>{target.name}</Typography>
                              <Chip
                                label={t(`build.targets.types.${target.type}`)}
                                size='small'
                                color={getTargetTypeColor(target.type) as any}
                                variant='outlined'
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant='caption' color='text.secondary'>
                                {target.path}
                              </Typography>
                              {target.description && (
                                <Typography
                                  variant='caption'
                                  display='block'
                                  color='text.secondary'
                                >
                                  {target.description}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <IconButton
                            edge='end'
                            onClick={() => handleRemoveTarget(target.id)}
                            size='small'
                            title={t('build.targets.remove')}
                          >
                            <Trash2 size={16} />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </List>

              {buildTargets.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant='body2' color='text.secondary'>
                    {t('build.targets.empty')}
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* 构建选项 */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: 'fit-content' }}>
              <Typography variant='h6' gutterBottom>
                {t('build.options.title')}
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <FormControl fullWidth size='small'>
                  <InputLabel>{t('build.options.outputFormat')}</InputLabel>
                  <Select
                    value={buildOptions.outputFormat}
                    label={t('build.options.outputFormat')}
                    onChange={e =>
                      setBuildOptions(prev => ({ ...prev, outputFormat: e.target.value as any }))
                    }
                  >
                    <MenuItem value='zip'>{t('build.options.formats.zip')}</MenuItem>
                    <MenuItem value='folder'>{t('build.options.formats.folder')}</MenuItem>
                  </Select>
                </FormControl>

                {buildOptions.outputFormat === 'zip' && (
                  <Box>
                    <Typography variant='body2' gutterBottom>
                      {t('build.options.compressionLevel')}: {buildOptions.compressionLevel}
                    </Typography>
                    <Box sx={{ px: 1 }}>
                      <input
                        type='range'
                        min='0'
                        max='9'
                        value={buildOptions.compressionLevel}
                        onChange={e =>
                          setBuildOptions(prev => ({
                            ...prev,
                            compressionLevel: parseInt(e.target.value),
                          }))
                        }
                        style={{ width: '100%' }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant='caption'>
                        {t('build.options.compression.fast')}
                      </Typography>
                      <Typography variant='caption'>
                        {t('build.options.compression.best')}
                      </Typography>
                    </Box>
                  </Box>
                )}

                <TextField
                  label={t('build.options.customName')}
                  value={buildOptions.customName || ''}
                  onChange={e => setBuildOptions(prev => ({ ...prev, customName: e.target.value }))}
                  size='small'
                  placeholder={t('build.options.placeholders.customName')}
                />

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TextField
                    label={t('build.options.outputPath')}
                    value={buildOptions.outputPath || ''}
                    size='small'
                    fullWidth
                    placeholder={t('build.options.placeholders.outputPath')}
                    InputProps={{ readOnly: true }}
                  />
                  <Button
                    variant='outlined'
                    onClick={handleSelectOutputPath}
                    startIcon={<FolderOpen size={16} />}
                    size='small'
                  >
                    {t('build.options.select')}
                  </Button>
                </Box>

                <Divider />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={buildOptions.includeMetadata}
                      onChange={e =>
                        setBuildOptions(prev => ({ ...prev, includeMetadata: e.target.checked }))
                      }
                    />
                  }
                  label={t('build.options.includeMetadata')}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={buildOptions.validateStructure}
                      onChange={e =>
                        setBuildOptions(prev => ({ ...prev, validateStructure: e.target.checked }))
                      }
                    />
                  }
                  label={t('build.options.validateStructure')}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={buildOptions.optimizeAssets}
                      onChange={e =>
                        setBuildOptions(prev => ({ ...prev, optimizeAssets: e.target.checked }))
                      }
                    />
                  }
                  label={t('build.options.optimizeAssets')}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={buildOptions.generateManifest}
                      onChange={e =>
                        setBuildOptions(prev => ({ ...prev, generateManifest: e.target.checked }))
                      }
                    />
                  }
                  label={t('build.options.generateManifest')}
                />
              </Box>
            </Paper>
          </Grid>

          {/* 构建控制 */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 2,
                }}
              >
                <Typography variant='h6'>{t('build.control.title')}</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant='contained'
                    startIcon={<Play size={16} />}
                    onClick={handleStartBuild}
                    disabled={isBuilding || buildTargets.length === 0}
                  >
                    {t('build.control.start')}
                  </Button>
                  <Button
                    variant='outlined'
                    startIcon={<Square size={16} />}
                    onClick={handleStopBuild}
                    disabled={!isBuilding}
                  >
                    {t('build.control.stop')}
                  </Button>
                </Box>
              </Box>

              {isBuilding && (
                <Box sx={{ mb: 2 }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      mb: 1,
                    }}
                  >
                    <Typography variant='body2'>
                      {t('build.control.building')}: {currentBuildTarget}
                    </Typography>
                    <Typography variant='body2'>{Math.round(buildProgress)}%</Typography>
                  </Box>
                  <LinearProgress variant='determinate' value={buildProgress} />
                </Box>
              )}

              {buildResults.length > 0 && (
                <Accordion>
                  <AccordionSummary expandIcon={<ChevronDown />}>
                    <Typography variant='subtitle1'>{t('build.results.title')}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List>
                      {buildResults.map(result => (
                        <ListItem key={result.id} sx={{ px: 0 }}>
                          <Box sx={{ mr: 2 }}>
                            {result.status === 'success' && <CheckCircle size={20} color='green' />}
                            {result.status === 'error' && <AlertCircle size={20} color='red' />}
                            {result.status === 'warning' && <Info size={20} color='orange' />}
                          </Box>
                          <ListItemText
                            primary={result.target}
                            secondary={
                              <Box>
                                <Typography variant='caption' color='text.secondary'>
                                  {result.message}
                                </Typography>
                                {result.outputPath && (
                                  <Typography
                                    variant='caption'
                                    display='block'
                                    color='text.secondary'
                                  >
                                    {t('build.results.output')}: {result.outputPath}
                                  </Typography>
                                )}
                                {result.size && (
                                  <Typography
                                    variant='caption'
                                    display='block'
                                    color='text.secondary'
                                  >
                                    {t('build.results.size')}: {formatFileSize(result.size)}
                                  </Typography>
                                )}
                                {result.duration && (
                                  <Typography
                                    variant='caption'
                                    display='block'
                                    color='text.secondary'
                                  >
                                    {t('build.results.duration')}:{' '}
                                    {(result.duration / 1000).toFixed(1)}s
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                          {result.outputPath && (
                            <ListItemSecondaryAction>
                              <Tooltip title={t('build.results.openOutput')}>
                                <IconButton
                                  edge='end'
                                  onClick={() => tauriService.openPath(result.outputPath!)}
                                  size='small'
                                >
                                  <FolderOpen size={16} />
                                </IconButton>
                              </Tooltip>
                            </ListItemSecondaryAction>
                          )}
                        </ListItem>
                      ))}
                    </List>
                  </AccordionDetails>
                </Accordion>
              )}
            </Paper>
          </Grid>
        </Grid>
      </motion.div>
    </Box>
  )
}

export default BuildPage
