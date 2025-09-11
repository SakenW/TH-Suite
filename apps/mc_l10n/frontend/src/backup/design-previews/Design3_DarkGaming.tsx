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
import PlayCircleFilledIcon from '@mui/icons-material/PlayCircleFilled'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import LanguageIcon from '@mui/icons-material/Language'
import GrassIcon from '@mui/icons-material/Grass'
import DiamondIcon from '@mui/icons-material/Diamond'
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment'

// 深色游戏风格 - 高对比度的末影主题
const EnderButton = styled(Button)({
  background: 'linear-gradient(135deg, #9333EA 0%, #7C3AED 50%, #6B21A8 100%)',
  color: '#E0E7FF',
  borderRadius: '4px',
  padding: '12px 24px',
  fontSize: '14px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '1px',
  border: '2px solid #A855F7',
  boxShadow: '0 0 20px rgba(147, 51, 234, 0.4), inset 0 0 20px rgba(147, 51, 234, 0.2)',
  transition: 'all 0.3s',
  '&:hover': {
    background: 'linear-gradient(135deg, #A855F7 0%, #9333EA 50%, #7C3AED 100%)',
    boxShadow: '0 0 30px rgba(168, 85, 247, 0.6), inset 0 0 20px rgba(168, 85, 247, 0.3)',
    transform: 'translateY(-2px)',
  },
  '&:active': {
    transform: 'translateY(0)',
  },
})

const NetherButton = styled(Button)({
  background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 50%, #991B1B 100%)',
  color: '#FEF2F2',
  borderRadius: '4px',
  padding: '12px 24px',
  fontSize: '14px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '1px',
  border: '2px solid #EF4444',
  boxShadow: '0 0 20px rgba(220, 38, 38, 0.4), inset 0 0 20px rgba(220, 38, 38, 0.2)',
  '&:hover': {
    boxShadow: '0 0 30px rgba(239, 68, 68, 0.6), inset 0 0 20px rgba(239, 68, 68, 0.3)',
  },
})

const DarkPanel = styled(Paper)({
  background: 'linear-gradient(135deg, #1F1F2E 0%, #1A1A2E 100%)',
  borderRadius: '8px',
  padding: '24px',
  border: '1px solid #374151',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.5)',
})

const GameCard = styled(Card)({
  background: 'linear-gradient(135deg, #2D2D44 0%, #252538 100%)',
  borderRadius: '6px',
  padding: '16px',
  marginBottom: '12px',
  border: '1px solid #4B5563',
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(90deg, transparent, rgba(147, 51, 234, 0.2), transparent)',
    transition: 'left 0.5s',
  },
  '&:hover': {
    transform: 'translateX(8px)',
    borderColor: '#9333EA',
    boxShadow: '0 0 30px rgba(147, 51, 234, 0.3)',
    '&::before': {
      left: '100%',
    },
  },
})

const NeonProgress = styled(LinearProgress)({
  height: 12,
  borderRadius: 6,
  backgroundColor: '#1F1F2E',
  border: '1px solid #4B5563',
  '& .MuiLinearProgress-bar': {
    borderRadius: 6,
    background: 'linear-gradient(90deg, #10B981 0%, #34D399 50%, #6EE7B7 100%)',
    boxShadow: '0 0 10px rgba(16, 185, 129, 0.5)',
  },
})

const GlowChip = styled(Chip, {
  shouldForwardProp: prop => prop !== 'glow',
})<{ glow: string }>(({ glow }) => ({
  borderRadius: '4px',
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.5px',
  textTransform: 'uppercase',
  border: '1px solid',
  ...(glow === 'emerald' && {
    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
    color: '#ECFDF5',
    borderColor: '#34D399',
    boxShadow: '0 0 15px rgba(16, 185, 129, 0.5)',
  }),
  ...(glow === 'amber' && {
    background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
    color: '#FFFBEB',
    borderColor: '#FCD34D',
    boxShadow: '0 0 15px rgba(245, 158, 11, 0.5)',
  }),
  ...(glow === 'red' && {
    background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
    color: '#FEF2F2',
    borderColor: '#F87171',
    boxShadow: '0 0 15px rgba(239, 68, 68, 0.5)',
  }),
  '& .MuiChip-label': {
    color: 'inherit',
  },
}))

