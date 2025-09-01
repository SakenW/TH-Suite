/**
 * 通用数据表格组件
 * 功能完整的数据表格，支持排序、过滤、分页、选择等功能
 */

import React, { useState, useMemo, useCallback } from 'react';
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
  Chip,
  TextField,
  InputAdornment,
  Toolbar,
  Tooltip,
  LinearProgress,
  Collapse,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  MoreVertical,
  Search,
  Filter,
  Download,
  RefreshCw as Refresh,
  Settings,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface TableColumn<T = any> {
  id: keyof T | string;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  width?: number | string;
  minWidth?: number;
  maxWidth?: number;
  align?: 'left' | 'center' | 'right';
  sticky?: boolean;
  hidden?: boolean;
  render?: (value: any, row: T, column: TableColumn<T>) => React.ReactNode;
  format?: (value: any) => string;
  filterType?: 'text' | 'select' | 'date' | 'range';
  filterOptions?: Array<{ label: string; value: any }>;
}

export interface TableAction<T = any> {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: (row: T) => void;
  disabled?: (row: T) => boolean;
  color?: 'inherit' | 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning';
  variant?: 'text' | 'outlined' | 'contained';
}

interface DataTableProps<T = any> {
  // 数据
  data: T[];
  columns: TableColumn<T>[];
  loading?: boolean;
  error?: string;
  
  // 选择功能
  selectable?: boolean;
  selectedRows?: T[];
  onSelectionChange?: (selected: T[]) => void;
  getRowId?: (row: T) => string;
  
  // 排序
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (column: string, order: 'asc' | 'desc') => void;
  
  // 分页
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: number[];
  
  // 过滤
  filters?: Record<string, any>;
  onFilterChange?: (filters: Record<string, any>) => void;
  globalFilter?: string;
  onGlobalFilterChange?: (filter: string) => void;
  
  // 行操作
  actions?: TableAction<T>[];
  rowActions?: TableAction<T>[];
  
  // 展开行
  expandableRows?: boolean;
  expandedRows?: Set<string>;
  onRowExpand?: (rowId: string) => void;
  renderExpandedRow?: (row: T) => React.ReactNode;
  
  // 样式配置
  dense?: boolean;
  stickyHeader?: boolean;
  showHeader?: boolean;
  showToolbar?: boolean;
  showPagination?: boolean;
  title?: string;
  subtitle?: string;
  
  // 事件
  onRowClick?: (row: T) => void;
  onRowDoubleClick?: (row: T) => void;
  onRefresh?: () => void;
  onExport?: () => void;
}

