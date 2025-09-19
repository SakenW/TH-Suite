/**
 * 虚拟化列表组件 - 基于@tanstack/react-virtual
 * 支持动态行高、滚动到指定位置、选中项高亮等功能
 */

import React, { useMemo, useCallback, forwardRef, useImperativeHandle, useRef, useEffect } from 'react'
import { Card, Spin, Empty, Space, Typography, Button, Tooltip } from 'antd'
import { 
  ArrowUpOutlined, 
  ArrowDownOutlined,
  VerticalAlignTopOutlined,
  VerticalAlignBottomOutlined,
  DashboardOutlined 
} from '@ant-design/icons'
import { useVirtualized, type VirtualizerConfig } from './useVirtualizer'
import { motion, AnimatePresence } from 'framer-motion'

const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

export interface VirtualizedListProps<T = any> {
  // 数据
  data: T[]
  renderItem: (item: T, index: number, isVisible: boolean) => React.ReactNode
  
  // 基础配置
  height?: number | string
  width?: number | string
  className?: string
  
  // 虚拟化配置
  virtualizerConfig?: Partial<VirtualizerConfig<T>>
  
  // 选中功能
  selectedKeys?: (string | number)[]
  onSelectionChange?: (selectedKeys: (string | number)[], selectedItems: T[]) => void
  getItemKey?: (item: T, index: number) => string | number
  
  // 高亮功能  
  highlightedKey?: string | number
  onHighlight?: (key: string | number, item: T) => void
  
  // 加载和错误状态
  loading?: boolean
  error?: string | null
  emptyText?: string
  
  // 工具栏
  showToolbar?: boolean
  toolbarTitle?: string
  toolbarExtra?: React.ReactNode
  
  // 性能监控
  showPerformanceStats?: boolean
  
  // 事件
  onItemClick?: (item: T, index: number) => void
  onItemDoubleClick?: (item: T, index: number) => void
  
  // 样式配置
  itemClassName?: string | ((item: T, index: number, isSelected: boolean, isHighlighted: boolean) => string)
  containerStyle?: React.CSSProperties
  
  // 响应式
  responsive?: boolean
}

export interface VirtualizedListRef {
  scrollToIndex: (index: number, align?: 'start' | 'center' | 'end') => void
  scrollToKey: (key: string | number) => void
  scrollToTop: () => void
  scrollToBottom: () => void
  getStats: () => any
}

// ============================================================
// 主组件
// ============================================================

