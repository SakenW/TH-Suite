/**
 * 完整虚拟化数据表格组件 - 终极性能优化版本
 * 支持1万+条数据的60fps流畅渲染
 */

import React, { useMemo, useCallback, forwardRef, useImperativeHandle, useRef, useState } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  useReactTable,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  RowSelectionState,
  OnChangeFn,
} from '@tanstack/react-table'
import { Card, Spin, Empty, Button, Input, Space, Typography, Tooltip, Dropdown, Checkbox } from 'antd'
import { 
  SearchOutlined,
  SettingOutlined,
  DownloadOutlined,
  VerticalAlignTopOutlined,
  VerticalAlignBottomOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  DashboardOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useVirtualized, TABLE_ROW_CONFIG } from './useVirtualizer'
import { motion, AnimatePresence } from 'framer-motion'

const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

export interface VirtualizedDataTableProps<TData = any> {
  // 核心数据
  data: TData[]
  columns: ColumnDef<TData, any>[]
  
  // 基础配置
  height?: number | string
  width?: number | string
  className?: string
  
  // 虚拟化配置
  rowHeight?: number | ((row: TData, index: number) => number)
  overscan?: number
  
  // 表格功能开关
  enableSorting?: boolean
  enableFiltering?: boolean
  enableColumnVisibility?: boolean
  enableRowSelection?: boolean
  enableGlobalFilter?: boolean
  
  // 状态管理（受控模式）
  sorting?: SortingState
  onSortingChange?: OnChangeFn<SortingState>
  columnFilters?: ColumnFiltersState
  onColumnFiltersChange?: OnChangeFn<ColumnFiltersState>
  columnVisibility?: VisibilityState
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>
  rowSelection?: RowSelectionState
  onRowSelectionChange?: OnChangeFn<RowSelectionState>
  globalFilter?: string
  onGlobalFilterChange?: OnChangeFn<string>
  
  // UI状态
  loading?: boolean
  error?: string | null
  emptyText?: string
  
  // 工具栏配置
  showToolbar?: boolean
  toolbarTitle?: string
  toolbarExtra?: React.ReactNode
  showGlobalFilter?: boolean
  showColumnVisibility?: boolean
  showExport?: boolean
  showRefresh?: boolean
  
  // 性能监控
  showPerformanceStats?: boolean
  
  // 事件处理
  onRowClick?: (row: TData, index: number) => void
  onRowDoubleClick?: (row: TData, index: number) => void
  onExport?: (data: TData[]) => void
  onRefresh?: () => void
  
  // 样式配置
  striped?: boolean
  bordered?: boolean
  size?: 'small' | 'middle' | 'large'
  headerHeight?: number
  
  // 响应式支持
  responsive?: boolean
  
  // 高级功能
  stickyHeader?: boolean
  resizableColumns?: boolean
  
  // 选中功能
  getRowId?: (row: TData, index: number) => string
  highlightedRowId?: string
  onHighlightRow?: (rowId: string, row: TData) => void
}

export interface VirtualizedDataTableRef<TData = any> {
  // 滚动控制
  scrollToRow: (rowIndex: number, align?: 'start' | 'center' | 'end') => void
  scrollToTop: () => void
  scrollToBottom: () => void
  
  // 数据访问
  getSelectedRows: () => TData[]
  getAllRows: () => TData[]
  getFilteredRows: () => TData[]
  
  // 状态控制
  clearSelection: () => void
  selectAll: () => void
  clearFilters: () => void
  
  // 性能监控
  getStats: () => any
  
  // 导出功能
  exportData: (format?: 'json' | 'csv') => string
}

// ============================================================
// 主组件
// ============================================================

