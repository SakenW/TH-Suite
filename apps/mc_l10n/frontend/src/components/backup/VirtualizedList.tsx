/**
 * React-Virtuoso 虚拟滚动列表组件
 * 优化长列表性能，支持大量数据的高效渲染
 */

import React, { useOptimistic, useActionState, useMemo, useCallback } from 'react'
import { Virtuoso, VirtuosoGrid, GroupedVirtuoso } from 'react-virtuoso'
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Chip,
  IconButton,
  Button,
  LinearProgress,
  Alert,
  Skeleton,
} from '@mui/material'
import { Search, Filter, SortAsc, SortDesc, Grid3X3, List, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// 类型定义
export interface VirtualListItem {
  id: string | number
  [key: string]: any
}

export interface VirtualListProps<T extends VirtualListItem> {
  items: T[]
  loading?: boolean
  error?: string
  itemHeight?: number
  renderItem: (item: T, index: number) => React.ReactNode
  renderEmpty?: () => React.ReactNode
  onLoadMore?: () => void
  onRefresh?: () => void
  enableSearch?: boolean
  searchPlaceholder?: string
  searchKeys?: (keyof T)[]
  title?: string
  viewMode?: 'list' | 'grid'
  gridColumns?: number
  groupBy?: (item: T) => string
  sortBy?: keyof T
  sortOrder?: 'asc' | 'desc'
  onSortChange?: (key: keyof T, order: 'asc' | 'desc') => void
}

interface SearchAction {
  success: boolean
  message: string
  filteredCount: number
}

export function VirtualizedList<T extends VirtualListItem>({
  items,
  loading = false,
  error,
  itemHeight = 80,
  renderItem,
  renderEmpty,
  onLoadMore,
  onRefresh,
  enableSearch = true,
  searchPlaceholder = '搜索...',
  searchKeys = ['name', 'title'] as (keyof T)[],
  title,
  viewMode = 'list',
  gridColumns = 3,
  groupBy,
  sortBy,
  sortOrder = 'asc',
  onSortChange,
}: VirtualListProps<T>) {
  const [searchQuery, setSearchQuery] = React.useState('')
  const [currentViewMode, setCurrentViewMode] = React.useState(viewMode)

  // React 19 useOptimistic: 乐观更新搜索结果
  const [optimisticItems, addOptimisticUpdate] = useOptimistic(
    items,
    (currentItems: T[], update: { type: string; payload: any }): T[] => {
      switch (update.type) {
        case 'FILTER':
          return currentItems.filter(item =>
            searchKeys.some(key =>
              String(item[key]).toLowerCase().includes(update.payload.query.toLowerCase()),
            ),
          )
        case 'SORT':
          return [...currentItems].sort((a, b) => {
            const aVal = a[update.payload.key]
            const bVal = b[update.payload.key]
            const order = update.payload.order === 'asc' ? 1 : -1

            if (aVal < bVal) return -order
            if (aVal > bVal) return order
            return 0
          })
        case 'ADD':
          return [...currentItems, update.payload.item]
        case 'UPDATE':
          return currentItems.map(item =>
            item.id === update.payload.id ? { ...item, ...update.payload.data } : item,
          )
        case 'DELETE':
          return currentItems.filter(item => item.id !== update.payload.id)
        default:
          return currentItems
      }
    },
  )

  // React 19 useActionState: 搜索操作状态管理
  const handleSearch = async (
    prevState: SearchAction,
    formData: FormData,
  ): Promise<SearchAction> => {
    try {
      const query = formData.get('query') as string
      setSearchQuery(query)

      // 立即应用搜索过滤
      addOptimisticUpdate({
        type: 'FILTER',
        payload: { query },
      })

      const filteredCount = items.filter(item =>
        searchKeys.some(key => String(item[key]).toLowerCase().includes(query.toLowerCase())),
      ).length

      return {
        success: true,
        message: query ? `找到 ${filteredCount} 个匹配项` : '显示全部',
        filteredCount,
      }
    } catch (error) {
      return {
        success: false,
        message: '搜索失败',
        filteredCount: 0,
      }
    }
  }

  const [searchState, searchAction, isSearchPending] = useActionState(handleSearch, {
    success: true,
    message: '',
    filteredCount: items.length,
  })

  // 过滤和排序后的数据
  const processedItems = useMemo(() => {
    let filtered = optimisticItems

    // 应用搜索过滤
    if (searchQuery) {
      filtered = filtered.filter(item =>
        searchKeys.some(key => String(item[key]).toLowerCase().includes(searchQuery.toLowerCase())),
      )
    }

    // 应用排序
    if (sortBy) {
      filtered = [...filtered].sort((a, b) => {
        const aVal = a[sortBy]
        const bVal = b[sortBy]
        const order = sortOrder === 'asc' ? 1 : -1

        if (aVal < bVal) return -order
        if (aVal > bVal) return order
        return 0
      })
    }

    return filtered
  }, [optimisticItems, searchQuery, searchKeys, sortBy, sortOrder])

  // 分组数据（如果启用分组）
  const groupedItems = useMemo(() => {
    if (!groupBy) return null

    const groups = new Map<string, T[]>()
    processedItems.forEach(item => {
      const group = groupBy(item)
      if (!groups.has(group)) {
        groups.set(group, [])
      }
      groups.get(group)!.push(item)
    })

    return Array.from(groups.entries()).map(([groupName, groupItems]) => ({
      groupName,
      items: groupItems,
    }))
  }, [processedItems, groupBy])

  // 处理排序变化
  const handleSortChange = useCallback(
    (key: keyof T) => {
      const newOrder = sortBy === key && sortOrder === 'asc' ? 'desc' : 'asc'
      if (onSortChange) {
        onSortChange(key, newOrder)
      }

      // 应用乐观排序
      addOptimisticUpdate({
        type: 'SORT',
        payload: { key, order: newOrder },
      })
    },
    [sortBy, sortOrder, onSortChange],
  )

  // 加载更多处理
  const handleLoadMore = useCallback(() => {
    if (onLoadMore && !loading) {
      onLoadMore()
    }
  }, [onLoadMore, loading])

  // 列表项渲染器
  const ItemRenderer = useCallback(
    ({ index }: { index: number }) => {
      const item = processedItems[index]
      if (!item) {
        return <Skeleton variant='rectangular' width='100%' height={itemHeight} />
      }

      return (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: index * 0.02 }}
        >
          {renderItem(item, index)}
        </motion.div>
      )
    },
    [processedItems, renderItem, itemHeight],
  )

  // 网格项渲染器
  const GridItemRenderer = useCallback(
    ({ index }: { index: number }) => {
      const item = processedItems[index]
      if (!item) {
        return <Skeleton variant='rectangular' width='100%' height={200} />
      }

      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2, delay: index * 0.03 }}
        >
          {renderItem(item, index)}
        </motion.div>
      )
    },
    [processedItems, renderItem],
  )

  // 分组标题渲染器
  const GroupHeaderRenderer = useCallback(
    ({ groupIndex }: { groupIndex: number }) => {
      if (!groupedItems) return null
      const group = groupedItems[groupIndex]

      return (
        <Box sx={{ p: 2, backgroundColor: 'grey.100', fontWeight: 600 }}>
          <Typography variant='h6'>
            {group.groupName} ({group.items.length})
          </Typography>
        </Box>
      )
    },
    [groupedItems],
  )

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题和控制栏 */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {title && <Typography variant='h6'>{title}</Typography>}
          <Chip
            label={`${processedItems.length} 项`}
            size='small'
            color='primary'
            variant='outlined'
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {/* 视图切换 */}
          <IconButton
            size='small'
            color={currentViewMode === 'list' ? 'primary' : 'default'}
            onClick={() => setCurrentViewMode('list')}
          >
            <List size={18} />
          </IconButton>
          <IconButton
            size='small'
            color={currentViewMode === 'grid' ? 'primary' : 'default'}
            onClick={() => setCurrentViewMode('grid')}
          >
            <Grid3X3 size={18} />
          </IconButton>

          {/* 刷新按钮 */}
          {onRefresh && (
            <IconButton size='small' onClick={onRefresh} disabled={loading}>
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            </IconButton>
          )}
        </Box>
      </Box>

      {/* 搜索栏 */}
      {enableSearch && (
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <form action={searchAction}>
            <TextField
              name='query'
              size='small'
              placeholder={searchPlaceholder}
              defaultValue={searchQuery}
              fullWidth
              InputProps={{
                startAdornment: <Search size={18} />,
              }}
              disabled={isSearchPending}
            />
          </form>

          {/* 搜索结果状态 */}
          <AnimatePresence>
            {searchState.message && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Box sx={{ mt: 1 }}>
                  <Typography variant='caption' color='text.secondary'>
                    {searchState.message}
                  </Typography>
                </Box>
              </motion.div>
            )}
          </AnimatePresence>
        </Box>
      )}

      {/* 加载状态 */}
      {loading && <LinearProgress />}

      {/* 错误状态 */}
      {error && (
        <Box sx={{ p: 2 }}>
          <Alert severity='error'>{error}</Alert>
        </Box>
      )}

      {/* 虚拟滚动内容 */}
      <Box sx={{ flex: 1 }}>
        {processedItems.length === 0 && !loading ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              p: 4,
            }}
          >
            {renderEmpty ? (
              renderEmpty()
            ) : (
              <>
                <Typography variant='h6' color='text.secondary' gutterBottom>
                  暂无数据
                </Typography>
                <Typography variant='body2' color='text.secondary'>
                  {searchQuery ? '没有找到匹配的结果' : '当前列表为空'}
                </Typography>
              </>
            )}
          </Box>
        ) : (
          <>
            {/* 分组虚拟列表 */}
            {groupBy && groupedItems ? (
              <GroupedVirtuoso
                groupCounts={groupedItems.map(group => group.items.length)}
                groupContent={GroupHeaderRenderer}
                itemContent={index => {
                  const flatIndex =
                    groupedItems.reduce((acc, group, groupIndex) => {
                      return groupIndex < Math.floor(index / 1000) ? acc + group.items.length : acc
                    }, 0) +
                    (index % 1000)
                  return <ItemRenderer index={flatIndex} />
                }}
                style={{ height: '100%' }}
              />
            ) : currentViewMode === 'grid' ? (
              /* 网格虚拟列表 */
              <VirtuosoGrid
                totalCount={processedItems.length}
                itemContent={GridItemRenderer}
                listClassName='virtuoso-grid'
                style={{ height: '100%' }}
                endReached={handleLoadMore}
              />
            ) : (
              /* 普通虚拟列表 */
              <Virtuoso
                totalCount={processedItems.length}
                itemContent={ItemRenderer}
                style={{ height: '100%' }}
                endReached={handleLoadMore}
                overscan={5}
                increaseViewportBy={{
                  top: itemHeight * 2,
                  bottom: itemHeight * 2,
                }}
              />
            )}
          </>
        )}
      </Box>
    </Box>
  )
}

export default VirtualizedList
