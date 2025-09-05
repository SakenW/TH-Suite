import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';

import LayoutMinecraft from '@components/Layout/LayoutMinecraft';
import ScanPageMinecraft from '@pages/ScanPageMinecraft';
import HomePageMinecraft from '@pages/HomePageMinecraft';
import ProjectPageMinecraft from '@pages/ProjectPageMinecraft';
import SettingsPageMinecraft from '@pages/SettingsPageMinecraft';
import ExtractPageMinecraft from '@pages/ExtractPageMinecraft';
import ExportPageMinecraft from '@pages/ExportPageMinecraft';
import PlaceholderPage from '@pages/PlaceholderPage';
import ProgressTestPage from '@pages/ProgressTestPage';
import TransferPageMinecraft from '@pages/TransferPageMinecraft';
import BuildPageMinecraft from '@pages/BuildPageMinecraft';
import LocalDataPageMinecraft from '@pages/LocalDataPageMinecraft';
import SecurityPageMinecraft from '@pages/SecurityPageMinecraft';
import ServerPageMinecraft from '@pages/ServerPageMinecraft';
import DesignPreviewHub from './design-previews/DesignPreviewHub';
import { useAppStore } from '@stores/appStore';
import { initializeTauri, storageService } from '@services';
import { useGlobalShortcuts } from '@hooks/useKeyboardShortcuts';
import { ShortcutHelp } from '@components/ShortcutHelp';

interface AppProps {
  onReady?: () => void;
}

function App({ onReady }: AppProps) {
  const isInitialized = useAppStore((state) => state.isInitialized);
  const isLoading = useAppStore((state) => state.isLoading);
  const loadingMessage = useAppStore((state) => state.loadingMessage);
  const initialize = useAppStore((state) => state.initialize);
  
  // 启用全局快捷键
  useGlobalShortcuts();

  console.log('🔄 App render - isInitialized:', isInitialized, 'isLoading:', isLoading);

  useEffect(() => {
    // 防止重复初始化的标识
    if (isInitialized) {
      console.log('🔄 App already initialized, skipping...');
      onReady?.();
      return;
    }

    let isCancelled = false;
    
    const initApp = async () => {
      if (isCancelled || isInitialized) return;
      
      try {
        console.log('🚀 Starting app initialization sequence...');
        
        // Initialize Tauri APIs
        console.log('📱 Initializing Tauri APIs...');
        await initializeTauri();
        
        if (isCancelled || isInitialized) return;
        console.log('✅ Tauri APIs initialized successfully');
        
        // Initialize storage service
        console.log('💾 Initializing storage service...');
        await storageService.init();
        
        if (isCancelled || isInitialized) return;
        console.log('✅ Storage service initialized successfully');
        
        // Initialize app store
        console.log('🏪 Initializing app store...');
        const result = await initialize();
        
        if (isCancelled || isInitialized) return;
        console.log('✅ App store initialization result:', result);
        
        // Notify that app is ready
        console.log('🎉 App initialization sequence complete');
        onReady?.();
      } catch (error) {
        if (!isCancelled) {
          console.error('❌ Failed to initialize app:', error);
          // Still call onReady to remove HTML loading spinner
          onReady?.();
        }
      }
    };

    console.log('🔧 Setting up initialization effect...');
    initApp();
    
    return () => {
      isCancelled = true;
    };
  }, [isInitialized, initialize, onReady]);

  if (!isInitialized) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bgcolor="background.default"
        sx={{ color: 'text.primary' }}
      >
        {/* 显示详细的加载状态 */}
        <Box textAlign="center" mb={2}>
          <h2>🎮 TH Suite MC L10n</h2>
          <p>Minecraft 本地化工具</p>
        </Box>
        
        {isLoading ? (
          <Box textAlign="center">
            <div className="loading-spinner" style={{
              width: '40px',
              height: '40px',
              border: '4px solid rgba(255, 255, 255, 0.3)',
              borderTop: '4px solid white',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }} />
            <p>{loadingMessage || '正在初始化应用...'}</p>
          </Box>
        ) : (
          <Box textAlign="center">
            <p>⚠️ 应用初始化可能失败</p>
            <p>请检查控制台日志或刷新页面重试</p>
            <button 
              onClick={() => window.location.reload()}
              style={{
                padding: '8px 16px',
                background: '#1976d2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                marginTop: '10px'
              }}
            >
              刷新页面
            </button>
          </Box>
        )}
        
        {/* 调试信息 */}
        <Box mt={4} p={2} bgcolor="rgba(0,0,0,0.1)" borderRadius={1} fontSize="12px">
          <div>调试信息:</div>
          <div>isInitialized: {isInitialized.toString()}</div>
          <div>isLoading: {isLoading.toString()}</div>
          <div>loadingMessage: {loadingMessage || 'null'}</div>
        </Box>
      </Box>
    );
  }

  return (
    <>
      <LayoutMinecraft>
        <Routes>
        <Route path="/" element={<HomePageMinecraft />} />
        <Route path="/home" element={<HomePageMinecraft />} />
        <Route path="/project" element={<ProjectPageMinecraft />} />
        <Route path="/scan" element={<ScanPageMinecraft />} />
        <Route path="/progress-test" element={<ProgressTestPage />} />
        <Route path="/design-preview" element={<DesignPreviewHub />} />
        <Route path="/extract" element={<ExtractPageMinecraft />} />
        <Route path="/export" element={<ExportPageMinecraft />} />
        <Route path="/transfer" element={<TransferPageMinecraft />} />
        <Route path="/build" element={<BuildPageMinecraft />} />
        <Route path="/security" element={<SecurityPageMinecraft />} />
        <Route path="/server" element={<ServerPageMinecraft />} />
        <Route path="/settings" element={<SettingsPageMinecraft />} />
        <Route path="/local-data" element={<LocalDataPageMinecraft />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </LayoutMinecraft>
    <ShortcutHelp />
    </>
  );
}

export default App;