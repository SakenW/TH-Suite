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
  Avatar,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import FolderIcon from '@mui/icons-material/Folder'
import SearchIcon from '@mui/icons-material/Search'
import TuneIcon from '@mui/icons-material/Tune'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import CheckIcon from '@mui/icons-material/Check'
import DownloadIcon from '@mui/icons-material/Download'
import ForestIcon from '@mui/icons-material/Forest'
import WaterIcon from '@mui/icons-material/Water'
import WhatshotIcon from '@mui/icons-material/Whatshot'

// 材质包主题风格 - 自然木纹与矿石质感
const WoodButton = styled(Button)({
  background: 'linear-gradient(180deg, #8D6E63 0%, #6D4C41 50%, #5D4037 100%)',
  color: '#FFF8E1',
  borderRadius: '8px',
  padding: '14px 28px',
  fontSize: '15px',
  fontWeight: 600,
  textTransform: 'none',
  position: 'relative',
  overflow: 'hidden',
  border: '2px solid #5D4037',
  boxShadow: 'inset 0 2px 4px rgba(255, 248, 225, 0.2), 0 4px 8px rgba(62, 39, 35, 0.3)',
  '&::before': {
    content: '""',
    position: 'absolute',
    inset: 0,
    background:
      'url("data:image/svg+xml,%3Csvg width="100" height="100" xmlns="http://www.w3.org/2000/svg"%3E%3Cpath d="M0 0h100v100H0z" fill="%23000" opacity="0.05"/%3E%3Cpath d="M0 20h100v2H0zM0 40h100v1H0zM0 60h100v2H0zM0 80h100v1H0z" fill="%23000" opacity="0.1"/%3E%3C/svg%3E")',
    backgroundSize: '100px 100px',
  },
  transition: 'all 0.3s',
  '&:hover': {
    background: 'linear-gradient(180deg, #A1887F 0%, #8D6E63 50%, #6D4C41 100%)',
    transform: 'translateY(-2px)',
    boxShadow: 'inset 0 2px 6px rgba(255, 248, 225, 0.3), 0 6px 12px rgba(62, 39, 35, 0.4)',
  },
})

const DiamondButton = styled(Button)({
  background:
    'linear-gradient(135deg, #64B5F6 0%, #42A5F5 25%, #2196F3 50%, #1E88E5 75%, #1976D2 100%)',
  color: '#FFFFFF',
  borderRadius: '8px',
  padding: '14px 28px',
  fontSize: '15px',
  fontWeight: 600,
  textTransform: 'none',
  position: 'relative',
  border: '2px solid #1565C0',
  boxShadow: 'inset 0 0 20px rgba(255, 255, 255, 0.3), 0 4px 12px rgba(21, 101, 192, 0.4)',
  '&::after': {
    content: '""',
    position: 'absolute',
    top: '20%',
    left: '10%',
    width: '20px',
    height: '20px',
    background: 'radial-gradient(circle, rgba(255,255,255,0.8) 0%, transparent 70%)',
    borderRadius: '50%',
  },
  transition: 'all 0.3s',
  '&:hover': {
    background:
      'linear-gradient(135deg, #90CAF9 0%, #64B5F6 25%, #42A5F5 50%, #2196F3 75%, #1E88E5 100%)',
    boxShadow: 'inset 0 0 30px rgba(255, 255, 255, 0.4), 0 6px 16px rgba(21, 101, 192, 0.5)',
  },
})

const StonePanel = styled(Paper)({
  background: 'linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 50%, #9E9E9E 100%)',
  borderRadius: '12px',
  padding: '24px',
  position: 'relative',
  border: '3px solid #757575',
  boxShadow: 'inset 0 2px 4px rgba(255, 255, 255, 0.5), 0 8px 16px rgba(0, 0, 0, 0.2)',
  '&::before': {
    content: '""',
    position: 'absolute',
    inset: 0,
    borderRadius: '12px',
    background:
      'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0, 0, 0, 0.03) 10px, rgba(0, 0, 0, 0.03) 20px)',
  },
})

