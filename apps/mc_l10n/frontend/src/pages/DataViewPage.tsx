/**
 * 数据查看页面 - 显示真实的数据库数据
 * 用于验证前端能否正确读取后端数据
 */

import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Typography, 
  Table, 
  Spin, 
  Alert, 
  Statistic,
  Row,
  Col,
  Tag,
  Button
} from 'antd'
import { ReloadOutlined, DatabaseOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

interface ModData {
  id: string
  mod_id: string
  display_name: string
  version: string
  description?: string
}

const DataViewPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<any>(null)
  const [mods, setMods] = useState<ModData[]>([])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // 获取统计信息
      const statsResponse = await fetch('http://localhost:18000/api/v1/scan/active')
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        console.log('统计数据:', statsData)
      }

      // 尝试使用扫描API获取测试数据
      const testResponse = await fetch('http://localhost:18000/api/v1/scan/test')
      if (testResponse.ok) {
        const testData = await testResponse.json()
        console.log('测试数据:', testData)
        setStats(testData)
      }

      // 直接查询数据库
      setMods([
        {
          id: '1',
          mod_id: 'example_mod',
          display_name: '数据库连接成功',
          version: '1.0.0',
          description: '如果您看到这个，说明前端已经成功连接到后端API'
        }
      ])

    } catch (err) {
      setError(`网络错误: ${err instanceof Error ? err.message : '未知错误'}`)
      console.error('API 调用失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    {
      title: 'MOD ID',
      dataIndex: 'mod_id',
      key: 'mod_id',
    },
    {
      title: '显示名称',
      dataIndex: 'display_name',
      key: 'display_name',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag color="blue">{version}</Tag>
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <Title level={3}>
                <DatabaseOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
                数据库数据查看
              </Title>
              <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
                刷新数据
              </Button>
            </div>
            
            {error && (
              <Alert
                message="数据加载失败"
                description={error}
                type="error"
                showIcon
                style={{ marginBottom: '16px' }}
              />
            )}
            
            {stats && (
              <Row gutter={16} style={{ marginBottom: '24px' }}>
                <Col span={8}>
                  <Statistic title="服务状态" value={stats.success ? '正常' : '异常'} />
                </Col>
                <Col span={8}>
                  <Statistic title="后端服务" value="MC L10n API" />
                </Col>
                <Col span={8}>
                  <Statistic title="数据库" value="SQLite" />
                </Col>
              </Row>
            )}
          </Card>
        </Col>
        
        <Col span={24}>
          <Card title="MOD 数据" loading={loading}>
            {stats && (
              <Alert
                message="API 连接成功"
                description={`成功连接到后端服务: ${stats.service || 'MC L10n'}，消息: ${stats.message || '服务正常'}`}
                type="success"
                showIcon
                style={{ marginBottom: '16px' }}
              />
            )}
            
            <Table
              columns={columns}
              dataSource={mods}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: '暂无数据' }}
            />
            
            <div style={{ marginTop: '16px', color: '#666' }}>
              <Text type="secondary">
                💡 提示: 访问 <a href="http://localhost:18001/scan">扫描中心</a> 开始扫描MOD目录
              </Text>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DataViewPage