export const VirtualizedList = forwardRef<VirtualizedListRef, VirtualizedListProps>(({
  data,
  renderItem,
  height = 400,
  width = '100%',
  className = '',
  virtualizerConfig = {},
  selectedKeys = [],
  onSelectionChange,
  getItemKey,
  highlightedKey,
  onHighlight,
  loading = false,
  error = null,
  emptyText = '暂无数据',
  showToolbar = false,
  toolbarTitle,
  toolbarExtra,
  showPerformanceStats = false,
  onItemClick,
  onItemDoubleClick,
  itemClassName,
  containerStyle = {},
  responsive = true,
}, ref) => {
  
  const lastScrollTime = useRef(Date.now())
  const itemKeyMap = useRef<Map<string | number, number>>(new Map())
  
  // 构建键值索引映射
  useEffect(() => {
    itemKeyMap.current.clear()
    data.forEach((item, index) => {
      const key = getItemKey ? getItemKey(item, index) : index
      itemKeyMap.current.set(key, index)
    })
  }, [data, getItemKey])
  
  // 默认获取项目键值
  const defaultGetItemKey = useCallback((index: number, item: T) => {
    return getItemKey ? getItemKey(item, index) : index
  }, [getItemKey])
  
  // 虚拟化配置
  const finalVirtualizerConfig = useMemo((): VirtualizerConfig<T> => ({
    data,
    estimateSize: 56, // 默认行高
    overscan: 8,
    enableMeasureCache: true,
    cacheSize: 200,
    getItemKey: defaultGetItemKey,
    responsive: responsive ? {
      breakpoints: {
        xs: 0,
        sm: 576,
        md: 768,
        lg: 992,
        xl: 1200,
      },
      estimateSizes: {
        xs: 48,
        sm: 56,
        md: 64,
        lg: 72,
        xl: 80,
      },
    } : undefined,
    ...virtualizerConfig,
  }), [data, virtualizerConfig, defaultGetItemKey, responsive])
  
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
  } = useVirtualized(finalVirtualizerConfig)
  
  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    scrollToIndex: (index: number, align: 'start' | 'center' | 'end' = 'start') => {
      scrollToIndex(index, { align })
    },
    scrollToKey: (key: string | number) => {
      const index = itemKeyMap.current.get(key)
      if (index !== undefined) {
        scrollToIndex(index, { align: 'center' })
      }
    },
    scrollToTop,
    scrollToBottom,
    getStats: () => stats,
  }), [scrollToIndex, scrollToTop, scrollToBottom, stats])
  
  // 选中状态检查
  const isItemSelected = useCallback((item: T, index: number) => {
    const key = defaultGetItemKey(index, item)
    return selectedKeys.includes(key)
  }, [selectedKeys, defaultGetItemKey])
  
  // 高亮状态检查
  const isItemHighlighted = useCallback((item: T, index: number) => {
    const key = defaultGetItemKey(index, item)
    return key === highlightedKey
  }, [highlightedKey, defaultGetItemKey])
  
  // 项目点击处理
  const handleItemClick = useCallback((item: T, index: number, event: React.MouseEvent) => {
    const key = defaultGetItemKey(index, item)
    
    // 处理选中
    if (onSelectionChange) {
      let newSelectedKeys: (string | number)[]
      
      if (event.ctrlKey || event.metaKey) {
        // 多选模式
        if (selectedKeys.includes(key)) {
          newSelectedKeys = selectedKeys.filter(k => k !== key)
        } else {
          newSelectedKeys = [...selectedKeys, key]
        }
      } else if (event.shiftKey && selectedKeys.length > 0) {
        // 范围选择
        const lastSelectedIndex = itemKeyMap.current.get(selectedKeys[selectedKeys.length - 1])
        if (lastSelectedIndex !== undefined) {
          const start = Math.min(index, lastSelectedIndex)
          const end = Math.max(index, lastSelectedIndex)
          newSelectedKeys = []
          for (let i = start; i <= end; i++) {
            if (i < data.length) {
              const itemKey = defaultGetItemKey(i, data[i])
              newSelectedKeys.push(itemKey)
            }
          }
        } else {
          newSelectedKeys = [key]
        }
      } else {
        // 单选模式
        newSelectedKeys = [key]
      }
      
      const selectedItems = newSelectedKeys.map(k => {
        const idx = itemKeyMap.current.get(k)
        return idx !== undefined ? data[idx] : null
      }).filter(Boolean) as T[]
      
      onSelectionChange(newSelectedKeys, selectedItems)
    }
    
    // 处理高亮
    if (onHighlight) {
      onHighlight(key, item)
    }
    
    // 触发点击事件
    onItemClick?.(item, index)
  }, [defaultGetItemKey, onSelectionChange, selectedKeys, onHighlight, onItemClick, data])
  
  // 项目双击处理
  const handleItemDoubleClick = useCallback((item: T, index: number, event: React.MouseEvent) => {
    event.preventDefault()
    onItemDoubleClick?.(item, index)
  }, [onItemDoubleClick])
  
  // 生成项目样式类名
  const getItemClassName = useCallback((item: T, index: number) => {
    const isSelected = isItemSelected(item, index)
    const isHighlighted = isItemHighlighted(item, index)
    const isVisible = virtualItems.some(vi => vi.index === index)
    
    let className = 'virtualized-list-item'
    
    if (isSelected) className += ' selected'
    if (isHighlighted) className += ' highlighted'
    if (isVisible) className += ' visible'
    if (onItemClick) className += ' clickable'
    
    if (typeof itemClassName === 'function') {
      className += ' ' + itemClassName(item, index, isSelected, isHighlighted)
    } else if (itemClassName) {
      className += ' ' + itemClassName
    }
    
    return className
  }, [isItemSelected, isItemHighlighted, virtualItems, itemClassName, onItemClick])
  
  // 工具栏渲染
  const renderToolbar = useCallback(() => {
    if (!showToolbar) return null
    
    const hasSelection = selectedKeys.length > 0
    
    return (
      <div className="virtualized-list-toolbar" style={{ 
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
              已选择 {selectedKeys.length} 项
            </Text>
          )}
        </div>
        
        <Space>
          {toolbarExtra}
          
          <Tooltip title="回到顶部">
            <Button 
              size="small" 
              icon={<VerticalAlignTopOutlined />}
              onClick={scrollToTop}
            />
          </Tooltip>
          
          <Tooltip title="到底部">
            <Button 
              size="small"
              icon={<VerticalAlignBottomOutlined />}
              onClick={scrollToBottom}
            />
          </Tooltip>
          
          {showPerformanceStats && (
            <Tooltip title={`可见范围: ${stats.visibleRange[0]}-${stats.visibleRange[1]} / ${stats.totalCount}, 缓存命中率: ${stats.cacheHitRate.toFixed(1)}%`}>
              <Button size="small" icon={<DashboardOutlined />} />
            </Tooltip>
          )}
        </Space>
      </div>
    )
  }, [showToolbar, toolbarTitle, toolbarExtra, selectedKeys.length, scrollToTop, scrollToBottom, showPerformanceStats, stats])
  
  // 错误状态
  if (error) {
    return (
      <Card className={className} style={{ height, width, ...containerStyle }}>
        {renderToolbar()}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <Text type="danger">加载数据时出现错误: {error}</Text>
        </div>
      </Card>
    )
  }
  
  // 空数据状态
  if (!loading && data.length === 0) {
    return (
      <Card className={className} style={{ height, width, ...containerStyle }}>
        {renderToolbar()}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <Empty description={emptyText} />
        </div>
      </Card>
    )
  }
  
  return (
    <Card 
      className={`virtualized-list ${className}`} 
      style={{ height, width, ...containerStyle }}
      bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      {renderToolbar()}
      
      <div style={{ flex: 1, position: 'relative' }}>
        <Spin spinning={loading}>
          <div
            ref={parentRef}
            style={{
              height: showToolbar ? 'calc(100% - 60px)' : '100%',
              width: '100%',
              overflow: 'auto',
            }}
            className="virtualized-list-container"
          >
            <div
              style={{
                height: `${totalSize}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              <AnimatePresence>
                {virtualItems.map((virtualItem) => {
                  const item = virtualItem.item
                  const isSelected = isItemSelected(item, virtualItem.index)
                  const isHighlighted = isItemHighlighted(item, virtualItem.index)
                  
                  return (
                    <motion.div
                      key={virtualItem.key}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.15 }}
                      data-index={virtualItem.index}
                      className={getItemClassName(item, virtualItem.index)}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: `${virtualItem.size}px`,
                        transform: `translateY(${virtualItem.start}px)`,
                        cursor: onItemClick ? 'pointer' : 'default',
                        backgroundColor: isSelected ? '#e6f7ff' : isHighlighted ? '#fff7e6' : 'transparent',
                        borderLeft: isSelected ? '3px solid #1890ff' : isHighlighted ? '3px solid #faad14' : '3px solid transparent',
                        transition: isScrolling ? 'none' : 'background-color 0.2s, border-color 0.2s',
                      }}
                      onClick={(e) => handleItemClick(item, virtualItem.index, e)}
                      onDoubleClick={(e) => handleItemDoubleClick(item, virtualItem.index, e)}
                    >
                      {renderItem(item, virtualItem.index, true)}
                    </motion.div>
                  )
                })}
              </AnimatePresence>
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

VirtualizedList.displayName = 'VirtualizedList'

export default VirtualizedList