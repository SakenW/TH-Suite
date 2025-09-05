import React from 'react';
import { Box, Paper, Button, Typography, Card, Chip, LinearProgress, IconButton } from '@mui/material';
import { styled } from '@mui/material/styles';
import FolderIcon from '@mui/icons-material/Folder';
import SearchIcon from '@mui/icons-material/Search';
import SettingsIcon from '@mui/icons-material/Settings';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StarIcon from '@mui/icons-material/Star';
import GetAppIcon from '@mui/icons-material/GetApp';
import BuildIcon from '@mui/icons-material/Build';
import TerrainIcon from '@mui/icons-material/Terrain';

// 像素艺术风格 - 8位复古游戏风
const PixelButton = styled(Button)({
  background: '#4ADE80',
  color: '#052E16',
  borderRadius: 0,
  padding: '12px 24px',
  fontSize: '14px',
  fontFamily: '"Press Start 2P", "Courier New", monospace',
  fontWeight: 400,
  textTransform: 'uppercase',
  position: 'relative',
  boxShadow: '4px 4px 0px #166534',
  transition: 'all 0.1s',
  '&:hover': {
    background: '#86EFAC',
    transform: 'translate(-2px, -2px)',
    boxShadow: '6px 6px 0px #166534',
  },
  '&:active': {
    transform: 'translate(2px, 2px)',
    boxShadow: '2px 2px 0px #166534',
  }
});

const PixelButtonRed = styled(Button)({
  background: '#F87171',
  color: '#450A0A',
  borderRadius: 0,
  padding: '12px 24px',
  fontSize: '14px',
  fontFamily: '"Press Start 2P", "Courier New", monospace',
  fontWeight: 400,
  textTransform: 'uppercase',
  boxShadow: '4px 4px 0px #991B1B',
  transition: 'all 0.1s',
  '&:hover': {
    background: '#FCA5A5',
    transform: 'translate(-2px, -2px)',
    boxShadow: '6px 6px 0px #991B1B',
  },
  '&:active': {
    transform: 'translate(2px, 2px)',
    boxShadow: '2px 2px 0px #991B1B',
  }
});

const PixelPanel = styled(Paper)({
  background: '#F3E8D5',
  borderRadius: 0,
  padding: '24px',
  border: '4px solid #8B7355',
  boxShadow: '8px 8px 0px #5C4A3B',
  position: 'relative',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: '-4px',
    left: '-4px',
    right: '-4px',
    bottom: '-4px',
    background: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(139, 115, 85, 0.1) 10px, rgba(139, 115, 85, 0.1) 20px)',
    pointerEvents: 'none',
  }
});

const PixelCard = styled(Card)({
  background: '#FDFCF8',
  borderRadius: 0,
  padding: '16px',
  marginBottom: '16px',
  border: '3px solid #A8A29E',
  boxShadow: '4px 4px 0px #78716C',
  transition: 'all 0.1s',
  '&:hover': {
    transform: 'translate(-2px, -2px)',
    boxShadow: '6px 6px 0px #78716C',
    borderColor: '#4ADE80',
  }
});

const PixelProgress = styled(LinearProgress)({
  height: 16,
  borderRadius: 0,
  backgroundColor: '#E7E5E4',
  border: '2px solid #78716C',
  '& .MuiLinearProgress-bar': {
    borderRadius: 0,
    background: 'repeating-linear-gradient(90deg, #4ADE80, #4ADE80 8px, #22C55E 8px, #22C55E 16px)',
  }
});

const PixelChip = styled(Chip, {
  shouldForwardProp: (prop) => prop !== 'color',
})<{ color: string }>(({ color }) => ({
  borderRadius: 0,
  fontFamily: '"Press Start 2P", monospace',
  fontSize: '10px',
  fontWeight: 400,
  border: '2px solid',
  height: '32px',
  ...(color === 'green' && {
    backgroundColor: '#4ADE80',
    color: '#052E16',
    borderColor: '#166534',
  }),
  ...(color === 'yellow' && {
    backgroundColor: '#FDE047',
    color: '#422006',
    borderColor: '#A16207',
  }),
  ...(color === 'red' && {
    backgroundColor: '#F87171',
    color: '#450A0A',
    borderColor: '#991B1B',
  }),
}));

