/**
 * 服务容器类型定义 - 最优化版本
 * 简化的依赖注入系统
 */

export interface ServiceDefinition<T = any> {
  factory: (...deps: any[]) => T | Promise<T>;
  singleton?: boolean;
  dependencies?: string[];
}

export interface ServiceRegistry {
  apiClient: ServiceDefinition;
  projectService: ServiceDefinition;
  scanService: ServiceDefinition;
}

export interface ServiceResult<T = any> {
  success: boolean;
  data?: T;
  error?: ServiceError;
  metadata?: Record<string, any>;
}

export interface ServiceError {
  code: string;
  message: string;
  details?: any;
  timestamp?: Date;
}