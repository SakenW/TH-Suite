/**
 * 扫描服务 - 新增服务
 * 处理项目扫描相关的业务逻辑，统一扫描接口
 */

import { BaseApiService } from '../baseApiService';
import { ServiceResult } from '../container/types';
import { 
  ScanRequest, 
  ScanStatus, 
  ScanResult, 
  ListOptions,
  ScanServiceInterface
} from './types';

export class ScanService implements ScanServiceInterface {
  constructor(private apiClient: BaseApiService) {}

  /**
   * 开始扫描
   */
  async startScan(request: ScanRequest): Promise<ServiceResult<{ scan_id: string }>> {
    try {
      // 兼容旧的扫描 API
      const payload = {
        directory: request.directory,
        incremental: request.incremental ?? true,
        ...request.scan_options
      };

      const response = await this.apiClient.post('/scan-project', payload, { timeout: 120000 }); // 2分钟超时
      
      // 调试：打印完整响应
      console.log('🔍 ScanService: 完整API响应', JSON.stringify(response, null, 2));
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'SCAN_START_FAILED',
            message: response.error?.message || '启动扫描失败',
            details: response.error
          }
        };
      }

      // 获取扫描ID，处理两种响应格式：
      // 1. 标准格式: { success: true, data: { scan_id: "..." } }
      // 2. 扁平格式: { success: true, scan_id: "...", job_id: "..." }
      let scanId;
      
      if (response.data) {
        // 标准格式
        scanId = response.data.scan_id || response.data.job_id || response.data.task_id;
      } else {
        // 扁平格式 - 检查响应本身
        scanId = (response as any).scan_id || (response as any).job_id || (response as any).task_id;
      }
      
      if (!scanId) {
        return {
          success: false,
          error: {
            code: 'SCAN_START_NO_ID',
            message: '服务器响应中缺少扫描ID',
            details: response
          }
        };
      }

      return {
        success: true,
        data: { 
          scan_id: scanId
        }
      };
    } catch (error: any) {
      return this.handleError('SCAN_START_ERROR', '启动扫描时发生错误', error);
    }
  }

  /**
   * 获取扫描状态
   */
  async getStatus(scanId: string): Promise<ServiceResult<ScanStatus>> {
    try {
      console.log(`🔍 获取扫描状态: ${scanId}`);
      console.log(`🔍 请求URL: /scan-status/${scanId}`);
      // 为状态查询使用较短的超时时间，避免阻塞轮询
      const response = await this.apiClient.get(`/scan-status/${scanId}`, undefined, { timeout: 15000 });
      
      console.log(`🔍 扫描状态响应:`, JSON.stringify(response, null, 2));
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'SCAN_STATUS_FAILED',
            message: response.error?.message || '获取扫描状态失败',
            details: response.error
          }
        };
      }

      // 转换状态数据
      const status = this.transformScanStatus(scanId, response.data);

      return {
        success: true,
        data: status
      };
    } catch (error: any) {
      return this.handleError('SCAN_STATUS_ERROR', '获取扫描状态时发生错误', error);
    }
  }

  /**
   * 获取扫描结果
   */
  async getResults(scanId: string): Promise<ServiceResult<ScanResult>> {
    try {
      const response = await this.apiClient.get(`/scan-results/${scanId}`);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'SCAN_RESULTS_FAILED',
            message: response.error?.message || '获取扫描结果失败',
            details: response.error
          }
        };
      }

      // 转换结果数据
      const result: ScanResult = {
        scan_id: response.data.scan_id || scanId,
        mods: response.data.mods || [],
        language_files: response.data.language_files || [],
        statistics: response.data.statistics || {
          total_mods: response.data.total_mods || 0,
          total_language_files: response.data.total_language_files || 0,
          total_keys: response.data.total_keys || 0,
          scan_duration_ms: response.data.scan_duration_ms || 0
        }
      };

      return {
        success: true,
        data: result
      };
    } catch (error: any) {
      return this.handleError('SCAN_RESULTS_ERROR', '获取扫描结果时发生错误', error);
    }
  }

  /**
   * 取消扫描
   */
  async cancelScan(scanId: string): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.post(`/scan-cancel/${scanId}`);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'SCAN_CANCEL_FAILED',
            message: response.error?.message || '取消扫描失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: true
      };
    } catch (error: any) {
      return this.handleError('SCAN_CANCEL_ERROR', '取消扫描时发生错误', error);
    }
  }

  /**
   * 获取扫描历史列表
   */
  async listScans(options: ListOptions = {}): Promise<ServiceResult<{ scans: ScanStatus[]; pagination: any }>> {
    try {
      const params = this.buildListParams(options);
      const response = await this.apiClient.get('/scans', params);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'SCAN_LIST_FAILED',
            message: response.error?.message || '获取扫描列表失败',
            details: response.error
          }
        };
      }

      // 转换扫描数据
      const scans = response.data.scans?.map((s: any) => 
        this.transformScanStatus(s.scan_id, s)
      ) || [];

      return {
        success: true,
        data: {
          scans,
          pagination: response.data.pagination || { total: scans.length, page: 1, page_size: scans.length }
        }
      };
    } catch (error: any) {
      return this.handleError('SCAN_LIST_ERROR', '获取扫描列表时发生错误', error);
    }
  }

  /**
   * 轮询扫描状态直到完成
   */
  async waitForScanCompletion(
    scanId: string, 
    onProgress?: (status: ScanStatus) => void,
    options: { timeout?: number; interval?: number } = {}
  ): Promise<ServiceResult<ScanResult>> {
    const { timeout = 300000, interval = 1000 } = options; // 5分钟超时，1秒间隔
    const startTime = Date.now();
    
    console.log(`⏳ 开始轮询扫描状态: ${scanId}, 间隔: ${interval}ms`);

    while (Date.now() - startTime < timeout) {
      try {
        const statusResult = await this.getStatus(scanId);
        
        if (!statusResult.success) {
          return {
            success: false,
            error: statusResult.error
          };
        }

        const status = statusResult.data!;
        console.log(`📊 扫描进度更新:`, status);
        onProgress?.(status);

        // 检查是否完成
        if (status.status === 'completed') {
          return await this.getResults(scanId);
        }
        
        if (status.status === 'failed') {
          return {
            success: false,
            error: {
              code: 'SCAN_FAILED',
              message: status.error || '扫描失败',
              details: status
            }
          };
        }
        
        if (status.status === 'cancelled') {
          return {
            success: false,
            error: {
              code: 'SCAN_CANCELLED',
              message: '扫描已取消',
              details: status
            }
          };
        }

        // 等待下次检查
        await this.delay(interval);
        
      } catch (error) {
        return this.handleError('SCAN_POLL_ERROR', '扫描状态轮询错误', error);
      }
    }

    // 超时
    return {
      success: false,
      error: {
        code: 'SCAN_TIMEOUT',
        message: '扫描超时',
        timestamp: new Date()
      }
    };
  }

  // === 私有辅助方法 ===

  /**
   * 转换扫描状态数据
   */
  private transformScanStatus(scanId: string, data: any): ScanStatus {
    // 处理新的嵌套格式和旧的扁平格式
    const progressData = data.progress || {};
    
    // 优先使用扁平字段，如果不存在则从嵌套的progress对象中提取
    const progress = data.progress && typeof data.progress === 'object' 
      ? (progressData.percent || 0) 
      : (data.progress || 0);
    
    const processed_files = data.processed_files !== undefined 
      ? data.processed_files 
      : (progressData.processed || 0);
    
    const total_files = data.total_files !== undefined
      ? data.total_files
      : (progressData.total || 0);
    
    const current_file = data.current_file || progressData.current_item || '';
    
    return {
      scan_id: scanId,
      status: data.status || 'pending',
      progress: progress,
      total_files: total_files,
      processed_files: processed_files,
      current_file: current_file,
      total_mods: data.total_mods || data.statistics?.total_mods || 0,
      total_language_files: data.total_language_files || data.statistics?.total_language_files || 0,
      total_keys: data.total_keys || data.statistics?.total_keys || 0,
      scan_mode: data.scan_mode || '全量',
      started_at: new Date(data.started_at || Date.now()),
      completed_at: data.completed_at ? new Date(data.completed_at) : undefined,
      error: data.error || data.error_message
    };
  }

  /**
   * 构建列表查询参数
   */
  private buildListParams(options: ListOptions) {
    const params: any = {};
    
    if (options.page !== undefined) params.page = options.page;
    if (options.page_size !== undefined) params.page_size = options.page_size;
    if (options.sort_field) params.sort_field = options.sort_field;
    if (options.sort_direction) params.sort_direction = options.sort_direction;
    if (options.search_text) params.search_text = options.search_text;
    
    return params;
  }

  /**
   * 延迟工具函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 统一错误处理
   */
  private handleError(code: string, message: string, error: any): ServiceResult<never> {
    console.error(`ScanService: ${message}`, error);
    
    return {
      success: false,
      error: {
        code,
        message,
        details: error,
        timestamp: new Date()
      }
    };
  }
}