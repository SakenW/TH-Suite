import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { createTheme, ThemeProvider as MuiThemeProvider, Theme } from '@mui/material/styles';
import { minecraftTheme } from '../theme/minecraftTheme';
import { minecraftColors } from '../theme/minecraftTheme';

export type ThemeMode = 'light' | 'dark' | 'minecraft' | 'highContrast';
export type ColorScheme = 'emerald' | 'diamond' | 'gold' | 'redstone' | 'netherite';

interface ThemeContextType {
  themeMode: ThemeMode;
  colorScheme: ColorScheme;
  setThemeMode: (mode: ThemeMode) => void;
  setColorScheme: (scheme: ColorScheme) => void;
  toggleTheme: () => void;
  theme: Theme;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

const colorSchemes = {
  emerald: {
    primary: minecraftColors.emerald,
    secondary: minecraftColors.diamondBlue,
    accent: minecraftColors.goldYellow,
  },
  diamond: {
    primary: minecraftColors.diamondBlue,
    secondary: minecraftColors.emerald,
    accent: minecraftColors.goldYellow,
  },
  gold: {
    primary: minecraftColors.goldYellow,
    secondary: minecraftColors.emerald,
    accent: minecraftColors.diamondBlue,
  },
  redstone: {
    primary: minecraftColors.redstoneRed,
    secondary: minecraftColors.iron,
    accent: minecraftColors.goldYellow,
  },
  netherite: {
    primary: '#4A4A4A',
    secondary: minecraftColors.netheriteGray,
    accent: minecraftColors.goldYellow,
  },
};

const createCustomTheme = (mode: ThemeMode, colorScheme: ColorScheme): Theme => {
  const colors = colorSchemes[colorScheme];
  
  if (mode === 'minecraft') {
    // Return the original minecraft theme
    return minecraftTheme;
  }
  
  const baseTheme = createTheme({
    palette: {
      mode: mode === 'light' ? 'light' : 'dark',
      primary: {
        main: colors.primary,
      },
      secondary: {
        main: colors.secondary,
      },
      background: mode === 'light' 
        ? {
            default: '#F5F5F5',
            paper: '#FFFFFF',
          }
        : mode === 'highContrast'
        ? {
            default: '#000000',
            paper: '#0A0A0A',
          }
        : {
            default: '#0F172A',
            paper: '#1E293B',
          },
      text: mode === 'light'
        ? {
            primary: '#2C3E50',
            secondary: '#546E7A',
          }
        : mode === 'highContrast'
        ? {
            primary: '#FFFFFF',
            secondary: '#FFFF00',
          }
        : {
            primary: '#FFFFFF',
            secondary: 'rgba(255, 255, 255, 0.7)',
          },
    },
    typography: {
      fontFamily: '"Minecraft", "Roboto", "Helvetica", "Arial", sans-serif',
      h1: {
        fontFamily: '"Minecraft", monospace',
        fontSize: '2.5rem',
        fontWeight: 700,
      },
      h2: {
        fontFamily: '"Minecraft", monospace',
        fontSize: '2rem',
        fontWeight: 600,
      },
      h3: {
        fontFamily: '"Minecraft", monospace',
        fontSize: '1.75rem',
        fontWeight: 600,
      },
      h4: {
        fontFamily: '"Minecraft", monospace',
        fontSize: '1.5rem',
        fontWeight: 500,
      },
      h5: {
        fontFamily: '"Minecraft", monospace',
        fontSize: '1.25rem',
        fontWeight: 500,
      },
      h6: {
        fontFamily: '"Minecraft", monospace',
        fontSize: '1rem',
        fontWeight: 500,
      },
    },
    shape: {
      borderRadius: mode === 'minecraft' ? 0 : 4,
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: mode === 'minecraft' ? 0 : 4,
            textTransform: 'none',
            fontFamily: '"Minecraft", monospace',
            boxShadow: mode === 'minecraft' ? `2px 2px 0px rgba(0,0,0,0.5)` : undefined,
            '&:hover': {
              transform: mode === 'minecraft' ? 'translate(-1px, -1px)' : undefined,
              boxShadow: mode === 'minecraft' ? `3px 3px 0px rgba(0,0,0,0.5)` : undefined,
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: mode === 'minecraft' ? 0 : 8,
            border: mode === 'minecraft' ? `3px solid ${colors.primary}33` : undefined,
            background: mode === 'minecraft' 
              ? `linear-gradient(135deg, ${colors.primary}11 0%, transparent 100%)`
              : undefined,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: mode === 'minecraft' ? 0 : 4,
              '& fieldset': {
                borderWidth: mode === 'minecraft' ? 2 : 1,
              },
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: mode === 'minecraft' ? 0 : 4,
          },
        },
      },
    },
  });
  
  return baseTheme;
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('themeMode');
    return (saved as ThemeMode) || 'minecraft';
  });
  
  const [colorScheme, setColorScheme] = useState<ColorScheme>(() => {
    const saved = localStorage.getItem('colorScheme');
    return (saved as ColorScheme) || 'emerald';
  });
  
  const theme = useMemo(
    () => createCustomTheme(themeMode, colorScheme),
    [themeMode, colorScheme]
  );
  
  useEffect(() => {
    localStorage.setItem('themeMode', themeMode);
  }, [themeMode]);
  
  useEffect(() => {
    localStorage.setItem('colorScheme', colorScheme);
  }, [colorScheme]);
  
  useEffect(() => {
    // Apply theme mode to document
    document.documentElement.setAttribute('data-theme', themeMode);
    
    // Apply high contrast styles if needed
    if (themeMode === 'highContrast') {
      document.body.style.filter = 'contrast(1.2)';
    } else {
      document.body.style.filter = '';
    }
  }, [themeMode]);
  
  const toggleTheme = () => {
    const modes: ThemeMode[] = ['minecraft', 'dark', 'light', 'highContrast'];
    const currentIndex = modes.indexOf(themeMode);
    const nextIndex = (currentIndex + 1) % modes.length;
    setThemeMode(modes[nextIndex]);
  };
  
  const value: ThemeContextType = {
    themeMode,
    colorScheme,
    setThemeMode,
    setColorScheme,
    toggleTheme,
    theme,
  };
  
  return (
    <ThemeContext.Provider value={value}>
      <MuiThemeProvider theme={theme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};