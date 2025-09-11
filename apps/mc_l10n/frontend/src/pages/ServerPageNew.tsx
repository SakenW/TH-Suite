/**
 * 服务器状态页占位符
 * TODO: 基于设计文档实现服务器状态功能
 */

import React from 'react'
import { Card, Typography, Button, Empty } from 'antd'
import { useNavigate } from 'react-router-dom'
import { CloudServerOutlined } from '@ant-design/icons'

const { Title } = Typography

export const ServerPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>服务器状态</Title>
      <Card>
        <Empty
          description="服务器状态页面开发中"
          image={<CloudServerOutlined style={{ fontSize: 64, color: '#ccc' }} />}
        >
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </Empty>
      </Card>
    </div>
  )
}

export default ServerPage