# 组件使用指南

基于 Ant Design + Minecraft 轻装饰主题系统的组件使用规范和最佳实践。

## 设计原则

1. **Ant Design 唯一组件库**: 严格使用 AntD 组件，禁止引入其他 UI 库
2. **Minecraft 轻装饰**: 像素化元素仅作装饰，不影响现代交互体验
3. **玩家友好**: 界面文案"人话化"，避免专业术语
4. **安全默认**: 危险操作双确认，默认安全选项

## 核心组件系统

### 1. 主题系统

#### ThemeProvider - 主题提供者

```tsx
import { ThemeProvider } from './contexts/ThemeProvider'

function App() {
  return (
    <ThemeProvider>
      {/* 整个应用 */}
    </ThemeProvider>
  )
}
```

#### useTheme Hook - 主题控制

```tsx
import { useTheme } from './contexts/ThemeProvider'

function MyComponent() {
  const { 
    mode,        // 'light' | 'dark' | 'auto'
    isDark,      // boolean
    toggleTheme, // () => void
    setTheme,    // (mode: ThemeMode) => void
    colors       // MC_COLORS 对象
  } = useTheme()
  
  return (
    <div style={{ color: colors.primary }}>
      <Button onClick={toggleTheme}>
        当前主题: {isDark ? '暗色' : '亮色'}
      </Button>
    </div>
  )
}
```

### 2. 布局组件

#### MainLayout - 主布局

```tsx
import MainLayout from './layouts/MainLayout'

function App() {
  return (
    <MainLayout>
      {/* 页面内容 */}
    </MainLayout>
  )
}
```

**特性**:
- 左侧导航栏（可折叠）
- 顶部状态条
- 响应式设计
- Minecraft 风格装饰

#### TopStatusBar - 顶部状态条

```tsx
import { TopStatusBar } from './components/TopStatusBar'

// 在 MainLayout 中自动包含，无需手动使用
```

**显示内容**:
- 连接状态（✅ 已连接 / ⛔ 离线）
- 快速指标（可拉取 X / 待上传 Y）
- 时间信息（上次扫描/同步时间）
- 主题切换按钮

### 3. Ant Design 组件使用规范

#### 基础组件导入

```tsx
// 布局组件
import { Row, Col, Space, Divider } from 'antd'

// 数据展示
import { Table, Card, Statistic, Progress, Badge, Tag } from 'antd'

// 数据录入
import { Button, Input, Select, Form, Switch, Checkbox } from 'antd'

// 反馈组件
import { Alert, Modal, Notification, Empty, Spin } from 'antd'

// 导航组件
import { Menu, Breadcrumb, Pagination } from 'antd'

// 图标
import { 
  HomeOutlined, 
  ScanOutlined, 
  SyncOutlined,
  BuildOutlined,
  SettingOutlined,
  CloudServerOutlined 
} from '@ant-design/icons'
```

#### 按钮组件

```tsx
// 基础按钮
<Button type="primary">主要操作</Button>
<Button type="default">次要操作</Button>
<Button type="text">文本按钮</Button>

// 带图标
<Button type="primary" icon={<ScanOutlined />}>
  开始扫描
</Button>

// 危险操作（需要确认）
<Button type="primary" danger>
  删除项目
</Button>

// Minecraft 方块化装饰
import { mcDecorationStyles } from '../theme/minecraft'

<Button 
  type="primary" 
  style={mcDecorationStyles.blockButton}
>
  方块化按钮
</Button>
```

#### 卡片组件

```tsx
// 基础卡片
<Card title="卡片标题">
  卡片内容
</Card>

// 带操作的卡片
<Card
  title={
    <Space>
      <FolderOutlined />
      整合包项目
    </Space>
  }
  extra={
    <Button type="primary" icon={<ScanOutlined />}>
      扫描
    </Button>
  }
>
  <Row gutter={16}>
    <Col span={8}>
      <Statistic title="词条数" value={12345} />
    </Col>
    <Col span={8}>
      <Statistic 
        title="覆盖率" 
        value={78.5} 
        suffix="%" 
        valueStyle={{ color: '#4CAF50' }}
      />
    </Col>
  </Row>
</Card>

// Minecraft 像素化装饰
import { mcDecorationStyles } from '../theme/minecraft'

<Card style={mcDecorationStyles.pixelCard}>
  像素化卡片
</Card>
```

#### 表格组件

```tsx
const columns = [
  {
    title: '名称',
    dataIndex: 'name',
    key: 'name',
    render: (text: string, record: any) => (
      <Space>
        <FolderOutlined style={{ color: '#4CAF50' }} />
        <div>
          <Text strong>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.source}
          </Text>
        </div>
      </Space>
    ),
  },
  {
    title: '覆盖率',
    dataIndex: 'coverage',
    key: 'coverage',
    render: (coverage: number) => (
      <Progress 
        percent={coverage} 
        size="small" 
        strokeColor="#4CAF50"
        format={(percent) => `${percent}%`}
      />
    ),
  },
  {
    title: '操作',
    key: 'actions',
    render: (_, record: any) => (
      <Space size="small">
        <Button size="small">详情</Button>
        <Button size="small" icon={<ScanOutlined />}>重扫</Button>
        <Button size="small" icon={<FolderOpenOutlined />} />
      </Space>
    ),
  },
]

<Table
  columns={columns}
  dataSource={data}
  rowKey="id"
  pagination={{
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total, range) => 
      `显示 ${range[0]}-${range[1]} 条，共 ${total} 条数据`,
  }}
/>
```

