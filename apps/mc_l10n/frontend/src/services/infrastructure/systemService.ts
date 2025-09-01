/**
 * 系统管理服务
 * 处理系统信息、健康检查、任务管理等
 */

import { 
  ApiResponse,
  HealthCheckResponse,
  SystemInfo,
  AsyncTask,
  SearchResult
} from '../types/api';
import { BaseApiService } from '../baseApiService';

class SystemService extends BaseApiService {
  /**
   * 健康检查
   */
  async healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
    return this.get<HealthCheckResponse>('/health');
  }

  /**
   * 获取系统信息
   */
  async getSystemInfo(): Promise<ApiResponse<SystemInfo>> {
    return this.get<SystemInfo>('/info');
  }

  // ==================== 异步任务管理 ====================

  /**
   * 获取任务列表
   */
  async getTasks(params?: {
    task_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<{
    tasks: AsyncTask[];
    total: number;
  }>> {
    return this.get('/tasks', params);
  }

  /**
   * 获取任务详情
   */
  async getTask(taskId: string): Promise<ApiResponse<AsyncTask>> {
    return this.get<AsyncTask>(`/tasks/${taskId}`);
  }

  /**
   * 取消任务
   */
  async cancelTask(taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/tasks/${taskId}/cancel`);
  }

  /**
   * 重试失败的任务
   */
  async retryTask(taskId: string): Promise<ApiResponse<AsyncTask>> {
    return this.post<AsyncTask>(`/tasks/${taskId}/retry`);
  }

  /**
   * 删除已完成的任务
   */
  async deleteTask(taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/tasks/${taskId}`);
  }

  /**
   * 批量删除已完成的任务
   */
  async cleanupTasks(olderThan?: string): Promise<ApiResponse<{
    deleted_count: number;
    message: string;
  }>> {
    const params = olderThan ? { older_than: olderThan } : {};
    return this.post('/tasks/cleanup', params);
  }

  // ==================== 全局搜索 ====================

  /**
   * 全局搜索
   */
  async globalSearch(params: {
    q: string;
    types?: string[]; // ['projects', 'mods', 'translations']
    filters?: Record<string, any>;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<SearchResult<any>>> {
    return this.get<SearchResult<any>>('/search', params);
  }

  /**
   * 搜索建议
   */
  async getSearchSuggestions(query: string, type?: string): Promise<ApiResponse<{
    suggestions: string[];
    recent_searches: string[];
  }>> {
    const params: any = { q: query };
    if (type) params.type = type;
    return this.get('/search/suggestions', params);
  }

  // ==================== 配置管理 ====================

  /**
   * 获取系统配置
   */
  async getSystemConfig(): Promise<ApiResponse<{
    database: {
      url: string;
      max_connections: number;
      pool_timeout: number;
    };
    logging: {
      level: string;
      file_path?: string;
      max_size?: string;
    };
    security: {
      cors_origins: string[];
      auth_enabled: boolean;
    };
    features: {
      auto_translation: boolean;
      quality_checks: boolean;
      collaboration: boolean;
    };
    limits: {
      max_file_size: number;
      max_entries_per_project: number;
      concurrent_tasks: number;
    };
  }>> {
    return this.get('/config');
  }

  /**
   * 更新系统配置
   */
  async updateSystemConfig(config: Record<string, any>): Promise<ApiResponse<{ message: string }>> {
    return this.patch('/config', config);
  }

  /**
   * 重置配置为默认值
   */
  async resetSystemConfig(): Promise<ApiResponse<{ message: string }>> {
    return this.post('/config/reset');
  }

  // ==================== 备份和恢复 ====================

  /**
   * 创建数据备份
   */
  async createBackup(data?: {
    include_files?: boolean;
    compression_level?: number;
    description?: string;
  }): Promise<ApiResponse<AsyncTask>> {
    return this.post<AsyncTask>('/backup/create', data);
  }

  /**
   * 获取备份列表
   */
  async getBackups(): Promise<ApiResponse<Array<{
    id: string;
    filename: string;
    size: number;
    created_at: string;
    description?: string;
    includes_files: boolean;
  }>>> {
    return this.get('/backup/list');
  }

  /**
   * 下载备份文件
   */
  async downloadBackup(backupId: string): Promise<ApiResponse<Blob>> {
    return this.getBlob(`/backup/${backupId}/download`);
  }

  /**
   * 恢复数据备份
   */
  async restoreBackup(
    backupId: string,
    options?: {
      confirm_overwrite?: boolean;
      restore_files?: boolean;
    }
  ): Promise<ApiResponse<AsyncTask>> {
    return this.post<AsyncTask>(`/backup/${backupId}/restore`, options);
  }

  /**
   * 删除备份
   */
  async deleteBackup(backupId: string): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/backup/${backupId}`);
  }

  // ==================== 日志管理 ====================

  /**
   * 获取系统日志
   */
  async getSystemLogs(params?: {
    level?: 'debug' | 'info' | 'warning' | 'error';
    start_time?: string;
    end_time?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<{
    logs: Array<{
      timestamp: string;
      level: string;
      message: string;
      module?: string;
      request_id?: string;
      details?: any;
    }>;
    total: number;
  }>> {
    return this.get('/logs', params);
  }

  /**
   * 下载日志文件
   */
  async downloadLogFile(date?: string): Promise<ApiResponse<Blob>> {
    const params = date ? { date } : {};
    return this.getBlob('/logs/download', params);
  }

  /**
   * 清理旧日志
   */
  async cleanupLogs(olderThan?: string): Promise<ApiResponse<{
    deleted_files: number;
    freed_space: number;
    message: string;
  }>> {
    const params = olderThan ? { older_than: olderThan } : {};
    return this.post('/logs/cleanup', params);
  }

  // ==================== 性能监控 ====================

  /**
   * 获取系统性能指标
   */
  async getSystemMetrics(): Promise<ApiResponse<{
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    active_connections: number;
    response_times: {
      avg: number;
      p95: number;
      p99: number;
    };
    request_counts: {
      total: number;
      successful: number;
      errors: number;
    };
    database: {
      connections: number;
      queries_per_second: number;
      slow_queries: number;
    };
  }>> {
    return this.get('/metrics');
  }

  /**
   * 获取历史性能数据
   */
  async getHistoricalMetrics(params: {
    start_time: string;
    end_time: string;
    interval?: '1m' | '5m' | '15m' | '1h' | '1d';
    metrics?: string[];
  }): Promise<ApiResponse<{
    timestamps: string[];
    data: Record<string, number[]>;
  }>> {
    return this.get('/metrics/history', params);
  }

  // ==================== 维护工具 ====================

  /**
   * 数据库优化
   */
  async optimizeDatabase(): Promise<ApiResponse<AsyncTask>> {
    return this.post<AsyncTask>('/maintenance/optimize-db');
  }

  /**
   * 重建搜索索引
   */
  async rebuildSearchIndex(): Promise<ApiResponse<AsyncTask>> {
    return this.post<AsyncTask>('/maintenance/rebuild-index');
  }

  /**
   * 清理临时文件
   */
  async cleanupTempFiles(): Promise<ApiResponse<{
    deleted_files: number;
    freed_space: number;
    message: string;
  }>> {
    return this.post('/maintenance/cleanup-temp');
  }

  /**
   * 验证数据完整性
   */
  async validateDataIntegrity(): Promise<ApiResponse<AsyncTask>> {
    return this.post<AsyncTask>('/maintenance/validate-data');
  }

  // ==================== 通知和警报 ====================

  /**
   * 获取系统通知
   */
  async getNotifications(params?: {
    type?: 'info' | 'warning' | 'error' | 'success';
    read?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<{
    notifications: Array<{
      id: string;
      type: string;
      title: string;
      message: string;
      read: boolean;
      created_at: string;
      data?: any;
    }>;
    unread_count: number;
    total: number;
  }>> {
    return this.get('/notifications', params);
  }

  /**
   * 标记通知为已读
   */
  async markNotificationRead(notificationId: string): Promise<ApiResponse<{ message: string }>> {
    return this.patch(`/notifications/${notificationId}/read`);
  }

  /**
   * 批量标记通知为已读
   */
  async markAllNotificationsRead(): Promise<ApiResponse<{ 
    marked_count: number;
    message: string; 
  }>> {
    return this.post('/notifications/mark-all-read');
  }

  /**
   * 删除通知
   */
  async deleteNotification(notificationId: string): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/notifications/${notificationId}`);
  }

  // ==================== 用户会话管理 ====================

  /**
   * 获取活跃会话列表
   */
  async getActiveSessions(): Promise<ApiResponse<Array<{
    session_id: string;
    user_id?: string;
    ip_address: string;
    user_agent: string;
    created_at: string;
    last_activity: string;
    current: boolean;
  }>>> {
    return this.get('/sessions');
  }

  /**
   * 终止会话
   */
  async terminateSession(sessionId: string): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/sessions/${sessionId}`);
  }

  /**
   * 终止所有其他会话
   */
  async terminateOtherSessions(): Promise<ApiResponse<{ 
    terminated_count: number;
    message: string; 
  }>> {
    return this.post('/sessions/terminate-others');
  }
}

// 导出类和单例实例
export { SystemService };

// 创建单例实例
const systemService = new SystemService();
export { systemService };
export default systemService;