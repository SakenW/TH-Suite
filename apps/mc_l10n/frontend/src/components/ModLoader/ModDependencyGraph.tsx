import React, { useMemo, useState } from 'react'
import { 
  Card, 
  Tree, 
  Alert, 
  Space, 
  Tag, 
  Typography, 
  Collapse,
  List,
  Tooltip,
  Badge,
  Empty,
  Tabs,
  Button
} from 'antd'
import { 
  NodeIndexOutlined, 
  WarningOutlined, 
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined,
  BugOutlined,
  InfoCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import { ModInfo } from './ModInfoCard'

const { Text, Title } = Typography
const { Panel } = Collapse

export interface DependencyAnalysis {
  dependency_graph: Record<string, string[]>
  missing_dependencies: string[]
  dependency_conflicts: any[]
  total_dependencies: number
}

interface ModDependencyGraphProps {
  mods: ModInfo[]
  analysis: DependencyAnalysis
  loading?: boolean
  onRefresh?: () => void
  className?: string
}

interface DependencyNode extends DataNode {
  mod_id: string
  is_missing?: boolean
  is_optional?: boolean
  dependency_count?: number
}

export const ModDependencyGraph: React.FC<ModDependencyGraphProps> = ({
  mods = [],
  analysis,
  loading = false,
  onRefresh,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState('tree')
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])

  // 创建MOD映射，便于查找
  const modMap = useMemo(() => {
    return new Map(mods.map(mod => [mod.mod_id, mod]))
  }, [mods])

  // 构建依赖树数据
  const dependencyTree = useMemo(() => {
    if (!analysis.dependency_graph) return []

    const treeData: DependencyNode[] = []
    const processedNodes = new Set<string>()

    // 找到根节点（没有被其他MOD依赖的）
    const dependents = new Set<string>()
    Object.values(analysis.dependency_graph).forEach(deps => {
      deps.forEach(dep => dependents.add(dep))
    })

    const rootNodes = Object.keys(analysis.dependency_graph).filter(
      modId => !dependents.has(modId)
    )

    const buildNode = (modId: string, visited = new Set<string>()): DependencyNode | null => {
      if (visited.has(modId)) {
        // 检测到循环依赖
        return {
          key: `${modId}-cycle`,
          title: (
            <Space>
              <ExclamationCircleOutlined style={{ color: '#faad14' }} />
              <Text type="warning">{modId} (循环依赖)</Text>
            </Space>
          ),
          mod_id: modId,
          isLeaf: true
        }
      }

      const mod = modMap.get(modId)
      const dependencies = analysis.dependency_graph[modId] || []
      const isMissing = analysis.missing_dependencies.includes(modId)

      const newVisited = new Set(visited)
      newVisited.add(modId)

      const children: DependencyNode[] = dependencies.map(depId => 
        buildNode(depId, newVisited)
      ).filter(Boolean) as DependencyNode[]

      const loaderIcon = getModLoaderIcon(mod?.loader_type)
      const statusIcon = isMissing ? 
        <WarningOutlined style={{ color: '#ff4d4f' }} /> :
        <CheckCircleOutlined style={{ color: '#52c41a' }} />

      return {
        key: modId,
        title: (
          <Space>
            {statusIcon}
            {loaderIcon}
            <Text strong={!isMissing} type={isMissing ? 'danger' : undefined}>
              {mod?.name || modId}
            </Text>
            {mod?.version && (
              <Tag color="blue">v{mod.version}</Tag>
            )}
            {dependencies.length > 0 && (
              <Badge count={dependencies.length} color="#87CEEB" />
            )}
          </Space>
        ),
        mod_id: modId,
        is_missing: isMissing,
        dependency_count: dependencies.length,
        children: children.length > 0 ? children : undefined
      }
    }

    // 构建根节点
    rootNodes.forEach(modId => {
      const node = buildNode(modId)
      if (node) {
        treeData.push(node)
      }
    })

    // 处理孤立节点（没有依赖关系的MOD）
    const allGraphMods = new Set([
      ...Object.keys(analysis.dependency_graph),
      ...Object.values(analysis.dependency_graph).flat()
    ])
    
    mods.forEach(mod => {
      if (!allGraphMods.has(mod.mod_id)) {
        treeData.push({
          key: `isolated-${mod.mod_id}`,
          title: (
            <Space>
              <InfoCircleOutlined style={{ color: '#1890ff' }} />
              {getModLoaderIcon(mod.loader_type)}
              <Text>{mod.name}</Text>
              <Tag color="default">独立</Tag>
            </Space>
          ),
          mod_id: mod.mod_id,
          dependency_count: 0,
          isLeaf: true
        })
      }
    })

    return treeData
  }, [mods, analysis, modMap])

  // 获取MOD加载器图标
  function getModLoaderIcon(loaderType?: string) {
    const icons = {
      forge: '🔥',
      neoforge: '⚡',
      fabric: '🧵',
      quilt: '🪡',
      unknown: '❓'
    }
    return <span>{icons[loaderType as keyof typeof icons] || icons.unknown}</span>
  }

  // 扁平化依赖列表
  const flatDependencies = useMemo(() => {
    const deps: Array<{
      mod: ModInfo
      dependencies: string[]
      missing: string[]
      resolved: string[]
    }> = []

    mods.forEach(mod => {
      const dependencies = analysis.dependency_graph[mod.mod_id] || []
      const missing = dependencies.filter(dep => analysis.missing_dependencies.includes(dep))
      const resolved = dependencies.filter(dep => !analysis.missing_dependencies.includes(dep))

      if (dependencies.length > 0) {
        deps.push({
          mod,
          dependencies,
          missing,
          resolved
        })
      }
    })

    return deps.sort((a, b) => b.dependencies.length - a.dependencies.length)
  }, [mods, analysis])

  const handleTreeExpand = (keys: React.Key[]) => {
    setExpandedKeys(keys)
  }

  const expandAll = () => {
    const getAllKeys = (nodes: DependencyNode[]): React.Key[] => {
      let keys: React.Key[] = []
      nodes.forEach(node => {
        keys.push(node.key)
        if (node.children) {
          keys = keys.concat(getAllKeys(node.children))
        }
      })
      return keys
    }
    setExpandedKeys(getAllKeys(dependencyTree))
  }

  const collapseAll = () => {
    setExpandedKeys([])
  }

  const tabItems = [
    {
      key: 'tree',
      label: (
        <Space>
          <NodeIndexOutlined />
          依赖树
        </Space>
      ),
      children: (
        <div>
          <div className="mb-4 flex justify-between items-center">
            <Space>
              <Button onClick={expandAll}>
                展开全部
              </Button>
              <Button onClick={collapseAll}>
                收起全部
              </Button>
              {onRefresh && (
                <Button 
                  
                  icon={<ReloadOutlined />} 
                  onClick={onRefresh}
                  loading={loading}
                >
                  刷新
                </Button>
              )}
            </Space>
            <Text type="secondary" className="text-sm">
              {dependencyTree.length} 个根节点
            </Text>
          </div>

          {dependencyTree.length > 0 ? (
            <Tree
              treeData={dependencyTree}
              expandedKeys={expandedKeys}
              onExpand={handleTreeExpand}
              showIcon={false}
              className="dependency-tree"
            />
          ) : (
            <Empty description="没有检测到依赖关系" />
          )}
        </div>
      )
    },
    {
      key: 'list',
      label: (
        <Space>
          <ApiOutlined />
          依赖列表
        </Space>
      ),
      children: (
        <List
          dataSource={flatDependencies}
          renderItem={(item) => (
            <List.Item>
              <Card className="w-full">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <Space>
                      {getModLoaderIcon(item.mod.loader_type)}
                      <Text strong>{item.mod.name}</Text>
                      <Tag color="blue">
                        v{item.mod.version}
                      </Tag>
                    </Space>
                    
                    <div className="mt-2">
                      <Text className="text-sm text-gray-600">依赖项：</Text>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {item.resolved.map((dep, index) => (
                          <Tag key={index} color="green">
                            ✓ {dep}
                          </Tag>
                        ))}
                        {item.missing.map((dep, index) => (
                          <Tag key={index} color="red">
                            ✗ {dep}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <Text type="secondary" className="text-sm">
                      {item.dependencies.length} 个依赖
                    </Text>
                    {item.missing.length > 0 && (
                      <div>
                        <Tag color="red">
                          {item.missing.length} 个缺失
                        </Tag>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            </List.Item>
          )}
          pagination={flatDependencies.length > 10 ? {
            pageSize: 10,
            showSizeChanger: false,
            showQuickJumper: false
          } : false}
        />
      )
    },
    {
      key: 'issues',
      label: (
        <Space>
          <BugOutlined />
          问题诊断
          {analysis.missing_dependencies.length > 0 && (
            <Badge count={analysis.missing_dependencies.length} color="red" />
          )}
        </Space>
      ),
      children: (
        <div className="space-y-4">
          {/* 缺失依赖 */}
          {analysis.missing_dependencies.length > 0 && (
            <Alert
              type="error"
              showIcon
              icon={<WarningOutlined />}
              message={`发现 ${analysis.missing_dependencies.length} 个缺失的依赖`}
              description={
                <div className="mt-2">
                  <Text>以下依赖项在当前MOD包中未找到：</Text>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {analysis.missing_dependencies.map((dep, index) => (
                      <Tag key={index} color="red">
                        {dep}
                      </Tag>
                    ))}
                  </div>
                  <div className="mt-3">
                    <Text type="secondary" className="text-sm">
                      建议：请确认这些MOD是否已正确安装，或者是否为可选依赖项。
                    </Text>
                  </div>
                </div>
              }
            />
          )}

          {/* 依赖冲突 */}
          {analysis.dependency_conflicts.length > 0 && (
            <Alert
              type="warning"
              showIcon
              message={`发现 ${analysis.dependency_conflicts.length} 个依赖冲突`}
              description="某些MOD可能存在版本不兼容的问题。"
            />
          )}

          {/* 正常状态 */}
          {analysis.missing_dependencies.length === 0 && analysis.dependency_conflicts.length === 0 && (
            <Alert
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
              message="依赖关系正常"
              description={`所有 ${analysis.total_dependencies} 个依赖项都已正确解析。`}
            />
          )}

          {/* 统计信息 */}
          <Card title="依赖关系统计">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <Text type="secondary" className="text-sm">总依赖数</Text>
                <div className="text-lg font-semibold">
                  {analysis.total_dependencies}
                </div>
              </div>
              <div className="text-center">
                <Text type="secondary" className="text-sm">有依赖的MOD</Text>
                <div className="text-lg font-semibold">
                  {Object.keys(analysis.dependency_graph).length}
                </div>
              </div>
              <div className="text-center">
                <Text type="secondary" className="text-sm text-red-500">缺失依赖</Text>
                <div className="text-lg font-semibold text-red-500">
                  {analysis.missing_dependencies.length}
                </div>
              </div>
              <div className="text-center">
                <Text type="secondary" className="text-sm text-orange-500">冲突</Text>
                <div className="text-lg font-semibold text-orange-500">
                  {analysis.dependency_conflicts.length}
                </div>
              </div>
            </div>
          </Card>
        </div>
      )
    }
  ]

  return (
    <Card 
      className={`mod-dependency-graph ${className}`}
      title={
        <Space>
          <NodeIndexOutlined />
          <span>MOD依赖关系分析</span>
          {analysis.missing_dependencies.length > 0 && (
            <Badge count={analysis.missing_dependencies.length} color="red" />
          )}
        </Space>
      }
      loading={loading}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        type="card"
      />
    </Card>
  )
}

export default ModDependencyGraph