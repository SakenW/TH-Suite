import React from 'react'
import { Card, Tag, Avatar, Space, Tooltip, Typography, Descriptions, Badge } from 'antd'
import { 
  UserOutlined, 
  CodeOutlined, 
  GlobalOutlined, 
  LinkOutlined,
  BugOutlined,
  HomeOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'

const { Text, Link } = Typography

export interface ModInfo {
  mod_id: string
  name: string
  version: string
  loader_type: 'forge' | 'fabric' | 'quilt' | 'neoforge' | 'unknown'
  minecraft_version?: string
  authors: string[]
  description?: string
  file_path?: string
  file_size?: number
  homepage?: string
  license?: string
  supported_sides?: Set<string>
  dependencies?: string[]
  loader_info?: {
    loader_type: string
    version: string
    minecraft_version: string
    loader_name: string
    capabilities: string[]
  }
}

interface ModInfoCardProps {
  mod: ModInfo
  className?: string
  compact?: boolean
}

const getLoaderConfig = (loaderType: string) => {
  const configs = {
    forge: {
      color: '#FF6B35',
      backgroundColor: '#FFF2F0',
      borderColor: '#FFB8A6',
      icon: '🔥',
      displayName: 'Forge'
    },
    neoforge: {
      color: '#722ED1',
      backgroundColor: '#F9F0FF',
      borderColor: '#D3ADF7',
      icon: '⚡',
      displayName: 'NeoForge'
    },
    fabric: {
      color: '#52C41A',
      backgroundColor: '#F6FFED',
      borderColor: '#B7EB8F',
      icon: '🧵',
      displayName: 'Fabric'
    },
    quilt: {
      color: '#1890FF',
      backgroundColor: '#E6F7FF',
      borderColor: '#91D5FF',
      icon: '🪡',
      displayName: 'Quilt'
    },
    unknown: {
      color: '#8C8C8C',
      backgroundColor: '#F5F5F5',
      borderColor: '#D9D9D9',
      icon: '❓',
      displayName: '未知'
    }
  }
  return configs[loaderType as keyof typeof configs] || configs.unknown
}

const getSideConfig = (sides?: Set<string>) => {
  if (!sides) return { text: '通用', color: 'default' }
  
  if (sides.has('client') && sides.has('server')) {
    return { text: '客户端+服务端', color: 'success' }
  } else if (sides.has('client')) {
    return { text: '仅客户端', color: 'processing' }
  } else if (sides.has('server')) {
    return { text: '仅服务端', color: 'warning' }
  }
  return { text: '未知', color: 'default' }
}

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '-'
  
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`
}

export const ModInfoCard: React.FC<ModInfoCardProps> = ({ 
  mod, 
  className = '', 
  compact = false 
}) => {
  const loaderConfig = getLoaderConfig(mod.loader_type)
  const sideConfig = getSideConfig(mod.supported_sides)

  const cardTitle = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg">{loaderConfig.icon}</span>
        <div>
          <Text strong className="text-base">
            {mod.name}
          </Text>
          <br />
          <Text type="secondary" className="text-xs">
            ID: {mod.mod_id}
          </Text>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Tag 
          color={loaderConfig.color}
          style={{ 
            backgroundColor: loaderConfig.backgroundColor,
            borderColor: loaderConfig.borderColor,
            margin: 0
          }}
        >
          {loaderConfig.displayName}
        </Tag>
        <Badge 
          count={mod.version} 
          color="#87CEEB"
          style={{ backgroundColor: '#F0F8FF' }}
        />
      </div>
    </div>
  )

  const cardExtra = (
    <Space>
      {mod.homepage && (
        <Tooltip title="主页">
          <Link href={mod.homepage} target="_blank">
            <HomeOutlined />
          </Link>
        </Tooltip>
      )}
      <Tooltip title={`文件大小: ${formatFileSize(mod.file_size)}`}>
        <InfoCircleOutlined />
      </Tooltip>
    </Space>
  )

  if (compact) {
    return (
      <Card 
        className={`mod-info-card-compact ${className}`}
       
        hoverable
        style={{ marginBottom: 8 }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg">{loaderConfig.icon}</span>
            <div>
              <Text strong>{mod.name}</Text>
              <br />
              <Text type="secondary" className="text-xs">
                {mod.mod_id} • v{mod.version}
              </Text>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Tag color={loaderConfig.color}>
              {loaderConfig.displayName}
            </Tag>
            {mod.minecraft_version && (
              <Tag color="blue">
                MC {mod.minecraft_version}
              </Tag>
            )}
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card
      className={`mod-info-card ${className}`}
      title={cardTitle}
      extra={cardExtra}
      hoverable
      style={{ 
        marginBottom: 16,
        borderLeft: `4px solid ${loaderConfig.color}`
      }}
    >
      <div className="space-y-4">
        {/* 基本信息 */}
        <Descriptions column={2} bordered>
          <Descriptions.Item label="版本" span={1}>
            <Badge count={mod.version} color="blue" />
          </Descriptions.Item>
          
          <Descriptions.Item label="Minecraft版本" span={1}>
            {mod.minecraft_version ? (
              <Tag color="green">MC {mod.minecraft_version}</Tag>
            ) : (
              <Text type="secondary">未知</Text>
            )}
          </Descriptions.Item>

          <Descriptions.Item label="支持环境" span={1}>
            <Tag color={sideConfig.color}>{sideConfig.text}</Tag>
          </Descriptions.Item>

          <Descriptions.Item label="文件大小" span={1}>
            <Text code>{formatFileSize(mod.file_size)}</Text>
          </Descriptions.Item>

          {mod.license && (
            <Descriptions.Item label="许可证" span={2}>
              <Tag icon={<CodeOutlined />} color="default">
                {mod.license}
              </Tag>
            </Descriptions.Item>
          )}
        </Descriptions>

        {/* 描述 */}
        {mod.description && (
          <div>
            <Text type="secondary" className="text-sm">
              {mod.description}
            </Text>
          </div>
        )}

        {/* 作者信息 */}
        {mod.authors && mod.authors.length > 0 && (
          <div>
            <Text strong className="text-sm">作者：</Text>
            <div className="flex flex-wrap gap-1 mt-1">
              {mod.authors.slice(0, 3).map((author, index) => (
                <Tag 
                  key={index}
                  icon={<UserOutlined />}
                  color="blue"
                  className="text-xs"
                >
                  {author}
                </Tag>
              ))}
              {mod.authors.length > 3 && (
                <Tooltip title={mod.authors.slice(3).join(', ')}>
                  <Tag color="blue" className="text-xs">
                    +{mod.authors.length - 3} 更多
                  </Tag>
                </Tooltip>
              )}
            </div>
          </div>
        )}

        {/* 依赖信息 */}
        {mod.dependencies && mod.dependencies.length > 0 && (
          <div>
            <Text strong className="text-sm">依赖MOD：</Text>
            <div className="flex flex-wrap gap-1 mt-1">
              {mod.dependencies.slice(0, 5).map((dep, index) => (
                <Tag key={index} color="orange" className="text-xs">
                  {dep}
                </Tag>
              ))}
              {mod.dependencies.length > 5 && (
                <Tooltip title={mod.dependencies.slice(5).join(', ')}>
                  <Tag color="orange" className="text-xs">
                    +{mod.dependencies.length - 5} 更多
                  </Tag>
                </Tooltip>
              )}
            </div>
          </div>
        )}

        {/* 加载器详细信息 */}
        {mod.loader_info && (
          <div className="bg-gray-50 p-3 rounded-lg">
            <Text strong className="text-sm">加载器信息：</Text>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div>
                <Text className="text-xs text-gray-500">加载器版本：</Text>
                <br />
                <Text code className="text-xs">{mod.loader_info.version}</Text>
              </div>
              <div>
                <Text className="text-xs text-gray-500">能力：</Text>
                <br />
                <div className="flex flex-wrap gap-1">
                  {mod.loader_info.capabilities?.slice(0, 3).map((cap, index) => (
                    <Tag key={index} color="cyan">
                      {cap}
                    </Tag>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 链接 */}
        {mod.homepage && (
          <div className="flex gap-2">
            <Link href={mod.homepage} target="_blank" className="text-sm">
              <HomeOutlined /> 项目主页
            </Link>
          </div>
        )}
      </div>
    </Card>
  )
}

export default ModInfoCard