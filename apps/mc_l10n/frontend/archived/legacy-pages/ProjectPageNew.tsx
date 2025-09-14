/**
 * 重构后的项目管理页面
 * 使用新的 API 客户端架构和现代化组件
 */

import React, { useState, useCallback } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Fab,
  useTheme,
  alpha,
  Chip,
  InputAdornment,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Pagination,
  Stack,
  Alert,
} from '@mui/material'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Search, Filter, BarChart3, Folder, Archive, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ProjectCard } from '../components/Project/ProjectCard'
import { CreateProjectDialog } from '../components/Project/CreateProjectDialog'
import { Project, ProjectSearchParams } from '../types/api'
import { usePaginatedApi, useApi } from '../hooks/useApi'
import { projectService } from '../services'
import { createSearchParams } from '../services'
import toast from 'react-hot-toast'

const PROJECT_TYPES = [
  { value: '', label: '全部类型' },
  { value: 'mod', label: '模组' },
  { value: 'resource_pack', label: '资源包' },
  { value: 'mixed', label: '混合项目' },
]

const PROJECT_STATUSES = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '活跃' },
  { value: 'paused', label: '暂停' },
  { value: 'archived', label: '已归档' },
]

const SORT_OPTIONS = [
  { value: 'updated_at', label: '最近更新' },
  { value: 'created_at', label: '创建时间' },
  { value: 'name', label: '项目名称' },
]

