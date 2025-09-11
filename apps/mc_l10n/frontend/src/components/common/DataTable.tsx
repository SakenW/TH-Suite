/**
 * 通用数据表格组件 - Ant Design版本
 * 功能完整的数据表格，支持排序、过滤、分页、选择等功能
 */

import React, { useState, useMemo, useCallback } from 'react'
import {
  Table,
  Input,
  Button,
  Space,
  Dropdown,
  Typography,
  Card,
  Tooltip,
  Checkbox,
  Row,
  Col,
  Collapse,
  Menu,
  Empty,
  Spin,
  Alert,
} from 'antd'
import type { TableColumnsType, TableProps } from 'antd'
import {
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  ReloadOutlined,
  SettingOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  MoreOutlined,
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'

const { Text, Title } = Typography
const { Panel } = Collapse

export interface AntTableColumn<T = any> {
  key: keyof T | string
  title: string
  dataIndex?: keyof T | string
  sortable?: boolean
  filterable?: boolean
  width?: number | string
  minWidth?: number
  maxWidth?: number
  align?: 'left' | 'center' | 'right'
  fixed?: 'left' | 'right'
  hidden?: boolean
  render?: (value: any, record: T, index: number) => React.ReactNode
  filterType?: 'text' | 'select' | 'date' | 'range'
  filterOptions?: Array<{ label: string; value: any }>
  sorter?: boolean | ((a: T, b: T) => number)
}

export interface AntTableAction<T = any> {
  key: string
  label: string
  icon?: React.ReactNode
  onClick: (record: T, index: number) => void
  disabled?: (record: T, index: number) => boolean
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text'
  danger?: boolean
}

interface AntDataTableProps<T = any> {
  // 数据
  data: T[]
  columns: AntTableColumn<T>[]
  loading?: boolean
  error?: string

  // 选择功能
  rowSelection?: boolean
  selectedRows?: T[]
  onSelectionChange?: (selectedKeys: React.Key[], selectedRows: T[]) => void
  rowKey?: string | ((record: T) => string)

  // 分页
  pagination?: {
    current?: number
    pageSize?: number
    total?: number
    showSizeChanger?: boolean
    showQuickJumper?: boolean
    showTotal?: (total: number, range: [number, number]) => string
    onChange?: (page: number, pageSize: number) => void
  }

  // 过滤和搜索
  globalSearch?: boolean
  globalSearchValue?: string
  onGlobalSearchChange?: (value: string) => void

  // 行操作
  actions?: AntTableAction<T>[]
  rowActions?: AntTableAction<T>[]

  // 展开行
  expandable?: {
    expandedRowKeys?: React.Key[]
    onExpand?: (expanded: boolean, record: T) => void
    expandedRowRender?: (record: T, index: number) => React.ReactNode
  }

  // 样式配置
  size?: 'small' | 'middle' | 'large'
  bordered?: boolean
  showHeader?: boolean
  title?: string
  subtitle?: string

  // 事件
  onRow?: (record: T, index?: number) => React.HTMLAttributes<any>
  onRefresh?: () => void
  onExport?: () => void
}

export const AntDataTable = <T extends Record<string, any>>({
  data,
  columns: initialColumns,
  loading = false,
  error,
  rowSelection = false,
  selectedRows = [],
  onSelectionChange,
  rowKey = 'id',
  pagination,
  globalSearch = true,
  globalSearchValue = '',
  onGlobalSearchChange,
  actions = [],
  rowActions = [],
  expandable,
  size = 'middle',
  bordered = false,
  showHeader = true,
  title,
  subtitle,
  onRow,
  onRefresh,
  onExport,
}: AntDataTableProps<T>) => {
  const [searchValue, setSearchValue] = useState(globalSearchValue)
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(
    new Set(initialColumns.filter(col => !col.hidden).map(col => col.key as string)),
  )

  // 计算可见列
  const columns = useMemo(() => {
    const visibleCols = initialColumns
      .filter(col => visibleColumns.has(col.key as string))
      .map(col => {
        const antCol: any = {
          key: col.key,
          title: col.title,
          dataIndex: col.dataIndex || col.key,
          width: col.width,
          align: col.align,
          fixed: col.fixed,
          render: col.render,
          sorter: col.sortable ? col.sorter || true : false,
        }

        if (col.filterable) {
          antCol.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }: any) => (
            <div style={{ padding: 8 }}>
              <Input
                placeholder={`搜索 ${col.title}`}
                value={selectedKeys[0]}
                onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
                onPressEnter={() => confirm()}
                style={{ width: 188, marginBottom: 8, display: 'block' }}
              />
              <Space>
                <Button
                  type="primary"
                  onClick={() => confirm()}
                  icon={<SearchOutlined />}
                  size="small"
                  style={{ width: 90 }}
                >
                  搜索
                </Button>
                <Button
                  onClick={() => clearFilters?.()}
                  size="small"
                  style={{ width: 90 }}
                >
                  重置
                </Button>
              </Space>
            </div>
          )
          antCol.filterIcon = (filtered: boolean) => (
            <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
          )
          antCol.onFilter = (value: any, record: T) =>
            record[col.dataIndex || col.key]
              ?.toString()
              .toLowerCase()
              .includes(value.toLowerCase())
        }

        return antCol
      })

    // 添加行操作列
    if (rowActions.length > 0) {
      visibleCols.push({
        key: 'actions',
        title: '操作',
        width: 100,
        fixed: 'right',
        render: (_: any, record: T, index: number) => (
          <Dropdown
            menu={{
              items: rowActions.map(action => ({
                key: action.key,
                label: action.label,
                icon: action.icon,
                disabled: action.disabled?.(record, index),
                danger: action.danger,
                onClick: () => action.onClick(record, index),
              })),
            }}
            trigger={['click']}
          >
            <Button size="small" icon={<MoreOutlined />} />
          </Dropdown>
        ),
      })
    }

    return visibleCols
  }, [initialColumns, visibleColumns, rowActions])

  // 行选择配置
  const rowSelectionConfig = useMemo(() => {
    if (!rowSelection) return undefined

    return {
      selectedRowKeys: selectedRows.map(row => 
        typeof rowKey === 'function' ? rowKey(row) : row[rowKey]
      ),
      onChange: (selectedRowKeys: React.Key[], selectedRecords: T[]) => {
        onSelectionChange?.(selectedRowKeys, selectedRecords)
      },
      getCheckboxProps: (record: T) => ({
        name: typeof rowKey === 'function' ? rowKey(record) : record[rowKey],
      }),
    }
  }, [rowSelection, selectedRows, rowKey, onSelectionChange])

  // 搜索处理
  const handleSearch = useCallback((value: string) => {
    setSearchValue(value)
    onGlobalSearchChange?.(value)
  }, [onGlobalSearchChange])

  // 列显示切换
  const toggleColumnVisibility = useCallback((columnKey: string) => {
    setVisibleColumns(prev => {
      const newSet = new Set(prev)
      if (newSet.has(columnKey)) {
        newSet.delete(columnKey)
      } else {
        newSet.add(columnKey)
      }
      return newSet
    })
  }, [])

  // 渲染工具栏
  const renderToolbar = () => {
    const hasSelection = selectedRows.length > 0

    return (
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space direction="vertical" size={0}>
            {title && <Title level={4} style={{ margin: 0 }}>{title}</Title>}
            {subtitle && <Text type="secondary">{subtitle}</Text>}
            {hasSelection && (
              <Text>已选择 {selectedRows.length} 项</Text>
            )}
          </Space>
        </Col>

        <Col>
          <Space>
            {/* 批量操作按钮 */}
            {hasSelection &&
              actions.map(action => (
                <Button
                  key={action.key}
                  type={action.type}
                  danger={action.danger}
                  icon={action.icon}
                  onClick={() => selectedRows.forEach((row, index) => action.onClick(row, index))}
                  disabled={selectedRows.some((row, index) => action.disabled?.(row, index))}
                >
                  {action.label}
                </Button>
              ))}

            {/* 搜索框 */}
            {globalSearch && (
              <Input
                placeholder="搜索..."
                value={searchValue}
                onChange={(e) => handleSearch(e.target.value)}
                prefix={<SearchOutlined />}
                style={{ width: 200 }}
                allowClear
              />
            )}

            {/* 工具按钮 */}
            {onExport && (
              <Tooltip title="导出">
                <Button icon={<DownloadOutlined />} onClick={onExport} />
              </Tooltip>
            )}

            {onRefresh && (
              <Tooltip title="刷新">
                <Button icon={<ReloadOutlined />} onClick={onRefresh} />
              </Tooltip>
            )}

            {/* 列设置 */}
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'columns',
                    label: '显示列',
                    children: initialColumns.map(col => ({
                      key: col.key as string,
                      label: (
                        <Checkbox
                          checked={visibleColumns.has(col.key as string)}
                          onChange={() => toggleColumnVisibility(col.key as string)}
                        >
                          {col.title}
                        </Checkbox>
                      ),
                    })),
                  },
                ],
              }}
              trigger={['click']}
            >
              <Tooltip title="列设置">
                <Button icon={<SettingOutlined />} />
              </Tooltip>
            </Dropdown>
          </Space>
        </Col>
      </Row>
    )
  }

  // 错误状态
  if (error) {
    return (
      <Card>
        {renderToolbar()}
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          action={
            onRefresh && (
              <Button size="small" danger onClick={onRefresh}>
                重试
              </Button>
            )
          }
        />
      </Card>
    )
  }

  // 空数据状态
  if (!loading && data.length === 0) {
    return (
      <Card>
        {renderToolbar()}
        <Empty description="暂无数据" />
      </Card>
    )
  }

  return (
    <Card>
      {renderToolbar()}
      
      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={data}
          rowKey={rowKey}
          rowSelection={rowSelectionConfig}
          pagination={pagination}
          expandable={expandable}
          size={size}
          bordered={bordered}
          showHeader={showHeader}
          onRow={onRow}
          scroll={{ x: 'max-content' }}
        />
      </Spin>
    </Card>
  )
}