#### 进度组件

```tsx
// 基础进度条
<Progress percent={78.5} strokeColor="#4CAF50" />

// 圆形进度
<Progress 
  type="circle" 
  percent={85} 
  strokeColor="#4CAF50"
  format={(percent) => `${percent}%`}
/>

// 经验条样式（Minecraft 装饰）
<Progress 
  percent={60}
  strokeColor={{
    '0%': '#4CAF50',
    '100%': '#8BC34A',
  }}
  style={{
    background: 'rgba(76, 175, 80, 0.2)',
    border: '1px solid rgba(0,0,0,0.2)',
    borderRadius: '2px',
  }}
/>
```

#### 标签和徽章

```tsx
// 状态标签
<Tag color="success">已完成</Tag>
<Tag color="processing" icon={<SyncOutlined spin />}>
  扫描中
</Tag>
<Tag color="warning">需要上传</Tag>
<Tag color="error">需要注意</Tag>

// 数量徽章
<Badge count={5} offset={[10, 0]}>
  <Button>通知</Button>
</Badge>

// 状态徽章
<Badge status="success" text="已连接" />
<Badge status="error" text="离线" />
<Badge status="processing" text="同步中" />
```

#### 表单组件

```tsx
<Form layout="vertical">
  <Form.Item 
    label="项目名称" 
    name="name"
    rules={[{ required: true, message: '请输入项目名称' }]}
  >
    <Input placeholder="请输入项目名称" />
  </Form.Item>
  
  <Form.Item 
    label="目标语言" 
    name="languages"
  >
    <Select 
      mode="multiple" 
      placeholder="选择要翻译的语言"
    >
      <Option value="zh_cn">简体中文</Option>
      <Option value="en_us">English (US)</Option>
      <Option value="ja_jp">日本語</Option>
    </Select>
  </Form.Item>
  
  <Form.Item>
    <Space>
      <Button type="primary" htmlType="submit">
        创建项目
      </Button>
      <Button htmlType="button">
        取消
      </Button>
    </Space>
  </Form.Item>
</Form>
```

### 4. Minecraft 装饰样式

#### 预定义装饰样式

```tsx
import { mcDecorationStyles } from '../theme/minecraft'

// 像素化卡片
<Card style={mcDecorationStyles.pixelCard}>
  带网格背景和方块化阴影的卡片
</Card>

// 方块化按钮
<Button style={mcDecorationStyles.blockButton}>
  具有像素化描边和阴影效果的按钮
</Button>

// 经验条进度
<div style={mcDecorationStyles.expBar}>
  Minecraft 风格的经验条
</div>
```

#### 自定义装饰

```tsx
import { MC_COLORS } from '../theme/minecraft'

const customStyle = {
  border: `2px solid ${MC_COLORS.primary}`,
  borderRadius: '4px',
  boxShadow: '2px 2px 0 rgba(0,0,0,0.3)',
  background: `linear-gradient(145deg, ${MC_COLORS.primary}10, ${MC_COLORS.success}05)`,
}
```

### 5. 页面模板

#### 标准页面结构

```tsx
import React from 'react'
import { 
  Row, 
  Col, 
  Card, 
  Button, 
  Typography, 
  Space,
  Statistic,
  Table 
} from 'antd'
import { ScanOutlined, FolderOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeProvider'

const { Title, Text } = Typography

export const PageTemplate: React.FC = () => {
  const navigate = useNavigate()
  const { colors } = useTheme()

  return (
    <div style={{ padding: 24 }}>
      {/* 页头区域 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }}>
            页面标题
          </Title>
          <Text type="secondary">
            人话化的页面描述，告诉用户这个页面是做什么的
          </Text>
        </Col>
        <Col>
          <Space>
            <Button icon={<FolderOutlined />}>
              次要操作
            </Button>
            <Button type="primary" icon={<ScanOutlined />}>
              主要操作
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 统计指标区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={24}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="统计项1"
              value={123}
              suffix="个"
              prefix={<FolderOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="统计项2"
              value={45.6}
              precision={1}
              suffix="%"
              valueStyle={{ color: colors.success }}
            />
          </Col>
          {/* 更多统计项... */}
        </Row>
      </Card>

      {/* 主要内容区域 */}
      <Card>
        {/* 页面主要内容 */}
      </Card>
    </div>
  )
}

export default PageTemplate
```

#### 空状态页面

```tsx
import { Empty, Button } from 'antd'
import { ScanOutlined } from '@ant-design/icons'

function EmptyStatePage() {
  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Empty
          description="暂无数据"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" icon={<ScanOutlined />}>
            开始第一次扫描
          </Button>
        </Empty>
      </Card>
    </div>
  )
}
```

