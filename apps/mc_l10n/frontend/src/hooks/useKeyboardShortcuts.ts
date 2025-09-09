import { useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@stores/appStore'

export interface ShortcutDefinition {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  description: string
  action: () => void
  global?: boolean
  preventDefault?: boolean
}

interface ShortcutOptions {
  enabled?: boolean
  preventDefault?: boolean
}

/**
 * 全局快捷键管理 Hook
 */
export function useKeyboardShortcuts(
  shortcuts: ShortcutDefinition[],
  options: ShortcutOptions = {},
) {
  const { enabled = true, preventDefault = true } = options
  const shortcutsRef = useRef(shortcuts)

  useEffect(() => {
    shortcutsRef.current = shortcuts
  }, [shortcuts])

  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      const activeElement = document.activeElement
      const isInputField =
        activeElement?.tagName === 'INPUT' ||
        activeElement?.tagName === 'TEXTAREA' ||
        (activeElement as HTMLElement)?.contentEditable === 'true'

      for (const shortcut of shortcutsRef.current) {
        // 如果不是全局快捷键且焦点在输入框中，跳过
        if (!shortcut.global && isInputField) continue

        // 确保 key 存在才进行比较
        if (!event.key || !shortcut.key) continue

        const keyMatch =
          event.key.toLowerCase() === shortcut.key.toLowerCase() ||
          (event.code && event.code.toLowerCase() === shortcut.key.toLowerCase())

        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : true
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
        const altMatch = shortcut.alt ? event.altKey : !event.altKey
        const metaMatch = shortcut.meta ? event.metaKey : true

        if (keyMatch && ctrlMatch && shiftMatch && altMatch && metaMatch) {
          if (shortcut.preventDefault ?? preventDefault) {
            event.preventDefault()
            event.stopPropagation()
          }
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled, preventDefault])
}

/**
 * 应用级全局快捷键
 */
export function useGlobalShortcuts() {
  const navigate = useNavigate()
  const { setSidebarOpen, sidebarOpen } = useAppStore()

  const shortcuts: ShortcutDefinition[] = [
    // 导航快捷键
    {
      key: 'h',
      ctrl: true,
      description: '返回首页',
      action: () => navigate('/'),
      global: true,
    },
    {
      key: 's',
      ctrl: true,
      description: '扫描页面',
      action: () => navigate('/scan'),
      global: true,
    },
    {
      key: 'p',
      ctrl: true,
      description: '项目管理',
      action: () => navigate('/project'),
      global: true,
    },
    {
      key: 'e',
      ctrl: true,
      description: '导出管理',
      action: () => navigate('/export'),
      global: true,
    },
    {
      key: 't',
      ctrl: true,
      description: '传输管理',
      action: () => navigate('/transfer'),
      global: true,
    },
    {
      key: 'b',
      ctrl: true,
      description: '构建管理',
      action: () => navigate('/build'),
      global: true,
    },
    {
      key: ',',
      ctrl: true,
      description: '设置',
      action: () => navigate('/settings'),
      global: true,
    },

    // 界面控制
    {
      key: '\\',
      ctrl: true,
      description: '切换侧边栏',
      action: () => setSidebarOpen(!sidebarOpen),
      global: true,
    },
    {
      key: 'Escape',
      description: '关闭对话框/返回',
      action: () => {
        // 检查是否有打开的对话框
        const dialog = document.querySelector('[role="dialog"]')
        if (dialog) {
          const closeButton = dialog.querySelector('[aria-label="close"]') as HTMLElement
          closeButton?.click()
        } else {
          window.history.back()
        }
      },
      global: false,
    },

    // 功能快捷键
    {
      key: 'n',
      ctrl: true,
      description: '新建项目',
      action: () => {
        navigate('/project')
        // 触发新建项目对话框
        setTimeout(() => {
          const newButton = document.querySelector('[data-action="new-project"]') as HTMLElement
          newButton?.click()
        }, 100)
      },
      global: true,
    },
    {
      key: 'o',
      ctrl: true,
      description: '打开文件',
      action: () => {
        const fileInput = document.createElement('input')
        fileInput.type = 'file'
        fileInput.accept = '.jar,.zip'
        fileInput.onchange = e => {
          const file = (e.target as HTMLInputElement).files?.[0]
          if (file) {
            console.log('Selected file:', file.name)
            // 处理文件
          }
        }
        fileInput.click()
      },
      global: true,
    },
    {
      key: 'r',
      ctrl: true,
      description: '刷新',
      action: () => window.location.reload(),
      global: true,
      preventDefault: true,
    },
    {
      key: 'f',
      ctrl: true,
      description: '搜索',
      action: () => {
        const searchInput = document.querySelector('[data-role="search"]') as HTMLInputElement
        searchInput?.focus()
      },
      global: true,
    },

    // 开发者工具
    {
      key: 'F12',
      description: '开发者工具',
      action: () => {
        if (window.__TAURI__) {
          // Tauri 环境下打开开发者工具
          console.log('Opening DevTools...')
        }
      },
      global: true,
      preventDefault: false,
    },
  ]

  useKeyboardShortcuts(shortcuts)

  return shortcuts
}

/**
 * 页面级快捷键 Hook
 */
export function usePageShortcuts(pageShortcuts: ShortcutDefinition[]) {
  const allShortcuts = [...pageShortcuts]
  useKeyboardShortcuts(allShortcuts, { enabled: true })
  return allShortcuts
}

/**
 * 对话框快捷键 Hook
 */
export function useDialogShortcuts(isOpen: boolean, onClose: () => void, onConfirm?: () => void) {
  const shortcuts: ShortcutDefinition[] = [
    {
      key: 'Escape',
      description: '关闭对话框',
      action: onClose,
      global: false,
    },
  ]

  if (onConfirm) {
    shortcuts.push({
      key: 'Enter',
      ctrl: true,
      description: '确认',
      action: onConfirm,
      global: false,
    })
  }

  useKeyboardShortcuts(shortcuts, { enabled: isOpen })
}

/**
 * 表格快捷键 Hook
 */
export function useTableShortcuts(
  selectedRows: string[],
  onSelectAll: () => void,
  onDeselectAll: () => void,
  onDelete?: () => void,
  onEdit?: () => void,
) {
  const shortcuts: ShortcutDefinition[] = [
    {
      key: 'a',
      ctrl: true,
      description: '全选',
      action: onSelectAll,
      global: false,
    },
    {
      key: 'd',
      ctrl: true,
      description: '取消选择',
      action: onDeselectAll,
      global: false,
    },
  ]

  if (onDelete && selectedRows.length > 0) {
    shortcuts.push({
      key: 'Delete',
      description: '删除选中项',
      action: onDelete,
      global: false,
    })
  }

  if (onEdit && selectedRows.length === 1) {
    shortcuts.push({
      key: 'Enter',
      description: '编辑选中项',
      action: onEdit,
      global: false,
    })
  }

  useKeyboardShortcuts(shortcuts, { enabled: true })
}

/**
 * 组合键显示格式化
 */
export function formatShortcut(shortcut: ShortcutDefinition): string {
  const keys: string[] = []

  if (shortcut.ctrl) keys.push('Ctrl')
  if (shortcut.shift) keys.push('Shift')
  if (shortcut.alt) keys.push('Alt')
  if (shortcut.meta) keys.push('Meta')

  keys.push(shortcut.key.toUpperCase())

  return keys.join('+')
}

/**
 * 获取操作系统相关的修饰键
 */
export function getModifierKey(): string {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  return isMac ? '⌘' : 'Ctrl'
}

/**
 * 快捷键帮助文本生成
 */
export function generateShortcutHelp(shortcuts: ShortcutDefinition[]): string {
  return shortcuts.map(s => `${formatShortcut(s)}: ${s.description}`).join('\n')
}
