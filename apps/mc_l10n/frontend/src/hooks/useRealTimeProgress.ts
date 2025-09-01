/**
 * 实时进度监控 Hook
 * 提供平滑的进度更新、状态管理和自适应轮询机制
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { ScanStatus, ScanResult } from '../services/domain/types';
import { getScanService } from '../services';

interface ProgressSnapshot {
  timestamp: number;
  progress: number;
  processed_files: number;
}

interface UseRealTimeProgressOptions {
  scanId?: string;
  pollingInterval?: number;
  smoothingEnabled?: boolean;
  adaptivePolling?: boolean;
  onStatusChange?: (status: ScanStatus) => void;
  onComplete?: (result: ScanResult) => void;
  onError?: (error: any) => void;
}

interface UseRealTimeProgressReturn {
  status: ScanStatus | null;
  result: ScanResult | null;
  isPolling: boolean;
  error: any;
  startPolling: (scanId: string) => void;
  stopPolling: () => void;
  estimatedTimeRemaining: number | null;
  processingSpeed: number | null;
}

export const useRealTimeProgress = (
  options: UseRealTimeProgressOptions = {}
): UseRealTimeProgressReturn => {
  const {
    scanId: initialScanId,
    pollingInterval = 1000,
    smoothingEnabled = true,
    adaptivePolling = true,
    onStatusChange,
    onComplete,
    onError,
  } = options;

  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<any>(null);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null);
  const [processingSpeed, setProcessingSpeed] = useState<number | null>(null);

  const scanService = getScanService();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentScanId = useRef<string | null>(null);
  const progressHistory = useRef<ProgressSnapshot[]>([]);
  const lastUpdateTime = useRef<number>(0);
  const currentPollingInterval = useRef<number>(pollingInterval);

  // 自适应轮询间隔调整
  const adjustPollingInterval = useCallback((currentStatus: ScanStatus) => {
    if (!adaptivePolling) return;

    // 根据进度速度调整轮询频率
    const progressRate = processingSpeed || 0;
    
    if (progressRate > 50) {
      // 高速处理时，增加轮询频率
      currentPollingInterval.current = Math.max(500, pollingInterval * 0.5);
    } else if (progressRate > 10) {
      // 中速处理时，使用默认频率
      currentPollingInterval.current = pollingInterval;
    } else {
      // 低速处理时，降低轮询频率
      currentPollingInterval.current = Math.min(3000, pollingInterval * 2);
    }

    // 接近完成时增加轮询频率
    if (currentStatus.progress >= 90) {
      currentPollingInterval.current = Math.max(500, currentPollingInterval.current * 0.5);
    }
  }, [pollingInterval, adaptivePolling, processingSpeed]);

  // 计算处理速度和预估剩余时间
  const calculateMetrics = useCallback((newStatus: ScanStatus) => {
    const now = Date.now();
    const snapshot: ProgressSnapshot = {
      timestamp: now,
      progress: newStatus.progress,
      processed_files: newStatus.processed_files,
    };

    progressHistory.current.push(snapshot);

    // 保留最近30秒的历史数据
    const cutoff = now - 30000;
    progressHistory.current = progressHistory.current.filter(s => s.timestamp >= cutoff);

    if (progressHistory.current.length >= 2) {
      const oldest = progressHistory.current[0];
      const latest = progressHistory.current[progressHistory.current.length - 1];
      
      const timeDiff = (latest.timestamp - oldest.timestamp) / 1000; // 秒
      const filesDiff = latest.processed_files - oldest.processed_files;
      const progressDiff = latest.progress - oldest.progress;

      if (timeDiff > 0) {
        // 计算文件处理速度（文件/秒）
        const speed = filesDiff / timeDiff;
        setProcessingSpeed(speed);

        // 计算预估剩余时间
        if (progressDiff > 0 && newStatus.progress < 100) {
          const remainingProgress = 100 - newStatus.progress;
          const remainingTime = (remainingProgress / progressDiff) * timeDiff * 1000; // 毫秒
          setEstimatedTimeRemaining(Math.max(0, remainingTime));
        }
      }
    }
  }, []);

  // 执行状态轮询
  const pollStatus = useCallback(async () => {
    if (!currentScanId.current) return;

    try {
      const response = await scanService.getStatus(currentScanId.current);
      
      if (response.success && response.data) {
        const newStatus = response.data;
        setStatus(newStatus);
        setError(null);

        // 计算性能指标
        calculateMetrics(newStatus);

        // 调整轮询间隔
        adjustPollingInterval(newStatus);

        // 触发状态变化回调
        onStatusChange?.(newStatus);

        // 检查是否完成
        if (newStatus.status === 'completed') {
          setIsPolling(false);
          
          // 获取最终结果
          const resultResponse = await scanService.getResults(currentScanId.current);
          if (resultResponse.success && resultResponse.data) {
            setResult(resultResponse.data);
            onComplete?.(resultResponse.data);
          }
          
          return;
        }

        // 检查是否失败或取消
        if (newStatus.status === 'failed' || newStatus.status === 'cancelled') {
          setIsPolling(false);
          return;
        }

      } else {
        setError(response.error);
        onError?.(response.error);
      }
    } catch (err) {
      console.error('轮询状态时出错:', err);
      setError(err);
      onError?.(err);
    }
  }, [scanService, calculateMetrics, adjustPollingInterval, onStatusChange, onComplete, onError]);

  // 启动轮询
  const startPolling = useCallback((scanId: string) => {
    console.log(`🔄 开始轮询扫描状态: ${scanId}`);
    
    // 停止当前轮询
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // 重置状态
    currentScanId.current = scanId;
    progressHistory.current = [];
    setStatus(null);
    setResult(null);
    setError(null);
    setEstimatedTimeRemaining(null);
    setProcessingSpeed(null);
    setIsPolling(true);
    lastUpdateTime.current = Date.now();

    // 立即执行一次轮询
    pollStatus();

    // 启动定时轮询
    const poll = () => {
      if (isPolling) {
        pollStatus();
        intervalRef.current = setTimeout(poll, currentPollingInterval.current);
      }
    };
    
    intervalRef.current = setTimeout(poll, currentPollingInterval.current);
  }, [pollStatus, isPolling]);

  // 停止轮询
  const stopPolling = useCallback(() => {
    console.log('⏹️ 停止轮询扫描状态');
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    currentScanId.current = null;
    setIsPolling(false);
    progressHistory.current = [];
  }, []);

  // 自动启动轮询（如果提供了初始扫描ID）
  useEffect(() => {
    if (initialScanId) {
      startPolling(initialScanId);
    }
    
    return () => {
      stopPolling();
    };
  }, [initialScanId, startPolling, stopPolling]);

  // 清理资源
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    status,
    result,
    isPolling,
    error,
    startPolling,
    stopPolling,
    estimatedTimeRemaining,
    processingSpeed,
  };
};

export default useRealTimeProgress;