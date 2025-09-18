/**
 * 项目管理 API 服务
 * 处理项目的CRUD操作、统计信息、配置管理等
 * 集成v2.1项目管理功能和真实数据操作
 */

import { BaseApiClient } from './BaseApiClient'
import { 
  Project,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectStatistics,
  ApiResponse,
  RequestConfig,
  PaginatedResponse,
  PaginationParams,
  SortParams,
  FilterParams
} from './types'
import { ServiceResult } from '../container/types'

export interface ProjectSearchParams extends PaginationParams, SortParams, FilterParams {
  mc_version?: string
  target_language?: string
  include_archived?: boolean
  include_statistics?: boolean
  created_after?: string
  created_before?: string
}

export class ProjectApiService {
  private client: BaseApiClient

  constructor(client?: BaseApiClient) {
    this.client = client || new BaseApiClient()
  }

  // ============================================================
  // 项目CRUD操作
  // ============================================================

  /**
   * 创建新项目
   */
  async createProject(
    request: ProjectCreateRequest,
    config?: RequestConfig
  ): Promise<ServiceResult<Project>> {
    try {
      const response = await this.client.post<Project>(
        '/api/v1/projects',
        request,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_CREATE_FAILED',
            message: response.message || '创建项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '创建项目请求失败'
        }
      }
    }
  }

  /**
   * 获取项目详情
   */
  async getProject(
    projectId: string,
    includeStatistics: boolean = false,
    config?: RequestConfig
  ): Promise<ServiceResult<Project>> {
    try {
      const params = includeStatistics ? { include_statistics: true } : undefined
      const response = await this.client.get<Project>(
        `/api/v1/projects/${projectId}`,
        { ...config, params }
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_NOT_FOUND',
            message: response.message || '项目未找到'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取项目请求失败'
        }
      }
    }
  }

  /**
   * 更新项目
   */
  async updateProject(
    projectId: string,
    request: ProjectUpdateRequest,
    config?: RequestConfig
  ): Promise<ServiceResult<Project>> {
    try {
      const response = await this.client.put<Project>(
        `/api/v1/projects/${projectId}`,
        request,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_UPDATE_FAILED',
            message: response.message || '更新项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '更新项目请求失败'
        }
      }
    }
  }

  /**
   * 删除项目
   */
  async deleteProject(
    projectId: string,
    force: boolean = false,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const params = force ? { force: true } : undefined
      const response = await this.client.delete<{ deleted: boolean }>(
        `/api/v1/projects/${projectId}`,
        { ...config, params }
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.deleted
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_DELETE_FAILED',
            message: response.message || '删除项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '删除项目请求失败'
        }
      }
    }
  }

  /**
   * 归档项目
   */
  async archiveProject(
    projectId: string,
    reason?: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.post<{ archived: boolean }>(
        `/api/v1/projects/${projectId}/archive`,
        { reason },
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.archived
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_ARCHIVE_FAILED',
            message: response.message || '归档项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '归档项目请求失败'
        }
      }
    }
  }

  /**
   * 恢复归档项目
   */
  async unarchiveProject(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.post<{ unarchived: boolean }>(
        `/api/v1/projects/${projectId}/unarchive`,
        {},
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.unarchived
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_UNARCHIVE_FAILED',
            message: response.message || '恢复项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '恢复项目请求失败'
        }
      }
    }
  }

  // ============================================================
  // 项目查询和搜索
  // ============================================================

  /**
   * 获取项目列表
   */
  async getProjects(
    params?: ProjectSearchParams,
    config?: RequestConfig
  ): Promise<ServiceResult<PaginatedResponse<Project>>> {
    try {
      const response = await this.client.get<PaginatedResponse<Project>>(
        '/api/v1/projects',
        { ...config, params }
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECTS_FETCH_FAILED',
            message: response.message || '获取项目列表失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取项目列表请求失败'
        }
      }
    }
  }

  /**
   * 搜索项目
   */
  async searchProjects(
    query: string,
    params?: ProjectSearchParams,
    config?: RequestConfig
  ): Promise<ServiceResult<PaginatedResponse<Project>>> {
    try {
      const searchParams = {
        ...params,
        search: query
      }

      const response = await this.client.get<PaginatedResponse<Project>>(
        '/api/v1/projects/search',
        { ...config, params: searchParams }
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_SEARCH_FAILED',
            message: response.message || '搜索项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '搜索项目请求失败'
        }
      }
    }
  }

  /**
   * 获取最近使用的项目
   */
  async getRecentProjects(
    limit: number = 10,
    config?: RequestConfig
  ): Promise<ServiceResult<Project[]>> {
    try {
      const params = { limit }
      const response = await this.client.get<Project[]>(
        '/api/v1/projects/recent',
        { ...config, params }
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'RECENT_PROJECTS_FAILED',
            message: response.message || '获取最近项目失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取最近项目请求失败'
        }
      }
    }
  }

  // ============================================================
  // 项目统计和分析
  // ============================================================

  /**
   * 获取项目统计信息
   */
  async getProjectStatistics(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<ProjectStatistics>> {
    try {
      const response = await this.client.get<ProjectStatistics>(
        `/api/v1/projects/${projectId}/statistics`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'STATISTICS_FETCH_FAILED',
            message: response.message || '获取项目统计失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取项目统计请求失败'
        }
      }
    }
  }

  /**
   * 刷新项目统计信息
   */
  async refreshProjectStatistics(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<ProjectStatistics>> {
    try {
      const response = await this.client.post<ProjectStatistics>(
        `/api/v1/projects/${projectId}/statistics/refresh`,
        {},
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'STATISTICS_REFRESH_FAILED',
            message: response.message || '刷新项目统计失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '刷新项目统计请求失败'
        }
      }
    }
  }

  /**
   * 获取全局项目统计
   */
  async getGlobalStatistics(
    config?: RequestConfig
  ): Promise<ServiceResult<{
    total_projects: number
    active_projects: number
    archived_projects: number
    total_packs: number
    total_mods: number
    total_content_instances: number
    mc_version_distribution: Record<string, number>
    language_distribution: Record<string, number>
    project_trends: Array<{
      date: string
      projects_created: number
      projects_archived: number
    }>
  }>> {
    try {
      const response = await this.client.get(
        '/api/v1/projects/statistics/global',
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'GLOBAL_STATISTICS_FAILED',
            message: response.message || '获取全局统计失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取全局统计请求失败'
        }
      }
    }
  }

  // ============================================================
  // 项目配置和设置
  // ============================================================

  /**
   * 获取项目配置
   */
  async getProjectConfig(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    scan_settings: {
      auto_scan: boolean
      scan_interval_hours: number
      include_subdirectories: boolean
      exclude_patterns: string[]
    }
    sync_settings: {
      auto_sync: boolean
      conflict_resolution: 'local_wins' | 'remote_wins' | 'manual'
      batch_size: number
    }
    export_settings: {
      default_format: string
      include_metadata: boolean
      compress_output: boolean
    }
    notification_settings: {
      scan_completion: boolean
      sync_completion: boolean
      error_alerts: boolean
    }
  }>> {
    try {
      const response = await this.client.get(
        `/api/v1/projects/${projectId}/config`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_CONFIG_FAILED',
            message: response.message || '获取项目配置失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '获取项目配置请求失败'
        }
      }
    }
  }

  /**
   * 更新项目配置
   */
  async updateProjectConfig(
    projectId: string,
    configUpdate: Record<string, any>,
    config?: RequestConfig
  ): Promise<ServiceResult<boolean>> {
    try {
      const response = await this.client.put<{ updated: boolean }>(
        `/api/v1/projects/${projectId}/config`,
        configUpdate,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data.updated
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_CONFIG_UPDATE_FAILED',
            message: response.message || '更新项目配置失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '更新项目配置请求失败'
        }
      }
    }
  }

  // ============================================================
  // 项目验证和检查
  // ============================================================

  /**
   * 验证项目路径
   */
  async validateProjectPaths(
    sourcePath: string,
    outputPath: string,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    source_valid: boolean
    output_valid: boolean
    source_warnings: string[]
    output_warnings: string[]
    suggestions: {
      recommended_source_path?: string
      recommended_output_path?: string
    }
  }>> {
    try {
      const response = await this.client.post(
        '/api/v1/projects/validate-paths',
        {
          source_path: sourcePath,
          output_path: outputPath
        },
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PATH_VALIDATION_FAILED',
            message: response.message || '路径验证失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '路径验证请求失败'
        }
      }
    }
  }

  /**
   * 检查项目健康状态
   */
  async checkProjectHealth(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    overall_health: 'healthy' | 'warning' | 'error'
    checks: Array<{
      check_name: string
      status: 'pass' | 'warning' | 'fail'
      message: string
      suggestion?: string
    }>
    last_check: string
  }>> {
    try {
      const response = await this.client.get(
        `/api/v1/projects/${projectId}/health`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_HEALTH_CHECK_FAILED',
            message: response.message || '项目健康检查失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '项目健康检查请求失败'
        }
      }
    }
  }

  // ============================================================
  // 实用方法
  // ============================================================

  /**
   * 导出项目配置
   */
  async exportProjectConfig(
    projectId: string,
    config?: RequestConfig
  ): Promise<ServiceResult<{
    export_data: Record<string, any>
    export_format: 'json' | 'yaml'
    created_at: string
  }>> {
    try {
      const response = await this.client.get(
        `/api/v1/projects/${projectId}/export`,
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_EXPORT_FAILED',
            message: response.message || '导出项目配置失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '导出项目配置请求失败'
        }
      }
    }
  }

  /**
   * 导入项目配置
   */
  async importProjectConfig(
    configData: Record<string, any>,
    options?: {
      overwrite_existing?: boolean
      validate_before_import?: boolean
      dry_run?: boolean
    },
    config?: RequestConfig
  ): Promise<ServiceResult<{
    imported_project_id?: string
    validation_results?: Array<{
      field: string
      valid: boolean
      message: string
    }>
    preview?: Project
  }>> {
    try {
      const response = await this.client.post(
        '/api/v1/projects/import',
        {
          config_data: configData,
          options
        },
        config
      )

      if (response.success && response.data) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: {
            code: 'PROJECT_IMPORT_FAILED',
            message: response.message || '导入项目配置失败'
          }
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: {
          code: error.code || 'NETWORK_ERROR',
          message: error.message || '导入项目配置请求失败'
        }
      }
    }
  }
}

// 创建全局实例
export const projectApiService = new ProjectApiService()

// 导出类型
export type {
  Project,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectStatistics,
  ProjectSearchParams
}