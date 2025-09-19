/**
 * 基于TanStack Table的高性能数据表格组件
 * 集成了排序、过滤、分页、虚拟化等功能
 */

import React, { useMemo, useState, useCallback } from 'react'
import { 
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  PaginationState,
  OnChangeFn,
} from '@tanstack/react-table'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow,
  Button,
  Input,
  Select,
  Pagination,
  Spin,
  Empty,
  Space,
  Tooltip,
  Dropdown,
  Badge,
  Typography,
  Flex
} from 'antd'
import { 
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  SettingOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  EyeOutlined,
  EyeInvisibleOutlined
} from '@ant-design/icons'
import { Virtuoso } from 'react-virtuoso'

const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

export interface DataTableProps<TData> {
  // 数据
  data: TData[]
  columns: ColumnDef<TData>[]
  
  // 加载状态
  loading?: boolean
  error?: Error | null
  
  // 分页配置
  pagination?: {
    pageIndex: number
    pageSize: number
    total: number
    onChange: (pageIndex: number, pageSize: number) => void
  }
  
  // 排序配置
  sorting?: {
    state: SortingState
    onChange: OnChangeFn<SortingState>
  }
  
  // 过滤配置
  filtering?: {
    globalFilter: string
    columnFilters: ColumnFiltersState
    onGlobalFilterChange: OnChangeFn<string>
    onColumnFiltersChange: OnChangeFn<ColumnFiltersState>
  }
  
  // 列可见性
  columnVisibility?: {
    state: VisibilityState
    onChange: OnChangeFn<VisibilityState>
  }
  
  // 行选择
  rowSelection?: {
    state: Record<string, boolean>
    onChange: OnChangeFn<Record<string, boolean>>
    mode?: 'checkbox' | 'radio'
  }
  
  // 虚拟化配置
  virtualization?: {
    enabled: boolean
    estimateSize?: number
  }
  
  // 自定义配置
  tableOptions?: {
    enableGlobalFilter?: boolean
    enableColumnFilters?: boolean
    enableSorting?: boolean
    enableMultiSort?: boolean
    enableColumnResizing?: boolean
    enableRowSelection?: boolean
    enablePagination?: boolean
  }
  
  // 工具栏配置
  toolbar?: {
    title?: string
    showGlobalFilter?: boolean
    showColumnVisibility?: boolean
    showExport?: boolean
    customActions?: React.ReactNode
  }
  
  // 事件处理
  onRowClick?: (row: TData) => void
  onRowDoubleClick?: (row: TData) => void
  onExport?: (data: TData[]) => void
  
  // 样式
  className?: string
  size?: 'small' | 'middle' | 'large'
  bordered?: boolean
  striped?: boolean
}

// ============================================================
// 主组件
// ============================================================

