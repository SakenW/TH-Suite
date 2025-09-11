/**
 * 创建项目对话框组件
 * 使用新的 API 架构和表单验证
 */

import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Alert,
  Chip,
  LinearProgress,
  Grid,
  Card,
  CardContent,
  IconButton,
} from '@mui/material'
import { useTheme, alpha } from '@mui/material/styles'
import { FolderOpen, Package, FileImage, Layers, X, CheckCircle, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { CreateProjectRequest } from '../../types/api'
import { useApi } from '../../hooks/useApi'
import { projectService } from '../../services'
import { tauriService } from '../../services'
import toast from 'react-hot-toast'

interface CreateProjectDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

interface FormData extends CreateProjectRequest {
  [key: string]: any
}

const PROJECT_TYPES = [
  {
    value: 'mod' as const,
    label: '模组项目',
    description: '单个模组开发项目',
    icon: <Package size={20} />,
    color: '#2196F3',
  },
  {
    value: 'resource_pack' as const,
    label: '资源包项目',
    description: '材质包或数据包项目',
    icon: <FileImage size={20} />,
    color: '#FF9800',
  },
  {
    value: 'mixed' as const,
    label: '混合项目',
    description: '包含多种类型的复合项目',
    icon: <Layers size={20} />,
    color: '#9C27B0',
  },
]

const COMMON_LANGUAGES = [
  { code: 'zh_cn', name: '简体中文' },
  { code: 'zh_tw', name: '繁体中文' },
  { code: 'en_us', name: 'English (US)' },
  { code: 'ja_jp', name: '日本語' },
  { code: 'ko_kr', name: '한국어' },
  { code: 'ru_ru', name: 'Русский' },
  { code: 'fr_fr', name: 'Français' },
  { code: 'de_de', name: 'Deutsch' },
  { code: 'es_es', name: 'Español' },
  { code: 'pt_br', name: 'Português (Brasil)' },
]

export const CreateProjectDialog: React.FC<CreateProjectDialogProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const theme = useTheme()
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    source_path: '',
    output_path: '',
    project_type: 'mod',
    default_language: 'en_us',
    supported_languages: ['en_us'],
  })

  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({})
  const [pathValidation, setPathValidation] = useState<{
    valid: boolean
    message?: string
    suggestions?: string[]
  } | null>(null)

  // API hooks
  const { execute: createProject, loading: creating } = useApi(
    () => projectService.createProject(formData),
    false,
  )

  const { execute: validatePath, loading: validatingPath } = useApi(
    () => projectService.validateProjectPath(formData.source_path),
    false,
  )

  const handleClose = () => {
    if (!creating) {
      setFormData({
        name: '',
        description: '',
        source_path: '',
        output_path: '',
        project_type: 'mod',
        default_language: 'en_us',
        supported_languages: ['en_us'],
      })
      setErrors({})
      setPathValidation(null)
      onClose()
    }
  }

  const handleInputChange = (field: keyof FormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }))

    // 清除对应字段的错误
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined,
      }))
    }
  }

  const handleSelectPath = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory({
        title: '选择项目源目录',
      })

      if (selectedPath) {
        handleInputChange('source_path', selectedPath)

        // 自动验证路径
        setTimeout(() => {
          validateProjectPath()
        }, 500)

        // 如果没有设置项目名称，从路径中提取
        if (!formData.name) {
          const folderName = selectedPath.split(/[/\\]/).pop()
          if (folderName) {
            handleInputChange('name', folderName)
          }
        }
      }
    } catch (error) {
      toast.error('选择路径失败')
    }
  }

  const handleSelectOutputPath = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory({
        title: '选择输出目录',
      })

      if (selectedPath) {
        handleInputChange('output_path', selectedPath)
      }
    } catch (error) {
      toast.error('选择输出路径失败')
    }
  }

  const validateProjectPath = async () => {
    if (!formData.source_path.trim()) {
      setPathValidation(null)
      return
    }

    try {
      const result = await validatePath()
      if (result) {
        setPathValidation(result)
      }
    } catch (error) {
      setPathValidation({
        valid: false,
        message: '路径验证失败',
      })
    }
  }

  const handleAddLanguage = (languageCode: string) => {
    if (!formData.supported_languages.includes(languageCode)) {
      handleInputChange('supported_languages', [...formData.supported_languages, languageCode])
    }
  }

  const handleRemoveLanguage = (languageCode: string) => {
    if (languageCode !== formData.default_language) {
      handleInputChange(
        'supported_languages',
        formData.supported_languages.filter(lang => lang !== languageCode),
      )
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {}

    if (!formData.name.trim()) {
      newErrors.name = '项目名称不能为空'
    }

    if (!formData.source_path.trim()) {
      newErrors.source_path = '源路径不能为空'
    }

    if (!formData.supported_languages.length) {
      newErrors.supported_languages = '至少需要支持一种语言'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {
    if (!validateForm()) {
      return
    }

    try {
      const result = await createProject()
      if (result) {
        toast.success('项目创建成功！')
        onSuccess()
        handleClose()
      }
    } catch (error) {
      toast.error('创建项目失败')
    }
  }

  const selectedProjectType = PROJECT_TYPES.find(type => type.value === formData.project_type)

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth='md'
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          maxHeight: '90vh',
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 2,
                background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Package size={20} color='white' />
            </Box>
            <Box>
              <Typography variant='h6' sx={{ fontWeight: 700 }}>
                创建新项目
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                配置项目基本信息和语言支持
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={handleClose} disabled={creating}>
            <X size={20} />
          </IconButton>
        </Box>
      </DialogTitle>

      {creating && <LinearProgress />}

      <DialogContent sx={{ pt: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* 项目类型选择 */}
          <Box>
            <Typography variant='subtitle2' sx={{ mb: 2, fontWeight: 600 }}>
              项目类型
            </Typography>
            <Grid container spacing={2}>
              {PROJECT_TYPES.map(type => (
                <Grid item xs={12} sm={4} key={type.value}>
                  <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    <Card
                      sx={{
                        cursor: 'pointer',
                        border:
                          formData.project_type === type.value
                            ? `2px solid ${type.color}`
                            : `1px solid ${alpha(theme.palette.divider, 0.3)}`,
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          borderColor: type.color,
                          boxShadow: `0 4px 12px ${alpha(type.color, 0.2)}`,
                        },
                      }}
                      onClick={() => handleInputChange('project_type', type.value)}
                    >
                      <CardContent sx={{ textAlign: 'center', py: 2 }}>
                        <Box sx={{ color: type.color, mb: 1 }}>{type.icon}</Box>
                        <Typography variant='subtitle2' sx={{ fontWeight: 600, mb: 0.5 }}>
                          {type.label}
                        </Typography>
                        <Typography variant='caption' color='text.secondary'>
                          {type.description}
                        </Typography>
                      </CardContent>
                    </Card>
                  </motion.div>
                </Grid>
              ))}
            </Grid>
          </Box>

          {/* 基本信息 */}
          <Box>
            <Typography variant='subtitle2' sx={{ mb: 2, fontWeight: 600 }}>
              基本信息
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label='项目名称'
                value={formData.name}
                onChange={e => handleInputChange('name', e.target.value)}
                error={!!errors.name}
                helperText={errors.name}
                fullWidth
                disabled={creating}
              />

              <TextField
                label='项目描述（可选）'
                value={formData.description}
                onChange={e => handleInputChange('description', e.target.value)}
                multiline
                rows={2}
                fullWidth
                disabled={creating}
              />
            </Box>
          </Box>

          {/* 路径配置 */}
          <Box>
            <Typography variant='subtitle2' sx={{ mb: 2, fontWeight: 600 }}>
              路径配置
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    label='源路径'
                    value={formData.source_path}
                    onChange={e => handleInputChange('source_path', e.target.value)}
                    onBlur={validateProjectPath}
                    error={!!errors.source_path}
                    helperText={errors.source_path}
                    fullWidth
                    disabled={creating}
                    placeholder='项目源文件所在目录'
                  />
                  <Button
                    variant='outlined'
                    onClick={handleSelectPath}
                    disabled={creating}
                    sx={{ minWidth: 100, height: 56 }}
                    startIcon={<FolderOpen size={16} />}
                  >
                    浏览
                  </Button>
                </Box>

                {/* 路径验证结果 */}
                <AnimatePresence>
                  {pathValidation && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <Alert
                        severity={pathValidation.valid ? 'success' : 'warning'}
                        sx={{ mt: 1 }}
                        icon={
                          pathValidation.valid ? (
                            <CheckCircle size={16} />
                          ) : (
                            <AlertCircle size={16} />
                          )
                        }
                      >
                        {pathValidation.message}
                        {pathValidation.suggestions && pathValidation.suggestions.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            <Typography variant='caption'>建议:</Typography>
                            <ul style={{ margin: '4px 0', paddingLeft: 16 }}>
                              {pathValidation.suggestions.map((suggestion, index) => (
                                <li key={index}>
                                  <Typography variant='caption'>{suggestion}</Typography>
                                </li>
                              ))}
                            </ul>
                          </Box>
                        )}
                      </Alert>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Box>

              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  label='输出路径（可选）'
                  value={formData.output_path}
                  onChange={e => handleInputChange('output_path', e.target.value)}
                  fullWidth
                  disabled={creating}
                  placeholder='构建输出目录，留空使用默认位置'
                />
                <Button
                  variant='outlined'
                  onClick={handleSelectOutputPath}
                  disabled={creating}
                  sx={{ minWidth: 100, height: 56 }}
                  startIcon={<FolderOpen size={16} />}
                >
                  浏览
                </Button>
              </Box>
            </Box>
          </Box>

          {/* 语言配置 */}
          <Box>
            <Typography variant='subtitle2' sx={{ mb: 2, fontWeight: 600 }}>
              语言配置
            </Typography>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>默认语言</InputLabel>
              <Select
                value={formData.default_language}
                onChange={e => handleInputChange('default_language', e.target.value)}
                label='默认语言'
                disabled={creating}
              >
                {COMMON_LANGUAGES.map(lang => (
                  <MenuItem key={lang.code} value={lang.code}>
                    {lang.name} ({lang.code})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ mb: 2 }}>
              <Typography variant='body2' sx={{ mb: 1, fontWeight: 600 }}>
                支持的语言
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {formData.supported_languages.map(langCode => {
                  const lang = COMMON_LANGUAGES.find(l => l.code === langCode)
                  const isDefault = langCode === formData.default_language

                  return (
                    <Chip
                      key={langCode}
                      label={lang ? `${lang.name} (${lang.code})` : langCode}
                      variant={isDefault ? 'filled' : 'outlined'}
                      color={isDefault ? 'primary' : 'default'}
                      onDelete={isDefault ? undefined : () => handleRemoveLanguage(langCode)}
                      disabled={creating}
                    />
                  )
                })}
              </Box>

              <FormControl size='small' sx={{ minWidth: 200 }}>
                <InputLabel>添加语言</InputLabel>
                <Select
                  value=''
                  onChange={e => {
                    if (e.target.value) {
                      handleAddLanguage(e.target.value)
                    }
                  }}
                  label='添加语言'
                  disabled={creating}
                >
                  {COMMON_LANGUAGES.filter(
                    lang => !formData.supported_languages.includes(lang.code),
                  ).map(lang => (
                    <MenuItem key={lang.code} value={lang.code}>
                      {lang.name} ({lang.code})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            {errors.supported_languages && (
              <Alert severity='error' sx={{ mt: 1 }}>
                {errors.supported_languages}
              </Alert>
            )}
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} disabled={creating}>
          取消
        </Button>
        <Button
          onClick={handleSubmit}
          variant='contained'
          disabled={creating || !formData.name.trim() || !formData.source_path.trim()}
          sx={{
            minWidth: 100,
            background: selectedProjectType
              ? `linear-gradient(135deg, ${selectedProjectType.color}, ${alpha(selectedProjectType.color, 0.8)})`
              : undefined,
          }}
        >
          {creating ? '创建中...' : '创建项目'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
