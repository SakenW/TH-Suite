/**
 * Trans-Hub 连接状态栏组件
 * 显示与 Trans-Hub 服务器的连接状态
 */

import React from 'react';
import {
  Box,
  Chip,
  IconButton,
  Tooltip,
  Typography,
  Badge,
  CircularProgress
} from '@mui/material';
import {
  Wifi,
  WifiOff,
  Cloud,
  CloudOff,
  RefreshCw,
  Upload,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTransHub } from '../hooks/useTransHub';

interface TransHubStatusBarProps {
  compact?: boolean;
  showDetails?: boolean;
  onStatusClick?: () => void;
}

export const TransHubStatusBar: React.FC<TransHubStatusBarProps> = ({
  compact = false,
  showDetails = true,
  onStatusClick
}) => {
  const {
    isConnected,
    connectionStatus,
    isConnecting,
    offlineQueueSize,
    refreshStatus,
    syncOfflineQueue
  } = useTransHub();

  // 获取状态颜色
  const getStatusColor = () => {
    if (isConnecting) return 'warning';
    if (isConnected) return 'success';
    if (connectionStatus?.status === 'offline') return 'info';
    return 'error';
  };

  // 获取状态图标
  const getStatusIcon = () => {
    if (isConnecting) {
      return <CircularProgress size={16} sx={{ color: 'warning.main' }} />;
    }
    if (isConnected) {
      return <Cloud size={16} />;
    }
    if (connectionStatus?.status === 'offline') {
      return <CloudOff size={16} />;
    }
    return <WifiOff size={16} />;
  };

  // 获取状态文本
  const getStatusText = () => {
    if (isConnecting) return '连接中...';
    if (isConnected) return '已连接';
    if (connectionStatus?.status === 'offline') return '离线模式';
    return '未连接';
  };

  // 处理刷新
  const handleRefresh = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await refreshStatus();
  };

  // 处理同步
  const handleSync = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await syncOfflineQueue();
  };

  if (compact) {
    // 紧凑模式
    return (
      <Tooltip title={`Trans-Hub: ${getStatusText()}`}>
        <Box
          onClick={onStatusClick}
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            cursor: onStatusClick ? 'pointer' : 'default'
          }}
        >
          <Badge badgeContent={offlineQueueSize} color="warning">
            <Chip
              size="small"
              icon={getStatusIcon()}
              label={getStatusText()}
              color={getStatusColor()}
              variant="outlined"
            />
          </Badge>
        </Box>
      </Tooltip>
    );
  }

  // 完整模式
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
      >
        <Box
          onClick={onStatusClick}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            p: 1,
            borderRadius: 1,
            backgroundColor: 'background.paper',
            border: '1px solid',
            borderColor: `${getStatusColor()}.main`,
            cursor: onStatusClick ? 'pointer' : 'default',
            transition: 'all 0.3s ease',
            '&:hover': onStatusClick ? {
              backgroundColor: 'action.hover',
              borderColor: `${getStatusColor()}.dark`
            } : {}
          }}
        >
          {/* 状态图标 */}
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {getStatusIcon()}
          </Box>

          {/* 状态信息 */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" fontWeight="medium">
              Trans-Hub {getStatusText()}
            </Typography>
            
            {showDetails && connectionStatus && (
              <Typography variant="caption" color="text.secondary">
                {connectionStatus.serverUrl || '未配置服务器'}
              </Typography>
            )}
          </Box>

          {/* 离线队列标记 */}
          {offlineQueueSize > 0 && (
            <Tooltip title="离线队列">
              <Badge badgeContent={offlineQueueSize} color="warning">
                <Upload size={16} />
              </Badge>
            </Tooltip>
          )}

          {/* 操作按钮 */}
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {/* 刷新按钮 */}
            <Tooltip title="刷新状态">
              <IconButton
                size="small"
                onClick={handleRefresh}
                disabled={isConnecting}
              >
                <RefreshCw size={14} />
              </IconButton>
            </Tooltip>

            {/* 同步按钮 */}
            {offlineQueueSize > 0 && isConnected && (
              <Tooltip title="同步离线队列">
                <IconButton
                  size="small"
                  onClick={handleSync}
                  color="warning"
                >
                  <Upload size={14} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      </motion.div>
    </AnimatePresence>
  );
};

export default TransHubStatusBar;