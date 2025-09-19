/**
 * 项目表格组件
 * 专用于显示项目列表的数据表格
 */

import React, { useMemo, useState } from 'react'
import { ColumnDef, SortingState, ColumnFiltersState, VisibilityState } from '@tanstack/react-table'
import { Tag, Button, Space, Typography, Avatar, Tooltip, Dropdown, Progress } from 'antd'
import { 
  EditOutlined, 
  DeleteOutlined, 
  ArchiveBoxOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  MoreOutlined,
  FolderOutlined,
  CalendarOutlined,
  GlobalOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { DataTable } from './DataTable'
import { Project, ProjectSearchParams } from '../../services/api/types'
import { useProjects } from '../../hooks/api'

const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

interface ProjectTableProps {
  projectId?: string
  searchParams?: ProjectSearchParams
  onProjectSelect?: (project: Project) => void
  onProjectEdit?: (project: Project) => void
  onProjectDelete?: (project: Project) => void
  onProjectArchive?: (project: Project) => void
  onProjectView?: (project: Project) => void
  className?: string
}

// ============================================================
// 列定义
// ============================================================

const createProjectColumns = (
  onEdit?: (project: Project) => void,
  onDelete?: (project: Project) => void,
  onArchive?: (project: Project) => void,
  onView?: (project: Project) => void
): ColumnDef<Project>[] => [
  {
    id: 'select',
    header: ({ table }) => (
      <input
        type="checkbox"
        checked={table.getIsAllPageRowsSelected()}
        onChange={table.getToggleAllPageRowsSelectedHandler()}
        className="rounded border-gray-300"
      />
    ),
    cell: ({ row }) => (
      <input
        type="checkbox"
        checked={row.getIsSelected()}
        onChange={row.getToggleSelectedHandler()}
        className="rounded border-gray-300"
      />
    ),
    enableSorting: false,
    enableHiding: false,
    size: 50,
  },
  
  {
    accessorKey: 'name',
    header: '项目名称',
    cell: ({ row }) => {
      const project = row.original
      return (
        <div className="flex items-center space-x-3">
          <Avatar 
            shape="square" 
            size="large"
            icon={<FolderOutlined />}
            className="bg-blue-500"
          />
          <div>
            <div className="font-medium text-gray-900">
              {project.name}
            </div>
            {project.description && (
              <div className="text-sm text-gray-500 truncate max-w-xs">
                {project.description}
              </div>
            )}
          </div>
        </div>
      )
    },
    enableSorting: true,
    size: 250,
  },
  
  {
    accessorKey: 'mc_version',
    header: 'MC版本',
    cell: ({ getValue }) => {
      const version = getValue() as string
      return (
        <Tag color="blue" className="font-mono">
          {version}
        </Tag>
      )
    },
    enableSorting: true,
    size: 100,
  },
  
  {
    accessorKey: 'target_language',
    header: '目标语言',
    cell: ({ getValue }) => {
      const language = getValue() as string
      const languageMap: Record<string, { name: string; flag: string }> = {
        'zh_cn': { name: '简体中文', flag: '🇨🇳' },
        'zh_tw': { name: '繁体中文', flag: '🇹🇼' },
        'en_us': { name: 'English', flag: '🇺🇸' },
        'ja_jp': { name: '日本語', flag: '🇯🇵' },
        'ko_kr': { name: '한국어', flag: '🇰🇷' },
      }
      
      const langInfo = languageMap[language] || { name: language, flag: '🌐' }
      
      return (
        <Space>
          <span>{langInfo.flag}</span>
          <span>{langInfo.name}</span>
        </Space>
      )
    },
    enableSorting: true,
    size: 120,
  },
  
  {
    accessorKey: 'status',
    header: '状态',
    cell: ({ getValue }) => {
      const status = getValue() as string
      const statusConfig = {
        active: { color: 'success', icon: <CheckCircleOutlined />, text: '活跃' },
        inactive: { color: 'default', icon: <ClockCircleOutlined />, text: '未激活' },
        archived: { color: 'warning', icon: <ArchiveBoxOutlined />, text: '已归档' },
        error: { color: 'error', icon: <ExclamationCircleOutlined />, text: '错误' },
      }
      
      const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.inactive
      
      return (
        <Tag color={config.color} icon={config.icon}>
          {config.text}
        </Tag>
      )
    },
    enableSorting: true,
    size: 100,
  },
  
  {
    accessorKey: 'progress',
    header: '翻译进度',
    cell: ({ row }) => {
      const project = row.original
      // 假设从统计信息中获取进度
      const translated = project.statistics?.translated_entries || 0
      const total = project.statistics?.total_entries || 1
      const percentage = Math.round((translated / total) * 100)
      
      return (
        <div className="w-20">
          <Progress 
            percent={percentage}
            size="small"
            strokeColor={{
              '0%': '#ff4d4f',
              '50%': '#faad14',
              '100%': '#52c41a',
            }}
          />
          <Text type="secondary" className="text-xs">
            {translated}/{total}
          </Text>
        </div>
      )
    },
    enableSorting: false,
    size: 120,
  },
  
  {
    accessorKey: 'created_at',
    header: '创建时间',
    cell: ({ getValue }) => {
      const date = getValue() as string
      return (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          <Space>
            <CalendarOutlined className="text-gray-400" />
            <span className="text-sm">
              {dayjs(date).fromNow()}
            </span>
          </Space>
        </Tooltip>
      )
    },
    enableSorting: true,
    size: 120,
  },
  
  {
    accessorKey: 'updated_at',
    header: '更新时间',
    cell: ({ getValue }) => {
      const date = getValue() as string
      return (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          <span className="text-sm text-gray-500">
            {dayjs(date).fromNow()}
          </span>
        </Tooltip>
      )
    },
    enableSorting: true,
    size: 120,
  },
  
  {
    id: 'actions',
    header: '操作',
    cell: ({ row }) => {
      const project = row.original
      
      const menuItems = [
        {
          key: 'view',
          label: '查看详情',
          icon: <EyeOutlined />,
          onClick: () => onView?.(project),
        },
        {
          key: 'edit',
          label: '编辑项目',
          icon: <EditOutlined />,
          onClick: () => onEdit?.(project),
        },
        {
          type: 'divider' as const,
        },
        {
          key: 'archive',
          label: project.status === 'archived' ? '恢复项目' : '归档项目',
          icon: <ArchiveBoxOutlined />,
          onClick: () => onArchive?.(project),
        },
        {
          key: 'delete',
          label: '删除项目',
          icon: <DeleteOutlined />,
          danger: true,
          onClick: () => onDelete?.(project),
        },
      ]
      
      return (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => onView?.(project)}
          >
            打开
          </Button>
          
          <Dropdown
            menu={{ items: menuItems }}
            trigger={['click']}
            placement="bottomRight"
          >
            <Button size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      )
    },
    enableSorting: false,
    enableHiding: false,
    size: 120,
  },
]

