import React, { useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Slider,
  Divider,
  Alert,
  Tabs,
  Tab,
  RadioGroup,
  Radio,
  Button as MuiButton,
} from '@mui/material'
import { motion } from 'framer-motion'
import {
  Settings,
  Globe,
  Palette,
  Volume2,
  Shield,
  Database,
  Wifi,
  HardDrive,
  Zap,
  Search,
  Moon,
  Sun,
  Monitor,
  Bell,
  Key,
  Server,
  FolderOpen,
  Download,
  Upload,
  RefreshCw,
  Save,
  RotateCcw,
  Info,
  Check,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { MinecraftButton } from '../components/minecraft/MinecraftButton'
import { MinecraftCard } from '../components/minecraft/MinecraftCard'
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress'
import { MinecraftBlock } from '../components/MinecraftComponents'
import { MinecraftNotificationSettings } from '../components/minecraft/MinecraftNotificationSettings'
import { MinecraftThemeSwitcher } from '../components/minecraft/MinecraftThemeSwitcher'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

export default function SettingsPageMinecraft() {
  const [activeTab, setActiveTab] = useState(0)
  const [settings, setSettings] = useState({
    // 通用设置
    language: 'zh_CN',
    theme: 'auto',
    autoSave: true,
    autoBackup: true,
    backupInterval: 30,

    // 界面设置
    animations: true,
    particles: true,
    sounds: true,
    soundVolume: 70,
    notifications: true,
    fontSize: 'medium',
    compactMode: false,

    // 扫描设置
    scanDepth: 3,
    excludePatterns: '.git, node_modules, .cache',
    includeHidden: false,
    parallelScanning: true,
    cacheResults: true,
    cacheDuration: 7,

    // 网络设置
    serverUrl: 'https://api.trans-hub.com',
    apiKey: '',
    proxyEnabled: false,
    proxyUrl: '',
    connectionTimeout: 30,
    retryAttempts: 3,

    // 性能设置
    maxThreads: 4,
    memoryLimit: 2048,
    chunkSize: 100,
    enableGPU: false,

    // 存储设置
    dataPath: 'C:/Users/Admin/AppData/Local/TH-Suite',
    tempPath: 'C:/Users/Admin/AppData/Local/Temp/TH-Suite',
    maxCacheSize: 1024,
    autoCleanup: true,
  })

  const [unsavedChanges, setUnsavedChanges] = useState(false)

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setUnsavedChanges(true)
  }

  const handleSaveSettings = () => {
    // 模拟保存设置
    setTimeout(() => {
      setUnsavedChanges(false)
      toast.success('设置已保存', { icon: '💾' })
    }, 500)
  }

  const handleResetSettings = () => {
    toast.success('设置已重置为默认值', { icon: '🔄' })
    setUnsavedChanges(false)
  }

  const handleClearCache = () => {
    toast.success('缓存已清理', { icon: '🧹' })
  }

  const handleExportSettings = () => {
    toast.success('设置已导出', { icon: '📤' })
  }

  const handleImportSettings = () => {
    toast.info('选择设置文件...', { icon: '📥' })
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
              background: 'linear-gradient(135deg, #9C27B0 0%, #673AB7 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              mb: 1,
            }}
          >
            ⚙️ 设置
          </Typography>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '14px',
              color: 'text.secondary',
            }}
          >
            配置应用偏好和系统参数
          </Typography>
        </Box>
      </motion.div>

      {/* 未保存提示 */}
      {unsavedChanges && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <Alert
            severity='warning'
            sx={{
              mb: 3,
              fontFamily: '"Minecraft", monospace',
              fontSize: '12px',
              background: 'linear-gradient(135deg, rgba(255,152,0,0.2) 0%, rgba(0,0,0,0.2) 100%)',
              border: '2px solid #FF9800',
              borderRadius: 0,
            }}
            action={
              <MinecraftButton minecraftStyle='emerald' size='small' onClick={handleSaveSettings}>
                保存
              </MinecraftButton>
            }
          >
            您有未保存的更改
          </Alert>
        </motion.div>
      )}

      {/* 标签页 */}
      <MinecraftCard variant='inventory'>
        <Tabs
          value={activeTab}
          onChange={(e, v) => setActiveTab(v)}
          sx={{
            borderBottom: '2px solid #4A4A4A',
            '& .MuiTab-root': {
              fontFamily: '"Minecraft", monospace',
              fontSize: '12px',
              textTransform: 'none',
              minHeight: 48,
              color: 'text.secondary',
              '&.Mui-selected': {
                color: '#00BCD4',
              },
            },
            '& .MuiTabs-indicator': {
              backgroundColor: '#00BCD4',
              height: 3,
            },
          }}
        >
          <Tab icon={<Settings size={16} />} iconPosition='start' label='通用' />
          <Tab icon={<Palette size={16} />} iconPosition='start' label='界面' />
          <Tab icon={<Search size={16} />} iconPosition='start' label='扫描' />
          <Tab icon={<Wifi size={16} />} iconPosition='start' label='网络' />
          <Tab icon={<Zap size={16} />} iconPosition='start' label='性能' />
          <Tab icon={<Bell size={16} />} iconPosition='start' label='通知' />
          <Tab icon={<HardDrive size={16} />} iconPosition='start' label='存储' />
        </Tabs>

        {/* 通用设置 */}
        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                  语言
                </InputLabel>
                <Select
                  value={settings.language}
                  onChange={e => handleSettingChange('language', e.target.value)}
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  }}
                >
                  <MenuItem value='zh_CN'>简体中文</MenuItem>
                  <MenuItem value='zh_TW'>繁體中文</MenuItem>
                  <MenuItem value='en_US'>English</MenuItem>
                  <MenuItem value='ja_JP'>日本語</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                  主题
                </InputLabel>
                <Select
                  value={settings.theme}
                  onChange={e => handleSettingChange('theme', e.target.value)}
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  }}
                >
                  <MenuItem value='auto'>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Monitor size={16} /> 跟随系统
                    </Box>
                  </MenuItem>
                  <MenuItem value='light'>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Sun size={16} /> 浅色
                    </Box>
                  </MenuItem>
                  <MenuItem value='dark'>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Moon size={16} /> 深色
                    </Box>
                  </MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoSave}
                    onChange={e => handleSettingChange('autoSave', e.target.checked)}
                    sx={{ '& .MuiSwitch-thumb': { boxShadow: 'none' } }}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    自动保存
                  </Typography>
                }
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoBackup}
                    onChange={e => handleSettingChange('autoBackup', e.target.checked)}
                    sx={{ '& .MuiSwitch-thumb': { boxShadow: 'none' } }}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    自动备份
                  </Typography>
                }
              />
            </Grid>
            {settings.autoBackup && (
              <Grid item xs={12}>
                <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                  备份间隔（分钟）
                </Typography>
                <Slider
                  value={settings.backupInterval}
                  onChange={(e, v) => handleSettingChange('backupInterval', v)}
                  min={5}
                  max={120}
                  step={5}
                  marks
                  valueLabelDisplay='auto'
                  sx={{
                    '& .MuiSlider-thumb': {
                      borderRadius: 0,
                      width: 16,
                      height: 16,
                    },
                    '& .MuiSlider-rail': {
                      borderRadius: 0,
                    },
                    '& .MuiSlider-track': {
                      borderRadius: 0,
                    },
                  }}
                />
              </Grid>
            )}
          </Grid>
        </TabPanel>

        {/* 界面设置 - 使用主题切换器 */}
        <TabPanel value={activeTab} index={1}>
          <MinecraftThemeSwitcher />
        </TabPanel>

        {/* 旧的界面设置（已替换） */}
        {false && (
          <TabPanel value={activeTab} index={-1}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.animations}
                      onChange={e => handleSettingChange('animations', e.target.checked)}
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                      启用动画
                    </Typography>
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.particles}
                      onChange={e => handleSettingChange('particles', e.target.checked)}
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                      粒子效果
                    </Typography>
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.sounds}
                      onChange={e => handleSettingChange('sounds', e.target.checked)}
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                      音效
                    </Typography>
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications}
                      onChange={e => handleSettingChange('notifications', e.target.checked)}
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                      通知提醒
                    </Typography>
                  }
                />
              </Grid>
              {settings.sounds && (
                <Grid item xs={12}>
                  <Typography
                    sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}
                  >
                    音量
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Volume2 size={20} />
                    <Slider
                      value={settings.soundVolume}
                      onChange={(e, v) => handleSettingChange('soundVolume', v)}
                      min={0}
                      max={100}
                      valueLabelDisplay='auto'
                      sx={{
                        flex: 1,
                        '& .MuiSlider-thumb': {
                          borderRadius: 0,
                          width: 16,
                          height: 16,
                        },
                      }}
                    />
                  </Box>
                </Grid>
              )}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
              </Grid>
              <Grid item xs={12}>
                <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 2 }}>
                  字体大小
                </Typography>
                <RadioGroup
                  row
                  value={settings.fontSize}
                  onChange={e => handleSettingChange('fontSize', e.target.value)}
                >
                  <FormControlLabel
                    value='small'
                    control={<Radio size='small' />}
                    label={
                      <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                        小
                      </Typography>
                    }
                  />
                  <FormControlLabel
                    value='medium'
                    control={<Radio size='small' />}
                    label={
                      <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                        中
                      </Typography>
                    }
                  />
                  <FormControlLabel
                    value='large'
                    control={<Radio size='small' />}
                    label={
                      <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '16px' }}>
                        大
                      </Typography>
                    }
                  />
                </RadioGroup>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.compactMode}
                      onChange={e => handleSettingChange('compactMode', e.target.checked)}
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                      紧凑模式
                    </Typography>
                  }
                />
              </Grid>
            </Grid>
          </TabPanel>
        )}

        {/* 扫描设置 */}
        <TabPanel value={activeTab} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                扫描深度
              </Typography>
              <Slider
                value={settings.scanDepth}
                onChange={(e, v) => handleSettingChange('scanDepth', v)}
                min={1}
                max={10}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                缓存时长（天）
              </Typography>
              <Slider
                value={settings.cacheDuration}
                onChange={(e, v) => handleSettingChange('cacheDuration', v)}
                min={1}
                max={30}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='排除模式'
                value={settings.excludePatterns}
                onChange={e => handleSettingChange('excludePatterns', e.target.value)}
                helperText='使用逗号分隔多个模式'
                InputLabelProps={{
                  sx: { fontFamily: '"Minecraft", monospace', fontSize: '12px' },
                }}
                InputProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  },
                }}
                FormHelperTextProps={{
                  sx: { fontFamily: '"Minecraft", monospace', fontSize: '10px' },
                }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.includeHidden}
                    onChange={e => handleSettingChange('includeHidden', e.target.checked)}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    包含隐藏文件
                  </Typography>
                }
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.parallelScanning}
                    onChange={e => handleSettingChange('parallelScanning', e.target.checked)}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    并行扫描
                  </Typography>
                }
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.cacheResults}
                    onChange={e => handleSettingChange('cacheResults', e.target.checked)}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    缓存结果
                  </Typography>
                }
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* 网络设置 */}
        <TabPanel value={activeTab} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='服务器地址'
                value={settings.serverUrl}
                onChange={e => handleSettingChange('serverUrl', e.target.value)}
                InputLabelProps={{
                  sx: { fontFamily: '"Minecraft", monospace', fontSize: '12px' },
                }}
                InputProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  },
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='API 密钥'
                type='password'
                value={settings.apiKey}
                onChange={e => handleSettingChange('apiKey', e.target.value)}
                InputLabelProps={{
                  sx: { fontFamily: '"Minecraft", monospace', fontSize: '12px' },
                }}
                InputProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': { borderRadius: 0, borderWidth: 2 },
                  },
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.proxyEnabled}
                    onChange={e => handleSettingChange('proxyEnabled', e.target.checked)}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    使用代理
                  </Typography>
                }
              />
            </Grid>
            {settings.proxyEnabled && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label='代理地址'
                  value={settings.proxyUrl}
                  onChange={e => handleSettingChange('proxyUrl', e.target.value)}
                  InputLabelProps={{
                    sx: { fontFamily: '"Minecraft", monospace', fontSize: '12px' },
                  }}
                  InputProps={{
                    sx: {
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '14px',
                      '& fieldset': { borderRadius: 0, borderWidth: 2 },
                    },
                  }}
                />
              </Grid>
            )}
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                连接超时（秒）
              </Typography>
              <Slider
                value={settings.connectionTimeout}
                onChange={(e, v) => handleSettingChange('connectionTimeout', v)}
                min={5}
                max={120}
                step={5}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                重试次数
              </Typography>
              <Slider
                value={settings.retryAttempts}
                onChange={(e, v) => handleSettingChange('retryAttempts', v)}
                min={0}
                max={10}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <MinecraftButton
                minecraftStyle='diamond'
                onClick={() => toast.success('连接测试成功', { icon: '✅' })}
                startIcon={<Wifi size={16} />}
              >
                测试连接
              </MinecraftButton>
            </Grid>
          </Grid>
        </TabPanel>

        {/* 性能设置 */}
        <TabPanel value={activeTab} index={4}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                最大线程数
              </Typography>
              <Slider
                value={settings.maxThreads}
                onChange={(e, v) => handleSettingChange('maxThreads', v)}
                min={1}
                max={16}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                内存限制（MB）
              </Typography>
              <Slider
                value={settings.memoryLimit}
                onChange={(e, v) => handleSettingChange('memoryLimit', v)}
                min={512}
                max={8192}
                step={512}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                批处理大小
              </Typography>
              <Slider
                value={settings.chunkSize}
                onChange={(e, v) => handleSettingChange('chunkSize', v)}
                min={10}
                max={1000}
                step={10}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enableGPU}
                    onChange={e => handleSettingChange('enableGPU', e.target.checked)}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    启用 GPU 加速
                  </Typography>
                }
              />
            </Grid>
            <Grid item xs={12}>
              <MinecraftCard variant='enchantment'>
                <Box sx={{ p: 2 }}>
                  <Typography
                    sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px', mb: 2 }}
                  >
                    系统信息
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '12px',
                          color: 'text.secondary',
                        }}
                      >
                        CPU: Intel Core i7-10700K
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '12px',
                          color: 'text.secondary',
                        }}
                      >
                        内存: 16GB DDR4
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '12px',
                          color: 'text.secondary',
                        }}
                      >
                        GPU: NVIDIA RTX 3070
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '12px',
                          color: 'text.secondary',
                        }}
                      >
                        存储: 512GB SSD
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              </MinecraftCard>
            </Grid>
          </Grid>
        </TabPanel>

        {/* 存储设置 */}
        <TabPanel value={activeTab} index={5}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='数据存储路径'
                value={settings.dataPath}
                onChange={e => handleSettingChange('dataPath', e.target.value)}
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
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='临时文件路径'
                value={settings.tempPath}
                onChange={e => handleSettingChange('tempPath', e.target.value)}
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
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px', mb: 1 }}>
                最大缓存大小（MB）
              </Typography>
              <Slider
                value={settings.maxCacheSize}
                onChange={(e, v) => handleSettingChange('maxCacheSize', v)}
                min={100}
                max={10240}
                step={100}
                marks
                valueLabelDisplay='auto'
                sx={{
                  '& .MuiSlider-thumb': {
                    borderRadius: 0,
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoCleanup}
                    onChange={e => handleSettingChange('autoCleanup', e.target.checked)}
                  />
                }
                label={
                  <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px' }}>
                    自动清理
                  </Typography>
                }
              />
            </Grid>
            <Grid item xs={12}>
              <MinecraftCard variant='chest'>
                <Box sx={{ p: 2 }}>
                  <Typography
                    sx={{ fontFamily: '"Minecraft", monospace', fontSize: '14px', mb: 2 }}
                  >
                    存储使用情况
                  </Typography>
                  <MinecraftProgress
                    value={3.2}
                    max={10}
                    variant='loading'
                    label='缓存使用'
                    size='medium'
                  />
                  <Box sx={{ mt: 2 }}>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '12px',
                        color: 'text.secondary',
                      }}
                    >
                      已使用: 3.2 GB / 10 GB
                    </Typography>
                  </Box>
                  <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                    <MinecraftButton
                      minecraftStyle='redstone'
                      size='small'
                      onClick={handleClearCache}
                    >
                      清理缓存
                    </MinecraftButton>
                    <MinecraftButton
                      minecraftStyle='iron'
                      size='small'
                      onClick={() => toast.info('打开文件夹...')}
                    >
                      打开文件夹
                    </MinecraftButton>
                  </Box>
                </Box>
              </MinecraftCard>
            </Grid>
          </Grid>
        </TabPanel>

        {/* 通知设置 */}
        <TabPanel value={activeTab} index={6}>
          <MinecraftNotificationSettings />
        </TabPanel>
      </MinecraftCard>

      {/* 操作按钮 */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <MinecraftButton
            minecraftStyle='iron'
            onClick={handleExportSettings}
            startIcon={<Download size={16} />}
          >
            导出设置
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle='iron'
            onClick={handleImportSettings}
            startIcon={<Upload size={16} />}
          >
            导入设置
          </MinecraftButton>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <MinecraftButton
            minecraftStyle='redstone'
            onClick={handleResetSettings}
            startIcon={<RotateCcw size={16} />}
          >
            重置默认
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle='emerald'
            onClick={handleSaveSettings}
            startIcon={<Save size={16} />}
            glowing={unsavedChanges}
          >
            保存设置
          </MinecraftButton>
        </Box>
      </Box>
    </Box>
  )
}
