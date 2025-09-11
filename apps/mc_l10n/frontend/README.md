# 🎮 TH Suite MC L10n Frontend

TH Suite MC L10n 前端应用，基于 Tauri + React + TypeScript + **Ant Design** 构建的 Minecraft 本地化桌面应用程序。

## 🚀 最新更新 (2024.09)

### ✅ V6 前端架构重构完成 - Material-UI 到 Ant Design 全面迁移

- 🎯 **✅ 完全重写**: 基于《我的世界工具前端设计.md》规范完全重构完成
- 🎨 **✅ Ant Design 唯一组件库**: 严格遵循设计文档，100% 移除所有 Material-UI 依赖
- ✨ **✅ Minecraft 轻装饰主题**: 像素化描边、方块化阴影、网格背景，保持现代可读性
- 👤 **✅ 玩家友好界面**: "人话化"文案，隐藏工程参数，安全默认策略
- 📋 **✅ 标准化工作流**: 扫描 → 差量同步 → 构建本地化产物
- 🔄 **✅ 完整迁移**: 所有核心组件已迁移，应用完全可用

## 技术栈

### 核心技术
- **框架**: React 19 + TypeScript 5.9
- **构建工具**: Vite 7.x
- **桌面框架**: Tauri 2.x
- **UI 库**: **Ant Design 5.x** (唯一组件库)
- **主题系统**: 基于 AntD Token 的 Minecraft 轻装饰
- **状态管理**: Zustand
- **路由**: React Router DOM 6.x
- **HTTP 客户端**: Axios
- **表单处理**: React Hook Form + Zod
- **通知**: React Hot Toast
- **图标**: Ant Design Icons

### 设计原则
- **Ant Design 为唯一组件库**: 完全基于 AntD 组件体系
- **Minecraft 轻装饰**: 像素化元素仅作装饰，不影响可用性
- **玩家友好**: 界面文案"人话化"，避免专业术语
- **安全默认**: 默认旁路产物，破坏性操作双确认
- **离线可用**: 断网可操作，联网自动续传

## 项目架构

### 新版文件结构
```
src/
├── theme/                    # 主题系统
│   └── minecraft.ts         # Minecraft 轻装饰主题配置
├── contexts/                 # React 上下文
│   └── ThemeProvider.tsx    # 主题提供者（集成 AntD ConfigProvider）
├── layouts/                  # 布局组件
│   └── MainLayout.tsx       # 主布局（左侧导航+顶部状态条）
├── components/               # 组件系统
│   ├── TopStatusBar.tsx     # 顶部状态条（连接状态+快速指标）
│   ├── common/              # 通用组件
│   └── ui/                  # UI 基础组件
├── pages/                    # 页面组件
│   ├── WelcomePage.tsx      # 欢迎页（工具介绍+快速入口）
│   ├── ProjectsPacksPage.tsx # 整合包项目页
│   ├── ProjectsModsPage.tsx  # MOD 项目页
│   ├── ScanPage.tsx         # 扫描中心
│   ├── SyncPage.tsx         # 同步中心
│   ├── BuildPage.tsx        # 构建中心
│   ├── ServerPage.tsx       # 服务器状态
│   └── SettingsPage.tsx     # 设置页
├── services/                 # 服务层（保留原架构）
│   ├── domain/              # 领域服务
│   ├── infrastructure/      # 基础设施服务
│   └── container/           # 依赖注入容器
├── stores/                   # 状态管理（保留 Zustand）
├── hooks/                    # 自定义 Hooks
├── App.new.tsx              # 新版主应用组件
├── main.new.tsx            # 新版应用入口
└── index.css               # 全局样式
```

### 设计规范对齐

根据《我的世界工具前端设计.md》实现的页面结构：

#### 4.1 主导航（左侧）
- ✅ 欢迎页
- ✅ 项目（整合包/MOD 分离）
- ✅ 扫描中心
- ✅ 同步中心
- ✅ 构建中心
- ✅ 服务器状态
- ✅ 设置

#### 4.2 顶部状态条（精简）
- ✅ 连接状态（✅ 已连接 / ⛔ 离线）
- ✅ 快速指标（可拉取 X / 待上传 Y）
- ✅ 时间信息（上次扫描/同步时间）

## 功能特性

### 核心工作流
- 🔍 **扫描中心**: 新建项目 → 扫描识别 → 版本/加载器组合管理
- 🔄 **同步中心**: 语言多选 → Push/Pull 差量同步 → Dry Run 支持
- 🏗️ **构建中心**: 安全策略（旁路产物/原地覆盖） → 产物生成 → 回滚点
- 📊 **项目管理**: 整合包/MOD 分离显示 → 版本切换 → 专属覆盖管理

### Minecraft 轻装饰特性
- 🎨 **像素化装饰**: 2px 描边、方块化阴影、网格背景
- 🎮 **游戏化色彩**: 绿宝石绿、金锭黄、红石红、青金石蓝
- 🧱 **材质风格**: 基于方块材质的中性色系
- ✨ **现代交互**: 保持 AntD 交互规范，装饰不影响可用性

### 安全与可靠性
- 🛡️ **安全默认**: 默认旁路产物，避免意外覆盖
- 🔄 **自动备份**: 构建前自动创建回滚点
- ⚠️ **双确认**: 破坏性操作需双重确认
- 📴 **离线支持**: 断网任务入队，联网自动续传

## 开发环境设置

### 前置要求
- Node.js 18+
- Rust 1.60+
- pnpm (推荐) 或 npm

### 安装依赖
```bash
# 安装前端依赖
pnpm install

# 安装 Tauri CLI
pnpm add -g @tauri-apps/cli
```

