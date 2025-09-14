/**
 * 补丁管理器组件
 * 用于下载和应用 Trans-Hub 的翻译补丁
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  LinearProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  Badge,
  Divider,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import {
  Download,
  Upload,
  CheckCircle,
  AlertCircle,
  Package,
  FileText,
  Clock,
  Layers,
  Archive,
  RefreshCw,
  Info,
  Trash2,
  Eye,
  Play,
  FolderOpen,
  Check,
  X,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTransHub } from '../hooks/useTransHub'
import { useNotification } from '../hooks/useNotification'
import { MinecraftCard } from './minecraft/MinecraftCard'
import { MinecraftButton } from './minecraft/MinecraftButton'
import { MinecraftProgress } from './minecraft/MinecraftProgress'
import { minecraftColors } from '../theme/minecraftTheme'
import { UploadProgress } from './UploadProgress'
import {
  transHubService,
  type UploadProgress as UploadProgressType,
} from '../services/transhubService'

interface PatchInfo {
  id: string
  version: string
  projectId: string
  projectName: string
  language: string
  entries: number
  size: number
  createdAt: string
  author?: string
  description?: string
  applied?: boolean
  downloadProgress?: number
}

interface PatchManagerProps {
  projectId?: string
  onPatchApplied?: (patchId: string) => void
}

export const PatchManager: React.FC<PatchManagerProps> = ({ projectId, onPatchApplied }) => {
  const [patches, setPatches] = useState<PatchInfo[]>([])
  const [selectedPatch, setSelectedPatch] = useState<PatchInfo | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [applyStrategy, setApplyStrategy] = useState<'overlay' | 'jar_inplace'>('overlay')
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [applyDialogOpen, setApplyDialogOpen] = useState(false)
  const [targetPath, setTargetPath] = useState('')
  const [createBackup, setCreateBackup] = useState(true)
  const [downloadProgress, setDownloadProgress] = useState<UploadProgressType | null>(null)
  const [selectedPatches, setSelectedPatches] = useState<string[]>([])
  const [batchMode, setBatchMode] = useState(false)

  const { isConnected, downloadPatches } = useTransHub()
  const notification = useNotification()

  // 获取可用补丁列表
  const fetchPatches = async () => {
    if (!isConnected) {
      notification.warning('未连接', '请先连接到 Trans-Hub 服务器')
      return
    }

    try {
      const patchList = await downloadPatches(projectId || 'all')

      // 模拟补丁数据（实际应该从服务器获取）
      const mockPatches: PatchInfo[] = [
        {
          id: 'patch_001',
          version: '1.0.0',
          projectId: 'minecraft_mods',
          projectName: 'Minecraft Mods Pack',
          language: 'zh_CN',
          entries: 1234,
          size: 2048000,
          createdAt: new Date().toISOString(),
          author: 'TransHub Team',
          description: '包含主流模组的完整中文翻译',
          applied: false,
        },
        {
          id: 'patch_002',
          version: '1.0.1',
          projectId: 'twilight_forest',
          projectName: 'Twilight Forest',
          language: 'zh_CN',
          entries: 567,
          size: 512000,
          createdAt: new Date(Date.now() - 86400000).toISOString(),
          author: 'Community',
          description: '暮色森林模组汉化更新',
          applied: true,
        },
        {
          id: 'patch_003',
          version: '2.0.0',
          projectId: 'industrial_craft',
          projectName: 'Industrial Craft 2',
          language: 'zh_CN',
          entries: 890,
          size: 1024000,
          createdAt: new Date(Date.now() - 172800000).toISOString(),
          author: 'IC2 Team',
          description: '工业2模组完整汉化',
          applied: false,
        },
      ]

      setPatches(mockPatches)
      notification.success('获取成功', `发现 ${mockPatches.length} 个可用补丁`)
    } catch (error) {
      console.error('Failed to fetch patches:', error)
      notification.error('获取失败', '无法获取补丁列表')
    }
  }

  // 下载补丁
  const handleDownloadPatch = async (patch: PatchInfo) => {
    setIsDownloading(true)

    // 设置下载进度
    setDownloadProgress({
      totalChunks: 1,
      completedChunks: 0,
      currentChunk: 1,
      percentage: 0,
      bytesUploaded: 0,
      totalBytes: patch.size,
      speed: 0,
      remainingTime: 0,
      status: 'preparing',
    })

    try {
      const startTime = Date.now()
      let downloadedBytes = 0

      // 模拟下载过程（实际应该调用API）
      for (let i = 0; i <= 100; i += 5) {
        downloadedBytes = (patch.size * i) / 100
        const elapsed = (Date.now() - startTime) / 1000
        const speed = elapsed > 0 ? downloadedBytes / elapsed : 0
        const remainingBytes = patch.size - downloadedBytes
        const remainingTime = speed > 0 ? remainingBytes / speed : 0

        setDownloadProgress({
          totalChunks: 1,
          completedChunks: 0,
          currentChunk: 1,
          percentage: i,
          bytesUploaded: downloadedBytes,
          totalBytes: patch.size,
          speed,
          remainingTime,
          status: i === 100 ? 'completed' : 'uploading',
        })

        // 更新补丁的下载进度
        setPatches(prev => prev.map(p => (p.id === patch.id ? { ...p, downloadProgress: i } : p)))

        await new Promise(resolve => setTimeout(resolve, 100))
      }

      notification.success('下载完成', `补丁 ${patch.projectName} 已下载`)

      // 清除下载进度
      setTimeout(() => {
        setDownloadProgress(null)
        // 打开应用对话框
        setSelectedPatch(patch)
        setApplyDialogOpen(true)
      }, 1000)
    } catch (error) {
      setDownloadProgress({
        totalChunks: 1,
        completedChunks: 0,
        currentChunk: 1,
        percentage: 0,
        bytesUploaded: 0,
        totalBytes: patch.size,
        speed: 0,
        remainingTime: 0,
        status: 'failed',
        error: '下载失败',
      })
      notification.error('下载失败', '无法下载补丁文件')
    } finally {
      setIsDownloading(false)
    }
  }

  // 批量下载补丁
  const handleBatchDownload = async () => {
    if (selectedPatches.length === 0) {
      notification.warning('未选择', '请选择要下载的补丁')
      return
    }

    const patchesToDownload = patches.filter(p => selectedPatches.includes(p.id))

    for (const patch of patchesToDownload) {
      await handleDownloadPatch(patch)
    }

    setSelectedPatches([])
    setBatchMode(false)
  }

  // 切换选择状态
  const togglePatchSelection = (patchId: string) => {
    setSelectedPatches(prev =>
      prev.includes(patchId) ? prev.filter(id => id !== patchId) : [...prev, patchId],
    )
  }

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedPatches.length === patches.length) {
      setSelectedPatches([])
    } else {
      setSelectedPatches(patches.map(p => p.id))
    }
  }

  // 应用补丁
  const handleApplyPatch = async () => {
    if (!selectedPatch || !targetPath) {
      notification.warning('缺少参数', '请选择目标路径')
      return
    }

    setIsApplying(true)

    try {
      // 这里应该调用实际的应用补丁API
      // await applyPatch(selectedPatch.id, targetPath, applyStrategy, createBackup);

      // 模拟应用过程
      await new Promise(resolve => setTimeout(resolve, 2000))

      // 更新补丁状态
      setPatches(prev => prev.map(p => (p.id === selectedPatch.id ? { ...p, applied: true } : p)))

      notification.achievement('应用成功！', `${selectedPatch.projectName} 的翻译已成功应用`, {
        minecraft: { block: 'emerald', particle: true },
      })

      if (onPatchApplied) {
        onPatchApplied(selectedPatch.id)
      }

      setApplyDialogOpen(false)
      setSelectedPatch(null)
    } catch (error) {
      notification.error('应用失败', '无法应用补丁到目标位置')
    } finally {
      setIsApplying(false)
    }
  }

  // 查看补丁详情
  const handleViewDetails = (patch: PatchInfo) => {
    setSelectedPatch(patch)
    setDetailsOpen(true)
  }

  // 格式化文件大小
  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 格式化时间
  const formatTime = (isoString: string): string => {
    const date = new Date(isoString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 7) return `${days} 天前`
    if (days < 30) return `${Math.floor(days / 7)} 周前`
    return date.toLocaleDateString()
  }

  useEffect(() => {
    if (isConnected) {
      fetchPatches()
    }
  }, [isConnected, projectId])

  return (
    <Box>
      {/* 下载进度 */}
      {downloadProgress && (
        <Box sx={{ mb: 3 }}>
          <UploadProgress
            progress={downloadProgress}
            onCancel={() => setDownloadProgress(null)}
            onRetry={() => {
              if (selectedPatch) {
                handleDownloadPatch(selectedPatch)
              }
            }}
            compact={true}
          />
        </Box>
      )}

      {/* 工具栏 */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace' }}>
          翻译补丁管理
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {batchMode && (
            <>
              <MinecraftButton
                minecraftStyle='emerald'
                startIcon={<Download size={16} />}
                onClick={handleBatchDownload}
                disabled={selectedPatches.length === 0 || isDownloading}
              >
                下载选中 ({selectedPatches.length})
              </MinecraftButton>
              <MinecraftButton minecraftStyle='stone' onClick={toggleSelectAll}>
                {selectedPatches.length === patches.length ? '取消全选' : '全选'}
              </MinecraftButton>
            </>
          )}
          <MinecraftButton
            minecraftStyle={batchMode ? 'redstone' : 'diamond'}
            startIcon={<Layers size={16} />}
            onClick={() => {
              setBatchMode(!batchMode)
              setSelectedPatches([])
            }}
          >
            {batchMode ? '取消批量' : '批量操作'}
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle='gold'
            startIcon={<RefreshCw size={16} />}
            onClick={fetchPatches}
            disabled={!isConnected || isDownloading}
          >
            刷新列表
          </MinecraftButton>
          {!isConnected && (
            <Chip label='离线模式' color='warning' size='small' icon={<AlertCircle size={14} />} />
          )}
        </Box>
      </Box>

      {/* 补丁列表 */}
      <Grid container spacing={3}>
        {patches.length === 0 ? (
          <Grid item xs={12}>
            <Alert severity='info'>暂无可用补丁。请确保已连接到 Trans-Hub 服务器并完成扫描。</Alert>
          </Grid>
        ) : (
          patches.map(patch => (
            <Grid item xs={12} md={6} lg={4} key={patch.id}>
              <MinecraftCard variant='chest' glowing={patch.downloadProgress ? true : false}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography
                      variant='h6'
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '14px',
                      }}
                    >
                      {patch.projectName}
                    </Typography>
                    {patch.applied && (
                      <Chip
                        label='已应用'
                        size='small'
                        icon={<CheckCircle size={12} />}
                        sx={{
                          bgcolor: 'rgba(46, 175, 204, 0.2)',
                          color: minecraftColors.emerald,
                        }}
                      />
                    )}
                  </Box>

                  <Box sx={{ mb: 2 }}>
                    <Typography variant='caption' color='text.secondary'>
                      版本: {patch.version} | 语言: {patch.language}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                    <Chip
                      label={`${patch.entries} 条目`}
                      size='small'
                      icon={<FileText size={12} />}
                      variant='outlined'
                    />
                    <Chip
                      label={formatSize(patch.size)}
                      size='small'
                      icon={<Archive size={12} />}
                      variant='outlined'
                    />
                  </Box>

                  {patch.description && (
                    <Typography variant='body2' sx={{ mb: 2, color: 'text.secondary' }}>
                      {patch.description}
                    </Typography>
                  )}

                  <Box
                    sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                  >
                    <Typography variant='caption' color='text.secondary'>
                      {formatTime(patch.createdAt)}
                    </Typography>
                    {patch.author && (
                      <Typography variant='caption' color='text.secondary'>
                        by {patch.author}
                      </Typography>
                    )}
                  </Box>

                  {patch.downloadProgress !== undefined && patch.downloadProgress > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <MinecraftProgress variant='experience' value={patch.downloadProgress} />
                      <Typography variant='caption' color='text.secondary'>
                        下载中... {patch.downloadProgress}%
                      </Typography>
                    </Box>
                  )}
                </CardContent>

                <CardActions>
                  <MinecraftButton
                    size='small'
                    minecraftStyle='emerald'
                    startIcon={patch.applied ? <Check size={14} /> : <Download size={14} />}
                    onClick={() => handleDownloadPatch(patch)}
                    disabled={isDownloading || patch.applied}
                    fullWidth
                  >
                    {patch.applied ? '已应用' : '下载并应用'}
                  </MinecraftButton>
                  <IconButton size='small' onClick={() => handleViewDetails(patch)}>
                    <Eye size={16} />
                  </IconButton>
                </CardActions>
              </MinecraftCard>
            </Grid>
          ))
        )}
      </Grid>

      {/* 应用补丁对话框 */}
      <Dialog
        open={applyDialogOpen}
        onClose={() => !isApplying && setApplyDialogOpen(false)}
        maxWidth='sm'
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#0F172A',
            border: '2px solid #2A2A4E',
            borderRadius: 0,
          },
        }}
      >
        <DialogTitle sx={{ fontFamily: '"Minecraft", monospace' }}>应用翻译补丁</DialogTitle>
        <DialogContent>
          {selectedPatch && (
            <Box sx={{ mt: 2 }}>
              <Alert severity='info' sx={{ mb: 2 }}>
                即将应用 {selectedPatch.projectName} 的翻译补丁
              </Alert>

              <TextField
                fullWidth
                label='目标路径'
                value={targetPath}
                onChange={e => setTargetPath(e.target.value)}
                placeholder='选择游戏或模组目录'
                sx={{ mb: 2 }}
                InputProps={{
                  endAdornment: (
                    <IconButton edge='end'>
                      <FolderOpen size={16} />
                    </IconButton>
                  ),
                }}
              />

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>应用策略</InputLabel>
                <Select
                  value={applyStrategy}
                  label='应用策略'
                  onChange={e => setApplyStrategy(e.target.value as any)}
                >
                  <MenuItem value='overlay'>
                    <Box>
                      <Typography>覆盖资源包（推荐）</Typography>
                      <Typography variant='caption' color='text.secondary'>
                        创建独立的资源包，不修改原文件
                      </Typography>
                    </Box>
                  </MenuItem>
                  <MenuItem value='jar_inplace'>
                    <Box>
                      <Typography>直接修改</Typography>
                      <Typography variant='caption' color='text.secondary'>
                        直接修改JAR文件中的语言文件
                      </Typography>
                    </Box>
                  </MenuItem>
                </Select>
              </FormControl>

              <FormControlLabel
                control={
                  <Checkbox
                    checked={createBackup}
                    onChange={e => setCreateBackup(e.target.checked)}
                  />
                }
                label='创建备份'
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle='stone'
            onClick={() => setApplyDialogOpen(false)}
            disabled={isApplying}
          >
            取消
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle='emerald'
            startIcon={<Play size={16} />}
            onClick={handleApplyPatch}
            disabled={isApplying || !targetPath}
          >
            {isApplying ? '应用中...' : '应用补丁'}
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* 补丁详情对话框 */}
      <Dialog
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        maxWidth='md'
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#0F172A',
            border: '2px solid #2A2A4E',
            borderRadius: 0,
          },
        }}
      >
        <DialogTitle sx={{ fontFamily: '"Minecraft", monospace' }}>补丁详情</DialogTitle>
        <DialogContent>
          {selectedPatch && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant='caption' color='text.secondary'>
                    项目名称
                  </Typography>
                  <Typography>{selectedPatch.projectName}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant='caption' color='text.secondary'>
                    版本
                  </Typography>
                  <Typography>{selectedPatch.version}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant='caption' color='text.secondary'>
                    语言
                  </Typography>
                  <Typography>{selectedPatch.language}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant='caption' color='text.secondary'>
                    条目数量
                  </Typography>
                  <Typography>{selectedPatch.entries}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant='caption' color='text.secondary'>
                    文件大小
                  </Typography>
                  <Typography>{formatSize(selectedPatch.size)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant='caption' color='text.secondary'>
                    创建时间
                  </Typography>
                  <Typography>{new Date(selectedPatch.createdAt).toLocaleString()}</Typography>
                </Grid>
                {selectedPatch.author && (
                  <Grid item xs={12}>
                    <Typography variant='caption' color='text.secondary'>
                      作者
                    </Typography>
                    <Typography>{selectedPatch.author}</Typography>
                  </Grid>
                )}
                {selectedPatch.description && (
                  <Grid item xs={12}>
                    <Typography variant='caption' color='text.secondary'>
                      描述
                    </Typography>
                    <Typography>{selectedPatch.description}</Typography>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <MinecraftButton minecraftStyle='stone' onClick={() => setDetailsOpen(false)}>
            关闭
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default PatchManager