## 文案规范

### 1. 术语标准化

| 概念 | 标准用词 | 说明 |
|------|----------|------|
| 覆盖率 | "覆盖率：能翻译的里，有多少已经翻译好了" | 不使用"Coverage Rate" |
| 可拉取增量 | "可拉取增量：服务器上还有多少翻译，你本地还没用上" | 不使用"Delta Sync" |
| 专属覆盖 | "专属覆盖：整合包自己写的优先翻译" | 不使用"Pack Override" |
| 跨包复用 | "跨包复用：某个 MOD 在多个整合包里都被用到" | 不使用"Cross-pack Reuse" |

### 2. 操作文案

```tsx
// ✅ 人话化文案
<Button>开始扫描</Button>
<Button>去同步</Button>
<Button>生成本地化文件</Button>
<Text>这个操作会覆盖原文件，建议先做备份</Text>

// ❌ 工程化术语
<Button>Execute Scan</Button>
<Button>Sync Delta</Button>
<Button>Build Artifacts</Button>
<Text>This operation will override existing files</Text>
```

### 3. 错误和提示信息

```tsx
// 友好的错误信息
<Alert
  message="扫描遇到问题"
  description="看起来这个文件夹里没找到 MOD 文件，试试选择其他文件夹？"
  type="warning"
  showIcon
/>

// 成功提示
<Alert
  message="扫描完成！"
  description="找到了 156 个 MOD，共 23,847 个需要翻译的词条"
  type="success"
  showIcon
/>

// 操作确认
<Modal
  title="确认覆盖"
  content="这个操作会替换原文件。建议先生成旁路产物并对比差异。"
  okText="我已做好备份，确认覆盖"
  cancelText="取消"
/>
```

## 最佳实践

### 1. 性能优化

```tsx
// 使用 React.memo 优化组件
const ProjectCard = React.memo(({ project }) => {
  return <Card>{/* ... */}</Card>
})

// 列表虚拟化（大数据量）
import { List } from 'antd'

<List
  dataSource={largeDataset}
  pagination={{
    pageSize: 50,
    showSizeChanger: true,
  }}
  renderItem={item => (
    <List.Item>{/* 列表项 */}</List.Item>
  )}
/>
```

### 2. 响应式设计

```tsx
// 使用 Row/Col 系统
<Row gutter={[16, 16]}>
  <Col xs={24} sm={12} md={8} lg={6}>
    <Card>响应式卡片</Card>
  </Col>
</Row>

// 响应式隐藏
<Col xs={0} sm={8}>
  <Text>小屏幕时隐藏</Text>
</Col>
```

### 3. 无障碍支持

```tsx
// 键盘导航
<Button 
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick()
    }
  }}
>
  可键盘操作的按钮
</Button>

// 屏幕阅读器支持
<img alt="项目图标" />
<Button aria-label="删除项目">
  <DeleteOutlined />
</Button>
```

### 4. 错误边界

```tsx
import { ErrorBoundary } from '../components/common'

function MyPage() {
  return (
    <ErrorBoundary>
      <Card>
        {/* 页面内容 */}
      </Card>
    </ErrorBoundary>
  )
}
```

## 注意事项

### 禁止事项

1. ❌ **禁用 Material-UI**: 不得导入任何 `@mui/*` 包
2. ❌ **禁用工程化术语**: 界面文案必须"人话化"
3. ❌ **禁用复杂 Minecraft 元素**: 装饰元素不得影响可读性
4. ❌ **禁用危险操作**: 破坏性操作必须双确认

### 必须事项

1. ✅ **必须使用 Ant Design**: 所有 UI 组件来自 `antd`
2. ✅ **必须应用主题系统**: 使用 `useTheme` Hook 获取主题状态
3. ✅ **必须遵循设计文档**: 严格按照《我的世界工具前端设计.md》规范
4. ✅ **必须考虑无障碍**: 支持键盘导航和屏幕阅读器

### 代码规范

```tsx
// ✅ 推荐的组件结构
import React from 'react'
import { Card, Button } from 'antd'        // 外部依赖
import { ScanOutlined } from '@ant-design/icons'
import { useTheme } from '../contexts/ThemeProvider' // 内部依赖

interface Props {
  title: string
  onScan: () => void
}

export const ProjectCard: React.FC<Props> = ({ title, onScan }) => {
  const { colors } = useTheme()
  
  return (
    <Card 
      title={title}
      extra={
        <Button 
          type="primary" 
          icon={<ScanOutlined />}
          onClick={onScan}
        >
          开始扫描
        </Button>
      }
    >
      {/* 组件内容 */}
    </Card>
  )
}

export default ProjectCard
```

## 相关资源

- [Ant Design 官方文档](https://ant.design/components/overview-cn/)
- [Ant Design Icons](https://ant.design/components/icon-cn/)
- [项目设计规范](../../../我的世界工具前端设计.md)
- [迁移指南](./MIGRATION.md)