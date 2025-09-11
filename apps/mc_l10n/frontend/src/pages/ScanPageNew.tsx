/**
 * 扫描中心页面 - 实现目录扫描功能
 * 支持增量扫描、进度监控、结果展示
 */

import React, { useState, useRef, useCallback } from 'react'
import { 
  Card, 
  Typography, 
  Button, 
  Input, 
  Space, 
  Progress, 
  Alert, 
  Table, 
  Tag, 
  Tooltip,
  Divider,
  Row,
  Col,
  notification,
  Spin,
  Empty
} from 'antd'
import { 
  FolderOpenOutlined, 
  ScanOutlined, 
  ReloadOutlined, 
  StopOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  HourglassOutlined
} from '@ant-design/icons'
import { scanApi } from '../services/api'
import type { ScanRequest, ScanStatus, ScanResult } from '../services/api/types'

const { Title, Text } = Typography
const { TextArea } = Input

interface ScanPageState {
  directory: string
  isScanning: boolean
  scanId: string | null
  progress: ScanStatus | null
  result: ScanResult | null
  error: string | null
  connectionStatus: boolean | null
}

export const ScanPage: React.FC = () => {
  const [state, setState] = useState<ScanPageState>({
    directory: '',
    isScanning: false,
    scanId: null,
    progress: null,
    result: null,
    error: null,
    connectionStatus: null
  })

  const abortControllerRef = useRef<AbortController | null>(null)

  // 测试后端连接
  const testConnection = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, connectionStatus: null }))
      const isConnected = await scanApi.testConnection()
      setState(prev => ({ ...prev, connectionStatus: isConnected }))
      if (isConnected) {
        notification.success({ message: '后端连接正常', duration: 2 })
      } else {
        notification.error({ message: '后端连接失败', description: '请检查后端服务是否启动' })
      }
    } catch (error) {
      setState(prev => ({ ...prev, connectionStatus: false }))
      notification.error({ message: '连接测试失败', description: String(error) })
    }
  }, [])

  // 选择目录（Tauri）
  const selectDirectory = useCallback(async () => {
    try {
      // @ts-ignore - Tauri API
      if (typeof window.__TAURI__ !== 'undefined') {
        // const { open } = await import('@tauri-apps/api/dialog')
        // const selected = await open({
        //   directory: true,
        //   multiple: false,
        // })
        const selected = null // 暂时禁用Tauri功能
        if (selected && typeof selected === 'string') {
          setState(prev => ({ ...prev, directory: selected }))
        }
      } else {
        // Web环境提示
        notification.info({ 
          message: '目录选择', 
          description: '在Web环境中请手动输入目录路径' 
        })
      }
    } catch (error) {
      notification.error({ message: '选择目录失败', description: String(error) })
    }
  }, [])

  // 开始扫描
  const startScan = useCallback(async () => {
    if (!state.directory.trim()) {
      notification.warning({ message: '请先选择或输入目录路径' })
      return
    }

    setState(prev => ({ 
      ...prev, 
      isScanning: true, 
      scanId: null, 
      progress: null, 
      result: null, 
      error: null 
    }))

    abortControllerRef.current = new AbortController()

    const scanRequest: ScanRequest = {
      directory: state.directory.trim(),
      incremental: true
    }

    try {
      const result = await scanApi.executeScanWorkflow(
        scanRequest,
        {
          onStart: (scanId) => {
            setState(prev => ({ ...prev, scanId }))
            notification.success({ message: `扫描已启动`, description: `任务ID: ${scanId}` })
          },
          onProgress: (status) => {
            setState(prev => ({ ...prev, progress: status }))
          },
          onComplete: (result) => {
            setState(prev => ({ ...prev, result }))
            notification.success({ message: '扫描完成', description: `共发现 ${result.statistics.total_files} 个文件` })
          },
          onError: (error) => {
            setState(prev => ({ ...prev, error: error.message }))
            notification.error({ message: '扫描失败', description: error.message })
          }
        },
        {
          signal: abortControllerRef.current.signal,
          timeout: 10 * 60 * 1000 // 10分钟超时
        }
      )

      setState(prev => ({ ...prev, result }))
    } catch (error) {
      setState(prev => ({ ...prev, error: String(error) }))
    } finally {
      setState(prev => ({ ...prev, isScanning: false }))
      abortControllerRef.current = null
    }
  }, [state.directory])

  // 停止扫描
  const stopScan = useCallback(async () => {
    if (state.scanId) {
      try {
        await scanApi.cancelScan(state.scanId)
        notification.info({ message: '正在停止扫描...' })
      } catch (error) {
        notification.error({ message: '停止扫描失败', description: String(error) })
      }
    }
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }, [state.scanId])

  // 重新扫描
  const restartScan = useCallback(() => {
    setState(prev => ({ 
      ...prev, 
      progress: null, 
      result: null, 
      error: null,
      scanId: null
    }))
    startScan()
  }, [startScan])

  // 渲染进度信息
  const renderProgress = () => {
    if (!state.progress) return null

    const { current_file, processed_files, total_files, status, started_at } = state.progress

    const percent = total_files > 0 ? Math.round((processed_files / total_files) * 100) : 0
    const elapsed = started_at ? Date.now() - new Date(started_at).getTime() : 0
    const elapsedSeconds = Math.floor(elapsed / 1000)

    return (
      <Card title="扫描进度" className="mb-4">
        <Space direction="vertical" className="w-full">
          <div className="flex justify-between items-center">
            <Text>状态: <Tag color={status === 'running' ? 'blue' : status === 'completed' ? 'green' : 'red'}>{status}</Tag></Text>
            <Text>已用时: {elapsedSeconds}s</Text>
          </div>
          
          <Progress 
            percent={percent} 
            status={status === 'failed' ? 'exception' : status === 'completed' ? 'success' : 'active'}
            format={() => `${processed_files}/${total_files}`}
          />
          
          {current_file && (
            <div className="bg-gray-50 p-2 rounded">
              <Text type="secondary" className="text-xs">正在处理: {current_file}</Text>
            </div>
          )}
        </Space>
      </Card>
    )
  }

  // 渲染扫描结果
  const renderResults = () => {
    if (!state.result) return null

    const { statistics, discovered_packs, discovered_mods } = state.result

    const columns = [
      { title: '名称', dataIndex: 'name', key: 'name' },
      { title: '版本', dataIndex: 'version', key: 'version' },
      { title: '平台', dataIndex: 'platform', key: 'platform', render: (platform: string) => <Tag>{platform}</Tag> },
      { title: '语言文件数', dataIndex: 'language_file_count', key: 'language_file_count' }
    ]

    return (
      <Card title="扫描结果" className="mt-4">
        <Row gutter={16} className="mb-4">
          <Col span={6}>
            <Card size="small">
              <div className="text-center">
                <FileTextOutlined className="text-2xl text-blue-500 mb-2" />
                <div className="text-2xl font-bold">{statistics.total_files}</div>
                <div className="text-gray-500">文件总数</div>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <div className="text-center">
                <CheckCircleOutlined className="text-2xl text-green-500 mb-2" />
                <div className="text-2xl font-bold">{statistics.language_files}</div>
                <div className="text-gray-500">语言文件</div>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <div className="text-center">
                <ScanOutlined className="text-2xl text-purple-500 mb-2" />
                <div className="text-2xl font-bold">{discovered_packs.length}</div>
                <div className="text-gray-500">整合包</div>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <div className="text-center">
                <ExclamationCircleOutlined className="text-2xl text-orange-500 mb-2" />
                <div className="text-2xl font-bold">{discovered_mods.length}</div>
                <div className="text-gray-500">模组</div>
              </div>
            </Card>
          </Col>
        </Row>

        {discovered_packs.length > 0 && (
          <>
            <Title level={4}>发现的整合包</Title>
            <Table 
              columns={columns}
              dataSource={discovered_packs.map(pack => ({ ...pack, key: pack.id }))}
              size="small"
              pagination={{ pageSize: 5 }}
            />
          </>
        )}

        {discovered_mods.length > 0 && (
          <>
            <Title level={4}>发现的模组</Title>
            <Table 
              columns={columns}
              dataSource={discovered_mods.map(mod => ({ ...mod, key: mod.id }))}
              size="small"
              pagination={{ pageSize: 5 }}
            />
          </>
        )}
      </Card>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="mb-0">🔍 扫描中心</Title>
        <Space>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={testConnection}
            loading={state.connectionStatus === null}
          >
            测试连接
          </Button>
          {state.connectionStatus !== null && (
            <Tag color={state.connectionStatus ? 'green' : 'red'}>
              {state.connectionStatus ? '连接正常' : '连接失败'}
            </Tag>
          )}
        </Space>
      </div>

      {/* 扫描配置 */}
      <Card title="🔍 扫描配置" className="mb-4">
        <Space direction="vertical" className="w-full">
          {/* 扫描说明 */}
          <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
            <Text type="secondary" className="text-sm">
              💡 <strong>扫描说明:</strong> 选择包含 Minecraft 模组或整合包的目录。
              支持扫描 .jar 文件、.zip 文件和解压后的文件夹，自动识别语言文件。
            </Text>
          </div>

          {/* 快速示例目录 */}
          <div>
            <Text strong className="block mb-2">📁 常见目录示例:</Text>
            <Space wrap>
              {[
                'D:\\Games\\Curseforge\\Minecraft\\Instances\\DeceasedCraft - Modern Zombie Apocalypse',
                '/home/user/.minecraft/mods',
                'C:\\Users\\User\\AppData\\Roaming\\.minecraft\\mods',
                'D:\\Games\\Minecraft\\mods'
              ].map(example => (
                <Button 
                  key={example}
                  size="small" 
                  type={example.includes('DeceasedCraft') ? 'primary' : 'dashed'}
                  onClick={() => setState(prev => ({ ...prev, directory: example }))}
                  disabled={state.isScanning}
                  className="text-xs"
                >
                  {example.includes('DeceasedCraft') ? '🎯 ' : ''}{example}
                </Button>
              ))}
            </Space>
          </div>

          {/* 目录输入 */}
          <div>
            <Text strong>📂 目录路径:</Text>
            <div className="flex gap-2 mt-1">
              <Input
                value={state.directory}
                onChange={(e) => setState(prev => ({ ...prev, directory: e.target.value }))}
                placeholder="输入要扫描的目录路径，例如: /home/user/.minecraft/mods"
                className="flex-1"
                disabled={state.isScanning}
              />
              <Button 
                icon={<FolderOpenOutlined />} 
                onClick={selectDirectory}
                disabled={state.isScanning}
                title="浏览选择目录"
              >
                浏览
              </Button>
            </div>
          </div>

          {/* 扫描选项 */}
          <div>
            <Text strong className="block mb-2">⚙️ 扫描选项:</Text>
            <Space wrap>
              <Tooltip title="只扫描新文件和变更的文件，跳过已处理的内容">
                <Tag color="blue" className="cursor-help">
                  <CheckCircleOutlined /> 增量扫描（推荐）
                </Tag>
              </Tooltip>
              <Tooltip title="包括 .jar、.zip 文件和文件夹">
                <Tag color="green" className="cursor-help">
                  <FileTextOutlined /> 智能文件识别
                </Tag>
              </Tooltip>
              <Tooltip title="自动检测 JSON、Properties 等语言文件格式">
                <Tag color="purple" className="cursor-help">
                  <TranslationOutlined /> 多格式支持
                </Tag>
              </Tooltip>
            </Space>
          </div>

          {/* 操作按钮 */}
          <Space size="large" className="pt-2">
            <Button
              type="primary"
              size="large"
              icon={<ScanOutlined />}
              onClick={startScan}
              loading={state.isScanning}
              disabled={!state.directory.trim() || state.connectionStatus === false}
              className="min-w-32"
            >
              {state.isScanning ? '扫描中...' : '🚀 开始扫描'}
            </Button>
            
            {state.isScanning && (
              <Button 
                size="large"
                icon={<StopOutlined />} 
                onClick={stopScan}
                danger
              >
                ⏹️ 停止扫描
              </Button>
            )}

            {state.result && !state.isScanning && (
              <Button 
                size="large"
                icon={<ReloadOutlined />} 
                onClick={restartScan}
              >
                🔄 重新扫描
              </Button>
            )}

            {/* 连接状态提示 */}
            {state.connectionStatus === false && (
              <Text type="danger" className="text-sm">
                ⚠️ 后端服务未连接，无法扫描
              </Text>
            )}
          </Space>
        </Space>
      </Card>

      {/* 错误信息 */}
      {state.error && (
        <Alert
          type="error"
          message="扫描失败"
          description={state.error}
          showIcon
          closable
          onClose={() => setState(prev => ({ ...prev, error: null }))}
          className="mb-4"
        />
      )}

      {/* 扫描进度 */}
      {renderProgress()}

      {/* 扫描结果 */}
      {renderResults()}

      {/* 空状态和引导 */}
      {!state.isScanning && !state.result && !state.error && (
        <div>
          {/* 快速入门指导 */}
          <Card title="🎯 快速入门" className="mb-4">
            <Row gutter={16}>
              <Col span={8}>
                <Card size="small" className="text-center h-full">
                  <div className="text-4xl mb-2">📁</div>
                  <Text strong>1. 选择目录</Text>
                  <div className="text-xs text-gray-500 mt-1">
                    选择包含 .jar 模组文件或整合包的目录
                  </div>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" className="text-center h-full">
                  <div className="text-4xl mb-2">🔍</div>
                  <Text strong>2. 开始扫描</Text>
                  <div className="text-xs text-gray-500 mt-1">
                    自动识别模组和语言文件
                  </div>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" className="text-center h-full">
                  <div className="text-4xl mb-2">📊</div>
                  <Text strong>3. 查看结果</Text>
                  <div className="text-xs text-gray-500 mt-1">
                    查看发现的模组和翻译状态
                  </div>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 测试目录建议 */}
          <Card title="🧪 测试扫描" className="mb-4">
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <Text strong className="block mb-2">💡 没有现成的模组目录？试试这些方法：</Text>
              <Space direction="vertical" size="small" className="w-full">
                <div>
                  <Text strong>• 创建测试目录：</Text>
                  <code className="ml-2 bg-gray-100 px-2 py-1 rounded text-xs">
                    mkdir ~/minecraft-test && cd ~/minecraft-test
                  </code>
                </div>
                <div>
                  <Text strong>• 下载一些示例模组：</Text>
                  <div className="ml-4 text-sm text-gray-600">
                    - 从 CurseForge 或 Modrinth 下载几个 .jar 模组文件
                    - 或者扫描已有的 .minecraft/mods 目录
                  </div>
                </div>
                <div>
                  <Text strong>• 使用当前目录：</Text>
                  <Button 
                    size="small" 
                    type="link" 
                    onClick={() => setState(prev => ({ ...prev, directory: '/tmp' }))}
                    className="p-0 h-auto"
                  >
                    点击使用 /tmp 目录进行测试
                  </Button>
                </div>
              </Space>
            </div>
          </Card>

          {/* 空状态图标 */}
          <Card>
            <Empty
              image={<HourglassOutlined className="text-6xl text-gray-300" />}
              description={
                <div>
                  <Text type="secondary">准备好了吗？选择目录开始扫描！</Text>
                  <br />
                  <Text type="secondary" className="text-xs">
                    支持 Minecraft 模组(.jar)、整合包和资源包的自动识别
                  </Text>
                </div>
              }
            />
          </Card>
        </div>
      )}
    </div>
  )
}

export default ScanPage