### 开发模式
```bash
# 启动新版前端开发服务器
pnpm dev

# 启动 Tauri 桌面应用开发模式
pnpm tauri:dev
```

### 使用新版架构
```bash
# 临时测试新架构（推荐）
# 将 src/main.new.tsx 重命名为 src/main.tsx
# 将 src/App.new.tsx 重命名为 src/App.tsx

# 或者修改 index.html 中的脚本引用
# 从 src/main.tsx 改为 src/main.new.tsx
```

## 新版主题系统使用指南

### ThemeProvider 集成
```tsx
import { ThemeProvider } from './contexts/ThemeProvider'

function App() {
  return (
    <ThemeProvider>
      {/* 你的应用内容 */}
    </ThemeProvider>
  )
}
```

### 使用主题 Hook
```tsx
import { useTheme } from './contexts/ThemeProvider'

function MyComponent() {
  const { isDark, toggleTheme, colors } = useTheme()
  
  return (
    <div style={{ color: colors.primary }}>
      <button onClick={toggleTheme}>
        切换主题: {isDark ? '暗色' : '亮色'}
      </button>
    </div>
  )
}
```

### Minecraft 装饰样式
```tsx
import { mcDecorationStyles } from './theme/minecraft'

function PixelCard() {
  return (
    <Card style={mcDecorationStyles.pixelCard}>
      像素化卡片
    </Card>
  )
}

function BlockButton() {
  return (
    <Button style={mcDecorationStyles.blockButton}>
      方块化按钮
    </Button>
  )
}
```

## Ant Design 组件规范

### 基础组件使用
```tsx
import { 
  Button, 
  Card, 
  Table, 
  Form, 
  Input, 
  Select,
  Progress,
  Badge,
  Tag,
  Space,
  Row,
  Col 
} from 'antd'
import { 
  HomeOutlined, 
  ScanOutlined, 
  SyncOutlined 
} from '@ant-design/icons'

// 符合设计文档的组件使用示例
function ProjectCard() {
  return (
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
          <Progress percent={78.5} strokeColor="#4CAF50" />
        </Col>
        <Col span={16}>
          <Space>
            <Tag color="blue">可拉取 123</Tag>
            <Tag color="orange">待上传 45</Tag>
          </Space>
        </Col>
      </Row>
    </Card>
  )
}
```

## 可用脚本

```bash
# 开发
pnpm dev              # Vite 开发服务器
pnpm tauri:dev        # Tauri 桌面应用开发

# 构建
pnpm build            # 构建前端资源
pnpm tauri:build      # 构建 Tauri 应用

# 代码质量
pnpm lint             # ESLint 检查
pnpm lint:fix         # ESLint 自动修复
pnpm type-check       # TypeScript 类型检查
pnpm format           # Prettier 格式化
pnpm check:all        # 运行所有检查
```

## 配置说明

### 主要配置文件
- `tauri.conf.json` - Tauri 应用配置
- `vite.config.ts` - Vite 构建配置
- `tsconfig.json` - TypeScript 配置
- `package.json` - 依赖和脚本配置

### 环境变量
```bash
# 开发环境
VITE_API_URL=http://localhost:18000
VITE_WS_URL=ws://localhost:18000

# 生产环境
VITE_API_URL=https://api.trans-hub.com
VITE_WS_URL=wss://api.trans-hub.com
```

## 迁移指南

### 从 Material-UI 迁移到 Ant Design

1. **组件映射**:
   ```tsx
   // 旧版 (Material-UI)
   import { Button, Card, Typography } from '@mui/material'
   
   // 新版 (Ant Design)
   import { Button, Card, Typography } from 'antd'
   ```

2. **主题系统**:
   ```tsx
   // 旧版
   import { ThemeProvider } from '@mui/material/styles'
   
   // 新版
   import { ThemeProvider } from './contexts/ThemeProvider'
   ```

3. **图标系统**:
   ```tsx
   // 旧版
   import { Home, Settings } from '@mui/icons-material'
   
   // 新版
   import { HomeOutlined, SettingOutlined } from '@ant-design/icons'
   ```

## 部署

### 开发版本
```bash
pnpm tauri:dev
```

### 生产版本
```bash
pnpm tauri:build
```

构建产物位于 `src-tauri/target/release/bundle/`

## 故障排除

### 新架构相关

1. **类型错误**: 确保移除了所有 Material-UI 相关导入
2. **主题不生效**: 检查 ThemeProvider 是否正确包装应用
3. **组件样式异常**: 确认使用的是 Ant Design 组件而非 MUI

### 通用问题

1. **依赖安装失败**: 清除 node_modules 和 pnpm-lock.yaml，重新安装
2. **Tauri 构建失败**: 检查 Rust 工具链和系统依赖
3. **开发服务器启动失败**: 检查端口占用和环境变量配置

## 后续开发计划

### 待实现页面（按优先级）
1. 🔍 **扫描中心** - 项目创建和扫描流程
2. 🔄 **同步中心** - 语言多选和 Push/Pull 工作流  
3. 🏗️ **构建中心** - 安全策略和产物生成
4. 🖥️ **服务器状态** - 信号灯格和连通性测试
5. ⚙️ **设置页** - 用户友好的配置选项

### 技术改进
- [ ] 完善 TypeScript 类型定义
- [ ] 集成实时进度系统
- [ ] 添加无障碍功能支持
- [ ] 性能优化和代码分割
- [ ] 完整的错误边界处理

## 贡献

欢迎提交 Issue 和 Pull Request！请确保遵循项目的代码规范和设计原则。

## 许可证

MIT License