/**
 * 增强版翻译表格组件
 * 使用 TanStack Table 替换 MUI DataGrid，集成 React 19 特性
 */

import React, { useMemo, useOptimistic, useActionState } from 'react'
import { createColumnHelper } from '@tanstack/react-table'
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Button,
  TextField,
  Tooltip,
  Badge,
  LinearProgress,
} from '@mui/material'
import { Edit, Check, X, Globe, AlertTriangle, Clock, Star, Copy, ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'
import TanStackDataTable from './common/TanStackDataTable'
import VirtualizedList from './common/VirtualizedList'

// 翻译条目类型定义
interface TranslationEntry {
  id: string
  key: string
  originalText: string
  translatedText: string
  status: 'pending' | 'translated' | 'reviewed' | 'approved'
  priority: 'low' | 'medium' | 'high'
  lastModified: Date
  translator?: string
  reviewer?: string
  notes?: string
  context?: string
  difficulty: 'easy' | 'medium' | 'hard'
  characterCount: number
  wordCount: number
}

// 翻译操作类型
interface TranslationAction {
  type: 'edit' | 'approve' | 'reject' | 'copy'
  entryId: string
  value?: string
  notes?: string
}

interface TranslationActionState {
  success: boolean
  message: string
  updatedEntry?: TranslationEntry
}

interface TranslationTableProps {
  entries: TranslationEntry[]
  loading?: boolean
  onEdit?: (id: string, newText: string) => void
  onApprove?: (id: string) => void
  onReject?: (id: string, reason: string) => void
  viewMode?: 'table' | 'list' | 'cards'
}

export function TranslationTableEnhanced({
  entries,
  loading = false,
  onEdit,
  onApprove,
  onReject,
  viewMode = 'table',
}: TranslationTableProps) {
  // React 19 useOptimistic: 乐观更新翻译状态
  const [optimisticEntries, addOptimisticUpdate] = useOptimistic(
    entries,
    (currentEntries: TranslationEntry[], update: { type: string; payload: any }) => {
      switch (update.type) {
        case 'EDIT':
          return currentEntries.map(entry =>
            entry.id === update.payload.id
              ? { ...entry, translatedText: update.payload.text, status: 'translated' as const }
              : entry,
          )
        case 'APPROVE':
          return currentEntries.map(entry =>
            entry.id === update.payload.id ? { ...entry, status: 'approved' as const } : entry,
          )
        case 'REJECT':
          return currentEntries.map(entry =>
            entry.id === update.payload.id
              ? { ...entry, status: 'pending' as const, notes: update.payload.reason }
              : entry,
          )
        default:
          return currentEntries
      }
    },
  )

  // React 19 useActionState: 翻译操作状态管理
  const handleTranslationAction = async (
    prevState: TranslationActionState,
    formData: FormData,
  ): Promise<TranslationActionState> => {
    try {
      const actionType = formData.get('actionType') as string
      const entryId = formData.get('entryId') as string
      const value = formData.get('value') as string
      const notes = formData.get('notes') as string

      // 立即应用乐观更新
      switch (actionType) {
        case 'edit':
          addOptimisticUpdate({
            type: 'EDIT',
            payload: { id: entryId, text: value },
          })
          if (onEdit) onEdit(entryId, value)
          break

        case 'approve':
          addOptimisticUpdate({
            type: 'APPROVE',
            payload: { id: entryId },
          })
          if (onApprove) onApprove(entryId)
          break

        case 'reject':
          addOptimisticUpdate({
            type: 'REJECT',
            payload: { id: entryId, reason: notes || '需要修改' },
          })
          if (onReject) onReject(entryId, notes || '需要修改')
          break
      }

      return {
        success: true,
        message: `操作成功: ${actionType}`,
        updatedEntry: optimisticEntries.find(e => e.id === entryId),
      }
    } catch (error) {
      return {
        success: false,
        message: '操作失败，请重试',
      }
    }
  }

  const [actionState, actionDispatch, isActionPending] = useActionState(handleTranslationAction, {
    success: false,
    message: '',
  })

  // 创建列定义
  const columnHelper = createColumnHelper<TranslationEntry>()

  const columns = useMemo(
    () => [
      columnHelper.accessor('key', {
        header: '键名',
        cell: ({ getValue }) => (
          <Typography
            variant='body2'
            sx={{
              fontFamily: 'monospace',
              color: 'primary.main',
              fontSize: '0.875rem',
            }}
          >
            {getValue()}
          </Typography>
        ),
        size: 200,
      }),

      columnHelper.accessor('originalText', {
        header: '原文',
        cell: ({ getValue }) => (
          <Box sx={{ maxWidth: 300 }}>
            <Typography
              variant='body2'
              sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}
            >
              {getValue()}
            </Typography>
          </Box>
        ),
        size: 300,
      }),

      columnHelper.accessor('translatedText', {
        header: '译文',
        cell: ({ row, getValue }) => {
          const [isEditing, setIsEditing] = React.useState(false)
          const [editValue, setEditValue] = React.useState(getValue())

          if (isEditing) {
            return (
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <TextField
                  size='small'
                  multiline
                  maxRows={3}
                  value={editValue}
                  onChange={e => setEditValue(e.target.value)}
                  sx={{ flex: 1 }}
                />
                <form action={actionDispatch} onSubmit={() => setIsEditing(false)}>
                  <input type='hidden' name='actionType' value='edit' />
                  <input type='hidden' name='entryId' value={row.original.id} />
                  <input type='hidden' name='value' value={editValue} />
                  <IconButton size='small' type='submit' color='success'>
                    <Check size={16} />
                  </IconButton>
                </form>
                <IconButton
                  size='small'
                  onClick={() => {
                    setIsEditing(false)
                    setEditValue(getValue())
                  }}
                >
                  <X size={16} />
                </IconButton>
              </Box>
            )
          }

          return (
            <Box sx={{ maxWidth: 300 }}>
              <Typography
                variant='body2'
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  cursor: 'pointer',
                }}
                onClick={() => setIsEditing(true)}
              >
                {getValue() || (
                  <span style={{ color: '#999', fontStyle: 'italic' }}>点击添加翻译...</span>
                )}
              </Typography>
            </Box>
          )
        },
        size: 300,
      }),

      columnHelper.accessor('status', {
        header: '状态',
        cell: ({ getValue }) => {
          const status = getValue()
          const statusConfig = {
            pending: { color: 'warning' as const, label: '待翻译', icon: <Clock size={14} /> },
            translated: { color: 'info' as const, label: '已翻译', icon: <Edit size={14} /> },
            reviewed: { color: 'secondary' as const, label: '已审核', icon: <Check size={14} /> },
            approved: { color: 'success' as const, label: '已批准', icon: <Star size={14} /> },
          }

          const config = statusConfig[status]
          return (
            <Chip
              icon={config.icon}
              label={config.label}
              color={config.color}
              size='small'
              variant='outlined'
            />
          )
        },
        size: 120,
      }),

      columnHelper.accessor('priority', {
        header: '优先级',
        cell: ({ getValue }) => {
          const priority = getValue()
          const priorityConfig = {
            low: { color: 'default' as const, label: '低' },
            medium: { color: 'warning' as const, label: '中' },
            high: { color: 'error' as const, label: '高' },
          }

          const config = priorityConfig[priority]
          return <Chip label={config.label} color={config.color} size='small' />
        },
        size: 100,
      }),

      columnHelper.accessor('difficulty', {
        header: '难度',
        cell: ({ getValue }) => {
          const difficulty = getValue()
          const stars = difficulty === 'easy' ? 1 : difficulty === 'medium' ? 2 : 3

          return (
            <Box sx={{ display: 'flex' }}>
              {Array.from({ length: 3 }, (_, i) => (
                <Star
                  key={i}
                  size={14}
                  fill={i < stars ? '#ffc107' : 'none'}
                  color={i < stars ? '#ffc107' : '#e0e0e0'}
                />
              ))}
            </Box>
          )
        },
        size: 100,
      }),

      columnHelper.display({
        id: 'actions',
        header: '操作',
        cell: ({ row }) => (
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title='批准'>
              <form action={actionDispatch} style={{ display: 'inline' }}>
                <input type='hidden' name='actionType' value='approve' />
                <input type='hidden' name='entryId' value={row.original.id} />
                <IconButton
                  size='small'
                  color='success'
                  type='submit'
                  disabled={row.original.status === 'approved'}
                >
                  <Check size={16} />
                </IconButton>
              </form>
            </Tooltip>

            <Tooltip title='拒绝'>
              <form action={actionDispatch} style={{ display: 'inline' }}>
                <input type='hidden' name='actionType' value='reject' />
                <input type='hidden' name='entryId' value={row.original.id} />
                <input type='hidden' name='notes' value='需要重新翻译' />
                <IconButton
                  size='small'
                  color='error'
                  type='submit'
                  disabled={row.original.status === 'pending'}
                >
                  <X size={16} />
                </IconButton>
              </form>
            </Tooltip>

            <Tooltip title='复制原文'>
              <IconButton
                size='small'
                onClick={() => navigator.clipboard.writeText(row.original.originalText)}
              >
                <Copy size={16} />
              </IconButton>
            </Tooltip>
          </Box>
        ),
        size: 120,
      }),
    ],
    [actionDispatch],
  )

  // 列表视图渲染器
  const renderListItem = (entry: TranslationEntry, index: number) => (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.02 }}
    >
      <Box
        sx={{
          p: 2,
          mb: 1,
          border: 1,
          borderColor: 'divider',
          borderRadius: 2,
          backgroundColor: 'background.paper',
          '&:hover': { backgroundColor: 'action.hover' },
        }}
      >
        <Box
          sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}
        >
          <Typography variant='subtitle2' color='primary'>
            {entry.key}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip label={entry.status} size='small' />
            <Chip label={entry.priority} size='small' color='warning' />
          </Box>
        </Box>

        <Typography variant='body2' color='text.secondary' gutterBottom>
          原文: {entry.originalText}
        </Typography>

        <Typography variant='body2' gutterBottom>
          译文: {entry.translatedText || '待翻译'}
        </Typography>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant='caption' color='text.secondary'>
            {entry.characterCount} 字符 • {entry.wordCount} 词
          </Typography>

          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <IconButton size='small' color='success'>
              <Check size={16} />
            </IconButton>
            <IconButton size='small' color='error'>
              <X size={16} />
            </IconButton>
          </Box>
        </Box>
      </Box>
    </motion.div>
  )

  // 统计信息
  const stats = useMemo(() => {
    const total = optimisticEntries.length
    const pending = optimisticEntries.filter(e => e.status === 'pending').length
    const translated = optimisticEntries.filter(e => e.status === 'translated').length
    const approved = optimisticEntries.filter(e => e.status === 'approved').length
    const progress = total > 0 ? ((translated + approved) / total) * 100 : 0

    return { total, pending, translated, approved, progress }
  }, [optimisticEntries])

  if (viewMode === 'list') {
    return (
      <Box sx={{ height: '100%' }}>
        {/* 统计面板 */}
        <Box sx={{ mb: 2, p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
          <Typography variant='h6' gutterBottom>
            翻译进度
          </Typography>
          <LinearProgress
            variant='determinate'
            value={stats.progress}
            sx={{ mb: 1, height: 8, borderRadius: 4 }}
          />
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Chip label={`总计: ${stats.total}`} />
            <Chip label={`待翻译: ${stats.pending}`} color='warning' />
            <Chip label={`已翻译: ${stats.translated}`} color='info' />
            <Chip label={`已批准: ${stats.approved}`} color='success' />
          </Box>
        </Box>

        <VirtualizedList
          items={optimisticEntries}
          loading={loading}
          renderItem={renderListItem}
          enableSearch
          searchKeys={['key', 'originalText', 'translatedText']}
          title='翻译条目列表'
          itemHeight={120}
        />
      </Box>
    )
  }

  return (
    <Box sx={{ height: '100%' }}>
      {/* 操作反馈 */}
      {actionState.message && (
        <Box sx={{ mb: 2 }}>
          <Chip
            label={actionState.message}
            color={actionState.success ? 'success' : 'error'}
            onDelete={() => {}} // 清除消息
          />
        </Box>
      )}

      <TanStackDataTable
        data={optimisticEntries}
        columns={columns}
        loading={loading || isActionPending}
        title='翻译管理表格'
        enableSorting
        enableFiltering
        enablePagination
        enableSelection
        pageSize={20}
        searchPlaceholder='搜索翻译键、原文或译文...'
        onRowClick={entry => {
          console.log('点击行:', entry)
        }}
        onExport={data => {
          console.log('导出数据:', data)
        }}
        onRefresh={() => {
          console.log('刷新数据')
        }}
      />
    </Box>
  )
}

export default TranslationTableEnhanced
