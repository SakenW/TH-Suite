/**
 * 构建中心页占位符
 * TODO: 基于设计文档实现构建中心功能
 */

import React from 'react'
import { Card, Typography, Button, Empty } from 'antd'
import { useNavigate } from 'react-router-dom'
import { BuildOutlined } from '@ant-design/icons'

const { Title } = Typography

export const BuildPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>构建中心</Title>
      <Card>
        <Empty
          description="构建中心页面开发中"
          image={<BuildOutlined style={{ fontSize: 64, color: '#ccc' }} />}
        >
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </Empty>
      </Card>
    </div>
  )
}

export default BuildPage