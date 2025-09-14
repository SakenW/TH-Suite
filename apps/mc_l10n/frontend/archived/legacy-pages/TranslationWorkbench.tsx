/**
 * 翻译工作台页面
 * 重构后的翻译管理界面，使用新的 API 架构
 */

import React, { useState, useCallback, useMemo } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  InputAdornment,
  Chip,
  Stack,
  IconButton,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  LinearProgress,
  Pagination,
} from '@mui/material'
import { useTheme, alpha } from '@mui/material/styles'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Filter,
  Download,
  Upload,
  FileText,
  Globe,
  CheckCircle,
  Clock,
  AlertCircle,
  Zap,
  BarChart3,
  Settings,
} from 'lucide-react'
import { TranslationTable } from '../components/Translation/TranslationTable'
import { TranslationEntry, TranslationSearchParams, Project } from '../types/api'
import { usePaginatedApi, useApi, useAsyncTask } from '../hooks/useApi'
import { translationService, projectService } from '../services'
import { createSearchParams } from '../services'
import toast from 'react-hot-toast'

const LANGUAGE_OPTIONS = [
  { value: '', label: '全部语言' },
  { value: 'zh_cn', label: '简体中文' },
  { value: 'zh_tw', label: '繁体中文' },
  { value: 'en_us', label: 'English (US)' },
  { value: 'ja_jp', label: '日本語' },
  { value: 'ko_kr', label: '한국어' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'untranslated', label: '未翻译', color: '#9E9E9E' },
  { value: 'translated', label: '已翻译', color: '#4CAF50' },
  { value: 'reviewed', label: '已审核', color: '#2196F3' },
  { value: 'approved', label: '已批准', color: '#8BC34A' },
  { value: 'needs_update', label: '需更新', color: '#FF9800' },
]

const SORT_OPTIONS = [
  { value: 'updated_at', label: '最近更新' },
  { value: 'created_at', label: '创建时间' },
  { value: 'entry_key', label: '键名' },
  { value: 'status', label: '状态' },
]

