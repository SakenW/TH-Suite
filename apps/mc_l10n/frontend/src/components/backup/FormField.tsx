/**
 * 表单字段组件
 * 统一的表单输入组件，支持多种字段类型和验证
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  TextField,
  FormControl,
  FormLabel,
  FormHelperText,
  FormControlLabel,
  Switch,
  Checkbox,
  Radio,
  RadioGroup,
  Select,
  MenuItem,
  Chip,
  Autocomplete,
  Slider,
  Typography,
  InputAdornment,
  IconButton,
  Paper,
  Stack,
  Avatar,
} from '@mui/material'
import { useTheme, alpha } from '@mui/material/styles'
import { DatePicker, TimePicker, DateTimePicker } from '@mui/x-date-pickers'
import {
  Eye,
  EyeOff,
  Calendar,
  Clock,
  Search,
  Upload,
  X,
  Plus,
  File,
  Image,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export type FieldType =
  | 'text'
  | 'email'
  | 'password'
  | 'number'
  | 'tel'
  | 'url'
  | 'textarea'
  | 'select'
  | 'multiselect'
  | 'autocomplete'
  | 'checkbox'
  | 'switch'
  | 'radio'
  | 'slider'
  | 'date'
  | 'time'
  | 'datetime'
  | 'file'
  | 'image'
  | 'color'
  | 'tags'

export interface FieldOption {
  value: any
  label: string
  disabled?: boolean
  icon?: React.ReactNode
  description?: string
  avatar?: string
}

export interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  pattern?: RegExp
  custom?: (value: any) => string | null
}

export interface FormFieldProps {
  name: string
  label: string
  type: FieldType
  value?: any
  onChange: (value: any) => void

  // 验证
  validation?: ValidationRule
  error?: string
  helperText?: string

  // 选项（用于 select、radio 等）
  options?: FieldOption[]

  // 样式和行为
  placeholder?: string
  disabled?: boolean
  readonly?: boolean
  fullWidth?: boolean
  size?: 'small' | 'medium'
  variant?: 'outlined' | 'filled' | 'standard'

  // 特殊属性
  multiline?: boolean
  rows?: number
  maxRows?: number
  multiple?: boolean
  allowCustom?: boolean // 用于 autocomplete 和 tags

  // 数值相关
  min?: number
  max?: number
  step?: number

  // 文件相关
  accept?: string
  maxSize?: number // MB
  maxFiles?: number

  // 样式定制
  startAdornment?: React.ReactNode
  endAdornment?: React.ReactNode

  // 事件回调
  onFocus?: () => void
  onBlur?: () => void
}

export const FormField: React.FC<FormFieldProps> = ({
  name,
  label,
  type,
  value = '',
  onChange,
  validation,
  error,
  helperText,
  options = [],
  placeholder,
  disabled = false,
  readonly = false,
  fullWidth = true,
  size = 'medium',
  variant = 'outlined',
  multiline = false,
  rows = 4,
  maxRows,
  multiple = false,
  allowCustom = false,
  min,
  max,
  step = 1,
  accept,
  maxSize = 10,
  maxFiles = 1,
  startAdornment,
  endAdornment,
  onFocus,
  onBlur,
}) => {
  const theme = useTheme()
  const [showPassword, setShowPassword] = useState(false)
  const [internalError, setInternalError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  // 表单验证
  useEffect(() => {
    if (validation && value !== undefined && value !== '') {
      const validateValue = () => {
        if (validation.required && (!value || (Array.isArray(value) && value.length === 0))) {
          return '此字段为必填项'
        }

        if (validation.min !== undefined) {
          if (typeof value === 'string' && value.length < validation.min) {
            return `最少需要 ${validation.min} 个字符`
          }
          if (typeof value === 'number' && value < validation.min) {
            return `最小值为 ${validation.min}`
          }
        }

        if (validation.max !== undefined) {
          if (typeof value === 'string' && value.length > validation.max) {
            return `最多允许 ${validation.max} 个字符`
          }
          if (typeof value === 'number' && value > validation.max) {
            return `最大值为 ${validation.max}`
          }
        }

        if (validation.pattern && typeof value === 'string' && !validation.pattern.test(value)) {
          return '格式不正确'
        }

        if (validation.custom) {
          return validation.custom(value)
        }

        return null
      }

      setInternalError(validateValue())
    } else {
      setInternalError(null)
    }
  }, [value, validation])

  const displayError = error || internalError
  const hasError = Boolean(displayError)

  // 密码字段的眼睛图标
  const getPasswordAdornment = () => (
    <InputAdornment position='end'>
      <IconButton
        aria-label='切换密码显示'
        onClick={() => setShowPassword(!showPassword)}
        edge='end'
        size='small'
      >
        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
      </IconButton>
    </InputAdornment>
  )

  // 文件上传处理
  const handleFileChange = (files: FileList | null) => {
    if (!files) return

    const fileArray = Array.from(files)
    const validFiles = fileArray.filter(file => {
      if (maxSize && file.size > maxSize * 1024 * 1024) {
        setInternalError(`文件 ${file.name} 超过了 ${maxSize}MB 的大小限制`)
        return false
      }
      return true
    })

    if (validFiles.length > 0) {
      setInternalError(null)
      onChange(multiple ? validFiles : validFiles[0])
    }
  }

  // 标签输入处理
  const handleTagsChange = (newValue: string[]) => {
    onChange(newValue)
  }

  // 拖拽文件处理
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files)
    }
  }

  // 渲染基础文本输入
  const renderTextField = () => (
    <TextField
      name={name}
      label={label}
      type={type === 'password' ? (showPassword ? 'text' : 'password') : type}
      value={value}
      onChange={e => onChange(e.target.value)}
      onFocus={onFocus}
      onBlur={onBlur}
      placeholder={placeholder}
      disabled={disabled}
      readOnly={readonly}
      fullWidth={fullWidth}
      size={size}
      variant={variant}
      multiline={multiline}
      rows={multiline ? rows : undefined}
      maxRows={maxRows}
      error={hasError}
      helperText={displayError || helperText}
      InputProps={{
        startAdornment: startAdornment,
        endAdornment: type === 'password' ? getPasswordAdornment() : endAdornment,
        inputProps: {
          min: min,
          max: max,
          step: step,
        },
      }}
    />
  )

  // 渲染选择器
  const renderSelect = () => (
    <FormControl fullWidth={fullWidth} size={size} error={hasError} disabled={disabled}>
      <FormLabel>{label}</FormLabel>
      <Select
        value={value}
        onChange={e => onChange(e.target.value)}
        multiple={multiple}
        variant={variant}
        displayEmpty
        renderValue={
          multiple
            ? (selected: any[]) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map(val => {
                    const option = options.find(opt => opt.value === val)
                    return (
                      <Chip
                        key={val}
                        label={option?.label || val}
                        size='small'
                        sx={{ height: 24 }}
                      />
                    )
                  })}
                </Box>
              )
            : undefined
        }
      >
        {placeholder && (
          <MenuItem value='' disabled>
            <em>{placeholder}</em>
          </MenuItem>
        )}
        {options.map(option => (
          <MenuItem
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            {option.icon && option.icon}
            {option.avatar && <Avatar src={option.avatar} sx={{ width: 24, height: 24 }} />}
            <Box>
              <Typography variant='body2'>{option.label}</Typography>
              {option.description && (
                <Typography variant='caption' color='text.secondary'>
                  {option.description}
                </Typography>
              )}
            </Box>
          </MenuItem>
        ))}
      </Select>
      {(displayError || helperText) && (
        <FormHelperText>{displayError || helperText}</FormHelperText>
      )}
    </FormControl>
  )

  // 渲染自动完成
  const renderAutocomplete = () => (
    <Autocomplete
      options={options}
      value={value}
      onChange={(_, newValue) => onChange(newValue)}
      getOptionLabel={(option: FieldOption) => option.label}
      isOptionEqualToValue={(option, value) => option.value === value?.value}
      disabled={disabled}
      multiple={multiple}
      freeSolo={allowCustom}
      size={size}
      renderInput={params => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          error={hasError}
          helperText={displayError || helperText}
          variant={variant}
        />
      )}
      renderOption={(props, option) => (
        <Box component='li' {...props} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {option.icon}
          {option.avatar && <Avatar src={option.avatar} sx={{ width: 24, height: 24 }} />}
          <Box>
            <Typography variant='body2'>{option.label}</Typography>
            {option.description && (
              <Typography variant='caption' color='text.secondary'>
                {option.description}
              </Typography>
            )}
          </Box>
        </Box>
      )}
      renderTags={(tagValue, getTagProps) =>
        tagValue.map((option, index) => (
          <Chip
            {...getTagProps({ index })}
            key={option.value}
            label={option.label}
            size='small'
            icon={option.icon}
            avatar={
              option.avatar ? (
                <Avatar src={option.avatar} sx={{ width: 24, height: 24 }} />
              ) : undefined
            }
          />
        ))
      }
    />
  )

  // 渲染标签输入
  const renderTagsField = () => (
    <Autocomplete
      multiple
      freeSolo
      options={[]}
      value={value || []}
      onChange={(_, newValue) => handleTagsChange(newValue as string[])}
      renderTags={(tagValue, getTagProps) =>
        tagValue.map((option, index) => (
          <Chip
            {...getTagProps({ index })}
            key={index}
            label={option}
            size='small'
            onDelete={() => {
              const newTags = [...value]
              newTags.splice(index, 1)
              handleTagsChange(newTags)
            }}
          />
        ))
      }
      renderInput={params => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder || '输入后按回车添加标签'}
          error={hasError}
          helperText={displayError || helperText}
          variant={variant}
        />
      )}
    />
  )

  // 渲染文件上传
  const renderFileUpload = () => (
    <FormControl fullWidth={fullWidth} error={hasError}>
      <FormLabel>{label}</FormLabel>
      <Paper
        variant='outlined'
        sx={{
          p: 3,
          textAlign: 'center',
          cursor: disabled ? 'not-allowed' : 'pointer',
          border: dragActive
            ? `2px dashed ${theme.palette.primary.main}`
            : hasError
              ? `2px dashed ${theme.palette.error.main}`
              : `2px dashed ${theme.palette.divider}`,
          backgroundColor: dragActive
            ? alpha(theme.palette.primary.main, 0.05)
            : hasError
              ? alpha(theme.palette.error.main, 0.05)
              : 'transparent',
          transition: 'all 0.2s ease-in-out',
          '&:hover': disabled
            ? {}
            : {
                backgroundColor: alpha(theme.palette.primary.main, 0.02),
                borderColor: theme.palette.primary.main,
              },
        }}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => {
          if (!disabled) {
            document.getElementById(`file-input-${name}`)?.click()
          }
        }}
      >
        <input
          id={`file-input-${name}`}
          type='file'
          accept={accept}
          multiple={multiple}
          onChange={e => handleFileChange(e.target.files)}
          style={{ display: 'none' }}
          disabled={disabled}
        />

        <Box sx={{ mb: 2 }}>{type === 'image' ? <Image size={48} /> : <Upload size={48} />}</Box>

        <Typography variant='body1' sx={{ mb: 1 }}>
          拖拽文件到此处或 <strong>点击选择</strong>
        </Typography>

        <Typography variant='body2' color='text.secondary'>
          {accept && `支持格式: ${accept}`}
          {maxSize && ` • 最大 ${maxSize}MB`}
          {multiple && maxFiles && ` • 最多 ${maxFiles} 个文件`}
        </Typography>

        {value && (
          <Box sx={{ mt: 2 }}>
            {Array.isArray(value) ? (
              <Stack spacing={1}>
                {value.map((file: File, index: number) => (
                  <Chip
                    key={index}
                    label={file.name}
                    size='small'
                    icon={<File size={16} />}
                    onDelete={() => {
                      const newFiles = [...value]
                      newFiles.splice(index, 1)
                      onChange(newFiles)
                    }}
                  />
                ))}
              </Stack>
            ) : (
              <Chip
                label={value.name}
                size='small'
                icon={<File size={16} />}
                onDelete={() => onChange(null)}
              />
            )}
          </Box>
        )}
      </Paper>
      {(displayError || helperText) && (
        <FormHelperText>{displayError || helperText}</FormHelperText>
      )}
    </FormControl>
  )

  // 渲染滑块
  const renderSlider = () => (
    <FormControl fullWidth={fullWidth} error={hasError}>
      <FormLabel sx={{ mb: 1 }}>{label}</FormLabel>
      <Box sx={{ px: 2 }}>
        <Slider
          value={value}
          onChange={(_, newValue) => onChange(newValue)}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          valueLabelDisplay='auto'
          marks={step === 1 && max && max <= 10}
        />
      </Box>
      {(displayError || helperText) && (
        <FormHelperText sx={{ mx: 0 }}>{displayError || helperText}</FormHelperText>
      )}
    </FormControl>
  )

  // 根据字段类型渲染对应组件
  switch (type) {
    case 'text':
    case 'email':
    case 'password':
    case 'number':
    case 'tel':
    case 'url':
    case 'textarea':
      return renderTextField()

    case 'select':
    case 'multiselect':
      return renderSelect()

    case 'autocomplete':
      return renderAutocomplete()

    case 'tags':
      return renderTagsField()

    case 'checkbox':
      return (
        <FormControlLabel
          control={
            <Checkbox
              checked={Boolean(value)}
              onChange={e => onChange(e.target.checked)}
              disabled={disabled}
              size={size}
            />
          }
          label={label}
          disabled={disabled}
        />
      )

    case 'switch':
      return (
        <FormControlLabel
          control={
            <Switch
              checked={Boolean(value)}
              onChange={e => onChange(e.target.checked)}
              disabled={disabled}
              size={size}
            />
          }
          label={label}
          disabled={disabled}
        />
      )

    case 'radio':
      return (
        <FormControl component='fieldset' error={hasError} disabled={disabled}>
          <FormLabel component='legend'>{label}</FormLabel>
          <RadioGroup value={value} onChange={e => onChange(e.target.value)}>
            {options.map(option => (
              <FormControlLabel
                key={option.value}
                value={option.value}
                control={<Radio size={size} />}
                label={option.label}
                disabled={option.disabled}
              />
            ))}
          </RadioGroup>
          {(displayError || helperText) && (
            <FormHelperText>{displayError || helperText}</FormHelperText>
          )}
        </FormControl>
      )

    case 'slider':
      return renderSlider()

    case 'file':
    case 'image':
      return renderFileUpload()

    case 'color':
      return (
        <FormControl fullWidth={fullWidth} error={hasError}>
          <FormLabel>{label}</FormLabel>
          <TextField
            type='color'
            value={value}
            onChange={e => onChange(e.target.value)}
            disabled={disabled}
            variant={variant}
            size={size}
            sx={{ '& input': { height: 40, cursor: 'pointer' } }}
          />
          {(displayError || helperText) && (
            <FormHelperText>{displayError || helperText}</FormHelperText>
          )}
        </FormControl>
      )

    default:
      return renderTextField()
  }
}
