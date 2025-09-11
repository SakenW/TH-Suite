import React from 'react'
import { Box, TextField, Button, Typography, IconButton } from '@mui/material'
import { FolderOpen, Folder, ExternalLink } from 'lucide-react'
import { TauriService } from '../services'

// 创建 Tauri 服务实例
const tauriService = new TauriService()
import { useTranslation } from '@hooks/useTranslation'
import toast from 'react-hot-toast'

interface DirectorySelectorProps {
  label: string
  value: string
  onChange: (path: string) => void
  placeholder?: string
  disabled?: boolean
  showOpenButton?: boolean
  fullWidth?: boolean
}

export const DirectorySelector: React.FC<DirectorySelectorProps> = ({
  label,
  value,
  onChange,
  placeholder = '',
  disabled = false,
  showOpenButton = true,
  fullWidth = true,
}) => {
  const { t } = useTranslation()

  const handleSelectDirectory = async () => {
    try {
      const selectedPath = await tauriService.selectDirectory({
        title: label,
        defaultPath: value || undefined,
      })

      if (selectedPath) {
        onChange(selectedPath)
        toast.success(t('common.directorySelected', 'Directory selected'))
      }
    } catch (error) {
      console.error('Failed to select directory:', error)
      toast.error(t('common.failedToSelectDirectory', 'Failed to select directory'))
    }
  }

  const handleOpenDirectory = async () => {
    if (value) {
      try {
        await tauriService.openPath(value)
      } catch (error) {
        console.error('Failed to open directory:', error)
        toast.error(t('common.failedToOpenDirectory', 'Failed to open directory'))
      }
    }
  }

  return (
    <Box>
      <TextField
        fullWidth={fullWidth}
        label={label}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        InputProps={{
          readOnly: false,
          endAdornment: (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <IconButton
                onClick={handleSelectDirectory}
                disabled={disabled}
                size='small'
                title={t('common.browse', 'Browse')}
              >
                <FolderOpen size={18} />
              </IconButton>
              {showOpenButton && value && (
                <IconButton
                  onClick={handleOpenDirectory}
                  disabled={disabled}
                  size='small'
                  title={t('common.openInExplorer', 'Open in Explorer')}
                >
                  <ExternalLink size={16} />
                </IconButton>
              )}
            </Box>
          ),
        }}
      />

      {value && (
        <Typography
          variant='caption'
          color='text.secondary'
          sx={{
            display: 'block',
            mt: 0.5,
            wordBreak: 'break-all',
            fontSize: '0.75rem',
          }}
          title={value}
        >
          {value}
        </Typography>
      )}
    </Box>
  )
}

export default DirectorySelector