const ProjectPageNew: React.FC = () => {
  const theme = useTheme()
  const navigate = useNavigate()

  // 状态管理
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState({
    project_type: '',
    status: '',
    language: '',
  })
  const [sortBy, setSortBy] = useState('updated_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [deleteConfirmDialog, setDeleteConfirmDialog] = useState<{
    open: boolean
    project: Project | null
  }>({
    open: false,
    project: null,
  })

  // API hooks
  const {
    data: projects,
    loading: loadingProjects,
    error: projectsError,
    total,
    page,
    totalPages,
    loadPage,
    refresh: refreshProjects,
  } = usePaginatedApi(
    useCallback(
      (params: any) => {
        const searchParams = createSearchParams(
          searchQuery,
          filters,
          { page: params.page, pageSize: params.page_size },
          { sortBy, sortOrder },
        )
        return projectService.getProjects(searchParams)
      },
      [searchQuery, filters, sortBy, sortOrder],
    ),
  )

  const { execute: deleteProject, loading: deleting } = useApi(
    () =>
      deleteConfirmDialog.project
        ? projectService.deleteProject(deleteConfirmDialog.project.id)
        : Promise.reject(),
    false,
  )

  const { data: globalStats } = useApi(() => projectService.getProjectStatistics(), true)

  // 事件处理
  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query)
      loadPage(1)
    },
    [loadPage],
  )

  const handleFilterChange = useCallback(
    (filterType: string, value: string) => {
      setFilters(prev => ({
        ...prev,
        [filterType]: value,
      }))
      loadPage(1)
    },
    [loadPage],
  )

  const handleSortChange = useCallback(
    (newSortBy: string) => {
      if (newSortBy === sortBy) {
        setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        setSortBy(newSortBy)
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

  const handleSelectProject = useCallback(
    (project: Project) => {
      setSelectedProject(project)
      // 可以根据需要导航到项目详情页
      navigate(`/projects/${project.id}`)
    },
    [navigate],
  )

  const handleEditProject = useCallback((project: Project) => {
    // 打开编辑对话框或导航到编辑页面
    console.log('Edit project:', project)
    toast.info('编辑功能开发中...')
  }, [])

  const handleDeleteProject = useCallback((project: Project) => {
    setDeleteConfirmDialog({ open: true, project })
  }, [])

  const handleConfirmDelete = useCallback(async () => {
    try {
      await deleteProject()
      toast.success('项目删除成功')
      setDeleteConfirmDialog({ open: false, project: null })
      refreshProjects()
    } catch (error) {
      toast.error('删除项目失败')
    }
  }, [deleteProject, refreshProjects])

  const handleCreateSuccess = useCallback(() => {
    refreshProjects()
    setCreateDialogOpen(false)
  }, [refreshProjects])

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        backgroundColor: theme.palette.background.default,
      }}
    >
      <Box sx={{ maxWidth: 1400, mx: 'auto', p: { xs: 2, sm: 3, md: 4 } }}>
        {/* 页面头部 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ mb: 4 }}>
            <Box
              sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}
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
                  项目管理
                </Typography>
                <Typography variant='body1' color='text.secondary'>
                  管理您的 Minecraft 本地化项目
                </Typography>
              </Box>

              <Button
                variant='contained'
                startIcon={<Plus size={20} />}
                onClick={() => setCreateDialogOpen(true)}
                sx={{
                  borderRadius: 3,
                  px: 3,
                  py: 1.5,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                  boxShadow: theme.shadows[4],
                  '&:hover': {
                    boxShadow: theme.shadows[8],
                    transform: 'translateY(-2px)',
                  },
                  transition: 'all 0.3s ease',
                }}
              >
                新建项目
              </Button>
            </Box>

            {/* 统计信息卡片 */}
            {globalStats?.data && (
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)}, ${alpha(theme.palette.primary.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <Folder
                        color={theme.palette.primary.main}
                        size={32}
                        style={{ marginBottom: 8 }}
                      />
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.primary.main }}
                      >
                        {globalStats.data.total_projects}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        总项目数
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.success.main, 0.1)}, ${alpha(theme.palette.success.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <BarChart3
                        color={theme.palette.success.main}
                        size={32}
                        style={{ marginBottom: 8 }}
                      />
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.success.main }}
                      >
                        {globalStats.data.active_projects}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        活跃项目
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.warning.main, 0.1)}, ${alpha(theme.palette.warning.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.warning.main }}
                      >
                        {globalStats.data.total_entries.toLocaleString()}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        翻译条目
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card
                    sx={{
                      background: `linear-gradient(135deg, ${alpha(theme.palette.info.main, 0.1)}, ${alpha(theme.palette.info.main, 0.05)})`,
                      border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <Typography
                        variant='h5'
                        sx={{ fontWeight: 700, color: theme.palette.info.main }}
                      >
                        {Math.round(globalStats.data.translation_progress)}%
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
            <Card sx={{ p: 3, mb: 3 }}>
              <Grid container spacing={3} alignItems='center'>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    placeholder='搜索项目...'
                    value={searchQuery}
                    onChange={e => handleSearch(e.target.value)}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position='start'>
                          <Search size={20} color={theme.palette.text.secondary} />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>

                <Grid item xs={12} sm={4} md={2}>
                  <FormControl fullWidth size='small'>
                    <InputLabel>项目类型</InputLabel>
                    <Select
                      value={filters.project_type}
                      label='项目类型'
                      onChange={e => handleFilterChange('project_type', e.target.value)}
                    >
                      {PROJECT_TYPES.map(type => (
                        <MenuItem key={type.value} value={type.value}>
                          {type.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={4} md={2}>
                  <FormControl fullWidth size='small'>
                    <InputLabel>项目状态</InputLabel>
                    <Select
                      value={filters.status}
                      label='项目状态'
                      onChange={e => handleFilterChange('status', e.target.value)}
                    >
                      {PROJECT_STATUSES.map(status => (
                        <MenuItem key={status.value} value={status.value}>
                          {status.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={4} md={2}>
                  <FormControl fullWidth size='small'>
                    <InputLabel>排序方式</InputLabel>
                    <Select
                      value={sortBy}
                      label='排序方式'
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
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip
                      icon={<Filter size={16} />}
                      label={`${total || 0} 个项目`}
                      variant='outlined'
                      size='small'
                    />
                  </Box>
                </Grid>
              </Grid>
            </Card>
          </Box>
        </motion.div>

        {/* 项目列表 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {projectsError && (
            <Alert severity='error' sx={{ mb: 3 }}>
              加载项目失败: {projectsError}
            </Alert>
          )}

          {loadingProjects ? (
            <Grid container spacing={3}>
              {Array.from({ length: 8 }).map((_, index) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                  <Card sx={{ height: 280 }}>
                    <CardContent>
                      <Box sx={{ animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>
                        <Box sx={{ height: 20, bgcolor: 'grey.300', borderRadius: 1, mb: 2 }} />
                        <Box sx={{ height: 16, bgcolor: 'grey.200', borderRadius: 1, mb: 1 }} />
                        <Box
                          sx={{ height: 16, bgcolor: 'grey.200', borderRadius: 1, width: '80%' }}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          ) : projects && projects.length > 0 ? (
            <>
              <Grid container spacing={3}>
                <AnimatePresence>
                  {projects.map(project => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
                      <ProjectCard
                        project={project}
                        isSelected={selectedProject?.id === project.id}
                        onSelect={handleSelectProject}
                        onEdit={handleEditProject}
                        onDelete={handleDeleteProject}
                        onRefresh={refreshProjects}
                      />
                    </Grid>
                  ))}
                </AnimatePresence>
              </Grid>

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
          ) : (
            <Card sx={{ textAlign: 'center', py: 8 }}>
              <CardContent>
                <Folder
                  size={64}
                  color={theme.palette.text.secondary}
                  style={{ marginBottom: 24 }}
                />
                <Typography variant='h6' color='text.secondary' sx={{ mb: 2 }}>
                  {searchQuery || Object.values(filters).some(v => v)
                    ? '未找到匹配的项目'
                    : '暂无项目'}
                </Typography>
                <Typography variant='body2' color='text.secondary' sx={{ mb: 3 }}>
                  {searchQuery || Object.values(filters).some(v => v)
                    ? '请尝试调整搜索条件或过滤器'
                    : '点击"新建项目"按钮创建您的第一个项目'}
                </Typography>
                {!searchQuery && !Object.values(filters).some(v => v) && (
                  <Button
                    variant='contained'
                    startIcon={<Plus size={20} />}
                    onClick={() => setCreateDialogOpen(true)}
                  >
                    新建项目
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </motion.div>

        {/* 浮动操作按钮 */}
        <Fab
          color='primary'
          aria-label='新建项目'
          onClick={() => setCreateDialogOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            '&:hover': {
              background: `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.secondary.dark})`,
              transform: 'scale(1.1)',
            },
            transition: 'all 0.3s ease',
          }}
        >
          <Plus size={24} />
        </Fab>

        {/* 创建项目对话框 */}
        <CreateProjectDialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
          onSuccess={handleCreateSuccess}
        />

        {/* 删除确认对话框 */}
        {/* 这里可以添加删除确认对话框组件 */}
      </Box>
    </Box>
  )
}

export default ProjectPageNew
