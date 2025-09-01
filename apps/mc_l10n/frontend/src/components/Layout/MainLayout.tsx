/**
 * 主布局组件
 * 提供统一的页面布局和导航结构
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Avatar,
  Menu,
  MenuItem,
  Tooltip,
  useMediaQuery,
  Paper,
  Breadcrumbs,
  Link,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Menu as MenuIcon,
  Dashboard,
  FolderOpen,
  Settings,
  Notifications,
  Search,
  Sun,
  Moon,
  User,
  LogOut,
  ChevronRight,
  Home,
  Bell,
  Globe,
  FileText,
  TrendingUp,
  HelpCircle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;
  submenu?: NavItem[];
}

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
  breadcrumbs?: Array<{ label: string; path?: string }>;
  actions?: React.ReactNode;
}

const DRAWER_WIDTH = 280;

const navigationItems: NavItem[] = [
  {
    id: 'dashboard',
    label: '仪表板',
    icon: <Dashboard size={20} />,
    path: '/dashboard',
  },
  {
    id: 'projects',
    label: '项目管理',
    icon: <FolderOpen size={20} />,
    path: '/projects',
    badge: 3,
  },
  {
    id: 'translations',
    label: '翻译管理',
    icon: <Globe size={20} />,
    path: '/translations',
    submenu: [
      { id: 'translations-list', label: '翻译列表', icon: <FileText size={16} />, path: '/translations' },
      { id: 'translations-progress', label: '翻译进度', icon: <TrendingUp size={16} />, path: '/translations/progress' },
    ],
  },
  {
    id: 'settings',
    label: '设置',
    icon: <Settings size={20} />,
    path: '/settings',
  },
];

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  title,
  breadcrumbs,
  actions,
}) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));

  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const [notifications] = useState(5);
  const [darkMode, setDarkMode] = useState(false);
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

  // 检测当前路径并展开相应的菜单
  useEffect(() => {
    const currentPath = location.pathname;
    navigationItems.forEach(item => {
      if (item.submenu?.some(sub => currentPath.startsWith(sub.path))) {
        setExpandedItems(prev => prev.includes(item.id) ? prev : [...prev, item.id]);
      }
    });
  }, [location.pathname]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleNavItemClick = (item: NavItem) => {
    if (item.submenu) {
      setExpandedItems(prev => 
        prev.includes(item.id) 
          ? prev.filter(id => id !== item.id)
          : [...prev, item.id]
      );
    } else {
      navigate(item.path);
      if (isMobile) {
        setMobileOpen(false);
      }
    }
  };

  const isActiveRoute = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const renderNavItem = (item: NavItem, depth = 0) => {
    const isActive = isActiveRoute(item.path);
    const isExpanded = expandedItems.includes(item.id);
    const hasSubmenu = item.submenu && item.submenu.length > 0;

    return (
      <Box key={item.id}>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => handleNavItemClick(item)}
            sx={{
              pl: 2 + depth * 2,
              py: 1.5,
              borderRadius: 2,
              mx: 1,
              mb: 0.5,
              backgroundColor: isActive ? alpha(theme.palette.primary.main, 0.1) : 'transparent',
              color: isActive ? theme.palette.primary.main : theme.palette.text.primary,
              '&:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.08),
              },
              transition: 'all 0.2s ease-in-out',
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 40,
                color: isActive ? theme.palette.primary.main : theme.palette.text.secondary,
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              sx={{
                '& .MuiListItemText-primary': {
                  fontSize: '0.875rem',
                  fontWeight: isActive ? 600 : 500,
                },
              }}
            />
            {item.badge && item.badge > 0 && (
              <Badge
                badgeContent={item.badge}
                color="error"
                sx={{
                  '& .MuiBadge-badge': {
                    fontSize: '0.75rem',
                    height: 18,
                    minWidth: 18,
                  },
                }}
              />
            )}
            {hasSubmenu && (
              <IconButton size="small" sx={{ ml: 1 }}>
                <motion.div
                  animate={{ rotate: isExpanded ? 90 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronRight size={16} />
                </motion.div>
              </IconButton>
            )}
          </ListItemButton>
        </ListItem>

        <AnimatePresence>
          {hasSubmenu && isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              {item.submenu!.map(subItem => renderNavItem(subItem, depth + 1))}
            </motion.div>
          )}
        </AnimatePresence>
      </Box>
    );
  };

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Logo 区域 */}
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          MC L10n
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Minecraft 本地化工具
        </Typography>
      </Box>

      <Divider />

      {/* 导航菜单 */}
      <Box sx={{ flex: 1, overflow: 'auto', py: 1 }}>
        <List>
          {navigationItems.map(item => renderNavItem(item))}
        </List>
      </Box>

      {/* 底部信息 */}
      <Box sx={{ p: 2 }}>
        <Paper
          sx={{
            p: 2,
            backgroundColor: alpha(theme.palette.primary.main, 0.05),
            border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
          }}
        >
          <Typography variant="caption" color="text.secondary" display="block">
            当前版本
          </Typography>
          <Typography variant="body2" fontWeight={600}>
            v1.0.0-beta
          </Typography>
        </Paper>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      {/* 应用栏 */}
      <AppBar
        position="fixed"
        sx={{
          width: { lg: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { lg: `${DRAWER_WIDTH}px` },
          backgroundColor: 'background.paper',
          color: 'text.primary',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="打开导航"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { lg: 'none' } }}
          >
            <MenuIcon size={20} />
          </IconButton>

          <Box sx={{ flex: 1 }}>
            {breadcrumbs && breadcrumbs.length > 0 && (
              <Breadcrumbs
                separator={<ChevronRight size={16} />}
                sx={{ mb: 0.5 }}
              >
                <Link
                  component="button"
                  variant="body2"
                  onClick={() => navigate('/dashboard')}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    textDecoration: 'none',
                    color: 'text.secondary',
                    '&:hover': { color: 'primary.main' },
                  }}
                >
                  <Home size={14} style={{ marginRight: 4 }} />
                  主页
                </Link>
                {breadcrumbs.map((breadcrumb, index) => (
                  <Typography
                    key={index}
                    variant="body2"
                    color={index === breadcrumbs.length - 1 ? 'text.primary' : 'text.secondary'}
                    sx={{ fontWeight: index === breadcrumbs.length - 1 ? 600 : 400 }}
                  >
                    {breadcrumb.label}
                  </Typography>
                ))}
              </Breadcrumbs>
            )}
            {title && (
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {title}
              </Typography>
            )}
          </Box>

          {actions && (
            <Box sx={{ mr: 2 }}>
              {actions}
            </Box>
          )}

          {/* 顶部操作按钮 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="搜索">
              <IconButton size="small">
                <Search size={18} />
              </IconButton>
            </Tooltip>

            <Tooltip title="通知">
              <IconButton size="small">
                <Badge badgeContent={notifications} color="error">
                  <Bell size={18} />
                </Badge>
              </IconButton>
            </Tooltip>

            <Tooltip title={darkMode ? '切换到亮色模式' : '切换到暗色模式'}>
              <IconButton 
                size="small" 
                onClick={() => setDarkMode(!darkMode)}
              >
                {darkMode ? <Sun size={18} /> : <Moon size={18} />}
              </IconButton>
            </Tooltip>

            <Tooltip title="帮助">
              <IconButton size="small">
                <HelpCircle size={18} />
              </IconButton>
            </Tooltip>

            {/* 用户菜单 */}
            <Tooltip title="用户菜单">
              <IconButton
                size="small"
                onClick={handleUserMenuOpen}
                sx={{ ml: 1 }}
              >
                <Avatar sx={{ width: 32, height: 32, fontSize: '0.875rem' }}>
                  U
                </Avatar>
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* 侧边栏 */}
      <Box
        component="nav"
        sx={{ width: { lg: DRAWER_WIDTH }, flexShrink: { lg: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', lg: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', lg: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
              borderRight: `1px solid ${theme.palette.divider}`,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* 主内容区域 */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { lg: `calc(100% - ${DRAWER_WIDTH}px)` },
          height: '100vh',
          backgroundColor: 'background.default',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Toolbar />
        <Box 
          sx={{ 
            flex: 1,
            overflow: 'auto',
            p: 3,
            '&::-webkit-scrollbar': {
              width: '8px',
            },
            '&::-webkit-scrollbar-track': {
              background: 'rgba(0,0,0,0.05)',
              borderRadius: '10px',
            },
            '&::-webkit-scrollbar-thumb': {
              background: 'rgba(0,188,212,0.3)',
              borderRadius: '10px',
              '&:hover': {
                background: 'rgba(0,188,212,0.5)',
              },
            },
          }}
        >
          {children}
        </Box>
      </Box>

      {/* 用户菜单 */}
      <Menu
        anchorEl={userMenuAnchor}
        open={Boolean(userMenuAnchor)}
        onClose={handleUserMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        PaperProps={{
          sx: {
            mt: 1,
            minWidth: 200,
            borderRadius: 2,
            boxShadow: theme.shadows[8],
          },
        }}
      >
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <User size={18} />
          </ListItemIcon>
          <ListItemText primary="个人资料" />
        </MenuItem>
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <Settings size={18} />
          </ListItemIcon>
          <ListItemText primary="设置" />
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <LogOut size={18} />
          </ListItemIcon>
          <ListItemText primary="退出登录" />
        </MenuItem>
      </Menu>
    </Box>
  );
};