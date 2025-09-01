// 从 ui-kit 包导入通用组件 - 暂时注释掉以解决依赖问题
// export { 
//   LoadingSpinner, 
//   FileDropZone, 
//   ConfirmDialog, 
//   LanguageSwitcher, 
//   ErrorBoundary 
// } from '@th-suite/ui-kit';
// export type { 
//   LoadingSpinnerProps, 
//   FileDropZoneProps, 
//   ConfirmDialogProps, 
//   LanguageSwitcherProps, 
//   ErrorBoundaryProps,
//   LanguageOption 
// } from '@th-tools/ui-kit';

// 通用组件导出
export { ErrorBoundary } from './ErrorBoundary.tsx';
export { LoadingSkeleton } from './LoadingSkeleton.tsx';
export { StatusIndicator } from './StatusIndicator.tsx';
export { ProgressIndicator } from './ProgressIndicator.tsx';
export { SearchBox } from './SearchBox.tsx';
export { DataTable } from './DataTable.tsx';
export { EmptyState } from './EmptyState.tsx';
export { NotificationSystem } from './NotificationSystem.tsx';
export { FormField } from './FormField.tsx';

// 类型导出
export type { ErrorBoundaryProps } from './ErrorBoundary.tsx';
export type { LoadingSkeletonProps } from './LoadingSkeleton.tsx';
export type { StatusType } from './StatusIndicator.tsx';
export type { ProgressIndicatorProps } from './ProgressIndicator.tsx';
export type { SearchBoxProps, SearchSuggestion } from './SearchBox.tsx';
export type { DataTableProps, TableColumn, SortConfig, FilterConfig } from './DataTable.tsx';
export type { EmptyStateType } from './EmptyState.tsx';
export type { NotificationType, NotificationVariant, Notification, NotificationAction } from './NotificationSystem.tsx';
export type { FieldType, FieldOption, ValidationRule, FormFieldProps } from './FormField.tsx';