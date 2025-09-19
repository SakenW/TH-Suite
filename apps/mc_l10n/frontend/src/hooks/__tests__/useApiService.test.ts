import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useApiService } from '../useApiService'

// Mock API service
const mockApiService = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  health: vi.fn(),
}

vi.mock('@/services/api/BaseApiService', () => ({
  default: class MockApiService {
    constructor() {
      return mockApiService
    }
  },
}))

describe('useApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should initialize API service', () => {
    const { result } = renderHook(() => useApiService())
    
    expect(result.current.apiService).toBeDefined()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('should handle GET requests', async () => {
    const mockData = { id: 1, name: 'Test' }
    mockApiService.get.mockResolvedValue({ success: true, data: mockData })

    const { result } = renderHook(() => useApiService())
    
    const response = await result.current.get('/test')
    
    expect(mockApiService.get).toHaveBeenCalledWith('/test')
    expect(response.success).toBe(true)
    expect(response.data).toEqual(mockData)
  })

  it('should handle POST requests', async () => {
    const postData = { name: 'New Item' }
    const mockResponse = { id: 2, ...postData }
    mockApiService.post.mockResolvedValue({ success: true, data: mockResponse })

    const { result } = renderHook(() => useApiService())
    
    const response = await result.current.post('/test', postData)
    
    expect(mockApiService.post).toHaveBeenCalledWith('/test', postData)
    expect(response.data).toEqual(mockResponse)
  })

  it('should handle API errors', async () => {
    const errorMessage = 'Network error'
    mockApiService.get.mockRejectedValue(new Error(errorMessage))

    const { result } = renderHook(() => useApiService())
    
    try {
      await result.current.get('/test')
    } catch (error) {
      expect(error.message).toBe(errorMessage)
    }
  })

  it('should track loading state', async () => {
    // 模拟慢速API调用
    mockApiService.get.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
    )

    const { result } = renderHook(() => useApiService())
    
    expect(result.current.isLoading).toBe(false)
    
    const request = result.current.get('/test')
    
    // 在请求期间应该显示loading
    expect(result.current.isLoading).toBe(true)
    
    await request
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('should handle concurrent requests', async () => {
    mockApiService.get.mockResolvedValue({ success: true, data: 'response' })

    const { result } = renderHook(() => useApiService())
    
    // 同时发起多个请求
    const requests = [
      result.current.get('/test1'),
      result.current.get('/test2'),
      result.current.get('/test3'),
    ]
    
    const responses = await Promise.all(requests)
    
    expect(responses).toHaveLength(3)
    responses.forEach(response => {
      expect(response.success).toBe(true)
    })
  })

  it('should validate request data', async () => {
    const { result } = renderHook(() => useApiService())
    
    // 测试无效的URL
    await expect(result.current.get('')).rejects.toThrow()
    
    // 测试无效的数据
    await expect(result.current.post('/test', null)).rejects.toThrow()
  })

  it('should implement retry logic', async () => {
    // 第一次调用失败，第二次成功
    mockApiService.get
      .mockRejectedValueOnce(new Error('Temporary error'))
      .mockResolvedValueOnce({ success: true, data: 'success' })

    const { result } = renderHook(() => useApiService())
    
    const response = await result.current.get('/test', { retry: true })
    
    expect(mockApiService.get).toHaveBeenCalledTimes(2)
    expect(response.success).toBe(true)
  })

  it('should cache responses when configured', async () => {
    const mockData = { cached: true }
    mockApiService.get.mockResolvedValue({ success: true, data: mockData })

    const { result } = renderHook(() => useApiService())
    
    // 第一次请求
    await result.current.get('/test', { cache: true })
    
    // 第二次请求应该使用缓存
    await result.current.get('/test', { cache: true })
    
    // API应该只被调用一次
    expect(mockApiService.get).toHaveBeenCalledTimes(1)
  })

  it('should handle timeout correctly', async () => {
    mockApiService.get.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 10000))
    )

    const { result } = renderHook(() => useApiService())
    
    await expect(
      result.current.get('/test', { timeout: 100 })
    ).rejects.toThrow('timeout')
  })
})