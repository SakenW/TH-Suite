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
  Slider,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CardActions,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from '@mui/material'
import {
  Settings,
  Palette,
  Globe,
  HardDrive,
  Shield,
  Bell,
  Download,
  Upload,
  Trash2,
  FolderOpen,
  RefreshCw,
  Save,
  RotateCcw,
  Info,
  ExternalLink,
} from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppStore } from '@stores/appStore'
import { tauriService } from '@services'
import { useCommonTranslation, useMcStudioTranslation } from '@hooks/useTranslation'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role='tabpanel'
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

const SettingsPage: React.FC = () => {
  const { t: tCommon } = useCommonTranslation()
  const { t: tMc } = useMcStudioTranslation()
  const { settings, updateSettings, recentProjects, clearRecentProjects } = useAppStore()
  const [currentTab, setCurrentTab] = useState(0)
  const [tempSettings, setTempSettings] = useState(settings)
  const [showResetDialog, setShowResetDialog] = useState(false)
  const [appVersion, setAppVersion] = useState<string>('')
  const [tauriVersion, setTauriVersion] = useState<string>('')

  useEffect(() => {
    loadVersionInfo()
  }, [])

  const loadVersionInfo = async () => {
    try {
      if (tauriService.isTauri()) {
        const version = await tauriService.getVersion()
        setAppVersion(version)
        setTauriVersion('1.5.0') // Tauri 版本
      }
    } catch (error) {
      console.error('Failed to load version info:', error)
    }
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue)
  }

  const handleSettingChange = (key: keyof typeof settings, value: any) => {
    setTempSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSaveSettings = () => {
    updateSettings(tempSettings)
    toast.success('设置已保存')
  }

  const handleResetSettings = () => {
    setShowResetDialog(true)
  }

  const confirmResetSettings = () => {
    const defaultSettings = {
      theme: 'system' as const,
      language: 'zh-CN' as const,
      autoSave: true,
      autoBackup: false,
      maxRecentProjects: 10,
      defaultOutputPath: '',
      enableNotifications: true,
      enableSounds: true,
      compressionLevel: 6,
      maxConcurrentJobs: 4,
      enableTelemetry: false,
      checkUpdates: true,
    }
    setTempSettings(defaultSettings)
    updateSettings(defaultSettings)
    setShowResetDialog(false)
    toast.success('设置已重置为默认值')
  }

  const handleSelectDefaultOutputPath = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory()
      if (selectedPath) {
        handleSettingChange('defaultOutputPath', selectedPath)
      }
    } catch (error) {
      console.error('Failed to select default output path:', error)
      toast.error('选择默认输出路径失败')
    }
  }

  const handleClearRecentProjects = () => {
    clearRecentProjects()
    toast.success('最近项目列表已清空')
  }

  const handleExportSettings = async () => {
    try {
      const settingsJson = JSON.stringify(tempSettings, null, 2)
      const filePath = await tauriService.saveFile({
        defaultPath: 'mc-studio-settings.json',
        filters: [{ name: 'JSON', extensions: ['json'] }],
      })

      if (filePath) {
        await tauriService.writeTextFile(filePath, settingsJson)
        toast.success('设置已导出')
      }
    } catch (error) {
      console.error('Failed to export settings:', error)
      toast.error('导出设置失败')
    }
  }

  const handleImportSettings = async () => {
    try {
      const filePath = await tauriService.selectFile({
        filters: [{ name: 'JSON', extensions: ['json'] }],
      })

      if (filePath) {
        const settingsJson = await tauriService.readTextFile(filePath)
        const importedSettings = JSON.parse(settingsJson)
        setTempSettings(importedSettings)
        toast.success('设置已导入')
      }
    } catch (error) {
      console.error('Failed to import settings:', error)
      toast.error('导入设置失败')
    }
  }

  const handleCheckUpdates = async () => {
    try {
      // 这里应该调用更新检查 API
      toast.success('当前已是最新版本')
    } catch (error) {
      console.error('Failed to check updates:', error)
      toast.error('检查更新失败')
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1000, mx: 'auto' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography variant='h4' gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
          {tCommon('settings.title')}
        </Typography>

        <Paper sx={{ width: '100%' }}>
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            variant='scrollable'
            scrollButtons='auto'
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab icon={<Settings size={20} />} label={tCommon('settings.tabs.general')} />
            <Tab icon={<Palette size={20} />} label={tCommon('settings.tabs.appearance')} />
            <Tab icon={<HardDrive size={20} />} label={tCommon('settings.tabs.storage')} />
            <Tab icon={<Bell size={20} />} label={tCommon('settings.tabs.notifications')} />
            <Tab icon={<Shield size={20} />} label={tCommon('settings.tabs.privacy')} />
            <Tab icon={<Info size={20} />} label={tCommon('settings.tabs.about')} />
          </Tabs>

          {/* 常规设置 */}
          <TabPanel value={currentTab} index={0}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>{tCommon('settings.general.language')}</InputLabel>
                  <Select
                    value={tempSettings.language}
                    label={tCommon('settings.general.language')}
                    onChange={e => handleSettingChange('language', e.target.value)}
                  >
                    <MenuItem value='zh-CN'>简体中文</MenuItem>
                    <MenuItem value='en-US'>English</MenuItem>
                    <MenuItem value='ja-JP'>日本語</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <Box>
                  <Typography gutterBottom>
                    {tCommon('settings.general.maxConcurrentJobs')}
                  </Typography>
                  <Slider
                    value={tempSettings.maxConcurrentJobs}
                    onChange={(_, value) => handleSettingChange('maxConcurrentJobs', value)}
                    min={1}
                    max={8}
                    marks
                    valueLabelDisplay='auto'
                  />
                </Box>
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tempSettings.autoSave}
                      onChange={e => handleSettingChange('autoSave', e.target.checked)}
                    />
                  }
                  label={tCommon('settings.general.autoSave')}
                />
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tempSettings.autoBackup}
                      onChange={e => handleSettingChange('autoBackup', e.target.checked)}
                    />
                  }
                  label={tCommon('settings.general.autoBackup')}
                />
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tempSettings.checkUpdates}
                      onChange={e => handleSettingChange('checkUpdates', e.target.checked)}
                    />
                  }
                  label={tCommon('settings.general.checkUpdates')}
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* 外观设置 */}
          <TabPanel value={currentTab} index={1}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>{tCommon('settings.appearance.theme')}</InputLabel>
                  <Select
                    value={tempSettings.theme}
                    label={tCommon('settings.appearance.theme')}
                    onChange={e => handleSettingChange('theme', e.target.value)}
                  >
                    <MenuItem value='light'>{tCommon('settings.appearance.light')}</MenuItem>
                    <MenuItem value='dark'>{tCommon('settings.appearance.dark')}</MenuItem>
                    <MenuItem value='system'>{tCommon('settings.appearance.system')}</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Alert severity='info'>{tCommon('settings.appearance.themeChangeNotice')}</Alert>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 存储设置 */}
          <TabPanel value={currentTab} index={2}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <TextField
                    label={tCommon('settings.storage.defaultOutputPath')}
                    value={tempSettings.defaultOutputPath}
                    fullWidth
                    InputProps={{ readOnly: true }}
                    placeholder={tCommon('settings.storage.selectOutputPath')}
                  />
                  <Button
                    variant='outlined'
                    onClick={handleSelectDefaultOutputPath}
                    startIcon={<FolderOpen size={16} />}
                  >
                    {tCommon('settings.storage.select')}
                  </Button>
                </Box>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  label={tCommon('settings.storage.maxRecentProjects')}
                  type='number'
                  value={tempSettings.maxRecentProjects}
                  onChange={e => handleSettingChange('maxRecentProjects', parseInt(e.target.value))}
                  inputProps={{ min: 1, max: 50 }}
                  fullWidth
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Box>
                  <Typography gutterBottom>
                    {tCommon('settings.storage.compressionLevel')}
                  </Typography>
                  <Slider
                    value={tempSettings.compressionLevel}
                    onChange={(_, value) => handleSettingChange('compressionLevel', value)}
                    min={0}
                    max={9}
                    marks
                    valueLabelDisplay='auto'
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant='caption'>快速</Typography>
                    <Typography variant='caption'>最佳</Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Card variant='outlined'>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      {tCommon('settings.storage.recentProjects')}
                    </Typography>
                    <Typography variant='body2' color='text.secondary' gutterBottom>
                      {tCommon('settings.storage.currentRecentProjects', {
                        count: recentProjects.length,
                      })}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button
                      startIcon={<Trash2 size={16} />}
                      onClick={handleClearRecentProjects}
                      color='error'
                    >
                      {tCommon('settings.storage.clearRecentProjects')}
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 通知设置 */}
          <TabPanel value={currentTab} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tempSettings.enableNotifications}
                      onChange={e => handleSettingChange('enableNotifications', e.target.checked)}
                    />
                  }
                  label={tCommon('settings.notifications.enable')}
                />
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tempSettings.enableSounds}
                      onChange={e => handleSettingChange('enableSounds', e.target.checked)}
                    />
                  }
                  label={tCommon('settings.notifications.enableSounds')}
                />
              </Grid>

              <Grid item xs={12}>
                <Alert severity='info'>{tCommon('settings.notifications.permissionNotice')}</Alert>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 隐私设置 */}
          <TabPanel value={currentTab} index={4}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tempSettings.enableTelemetry}
                      onChange={e => handleSettingChange('enableTelemetry', e.target.checked)}
                    />
                  }
                  label={tCommon('settings.privacy.enableTelemetry')}
                />
              </Grid>

              <Grid item xs={12}>
                <Alert severity='info'>{tCommon('settings.privacy.telemetryNotice')}</Alert>
              </Grid>

              <Grid item xs={12}>
                <Card variant='outlined'>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      {tCommon('settings.privacy.dataManagement')}
                    </Typography>
                    <Typography variant='body2' color='text.secondary' gutterBottom>
                      {tCommon('settings.privacy.dataManagementDesc')}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button startIcon={<Download size={16} />} onClick={handleExportSettings}>
                      {tCommon('settings.privacy.exportSettings')}
                    </Button>
                    <Button startIcon={<Upload size={16} />} onClick={handleImportSettings}>
                      {tCommon('settings.privacy.importSettings')}
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 关于 */}
          <TabPanel value={currentTab} index={5}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      MC Studio
                    </Typography>
                    <Typography variant='body2' color='text.secondary' gutterBottom>
                      {tCommon('settings.about.appDescription')}
                    </Typography>
                    <Box sx={{ mt: 2, mb: 2 }}>
                      <Chip
                        label={`${tCommon('settings.about.version')} ${appVersion || '1.0.0'}`}
                        size='small'
                        sx={{ mr: 1 }}
                      />
                      <Chip label={`Tauri ${tauriVersion}`} size='small' variant='outlined' />
                    </Box>
                    <Typography variant='body2' color='text.secondary' sx={{ mt: 1 }}>
                      <strong>{tCommon('settings.about.author')}:</strong>{' '}
                      {tCommon('settings.about.authorName')}
                    </Typography>
                    <Typography variant='body2' color='text.secondary' sx={{ mt: 1 }}>
                      <strong>{tCommon('settings.about.website')}:</strong>{' '}
                      {tCommon('settings.about.websiteUrl')}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button startIcon={<RefreshCw size={16} />} onClick={handleCheckUpdates}>
                      {tCommon('settings.about.checkUpdates')}
                    </Button>
                    <Button
                      startIcon={<ExternalLink size={16} />}
                      onClick={() => tauriService.openUrl('https://trans-hub.net')}
                    >
                      {tCommon('settings.about.website')}
                    </Button>
                    <Button
                      startIcon={<ExternalLink size={16} />}
                      onClick={() => tauriService.openUrl('https://github.com/Saken/th-tools')}
                    >
                      GitHub
                    </Button>
                  </CardActions>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      {tCommon('settings.about.techStack')}
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary={tCommon('settings.about.frontend')}
                          secondary='React + TypeScript + Vite'
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary={tCommon('settings.about.uiFramework')}
                          secondary='Material-UI + Framer Motion'
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary={tCommon('settings.about.desktopFramework')}
                          secondary='Tauri'
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary={tCommon('settings.about.backend')}
                          secondary='FastAPI + Python'
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      {tCommon('settings.about.contact')}
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary={tCommon('settings.about.discord')}
                          secondary={tCommon('settings.about.discordPlaceholder')}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary='QQ群' secondary='即将开放' />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary='Telegram' secondary='即将开放' />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12}>
                <Alert severity='info'>{tCommon('settings.about.thankYou')}</Alert>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 操作按钮 */}
          <Box
            sx={{
              p: 3,
              borderTop: 1,
              borderColor: 'divider',
              display: 'flex',
              gap: 2,
              justifyContent: 'flex-end',
            }}
          >
            <Button
              variant='outlined'
              startIcon={<RotateCcw size={16} />}
              onClick={handleResetSettings}
            >
              {tCommon('settings.actions.resetToDefault')}
            </Button>
            <Button variant='contained' startIcon={<Save size={16} />} onClick={handleSaveSettings}>
              {tCommon('settings.actions.saveSettings')}
            </Button>
          </Box>
        </Paper>

        {/* 重置确认对话框 */}
        <Dialog open={showResetDialog} onClose={() => setShowResetDialog(false)}>
          <DialogTitle>{tCommon('settings.messages.resetTitle')}</DialogTitle>
          <DialogContent>
            <Typography>{tCommon('settings.messages.resetConfirm')}</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowResetDialog(false)}>{tCommon('common.cancel')}</Button>
            <Button onClick={confirmResetSettings} color='error' variant='contained'>
              {tCommon('settings.actions.reset')}
            </Button>
          </DialogActions>
        </Dialog>
      </motion.div>
    </Box>
  )
}

export default SettingsPage
