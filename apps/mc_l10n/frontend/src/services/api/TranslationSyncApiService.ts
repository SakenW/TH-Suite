/**
 * 翻译同步API服务
 * 提供翻译数据同步的前端API接口
 * 
 * 主要功能:
 * - 准备同步分析
 * - 执行同步操作
 * - 实时状态监控
 * - 冲突解决管理
 * 
 * 作者: Claude Code
 * 创建时间: 2025-09-20
 */

import { BaseApiService } from './BaseApiService';

// ============================================================
// 类型定义
// ============================================================

export interface SyncPrepareRequest {
  direction: 'local_to_remote' | 'remote_to_local' | 'bidirectional';
  language_filters?: string[];
  pack_filters?: string[];
  mod_filters?: string[];
  auto_resolve_conflicts?: boolean;
  conflict_resolution?: 'local_wins' | 'remote_wins' | 'latest_wins' | 'manual_resolve';
  batch_size?: number;
  max_concurrency?: number;
}

export interface SyncExecuteRequest {
  force?: boolean;
  dry_run?: boolean;
}

export interface ConflictResolveRequest {
  conflict_id: string;
  resolution: 'local_wins' | 'remote_wins' | 'manual';
  resolved_entry?: any;
}

export interface SyncProgressResponse {
  session_id: string;
  status: string;
  direction: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  
  // 进度统计
  total_entries: number;
  processed_entries: number;
  success_entries: number;
  failed_entries: number;
  conflicts_entries: number;
  
  // 进度信息
  progress_percentage: number;
  estimated_completion?: string;
  current_operation?: string;
  
  // 错误信息
  errors: string[];
  warnings: string[];
}

export interface SyncAnalysisResponse {
  session_id: string;
  direction: string;
  total_local: number;
  total_remote: number;
  
  // 变更统计
  total_changes: number;
  added: number;
  modified: number;
  deleted: number;
  conflicts: number;
  
  // 详细分析
  by_language: Record<string, number>;
  by_pack: Record<string, number>;
  estimated_time: number;
  
  // 建议
  recommendations: string[];
}

export interface SyncOptimizationStats {
  transfer: {
    batches_created: number;
    batches_transmitted: number;
    batches_failed: number;
    total_bytes_original: number;
    total_bytes_compressed: number;
    compression_ratio: number;
    success_rate: number;
  };
  cache: {
    keyset_fingerprints: {
      total_count: number;
      average_key_count: number;
    };
    cas_objects: {
      total_count: number;
      total_size_bytes: number;
      by_type: Record<string, number>;
    };
  };
  optimization: {
    average_compression_ratio: number;
    cache_efficiency: number;
    total_data_saved: number;
  };
}

// ============================================================
// API服务类
// ============================================================

export class TranslationSyncApiService extends BaseApiService {
  private readonly baseUrl = '/api/v1/sync';

  /**
   * 准备同步，分析差异
   */
  async prepareSync(request: SyncPrepareRequest): Promise<SyncAnalysisResponse> {
    return this.request<SyncAnalysisResponse>({
      method: 'POST',
      url: `${this.baseUrl}/prepare`,
      data: request
    });
  }

  /**
   * 执行同步操作
   */
  async executeSync(sessionId: string, request: SyncExecuteRequest): Promise<{
    success: boolean;
    message: string;
    session_id: string;
    dry_run: boolean;
  }> {
    return this.request({
      method: 'POST',
      url: `${this.baseUrl}/execute/${sessionId}`,
      data: request
    });
  }

  /**
   * 获取同步状态
   */
  async getSyncStatus(sessionId: string): Promise<SyncProgressResponse> {
    return this.request<SyncProgressResponse>({
      method: 'GET',
      url: `${this.baseUrl}/status/${sessionId}`
    });
  }

  /**
   * 获取所有同步会话
   */
  async getAllSyncSessions(status?: string, limit?: number): Promise<SyncProgressResponse[]> {
    const params: Record<string, any> = {};
    if (status) params.status = status;
    if (limit) params.limit = limit;

    return this.request<SyncProgressResponse[]>({
      method: 'GET',
      url: `${this.baseUrl}/sessions`,
      params
    });
  }

  /**
   * 解决冲突
   */
  async resolveConflict(request: ConflictResolveRequest): Promise<{
    success: boolean;
    message: string;
    conflict_id: string;
    resolution: string;
  }> {
    return this.request({
      method: 'POST',
      url: `${this.baseUrl}/resolve-conflict`,
      data: request
    });
  }

  /**
   * 取消同步
   */
  async cancelSync(sessionId: string): Promise<{
    success: boolean;
    message: string;
    session_id: string;
  }> {
    return this.request({
      method: 'DELETE',
      url: `${this.baseUrl}/cancel/${sessionId}`
    });
  }

