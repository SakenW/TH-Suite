import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  CardActions,
  Chip,
  useTheme,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material'
import { motion } from 'framer-motion'
import {
  Plus,
  FolderOpen,
  Package,
  Settings,
  Trash2,
  ChevronDown,
  ChevronUp,
  Scan,
  FileText,
} from 'lucide-react'
import { alpha } from '@mui/material/styles'
import { useNavigate } from 'react-router-dom'
import { tauriService } from '@services'
import { apiService } from '@services/apiService'
import ProjectScan from '../components/ProjectScan'
import toast from 'react-hot-toast'

interface Project {
  id: string
  name: string
  type: 'modpack' | 'mod'
  path: string
  lastModified: Date
  description?: string
  scanResults?: {
    mods: Array<{
      name: string
      version: string
      path: string
      dependencies?: string[]
    }>
    configs: Array<{
      name: string
      path: string
      type: string
    }>
    resources: Array<{
      name: string
      path: string
      type: string
    }>
  }
}

const ProjectPage: React.FC = () => {
  const theme = useTheme()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [currentProject, setCurrentProject] = useState<Project | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectType, setNewProjectType] = useState<'modpack' | 'mod'>('modpack')
  const [newProjectPath, setNewProjectPath] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [scanningProject, setScanningProject] = useState<string | null>(null)
  const [showProjectScan, setShowProjectScan] = useState(false)
  const [selectedProjectPath, setSelectedProjectPath] = useState<string>('')

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const mockProjects: Project[] = [
        {
          id: '1',
          name: 'My Modpack',
          type: 'modpack',
          path: '/path/to/modpack',
          lastModified: new Date(),
          description: 'A custom modpack for survival gameplay',
          scanResults: {
            mods: [
              { name: 'JEI', version: '1.19.2-11.6.0.1019', path: '/mods/jei.jar' },
              { name: 'Forge', version: '43.2.14', path: '/mods/forge.jar' },
            ],
            configs: [
              { name: 'jei-client.toml', path: '/config/jei-client.toml', type: 'TOML' },
              { name: 'forge-common.toml', path: '/config/forge-common.toml', type: 'TOML' },
            ],
            resources: [
              {
                name: 'custom_texture.png',
                path: '/resourcepacks/custom/textures/custom_texture.png',
                type: 'PNG',
              },
            ],
          },
        },
        {
          id: '2',
          name: 'Custom Mod',
          type: 'mod',
          path: '/path/to/mod',
          lastModified: new Date(),
          description: 'A utility mod for enhanced gameplay',
          scanResults: {
            mods: [{ name: 'CustomMod', version: '1.0.0', path: '/src/main/java' }],
            configs: [
              {
                name: 'custom-mod.toml',
                path: '/src/main/resources/META-INF/custom-mod.toml',
                type: 'TOML',
              },
            ],
            resources: [
              { name: 'mod_logo.png', path: '/src/main/resources/logo.png', type: 'PNG' },
            ],
          },
        },
      ]
      setProjects(mockProjects)
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const handleCreateProject = async (type: 'modpack' | 'mod') => {
    try {
      // 打开文件选择器选择项目路径
      const selectedPath = await tauriService.selectDirectory({
        title: `选择${type === 'modpack' ? '模组包' : '独立模组'}项目目录`,
      })
      if (selectedPath) {
        // 设置选中的路径并显示ProjectScan组件
        setSelectedProjectPath(selectedPath)
        setNewProjectType(type)
        setShowProjectScan(true)
      }
    } catch (error) {
      console.error('Failed to select project path:', error)
      toast.error('选择项目路径失败')
    }
  }

  const handleScanComplete = (result: any) => {
    // 扫描完成后的处理逻辑
    console.log('Scan completed:', result)
  }

  const handleProjectCreated = (result: any) => {
    // 项目创建完成后的处理逻辑
    console.log('Project created:', result)
    setShowProjectScan(false)
    loadProjects() // 刷新项目列表
    toast.success('项目创建成功！')
  }

  const handleSelectProjectPath = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory({
        title: '选择项目目录',
      })
      if (selectedPath) {
        setNewProjectPath(selectedPath)
      }
    } catch (error) {
      console.error('Failed to select path:', error)
    }
  }

  const handleConfirmCreate = async () => {
    try {
      const newProject: Project = {
        id: Date.now().toString(),
        name: newProjectName,
        type: newProjectType,
        path: newProjectPath,
        lastModified: new Date(),
        description: newProjectDescription,
      }
      setProjects(prev => [...prev, newProject])
      setCreateDialogOpen(false)
      setNewProjectName('')
      setNewProjectPath('')
      setNewProjectDescription('')
    } catch (error) {
      console.error('Failed to create project:', error)
    }
  }

  const handleOpenProject = async (project: Project) => {
    try {
      setCurrentProject(project)
      navigate('/build')
    } catch (error) {
      console.error('Failed to open project:', error)
    }
  }

  const handleDeleteProject = async (projectId: string) => {
    try {
      setProjects(prev => prev.filter(p => p.id !== projectId))
      if (currentProject?.id === projectId) {
        setCurrentProject(null)
      }
    } catch (error) {
      console.error('Failed to delete project:', error)
    }
  }

  const handleScanProject = async (projectId: string) => {
    try {
      setScanningProject(projectId)

      // 获取项目信息
      const project = projects.find(p => p.id === projectId)
      if (!project) {
        toast.error('项目不存在')
        setScanningProject(null)
        return
      }

      // 调用真实的扫描API
      const scanResponse = await apiService.scanDirectory({
        directory_path: project.path,
        recursive: true,
        file_patterns: ['*.jar', '*.json', '*.toml', '*.cfg'],
      })

      if (scanResponse.success && scanResponse.data) {
        // 轮询扫描结果
        const jobId = scanResponse.data.job_id
        let scanCompleted = false
        let attempts = 0
        const maxAttempts = 30 // 最多等待30次，每次2秒

        while (!scanCompleted && attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 2000))
          attempts++

          try {
            const jobStatus = await apiService.getJobStatus(jobId)
            if (jobStatus.success && jobStatus.data) {
              if (jobStatus.data.status === 'completed') {
                // 扫描完成，获取结果
                const result = jobStatus.data.result

                // 更新项目扫描结果
                setProjects(prev =>
                  prev.map(p => {
                    if (p.id === projectId) {
                      return {
                        ...p,
                        scanResults: {
                          mods:
                            result.mod_jars?.map((mod: any) => ({
                              name: mod.display_name || mod.mod_id,
                              version: mod.version,
                              path: mod.jar_path,
                              dependencies: mod.dependencies || [],
                            })) || [],
                          configs:
                            result.override_contents
                              ?.filter(
                                (item: any) =>
                                  item.path.endsWith('.toml') || item.path.endsWith('.cfg'),
                              )
                              .map((config: any) => ({
                                name: config.path.split('/').pop(),
                                path: config.path,
                                type: config.path.endsWith('.toml') ? 'TOML' : 'CFG',
                              })) || [],
                          resources:
                            result.language_resources?.map((resource: any) => ({
                              name: resource.source_path.split('/').pop(),
                              path: resource.source_path,
                              type:
                                resource.source_path.split('.').pop()?.toUpperCase() || 'UNKNOWN',
                            })) || [],
                        },
                      }
                    }
                    return p
                  }),
                )

                scanCompleted = true
                toast.success(
                  `项目扫描完成！发现 ${result.total_mods || 0} 个模组，${result.total_language_files || 0} 个语言文件`,
                )
              } else if (jobStatus.data.status === 'failed') {
                throw new Error(jobStatus.data.error || '扫描失败')
              }
              // 如果状态是 'running' 或 'pending'，继续等待
            }
          } catch (statusError) {
            console.error('Failed to get job status:', statusError)
            break
          }
        }

        if (!scanCompleted) {
          toast.error('扫描超时，请重试')
        }
      } else {
        throw new Error(scanResponse.message || '启动扫描失败')
      }

      setScanningProject(null)
    } catch (error) {
      console.error('Failed to scan project:', error)
      toast.error(`扫描项目失败: ${error instanceof Error ? error.message : '未知错误'}`)
      setScanningProject(null)
    }
  }

  const toggleProjectExpansion = (projectId: string) => {
    setExpandedProjects(prev => {
      const newSet = new Set(prev)
      if (newSet.has(projectId)) {
        newSet.delete(projectId)
      } else {
        newSet.add(projectId)
      }
      return newSet
    })
  }

  const renderScanResults = (project: Project) => {
    if (!project.scanResults) return null

    const { mods, configs, resources } = project.scanResults

    return (
      <Box sx={{ mt: 2, pl: 2, borderLeft: `2px solid ${theme.palette.divider}` }}>
        <Typography variant='subtitle2' sx={{ mb: 1, fontWeight: 600 }}>
          扫描结果
        </Typography>

        {mods.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant='body2' color='primary' sx={{ fontWeight: 600, mb: 1 }}>
              模组 ({mods.length})
            </Typography>
            <List dense sx={{ pl: 2 }}>
              {mods.map((mod, index) => (
                <ListItem key={index} sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <Package size={16} />
                  </ListItemIcon>
                  <ListItemText
                    primary={`${mod.name} v${mod.version}`}
                    secondary={mod.path}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {configs.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant='body2' color='secondary' sx={{ fontWeight: 600, mb: 1 }}>
              配置文件 ({configs.length})
            </Typography>
            <List dense sx={{ pl: 2 }}>
              {configs.map((config, index) => (
                <ListItem key={index} sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <Settings size={16} />
                  </ListItemIcon>
                  <ListItemText
                    primary={config.name}
                    secondary={config.path}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {resources.length > 0 && (
          <Box>
            <Typography variant='body2' color='text.secondary' sx={{ fontWeight: 600, mb: 1 }}>
              资源文件 ({resources.length})
            </Typography>
            <List dense sx={{ pl: 2 }}>
              {resources.map((resource, index) => (
                <ListItem key={index} sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <FileText size={16} />
                  </ListItemIcon>
                  <ListItemText
                    primary={resource.name}
                    secondary={resource.path}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </Box>
    )
  }

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        padding: { xs: 2, sm: 3, md: 4 },
        backgroundColor: theme.palette.background.default,
      }}
    >
      <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* 新建项目区域 - 美化版 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Card
              sx={{
                mb: 4,
                background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.05)} 0%, ${alpha(theme.palette.secondary.main, 0.05)} 100%)`,
                border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
                borderRadius: 3,
                overflow: 'hidden',
                position: 'relative',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '4px',
                  background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                },
              }}
            >
              <CardContent sx={{ p: 4 }}>
                <Grid container spacing={4} alignItems='center'>
                  {/* 左侧：标题和描述 */}
                  <Grid item xs={12} md={6}>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.6, delay: 0.2 }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Box
                          sx={{
                            width: 64,
                            height: 64,
                            borderRadius: 3,
                            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            mr: 3,
                            boxShadow: theme.shadows[4],
                            position: 'relative',
                            '&::after': {
                              content: '""',
                              position: 'absolute',
                              inset: 2,
                              borderRadius: 2,
                              background: 'rgba(255,255,255,0.1)',
                            },
                          }}
                        >
                          <Plus size={28} color='white' style={{ zIndex: 1 }} />
                        </Box>
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
                              fontSize: { xs: '1.8rem', md: '2.2rem' },
                            }}
                          >
                            快速开始
                          </Typography>
                          <Typography
                            variant='body1'
                            sx={{
                              color: theme.palette.text.secondary,
                              fontSize: '1.1rem',
                              lineHeight: 1.6,
                              fontWeight: 500,
                            }}
                          >
                            选择项目文件夹，自动识别并创建项目 🚀
                          </Typography>
                        </Box>
                      </Box>
                    </motion.div>
                  </Grid>

                  {/* 右侧：操作按钮 */}
                  <Grid item xs={12} md={6}>
                    <motion.div
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.6, delay: 0.4 }}
                    >
                      <Box
                        sx={{
                          display: 'flex',
                          gap: 3,
                          justifyContent: { xs: 'center', md: 'flex-end' },
                          flexDirection: { xs: 'column', sm: 'row' },
                          alignItems: 'stretch',
                        }}
                      >
                        <Button
                          variant='contained'
                          size='large'
                          startIcon={<Package size={22} />}
                          onClick={() => handleCreateProject('modpack')}
                          sx={{
                            minWidth: 160,
                            height: 56,
                            borderRadius: 3,
                            textTransform: 'none',
                            fontSize: '1.1rem',
                            fontWeight: 700,
                            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                            boxShadow: theme.shadows[6],
                            '&:hover': {
                              background: `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.primary.main})`,
                              transform: 'translateY(-2px)',
                              boxShadow: theme.shadows[12],
                            },
                            transition: 'all 0.3s ease',
                            position: 'relative',
                            overflow: 'hidden',
                            '&::before': {
                              content: '""',
                              position: 'absolute',
                              top: 0,
                              left: '-100%',
                              width: '100%',
                              height: '100%',
                              background:
                                'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
                              transition: 'left 0.5s ease',
                            },
                            '&:hover::before': {
                              left: '100%',
                            },
                          }}
                        >
                          📦 模组包
                        </Button>
                        <Button
                          variant='outlined'
                          size='large'
                          startIcon={<Settings size={22} />}
                          onClick={() => handleCreateProject('mod')}
                          sx={{
                            minWidth: 160,
                            height: 56,
                            borderRadius: 3,
                            textTransform: 'none',
                            fontSize: '1.1rem',
                            fontWeight: 700,
                            borderWidth: 2,
                            borderColor: theme.palette.secondary.main,
                            color: theme.palette.secondary.main,
                            '&:hover': {
                              borderWidth: 2,
                              borderColor: theme.palette.secondary.dark,
                              backgroundColor: alpha(theme.palette.secondary.main, 0.1),
                              transform: 'translateY(-2px)',
                              boxShadow: theme.shadows[8],
                            },
                            transition: 'all 0.3s ease',
                          }}
                        >
                          ⚙️ 独立模组
                        </Button>
                      </Box>
                      <Typography
                        variant='body2'
                        sx={{
                          mt: 3,
                          textAlign: { xs: 'center', md: 'right' },
                          color: theme.palette.text.secondary,
                          fontSize: '0.95rem',
                          fontStyle: 'italic',
                        }}
                      >
                        💡 点击按钮选择文件夹，系统将自动扫描并识别项目类型
                      </Typography>
                    </motion.div>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </motion.div>

          {/* 当前项目卡片 */}
          {currentProject && (
            <Card sx={{ mb: 4, border: `2px solid ${theme.palette.primary.main}` }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Chip
                    label={currentProject.type === 'modpack' ? '模组包' : '独立模组'}
                    color='primary'
                    size='small'
                    sx={{ mr: 2 }}
                  />
                  <Typography variant='h6' sx={{ flexGrow: 1 }}>
                    当前项目: {currentProject.name}
                  </Typography>
                  <Button variant='outlined' size='small' onClick={() => navigate('/build')}>
                    打开项目
                  </Button>
                </Box>
                <Typography variant='body2' color='text.secondary'>
                  {currentProject.description || '暂无描述'}
                </Typography>
                <Typography
                  variant='caption'
                  color='text.secondary'
                  sx={{ mt: 1, display: 'block' }}
                >
                  路径: {currentProject.path}
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* 项目列表 - 分组显示 */}
          {projects.length === 0 ? (
            <Card sx={{ textAlign: 'center', py: 6, backgroundColor: theme.palette.grey[50] }}>
              <CardContent>
                <Package
                  size={48}
                  color={theme.palette.text.secondary}
                  style={{ marginBottom: 16 }}
                />
                <Typography variant='h6' color='text.secondary' sx={{ mt: 2, mb: 1 }}>
                  暂无项目
                </Typography>
                <Typography variant='body2' color='text.secondary'>
                  点击上方"快速开始"按钮创建您的第一个项目
                </Typography>
              </CardContent>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {/* 模组包项目 */}
              {(() => {
                const modpackProjects = projects.filter(p => p.type === 'modpack')
                return (
                  modpackProjects.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                    >
                      <Card
                        sx={{
                          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.03)} 0%, ${alpha(theme.palette.primary.main, 0.08)} 100%)`,
                          border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`,
                          borderRadius: 3,
                        }}
                      >
                        <CardContent sx={{ pb: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                            <Box
                              sx={{
                                width: 40,
                                height: 40,
                                borderRadius: 2,
                                background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                mr: 2,
                                boxShadow: theme.shadows[3],
                              }}
                            >
                              <Package size={20} color='white' />
                            </Box>
                            <Typography
                              variant='h5'
                              sx={{
                                fontWeight: 700,
                                color: theme.palette.primary.main,
                                fontSize: '1.5rem',
                              }}
                            >
                              📦 模组包项目
                            </Typography>
                            <Chip
                              label={modpackProjects.length}
                              size='small'
                              color='primary'
                              sx={{ ml: 2 }}
                            />
                          </Box>
                          <Grid container spacing={3}>
                            {modpackProjects.map(project => (
                              <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
                                <motion.div
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ duration: 0.3 }}
                                >
                                  <Card
                                    sx={{
                                      height: '100%',
                                      display: 'flex',
                                      flexDirection: 'column',
                                      cursor: 'pointer',
                                      transition: 'all 0.3s ease',
                                      border:
                                        currentProject?.id === project.id
                                          ? `2px solid ${theme.palette.primary.main}`
                                          : `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                                      borderRadius: 2,
                                      '&:hover': {
                                        transform: 'translateY(-6px)',
                                        boxShadow: theme.shadows[12],
                                        borderColor: theme.palette.primary.main,
                                      },
                                    }}
                                    onClick={() => handleOpenProject(project)}
                                  >
                                    <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                        <Chip
                                          label='模组包'
                                          color='primary'
                                          size='small'
                                          sx={{ fontWeight: 600 }}
                                        />
                                      </Box>
                                      <Typography
                                        variant='h6'
                                        sx={{ mb: 1, fontWeight: 700, fontSize: '1.1rem' }}
                                      >
                                        {project.name}
                                      </Typography>
                                      <Typography
                                        variant='body2'
                                        color='text.secondary'
                                        sx={{ mb: 2, lineHeight: 1.5 }}
                                      >
                                        {project.description || '暂无描述'}
                                      </Typography>
                                      <Typography
                                        variant='caption'
                                        color='text.secondary'
                                        sx={{ fontWeight: 500 }}
                                      >
                                        最后修改: {project.lastModified.toLocaleDateString()}
                                      </Typography>
                                    </CardContent>
                                    <CardActions
                                      sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}
                                    >
                                      <Box sx={{ display: 'flex', gap: 1 }}>
                                        <IconButton
                                          size='small'
                                          color='primary'
                                          onClick={e => {
                                            e.stopPropagation()
                                            handleOpenProject(project)
                                          }}
                                          title='打开项目'
                                        >
                                          <FolderOpen size={16} />
                                        </IconButton>
                                        <IconButton
                                          size='small'
                                          color='info'
                                          onClick={e => {
                                            e.stopPropagation()
                                            handleScanProject(project.id)
                                          }}
                                          title='扫描项目'
                                          disabled={scanningProject === project.id}
                                        >
                                          <Scan size={16} />
                                        </IconButton>
                                        {project.scanResults && (
                                          <IconButton
                                            size='small'
                                            onClick={e => {
                                              e.stopPropagation()
                                              toggleProjectExpansion(project.id)
                                            }}
                                            title={
                                              expandedProjects.has(project.id)
                                                ? '收起详情'
                                                : '展开详情'
                                            }
                                          >
                                            {expandedProjects.has(project.id) ? (
                                              <ChevronUp size={16} />
                                            ) : (
                                              <ChevronDown size={16} />
                                            )}
                                          </IconButton>
                                        )}
                                      </Box>
                                      <IconButton
                                        size='small'
                                        color='error'
                                        onClick={e => {
                                          e.stopPropagation()
                                          handleDeleteProject(project.id)
                                        }}
                                        title='删除项目'
                                      >
                                        <Trash2 size={16} />
                                      </IconButton>
                                    </CardActions>

                                    <Collapse
                                      in={expandedProjects.has(project.id)}
                                      timeout='auto'
                                      unmountOnExit
                                    >
                                      <Box sx={{ px: 2, pb: 2 }}>
                                        <Divider sx={{ mb: 2 }} />
                                        {renderScanResults(project)}
                                      </Box>
                                    </Collapse>
                                  </Card>
                                </motion.div>
                              </Grid>
                            ))}
                          </Grid>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )
                )
              })()}

              {/* 独立模组项目 */}
              {(() => {
                const modProjects = projects.filter(p => p.type === 'mod')
                return (
                  modProjects.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: 0.1 }}
                    >
                      <Card
                        sx={{
                          background: `linear-gradient(135deg, ${alpha(theme.palette.secondary.main, 0.03)} 0%, ${alpha(theme.palette.secondary.main, 0.08)} 100%)`,
                          border: `1px solid ${alpha(theme.palette.secondary.main, 0.15)}`,
                          borderRadius: 3,
                        }}
                      >
                        <CardContent sx={{ pb: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                            <Box
                              sx={{
                                width: 40,
                                height: 40,
                                borderRadius: 2,
                                background: `linear-gradient(135deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.dark})`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                mr: 2,
                                boxShadow: theme.shadows[3],
                              }}
                            >
                              <Settings size={20} color='white' />
                            </Box>
                            <Typography
                              variant='h5'
                              sx={{
                                fontWeight: 700,
                                color: theme.palette.secondary.main,
                                fontSize: '1.5rem',
                              }}
                            >
                              ⚙️ 独立模组项目
                            </Typography>
                            <Chip
                              label={modProjects.length}
                              size='small'
                              color='secondary'
                              sx={{ ml: 2 }}
                            />
                          </Box>
                          <Grid container spacing={3}>
                            {modProjects.map(project => (
                              <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
                                <motion.div
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ duration: 0.3 }}
                                >
                                  <Card
                                    sx={{
                                      height: '100%',
                                      display: 'flex',
                                      flexDirection: 'column',
                                      cursor: 'pointer',
                                      transition: 'all 0.3s ease',
                                      border:
                                        currentProject?.id === project.id
                                          ? `2px solid ${theme.palette.secondary.main}`
                                          : `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
                                      borderRadius: 2,
                                      '&:hover': {
                                        transform: 'translateY(-6px)',
                                        boxShadow: theme.shadows[12],
                                        borderColor: theme.palette.secondary.main,
                                      },
                                    }}
                                    onClick={() => handleOpenProject(project)}
                                  >
                                    <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                        <Chip
                                          label='独立模组'
                                          color='secondary'
                                          size='small'
                                          sx={{ fontWeight: 600 }}
                                        />
                                      </Box>
                                      <Typography
                                        variant='h6'
                                        sx={{ mb: 1, fontWeight: 700, fontSize: '1.1rem' }}
                                      >
                                        {project.name}
                                      </Typography>
                                      <Typography
                                        variant='body2'
                                        color='text.secondary'
                                        sx={{ mb: 2, lineHeight: 1.5 }}
                                      >
                                        {project.description || '暂无描述'}
                                      </Typography>
                                      <Typography
                                        variant='caption'
                                        color='text.secondary'
                                        sx={{ fontWeight: 500 }}
                                      >
                                        最后修改: {project.lastModified.toLocaleDateString()}
                                      </Typography>
                                    </CardContent>
                                    <CardActions
                                      sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}
                                    >
                                      <Box sx={{ display: 'flex', gap: 1 }}>
                                        <IconButton
                                          size='small'
                                          color='primary'
                                          onClick={e => {
                                            e.stopPropagation()
                                            handleOpenProject(project)
                                          }}
                                          title='打开项目'
                                        >
                                          <FolderOpen size={16} />
                                        </IconButton>
                                        <IconButton
                                          size='small'
                                          color='info'
                                          onClick={e => {
                                            e.stopPropagation()
                                            handleScanProject(project.id)
                                          }}
                                          title='扫描项目'
                                          disabled={scanningProject === project.id}
                                        >
                                          <Scan size={16} />
                                        </IconButton>
                                        {project.scanResults && (
                                          <IconButton
                                            size='small'
                                            onClick={e => {
                                              e.stopPropagation()
                                              toggleProjectExpansion(project.id)
                                            }}
                                            title={
                                              expandedProjects.has(project.id)
                                                ? '收起详情'
                                                : '展开详情'
                                            }
                                          >
                                            {expandedProjects.has(project.id) ? (
                                              <ChevronUp size={16} />
                                            ) : (
                                              <ChevronDown size={16} />
                                            )}
                                          </IconButton>
                                        )}
                                      </Box>
                                      <IconButton
                                        size='small'
                                        color='error'
                                        onClick={e => {
                                          e.stopPropagation()
                                          handleDeleteProject(project.id)
                                        }}
                                        title='删除项目'
                                      >
                                        <Trash2 size={16} />
                                      </IconButton>
                                    </CardActions>

                                    <Collapse
                                      in={expandedProjects.has(project.id)}
                                      timeout='auto'
                                      unmountOnExit
                                    >
                                      <Box sx={{ px: 2, pb: 2 }}>
                                        <Divider sx={{ mb: 2 }} />
                                        {renderScanResults(project)}
                                      </Box>
                                    </Collapse>
                                  </Card>
                                </motion.div>
                              </Grid>
                            ))}
                          </Grid>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )
                )
              })()}
            </Box>
          )}

          {/* ProjectScan组件 */}
          {showProjectScan && (
            <ProjectScan
              onScanComplete={handleScanComplete}
              onCreateProject={handleProjectCreated}
            />
          )}

          {/* 新建项目对话框 */}
          <Dialog
            open={createDialogOpen}
            onClose={() => setCreateDialogOpen(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>新建项目</DialogTitle>
            <DialogContent>
              <Box sx={{ pt: 2 }}>
                <TextField
                  autoFocus
                  margin='dense'
                  label='项目名称'
                  fullWidth
                  variant='outlined'
                  value={newProjectName}
                  onChange={e => setNewProjectName(e.target.value)}
                  sx={{ mb: 2 }}
                />
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>项目类型</InputLabel>
                  <Select
                    value={newProjectType}
                    label='项目类型'
                    onChange={e => setNewProjectType(e.target.value as 'modpack' | 'mod')}
                  >
                    <MenuItem value='modpack'>模组包</MenuItem>
                    <MenuItem value='mod'>独立模组</MenuItem>
                  </Select>
                </FormControl>
                <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                  <TextField
                    label='项目路径'
                    fullWidth
                    variant='outlined'
                    value={newProjectPath}
                    onChange={e => setNewProjectPath(e.target.value)}
                    placeholder='选择项目保存位置'
                  />
                  <Button
                    variant='outlined'
                    onClick={handleSelectProjectPath}
                    sx={{ minWidth: 100 }}
                  >
                    浏览
                  </Button>
                </Box>
                <TextField
                  label='项目描述（可选）'
                  fullWidth
                  multiline
                  rows={3}
                  variant='outlined'
                  value={newProjectDescription}
                  onChange={e => setNewProjectDescription(e.target.value)}
                  placeholder='简要描述这个项目的用途和特点'
                />
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setCreateDialogOpen(false)}>取消</Button>
              <Button
                onClick={handleConfirmCreate}
                variant='contained'
                disabled={!newProjectName.trim()}
              >
                创建
              </Button>
            </DialogActions>
          </Dialog>
        </motion.div>
      </Box>
    </Box>
  )
}

export default ProjectPage