export const VirtualizedDataTable = forwardRef<VirtualizedDataTableRef, VirtualizedDataTableProps>(({
  data,
  columns,
  height = 600,
  width = '100%',
  className = '',
  rowHeight = 48,
  overscan = 10,
  enableSorting = true,
  enableFiltering = true,
  enableColumnVisibility = true,
  enableRowSelection = false,
  enableGlobalFilter = true,
  sorting: externalSorting,
  onSortingChange: externalOnSortingChange,
  columnFilters: externalColumnFilters,
  onColumnFiltersChange: externalOnColumnFiltersChange,
  columnVisibility: externalColumnVisibility,
  onColumnVisibilityChange: externalOnColumnVisibilityChange,
  rowSelection: externalRowSelection,
  onRowSelectionChange: externalOnRowSelectionChange,
  globalFilter: externalGlobalFilter,
  onGlobalFilterChange: externalOnGlobalFilterChange,
  loading = false,
  error = null,
  emptyText = '暂无数据',
  showToolbar = true,
  toolbarTitle,
  toolbarExtra,
  showGlobalFilter = true,
  showColumnVisibility = true,
  showExport = true,
  showRefresh = false,
  showPerformanceStats = false,
  onRowClick,
  onRowDoubleClick,
  onExport,
  onRefresh,
  striped = true,
  bordered = true,
  size = 'middle',
  headerHeight = 48,
  responsive = true,
  stickyHeader = true,
  resizableColumns = false,
  getRowId,
  highlightedRowId,
  onHighlightRow,
}, ref) => {
  
  // ============================================================
  // 内部状态管理
  // ============================================================
  
  const [internalSorting, setInternalSorting] = useState<SortingState>([])
  const [internalColumnFilters, setInternalColumnFilters] = useState<ColumnFiltersState>([])
  const [internalColumnVisibility, setInternalColumnVisibility] = useState<VisibilityState>({})
  const [internalRowSelection, setInternalRowSelection] = useState<RowSelectionState>({})
  const [internalGlobalFilter, setInternalGlobalFilter] = useState('')
  
  // 状态管理逻辑 - 支持受控/非受控模式
  const sorting = externalSorting ?? internalSorting
  const onSortingChange = externalOnSortingChange ?? setInternalSorting
  const columnFilters = externalColumnFilters ?? internalColumnFilters
  const onColumnFiltersChange = externalOnColumnFiltersChange ?? setInternalColumnFilters
  const columnVisibility = externalColumnVisibility ?? internalColumnVisibility
  const onColumnVisibilityChange = externalOnColumnVisibilityChange ?? setInternalColumnVisibility
  const rowSelection = externalRowSelection ?? internalRowSelection
  const onRowSelectionChange = externalOnRowSelectionChange ?? setInternalRowSelection
  const globalFilter = externalGlobalFilter ?? internalGlobalFilter
  const onGlobalFilterChange = externalOnGlobalFilterChange ?? setInternalGlobalFilter
  
  // ============================================================
  // 行高计算
  // ============================================================
  
  const calculateRowHeight = useCallback((index: number) => {
    if (typeof rowHeight === 'function') {
      return rowHeight(data[index], index)
    }
    return rowHeight
  }, [rowHeight, data])
  
  // ============================================================
  // TanStack Table 配置
  // ============================================================
  
  const table = useReactTable({
    data,
    columns,
    
    // 核心功能
    getCoreRowModel: getCoreRowModel(),
    
    // 排序
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    enableSorting,
    enableMultiSort: true,
    state: { sorting },
    onSortingChange,
    
    // 过滤
    getFilteredRowModel: (enableFiltering || enableGlobalFilter) ? getFilteredRowModel() : undefined,
    enableFilters: enableFiltering,
    enableGlobalFilter,
    globalFilterFn: 'includesString',
    state: { 
      ...table?.initialState,
      columnFilters,
      globalFilter,
    },
    onColumnFiltersChange,
    onGlobalFilterChange,
    
    // 列可见性
    enableHiding: enableColumnVisibility,
    state: {
      ...table?.initialState,
      columnVisibility,
    },
    onColumnVisibilityChange,
    
    // 行选择
    enableRowSelection,
    enableMultiRowSelection: true,
    state: {
      ...table?.initialState,
      rowSelection,
    },
    onRowSelectionChange,
    getRowId: getRowId ? (row, index) => getRowId(row, index) : undefined,
    
    debugTable: (import.meta as any).env?.MODE === 'development',
  })
  
  // 获取处理后的行数据
  const rows = useMemo(() => table.getRowModel().rows, [table])
  
  // ============================================================
  // 虚拟化配置
  // ============================================================
  
  const virtualizerConfig = useMemo(() => ({
    ...TABLE_ROW_CONFIG,
    data: rows,
    estimateSize: calculateRowHeight,
    overscan,
    getItemKey: (index: number) => rows[index]?.id ?? `row-${index}`,
    responsive: responsive ? {
      breakpoints: { xs: 0, sm: 576, md: 768, lg: 992, xl: 1200 },
      estimateSizes: { xs: 36, sm: 40, md: 48, lg: 56, xl: 64 },
    } : undefined,
  }), [rows, calculateRowHeight, overscan, responsive])
  
  // 使用虚拟化Hook
  const {
    virtualizer,
    virtualItems,
    parentRef,
    scrollToIndex,
    scrollToTop,
    scrollToBottom,
    totalSize,
    isScrolling,
    stats,
  } = useVirtualized(virtualizerConfig)
  
  // ============================================================
  // 暴露的方法
  // ============================================================
  
  useImperativeHandle(ref, () => ({
    scrollToRow: (rowIndex: number, align: 'start' | 'center' | 'end' = 'start') => {
      scrollToIndex(rowIndex, { align })
    },
    scrollToTop,
    scrollToBottom,
    getSelectedRows: () => table.getSelectedRowModel().rows.map(row => row.original),
    getAllRows: () => data,
    getFilteredRows: () => table.getFilteredRowModel().rows.map(row => row.original),
    clearSelection: () => table.resetRowSelection(),
    selectAll: () => table.toggleAllRowsSelected(true),
    clearFilters: () => {
      table.resetColumnFilters()
      table.resetGlobalFilter()
    },
    getStats: () => stats,
    exportData: (format = 'json') => {
      const exportData = table.getFilteredRowModel().rows.map(row => row.original)
      if (format === 'csv') {
        // 简单的CSV导出实现
        const headers = table.getAllLeafColumns().map(col => col.columnDef.header as string).join(',')
        const csvData = exportData.map(row => 
          table.getAllLeafColumns().map(col => 
            String(row[col.id as keyof typeof row] || '')
          ).join(',')
        ).join('\n')
        return headers + '\n' + csvData
      }
      return JSON.stringify(exportData, null, 2)
    },
  }), [table, data, stats, scrollToIndex, scrollToTop, scrollToBottom])
  
  // ============================================================
  // 事件处理
  // ============================================================
  
  const handleRowClick = useCallback((row: any, index: number, event: React.MouseEvent) => {
    // 处理行选择
    if (enableRowSelection && !event.target?.closest('.ant-checkbox, button')) {
      row.toggleSelected()
    }
    
    // 处理高亮
    if (onHighlightRow && getRowId) {
      const rowId = getRowId(row.original, index)
      onHighlightRow(rowId, row.original)
    }
    
    onRowClick?.(row.original, index)
  }, [enableRowSelection, onHighlightRow, getRowId, onRowClick])
  
  const handleRowDoubleClick = useCallback((row: any, index: number) => {
    onRowDoubleClick?.(row.original, index)
  }, [onRowDoubleClick])
  
  // ============================================================
  // 渲染函数
  // ============================================================
  
  const renderToolbar = useCallback(() => {
    if (!showToolbar) return null
    
    const selectedRows = table.getSelectedRowModel().rows
    const hasSelection = selectedRows.length > 0
    
    return (
      <div className="virtualized-data-table-toolbar" style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '12px 16px',
        borderBottom: bordered ? '1px solid #f0f0f0' : undefined,
        backgroundColor: '#fafafa',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {toolbarTitle && (
            <Text strong style={{ fontSize: 16 }}>
              {toolbarTitle}
            </Text>
          )}
          {hasSelection && (
            <Text type="secondary">
              已选择 {selectedRows.length} 行
            </Text>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            显示 {rows.length} / {data.length} 行
          </Text>
        </div>
        
        <Space>
          {/* 全局搜索 */}
          {showGlobalFilter && enableGlobalFilter && (
            <Input
              placeholder="搜索..."
              prefix={<SearchOutlined />}
              value={globalFilter}
              onChange={(e) => onGlobalFilterChange?.(e.target.value)}
              style={{ width: 200 }}
              allowClear
              size={size}
            />
          )}
          
          {/* 自定义工具栏项目 */}
          {toolbarExtra}
          
          {/* 导出 */}
          {showExport && onExport && (
            <Tooltip title="导出数据">
              <Button
                icon={<DownloadOutlined />}
                onClick={() => onExport(table.getFilteredRowModel().rows.map(row => row.original))}
                size={size}
              >
                导出
              </Button>
            </Tooltip>
          )}
          
          {/* 刷新 */}
          {showRefresh && onRefresh && (
            <Tooltip title="刷新数据">
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
                size={size}
              />
            </Tooltip>
          )}
          
          {/* 列可见性设置 */}
          {showColumnVisibility && enableColumnVisibility && (
            <Dropdown
              menu={{
                items: table.getAllLeafColumns().map(column => ({
                  key: column.id,
                  label: (
                    <Checkbox
                      checked={column.getIsVisible()}
                      onChange={(e) => column.toggleVisibility(e.target.checked)}
                    >
                      {column.columnDef.header as string}
                    </Checkbox>
                  ),
                })),
              }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Tooltip title="列设置">
                <Button icon={<SettingOutlined />} size={size} />
              </Tooltip>
            </Dropdown>
          )}
          
          {/* 滚动控制 */}
          <Space.Compact>
            <Tooltip title="回到顶部">
              <Button 
                size={size}
                icon={<VerticalAlignTopOutlined />} 
                onClick={scrollToTop} 
              />
            </Tooltip>
            <Tooltip title="到底部">
              <Button 
                size={size}
                icon={<VerticalAlignBottomOutlined />} 
                onClick={scrollToBottom} 
              />
            </Tooltip>
          </Space.Compact>
          
          {/* 性能监控 */}
          {showPerformanceStats && (
            <Tooltip title={`渲染: ${stats.renderedCount}/${stats.totalCount} | 缓存命中率: ${stats.cacheHitRate.toFixed(1)}%`}>
              <Button size={size} icon={<DashboardOutlined />} />
            </Tooltip>
          )}
        </Space>
      </div>
    )
  }, [showToolbar, toolbarTitle, toolbarExtra, table, bordered, showGlobalFilter, enableGlobalFilter, globalFilter, onGlobalFilterChange, size, showExport, onExport, showRefresh, onRefresh, loading, showColumnVisibility, enableColumnVisibility, scrollToTop, scrollToBottom, showPerformanceStats, stats, rows.length, data.length])
  
  const renderTableHeader = useCallback(() => {
    return (
      <div 
        className="virtualized-data-table-header"
        style={{
          display: 'flex',
          position: stickyHeader ? 'sticky' : 'relative',
          top: 0,
          zIndex: 10,
          backgroundColor: '#fafafa',
          borderBottom: bordered ? '2px solid #f0f0f0' : undefined,
          height: headerHeight,
        }}
      >
        {table.getHeaderGroups()[0]?.headers.map((header) => (
          <div
            key={header.id}
            className="virtualized-data-table-header-cell"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              width: header.getSize(),
              minWidth: header.column.columnDef.minSize ?? 100,
              maxWidth: header.column.columnDef.maxSize,
              borderRight: bordered ? '1px solid #f0f0f0' : undefined,
              cursor: header.column.getCanSort() ? 'pointer' : 'default',
              userSelect: 'none',
              fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14,
              fontWeight: 600,
            }}
            onClick={header.column.getToggleSortingHandler()}
          >
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8 }}>
              {/* 行选择列 */}
              {enableRowSelection && header.column.id === 'select' && (
                <Checkbox
                  checked={table.getIsAllRowsSelected()}
                  indeterminate={table.getIsSomeRowsSelected()}
                  onChange={table.getToggleAllRowsSelectedHandler()}
                />
              )}
              
              {/* 列标题 */}
              {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
            </div>
            
            {/* 排序指示器 */}
            {header.column.getCanSort() && (
              <div style={{ marginLeft: 4, opacity: 0.6 }}>
                {{
                  asc: <SortAscendingOutlined />,
                  desc: <SortDescendingOutlined />,
                }[header.column.getIsSorted() as string] ?? null}
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }, [table, stickyHeader, bordered, headerHeight, size, enableRowSelection])
  
  // ============================================================
  // 错误和空状态处理
  // ============================================================
  
  if (error) {
    return (
      <Card className={className} style={{ height, width }}>
        {renderToolbar()}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Text type="danger">加载数据时出现错误: {error}</Text>
        </div>
      </Card>
    )
  }
  
  if (!loading && data.length === 0) {
    return (
      <Card className={className} style={{ height, width }}>
        {renderToolbar()}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Empty description={emptyText} />
        </div>
      </Card>
    )
  }
  
  // ============================================================
  // 主渲染
  // ============================================================
  
  return (
    <Card
      className={`virtualized-data-table ${className}`}
      style={{ height, width }}
      bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      {renderToolbar()}
      
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <Spin spinning={loading}>
          <div className="virtualized-data-table-container" style={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            border: bordered ? '1px solid #f0f0f0' : undefined,
            borderTop: 'none',
          }}>
            {/* 表头 */}
            {renderTableHeader()}
            
            {/* 虚拟化表体 */}
            <div
              ref={parentRef}
              style={{
                flex: 1,
                overflow: 'auto',
              }}
            >
              <div style={{ 
                height: `${totalSize}px`, 
                width: '100%', 
                position: 'relative',
                paddingTop: stickyHeader ? 0 : headerHeight,
              }}>
                <AnimatePresence>
                  {virtualItems.map((virtualItem) => {
                    const row = virtualItem.item
                    const isSelected = row.getIsSelected()
                    const isHighlighted = highlightedRowId && getRowId ? 
                      getRowId(row.original, virtualItem.index) === highlightedRowId : false
                    
                    return (
                      <motion.div
                        key={virtualItem.key}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.1 }}
                        data-index={virtualItem.index}
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: `${virtualItem.size}px`,
                          transform: `translateY(${virtualItem.start}px)`,
                          display: 'flex',
                          alignItems: 'center',
                          borderBottom: bordered ? '1px solid #f0f0f0' : undefined,
                          backgroundColor: isSelected ? '#e6f7ff' : 
                                         isHighlighted ? '#fff7e6' :
                                         striped && virtualItem.index % 2 === 1 ? '#fafafa' : 'transparent',
                          cursor: onRowClick ? 'pointer' : 'default',
                          transition: isScrolling ? 'none' : 'background-color 0.2s',
                        }}
                        onClick={(e) => handleRowClick(row, virtualItem.index, e)}
                        onDoubleClick={() => handleRowDoubleClick(row, virtualItem.index)}
                      >
                        {row.getVisibleCells().map(cell => (
                          <div
                            key={cell.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              padding: size === 'small' ? '4px 8px' : size === 'large' ? '12px 16px' : '8px 12px',
                              width: cell.column.getSize(),
                              minWidth: cell.column.columnDef.minSize ?? 100,
                              maxWidth: cell.column.columnDef.maxSize,
                              borderRight: bordered ? '1px solid #f0f0f0' : undefined,
                              fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </div>
                        ))}
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </Spin>
        
        {/* 滚动指示器 */}
        <AnimatePresence>
          {isScrolling && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              style={{
                position: 'absolute',
                top: 16,
                right: 16,
                background: 'rgba(0,0,0,0.8)',
                color: 'white',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 12,
                pointerEvents: 'none',
                zIndex: 1000,
              }}
            >
              滚动中... ({stats.visibleRange[0]}-{stats.visibleRange[1]})
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  )
})

VirtualizedDataTable.displayName = 'VirtualizedDataTable'

export default VirtualizedDataTable