  /**
   * 快速推送同步
   */
  async quickPushSync(
    language_filters?: string[], 
    pack_filters?: string[]
  ): Promise<{
    success: boolean;
    message: string;
    session_id: string;
    analysis: SyncAnalysisResponse;
    type: string;
  }> {
    return this.request({
      method: 'POST',
      url: `${this.baseUrl}/quick/push`,
      data: {
        language_filters,
        pack_filters
      }
    });
  }

  /**
   * 快速拉取同步
   */
  async quickPullSync(
    language_filters?: string[], 
    pack_filters?: string[]
  ): Promise<{
    success: boolean;
    message: string;
    session_id: string;
    analysis: SyncAnalysisResponse;
    type: string;
  }> {
    return this.request({
      method: 'POST',
      url: `${this.baseUrl}/quick/pull`,
      data: {
        language_filters,
        pack_filters
      }
    });
  }

  /**
   * 获取优化统计信息
   */
  async getOptimizationStats(): Promise<SyncOptimizationStats> {
    // 这个端点需要在后端添加
    return this.request<SyncOptimizationStats>({
      method: 'GET',
      url: `${this.baseUrl}/stats/optimization`
    });
  }

  /**
   * 轮询同步状态直到完成
   */
  async pollSyncStatus(
    sessionId: string,
    onProgress?: (progress: SyncProgressResponse) => void,
    intervalMs: number = 1000
  ): Promise<SyncProgressResponse> {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const progress = await this.getSyncStatus(sessionId);
          
          if (onProgress) {
            onProgress(progress);
          }

          // 检查是否完成
          if (['completed', 'failed', 'cancelled'].includes(progress.status)) {
            resolve(progress);
            return;
          }

          // 继续轮询
          setTimeout(poll, intervalMs);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  /**
   * 创建同步会话的事件流监听
   */
  createSyncStatusStream(sessionId: string): EventSource {
    // 这需要后端支持 Server-Sent Events
    const eventSource = new EventSource(`${this.baseUrl}/stream/${sessionId}`);
    return eventSource;
  }

  /**
   * 批量操作：准备并执行同步
   */
  async prepareAndExecuteSync(
    request: SyncPrepareRequest,
    executeRequest: SyncExecuteRequest = {},
    onProgress?: (progress: SyncProgressResponse) => void
  ): Promise<{
    analysis: SyncAnalysisResponse;
    finalProgress: SyncProgressResponse;
  }> {
    // 1. 准备同步
    const analysis = await this.prepareSync(request);

    // 2. 执行同步
    await this.executeSync(analysis.session_id, executeRequest);

    // 3. 监控进度
    const finalProgress = await this.pollSyncStatus(analysis.session_id, onProgress);

    return { analysis, finalProgress };
  }

  /**
   * 估算同步时间
   */
  estimateSyncTime(analysis: SyncAnalysisResponse): {
    estimatedSeconds: number;
    estimatedMinutes: number;
    complexity: 'low' | 'medium' | 'high';
  } {
    const { total_changes, conflicts, estimated_time } = analysis;

    let complexity: 'low' | 'medium' | 'high' = 'low';
    
    if (conflicts > 10 || total_changes > 1000) {
      complexity = 'high';
    } else if (conflicts > 0 || total_changes > 100) {
      complexity = 'medium';
    }

    // 基础时间加上冲突处理时间
    const baseTime = estimated_time;
    const conflictTime = conflicts * 2; // 每个冲突增加2秒
    const totalSeconds = baseTime + conflictTime;

    return {
      estimatedSeconds: totalSeconds,
      estimatedMinutes: Math.ceil(totalSeconds / 60),
      complexity
    };
  }

  /**
   * 格式化同步状态描述
   */
  formatSyncStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'idle': '等待执行',
      'preparing': '准备同步',
      'detecting_changes': '检测变更',
      'merging': '合并数据',
      'transferring': '传输数据',
      'applying_changes': '应用变更',
      'completed': '同步完成',
      'failed': '同步失败',
      'cancelled': '已取消'
    };

    return statusMap[status] || status;
  }

  /**
   * 格式化同步方向描述
   */
  formatSyncDirection(direction: string): string {
    const directionMap: Record<string, string> = {
      'local_to_remote': '本地 → 远程',
      'remote_to_local': '远程 → 本地',
      'bidirectional': '双向同步'
    };

    return directionMap[direction] || direction;
  }

  /**
   * 计算同步进度百分比
   */
  calculateProgress(progress: SyncProgressResponse): number {
    if (progress.total_entries === 0) return 0;
    return Math.round((progress.processed_entries / progress.total_entries) * 100);
  }

  /**
   * 获取同步状态颜色
   */
  getStatusColor(status: string): string {
    const colorMap: Record<string, string> = {
      'idle': 'gray',
      'preparing': 'blue',
      'detecting_changes': 'blue',
      'merging': 'orange',
      'transferring': 'orange',
      'applying_changes': 'orange',
      'completed': 'green',
      'failed': 'red',
      'cancelled': 'gray'
    };

    return colorMap[status] || 'gray';
  }
}

// ============================================================
// 服务实例
// ============================================================

export const translationSyncApiService = new TranslationSyncApiService();