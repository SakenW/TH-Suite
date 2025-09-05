/**
 * 基础 API 服务类
 * 提供通用的 HTTP 请求方法和错误处理
 */

import { ApiResponse, ApiErrorResponse } from '../types/api';

interface RequestConfig extends RequestInit {
  timeout?: number;
}

interface RequestInterceptor {
  onRequest?: (config: RequestConfig) => RequestConfig | Promise<RequestConfig>;
  onResponse?: (response: Response) => Response | Promise<Response>;
  onError?: (error: any) => void | Promise<void>;
}

export class BaseApiService {
  protected readonly baseUrl: string;
  private interceptors: RequestInterceptor[] = [];

  constructor(baseUrl: string = 'http://localhost:18000') {  // 使用18000端口，不加 /api/v1
    this.baseUrl = baseUrl;
  }

  /**
   * 添加请求拦截器
   */
  addInterceptor(interceptor: RequestInterceptor): void {
    this.interceptors.push(interceptor);
  }

  /**
   * 通用请求方法
   */
  protected async request<T = any>(
    endpoint: string,
    config: RequestConfig = {}
  ): Promise<ApiResponse<T>> {
    try {
      // 构建完整 URL
      const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
      
      // 默认配置
      const defaultConfig: RequestConfig = {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        timeout: 120000, // 120秒超时，扫描大型目录需要更长时间
      };

      // 合并配置
      let finalConfig = { ...defaultConfig, ...config };
      finalConfig.headers = { ...defaultConfig.headers, ...config.headers };

      // 执行请求拦截器
      for (const interceptor of this.interceptors) {
        if (interceptor.onRequest) {
          finalConfig = await interceptor.onRequest(finalConfig);
        }
      }

      // 设置超时控制
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), finalConfig.timeout);
      finalConfig.signal = controller.signal;

      // 发送请求
      let response = await fetch(url, finalConfig);
      clearTimeout(timeoutId);

      // 执行响应拦截器
      for (const interceptor of this.interceptors) {
        if (interceptor.onResponse) {
          response = await interceptor.onResponse(response);
        }
      }

      // 处理响应
      return await this.handleResponse<T>(response);

    } catch (error: any) {
      // 执行错误拦截器
      for (const interceptor of this.interceptors) {
        if (interceptor.onError) {
          await interceptor.onError(error);
        }
      }

      // 处理错误
      return this.handleError(error);
    }
  }

  /**
   * 处理响应
   */
  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const contentType = response.headers.get('content-type');
    
    // 处理不同内容类型
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error?.message || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      return data;
    } else if (contentType?.includes('application/octet-stream') || contentType?.includes('application/zip')) {
      // 处理文件下载
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      return {
        success: true,
        data: blob as any
      };
    } else {
      // 处理文本响应
      const text = await response.text();
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${text}`);
      }
      
      return {
        success: true,
        data: text as any
      };
    }
  }

  /**
   * 处理错误
   */
  private handleError(error: any): ApiResponse {
    // Only log non-404 errors or non-Trans-Hub 404 errors
    const isTransHub404 = error.message?.includes('404') && error.message?.includes('transhub');
    if (!isTransHub404) {
      console.error('API request failed:', error);
    }
    
    let message = '网络请求失败';
    let code = 'NETWORK_ERROR';
    
    if (error.name === 'AbortError') {
      message = '请求超时';
      code = 'TIMEOUT_ERROR';
    } else if (error.message) {
      message = error.message;
      // Set specific code for 404 errors
      if (error.message.includes('404')) {
        code = 'NOT_FOUND';
      }
    }
    
    return {
      success: false,
      error: {
        code,
        message
      }
    } as ApiErrorResponse;
  }

  /**
   * 构建查询参数
   */
  protected buildQueryString(params: Record<string, any>): string {
    if (!params || Object.keys(params).length === 0) {
      return '';
    }

    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        if (Array.isArray(value)) {
          value.forEach(v => searchParams.append(key, String(v)));
        } else {
          searchParams.append(key, String(value));
        }
      }
    });
    
    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : '';
  }

  // ==================== HTTP 方法 ====================

  /**
   * GET 请求
   */
  protected async get<T = any>(
    endpoint: string, 
    params?: Record<string, any>,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    const queryString = this.buildQueryString(params || {});
    return this.request<T>(`${endpoint}${queryString}`, config);
  }

  /**
   * POST 请求
   */
  protected async post<T = any>(
    endpoint: string, 
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...config
    });
  }

  /**
   * PUT 请求
   */
  protected async put<T = any>(
    endpoint: string, 
    data?: any
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PATCH 请求
   */
  protected async patch<T = any>(
    endpoint: string, 
    data?: any
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE 请求
   */
  protected async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    });
  }

  /**
   * 上传文件（FormData）
   */
  protected async postFormData<T = any>(
    endpoint: string, 
    formData: FormData
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        // 不设置 Content-Type，让浏览器自动设置 multipart/form-data
        'Accept': 'application/json',
      },
    });
  }

  /**
   * 下载文件
   */
  protected async getBlob(endpoint: string): Promise<ApiResponse<Blob>> {
    return this.request<Blob>(endpoint, {
      headers: {
        'Accept': 'application/octet-stream',
      },
    });
  }

  // ==================== 工具方法 ====================

  /**
   * 检查连接状态
   */
  async checkConnection(): Promise<boolean> {
    try {
      // 健康检查API不在 /api/v1 前缀下
      const url = 'http://localhost:18000/health';  // 使用18000端口
      const response = await this.request(url);
      return response.success !== false; // 健康检查返回的格式可能不同
    } catch (error) {
      console.error('Backend connection check failed:', error);
      return false;
    }
  }

  /**
   * 获取 API 基础 URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * 设置认证令牌
   */
  setAuthToken(token: string): void {
    this.addInterceptor({
      onRequest: async (config) => {
        config.headers = {
          ...config.headers,
          'Authorization': `Bearer ${token}`
        };
        return config;
      }
    });
  }

  /**
   * 清除认证令牌
   */
  clearAuthToken(): void {
    // 这里可以实现清除逻辑，简单实现是重新创建实例
    this.interceptors = this.interceptors.filter(
      interceptor => !interceptor.onRequest?.toString().includes('Authorization')
    );
  }
}