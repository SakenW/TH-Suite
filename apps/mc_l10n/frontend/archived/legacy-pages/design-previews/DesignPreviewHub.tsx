import React, { useState } from 'react'
import { Box, Typography, Button, Paper, Grid, Tabs, Tab } from '@mui/material'
import { styled } from '@mui/material/styles'
import DesignPreviewWrapper from './DesignPreviewWrapper'
import Design1_ClassicMC from './Design1_ClassicMC'
import Design2_ModernFlat from './Design2_ModernFlat'
import Design3_DarkGaming from './Design3_DarkGaming'
import Design4_PixelArt from './Design4_PixelArt'
import Design5_TexturePack from './Design5_TexturePack'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div
      role='tabpanel'
      hidden={value !== index}
      id={`design-tabpanel-${index}`}
      aria-labelledby={`design-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  )
}

const StyledTabs = styled(Tabs)({
  backgroundColor: '#1F2937',
  borderRadius: '12px',
  padding: '8px',
  '& .MuiTabs-indicator': {
    backgroundColor: '#10B981',
    height: '4px',
    borderRadius: '2px',
  },
})

const StyledTab = styled(Tab)({
  color: '#9CA3AF',
  fontWeight: 600,
  fontSize: '14px',
  textTransform: 'none',
  minHeight: '48px',
  '&.Mui-selected': {
    color: '#10B981',
  },
})

const PreviewCard = styled(Paper)(({ selected }: { selected?: boolean }) => ({
  padding: '16px',
  borderRadius: '12px',
  cursor: 'pointer',
  transition: 'all 0.3s',
  border: selected ? '3px solid #10B981' : '3px solid transparent',
  background: selected ? 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)' : '#FFFFFF',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
    borderColor: selected ? '#10B981' : '#E5E7EB',
  },
}))

const designs = [
  {
    id: 1,
    name: '经典 Minecraft',
    description: '仿制游戏内 GUI 风格，灰色石质界面配合经典按钮样式',
    colors: ['#C6C6C6', '#8B8B8B', '#5ADB5A', '#2D2D2D'],
    component: Design1_ClassicMC,
  },
  {
    id: 2,
    name: '现代扁平化',
    description: '清爽明亮的设计，绿色主题配合圆角卡片和渐变效果',
    colors: ['#7EC850', '#F5FFF5', '#FFFFFF', '#E8F5E9'],
    component: Design2_ModernFlat,
  },
  {
    id: 3,
    name: '深色游戏风',
    description: '末影主题深色界面，紫色霓虹效果营造科技感',
    colors: ['#9333EA', '#1F1F2E', '#10B981', '#0F0F1E'],
    component: Design3_DarkGaming,
  },
  {
    id: 4,
    name: '像素艺术',
    description: '8位复古游戏风格，方块化设计配合像素字体',
    colors: ['#4ADE80', '#F3E8D5', '#87CEEB', '#FDE047'],
    component: Design4_PixelArt,
  },
  {
    id: 5,
    name: '材质包主题',
    description: '自然木纹与矿石质感，仿制 Minecraft 材质包风格',
    colors: ['#8D6E63', '#64B5F6', '#66BB6A', '#E0E0E0'],
    component: Design5_TexturePack,
  },
]

export default function DesignPreviewHub() {
  const [selectedDesign, setSelectedDesign] = useState(0)
  const [viewMode, setViewMode] = useState<'grid' | 'full'>('grid')

  const CurrentDesign = designs[selectedDesign].component

  return (
    <DesignPreviewWrapper>
      <Box sx={{ minHeight: '100vh', backgroundColor: '#F9FAFB' }}>
        {/* 控制栏 */}
        <Paper
          sx={{
            position: 'sticky',
            top: 0,
            zIndex: 1000,
            borderRadius: 0,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            backgroundColor: '#FFFFFF',
            p: 3,
          }}
        >
          <Box sx={{ maxWidth: '1400px', margin: '0 auto' }}>
            <Typography
              variant='h4'
              sx={{
                fontWeight: 700,
                mb: 1,
                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              UI 设计预览中心
            </Typography>
            <Typography variant='body1' sx={{ color: '#6B7280', mb: 3 }}>
              选择您喜欢的 Minecraft 主题界面风格
            </Typography>

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <StyledTabs value={selectedDesign} onChange={(_, v) => setSelectedDesign(v)}>
                {designs.map((design, index) => (
                  <StyledTab key={design.id} label={design.name} />
                ))}
              </StyledTabs>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant={viewMode === 'grid' ? 'contained' : 'outlined'}
                  onClick={() => setViewMode('grid')}
                  sx={{
                    backgroundColor: viewMode === 'grid' ? '#10B981' : 'transparent',
                    color: viewMode === 'grid' ? '#FFFFFF' : '#10B981',
                    borderColor: '#10B981',
                    '&:hover': {
                      backgroundColor: viewMode === 'grid' ? '#059669' : 'rgba(16, 185, 129, 0.1)',
                    },
                  }}
                >
                  网格视图
                </Button>
                <Button
                  variant={viewMode === 'full' ? 'contained' : 'outlined'}
                  onClick={() => setViewMode('full')}
                  sx={{
                    backgroundColor: viewMode === 'full' ? '#10B981' : 'transparent',
                    color: viewMode === 'full' ? '#FFFFFF' : '#10B981',
                    borderColor: '#10B981',
                    '&:hover': {
                      backgroundColor: viewMode === 'full' ? '#059669' : 'rgba(16, 185, 129, 0.1)',
                    },
                  }}
                >
                  全屏预览
                </Button>
              </Box>
            </Box>
          </Box>
        </Paper>

        {/* 内容区 */}
        {viewMode === 'grid' ? (
          <Box sx={{ p: 4 }}>
            <Grid container spacing={3} sx={{ maxWidth: '1400px', margin: '0 auto' }}>
              {designs.map((design, index) => (
                <Grid item xs={12} md={6} lg={4} key={design.id}>
                  <PreviewCard
                    selected={selectedDesign === index}
                    onClick={() => setSelectedDesign(index)}
                  >
                    <Typography variant='h6' sx={{ fontWeight: 600, mb: 1 }}>
                      {design.name}
                    </Typography>
                    <Typography variant='body2' sx={{ color: '#6B7280', mb: 2 }}>
                      {design.description}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                      {design.colors.map((color, idx) => (
                        <Box
                          key={idx}
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: '8px',
                            backgroundColor: color,
                            border: '2px solid #E5E7EB',
                            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                          }}
                        />
                      ))}
                    </Box>
                    <Button
                      fullWidth
                      variant='outlined'
                      sx={{
                        borderColor: '#10B981',
                        color: '#10B981',
                        '&:hover': {
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          borderColor: '#059669',
                        },
                      }}
                      onClick={e => {
                        e.stopPropagation()
                        setViewMode('full')
                        setSelectedDesign(index)
                      }}
                    >
                      查看完整预览
                    </Button>
                  </PreviewCard>
                </Grid>
              ))}
            </Grid>

            {/* 迷你预览 */}
            <Box sx={{ mt: 4, maxWidth: '1400px', margin: '32px auto 0' }}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: '12px',
                  border: '2px solid #E5E7EB',
                  overflow: 'hidden',
                  height: '600px',
                  position: 'relative',
                }}
              >
                <Typography
                  variant='h6'
                  sx={{
                    position: 'absolute',
                    top: 16,
                    left: 16,
                    zIndex: 10,
                    backgroundColor: '#FFFFFF',
                    px: 2,
                    py: 0.5,
                    borderRadius: '8px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                    fontWeight: 600,
                  }}
                >
                  当前预览: {designs[selectedDesign].name}
                </Typography>
                <Box
                  sx={{
                    transform: 'scale(0.6)',
                    transformOrigin: 'top left',
                    width: '166.67%',
                    height: '166.67%',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    overflow: 'hidden',
                  }}
                >
                  <CurrentDesign />
                </Box>
              </Paper>
            </Box>
          </Box>
        ) : (
          <Box>
            <CurrentDesign />
          </Box>
        )}
      </Box>
    </DesignPreviewWrapper>
  )
}
