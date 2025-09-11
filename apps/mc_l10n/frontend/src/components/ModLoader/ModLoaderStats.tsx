import React from 'react'
import { Card, Row, Col, Statistic, Progress, Tag, Space, Typography, Tooltip, Badge } from 'antd'
import { 
  FireOutlined, 
  ThunderboltOutlined, 
  BugOutlined, 
  QuestionCircleOutlined,
  DesktopOutlined,
  CloudServerOutlined,
  GlobalOutlined,
  ApiOutlined
} from '@ant-design/icons'

const { Text, Title } = Typography

export interface ModLoaderStatistics {
  total_mods: number
  total_language_files: number
  total_translation_entries: number
  total_file_size: number
  total_dependencies: number
  loader_distribution: Record<string, number>
  locale_distribution: Record<string, number>
  minecraft_versions: string[]
  supported_sides: {
    client: number
    server: number
    both: number
  }
  supported_loaders: string[]
}

interface ModLoaderStatsProps {
  statistics: ModLoaderStatistics
  className?: string
}

const getLoaderIcon = (loaderType: string) => {
  const icons = {
    forge: <FireOutlined style={{ color: '#FF6B35' }} />,
    neoforge: <ThunderboltOutlined style={{ color: '#722ED1' }} />,
    fabric: <ApiOutlined style={{ color: '#52C41A' }} />,
    quilt: <BugOutlined style={{ color: '#1890FF' }} />,
    unknown: <QuestionCircleOutlined style={{ color: '#8C8C8C' }} />
  }
  return icons[loaderType as keyof typeof icons] || icons.unknown
}

const getLoaderColor = (loaderType: string): string => {
  const colors = {
    forge: '#FF6B35',
    neoforge: '#722ED1', 
    fabric: '#52C41A',
    quilt: '#1890FF',
    unknown: '#8C8C8C'
  }
  return colors[loaderType as keyof typeof colors] || colors.unknown
}

