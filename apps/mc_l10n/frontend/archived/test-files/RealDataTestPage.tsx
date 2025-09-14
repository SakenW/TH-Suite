/**
 * 真实数据测试页面
 * 展示与后端API的完整集成功能
 */

import React, { useState, useEffect } from 'react'
import { Card, Button, Alert, Table, Tag, Progress, notification, Space, Typography, Row, Col, Divider } from 'antd'
import { 
  FolderOutlined, 
  SearchOutlined, 
  SyncOutlined, 
  FileTextOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  ApiOutlined
} from '@ant-design/icons'
import { ScanApiService, ProjectApiService, TransHubSdkService } from '../services/api'

const { Title, Text, Paragraph } = Typography

interface ApiTestResult {
  name: string
  status: 'success' | 'error' | 'pending'
  message: string
  data?: any
}

const RealDataTestPage: React.FC = () => {
  const [testResults, setTestResults] = useState<ApiTestResult[]>([])
  const [isScanning, setIsScanning] = useState(false)
  const [activeScanId, setActiveScanId] = useState<string | null>(null)
  const [scanProgress, setScanProgress] = useState(0)

  // 测试用的真实路径
  const testPath = '/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse'

  // API测试项目
  const runApiTests = async () => {
    const tests: Partial<ApiTestResult>[] = [
      { name: '健康检查', status: 'pending' },
      { name: '扫描服务连接', status: 'pending' },
      { name: 'V6 API连接', status: 'pending' },
      { name: '活跃扫描查询', status: 'pending' },
    ]
    
    setTestResults(tests as ApiTestResult[])

    // 1. 健康检查
    try {
      const healthResponse = await fetch('http://localhost:18000/health')
      const healthData = await healthResponse.json()
      tests[0] = {
        name: '健康检查',
        status: 'success',
        message: `服务状态: ${healthData.status}`,
        data: healthData
      }
    } catch (error) {
      tests[0] = {
        name: '健康检查',
        status: 'error',
        message: `连接失败: ${error}`
      }
    }
    setTestResults([...tests] as ApiTestResult[])

    // 2. 扫描服务测试
    try {
      const scanTest = await scanApi.testConnection()
      tests[1] = {
        name: '扫描服务连接',
        status: scanTest ? 'success' : 'error',
        message: scanTest ? '扫描服务可用' : '扫描服务不可用'
      }
    } catch (error) {
      tests[1] = {
        name: '扫描服务连接', 
        status: 'error',
        message: `扫描服务错误: ${error}`
      }
    }
    setTestResults([...tests] as ApiTestResult[])

    // 3. V6 API测试
    try {
      const v6Response = await v6ApiClient.getMods({ page: 1, limit: 1 })
      tests[2] = {
        name: 'V6 API连接',
        status: 'success',
        message: `V6数据库连接成功，MOD数量: ${v6Response.pagination.total}`,
        data: v6Response
      }
    } catch (error) {
      tests[2] = {
        name: 'V6 API连接',
        status: 'error', 
        message: `V6 API错误: ${error}`
      }
    }
    setTestResults([...tests] as ApiTestResult[])

    // 4. 活跃扫描
    try {
      const activeScans = await scanApi.getActiveScans()
      tests[3] = {
        name: '活跃扫描查询',
        status: 'success',
        message: `活跃扫描: ${activeScans.active_scans.length} 个`,
        data: activeScans
      }
    } catch (error) {
      tests[3] = {
        name: '活跃扫描查询',
        status: 'error',
        message: `活跃扫描查询失败: ${error}`
      }
    }
    setTestResults([...tests] as ApiTestResult[])

    notification.success({
      message: 'API测试完成',
      description: `完成了 ${tests.length} 项API连接测试`
    })
  }

  // 开始真实扫描
  const startRealScan = async () => {
    if (isScanning) {
      notification.warning({
        message: '扫描进行中',
        description: '请等待当前扫描完成'
      })
      return
    }

    setIsScanning(true)
    setScanProgress(0)

    try {
      const scanResult = await scanApi.startScan({
        directory: testPath,
        incremental: true
      })

      const scanId = scanResult.scan_id
      setActiveScanId(scanId)

      notification.info({
        message: '真实扫描已启动',
        description: `扫描ID: ${scanId}`
      })

      // 轮询扫描状态
      const pollStatus = async () => {
        try {
          const status = await scanApi.getScanStatus(scanId)
          
          setScanProgress(status.progress || 0)
          
          if (status.status === 'completed') {
            setIsScanning(false)
            setActiveScanId(null)
            
            notification.success({
              message: '真实扫描完成',
              description: `发现 ${status.statistics.total_mods} 个MOD，${status.statistics.total_keys} 个翻译键`
            })
          } else if (status.status === 'failed') {
            setIsScanning(false)
            setActiveScanId(null)
            
            notification.error({
              message: '扫描失败',
              description: status.message || '扫描过程中发生错误'
            })
          } else if (status.status === 'scanning' || status.status === 'running') {
            setTimeout(pollStatus, 2000) // 2秒轮询一次
          }
        } catch (error) {
          setIsScanning(false)
          setActiveScanId(null)
          
          notification.error({
            message: '状态查询失败',
            description: '无法获取扫描进度'
          })
        }
      }
      
      setTimeout(pollStatus, 2000)

    } catch (error) {
      setIsScanning(false)
      setScanProgress(0)
      
      notification.error({
        message: '启动扫描失败',
        description: error instanceof Error ? error.message : '未知错误'
      })
    }
  }

  const testColumns = [
    {
      title: '测试项目',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <ApiOutlined />
          <span>{text}</span>
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = {
          success: { color: 'success', text: '成功' },
          error: { color: 'error', text: '失败' },
          pending: { color: 'processing', text: '测试中' }
        }[status] || { color: 'default', text: status }
        
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    {
      title: '结果',
      dataIndex: 'message',
      key: 'message',
      render: (text: string) => <Text code>{text}</Text>
    }
  ]

  return (
    <div className="p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <Title level={2}>🧪 真实数据测试</Title>
        <Paragraph type="secondary">
          测试前端与后端API的完整集成，使用真实的Minecraft实例数据
        </Paragraph>
        
        <Alert
          type="info"
          message="测试环境信息"
          description={
            <div>
              <div><strong>后端API:</strong> http://localhost:18000</div>
              <div><strong>测试数据源:</strong> {testPath}</div>
              <div><strong>数据类型:</strong> 真实的Minecraft mod JAR文件</div>
            </div>
          }
          showIcon
          className="mb-4"
        />
      </div>

      {/* 快速操作区 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12}>
          <Card>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div className="text-center">
                <DatabaseOutlined style={{ fontSize: '2em', color: '#1890ff' }} />
                <Title level={4} className="mb-0 mt-2">API连接测试</Title>
              </div>
              <Button 
                type="primary" 
                block 
                icon={<ApiOutlined />}
                onClick={runApiTests}
              >
                运行API测试
              </Button>
            </Space>
          </Card>
        </Col>
        
        <Col xs={24} sm={12}>
          <Card>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div className="text-center">
                <FolderOutlined style={{ fontSize: '2em', color: '#52c41a' }} />
                <Title level={4} className="mb-0 mt-2">真实数据扫描</Title>
              </div>
              <Button 
                type="primary" 
                danger
                block 
                icon={isScanning ? <SyncOutlined spin /> : <SearchOutlined />}
                onClick={startRealScan}
                loading={isScanning}
              >
                {isScanning ? '扫描中...' : '开始真实扫描'}
              </Button>
              
              {isScanning && (
                <div className="mt-3">
                  <Text className="block mb-2">扫描进度：</Text>
                  <Progress 
                    percent={Math.round(scanProgress)} 
                    status={scanProgress >= 100 ? 'success' : 'active'}
                    strokeColor={{
                      '0%': '#108ee9',
                      '100%': '#87d068',
                    }}
                  />
                  {activeScanId && (
                    <Text type="secondary" className="text-xs">
                      扫描ID: {activeScanId}
                    </Text>
                  )}
                </div>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* API测试结果 */}
      <Card title="API测试结果" className="mb-6">
        {testResults.length > 0 ? (
          <Table
            columns={testColumns}
            dataSource={testResults}
            rowKey="name"
            pagination={false}
           
          />
        ) : (
          <div className="text-center py-8">
            <Text type="secondary">点击"运行API测试"开始测试后端连接</Text>
          </div>
        )}
      </Card>

      {/* 技术说明 */}
      <Card title="💡 技术说明">
        <Paragraph>
          <strong>这个测试页面演示了以下功能：</strong>
        </Paragraph>
        <ul>
          <li><strong>API健康检查:</strong> 验证后端服务可用性</li>
          <li><strong>扫描服务测试:</strong> 测试扫描API连接</li>
          <li><strong>V6数据库集成:</strong> 查询V6架构的数据库</li>
          <li><strong>真实数据扫描:</strong> 扫描真实的Minecraft mod文件</li>
          <li><strong>进度实时监控:</strong> 轮询显示扫描进度</li>
          <li><strong>错误处理:</strong> 完整的错误捕获和用户通知</li>
        </ul>
        
        <Divider />
        
        <Paragraph>
          <strong>数据源信息:</strong> 当前使用的是位于 WSL 环境中的真实 Minecraft 实例，
          包含225个mod JAR文件，总计超过26万个翻译条目。扫描过程会解析每个JAR文件中的
          语言资源文件，提取翻译键值对。
        </Paragraph>
      </Card>
    </div>
  )
}

export default RealDataTestPage