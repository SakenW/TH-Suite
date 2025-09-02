/**
 * Trans-Hub API 客户端服务
 * 用于与 Trans-Hub 服务器通信
 */

import { BaseApiService } from './baseApiService';

export interface ServerConfig {
  baseUrl: string;
  apiKey?: string;
  offlineMode?: boolean;
  autoSync?: boolean;
}

export interface ConnectionStatus {
  connected: boolean;
  status: string;
  serverUrl: string;
  offlineQueueSize: number;
  message: string;
}

export interface UploadRequest {
  projectId: string;
  scanId: string;
  entries: Record<string, Record<string, string>>;
  metadata?: Record<string, any>;
}

export interface BatchUploadOptions {
  chunkSize?: number;  // 每个分片的大小
  maxRetries?: number; // 最大重试次数
  retryDelay?: number; // 重试延迟（毫秒）
  onProgress?: (progress: UploadProgress) => void;
}

export interface UploadProgress {
  totalChunks: number;
  completedChunks: number;
  currentChunk: number;
  percentage: number;
  bytesUploaded: number;
  totalBytes: number;
  speed: number; // bytes/second
  remainingTime: number; // seconds
  status: 'preparing' | 'uploading' | 'completed' | 'failed' | 'retrying';
  error?: string;
}

export interface PatchInfo {
  patchId: string;
  version: string;
  itemCount: number;
  createdAt?: string;
}

export interface TranslationStatus {
  available: boolean;
  totalKeys?: number;
  translatedKeys?: number;
  progress?: number;
  qualityScore?: number;
  lastUpdated?: string;
}

class TransHubService extends BaseApiService {
  private connectionStatus: ConnectionStatus | null = null;

  /**
   * 连接到 Trans-Hub 服务器
   */
  async connect(config: ServerConfig): Promise<ConnectionStatus> {
    try {
      const response = await this.post<ConnectionStatus>('/transhub/connect', config);
      this.connectionStatus = response;
      return response;
    } catch (error) {
      console.error('Failed to connect to Trans-Hub:', error);
      throw error;
    }
  }

  /**
   * 断开连接
   */
  async disconnect(): Promise<void> {
    try {
      await this.post('/transhub/disconnect', {});
      this.connectionStatus = null;
    } catch (error) {
      console.error('Failed to disconnect from Trans-Hub:', error);
      throw error;
    }
  }

  /**
   * 获取连接状态
   */
  async getStatus(): Promise<ConnectionStatus> {
    try {
      const response = await this.get<ConnectionStatus>('/transhub/status');
      this.connectionStatus = response;
      return response;
    } catch (error: any) {
      // Silently handle 404 errors for Trans-Hub endpoints that may not be implemented yet
      if (error?.error?.code === 'NOT_FOUND' || error?.message?.includes('404')) {
        return {
          connected: false,
          status: 'not_implemented',
          serverUrl: '',
          offlineQueueSize: 0,
          message: 'Trans-Hub integration not yet implemented'
        };
      }
      // Only log non-404 errors
      if (!error?.message?.includes('404')) {
        console.error('Failed to get connection status:', error);
      }
      // 返回默认状态
      return {
        connected: false,
        status: 'disconnected',
        serverUrl: '',
        offlineQueueSize: 0,
        message: 'Unable to get status'
      };
    }
  }

  /**
   * 上传扫描结果
   */
  async uploadScanResults(request: UploadRequest): Promise<{
    success: boolean;
    message: string;
    queued: boolean;
    scanId: string;
  }> {
    try {
      return await this.post('/transhub/upload', request);
    } catch (error) {
      console.error('Failed to upload scan results:', error);
      throw error;
    }
  }

  /**
   * 批量上传扫描结果（分片传输）
   */
  async batchUploadScanResults(
    request: UploadRequest,
    options: BatchUploadOptions = {}
  ): Promise<{
    success: boolean;
    message: string;
    uploadId: string;
    totalChunks: number;
  }> {
    const {
      chunkSize = 100, // 默认每个分片100个条目
      maxRetries = 3,
      retryDelay = 1000,
      onProgress
    } = options;

    // 将 entries 分割成分片
    const allEntries = Object.entries(request.entries);
    const totalItems = allEntries.length;
    const totalChunks = Math.ceil(totalItems / chunkSize);
    const uploadId = `upload_${Date.now()}_${request.scanId}`;

    let completedChunks = 0;
    const startTime = Date.now();
    let bytesUploaded = 0;
    const totalBytes = JSON.stringify(request.entries).length;

    // 更新进度
    const updateProgress = (status: UploadProgress['status'], error?: string) => {
      if (onProgress) {
        const elapsed = (Date.now() - startTime) / 1000;
        const speed = elapsed > 0 ? bytesUploaded / elapsed : 0;
        const remainingBytes = totalBytes - bytesUploaded;
        const remainingTime = speed > 0 ? remainingBytes / speed : 0;

        onProgress({
          totalChunks,
          completedChunks,
          currentChunk: completedChunks + 1,
          percentage: (completedChunks / totalChunks) * 100,
          bytesUploaded,
          totalBytes,
          speed,
          remainingTime,
          status,
          error
        });
      }
    };

    updateProgress('preparing');

    // 上传每个分片
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, totalItems);
      const chunkEntries = Object.fromEntries(allEntries.slice(start, end));
      const chunkSize = JSON.stringify(chunkEntries).length;

      let retryCount = 0;
      let uploaded = false;

