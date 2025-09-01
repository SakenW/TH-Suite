/**
 * Minecraft 风格主布局组件
 * 提供整体的页面框架和导航
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  MCPanel, 
  MCButton, 
  MCInventorySlot,
  MCTooltip,
  MCStatusBars,
  minecraftColors,
  typography,
  textures
} from '../components/minecraft';
import { languageManager } from '../i18n/config';

// 导航项类型
interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
  badge?: number;
  tooltip?: string;
}

// 快捷栏项目
interface HotbarItem {
  id: string;
  icon: string;
  label: string;
  action?: () => void;
  active?: boolean;
}

const MCLayout: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [selectedHotbarSlot, setSelectedHotbarSlot] = useState(0);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [serverStatus, setServerStatus] = useState<'online' | 'offline'>('offline');
  
  // 导航项目
  const navItems: NavItem[] = [
    {
      id: 'home',
      label: t('navigation.home'),
      icon: '🏠',
      path: '/',
      tooltip: 'Return to spawn'
    },
    {
      id: 'scan',
      label: t('mcStudio.welcome.quickActions.scan.title'),
      icon: '🔍',
      path: '/scan',
      tooltip: 'Scan for resources'
    },
    {
      id: 'patches',
      label: t('mcStudio.features.modLocalization.title'),
      icon: '📦',
      path: '/patches',
      badge: 3,
      tooltip: 'Manage patches'
    },
    {
      id: 'quality',
      label: t('common.labels.quality', 'Quality'),
      icon: '✨',
      path: '/quality',
      tooltip: 'Quality checks'
    },
    {
      id: 'sync',
      label: t('mcStudio.workflow.synchronization.status.completed'),
      icon: '🔄',
      path: '/sync',
      tooltip: 'Sync with Trans-Hub'
    },
    {
      id: 'metrics',
      label: t('navigation.dashboard'),
      icon: '📊',
      path: '/metrics',
      tooltip: 'View metrics'
    },
    {
      id: 'settings',
      label: t('navigation.settings'),
      icon: '⚙️',
      path: '/settings',
      tooltip: 'Game settings'
    }
  ];

  // 快捷栏项目（底部）
  const hotbarItems: HotbarItem[] = [
    { id: 'scan', icon: '🔍', label: 'Scan', action: () => navigate('/scan') },
    { id: 'build', icon: '🔨', label: 'Build', action: () => navigate('/build') },
    { id: 'export', icon: '📤', label: 'Export', action: () => navigate('/export') },
    { id: 'import', icon: '📥', label: 'Import', action: () => navigate('/import') },
    { id: 'translate', icon: '🌐', label: 'Translate', action: () => navigate('/translate') },
    { id: 'test', icon: '🧪', label: 'Test', action: () => navigate('/test') },
    { id: 'deploy', icon: '🚀', label: 'Deploy', action: () => navigate('/deploy') },
    { id: 'help', icon: '❓', label: 'Help', action: () => navigate('/help') },
    { id: 'terminal', icon: '💻', label: 'Terminal', action: () => console.log('Open terminal') },
  ];

  // 更新时间
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 检查服务器状态
  useEffect(() => {
    const checkServerStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/health');
        setServerStatus(response.ok ? 'online' : 'offline');
      } catch {
        setServerStatus('offline');
      }
    };
    
    checkServerStatus();
    const interval = setInterval(checkServerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key >= '1' && e.key <= '9') {
        const slot = parseInt(e.key) - 1;
        setSelectedHotbarSlot(slot);
        hotbarItems[slot]?.action?.();
      }
      if (e.key === 'Escape') {
        setIsMenuOpen(!isMenuOpen);
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isMenuOpen]);

  // 获取当前页面标题
  const getCurrentPageTitle = () => {
    const currentNav = navItems.find(item => item.path === location.pathname);
    return currentNav?.label || 'Minecraft Localization Studio';
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#2C2C2C',
        backgroundImage: textures.stone,
        backgroundSize: '64px 64px',
        backgroundRepeat: 'repeat',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: typography.fontFamily.minecraft,
        imageRendering: 'pixelated',
      }}
    >
      {/* 顶部状态栏 */}
      <div
        style={{
          height: '32px',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderBottom: `2px solid ${minecraftColors.ui.border.dark}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          color: minecraftColors.ui.text.secondary,
          fontSize: typography.fontSize.small,
        }}
      >
        {/* 左侧信息 */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span>TH Suite MC L10n</span>
          <span style={{ color: minecraftColors.formatting['§7'] }}>|</span>
          <span>{getCurrentPageTitle()}</span>
        </div>

        {/* 右侧状态 */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          {/* 服务器状态 */}
          <MCTooltip content="Trans-Hub Server Status">
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: serverStatus === 'online' 
                    ? minecraftColors.status.online 
                    : minecraftColors.status.offline,
                  boxShadow: serverStatus === 'online'
                    ? `0 0 4px ${minecraftColors.status.online}`
                    : 'none',
                }}
              />
              <span>{serverStatus === 'online' ? 'Online' : 'Offline'}</span>
            </div>
          </MCTooltip>

          {/* 语言切换 */}
          <MCTooltip content="Change Language">
            <select
              value={i18n.language}
              onChange={(e) => languageManager.setLanguage(e.target.value as any)}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: minecraftColors.ui.text.secondary,
                fontFamily: typography.fontFamily.minecraft,
                fontSize: typography.fontSize.small,
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              <option value="en">English</option>
              <option value="zh-CN">简体中文</option>
            </select>
          </MCTooltip>

          {/* 游戏时间 */}
          <span>{currentTime.toLocaleTimeString()}</span>
        </div>
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, display: 'flex', position: 'relative' }}>
        {/* 左侧导航栏 */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: '280px',
                zIndex: 100,
              }}
            >
              <MCPanel
                variant="planks"
                title="Menu"
                closable
                onClose={() => setIsMenuOpen(false)}
                height="100%"
                style={{ height: '100%' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {navItems.map(item => (
                    <MCButton
                      key={item.id}
                      onClick={() => {
                        navigate(item.path);
                        setIsMenuOpen(false);
                      }}
                      variant={location.pathname === item.path ? 'primary' : 'default'}
                      fullWidth
                      icon={<span>{item.icon}</span>}
                    >
                      <span style={{ flex: 1, textAlign: 'left' }}>{item.label}</span>
                      {item.badge && (
                        <span
                          style={{
                            backgroundColor: minecraftColors.primary.redstone,
                            color: minecraftColors.ui.text.secondary,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: typography.fontSize.tiny,
                          }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </MCButton>
                  ))}
                </div>

                {/* 玩家状态 */}
                <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
                  <MCStatusBars
                    health={18}
                    hunger={16}
                    armor={10}
                    showLabels={false}
                    vertical={true}
                  />
                </div>
              </MCPanel>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 菜单按钮 */}
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          style={{
            position: 'absolute',
            left: '16px',
            top: '16px',
            width: '40px',
            height: '40px',
            backgroundColor: minecraftColors.ui.button.default,
            border: `2px solid ${minecraftColors.ui.border.dark}`,
            color: minecraftColors.ui.text.secondary,
            fontSize: '20px',
            fontFamily: typography.fontFamily.minecraft,
            cursor: 'pointer',
            zIndex: 99,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          ☰
        </button>

        {/* 页面内容 */}
        <main
          style={{
            flex: 1,
            padding: '24px',
            paddingBottom: '80px', // 为快捷栏留出空间
            overflow: 'auto',
          }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* 底部快捷栏（Hotbar） */}
      <div
        style={{
          position: 'fixed',
          bottom: '16px',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: '2px',
          padding: '4px',
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          border: `2px solid ${minecraftColors.ui.border.dark}`,
          zIndex: 1000,
        }}
      >
        {hotbarItems.map((item, index) => (
          <MCTooltip
            key={item.id}
            content={item.label}
            position="top"
          >
            <div style={{ position: 'relative' }}>
              <MCInventorySlot
                item={<span style={{ fontSize: '20px' }}>{item.icon}</span>}
                selected={selectedHotbarSlot === index}
                onClick={() => {
                  setSelectedHotbarSlot(index);
                  item.action?.();
                }}
                size={44}
              />
              <span
                style={{
                  position: 'absolute',
                  top: '2px',
                  left: '4px',
                  color: minecraftColors.ui.text.secondary,
                  fontSize: typography.fontSize.tiny,
                  fontFamily: typography.fontFamily.minecraft,
                  textShadow: '1px 1px 0px rgba(0, 0, 0, 0.75)',
                  pointerEvents: 'none',
                }}
              >
                {index + 1}
              </span>
            </div>
          </MCTooltip>
        ))}
      </div>
    </div>
  );
};

export default MCLayout;