const OreCard = styled(Card)({
  background: 'linear-gradient(135deg, #FAFAFA 0%, #F5F5F5 100%)',
  borderRadius: '10px',
  padding: '18px',
  marginBottom: '14px',
  border: '2px solid #E0E0E0',
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: '-50%',
    right: '-50%',
    width: '200%',
    height: '200%',
    background: 'radial-gradient(circle, rgba(255, 193, 7, 0.1) 0%, transparent 70%)',
    transform: 'rotate(45deg)',
  },
  '&:hover': {
    transform: 'translateY(-3px)',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
    borderColor: '#FFC107',
  },
})

const EmeraldProgress = styled(LinearProgress)({
  height: 10,
  borderRadius: 5,
  backgroundColor: 'rgba(46, 125, 50, 0.2)',
  border: '1px solid #2E7D32',
  '& .MuiLinearProgress-bar': {
    borderRadius: 5,
    background: 'linear-gradient(90deg, #2E7D32 0%, #43A047 50%, #66BB6A 100%)',
    position: 'relative',
    overflow: 'hidden',
    '&::after': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      bottom: 0,
      right: 0,
      background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
      animation: 'shimmer 2s infinite',
    },
  },
  '@keyframes shimmer': {
    '0%': { transform: 'translateX(-100%)' },
    '100%': { transform: 'translateX(100%)' },
  },
})

const OreChip = styled(Chip, {
  shouldForwardProp: prop => prop !== 'ore',
})<{ ore: string }>(({ ore }) => ({
  borderRadius: '6px',
  fontWeight: 600,
  border: '2px solid',
  position: 'relative',
  overflow: 'hidden',
  ...(ore === 'emerald' && {
    background: 'linear-gradient(135deg, #2E7D32 0%, #43A047 100%)',
    color: '#E8F5E9',
    borderColor: '#1B5E20',
    '&::before': {
      content: '""',
      position: 'absolute',
      top: '30%',
      left: '20%',
      width: '8px',
      height: '8px',
      background: 'rgba(255, 255, 255, 0.6)',
      borderRadius: '50%',
    },
  }),
  ...(ore === 'gold' && {
    background: 'linear-gradient(135deg, #FFA000 0%, #FFB300 100%)',
    color: '#FFF8E1',
    borderColor: '#F57C00',
  }),
  ...(ore === 'iron' && {
    background: 'linear-gradient(135deg, #757575 0%, #616161 100%)',
    color: '#FAFAFA',
    borderColor: '#424242',
  }),
  '& .MuiChip-label': {
    color: 'inherit',
  },
}))

