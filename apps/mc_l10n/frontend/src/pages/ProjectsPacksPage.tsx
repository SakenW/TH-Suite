/**
 * 整合包项目页面 - 管理已扫描的整合包项目
 * 支持查看、编辑、删除整合包和版本管理
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Badge,
  Progress,
  Typography,
  Input,
  Select,
  Tooltip,
  Row,
  Col,
  Statistic,
  Empty,
  App,
  Popconfirm,
  Modal,
  Divider
} from 'antd'
import {
  FolderOutlined,
  ScanOutlined,
  ReloadOutlined,
  FolderOpenOutlined,
  CloudServerOutlined,
  EyeOutlined,
  DeleteOutlined,
  EditOutlined,
  SettingOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { packApi } from '../services/api'
import type { PackInfo, PackVersion, PaginatedResponse } from '../services/api/types'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography
const { Search } = Input
const { Option } = Select

interface PacksPageState {
  packs: PackInfo[]
  loading: boolean
  searchText: string
  selectedPack: PackInfo | null
  modalVisible: boolean
  packVersions: PackVersion[]
  versionsLoading: boolean
  pagination: {
    current: number
    pageSize: number
    total: number
  }
  statistics: {
    totalPacks: number
    totalVersions: number
    totalMods: number
    platformDistribution: Record<string, number>
  }
  // 新增批量操作相关状态
  selectedRowKeys: string[]
  platformFilter?: string
  versionFilter?: string
  showBatchModal: boolean
}

export const ProjectsPacksPage: React.FC = () => {
  const navigate = useNavigate()
  const { notification } = App.useApp()
  
  const [state, setState] = useState<PacksPageState>({
    packs: [],
    loading: false,
    searchText: '',
    selectedPack: null,
    modalVisible: false,
    packVersions: [],
    versionsLoading: false,
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0
    },
    statistics: {
      totalPacks: 0,
      totalVersions: 0,
      totalMods: 0,
      platformDistribution: {}
    },
    // 新增批量操作状态初始值
    selectedRowKeys: [],
    platformFilter: undefined,
    versionFilter: undefined,
    showBatchModal: false
  })

  // 加载整合包列表
  const loadPacks = useCallback(async (
    page: number = 1,
    search?: string,
    platform?: string
  ) => {
    setState(prev => ({ ...prev, loading: true }))
    
    try {
      const response: PaginatedResponse<PackInfo> = await packApi.getPackList({
        page,
        limit: state.pagination.pageSize,
        platform,
        search
      })

      // 计算统计信息
      const platformDistribution: Record<string, number> = {}
      let totalMods = 0
      
      ;(response.items || []).forEach(pack => {
        platformDistribution[pack.platform] = (platformDistribution[pack.platform] || 0) + 1
        totalMods += pack.mod_count || 0
      })

      setState(prev => ({
        ...prev,
        packs: response.items || [],
        pagination: {
          ...prev.pagination,
          current: page,
          total: response.total || 0
        },
        statistics: {
          totalPacks: response.total || 0,
          totalVersions: (response.items || []).reduce((sum, pack) => sum + (pack.version_count || 0), 0),
          totalMods,
          platformDistribution
        }
      }))
    } catch (error) {
      notification.error({ 
        message: '加载整合包失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, packs: [] }))
    } finally {
      setState(prev => ({ ...prev, loading: false }))
    }
  }, [state.pagination.pageSize])

  // 查看整合包详情
  const viewPackDetail = useCallback(async (pack: PackInfo) => {
    setState(prev => ({ 
      ...prev, 
      selectedPack: pack, 
      modalVisible: true, 
      versionsLoading: true 
    }))

    try {
      const versions = await packApi.getPackVersions(pack.id)
      setState(prev => ({ ...prev, packVersions: versions, versionsLoading: false }))
    } catch (error) {
      notification.error({ message: '加载版本信息失败', description: String(error) })
      setState(prev => ({ ...prev, packVersions: [], versionsLoading: false }))
    }
  }, [])

  // 删除整合包
  const deletePack = useCallback(async (packId: string) => {
    try {
      await packApi.deletePack(packId)
      notification.success({ message: '删除整合包成功' })
      loadPacks(state.pagination.current, state.searchText)
    } catch (error) {
      notification.error({ message: '删除整合包失败', description: String(error) })
    }
  }, [state.pagination.current, state.searchText, loadPacks])

  // 搜索整合包
  const handleSearch = useCallback((value: string) => {
    setState(prev => ({ ...prev, searchText: value }))
    loadPacks(1, value)
  }, [loadPacks])

  // 分页变化
  const handleTableChange = useCallback((pagination: any) => {
    loadPacks(pagination.current, state.searchText)
  }, [state.searchText, loadPacks])

  // 初始加载
  useEffect(() => {
    loadPacks()
  }, [])

  // 表格列定义
  const columns = [
    {
      title: '整合包名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: PackInfo) => (
        <div>
          <div className="font-medium">{text}</div>
          <div className="text-xs text-gray-500">{record.id}</div>
        </div>
      ),
    },
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      width: 100,
      render: (platform: string) => (
        <Tag color={platform === 'curseforge' ? 'orange' : platform === 'modrinth' ? 'green' : 'blue'}>
          {platform}
        </Tag>
      ),
    },
    {
      title: '版本数',
      dataIndex: 'version_count',
      key: 'version_count',
      width: 80,
      render: (count: number) => <Badge count={count || 0} showZero />,
    },
    {
      title: '包含模组',
      dataIndex: 'mod_count',
      key: 'mod_count',
      width: 100,
      render: (count: number) => <Text>{(count || 0).toLocaleString()}</Text>,
    },
    {
      title: '最新版本',
      dataIndex: 'latest_mc_version',
      key: 'latest_mc_version',
      width: 120,
      render: (version: string) => version ? <Tag color="blue">{version}</Tag> : '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 120,
      render: (date: string) => date ? dayjs(date).fromNow() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: PackInfo) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
             
              onClick={() => viewPackDetail(record)}
            />
          </Tooltip>
          <Tooltip title="打开文件夹">
            <Button 
              type="text" 
              icon={<FolderOpenOutlined />} 
             
              onClick={() => handleOpenFolder(record.root_path || '')}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个整合包吗？"
            onConfirm={() => deletePack(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button 
                type="text" 
                icon={<DeleteOutlined />} 
               
                danger
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 版本表格列
  const versionColumns = [
    {
      title: 'MC 版本',
      dataIndex: 'mc_version',
      key: 'mc_version',
      render: (version: string) => <Tag color="blue">{version}</Tag>,
    },
    {
      title: '模组加载器',
      dataIndex: 'loader',
      key: 'loader',
      render: (loader: string) => <Tag color="green">{loader}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
  ]

  // 批量操作处理
  const handleBatchDelete = useCallback(async () => {
    if (state.selectedRowKeys.length === 0) return
    
    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${state.selectedRowKeys.length} 个整合包吗？此操作不可撤销。`,
      okText: '确定删除',
      cancelText: '取消',
      danger: true,
      onOk: async () => {
        try {
          // TODO: 实现批量删除API调用
          for (const packId of state.selectedRowKeys) {
            await packApi.deletePack(packId)
          }
          notification.success({ message: `成功删除 ${state.selectedRowKeys.length} 个整合包` })
          setState(prev => ({ ...prev, selectedRowKeys: [] }))
          loadPacks(state.pagination.current, state.searchText, state.platformFilter)
        } catch (error) {
          notification.error({ message: '批量删除失败', description: String(error) })
        }
      }
    })
  }, [state.selectedRowKeys, state.pagination.current, state.searchText, state.platformFilter, loadPacks])

  // 行选择配置
  const rowSelection = {
    selectedRowKeys: state.selectedRowKeys,
    onChange: (selectedRowKeys: React.Key[]) => {
      setState(prev => ({ ...prev, selectedRowKeys: selectedRowKeys as string[] }))
    },
    onSelectAll: (selected: boolean, selectedRows: PackInfo[], changeRows: PackInfo[]) => {
      console.log('Select all:', selected, selectedRows, changeRows)
    },
    onSelect: (record: PackInfo, selected: boolean, selectedRows: PackInfo[]) => {
      console.log('Select:', record, selected, selectedRows)
    },
  }

  // 批量操作弹窗处理
  const setShowBatchModal = (visible: boolean) => {
    setState(prev => ({ ...prev, showBatchModal: visible }))
  }

  // 操作处理
  const handleOpenFolder = async (path: string) => {
    try {
      // 检查是否在Tauri环境中
      if (typeof window !== 'undefined' && (window as any).__TAURI__ && (window as any).__TAURI__.tauri) {
        // 使用Tauri全局API
        await (window as any).__TAURI__.tauri.invoke('open_path', { path })
      } else {
        notification.info({ message: '文件夹操作仅在桌面应用中可用' })
      }
    } catch (error) {
      notification.error({ message: '打开文件夹失败', description: String(error) })
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">📦 整合包项目</Title>
        <Space>
          <Button icon={<ScanOutlined />} onClick={() => navigate('/scan')}>
            去扫描整合包
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => loadPacks(1, state.searchText)}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 统计信息 */}
      <Row gutter={16} className="mb-6">
        <Col span={6}>
          <Card>
            <Statistic 
              title="整合包总数" 
              value={state.statistics.totalPacks} 
              prefix={<FolderOutlined />} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="版本总数" 
              value={state.statistics.totalVersions}
              prefix={<SettingOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="包含模组总数" 
              value={state.statistics.totalMods} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-2">平台分布</div>
              <div>
                {Object.entries(state.statistics.platformDistribution).map(([platform, count]) => (
                  <Tag key={platform} color={platform === 'curseforge' ? 'orange' : 'green'}>
                    {platform}: {count}
                  </Tag>
                ))}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 搜索和批量操作 */}
      <Card className="mb-4">
        <Row gutter={16} align="middle">
          <Col flex={1}>
            <Search
              placeholder="搜索整合包名称或ID..."
              onSearch={handleSearch}
              onChange={(e) => setState(prev => ({ ...prev, searchText: e.target.value }))}
              value={state.searchText}
              allowClear
            />
          </Col>
          <Col>
            <Select
              placeholder="平台筛选"
              allowClear
              style={{ width: 120 }}
              onChange={(value) => {
                setState(prev => ({ ...prev, platformFilter: value }))
                loadPacks(1, state.searchText, value)
              }}
              options={[
                { label: 'CurseForge', value: 'curseforge' },
                { label: 'Modrinth', value: 'modrinth' },
                { label: 'MultiMC', value: 'multimc' }
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="版本筛选"
              allowClear
              style={{ width: 120 }}
              onChange={(value) => {
                setState(prev => ({ ...prev, versionFilter: value }))
                // TODO: 实现版本筛选逻辑
              }}
              options={[
                { label: '1.20.x', value: '1.20' },
                { label: '1.19.x', value: '1.19' },
                { label: '1.18.x', value: '1.18' },
                { label: '1.16.x', value: '1.16' }
              ]}
            />
          </Col>
          <Col>
            <Space.Compact>
              <Button 
                icon={<EditOutlined />}
                disabled={state.selectedRowKeys.length === 0}
                onClick={() => setShowBatchModal(true)}
              >
                批量操作
              </Button>
              <Button 
                icon={<DeleteOutlined />}
                danger
                disabled={state.selectedRowKeys.length === 0}
                onClick={handleBatchDelete}
              >
                批量删除
              </Button>
            </Space.Compact>
          </Col>
        </Row>
      </Card>

      {/* 整合包表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={state.packs}
          rowKey="id"
          loading={state.loading}
          rowSelection={rowSelection}
          pagination={{
            current: state.pagination.current,
            pageSize: state.pagination.pageSize,
            total: state.pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => {
              const selectedInfo = state.selectedRowKeys.length > 0 
                ? `，已选择 ${state.selectedRowKeys.length} 条` 
                : ''
              return `${range[0]}-${range[1]} 共 ${total} 条${selectedInfo}`
            },
          }}
          onChange={handleTableChange}
          locale={{
            emptyText: (
              <Empty
                image={<FolderOutlined className="text-6xl text-gray-300" />}
                description={
                  <div>
                    <Text type="secondary">暂无整合包数据</Text>
                    <br />
                    <Button type="link" onClick={() => navigate('/scan')}>
                      前往扫描中心添加整合包
                    </Button>
                  </div>
                }
              />
            )
          }}
        />
      </Card>

      {/* 整合包详情弹窗 */}
      <Modal
        title={`整合包详情 - ${state.selectedPack?.name}`}
        open={state.modalVisible}
        onCancel={() => setState(prev => ({ ...prev, modalVisible: false, selectedPack: null }))}
        width={900}
        footer={[
          <Button key="close" onClick={() => setState(prev => ({ ...prev, modalVisible: false }))}>
            关闭
          </Button>
        ]}
      >
        {state.selectedPack && (
          <div>
            <Row gutter={16} className="mb-4">
              <Col span={12}>
                <Card title="基本信息">
                  <p><strong>ID:</strong> {state.selectedPack.id}</p>
                  <p><strong>平台:</strong> <Tag>{state.selectedPack.platform}</Tag></p>
                  <p><strong>根路径:</strong> {state.selectedPack.root_path}</p>
                  <p><strong>最新MC版本:</strong> {state.selectedPack.latest_mc_version || '-'}</p>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="统计信息">
                  <p><strong>版本数:</strong> {state.selectedPack.version_count || 0}</p>
                  <p><strong>包含模组:</strong> {state.selectedPack.mod_count || 0}</p>
                  <p><strong>创建时间:</strong> {state.selectedPack.created_at ? dayjs(state.selectedPack.created_at).format('YYYY-MM-DD HH:mm') : '-'}</p>
                  <p><strong>更新时间:</strong> {state.selectedPack.updated_at ? dayjs(state.selectedPack.updated_at).format('YYYY-MM-DD HH:mm') : '-'}</p>
                </Card>
              </Col>
            </Row>

            <Divider>版本列表</Divider>
            <Table
              columns={versionColumns}
              dataSource={state.packVersions}
              rowKey="id"
              loading={state.versionsLoading}
             
              pagination={{ pageSize: 5 }}
              locale={{
                emptyText: state.versionsLoading ? '加载中...' : '暂无版本信息'
              }}
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ProjectsPacksPage