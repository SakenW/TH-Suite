/**
 * 撤销重做功能 Hook
 * 提供操作历史记录和撤销/重做功能
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useNotification } from './useNotification';

export interface UndoRedoAction {
  id: string;
  type: string;
  description: string;
  timestamp: number;
  data: any;
  undo: () => void | Promise<void>;
  redo: () => void | Promise<void>;
}

interface UndoRedoState<T> {
  current: T;
  history: T[];
  future: T[];
  canUndo: boolean;
  canRedo: boolean;
}

interface UndoRedoOptions {
  maxHistorySize?: number;
  debounceDelay?: number;
  persistent?: boolean;
  storageKey?: string;
  onUndo?: (action: UndoRedoAction) => void;
  onRedo?: (action: UndoRedoAction) => void;
  onChange?: (state: any) => void;
}

/**
 * 通用的撤销重做 Hook
 */
export function useUndoRedo<T>(
  initialState: T,
  options: UndoRedoOptions = {}
) {
  const {
    maxHistorySize = 50,
    debounceDelay = 500,
    persistent = false,
    storageKey = 'undo-redo-history',
    onUndo,
    onRedo,
    onChange,
  } = options;

  const [state, setState] = useState<UndoRedoState<T>>(() => {
    // 从本地存储恢复（如果启用）
    if (persistent && typeof window !== 'undefined') {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          return {
            current: parsed.current || initialState,
            history: parsed.history || [],
            future: parsed.future || [],
            canUndo: (parsed.history?.length || 0) > 0,
            canRedo: (parsed.future?.length || 0) > 0,
          };
        } catch (error) {
          console.error('Failed to restore undo/redo state:', error);
        }
      }
    }

    return {
      current: initialState,
      history: [],
      future: [],
      canUndo: false,
      canRedo: false,
    };
  });

  const debounceTimer = useRef<NodeJS.Timeout>();

  // 保存到本地存储
  useEffect(() => {
    if (persistent && typeof window !== 'undefined') {
      localStorage.setItem(storageKey, JSON.stringify(state));
    }
  }, [state, persistent, storageKey]);

  /**
   * 添加新状态到历史记录
   */
  const pushState = useCallback((newState: T, immediate = false) => {
    const updateState = () => {
      setState(prev => {
        const newHistory = [...prev.history, prev.current];
        
        // 限制历史记录大小
        if (newHistory.length > maxHistorySize) {
          newHistory.shift();
        }

        const newStateObj = {
          current: newState,
          history: newHistory,
          future: [], // 清空未来历史
          canUndo: true,
          canRedo: false,
        };

        onChange?.(newState);
        return newStateObj;
      });
    };

    if (immediate || debounceDelay === 0) {
      updateState();
    } else {
      // 防抖处理
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
      debounceTimer.current = setTimeout(updateState, debounceDelay);
    }
  }, [maxHistorySize, debounceDelay, onChange]);

  /**
   * 撤销操作
   */
  const undo = useCallback(() => {
    setState(prev => {
      if (prev.history.length === 0) return prev;

      const newHistory = [...prev.history];
      const previousState = newHistory.pop()!;
      const newFuture = [prev.current, ...prev.future];

      const newStateObj = {
        current: previousState,
        history: newHistory,
        future: newFuture,
        canUndo: newHistory.length > 0,
        canRedo: true,
      };

      onChange?.(previousState);
      return newStateObj;
    });
  }, [onChange]);

  /**
   * 重做操作
   */
  const redo = useCallback(() => {
    setState(prev => {
      if (prev.future.length === 0) return prev;

      const newFuture = [...prev.future];
      const nextState = newFuture.shift()!;
      const newHistory = [...prev.history, prev.current];

      const newStateObj = {
        current: nextState,
        history: newHistory,
        future: newFuture,
        canUndo: true,
        canRedo: newFuture.length > 0,
      };

      onChange?.(nextState);
      return newStateObj;
    });
  }, [onChange]);

  /**
   * 重置历史记录
   */
  const reset = useCallback((newInitialState?: T) => {
    setState({
      current: newInitialState || initialState,
      history: [],
      future: [],
      canUndo: false,
      canRedo: false,
    });
    
    if (persistent && typeof window !== 'undefined') {
      localStorage.removeItem(storageKey);
    }
  }, [initialState, persistent, storageKey]);

  /**
   * 清除历史记录但保留当前状态
   */
  const clearHistory = useCallback(() => {
    setState(prev => ({
      ...prev,
      history: [],
      future: [],
      canUndo: false,
      canRedo: false,
    }));
  }, []);

  /**
   * 获取历史记录信息
   */
  const getHistoryInfo = useCallback(() => {
    return {
      historySize: state.history.length,
      futureSize: state.future.length,
      totalSize: state.history.length + state.future.length + 1,
      maxSize: maxHistorySize,
    };
  }, [state, maxHistorySize]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, []);

  return {
    state: state.current,
    setState: pushState,
    undo,
    redo,
    reset,
    clearHistory,
    canUndo: state.canUndo,
    canRedo: state.canRedo,
    history: state.history,
    future: state.future,
    historyInfo: getHistoryInfo(),
  };
}