export const DataTable = <T extends Record<string, any>>({
  data,
  columns: initialColumns,
  loading = false,
  error,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  getRowId = (row) => row.id,
  sortBy,
  sortOrder = 'asc',
  onSort,
  page = 0,
  pageSize = 10,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [5, 10, 25, 50, 100],
  filters = {},
  onFilterChange,
  globalFilter = '',
  onGlobalFilterChange,
  actions = [],
  rowActions = [],
  expandableRows = false,
  expandedRows = new Set(),
  onRowExpand,
  renderExpandedRow,
  dense = false,
  stickyHeader = false,
  showHeader = true,
  showToolbar = true,
  showPagination = true,
  title,
  subtitle,
  onRowClick,
  onRowDoubleClick,
  onRefresh,
  onExport,
}: DataTableProps<T>) => {
  const theme = useTheme();
  const [columnMenuAnchor, setColumnMenuAnchor] = useState<HTMLElement | null>(null);
  const [actionMenuAnchor, setActionMenuAnchor] = useState<{ [key: string]: HTMLElement | null }>({});
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(
    new Set(initialColumns.filter(col => !col.hidden).map(col => col.id as string))
  );

  // 计算可见列
  const columns = useMemo(() => 
    initialColumns.filter(col => visibleColumns.has(col.id as string)),
    [initialColumns, visibleColumns]
  );

  // 选择相关逻辑
  const selectedRowIds = useMemo(() => 
    new Set(selectedRows.map(getRowId)),
    [selectedRows, getRowId]
  );

  const isAllSelected = data.length > 0 && selectedRowIds.size === data.length;
  const isPartiallySelected = selectedRowIds.size > 0 && selectedRowIds.size < data.length;

  const handleSelectAll = useCallback((checked: boolean) => {
    if (onSelectionChange) {
      onSelectionChange(checked ? [...data] : []);
    }
  }, [data, onSelectionChange]);

  const handleSelectRow = useCallback((row: T, checked: boolean) => {
    if (onSelectionChange) {
      const rowId = getRowId(row);
      if (checked) {
        onSelectionChange([...selectedRows, row]);
      } else {
        onSelectionChange(selectedRows.filter(r => getRowId(r) !== rowId));
      }
    }
  }, [selectedRows, onSelectionChange, getRowId]);

  // 排序处理
  const handleSort = useCallback((column: string) => {
    if (onSort) {
      const newOrder = sortBy === column && sortOrder === 'asc' ? 'desc' : 'asc';
      onSort(column, newOrder);
    }
  }, [sortBy, sortOrder, onSort]);

  // 列显示/隐藏切换
  const toggleColumnVisibility = useCallback((columnId: string) => {
    setVisibleColumns(prev => {
      const newSet = new Set(prev);
      if (newSet.has(columnId)) {
        newSet.delete(columnId);
      } else {
        newSet.add(columnId);
      }
      return newSet;
    });
  }, []);

  // 行展开切换
  const toggleRowExpansion = useCallback((rowId: string) => {
    if (onRowExpand) {
      onRowExpand(rowId);
    }
  }, [onRowExpand]);

  // 菜单处理
  const handleActionMenuClick = useCallback((rowId: string, event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setActionMenuAnchor(prev => ({ ...prev, [rowId]: event.currentTarget }));
  }, []);

  const handleActionMenuClose = useCallback((rowId: string) => {
    setActionMenuAnchor(prev => ({ ...prev, [rowId]: null }));
  }, []);

  // 渲染工具栏
  const renderToolbar = () => {
    if (!showToolbar) return null;

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
          <Typography
            sx={{ flex: '1 1 100%' }}
            color="inherit"
            variant="subtitle1"
            component="div"
          >
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
            onChange={(e) => onGlobalFilterChange(e.target.value)}
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
          {selectedRows.length > 0 && actions.map((action) => (
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
            <IconButton
              onClick={(e) => setColumnMenuAnchor(e.currentTarget)}
              size="small"
            >
              <Settings size={16} />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    );
  };

  // 渲染表格头部
  const renderTableHead = () => {
    if (!showHeader) return null;

    return (
      <TableHead>
        <TableRow>
          {selectable && (
            <TableCell padding="checkbox">
              <Checkbox
                color="primary"
                indeterminate={isPartiallySelected}
                checked={isAllSelected}
                onChange={(e) => handleSelectAll(e.target.checked)}
              />
            </TableCell>
          )}

          {expandableRows && <TableCell width={48} />}

          {columns.map((column) => (
            <TableCell
              key={column.id as string}
              align={column.align}
              style={{
                width: column.width,
                minWidth: column.minWidth,
                maxWidth: column.maxWidth,
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
            <TableCell width={48} align="center">
              操作
            </TableCell>
          )}
        </TableRow>
      </TableHead>
    );
  };

  // 渲染表格行
  const renderTableRows = () => {
    if (data.length === 0 && !loading) {
      return (
        <TableRow>
          <TableCell colSpan={columns.length + (selectable ? 1 : 0) + (expandableRows ? 1 : 0) + (rowActions.length > 0 ? 1 : 0)}>
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                {error || '暂无数据'}
              </Typography>
            </Box>
          </TableCell>
        </TableRow>
      );
    }

    return data.map((row) => {
      const rowId = getRowId(row);
      const isSelected = selectedRowIds.has(rowId);
      const isExpanded = expandedRows.has(rowId);

      return (
        <React.Fragment key={rowId}>
          <TableRow
            hover
            selected={isSelected}
            onClick={() => onRowClick?.(row)}
            onDoubleClick={() => onRowDoubleClick?.(row)}
            sx={{
              cursor: onRowClick ? 'pointer' : 'default',
            }}
          >
            {selectable && (
              <TableCell padding="checkbox">
                <Checkbox
                  color="primary"
                  checked={isSelected}
                  onChange={(e) => handleSelectRow(row, e.target.checked)}
                  onClick={(e) => e.stopPropagation()}
                />
              </TableCell>
            )}

            {expandableRows && (
              <TableCell>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleRowExpansion(rowId);
                  }}
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </IconButton>
              </TableCell>
            )}

            {columns.map((column) => {
              const value = row[column.id];
              const displayValue = column.render 
                ? column.render(value, row, column)
                : column.format 
                ? column.format(value)
                : value;

              return (
                <TableCell key={column.id as string} align={column.align}>
                  {displayValue}
                </TableCell>
              );
            })}

            {rowActions.length > 0 && (
              <TableCell align="center">
                <IconButton
                  size="small"
                  onClick={(e) => handleActionMenuClick(rowId, e)}
                >
                  <MoreVertical size={16} />
                </IconButton>
              </TableCell>
            )}
          </TableRow>

          {/* 展开行 */}
          {expandableRows && renderExpandedRow && (
            <TableRow>
              <TableCell
                colSpan={columns.length + (selectable ? 1 : 0) + 1 + (rowActions.length > 0 ? 1 : 0)}
                sx={{ py: 0, border: 0 }}
              >
                <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                  <Box sx={{ p: 2 }}>
                    {renderExpandedRow(row)}
                  </Box>
                </Collapse>
              </TableCell>
            </TableRow>
          )}

          {/* 行操作菜单 */}
          <Menu
            anchorEl={actionMenuAnchor[rowId]}
            open={Boolean(actionMenuAnchor[rowId])}
            onClose={() => handleActionMenuClose(rowId)}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          >
            {rowActions.map((action) => (
              <MenuItem
                key={action.id}
                onClick={() => {
                  action.onClick(row);
                  handleActionMenuClose(rowId);
                }}
                disabled={action.disabled?.(row)}
              >
                {action.icon && (
                  <Box sx={{ mr: 1, display: 'flex' }}>
                    {action.icon}
                  </Box>
                )}
                {action.label}
              </MenuItem>
            ))}
          </Menu>
        </React.Fragment>
      );
    });
  };

  return (
    <Paper sx={{ width: '100%', borderRadius: 2 }}>
      {renderToolbar()}

      {loading && <LinearProgress />}

      <TableContainer sx={{ maxHeight: 600 }}>
        <Table
          stickyHeader={stickyHeader}
          size={dense ? 'small' : 'medium'}
          aria-labelledby="tableTitle"
        >
          {renderTableHead()}
          <TableBody>
            <AnimatePresence>
              {renderTableRows()}
            </AnimatePresence>
          </TableBody>
        </Table>
      </TableContainer>

      {/* 分页 */}
      {showPagination && (
        <TablePagination
          rowsPerPageOptions={pageSizeOptions}
          component="div"
          count={total || data.length}
          rowsPerPage={pageSize}
          page={page}
          onPageChange={(e, newPage) => onPageChange?.(newPage)}
          onRowsPerPageChange={(e) => onPageSizeChange?.(parseInt(e.target.value, 10))}
          labelRowsPerPage="每页显示:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} 共 ${count !== -1 ? count : `超过 ${to}`} 条`}
        />
      )}

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
        {initialColumns.map((column) => (
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
    </Paper>
  );
};