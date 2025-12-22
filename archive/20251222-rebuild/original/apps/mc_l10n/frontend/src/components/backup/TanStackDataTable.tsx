/**
 * TanStack Table 高性能数据表格组件
 * 替换 @mui/x-data-grid，提供更好的性能和React 19兼容性
 */

import React, { useMemo, useState, useOptimistic, useActionState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  ColumnDef,
  flexRender,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  PaginationState,
} from '@tanstack/react-table'
import {
  Box,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Paper,
  TextField,
  Button,
  IconButton,
  Typography,
  Chip,
  LinearProgress,
  Pagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  Tooltip,
} from '@mui/material'
import {
  Search,
  SortAsc,
  SortDesc,
  Filter,
  Download,
  Upload,
  RefreshCw,
  Settings,
  Eye,
  EyeOff,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// 类型定义
export interface TanStackDataTableProps<T = any> {
  data: T[]
  columns: ColumnDef<T>[]
  loading?: boolean
  error?: string
  enableSorting?: boolean
  enableFiltering?: boolean
  enablePagination?: boolean
  enableColumnVisibility?: boolean
  enableSelection?: boolean
  pageSize?: number
  pageSizeOptions?: number[]
  onSelectionChange?: (selectedRows: T[]) => void
  onRowClick?: (row: T) => void
  onExport?: (data: T[]) => void
  onRefresh?: () => void
  title?: string
  searchPlaceholder?: string
  emptyMessage?: string
}

export interface TableAction {
  type: 'refresh' | 'export' | 'import' | 'filter'
  payload?: any
}

export interface TableActionState {
  success: boolean
  message: string
  loading: boolean
}

export function TanStackDataTable<T = any>({
  data,
  columns,
  loading = false,
  error,
  enableSorting = true,
  enableFiltering = true,
  enablePagination = true,
  enableColumnVisibility = true,
  enableSelection = false,
  pageSize = 10,
  pageSizeOptions = [5, 10, 20, 50, 100],
  onSelectionChange,
  onRowClick,
  onExport,
  onRefresh,
  title = '数据表格',
  searchPlaceholder = '搜索...',
  emptyMessage = '暂无数据',
}: TanStackDataTableProps<T>) {
  // 基础状态
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})
  const [globalFilter, setGlobalFilter] = useState('')
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize,
  })

  // React 19 useOptimistic: 乐观更新数据
  const [optimisticData, addOptimistic] = useOptimistic(
    data,
    (currentData: T[], update: { type: string; payload: any }) => {
      switch (update.type) {
        case 'ADD':
          return [...currentData, update.payload]
        case 'UPDATE':
          return currentData.map(item =>
            (item as any).id === update.payload.id ? update.payload : item,
          )
        case 'DELETE':
          return currentData.filter(item => (item as any).id !== update.payload.id)
        default:
          return currentData
      }
    },
  )

  // React 19 useActionState: 表格操作状态管理
  const handleTableAction = async (
    prevState: TableActionState,
    formData: FormData,
  ): Promise<TableActionState> => {
    try {
      const actionType = formData.get('actionType') as string

      switch (actionType) {
        case 'refresh':
          if (onRefresh) {
            onRefresh()
          }
          return {
            success: true,
            message: '数据刷新成功',
            loading: false,
          }

        case 'export':
          if (onExport) {
            onExport(filteredData)
          }
          return {
            success: true,
            message: '数据导出成功',
            loading: false,
          }

        default:
          return {
            success: false,
            message: '未知操作',
            loading: false,
          }
      }
    } catch (error) {
      return {
        success: false,
        message: '操作失败',
        loading: false,
      }
    }
  }

  const [actionState, actionDispatch, isActionPending] = useActionState(handleTableAction, {
    success: false,
    message: '',
    loading: false,
  })

  // 动态列定义（支持选择列）
  const enhancedColumns = useMemo(() => {
    const baseColumns = [...columns]

    if (enableSelection) {
      baseColumns.unshift({
        id: 'select',
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllPageRowsSelected()}
            indeterminate={table.getIsSomePageRowsSelected()}
            onChange={e => table.toggleAllPageRowsSelected(!!e.target.checked)}
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={e => row.toggleSelected(!!e.target.checked)}
          />
        ),
        enableSorting: false,
        enableColumnFilter: false,
        size: 50,
      } as ColumnDef<T>)
    }

    return baseColumns
  }, [columns, enableSelection])

  // TanStack Table 实例
  const table = useReactTable({
    data: optimisticData,
    columns: enhancedColumns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
      pagination,
    },
    enableRowSelection: enableSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: enableFiltering ? getFilteredRowModel() : undefined,
    getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
  })

  const filteredData = table.getFilteredRowModel().rows.map(row => row.original)
  const selectedRows = table.getFilteredSelectedRowModel().rows.map(row => row.original)

  // 选择变化处理
  React.useEffect(() => {
    if (onSelectionChange && enableSelection) {
      onSelectionChange(selectedRows)
    }
  }, [selectedRows, onSelectionChange, enableSelection])

  return (
    <Box sx={{ width: '100%' }}>
      {/* 表格标题和工具栏 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant='h6' component='h2'>
          {title}
          {optimisticData.length > 0 && (
            <Chip label={`${optimisticData.length} 条记录`} size='small' sx={{ ml: 1 }} />
          )}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {/* 刷新按钮 */}
          {onRefresh && (
            <form action={actionDispatch}>
              <input type='hidden' name='actionType' value='refresh' />
              <Tooltip title='刷新数据'>
                <IconButton type='submit' disabled={isActionPending || loading} size='small'>
                  <RefreshCw size={18} className={isActionPending ? 'animate-spin' : ''} />
                </IconButton>
              </Tooltip>
            </form>
          )}

          {/* 导出按钮 */}
          {onExport && (
            <form action={actionDispatch}>
              <input type='hidden' name='actionType' value='export' />
              <Tooltip title='导出数据'>
                <IconButton
                  type='submit'
                  disabled={isActionPending || optimisticData.length === 0}
                  size='small'
                >
                  <Download size={18} />
                </IconButton>
              </Tooltip>
            </form>
          )}

          {/* 列可见性控制 */}
          {enableColumnVisibility && (
            <Tooltip title='列显示设置'>
              <IconButton size='small'>
                <Settings size={18} />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* 搜索和过滤工具栏 */}
      {enableFiltering && (
        <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
          <TextField
            size='small'
            placeholder={searchPlaceholder}
            value={globalFilter ?? ''}
            onChange={e => setGlobalFilter(e.target.value)}
            InputProps={{
              startAdornment: <Search size={18} />,
            }}
            sx={{ minWidth: 200 }}
          />

          {enableSelection && selectedRows.length > 0 && (
            <Chip
              label={`已选择 ${selectedRows.length} 项`}
              color='primary'
              onDelete={() => table.toggleAllRowsSelected(false)}
            />
          )}
        </Box>
      )}

      {/* 操作状态反馈 */}
      <AnimatePresence>
        {actionState.message && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <Box sx={{ mb: 2 }}>
              <Chip
                label={actionState.message}
                color={actionState.success ? 'success' : 'error'}
                variant='outlined'
              />
            </Box>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 加载状态 */}
      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* 错误状态 */}
      {error && (
        <Box sx={{ mb: 2, p: 2, backgroundColor: 'error.light', borderRadius: 1 }}>
          <Typography color='error'>{error}</Typography>
        </Box>
      )}

      {/* 数据表格 */}
      <TableContainer component={Paper} elevation={2}>
        <Table stickyHeader>
          <TableHead>
            {table.getHeaderGroups().map(headerGroup => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <TableCell
                    key={header.id}
                    sx={{
                      fontWeight: 600,
                      backgroundColor: 'grey.50',
                      position: 'relative',
                    }}
                    style={{ width: header.getSize() }}
                  >
                    {header.isPlaceholder ? null : (
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          cursor: header.column.getCanSort() ? 'pointer' : 'default',
                        }}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getCanSort() && (
                          <Box sx={{ ml: 1, display: 'flex', flexDirection: 'column' }}>
                            {header.column.getIsSorted() === 'asc' && <SortAsc size={14} />}
                            {header.column.getIsSorted() === 'desc' && <SortDesc size={14} />}
                            {!header.column.getIsSorted() && (
                              <Box sx={{ opacity: 0.3 }}>
                                <SortAsc size={14} />
                              </Box>
                            )}
                          </Box>
                        )}
                      </Box>
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableHead>
          <TableBody>
            <AnimatePresence>
              {table.getRowModel().rows.map((row, index) => (
                <motion.tr
                  key={row.id}
                  component={TableRow}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  hover
                  onClick={() => onRowClick && onRowClick(row.original)}
                  sx={{ cursor: onRowClick ? 'pointer' : 'default' }}
                >
                  {row.getVisibleCells().map(cell => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </motion.tr>
              ))}
            </AnimatePresence>
          </TableBody>
        </Table>
      </TableContainer>

      {/* 空数据状态 */}
      {!loading && optimisticData.length === 0 && (
        <Box
          sx={{
            textAlign: 'center',
            py: 8,
            color: 'text.secondary',
          }}
        >
          <Typography variant='h6' gutterBottom>
            {emptyMessage}
          </Typography>
          <Typography variant='body2'>当前没有可显示的数据</Typography>
        </Box>
      )}

      {/* 分页控件 */}
      {enablePagination && optimisticData.length > 0 && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mt: 2,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <FormControl size='small' sx={{ minWidth: 120 }}>
              <InputLabel>每页条数</InputLabel>
              <Select
                value={table.getState().pagination.pageSize}
                onChange={e => table.setPageSize(Number(e.target.value))}
                label='每页条数'
              >
                {pageSizeOptions.map(size => (
                  <MenuItem key={size} value={size}>
                    {size}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Typography variant='body2' color='text.secondary'>
              显示{' '}
              {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} -{' '}
              {Math.min(
                (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                optimisticData.length,
              )}{' '}
              条，共 {optimisticData.length} 条
            </Typography>
          </Box>

          <Pagination
            count={table.getPageCount()}
            page={table.getState().pagination.pageIndex + 1}
            onChange={(_, page) => table.setPageIndex(page - 1)}
            showFirstButton
            showLastButton
          />
        </Box>
      )}
    </Box>
  )
}

export default TanStackDataTable
