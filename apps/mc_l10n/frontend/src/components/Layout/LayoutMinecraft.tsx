import React, { useState } from 'react';
import { 
  Box, 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  IconButton,
  Typography,
  Divider,
  Badge,
  Tooltip,
  Avatar
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Menu as MenuIcon,
  Home,
  Search,
  Folder,
  Package,
  Download,
  Upload,
  Hammer,
  Settings,
  Database,
  Shield,
  Server,
  ChevronLeft,
  Sparkles,
  Gamepad2,
  X
} from 'lucide-react';
import { MinecraftBlock } from '../MinecraftComponents';
import { MinecraftThemeToggle } from '../minecraft/MinecraftThemeToggle';
import { minecraftColors } from '../../theme/minecraftTheme';

interface LayoutMinecraftProps {
  children: React.ReactNode;
}

interface MenuItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;
  color?: string;
  blockType?: 'grass' | 'stone' | 'diamond' | 'gold' | 'iron' | 'emerald';
}

const menuItems: MenuItem[] = [
  { 
    id: 'home', 
    label: '首页', 
    icon: <Home size={20} />, 
    path: '/',
    blockType: 'diamond',
    color: minecraftColors.diamondBlue
  },
  { 
    id: 'scan', 
    label: '扫描', 
    icon: <Search size={20} />, 
    path: '/scan',
    blockType: 'emerald',
    color: minecraftColors.emerald,
    badge: 3
  },
  { 
    id: 'project', 
    label: '项目管理', 
    icon: <Folder size={20} />, 
    path: '/project',
    blockType: 'gold',
    color: minecraftColors.goldYellow
  },
  { 
    id: 'extract', 
    label: '提取管理', 
    icon: <Package size={20} />, 
    path: '/extract',
    blockType: 'iron',
    color: minecraftColors.iron
  },
  { 
    id: 'export', 
    label: '导出管理', 
    icon: <Download size={20} />, 
    path: '/export',
    blockType: 'grass',
    color: minecraftColors.grassGreen
  },
  { 
    id: 'transfer', 
    label: '传输管理', 
    icon: <Upload size={20} />, 
    path: '/transfer',
    blockType: 'stone',
    color: minecraftColors.stoneGray
  },
  { 
    id: 'build', 
    label: '构建管理', 
    icon: <Hammer size={20} />, 
    path: '/build',
    blockType: 'iron',
    color: minecraftColors.cobblestone
  },
];

const bottomMenuItems: MenuItem[] = [
  { 
    id: 'local-data', 
    label: '本地数据', 
    icon: <Database size={20} />, 
    path: '/local-data',
    color: '#9C27B0'
  },
  { 
    id: 'security', 
    label: '安全设置', 
    icon: <Shield size={20} />, 
    path: '/security',
    color: '#F44336'
  },
  { 
    id: 'server', 
    label: '服务器', 
    icon: <Server size={20} />, 
    path: '/server',
    color: '#2196F3'
  },
  { 
    id: 'settings', 
    label: '设置', 
    icon: <Settings size={20} />, 
    path: '/settings',
    color: '#607D8B'
  },
];

