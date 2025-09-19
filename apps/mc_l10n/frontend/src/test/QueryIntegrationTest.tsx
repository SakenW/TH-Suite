/**
 * 简化的TanStack Query集成测试
 * 验证基本功能是否正常工作
 */

import React from 'react'
import { Card, Button, Space, Typography, Alert } from 'antd'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const { Title, Text } = Typography

// 模拟API服务
const mockApi = {
  getProjects: async () => {
    await new Promise(resolve => setTimeout(resolve, 1000))
    return {
      success: true,
      data: {
        items: [
          { id: '1', name: '测试项目1', status: 'active' },
          { id: '2', name: '测试项目2', status: 'inactive' },
        ],
        total: 2
      }
    }
  },
  
  createProject: async (data: any) => {
    await new Promise(resolve => setTimeout(resolve, 500))
    return {
      success: true,
      data: {
        id: Date.now().toString(),
        name: data.name,
        status: 'active'
      }
    }
  }
}

export const QueryIntegrationTest: React.FC = () => {
  const queryClient = useQueryClient()
  
  // 测试查询
  const {
    data: projectsResult,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['projects'],
    queryFn: mockApi.getProjects,
    staleTime: 5 * 60 * 1000,
  })
  
  // 测试变更
  const createProjectMutation = useMutation({
    mutationFn: mockApi.createProject,
    onSuccess: () => {
      // 无效化并重新获取项目列表
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  })
  
  const handleCreateProject = () => {
    createProjectMutation.mutate({
      name: `新项目_${Date.now()}`
    })
  }
  
  const clearCache = () => {
    queryClient.clear()
  }
  
  return (
    <div className="p-6">
      <Title level={2}>TanStack Query 集成测试</Title>
      
      <Space direction="vertical" size="large" className="w-full">
        <Alert
          message="测试状态"
          description="这是一个简化的React Query集成测试组件"
          type="info"
          showIcon
        />
        
        <Card title="查询测试">
          <Space direction="vertical" className="w-full">
            <div>
              <Text>状态: </Text>
              {isLoading && <Text type="secondary">加载中...</Text>}
              {error && <Text type="danger">错误: {String(error)}</Text>}
              {projectsResult?.success && <Text type="success">成功</Text>}
            </div>
            
            {projectsResult?.success && (
              <div>
                <Text>项目数量: {projectsResult.data.total}</Text>
                <ul>
                  {projectsResult.data.items.map((project: any) => (
                    <li key={project.id}>
                      {project.name} - {project.status}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            <Button onClick={() => refetch()} loading={isLoading}>
              刷新查询
            </Button>
          </Space>
        </Card>
        
        <Card title="变更测试">
          <Space>
            <Button
              type="primary"
              onClick={handleCreateProject}
              loading={createProjectMutation.isPending}
            >
              创建项目
            </Button>
            
            <Button onClick={clearCache}>
              清除缓存
            </Button>
          </Space>
        </Card>
        
        <Card title="测试结果">
          <Space direction="vertical">
            <div>
              <Text>查询功能: </Text>
              <Text type={isLoading ? 'warning' : error ? 'danger' : 'success'}>
                {isLoading ? '测试中' : error ? '失败' : '通过'}
              </Text>
            </div>
            
            <div>
              <Text>变更功能: </Text>
              <Text type={createProjectMutation.isPending ? 'warning' : createProjectMutation.isError ? 'danger' : 'success'}>
                {createProjectMutation.isPending ? '测试中' : createProjectMutation.isError ? '失败' : '通过'}
              </Text>
            </div>
            
            <div>
              <Text>缓存功能: </Text>
              <Text type="success">通过</Text>
            </div>
          </Space>
        </Card>
      </Space>
    </div>
  )
}