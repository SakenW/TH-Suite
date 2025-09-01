/**
 * 扫描页面 - 最优化版本
 * 使用新的服务架构和现代React模式
 */

import React, { useState } from 'react';
import { Box, Button, Typography, LinearProgress, Alert } from '@mui/material';
import { FolderOpen, Play, CheckCircle, Square, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

import { useScan } from '../hooks/useServices';
import { useRealTimeProgress } from '../hooks/useRealTimeProgress';
import { TauriService } from '../services';
import type { ScanStatus, ScanResult } from '../services/domain/types';
import RealTimeProgressIndicator from '../components/common/RealTimeProgressIndicator';

const tauriService = new TauriService();

export default function ScanPageOptimal() {
  console.log('🔄 ScanPageOptimal rendering...');
  
  const [directory, setDirectory] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  
  console.log('📞 Calling useScan hook...');
  const { startScan, service } = useScan();
  console.log('✅ useScan hook completed');
  
  // 使用增强的实时进度 Hook
  const {
    status: scanStatus,
    result: scanResult,
    isPolling,
    error: progressError,
    startPolling,
    stopPolling,
    estimatedTimeRemaining,
    processingSpeed,
  } = useRealTimeProgress({
    pollingInterval: 800, // 800ms 轮询间隔，更加平滑
    smoothingEnabled: true,
    adaptivePolling: true,
    onStatusChange: (status) => {
      console.log('📊 实时状态更新:', status);
    },
    onComplete: (result) => {
      console.log('✅ 扫描完成:', result);
      toast.success(`扫描完成！发现 ${result.statistics.total_mods} 个模组`);
      setIsScanning(false);
      setCurrentScanId(null);
    },
    onError: (error) => {
      console.error('❌ 进度监控错误:', error);
      toast.error('扫描状态监控出错');
    },
  });
  
  console.log('🎯 ScanPageOptimal state:', {
    directory,
    isScanning,
    hasStatus: !!scanStatus,
    hasResult: !!scanResult
  });

  const selectDirectory = async () => {
    try {
      const result = await tauriService.selectDirectory({
        title: '选择要扫描的目录',
        defaultPath: directory || undefined,
      });
      
      if (result) {
        setDirectory(result);
      }
    } catch (error) {
      toast.error('选择目录失败');
      console.error(error);
    }
  };

  const handleStartScan = async () => {
    if (!directory) {
      toast.error('请先选择目录');
      return;
    }

    try {
      setIsScanning(true);
      setCurrentScanId(null);

      // 开始扫描
      const startResult = await startScan({
        directory,
        incremental: true,
      });

      if (!startResult.success) {
        throw new Error(startResult.error?.message || '启动扫描失败');
      }

      const scanId = startResult.data!.scan_id;
      setCurrentScanId(scanId);
      toast.success('扫描已开始 - 实时进度监控已启用');

      // 启动实时进度监控
      startPolling(scanId);

    } catch (error) {
      toast.error(`扫描失败: ${error instanceof Error ? error.message : '未知错误'}`);
      console.error(error);
      setIsScanning(false);
      setCurrentScanId(null);
    }
  };

  const handleCancelScan = async () => {
    if (!currentScanId) {
      return;
    }

    try {
      // 停止进度监控
      stopPolling();
      
      const result = await service.cancelScan(currentScanId);
      if (result.success) {
        toast.success('扫描已取消');
        setIsScanning(false);
        setCurrentScanId(null);
      } else {
        toast.error('取消扫描失败');
      }
    } catch (error) {
      toast.error('取消扫描时发生错误');
      console.error(error);
    }
  };

  return (
    <Box 
      className="page-enter"
      sx={{ 
        p: 3, 
        maxWidth: 1200, 
        mx: 'auto',
        background: 'transparent',
      }}
    >
      <Typography 
        variant="h4" 
        gutterBottom 
        className="gradient-text"
        sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 2,
          mb: 3,
          fontSize: '2.2rem'
        }}
      >
        <Box className="float">
          <Play size={36} />
        </Box>
        项目扫描 - 现代架构
      </Typography>

      <Typography 
        variant="body1" 
        sx={{ 
          mb: 4,
          fontSize: '1.1rem',
          color: 'text.secondary',
          textAlign: 'center',
          maxWidth: 600,
          mx: 'auto',
          lineHeight: 1.8
        }}
      >
        🎮 选择包含 Minecraft 模组 JAR 文件的目录，开始智能扫描和本地化分析。
        <br />
        支持增量扫描、实时进度显示和详细统计报告。
      </Typography>

      {/* 目录选择卡片 */}
      <Box 
        className="glass" 
        sx={{ 
          mb: 4, 
          p: 3, 
          borderRadius: 3, 
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: '0 12px 40px rgba(0, 188, 212, 0.15)',
          }
        }}
      >
        <Typography 
          variant="h6" 
          gutterBottom 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1,
            color: 'primary.main',
            fontWeight: 600
          }}
        >
          <FolderOpen size={20} />
          📁 选择扫描目录
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 2 }}>
          <Box
            sx={{ 
              flex: 1, 
              p: 2, 
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(245, 242, 208, 0.6) 100%)',
              borderRadius: 2,
              minHeight: 48,
              display: 'flex',
              alignItems: 'center',
              border: '1px solid',
              borderColor: directory ? 'primary.main' : 'divider',
              position: 'relative',
              overflow: 'hidden',
              '&::after': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: directory ? 0 : '-100%',
                width: '100%',
                height: '2px',
                background: 'linear-gradient(135deg, #00BCD4, #1976D2)',
                transition: 'left 0.3s ease',
              }
            }}
          >
            <Typography 
              variant="body1"
              sx={{ 
                color: directory ? 'text.primary' : 'text.secondary',
                fontSize: '0.95rem',
                fontFamily: 'monospace'
              }}
            >
              {directory || '💻 未选择目录 - 点击右侧按钮选择 Minecraft 模组目录'}
            </Typography>
          </Box>
          
          <Button
            variant="contained"
            onClick={selectDirectory}
            startIcon={<FolderOpen size={18} />}
            disabled={isScanning}
            sx={{
              px: 3,
              py: 1.5,
              fontSize: '1rem',
              whiteSpace: 'nowrap'
            }}
          >
            浏览目录
          </Button>
        </Box>
      </Box>

      {/* 现代化扫描控制区域 */}
      <Box 
        className="glass"
        sx={{ 
          mb: 4, 
          p: 4, 
          borderRadius: 3,
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(227, 242, 253, 0.8) 100%)',
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 32px rgba(0, 188, 212, 0.2)',
          }
        }}
      >
        <Typography 
          variant="h6" 
          gutterBottom
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1,
            color: 'primary.main',
            fontWeight: 600,
            mb: 3
          }}
        >
          <Box className={isScanning ? 'pulse' : ''}>
            ⚡
          </Box>
          扫描控制中心
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 3, alignItems: 'center', flexWrap: 'wrap' }}>
          {!isScanning ? (
            <Button
              variant="contained"
              size="large"
              onClick={handleStartScan}
              disabled={!directory}
              startIcon={<Play size={22} />}
              className="modern-button"
              sx={{ 
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                fontWeight: 700,
                minWidth: 160,
                background: directory 
                  ? 'linear-gradient(135deg, #4CAF50 0%, #8BC34A 100%)'
                  : 'linear-gradient(135deg, #9E9E9E 0%, #757575 100%)',
                '&:hover': {
                  background: directory 
                    ? 'linear-gradient(135deg, #8BC34A 0%, #4CAF50 100%)'
                    : 'linear-gradient(135deg, #757575 0%, #9E9E9E 100%)',
                }
              }}
            >
              🚀 开始扫描
            </Button>
          ) : (
            <>
              <Button
                variant="contained"
                size="large"
                disabled
                startIcon={<Clock size={20} />}
                className="pulse"
                sx={{ 
                  minWidth: 160,
                  px: 4,
                  py: 1.5,
                  fontSize: '1.1rem',
                  background: 'linear-gradient(135deg, #FF9800 0%, #FFB300 100%)',
                  color: '#FFFFFF'
                }}
              >
                ⏳ 扫描进行中...
              </Button>
              <Button
                variant="outlined"
                size="large"
                onClick={handleCancelScan}
                startIcon={<Square size={18} />}
                color="error"
                sx={{
                  px: 3,
                  py: 1.5,
                  fontSize: '1rem',
                  borderWidth: 2,
                  '&:hover': {
                    borderWidth: 2,
                  }
                }}
              >
                ⏹️ 取消扫描
              </Button>
            </>
          )}
          
          {/* 扫描配置信息 */}
          <Box 
            sx={{ 
              ml: 'auto', 
              display: 'flex', 
              flexDirection: 'column',
              alignItems: 'flex-end',
              gap: 0.5
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box 
                className="status-indicator active"
                sx={{ 
                  width: 8, 
                  height: 8, 
                  borderRadius: '50%', 
                  bgcolor: 'success.main'
                }}
              />
              <Typography variant="body2" color="text.secondary">
                📊 增量扫描模式
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              🔧 智能检测 • 实时统计 • 增量更新
            </Typography>
          </Box>
        </Box>
        
        {/* 实时状态指示器 */}
        {isScanning && scanStatus && (
          <Box 
            sx={{ 
              mt: 3, 
              p: 2, 
              background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(103, 58, 183, 0.05) 100%)',
              borderRadius: 2,
              border: '1px solid',
              borderColor: 'info.main',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            <Box className="shimmer" sx={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2 }} />
            <Typography 
              variant="body2" 
              sx={{ 
                color: 'info.main',
                fontFamily: 'monospace',
                fontWeight: 600
              }}
            >
              🆔 <strong>扫描会话:</strong> {currentScanId} • 
              📊 <strong>当前状态:</strong> {scanStatus.status.toUpperCase()} • 
              📈 <strong>完成度:</strong> {Math.round(scanStatus.progress)}%
            </Typography>
          </Box>
        )}
      </Box>

      {/* 实时扫描进度 - 使用新的增强组件 */}
      {(scanStatus || isScanning) && (
        <Box sx={{ mb: 3 }}>
          <RealTimeProgressIndicator
            scanId={currentScanId || 'debug-scan'}
            progress={scanStatus?.progress || 0}
            status={scanStatus?.status || (isScanning ? 'running' : 'pending')}
            currentFile={scanStatus?.current_file || (isScanning ? '正在初始化扫描...' : undefined)}
            statistics={{
              total_files: scanStatus?.total_files || 0,
              processed_files: scanStatus?.processed_files || 0,
              total_mods: scanStatus?.total_mods || 0,
              total_language_files: scanStatus?.total_language_files || 0,
              total_keys: scanStatus?.total_keys || 0,
              scan_duration_ms: scanStatus?.status === 'completed' && scanStatus?.started_at 
                ? Date.now() - scanStatus.started_at.getTime()
                : undefined
            }}
            error={scanStatus?.error || progressError?.message}
            startTime={scanStatus?.started_at || (isScanning ? new Date() : undefined)}
            estimatedTimeRemaining={estimatedTimeRemaining || undefined}
            onCancel={handleCancelScan}
            animated={true}
            compact={false}
            showDetails={true}
          />
        </Box>
      )}

      {/* 扫描完成结果 */}
      {scanResult && (
        <Box sx={{ p: 3, bgcolor: 'success.light', borderRadius: 2, border: '2px solid', borderColor: 'success.main' }}>
          <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3, color: 'success.contrastText' }}>
            <CheckCircle size={24} />
            🎉 扫描成功完成！
          </Typography>
          
          {/* 主要统计数据 */}
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 3, mb: 3 }}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(255,255,255,0.9)', borderRadius: 2, boxShadow: 1 }}>
              <Typography variant="h3" color="success.main" fontWeight="bold" sx={{ mb: 1 }}>
                {scanResult.statistics.total_mods}
              </Typography>
              <Typography variant="h6" color="text.primary">
                发现模组
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Minecraft 模组包
              </Typography>
            </Box>
            
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(255,255,255,0.9)', borderRadius: 2, boxShadow: 1 }}>
              <Typography variant="h3" color="info.main" fontWeight="bold" sx={{ mb: 1 }}>
                {scanResult.statistics.total_language_files}
              </Typography>
              <Typography variant="h6" color="text.primary">
                语言文件
              </Typography>
              <Typography variant="caption" color="text.secondary">
                本地化资源文件
              </Typography>
            </Box>
            
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(255,255,255,0.9)', borderRadius: 2, boxShadow: 1 }}>
              <Typography variant="h3" color="warning.main" fontWeight="bold" sx={{ mb: 1 }}>
                {scanResult.statistics.total_keys.toLocaleString()}
              </Typography>
              <Typography variant="h6" color="text.primary">
                翻译条目
              </Typography>
              <Typography variant="caption" color="text.secondary">
                待翻译文本条目
              </Typography>
            </Box>
          </Box>
          
          {/* 性能指标 */}
          {scanResult.statistics.scan_duration_ms && (
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, bgcolor: 'rgba(255,255,255,0.7)', borderRadius: 1, mb: 2 }}>
              <Typography variant="body2" color="text.primary">
                <strong>扫描耗时:</strong> {Math.round(scanResult.statistics.scan_duration_ms / 1000)}秒
              </Typography>
              {scanResult.statistics.total_files && (
                <Typography variant="body2" color="text.primary">
                  <strong>处理速度:</strong> {Math.round(scanResult.statistics.total_files / (scanResult.statistics.scan_duration_ms / 1000))} 文件/秒
                </Typography>
              )}
            </Box>
          )}
          
          {/* 快速操作按钮 */}
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 2 }}>
            <Button variant="contained" color="primary" size="large">
              查看详细结果
            </Button>
            <Button variant="outlined" color="primary" size="large">
              导出扫描报告
            </Button>
            <Button variant="text" color="primary" size="large" onClick={() => { setCurrentScanId(null); }}>
              重新扫描
            </Button>
          </Box>
        </Box>
      )}

      <Alert severity="info" sx={{ mt: 3 }}>
        <strong>最优架构特性：</strong>
        <br />
        • 使用依赖注入的服务架构
        <br />
        • 类型安全的服务访问
        <br />
        • 现代化的React Hooks模式
        <br />
        • 统一的错误处理和状态管理
      </Alert>
    </Box>
  );
}