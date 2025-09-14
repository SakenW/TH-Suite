import React from 'react'
import { IconButton, Tooltip, Menu, MenuItem, Box, Typography } from '@mui/material'
import { Palette, Sun, Moon, Gamepad2, Contrast } from 'lucide-react'
import { useTheme, ThemeMode } from '../../contexts/ThemeContext'
import { minecraftColors } from '../../theme/minecraftTheme'

const themeIcons: Record<ThemeMode, React.ReactNode> = {
  minecraft: <Gamepad2 size={20} />,
  dark: <Moon size={20} />,
  light: <Sun size={20} />,
  highContrast: <Contrast size={20} />,
}

const themeLabels: Record<ThemeMode, string> = {
  minecraft: 'Minecraft 主题',
  dark: '暗色主题',
  light: '亮色主题',
  highContrast: '高对比度',
}

export const MinecraftThemeToggle: React.FC = () => {
  const { themeMode, setThemeMode, toggleTheme } = useTheme()
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    if (event.shiftKey) {
      // Shift+Click 快速切换
      toggleTheme()
    } else {
      // 普通点击打开菜单
      setAnchorEl(event.currentTarget)
    }
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleThemeSelect = (mode: ThemeMode) => {
    setThemeMode(mode)
    handleClose()
  }

  return (
    <>
      <Tooltip title={`主题: ${themeLabels[themeMode]} (Shift+点击快速切换)`}>
        <IconButton
          onClick={handleClick}
          sx={{
            color: themeMode === 'minecraft' ? minecraftColors.goldYellow : 'inherit',
            bgcolor: 'rgba(255,255,255,0.05)',
            '&:hover': {
              bgcolor: 'rgba(255,255,255,0.1)',
              transform: 'rotate(15deg)',
            },
            transition: 'all 0.3s',
          }}
        >
          {themeIcons[themeMode]}
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        PaperProps={{
          sx: {
            bgcolor: 'background.paper',
            border: '2px solid',
            borderColor: 'divider',
            borderRadius: themeMode === 'minecraft' ? 0 : 1,
            minWidth: 200,
          },
        }}
      >
        {(Object.keys(themeIcons) as ThemeMode[]).map(mode => (
          <MenuItem
            key={mode}
            onClick={() => handleThemeSelect(mode)}
            selected={themeMode === mode}
            sx={{
              fontFamily: '"Minecraft", monospace',
              '&.Mui-selected': {
                bgcolor: 'rgba(255,255,255,0.08)',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.12)',
                },
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              {themeIcons[mode]}
              <Typography variant='body2'>{themeLabels[mode]}</Typography>
            </Box>
          </MenuItem>
        ))}
      </Menu>
    </>
  )
}
