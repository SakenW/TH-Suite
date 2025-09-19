// DatabaseTestPage.tsx - 数据库功能演示页面
import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Input,
  Form,
  Table,
  Space,
  Typography,
  Alert,
  Tabs,
  Statistic,
  Row,
  Col,
  message,
  Spin,
  Tag,
  Divider,
  Modal
} from 'antd';
import {
  DatabaseOutlined,
  SecurityScanOutlined,
  PerformanceOutlined,
  SettingOutlined,
  FileProtectOutlined,
  CloudSyncOutlined
} from '@ant-design/icons';
import { encryptedDb, type DatabaseStats, type SecurityConfig } from '../services/database/EncryptedDatabaseService';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface TestRecord {
  id: number;
  name: string;
  value: string;
  created_at: string;
}

export const DatabaseTestPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [dbStats, setDbStats] = useState<DatabaseStats | null>(null);
  const [securityConfig, setSecurityConfig] = useState<SecurityConfig | null>(null);
  const [testRecords, setTestRecords] = useState<TestRecord[]>([]);
  const [deviceFingerprint, setDeviceFingerprint] = useState<string>('');
  const [queryResult, setQueryResult] = useState<any[]>([]);
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM test_records LIMIT 10');
  
  const [form] = Form.useForm();

  useEffect(() => {
    initializeDatabase();
  }, []);

  const initializeDatabase = async () => {
    setLoading(true);
    try {
      // 初始化数据库
      const result = await encryptedDb.initialize();
      message.success(result);
      setInitialized(true);

      // 获取安全配置
      const config = await encryptedDb.initializeSecurityConfig();
      setSecurityConfig(config);

      // 获取设备指纹
      const fingerprint = await encryptedDb.getDeviceFingerprint();
      setDeviceFingerprint(fingerprint);

      // 创建测试表
      await createTestTable();
      
      // 刷新数据
      await refreshData();
      
    } catch (error) {
      message.error(`初始化失败: ${error}`);
      console.error('Database initialization failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const createTestTable = async () => {
    try {
      await encryptedDb.execute(`
        CREATE TABLE IF NOT EXISTS test_records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          value TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);
    } catch (error) {
      console.error('Failed to create test table:', error);
    }
  };

  const refreshData = async () => {
    try {
      // 刷新数据库统计
      const stats = await encryptedDb.getStats();
      setDbStats(stats);

      // 刷新测试记录
      const records = await encryptedDb.findMany('test_records', {}, ['*'], 'created_at DESC', 20);
      setTestRecords(records as TestRecord[]);

    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  };

  const handleAddRecord = async (values: { name: string; value: string }) => {
    setLoading(true);
    try {
      await encryptedDb.insert('test_records', values);
      message.success('记录添加成功');
      form.resetFields();
      await refreshData();
    } catch (error) {
      message.error(`添加失败: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRecord = async (id: number) => {
    try {
      await encryptedDb.delete('test_records', { id });
      message.success('记录删除成功');
      await refreshData();
    } catch (error) {
      message.error(`删除失败: ${error}`);
    }
  };

  const handleOptimizeDatabase = async () => {
    setLoading(true);
    try {
      const result = await encryptedDb.optimize();
      message.success(result);
      await refreshData();
    } catch (error) {
      message.error(`优化失败: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIntegrity = async () => {
    setLoading(true);
    try {
      const isValid = await encryptedDb.checkIntegrity();
      if (isValid) {
        message.success('数据库完整性检查通过');
      } else {
        message.error('数据库完整性检查失败');
      }
    } catch (error) {
      message.error(`完整性检查失败: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteQuery = async () => {
    setLoading(true);
    try {
      const result = await encryptedDb.query(sqlQuery);
      setQueryResult(result);
      message.success(`查询成功，返回 ${result.length} 条记录`);
    } catch (error) {
      message.error(`查询失败: ${error}`);
      setQueryResult([]);
    } finally {
      setLoading(false);
    }
  };

  const handleBackupDatabase = async () => {
    setLoading(true);
    try {
      const backupPath = `./backup_${Date.now()}.db`;
      const result = await encryptedDb.backup(backupPath);
      message.success(result);
    } catch (error) {
      message.error(`备份失败: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePerformanceTest = async () => {
    setLoading(true);
    const testSize = 1000;
    
    try {
      const startTime = Date.now();
      
      // 批量插入测试
      await encryptedDb.transaction(async (db) => {
        for (let i = 0; i < testSize; i++) {
          await db.insert('test_records', {
            name: `性能测试记录 ${i}`,
            value: `测试数据 ${Math.random().toString(36).substring(7)}`
          });
        }
      });
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      message.success(
        `性能测试完成: 插入 ${testSize} 条记录耗时 ${duration}ms (${(testSize / duration * 1000).toFixed(2)} 记录/秒)`
      );
      
      await refreshData();
      
    } catch (error) {
      message.error(`性能测试失败: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCleanTestData = async () => {
    Modal.confirm({
      title: '确认清理',
      content: '是否确认删除所有测试数据？此操作不可撤销。',
      onOk: async () => {
        setLoading(true);
        try {
          await encryptedDb.execute('DELETE FROM test_records');
          message.success('测试数据已清理');
          await refreshData();
        } catch (error) {
          message.error(`清理失败: ${error}`);
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const recordColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: TestRecord) => (
        <Button
          type="link"
          danger
          size="small"
          onClick={() => handleDeleteRecord(record.id)}
        >
          删除
        </Button>
      ),
    },
  ];

  const queryColumns = queryResult.length > 0 
    ? Object.keys(queryResult[0]).map(key => ({
        title: key,
        dataIndex: key,
        key,
        ellipsis: true,
      }))
    : [];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <DatabaseOutlined /> SQLCipher 加密数据库测试
      </Title>
      
      {!initialized && (
        <Alert
          message="数据库未初始化"
          description="请等待数据库初始化完成"
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Tabs
        defaultActiveKey="overview"
        items={[
          {
            key: 'overview',
            label: (
              <span>
                <DatabaseOutlined />
                概览
              </span>
            ),
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="数据库状态"
                      value={initialized ? "已初始化" : "未初始化"}
                      valueStyle={{ color: initialized ? '#3f8600' : '#cf1322' }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="页面数量"
                      value={dbStats?.page_count || 0}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="数据库大小"
                      value={dbStats?.database_size || 0}
                      suffix="字节"
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="缓存命中率"
                      value={dbStats?.cache_hit_ratio ? (dbStats.cache_hit_ratio * 100).toFixed(2) : 'N/A'}
                      suffix="%"
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'security',
            label: (
              <span>
                <SecurityScanOutlined />
                安全配置
              </span>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card title="设备指纹">
                  <Paragraph>
                    <Text strong>指纹哈希:</Text> {deviceFingerprint.substring(0, 32)}...
                  </Paragraph>
                  <Paragraph>
                    <Text type="secondary">
                      设备指纹用于生成设备特定的加密密钥，确保数据库只能在当前设备上解密。
                    </Text>
                  </Paragraph>
                </Card>
                
                <Card title="安全配置">
                  {securityConfig && (
                    <Space direction="vertical">
                      <div>
                        <Text strong>设备指纹哈希:</Text> 
                        <Tag color="blue">{securityConfig.device_fingerprint_hash}</Tag>
                      </div>
                      <div>
                        <Text strong>用户口令启用:</Text> 
                        <Tag color={securityConfig.user_passphrase_enabled ? 'green' : 'orange'}>
                          {securityConfig.user_passphrase_enabled ? '已启用' : '未启用'}
                        </Tag>
                      </div>
                      <div>
                        <Text strong>验证哈希:</Text> 
                        <Tag color={securityConfig.has_verification_hash ? 'green' : 'orange'}>
                          {securityConfig.has_verification_hash ? '已配置' : '未配置'}
                        </Tag>
                      </div>
                    </Space>
                  )}
                </Card>
              </Space>
            ),
          },
          {
            key: 'data',
            label: (
              <span>
                <FileProtectOutlined />
                数据管理
              </span>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card title="添加测试记录">
                  <Form
                    form={form}
                    layout="inline"
                    onFinish={handleAddRecord}
                    style={{ marginBottom: 16 }}
                  >
                    <Form.Item name="name" rules={[{ required: true, message: '请输入名称' }]}>
                      <Input placeholder="记录名称" />
                    </Form.Item>
                    <Form.Item name="value" rules={[{ required: true, message: '请输入值' }]}>
                      <Input placeholder="记录值" />
                    </Form.Item>
                    <Form.Item>
                      <Button type="primary" htmlType="submit" loading={loading}>
                        添加记录
                      </Button>
                    </Form.Item>
                  </Form>
                </Card>

                <Card 
                  title={`测试记录 (${testRecords.length} 条)`}
                  extra={
                    <Space>
                      <Button onClick={refreshData}>刷新</Button>
                      <Button danger onClick={handleCleanTestData}>
                        清理数据
                      </Button>
                    </Space>
                  }
                >
                  <Table
                    columns={recordColumns}
                    dataSource={testRecords}
                    rowKey="id"
                    size="small"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showQuickJumper: true,
                    }}
                  />
                </Card>
              </Space>
            ),
          },
          {
            key: 'query',
            label: (
              <span>
                <SettingOutlined />
                SQL 查询
              </span>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card title="执行 SQL 查询">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <TextArea
                      value={sqlQuery}
                      onChange={(e) => setSqlQuery(e.target.value)}
                      placeholder="输入 SQL 查询语句"
                      rows={4}
                    />
                    <Button 
                      type="primary" 
                      onClick={handleExecuteQuery}
                      loading={loading}
                    >
                      执行查询
                    </Button>
                  </Space>
                </Card>

                {queryResult.length > 0 && (
                  <Card title={`查询结果 (${queryResult.length} 条记录)`}>
                    <Table
                      columns={queryColumns}
                      dataSource={queryResult}
                      rowKey={(record, index) => index || 0}
                      size="small"
                      scroll={{ x: true }}
                      pagination={{
                        pageSize: 20,
                        showSizeChanger: true,
                        showQuickJumper: true,
                      }}
                    />
                  </Card>
                )}
              </Space>
            ),
          },
          {
            key: 'performance',
            label: (
              <span>
                <PerformanceOutlined />
                性能测试
              </span>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card title="数据库操作">
                  <Space wrap>
                    <Button 
                      type="primary" 
                      onClick={handleOptimizeDatabase}
                      loading={loading}
                      icon={<DatabaseOutlined />}
                    >
                      优化数据库
                    </Button>
                    <Button 
                      onClick={handleCheckIntegrity}
                      loading={loading}
                      icon={<SecurityScanOutlined />}
                    >
                      完整性检查
                    </Button>
                    <Button 
                      onClick={handleBackupDatabase}
                      loading={loading}
                      icon={<CloudSyncOutlined />}
                    >
                      备份数据库
                    </Button>
                  </Space>
                </Card>

                <Card title="性能测试">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Paragraph>
                      此测试将插入 1000 条记录来测试数据库的写入性能。
                    </Paragraph>
                    <Button 
                      type="primary" 
                      danger
                      onClick={handlePerformanceTest}
                      loading={loading}
                      icon={<PerformanceOutlined />}
                    >
                      开始性能测试
                    </Button>
                  </Space>
                </Card>

                {dbStats && (
                  <Card title="数据库统计信息">
                    <Row gutter={[16, 16]}>
                      <Col span={12}>
                        <Statistic title="页面数量" value={dbStats.page_count} />
                      </Col>
                      <Col span={12}>
                        <Statistic 
                          title="数据库大小" 
                          value={`${(dbStats.database_size / 1024).toFixed(2)} KB`} 
                        />
                      </Col>
                      {dbStats.wal_size && (
                        <Col span={12}>
                          <Statistic 
                            title="WAL 大小" 
                            value={`${(dbStats.wal_size / 1024).toFixed(2)} KB`} 
                          />
                        </Col>
                      )}
                      {dbStats.cache_hit_ratio && (
                        <Col span={12}>
                          <Statistic 
                            title="缓存命中率" 
                            value={`${(dbStats.cache_hit_ratio * 100).toFixed(2)}%`} 
                          />
                        </Col>
                      )}
                    </Row>
                  </Card>
                )}
              </Space>
            ),
          },
        ]}
      />

      {loading && (
        <div style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0, 
          background: 'rgba(255, 255, 255, 0.8)', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          zIndex: 9999 
        }}>
          <Spin size="large" />
        </div>
      )}
    </div>
  );
};