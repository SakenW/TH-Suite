# 前端架构迁移指南

## 概述

TH Suite MC L10n 前端架构已完全重构，基于《我的世界工具前端设计.md》规范，从 **Material-UI** 完全迁移到 **Ant Design**，并实现 Minecraft 轻装饰主题系统。

## 迁移背景

### 为什么要迁移？

1. **设计文档要求**: 《我的世界工具前端设计.md》明确规定 "Ant Design 为唯一组件库"
2. **用户体验优化**: 实现"玩家友好"界面，"人话化"文案，隐藏工程参数
3. **视觉一致性**: 统一的 Minecraft 轻装饰主题，保持现代可读性
4. **标准化工作流**: 扫描 → 差量同步 → 构建本地化产物的标准化流程

### 技术决策

- ✅ **完全重写** 而非渐进式迁移，确保架构纯净
- ✅ **保留服务层** 架构，仅更换 UI 层
- ✅ **Ant Design 5.x** 作为唯一 UI 组件库
- ✅ **轻装饰设计** 像素化元素仅作装饰，不影响可用性

## 架构对比

### 旧架构 (Material-UI)
```
src/
├── components/
│   ├── minecraft/          # 重度 Minecraft 游戏化组件
│   ├── common/
│   └── Layout/
├── pages/                  # 各种 *Minecraft.tsx 页面
├── theme/
│   └── minecraftTheme.ts   # 基于 MUI 的主题
└── App.tsx                 # MUI ThemeProvider
```

### 新架构 (Ant Design)
```
src/
├── theme/
│   └── minecraft.ts        # 基于 AntD Token 的轻装饰主题
├── contexts/
│   └── ThemeProvider.tsx   # 集成 AntD ConfigProvider
├── layouts/
│   └── MainLayout.tsx      # 左侧导航 + 顶部状态条
├── components/
│   └── TopStatusBar.tsx    # 精简的状态条
├── pages/                  # 符合设计文档的页面结构
│   ├── WelcomePage.tsx     # 工具介绍 + 快速入口
│   ├── ProjectsPacksPage.tsx
│   └── ...
├── App.new.tsx             # 新版主应用
└── main.new.tsx           # 新版入口
```

## 主要变更

### 1. UI 组件库更换

#### 组件映射表

| 功能 | 旧版 (Material-UI) | 新版 (Ant Design) |
|------|-------------------|-------------------|
| 按钮 | `<Button>` from @mui/material | `<Button>` from antd |
| 卡片 | `<Card>` from @mui/material | `<Card>` from antd |
| 表格 | `<Table>` from @mui/material | `<Table>` from antd |
| 表单 | `<TextField>` from @mui/material | `<Input>`, `<Form>` from antd |
| 布局 | `<Box>`, `<Container>` | `<Row>`, `<Col>`, `<Space>` |
| 导航 | `<List>`, `<ListItem>` | `<Menu>` |
| 图标 | `@mui/icons-material` | `@ant-design/icons` |

#### 导入语句更换

```tsx
// 旧版
import { Button, Card, Typography, Box } from '@mui/material'
import { Home, Settings, Scan } from '@mui/icons-material'

// 新版
import { Button, Card, Typography, Space } from 'antd'
import { HomeOutlined, SettingOutlined, ScanOutlined } from '@ant-design/icons'
```

### 2. 主题系统重构

#### 旧版主题 (Material-UI)
```tsx
import { createTheme, ThemeProvider } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    primary: { main: '#4CAF50' },
    // 复杂的 MUI 主题配置
  }
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  )
}
```

#### 新版主题 (Ant Design)
```tsx
import { ConfigProvider } from 'antd'
import { getMinecraftTheme } from './theme/minecraft'

function App() {
  const isDark = useTheme()
  
  return (
    <ConfigProvider theme={getMinecraftTheme(isDark)}>
      {children}
    </ConfigProvider>
  )
}
```

### 3. 页面结构标准化

#### 设计文档要求的页面结构

根据《我的世界工具前端设计.md》，所有页面必须符合以下结构：

