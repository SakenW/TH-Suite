/**
 * 错误处理工具
 * 提供统一的错误处理和重试机制
 */

import { QueryClient } from '@tanstack/react-query'
import { message, notification } from 'antd'
import { ServiceResult } from '../services/api/types'

// ============================================================
// 错误类型定义
// ============================================================

export interface AppError {
  code: string
  message: string
  details?: any
  timestamp?: string
  source?: 'api' | 'network' | 'validation' | 'unknown'
}

export interface RetryConfig {
  maxRetries: number
  retryDelay: (attempt: number) => number
  shouldRetry: (error: AppError) => boolean
}

// ============================================================
// 错误分类和处理
// ============================================================

/**
 * 错误分类器
 */
export const classifyError = (error: any): AppError => {
  const timestamp = new Date().toISOString()
  
  // API错误
  if (error?.response) {
    const status = error.response.status
    const data = error.response.data
    
    return {
      code: data?.code || `HTTP_${status}`,
      message: data?.message || error.message || '服务器错误',
      details: data?.details || error.response.data,
      timestamp,
      source: 'api',
    }
  }
  
  // 网络错误
  if (error?.request || error?.code === 'NETWORK_ERROR') {
    return {
      code: 'NETWORK_ERROR',
      message: '网络连接错误，请检查网络设置',
      details: error.message,
      timestamp,
      source: 'network',
    }
  }
  
  // 验证错误
  if (error?.code === 'VALIDATION_ERROR') {
    return {
      code: 'VALIDATION_ERROR',
      message: error.message || '数据验证失败',
      details: error.details,
      timestamp,
      source: 'validation',
    }
  }
  
  // 未知错误
  return {
    code: error?.code || 'UNKNOWN_ERROR',
    message: error?.message || '发生了未知错误',
    details: error,
    timestamp,
    source: 'unknown',
  }
}

/**
 * 错误严重级别判断
 */
export const getErrorSeverity = (error: AppError): 'low' | 'medium' | 'high' | 'critical' => {
  // 网络错误 - 中等严重
  if (error.source === 'network') {
    return 'medium'
  }
  
  // API错误 - 根据状态码判断
  if (error.source === 'api') {
    if (error.code.includes('400') || error.code.includes('422')) {
      return 'low' // 客户端错误
    }
    if (error.code.includes('401') || error.code.includes('403')) {
      return 'high' // 认证错误
    }
    if (error.code.includes('500')) {
      return 'critical' // 服务器错误
    }
    return 'medium'
  }
  
  // 验证错误 - 低严重
  if (error.source === 'validation') {
    return 'low'
  }
  
  // 未知错误 - 高严重
  return 'high'
}

/**
 * 错误恢复建议
 */
export const getRecoverySuggestion = (error: AppError): string => {
  switch (error.source) {
    case 'network':
      return '请检查网络连接后重试'
    case 'api':
      if (error.code.includes('401')) {
        return '请重新登录'
      }
      if (error.code.includes('403')) {
        return '您没有执行此操作的权限'
      }
      if (error.code.includes('404')) {
        return '请求的资源不存在'
      }
      if (error.code.includes('500')) {
        return '服务器暂时不可用，请稍后重试'
      }
      return '请稍后重试或联系技术支持'
    case 'validation':
      return '请检查输入的数据是否正确'
    default:
      return '请刷新页面后重试'
  }
}

// ============================================================
// 错误处理器
// ============================================================

/**
 * 全局错误处理器
 */
export class ErrorHandler {
  private static instance: ErrorHandler
  private queryClient?: QueryClient
  private errorHistory: AppError[] = []
  private maxHistorySize = 100
  
