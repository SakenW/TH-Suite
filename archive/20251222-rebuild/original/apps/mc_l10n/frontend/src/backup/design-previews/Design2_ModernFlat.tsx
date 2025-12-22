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
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import RadarIcon from '@mui/icons-material/Radar'
import TuneIcon from '@mui/icons-material/Tune'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import DoneAllIcon from '@mui/icons-material/DoneAll'
import TranslateIcon from '@mui/icons-material/Translate'
import SportsEsportsIcon from '@mui/icons-material/SportsEsports'
import InventoryIcon from '@mui/icons-material/Inventory'

// 现代扁平化风格 - 清爽明亮的 Minecraft 主题
const ModernButton = styled(Button)(({ theme }) => ({
  background: 'linear-gradient(135deg, #7EC850 0%, #5BA633 100%)',
  color: '#FFFFFF',
  borderRadius: '12px',
  padding: '12px 24px',
  fontSize: '15px',
  fontWeight: 600,
  textTransform: 'none',
  boxShadow: '0 4px 12px rgba(126, 200, 80, 0.3)',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: 'linear-gradient(135deg, #8ED45A 0%, #6BB63D 100%)',
    transform: 'translateY(-2px)',
    boxShadow: '0 6px 20px rgba(126, 200, 80, 0.4)',
  },
  '&:active': {
    transform: 'translateY(0)',
  },
}))

const SecondaryButton = styled(Button)({
  background: '#FFFFFF',
  color: '#5BA633',
  borderRadius: '12px',
  border: '2px solid #7EC850',
  padding: '12px 24px',
  fontSize: '15px',
  fontWeight: 600,
  textTransform: 'none',
  transition: 'all 0.3s',
  '&:hover': {
    background: '#F0FFF0',
    borderColor: '#5BA633',
  },
})

const ModernCard = styled(Card)({
  background: '#FFFFFF',
  borderRadius: '16px',
  padding: '20px',
  boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)',
  border: '1px solid rgba(126, 200, 80, 0.1)',
  marginBottom: '16px',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.12)',
    transform: 'translateX(4px)',
    borderColor: 'rgba(126, 200, 80, 0.3)',
  },
})

const ModernPanel = styled(Paper)({
  background: '#FFFFFF',
  borderRadius: '20px',
  padding: '24px',
  boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
  border: '1px solid #F0F0F0',
})

const GradientProgress = styled(LinearProgress)({
  height: 8,
  borderRadius: 4,
  backgroundColor: '#E8F5E9',
  '& .MuiLinearProgress-bar': {
    borderRadius: 4,
    background: 'linear-gradient(90deg, #7EC850 0%, #5BA633 100%)',
  },
})

const StatusChip = styled(Chip, {
  shouldForwardProp: prop => prop !== 'status',
})<{ status: string }>(({ status }) => ({
  borderRadius: '8px',
  fontWeight: 600,
  fontSize: '12px',
  height: '28px',
  ...(status === 'completed' && {
    background: 'linear-gradient(135deg, #7EC850 0%, #5BA633 100%)',
    color: '#FFFFFF',
  }),
  ...(status === 'partial' && {
    background: 'linear-gradient(135deg, #FFB74D 0%, #FF9800 100%)',
    color: '#FFFFFF',
  }),
  ...(status === 'pending' && {
    background: 'linear-gradient(135deg, #FF7A7A 0%, #FF5252 100%)',
    color: '#FFFFFF',
  }),
  '& .MuiChip-label': {
    color: '#FFFFFF',
  },
}))

