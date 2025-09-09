import React, { useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  FormControlLabel,
  Checkbox,
  RadioGroup,
  Radio,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Tooltip,
  Alert,
} from '@mui/material'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Download,
  FileJson,
  FileText,
  FileArchive,
  FolderOpen,
  Settings,
  Filter,
  Package,
  Globe,
  Hash,
  Check,
  X,
  Info,
  Upload,
  Save,
  Play,
  Eye,
  Copy,
  Trash2,
  Plus,
  HardDrive,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { MinecraftButton } from '../components/minecraft/MinecraftButton'
import { MinecraftCard } from '../components/minecraft/MinecraftCard'
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress'
import { MinecraftBlock } from '../components/MinecraftComponents'
import { MinecraftDataExchange } from '../components/minecraft/MinecraftDataExchange'

interface ExportProfile {
  id: string
  name: string
  format: 'json' | 'properties' | 'lang' | 'csv' | 'excel'
  languages: string[]
  includeComments: boolean
  includeMetadata: boolean
  compression: 'none' | 'zip' | 'tar' | '7z'
  splitByMod: boolean
  template?: string
}

interface ExportTask {
  id: string
  name: string
  profile: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  progress: number
  files: number
  size: number
  createdAt: string
  error?: string
}

const exportProfiles: ExportProfile[] = [
  {
    id: '1',
    name: 'Minecraft 标准格式',
    format: 'json',
    languages: ['zh_CN', 'en_US'],
    includeComments: false,
    includeMetadata: true,
    compression: 'zip',
    splitByMod: true,
  },
  {
    id: '2',
    name: 'Forge 兼容格式',
    format: 'lang',
    languages: ['zh_CN'],
    includeComments: true,
    includeMetadata: false,
    compression: 'none',
    splitByMod: false,
  },
  {
    id: '3',
    name: '翻译团队格式',
    format: 'excel',
    languages: ['zh_CN', 'zh_TW', 'en_US'],
    includeComments: true,
    includeMetadata: true,
    compression: 'zip',
    splitByMod: true,
  },
]

const exportTasks: ExportTask[] = [
  {
    id: '1',
    name: 'ATM9_完整汉化包_v1.2',
    profile: 'Minecraft 标准格式',
    status: 'completed',
    progress: 100,
    files: 450,
    size: 12500000,
    createdAt: '2025-01-01 14:30',
  },
  {
    id: '2',
    name: 'Create_模组语言包',
    profile: 'Forge 兼容格式',
    status: 'processing',
    progress: 65,
    files: 120,
    size: 3200000,
    createdAt: '2025-01-01 15:45',
  },
]

