import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

// 创建一个独立的主题用于设计预览
const previewTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#10B981',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#9333EA',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F9FAFB',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1F2937',
      secondary: '#6B7280',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
});

interface DesignPreviewWrapperProps {
  children: React.ReactNode;
}

export default function DesignPreviewWrapper({ children }: DesignPreviewWrapperProps) {
  return (
    <ThemeProvider theme={previewTheme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}