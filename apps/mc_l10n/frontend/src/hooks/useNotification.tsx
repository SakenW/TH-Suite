import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { NotificationOptions, NotificationContainer } from '../components/minecraft/MinecraftNotification';

interface NotificationContextType {
  notify: (options: Omit<NotificationOptions, 'id'>) => string;
  success: (title: string, message?: string) => string;
  error: (title: string, message?: string) => string;
  warning: (title: string, message?: string) => string;
  info: (title: string, message?: string) => string;
  achievement: (title: string, message?: string, options?: Partial<NotificationOptions>) => string;
  system: (title: string, message?: string) => string;
  remove: (id: string) => void;
  clear: () => void;
  updateProgress: (id: string, progress: number) => void;
  settings: NotificationSettings;
  updateSettings: (settings: Partial<NotificationSettings>) => void;
}

interface NotificationSettings {
  position: NotificationOptions['position'];
  soundEnabled: boolean;
  achievementEffects: boolean;
  maxNotifications: number;
  defaultDuration: number;
}

const defaultSettings: NotificationSettings = {
  position: 'top-right',
  soundEnabled: true,
  achievementEffects: true,
  maxNotifications: 5,
  defaultDuration: 5000,
};

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationOptions[]>([]);
  const [settings, setSettings] = useState<NotificationSettings>(defaultSettings);
  const notificationCounter = useRef(0);
  const audioRefs = useRef<{ [key: string]: HTMLAudioElement }>({});

  // 预加载音效 - Temporarily disabled until sound files are available
  React.useEffect(() => {
    // Sound preloading disabled to prevent console errors
    /*
    const sounds = {
      success: '/sounds/success.ogg',
      error: '/sounds/error.ogg',
      warning: '/sounds/warning.ogg',
      info: '/sounds/info.ogg',
      achievement: '/sounds/achievement.ogg',
      system: '/sounds/system.ogg',
    };

    // 预加载所有音效文件
    Object.entries(sounds).forEach(([type, path]) => {
      const audio = new Audio(path);
      audio.preload = 'auto';
      audio.volume = 0.5;
      audioRefs.current[type] = audio;
    });
    */
  }, []);

  const playSound = useCallback((type: string) => {
    // Temporarily disabled until sound files are available
    return;
    
    /*
    if (!settings.soundEnabled) return;
    
    const audio = audioRefs.current[type];
    if (audio) {
      // 克隆音频以支持重叠播放
      const audioClone = audio.cloneNode() as HTMLAudioElement;
      audioClone.play().catch(err => {
        console.warn('Failed to play notification sound:', err);
      });
    }
    */
  }, [settings.soundEnabled]);

  const notify = useCallback((options: Omit<NotificationOptions, 'id'>): string => {
    const id = `notification-${++notificationCounter.current}`;
    const notification: NotificationOptions = {
      ...options,
      id,
      duration: options.duration || settings.defaultDuration,
      position: options.position || settings.position,
      minecraft: {
        ...options.minecraft,
        particle: options.type === 'achievement' ? settings.achievementEffects : false,
        glow: options.type === 'achievement' ? settings.achievementEffects : false,
      },
    };

    setNotifications(prev => {
      // 限制最大通知数量
      const newNotifications = [...prev, notification];
      if (newNotifications.length > settings.maxNotifications) {
        return newNotifications.slice(-settings.maxNotifications);
      }
      return newNotifications;
    });

    // 播放音效
    if (options.type) {
      playSound(options.type);
    }

    return id;
  }, [settings, playSound]);

  const success = useCallback((title: string, message?: string): string => {
    return notify({ title, message, type: 'success' });
  }, [notify]);

  const error = useCallback((title: string, message?: string): string => {
    return notify({ title, message, type: 'error', persistent: true });
  }, [notify]);

  const warning = useCallback((title: string, message?: string): string => {
    return notify({ title, message, type: 'warning' });
  }, [notify]);

  const info = useCallback((title: string, message?: string): string => {
    return notify({ title, message, type: 'info' });
  }, [notify]);

  const achievement = useCallback((title: string, message?: string, options?: Partial<NotificationOptions>): string => {
    return notify({ 
      title: `🏆 ${title}`, 
      message, 
      type: 'achievement',
      duration: 7000,
      ...options,
      minecraft: {
        block: 'gold',
        particle: true,
        glow: true,
        ...options?.minecraft,
      }
    });
  }, [notify]);

  const system = useCallback((title: string, message?: string): string => {
    return notify({ title, message, type: 'system' });
  }, [notify]);

  const remove = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clear = useCallback(() => {
    setNotifications([]);
  }, []);

  const updateProgress = useCallback((id: string, progress: number) => {
    setNotifications(prev => prev.map(n => 
      n.id === id ? { ...n, progress } : n
    ));
  }, []);

  const updateSettings = useCallback((newSettings: Partial<NotificationSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
    
    // 保存设置到本地存储
    const mergedSettings = { ...settings, ...newSettings };
    localStorage.setItem('notification-settings', JSON.stringify(mergedSettings));
  }, [settings]);

  // 从本地存储加载设置
  React.useEffect(() => {
    const savedSettings = localStorage.getItem('notification-settings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings(parsed);
      } catch (err) {
        console.error('Failed to load notification settings:', err);
      }
    }
  }, []);

  const value: NotificationContextType = {
    notify,
    success,
    error,
    warning,
    info,
    achievement,
    system,
    remove,
    clear,
    updateProgress,
    settings,
    updateSettings,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationContainer
        notifications={notifications}
        position={settings.position}
        onRemove={remove}
      />
    </NotificationContext.Provider>
  );
};

// 便捷的全局通知函数（可选）
let globalNotify: NotificationContextType | null = null;

export const setGlobalNotify = (notify: NotificationContextType) => {
  globalNotify = notify;
};

export const notify = {
  success: (title: string, message?: string) => {
    if (globalNotify) return globalNotify.success(title, message);
    console.warn('Notification system not initialized');
    return '';
  },
  error: (title: string, message?: string) => {
    if (globalNotify) return globalNotify.error(title, message);
    console.warn('Notification system not initialized');
    return '';
  },
  warning: (title: string, message?: string) => {
    if (globalNotify) return globalNotify.warning(title, message);
    console.warn('Notification system not initialized');
    return '';
  },
  info: (title: string, message?: string) => {
    if (globalNotify) return globalNotify.info(title, message);
    console.warn('Notification system not initialized');
    return '';
  },
  achievement: (title: string, message?: string, options?: Partial<NotificationOptions>) => {
    if (globalNotify) return globalNotify.achievement(title, message, options);
    console.warn('Notification system not initialized');
    return '';
  },
  system: (title: string, message?: string) => {
    if (globalNotify) return globalNotify.system(title, message);
    console.warn('Notification system not initialized');
    return '';
  },
};