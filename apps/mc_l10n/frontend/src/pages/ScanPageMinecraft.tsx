import React, { useState, useEffect } from 'react';
import { Box, Typography, Grid, Chip, Alert, Divider, FormControlLabel, Switch, Tooltip, TextField } from '@mui/material';
import { FolderOpen, Play, Pause, CheckCircle, AlertCircle, Package, FileText, Hash, Clock, Cloud, CloudOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { MinecraftButton } from '../components/minecraft/MinecraftButton';
import { MinecraftCard } from '../components/minecraft/MinecraftCard';
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress';
import { MinecraftBlock, ParticleEffect } from '../components/MinecraftComponents';
import { UploadProgress } from '../components/UploadProgress';
import { useScan } from '../hooks/useServices';
import { useRealTimeProgress } from '../hooks/useRealTimeProgress';
import { useNotification } from '../hooks/useNotification';
import { TauriService } from '../services';
import { useTransHub } from '../hooks/useTransHub';
import { transHubService, type UploadProgress as UploadProgressType } from '../services/transhubService';

const tauriService = new TauriService();

export default function ScanPageMinecraft() {
  const [directory, setDirectory] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [showParticles, setShowParticles] = useState(false);
  const [autoUpload, setAutoUpload] = useState(true); // 默认开启自动上传
  const [uploadProgress, setUploadProgress] = useState<UploadProgressType | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const { startScan, service } = useScan();
  const notification = useNotification();
  const { isConnected, uploadScanResults } = useTransHub();
  
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
    pollingInterval: 800,
    smoothingEnabled: true,
    adaptivePolling: true,
    onStatusChange: (status) => {
      console.log('📊 Status update:', status);
    },
    onComplete: async (result) => {
      console.log('✅ Scan complete:', result);
      setShowParticles(true);
      setTimeout(() => setShowParticles(false), 3000);
      
      notification.achievement(
        '扫描完成！',
        `成功发现 ${result.statistics.total_mods} 个模组，${result.statistics.total_language_files} 个语言文件`,
        { 
          minecraft: { block: 'emerald', particle: true, glow: true },
          actions: [
            { label: '查看详情', onClick: () => console.log('View details'), style: 'primary' },
            { label: '开始翻译', onClick: () => console.log('Start translation'), style: 'secondary' }
          ]
        }
      );
      
      // 自动上传扫描结果到 Trans-Hub
      if (autoUpload && currentScanId) {
        if (isConnected) {
          setIsUploading(true);
          
          try {
            // 准备上传数据
            const entries: Record<string, Record<string, string>> = {};
            
            // 将扫描结果转换为上传格式
            if (result.entries) {
              for (const [modId, modData] of Object.entries(result.entries)) {
                entries[modId] = {};
                if (typeof modData === 'object' && modData !== null && 'entries' in modData) {
                  const mod = modData as any;
                  for (const [key, value] of Object.entries(mod.entries || {})) {
                    if (typeof value === 'string') {
                      entries[modId][key] = value;
                    }
                  }
                }
              }
            }
            
            // 使用批量上传功能
            const uploadResult = await transHubService.batchUploadScanResults(
              {
                projectId: directory, // 使用目录作为项目ID
                scanId: currentScanId,
                entries,
                metadata: {
                  totalMods: result.statistics.total_mods,
                  totalFiles: result.statistics.total_language_files,
                  totalEntries: result.statistics.total_entries,
                  scanTime: new Date().toISOString()
                }
              },
              {
                chunkSize: 100,
                maxRetries: 3,
                retryDelay: 1000,
                onProgress: (progress) => {
                  setUploadProgress(progress);
                }
              }
            );
            
            if (uploadResult.success) {
              notification.success('上传成功', `扫描结果已同步到 Trans-Hub（${uploadResult.totalChunks} 个分片）`);
            } else {
              notification.warning('上传失败', '扫描结果已保存到离线队列');
            }
          } catch (error) {
            console.error('Upload error:', error);
            notification.error('上传错误', '无法上传扫描结果');
            setUploadProgress({
              totalChunks: 0,
              completedChunks: 0,
              currentChunk: 0,
              percentage: 0,
              bytesUploaded: 0,
              totalBytes: 0,
              speed: 0,
              remainingTime: 0,
              status: 'failed',
              error: error instanceof Error ? error.message : '上传失败'
            });
          } finally {
            setIsUploading(false);
          }
        } else {
          notification.info('离线模式', '扫描结果已保存，连接后将自动同步');
        }
      }
      
      setIsScanning(false);
      setCurrentScanId(null);
    },
    onError: (error) => {
      console.error('❌ Scan error:', error);
      notification.error('扫描失败', `错误信息: ${error}`);
      setIsScanning(false);
      setCurrentScanId(null);
    },
  });

  const handleSelectDirectory = async () => {
    // 检查是否在 Tauri 环境中
    if (tauriService.isTauri()) {
      try {
        const selected = await tauriService.selectFolder();
        if (selected) {
          setDirectory(selected);
          notification.success('已选择目录', selected);
        }
      } catch (error) {
        console.error('Failed to select directory:', error);
        notification.error('选择目录失败', '请检查文件系统权限');
      }
    } else {
      // Web 环境下使用手动输入
      const input = prompt('请输入目录路径（支持 Windows 路径格式，如 D:\\Games\\Curseforge\\Minecraft）：');
      if (input) {
        // 转换 Windows 路径为 WSL 路径格式
        let convertedPath = input;
        if (input.match(/^[A-Z]:\\/i)) {
          // 将 D:\path 转换为 /mnt/d/path
          const driveLetter = input[0].toLowerCase();
          convertedPath = `/mnt/${driveLetter}/${input.slice(3).replace(/\\/g, '/')}`;
        }
        setDirectory(convertedPath);
        notification.success('已设置目录', convertedPath);
      }
    }
  };

  const handleStartScan = async () => {
    if (!directory) {
      notification.warning('请先选择目录', '需要选择一个包含模组的目录');
      return;
    }

    setIsScanning(true);
    setShowParticles(false);

    try {
      const scanId = await startScan(directory);
      if (scanId) {
        setCurrentScanId(scanId);
        startPolling(scanId);
        notification.info('扫描已启动', '正在分析目录结构...');
      } else {
        throw new Error('未能获取扫描ID');
      }
    } catch (error) {
      console.error('Failed to start scan:', error);
      notification.error('启动扫描失败', '请检查后端服务是否正常运行');
      setIsScanning(false);
    }
  };

  const handleStopScan = () => {
    if (currentScanId) {
      stopPolling();
      setIsScanning(false);
      setCurrentScanId(null);
      notification.success('扫描已停止');
    }
  };

  const formatTime = (milliseconds: number | null | undefined): string => {
    if (!milliseconds || milliseconds <= 0) return '--:--';
    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = Math.floor(totalSeconds % 60);
    
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatSpeed = (speed: number | null | undefined): string => {
    if (!speed || speed <= 0) return '0.0 文件/秒';
    if (speed < 1) {
      return `${speed.toFixed(2)} 文件/秒`;
    }
    return `${speed.toFixed(1)} 文件/秒`;
  };

  return (
    <Box sx={{ position: 'relative', minHeight: '100vh', p: 3 }}>
      {/* 粒子效果 */}
      <AnimatePresence>
        {showParticles && (
          <ParticleEffect count={50} duration={3000} />
        )}
      </AnimatePresence>

      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography
            variant="h3"
            sx={{
              fontFamily: '"Minecraft", "Press Start 2P", monospace',
              fontSize: { xs: '24px', md: '32px' },
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              background: 'linear-gradient(135deg, #2EAFCC 0%, #17C35C 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              mb: 2,
            }}
          >
            🎮 模组扫描器
          </Typography>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '14px',
              color: 'text.secondary',
              letterSpacing: '0.02em',
            }}
          >
            扫描并识别 Minecraft 模组和资源包
          </Typography>
        </Box>
      </motion.div>

      <Grid container spacing={3}>
        {/* 上传进度 */}
        {uploadProgress && (
          <Grid item xs={12}>
            <UploadProgress
              progress={uploadProgress}
              onCancel={() => setUploadProgress(null)}
              onRetry={async () => {
                // 重试上传逻辑
                setUploadProgress(null);
                // 可以在这里重新触发上传
              }}
              showDetails={true}
              compact={false}
            />
          </Grid>
        )}

        {/* 控制面板 */}
        <Grid item xs={12}>
          <MinecraftCard
            variant="crafting"
            title="控制面板"
            icon="diamond"
            glowing={isScanning}
          >
            <Box sx={{ p: 2 }}>
              {/* 目录选择 */}
              <Box sx={{ mb: 3 }}>
                <Typography
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '12px',
                    color: 'text.secondary',
                    mb: 0.5,
                  }}
                >
                  扫描目录
                </Typography>
                <Typography
                  sx={{
                    fontFamily: '"Minecraft", monospace',
                    fontSize: '10px',
                    color: '#FFA000',
                    mb: 1.5,
                  }}
                >
                  💡 提示：请选择具体的模组文件夹（如 .../ATM10/mods），避免扫描整个 Instances 目录
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  {tauriService.isTauri() ? (
                    <>
                      <Box
                        sx={{
                          flex: 1,
                          p: 1.5,
                          background: 'rgba(0,0,0,0.3)',
                          border: '2px solid #4A4A4A',
                          borderRadius: 0,
                          fontFamily: 'monospace',
                          fontSize: '14px',
                          color: directory ? '#FFFFFF' : '#888888',
                          minHeight: '40px',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        {directory || '请选择目录...'}
                      </Box>
                      <MinecraftButton
                        minecraftStyle="gold"
                        onClick={handleSelectDirectory}
                        disabled={isScanning}
                        startIcon={<FolderOpen size={16} />}
                      >
                        选择
                      </MinecraftButton>
                    </>
                  ) : (
                    <>
                      <TextField
                        fullWidth
                        value={directory}
                        onChange={(e) => {
                          let value = e.target.value;
                          // 自动转换 Windows 路径为 WSL 路径
                          if (value.match(/^[A-Z]:\\/i)) {
                            const driveLetter = value[0].toLowerCase();
                            value = `/mnt/${driveLetter}/${value.slice(3).replace(/\\/g, '/')}`;
                          }
                          setDirectory(value);
                        }}
                        placeholder="输入目录路径（如: D:\Games\Curseforge\Minecraft 或 /mnt/d/Games/Curseforge/Minecraft）"
                        disabled={isScanning}
                        sx={{
                          '& .MuiInputBase-root': {
                            background: 'rgba(0,0,0,0.3)',
                            border: '2px solid #4A4A4A',
                            borderRadius: 0,
                            fontFamily: 'monospace',
                            fontSize: '14px',
                            color: '#FFFFFF',
                            '&:hover': {
                              borderColor: '#6A6A6A',
                            },
                            '&.Mui-focused': {
                              borderColor: '#2EAFCC',
                            },
                          },
                          '& .MuiInputBase-input': {
                            padding: '12px',
                          },
                          '& fieldset': {
                            border: 'none',
                          },
                        }}
                      />
                      <Tooltip title="设置推荐的模组文件夹路径（ATM10）">
                        <MinecraftButton
                          minecraftStyle="gold"
                          onClick={() => {
                            // 设置推荐的ATM10模组路径
                            const recommendedPath = '/mnt/d/Games/Curseforge/Minecraft/Instances/All the Mods 10 - ATM10/mods';
                            setDirectory(recommendedPath);
                            notification.info(
                              '推荐路径', 
                              '已设置ATM10模组路径，请确认路径存在'
                            );
                          }}
                          disabled={isScanning}
                          startIcon={<FolderOpen size={16} />}
                        >
                          ATM10
                        </MinecraftButton>
                      </Tooltip>
                    </>
                  )}
                </Box>
              </Box>

              {/* Trans-Hub 自动上传选项 */}
              <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoUpload}
                      onChange={(e) => setAutoUpload(e.target.checked)}
                      disabled={isScanning}
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': {
                          color: '#2EAFCC',
                        },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                          backgroundColor: '#2EAFCC',
                        },
                      }}
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {autoUpload ? <Cloud size={16} /> : <CloudOff size={16} />}
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '12px',
                        }}
                      >
                        自动上传到 Trans-Hub
                      </Typography>
                    </Box>
                  }
                />
                {isConnected ? (
                  <Chip
                    label="已连接"
                    size="small"
                    icon={<Cloud size={14} />}
                    sx={{
                      bgcolor: 'rgba(46, 175, 204, 0.2)',
                      color: '#2EAFCC',
                      border: '1px solid #2EAFCC',
                    }}
                  />
                ) : (
                  <Tooltip title="未连接到 Trans-Hub 服务器">
                    <Chip
                      label="离线模式"
                      size="small"
                      icon={<CloudOff size={14} />}
                      sx={{
                        bgcolor: 'rgba(255, 152, 0, 0.2)',
                        color: '#FF9800',
                        border: '1px solid #FF9800',
                      }}
                    />
                  </Tooltip>
                )}
              </Box>

              {/* 操作按钮 */}
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                {!isScanning ? (
                  <MinecraftButton
                    minecraftStyle="emerald"
                    onClick={handleStartScan}
                    disabled={!directory}
                    startIcon={<Play size={16} />}
                    glowing
                    sx={{ minWidth: 150 }}
                  >
                    开始扫描
                  </MinecraftButton>
                ) : (
                  <MinecraftButton
                    minecraftStyle="redstone"
                    onClick={handleStopScan}
                    startIcon={<Pause size={16} />}
                    sx={{ minWidth: 150 }}
                  >
                    停止扫描
                  </MinecraftButton>
                )}
              </Box>
            </Box>
          </MinecraftCard>
        </Grid>

        {/* 进度显示 */}
        {(isScanning || scanStatus) && (
          <Grid item xs={12}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <MinecraftCard
                variant="enchantment"
                title="扫描进度"
                icon="emerald"
                glowing
              >
                <Box sx={{ p: 2 }}>
                  {/* 主进度条 */}
                  <MinecraftProgress
                    value={Math.min(100, Math.max(0, scanStatus?.progress || 0))}
                    max={100}  // 进度是百分比，最大值固定为100
                    variant="experience"
                    label="整体进度"
                    animated
                    size="large"
                  />

                  {/* 统计信息 */}
                  <Grid container spacing={2} sx={{ mt: 3 }}>
                    <Grid item xs={6} md={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <MinecraftBlock type="grass" size={32} animated />
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '20px',
                            color: '#FFFFFF',
                            mt: 1,
                            fontWeight: 'bold',
                          }}
                        >
                          {(scanStatus?.processed_files || scanStatus?.current || 0).toLocaleString()}
                        </Typography>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '11px',
                            color: 'text.secondary',
                            mt: 0.5,
                          }}
                        >
                          已处理
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <MinecraftBlock type="diamond" size={32} animated />
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '20px',
                            color: '#FFFFFF',
                            mt: 1,
                            fontWeight: 'bold',
                          }}
                        >
                          {(scanStatus?.total_files || scanStatus?.total || 0).toLocaleString()}
                        </Typography>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '11px',
                            color: 'text.secondary',
                            mt: 0.5,
                          }}
                        >
                          总计
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Box sx={{ fontSize: 32 }}>⚡</Box>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '18px',
                            color: '#FFFFFF',
                            mt: 1,
                            fontWeight: 'bold',
                          }}
                        >
                          {formatSpeed(processingSpeed)}
                        </Typography>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '11px',
                            color: 'text.secondary',
                            mt: 0.5,
                          }}
                        >
                          处理速度
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Box sx={{ fontSize: 32 }}>⏱️</Box>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '20px',
                            color: '#FFFFFF',
                            mt: 1,
                            fontWeight: 'bold',
                          }}
                        >
                          {formatTime(estimatedTimeRemaining)}
                        </Typography>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '11px',
                            color: 'text.secondary',
                            mt: 0.5,
                          }}
                        >
                          剩余时间
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  {/* 当前文件 */}
                  {scanStatus?.current_file && (
                    <Box sx={{ mt: 3, p: 2, background: 'rgba(0,0,0,0.3)', borderRadius: 0 }}>
                      <Typography
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '11px',
                          color: '#888888',
                          mb: 0.5,
                        }}
                      >
                        正在处理:
                      </Typography>
                      <Typography
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '12px',
                          color: '#00FF00',
                          wordBreak: 'break-all',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                        }}
                      >
                        📂 {scanStatus.current_file.split('/').pop() || scanStatus.current_file.split('\\').pop() || scanStatus.current_file}
                      </Typography>
                      <Typography
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '10px',
                          color: '#666666',
                          mt: 0.5,
                          wordBreak: 'break-all',
                        }}
                        title={scanStatus.current_file}
                      >
                        {scanStatus.current_file.length > 80 
                          ? '...' + scanStatus.current_file.slice(-77) 
                          : scanStatus.current_file}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </MinecraftCard>
            </motion.div>
          </Grid>
        )}

        {/* 扫描结果 */}
        {scanResult && (
          <Grid item xs={12}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <MinecraftCard
                variant="chest"
                title="扫描结果"
                icon="gold"
              >
                <Box sx={{ p: 2 }}>
                  {/* 结果统计 */}
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={4}>
                      <Box
                        sx={{
                          p: 2,
                          background: 'rgba(0,0,0,0.2)',
                          border: '2px solid #4A4A4A',
                          borderRadius: 0,
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Package size={20} />
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '14px',
                              color: '#FFD700',
                            }}
                          >
                            模组数量
                          </Typography>
                        </Box>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '24px',
                            color: '#FFFFFF',
                          }}
                        >
                          {scanResult.statistics.total_mods}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Box
                        sx={{
                          p: 2,
                          background: 'rgba(0,0,0,0.2)',
                          border: '2px solid #4A4A4A',
                          borderRadius: 0,
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <FileText size={20} />
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '14px',
                              color: '#87CEEB',
                            }}
                          >
                            语言文件
                          </Typography>
                        </Box>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '24px',
                            color: '#FFFFFF',
                          }}
                        >
                          {scanResult.statistics.total_language_files || scanResult.statistics.total_lang_files || 0}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Box
                        sx={{
                          p: 2,
                          background: 'rgba(0,0,0,0.2)',
                          border: '2px solid #4A4A4A',
                          borderRadius: 0,
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Hash size={20} />
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '14px',
                              color: '#98FB98',
                            }}
                          >
                            翻译键
                          </Typography>
                        </Box>
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '24px',
                            color: '#FFFFFF',
                          }}
                        >
                          {scanResult.statistics.total_keys}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  {/* 模组列表 */}
                  {scanResult.mods && scanResult.mods.length > 0 && (
                    <Box sx={{ mt: 3 }}>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '14px',
                          color: '#FFFFFF',
                          mb: 2,
                        }}
                      >
                        已发现的模组：
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {scanResult.mods.slice(0, 20).map((mod, index) => (
                          <motion.div
                            key={mod.id}
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.2, delay: index * 0.02 }}
                          >
                            <Chip
                              label={mod.name}
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '11px',
                                background: 'linear-gradient(135deg, #4A4A4A 0%, #2A2A2A 100%)',
                                color: '#FFFFFF',
                                border: '1px solid #1A1A1A',
                                borderRadius: 0,
                                '&:hover': {
                                  background: 'linear-gradient(135deg, #5A5A5A 0%, #3A3A3A 100%)',
                                  transform: 'translateY(-2px)',
                                },
                              }}
                            />
                          </motion.div>
                        ))}
                        {scanResult.mods.length > 20 && (
                          <Chip
                            label={`+${scanResult.mods.length - 20} 更多`}
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '11px',
                              background: 'linear-gradient(135deg, #FFD700 0%, #FFA500 100%)',
                              color: '#000000',
                              border: '1px solid #FF8C00',
                              borderRadius: 0,
                            }}
                          />
                        )}
                      </Box>
                    </Box>
                  )}

                  {/* 语言文件列表 */}
                  {scanResult.language_files && scanResult.language_files.length > 0 && (
                    <Box sx={{ mt: 3 }}>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '14px',
                          color: '#FFFFFF',
                          mb: 2,
                        }}
                      >
                        语言文件示例：
                      </Typography>
                      <Box 
                        sx={{ 
                          maxHeight: 200, 
                          overflowY: 'auto',
                          background: 'rgba(0,0,0,0.2)',
                          border: '1px solid #4A4A4A',
                          p: 2,
                        }}
                      >
                        {scanResult.language_files.slice(0, 10).map((file, index) => (
                          <Box
                            key={file.id}
                            sx={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              py: 0.5,
                              borderBottom: index < 9 ? '1px solid #2A2A2A' : 'none',
                            }}
                          >
                            <Typography
                              sx={{
                                fontFamily: 'monospace',
                                fontSize: '11px',
                                color: '#87CEEB',
                              }}
                            >
                              {file.file_name}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 2 }}>
                              <Typography
                                sx={{
                                  fontFamily: 'monospace',
                                  fontSize: '10px',
                                  color: '#888888',
                                }}
                              >
                                {file.language}
                              </Typography>
                              <Typography
                                sx={{
                                  fontFamily: 'monospace',
                                  fontSize: '10px',
                                  color: '#98FB98',
                                }}
                              >
                                {file.key_count} keys
                              </Typography>
                            </Box>
                          </Box>
                        ))}
                        {scanResult.language_files.length > 10 && (
                          <Typography
                            sx={{
                              fontFamily: 'monospace',
                              fontSize: '10px',
                              color: '#FFD700',
                              textAlign: 'center',
                              mt: 1,
                            }}
                          >
                            ... 及其他 {scanResult.language_files.length - 10} 个文件
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  )}

                  {/* 操作按钮 */}
                  <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'center' }}>
                    <MinecraftButton
                      minecraftStyle="diamond"
                      onClick={() => toast.success('功能开发中...', { icon: '🔨' })}
                    >
                      导出结果
                    </MinecraftButton>
                    <MinecraftButton
                      minecraftStyle="emerald"
                      onClick={() => toast.success('功能开发中...', { icon: '🔨' })}
                    >
                      开始翻译
                    </MinecraftButton>
                  </Box>
                </Box>
              </MinecraftCard>
            </motion.div>
          </Grid>
        )}

        {/* 错误提示 */}
        {progressError && (
          <Grid item xs={12}>
            <Alert
              severity="error"
              icon={<AlertCircle size={20} />}
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px',
                background: 'linear-gradient(135deg, rgba(244,67,54,0.2) 0%, rgba(139,0,0,0.2) 100%)',
                border: '2px solid #DC143C',
                borderRadius: 0,
              }}
            >
              {typeof progressError === 'string' ? progressError : progressError?.message || '扫描过程中发生错误'}
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}