  private constructor() {}
  
  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler()
    }
    return ErrorHandler.instance
  }
  
  setQueryClient(queryClient: QueryClient) {
    this.queryClient = queryClient
  }
  
  /**
   * 处理错误
   */
  handleError(error: any, context?: string): AppError {
    const appError = classifyError(error)
    const severity = getErrorSeverity(appError)
    
    // 记录错误历史
    this.addToHistory(appError)
    
    // 控制台输出
    console.error(`[ErrorHandler] ${context || 'Unknown context'}:`, appError)
    
    // 根据严重级别显示不同的提示
    this.showErrorNotification(appError, severity, context)
    
    // 记录到错误报告服务（可选）
    this.reportError(appError, context)
    
    return appError
  }
  
  /**
   * 处理ServiceResult错误
   */
  handleServiceResult<T>(result: ServiceResult<T>, context?: string): T | null {
    if (result.success) {
      return result.data || null
    }
    
    const error = result.error || {
      code: 'UNKNOWN_ERROR',
      message: '未知错误'
    }
    
    this.handleError(error, context)
    return null
  }
  
  /**
   * 显示错误通知
   */
  private showErrorNotification(error: AppError, severity: string, context?: string) {
    const suggestion = getRecoverySuggestion(error)
    
    switch (severity) {
      case 'low':
        message.warning(error.message)
        break
        
      case 'medium':
        notification.warning({
          message: context || '操作失败',
          description: error.message,
          duration: 5,
        })
        break
        
      case 'high':
        notification.error({
          message: context || '错误',
          description: `${error.message}\n建议: ${suggestion}`,
          duration: 8,
        })
        break
        
      case 'critical':
        notification.error({
          message: '严重错误',
          description: `${error.message}\n错误代码: ${error.code}\n建议: ${suggestion}`,
          duration: 0, // 不自动关闭
        })
        break
    }
  }
  
  /**
   * 记录错误历史
   */
  private addToHistory(error: AppError) {
    this.errorHistory.unshift(error)
    
    // 限制历史记录大小
    if (this.errorHistory.length > this.maxHistorySize) {
      this.errorHistory = this.errorHistory.slice(0, this.maxHistorySize)
    }
  }
  
  /**
   * 获取错误历史
   */
  getErrorHistory(): AppError[] {
    return [...this.errorHistory]
  }
  
  /**
   * 清除错误历史
   */
  clearErrorHistory() {
    this.errorHistory = []
  }
  
  /**
   * 上报错误到服务器（可选）
   */
  private reportError(error: AppError, context?: string) {
    // 实现错误上报逻辑
    if (import.meta.env.PROD) {
      // 发送到错误监控服务
      console.log('Reporting error to monitoring service:', {
        error,
        context,
        userAgent: navigator.userAgent,
        url: window.location.href,
      })
    }
  }
  
  /**
   * 重试操作
   */
  async retryOperation<T>(
    operation: () => Promise<T>,
    config: Partial<RetryConfig> = {}
  ): Promise<T> {
    const defaultConfig: RetryConfig = {
      maxRetries: 3,
      retryDelay: (attempt) => Math.min(1000 * Math.pow(2, attempt), 10000),
      shouldRetry: (error) => error.source === 'network' || error.source === 'api',
    }
    
    const retryConfig = { ...defaultConfig, ...config }
    let lastError: AppError
    
    for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
      try {
        return await operation()
      } catch (error) {
        lastError = classifyError(error)
        
        // 如果是最后一次尝试或不应该重试，抛出错误
        if (attempt === retryConfig.maxRetries || !retryConfig.shouldRetry(lastError)) {
          throw lastError
        }
        
        // 等待重试延迟
        const delay = retryConfig.retryDelay(attempt)
        await new Promise(resolve => setTimeout(resolve, delay))
        
        console.log(`Retrying operation (attempt ${attempt + 1}/${retryConfig.maxRetries})`)
      }
    }
    
    throw lastError!
  }
}

// ============================================================
// React Query 错误处理
// ============================================================

/**
 * React Query 错误边界
 */
export const queryErrorHandler = (error: any, query: any) => {
  const errorHandler = ErrorHandler.getInstance()
  const context = `Query: ${query.queryKey.join(' / ')}`
  
  errorHandler.handleError(error, context)
}

/**
 * React Query 变更错误处理
 */
export const mutationErrorHandler = (error: any, variables: any, context: any) => {
  const errorHandler = ErrorHandler.getInstance()
  const mutationContext = context?.mutationKey || 'Unknown mutation'
  
  errorHandler.handleError(error, `Mutation: ${mutationContext}`)
}

// ============================================================
// 导出单例实例
// ============================================================

export const errorHandler = ErrorHandler.getInstance()

// ============================================================
// React Hook
// ============================================================

export const useErrorHandler = () => {
  return {
    handleError: (error: any, context?: string) => errorHandler.handleError(error, context),
    handleServiceResult: <T>(result: ServiceResult<T>, context?: string) => 
      errorHandler.handleServiceResult(result, context),
    retryOperation: <T>(operation: () => Promise<T>, config?: Partial<RetryConfig>) =>
      errorHandler.retryOperation(operation, config),
    getErrorHistory: () => errorHandler.getErrorHistory(),
    clearErrorHistory: () => errorHandler.clearErrorHistory(),
  }
}