const formatFileSize = (bytes: number): string => {
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`
}

export const ModLoaderStats: React.FC<ModLoaderStatsProps> = ({ 
  statistics, 
  className = '' 
}) => {
  const totalMods = statistics.total_mods || 0
  const totalSides = statistics.supported_sides.client + 
                    statistics.supported_sides.server + 
                    statistics.supported_sides.both

  return (
    <div className={`mod-loader-stats ${className}`}>
      {/* 总览卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic
              title="总MOD数量"
              value={statistics.total_mods}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic
              title="语言文件"
              value={statistics.total_language_files}
              prefix={<GlobalOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic
              title="翻译条目"
              value={statistics.total_translation_entries}
              prefix={<BugOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic
              title="总文件大小"
              value={formatFileSize(statistics.total_file_size)}
              prefix={<DesktopOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 加载器分布 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <ApiOutlined />
                <span>MOD加载器分布</span>
              </Space>
            }
            hoverable
          >
            <div className="space-y-4">
              {Object.entries(statistics.loader_distribution).map(([loader, count]) => {
                const percentage = totalMods > 0 ? (count / totalMods) * 100 : 0
                const color = getLoaderColor(loader)
                
                return (
                  <div key={loader}>
                    <div className="flex items-center justify-between mb-2">
                      <Space size="small">
                        {getLoaderIcon(loader)}
                        <Text strong>
                          {loader.charAt(0).toUpperCase() + loader.slice(1)}
                        </Text>
                      </Space>
                      <Space size="small">
                        <Text>{count}</Text>
                        <Text type="secondary">({percentage.toFixed(1)}%)</Text>
                      </Space>
                    </div>
                    <Progress 
                      percent={percentage} 
                      strokeColor={color}
                      showInfo={false}
                      size="small"
                    />
                  </div>
                )
              })}
              
              {Object.keys(statistics.loader_distribution).length === 0 && (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>
          </Card>
        </Col>

        {/* 环境支持分布 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <CloudServerOutlined />
                <span>环境支持分布</span>
              </Space>
            }
            hoverable
          >
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Space size="small">
                    <DesktopOutlined style={{ color: '#1890ff' }} />
                    <Text>仅客户端</Text>
                  </Space>
                  <Space size="small">
                    <Text>{statistics.supported_sides.client}</Text>
                    <Text type="secondary">
                      ({totalSides > 0 ? ((statistics.supported_sides.client / totalSides) * 100).toFixed(1) : 0}%)
                    </Text>
                  </Space>
                </div>
                <Progress 
                  percent={totalSides > 0 ? (statistics.supported_sides.client / totalSides) * 100 : 0} 
                  strokeColor="#1890ff"
                  showInfo={false}
                  size="small"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Space size="small">
                    <CloudServerOutlined style={{ color: '#faad14' }} />
                    <Text>仅服务端</Text>
                  </Space>
                  <Space size="small">
                    <Text>{statistics.supported_sides.server}</Text>
                    <Text type="secondary">
                      ({totalSides > 0 ? ((statistics.supported_sides.server / totalSides) * 100).toFixed(1) : 0}%)
                    </Text>
                  </Space>
                </div>
                <Progress 
                  percent={totalSides > 0 ? (statistics.supported_sides.server / totalSides) * 100 : 0} 
                  strokeColor="#faad14"
                  showInfo={false}
                  size="small"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Space size="small">
                    <GlobalOutlined style={{ color: '#52c41a' }} />
                    <Text>通用</Text>
                  </Space>
                  <Space size="small">
                    <Text>{statistics.supported_sides.both}</Text>
                    <Text type="secondary">
                      ({totalSides > 0 ? ((statistics.supported_sides.both / totalSides) * 100).toFixed(1) : 0}%)
                    </Text>
                  </Space>
                </div>
                <Progress 
                  percent={totalSides > 0 ? (statistics.supported_sides.both / totalSides) * 100 : 0} 
                  strokeColor="#52c41a"
                  showInfo={false}
                  size="small"
                />
              </div>
            </div>
          </Card>
        </Col>

        {/* Minecraft版本分布 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <BugOutlined />
                <span>Minecraft版本</span>
              </Space>
            }
            hoverable
          >
            <div className="space-y-2">
              {statistics.minecraft_versions.length > 0 ? (
                <>
                  <div className="flex flex-wrap gap-1">
                    {statistics.minecraft_versions.slice(0, 8).map((version, index) => (
                      <Tag key={index} color="green">
                        MC {version}
                      </Tag>
                    ))}
                    {statistics.minecraft_versions.length > 8 && (
                      <Tooltip title={statistics.minecraft_versions.slice(8).join(', ')}>
                        <Tag color="green">
                          +{statistics.minecraft_versions.length - 8} 更多
                        </Tag>
                      </Tooltip>
                    )}
                  </div>
                  <div className="mt-3">
                    <Text type="secondary" className="text-sm">
                      支持 {statistics.minecraft_versions.length} 个版本
                    </Text>
                  </div>
                </>
              ) : (
                <Text type="secondary">暂无版本信息</Text>
              )}
            </div>
          </Card>
        </Col>

        {/* 语言分布 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <GlobalOutlined />
                <span>语言分布</span>
              </Space>
            }
            hoverable
          >
            <div className="space-y-3">
              {Object.keys(statistics.locale_distribution).length > 0 ? (
                <>
                  {Object.entries(statistics.locale_distribution)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 6)
                    .map(([locale, count]) => {
                      const percentage = statistics.total_language_files > 0 
                        ? (count / statistics.total_language_files) * 100 
                        : 0
                      
                      return (
                        <div key={locale}>
                          <div className="flex items-center justify-between mb-1">
                            <Badge 
                              count={locale.toUpperCase()} 
                              color="blue" 
                              style={{ backgroundColor: '#f0f5ff' }}
                            />
                            <Space size="small">
                              <Text>{count}</Text>
                              <Text type="secondary">({percentage.toFixed(1)}%)</Text>
                            </Space>
                          </div>
                          <Progress 
                            percent={percentage} 
                            strokeColor="#1890ff"
                            showInfo={false}
                            size="small"
                          />
                        </div>
                      )
                    })}
                    
                  {Object.keys(statistics.locale_distribution).length > 6 && (
                    <div className="text-center pt-2">
                      <Text type="secondary" className="text-sm">
                        还有 {Object.keys(statistics.locale_distribution).length - 6} 种语言
                      </Text>
                    </div>
                  )}
                </>
              ) : (
                <Text type="secondary">暂无语言文件</Text>
              )}
            </div>
          </Card>
        </Col>

        {/* 依赖关系统计 */}
        <Col xs={24}>
          <Card 
            title={
              <Space>
                <ApiOutlined />
                <span>依赖关系统计</span>
              </Space>
            }
            hoverable
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Statistic
                  title="总依赖数量"
                  value={statistics.total_dependencies}
                  prefix={<ApiOutlined />}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="平均依赖数"
                  value={totalMods > 0 ? (statistics.total_dependencies / totalMods).toFixed(1) : 0}
                  suffix="个/MOD"
                  prefix={<BugOutlined />}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="支持的加载器"
                  value={statistics.supported_loaders.length}
                  suffix="种"
                  prefix={<ThunderboltOutlined />}
                />
              </Col>
            </Row>
            
            <div className="mt-4">
              <Text strong className="text-sm">支持的加载器类型：</Text>
              <div className="flex flex-wrap gap-1 mt-2">
                {statistics.supported_loaders.map((loader, index) => (
                  <Tag key={index} icon={getLoaderIcon(loader)} color="blue">
                    {loader.charAt(0).toUpperCase() + loader.slice(1)}
                  </Tag>
                ))}
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ModLoaderStats