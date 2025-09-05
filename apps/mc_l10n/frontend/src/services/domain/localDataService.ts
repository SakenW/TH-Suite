/**
 * 本地数据服务
 * 处理本地数据库统计和管理相关的业务逻辑
 */

import { BaseApiService } from '../baseApiService';
import { ServiceResult } from '../container/types';

export interface LocalDataStatistics {
  total_entries: number;
  by_project: Record<string, number>;
  by_source_type: Record<string, number>;
  mods_count?: number;
  language_files?: number;
  translation_keys?: number;
  scan_results?: {
    total_mods: number;
    total_language_files: number;
    total_translation_keys: number;
    languages: Record<string, number>;
    mod_details?: Array<{
      mod_id: string;
      mod_name: string;
      language_count: number;
      key_count: number;
    }>;
  };
}

export interface LocalEntry {
  local_id: number;
  project_id: string;
  source_type: string;
  source_file: string;
  source_locator?: string;
  source_lang_bcp47?: string;
  source_context?: any;
  source_payload?: any;
  note?: string;
  created_at: string;
  updated_at: string;
}

export interface MappingStatistics {
  total_mappings: number;
  active_mappings: number;
  pending_mappings: number;
  unmapped_entries: number;
  by_namespace?: Record<string, number>;
  by_language?: Record<string, number>;
}

export interface QueueStatistics {
  outbound_queue: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  inbound_queue: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  last_sync?: string;
  next_sync?: string;
}

export interface StorageStatistics {
  database_size: number;
  cache_size: number;
  backup_size: number;
  export_size: number;
  total_size: number;
  file_count: number;
  last_cleanup?: string;
}

export class LocalDataService {
  constructor(private apiClient: BaseApiService) {}

