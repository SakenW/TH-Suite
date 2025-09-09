/**
 * API 配置
 * 集中管理所有 API 相关的配置，避免硬编码
 */

// API 基础配置
export const API_CONFIG = {
  // 后端 API 地址
  BASE_URL: 'http://localhost:18000',

  // API 版本
  API_VERSION: 'v1',

  // 超时设置（毫秒）
  TIMEOUT: 30000,

  // 重试次数
  MAX_RETRIES: 3,

  // 轮询间隔（毫秒）
  POLLING_INTERVAL: 500,

  // 健康检查间隔（毫秒）
  HEALTH_CHECK_INTERVAL: 5000,
} as const

// API 端点
export const API_ENDPOINTS = {
  // 健康检查
  HEALTH: '/health',

  // 扫描相关
  SCAN_PROJECT: '/api/v1/scan-project',
  SCAN_STATUS: (scanId: string) => `/api/v1/scan-status/${scanId}`,
  SCAN_RESULT: (scanId: string) => `/api/v1/scan-result/${scanId}`,
  ACTIVE_SCANS: '/api/v1/scans/active',

  // 项目相关
  PROJECTS: '/api/v1/projects',
  PROJECT_DETAIL: (id: string) => `/api/v1/projects/${id}`,

  // MOD 相关
  MODS: '/api/v1/mods',
  MOD_DETAIL: (id: string) => `/api/v1/mods/${id}`,
} as const

// 构建完整 URL
export function buildApiUrl(endpoint: string): string {
  return `${API_CONFIG.BASE_URL}${endpoint}`
}

// 导出默认 API 基础 URL（向后兼容）
export const API_BASE_URL = API_CONFIG.BASE_URL
