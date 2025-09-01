import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Toaster } from 'react-hot-toast';

import App from './App';
import { ErrorBoundary } from './components/common';
import { minecraftTheme } from './theme/minecraftTheme';
import './index.css';
import './assets/fonts/minecraft.css';
import './i18n';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
    mutations: {
      retry: 1,
    },
  },
});

// Development configuration
const isDevelopment = import.meta.env.DEV;
const DISABLE_STRICT_MODE = true; // 临时禁用Strict Mode修复DOM错误

// Remove loading spinner when app is ready
const removeLoadingSpinner = () => {
  document.body.classList.add('app-ready');
};

const AppContent = () => (
  <ErrorBoundary
    onError={(error, errorInfo) => {
      console.error('Application error:', error, errorInfo);
    }}
    errorTitle="应用出现错误"
    errorDescription="很抱歉，TH Suite MC L10n 遇到了意外错误。"
    reloadButtonText="刷新页面"
    homeButtonText="返回首页"
    reportButtonText="报告错误"
  >
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={minecraftTheme}>
        <CssBaseline />
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <App onReady={removeLoadingSpinner} />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#4caf50',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#f44336',
                  secondary: '#fff',
                },
              },
            }}
          />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

ReactDOM.createRoot(document.getElementById('root')!).render(
  isDevelopment && !DISABLE_STRICT_MODE ? (
    <React.StrictMode>
      <AppContent />
    </React.StrictMode>
  ) : (
    <AppContent />
  )
);
