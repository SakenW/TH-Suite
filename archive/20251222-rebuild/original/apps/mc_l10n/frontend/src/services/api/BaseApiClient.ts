/**
 * 基础 API 客户端
 * 提供统一的 HTTP 请求、错误处理、重试机制
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ApiResponse, ApiError, RequestConfig } from './types'

export class BaseApiClient {
  private client: AxiosInstance
  private baseURL: string
  private defaultTimeout: number = 30000
  private defaultRetries: number = 3

  constructor(baseURL: string = 'http://localhost:18000') {
    this.baseURL = baseURL
    this.client = this.createAxiosInstance()
    this.setupInterceptors()
  }

  private createAxiosInstance(): AxiosInstance {
    return axios.create({
      baseURL: this.baseURL,
      timeout: this.defaultTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    })
  }

  private setupInterceptors() {
    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        // 添加请求时间戳
        config.metadata = { startTime: new Date() }
        console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        console.error('❌ Request Error:', error)
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => {
        const duration = new Date().getTime() - response.config.metadata?.startTime?.getTime() || 0
        console.log(`✅ API Response: ${response.status} ${response.config.url} (${duration}ms)`)
        return response
      },
      (error) => {
        const duration = new Date().getTime() - error.config?.metadata?.startTime?.getTime() || 0
        console.error(`❌ API Error: ${error.response?.status || 'NETWORK'} ${error.config?.url} (${duration}ms)`)
        return Promise.reject(this.transformError(error))
      }
    )
  }

  private transformError(error: any): ApiError {
    if (error.response) {
      // 服务器响应错误
      return {
        code: `HTTP_${error.response.status}`,
        message: error.response.data?.message || error.response.statusText || '服务器错误',
        details: {
          status: error.response.status,
          data: error.response.data,
          url: error.config?.url,
        },
      }
    } else if (error.request) {
      // 网络错误
      return {
        code: 'NETWORK_ERROR',
        message: '网络连接错误，请检查网络设置',
        details: {
          url: error.config?.url,
          timeout: error.code === 'ECONNABORTED',
        },
      }
    } else {
      // 其他错误
      return {
        code: 'UNKNOWN_ERROR',
        message: error.message || '未知错误',
        details: { originalError: error },
      }
    }
  }

  private async retryRequest<T>(
    requestFn: () => Promise<AxiosResponse<T>>,
    retries: number = this.defaultRetries
  ): Promise<AxiosResponse<T>> {
    let lastError: any

    for (let i = 0; i <= retries; i++) {
      try {
        return await requestFn()
      } catch (error: any) {
        lastError = error
        
        // 如果是客户端错误（4xx）或最后一次重试，直接抛出错误
        if (error.code?.startsWith('HTTP_4') || i === retries) {
          throw error
        }

        // 指数退避延迟
        const delay = Math.min(1000 * Math.pow(2, i), 10000)
        console.warn(`🔄 Retrying request (${i + 1}/${retries + 1}) after ${delay}ms...`)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }

    throw lastError
  }

  // GET 请求
  async get<T>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.retryRequest(
      () => this.client.get<ApiResponse<T>>(url, {
        timeout: config?.timeout || this.defaultTimeout,
        signal: config?.signal,
      }),
      config?.retries
    )
    return response.data
  }

  // POST 请求
  async post<T>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.retryRequest(
      () => this.client.post<ApiResponse<T>>(url, data, {
        timeout: config?.timeout || this.defaultTimeout,
        signal: config?.signal,
      }),
      config?.retries
    )
    return response.data
  }

  // PUT 请求
  async put<T>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.retryRequest(
      () => this.client.put<ApiResponse<T>>(url, data, {
        timeout: config?.timeout || this.defaultTimeout,
        signal: config?.signal,
      }),
      config?.retries
    )
    return response.data
  }

  // DELETE 请求
  async delete<T>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.retryRequest(
      () => this.client.delete<ApiResponse<T>>(url, {
        timeout: config?.timeout || this.defaultTimeout,
        signal: config?.signal,
      }),
      config?.retries
    )
    return response.data
  }

  // 流式请求（用于下载文件等）
  async stream(url: string, config?: AxiosRequestConfig): Promise<ReadableStream> {
    const response = await this.client.get(url, {
      ...config,
      responseType: 'stream',
    })
    return response.data
  }

  // 上传文件
  async upload<T>(
    url: string, 
    file: File | FormData, 
    config?: RequestConfig & { onProgress?: (progress: number) => void }
  ): Promise<ApiResponse<T>> {
    const formData = file instanceof FormData ? file : new FormData()
    if (file instanceof File) {
      formData.append('file', file)
    }

    const response = await this.client.post<ApiResponse<T>>(url, formData, {
      timeout: config?.timeout || 60000, // 上传超时时间更长
      signal: config?.signal,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && config?.onProgress) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100
          config.onProgress(Math.round(progress))
        }
      },
    })
    return response.data
  }

  // 健康检查
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.get('/health', { timeout: 5000, retries: 0 })
      return response.status === 'healthy'
    } catch {
      return false
    }
  }

  // 设置基础 URL
  setBaseURL(baseURL: string) {
    this.baseURL = baseURL
    this.client.defaults.baseURL = baseURL
  }

  // 设置默认超时时间
  setTimeout(timeout: number) {
    this.defaultTimeout = timeout
    this.client.defaults.timeout = timeout
  }

  // 设置认证头
  setAuthToken(token: string) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }

  // 清除认证头
  clearAuthToken() {
    delete this.client.defaults.headers.common['Authorization']
  }

  // 获取客户端实例（用于高级用法）
  getClient(): AxiosInstance {
    return this.client
  }
}

// 创建全局 API 客户端实例
export const apiClient = new BaseApiClient()

// 导出类型
export type { ApiResponse, ApiError, RequestConfig }