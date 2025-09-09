import React, { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Grid,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,
  Chip,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  Switch,
  FormControlLabel,
} from '@mui/material'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Plus,
  Folder,
  Edit,
  Trash2,
  MoreVertical,
  Star,
  StarOff,
  Copy,
  Archive,
  Download,
  Upload,
  Filter,
  SortAsc,
  SortDesc,
  FolderOpen,
  Package,
  Calendar,
  User,
  Globe,
  Hash,
  CheckCircle,
  AlertCircle,
  Clock,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { MinecraftButton } from '../components/minecraft/MinecraftButton'
import { MinecraftCard } from '../components/minecraft/MinecraftCard'
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress'
import { MinecraftBlock } from '../components/MinecraftComponents'

// 模拟项目数据
interface Project {
  id: string
  name: string
  description: string
  path: string
  modCount: number
  langFileCount: number
  totalKeys: number
  translatedKeys: number
  status: 'active' | 'completed' | 'archived' | 'paused'
  favorite: boolean
  createdAt: string
  updatedAt: string
  author: string
  version: string
  tags: string[]
}

// 将在组件加载时从API获取真实项目数据
export default function ProjectPageMinecraft() {
  const [projects, setProjects] = useState<Project[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'progress'>('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null)
  const [menuProject, setMenuProject] = useState<Project | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    path: '',
    version: '1.20.1',
  })

  // 稳定的状态更新回调
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value)
  }, [])

  const handleNewProjectNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setNewProject(prev => ({ ...prev, name: e.target.value }))
  }, [])

  const handleNewProjectDescriptionChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setNewProject(prev => ({ ...prev, description: e.target.value }))
  }, [])

  const handleNewProjectPathChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setNewProject(prev => ({ ...prev, path: e.target.value }))
  }, [])

  // 从API加载真实项目数据
  useEffect(() => {
    const loadProjects = async () => {
      try {
        // 获取所有扫描历史
        const response = await fetch('http://localhost:18000/api/v1/scans/history')
        const data = await response.json()

        if (data.success && data.data && Array.isArray(data.data)) {
          // 将扫描数据转换为项目格式
          const projectList: Project[] = data.data.map((scan: any) => ({
            id: scan.scan_id,
            name: scan.project_path?.split('/').pop() || scan.project_path?.split('\\').pop() || '未知项目',
            description: `包含 ${scan.total_mods || 0} 个模组的项目`,
            path: scan.project_path || '',
            modCount: scan.total_mods || 0,
            langFileCount: scan.total_language_files || 0,
            totalKeys: scan.total_keys || 0,
            translatedKeys: Math.floor((scan.total_keys || 0) * 0.6), // 模拟 60% 翻译率
            status: 'completed' as 'active' | 'paused' | 'completed',
            favorite: false,
            createdAt: scan.started_at || new Date().toISOString(),
            updatedAt: scan.completed_at || new Date().toISOString(),
            author: 'User',
            version: '1.20.1',
            tags: [scan.scan_type || '扫描'],
          }))

          setProjects(projectList)
          console.log(`加载了 ${projectList.length} 个扫描项目`)
        } else {
          console.warn('没有找到扫描历史数据')
          setProjects([])
        }
      } catch (error) {
        console.error('加载项目数据失败:', error)
        // 如果API失败，显示空列表
        setProjects([])
      }
    }

    loadProjects()
  }, [])

  // 过滤和排序项目
  const filteredProjects = projects
    .filter(project => {
      const matchesSearch =
        project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        project.description.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesFilter = filterStatus === 'all' || project.status === filterStatus
      return matchesSearch && matchesFilter
    })
    .sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'date':
          comparison = new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
          break
        case 'progress':
          const progressA = a.totalKeys > 0 ? (a.translatedKeys / a.totalKeys) * 100 : 0
          const progressB = b.totalKeys > 0 ? (b.translatedKeys / b.totalKeys) * 100 : 0
          comparison = progressB - progressA
          break
      }
      return sortOrder === 'asc' ? -comparison : comparison
    })

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, project: Project) => {
    setMenuAnchor(event.currentTarget)
    setMenuProject(project)
  }

  const handleMenuClose = () => {
    setMenuAnchor(null)
    setMenuProject(null)
  }

  const handleToggleFavorite = (projectId: string) => {
    setProjects(prev => prev.map(p => (p.id === projectId ? { ...p, favorite: !p.favorite } : p)))
    const project = projects.find(p => p.id === projectId)
    toast.success(project?.favorite ? '已取消收藏' : '已添加收藏', {
      icon: project?.favorite ? '⭐' : '✨',
    })
  }

  const handleCreateProject = () => {
    if (!newProject.name || !newProject.path) {
      toast.error('请填写必要信息')
      return
    }

    const project: Project = {
      id: Date.now().toString(),
      name: newProject.name,
      description: newProject.description,
      path: newProject.path,
      modCount: 0,
      langFileCount: 0,
      totalKeys: 0,
      translatedKeys: 0,
      status: 'active',
      favorite: false,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      author: 'Admin',
      version: newProject.version,
      tags: [],
    }

    setProjects(prev => [project, ...prev])
    setCreateDialogOpen(false)
    setNewProject({ name: '', description: '', path: '', version: '1.20.1' })
    toast.success('项目创建成功！', { icon: '🎉' })
  }

  const handleDeleteProject = (projectId: string) => {
    setProjects(prev => prev.filter(p => p.id !== projectId))
    handleMenuClose()
    toast.success('项目已删除', { icon: '🗑️' })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#4CAF50'
      case 'completed':
        return '#2196F3'
      case 'paused':
        return '#FF9800'
      case 'archived':
        return '#9E9E9E'
      default:
        return '#9E9E9E'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Clock size={16} />
      case 'completed':
        return <CheckCircle size={16} />
      case 'paused':
        return <AlertCircle size={16} />
      case 'archived':
        return <Archive size={16} />
      default:
        return <Clock size={16} />
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
              background: 'linear-gradient(135deg, #FFD700 0%, #FF6347 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              mb: 1,
            }}
          >
            📦 项目管理
          </Typography>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '14px',
              color: 'text.secondary',
            }}
          >
            管理和组织你的本地化项目
          </Typography>
        </Box>
      </motion.div>

      {/* 工具栏 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            placeholder='搜索项目...'
            value={searchTerm}
            onChange={handleSearchChange}
            InputProps={{
              startAdornment: (
                <InputAdornment position='start'>
                  <Search size={20} />
                </InputAdornment>
              ),
              sx: {
                fontFamily: '"Minecraft", monospace',
                fontSize: '14px',
                background: 'rgba(0,0,0,0.3)',
                border: '2px solid #4A4A4A',
                borderRadius: 0,
                '& fieldset': { border: 'none' },
              },
            }}
          />
        </Grid>
        <Grid item xs={6} md={2}>
          <FormControl fullWidth>
            <Select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '14px',
                background: 'rgba(0,0,0,0.3)',
                border: '2px solid #4A4A4A',
                borderRadius: 0,
                '& fieldset': { border: 'none' },
              }}
            >
              <MenuItem value='all'>全部状态</MenuItem>
              <MenuItem value='active'>进行中</MenuItem>
              <MenuItem value='completed'>已完成</MenuItem>
              <MenuItem value='paused'>已暂停</MenuItem>
              <MenuItem value='archived'>已归档</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={6} md={2}>
          <FormControl fullWidth>
            <Select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '14px',
                background: 'rgba(0,0,0,0.3)',
                border: '2px solid #4A4A4A',
                borderRadius: 0,
                '& fieldset': { border: 'none' },
              }}
            >
              <MenuItem value='name'>按名称</MenuItem>
              <MenuItem value='date'>按日期</MenuItem>
              <MenuItem value='progress'>按进度</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={6} md={2}>
          <MinecraftButton
            fullWidth
            minecraftStyle='iron'
            onClick={() => setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'))}
            startIcon={sortOrder === 'asc' ? <SortAsc size={16} /> : <SortDesc size={16} />}
          >
            {sortOrder === 'asc' ? '升序' : '降序'}
          </MinecraftButton>
        </Grid>
        <Grid item xs={6} md={2}>
          <MinecraftButton
            fullWidth
            minecraftStyle='emerald'
            onClick={() => setCreateDialogOpen(true)}
            startIcon={<Plus size={16} />}
            glowing
          >
            新建项目
          </MinecraftButton>
        </Grid>
      </Grid>

      {/* 项目统计 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <Box
            sx={{
              p: 2,
              background: 'linear-gradient(135deg, rgba(76,175,80,0.2) 0%, rgba(0,0,0,0.2) 100%)',
              border: '2px solid #4CAF50',
              borderRadius: 0,
              textAlign: 'center',
            }}
          >
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '24px',
                color: '#4CAF50',
              }}
            >
              {projects.length}
            </Typography>
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px',
                color: 'text.secondary',
              }}
            >
              总项目数
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} md={3}>
          <Box
            sx={{
              p: 2,
              background: 'linear-gradient(135deg, rgba(33,150,243,0.2) 0%, rgba(0,0,0,0.2) 100%)',
              border: '2px solid #2196F3',
              borderRadius: 0,
              textAlign: 'center',
            }}
          >
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '24px',
                color: '#2196F3',
              }}
            >
              {projects.filter(p => p.status === 'active').length}
            </Typography>
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px',
                color: 'text.secondary',
              }}
            >
              进行中
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} md={3}>
          <Box
            sx={{
              p: 2,
              background: 'linear-gradient(135deg, rgba(255,193,7,0.2) 0%, rgba(0,0,0,0.2) 100%)',
              border: '2px solid #FFC107',
              borderRadius: 0,
              textAlign: 'center',
            }}
          >
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '24px',
                color: '#FFC107',
              }}
            >
              {projects.reduce((sum, p) => sum + p.modCount, 0)}
            </Typography>
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px',
                color: 'text.secondary',
              }}
            >
              总模组数
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} md={3}>
          <Box
            sx={{
              p: 2,
              background: 'linear-gradient(135deg, rgba(156,39,176,0.2) 0%, rgba(0,0,0,0.2) 100%)',
              border: '2px solid #9C27B0',
              borderRadius: 0,
              textAlign: 'center',
            }}
          >
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '24px',
                color: '#9C27B0',
              }}
            >
              {projects.reduce((sum, p) => sum + p.totalKeys, 0).toLocaleString()}
            </Typography>
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px',
                color: 'text.secondary',
              }}
            >
              总翻译键
            </Typography>
          </Box>
        </Grid>
      </Grid>

      {/* 项目列表 */}
      <Grid container spacing={3}>
        <AnimatePresence>
          {filteredProjects.map((project, index) => (
            <Grid item xs={12} md={6} lg={4} key={project.id}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                whileHover={{ scale: 1.02 }}
              >
                <MinecraftCard
                  variant={project.status === 'completed' ? 'enchantment' : 'inventory'}
                  glowing={project.favorite}
                >
                  <Box sx={{ p: 2 }}>
                    {/* 项目头部 */}
                    <Box
                      sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        mb: 2,
                      }}
                    >
                      <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '16px',
                              color: '#FFFFFF',
                              fontWeight: 'bold',
                            }}
                          >
                            {project.name}
                          </Typography>
                          {project.favorite && <Star size={16} color='#FFD700' fill='#FFD700' />}
                        </Box>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '11px',
                            color: 'text.secondary',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                        >
                          {project.description}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <IconButton
                          size='small'
                          onClick={() => handleToggleFavorite(project.id)}
                          sx={{ color: project.favorite ? '#FFD700' : '#888' }}
                        >
                          {project.favorite ? <Star size={16} /> : <StarOff size={16} />}
                        </IconButton>
                        <IconButton size='small' onClick={e => handleMenuOpen(e, project)}>
                          <MoreVertical size={16} />
                        </IconButton>
                      </Box>
                    </Box>

                    {/* 状态标签 */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Chip
                        icon={getStatusIcon(project.status)}
                        label={
                          project.status === 'active'
                            ? '进行中'
                            : project.status === 'completed'
                              ? '已完成'
                              : project.status === 'paused'
                                ? '已暂停'
                                : '已归档'
                        }
                        size='small'
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '10px',
                          background: getStatusColor(project.status),
                          color: '#FFFFFF',
                          borderRadius: 0,
                          '& .MuiChip-icon': {
                            color: '#FFFFFF',
                          },
                        }}
                      />
                      <Chip
                        label={project.version}
                        size='small'
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '10px',
                          background: 'rgba(0,0,0,0.3)',
                          borderRadius: 0,
                        }}
                      />
                    </Box>

                    {/* 进度条 */}
                    <Box sx={{ mb: 2 }}>
                      <MinecraftProgress
                        value={project.translatedKeys}
                        max={project.totalKeys}
                        variant={project.status === 'completed' ? 'experience' : 'loading'}
                        size='small'
                        animated={project.status === 'active'}
                      />
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '10px',
                            color: 'text.secondary',
                          }}
                        >
                          {project.totalKeys > 0
                            ? ((project.translatedKeys / project.totalKeys) * 100).toFixed(1)
                            : '0.0'}
                          %
                        </Typography>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '10px',
                            color: 'text.secondary',
                          }}
                        >
                          {project.translatedKeys.toLocaleString()} /{' '}
                          {project.totalKeys.toLocaleString()}
                        </Typography>
                      </Box>
                    </Box>

                    {/* 统计信息 */}
                    <Grid container spacing={1} sx={{ mb: 2 }}>
                      <Grid item xs={6}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Package size={14} />
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '11px',
                              color: 'text.secondary',
                            }}
                          >
                            {project.modCount} 模组
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Globe size={14} />
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '11px',
                              color: 'text.secondary',
                            }}
                          >
                            {project.langFileCount} 语言文件
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>

                    {/* 标签 */}
                    {project.tags.length > 0 && (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                        {project.tags.map(tag => (
                          <Chip
                            key={tag}
                            label={tag}
                            size='small'
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '9px',
                              height: 20,
                              background: 'rgba(0,188,212,0.2)',
                              border: '1px solid #00BCD4',
                              borderRadius: 0,
                            }}
                          />
                        ))}
                      </Box>
                    )}

                    {/* 元信息 */}
                    <Box
                      sx={{
                        pt: 2,
                        borderTop: '1px solid rgba(255,255,255,0.1)',
                        display: 'flex',
                        justifyContent: 'space-between',
                      }}
                    >
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '10px',
                          color: 'text.secondary',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                        }}
                      >
                        <Calendar size={12} />
                        {new Date(project.updatedAt).toLocaleDateString()}
                      </Typography>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '10px',
                          color: 'text.secondary',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                        }}
                      >
                        <User size={12} />
                        {project.author}
                      </Typography>
                    </Box>

                    {/* 操作按钮 */}
                    <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                      <MinecraftButton
                        fullWidth
                        minecraftStyle='diamond'
                        size='small'
                        onClick={() => {
                          setSelectedProject(project)
                          toast.success('打开项目: ' + project.name)
                        }}
                      >
                        打开
                      </MinecraftButton>
                      <MinecraftButton
                        fullWidth
                        minecraftStyle='gold'
                        size='small'
                        onClick={() => {
                          toast.success('编辑项目: ' + project.name)
                        }}
                      >
                        编辑
                      </MinecraftButton>
                    </Box>
                  </Box>
                </MinecraftCard>
              </motion.div>
            </Grid>
          ))}
        </AnimatePresence>

        {/* 空状态 */}
        {filteredProjects.length === 0 && (
          <Grid item xs={12}>
            <Box
              sx={{
                py: 8,
                textAlign: 'center',
                opacity: 0.6,
              }}
            >
              <Package size={64} />
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '16px',
                  color: 'text.secondary',
                  mt: 2,
                }}
              >
                没有找到项目
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '12px',
                  color: 'text.secondary',
                  mt: 1,
                }}
              >
                尝试调整搜索条件或创建新项目
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>

      {/* 右键菜单 */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            background: 'rgba(0,0,0,0.9)',
            border: '2px solid #4A4A4A',
            borderRadius: 0,
            '& .MuiMenuItem-root': {
              fontFamily: '"Minecraft", monospace',
              fontSize: '12px',
              color: '#FFFFFF',
              '&:hover': {
                background: 'rgba(255,255,255,0.1)',
              },
            },
          },
        }}
      >
        <MenuItem
          onClick={() => {
            handleMenuClose()
            toast.success('复制项目: ' + menuProject?.name)
          }}
        >
          <Copy size={16} style={{ marginRight: 8 }} />
          复制项目
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose()
            toast.success('导出项目: ' + menuProject?.name)
          }}
        >
          <Download size={16} style={{ marginRight: 8 }} />
          导出项目
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose()
            toast.success('归档项目: ' + menuProject?.name)
          }}
        >
          <Archive size={16} style={{ marginRight: 8 }} />
          归档项目
        </MenuItem>
        <MenuItem onClick={() => menuProject && handleDeleteProject(menuProject.id)}>
          <Trash2 size={16} style={{ marginRight: 8 }} />
          删除项目
        </MenuItem>
      </Menu>

      {/* 创建项目对话框 */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth='sm'
        fullWidth
        PaperProps={{
          sx: {
            background: 'linear-gradient(135deg, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.85) 100%)',
            border: '3px solid #4A4A4A',
            borderRadius: 0,
            boxShadow: '0 0 30px rgba(0,188,212,0.5)',
          },
        }}
      >
        <DialogTitle
          sx={{
            fontFamily: '"Minecraft", monospace',
            fontSize: '18px',
            color: '#FFFFFF',
            borderBottom: '2px solid #4A4A4A',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <MinecraftBlock type='emerald' size={24} />
          创建新项目
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='项目名称'
                value={newProject.name}
                onChange={handleNewProjectNameChange}
                InputLabelProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '12px',
                    color: 'text.secondary',
                  },
                }}
                InputProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': {
                      borderRadius: 0,
                      borderWidth: 2,
                    },
                  },
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label='项目描述'
                multiline
                rows={3}
                value={newProject.description}
                onChange={handleNewProjectDescriptionChange}
                InputLabelProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '12px',
                    color: 'text.secondary',
                  },
                }}
                InputProps={{
                  sx: {
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': {
                      borderRadius: 0,
                      borderWidth: 2,
                    },
                  },
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  label='项目路径'
                  value={newProject.path}
                  onChange={handleNewProjectPathChange}
                  InputLabelProps={{
                    sx: {
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '12px',
                      color: 'text.secondary',
                    },
                  }}
                  InputProps={{
                    sx: {
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '14px',
                      '& fieldset': {
                        borderRadius: 0,
                        borderWidth: 2,
                      },
                    },
                  }}
                />
                <MinecraftButton
                  minecraftStyle='gold'
                  onClick={() => toast.info('选择文件夹功能开发中...')}
                >
                  <FolderOpen size={16} />
                </MinecraftButton>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '12px',
                    color: 'text.secondary',
                  }}
                >
                  游戏版本
                </InputLabel>
                <Select
                  value={newProject.version}
                  onChange={e => setNewProject({ ...newProject, version: e.target.value })}
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '14px',
                    '& fieldset': {
                      borderRadius: 0,
                      borderWidth: 2,
                    },
                  }}
                >
                  <MenuItem value='1.20.1'>1.20.1</MenuItem>
                  <MenuItem value='1.19.2'>1.19.2</MenuItem>
                  <MenuItem value='1.18.2'>1.18.2</MenuItem>
                  <MenuItem value='1.16.5'>1.16.5</MenuItem>
                  <MenuItem value='1.12.2'>1.12.2</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 2, borderTop: '2px solid #4A4A4A' }}>
          <MinecraftButton minecraftStyle='stone' onClick={() => setCreateDialogOpen(false)}>
            取消
          </MinecraftButton>
          <MinecraftButton minecraftStyle='emerald' onClick={handleCreateProject} glowing>
            创建
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
