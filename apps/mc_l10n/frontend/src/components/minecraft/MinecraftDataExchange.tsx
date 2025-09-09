import React, { useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Checkbox,
  FormControlLabel,
  FormGroup,
  TextField,
  LinearProgress,
  Alert,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  Tooltip,
} from '@mui/material'
import {
  Download,
  Upload,
  Save,
  FolderOpen,
  FileJson,
  FileArchive,
  FileText,
  Shield,
  Clock,
  CheckCircle,
  AlertCircle,
  Info,
  Trash2,
  RefreshCw,
  Archive,
  Database,
  Settings,
  Package,
  Key,
  Copy,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { MinecraftCard } from './MinecraftCard'
import { MinecraftButton } from './MinecraftButton'
import { MinecraftProgress } from './MinecraftProgress'
import {
  importExportService,
  ExportOptions,
  ImportResult,
} from '../../services/importExportService'
import { useNotification } from '../../hooks/useNotification'
import { minecraftColors } from '../../theme/minecraftTheme'

interface BackupItem {
  name: string
  date: string
  size: number
  type: 'auto' | 'manual'
}

export const MinecraftDataExchange: React.FC = () => {
  const notification = useNotification()
  const [activeTab, setActiveTab] = useState<'export' | 'import' | 'backup'>('export')
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)

  // 导出选项
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    includeProjects: true,
    includeTranslations: true,
    includeSettings: true,
    includeCache: false,
    compressed: true,
    encrypted: false,
    format: 'thdata',
  })
  const [exportPassword, setExportPassword] = useState('')

  // 导入状态
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importPassword, setImportPassword] = useState('')

  // 备份列表
  const [backups, setBackups] = useState<BackupItem[]>([
    { name: 'auto-backup-20240302', date: '2024-03-02 14:30', size: 2048576, type: 'auto' },
    { name: 'manual-backup-20240301', date: '2024-03-01 10:15', size: 1536000, type: 'manual' },
    { name: 'auto-backup-20240228', date: '2024-02-28 14:30', size: 1892352, type: 'auto' },
  ])

  const [selectedBackup, setSelectedBackup] = useState<string | null>(null)
  const [passwordDialog, setPasswordDialog] = useState(false)
  const [tempPassword, setTempPassword] = useState('')

  // 处理导出
  const handleExport = async () => {
    setIsProcessing(true)
    setProgress(0)

    try {
      // 模拟进度
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      await importExportService.exportData({
        ...exportOptions,
        password: exportOptions.encrypted ? exportPassword : undefined,
      })

      clearInterval(progressInterval)
      setProgress(100)

      notification.success('导出成功', '数据已成功导出到文件')
    } catch (error) {
      notification.error('导出失败', error instanceof Error ? error.message : '未知错误')
    } finally {
      setIsProcessing(false)
      setTimeout(() => setProgress(0), 1000)
    }
  }

  // 处理导入
  const handleImport = async () => {
    setIsProcessing(true)
    setProgress(0)

    try {
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const result = await importExportService.importData({
        overwrite: false,
        merge: true,
        validateSchema: true,
        password: importPassword || undefined,
      })

      clearInterval(progressInterval)
      setProgress(100)
      setImportResult(result)

      if (result.success) {
        notification.achievement(
          '导入成功',
          `成功导入 ${result.imported.projects} 个项目和 ${result.imported.translations} 条翻译`,
        )
      } else {
        notification.error('导入失败', result.errors.join(', '))
      }
    } catch (error) {
      notification.error('导入失败', error instanceof Error ? error.message : '未知错误')
    } finally {
      setIsProcessing(false)
      setTimeout(() => setProgress(0), 1000)
    }
  }

  // 创建备份
  const handleCreateBackup = async () => {
    setIsProcessing(true)

    try {
      const backupName = await importExportService.createBackup()

      // 更新备份列表
      const newBackup: BackupItem = {
        name: backupName,
        date: new Date().toLocaleString(),
        size: Math.floor(Math.random() * 3000000),
        type: 'manual',
      }

      setBackups([newBackup, ...backups])
      notification.success('备份成功', `备份 "${backupName}" 已创建`)
    } catch (error) {
      notification.error('备份失败', error instanceof Error ? error.message : '未知错误')
    } finally {
      setIsProcessing(false)
    }
  }

  // 恢复备份
  const handleRestoreBackup = async (backupName: string) => {
    if (!backupName) return

    setIsProcessing(true)

    try {
      await importExportService.restoreBackup(backupName)
      notification.success('恢复成功', `备份 "${backupName}" 已恢复`)
    } catch (error) {
      notification.error('恢复失败', error instanceof Error ? error.message : '未知错误')
    } finally {
      setIsProcessing(false)
    }
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <Box>
      {/* 标题和选项卡 */}
      <Box sx={{ mb: 3 }}>
        <Typography
          variant='h5'
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: minecraftColors.goldYellow,
            mb: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Archive size={24} />
          数据管理
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <MinecraftButton
            minecraftStyle={activeTab === 'export' ? 'emerald' : 'stone'}
            onClick={() => setActiveTab('export')}
            startIcon={<Download size={16} />}
          >
            导出数据
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle={activeTab === 'import' ? 'emerald' : 'stone'}
            onClick={() => setActiveTab('import')}
            startIcon={<Upload size={16} />}
          >
            导入数据
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle={activeTab === 'backup' ? 'emerald' : 'stone'}
            onClick={() => setActiveTab('backup')}
            startIcon={<Save size={16} />}
          >
            备份管理
          </MinecraftButton>
        </Box>
      </Box>

      {/* 进度条 */}
      {isProcessing && (
        <Box sx={{ mb: 2 }}>
          <MinecraftProgress value={progress} showLabel />
        </Box>
      )}

      {/* 导出面板 */}
      {activeTab === 'export' && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <MinecraftCard minecraftStyle='stone'>
              <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                导出内容
              </Typography>

              <FormGroup>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={exportOptions.includeProjects}
                      onChange={e =>
                        setExportOptions({
                          ...exportOptions,
                          includeProjects: e.target.checked,
                        })
                      }
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Package size={16} />
                      项目数据
                    </Box>
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={exportOptions.includeTranslations}
                      onChange={e =>
                        setExportOptions({
                          ...exportOptions,
                          includeTranslations: e.target.checked,
                        })
                      }
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <FileText size={16} />
                      翻译内容
                    </Box>
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={exportOptions.includeSettings}
                      onChange={e =>
                        setExportOptions({
                          ...exportOptions,
                          includeSettings: e.target.checked,
                        })
                      }
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Settings size={16} />
                      应用设置
                    </Box>
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={exportOptions.includeCache}
                      onChange={e =>
                        setExportOptions({
                          ...exportOptions,
                          includeCache: e.target.checked,
                        })
                      }
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Database size={16} />
                      缓存数据
                    </Box>
                  }
                />
              </FormGroup>
            </MinecraftCard>
          </Grid>

          <Grid item xs={12} md={6}>
            <MinecraftCard minecraftStyle='iron'>
              <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                导出选项
              </Typography>

              <FormGroup>
                <FormControlLabel
                  control={
                    <Switch
                      checked={exportOptions.compressed}
                      onChange={e =>
                        setExportOptions({
                          ...exportOptions,
                          compressed: e.target.checked,
                        })
                      }
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <FileArchive size={16} />
                      压缩文件
                    </Box>
                  }
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={exportOptions.encrypted}
                      onChange={e =>
                        setExportOptions({
                          ...exportOptions,
                          encrypted: e.target.checked,
                        })
                      }
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Shield size={16} />
                      加密保护
                    </Box>
                  }
                />

                {exportOptions.encrypted && (
                  <TextField
                    type='password'
                    label='加密密码'
                    value={exportPassword}
                    onChange={e => setExportPassword(e.target.value)}
                    fullWidth
                    sx={{ mt: 2 }}
                    InputProps={{
                      startAdornment: <Key size={16} style={{ marginRight: 8 }} />,
                    }}
                  />
                )}
              </FormGroup>

              <Box sx={{ mt: 3 }}>
                <MinecraftButton
                  fullWidth
                  minecraftStyle='emerald'
                  onClick={handleExport}
                  disabled={isProcessing}
                  startIcon={<Download size={16} />}
                >
                  导出数据
                </MinecraftButton>
              </Box>
            </MinecraftCard>
          </Grid>
        </Grid>
      )}

      {/* 导入面板 */}
      {activeTab === 'import' && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <MinecraftCard minecraftStyle='stone'>
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Upload size={48} style={{ color: minecraftColors.diamondBlue }} />
                <Typography
                  variant='h6'
                  sx={{ fontFamily: '"Minecraft", monospace', mt: 2, mb: 1 }}
                >
                  选择要导入的文件
                </Typography>
                <Typography variant='body2' color='text.secondary' sx={{ mb: 3 }}>
                  支持 .thdata, .json, .zip 格式
                </Typography>

                <MinecraftButton
                  minecraftStyle='diamond'
                  onClick={handleImport}
                  disabled={isProcessing}
                  startIcon={<FolderOpen size={16} />}
                >
                  选择文件
                </MinecraftButton>
              </Box>

              {importResult && (
                <Box sx={{ mt: 3 }}>
                  <Divider sx={{ mb: 2 }} />
                  <Alert severity={importResult.success ? 'success' : 'error'}>
                    {importResult.success ? '导入成功' : '导入失败'}
                  </Alert>

                  <Box sx={{ mt: 2 }}>
                    <Typography variant='body2'>导入统计：</Typography>
                    <List dense>
                      <ListItem>
                        <ListItemIcon>
                          <Package size={16} />
                        </ListItemIcon>
                        <ListItemText primary={`项目: ${importResult.imported.projects}`} />
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <FileText size={16} />
                        </ListItemIcon>
                        <ListItemText primary={`翻译: ${importResult.imported.translations}`} />
                      </ListItem>
                      {importResult.imported.settings && (
                        <ListItem>
                          <ListItemIcon>
                            <Settings size={16} />
                          </ListItemIcon>
                          <ListItemText primary='设置已导入' />
                        </ListItem>
                      )}
                    </List>
                  </Box>
                </Box>
              )}
            </MinecraftCard>
          </Grid>
        </Grid>
      )}

      {/* 备份管理面板 */}
      {activeTab === 'backup' && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Box
              sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace' }}>
                备份列表
              </Typography>
              <MinecraftButton
                minecraftStyle='emerald'
                onClick={handleCreateBackup}
                disabled={isProcessing}
                startIcon={<Save size={16} />}
              >
                创建备份
              </MinecraftButton>
            </Box>

            <MinecraftCard minecraftStyle='stone'>
              <List>
                {backups.map((backup, index) => (
                  <React.Fragment key={backup.name}>
                    {index > 0 && <Divider />}
                    <ListItem>
                      <ListItemIcon>
                        {backup.type === 'auto' ? (
                          <RefreshCw size={20} style={{ color: minecraftColors.iron }} />
                        ) : (
                          <Save size={20} style={{ color: minecraftColors.emerald }} />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {backup.name}
                            {backup.type === 'auto' && <Chip label='自动' size='small' />}
                          </Box>
                        }
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Clock size={12} />
                              <Typography variant='caption'>{backup.date}</Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Database size={12} />
                              <Typography variant='caption'>
                                {formatFileSize(backup.size)}
                              </Typography>
                            </Box>
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        <Tooltip title='恢复备份'>
                          <IconButton
                            onClick={() => handleRestoreBackup(backup.name)}
                            disabled={isProcessing}
                          >
                            <Upload size={18} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title='删除备份'>
                          <IconButton
                            onClick={() => {
                              setBackups(backups.filter(b => b.name !== backup.name))
                              notification.info('备份已删除')
                            }}
                            disabled={isProcessing}
                          >
                            <Trash2 size={18} />
                          </IconButton>
                        </Tooltip>
                      </ListItemSecondaryAction>
                    </ListItem>
                  </React.Fragment>
                ))}
              </List>
            </MinecraftCard>
          </Grid>
        </Grid>
      )}

      {/* 密码对话框 */}
      <Dialog open={passwordDialog} onClose={() => setPasswordDialog(false)}>
        <DialogTitle>输入密码</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin='dense'
            label='密码'
            type='password'
            fullWidth
            value={tempPassword}
            onChange={e => setTempPassword(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPasswordDialog(false)}>取消</Button>
          <Button
            onClick={() => {
              setImportPassword(tempPassword)
              setPasswordDialog(false)
              handleImport()
            }}
          >
            确认
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
