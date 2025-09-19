/**
 * 虚拟化树组件 - 用于大型文件树和层级数据
 * 支持懒加载、动态展开折叠、搜索过滤等功能
 */

import React, { useMemo, useCallback, forwardRef, useImperativeHandle, useState, useRef } from 'react'
import { Card, Spin, Empty, Button, Input, Space, Typography, Tooltip, Tag } from 'antd'
import { 
  SearchOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  FileOutlined,
  DownOutlined,
  RightOutlined,
  VerticalAlignTopOutlined,
  VerticalAlignBottomOutlined,
  ReloadOutlined,
  ExpandAltOutlined,
  ShrinkOutlined,
} from '@ant-design/icons'
import { useVirtualized, TREE_NODE_CONFIG } from './useVirtualizer'
import { motion, AnimatePresence } from 'framer-motion'

const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

export interface TreeNode<T = any> {
  id: string
  label: string
  data?: T
  children?: TreeNode<T>[]
  isLeaf?: boolean
  expanded?: boolean
  level?: number
  parent?: TreeNode<T>
  icon?: React.ReactNode
  disabled?: boolean
  checkable?: boolean
  checked?: boolean
  indeterminate?: boolean
}

export interface VirtualizedTreeProps<T = any> {
  // 数据
  data: TreeNode<T>[]
  
  // 基础配置
  height?: number | string
  width?: number | string
  className?: string
  
  // 虚拟化配置
  nodeHeight?: number | ((node: TreeNode<T>, level: number) => number)
  overscan?: number
  
  // 展开折叠
  expandedKeys?: string[]
  onExpandedKeysChange?: (expandedKeys: string[]) => void
  defaultExpandAll?: boolean
  defaultExpandedKeys?: string[]
  
  // 选择功能
  selectable?: boolean
  selectedKeys?: string[]
  onSelectionChange?: (selectedKeys: string[], selectedNodes: TreeNode<T>[]) => void
  
  // 勾选功能
  checkable?: boolean
  checkedKeys?: string[]
  onCheckedKeysChange?: (checkedKeys: string[], checkedNodes: TreeNode<T>[]) => void
  
  // 搜索功能
  searchable?: boolean
  searchValue?: string
  onSearchChange?: (value: string) => void
  filterTreeNode?: (node: TreeNode<T>, searchValue: string) => boolean
  
  // 懒加载
  loadData?: (node: TreeNode<T>) => Promise<TreeNode<T>[]>
  
  // 拖拽
  draggable?: boolean
  onDragStart?: (info: { node: TreeNode<T>; event: React.DragEvent }) => void
  onDragEnter?: (info: { node: TreeNode<T>; event: React.DragEvent }) => void
  onDragOver?: (info: { node: TreeNode<T>; event: React.DragEvent }) => void
  onDrop?: (info: { 
    dragNode: TreeNode<T>
    dropNode: TreeNode<T>
    dropPosition: number
    event: React.DragEvent 
  }) => void
  
  // 自定义渲染
  renderTreeNode?: (node: TreeNode<T>, level: number) => React.ReactNode
  renderIcon?: (node: TreeNode<T>, expanded: boolean) => React.ReactNode
  
  // UI状态
  loading?: boolean
  error?: string | null
  emptyText?: string
  
  // 工具栏
  showToolbar?: boolean
  toolbarTitle?: string
  toolbarExtra?: React.ReactNode
  
  // 事件
  onNodeClick?: (node: TreeNode<T>) => void
  onNodeDoubleClick?: (node: TreeNode<T>) => void
  onNodeRightClick?: (node: TreeNode<T>, event: React.MouseEvent) => void
  
  // 样式
  indent?: number
  showLine?: boolean
  showIcon?: boolean
  
  // 性能
  showPerformanceStats?: boolean
  
  // 响应式
  responsive?: boolean
}

export interface VirtualizedTreeRef<T = any> {
  scrollToNode: (nodeId: string, align?: 'start' | 'center' | 'end') => void
  scrollToTop: () => void
  scrollToBottom: () => void
  expandAll: () => void
  collapseAll: () => void
  getSelectedNodes: () => TreeNode<T>[]
  getCheckedNodes: () => TreeNode<T>[]
  getExpandedNodes: () => TreeNode<T>[]
  getStats: () => any
}

// ============================================================
// 工具函数
// ============================================================

function flattenTree<T>(
  nodes: TreeNode<T>[], 
  expandedKeys: Set<string>, 
  level = 0,
  parent?: TreeNode<T>
): TreeNode<T>[] {
  const result: TreeNode<T>[] = []
  
  for (const node of nodes) {
    const nodeWithLevel = { ...node, level, parent }
    result.push(nodeWithLevel)
    
    if (node.children && expandedKeys.has(node.id)) {
      result.push(...flattenTree(node.children, expandedKeys, level + 1, nodeWithLevel))
    }
  }
  
  return result
}