const PixelIcon = styled(Box)({
  width: 32,
  height: 32,
  backgroundColor: '#8B7355',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  position: 'relative',
  '&::after': {
    content: '""',
    position: 'absolute',
    inset: '4px',
    backgroundColor: '#D4A574',
  }
});

export default function Design4_PixelArt() {
  return (
    <Box sx={{ 
      minHeight: '100vh', 
      background: 'repeating-linear-gradient(0deg, #87CEEB 0px, #87CEEB 100px, #98D8E8 100px, #98D8E8 200px)',
      padding: 4,
      position: 'relative',
      '&::before': {
        content: '""',
        position: 'absolute',
        inset: 0,
        background: 'repeating-linear-gradient(90deg, transparent, transparent 50px, rgba(255, 255, 255, 0.1) 50px, rgba(255, 255, 255, 0.1) 100px)',
        pointerEvents: 'none',
      }
    }}>
      {/* 顶部栏 */}
      <PixelPanel sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Box sx={{
              width: 64,
              height: 64,
              background: 'repeating-linear-gradient(45deg, #4ADE80 0, #4ADE80 8px, #22C55E 8px, #22C55E 16px)',
              border: '4px solid #166534',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Typography sx={{ 
                fontSize: '24px', 
                fontWeight: 'bold',
                color: '#052E16',
                fontFamily: '"Press Start 2P", monospace',
              }}>
                MC
              </Typography>
            </Box>
            <Typography variant="h5" sx={{ 
              fontFamily: '"Press Start 2P", monospace',
              color: '#5C4A3B',
              fontSize: '20px',
              letterSpacing: '2px',
            }}>
              TH SUITE MC L10N
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <IconButton sx={{ 
              backgroundColor: '#FDE047',
              border: '3px solid #A16207',
              borderRadius: 0,
              color: '#422006',
              '&:hover': { 
                backgroundColor: '#FEF08A',
                transform: 'scale(1.1)',
              }
            }}>
              <FolderIcon />
            </IconButton>
            <IconButton sx={{ 
              backgroundColor: '#93C5FD',
              border: '3px solid #1E3A8A',
              borderRadius: 0,
              color: '#1E3A8A',
              '&:hover': { 
                backgroundColor: '#BFDBFE',
                transform: 'scale(1.1)',
              }
            }}>
              <SettingsIcon />
            </IconButton>
          </Box>
        </Box>
      </PixelPanel>

      {/* 主内容区 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: 3 }}>
        {/* 左侧项目列表 */}
        <PixelPanel>
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6" sx={{ 
              fontFamily: '"Press Start 2P", monospace',
              color: '#5C4A3B',
              fontSize: '14px',
            }}>
              MOD LIST
            </Typography>
            <PixelButton size="small" startIcon={<SearchIcon />}>
              SCAN
            </PixelButton>
          </Box>

          <PixelCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{
                  width: 40,
                  height: 40,
                  background: '#C084FC',
                  border: '3px solid #7C3AED',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <TerrainIcon sx={{ color: '#FFFFFF' }} />
                </Box>
                <Box>
                  <Typography sx={{ 
                    fontWeight: 'bold',
                    color: '#1C1917',
                    fontSize: '14px',
                    fontFamily: '"Press Start 2P", monospace',
                  }}>
                    TWILIGHT
                  </Typography>
                  <Typography variant="caption" sx={{ 
                    color: '#78716C',
                    fontFamily: 'monospace',
                  }}>
                    v4.7.3196
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <PixelChip label="OK" size="small" color="green" />
                <Typography sx={{ 
                  color: '#166534',
                  fontWeight: 'bold',
                  fontFamily: '"Press Start 2P", monospace',
                  fontSize: '16px',
                }}>
                  85%
                </Typography>
              </Box>
            </Box>
            <PixelProgress variant="determinate" value={85} sx={{ mt: 2 }} />
          </PixelCard>

          <PixelCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{
                  width: 40,
                  height: 40,
                  background: '#60A5FA',
                  border: '3px solid #1D4ED8',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <BuildIcon sx={{ color: '#FFFFFF' }} />
                </Box>
                <Box>
                  <Typography sx={{ 
                    fontWeight: 'bold',
                    color: '#1C1917',
                    fontSize: '14px',
                    fontFamily: '"Press Start 2P", monospace',
                  }}>
                    AE2
                  </Typography>
                  <Typography variant="caption" sx={{ 
                    color: '#78716C',
                    fontFamily: 'monospace',
                  }}>
                    v15.3.1
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <PixelChip label="WIP" size="small" color="yellow" />
                <Typography sx={{ 
                  color: '#A16207',
                  fontWeight: 'bold',
                  fontFamily: '"Press Start 2P", monospace',
                  fontSize: '16px',
                }}>
                  32%
                </Typography>
              </Box>
            </Box>
            <PixelProgress variant="determinate" value={32} sx={{ mt: 2 }} />
          </PixelCard>

          <PixelCard>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{
                  width: 40,
                  height: 40,
                  background: '#4ADE80',
                  border: '3px solid #166534',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <StarIcon sx={{ color: '#FFFFFF' }} />
                </Box>
                <Box>
                  <Typography sx={{ 
                    fontWeight: 'bold',
                    color: '#1C1917',
                    fontSize: '14px',
                    fontFamily: '"Press Start 2P", monospace',
                  }}>
                    JEI
                  </Typography>
                  <Typography variant="caption" sx={{ 
                    color: '#78716C',
                    fontFamily: 'monospace',
                  }}>
                    v20.1.16
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <PixelChip label="DONE" size="small" color="green" />
                <Typography sx={{ 
                  color: '#166534',
                  fontWeight: 'bold',
                  fontFamily: '"Press Start 2P", monospace',
                  fontSize: '16px',
                }}>
                  100%
                </Typography>
              </Box>
            </Box>
            <PixelProgress variant="determinate" value={100} sx={{ mt: 2 }} />
          </PixelCard>
        </PixelPanel>

        {/* 右侧状态面板 */}
        <PixelPanel>
          <Typography variant="h6" sx={{ 
            fontFamily: '"Press Start 2P", monospace',
            color: '#5C4A3B',
            fontSize: '14px',
            mb: 3
          }}>
            STATUS
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography sx={{ 
                color: '#78716C', 
                fontFamily: '"Press Start 2P", monospace',
                fontSize: '10px',
              }}>
                TOTAL
              </Typography>
              <Typography sx={{ 
                color: '#166534',
                fontFamily: '"Press Start 2P", monospace',
                fontSize: '14px',
              }}>
                72%
              </Typography>
            </Box>
            <PixelProgress variant="determinate" value={72} />
          </Box>

          <Box sx={{ 
            background: '#E7E5E4',
            border: '3px solid #A8A29E',
            p: 2,
            mb: 3
          }}>
            <Typography sx={{ 
              color: '#5C4A3B', 
              fontFamily: '"Press Start 2P", monospace',
              fontSize: '12px',
              mb: 2
            }}>
              STATS
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ 
                  color: '#78716C', 
                  fontSize: '11px',
                  fontFamily: 'monospace',
                }}>
                  MODS
                </Typography>
                <Typography sx={{ 
                  color: '#1C1917', 
                  fontWeight: 'bold',
                  fontFamily: '"Press Start 2P", monospace',
                  fontSize: '12px',
                }}>
                  125
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ 
                  color: '#78716C', 
                  fontSize: '11px',
                  fontFamily: 'monospace',
                }}>
                  DONE
                </Typography>
                <Typography sx={{ 
                  color: '#166534', 
                  fontWeight: 'bold',
                  fontFamily: '"Press Start 2P", monospace',
                  fontSize: '12px',
                }}>
                  90
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography sx={{ 
                  color: '#78716C', 
                  fontSize: '11px',
                  fontFamily: 'monospace',
                }}>
                  TODO
                </Typography>
                <Typography sx={{ 
                  color: '#A16207', 
                  fontWeight: 'bold',
                  fontFamily: '"Press Start 2P", monospace',
                  fontSize: '12px',
                }}>
                  35
                </Typography>
              </Box>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <PixelButton 
              fullWidth 
              size="large" 
              startIcon={<PlayArrowIcon />}
              sx={{ height: 48 }}
            >
              START
            </PixelButton>
            <PixelButtonRed 
              fullWidth 
              startIcon={<GetAppIcon />}
            >
              EXPORT
            </PixelButtonRed>
          </Box>
        </PixelPanel>
      </Box>
    </Box>
  );
}