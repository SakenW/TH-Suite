/**
 * 实时进度指示器组件
 * 专为扫描任务设计的增强型进度显示，支持实时更新、动画效果和丰富的状态展示
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Card,
  CardContent,
  Chip,
  Alert,
  Fade,
  Collapse,
  IconButton,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Play,
  Pause,
  CheckCircle,
  AlertCircle,
  Clock,
  Files,
  Package,
  Languages,
  Key,
  TrendingUp,
  Expand,
  Minimize2,
  Zap,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ScanStatistics {
  total_files: number;
  processed_files: number;
  total_mods: number;
  total_language_files: number;
  total_keys: number;
  scan_duration_ms?: number;
}

interface RealTimeProgressProps {
  scanId?: string;
  progress: number; // 0-100
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  currentFile?: string;
  statistics: ScanStatistics;
  error?: string;
  startTime?: Date;
  estimatedTimeRemaining?: number;
  onCancel?: () => void;
  animated?: boolean;
  compact?: boolean;
  showDetails?: boolean;
}

export const RealTimeProgressIndicator: React.FC<RealTimeProgressProps> = ({
  scanId,
  progress,
  status,
  currentFile,
  statistics,
  error,
  startTime,
  estimatedTimeRemaining,
  onCancel,
  animated = true,
  compact = false,
  showDetails = true,
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(!compact);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [smoothProgress, setSmoothProgress] = useState(progress);
  const [previousStats, setPreviousStats] = useState<ScanStatistics | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 计算经过的时间
  useEffect(() => {
    if (startTime && status === 'running') {
      const updateElapsedTime = () => {
        const now = Date.now();
        const elapsed = Math.floor((now - startTime.getTime()) / 1000);
        setElapsedTime(elapsed);
      };

      updateElapsedTime();
      intervalRef.current = setInterval(updateElapsedTime, 1000);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [startTime, status]);

  // 平滑进度动画
  useEffect(() => {
    if (animated) {
      const targetProgress = Math.max(0, Math.min(100, progress));
      const startProgress = smoothProgress;
      const diff = targetProgress - startProgress;
      
      if (Math.abs(diff) > 0.1) {
        const duration = Math.min(1000, Math.abs(diff) * 20); // 最多1秒动画
        const startTime = Date.now();
        
        const animateProgress = () => {
          const elapsed = Date.now() - startTime;
          const ratio = Math.min(elapsed / duration, 1);
          const easeOutQuart = 1 - Math.pow(1 - ratio, 4);
          const currentProgress = startProgress + diff * easeOutQuart;
          
          setSmoothProgress(currentProgress);
          
          if (ratio < 1) {
            requestAnimationFrame(animateProgress);
          }
        };
        
        requestAnimationFrame(animateProgress);
      } else {
        setSmoothProgress(progress);
      }
    } else {
      setSmoothProgress(progress);
    }
  }, [progress, animated, smoothProgress]);

  // 检测统计数据变化
  useEffect(() => {
    setPreviousStats(statistics);
  }, [statistics]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const formatFileSize = useCallback((bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }, []);

  const getStatusConfig = useCallback(() => {
    switch (status) {
      case 'completed':
        return {
          color: theme.palette.success.main,
          icon: <CheckCircle size={20} />,
          label: '完成',
          bgColor: alpha(theme.palette.success.main, 0.1),
        };
      case 'failed':
        return {
          color: theme.palette.error.main,
          icon: <AlertCircle size={20} />,
          label: '失败',
          bgColor: alpha(theme.palette.error.main, 0.1),
        };
      case 'cancelled':
        return {
          color: theme.palette.warning.main,
          icon: <Pause size={20} />,
          label: '已取消',
          bgColor: alpha(theme.palette.warning.main, 0.1),
        };
      case 'running':
        return {
          color: theme.palette.info.main,
          icon: <Play size={20} />,
          label: '运行中',
          bgColor: alpha(theme.palette.info.main, 0.1),
        };
      default:
        return {
          color: theme.palette.grey[500],
          icon: <Clock size={20} />,
          label: '等待中',
          bgColor: alpha(theme.palette.grey[500], 0.1),
        };
    }
  }, [status, theme]);

  const statusConfig = getStatusConfig();

  const renderCompactView = () => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <motion.div
          animate={{ rotate: status === 'running' ? 360 : 0 }}
          transition={{ duration: 2, repeat: status === 'running' ? Infinity : 0, ease: "linear" }}
        >
          {statusConfig.icon}
        </motion.div>
        <Typography variant="body2" sx={{ fontWeight: 600, color: statusConfig.color }}>
          {statusConfig.label}
        </Typography>
      </Box>
      
      <Box sx={{ flexGrow: 1, minWidth: 100 }}>
        <LinearProgress
          variant="determinate"
          value={smoothProgress}
          sx={{
            height: 6,
            borderRadius: 3,
            backgroundColor: alpha(statusConfig.color, 0.2),
            '& .MuiLinearProgress-bar': {
              backgroundColor: statusConfig.color,
              borderRadius: 3,
              transition: 'transform 0.3s ease',
            },
          }}
        />
      </Box>
      
      <Typography variant="body2" sx={{ fontWeight: 600, minWidth: 45, textAlign: 'right' }}>
        {Math.round(smoothProgress)}%
      </Typography>
      
      <IconButton size="small" onClick={() => setExpanded(!expanded)}>
        {expanded ? <Minimize2 size={16} /> : <Expand size={16} />}
      </IconButton>
    </Box>
  );

  const renderDetailedView = () => (
    <Card 
      elevation={2}
      sx={{
        borderRadius: 3,
        background: `linear-gradient(135deg, ${statusConfig.bgColor} 0%, ${alpha(statusConfig.color, 0.05)} 100%)`,
        border: `1px solid ${alpha(statusConfig.color, 0.2)}`,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* 顶部装饰条 */}
      <motion.div
        initial={{ width: '0%' }}
        animate={{ width: `${smoothProgress}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          height: 3,
          background: `linear-gradient(90deg, ${statusConfig.color}, ${alpha(statusConfig.color, 0.7)})`,
          borderRadius: '0 3px 3px 0',
        }}
      />

      <CardContent sx={{ pt: 2 }}>
        {/* 状态标题行 */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <motion.div
              animate={{ 
                rotate: status === 'running' ? 360 : 0,
                scale: status === 'running' ? [1, 1.1, 1] : 1 
              }}
              transition={{ 
                rotate: { duration: 2, repeat: status === 'running' ? Infinity : 0, ease: "linear" },
                scale: { duration: 2, repeat: status === 'running' ? Infinity : 0 }
              }}
            >
              <Box
                sx={{
                  p: 1,
                  borderRadius: 2,
                  backgroundColor: alpha(statusConfig.color, 0.1),
                  color: statusConfig.color,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {statusConfig.icon}
              </Box>
            </motion.div>
            
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, color: statusConfig.color, display: 'flex', alignItems: 'center', gap: 1 }}>
                扫描进度 {scanId && <Chip label={`#${scanId.slice(-8)}`} size="small" variant="outlined" />}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                实时扫描状态监控
              </Typography>
            </Box>
          </Box>
          
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="h4" sx={{ fontWeight: 800, color: statusConfig.color }}>
              {Math.round(smoothProgress)}%
            </Typography>
            {status === 'running' && elapsedTime > 0 && (
              <Typography variant="caption" color="text.secondary">
                已用时: {formatTime(elapsedTime)}
              </Typography>
            )}
          </Box>
        </Box>

        {/* 主进度条 */}
        <Box sx={{ mb: 3 }}>
          <LinearProgress
            variant="determinate"
            value={smoothProgress}
            sx={{
              height: 12,
              borderRadius: 6,
              backgroundColor: alpha(statusConfig.color, 0.1),
              '& .MuiLinearProgress-bar': {
                backgroundColor: statusConfig.color,
                borderRadius: 6,
                background: `linear-gradient(90deg, ${statusConfig.color}, ${alpha(statusConfig.color, 0.8)})`,
                transition: 'transform 0.3s ease',
              },
            }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {statistics.processed_files} / {statistics.total_files} 文件
            </Typography>
            {estimatedTimeRemaining && status === 'running' && (
              <Typography variant="caption" color="text.secondary">
                预计剩余: {formatTime(Math.ceil(estimatedTimeRemaining / 1000))}
              </Typography>
            )}
          </Box>
        </Box>

        {/* 当前处理文件 */}
        <AnimatePresence>
          {currentFile && status === 'running' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Box sx={{ 
                mb: 3, 
                p: 2, 
                backgroundColor: alpha(theme.palette.info.main, 0.05),
                borderRadius: 2,
                border: `1px dashed ${alpha(theme.palette.info.main, 0.2)}`,
                position: 'relative',
                overflow: 'hidden'
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <motion.div
                    animate={{ x: [-5, 5, -5] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <Zap size={16} color={theme.palette.info.main} />
                  </motion.div>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.info.main }}>
                    正在处理
                  </Typography>
                </Box>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    wordBreak: 'break-all',
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                    lineHeight: 1.4
                  }}
                >
                  {currentFile}
                </Typography>
              </Box>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 统计信息网格 */}
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 2, mb: 2 }}>
          <motion.div
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.2 }}
          >
            <Box sx={{ 
              textAlign: 'center', 
              p: 2, 
              backgroundColor: alpha(theme.palette.primary.main, 0.1),
              borderRadius: 2,
              border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                <Files size={16} color={theme.palette.primary.main} />
                <Typography variant="h5" color="primary.main" fontWeight="bold">
                  {statistics.processed_files}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  /{statistics.total_files}
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">
                处理文件
              </Typography>
            </Box>
          </motion.div>
          
          {statistics.total_mods > 0 && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              transition={{ duration: 0.2 }}
            >
              <Box sx={{ 
                textAlign: 'center', 
                p: 2, 
                backgroundColor: alpha(theme.palette.success.main, 0.1),
                borderRadius: 2,
                border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                  <Package size={16} color={theme.palette.success.main} />
                  <Typography variant="h5" color="success.main" fontWeight="bold">
                    {statistics.total_mods}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  发现模组
                </Typography>
              </Box>
            </motion.div>
          )}
          
          {statistics.total_language_files > 0 && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              transition={{ duration: 0.2 }}
            >
              <Box sx={{ 
                textAlign: 'center', 
                p: 2, 
                backgroundColor: alpha(theme.palette.info.main, 0.1),
                borderRadius: 2,
                border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                  <Languages size={16} color={theme.palette.info.main} />
                  <Typography variant="h5" color="info.main" fontWeight="bold">
                    {statistics.total_language_files}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  语言文件
                </Typography>
              </Box>
            </motion.div>
          )}
          
          {statistics.total_keys > 0 && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              transition={{ duration: 0.2 }}
            >
              <Box sx={{ 
                textAlign: 'center', 
                p: 2, 
                backgroundColor: alpha(theme.palette.warning.main, 0.1),
                borderRadius: 2,
                border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                  <Key size={16} color={theme.palette.warning.main} />
                  <Typography variant="h5" color="warning.main" fontWeight="bold">
                    {statistics.total_keys.toLocaleString()}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  翻译条目
                </Typography>
              </Box>
            </motion.div>
          )}
        </Box>

        {/* 性能指标 */}
        {statistics.scan_duration_ms && status === 'completed' && (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            p: 2, 
            backgroundColor: alpha(theme.palette.success.main, 0.05),
            borderRadius: 2, 
            border: `1px solid ${alpha(theme.palette.success.main, 0.1)}`,
            mb: 2 
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <TrendingUp size={16} color={theme.palette.success.main} />
              <Typography variant="body2" color="text.primary">
                <strong>扫描耗时:</strong> {Math.round(statistics.scan_duration_ms / 1000)}秒
              </Typography>
            </Box>
            {statistics.total_files > 0 && (
              <Typography variant="body2" color="text.primary">
                <strong>处理速度:</strong> {Math.round(statistics.total_files / (statistics.scan_duration_ms / 1000))} 文件/秒
              </Typography>
            )}
          </Box>
        )}

        {/* 错误信息 */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Alert severity="error" sx={{ mb: 2 }}>
                <strong>扫描错误:</strong> {error}
              </Alert>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 操作按钮 */}
        {status === 'running' && onCancel && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              style={{
                background: 'none',
                border: `2px solid ${theme.palette.error.main}`,
                borderRadius: 8,
                padding: '8px 16px',
                color: theme.palette.error.main,
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
              onClick={onCancel}
            >
              取消扫描
            </motion.button>
          </Box>
        )}
      </CardContent>
    </Card>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {compact && !expanded ? renderCompactView() : renderDetailedView()}
    </motion.div>
  );
};

export default RealTimeProgressIndicator;