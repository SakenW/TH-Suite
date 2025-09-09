/**
 * 虚拟化数据表格组件 - 性能优化版本
 * 使用虚拟滚动处理大量数据，提供更好的性能
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { FixedSizeList as List } from 'react-window'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  Paper,
  Checkbox,
  IconButton,
  Menu,
  MenuItem,
  Typography,
  Box,
  TextField,
  InputAdornment,
  Toolbar,
  Tooltip,
  LinearProgress,
} from '@mui/material'
import { useTheme, alpha } from '@mui/material/styles'
import {
  MoreVertical,
  Search,
  Download,
  RefreshCw as Refresh,
  Settings,
} from 'lucide-react'
import { TableColumn, TableAction } from './DataTable'

interface VirtualizedDataTableProps<T = any> {
  // 数据
  data: T[]
  columns: TableColumn<T>[]
  loading?: boolean
  error?: string
  
  // 虚拟化配置
  itemHeight?: number
  visibleRows?: number
  overscanCount?: number
  
  // 选择功能
  selectable?: boolean
  selectedRows?: T[]
  onSelectionChange?: (selected: T[]) => void
  getRowId?: (row: T) => string
  
  // 排序
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  onSort?: (column: string, order: 'asc' | 'desc') => void
  
  // 过滤
  globalFilter?: string
  onGlobalFilterChange?: (filter: string) => void
  
  // 行操作
  actions?: TableAction<T>[]
  rowActions?: TableAction<T>[]
  
  // 样式配置
  dense?: boolean
  stickyHeader?: boolean
  showHeader?: boolean
  showToolbar?: boolean
  title?: string
  subtitle?: string
  
  // 事件
  onRowClick?: (row: T) => void
  onRowDoubleClick?: (row: T) => void
  onRefresh?: () => void
  onExport?: () => void
}

interface VirtualRowProps {
  index: number
  style: React.CSSProperties
  data: {
    items: any[]
    columns: TableColumn[]
    selectedRowIds: Set<string>
    getRowId: (row: any) => string
    onSelectRow: (row: any, checked: boolean) => void
    onRowClick?: (row: any) => void
    onRowDoubleClick?: (row: any) => void
    rowActions: TableAction[]
    onActionMenuClick: (rowId: string, event: React.MouseEvent<HTMLElement>) => void
    selectable: boolean
  }
}

const VirtualRow = React.memo<VirtualRowProps>(({ index, style, data }) => {
  const {
    items,
    columns,
    selectedRowIds,
    getRowId,
    onSelectRow,
    onRowClick,
    onRowDoubleClick,
    rowActions,
    onActionMenuClick,
    selectable,
  } = data

  const row = items[index]
  const rowId = getRowId(row)
  const isSelected = selectedRowIds.has(rowId)

  return (
    <div style={style}>
      <TableRow
        hover
        selected={isSelected}
        onClick={() => onRowClick?.(row)}
        onDoubleClick={() => onRowDoubleClick?.(row)}
        sx={{
          cursor: onRowClick ? 'pointer' : 'default',
          display: 'flex',
          alignItems: 'center',
          width: '100%',
        }}
      >
        {selectable && (
          <TableCell 
            padding="checkbox"
            sx={{ display: 'flex', alignItems: 'center', width: '48px', minWidth: '48px' }}
          >
            <Checkbox
              color="primary"
              checked={isSelected}
              onChange={e => onSelectRow(row, e.target.checked)}
              onClick={e => e.stopPropagation()}
            />
          </TableCell>
        )}

        {columns.map((column, columnIndex) => {
          const value = row[column.id]
          const displayValue = column.render
            ? column.render(value, row, column)
            : column.format
              ? column.format(value)
              : value

          return (
            <TableCell 
              key={column.id as string} 
              align={column.align}
              sx={{
                display: 'flex',
                alignItems: 'center',
                width: column.width || 'auto',
                minWidth: column.minWidth || 120,
                maxWidth: column.maxWidth,
                flex: column.width ? 'none' : 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {displayValue}
            </TableCell>
          )
        })}

        {rowActions.length > 0 && (
          <TableCell 
            align="center"
            sx={{ display: 'flex', alignItems: 'center', width: '48px', minWidth: '48px' }}
          >
            <IconButton size="small" onClick={e => onActionMenuClick(rowId, e)}>
              <MoreVertical size={16} />
            </IconButton>
          </TableCell>
        )}
      </TableRow>
    </div>
  )
})

VirtualRow.displayName = 'VirtualRow'

export const VirtualizedDataTable = <T extends Record<string, any>>({
  data,
  columns: initialColumns,
  loading = false,
  error,
  itemHeight = 52,
  visibleRows = 10,
  overscanCount = 5,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  getRowId = row => row.id,
  sortBy,
  sortOrder = 'asc',
  onSort,
  globalFilter = '',
  onGlobalFilterChange,
  actions = [],
  rowActions = [],
  dense = false,
  stickyHeader = false,
  showHeader = true,
  showToolbar = true,
  title,
  subtitle,
  onRowClick,
  onRowDoubleClick,
  onRefresh,
  onExport,
}: VirtualizedDataTableProps<T>) => {
  const theme = useTheme()
  const listRef = useRef<List>(null)
  const [columnMenuAnchor, setColumnMenuAnchor] = useState<HTMLElement | null>(null)
  const [actionMenuAnchor, setActionMenuAnchor] = useState<{ [key: string]: HTMLElement | null }>(
    {},
  )
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(
    new Set(initialColumns.filter(col => !col.hidden).map(col => col.id as string)),
  )

  // 计算可见列
  const columns = useMemo(
    () => initialColumns.filter(col => visibleColumns.has(col.id as string)),
    [initialColumns, visibleColumns],
  )

  // 选择相关逻辑
  const selectedRowIds = useMemo(
    () => new Set(selectedRows.map(getRowId)),
    [selectedRows, getRowId],
  )

  const isAllSelected = data.length > 0 && selectedRowIds.size === data.length
  const isPartiallySelected = selectedRowIds.size > 0 && selectedRowIds.size < data.length

  // 过滤数据
  const filteredData = useMemo(() => {
    if (!globalFilter.trim()) return data

    const searchTerm = globalFilter.toLowerCase()
    return data.filter(row =>
      columns.some(column => {
        const value = row[column.id]
        const searchValue = column.format ? column.format(value) : String(value || '')
        return searchValue.toLowerCase().includes(searchTerm)
      })
    )
  }, [data, globalFilter, columns])

  // 排序数据
  const sortedData = useMemo(() => {
    if (!sortBy) return filteredData

    return [...filteredData].sort((a, b) => {
      const aValue = a[sortBy]
      const bValue = b[sortBy]

      if (aValue === bValue) return 0

      let comparison = 0
      if (aValue == null) comparison = -1
      else if (bValue == null) comparison = 1
      else if (typeof aValue === 'string' && typeof bValue === 'string') {
        comparison = aValue.localeCompare(bValue)
      } else {
        comparison = aValue < bValue ? -1 : 1
      }

      return sortOrder === 'desc' ? -comparison : comparison
    })
  }, [filteredData, sortBy, sortOrder])

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (onSelectionChange) {
        onSelectionChange(checked ? [...sortedData] : [])
      }
    },
    [sortedData, onSelectionChange],
  )

  const handleSelectRow = useCallback(
    (row: T, checked: boolean) => {
      if (onSelectionChange) {
        const rowId = getRowId(row)
        if (checked) {
          onSelectionChange([...selectedRows, row])
        } else {
          onSelectionChange(selectedRows.filter(r => getRowId(r) !== rowId))
        }
      }
    },
    [selectedRows, onSelectionChange, getRowId],
  )

  const handleSort = useCallback(
    (column: string) => {
      if (onSort) {
        const newOrder = sortBy === column && sortOrder === 'asc' ? 'desc' : 'asc'
        onSort(column, newOrder)
      }
    },
    [sortBy, sortOrder, onSort],
  )

  const toggleColumnVisibility = useCallback((columnId: string) => {
    setVisibleColumns(prev => {
      const newSet = new Set(prev)
      if (newSet.has(columnId)) {
        newSet.delete(columnId)
      } else {
        newSet.add(columnId)
      }
      return newSet
    })
  }, [])

  const handleActionMenuClick = useCallback(
    (rowId: string, event: React.MouseEvent<HTMLElement>) => {
      event.stopPropagation()
      setActionMenuAnchor(prev => ({ ...prev, [rowId]: event.currentTarget }))
    },
    [],
  )

  const handleActionMenuClose = useCallback((rowId: string) => {
    setActionMenuAnchor(prev => ({ ...prev, [rowId]: null }))
  }, [])

  // 准备虚拟化数据
  const virtualizedData = useMemo(() => ({
    items: sortedData,
    columns,
    selectedRowIds,
    getRowId,
    onSelectRow: handleSelectRow,
    onRowClick,
    onRowDoubleClick,
    rowActions,
    onActionMenuClick: handleActionMenuClick,
    selectable,
  }), [
    sortedData,
    columns,
    selectedRowIds,
    getRowId,
    handleSelectRow,
    onRowClick,
    onRowDoubleClick,
    rowActions,
    handleActionMenuClick,
    selectable,
  ])

  // 渲染工具栏
  const renderToolbar = () => {
    if (!showToolbar) return null

    return (
      <Toolbar
        sx={{
          pl: { sm: 2 },
          pr: { xs: 1, sm: 1 },
          ...(selectedRows.length > 0 && {
            bgcolor: alpha(theme.palette.primary.main, 0.08),
          }),
        }}
      >
        {selectedRows.length > 0 ? (
          <Typography sx={{ flex: '1 1 100%' }} color="inherit" variant="subtitle1" component="div">
            已选择 {selectedRows.length} 项
          </Typography>
        ) : (
          <Box sx={{ flex: '1 1 100%' }}>
            {title && (
              <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                {title}
              </Typography>
            )}
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
        )}

        {/* 搜索框 */}
        {onGlobalFilterChange && (
          <TextField
            size="small"
            placeholder="搜索..."
            value={globalFilter}
            onChange={e => onGlobalFilterChange(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={16} />
                </InputAdornment>
              ),
            }}
            sx={{ mr: 1, width: 200 }}
          />
        )}

        {/* 工具按钮 */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          {selectedRows.length > 0 &&
            actions.map(action => (
              <Tooltip key={action.id} title={action.label}>
                <IconButton
                  color={action.color}
                  onClick={() => selectedRows.forEach(action.onClick)}
                  size="small"
                >
                  {action.icon}
                </IconButton>
              </Tooltip>
            ))}

          {onExport && (
            <Tooltip title="导出">
              <IconButton onClick={onExport} size="small">
                <Download size={16} />
              </IconButton>
            </Tooltip>
          )}

          {onRefresh && (
            <Tooltip title="刷新">
              <IconButton onClick={onRefresh} size="small">
                <Refresh size={16} />
              </IconButton>
            </Tooltip>
          )}

          <Tooltip title="列设置">
            <IconButton onClick={e => setColumnMenuAnchor(e.currentTarget)} size="small">
              <Settings size={16} />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    )
  }

  // 渲染表格头部
  const renderTableHead = () => {
    if (!showHeader) return null

    return (
      <TableHead>
        <TableRow sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
          {selectable && (
            <TableCell 
              padding="checkbox"
              sx={{ display: 'flex', alignItems: 'center', width: '48px', minWidth: '48px' }}
            >
              <Checkbox
                color="primary"
                indeterminate={isPartiallySelected}
                checked={isAllSelected}
                onChange={e => handleSelectAll(e.target.checked)}
              />
            </TableCell>
          )}

          {columns.map(column => (
            <TableCell
              key={column.id as string}
              align={column.align}
              sx={{
                display: 'flex',
                alignItems: 'center',
                width: column.width || 'auto',
                minWidth: column.minWidth || 120,
                maxWidth: column.maxWidth,
                flex: column.width ? 'none' : 1,
              }}
              sortDirection={sortBy === column.id ? sortOrder : false}
            >
              {column.sortable ? (
                <TableSortLabel
                  active={sortBy === column.id}
                  direction={sortBy === column.id ? sortOrder : 'asc'}
                  onClick={() => handleSort(column.id as string)}
                >
                  {column.label}
                </TableSortLabel>
              ) : (
                column.label
              )}
            </TableCell>
          ))}

          {rowActions.length > 0 && (
            <TableCell 
              align="center"
              sx={{ display: 'flex', alignItems: 'center', width: '48px', minWidth: '48px' }}
            >
              操作
            </TableCell>
          )}
        </TableRow>
      </TableHead>
    )
  }

  const containerHeight = Math.min(sortedData.length * itemHeight, visibleRows * itemHeight)

  return (
    <Paper sx={{ width: '100%', borderRadius: 2 }}>
      {renderToolbar()}

      {loading && <LinearProgress />}

      {error && (
        <Box sx={{ p: 2 }}>
          <Typography color="error">{error}</Typography>
        </Box>
      )}

      <TableContainer>
        <Table stickyHeader={stickyHeader} size={dense ? 'small' : 'medium'}>
          {renderTableHead()}
        </Table>
        
        {sortedData.length === 0 && !loading ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              {error || '暂无数据'}
            </Typography>
          </Box>
        ) : (
          <List
            ref={listRef}
            height={containerHeight}
            itemCount={sortedData.length}
            itemSize={itemHeight}
            itemData={virtualizedData}
            overscanCount={overscanCount}
            width="100%"
          >
            {VirtualRow}
          </List>
        )}
      </TableContainer>

      {/* 数据统计 */}
      <Box sx={{ p: 1, borderTop: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          显示 {Math.min(visibleRows, sortedData.length)} / {sortedData.length} 条记录
          {filteredData.length !== data.length && ` (从 ${data.length} 条中筛选)`}
        </Typography>
        
        {selectedRows.length > 0 && (
          <Typography variant="body2" color="primary">
            已选择 {selectedRows.length} 项
          </Typography>
        )}
      </Box>

      {/* 列设置菜单 */}
      <Menu
        anchorEl={columnMenuAnchor}
        open={Boolean(columnMenuAnchor)}
        onClose={() => setColumnMenuAnchor(null)}
        PaperProps={{
          sx: { width: 200, maxHeight: 300 },
        }}
      >
        <Typography variant="subtitle2" sx={{ px: 2, py: 1, fontWeight: 600 }}>
          显示列
        </Typography>
        {initialColumns.map(column => (
          <MenuItem
            key={column.id as string}
            onClick={() => toggleColumnVisibility(column.id as string)}
          >
            <Checkbox
              checked={visibleColumns.has(column.id as string)}
              size="small"
              sx={{ mr: 1 }}
            />
            {column.label}
          </MenuItem>
        ))}
      </Menu>

      {/* 行操作菜单 */}
      {Object.entries(actionMenuAnchor).map(([rowId, anchorEl]) => {
        if (!anchorEl) return null
        
        const row = sortedData.find(r => getRowId(r) === rowId)
        if (!row) return null

        return (
          <Menu
            key={rowId}
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => handleActionMenuClose(rowId)}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          >
            {rowActions.map(action => (
              <MenuItem
                key={action.id}
                onClick={() => {
                  action.onClick(row)
                  handleActionMenuClose(rowId)
                }}
                disabled={action.disabled?.(row)}
              >
                {action.icon && <Box sx={{ mr: 1, display: 'flex' }}>{action.icon}</Box>}
                {action.label}
              </MenuItem>
            ))}
          </Menu>
        )
      })}
    </Paper>
  )
}