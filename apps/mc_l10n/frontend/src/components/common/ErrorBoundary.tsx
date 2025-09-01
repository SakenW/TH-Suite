import React, { Component, ReactNode } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { ErrorOutline, Refresh, Home, BugReport } from '@mui/icons-material';

export interface ErrorBoundaryProps {
  children: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  errorTitle?: string;
  errorDescription?: string;
  reloadButtonText?: string;
  homeButtonText?: string;
  reportButtonText?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleReport = () => {
    // 这里可以实现错误报告功能
    console.log('Report error:', this.state.error);
  };

  render() {
    if (this.state.hasError) {
      const {
        errorTitle = '应用出现错误',
        errorDescription = '很抱歉，应用遇到了意外错误。',
        reloadButtonText = '刷新页面',
        homeButtonText = '返回首页',
        reportButtonText = '报告错误'
      } = this.props;

      return (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            backgroundColor: '#f5f5f5',
            padding: 2
          }}
        >
          <Paper
            elevation={3}
            sx={{
              padding: 4,
              maxWidth: 500,
              textAlign: 'center'
            }}
          >
            <ErrorOutline
              sx={{
                fontSize: 64,
                color: 'error.main',
                marginBottom: 2
              }}
            />
            <Typography variant="h4" gutterBottom>
              {errorTitle}
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              {errorDescription}
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                startIcon={<Refresh />}
                onClick={this.handleReload}
              >
                {reloadButtonText}
              </Button>
              <Button
                variant="outlined"
                startIcon={<Home />}
                onClick={this.handleGoHome}
              >
                {homeButtonText}
              </Button>
              <Button
                variant="text"
                startIcon={<BugReport />}
                onClick={this.handleReport}
              >
                {reportButtonText}
              </Button>
            </Box>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <Box sx={{ marginTop: 3, textAlign: 'left' }}>
                <Typography variant="h6" gutterBottom>
                  错误详情 (开发模式):
                </Typography>
                <Paper
                  sx={{
                    padding: 2,
                    backgroundColor: '#f5f5f5',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    overflow: 'auto',
                    maxHeight: 200
                  }}
                >
                  <pre>{this.state.error.stack}</pre>
                </Paper>
              </Box>
            )}
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}