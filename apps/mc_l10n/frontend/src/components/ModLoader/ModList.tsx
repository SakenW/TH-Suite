import React, { useState, useMemo } from 'react'
import { 
  List, 
  Input, 
  Select, 
  Space, 
  Card, 
  Empty, 
  Spin, 
  Button,
  Tooltip,
  Typography,
  Row,
  Col,
  Tag,
  Switch
} from 'antd'
import { 
  SearchOutlined, 
  FilterOutlined, 
  SortAscendingOutlined,
  SortDescendingOutlined,
  AppstoreOutlined,
  BarsOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { ModInfo, ModInfoCard } from './ModInfoCard'

const { Search } = Input
const { Option } = Select
const { Text } = Typography

interface ModListProps {
  mods: ModInfo[]
  loading?: boolean
  onRefresh?: () => void
  className?: string
}

type SortBy = 'name' | 'version' | 'loader_type' | 'file_size' | 'minecraft_version'
type SortOrder = 'asc' | 'desc'

export const ModList: React.FC<ModListProps> = ({ 
  mods = [], 
  loading = false, 
  onRefresh,
  className = '' 
}) => {
  const [searchText, setSearchText] = useState('')
  const [filterLoader, setFilterLoader] = useState<string>('all')
  const [filterMinecraftVersion, setFilterMinecraftVersion] = useState<string>('all')
  const [sortBy, setSortBy] = useState<SortBy>('name')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')
  const [compactView, setCompactView] = useState(false)

  // 获取唯一的加载器类型
  const loaderTypes = useMemo(() => {
    const types = [...new Set(mods.map(mod => mod.loader_type))]
    return types.sort()
  }, [mods])

  // 获取唯一的Minecraft版本
  const minecraftVersions = useMemo(() => {
    const versions = [...new Set(mods.map(mod => mod.minecraft_version).filter(Boolean))]
    return versions.sort()
  }, [mods])

  // 过滤和排序逻辑
  const filteredAndSortedMods = useMemo(() => {
    let filtered = mods

    // 搜索过滤
    if (searchText) {
      const lowerSearchText = searchText.toLowerCase()
      filtered = filtered.filter(mod =>
        mod.name.toLowerCase().includes(lowerSearchText) ||
        mod.mod_id.toLowerCase().includes(lowerSearchText) ||
        mod.description?.toLowerCase().includes(lowerSearchText) ||
        mod.authors.some(author => author.toLowerCase().includes(lowerSearchText))
      )
    }

    // 加载器类型过滤
    if (filterLoader !== 'all') {
      filtered = filtered.filter(mod => mod.loader_type === filterLoader)
    }

    // Minecraft版本过滤
    if (filterMinecraftVersion !== 'all') {
      filtered = filtered.filter(mod => mod.minecraft_version === filterMinecraftVersion)
    }

    // 排序
    filtered = [...filtered].sort((a, b) => {
      let compareValue = 0

      switch (sortBy) {
        case 'name':
          compareValue = a.name.localeCompare(b.name)
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
      }

      return sortOrder === 'asc' ? compareValue : -compareValue
    })

    return filtered
  }, [mods, searchText, filterLoader, filterMinecraftVersion, sortBy, sortOrder])

  const toggleSortOrder = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
  }

  const resetFilters = () => {
    setSearchText('')
    setFilterLoader('all')
    setFilterMinecraftVersion('all')
    setSortBy('name')
    setSortOrder('asc')
  }

  const hasActiveFilters = searchText || filterLoader !== 'all' || filterMinecraftVersion !== 'all'

  return (
    <div className={`mod-list ${className}`}>
      {/* 过滤和排序控件 */}
      <Card className="mb-4">
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="搜索MOD名称、ID、描述或作者..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
              allowClear
            />
          </Col>
          
          <Col xs={12} sm={6} md={4}>
            <Select
              value={filterLoader}
              onChange={setFilterLoader}
              placeholder="选择加载器"
              className="w-full"
            >
              <Option value="all">全部加载器</Option>
              {loaderTypes.map(type => (
                <Option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Option>
              ))}
            </Select>
          </Col>
          
          <Col xs={12} sm={6} md={4}>
            <Select
              value={filterMinecraftVersion}
              onChange={setFilterMinecraftVersion}
              placeholder="MC版本"
              className="w-full"
            >
              <Option value="all">全部版本</Option>
              {minecraftVersions.map(version => (
                <Option key={version} value={version}>
                  MC {version}
                </Option>
              ))}
            </Select>
          </Col>

          <Col xs={12} sm={6} md={4}>
            <Select
              value={sortBy}
              onChange={(value: SortBy) => setSortBy(value)}
              className="w-full"
            >
              <Option value="name">按名称</Option>
              <Option value="version">按版本</Option>
              <Option value="loader_type">按加载器</Option>
              <Option value="file_size">按大小</Option>
              <Option value="minecraft_version">按MC版本</Option>
            </Select>
          </Col>

          <Col xs={12} sm={6} md={4}>
            <Space>
              <Tooltip title={`${sortOrder === 'asc' ? '升序' : '降序'}排列`}>
                <Button 
                  icon={sortOrder === 'asc' ? <SortAscendingOutlined /> : <SortDescendingOutlined />}
                  onClick={toggleSortOrder}
                />
              </Tooltip>
              
              <Tooltip title={compactView ? '切换到卡片视图' : '切换到紧凑视图'}>
                <Button 
                  icon={compactView ? <AppstoreOutlined /> : <BarsOutlined />}
                  onClick={() => setCompactView(!compactView)}
                />
              </Tooltip>

              {onRefresh && (
                <Tooltip title="刷新列表">
                  <Button 
                    icon={<ReloadOutlined />}
                    onClick={onRefresh}
                    loading={loading}
                  />
                </Tooltip>
              )}
            </Space>
          </Col>
        </Row>

        {/* 过滤器状态和统计 */}
        <Row justify="space-between" align="middle" className="mt-3 pt-3 border-t border-gray-200">
          <Col>
            <Space size="small">
              <Text type="secondary">
                显示 {filteredAndSortedMods.length} / {mods.length} 个MOD
              </Text>
              
              {hasActiveFilters && (
                <Button 
                  type="link" 
                  size="small"
                  onClick={resetFilters}
                  icon={<FilterOutlined />}
                >
                  清除筛选
                </Button>
              )}
            </Space>
          </Col>
          
          <Col>
            <Space size="small">
              <Text type="secondary">紧凑视图</Text>
              <Switch 
                checked={compactView}
                onChange={setCompactView}
                size="small"
              />
            </Space>
          </Col>
        </Row>

        {/* 活跃过滤器显示 */}
        {hasActiveFilters && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <Text type="secondary" className="text-sm mr-2">活跃筛选：</Text>
            <Space size={[4, 4]} wrap>
              {searchText && (
                <Tag closable onClose={() => setSearchText('')} color="blue">
                  搜索: {searchText}
                </Tag>
              )}
              {filterLoader !== 'all' && (
                <Tag closable onClose={() => setFilterLoader('all')} color="green">
                  加载器: {filterLoader}
                </Tag>
              )}
              {filterMinecraftVersion !== 'all' && (
                <Tag closable onClose={() => setFilterMinecraftVersion('all')} color="orange">
                  版本: MC {filterMinecraftVersion}
                </Tag>
              )}
            </Space>
          </div>
        )}
      </Card>

      {/* MOD列表 */}
      <Spin spinning={loading}>
        {filteredAndSortedMods.length === 0 ? (
          <Empty 
            description={
              hasActiveFilters 
                ? "没有找到符合条件的MOD" 
                : "暂无MOD数据"
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            {hasActiveFilters && (
              <Button type="primary" onClick={resetFilters}>
                清除所有筛选
              </Button>
            )}
          </Empty>
        ) : (
          <List
            dataSource={filteredAndSortedMods}
            renderItem={(mod, index) => (
              <List.Item key={`${mod.mod_id}-${index}`} style={{ border: 'none', padding: 0 }}>
                <ModInfoCard mod={mod} compact={compactView} />
              </List.Item>
            )}
            pagination={{
              pageSize: compactView ? 20 : 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `${range[0]}-${range[1]} 共 ${total} 个MOD`,
              pageSizeOptions: compactView ? ['10', '20', '50', '100'] : ['5', '10', '20', '50']
            }}
          />
        )}
      </Spin>
    </div>
  )
}

export default ModList