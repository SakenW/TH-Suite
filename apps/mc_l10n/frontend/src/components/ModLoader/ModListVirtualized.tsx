/**
 * 虚拟化MOD列表组件 - 基于@tanstack/react-virtual
 * 支持大数据量MOD列表的高性能渲染
 */

import React, { useState, useMemo, useCallback, useRef } from 'react'
import { 
  Input, 
  Select, 
  Space, 
  Empty, 
  Button,
  Tooltip,
  Typography,
  Row,
  Col,
  Tag,
  Switch,
  Card,
  Dropdown,
  Badge,
  MenuProps
} from 'antd'
import { 
  SearchOutlined, 
  FilterOutlined, 
  SortAscendingOutlined,
  SortDescendingOutlined,
  AppstoreOutlined,
  BarsOutlined,
  ReloadOutlined,
  ClearOutlined,
  MoreOutlined
} from '@ant-design/icons'
import VirtualizedList, { VirtualizedListRef } from '../virtualization/VirtualizedList'
import { ModInfo, ModInfoCard } from './ModInfoCard'
import { LIST_ITEM_CONFIG } from '../virtualization/useVirtualizer'

const { Search } = Input
const { Option } = Select
const { Text } = Typography

// ============================================================
// 类型定义
// ============================================================

interface ModListVirtualizedProps {
  mods: ModInfo[]
  loading?: boolean
  onRefresh?: () => void
  onModClick?: (mod: ModInfo, index: number) => void
  onModDoubleClick?: (mod: ModInfo, index: number) => void
  onModsExport?: (mods: ModInfo[]) => void
  className?: string
  height?: number | string
  
  // 选择功能
  selectable?: boolean
  selectedModIds?: string[]
  onSelectionChange?: (selectedIds: string[], selectedMods: ModInfo[]) => void
  
  // 高亮功能
  highlightedModId?: string
  onHighlight?: (modId: string, mod: ModInfo) => void
}

type SortBy = 'name' | 'version' | 'loader_type' | 'file_size' | 'minecraft_version' | 'author'
type SortOrder = 'asc' | 'desc'
type ViewMode = 'card' | 'compact' | 'list'

interface FilterState {
  searchText: string
  loaderType: string
  minecraftVersion: string
  author: string
  hasTranslations: 'all' | 'yes' | 'no'
}

// ============================================================
// 主组件
// ============================================================

