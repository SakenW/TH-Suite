import { createTheme } from '@mui/material/styles'
import { alpha } from '@mui/material/styles'

// 现代化 Minecraft 色彩调色板
const minecraftColors = {
  // 核心色彩 - 更加鲜艳和现代
  grassGreen: '#4CAF50',
  stoneGray: '#9E9E9E',
  diamondBlue: '#00BCD4',
  goldYellow: '#FFB300',
  redstone: '#F44336',

  // 自然方块色彩
  dirt: '#8D6E63',
  wood: '#D7CCC8',
  cobblestone: '#78909C',
  iron: '#CFD8DC',
  coal: '#263238',

  // 宝石和特殊方块
  emerald: '#4CAF50',
  lapis: '#3F51B5',
  obsidian: '#212121',
  netherack: '#8D4037',
  endstone: '#FFF8E1',

  // UI 增强色彩
  inventorySlot: '#37474F',
  hotbarSelected: '#FFFFFF',
  experienceGreen: '#8BC34A',
  healthRed: '#F44336',
  hungerOrange: '#FF9800',

  // 现代渐变色
  skyBlue: '#E3F2FD',
  horizonBlue: '#1976D2',
  sunsetOrange: '#FF7043',
  nightPurple: '#5E35B1',
}

// 创建现代化 Minecraft 主题
export const minecraftTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: minecraftColors.diamondBlue,
      light: '#4DD0E1',
      dark: '#0097A7',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: minecraftColors.goldYellow,
      light: '#FFD54F',
      dark: '#F57C00',
      contrastText: '#000000',
    },
    success: {
      main: minecraftColors.emerald,
      light: '#81C784',
      dark: '#388E3C',
      contrastText: '#FFFFFF',
    },
    warning: {
      main: minecraftColors.hungerOrange,
      light: '#FFB74D',
      dark: '#F57C00',
      contrastText: '#000000',
    },
    error: {
      main: minecraftColors.redstone,
      light: '#EF5350',
      dark: '#D32F2F',
      contrastText: '#FFFFFF',
    },
    info: {
      main: minecraftColors.lapis,
      light: '#7986CB',
      dark: '#303F9F',
      contrastText: '#FFFFFF',
    },
    background: {
      default: `linear-gradient(135deg, ${minecraftColors.skyBlue} 0%, #FAFAFA 50%, ${minecraftColors.endstone} 100%)`,
      paper: alpha('#FFFFFF', 0.95),
    },
    text: {
      primary: minecraftColors.obsidian,
      secondary: alpha(minecraftColors.coal, 0.7),
    },
    divider: alpha(minecraftColors.stoneGray, 0.2),
  },
  typography: {
    fontFamily:
      '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
    h1: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 800,
      letterSpacing: '-0.02em',
      background: `linear-gradient(135deg, ${minecraftColors.diamondBlue} 0%, ${minecraftColors.lapis} 100%)`,
      backgroundClip: 'text',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
    },
    h2: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.01em',
      background: `linear-gradient(135deg, ${minecraftColors.diamondBlue} 0%, ${minecraftColors.lapis} 100%)`,
      backgroundClip: 'text',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
    },
    h3: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.01em',
      color: minecraftColors.obsidian,
    },
    h4: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.01em',
      background: `linear-gradient(135deg, ${minecraftColors.diamondBlue} 0%, ${minecraftColors.horizonBlue} 100%)`,
      backgroundClip: 'text',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
    },
    h5: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 600,
      color: minecraftColors.obsidian,
    },
    h6: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 600,
      color: minecraftColors.coal,
    },
    button: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 600,
      letterSpacing: '0.02em',
      textTransform: 'none',
    },
    body1: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 400,
      lineHeight: 1.7,
    },
    body2: {
      fontFamily:
        '"Inter", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "微软雅黑", sans-serif',
      fontWeight: 400,
      lineHeight: 1.6,
    },
  },
  shape: {
    borderRadius: 16, // 现代化圆角
  },
  components: {
    // App Bar 样式
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: `linear-gradient(135deg, ${minecraftColors.diamondBlue} 0%, ${minecraftColors.horizonBlue} 100%)`,
          backdropFilter: 'blur(20px)',
          boxShadow: `0 8px 32px ${alpha(minecraftColors.diamondBlue, 0.3)}`,
          borderBottom: `1px solid ${alpha('#FFFFFF', 0.2)}`,
        },
      },
    },

    // Drawer 样式
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: `linear-gradient(180deg, ${alpha('#FFFFFF', 0.95)} 0%, ${alpha(minecraftColors.skyBlue, 0.9)} 100%)`,
          backdropFilter: 'blur(20px)',
          borderRight: `1px solid ${alpha(minecraftColors.stoneGray, 0.1)}`,
          boxShadow: `8px 0 32px ${alpha(minecraftColors.obsidian, 0.1)}`,
        },
      },
    },

    // List Item 样式
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          margin: '4px 12px',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            background: `linear-gradient(135deg, ${alpha(minecraftColors.diamondBlue, 0.1)} 0%, ${alpha(minecraftColors.skyBlue, 0.15)} 100%)`,
            transform: 'translateX(8px)',
            boxShadow: `4px 4px 12px ${alpha(minecraftColors.diamondBlue, 0.2)}`,
          },
          '&.Mui-selected': {
            background: `linear-gradient(135deg, ${alpha(minecraftColors.diamondBlue, 0.2)} 0%, ${alpha(minecraftColors.horizonBlue, 0.15)} 100%)`,
            borderLeft: `4px solid ${minecraftColors.diamondBlue}`,
            fontWeight: 600,
            '&:hover': {
              background: `linear-gradient(135deg, ${alpha(minecraftColors.diamondBlue, 0.3)} 0%, ${alpha(minecraftColors.horizonBlue, 0.2)} 100%)`,
            },
          },
        },
      },
    },

    // Card 样式
    MuiCard: {
      styleOverrides: {
        root: {
          background: `linear-gradient(135deg, ${alpha('#FFFFFF', 0.9)} 0%, ${alpha(minecraftColors.endstone, 0.6)} 100%)`,
          backdropFilter: 'blur(20px)',
          border: `1px solid ${alpha(minecraftColors.stoneGray, 0.15)}`,
          borderRadius: 20,
          boxShadow: `0 8px 32px ${alpha(minecraftColors.obsidian, 0.1)}`,
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-8px) scale(1.02)',
            boxShadow: `0 20px 60px ${alpha(minecraftColors.obsidian, 0.2)}`,
            border: `1px solid ${alpha(minecraftColors.diamondBlue, 0.3)}`,
          },
        },
      },
    },
    // Button 样式
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          textTransform: 'none',
          fontWeight: 600,
          padding: '12px 24px',
          fontSize: '0.95rem',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: `0 4px 12px ${alpha(minecraftColors.obsidian, 0.15)}`,
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: `0 8px 25px ${alpha(minecraftColors.obsidian, 0.25)}`,
          },
          '&:active': {
            transform: 'translateY(-1px)',
          },
        },
        contained: {
          background: `linear-gradient(135deg, ${minecraftColors.diamondBlue} 0%, ${minecraftColors.horizonBlue} 100%)`,
          color: '#FFFFFF',
          border: 'none',
          '&:hover': {
            background: `linear-gradient(135deg, ${minecraftColors.horizonBlue} 0%, ${minecraftColors.lapis} 100%)`,
            boxShadow: `0 8px 25px ${alpha(minecraftColors.diamondBlue, 0.4)}`,
          },
          '&:disabled': {
            background: alpha(minecraftColors.stoneGray, 0.3),
            color: alpha('#FFFFFF', 0.5),
          },
        },
        outlined: {
          borderColor: minecraftColors.diamondBlue,
          color: minecraftColors.diamondBlue,
          backgroundColor: alpha('#FFFFFF', 0.8),
          borderWidth: '2px',
          '&:hover': {
            backgroundColor: alpha(minecraftColors.diamondBlue, 0.1),
            borderColor: minecraftColors.horizonBlue,
            borderWidth: '2px',
          },
        },
        text: {
          color: minecraftColors.diamondBlue,
          '&:hover': {
            backgroundColor: alpha(minecraftColors.diamondBlue, 0.1),
          },
        },
      },
    },
    // Progress 样式
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          height: 16,
          borderRadius: 12,
          backgroundColor: alpha(minecraftColors.stoneGray, 0.2),
          overflow: 'hidden',
          position: 'relative',
          '&::after': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              'linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.1) 75%, transparent 75%)',
            backgroundSize: '20px 20px',
            animation: 'progress-shine 2s linear infinite',
          },
        },
        bar: {
          borderRadius: 12,
          background: `linear-gradient(135deg, ${minecraftColors.emerald} 0%, ${minecraftColors.experienceGreen} 100%)`,
          boxShadow: `inset 0 2px 4px rgba(255,255,255,0.3), 0 0 8px ${alpha(minecraftColors.emerald, 0.5)}`,
        },
      },
    },

    // Paper 样式
    MuiPaper: {
      styleOverrides: {
        root: {
          background: `linear-gradient(135deg, ${alpha('#FFFFFF', 0.95)} 0%, ${alpha(minecraftColors.endstone, 0.8)} 100%)`,
          backdropFilter: 'blur(20px)',
          border: `1px solid ${alpha(minecraftColors.stoneGray, 0.1)}`,
        },
        elevation1: {
          boxShadow: `0 4px 20px ${alpha(minecraftColors.obsidian, 0.08)}`,
        },
        elevation2: {
          boxShadow: `0 8px 30px ${alpha(minecraftColors.obsidian, 0.12)}`,
        },
        elevation3: {
          boxShadow: `0 12px 40px ${alpha(minecraftColors.obsidian, 0.16)}`,
        },
      },
    },

    // Alert 样式
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid',
          fontWeight: 500,
          backdropFilter: 'blur(10px)',
          boxShadow: `0 4px 20px ${alpha(minecraftColors.obsidian, 0.1)}`,
        },
        standardSuccess: {
          background: `linear-gradient(135deg, ${alpha(minecraftColors.emerald, 0.15)} 0%, ${alpha(minecraftColors.experienceGreen, 0.1)} 100%)`,
          borderColor: alpha(minecraftColors.emerald, 0.3),
          color: '#2E7D32',
        },
        standardError: {
          background: `linear-gradient(135deg, ${alpha(minecraftColors.redstone, 0.15)} 0%, ${alpha(minecraftColors.healthRed, 0.1)} 100%)`,
          borderColor: alpha(minecraftColors.redstone, 0.3),
          color: '#C62828',
        },
        standardWarning: {
          background: `linear-gradient(135deg, ${alpha(minecraftColors.goldYellow, 0.15)} 0%, ${alpha(minecraftColors.hungerOrange, 0.1)} 100%)`,
          borderColor: alpha(minecraftColors.goldYellow, 0.3),
          color: '#F57C00',
        },
        standardInfo: {
          background: `linear-gradient(135deg, ${alpha(minecraftColors.diamondBlue, 0.15)} 0%, ${alpha(minecraftColors.lapis, 0.1)} 100%)`,
          borderColor: alpha(minecraftColors.diamondBlue, 0.3),
          color: '#1976D2',
        },
      },
    },

    // Chip 样式
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          fontWeight: 600,
          background: `linear-gradient(135deg, ${alpha('#FFFFFF', 0.9)} 0%, ${alpha(minecraftColors.endstone, 0.7)} 100%)`,
          border: `1px solid ${alpha(minecraftColors.stoneGray, 0.2)}`,
          backdropFilter: 'blur(10px)',
          transition: 'all 0.2s ease',
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: `0 4px 12px ${alpha(minecraftColors.obsidian, 0.2)}`,
          },
        },
      },
    },
  },
})

export { minecraftColors }
export default minecraftTheme
