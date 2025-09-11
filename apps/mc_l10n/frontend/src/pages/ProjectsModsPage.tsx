/**
 * MOD 项目页面 - 管理已扫描的模组项目
 * 支持查看、编辑、删除模组和语言文件
 */

import React, { useState, useEffect, useCallback } from 'react'
import { 
  Card, 
  Typography, 
  Button, 
  Table, 
  Space, 
  Tag, 
  Input, 
  Modal, 
  Form,
  Select,
  notification,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Progress,
  Empty,
  Tooltip,
  Badge,
  Divider
} from 'antd'
import { 
  BugOutlined, 
  SearchOutlined, 
  EditOutlined, 
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  FileTextOutlined,
  TranslationOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ScanOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { modApi } from '../services/api'
import type { ModInfo, LanguageFileInfo, PaginatedResponse } from '../services/api/types'

const { Title, Text } = Typography
const { Search } = Input
const { Option } = Select

interface ModsPageState {
  mods: ModInfo[]
  loading: boolean
  searchText: string
  selectedMod: ModInfo | null
  modalVisible: boolean
  languageFiles: LanguageFileInfo[]
  languageFilesLoading: boolean
  pagination: {
    current: number
    pageSize: number
    total: number
  }
  statistics: {
    totalMods: number
    modsWithLanguageFiles: number
    totalLanguageFiles: number
    supportedLocales: string[]
  }
}

export const ProjectsModsPage: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  
  const [state, setState] = useState<ModsPageState>({
    mods: [],
    loading: false,
    searchText: '',
    selectedMod: null,
    modalVisible: false,
    languageFiles: [],
    languageFilesLoading: false,
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0
    },
    statistics: {
      totalMods: 0,
      modsWithLanguageFiles: 0,
      totalLanguageFiles: 0,
      supportedLocales: []
    }
  })

  // 加载模组列表
  const loadMods = useCallback(async (
    page: number = 1, 
    search?: string, 
    platform?: string,
    hasLanguageFiles?: boolean
  ) => {
    setState(prev => ({ ...prev, loading: true }))
    
    try {
      const response: PaginatedResponse<ModInfo> = await modApi.getModList({
        page,
        limit: state.pagination.pageSize,
        search,
        platform,
        has_language_files: hasLanguageFiles
      })

      setState(prev => ({
        ...prev,
        mods: response.items,
        pagination: {
          ...prev.pagination,
          current: page,
          total: response.total
        },
        statistics: {
          totalMods: response.total,
          modsWithLanguageFiles: response.items.filter(mod => mod.language_file_count > 0).length,
          totalLanguageFiles: response.items.reduce((sum, mod) => sum + mod.language_file_count, 0),
          supportedLocales: [...new Set(response.items.flatMap(mod => mod.supported_locales || []))]
        }
      }))
    } catch (error) {
      notification.error({ 
        message: '加载模组失败', 
        description: String(error) 
      })
      setState(prev => ({ ...prev, mods: [] }))
    } finally {
      setState(prev => ({ ...prev, loading: false }))
    }
  }, [state.pagination.pageSize])

  // 查看模组详情
  const viewModDetail = useCallback(async (mod: ModInfo) => {
    setState(prev => ({ 
      ...prev, 
      selectedMod: mod, 
      modalVisible: true, 
      languageFilesLoading: true 
    }))

    try {
      const languageFiles = await modApi.getModLanguageFiles(mod.id)
      setState(prev => ({ ...prev, languageFiles, languageFilesLoading: false }))
    } catch (error) {
      notification.error({ message: '加载语言文件失败', description: String(error) })
      setState(prev => ({ ...prev, languageFiles: [], languageFilesLoading: false }))
    }
  }, [])

  // 删除模组
  const deleteMod = useCallback(async (modId: string) => {
    try {
      await modApi.deleteMod(modId)
      notification.success({ message: '删除模组成功' })
      loadMods(state.pagination.current, state.searchText)
    } catch (error) {
      notification.error({ message: '删除模组失败', description: String(error) })
    }
  }, [state.pagination.current, state.searchText, loadMods])

  // 重新扫描模组
  const rescanMod = useCallback(async (modId: string) => {
    try {
      const result = await modApi.rescanMod(modId)
      notification.success({ 
        message: '重新扫描已启动', 
        description: `扫描ID: ${result.scan_id}` 
      })
    } catch (error) {
      notification.error({ message: '重新扫描失败', description: String(error) })
    }
  }, [])

  // 搜索模组
  const handleSearch = useCallback((value: string) => {
    setState(prev => ({ ...prev, searchText: value }))
    loadMods(1, value)
  }, [loadMods])

  // 分页变化
  const handleTableChange = useCallback((pagination: any) => {
    loadMods(pagination.current, state.searchText)
  }, [state.searchText, loadMods])

  // 初始加载
  useEffect(() => {
    loadMods()
  }, []) // 移除 loadMods 依赖避免无限循环

  // 表格列配置
  const columns = [
    {
      title: '模组名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: ModInfo) => (
        <div>
          <div className="font-medium">{text}</div>
          <div className="text-xs text-gray-500">{record.id}</div>
        </div>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
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
      title: '语言文件',
      dataIndex: 'language_file_count',
      key: 'language_file_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: count > 0 ? '#52c41a' : '#d9d9d9' }} />
      ),
    },
    {
      title: '支持的语言',
      dataIndex: 'supported_locales',
      key: 'supported_locales',
      width: 200,
      render: (locales: string[]) => (
        <div>
          {locales?.slice(0, 3).map(locale => (
            <Tag key={locale} size="small">{locale}</Tag>
          ))}
          {locales?.length > 3 && <Text type="secondary">+{locales.length - 3}</Text>}
        </div>
      ),
    },
    {
      title: '最后更新',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 120,
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: ModInfo) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              size="small"
              onClick={() => viewModDetail(record)}
            />
          </Tooltip>
          <Tooltip title="重新扫描">
            <Button 
              type="text" 
              icon={<ReloadOutlined />} 
              size="small"
              onClick={() => rescanMod(record.id)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个模组吗？"
            onConfirm={() => deleteMod(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button 
                type="text" 
                icon={<DeleteOutlined />} 
                size="small"
                danger
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 语言文件表格列
  const languageFileColumns = [
    {
      title: '文件路径',
      dataIndex: 'file_path',
      key: 'file_path',
    },
    {
      title: '语言',
      dataIndex: 'locale',
      key: 'locale',
      width: 100,
      render: (locale: string) => <Tag>{locale}</Tag>,
    },
    {
      title: '格式',
      dataIndex: 'format',
      key: 'format',
      width: 80,
      render: (format: string) => <Tag color="blue">{format}</Tag>,
    },
    {
      title: '键数量',
      dataIndex: 'key_count',
      key: 'key_count',
      width: 100,
      render: (count: number) => <Badge count={count} showZero />,
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => `${Math.round(size / 1024)}KB`,
    },
  ]

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">🛠️ MOD 项目</Title>
        <Space>
          <Button icon={<ScanOutlined />} onClick={() => navigate('/scan')}>
            去扫描模组
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => loadMods(1, state.searchText)}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 统计信息 */}
      <Row gutter={16} className="mb-6">
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="总模组数" 
              value={state.statistics.totalMods} 
              prefix={<BugOutlined />} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="包含语言文件" 
              value={state.statistics.modsWithLanguageFiles}
              suffix={`/ ${state.statistics.totalMods}`}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="语言文件总数" 
              value={state.statistics.totalLanguageFiles} 
              prefix={<TranslationOutlined />} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="支持语言数" 
              value={state.statistics.supportedLocales.length} 
              prefix={<CheckCircleOutlined />} 
            />
          </Card>
        </Col>
      </Row>

      {/* 搜索和过滤 */}
      <Card className="mb-4">
        <Row gutter={16} align="middle">
          <Col flex={1}>
            <Search
              placeholder="搜索模组名称或ID..."
              onSearch={handleSearch}
              onChange={(e) => setState(prev => ({ ...prev, searchText: e.target.value }))}
              value={state.searchText}
              allowClear
            />
          </Col>
        </Row>
      </Card>

      {/* 模组表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={state.mods}
          rowKey="id"
          loading={state.loading}
          pagination={{
            current: state.pagination.current,
            pageSize: state.pagination.pageSize,
            total: state.pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 条`,
          }}
          onChange={handleTableChange}
          locale={{
            emptyText: (
              <Empty
                image={<BugOutlined className="text-6xl text-gray-300" />}
                description={
                  <div>
                    <Text type="secondary">暂无模组数据</Text>
                    <br />
                    <Button type="link" onClick={() => navigate('/scan')}>
                      前往扫描中心添加模组
                    </Button>
                  </div>
                }
              />
            )
          }}
        />
      </Card>

      {/* 模组详情弹窗 */}
      <Modal
        title={`模组详情 - ${state.selectedMod?.name}`}
        open={state.modalVisible}
        onCancel={() => setState(prev => ({ ...prev, modalVisible: false, selectedMod: null }))}
        width={800}
        footer={[
          <Button key="close" onClick={() => setState(prev => ({ ...prev, modalVisible: false }))}>
            关闭
          </Button>
        ]}
      >
        {state.selectedMod && (
          <div>
            <Row gutter={16} className="mb-4">
              <Col span={12}>
                <Card size="small" title="基本信息">
                  <p><strong>ID:</strong> {state.selectedMod.id}</p>
                  <p><strong>版本:</strong> {state.selectedMod.version}</p>
                  <p><strong>平台:</strong> <Tag>{state.selectedMod.platform}</Tag></p>
                  <p><strong>文件路径:</strong> {state.selectedMod.file_path}</p>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="翻译统计">
                  <p><strong>语言文件:</strong> {state.selectedMod.language_file_count}</p>
                  <p><strong>支持语言:</strong></p>
                  <div>
                    {state.selectedMod.supported_locales?.map(locale => (
                      <Tag key={locale}>{locale}</Tag>
                    ))}
                  </div>
                </Card>
              </Col>
            </Row>

            <Divider>语言文件列表</Divider>
            <Table
              columns={languageFileColumns}
              dataSource={state.languageFiles}
              rowKey="id"
              loading={state.languageFilesLoading}
              size="small"
              pagination={{ pageSize: 5 }}
              locale={{
                emptyText: state.languageFilesLoading ? '加载中...' : '暂无语言文件'
              }}
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ProjectsModsPage