export const ModListVirtualized: React.FC<ModListVirtualizedProps> = ({ 
  mods = [], 
  loading = false, 
  onRefresh,
  onModClick,
  onModDoubleClick,
  onModsExport,
  className = '',
  height = 600,
  selectable = false,
  selectedModIds = [],
  onSelectionChange,
  highlightedModId,
  onHighlight
}) => {
  const virtualizerRef = useRef<VirtualizedListRef>(null)
  
  // 过滤和排序状态
  const [filters, setFilters] = useState<FilterState>({
    searchText: '',
    loaderType: 'all',
    minecraftVersion: 'all',
    author: 'all',
    hasTranslations: 'all',
  })
  
  const [sortBy, setSortBy] = useState<SortBy>('name')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')
  const [viewMode, setViewMode] = useState<ViewMode>('card')
  
  // 获取唯一值列表用于过滤器
  const filterOptions = useMemo(() => ({
    loaderTypes: [...new Set(mods.map(mod => mod.loader_type))].sort(),
    minecraftVersions: [...new Set(mods.map(mod => mod.minecraft_version).filter(Boolean))].sort(),
    authors: [...new Set(mods.flatMap(mod => mod.authors))].sort(),
  }), [mods])
  
  // 过滤和排序逻辑
  const filteredAndSortedMods = useMemo(() => {
    let filtered = mods
    
    // 文本搜索
    if (filters.searchText) {
      const searchTerm = filters.searchText.toLowerCase()
      filtered = filtered.filter(mod =>
        mod.name.toLowerCase().includes(searchTerm) ||
        mod.mod_id.toLowerCase().includes(searchTerm) ||
        mod.description?.toLowerCase().includes(searchTerm) ||
        mod.authors.some(author => author.toLowerCase().includes(searchTerm))
      )
    }
    
    // 加载器类型过滤
    if (filters.loaderType !== 'all') {
      filtered = filtered.filter(mod => mod.loader_type === filters.loaderType)
    }
    
    // Minecraft版本过滤
    if (filters.minecraftVersion !== 'all') {
      filtered = filtered.filter(mod => mod.minecraft_version === filters.minecraftVersion)
    }
    
    // 作者过滤
    if (filters.author !== 'all') {
      filtered = filtered.filter(mod => mod.authors.includes(filters.author))
    }
    
    // 翻译状态过滤
    if (filters.hasTranslations !== 'all') {
      const hasTranslations = filters.hasTranslations === 'yes'
      filtered = filtered.filter(mod => {
        const modHasTranslations = mod.language_files && mod.language_files.length > 0
        return modHasTranslations === hasTranslations
      })
    }
    
    // 排序
    return [...filtered].sort((a, b) => {
      let compareValue = 0
      
      switch (sortBy) {
        case 'name':
          compareValue = a.name.localeCompare(b.name, 'zh-CN')
          break
        case 'version':
          compareValue = a.version.localeCompare(b.version)
          break
        case 'loader_type':
          compareValue = a.loader_type.localeCompare(b.loader_type)
          break
        case 'file_size':
          compareValue = (a.file_size || 0) - (b.file_size || 0)
          break
        case 'minecraft_version':
          compareValue = (a.minecraft_version || '').localeCompare(b.minecraft_version || '')
          break
        case 'author':
          compareValue = (a.authors[0] || '').localeCompare(b.authors[0] || '', 'zh-CN')
          break
      }
      
      return sortOrder === 'asc' ? compareValue : -compareValue
    })
  }, [mods, filters, sortBy, sortOrder])
  
  // 过滤器更新函数
  const updateFilter = useCallback((key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }, [])
  
  // 重置过滤器
  const resetFilters = useCallback(() => {
    setFilters({
      searchText: '',
      loaderType: 'all',
      minecraftVersion: 'all',
      author: 'all',
      hasTranslations: 'all',
    })
    setSortBy('name')
    setSortOrder('asc')
  }, [])
  
  // 切换排序顺序
  const toggleSortOrder = useCallback(() => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
  }, [])
  
  // 检查是否有活动过滤器
  const hasActiveFilters = useMemo(() => {
    return filters.searchText || 
           filters.loaderType !== 'all' || 
           filters.minecraftVersion !== 'all' ||
           filters.author !== 'all' ||
           filters.hasTranslations !== 'all'
  }, [filters])
  
  // MOD项目渲染函数
  const renderModItem = useCallback((mod: ModInfo, index: number, isVisible: boolean) => {
    if (!isVisible) {
      // 非可见项目返回占位符
      return <div style={{ height: viewMode === 'compact' ? 64 : viewMode === 'list' ? 48 : 120 }} />
    }
    
    return (
      <div style={{ padding: '4px 8px' }}>
        <ModInfoCard 
          mod={mod} 
          compact={viewMode === 'compact'} 
          listMode={viewMode === 'list'}
          onClick={() => onModClick?.(mod, index)}
          onDoubleClick={() => onModDoubleClick?.(mod, index)}
        />
      </div>
    )
  }, [viewMode, onModClick, onModDoubleClick])
  
  // 获取MOD的唯一键
  const getModKey = useCallback((mod: ModInfo, index: number) => {
    return mod.mod_id || `mod-${index}`
  }, [])
  
  // 选择变更处理
  const handleSelectionChange = useCallback((selectedKeys: (string | number)[], selectedMods: ModInfo[]) => {
    if (onSelectionChange) {
      onSelectionChange(selectedKeys as string[], selectedMods)
    }
  }, [onSelectionChange])
  
  // 高亮处理
  const handleHighlight = useCallback((key: string | number, mod: ModInfo) => {
    if (onHighlight) {
      onHighlight(key as string, mod)
    }
  }, [onHighlight])
  
  // 虚拟化配置
  const virtualizerConfig = useMemo(() => ({
    ...LIST_ITEM_CONFIG,
    estimateSize: viewMode === 'compact' ? 72 : viewMode === 'list' ? 56 : 128,
    overscan: viewMode === 'list' ? 15 : 8,
  }), [viewMode])
  
  // 工具栏额外操作
  const toolbarExtra = useMemo(() => (
    <Space>
      {/* 导出按钮 */}
      {onModsExport && (
        <Button 
          onClick={() => onModsExport(filteredAndSortedMods)}
          disabled={filteredAndSortedMods.length === 0}
        >
          导出MOD列表
        </Button>
      )}
      
      {/* 视图模式切换 */}
      <Dropdown
        menu={{
          selectedKeys: [viewMode],
          onClick: ({ key }) => setViewMode(key as ViewMode),
          items: [
            { key: 'card', label: '卡片视图', icon: <AppstoreOutlined /> },
            { key: 'compact', label: '紧凑视图', icon: <BarsOutlined /> },
            { key: 'list', label: '列表视图', icon: <BarsOutlined /> },
          ],
        }}
        trigger={['click']}
      >
        <Button>
          视图 {viewMode === 'card' ? <AppstoreOutlined /> : <BarsOutlined />}
        </Button>
      </Dropdown>
      
      {/* 刷新按钮 */}
      {onRefresh && (
        <Tooltip title="刷新MOD列表">
          <Button 
            icon={<ReloadOutlined />}
            onClick={onRefresh}
            loading={loading}
          />
        </Tooltip>
      )}
    </Space>
  ), [onModsExport, filteredAndSortedMods, viewMode, onRefresh, loading])
  
  return (
    <div className={`mod-list-virtualized ${className}`}>
      {/* 过滤和排序控件 */}
      <Card className="mb-4" bodyStyle={{ padding: '16px' }}>
        <Row gutter={[16, 16]} align="middle">
          {/* 搜索框 */}
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="搜索MOD名称、ID、描述或作者..."
              value={filters.searchText}
              onChange={(e) => updateFilter('searchText', e.target.value)}
              allowClear
            />
          </Col>
          
          {/* 加载器过滤 */}
          <Col xs={12} sm={6} md={3}>
            <Select
              value={filters.loaderType}
              onChange={(value) => updateFilter('loaderType', value)}
              style={{ width: '100%' }}
              placeholder="加载器"
            >
              <Option value="all">全部加载器</Option>
              {filterOptions.loaderTypes.map(type => (
                <Option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Option>
              ))}
            </Select>
          </Col>
          
          {/* MC版本过滤 */}
          <Col xs={12} sm={6} md={3}>
            <Select
              value={filters.minecraftVersion}
              onChange={(value) => updateFilter('minecraftVersion', value)}
              style={{ width: '100%' }}
              placeholder="MC版本"
            >
              <Option value="all">全部版本</Option>
              {filterOptions.minecraftVersions.map(version => (
                <Option key={version} value={version}>
                  {version}
                </Option>
              ))}
            </Select>
          </Col>
          
          {/* 作者过滤 */}
          <Col xs={12} sm={6} md={3}>
            <Select
              value={filters.author}
              onChange={(value) => updateFilter('author', value)}
              style={{ width: '100%' }}
              placeholder="作者"
              showSearch
            >
              <Option value="all">全部作者</Option>
              {filterOptions.authors.slice(0, 50).map(author => (
                <Option key={author} value={author}>
                  {author}
                </Option>
              ))}
            </Select>
          </Col>
          
          {/* 排序方式 */}
          <Col xs={12} sm={6} md={3}>
            <Select
              value={sortBy}
              onChange={(value: SortBy) => setSortBy(value)}
              style={{ width: '100%' }}
            >
              <Option value="name">按名称</Option>
              <Option value="version">按版本</Option>
              <Option value="loader_type">按加载器</Option>
              <Option value="file_size">按大小</Option>
              <Option value="minecraft_version">按MC版本</Option>
              <Option value="author">按作者</Option>
            </Select>
          </Col>
          
          {/* 排序顺序和控制按钮 */}
          <Col xs={12} sm={6} md={2}>
            <Space>
              <Tooltip title={`${sortOrder === 'asc' ? '升序' : '降序'}排列`}>
                <Button 
                  icon={sortOrder === 'asc' ? <SortAscendingOutlined /> : <SortDescendingOutlined />}
                  onClick={toggleSortOrder}
                />
              </Tooltip>
            </Space>
          </Col>
        </Row>
        
        {/* 过滤器状态和统计 */}
        <Row justify="space-between" align="middle" className="mt-3 pt-3 border-t border-gray-200">
          <Col>
            <Space>
              <Text type="secondary">
                显示 {filteredAndSortedMods.length} / {mods.length} 个MOD
              </Text>
              
              {hasActiveFilters && (
                <Button 
                  type="link" 
                  size="small"
                  onClick={resetFilters}
                  icon={<ClearOutlined />}
                >
                  清除筛选
                </Button>
              )}
            </Space>
          </Col>
          
          <Col>
            <Space>
              <Text type="secondary">视图模式:</Text>
              <Switch 
                checked={viewMode === 'compact'}
                onChange={(checked) => setViewMode(checked ? 'compact' : 'card')}
                size="small"
              />
            </Space>
          </Col>
        </Row>
        
        {/* 活跃过滤器标签 */}
        {hasActiveFilters && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>活跃筛选：</Text>
            <Space size={[4, 4]} wrap>
              {filters.searchText && (
                <Tag closable onClose={() => updateFilter('searchText', '')} color="blue">
                  搜索: {filters.searchText}
                </Tag>
              )}
              {filters.loaderType !== 'all' && (
                <Tag closable onClose={() => updateFilter('loaderType', 'all')} color="green">
                  加载器: {filters.loaderType}
                </Tag>
              )}
              {filters.minecraftVersion !== 'all' && (
                <Tag closable onClose={() => updateFilter('minecraftVersion', 'all')} color="orange">
                  版本: {filters.minecraftVersion}
                </Tag>
              )}
              {filters.author !== 'all' && (
                <Tag closable onClose={() => updateFilter('author', 'all')} color="purple">
                  作者: {filters.author}
                </Tag>
              )}
              {filters.hasTranslations !== 'all' && (
                <Tag closable onClose={() => updateFilter('hasTranslations', 'all')} color="cyan">
                  翻译: {filters.hasTranslations === 'yes' ? '已翻译' : '未翻译'}
                </Tag>
              )}
            </Space>
          </div>
        )}
      </Card>
      
      {/* 虚拟化列表 */}
      <VirtualizedList
        ref={virtualizerRef}
        data={filteredAndSortedMods}
        renderItem={renderModItem}
        height={height}
        loading={loading}
        emptyText={hasActiveFilters ? '没有找到符合条件的MOD' : '暂无MOD数据'}
        getItemKey={getModKey}
        selectedKeys={selectable ? selectedModIds : undefined}
        onSelectionChange={selectable ? handleSelectionChange : undefined}
        highlightedKey={highlightedModId}
        onHighlight={onHighlight ? handleHighlight : undefined}
        showToolbar={true}
        toolbarTitle={`MOD列表 (${filteredAndSortedMods.length})`}
        toolbarExtra={toolbarExtra}
        showPerformanceStats={(import.meta as any).env?.MODE === 'development'}
        virtualizerConfig={virtualizerConfig}
        responsive={true}
      />
    </div>
  )
}

export default ModListVirtualized