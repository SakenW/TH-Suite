/**
 * 简化版欢迎页
 * 确保稳定运行的最小化版本
 */

import React from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Typography,
  Badge,
  Divider,
  Statistic,
  Progress,
} from 'antd'
import {
  ScanOutlined,
  SyncOutlined,
  BuildOutlined,
  FolderOutlined,
  CloudServerOutlined,
  SettingOutlined,
  HomeOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeProvider'

const { Title, Text, Paragraph } = Typography

export const WelcomePageSimple: React.FC = () => {
  const navigate = useNavigate()
  const { colors } = useTheme()

  const quickActions = [
    {
      title: '扫描项目',
      description: '扫描本地MOD和整合包，识别需要翻译的内容',
      icon: <ScanOutlined />,
      path: '/scan',
      color: '#52c41a',
    },
    {
      title: '同步翻译',
      description: '与Trans-Hub服务器同步最新翻译内容',
      icon: <SyncOutlined />,
      path: '/sync',
      color: '#1890ff',
    },
    {
      title: '构建产物',
      description: '生成本地化资源包和MOD文件',
      icon: <BuildOutlined />,
      path: '/build',
      color: '#722ed1',
    },
  ]

  const projectStats = [
    { title: '整合包项目', value: 3, suffix: '个' },
    { title: 'MOD项目', value: 12, suffix: '个' },
    { title: '翻译进度', value: 78.5, suffix: '%' },
    { title: '可拉取更新', value: 234, suffix: '条' },
  ]

  return (
    <div style={{ padding: 24 }}>
      {/* 欢迎标题 */}
      <Row style={{ marginBottom: 32 }}>
        <Col span={24}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Title level={1} style={{ color: colors.primary, marginBottom: 8 }}>
              🎮 TH Suite MC L10n
            </Title>
            <Title level={3} style={{ color: '#666', fontWeight: 400 }}>
              Minecraft 本地化工具套件
            </Title>
            <Paragraph style={{ fontSize: 16, color: '#888', maxWidth: 600, margin: '0 auto' }}>
              专业的 Minecraft 模组和整合包本地化工具，支持与 Trans-Hub 平台深度集成，
              提供完整的翻译工作流：扫描 → 同步 → 构建。
            </Paragraph>
          </div>
        </Col>
      </Row>

      {/* 统计概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {projectStats.map((stat, index) => (
          <Col xs={12} sm={6} key={index}>
            <Card>
              <Statistic
                title={stat.title}
                value={stat.value}
                suffix={stat.suffix}
                valueStyle={{ 
                  color: index === 2 ? colors.primary : undefined,
                  fontSize: 24 
                }}
              />
              {index === 2 && (
                <Progress 
                  percent={stat.value as number} 
                  strokeColor={colors.primary}
                  showInfo={false}
                  style={{ marginTop: 8 }}
                />
              )}
            </Card>
          </Col>
        ))}
      </Row>

      {/* 快速操作 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col span={24}>
          <Title level={3}>
            <HomeOutlined style={{ marginRight: 8 }} />
            快速开始
          </Title>
        </Col>
        {quickActions.map((action, index) => (
          <Col xs={24} sm={8} key={index}>
            <Card
              hoverable
              style={{
                borderColor: action.color,
                borderWidth: 2,
                height: '100%',
              }}
              onClick={() => navigate(action.path)}
            >
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <div style={{ 
                  fontSize: 48, 
                  color: action.color,
                  marginBottom: 16 
                }}>
                  {action.icon}
                </div>
                <Title level={4} style={{ marginBottom: 8 }}>
                  {action.title}
                </Title>
                <Text type="secondary">{action.description}</Text>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Divider />

      {/* 系统状态 */}
      <Row gutter={[24, 24]}>
        <Col xs={24} md={12}>
          <Card title="项目管理" extra={<FolderOutlined />}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>整合包项目</Text>
                <Button type="link" onClick={() => navigate('/projects/packs')}>
                  查看全部 →
                </Button>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>MOD项目</Text>
                <Button type="link" onClick={() => navigate('/projects/mods')}>
                  查看全部 →
                </Button>
              </div>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="服务器状态" extra={<CloudServerOutlined />}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text>Trans-Hub 连接</Text>
                <Badge status="success" text="已连接" />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text>本地服务</Text>
                <Badge status="processing" text="运行中" />
              </div>
              <Button type="link" onClick={() => navigate('/server')}>
                查看详情 →
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 底部快速链接 */}
      <div style={{ textAlign: 'center', marginTop: 48, paddingTop: 24, borderTop: '1px solid #f0f0f0' }}>
        <Space>
          <Button 
            type="link" 
            icon={<SettingOutlined />} 
            onClick={() => navigate('/settings')}
          >
            设置
          </Button>
          <Button 
            type="link" 
            icon={<CloudServerOutlined />} 
            onClick={() => navigate('/server')}
          >
            服务器状态
          </Button>
          <Button type="link" href="https://docs.trans-hub.com" target="_blank">
            帮助文档
          </Button>
        </Space>
      </div>
    </div>
  )
}

export default WelcomePageSimple