export default function Design3_DarkGaming() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0F0F1E 0%, #1A1A2E 50%, #16213E 100%)',
        padding: 4,
      }}
    >
      {/* 顶部栏 */}
      <DarkPanel sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box
              sx={{
                width: 56,
                height: 56,
                background: 'linear-gradient(135deg, #9333EA 0%, #6B21A8 100%)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 30px rgba(147, 51, 234, 0.5)',
              }}
            >
              <DiamondIcon sx={{ color: '#E0E7FF', fontSize: 32 }} />
            </Box>
            <Typography
              variant='h4'
              sx={{
                fontWeight: 800,
                background: 'linear-gradient(135deg, #E0E7FF 0%, #A78BFA 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                textShadow: '0 0 40px rgba(147, 51, 234, 0.5)',
                letterSpacing: '2px',
                textTransform: 'uppercase',
              }}
            >
              TH Suite MC L10n
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <IconButton
              sx={{
                color: '#E0E7FF',
                background: 'rgba(147, 51, 234, 0.2)',
                border: '1px solid #7C3AED',
                '&:hover': {
                  background: 'rgba(147, 51, 234, 0.3)',
                  boxShadow: '0 0 20px rgba(147, 51, 234, 0.5)',
                },
              }}
            >
              <FolderIcon />
            </IconButton>
            <IconButton
              sx={{
                color: '#E0E7FF',
                background: 'rgba(147, 51, 234, 0.2)',
                border: '1px solid #7C3AED',
                '&:hover': {
                  background: 'rgba(147, 51, 234, 0.3)',
                  boxShadow: '0 0 20px rgba(147, 51, 234, 0.5)',
                },
              }}
            >
              <SettingsIcon />
            </IconButton>
          </Box>
        </Box>
      </DarkPanel>

      {/* 主内容区 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 3 }}>
        {/* 左侧项目列表 */}
        <DarkPanel>
          <Box
            sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <Typography
              variant='h5'
              sx={{
                fontWeight: 700,
                color: '#E0E7FF',
                letterSpacing: '1px',
                textTransform: 'uppercase',
              }}
            >
              模组库
            </Typography>
            <EnderButton size='small' startIcon={<SearchIcon />}>
              扫描
            </EnderButton>
          </Box>

          <GameCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #6B21A8 100%)',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <LocalFireDepartmentIcon sx={{ color: '#E0E7FF' }} />
                </Box>
                <Box>
                  <Typography
                    variant='subtitle1'
                    sx={{
                      fontWeight: 700,
                      color: '#E0E7FF',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Twilight Forest
                  </Typography>
                  <Typography variant='caption' sx={{ color: '#9CA3AF' }}>
                    twilightforest-1.21.1-4.7.3196
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <GlowChip label='已翻译' size='small' glow='emerald' />
                <Typography
                  sx={{
                    color: '#10B981',
                    fontWeight: 700,
                    fontSize: '18px',
                    textShadow: '0 0 10px rgba(16, 185, 129, 0.5)',
                  }}
                >
                  85%
                </Typography>
              </Box>
            </Box>
            <NeonProgress variant='determinate' value={85} sx={{ mt: 2 }} />
          </GameCard>

          <GameCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    background: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <DiamondIcon sx={{ color: '#E0E7FF' }} />
                </Box>
                <Box>
                  <Typography
                    variant='subtitle1'
                    sx={{
                      fontWeight: 700,
                      color: '#E0E7FF',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Applied Energistics 2
                  </Typography>
                  <Typography variant='caption' sx={{ color: '#9CA3AF' }}>
                    ae2-15.3.1-beta
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <GlowChip label='部分' size='small' glow='amber' />
                <Typography
                  sx={{
                    color: '#F59E0B',
                    fontWeight: 700,
                    fontSize: '18px',
                    textShadow: '0 0 10px rgba(245, 158, 11, 0.5)',
                  }}
                >
                  32%
                </Typography>
              </Box>
            </Box>
            <NeonProgress variant='determinate' value={32} sx={{ mt: 2 }} />
          </GameCard>

          <GameCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <GrassIcon sx={{ color: '#E0E7FF' }} />
                </Box>
                <Box>
                  <Typography
                    variant='subtitle1'
                    sx={{
                      fontWeight: 700,
                      color: '#E0E7FF',
                      letterSpacing: '0.5px',
                    }}
                  >
                    JEI (Just Enough Items)
                  </Typography>
                  <Typography variant='caption' sx={{ color: '#9CA3AF' }}>
                    jei-1.21.1-20.1.16
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <GlowChip label='完成' icon={<CheckCircleIcon />} size='small' glow='emerald' />
                <Typography
                  sx={{
                    color: '#10B981',
                    fontWeight: 700,
                    fontSize: '18px',
                    textShadow: '0 0 10px rgba(16, 185, 129, 0.5)',
                  }}
                >
                  100%
                </Typography>
              </Box>
            </Box>
            <NeonProgress variant='determinate' value={100} sx={{ mt: 2 }} />
          </GameCard>
        </DarkPanel>

        {/* 右侧状态面板 */}
        <DarkPanel>
          <Typography
            variant='h5'
            sx={{
              fontWeight: 700,
              color: '#E0E7FF',
              letterSpacing: '1px',
              textTransform: 'uppercase',
              mb: 3,
            }}
          >
            任务中心
          </Typography>

          <Box sx={{ mb: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography
                sx={{
                  color: '#9CA3AF',
                  fontWeight: 600,
                  letterSpacing: '0.5px',
                  textTransform: 'uppercase',
                  fontSize: '12px',
                }}
              >
                全局进度
              </Typography>
              <Typography
                sx={{
                  color: '#10B981',
                  fontWeight: 700,
                  fontSize: '20px',
                  textShadow: '0 0 10px rgba(16, 185, 129, 0.5)',
                }}
              >
                72%
              </Typography>
            </Box>
            <NeonProgress variant='determinate' value={72} />
          </Box>

          <Box
            sx={{
              background: 'linear-gradient(135deg, #1F1F2E 0%, #252538 100%)',
              borderRadius: '6px',
              border: '1px solid #4B5563',
              p: 3,
              mb: 4,
            }}
          >
            <Typography
              sx={{
                color: '#E0E7FF',
                fontWeight: 700,
                letterSpacing: '0.5px',
                mb: 2,
                textTransform: 'uppercase',
                fontSize: '14px',
              }}
            >
              战绩统计
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ color: '#9CA3AF', fontSize: '14px' }}>模组总数</Typography>
                <Typography
                  sx={{
                    color: '#E0E7FF',
                    fontWeight: 700,
                    textShadow: '0 0 5px rgba(224, 231, 255, 0.3)',
                  }}
                >
                  125
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ color: '#9CA3AF', fontSize: '14px' }}>已完成</Typography>
                <Typography
                  sx={{
                    color: '#10B981',
                    fontWeight: 700,
                    textShadow: '0 0 10px rgba(16, 185, 129, 0.5)',
                  }}
                >
                  90
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ color: '#9CA3AF', fontSize: '14px' }}>进行中</Typography>
                <Typography
                  sx={{
                    color: '#F59E0B',
                    fontWeight: 700,
                    textShadow: '0 0 10px rgba(245, 158, 11, 0.5)',
                  }}
                >
                  35
                </Typography>
              </Box>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <EnderButton
              fullWidth
              size='large'
              startIcon={<PlayCircleFilledIcon />}
              sx={{ height: 56 }}
            >
              启动翻译
            </EnderButton>
            <NetherButton fullWidth startIcon={<LanguageIcon />}>
              导出语言包
            </NetherButton>
          </Box>
        </DarkPanel>
      </Box>
    </Box>
  )
}