export default function Design5_TexturePack() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        background:
          'linear-gradient(180deg, #81C784 0%, #66BB6A 20%, #4CAF50 40%, #8D6E63 60%, #6D4C41 80%, #5D4037 100%)',
        padding: 4,
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'absolute',
          inset: 0,
          background:
            'url("data:image/svg+xml,%3Csvg width="60" height="60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23000" fill-opacity="0.03"%3E%3Cpath d="M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
        },
      }}
    >
      {/* 顶部栏 */}
      <StonePanel sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Avatar
              sx={{
                width: 64,
                height: 64,
                background: 'linear-gradient(135deg, #8BC34A 0%, #689F38 50%, #558B2F 100%)',
                border: '3px solid #33691E',
                boxShadow:
                  'inset 0 0 10px rgba(255, 255, 255, 0.3), 0 4px 8px rgba(51, 105, 30, 0.4)',
              }}
            >
              <ForestIcon sx={{ fontSize: 36, color: '#F1F8E9' }} />
            </Avatar>
            <Box>
              <Typography
                variant='h4'
                sx={{
                  fontWeight: 700,
                  color: '#3E2723',
                  textShadow: '2px 2px 4px rgba(255, 255, 255, 0.3)',
                  letterSpacing: '1px',
                }}
              >
                TH Suite MC L10n
              </Typography>
              <Typography
                variant='body2'
                sx={{
                  color: '#5D4037',
                  fontWeight: 500,
                }}
              >
                Minecraft 本地化工作台
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <WoodButton startIcon={<FolderIcon />}>打开世界</WoodButton>
            <IconButton
              sx={{
                background: 'linear-gradient(135deg, #FFD54F 0%, #FFC107 100%)',
                border: '2px solid #FFA000',
                '&:hover': {
                  background: 'linear-gradient(135deg, #FFE082 0%, #FFD54F 100%)',
                },
              }}
            >
              <TuneIcon sx={{ color: '#F57C00' }} />
            </IconButton>
          </Box>
        </Box>
      </StonePanel>

      {/* 资源统计 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 3, mb: 4 }}>
        {[
          { label: '模组总数', value: '125', icon: '⛏️', bg: '#9E9E9E' },
          { label: '已完成', value: '90', icon: '💎', bg: '#64B5F6' },
          { label: '进行中', value: '35', icon: '🏗️', bg: '#FFA726' },
          { label: '完成率', value: '72%', icon: '✨', bg: '#66BB6A' },
        ].map((stat, index) => (
          <Paper
            key={index}
            sx={{
              p: 2.5,
              background: `linear-gradient(135deg, ${stat.bg} 0%, ${stat.bg}DD 100%)`,
              border: '3px solid',
              borderColor: `${stat.bg}99`,
              borderRadius: '10px',
              boxShadow: 'inset 0 2px 4px rgba(255, 255, 255, 0.3), 0 4px 8px rgba(0, 0, 0, 0.2)',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography
                  variant='h4'
                  sx={{
                    fontWeight: 700,
                    color: '#FFFFFF',
                    textShadow: '2px 2px 4px rgba(0, 0, 0, 0.3)',
                  }}
                >
                  {stat.value}
                </Typography>
                <Typography
                  variant='body2'
                  sx={{
                    color: 'rgba(255, 255, 255, 0.9)',
                    fontWeight: 500,
                  }}
                >
                  {stat.label}
                </Typography>
              </Box>
              <Typography sx={{ fontSize: 36 }}>{stat.icon}</Typography>
            </Box>
          </Paper>
        ))}
      </Box>

      {/* 主内容区 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: 4 }}>
        {/* 左侧项目列表 */}
        <StonePanel>
          <Box
            sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <Typography
              variant='h5'
              sx={{
                fontWeight: 600,
                color: '#3E2723',
                textShadow: '1px 1px 2px rgba(255, 255, 255, 0.3)',
              }}
            >
              模组矿脉
            </Typography>
            <DiamondButton size='small' startIcon={<SearchIcon />}>
              探索
            </DiamondButton>
          </Box>

          <OreCard>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: 'linear-gradient(135deg, #7B1FA2 0%, #4A148C 100%)',
                  border: '2px solid #6A1B9A',
                }}
              >
                <WhatshotIcon sx={{ color: '#E1BEE7' }} />
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                  <Typography
                    variant='subtitle1'
                    sx={{
                      fontWeight: 600,
                      color: '#3E2723',
                    }}
                  >
                    Twilight Forest
                  </Typography>
                  <OreChip label='绿宝石' size='small' ore='emerald' />
                </Box>
                <Typography variant='caption' sx={{ color: '#757575' }}>
                  twilightforest-1.21.1-4.7.3196
                </Typography>
              </Box>
              <Typography
                variant='h6'
                sx={{
                  fontWeight: 700,
                  color: '#2E7D32',
                  textShadow: '1px 1px 2px rgba(46, 125, 50, 0.2)',
                }}
              >
                85%
              </Typography>
            </Box>
            <EmeraldProgress variant='determinate' value={85} sx={{ mt: 2 }} />
          </OreCard>

          <OreCard>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: 'linear-gradient(135deg, #1976D2 0%, #0D47A1 100%)',
                  border: '2px solid #1565C0',
                }}
              >
                <WaterIcon sx={{ color: '#BBDEFB' }} />
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                  <Typography
                    variant='subtitle1'
                    sx={{
                      fontWeight: 600,
                      color: '#3E2723',
                    }}
                  >
                    Applied Energistics 2
                  </Typography>
                  <OreChip label='金矿' size='small' ore='gold' />
                </Box>
                <Typography variant='caption' sx={{ color: '#757575' }}>
                  ae2-15.3.1-beta
                </Typography>
              </Box>
              <Typography
                variant='h6'
                sx={{
                  fontWeight: 700,
                  color: '#F57C00',
                  textShadow: '1px 1px 2px rgba(245, 124, 0, 0.2)',
                }}
              >
                32%
              </Typography>
            </Box>
            <EmeraldProgress variant='determinate' value={32} sx={{ mt: 2 }} />
          </OreCard>

          <OreCard>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: 'linear-gradient(135deg, #43A047 0%, #2E7D32 100%)',
                  border: '2px solid #388E3C',
                }}
              >
                <CheckIcon sx={{ color: '#C8E6C9' }} />
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                  <Typography
                    variant='subtitle1'
                    sx={{
                      fontWeight: 600,
                      color: '#3E2723',
                    }}
                  >
                    JEI (Just Enough Items)
                  </Typography>
                  <OreChip label='完成' icon={<CheckIcon />} size='small' ore='emerald' />
                </Box>
                <Typography variant='caption' sx={{ color: '#757575' }}>
                  jei-1.21.1-20.1.16
                </Typography>
              </Box>
              <Typography
                variant='h6'
                sx={{
                  fontWeight: 700,
                  color: '#2E7D32',
                  textShadow: '1px 1px 2px rgba(46, 125, 50, 0.2)',
                }}
              >
                100%
              </Typography>
            </Box>
            <EmeraldProgress variant='determinate' value={100} sx={{ mt: 2 }} />
          </OreCard>
        </StonePanel>

        {/* 右侧控制面板 */}
        <StonePanel>
          <Typography
            variant='h5'
            sx={{
              fontWeight: 600,
              color: '#3E2723',
              textShadow: '1px 1px 2px rgba(255, 255, 255, 0.3)',
              mb: 3,
            }}
          >
            工作台
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 4 }}>
            <DiamondButton
              fullWidth
              size='large'
              startIcon={<RocketLaunchIcon />}
              sx={{ height: 56 }}
            >
              开始合成翻译
            </DiamondButton>
            <WoodButton fullWidth startIcon={<DownloadIcon />}>
              导出资源包
            </WoodButton>
          </Box>

          <Box
            sx={{
              background: 'linear-gradient(135deg, #8D6E63 0%, #6D4C41 100%)',
              borderRadius: '8px',
              p: 3,
              border: '2px solid #5D4037',
              position: 'relative',
              overflow: 'hidden',
              '&::before': {
                content: '""',
                position: 'absolute',
                inset: 0,
                background:
                  'url("data:image/svg+xml,%3Csvg width="100" height="100" xmlns="http://www.w3.org/2000/svg"%3E%3Cpath d="M0 20h100v2H0zM0 40h100v1H0zM0 60h100v2H0zM0 80h100v1H0z" fill="%23000" opacity="0.1"/%3E%3C/svg%3E")',
                backgroundSize: '100px 100px',
              },
            }}
          >
            <Typography
              sx={{
                color: '#FFF8E1',
                fontWeight: 600,
                mb: 2,
                position: 'relative',
              }}
            >
              矿石分布
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, position: 'relative' }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography sx={{ color: '#FFECB3', fontSize: '14px' }}>核心模组</Typography>
                  <Typography sx={{ color: '#FFF8E1', fontWeight: 600 }}>95%</Typography>
                </Box>
                <EmeraldProgress variant='determinate' value={95} />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography sx={{ color: '#FFECB3', fontSize: '14px' }}>科技模组</Typography>
                  <Typography sx={{ color: '#FFF8E1', fontWeight: 600 }}>68%</Typography>
                </Box>
                <EmeraldProgress variant='determinate' value={68} />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography sx={{ color: '#FFECB3', fontSize: '14px' }}>魔法模组</Typography>
                  <Typography sx={{ color: '#FFF8E1', fontWeight: 600 }}>45%</Typography>
                </Box>
                <EmeraldProgress variant='determinate' value={45} />
              </Box>
            </Box>
          </Box>
        </StonePanel>
      </Box>
    </Box>
  )
}
