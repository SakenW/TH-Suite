import React from 'react';
import { Box, CssBaseline, useTheme, useMediaQuery } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';

import Sidebar from './Sidebar';
import Header from './Header';
import { useAppStore } from '@stores/appStore';

interface LayoutProps {
  children: React.ReactNode;
}

const SIDEBAR_WIDTH = 280;
const SIDEBAR_COLLAPSED_WIDTH = 64;

function Layout({ children }: LayoutProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { sidebarOpen, setSidebarOpen } = useAppStore();

  const sidebarWidth = sidebarOpen ? SIDEBAR_WIDTH : SIDEBAR_COLLAPSED_WIDTH;

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const handleSidebarClose = () => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <CssBaseline />
      
      {/* Header */}
      <Header
        sidebarWidth={isMobile ? 0 : sidebarWidth}
        onSidebarToggle={handleSidebarToggle}
      />
      
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        width={SIDEBAR_WIDTH}
        collapsedWidth={SIDEBAR_COLLAPSED_WIDTH}
        isMobile={isMobile}
        onClose={handleSidebarClose}
      />
      
      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          marginTop: '64px', // Header height
          // Remove marginLeft since Drawer with permanent variant already reserves space
        }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{
              duration: 0.3,
              ease: 'easeInOut',
            }}
            style={{
              height: '100%',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </Box>
      
      {/* Mobile overlay */}
      {isMobile && sidebarOpen && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: theme.zIndex.drawer - 1,
          }}
          onClick={handleSidebarClose}
        />
      )}
    </Box>
  );
}

export default Layout;