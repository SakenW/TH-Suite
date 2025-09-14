/**
 * 最简测试页面
 */

import React from 'react'
import { Card, Typography } from 'antd'

const { Title, Text } = Typography

export const TestPage: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={1}>🎮 TH Suite MC L10n</Title>
        <Title level={3}>测试页面</Title>
        <Text>如果你能看到这段文字，说明Ant Design架构运行正常！</Text>
        <div style={{ marginTop: 24 }}>
          <p>✅ React 19 运行正常</p>
          <p>✅ Ant Design 加载成功</p>
          <p>✅ Minecraft 轻装饰主题已启用</p>
          <p>✅ 路由系统工作正常</p>
        </div>
      </Card>
    </div>
  )
}

export default TestPage