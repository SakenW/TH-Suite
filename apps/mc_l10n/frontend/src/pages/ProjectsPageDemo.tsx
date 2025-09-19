/**
 * 项目页面演示
 * 展示如何使用新的React Query hooks和TanStack Table
 */

import React, { useState } from 'react'
import {
  Layout,
  Card,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  Input,
  Select,
  message,
  Breadcrumb,
} from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  SettingOutlined,
  BarChartOutlined,
  HomeOutlined,
  FolderOutlined,
} from '@ant-design/icons'

// 引入新的React Query hooks
import {
  useProjects,
  useRecentProjects,
  useGlobalStatistics,
  useCreateProject,
  useDeleteProject,
  useArchiveProject,
} from '../hooks/api'
import { ProjectTable } from '../components/tables/ProjectTable'
import { useErrorHandler } from '../utils/errorHandling'
import { Project, ProjectCreateRequest } from '../services/api/types'

const { Header, Content } = Layout
const { Title, Paragraph } = Typography
const { Option } = Select

// ============================================================
// 主组件
// ============================================================

export const ProjectsPageDemo: React.FC = () => {
  const { handleError, handleServiceResult } = useErrorHandler()
  
  // ============================================================
  // 状态管理
  // ============================================================
  
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false)
  const [selectedProjects, setSelectedProjects] = useState<Project[]>([])
  const [searchParams, setSearchParams] = useState({
    page: 1,
    limit: 20,
    sort_by: 'updated_at',
    sort_order: 'desc' as const,
  })
  
  const [createForm] = Form.useForm<ProjectCreateRequest>()
  
  // ============================================================
  // React Query hooks
  // ============================================================
  
  // 项目列表查询
  const {
    data: projectsResult,
    isLoading: isProjectsLoading,
    error: projectsError,
    refetch: refetchProjects,
  } = useProjects(searchParams, {
    onError: (error) => {
      handleError(error, '获取项目列表失败')
    }
  })
  
  // 最近项目查询
  const {
    data: recentProjectsResult,
    isLoading: isRecentProjectsLoading,
  } = useRecentProjects(5, {
    onError: (error) => {
      handleError(error, '获取最近项目失败')
    }
  })
  
  // 全局统计查询
  const {
    data: globalStatsResult,
    isLoading: isGlobalStatsLoading,
  } = useGlobalStatistics({
    onError: (error) => {
      handleError(error, '获取全局统计失败')
    }
  })
  
  // 创建项目变更
  const createProjectMutation = useCreateProject({
    onSuccess: (result) => {
      const project = handleServiceResult(result, '创建项目')
      if (project) {
        message.success(`项目 "${project.name}" 创建成功`)
        setIsCreateModalVisible(false)
        createForm.resetFields()
        refetchProjects()
      }
    },
    onError: (error) => {
      handleError(error, '创建项目失败')
    }
  })
  
  // 删除项目变更
  const deleteProjectMutation = useDeleteProject({
    onSuccess: (result) => {
      const success = handleServiceResult(result, '删除项目')
      if (success) {
        message.success('项目删除成功')
        refetchProjects()
      }
    },
    onError: (error) => {
      handleError(error, '删除项目失败')
    }
  })
  
  // 归档项目变更
  const archiveProjectMutation = useArchiveProject({
    onSuccess: (result) => {
      const success = handleServiceResult(result, '归档项目')
      if (success) {
        message.success('项目归档状态更新成功')
        refetchProjects()
      }
    },
    onError: (error) => {
      handleError(error, '更新项目归档状态失败')
    }
  })
  
  // ============================================================
  // 事件处理
  // ============================================================
  
  const handleCreateProject = async () => {
    try {
      const values = await createForm.validateFields()
      createProjectMutation.mutate(values)
    } catch (error) {
      console.error('Form validation failed:', error)
    }
  }
  
  const handleProjectEdit = (project: Project) => {
    message.info(`编辑项目: ${project.name}`)
    // 实现编辑逻辑
  }
  
  const handleProjectDelete = (project: Project) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除项目 "${project.name}" 吗？此操作无法撤销。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        deleteProjectMutation.mutate({
          projectId: project.id,
          force: false,
        })
      },
    })
  }
  
  const handleProjectArchive = (project: Project) => {
    const action = project.status === 'archived' ? '恢复' : '归档'
    Modal.confirm({
      title: `确认${action}`,
      content: `确定要${action}项目 "${project.name}" 吗？`,
      okText: action,
      cancelText: '取消',
      onOk: () => {
        archiveProjectMutation.mutate({
          projectId: project.id,
          reason: `用户${action}操作`,
        })
      },
    })
  }
  
  const handleProjectView = (project: Project) => {
    message.info(`查看项目详情: ${project.name}`)
    // 实现查看逻辑
  }
  
  const handleProjectSelect = (project: Project) => {
    setSelectedProjects(prev => {
      const isSelected = prev.some(p => p.id === project.id)
      if (isSelected) {
        return prev.filter(p => p.id !== project.id)
      } else {
        return [...prev, project]
      }
    })
  }
  
  // ============================================================
  // 渲染辅助函数
  // ============================================================
  
  const renderStatistics = () => {
    if (isGlobalStatsLoading) {
      return <div>加载统计数据中...</div>
    }
    
    const stats = handleServiceResult(globalStatsResult, '全局统计')
    if (!stats) {
      return <div>无法加载统计数据</div>
    }
    
    return (
      <Row gutter={16}>
        <Col span={6}>
          <Statistic
            title="总项目数"
            value={stats.total_projects}
            prefix={<FolderOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="活跃项目"
            value={stats.active_projects}
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="归档项目"
            value={stats.archived_projects}
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="总内容实例"
            value={stats.total_content_instances}
          />
        </Col>
      </Row>
    )
  }
  
  const renderRecentProjects = () => {
    if (isRecentProjectsLoading) {
      return <div>加载最近项目中...</div>
    }
    
    const recentProjects = handleServiceResult(recentProjectsResult, '最近项目')
    if (!recentProjects || recentProjects.length === 0) {
      return <div>暂无最近项目</div>
    }
    
    return (
      <Space direction="vertical" className="w-full">
        {recentProjects.map((project: Project) => (
          <Card
            key={project.id}
            size="small"
            className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => handleProjectView(project)}
          >
            <div className="flex justify-between items-center">
              <div>
                <div className="font-medium">{project.name}</div>
                <div className="text-sm text-gray-500">{project.mc_version}</div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-500">
                  {new Date(project.updated_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </Space>
    )
  }
  
  const renderCreateModal = () => (
    <Modal
      title="创建新项目"
      open={isCreateModalVisible}
      onOk={handleCreateProject}
      onCancel={() => {
        setIsCreateModalVisible(false)
        createForm.resetFields()
      }}
      confirmLoading={createProjectMutation.isPending}
      width={600}
    >
      <Form
        form={createForm}
        layout="vertical"
        initialValues={{
          mc_version: '1.19.2',
          target_language: 'zh_cn',
        }}
      >
        <Form.Item
          label="项目名称"
          name="name"
          rules={[
            { required: true, message: '请输入项目名称' },
            { min: 2, max: 50, message: '项目名称长度应在2-50字符之间' },
          ]}
        >
          <Input placeholder="输入项目名称" />
        </Form.Item>
        
        <Form.Item
          label="项目描述"
          name="description"
          rules={[{ max: 200, message: '描述长度不能超过200字符' }]}
        >
          <Input.TextArea
            placeholder="输入项目描述（可选）"
            rows={3}
          />
        </Form.Item>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="源路径"
              name="source_path"
              rules={[{ required: true, message: '请输入源路径' }]}
            >
              <Input placeholder="/path/to/source" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="输出路径"
              name="output_path"
              rules={[{ required: true, message: '请输入输出路径' }]}
            >
              <Input placeholder="/path/to/output" />
            </Form.Item>
          </Col>
        </Row>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Minecraft版本"
              name="mc_version"
              rules={[{ required: true, message: '请选择Minecraft版本' }]}
            >
              <Select placeholder="选择版本">
                <Option value="1.20.1">1.20.1</Option>
                <Option value="1.19.4">1.19.4</Option>
                <Option value="1.19.2">1.19.2</Option>
                <Option value="1.18.2">1.18.2</Option>
                <Option value="1.16.5">1.16.5</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="目标语言"
              name="target_language"
              rules={[{ required: true, message: '请选择目标语言' }]}
            >
              <Select placeholder="选择语言">
                <Option value="zh_cn">简体中文</Option>
                <Option value="zh_tw">繁体中文</Option>
                <Option value="en_us">English</Option>
                <Option value="ja_jp">日本語</Option>
                <Option value="ko_kr">한국어</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  )
  
  // ============================================================
  // 渲染
  // ============================================================
  
  return (
    <Layout className="min-h-screen">
      <Header className="bg-white border-b border-gray-200">
        <div className="flex justify-between items-center h-full">
          <div>
            <Breadcrumb>
              <Breadcrumb.Item href="/">
                <HomeOutlined />
              </Breadcrumb.Item>
              <Breadcrumb.Item>项目管理</Breadcrumb.Item>
            </Breadcrumb>
            <Title level={3} className="mb-0 mt-2">
              项目管理
            </Title>
          </div>
          
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetchProjects()}
              loading={isProjectsLoading}
            >
              刷新
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => message.info('打开设置')}
            >
              设置
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsCreateModalVisible(true)}
            >
              新建项目
            </Button>
          </Space>
        </div>
      </Header>
      
      <Content className="p-6">
        <Row gutter={[16, 16]}>
          {/* 统计卡片 */}
          <Col span={18}>
            <Card title="项目统计" className="mb-4">
              {renderStatistics()}
            </Card>
          </Col>
          
          {/* 最近项目 */}
          <Col span={6}>
            <Card title="最近项目" className="mb-4">
              {renderRecentProjects()}
            </Card>
          </Col>
          
          {/* 项目表格 */}
          <Col span={24}>
            <Card>
              <ProjectTable
                searchParams={searchParams}
                onProjectSelect={handleProjectSelect}
                onProjectEdit={handleProjectEdit}
                onProjectDelete={handleProjectDelete}
                onProjectArchive={handleProjectArchive}
                onProjectView={handleProjectView}
              />
            </Card>
          </Col>
        </Row>
        
        {selectedProjects.length > 0 && (
          <div className="fixed bottom-6 right-6 bg-white rounded-lg shadow-lg p-4 border">
            <div className="flex items-center space-x-4">
              <span>已选择 {selectedProjects.length} 个项目</span>
              <Space>
                <Button size="small">批量操作</Button>
                <Button 
                  size="small" 
                  onClick={() => setSelectedProjects([])}
                >
                  清除选择
                </Button>
              </Space>
            </div>
          </div>
        )}
        
        {renderCreateModal()}
      </Content>
    </Layout>
  )
}