export default function Design2_ModernFlat() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #F5FFF5 0%, #E8F5E9 100%)',
        padding: 4,
      }}
    >
      {/* 顶部栏 */}
      <ModernPanel sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar
              sx={{
                width: 56,
                height: 56,
                background: 'linear-gradient(135deg, #7EC850 0%, #5BA633 100%)',
              }}
            >
              <SportsEsportsIcon sx={{ fontSize: 32 }} />
            </Avatar>
            <Box>
              <Typography
                variant='h4'
                sx={{
                  fontWeight: 700,
                  background: 'linear-gradient(135deg, #2E7D32 0%, #5BA633 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                TH Suite MC L10n
              </Typography>
              <Typography variant='body2' sx={{ color: '#757575' }}>
                Minecraft 本地化工具套件
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <SecondaryButton startIcon={<FolderOpenIcon />}>打开项目</SecondaryButton>
            <IconButton
              sx={{
                background: '#F5F5F5',
                '&:hover': { background: '#EEEEEE' },
              }}
            >
              <TuneIcon />
            </IconButton>
          </Box>
        </Box>
      </ModernPanel>

      {/* 快速统计卡片 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 3, mb: 4 }}>
        <Paper
          sx={{
            p: 3,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #FFFFFF 0%, #F0FFF0 100%)',
            border: '1px solid rgba(126, 200, 80, 0.2)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant='h4' sx={{ fontWeight: 700, color: '#2E7D32' }}>
                125
              </Typography>
              <Typography variant='body2' sx={{ color: '#757575' }}>
                模组总数
              </Typography>
            </Box>
            <InventoryIcon sx={{ fontSize: 40, color: '#7EC850' }} />
          </Box>
        </Paper>

        <Paper
          sx={{
            p: 3,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #FFFFFF 0%, #FFF3E0 100%)',
            border: '1px solid rgba(255, 152, 0, 0.2)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant='h4' sx={{ fontWeight: 700, color: '#F57C00' }}>
                72%
              </Typography>
              <Typography variant='body2' sx={{ color: '#757575' }}>
                总体进度
              </Typography>
            </Box>
            <RadarIcon sx={{ fontSize: 40, color: '#FF9800' }} />
          </Box>
        </Paper>

        <Paper
          sx={{
            p: 3,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #FFFFFF 0%, #E8F5E9 100%)',
            border: '1px solid rgba(126, 200, 80, 0.2)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant='h4' sx={{ fontWeight: 700, color: '#2E7D32' }}>
                90
              </Typography>
              <Typography variant='body2' sx={{ color: '#757575' }}>
                已完成
              </Typography>
            </Box>
            <DoneAllIcon sx={{ fontSize: 40, color: '#7EC850' }} />
          </Box>
        </Paper>

        <Paper
          sx={{
            p: 3,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #FFFFFF 0%, #FFEBEE 100%)',
            border: '1px solid rgba(255, 82, 82, 0.2)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant='h4' sx={{ fontWeight: 700, color: '#D32F2F' }}>
                35
              </Typography>
              <Typography variant='body2' sx={{ color: '#757575' }}>
                待处理
              </Typography>
            </Box>
            <TranslateIcon sx={{ fontSize: 40, color: '#FF5252' }} />
          </Box>
        </Paper>
      </Box>

      {/* 主内容区 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 4 }}>
        {/* 左侧项目列表 */}
        <ModernPanel>
          <Box
            sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <Typography variant='h5' sx={{ fontWeight: 600, color: '#2E7D32' }}>
              模组列表
            </Typography>
            <ModernButton size='small' startIcon={<RadarIcon />}>
              扫描模组
            </ModernButton>
          </Box>

          <ModernCard>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
                }}
              >
                TF
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                  <Typography variant='subtitle1' sx={{ fontWeight: 600, color: '#1A1A1A' }}>
                    Twilight Forest
                  </Typography>
                  <StatusChip label='已翻译' size='small' status='completed' />
                </Box>
                <Typography variant='caption' sx={{ color: '#757575' }}>
                  twilightforest-1.21.1-4.7.3196
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant='h6' sx={{ fontWeight: 700, color: '#2E7D32' }}>
                  85%
                </Typography>
              </Box>
            </Box>
            <GradientProgress variant='determinate' value={85} sx={{ mt: 2 }} />
          </ModernCard>

          <ModernCard>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)',
                }}
              >
                AE
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                  <Typography variant='subtitle1' sx={{ fontWeight: 600, color: '#1A1A1A' }}>
                    Applied Energistics 2
                  </Typography>
                  <StatusChip label='部分翻译' size='small' status='partial' />
                </Box>
                <Typography variant='caption' sx={{ color: '#757575' }}>
                  ae2-15.3.1-beta
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant='h6' sx={{ fontWeight: 700, color: '#F57C00' }}>
                  32%
                </Typography>
              </Box>
            </Box>
            <GradientProgress variant='determinate' value={32} sx={{ mt: 2 }} />
          </ModernCard>

          <ModernCard>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: 'linear-gradient(135deg, #7EC850 0%, #5BA633 100%)',
                }}
              >
                JEI
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                  <Typography variant='subtitle1' sx={{ fontWeight: 600, color: '#1A1A1A' }}>
                    Just Enough Items
                  </Typography>
                  <StatusChip label='完成' icon={<DoneAllIcon />} size='small' status='completed' />
                </Box>
                <Typography variant='caption' sx={{ color: '#757575' }}>
                  jei-1.21.1-20.1.16
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant='h6' sx={{ fontWeight: 700, color: '#2E7D32' }}>
                  100%
                </Typography>
              </Box>
            </Box>
            <GradientProgress variant='determinate' value={100} sx={{ mt: 2 }} />
          </ModernCard>
        </ModernPanel>

        {/* 右侧操作面板 */}
        <ModernPanel>
          <Typography variant='h5' sx={{ fontWeight: 600, color: '#2E7D32', mb: 3 }}>
            快速操作
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 4 }}>
            <ModernButton
              fullWidth
              size='large'
              startIcon={<RocketLaunchIcon />}
              sx={{ height: 56 }}
            >
              开始翻译流程
            </ModernButton>
            <SecondaryButton fullWidth startIcon={<TranslateIcon />}>
              导出语言包
            </SecondaryButton>
          </Box>

          <Box
            sx={{
              background: 'linear-gradient(135deg, #F5FFF5 0%, #E8F5E9 100%)',
              borderRadius: '12px',
              p: 3,
              border: '1px solid rgba(126, 200, 80, 0.2)',
            }}
          >
            <Typography variant='h6' sx={{ fontWeight: 600, color: '#2E7D32', mb: 2 }}>
              翻译进度概览
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant='body2' sx={{ color: '#424242' }}>
                    核心模组
                  </Typography>
                  <Typography variant='body2' sx={{ fontWeight: 600, color: '#2E7D32' }}>
                    95%
                  </Typography>
                </Box>
                <GradientProgress variant='determinate' value={95} />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant='body2' sx={{ color: '#424242' }}>
                    科技模组
                  </Typography>
                  <Typography variant='body2' sx={{ fontWeight: 600, color: '#F57C00' }}>
                    68%
                  </Typography>
                </Box>
                <GradientProgress variant='determinate' value={68} />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant='body2' sx={{ color: '#424242' }}>
                    魔法模组
                  </Typography>
                  <Typography variant='body2' sx={{ fontWeight: 600, color: '#F57C00' }}>
                    45%
                  </Typography>
                </Box>
                <GradientProgress variant='determinate' value={45} />
              </Box>
            </Box>
          </Box>
        </ModernPanel>
      </Box>
    </Box>
  )
}
