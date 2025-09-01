import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';

import Layout from '@components/Layout';
import ScanPageOptimal from '@pages/ScanPageOptimal';
import PlaceholderPage from '@pages/PlaceholderPage';
import ProgressTestPage from '@pages/ProgressTestPage';
import { useAppStore } from '@stores/appStore';
import { initializeTauri } from '@services';

interface AppProps {
  onReady?: () => void;
}

function App({ onReady }: AppProps) {
  const isInitialized = useAppStore((state) => state.isInitialized);
  const isLoading = useAppStore((state) => state.isLoading);
  const loadingMessage = useAppStore((state) => state.loadingMessage);
  const initialize = useAppStore((state) => state.initialize);

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
    <Layout>
      <Routes>
        <Route path="/" element={<ScanPageOptimal />} />
        <Route path="/home" element={<PlaceholderPage title="首页" description="应用首页和概览信息" features={['项目统计', '快捷操作', '最近活动']} />} />
        <Route path="/project" element={<PlaceholderPage title="项目管理" description="管理翻译项目" features={['项目创建', '项目编辑', '项目删除', '项目搜索']} />} />
        <Route path="/scan" element={<ScanPageOptimal />} />
        <Route path="/progress-test" element={<ProgressTestPage />} />
        <Route path="/extract" element={<PlaceholderPage title="提取管理" description="从JAR和资源包中提取翻译内容" features={['文件解析', '内容提取', '格式转换']} />} />
        <Route path="/export" element={<PlaceholderPage title="导出管理" description="导出翻译文件到各种格式" features={['多格式支持', '批量导出', '自定义模板']} />} />
        <Route path="/transfer" element={<PlaceholderPage title="传输管理" description="与Trans-Hub平台同步数据" features={['上传下载', '增量同步', '冲突解决']} />} />
        <Route path="/build" element={<PlaceholderPage title="构建管理" description="构建最终的本地化包" features={['自动构建', '质量检查', '版本管理']} />} />
        <Route path="/security" element={<PlaceholderPage title="安全设置" description="管理访问权限和安全策略" features={['权限控制', '数据加密', '审计日志']} />} />
        <Route path="/server" element={<PlaceholderPage title="服务器设置" description="配置Trans-Hub连接" features={['服务器配置', '连接测试', '同步设置']} />} />
        <Route path="/settings" element={<PlaceholderPage title="应用设置" description="配置应用偏好和参数" features={['界面设置', '语言配置', '缓存管理']} />} />
        <Route path="/local-data" element={<PlaceholderPage title="本地数据" description="管理本地存储的翻译数据" features={['数据浏览', '数据清理', '导入导出']} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;