export function DataTable<TData>({
  data,
  columns,
  loading = false,
  error = null,
  pagination,
  sorting,
  filtering,
  columnVisibility,
  rowSelection,
  virtualization,
  tableOptions = {},
  toolbar,
  onRowClick,
  onRowDoubleClick,
  onExport,
  className = '',
  size = 'middle',
  bordered = true,
  striped = true,
}: DataTableProps<TData>) {
  
  // ============================================================
  // 状态管理
  // ============================================================
  
  const [localSorting, setLocalSorting] = useState<SortingState>([])
  const [localColumnFilters, setLocalColumnFilters] = useState<ColumnFiltersState>([])
  const [localGlobalFilter, setLocalGlobalFilter] = useState('')
  const [localColumnVisibility, setLocalColumnVisibility] = useState<VisibilityState>({})
  const [localRowSelection, setLocalRowSelection] = useState<Record<string, boolean>>({})
  const [localPagination, setLocalPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 20,
  })
  
  // ============================================================
  // 表格配置
  // ============================================================
  
  const table = useReactTable({
    data,
    columns,
    
    // 核心功能
    getCoreRowModel: getCoreRowModel(),
    
    // 排序
    getSortedRowModel: tableOptions.enableSorting !== false ? getSortedRowModel() : undefined,
    state: {
      ...(sorting && { sorting: sorting.state }),
      ...(!sorting && tableOptions.enableSorting !== false && { sorting: localSorting }),
    },
    onSortingChange: sorting?.onChange || setLocalSorting,
    enableSorting: tableOptions.enableSorting !== false,
    enableMultiSort: tableOptions.enableMultiSort !== false,
    
    // 过滤
    getFilteredRowModel: (tableOptions.enableGlobalFilter || tableOptions.enableColumnFilters) ? getFilteredRowModel() : undefined,
    globalFilterFn: 'includesString',
    ...(filtering && {
      state: {
        globalFilter: filtering.globalFilter,
        columnFilters: filtering.columnFilters,
      },
      onGlobalFilterChange: filtering.onGlobalFilterChange,
      onColumnFiltersChange: filtering.onColumnFiltersChange,
    }),
    ...(!filtering && {
      state: {
        globalFilter: localGlobalFilter,
        columnFilters: localColumnFilters,
      },
      onGlobalFilterChange: setLocalGlobalFilter,
      onColumnFiltersChange: setLocalColumnFilters,
    }),
    
    // 分页
    getPaginationRowModel: tableOptions.enablePagination !== false ? getPaginationRowModel() : undefined,
    ...(pagination && {
      manualPagination: true,
      pageCount: Math.ceil(pagination.total / pagination.pageSize),
      state: {
        pagination: {
          pageIndex: pagination.pageIndex,
          pageSize: pagination.pageSize,
        },
      },
      onPaginationChange: (updater) => {
        const newState = typeof updater === 'function' 
          ? updater({ pageIndex: pagination.pageIndex, pageSize: pagination.pageSize })
          : updater
        pagination.onChange(newState.pageIndex, newState.pageSize)
      },
    }),
    ...(!pagination && tableOptions.enablePagination !== false && {
      state: { pagination: localPagination },
      onPaginationChange: setLocalPagination,
    }),
    
    // 列可见性
    ...(columnVisibility && {
      state: { columnVisibility: columnVisibility.state },
      onColumnVisibilityChange: columnVisibility.onChange,
    }),
    ...(!columnVisibility && {
      state: { columnVisibility: localColumnVisibility },
      onColumnVisibilityChange: setLocalColumnVisibility,
    }),
    
    // 行选择
    ...(rowSelection && {
      enableRowSelection: true,
      state: { rowSelection: rowSelection.state },
      onRowSelectionChange: rowSelection.onChange,
    }),
    ...(!rowSelection && tableOptions.enableRowSelection && {
      enableRowSelection: true,
      state: { rowSelection: localRowSelection },
      onRowSelectionChange: setLocalRowSelection,
    }),
    
    // 调试
    debugTable: process.env.NODE_ENV === 'development',
  })
  
  // ============================================================
  // 工具栏组件
  // ============================================================
  
  const renderToolbar = useCallback(() => {
    if (!toolbar) return null
    
    const selectedRows = table.getSelectedRowModel().rows
    const hasSelection = selectedRows.length > 0
    
    return (
      <Flex justify="space-between" align="center" className="mb-4 p-4 bg-gray-50 rounded-lg">
        <div>
          {toolbar.title && (
            <Text strong className="text-lg">
              {toolbar.title}
            </Text>
          )}
          {hasSelection && (
            <Badge count={selectedRows.length} className="ml-2">
              <Text type="secondary">已选择</Text>
            </Badge>
          )}
        </div>
        
        <Space>
          {/* 全局搜索 */}
          {toolbar.showGlobalFilter && (
            <Input
              placeholder="搜索..."
              prefix={<SearchOutlined />}
              value={filtering?.globalFilter || localGlobalFilter}
              onChange={(e) => {
                const value = e.target.value
                filtering?.onGlobalFilterChange?.(value) || setLocalGlobalFilter(value)
              }}
              style={{ width: 200 }}
              allowClear
            />
          )}
          
          {/* 列可见性控制 */}
          {toolbar.showColumnVisibility && (
            <Dropdown
              menu={{
                items: table.getAllLeafColumns().map(column => ({
                  key: column.id,
                  label: (
                    <Flex justify="space-between" align="center">
                      <span>{column.columnDef.header as string}</span>
                      {column.getIsVisible() ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                    </Flex>
                  ),
                  onClick: () => column.toggleVisibility(),
                })),
              }}
              trigger={['click']}
            >
              <Button icon={<SettingOutlined />}>
                列设置
              </Button>
            </Dropdown>
          )}
          
          {/* 导出功能 */}
          {toolbar.showExport && (
            <Button
              icon={<DownloadOutlined />}
              onClick={() => onExport?.(data)}
            >
              导出
            </Button>
          )}
          
          {/* 自定义操作 */}
          {toolbar.customActions}
        </Space>
      </Flex>
    )
  }, [toolbar, table, data, filtering, localGlobalFilter, onExport])
  
  // ============================================================
  // 表格头部组件
  // ============================================================
  
  const renderTableHeader = useCallback(() => (
    <TableHeader>
      {table.getHeaderGroups().map((headerGroup) => (
        <TableRow key={headerGroup.id}>
          {headerGroup.headers.map((header) => (
            <TableHead 
              key={header.id}
              style={{ width: header.getSize() }}
              className="select-none"
            >
              {header.isPlaceholder ? null : (
                <div className="flex items-center space-x-2">
                  {/* 列标题 */}
                  <div
                    className={`flex items-center space-x-1 ${
                      header.column.getCanSort() ? 'cursor-pointer hover:bg-gray-100 p-1 rounded' : ''
                    }`}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    
                    {/* 排序指示器 */}
                    {header.column.getCanSort() && (
                      <span className="text-gray-400">
                        {{
                          asc: <SortAscendingOutlined />,
                          desc: <SortDescendingOutlined />,
                        }[header.column.getIsSorted() as string] ?? (
                          <div className="w-4 h-4" />
                        )}
                      </span>
                    )}
                  </div>
                  
                  {/* 列过滤 */}
                  {header.column.getCanFilter() && (
                    <FilterOutlined 
                      className="text-gray-400 cursor-pointer hover:text-blue-500"
                      onClick={(e) => {
                        e.stopPropagation()
                        // 触发列过滤弹窗
                      }}
                    />
                  )}
                </div>
              )}
            </TableHead>
          ))}
        </TableRow>
      ))}
    </TableHeader>
  ), [table])
  
  // ============================================================
  // 表格行组件
  // ============================================================
  
  const renderTableRow = useCallback((row: any, index: number) => (
    <TableRow 
      key={row.id}
      className={`
        ${striped && index % 2 === 0 ? 'bg-gray-50' : ''}
        ${row.getIsSelected() ? 'bg-blue-50 border-blue-200' : ''}
        ${onRowClick ? 'cursor-pointer hover:bg-gray-100' : ''}
      `}
      onClick={() => onRowClick?.(row.original)}
      onDoubleClick={() => onRowDoubleClick?.(row.original)}
    >
      {row.getVisibleCells().map((cell: any) => (
        <TableCell key={cell.id}>
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </TableCell>
      ))}
    </TableRow>
  ), [striped, onRowClick, onRowDoubleClick])
  
  // ============================================================
  // 虚拟化表格体
  // ============================================================
  
  const renderVirtualizedTableBody = useCallback(() => {
    const rows = table.getRowModel().rows
    
    if (virtualization?.enabled && rows.length > 100) {
      return (
        <TableBody>
          <TableRow>
            <TableCell colSpan={columns.length} className="p-0">
              <Virtuoso
                style={{ height: '400px' }}
                totalCount={rows.length}
                estimateSize={() => virtualization.estimateSize || 50}
                itemContent={(index) => renderTableRow(rows[index], index)}
              />
            </TableCell>
          </TableRow>
        </TableBody>
      )
    }
    
    return (
      <TableBody>
        {rows.map((row, index) => renderTableRow(row, index))}
      </TableBody>
    )
  }, [table, virtualization, columns.length, renderTableRow])
  
  // ============================================================
  // 分页组件
  // ============================================================
  
  const renderPagination = useCallback(() => {
    if (tableOptions.enablePagination === false) return null
    
    const pageSize = pagination?.pageSize || localPagination.pageSize
    const pageIndex = pagination?.pageIndex || localPagination.pageIndex
    const total = pagination?.total || table.getFilteredRowModel().rows.length
    
    return (
      <Flex justify="space-between" align="center" className="mt-4">
        <div>
          <Text type="secondary">
            显示 {pageIndex * pageSize + 1} 到 {Math.min((pageIndex + 1) * pageSize, total)} 条，
            共 {total} 条记录
          </Text>
        </div>
        
        <Space>
          <Select
            value={pageSize}
            onChange={(value) => {
              pagination?.onChange?.(0, value) || 
              setLocalPagination(prev => ({ ...prev, pageIndex: 0, pageSize: value }))
            }}
            options={[
              { label: '10 条/页', value: 10 },
              { label: '20 条/页', value: 20 },
              { label: '50 条/页', value: 50 },
              { label: '100 条/页', value: 100 },
            ]}
          />
          
          <Pagination
            current={pageIndex + 1}
            pageSize={pageSize}
            total={total}
            showSizeChanger={false}
            showQuickJumper
            onChange={(page, size) => {
              pagination?.onChange?.(page - 1, size) ||
              setLocalPagination(prev => ({ ...prev, pageIndex: page - 1, pageSize: size }))
            }}
          />
        </Space>
      </Flex>
    )
  }, [pagination, localPagination, tableOptions.enablePagination, table])
  
  // ============================================================
  // 渲染
  // ============================================================
  
  if (error) {
    return (
      <div className="text-center py-8">
        <Text type="danger">加载数据时出现错误: {error.message}</Text>
      </div>
    )
  }
  
  if (!loading && data.length === 0) {
    return (
      <div className="text-center py-8">
        <Empty description="暂无数据" />
      </div>
    )
  }
  
  return (
    <div className={`data-table ${className}`}>
      {renderToolbar()}
      
      <Spin spinning={loading}>
        <Table
          className={`
            ${bordered ? 'border rounded-lg' : ''}
            ${size === 'small' ? 'text-sm' : size === 'large' ? 'text-lg' : ''}
          `}
        >
          {renderTableHeader()}
          {renderVirtualizedTableBody()}
        </Table>
      </Spin>
      
      {renderPagination()}
    </div>
  )
}

// ============================================================
// 导出默认配置
// ============================================================

export const defaultTableOptions = {
  enableGlobalFilter: true,
  enableColumnFilters: true,
  enableSorting: true,
  enableMultiSort: true,
  enableColumnResizing: false,
  enableRowSelection: false,
  enablePagination: true,
}

export const defaultToolbarConfig = {
  showGlobalFilter: true,
  showColumnVisibility: true,
  showExport: true,
}