export default function ExportPageMinecraft() {
  const [selectedProfile, setSelectedProfile] = useState(exportProfiles[0])
  const [tasks, setTasks] = useState<ExportTask[]>(exportTasks)
  const [exportSettings, setExportSettings] = useState({
    outputPath: 'D:/Exports/Minecraft',
    namePattern: '{project}_{date}_{version}',
    overwriteExisting: false,
    validateContent: true,
    generateReport: true,
    openAfterExport: true,
  })

  const handleStartExport = () => {
    const newTask: ExportTask = {
      id: Date.now().toString(),
      name: `导出任务_${new Date().toLocaleTimeString()}`,
      profile: selectedProfile.name,
      status: 'processing',
      progress: 0,
      files: 0,
      size: 0,
      createdAt: new Date().toLocaleString(),
    }

    setTasks(prev => [newTask, ...prev])
    toast.success('开始导出...', { icon: '🚀' })

    // 模拟导出进度
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 20
      if (progress >= 100) {
        progress = 100
        clearInterval(interval)
        setTasks(prev =>
          prev.map(t =>
            t.id === newTask.id
              ? { ...t, status: 'completed', progress: 100, files: 234, size: 5600000 }
              : t,
          ),
        )
        toast.success('导出完成！', { icon: '✅' })
      } else {
        setTasks(prev =>
          prev.map(t =>
            t.id === newTask.id
              ? {
                  ...t,
                  progress,
                  files: Math.floor(progress * 2.34),
                  size: Math.floor(progress * 56000),
                }
              : t,
          ),
        )
      }
    }, 500)
  }

  const handleDeleteTask = (taskId: string) => {
    setTasks(prev => prev.filter(t => t.id !== taskId))
    toast.success('任务已删除', { icon: '🗑️' })
  }

  const handleDownloadResult = (task: ExportTask) => {
    toast.success(`下载 ${task.name}`, { icon: '💾' })
  }

  const formatSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'json':
        return <FileJson size={20} color='#4CAF50' />
      case 'properties':
      case 'lang':
        return <FileText size={20} color='#2196F3' />
      case 'csv':
        return <FileText size={20} color='#FF9800' />
      case 'excel':
        return <FileText size={20} color='#4CAF50' />
      default:
        return <FileText size={20} />
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ mb: 4 }}>
          <Typography
            variant='h3'
            sx={{
              fontFamily: '"Minecraft", "Press Start 2P", monospace',
              fontSize: { xs: '24px', md: '32px' },
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              background: 'linear-gradient(135deg, #4CAF50 0%, #2196F3 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              mb: 1,
            }}
          >
            📤 导出管理
          </Typography>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '14px',
              color: 'text.secondary',
            }}
          >
            导出翻译文件到各种格式
          </Typography>
        </Box>
      </motion.div>

      <Grid container spacing={3}>
        {/* 导出配置 */}
        <Grid item xs={12} lg={6}>
          <MinecraftCard variant='crafting' title='导出配置' icon='diamond'>
            <Box sx={{ p: 2 }}>
              {/* 预设选择 */}
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                  导出预设
                </InputLabel>
                <Select
                  value={selectedProfile.id}
                  onChange={e => {
                    const profile = exportProfiles.find(p => p.id === e.target.value)
                    if (profile) setSelectedProfile(profile)
                  }}
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  }}
                >
                  {exportProfiles.map(profile => (
                    <MenuItem key={profile.id} value={profile.id}>
                      {profile.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* 格式选择 */}
              <Box sx={{ mb: 3 }}>
                <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                  导出格式
                </Typography>
                <RadioGroup
                  value={selectedProfile.format}
                  onChange={e =>
                    setSelectedProfile({ ...selectedProfile, format: e.target.value as any })
                  }
                >
                  <FormControlLabel
                    value='json'
                    control={<Radio size='small' />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FileJson size={16} />
                        <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                          JSON (1.13+)
                        </Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value='lang'
                    control={<Radio size='small' />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FileText size={16} />
                        <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                          LANG (1.12.2)
                        </Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value='properties'
                    control={<Radio size='small' />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FileText size={16} />
                        <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                          Properties
                        </Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value='excel'
                    control={<Radio size='small' />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FileText size={16} />
                        <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                          Excel
                        </Typography>
                      </Box>
                    }
                  />
                </RadioGroup>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* 语言选择 */}
              <Box sx={{ mb: 3 }}>
                <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                  导出语言
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {['zh_CN', 'zh_TW', 'en_US', 'ja_JP', 'ko_KR'].map(lang => (
                    <Chip
                      key={lang}
                      label={lang}
                      onClick={() => {
                        const languages = selectedProfile.languages.includes(lang)
                          ? selectedProfile.languages.filter(l => l !== lang)
                          : [...selectedProfile.languages, lang]
                        setSelectedProfile({ ...selectedProfile, languages })
                      }}
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '11px',
                        background: selectedProfile.languages.includes(lang)
                          ? 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)'
                          : 'rgba(0,0,0,0.3)',
                        borderRadius: 0,
                        cursor: 'pointer',
                      }}
                    />
                  ))}
                </Box>
              </Box>

              {/* 导出选项 */}
              <Box sx={{ mb: 3 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectedProfile.includeComments}
                      onChange={e =>
                        setSelectedProfile({
                          ...selectedProfile,
                          includeComments: e.target.checked,
                        })
                      }
                      size='small'
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                      包含注释
                    </Typography>
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectedProfile.includeMetadata}
                      onChange={e =>
                        setSelectedProfile({
                          ...selectedProfile,
                          includeMetadata: e.target.checked,
                        })
                      }
                      size='small'
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                      包含元数据
                    </Typography>
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectedProfile.splitByMod}
                      onChange={e =>
                        setSelectedProfile({ ...selectedProfile, splitByMod: e.target.checked })
                      }
                      size='small'
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                      按模组分割
                    </Typography>
                  }
                />
              </Box>

              {/* 压缩选项 */}
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                  压缩格式
                </InputLabel>
                <Select
                  value={selectedProfile.compression}
                  onChange={e =>
                    setSelectedProfile({ ...selectedProfile, compression: e.target.value as any })
                  }
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  }}
                >
                  <MenuItem value='none'>不压缩</MenuItem>
                  <MenuItem value='zip'>ZIP</MenuItem>
                  <MenuItem value='tar'>TAR</MenuItem>
                  <MenuItem value='7z'>7Z</MenuItem>
                </Select>
              </FormControl>

              {/* 输出路径 */}
              <TextField
                fullWidth
                label='输出路径'
                value={exportSettings.outputPath}
                onChange={e => setExportSettings({ ...exportSettings, outputPath: e.target.value })}
                InputLabelProps={{
                  sx: { fontFamily: '"Minecraft", monospace', fontSize: '12px' },
                }}
                InputProps={{
                  endAdornment: (
                    <MinecraftButton
                      minecraftStyle='gold'
                      size='small'
                      onClick={() => toast.info('选择文件夹...')}
                    >
                      <FolderOpen size={16} />
                    </MinecraftButton>
                  ),
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  },
                }}
                sx={{ mb: 3 }}
              />

              {/* 操作按钮 */}
              <Box sx={{ display: 'flex', gap: 2 }}>
                <MinecraftButton
                  fullWidth
                  minecraftStyle='emerald'
                  onClick={handleStartExport}
                  startIcon={<Download size={16} />}
                  glowing
                >
                  开始导出
                </MinecraftButton>
                <MinecraftButton
                  fullWidth
                  minecraftStyle='diamond'
                  onClick={() => toast.info('保存预设...')}
                  startIcon={<Save size={16} />}
                >
                  保存预设
                </MinecraftButton>
              </Box>
            </Box>
          </MinecraftCard>
        </Grid>

        {/* 导出任务 */}
        <Grid item xs={12} lg={6}>
          <MinecraftCard variant='chest' title='导出任务' icon='gold'>
            <Box sx={{ p: 2 }}>
              <List>
                <AnimatePresence>
                  {tasks.map((task, index) => (
                    <motion.div
                      key={task.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                    >
                      <ListItem
                        sx={{
                          mb: 1,
                          background: 'rgba(0,0,0,0.2)',
                          border: `1px solid ${
                            task.status === 'completed'
                              ? '#4CAF50'
                              : task.status === 'processing'
                                ? '#2196F3'
                                : task.status === 'error'
                                  ? '#F44336'
                                  : '#4A4A4A'
                          }`,
                          borderRadius: 0,
                        }}
                      >
                        <ListItemIcon>
                          {task.status === 'completed' ? (
                            <Check size={20} color='#4CAF50' />
                          ) : task.status === 'processing' ? (
                            <Play size={20} color='#2196F3' />
                          ) : task.status === 'error' ? (
                            <X size={20} color='#F44336' />
                          ) : (
                            <Info size={20} />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '14px',
                                color: '#FFFFFF',
                              }}
                            >
                              {task.name}
                            </Typography>
                          }
                          secondary={
                            <Box>
                              <Box sx={{ display: 'flex', gap: 2, mt: 0.5 }}>
                                <Typography
                                  sx={{
                                    fontFamily: '"Minecraft", monospace',
                                    fontSize: '10px',
                                    color: 'text.secondary',
                                  }}
                                >
                                  {task.profile}
                                </Typography>
                                <Typography
                                  sx={{
                                    fontFamily: '"Minecraft", monospace',
                                    fontSize: '10px',
                                    color: 'text.secondary',
                                  }}
                                >
                                  {task.createdAt}
                                </Typography>
                              </Box>
                              {task.status === 'processing' && (
                                <Box sx={{ mt: 1 }}>
                                  <MinecraftProgress
                                    value={task.progress}
                                    variant='loading'
                                    size='small'
                                    animated
                                  />
                                </Box>
                              )}
                              {task.status === 'completed' && (
                                <Box sx={{ mt: 1, display: 'flex', gap: 2 }}>
                                  <Chip
                                    label={`${task.files} 文件`}
                                    size='small'
                                    sx={{
                                      fontFamily: '"Minecraft", monospace',
                                      fontSize: '10px',
                                      height: 20,
                                      background: 'rgba(0,0,0,0.3)',
                                      borderRadius: 0,
                                    }}
                                  />
                                  <Chip
                                    label={formatSize(task.size)}
                                    size='small'
                                    sx={{
                                      fontFamily: '"Minecraft", monospace',
                                      fontSize: '10px',
                                      height: 20,
                                      background: 'rgba(0,0,0,0.3)',
                                      borderRadius: 0,
                                    }}
                                  />
                                </Box>
                              )}
                              {task.error && (
                                <Alert
                                  severity='error'
                                  sx={{
                                    mt: 1,
                                    py: 0.5,
                                    fontFamily: '"Minecraft", monospace',
                                    fontSize: '10px',
                                    background: 'rgba(244,67,54,0.1)',
                                    border: '1px solid #F44336',
                                    borderRadius: 0,
                                  }}
                                >
                                  {task.error}
                                </Alert>
                              )}
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          {task.status === 'completed' && (
                            <>
                              <Tooltip title='下载'>
                                <IconButton size='small' onClick={() => handleDownloadResult(task)}>
                                  <Download size={16} />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title='查看'>
                                <IconButton size='small'>
                                  <Eye size={16} />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                          <Tooltip title='删除'>
                            <IconButton size='small' onClick={() => handleDeleteTask(task.id)}>
                              <Trash2 size={16} />
                            </IconButton>
                          </Tooltip>
                        </ListItemSecondaryAction>
                      </ListItem>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </List>

              {tasks.length === 0 && (
                <Box sx={{ py: 4, textAlign: 'center', opacity: 0.6 }}>
                  <Package size={48} />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '14px',
                      color: 'text.secondary',
                      mt: 2,
                    }}
                  >
                    暂无导出任务
                  </Typography>
                </Box>
              )}
            </Box>
          </MinecraftCard>
        </Grid>

        {/* 快速统计 */}
        <Grid item xs={12}>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <MinecraftCard variant='inventory'>
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <Download size={24} />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#FFFFFF',
                      mt: 1,
                    }}
                  >
                    {tasks.filter(t => t.status === 'completed').length}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    已完成
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={3}>
              <MinecraftCard variant='inventory'>
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <Play size={24} color='#2196F3' />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#2196F3',
                      mt: 1,
                    }}
                  >
                    {tasks.filter(t => t.status === 'processing').length}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    处理中
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={3}>
              <MinecraftCard variant='inventory'>
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <FileArchive size={24} color='#FFD700' />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#FFD700',
                      mt: 1,
                    }}
                  >
                    {tasks.reduce((sum, t) => sum + t.files, 0)}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    总文件数
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={3}>
              <MinecraftCard variant='inventory'>
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <HardDrive size={24} color='#9C27B0' />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#9C27B0',
                      mt: 1,
                    }}
                  >
                    {formatSize(tasks.reduce((sum, t) => sum + t.size, 0))}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    总大小
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {/* 数据导入导出功能 */}
      <Box sx={{ mt: 4 }}>
        <Typography
          variant='h4'
          sx={{
            fontFamily: '"Minecraft", monospace',
            fontSize: '20px',
            mb: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            color: '#FFD700',
          }}
        >
          <Package size={24} />
          数据管理
        </Typography>
        <MinecraftDataExchange />
      </Box>
    </Box>
  )
}