export default function LayoutMinecraft({ children }: LayoutMinecraftProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  const sidebarWidth = sidebarOpen ? 260 : 80;

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#0A0E27' }}>
      {/* 顶部栏 */}
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          height: 64,
          background: 'linear-gradient(180deg, #1A1A2E 0%, #0F0F1E 100%)',
          borderBottom: '3px solid #2A2A4E',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          zIndex: 1200,
          boxShadow: '0 4px 20px rgba(0,0,0,0.8)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton
            onClick={() => setSidebarOpen(!sidebarOpen)}
            sx={{
              color: '#FFFFFF',
              background: 'rgba(255,255,255,0.1)',
              border: '2px solid rgba(255,255,255,0.2)',
              borderRadius: 0,
              '&:hover': {
                background: 'rgba(255,255,255,0.2)',
                transform: 'scale(1.1)',
              }
            }}
          >
            {sidebarOpen ? <ChevronLeft size={20} /> : <MenuIcon size={20} />}
          </IconButton>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MinecraftBlock type="diamond" size={32} animated />
            <Typography
              sx={{
                fontFamily: '"Minecraft", "Press Start 2P", monospace',
                fontSize: '16px',
                color: '#FFFFFF',
                textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
                letterSpacing: '0.05em',
                display: { xs: 'none', sm: 'block' }
              }}
            >
              TH Suite MC L10n
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <motion.div whileHover={{ scale: 1.1 }}>
            <MinecraftThemeToggle />
          </motion.div>
          
          <motion.div whileHover={{ scale: 1.1 }}>
            <Tooltip title="游戏模式">
              <IconButton
                sx={{
                  color: '#FFD700',
                  '&:hover': { background: 'rgba(255,215,0,0.1)' }
                }}
              >
                <Gamepad2 size={20} />
              </IconButton>
            </Tooltip>
          </motion.div>
          
          <motion.div whileHover={{ scale: 1.1 }}>
            <Tooltip title="特效">
              <IconButton
                sx={{
                  color: '#E91E63',
                  '&:hover': { background: 'rgba(233,30,99,0.1)' }
                }}
              >
                <Sparkles size={20} />
              </IconButton>
            </Tooltip>
          </motion.div>

          <Avatar
            sx={{
              width: 32,
              height: 32,
              background: 'linear-gradient(135deg, #667EEA 0%, #764BA2 100%)',
              fontSize: '14px',
              fontFamily: '"Minecraft", monospace',
              border: '2px solid #FFFFFF',
              borderRadius: 0,
            }}
          >
            S
          </Avatar>
        </Box>
      </Box>

      {/* 侧边栏 */}
      <Drawer
        variant="permanent"
        sx={{
          width: sidebarWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: sidebarWidth,
            boxSizing: 'border-box',
            background: 'linear-gradient(180deg, #16213E 0%, #0F172A 100%)',
            borderRight: '3px solid #2A2A4E',
            mt: '64px',
            transition: 'width 0.3s ease',
            overflow: 'hidden',
            boxShadow: '4px 0 20px rgba(0,0,0,0.8)',
          },
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* 主菜单 */}
          <List sx={{ flex: 1, py: 2 }}>
            {menuItems.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <ListItem
                  button
                  onClick={() => handleNavigate(item.path)}
                  onMouseEnter={() => setHoveredItem(item.id)}
                  onMouseLeave={() => setHoveredItem(null)}
                  sx={{
                    mb: 1,
                    mx: 1,
                    borderRadius: 0,
                    position: 'relative',
                    background: isActive(item.path)
                      ? `linear-gradient(90deg, ${item.color}33 0%, transparent 100%)`
                      : hoveredItem === item.id
                      ? 'rgba(255,255,255,0.05)'
                      : 'transparent',
                    borderLeft: isActive(item.path) ? `4px solid ${item.color}` : '4px solid transparent',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: sidebarOpen ? 'translateX(8px)' : 'scale(1.1)',
                    },
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: isActive(item.path)
                        ? `linear-gradient(90deg, ${item.color}22 0%, transparent 100%)`
                        : 'transparent',
                      transition: 'all 0.3s ease',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 40,
                      color: isActive(item.path) ? item.color : '#FFFFFF',
                      filter: isActive(item.path) ? `drop-shadow(0 0 8px ${item.color})` : 'none',
                    }}
                  >
                    {item.blockType && (hoveredItem === item.id || isActive(item.path)) ? (
                      <MinecraftBlock type={item.blockType} size={20} animated={isActive(item.path)} />
                    ) : (
                      item.icon
                    )}
                  </ListItemIcon>
                  {sidebarOpen && (
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '13px',
                              color: isActive(item.path) ? '#FFFFFF' : 'rgba(255,255,255,0.8)',
                              fontWeight: isActive(item.path) ? 'bold' : 'normal',
                              letterSpacing: '0.02em',
                            }}
                          >
                            {item.label}
                          </Typography>
                          {item.badge && (
                            <Badge
                              badgeContent={item.badge}
                              sx={{
                                '& .MuiBadge-badge': {
                                  background: '#F44336',
                                  color: '#FFFFFF',
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '10px',
                                  height: 16,
                                  minWidth: 16,
                                  borderRadius: 0,
                                }
                              }}
                            />
                          )}
                        </Box>
                      }
                    />
                  )}
                </ListItem>
              </motion.div>
            ))}
          </List>

          <Divider sx={{ borderColor: '#2A2A4E', mx: 2 }} />

          {/* 底部菜单 */}
          <List sx={{ py: 2 }}>
            {bottomMenuItems.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.05 }}
              >
                <ListItem
                  button
                  onClick={() => handleNavigate(item.path)}
                  onMouseEnter={() => setHoveredItem(item.id)}
                  onMouseLeave={() => setHoveredItem(null)}
                  sx={{
                    mb: 0.5,
                    mx: 1,
                    borderRadius: 0,
                    background: isActive(item.path)
                      ? `linear-gradient(90deg, ${item.color}33 0%, transparent 100%)`
                      : hoveredItem === item.id
                      ? 'rgba(255,255,255,0.05)'
                      : 'transparent',
                    borderLeft: isActive(item.path) ? `4px solid ${item.color}` : '4px solid transparent',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: sidebarOpen ? 'translateX(8px)' : 'scale(1.1)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 40,
                      color: isActive(item.path) ? item.color : 'rgba(255,255,255,0.6)',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  {sidebarOpen && (
                    <ListItemText
                      primary={
                        <Typography
                          sx={{
                            fontFamily: '"Minecraft", monospace',
                            fontSize: '12px',
                            color: isActive(item.path) ? '#FFFFFF' : 'rgba(255,255,255,0.6)',
                            fontWeight: isActive(item.path) ? 'bold' : 'normal',
                          }}
                        >
                          {item.label}
                        </Typography>
                      }
                    />
                  )}
                </ListItem>
              </motion.div>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* 主内容区 */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          mt: '64px',
          ml: `${sidebarWidth}px`,
          transition: 'margin-left 0.3s ease',
          background: 'linear-gradient(135deg, #0A0E27 0%, #0F172A 100%)',
          minHeight: 'calc(100vh - 64px)',
          overflow: 'auto',
          '&::-webkit-scrollbar': {
            width: '12px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#0A0E27',
            borderRadius: 0,
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'linear-gradient(180deg, #4A4A6A 0%, #2A2A4E 100%)',
            borderRadius: 0,
            border: '2px solid #0A0E27',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'linear-gradient(180deg, #5A5A7A 0%, #3A3A5E 100%)',
          },
        }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </Box>
    </Box>
  );
}