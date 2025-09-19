/**
 * Ant Design 统一UI组件导出
 * 
 * 基于 Ant Design 5.x 的组件系统，统一项目UI风格
 * 所有组件都基于 Ant Design 原生组件，避免重复造轮子
 */

// 直接导出 Ant Design 核心组件
export {
  Alert,
  Badge,
  Button,
  Card,
  Progress,
  Tabs,
  Divider as Separator,
  Input,
  Select,
  Table,
} from 'antd'

// 导出 Ant Design 类型
export type {
  AlertProps,
  BadgeProps,
  ButtonProps,
  CardProps,
  ProgressProps,
  TabsProps,
  DividerProps as SeparatorProps,
  InputProps,
  SelectProps,
  TableProps,
} from 'antd'

// 自定义组件（如果需要特殊包装）
// 目前直接使用 Ant Design 原生组件