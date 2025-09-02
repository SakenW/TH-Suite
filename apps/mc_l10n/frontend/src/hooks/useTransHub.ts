/**
 * Trans-Hub 连接管理 Hook
 * 提供与 Trans-Hub 服务器的连接状态管理
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { transHubService, ConnectionStatus, ServerConfig, TranslationStatus } from '../services/transhubService';
import { useNotification } from './useNotification';

export interface UseTransHubReturn {
  // 状态
  isConnected: boolean;
  connectionStatus: ConnectionStatus | null;
  isConnecting: boolean;
  error: string | null;
  offlineQueueSize: number;
  
  // 方法
  connect: (config: ServerConfig) => Promise<boolean>;
  disconnect: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  testConnection: (serverUrl: string) => Promise<boolean>;
  syncOfflineQueue: () => Promise<void>;
  
  // 数据操作
  uploadScanResults: (projectId: string, scanId: string, entries: any, metadata?: any) => Promise<boolean>;
  downloadPatches: (projectId: string, since?: string) => Promise<any>;
  getTranslationStatus: (projectId: string, targetLanguage?: string) => Promise<TranslationStatus>;
}

export function useTransHub(): UseTransHubReturn {
  const notification = useNotification();
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const statusCheckInterval = useRef<NodeJS.Timeout>();

  // 获取连接状态
  const refreshStatus = useCallback(async () => {
    try {
      const status = await transHubService.getStatus();
      setConnectionStatus(status);
      setError(null);
    } catch (err) {
      console.error('Failed to refresh status:', err);
    }
  }, []);

  // 连接到服务器
  const connect = useCallback(async (config: ServerConfig): Promise<boolean> => {
    setIsConnecting(true);
    setError(null);

    try {
      const status = await transHubService.connect(config);
      setConnectionStatus(status);
      
      if (status.connected) {
        notification.success('连接成功', `已连接到 ${status.serverUrl}`);
        
        // 启动状态检查定时器
        if (statusCheckInterval.current) {
          clearInterval(statusCheckInterval.current);
        }
        statusCheckInterval.current = setInterval(refreshStatus, 30000); // 每30秒检查一次
        
        // 如果有离线队列，提示同步
        if (status.offlineQueueSize > 0) {
          notification.info(
            '离线队列', 
            `有 ${status.offlineQueueSize} 个待同步项目`
          );
        }
        
        return true;
      } else {
        notification.warning('连接失败', status.message);
        return false;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '连接失败';
      setError(message);
      notification.error('连接错误', message);
      return false;
    } finally {
      setIsConnecting(false);
    }
  }, [notification, refreshStatus]);

  // 断开连接
  const disconnect = useCallback(async () => {
    try {
      await transHubService.disconnect();
      setConnectionStatus(null);
      
      // 停止状态检查
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
        statusCheckInterval.current = undefined;
      }
      
      notification.info('已断开连接', 'Trans-Hub 连接已关闭');
    } catch (err) {
      const message = err instanceof Error ? err.message : '断开连接失败';
      setError(message);
      notification.error('断开连接错误', message);
    }
  }, [notification]);

  // 测试连接
  const testConnection = useCallback(async (serverUrl: string): Promise<boolean> => {
    try {
      const result = await transHubService.testConnection(serverUrl);
      
      if (result.reachable) {
        notification.success('测试成功', `服务器 ${serverUrl} 可访问`);
        return true;
      } else {
        notification.warning('测试失败', result.error || '服务器不可访问');
        return false;
      }
    } catch (err) {
      notification.error('测试错误', '无法测试服务器连接');
      return false;
    }
  }, [notification]);

  // 同步离线队列
  const syncOfflineQueue = useCallback(async () => {
    try {
      const result = await transHubService.syncOfflineQueue();
      
      if (result.success) {
        notification.success(
          '同步完成', 
          `离线队列已同步，剩余 ${result.remainingQueueSize} 项`
        );
      } else {
        notification.warning('同步失败', result.message);
      }
      
      // 刷新状态
      await refreshStatus();
    } catch (err) {
      notification.error('同步错误', '离线队列同步失败');
    }
  }, [notification, refreshStatus]);

  // 上传扫描结果
  const uploadScanResults = useCallback(async (
    projectId: string,
    scanId: string,
    entries: any,
    metadata?: any
  ): Promise<boolean> => {
    try {
      const result = await transHubService.uploadScanResults({
        projectId,
        scanId,
        entries,
        metadata
      });
      
      if (result.success) {
        if (result.queued) {
          notification.info('已加入队列', '扫描结果已加入离线队列');
        } else {
          notification.success('上传成功', '扫描结果已上传到服务器');
        }
        return true;
      } else {
        notification.warning('上传失败', result.message);
        return false;
      }
    } catch (err) {
      notification.error('上传错误', '无法上传扫描结果');
      return false;
    }
  }, [notification]);

  // 下载补丁
  const downloadPatches = useCallback(async (projectId: string, since?: string) => {
    try {
      const result = await transHubService.downloadPatches(projectId, since);
      
      if (result.success) {
        const source = result.fromCache ? '缓存' : '服务器';
        notification.success(
          '下载完成', 
          `从${source}获取了 ${result.patchCount} 个补丁`
        );
        return result.patches;
      } else {
        notification.warning('下载失败', '无法下载补丁');
        return [];
      }
    } catch (err) {
      notification.error('下载错误', '补丁下载失败');
      return [];
    }
  }, [notification]);

  // 获取翻译状态
  const getTranslationStatus = useCallback(async (
    projectId: string,
    targetLanguage = 'zh_cn'
  ): Promise<TranslationStatus> => {
    try {
      return await transHubService.getTranslationStatus(projectId, targetLanguage);
    } catch (err) {
      console.error('Failed to get translation status:', err);
      return { available: false };
    }
  }, []);

  // 初始化时获取状态
  useEffect(() => {
    refreshStatus();
    
    // 清理函数
    return () => {
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
      }
    };
  }, [refreshStatus]);

  return {
    // 状态
    isConnected: connectionStatus?.connected || false,
    connectionStatus,
    isConnecting,
    error,
    offlineQueueSize: connectionStatus?.offlineQueueSize || 0,
    
    // 方法
    connect,
    disconnect,
    refreshStatus,
    testConnection,
    syncOfflineQueue,
    
    // 数据操作
    uploadScanResults,
    downloadPatches,
    getTranslationStatus
  };
}