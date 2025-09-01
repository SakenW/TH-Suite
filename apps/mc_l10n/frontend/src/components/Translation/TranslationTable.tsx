/**
 * 翻译表格组件
 * 现代化的翻译条目管理界面
 */

import React, { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Checkbox,
  IconButton,
  TextField,
  Chip,
  Box,
  Typography,
  Menu,
  MenuItem,
  LinearProgress,
  Tooltip,
  Collapse,
  Avatar,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Edit,
  MoreVertical,
  Check,
  X,
  MessageCircle,
  History,
  Flag,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { TranslationEntry } from '../../types/api';
import { useApi } from '../../hooks/useApi';
import { translationService } from '../../services';
import toast from 'react-hot-toast';

interface TranslationTableProps {
  entries: TranslationEntry[];
  loading?: boolean;
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onEdit: (entry: TranslationEntry) => void;
  onRefresh: () => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (field: string) => void;
}

interface TableColumn {
  id: keyof TranslationEntry | 'actions';
  label: string;
  sortable?: boolean;
  minWidth?: number;
  align?: 'left' | 'center' | 'right';
  render?: (entry: TranslationEntry) => React.ReactNode;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'translated':
      return '#4CAF50';
    case 'reviewed':
      return '#2196F3';
    case 'approved':
      return '#8BC34A';
    case 'needs_update':
      return '#FF9800';
    case 'untranslated':
    default:
      return '#9E9E9E';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'translated':
      return '已翻译';
    case 'reviewed':
      return '已审核';
    case 'approved':
      return '已批准';
    case 'needs_update':
      return '需更新';
    case 'untranslated':
    default:
      return '未翻译';
  }
};