1. **欢迎页**: 工具介绍 + 快速入口 + 最近任务 + 连接卡片
2. **项目页**: 整合包/MOD 分离，版本切换，不显示版本号
3. **扫描中心**: 新建项目 + 扫描流程 + 版本/加载器组合
4. **同步中心**: 语言多选 + Push/Pull 双卡布局 + Dry Run
5. **构建中心**: 安全策略（旁路产物/原地覆盖）+ 双确认
6. **服务器状态**: 信号灯格 + 连通性测试
7. **设置**: 玩家可理解的配置项

### 4. 术语和文案标准化

#### 文案对比

| 概念 | 旧版文案 | 新版文案 (人话化) |
|------|----------|------------------|
| 覆盖率 | Coverage Rate | 覆盖率：能翻译的里，有多少已经翻译好了 |
| 增量更新 | Delta Sync | 可拉取增量：服务器上还有多少翻译，你本地还没用上 |
| 项目状态 | Project Status | - |
| 包覆盖 | Pack Override | 专属覆盖：整合包自己写的优先翻译 |
| 跨包复用 | Cross-pack Reuse | 跨包复用：某个 MOD 在多个整合包里都被用到 |

#### 状态指示器

```tsx
// 旧版：工程化术语
<Chip label="SCANNING" color="primary" />
<Chip label="ERROR" color="error" />

// 新版：人话化描述
<Tag color="processing" icon={<SyncOutlined spin />}>扫描中</Tag>
<Tag color="error">需要注意</Tag>
```

## 迁移步骤

### 第一阶段：切换到新架构 ✅

1. **安装 Ant Design 依赖** ✅:
   ```bash
   pnpm add antd @ant-design/icons @ant-design/colors dayjs
   pnpm remove @mui/material @mui/icons-material @emotion/react @emotion/styled
   ```

2. **使用新版文件** ✅:
   - 已更新 `src/main.tsx` 使用简化版应用入口
   - 已创建 `src/App.simple.tsx` 基于 Ant Design
   - 已创建 `src/pages/WelcomeMinimal.tsx` 生产就绪欢迎页

3. **验证基础功能** ✅:
   ```bash
   pnpm dev  # 应用已能正常启动，运行在 localhost:18001
   ```

### 第二阶段：清理旧代码 ✅

1. **移除 Material-UI 相关文件** ✅:
   - 已将旧文件移动到 `backup_*` 目录
   - 已完全重写核心组件使用 Ant Design
   - 已更新 Vite 配置移除 Emotion JSX

2. **更新导入语句** ✅:
   - 已将所有组件更新为 Ant Design 导入
   - 已验证无遗留 Material-UI 引用
   - 已更新图标为 @ant-design/icons

3. **修复类型错误** ✅:
   - TypeScript 编译通过
   - 已解决所有组件类型问题
   - 应用运行无错误

### 第三阶段：功能实现 (进行中)

1. **完善核心页面** (按优先级):
   - [ ] 扫描中心 - 项目创建和扫描流程
   - [ ] 同步中心 - 语言多选和 Push/Pull 工作流
   - [ ] 构建中心 - 安全策略和产物生成
   - [ ] 服务器状态 - 信号灯格和连通性测试
   - [ ] 设置页 - 用户友好的配置选项

2. **集成实时进度系统**:
   - [ ] 轮询机制优化
   - [ ] 进度动画和用户反馈
   - [ ] 错误处理和重试机制

3. **无障碍和性能优化**:
   - [ ] 键盘导航支持
   - [ ] 屏幕阅读器兼容
   - [ ] 代码分割和懒加载

## 开发指南

### 新增组件规范

1. **严格使用 Ant Design**:
   ```tsx
   // ✅ 正确
   import { Button, Card, Table } from 'antd'
   import { ScanOutlined } from '@ant-design/icons'
   
   // ❌ 错误 - 禁止使用 Material-UI
   import { Button } from '@mui/material'
   ```

2. **应用 Minecraft 轻装饰**:
   ```tsx
   import { mcDecorationStyles } from '../theme/minecraft'
   
   function MyCard() {
     return (
       <Card style={mcDecorationStyles.pixelCard}>
         {/* 像素化卡片 */}
       </Card>
     )
   }
   ```

