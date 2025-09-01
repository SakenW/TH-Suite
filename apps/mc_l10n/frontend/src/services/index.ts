/**
 * 服务层 - 最优化架构
 * 基于依赖注入的现代化服务管理
 */

// === 核心服务类 ===
export { BaseApiService } from './baseApiService';
import { BaseApiService } from './baseApiService';

// === 领域服务 ===
export { ProjectService } from './domain/projectService';
export { ScanService } from './domain/scanService';
import { ProjectService } from './domain/projectService';
import { ScanService } from './domain/scanService';

// === 基础设施服务 ===
export { TauriService, initializeTauri, FILE_FILTERS } from './infrastructure/tauriService';
export { SystemService } from './infrastructure/systemService';
export { FileService } from './infrastructure/fileService';

// === 服务容器 ===
export { serviceContainer } from './container/serviceContainer';
import { serviceContainer } from './container/serviceContainer';

// === 类型定义 ===
export type {
  // 容器类型
  ServiceResult, ServiceError,
  
  // 领域类型
  Project, ProjectCreateRequest, ProjectUpdateRequest, ProjectListOptions, ProjectStatistics,
  ScanRequest, ScanStatus, ScanResult,
  Mod, LanguageFile, TranslationEntry,
  PaginationParams, ListOptions,
} from './domain/types';

// === 服务初始化 ===

/**
 * 初始化所有服务
 */
function initializeServices() {
  // 基础服务
  serviceContainer.register('apiClient', {
    factory: () => new BaseApiService('http://localhost:8000/api/v1'),
    singleton: true,
  });
  
  // 领域服务  
  serviceContainer.register('projectService', {
    factory: () => {
      const apiClient = serviceContainer.resolve('apiClient');
      return new ProjectService(apiClient);
    },
    dependencies: ['apiClient'],
    singleton: true,
  });
  
  serviceContainer.register('scanService', {
    factory: () => {
      const apiClient = serviceContainer.resolve('apiClient');
      return new ScanService(apiClient);
    },
    dependencies: ['apiClient'],
    singleton: true,
  });
}

// === 服务访问器 ===

/**
 * 获取项目服务
 */
export function getProjectService(): ProjectService {
  return serviceContainer.resolve('projectService');
}

/**
 * 获取扫描服务
 */
export function getScanService(): ScanService {
  return serviceContainer.resolve('scanService');
}

// 兼容性导出（保持旧的命名）
export const useProjectService = getProjectService;
export const useScanService = getScanService;

// === 工具函数 ===

export const isTaskCompleted = (status: string): boolean => ['completed', 'failed', 'cancelled'].includes(status);
export const isTaskRunning = (status: string): boolean => ['pending', 'running', 'scanning'].includes(status);
export const isTaskSuccessful = (status: string): boolean => status === 'completed';

export const createPaginationParams = (page: number, pageSize: number = 20): PaginationParams => ({
  page: Math.max(1, page),
  page_size: Math.max(1, Math.min(100, pageSize)),
});

// 自动初始化
initializeServices();