export const TranslationTable: React.FC<TranslationTableProps> = ({
  entries,
  loading = false,
  selectedIds,
  onSelectionChange,
  onEdit,
  onRefresh,
  sortBy,
  sortOrder = 'asc',
  onSort,
}) => {
  const theme = useTheme();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [anchorEl, setAnchorEl] = useState<{ [key: string]: HTMLElement | null }>({});
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // API hooks
  const { execute: updateTranslation, loading: updating } = useApi(
    () => editingId ? translationService.updateTranslation(editingId, { translated_text: editValue }) : Promise.reject(),
    false
  );

  const columns: TableColumn[] = useMemo(() => [
    {
      id: 'entry_key',
      label: '键名',
      sortable: true,
      minWidth: 200,
      render: (entry) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton
            size="small"
            onClick={() => handleToggleExpanded(entry.id)}
          >
            {expandedRows.has(entry.id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </IconButton>
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              color: theme.palette.text.primary,
              wordBreak: 'break-all',
            }}
          >
            {entry.entry_key}
          </Typography>
        </Box>
      ),
    },
    {
      id: 'source_text',
      label: '原文',
      sortable: false,
      minWidth: 250,
      render: (entry) => (
        <Typography
          variant="body2"
          sx={{
            maxWidth: 250,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            color: theme.palette.text.secondary,
          }}
        >
          {entry.source_text}
        </Typography>
      ),
    },
    {
      id: 'translated_text',
      label: '译文',
      sortable: false,
      minWidth: 300,
      render: (entry) => (
        <Box sx={{ minWidth: 300 }}>
          {editingId === entry.id ? (
            <TextField
              fullWidth
              size="small"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSaveEdit();
                } else if (e.key === 'Escape') {
                  handleCancelEdit();
                }
              }}
              multiline
              maxRows={3}
              disabled={updating}
              InputProps={{
                sx: { fontSize: '0.875rem' }
              }}
            />
          ) : (
            <Typography
              variant="body2"
              sx={{
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: 1,
                minHeight: '32px',
                display: 'flex',
                alignItems: 'center',
                backgroundColor: entry.translated_text 
                  ? 'transparent' 
                  : alpha(theme.palette.warning.main, 0.1),
                color: entry.translated_text 
                  ? theme.palette.text.primary 
                  : theme.palette.text.secondary,
                border: `1px solid transparent`,
                '&:hover': {
                  backgroundColor: alpha(theme.palette.action.hover, 0.1),
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                },
              }}
              onClick={() => handleStartEdit(entry)}
            >
              {entry.translated_text || '点击添加翻译...'}
            </Typography>
          )}
        </Box>
      ),
    },
    {
      id: 'language_code',
      label: '语言',
      sortable: true,
      minWidth: 100,
      align: 'center',
      render: (entry) => (
        <Chip
          label={entry.language_code.toUpperCase()}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 600 }}
        />
      ),
    },
    {
      id: 'status',
      label: '状态',
      sortable: true,
      minWidth: 120,
      align: 'center',
      render: (entry) => (
        <Chip
          label={getStatusLabel(entry.status)}
          size="small"
          sx={{
            backgroundColor: alpha(getStatusColor(entry.status), 0.1),
            color: getStatusColor(entry.status),
            fontWeight: 600,
            borderColor: alpha(getStatusColor(entry.status), 0.3),
          }}
          variant="outlined"
        />
      ),
    },
    {
      id: 'updated_at',
      label: '更新时间',
      sortable: true,
      minWidth: 140,
      align: 'center',
      render: (entry) => (
        <Typography variant="caption" color="text.secondary">
          {new Date(entry.updated_at).toLocaleDateString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Typography>
      ),
    },
    {
      id: 'actions',
      label: '操作',
      sortable: false,
      minWidth: 100,
      align: 'center',
      render: (entry) => (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
          {editingId === entry.id ? (
            <>
              <IconButton
                size="small"
                onClick={handleSaveEdit}
                disabled={updating}
                color="primary"
              >
                <Check size={16} />
              </IconButton>
              <IconButton
                size="small"
                onClick={handleCancelEdit}
                disabled={updating}
                color="error"
              >
                <X size={16} />
              </IconButton>
            </>
          ) : (
            <>
              <Tooltip title="编辑翻译">
                <IconButton
                  size="small"
                  onClick={() => handleStartEdit(entry)}
                  color="primary"
                >
                  <Edit size={14} />
                </IconButton>
              </Tooltip>
              <Tooltip title="更多操作">
                <IconButton
                  size="small"
                  onClick={(e) => handleMenuClick(entry.id, e)}
                >
                  <MoreVertical size={14} />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Box>
      ),
    },
  ], [editingId, editValue, updating, expandedRows, theme]);

  const handleSelectAll = (checked: boolean) => {
    onSelectionChange(checked ? entries.map(e => e.id) : []);
  };

  const handleSelectItem = (id: string, checked: boolean) => {
    const newSelection = checked
      ? [...selectedIds, id]
      : selectedIds.filter(selectedId => selectedId !== id);
    onSelectionChange(newSelection);
  };

  const handleSort = (columnId: string) => {
    if (onSort) {
      onSort(columnId);
    }
  };

  const handleStartEdit = (entry: TranslationEntry) => {
    setEditingId(entry.id);
    setEditValue(entry.translated_text || '');
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;

    try {
      await updateTranslation();
      toast.success('翻译更新成功');
      setEditingId(null);
      setEditValue('');
      onRefresh();
    } catch (error) {
      toast.error('更新失败');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValue('');
  };

  const handleMenuClick = (entryId: string, event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(prev => ({ ...prev, [entryId]: event.currentTarget }));
  };

  const handleMenuClose = (entryId: string) => {
    setAnchorEl(prev => ({ ...prev, [entryId]: null }));
  };

  const handleToggleExpanded = (entryId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(entryId)) {
        newSet.delete(entryId);
      } else {
        newSet.add(entryId);
      }
      return newSet;
    });
  };

  const isAllSelected = entries.length > 0 && selectedIds.length === entries.length;
  const isPartiallySelected = selectedIds.length > 0 && selectedIds.length < entries.length;

  return (
    <Paper
      sx={{
        borderRadius: 3,
        overflow: 'hidden',
        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
      }}
    >
      {loading && <LinearProgress />}
      
      <TableContainer sx={{ maxHeight: 600 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" sx={{ backgroundColor: theme.palette.background.paper }}>
                <Checkbox
                  indeterminate={isPartiallySelected}
                  checked={isAllSelected}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  size="small"
                />
              </TableCell>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align || 'left'}
                  style={{ minWidth: column.minWidth }}
                  sx={{
                    backgroundColor: theme.palette.background.paper,
                    fontWeight: 600,
                    borderBottom: `2px solid ${theme.palette.divider}`,
                  }}
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
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.map((entry, index) => {
              const isSelected = selectedIds.includes(entry.id);
              const isExpanded = expandedRows.has(entry.id);

              return (
                <React.Fragment key={entry.id}>
                  <TableRow
                    hover
                    selected={isSelected}
                    sx={{
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.primary.main, 0.04),
                      },
                      ...(isSelected && {
                        backgroundColor: alpha(theme.palette.primary.main, 0.08),
                      }),
                    }}
                  >
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={isSelected}
                        onChange={(e) => handleSelectItem(entry.id, e.target.checked)}
                        size="small"
                      />
                    </TableCell>
                    {columns.map((column) => (
                      <TableCell
                        key={column.id}
                        align={column.align || 'left'}
                        sx={{ py: 1 }}
                      >
                        {column.render ? column.render(entry) : entry[column.id as keyof TranslationEntry]}
                      </TableCell>
                    ))}
                  </TableRow>

                  {/* 展开的详细信息 */}
                  <TableRow>
                    <TableCell colSpan={columns.length + 1} sx={{ py: 0, border: 0 }}>
                      <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                        <Box sx={{ p: 2, backgroundColor: alpha(theme.palette.action.hover, 0.3) }}>
                          <Box sx={{ display: 'flex', gap: 3 }}>
                            {/* 上下文信息 */}
                            {entry.context && (
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                  上下文
                                </Typography>
                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                  {entry.context}
                                </Typography>
                              </Box>
                            )}

                            {/* 备注信息 */}
                            {entry.comment && (
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                  备注
                                </Typography>
                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                  {entry.comment}
                                </Typography>
                              </Box>
                            )}

                            {/* 译者信息 */}
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                译者信息
                              </Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {entry.translator_id && (
                                  <Avatar sx={{ width: 20, height: 20 }}>
                                    {entry.translator_id.charAt(0).toUpperCase()}
                                  </Avatar>
                                )}
                                <Typography variant="caption" color="text.secondary">
                                  {entry.translator_id || '未指定'}
                                </Typography>
                              </Box>
                            </Box>
                          </Box>
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>

                  {/* 菜单 */}
                  <Menu
                    anchorEl={anchorEl[entry.id]}
                    open={Boolean(anchorEl[entry.id])}
                    onClose={() => handleMenuClose(entry.id)}
                    transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                    anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                  >
                    <MenuItem onClick={() => handleMenuClose(entry.id)}>
                      <History size={16} style={{ marginRight: 8 }} />
                      查看历史
                    </MenuItem>
                    <MenuItem onClick={() => handleMenuClose(entry.id)}>
                      <MessageCircle size={16} style={{ marginRight: 8 }} />
                      添加备注
                    </MenuItem>
                    <MenuItem onClick={() => handleMenuClose(entry.id)}>
                      <Flag size={16} style={{ marginRight: 8 }} />
                      标记为需要更新
                    </MenuItem>
                  </Menu>
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {entries.length === 0 && !loading && (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="body1" color="text.secondary">
            暂无翻译条目
          </Typography>
        </Box>
      )}
    </Paper>
  );
};