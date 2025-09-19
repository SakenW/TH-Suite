/**
 * 虚拟化表格组件 - 集成@tanstack/react-virtual和@tanstack/react-table
 * 支持大数据量表格的高性能渲染
 */

import React, { useMemo, useCallback, forwardRef, useImperativeHandle } from 'react'
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
  OnChangeFn,
} from '@tanstack/react-table'
import { Card, Spin, Empty, Button, Input, Space, Typography, Tooltip, Checkbox } from 'antd'
import { 
  SearchOutlined,
  SettingOutlined,
  DownloadOutlined,
  VerticalAlignTopOutlined,
  VerticalAlignBottomOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  DashboardOutlined
} from '@ant-design/icons'
import { useVirtualized, type VirtualizerConfig } from './useVirtualizer'
import { motion, AnimatePresence } from 'framer-motion'

const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

export interface VirtualizedTableProps<T = any> {
  // 数据和列定义
  data: T[]
  columns: ColumnDef<T, any>[]
  
  // 基础配置
  height?: number | string
  width?: number | string
  className?: string
  
  // 虚拟化配置
  rowHeight?: number | ((row: T, index: number) => number)
  overscan?: number
  
  // 表格功能
  enableSorting?: boolean
  enableFiltering?: boolean
  enableColumnVisibility?: boolean
  enableRowSelection?: boolean
  enableGlobalFilter?: boolean
  
  // 状态管理（可选，用于受控模式）
  sorting?: {
    state: SortingState
    onChange: OnChangeFn<SortingState>
  }
  columnFilters?: {
    state: ColumnFiltersState
    onChange: OnChangeFn<ColumnFiltersState>
  }
  columnVisibility?: {
    state: VisibilityState
    onChange: OnChangeFn<VisibilityState>
  }
  rowSelection?: {
    state: Record<string, boolean>
    onChange: OnChangeFn<Record<string, boolean>>
  }
  globalFilter?: {
    state: string
    onChange: OnChangeFn<string>
  }
  
  // 加载和错误状态
  loading?: boolean
  error?: string | null
  emptyText?: string
  
  // 工具栏配置
  showToolbar?: boolean
  toolbarTitle?: string
  toolbarExtra?: React.ReactNode
  
  // 性能监控
  showPerformanceStats?: boolean
  
  // 事件
  onRowClick?: (row: T, index: number) => void
  onRowDoubleClick?: (row: T, index: number) => void
  onExport?: (data: T[]) => void
  
  // 样式
  striped?: boolean
  bordered?: boolean
  size?: 'small' | 'middle' | 'large'
  
  // 响应式
  responsive?: boolean
}

export interface VirtualizedTableRef<T = any> {
  scrollToRow: (rowIndex: number, align?: 'start' | 'center' | 'end') => void
  scrollToTop: () => void
  scrollToBottom: () => void
  getSelectedRows: () => T[]
  clearSelection: () => void
  getStats: () => any
  exportData: () => T[]
}

// ============================================================
// 主组件
// ============================================================

