import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Chip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Minimize2,
  Square,
  X,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

import { useAppStore } from '@stores/appStore';
import { tauriService } from '@services';
import { useCommonTranslation, useMcStudioTranslation } from '@hooks/useTranslation';

interface HeaderProps {
  sidebarWidth: number;
  onSidebarToggle: () => void;
}

function Header({ sidebarWidth, onSidebarToggle }: HeaderProps) {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentProject } = useAppStore();
  const { t: tCommon } = useCommonTranslation();
  const { t: tMc } = useMcStudioTranslation();

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return tCommon('pages.home');
      case '/scan':
        return tCommon('pages.scan');
      case '/extract':
        return tCommon('pages.extract');
      case '/export':
        return tCommon('pages.export');
      case '/transfer':
        return tCommon('pages.transfer');
      case '/build':
        return tCommon('pages.build');
      case '/security':
        return tCommon('pages.security');
      case '/server':
        return tCommon('pages.server');
      case '/settings':
        return tCommon('pages.settings');
      default:
        return tMc('mcStudio.title');
    }
  };

  const handleMinimize = async () => {
    try {
      await tauriService.invokeBackend('minimize_window');
    } catch (error) {
      console.error('Failed to minimize window:', error);
    }
  };

  const handleMaximize = async () => {
    try {
      await tauriService.invokeBackend('toggle_maximize');
    } catch (error) {
      console.error('Failed to toggle maximize:', error);
    }
  };

  const handleClose = async () => {
    try {
      await tauriService.invokeBackend('close_window');
    } catch (error) {
      console.error('Failed to close window:', error);
    }
  };



  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        zIndex: theme.zIndex.drawer + 1,
        backgroundColor: alpha(theme.palette.background.paper, 0.8),
        backdropFilter: 'blur(8px)',
        borderBottom: `1px solid ${theme.palette.divider}`,
        color: theme.palette.text.primary,
        marginLeft: `${sidebarWidth}px`,
        width: `calc(100% - ${sidebarWidth}px)`,
        transition: theme.transitions.create(['width', 'margin-left'], {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen,
        }),
      }}
    >
      <Toolbar
        sx={{
          minHeight: '64px !important',
          paddingLeft: '16px !important',
          paddingRight: '16px !important',
        }}
        data-tauri-drag-region
      >
        {/* Menu button */}
        <IconButton
          edge="start"
          color="inherit"
          aria-label="toggle sidebar"
          onClick={onSidebarToggle}
          sx={{ marginRight: 2 }}
        >
          <MenuIcon size={20} />
        </IconButton>

        {/* Page title */}
        <Typography
          variant="h6"
          component="h1"
          sx={{
            fontWeight: 600,
            fontSize: '1.1rem',
            color: theme.palette.text.primary,
          }}
        >
          {getPageTitle()}
        </Typography>

        {/* Current project indicator */}
        {currentProject && (
          <Chip
            label={currentProject.name}
            size="small"
            variant="outlined"
            sx={{
              marginLeft: 2,
              fontSize: '0.75rem',
              height: '24px',
              borderColor: theme.palette.primary.main,
              color: theme.palette.primary.main,
            }}
          />
        )}

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* Tagline */}
        <Typography
          variant="body2"
          sx={{
            fontSize: '0.9rem',
            fontWeight: 500,
            color: theme.palette.text.secondary,
            marginRight: 2,
            display: { xs: 'none', md: 'block' },
            fontStyle: 'italic',
            letterSpacing: '0.5px',
          }}
        >
          语枢 - 让万语汇于一枢，行于无碍
        </Typography>

        {/* Action buttons */}
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: { xs: 0.5, sm: 1 },
          flexShrink: 0,
          minWidth: 'fit-content'
        }}>

          {/* Window controls (only show in Tauri) */}
          {tauriService.isRunningInTauri() && (
            <>
              <IconButton
                color="inherit"
                onClick={handleMinimize}
                sx={{
                  padding: '8px',
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.action.hover, 0.1),
                  },
                }}
              >
                <Minimize2 size={16} />
              </IconButton>
              
              <IconButton
                color="inherit"
                onClick={handleMaximize}
                sx={{
                  padding: '8px',
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.action.hover, 0.1),
                  },
                }}
              >
                <Square size={16} />
              </IconButton>
              
              <IconButton
                color="inherit"
                onClick={handleClose}
                sx={{
                  padding: '8px',
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.error.main, 0.1),
                    color: theme.palette.error.main,
                  },
                }}
              >
                <X size={16} />
              </IconButton>
            </>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Header;