/**
 * 项目服务 - 重构版本
 * 参考后端架构，使用统一的服务接口和错误处理
 */

import { BaseApiService } from '../baseApiService';
import { ServiceResult } from '../container/types';
import { 
  Project, 
  ProjectCreateRequest, 
  ProjectUpdateRequest, 
  ProjectListOptions, 
  ProjectStatistics,
  ProjectServiceInterface
} from './types';

export class ProjectService implements ProjectServiceInterface {
  constructor(private apiClient: BaseApiService) {}

  /**
   * 创建新项目
   */
  async create(request: ProjectCreateRequest): Promise<ServiceResult<{ project_id: string }>> {
    try {
      const response = await this.apiClient.post('/projects', request);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_CREATE_FAILED',
            message: response.error?.message || '创建项目失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error: any) {
      return this.handleError('PROJECT_CREATE_ERROR', '创建项目时发生错误', error);
    }
  }

  /**
   * 更新项目
   */
  async update(projectId: string, request: ProjectUpdateRequest): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.put(`/projects/${projectId}`, request);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_UPDATE_FAILED',
            message: response.error?.message || '更新项目失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: true
      };
    } catch (error: any) {
      return this.handleError('PROJECT_UPDATE_ERROR', '更新项目时发生错误', error);
    }
  }

  /**
   * 删除项目
   */
  async delete(projectId: string, force: boolean = false): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.apiClient.delete(`/projects/${projectId}?force=${force}`);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_DELETE_FAILED',
            message: response.error?.message || '删除项目失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: true
      };
    } catch (error: any) {
      return this.handleError('PROJECT_DELETE_ERROR', '删除项目时发生错误', error);
    }
  }

  /**
   * 归档项目
   */
  async archive(projectId: string, reason?: string): Promise<ServiceResult<boolean>> {
    try {
      const params = reason ? { archive_reason: reason } : {};
      const response = await this.apiClient.post(`/projects/${projectId}/archive`, params);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_ARCHIVE_FAILED',
            message: response.error?.message || '归档项目失败',
            details: response.error
          }
        };
      }

      return {
        success: true,
        data: true
      };
    } catch (error: any) {
      return this.handleError('PROJECT_ARCHIVE_ERROR', '归档项目时发生错误', error);
    }
  }

  /**
   * 根据 ID 获取项目
   */
  async getById(projectId: string, includeStatistics: boolean = true): Promise<ServiceResult<Project>> {
    try {
      const params = { include_statistics: includeStatistics };
      const response = await this.apiClient.get(`/projects/${projectId}`, params);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_NOT_FOUND',
            message: response.error?.message || '项目不存在',
            details: response.error
          }
        };
      }

      // 转换日期格式
      const project = this.transformProject(response.data);

      return {
        success: true,
        data: project
      };
    } catch (error: any) {
      return this.handleError('PROJECT_GET_ERROR', '获取项目时发生错误', error);
    }
  }

  /**
   * 获取项目列表
   */
  async list(options: ProjectListOptions = {}): Promise<ServiceResult<{ projects: Project[]; pagination: any }>> {
    try {
      const params = this.buildListParams(options);
      const response = await this.apiClient.get('/projects', params);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_LIST_FAILED',
            message: response.error?.message || '获取项目列表失败',
            details: response.error
          }
        };
      }

      // 转换项目数据
      const projects = response.data.projects.map((p: any) => this.transformProject(p));

      return {
        success: true,
        data: {
          projects,
          pagination: response.data.pagination
        }
      };
    } catch (error: any) {
      return this.handleError('PROJECT_LIST_ERROR', '获取项目列表时发生错误', error);
    }
  }

  /**
   * 搜索项目
   */
  async search(query: string, options: ProjectListOptions = {}): Promise<ServiceResult<{ projects: Project[]; pagination: any }>> {
    try {
      const params = {
        search_text: query,
        search_fields: ['name', 'description'],
        ...this.buildListParams(options)
      };
      
      const response = await this.apiClient.get('/projects/search', params);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_SEARCH_FAILED',
            message: response.error?.message || '搜索项目失败',
            details: response.error
          }
        };
      }

      // 转换项目数据
      const projects = response.data.projects.map((p: any) => this.transformProject(p));

      return {
        success: true,
        data: {
          projects,
          pagination: response.data.pagination
        }
      };
    } catch (error: any) {
      return this.handleError('PROJECT_SEARCH_ERROR', '搜索项目时发生错误', error);
    }
  }

  /**
   * 获取项目统计信息
   */
  async getStatistics(projectId: string): Promise<ServiceResult<ProjectStatistics>> {
    try {
      const response = await this.apiClient.get(`/projects/${projectId}/statistics`);
      
      if (!response.success) {
        return {
          success: false,
          error: {
            code: 'PROJECT_STATISTICS_FAILED',
            message: response.error?.message || '获取项目统计失败',
            details: response.error
          }
        };
      }

      // 转换统计数据
      const statistics: ProjectStatistics = {
        ...response.data,
        generated_at: new Date(response.data.generated_at)
      };

      return {
        success: true,
        data: statistics
      };
    } catch (error: any) {
      return this.handleError('PROJECT_STATISTICS_ERROR', '获取项目统计时发生错误', error);
    }
  }

  // === 私有辅助方法 ===

  /**
   * 转换项目数据格式
   */
  private transformProject(data: any): Project {
    return {
      ...data,
      created_at: new Date(data.created_at),
      updated_at: data.updated_at ? new Date(data.updated_at) : undefined
    };
  }

  /**
   * 构建列表查询参数
   */
  private buildListParams(options: ProjectListOptions) {
    const params: any = {};
    
    // 分页参数
    if (options.page !== undefined) params.page = options.page;
    if (options.page_size !== undefined) params.page_size = options.page_size;
    
    // 排序参数
    if (options.sort_field) params.sort_field = options.sort_field;
    if (options.sort_direction) params.sort_direction = options.sort_direction;
    
    // 搜索参数
    if (options.search_text) params.search_text = options.search_text;
    
    // 过滤参数
    if (options.mc_version_filter) params.mc_version_filter = options.mc_version_filter;
    if (options.language_filter) params.language_filter = options.language_filter;
    if (options.include_archived !== undefined) params.include_archived = options.include_archived;
    if (options.include_statistics !== undefined) params.include_statistics = options.include_statistics;
    
    return params;
  }

  /**
   * 统一错误处理
   */
  private handleError(code: string, message: string, error: any): ServiceResult<never> {
    console.error(`ProjectService: ${message}`, error);
    
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