export const VirtualizedTable = forwardRef<VirtualizedTableRef, VirtualizedTableProps>(({
  data,
  columns,
  height = 400,
  width = '100%',
  className = '',
  rowHeight = 56,
  overscan = 10,
  enableSorting = true,
  enableFiltering = true,
  enableColumnVisibility = true,
  enableRowSelection = false,
  enableGlobalFilter = true,
  sorting,
  columnFilters,
  columnVisibility,
  rowSelection,
  globalFilter,
  loading = false,
  error = null,
  emptyText = '暂无数据',
  showToolbar = true,
  toolbarTitle,
  toolbarExtra,
  showPerformanceStats = false,
  onRowClick,
  onRowDoubleClick,
  onExport,
  striped = true,
  bordered = true,
  size = 'middle',
  responsive = true,
}, ref) => {
  
  // 内部状态管理（当没有外部状态时使用）
  const [internalSorting, setInternalSorting] = React.useState<SortingState>([])
  const [internalColumnFilters, setInternalColumnFilters] = React.useState<ColumnFiltersState>([])
  const [internalColumnVisibility, setInternalColumnVisibility] = React.useState<VisibilityState>({})
  const [internalRowSelection, setInternalRowSelection] = React.useState<Record<string, boolean>>({})
  const [internalGlobalFilter, setInternalGlobalFilter] = React.useState('')
  
  // 行高计算函数
  const calculateRowHeight = useCallback((index: number) => {
    if (typeof rowHeight === 'function') {
      return rowHeight(data[index], index)
    }
    return rowHeight
  }, [rowHeight, data])
  
  // TanStack Table配置
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    
    // 排序
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    enableSorting,
    state: {
      sorting: sorting?.state ?? internalSorting,
    },
    onSortingChange: sorting?.onChange ?? setInternalSorting,
    
    // 过滤
    getFilteredRowModel: enableFiltering ? getFilteredRowModel() : undefined,
    enableFilters: enableFiltering,
    enableGlobalFilter,
    globalFilterFn: 'includesString',
    state: {
      ...table?.initialState,
      columnFilters: columnFilters?.state ?? internalColumnFilters,
      globalFilter: globalFilter?.state ?? internalGlobalFilter,
    },
    onColumnFiltersChange: columnFilters?.onChange ?? setInternalColumnFilters,
    onGlobalFilterChange: globalFilter?.onChange ?? setInternalGlobalFilter,
    
    // 列可见性
    enableHiding: enableColumnVisibility,
    state: {
      ...table?.initialState,
      columnVisibility: columnVisibility?.state ?? internalColumnVisibility,
    },
    onColumnVisibilityChange: columnVisibility?.onChange ?? setInternalColumnVisibility,
    
    // 行选择
    enableRowSelection,
    state: {
      ...table?.initialState,
      rowSelection: rowSelection?.state ?? internalRowSelection,
    },
    onRowSelectionChange: rowSelection?.onChange ?? setInternalRowSelection,
    
    debugTable: process.env.NODE_ENV === 'development',
  })
  
  // 获取处理后的数据行
  const rows = useMemo(() => table.getRowModel().rows, [table])
  
  // 虚拟化配置
  const virtualizerConfig = useMemo((): VirtualizerConfig => ({
    data: rows,
    estimateSize: calculateRowHeight,
    overscan,
    enableMeasureCache: true,
    cacheSize: 300,
    getItemKey: (index) => rows[index]?.id ?? index,
    responsive: responsive ? {
      breakpoints: { xs: 0, sm: 576, md: 768, lg: 992, xl: 1200 },
      estimateSizes: { xs: 40, sm: 48, md: 56, lg: 64, xl: 72 },
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
  
  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    scrollToRow: (rowIndex: number, align: 'start' | 'center' | 'end' = 'start') => {
      scrollToIndex(rowIndex, { align })
    },
    scrollToTop,
    scrollToBottom,
    getSelectedRows: () => {
      return table.getSelectedRowModel().rows.map(row => row.original)
    },
    clearSelection: () => {
      table.resetRowSelection()
    },
    getStats: () => stats,
    exportData: () => rows.map(row => row.original),
  }), [scrollToIndex, scrollToTop, scrollToBottom, table, stats, rows])
  
  // 处理行点击
  const handleRowClick = useCallback((row: any, index: number, event: React.MouseEvent) => {
    // 处理行选择
    if (enableRowSelection && !event.target?.closest('.ant-checkbox, button')) {
      row.toggleSelected()
    }
    
    onRowClick?.(row.original, index)
  }, [enableRowSelection, onRowClick])
  
  // 处理行双击
  const handleRowDoubleClick = useCallback((row: any, index: number) => {
    onRowDoubleClick?.(row.original, index)
  }, [onRowDoubleClick])
  
  // 获取行样式
  const getRowClassName = useCallback((row: any, index: number) => {
    let className = 'virtualized-table-row'
    
    if (striped && index % 2 === 1) className += ' striped'
    if (row.getIsSelected()) className += ' selected'
    if (onRowClick) className += ' clickable'
    
    return className
  }, [striped, onRowClick])
  
  // 工具栏渲染
  const renderToolbar = useCallback(() => {
    if (!showToolbar) return null
    
    const selectedRows = table.getSelectedRowModel().rows
    const hasSelection = selectedRows.length > 0
    
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '12px 16px',
        borderBottom: '1px solid #f0f0f0',
        backgroundColor: '#fafafa',
      }}>
        <div>
          {toolbarTitle && (
            <Text strong style={{ marginRight: 16 }}>
              {toolbarTitle}
            </Text>
          )}
          {hasSelection && (
            <Text type="secondary">
              已选择 {selectedRows.length} 行
            </Text>
          )}
        </div>
        
        <Space>
          {/* 全局搜索 */}
          {enableGlobalFilter && (
            <Input
              placeholder="搜索..."
              prefix={<SearchOutlined />}
              value={globalFilter?.state ?? internalGlobalFilter}
              onChange={(e) => {
                const value = e.target.value
                globalFilter?.onChange?.(value) || setInternalGlobalFilter(value)
              }}
              style={{ width: 200 }}
              allowClear
            />
          )}
          
          {toolbarExtra}
          
          {/* 导出 */}
          {onExport && (
            <Tooltip title="导出数据">
              <Button
                icon={<DownloadOutlined />}
                onClick={() => onExport(rows.map(row => row.original))}
              >
                导出
              </Button>
            </Tooltip>
          )}
          
          {/* 列设置 */}
          {enableColumnVisibility && (
            <Tooltip title="列设置">
              <Button icon={<SettingOutlined />} />
            </Tooltip>
          )}
          
          {/* 滚动控制 */}
          <Tooltip title="回到顶部">
            <Button size="small" icon={<VerticalAlignTopOutlined />} onClick={scrollToTop} />
          </Tooltip>
          <Tooltip title="到底部">
            <Button size="small" icon={<VerticalAlignBottomOutlined />} onClick={scrollToBottom} />
          </Tooltip>
          
          {/* 性能监控 */}
          {showPerformanceStats && (
            <Tooltip title={`可见行: ${stats.visibleRange[0]}-${stats.visibleRange[1]} / ${stats.totalCount}`}>
              <Button size="small" icon={<DashboardOutlined />} />
            </Tooltip>
          )}
        </Space>
      </div>
    )
  }, [showToolbar, toolbarTitle, toolbarExtra, table, enableGlobalFilter, globalFilter, internalGlobalFilter, onExport, rows, enableColumnVisibility, scrollToTop, scrollToBottom, showPerformanceStats, stats])
  
  // 表头渲染
  const renderTableHeader = useCallback(() => {
    return table.getHeaderGroups().map(headerGroup => (
      <div key={headerGroup.id} className="virtualized-table-header-row" style={{
        display: 'flex',
        borderBottom: '2px solid #f0f0f0',
        backgroundColor: '#fafafa',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}>
        {headerGroup.headers.map(header => (
          <div
            key={header.id}
            className="virtualized-table-header-cell"
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px 16px',
              width: header.getSize(),
              minWidth: header.column.columnDef.minSize,
              maxWidth: header.column.columnDef.maxSize,
              borderRight: bordered ? '1px solid #f0f0f0' : undefined,
              cursor: header.column.getCanSort() ? 'pointer' : 'default',
              userSelect: 'none',
              fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14,
              fontWeight: 600,
            }}
            onClick={header.column.getToggleSortingHandler()}
          >
            <div style={{ flex: 1 }}>
              {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
            </div>
            
            {/* 排序指示器 */}
            {header.column.getCanSort() && (
              <div style={{ marginLeft: 8 }}>
                {{
                  asc: <SortAscendingOutlined />,
                  desc: <SortDescendingOutlined />,
                }[header.column.getIsSorted() as string] ?? null}
              </div>
            )}
            
            {/* 行选择全选 */}
            {enableRowSelection && header.column.id === 'select' && (
              <Checkbox
                checked={table.getIsAllRowsSelected()}
                indeterminate={table.getIsSomeRowsSelected()}
                onChange={table.getToggleAllRowsSelectedHandler()}
              />
            )}
          </div>
        ))}
      </div>
    ))
  }, [table, bordered, size, enableRowSelection])
  
  // 错误状态
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
  
  // 空数据状态
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
  
  return (
    <Card 
      className={`virtualized-table ${className}`}
      style={{ height, width }}
      bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      {renderToolbar()}
      
      <div style={{ flex: 1, position: 'relative' }}>
        <Spin spinning={loading}>
          <div className="virtualized-table-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* 表头 */}
            <div className="virtualized-table-header">
              {renderTableHeader()}
            </div>
            
            {/* 虚拟化表体 */}
            <div
              ref={parentRef}
              style={{
                flex: 1,
                overflow: 'auto',
                border: bordered ? '1px solid #f0f0f0' : undefined,
                borderTop: 'none',
              }}
            >
              <div style={{ height: `${totalSize}px`, width: '100%', position: 'relative' }}>
                <AnimatePresence>
                  {virtualItems.map((virtualItem) => {
                    const row = virtualItem.item
                    const isSelected = row.getIsSelected()
                    
                    return (
                      <motion.div
                        key={virtualItem.key}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        transition={{ duration: 0.15 }}
                        data-index={virtualItem.index}
                        className={getRowClassName(row, virtualItem.index)}
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
                          backgroundColor: isSelected ? '#e6f7ff' : striped && virtualItem.index % 2 === 1 ? '#fafafa' : 'transparent',
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
                              padding: '8px 16px',
                              width: cell.column.getSize(),
                              minWidth: cell.column.columnDef.minSize,
                              maxWidth: cell.column.columnDef.maxSize,
                              borderRight: bordered ? '1px solid #f0f0f0' : undefined,
                              fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14,
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
        {isScrolling && (
          <div 
            style={{
              position: 'absolute',
              top: 8,
              right: 8,
              background: 'rgba(0,0,0,0.7)',
              color: 'white',
              padding: '4px 8px',
              borderRadius: 4,
              fontSize: 12,
              pointerEvents: 'none',
              zIndex: 1000,
            }}
          >
            滚动中...
          </div>
        )}
      </div>
    </Card>
  )
})

VirtualizedTable.displayName = 'VirtualizedTable'

export default VirtualizedTable