// ============================================================
// 主组件
// ============================================================

export const ProjectTable: React.FC<ProjectTableProps> = ({
  projectId,
  searchParams,
  onProjectSelect,
  onProjectEdit,
  onProjectDelete,
  onProjectArchive,
  onProjectView,
  className,
}) => {
  // ============================================================
  // 状态管理
  // ============================================================
  
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'updated_at', desc: true }
  ])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 20,
  })
  
  // ============================================================
  // 数据查询
  // ============================================================
  
  const queryParams = useMemo(() => ({
    ...searchParams,
    page: pagination.pageIndex + 1,
    limit: pagination.pageSize,
    sort_by: sorting[0]?.id || 'updated_at',
    sort_order: sorting[0]?.desc ? 'desc' : 'asc',
    search: globalFilter || undefined,
  }), [searchParams, pagination, sorting, globalFilter])
  
  const {
    data: projectsResult,
    isLoading,
    error,
    refetch,
  } = useProjects(queryParams)
  
  // ============================================================
  // 列定义
  // ============================================================
  
  const columns = useMemo(() => 
    createProjectColumns(onProjectEdit, onProjectDelete, onProjectArchive, onProjectView),
    [onProjectEdit, onProjectDelete, onProjectArchive, onProjectView]
  )
  
  // ============================================================
  // 事件处理
  // ============================================================
  
  const handlePaginationChange = (pageIndex: number, pageSize: number) => {
    setPagination({ pageIndex, pageSize })
  }
  
  const handleExport = (data: Project[]) => {
    // 实现导出逻辑
    const exportData = data.map(project => ({
      名称: project.name,
      描述: project.description,
      MC版本: project.mc_version,
      目标语言: project.target_language,
      状态: project.status,
      创建时间: dayjs(project.created_at).format('YYYY-MM-DD HH:mm:ss'),
      更新时间: dayjs(project.updated_at).format('YYYY-MM-DD HH:mm:ss'),
    }))
    
    const csv = [
      Object.keys(exportData[0]).join(','),
      ...exportData.map(row => Object.values(row).join(','))
    ].join('\n')
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `projects_${dayjs().format('YYYYMMDD_HHmmss')}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
  
  // ============================================================
  // 渲染
  // ============================================================
  
  if (!projectsResult?.success) {
    return (
      <div className="text-center py-8">
        <Text type="danger">
          加载项目列表失败: {projectsResult?.error?.message || '未知错误'}
        </Text>
        <div className="mt-4">
          <Button onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    )
  }
  
  const projects = projectsResult.data?.items || []
  const total = projectsResult.data?.total || 0
  
  return (
    <DataTable
      data={projects}
      columns={columns}
      loading={isLoading}
      error={error}
      className={className}
      
      // 分页配置
      pagination={{
        pageIndex: pagination.pageIndex,
        pageSize: pagination.pageSize,
        total,
        onChange: handlePaginationChange,
      }}
      
      // 排序配置
      sorting={{
        state: sorting,
        onChange: setSorting,
      }}
      
      // 过滤配置
      filtering={{
        globalFilter,
        columnFilters,
        onGlobalFilterChange: setGlobalFilter,
        onColumnFiltersChange: setColumnFilters,
      }}
      
      // 列可见性
      columnVisibility={{
        state: columnVisibility,
        onChange: setColumnVisibility,
      }}
      
      // 工具栏配置
      toolbar={{
        title: '项目列表',
        showGlobalFilter: true,
        showColumnVisibility: true,
        showExport: true,
        customActions: (
          <Button 
            type="primary" 
            onClick={() => {/* 创建新项目 */}}
          >
            新建项目
          </Button>
        ),
      }}
      
      // 事件处理
      onRowClick={onProjectSelect}
      onRowDoubleClick={onProjectView}
      onExport={handleExport}
      
      // 样式配置
      size="middle"
      bordered
      striped
    />
  )
}