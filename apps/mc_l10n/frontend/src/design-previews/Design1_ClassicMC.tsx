import React from 'react'
import {
  Box,
  Paper,
  Button,
  Typography,
  Card,
  Chip,
  LinearProgress,
  IconButton,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import FolderIcon from '@mui/icons-material/Folder'
import SearchIcon from '@mui/icons-material/Search'
import SettingsIcon from '@mui/icons-material/Settings'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import LanguageIcon from '@mui/icons-material/Language'

// 经典 Minecraft 风格 - 仿制游戏内 GUI
const MCButton = styled(Button)({
  background: 'linear-gradient(to bottom, #8B8B8B 0%, #717171 50%, #5A5A5A 100%)',
  border: '3px solid',
  borderColor: '#FFFFFF #373737 #373737 #FFFFFF',
  boxShadow: 'inset 2px 2px 0px rgba(255,255,255,0.5), inset -2px -2px 0px rgba(0,0,0,0.5)',
  color: '#FFFFFF',
  fontFamily: '"Minecraft", "Courier New", monospace',
  fontSize: '14px',
  fontWeight: 'bold',
  textShadow: '2px 2px 0px #3F3F3F',
  padding: '10px 20px',
  textTransform: 'none',
  '&:hover': {
    background: 'linear-gradient(to bottom, #9D9D9D 0%, #828282 50%, #6B6B6B 100%)',
    borderColor: '#FFFFA0 #474747 #474747 #FFFFA0',
  },
  '&:active': {
    borderColor: '#373737 #FFFFFF #FFFFFF #373737',
    boxShadow: 'inset -2px -2px 0px rgba(255,255,255,0.5), inset 2px 2px 0px rgba(0,0,0,0.5)',
  },
})

const MCPanel = styled(Paper)({
  background: '#C6C6C6',
  border: '4px solid',
  borderColor: '#FFFFFF #555555 #555555 #FFFFFF',
  boxShadow: 'inset -2px -2px 0px #8B8B8B, inset 2px 2px 0px #FFFFFF',
  padding: '16px',
  borderRadius: 0,
})

const MCCard = styled(Card)({
  background: 'linear-gradient(135deg, #8B8B8B 0%, #C6C6C6 100%)',
  border: '2px solid',
  borderColor: '#DFDFDF #555555 #555555 #DFDFDF',
  borderRadius: 0,
  padding: '12px',
  marginBottom: '8px',
  transition: 'all 0.2s',
  '&:hover': {
    borderColor: '#FFFFFF #373737 #373737 #FFFFFF',
    transform: 'translateY(-1px)',
    boxShadow: '0 4px 8px rgba(0,0,0,0.3)',
  },
})

const MCProgress = styled(LinearProgress)({
  height: 20,
  backgroundColor: '#2D2D2D',
  border: '2px solid',
  borderColor: '#1A1A1A #4A4A4A #4A4A4A #1A1A1A',
  borderRadius: 0,
  '& .MuiLinearProgress-bar': {
    background: 'linear-gradient(to right, #5ADB5A 0%, #4BC74B 50%, #3AB73A 100%)',
    borderRadius: 0,
  },
})

const MCChip = styled(Chip)({
  background: '#5ADB5A',
  color: '#FFFFFF',
  border: '2px solid',
  borderColor: '#7FFF7F #2D6B2D #2D6B2D #7FFF7F',
  borderRadius: 0,
  fontWeight: 'bold',
  textShadow: '1px 1px 0px #2D6B2D',
  '& .MuiChip-label': {
    color: '#FFFFFF',
  },
})

export default function Design1_ClassicMC() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #2D2D2D 0%, #1A1A1A 100%)',
        padding: 4,
      }}
    >
      {/* 顶部栏 */}
      <MCPanel sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography
            variant='h4'
            sx={{
              fontFamily: '"Minecraft", monospace',
              color: '#4A4A4A',
              textShadow: '2px 2px 0px #FFFFFF',
              fontWeight: 'bold',
            }}
          >
            TH Suite MC L10n
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <MCButton startIcon={<FolderIcon />}>打开项目</MCButton>
            <MCButton startIcon={<SettingsIcon />}>设置</MCButton>
          </Box>
        </Box>
      </MCPanel>

      {/* 主内容区 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: 3 }}>
        {/* 左侧项目列表 */}
        <MCPanel>
          <Box
            sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <Typography
              variant='h6'
              sx={{
                color: '#3F3F3F',
                fontWeight: 'bold',
                textShadow: '1px 1px 0px #FFFFFF',
              }}
            >
              模组列表
            </Typography>
            <MCButton size='small' startIcon={<SearchIcon />}>
              扫描
            </MCButton>
          </Box>

          {/* 模组卡片 */}
          <MCCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography
                  variant='subtitle1'
                  sx={{
                    fontWeight: 'bold',
                    color: '#2D2D2D',
                    textShadow: '1px 1px 0px #FFFFFF',
                  }}
                >
                  Twilight Forest
                </Typography>
                <Typography variant='caption' sx={{ color: '#5A5A5A' }}>
                  twilightforest-1.21.1-4.7.3196
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <MCChip label='已翻译' size='small' />
                <Typography
                  sx={{
                    color: '#2D2D2D',
                    fontWeight: 'bold',
                    textShadow: '1px 1px 0px #DFDFDF',
                  }}
                >
                  85%
                </Typography>
              </Box>
            </Box>
            <MCProgress variant='determinate' value={85} sx={{ mt: 1 }} />
          </MCCard>

          <MCCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography
                  variant='subtitle1'
                  sx={{
                    fontWeight: 'bold',
                    color: '#2D2D2D',
                    textShadow: '1px 1px 0px #FFFFFF',
                  }}
                >
                  Applied Energistics 2
                </Typography>
                <Typography variant='caption' sx={{ color: '#5A5A5A' }}>
                  ae2-15.3.1-beta
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <Chip
                  label='未翻译'
                  size='small'
                  sx={{
                    background: '#DB5A5A',
                    color: '#FFFFFF',
                    border: '2px solid',
                    borderColor: '#FF7F7F #6B2D2D #6B2D2D #FF7F7F',
                    borderRadius: 0,
                    fontWeight: 'bold',
                    textShadow: '1px 1px 0px #6B2D2D',
                  }}
                />
                <Typography
                  sx={{
                    color: '#2D2D2D',
                    fontWeight: 'bold',
                    textShadow: '1px 1px 0px #DFDFDF',
                  }}
                >
                  32%
                </Typography>
              </Box>
            </Box>
            <MCProgress variant='determinate' value={32} sx={{ mt: 1 }} />
          </MCCard>

          <MCCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography
                  variant='subtitle1'
                  sx={{
                    fontWeight: 'bold',
                    color: '#2D2D2D',
                    textShadow: '1px 1px 0px #FFFFFF',
                  }}
                >
                  JEI (Just Enough Items)
                </Typography>
                <Typography variant='caption' sx={{ color: '#5A5A5A' }}>
                  jei-1.21.1-20.1.16
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <MCChip label='完成' icon={<CheckCircleIcon />} size='small' />
                <Typography
                  sx={{
                    color: '#2D2D2D',
                    fontWeight: 'bold',
                    textShadow: '1px 1px 0px #DFDFDF',
                  }}
                >
                  100%
                </Typography>
              </Box>
            </Box>
            <MCProgress variant='determinate' value={100} sx={{ mt: 1 }} />
          </MCCard>
        </MCPanel>

        {/* 右侧状态面板 */}
        <MCPanel>
          <Typography
            variant='h6'
            sx={{
              color: '#3F3F3F',
              fontWeight: 'bold',
              textShadow: '1px 1px 0px #FFFFFF',
              mb: 2,
            }}
          >
            项目状态
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography sx={{ color: '#4A4A4A', fontWeight: 'bold' }}>总进度</Typography>
              <Typography
                sx={{
                  color: '#2D2D2D',
                  fontWeight: 'bold',
                  textShadow: '1px 1px 0px #DFDFDF',
                }}
              >
                72%
              </Typography>
            </Box>
            <MCProgress variant='determinate' value={72} />
          </Box>

          <Box
            sx={{
              background: '#8B8B8B',
              border: '2px solid',
              borderColor: '#555555 #DFDFDF #DFDFDF #555555',
              p: 2,
              mb: 3,
            }}
          >
            <Typography
              sx={{
                color: '#FFFFFF',
                fontWeight: 'bold',
                textShadow: '1px 1px 0px #3F3F3F',
                mb: 1,
              }}
            >
              统计信息
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ color: '#E0E0E0', fontSize: '14px' }}>模组总数</Typography>
                <Typography sx={{ color: '#FFFFFF', fontWeight: 'bold' }}>125</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ color: '#E0E0E0', fontSize: '14px' }}>已翻译</Typography>
                <Typography sx={{ color: '#5ADB5A', fontWeight: 'bold' }}>90</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ color: '#E0E0E0', fontSize: '14px' }}>待翻译</Typography>
                <Typography sx={{ color: '#FFD700', fontWeight: 'bold' }}>35</Typography>
              </Box>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <MCButton fullWidth size='large' startIcon={<PlayArrowIcon />} sx={{ height: 48 }}>
              开始翻译
            </MCButton>
            <MCButton fullWidth startIcon={<LanguageIcon />}>
              导出语言包
            </MCButton>
          </Box>
        </MCPanel>
      </Box>
    </Box>
  )
}
