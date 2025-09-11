/**
 * 设置页占位符
 * TODO: 基于设计文档实现设置页功能
 */

import React from 'react'
import { Card, Typography, Button, Empty } from 'antd'
import { useNavigate } from 'react-router-dom'
import { SettingOutlined } from '@ant-design/icons'

const { Title } = Typography

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>设置</Title>
      <Card>
        <Empty
          description="设置页面开发中"
          image={<SettingOutlined style={{ fontSize: 64, color: '#ccc' }} />}
        >
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </Empty>
      </Card>
    </div>
  )
}

export default SettingsPage