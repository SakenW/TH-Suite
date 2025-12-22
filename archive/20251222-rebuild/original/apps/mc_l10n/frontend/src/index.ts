// 主要模块统一导出文件

// 应用主组件
export { default as App } from './App'

// 组件
export * from './components'

// 页面
export * from './pages'

// 服务
// 最优化架构 - 服务层
export * from './services'

// 状态管理
export * from './stores/appStore'

// 钩子
export * from './hooks/useTranslation'

// 类型定义
export * from './types'

// 工具函数
export * from './utils'

// 主题
export * from './theme'

// 国际化
export { default as i18n } from './i18n'