function searchTree<T>(
  nodes: TreeNode<T>[], 
  searchValue: string, 
  filterFunc?: (node: TreeNode<T>, searchValue: string) => boolean
): TreeNode<T>[] {
  if (!searchValue) return nodes
  
  const defaultFilter = (node: TreeNode<T>, value: string) => 
    node.label.toLowerCase().includes(value.toLowerCase())
  
  const filter = filterFunc || defaultFilter
  
  const filterNode = (node: TreeNode<T>): TreeNode<T> | null => {
    const children = node.children?.map(filterNode).filter(Boolean) as TreeNode<T>[] || []
    
    if (filter(node, searchValue) || children.length > 0) {
      return {
        ...node,
        children: children.length > 0 ? children : undefined,
        expanded: children.length > 0 ? true : node.expanded
      }
    }
    
    return null
  }
  
  return nodes.map(filterNode).filter(Boolean) as TreeNode<T>[]
}

// ============================================================
// 主组件
// ============================================================

export const VirtualizedTree = forwardRef<VirtualizedTreeRef, VirtualizedTreeProps>(({
  data,
  height = 400,
  width = '100%',
  className = '',
  nodeHeight = 32,
  overscan = 15,
  expandedKeys: externalExpandedKeys,
  onExpandedKeysChange,
  defaultExpandAll = false,
  defaultExpandedKeys = [],
  selectable = false,
  selectedKeys = [],
  onSelectionChange,
  checkable = false,
  checkedKeys = [],
  onCheckedKeysChange,
  searchable = true,
  searchValue = '',
  onSearchChange,
  filterTreeNode,
  loadData,
  draggable = false,
  onDragStart,
  onDragEnter,
  onDragOver,
  onDrop,
  renderTreeNode,
  renderIcon,
  loading = false,
  error = null,
  emptyText = '暂无数据',
  showToolbar = true,
  toolbarTitle,
  toolbarExtra,
  onNodeClick,
  onNodeDoubleClick,
  onNodeRightClick,
  indent = 24,
  showLine = true,
  showIcon = true,
  showPerformanceStats = false,
  responsive = true,
}, ref) => {
  
  // 内部状态
  const [internalExpandedKeys, setInternalExpandedKeys] = useState<string[]>(() => {
    if (defaultExpandAll) {
      const getAllKeys = (nodes: TreeNode[]): string[] => {
        let keys: string[] = []
        for (const node of nodes) {
          keys.push(node.id)
          if (node.children) {
            keys.push(...getAllKeys(node.children))
          }
        }
        return keys
      }
      return getAllKeys(data)
    }
    return defaultExpandedKeys
  })
  
  const [internalSearchValue, setInternalSearchValue] = useState(searchValue)
  
  // 状态管理
  const expandedKeys = externalExpandedKeys ?? internalExpandedKeys
  const currentSearchValue = searchValue || internalSearchValue
  
  const expandedKeysSet = useMemo(() => new Set(expandedKeys), [expandedKeys])
  const selectedKeysSet = useMemo(() => new Set(selectedKeys), [selectedKeys])
  const checkedKeysSet = useMemo(() => new Set(checkedKeys), [checkedKeys])
  
  // 过滤和展平数据
  const flattenedNodes = useMemo(() => {
    const filteredData = searchTree(data, currentSearchValue, filterTreeNode)
    return flattenTree(filteredData, expandedKeysSet)
  }, [data, expandedKeysSet, currentSearchValue, filterTreeNode])
  
  // 节点ID到索引的映射
  const nodeIdToIndexMap = useMemo(() => {
    const map = new Map<string, number>()
    flattenedNodes.forEach((node, index) => {
      map.set(node.id, index)
    })
    return map
  }, [flattenedNodes])
  
  // 计算节点高度
  const calculateNodeHeight = useCallback((index: number) => {
    const node = flattenedNodes[index]
    if (typeof nodeHeight === 'function') {
      return nodeHeight(node, node.level || 0)
    }
    return nodeHeight
  }, [nodeHeight, flattenedNodes])
  
  // 虚拟化配置
  const virtualizerConfig = useMemo(() => ({
    ...TREE_NODE_CONFIG,
    data: flattenedNodes,
    estimateSize: calculateNodeHeight,
    overscan,
    getItemKey: (index: number) => flattenedNodes[index]?.id || `node-${index}`,
    responsive: responsive ? {
      breakpoints: { xs: 0, sm: 576, md: 768, lg: 992, xl: 1200 },
      estimateSizes: { xs: 28, sm: 32, md: 36, lg: 40, xl: 44 },
    } : undefined,
  }), [flattenedNodes, calculateNodeHeight, overscan, responsive])
  
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
  
  // 暴露的方法
  useImperativeHandle(ref, () => ({
    scrollToNode: (nodeId: string, align: 'start' | 'center' | 'end' = 'center') => {
      const index = nodeIdToIndexMap.get(nodeId)
      if (index !== undefined) {
        scrollToIndex(index, { align })
      }
    },
    scrollToTop,
    scrollToBottom,
    expandAll: () => {
      const getAllKeys = (nodes: TreeNode[]): string[] => {
        let keys: string[] = []
        for (const node of nodes) {
          if (node.children && node.children.length > 0) {
            keys.push(node.id)
            keys.push(...getAllKeys(node.children))
          }
        }
        return keys
      }
      const allKeys = getAllKeys(data)
      onExpandedKeysChange ? onExpandedKeysChange(allKeys) : setInternalExpandedKeys(allKeys)
    },
    collapseAll: () => {
      onExpandedKeysChange ? onExpandedKeysChange([]) : setInternalExpandedKeys([])
    },
    getSelectedNodes: () => flattenedNodes.filter(node => selectedKeysSet.has(node.id)),
    getCheckedNodes: () => flattenedNodes.filter(node => checkedKeysSet.has(node.id)),
    getExpandedNodes: () => flattenedNodes.filter(node => expandedKeysSet.has(node.id)),
    getStats: () => stats,
  }), [data, flattenedNodes, nodeIdToIndexMap, selectedKeysSet, checkedKeysSet, expandedKeysSet, stats, scrollToIndex, scrollToTop, scrollToBottom, onExpandedKeysChange])
  
  // 事件处理
  const handleNodeExpand = useCallback((node: TreeNode) => {
    const newExpandedKeys = expandedKeysSet.has(node.id) 
      ? expandedKeys.filter(key => key !== node.id)
      : [...expandedKeys, node.id]
    
    onExpandedKeysChange ? onExpandedKeysChange(newExpandedKeys) : setInternalExpandedKeys(newExpandedKeys)
  }, [expandedKeys, expandedKeysSet, onExpandedKeysChange])
  
  const handleNodeClick = useCallback((node: TreeNode, event: React.MouseEvent) => {
    // 处理选择
    if (selectable && onSelectionChange) {
      let newSelectedKeys: string[]
      
      if (event.ctrlKey || event.metaKey) {
        // 多选
        newSelectedKeys = selectedKeysSet.has(node.id)
          ? selectedKeys.filter(key => key !== node.id)
          : [...selectedKeys, node.id]
      } else {
        // 单选
        newSelectedKeys = [node.id]
      }
      
      const selectedNodes = flattenedNodes.filter(n => newSelectedKeys.includes(n.id))
      onSelectionChange(newSelectedKeys, selectedNodes)
    }
    
    onNodeClick?.(node)
  }, [selectable, selectedKeys, selectedKeysSet, onSelectionChange, flattenedNodes, onNodeClick])
  
  const handleSearchChange = useCallback((value: string) => {
    onSearchChange ? onSearchChange(value) : setInternalSearchValue(value)
  }, [onSearchChange])
  
  // 渲染默认节点图标
  const renderDefaultIcon = useCallback((node: TreeNode, expanded: boolean) => {
    if (renderIcon) {
      return renderIcon(node, expanded)
    }
    
    if (node.icon) {
      return node.icon
    }
    
    if (node.isLeaf !== false && (!node.children || node.children.length === 0)) {
      return <FileOutlined style={{ color: '#1890ff' }} />
    }
    
    return expanded ? 
      <FolderOpenOutlined style={{ color: '#faad14' }} /> : 
      <FolderOutlined style={{ color: '#faad14' }} />
  }, [renderIcon])
  
  // 渲染默认节点内容
  const renderDefaultNode = useCallback((node: TreeNode, level: number) => {
    const isExpanded = expandedKeysSet.has(node.id)
    const isSelected = selectedKeysSet.has(node.id)
    const isChecked = checkedKeysSet.has(node.id)
    const hasChildren = node.children && node.children.length > 0
    
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          paddingLeft: level * indent,
          height: '100%',
          cursor: 'pointer',
          backgroundColor: isSelected ? '#e6f7ff' : 'transparent',
        }}
        onClick={(e) => handleNodeClick(node, e)}
        onDoubleClick={() => onNodeDoubleClick?.(node)}
        onContextMenu={(e) => {
          e.preventDefault()
          onNodeRightClick?.(node, e)
        }}
      >
        {/* 展开/折叠图标 */}
        <div
          style={{
            width: 16,
            height: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: 4,
            cursor: hasChildren ? 'pointer' : 'default',
          }}
          onClick={(e) => {
            e.stopPropagation()
            if (hasChildren) {
              handleNodeExpand(node)
            }
          }}
        >
          {hasChildren && (
            isExpanded ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />
          )}
        </div>
        
        {/* 节点图标 */}
        {showIcon && (
          <div style={{ marginRight: 8, display: 'flex', alignItems: 'center' }}>
            {renderDefaultIcon(node, isExpanded)}
          </div>
        )}
        
        {/* 节点标签 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text 
            ellipsis={{ tooltip: node.label }}
            style={{ 
              fontWeight: isSelected ? 600 : 400,
              color: node.disabled ? '#bfbfbf' : undefined,
            }}
          >
            {node.label}
          </Text>
        </div>
        
        {/* 额外信息 */}
        {node.data && (
          <div style={{ marginLeft: 8 }}>
            <Tag size="small">{String(node.data)}</Tag>
          </div>
        )}
      </div>
    )
  }, [expandedKeysSet, selectedKeysSet, checkedKeysSet, indent, showIcon, handleNodeClick, handleNodeExpand, onNodeDoubleClick, onNodeRightClick, renderDefaultIcon])
  
  // 工具栏渲染
  const renderToolbar = useCallback(() => {
    if (!showToolbar) return null
    
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 12px',
        borderBottom: '1px solid #f0f0f0',
        backgroundColor: '#fafafa',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {toolbarTitle && (
            <Text strong>{toolbarTitle}</Text>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {flattenedNodes.length} 个节点
          </Text>
        </div>
        
        <Space>
          {/* 搜索框 */}
          {searchable && (
            <Input
              placeholder="搜索节点..."
              prefix={<SearchOutlined />}
              value={currentSearchValue}
              onChange={(e) => handleSearchChange(e.target.value)}
              style={{ width: 200 }}
              allowClear
              size="small"
            />
          )}
          
          {toolbarExtra}
          
          {/* 展开/折叠控制 */}
          <Space.Compact size="small">
            <Tooltip title="展开全部">
              <Button 
                icon={<ExpandAltOutlined />} 
                onClick={() => ref?.current?.expandAll?.()} 
              />
            </Tooltip>
            <Tooltip title="折叠全部">
              <Button 
                icon={<ShrinkOutlined />}
                onClick={() => ref?.current?.collapseAll?.()} 
              />
            </Tooltip>
          </Space.Compact>
          
          {/* 滚动控制 */}
          <Space.Compact size="small">
            <Tooltip title="回到顶部">
              <Button icon={<VerticalAlignTopOutlined />} onClick={scrollToTop} />
            </Tooltip>
            <Tooltip title="到底部">
              <Button icon={<VerticalAlignBottomOutlined />} onClick={scrollToBottom} />
            </Tooltip>
          </Space.Compact>
          
          {showPerformanceStats && (
            <Tooltip title={`可见: ${stats.visibleRange[0]}-${stats.visibleRange[1]} / ${stats.totalCount}`}>
              <Button size="small">
                {stats.renderedCount}/{stats.totalCount}
              </Button>
            </Tooltip>
          )}
        </Space>
      </div>
    )
  }, [showToolbar, toolbarTitle, toolbarExtra, flattenedNodes.length, searchable, currentSearchValue, handleSearchChange, scrollToTop, scrollToBottom, showPerformanceStats, stats])
  
  // 错误和空状态处理
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
  
  if (!loading && flattenedNodes.length === 0) {
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
      className={`virtualized-tree ${className}`}
      style={{ height, width }}
      bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      {renderToolbar()}
      
      <div style={{ flex: 1, position: 'relative' }}>
        <Spin spinning={loading}>
          <div
            ref={parentRef}
            style={{
              height: '100%',
              overflow: 'auto',
            }}
          >
            <div style={{ height: `${totalSize}px`, width: '100%', position: 'relative' }}>
              <AnimatePresence>
                {virtualItems.map((virtualItem) => {
                  const node = virtualItem.item
                  
                  return (
                    <motion.div
                      key={virtualItem.key}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      transition={{ duration: 0.1 }}
                      data-index={virtualItem.index}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: `${virtualItem.size}px`,
                        transform: `translateY(${virtualItem.start}px)`,
                        borderBottom: showLine ? '1px solid #f0f0f0' : undefined,
                      }}
                    >
                      {renderTreeNode ? renderTreeNode(node, node.level || 0) : renderDefaultNode(node, node.level || 0)}
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
            滚动中... ({stats.visibleRange[0]}-{stats.visibleRange[1]})
          </div>
        )}
      </div>
    </Card>
  )
})

VirtualizedTree.displayName = 'VirtualizedTree'

export default VirtualizedTree