/**
 * 操作历史管理器（更高级的撤销重做）
 */
export class ActionHistoryManager {
  private history: UndoRedoAction[] = [];
  private currentIndex = -1;
  private maxSize: number;
  private listeners: Set<(action: UndoRedoAction, type: 'undo' | 'redo' | 'add') => void> = new Set();

  constructor(maxSize = 100) {
    this.maxSize = maxSize;
  }

  /**
   * 添加操作到历史记录
   */
  addAction(action: UndoRedoAction) {
    // 如果不在最新位置，删除后面的历史
    if (this.currentIndex < this.history.length - 1) {
      this.history = this.history.slice(0, this.currentIndex + 1);
    }

    // 添加新操作
    this.history.push(action);
    this.currentIndex++;

    // 限制历史大小
    if (this.history.length > this.maxSize) {
      this.history.shift();
      this.currentIndex--;
    }

    this.notifyListeners(action, 'add');
  }

  /**
   * 撤销操作
   */
  async undo(): Promise<boolean> {
    if (!this.canUndo()) return false;

    const action = this.history[this.currentIndex];
    try {
      await action.undo();
      this.currentIndex--;
      this.notifyListeners(action, 'undo');
      return true;
    } catch (error) {
      console.error('Undo failed:', error);
      return false;
    }
  }

  /**
   * 重做操作
   */
  async redo(): Promise<boolean> {
    if (!this.canRedo()) return false;

    this.currentIndex++;
    const action = this.history[this.currentIndex];
    try {
      await action.redo();
      this.notifyListeners(action, 'redo');
      return true;
    } catch (error) {
      console.error('Redo failed:', error);
      this.currentIndex--;
      return false;
    }
  }

  /**
   * 批量撤销
   */
  async undoMany(count: number): Promise<number> {
    let undone = 0;
    for (let i = 0; i < count && this.canUndo(); i++) {
      if (await this.undo()) {
        undone++;
      } else {
        break;
      }
    }
    return undone;
  }

  /**
   * 批量重做
   */
  async redoMany(count: number): Promise<number> {
    let redone = 0;
    for (let i = 0; i < count && this.canRedo(); i++) {
      if (await this.redo()) {
        redone++;
      } else {
        break;
      }
    }
    return redone;
  }

  /**
   * 是否可以撤销
   */
  canUndo(): boolean {
    return this.currentIndex >= 0;
  }

  /**
   * 是否可以重做
   */
  canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  /**
   * 获取历史记录
   */
  getHistory(): UndoRedoAction[] {
    return [...this.history];
  }

  /**
   * 获取当前操作
   */
  getCurrentAction(): UndoRedoAction | null {
    return this.history[this.currentIndex] || null;
  }

  /**
   * 清除历史记录
   */
  clear() {
    this.history = [];
    this.currentIndex = -1;
  }

  /**
   * 添加监听器
   */
  addListener(listener: (action: UndoRedoAction, type: 'undo' | 'redo' | 'add') => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(action: UndoRedoAction, type: 'undo' | 'redo' | 'add') {
    this.listeners.forEach(listener => listener(action, type));
  }
}

/**
 * 使用操作历史管理器的 Hook
 */
export function useActionHistory(maxSize = 100) {
  const notification = useNotification();
  const [manager] = useState(() => new ActionHistoryManager(maxSize));
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [history, setHistory] = useState<UndoRedoAction[]>([]);

  useEffect(() => {
    const unsubscribe = manager.addListener((action, type) => {
      setCanUndo(manager.canUndo());
      setCanRedo(manager.canRedo());
      setHistory(manager.getHistory());

      // 显示通知
      if (type === 'undo') {
        notification.info('撤销', action.description);
      } else if (type === 'redo') {
        notification.info('重做', action.description);
      }
    });

    return unsubscribe;
  }, [manager, notification]);

  const addAction = useCallback((action: Omit<UndoRedoAction, 'id' | 'timestamp'>) => {
    manager.addAction({
      ...action,
      id: `action-${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
    });
    setCanUndo(manager.canUndo());
    setCanRedo(manager.canRedo());
    setHistory(manager.getHistory());
  }, [manager]);

  const undo = useCallback(async () => {
    await manager.undo();
  }, [manager]);

  const redo = useCallback(async () => {
    await manager.redo();
  }, [manager]);

  const clear = useCallback(() => {
    manager.clear();
    setCanUndo(false);
    setCanRedo(false);
    setHistory([]);
  }, [manager]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'z') {
        e.preventDefault();
        undo();
      } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z') {
        e.preventDefault();
        redo();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  return {
    addAction,
    undo,
    redo,
    clear,
    canUndo,
    canRedo,
    history,
    currentAction: manager.getCurrentAction(),
  };
}