  /**
   * 获取本地条目统计信息
   */
  async getStatistics(): Promise<ServiceResult<LocalDataStatistics>> {
    try {
      // 先尝试新的数据库统计API
      const dbStatsResponse = await this.apiClient.get('/api/database/statistics');
      
      if (dbStatsResponse.success && dbStatsResponse.data) {
        const dbStats = dbStatsResponse.data;
        
        // 返回数据库统计
        return {
          success: true,
          data: {
            total_entries: dbStats.total_entries || 0,
            by_project: { 'minecraft': dbStats.total_entries || 0 },
            by_source_type: { 
              'mod': dbStats.total_mods || 0,
              'lang_file': dbStats.total_language_files || 0
            },
            mods_count: dbStats.total_mods || 0,
            language_files: dbStats.total_language_files || 0,
            translation_keys: dbStats.total_translation_keys || 0,
            scan_results: {
              total_mods: dbStats.total_mods || 0,
              total_language_files: dbStats.total_language_files || 0,
              total_translation_keys: dbStats.total_translation_keys || 0,
              languages: dbStats.languages || {},
              mod_details: dbStats.mod_details || []
            }
          }
        };
      }
      
      // 如果新API失败，尝试旧API
      const response = await this.apiClient.get('/api/local/entries/statistics');
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'STATS_FETCH_FAILED',
            message: response.error?.message || '获取统计信息失败',
            details: response.error
          }
        };
      }

      // 增强统计数据
      const stats = response.data as LocalDataStatistics;
      
      // 计算额外的统计信息
      const enhancedStats: LocalDataStatistics = {
        ...stats,
        mods_count: stats.by_source_type?.mod || 0,
        language_files: stats.by_source_type?.lang_file || 0,
        translation_keys: stats.total_entries || 0
      };

      return {
        success: true,
        data: enhancedStats
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'STATS_ERROR',
          message: '获取统计信息时出错',
          details: error
        }
      };
    }
  }

  /**
   * 获取映射统计信息
   */
  async getMappingStatistics(): Promise<ServiceResult<MappingStatistics>> {
    try {
      const response = await this.apiClient.get('/api/local/mapping-links/statistics');
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'MAPPING_STATS_FAILED',
            message: response.error?.message || '获取映射统计失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: response.data as MappingStatistics
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'MAPPING_STATS_ERROR',
          message: '获取映射统计时出错',
          details: error
        }
      };
    }
  }

  /**
   * 获取队列统计信息
   */
  async getQueueStatistics(): Promise<ServiceResult<QueueStatistics>> {
    try {
      const response = await this.apiClient.get('/api/local/queue-statistics');
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'QUEUE_STATS_FAILED',
            message: response.error?.message || '获取队列统计失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: response.data as QueueStatistics
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'QUEUE_STATS_ERROR',
          message: '获取队列统计时出错',
          details: error
        }
      };
    }
  }

  /**
   * 列出本地条目
   */
  async listEntries(options: {
    namespace?: string;
    lang_mc?: string;
    source_file?: string;
    limit?: number;
    offset?: number;
  }): Promise<ServiceResult<LocalEntry[]>> {
    try {
      const params = new URLSearchParams();
      if (options.namespace) params.append('namespace', options.namespace);
      if (options.lang_mc) params.append('lang_mc', options.lang_mc);
      if (options.source_file) params.append('source_file', options.source_file);
      if (options.limit) params.append('limit', options.limit.toString());
      if (options.offset) params.append('offset', options.offset.toString());

      const response = await this.apiClient.get(`/api/local/entries?${params.toString()}`);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'LIST_ENTRIES_FAILED',
            message: response.error?.message || '获取条目列表失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: response.data as LocalEntry[]
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'LIST_ENTRIES_ERROR',
          message: '获取条目列表时出错',
          details: error
        }
      };
    }
  }

  /**
   * 获取扫描结果统计
   */
  async getScanResultStatistics(): Promise<ServiceResult<any>> {
    try {
      // 尝试从最新的扫描结果获取统计信息
      const response = await this.apiClient.get('/api/scan/project/latest');
      
      if (!response.success) {
        // 如果没有最新结果，返回空统计
        return {
          success: true,
          data: {
            total_mods: 0,
            total_language_files: 0,
            total_translation_keys: 0,
            languages: {},
            mod_details: []
          }
        };
      }

      const scanResult = response.data;
      
      // 解析扫描结果以获取统计信息
      const stats = {
        total_mods: scanResult.mods?.length || 0,
        total_language_files: 0,
        total_translation_keys: 0,
        languages: {} as Record<string, number>,
        mod_details: [] as any[]
      };

      // 遍历模组获取详细统计
      if (scanResult.mods && Array.isArray(scanResult.mods)) {
        for (const mod of scanResult.mods) {
          let languageCount = 0;
          let keyCount = 0;

          if (mod.languages) {
            for (const [lang, data] of Object.entries(mod.languages)) {
              languageCount++;
              stats.total_language_files++;
              
              // 统计每种语言的文件数
              stats.languages[lang] = (stats.languages[lang] || 0) + 1;
              
              // 统计翻译键数量
              if (typeof data === 'object' && data !== null) {
                const keys = Object.keys(data as any);
                keyCount += keys.length;
                stats.total_translation_keys += keys.length;
              }
            }
          }

          stats.mod_details.push({
            mod_id: mod.mod_id || mod.id,
            mod_name: mod.name || mod.display_name || mod.mod_id,
            language_count: languageCount,
            key_count: keyCount
          });
        }
      }

      return {
        success: true,
        data: stats
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'SCAN_STATS_ERROR',
          message: '获取扫描统计时出错',
          details: error
        }
      };
    }
  }

  /**
   * 获取存储统计信息（模拟数据）
   */
  async getStorageStatistics(): Promise<ServiceResult<StorageStatistics>> {
    try {
      // TODO: 实现实际的存储统计 API
      // 目前返回模拟数据
      const mockStats: StorageStatistics = {
        database_size: 104857600, // 100MB
        cache_size: 52428800,     // 50MB
        backup_size: 209715200,    // 200MB
        export_size: 31457280,     // 30MB
        total_size: 398458880,     // ~380MB
        file_count: 1523,
        last_cleanup: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
      };

      return {
        success: true,
        data: mockStats
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'STORAGE_STATS_ERROR',
          message: '获取存储统计时出错',
          details: error
        }
      };
    }
  }

  /**
   * 清理缓存
   */
  async cleanupCache(type: 'all' | 'cache' | 'backup' | 'temp'): Promise<ServiceResult<void>> {
    try {
      const response = await this.apiClient.post('/api/local/cleanup', { type });
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'CLEANUP_FAILED',
            message: response.error?.message || '清理失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: undefined
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'CLEANUP_ERROR',
          message: '清理时出错',
          details: error
        }
      };
    }
  }

  /**
   * 导入扫描结果
   */
  async importScanResults(inventoryFile: string, projectId: string = 'minecraft'): Promise<ServiceResult<any>> {
    try {
      const response = await this.apiClient.post('/api/local/entries/import-scan', {
        inventory_file: inventoryFile,
        project_id: projectId
      });
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'IMPORT_FAILED',
            message: response.error?.message || '导入失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: 'IMPORT_ERROR',
          message: '导入时出错',
          details: error
        }
      };
    }
  }
}