3. **遵循文案规范**:
   ```tsx
   // ✅ 人话化文案
   <Button>开始扫描</Button>
   <Text>这个操作会覆盖原文件，建议先做备份</Text>
   
   // ❌ 工程化术语
   <Button>Execute Scan</Button>
   <Text>This operation will override existing files</Text>
   ```

### 主题系统使用

1. **获取主题状态**:
   ```tsx
   import { useTheme } from '../contexts/ThemeProvider'
   
   function MyComponent() {
     const { isDark, toggleTheme, colors } = useTheme()
     
     return (
       <div style={{ color: colors.primary }}>
         <Button onClick={toggleTheme}>
           切换主题: {isDark ? '暗色' : '亮色'}
         </Button>
       </div>
     )
   }
   ```

2. **自定义装饰样式**:
   ```tsx
   import { mcDecorationStyles } from '../theme/minecraft'
   
   const customStyle = {
     ...mcDecorationStyles.blockButton,
     background: 'linear-gradient(145deg, #4CAF50, #8BC34A)',
   }
   ```

### 页面开发模板

```tsx
import React from 'react'
import { Card, Typography, Button, Space, Row, Col } from 'antd'
import { ScanOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeProvider'

const { Title, Text } = Typography

export const MyPage: React.FC = () => {
  const navigate = useNavigate()
  const { colors } = useTheme()

  return (
    <div style={{ padding: 24 }}>
      {/* 页头 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>页面标题</Title>
          <Text type="secondary">人话化的页面描述</Text>
        </Col>
        <Col>
          <Button type="primary" icon={<ScanOutlined />}>
            主要操作
          </Button>
        </Col>
      </Row>

      {/* 内容区域 */}
      <Card>
        {/* 页面内容 */}
      </Card>
    </div>
  )
}

export default MyPage
```

## 故障排除

### 常见问题

1. **类型错误: Cannot find module '@mui/material'**
   - **原因**: 文件中仍有 Material-UI 导入
   - **解决**: 替换为对应的 Ant Design 导入

2. **主题不生效**
   - **原因**: 未正确包装 ThemeProvider
   - **解决**: 确保根组件包装在 `<ThemeProvider>` 中

3. **组件样式异常**
   - **原因**: 混用了 Material-UI 和 Ant Design 组件
   - **解决**: 确保只使用 Ant Design 组件

### 调试工具

1. **开发者工具**:
   ```tsx
   // 主题调试
   console.log('Current theme:', useTheme())
   
   // 组件调试
   <div data-debug="component-name">...</div>
   ```

2. **类型检查**:
   ```bash
   pnpm type-check  # 检查类型错误
   pnpm lint        # 检查代码规范
   ```

## 验收标准

### 功能验收
- [x] 所有页面正常加载，无控制台错误
- [x] 主题切换正常工作（亮色/暗色模式）
- [x] 导航系统完整可用
- [x] 所有按钮和交互元素可正常操作

### 设计验收
- [x] 界面基于 Ant Design 5.x 组件
- [x] 使用"人话化"文案，避免专业术语
- [x] 应用 Minecraft 轻装饰主题
- [x] 实现左侧导航 + 顶部状态条布局

### 技术验收
- [x] 完全移除 Material-UI 依赖
- [x] 只使用 Ant Design 组件
- [x] TypeScript 无类型错误
- [x] 应用运行无错误

## 后续计划

### 短期目标 (1-2 周)
- [ ] 完成核心页面实现
- [ ] 集成实时进度系统
- [ ] 完善错误处理机制

### 中期目标 (1 个月)
- [ ] 无障碍功能支持
- [ ] 性能优化和代码分割
- [ ] 完整的测试覆盖

### 长期目标 (2-3 个月)
- [ ] 用户体验优化
- [ ] 国际化支持完善
- [ ] 移动端适配考虑

## 相关文档

- [前端 README](./README.md) - 完整的前端文档
- [项目 CLAUDE.md](../../../CLAUDE.md) - 项目开发指导
- [我的世界工具前端设计.md](../../../我的世界工具前端设计.md) - 设计规范文档

---

**注意**: 这是一次完全重写，不是渐进式迁移。新架构已经可以直接使用，建议尽快切换以获得最佳开发体验。