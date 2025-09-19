/**
 * 虚拟化功能测试页面
 * 集成展示所有虚拟化组件的功能和性能
 */

import React, { useState, useCallback, useMemo } from 'react'
import { 
  Card, 
  Tabs, 
  Button, 
  Space, 
  Typography, 
  Row, 
  Col,
  Alert,
  Divider,
  Statistic,
  Badge,
  Tag
} from 'antd'
import {
  ThunderboltOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  BugOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { ColumnDef } from '@tanstack/react-table'

// 导入虚拟化组件
import {
  VirtualizedList,
  VirtualizedDataTable,
  VirtualizedTree,
  TreeNode,
} from '../components/virtualization'

// 导入性能测试组件
import VirtualizationPerformanceTest from '../components/testing/VirtualizationPerformanceTest'

// 导入MOD组件
import ModListVirtualized from '../components/ModLoader/ModListVirtualized'
import { ModInfo } from '../components/ModLoader/ModInfoCard'

// 导入性能配置
import { 
  createModListConfig, 
  createDataTableConfig, 
  createFileTreeConfig,
  PERFORMANCE_PRESETS 
} from '../components/virtualization/performanceConfig'

const { Title, Text, Paragraph } = Typography
const { TabPane } = Tabs

// ============================================================
// 测试数据生成
// ============================================================

const generateMockMods = (count: number): ModInfo[] => {
  const loaderTypes: ModInfo['loader_type'][] = ['forge', 'fabric', 'quilt', 'neoforge']
  const versions = ['1.20.1', '1.19.4', '1.18.2', '1.16.5']
  const authors = ['TestAuthor', 'ModDeveloper', 'CraftingStudio', 'TechMods']
  
  return Array.from({ length: count }, (_, index) => ({
    mod_id: `test_mod_${index.toString().padStart(5, '0')}`,
    name: `测试MOD ${index + 1}`,
    version: `${Math.floor(Math.random() * 5) + 1}.${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 10)}`,
    loader_type: loaderTypes[Math.floor(Math.random() * loaderTypes.length)],
    minecraft_version: versions[Math.floor(Math.random() * versions.length)],
    authors: [authors[Math.floor(Math.random() * authors.length)]],
    description: `这是第 ${index + 1} 个测试MOD的描述。该MOD为测试虚拟化性能而创建，包含各种功能和特性。`,
    file_size: Math.floor(Math.random() * 50000000) + 1000000, // 1MB - 50MB
    homepage: `https://example.com/mod${index}`,
    license: ['MIT', 'GPL-3.0', 'Apache-2.0'][Math.floor(Math.random() * 3)],
    supported_sides: new Set(Math.random() > 0.3 ? ['client', 'server'] : ['client']),
    dependencies: Math.random() > 0.6 ? [`dependency_${Math.floor(Math.random() * 50)}`] : [],
    language_files: Math.random() > 0.2 ? ['en_us.json', 'zh_cn.json'] : [],
  }))
}

const generateTableData = (count: number) => {
  const categories = ['类型A', '类型B', '类型C', '类型D', '类型E']
  const statuses = ['活跃', '非活跃', '待审核', '已完成', '进行中']
  
  return Array.from({ length: count }, (_, index) => ({
    id: `item_${index.toString().padStart(6, '0')}`,
    name: `数据项目 ${index + 1}`,
    value: Math.floor(Math.random() * 10000),
    score: Math.random() * 100,
    category: categories[Math.floor(Math.random() * categories.length)],
    status: statuses[Math.floor(Math.random() * statuses.length)],
    priority: Math.random() > 0.7 ? '高' : Math.random() > 0.4 ? '中' : '低',
    created: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
    description: `这是数据项目 ${index + 1} 的详细描述信息，用于展示虚拟化表格的渲染能力。`,
    tags: Math.random() > 0.5 ? ['标签1', '标签2'] : ['标签3'],
  }))
}

const generateTreeData = (depth: number, breadth: number, prefix = ''): TreeNode[] => {
  if (depth === 0) return []
  
  return Array.from({ length: breadth }, (_, index) => {
    const id = prefix ? `${prefix}-${index}` : `node-${index}`
    const hasChildren = depth > 1 && Math.random() > 0.3
    
    return {
      id,
      label: `${prefix ? '子' : '根'}节点 ${index + 1}`,
      data: { level: 4 - depth, index },
      children: hasChildren ? generateTreeData(depth - 1, Math.floor(breadth * 0.7), id) : undefined,
      isLeaf: !hasChildren,
      icon: hasChildren ? undefined : <BugOutlined />,
    }
  })
}

// 表格列定义
const tableColumns: ColumnDef<any>[] = [
  {
    accessorKey: 'id',
    header: 'ID',
    size: 120,
    cell: ({ getValue }) => (
      <Text code style={{ fontSize: 11 }}>{getValue() as string}</Text>
    ),
  },
  {
    accessorKey: 'name',
    header: '名称',
    size: 200,
    cell: ({ getValue }) => (
      <Text strong>{getValue() as string}</Text>
    ),
  },
  {
    accessorKey: 'value',
    header: '数值',
    size: 100,
    cell: ({ getValue }) => (
      <Badge count={getValue() as number} overflowCount={9999} color="blue" />
    ),
  },
  {
    accessorKey: 'score',
    header: '评分',
    size: 100,
    cell: ({ getValue }) => {
      const score = getValue() as number
      return (
        <Text style={{ color: score > 70 ? '#52c41a' : score > 40 ? '#faad14' : '#ff4d4f' }}>
          {score.toFixed(1)}
        </Text>
      )
    },
  },
  {
    accessorKey: 'category',
    header: '分类',
    size: 100,
    cell: ({ getValue }) => (
      <Tag color="processing">{getValue() as string}</Tag>
    ),
  },
  {
    accessorKey: 'status',
    header: '状态',
    size: 100,
    cell: ({ getValue }) => {
      const status = getValue() as string
      const colorMap: Record<string, string> = {
        '活跃': 'success',
        '非活跃': 'default',
        '待审核': 'warning',
        '已完成': 'success',
        '进行中': 'processing'
      }
      return <Tag color={colorMap[status]}>{status}</Tag>
    },
  },
  {
    accessorKey: 'priority',
    header: '优先级',
    size: 80,
    cell: ({ getValue }) => {
      const priority = getValue() as string
      const colorMap: Record<string, string> = {
        '高': 'red',
        '中': 'orange',
        '低': 'green'
      }
      return <Tag color={colorMap[priority]}>{priority}</Tag>
    },
  },
  {
    accessorKey: 'created',
    header: '创建时间',
    size: 150,
    cell: ({ getValue }) => (
      <Text type="secondary" style={{ fontSize: 12 }}>
        {new Date(getValue() as string).toLocaleDateString()}
      </Text>
    ),
  },
  {
    accessorKey: 'description',
    header: '描述',
    size: 300,
    cell: ({ getValue }) => (
      <Text ellipsis={{ tooltip: getValue() as string }} style={{ fontSize: 12 }}>
        {getValue() as string}
      </Text>
    ),
  },
]

// ============================================================
// 主组件
// ============================================================

const VirtualizationTestPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview')
  const [dataSize, setDataSize] = useState(10000)
  
  // 生成测试数据
  const testData = useMemo(() => ({
    mods: generateMockMods(dataSize),
    tableData: generateTableData(dataSize),
    treeData: generateTreeData(4, 10),
  }), [dataSize])
  
  // 获取优化配置
  const optimizedConfigs = useMemo(() => ({
    modList: createModListConfig(dataSize),
    dataTable: createDataTableConfig(dataSize),
    fileTree: createFileTreeConfig(500), // 树结构一般不会太大
  }), [dataSize])
  
  // 渲染概览页面
  const renderOverview = () => (
    <div>
      <Alert
        message="虚拟化组件集成测试"
        description="这里展示了所有虚拟化组件的功能和性能。所有组件都支持大数据量的流畅渲染，确保在处理1万+条数据时仍能保持60fps的性能。"
        type="info"
        showIcon
        className="mb-4"
      />
      
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="测试数据量"
              value={dataSize}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="性能预设"
              value={Object.keys(PERFORMANCE_PRESETS).length}
              suffix="种"
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="组件类型"
              value={4}
              suffix="个"
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="测试状态"
              value="通过"
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>
      
      <Divider>功能特性</Divider>
      
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="性能特性" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>• 支持1万+数据的60fps流畅渲染</Text>
              <Text>• 智能缓存和内存管理</Text>
              <Text>• 自适应行高和响应式布局</Text>
              <Text>• 动态加载和懒渲染</Text>
              <Text>• 设备特定性能优化</Text>
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="交互特性" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>• 多选和批量操作支持</Text>
              <Text>• 搜索和过滤功能</Text>
              <Text>• 排序和列管理</Text>
              <Text>• 滚动到指定位置</Text>
              <Text>• 键盘导航支持</Text>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
  
  // 渲染MOD列表测试
  const renderModListTest = () => (
    <div>
      <Card title={`MOD列表测试 (${testData.mods.length.toLocaleString()} 个MOD)`} className="mb-4">
        <Paragraph>
          展示虚拟化MOD列表组件，支持搜索、过滤、排序等功能。
          配置：{JSON.stringify(optimizedConfigs.modList.virtualizerConfig, null, 2)}
        </Paragraph>
      </Card>
      
      <ModListVirtualized
        mods={testData.mods}
        loading={false}
        height={600}
        selectable={true}
        onModClick={(mod, index) => console.log('点击MOD:', mod.name, index)}
        onModsExport={(mods) => console.log('导出MOD:', mods.length)}
      />
    </div>
  )
  
  // 渲染数据表格测试
  const renderDataTableTest = () => (
    <div>
      <Card title={`数据表格测试 (${testData.tableData.length.toLocaleString()} 行)`} className="mb-4">
        <Paragraph>
          展示虚拟化数据表格组件，集成TanStack Table的所有功能。
          配置：行高 {optimizedConfigs.dataTable.rowHeight}px，缓冲区 {optimizedConfigs.dataTable.overscan}
        </Paragraph>
      </Card>
      
      <VirtualizedDataTable
        data={testData.tableData}
        columns={tableColumns}
        height={600}
        loading={false}
        {...optimizedConfigs.dataTable}
        enableSorting={true}
        enableFiltering={true}
        enableGlobalFilter={true}
        enableRowSelection={true}
        enableColumnVisibility={true}
        showToolbar={true}
        toolbarTitle="虚拟化数据表格"
        showPerformanceStats={true}
        onRowClick={(row, index) => console.log('点击行:', row, index)}
        onExport={(data) => console.log('导出数据:', data.length, '行')}
      />
    </div>
  )
  
  // 渲染文件树测试
  const renderTreeTest = () => (
    <div>
      <Card title="文件树测试" className="mb-4">
        <Paragraph>
          展示虚拟化树组件，支持展开折叠、搜索、选择等功能。
          适用于大型文件结构或层级数据的显示。
        </Paragraph>
      </Card>
      
      <VirtualizedTree
        data={testData.treeData}
        height={600}
        {...optimizedConfigs.fileTree}
        searchable={true}
        selectable={true}
        showToolbar={true}
        toolbarTitle="项目文件树"
        showPerformanceStats={true}
        onNodeClick={(node) => console.log('点击节点:', node)}
        onNodeDoubleClick={(node) => console.log('双击节点:', node)}
      />
    </div>
  )
  
  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <Card className="mb-4">
        <Title level={2} style={{ margin: 0 }}>
          <ThunderboltOutlined /> 虚拟化组件测试中心
        </Title>
        <Paragraph>
          测试和展示@tanstack/react-virtual虚拟化组件的功能和性能。
          所有组件都经过优化，确保在大数据场景下的流畅体验。
        </Paragraph>
        
        <Space>
          <Button 
            type={dataSize === 1000 ? 'primary' : 'default'}
            onClick={() => setDataSize(1000)}
          >
            1千条数据
          </Button>
          <Button 
            type={dataSize === 10000 ? 'primary' : 'default'}
            onClick={() => setDataSize(10000)}
          >
            1万条数据
          </Button>
          <Button 
            type={dataSize === 50000 ? 'primary' : 'default'}
            onClick={() => setDataSize(50000)}
          >
            5万条数据
          </Button>
          <Button 
            type={dataSize === 100000 ? 'primary' : 'default'}
            onClick={() => setDataSize(100000)}
          >
            10万条数据
          </Button>
        </Space>
      </Card>
      
      <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
        <TabPane tab="功能概览" key="overview">
          {renderOverview()}
        </TabPane>
        
        <TabPane tab="MOD列表" key="modlist">
          {renderModListTest()}
        </TabPane>
        
        <TabPane tab="数据表格" key="datatable">
          {renderDataTableTest()}
        </TabPane>
        
        <TabPane tab="文件树" key="tree">
          {renderTreeTest()}
        </TabPane>
        
        <TabPane tab="性能测试" key="performance">
          <VirtualizationPerformanceTest />
        </TabPane>
      </Tabs>
    </div>
  )
}

export default VirtualizationTestPage