const TranslationWorkbench: React.FC = () => {
  const theme = useTheme()

  // 状态管理
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState({
    language_code: '',
    status: '',
    has_translation: undefined as boolean | undefined,
  })
  const [sortBy, setSortBy] = useState('updated_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedEntries, setSelectedEntries] = useState<string[]>([])
  const [batchOperationDialog, setBatchOperationDialog] = useState<{
    open: boolean
    type: 'translate' | 'export' | 'import' | null
  }>({ open: false, type: null })

  // API hooks
  const { data: projects } = useApi(
    () => projectService.getProjects({ page: 1, page_size: 100 }),
    true,
  )

  const {
    data: translations,
    loading: loadingTranslations,
    error: translationsError,
    total,
    page,
    totalPages,
    loadPage,
    refresh: refreshTranslations,
  } = usePaginatedApi(
    useCallback(
      (params: any) => {
        if (!selectedProject) return Promise.resolve({ success: false })

        const searchParams: TranslationSearchParams = {
          ...createSearchParams(
            searchQuery,
            { ...filters, project_id: selectedProject },
            { page: params.page, pageSize: params.page_size },
            { sortBy, sortOrder },
          ),
        }

        return translationService.getTranslations(searchParams)
      },
      [selectedProject, searchQuery, filters, sortBy, sortOrder],
    ),
  )

  const { data: statistics, execute: loadStatistics } = useApi(
    () =>
      selectedProject
        ? translationService.getTranslationStatistics({ project_id: selectedProject })
        : Promise.resolve(null),
    false,
  )

  const { startTask: startBatchTranslate, data: batchTask, loading: batchLoading } = useAsyncTask()

  // 数据处理
  const projectOptions = useMemo(() => {
    if (!projects?.data?.items) return []
    return projects.data.items.map((project: Project) => ({
      value: project.id,
      label: project.name,
    }))
  }, [projects])

  const statusCounts = useMemo(() => {
    if (!statistics?.data) return {}
    return statistics.data.by_status || {}
  }, [statistics])

  // 事件处理
  const handleProjectChange = useCallback(
    (projectId: string) => {
      setSelectedProject(projectId)
      setSelectedEntries([])
      if (projectId) {
        loadStatistics()
      }
    },
    [loadStatistics],
  )

  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query)
      loadPage(1)
    },
    [loadPage],
  )

  const handleFilterChange = useCallback(
    (filterType: string, value: any) => {
      setFilters(prev => ({
        ...prev,
        [filterType]: value === '' ? undefined : value,
      }))
      loadPage(1)
    },
    [loadPage],
  )

  const handleSortChange = useCallback(
    (field: string) => {
      if (field === sortBy) {
        setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        setSortBy(field)
        setSortOrder('desc')
      }
      loadPage(1)
    },
    [sortBy, loadPage],
  )

  const handlePageChange = useCallback(
    (_: React.ChangeEvent<unknown>, newPage: number) => {
      loadPage(newPage)
    },
    [loadPage],
  )

  const handleSelectionChange = useCallback((ids: string[]) => {
    setSelectedEntries(ids)
  }, [])

  const handleBatchTranslate = useCallback(async () => {
    if (selectedEntries.length === 0) {
      toast.error('请选择要翻译的条目')
      return
    }

    try {
      const task = await translationService.autoTranslate({
        entry_ids: selectedEntries,
        target_language: filters.language_code || 'zh_cn',
        engine: 'google',
        preserve_formatting: true,
      })

      await startBatchTranslate(Promise.resolve({ success: true, data: task.data }))
      toast.success('批量翻译任务已启动')
      setBatchOperationDialog({ open: false, type: null })
    } catch (error) {
      toast.error('启动批量翻译失败')
    }
  }, [selectedEntries, filters.language_code, startBatchTranslate])

  const handleExport = useCallback(async () => {
    try {
      const task = await translationService.exportTranslations({
        project_id: selectedProject,
        language_codes: filters.language_code ? [filters.language_code] : undefined,
        format: 'xlsx',
        include_untranslated: true,
      })

      toast.success('导出任务已启动，请稍后下载')
    } catch (error) {
      toast.error('导出失败')
    }
  }, [selectedProject, filters.language_code])

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        backgroundColor: theme.palette.background.default,
      }}
    >
      <Box sx={{ maxWidth: 1600, mx: 'auto', p: { xs: 2, sm: 3, md: 4 } }}>
        {/* 页面头部 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ mb: 4 }}>
            <Box
              sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}
            >
              <Box>
                <Typography
                  variant='h4'
                  sx={{
                    fontWeight: 800,
                    background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    mb: 1,
                  }}
                >
                  翻译工作台
                </Typography>
                <Typography variant='body1' color='text.secondary'>
                  管理和编辑翻译条目
                </Typography>
              </Box>

              <Stack direction='row' spacing={2}>
                <Button
                  variant='outlined'
                  startIcon={<Upload size={20} />}
                  onClick={() => setBatchOperationDialog({ open: true, type: 'import' })}
                  disabled={!selectedProject}
                >
                  导入
                </Button>
                <Button
                  variant='outlined'
                  startIcon={<Download size={20} />}
                  onClick={handleExport}
                  disabled={!selectedProject}
                >
                  导出
                </Button>
              </Stack>
            </Box>

            {/* 项目选择器 */}
            <Card sx={{ mb: 3 }}>
              <CardContent sx={{ py: 2 }}>
                <FormControl fullWidth>
                  <InputLabel>选择项目</InputLabel>
                  <Select
                    value={selectedProject}
                    label='选择项目'
                    onChange={e => handleProjectChange(e.target.value)}
                  >
                    {projectOptions.map(project => (
                      <MenuItem key={project.value} value={project.value}>
                        {project.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </CardContent>
            </Card>

            {/* 统计信息 */}
            {statistics?.data && (
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={6} sm={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.info.main, 0.1)}, ${alpha(theme.palette.info.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <FileText
                        color={theme.palette.info.main}
                        size={24}
                        style={{ marginBottom: 8 }}
                      />
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.info.main }}
                      >
                        {statistics.data.total_entries.toLocaleString()}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        总条目
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={6} sm={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.success.main, 0.1)}, ${alpha(theme.palette.success.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <CheckCircle
                        color={theme.palette.success.main}
                        size={24}
                        style={{ marginBottom: 8 }}
                      />
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.success.main }}
                      >
                        {statistics.data.translated_entries.toLocaleString()}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        已翻译
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={6} sm={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.warning.main, 0.1)}, ${alpha(theme.palette.warning.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <Clock
                        color={theme.palette.warning.main}
                        size={24}
                        style={{ marginBottom: 8 }}
                      />
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.warning.main }}
                      >
                        {statistics.data.untranslated_entries.toLocaleString()}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        未翻译
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={6} sm={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)}, ${alpha(theme.palette.primary.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <BarChart3
                        color={theme.palette.primary.main}
                        size={24}
                        style={{ marginBottom: 8 }}
                      />
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.primary.main }}
                      >
                        {Math.round(statistics.data.translation_progress)}%
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        翻译进度
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* 搜索和过滤器 */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Grid container spacing={3} alignItems='center'>
                  <Grid item xs={12} md={4}>
                    <TextField
                      fullWidth
                      placeholder='搜索翻译条目...'
                      value={searchQuery}
                      onChange={e => handleSearch(e.target.value)}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position='start'>
                            <Search size={20} />
                          </InputAdornment>
                        ),
                      }}
                    />
                  </Grid>

                  <Grid item xs={12} sm={6} md={2}>
                    <FormControl fullWidth size='small'>
                      <InputLabel>语言</InputLabel>
                      <Select
                        value={filters.language_code || ''}
                        label='语言'
                        onChange={e => handleFilterChange('language_code', e.target.value)}
                      >
                        {LANGUAGE_OPTIONS.map(option => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} sm={6} md={2}>
                    <FormControl fullWidth size='small'>
                      <InputLabel>状态</InputLabel>
                      <Select
                        value={filters.status || ''}
                        label='状态'
                        onChange={e => handleFilterChange('status', e.target.value)}
                      >
                        {STATUS_OPTIONS.map(option => (
                          <MenuItem key={option.value} value={option.value}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {option.color && (
                                <Box
                                  sx={{
                                    width: 12,
                                    height: 12,
                                    borderRadius: '50%',
                                    backgroundColor: option.color,
                                  }}
                                />
                              )}
                              {option.label}
                            </Box>
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} sm={6} md={2}>
                    <FormControl fullWidth size='small'>
                      <InputLabel>排序</InputLabel>
                      <Select
                        value={sortBy}
                        label='排序'
                        onChange={e => handleSortChange(e.target.value)}
                      >
                        {SORT_OPTIONS.map(option => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} md={2}>
                    <Stack direction='row' spacing={1} alignItems='center'>
                      <Chip
                        icon={<Filter size={16} />}
                        label={`${total || 0} 条`}
                        variant='outlined'
                        size='small'
                      />
                      {selectedEntries.length > 0 && (
                        <Chip
                          label={`已选 ${selectedEntries.length}`}
                          color='primary'
                          size='small'
                        />
                      )}
                    </Stack>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Box>
        </motion.div>

        {/* 翻译表格 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {!selectedProject ? (
            <Card sx={{ textAlign: 'center', py: 8 }}>
              <CardContent>
                <Globe
                  size={64}
                  color={theme.palette.text.secondary}
                  style={{ marginBottom: 24 }}
                />
                <Typography variant='h6' color='text.secondary' sx={{ mb: 2 }}>
                  请选择一个项目
                </Typography>
                <Typography variant='body2' color='text.secondary'>
                  选择项目后即可开始翻译工作
                </Typography>
              </CardContent>
            </Card>
          ) : translationsError ? (
            <Alert severity='error' sx={{ mb: 3 }}>
              加载翻译失败: {translationsError}
            </Alert>
          ) : (
            <>
              <TranslationTable
                entries={translations || []}
                loading={loadingTranslations}
                selectedIds={selectedEntries}
                onSelectionChange={handleSelectionChange}
                onEdit={() => {}}
                onRefresh={refreshTranslations}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSortChange}
              />

              {/* 分页 */}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={handlePageChange}
                    color='primary'
                    size='large'
                    showFirstButton
                    showLastButton
                  />
                </Box>
              )}
            </>
          )}
        </motion.div>

        {/* 批量操作浮动按钮 */}
        <AnimatePresence>
          {selectedEntries.length > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              style={{
                position: 'fixed',
                bottom: 24,
                right: 24,
                zIndex: 1000,
              }}
            >
              <Fab
                color='primary'
                onClick={() => setBatchOperationDialog({ open: true, type: 'translate' })}
                disabled={batchLoading}
                sx={{
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                  '&:hover': {
                    background: `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.secondary.dark})`,
                    transform: 'scale(1.1)',
                  },
                  transition: 'all 0.3s ease',
                }}
              >
                <Zap size={24} />
              </Fab>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 批量翻译对话框 */}
        <Dialog
          open={batchOperationDialog.open && batchOperationDialog.type === 'translate'}
          onClose={() => setBatchOperationDialog({ open: false, type: null })}
          maxWidth='sm'
          fullWidth
        >
          <DialogTitle>批量翻译</DialogTitle>
          <DialogContent>
            <Typography variant='body1' sx={{ mb: 2 }}>
              将对选中的 {selectedEntries.length} 个条目执行自动翻译。
            </Typography>
            <Alert severity='info'>自动翻译结果仅供参考，建议人工审核后使用。</Alert>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setBatchOperationDialog({ open: false, type: null })}>
              取消
            </Button>
            <Button onClick={handleBatchTranslate} variant='contained' disabled={batchLoading}>
              {batchLoading ? '翻译中...' : '开始翻译'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* 任务进度 */}
        {batchTask && (
          <Card
            sx={{
              position: 'fixed',
              bottom: 100,
              right: 24,
              width: 300,
              zIndex: 1000,
            }}
          >
            <CardContent>
              <Typography variant='subtitle2' sx={{ mb: 1 }}>
                批量翻译进行中...
              </Typography>
              <LinearProgress variant='determinate' value={batchTask.progress} sx={{ mb: 1 }} />
              <Typography variant='caption' color='text.secondary'>
                {Math.round(batchTask.progress)}% 完成
              </Typography>
            </CardContent>
          </Card>
        )}
      </Box>
    </Box>
  )
}

export default TranslationWorkbench