      while (!uploaded && retryCount < maxRetries) {
        try {
          updateProgress('uploading');
          
          await this.post('/transhub/upload-chunk', {
            uploadId,
            projectId: request.projectId,
            scanId: request.scanId,
            chunkIndex: i,
            totalChunks,
            entries: chunkEntries,
            metadata: i === 0 ? request.metadata : undefined
          });

          uploaded = true;
          completedChunks++;
          bytesUploaded += chunkSize;
          updateProgress('uploading');
        } catch (error) {
          retryCount++;
          if (retryCount < maxRetries) {
            updateProgress('retrying', error instanceof Error ? error.message : 'Upload failed');
            await new Promise(resolve => setTimeout(resolve, retryDelay * retryCount));
          } else {
            updateProgress('failed', error instanceof Error ? error.message : 'Upload failed');
            throw error;
          }
        }
      }
    }

    updateProgress('completed');

    return {
      success: true,
      message: `Successfully uploaded ${totalChunks} chunks`,
      uploadId,
      totalChunks
    };
  }

  /**
   * 上传单个分片（带重试）
   */
  private async uploadChunkWithRetry(
    chunk: any,
    maxRetries: number,
    retryDelay: number
  ): Promise<void> {
    let retryCount = 0;
    let lastError: Error | null = null;

    while (retryCount < maxRetries) {
      try {
        await this.post('/transhub/upload-chunk', chunk);
        return; // 成功上传
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');
        retryCount++;
        
        if (retryCount < maxRetries) {
          // 指数退避
          const delay = retryDelay * Math.pow(2, retryCount - 1);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    // 所有重试都失败
    throw lastError || new Error('Upload failed after max retries');
  }

  /**
   * 下载补丁
   */
  async downloadPatches(projectId: string, since?: string): Promise<{
    success: boolean;
    patchCount: number;
    patches: PatchInfo[];
    fromCache: boolean;
  }> {
    try {
      return await this.post('/transhub/download-patches', {
        projectId,
        since
      });
    } catch (error) {
      console.error('Failed to download patches:', error);
      throw error;
    }
  }

  /**
   * 应用补丁
   */
  async applyPatch(patchId: string, strategy: 'overlay' | 'jar_inplace' = 'overlay', dryRun = false): Promise<{
    success: boolean;
    message: string;
    patchId: string;
  }> {
    try {
      return await this.post('/transhub/apply-patch', {
        patchId,
        strategy,
        dryRun
      });
    } catch (error) {
      console.error('Failed to apply patch:', error);
      throw error;
    }
  }

  /**
   * 获取翻译状态
   */
  async getTranslationStatus(projectId: string, targetLanguage = 'zh_cn'): Promise<TranslationStatus> {
    try {
      return await this.get(`/transhub/translation-status/${projectId}?target_language=${targetLanguage}`);
    } catch (error) {
      console.error('Failed to get translation status:', error);
      return {
        available: false
      };
    }
  }

  /**
   * 同步离线队列
   */
  async syncOfflineQueue(onProgress?: (progress: UploadProgress) => void): Promise<{
    success: boolean;
    message: string;
    remainingQueueSize: number;
  }> {
    try {
      // 获取离线队列大小
      const status = await this.getStatus();
      const queueSize = status.offlineQueueSize;
      
      if (queueSize === 0) {
        return {
          success: true,
          message: 'No items in offline queue',
          remainingQueueSize: 0
        };
      }

      // 开始同步
      if (onProgress) {
        onProgress({
          totalChunks: queueSize,
          completedChunks: 0,
          currentChunk: 1,
          percentage: 0,
          bytesUploaded: 0,
          totalBytes: 0,
          speed: 0,
          remainingTime: 0,
          status: 'uploading'
        });
      }

      const result = await this.post('/transhub/sync-offline', {});
      
      if (onProgress) {
        onProgress({
          totalChunks: queueSize,
          completedChunks: queueSize - result.remainingQueueSize,
          currentChunk: queueSize,
          percentage: 100,
          bytesUploaded: 0,
          totalBytes: 0,
          speed: 0,
          remainingTime: 0,
          status: 'completed'
        });
      }

      return result;
    } catch (error) {
      if (onProgress) {
        onProgress({
          totalChunks: 0,
          completedChunks: 0,
          currentChunk: 0,
          percentage: 0,
          bytesUploaded: 0,
          totalBytes: 0,
          speed: 0,
          remainingTime: 0,
          status: 'failed',
          error: error instanceof Error ? error.message : 'Sync failed'
        });
      }
      console.error('Failed to sync offline queue:', error);
      throw error;
    }
  }

  /**
   * 测试服务器连接
   */
  async testConnection(serverUrl: string): Promise<{
    reachable: boolean;
    serverUrl: string;
    message?: string;
    error?: string;
  }> {
    try {
      return await this.get(`/transhub/test-connection?server_url=${encodeURIComponent(serverUrl)}`);
    } catch (error) {
      console.error('Failed to test connection:', error);
      return {
        reachable: false,
        serverUrl,
        error: error instanceof Error ? error.message : 'Connection test failed'
      };
    }
  }

  /**
   * 获取当前连接状态（缓存）
   */
  getCurrentStatus(): ConnectionStatus | null {
    return this.connectionStatus;
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.connectionStatus?.connected || false;
  }

  /**
   * 获取离线队列大小
   */
  getOfflineQueueSize(): number {
    return this.connectionStatus?.offlineQueueSize || 0;
  }
}

// 导出单例
export const transHubService = new TransHubService();

// 导出类型
export type { TransHubService };