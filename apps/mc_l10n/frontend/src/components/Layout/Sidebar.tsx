import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Divider,
  Tooltip,
  useTheme,
  alpha,
  Collapse,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Home,
  Search,
  Download,
  Upload,
  Package,
  Server,
  Shield,
  Settings,
  ChevronDown,
  ChevronRight,
  FolderOpen,
  Languages,
  Database,
  TestTube,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@stores/appStore';
import { useCommonTranslation } from '@hooks/useTranslation';
// import { LanguageSwitcher, type LanguageOption } from '@th-suite/ui-kit'; // 暂时注释掉

interface SidebarProps {
  open: boolean;
  width: number;
  collapsedWidth: number;
  isMobile: boolean;
  onClose: () => void;
}

interface NavigationItem {
  id: string;
  labelKey: string;
  path: string;
  icon: React.ReactNode;
  descriptionKey?: string;
}

const navigationItems: NavigationItem[] = [
  {
    id: 'home',
    labelKey: 'pages.home',
    path: '/',
    icon: <Home size={20} />,
    descriptionKey: 'pageDescriptions.home',
  },
  {
    id: 'project',
    labelKey: 'pages.project',
    path: '/project',
    icon: <FolderOpen size={20} />,
    descriptionKey: 'pageDescriptions.project',
  },
  {
    id: 'scan',
    labelKey: 'pages.scan',
    path: '/scan',
    icon: <Search size={20} />,
    descriptionKey: 'pageDescriptions.scan',
  },
  {
    id: 'extract',
    labelKey: 'pages.extract',
    path: '/extract',
    icon: <Download size={20} />,
    descriptionKey: 'pageDescriptions.extract',
  },
  {
    id: 'export',
    labelKey: 'pages.export',
    path: '/export',
    icon: <Upload size={20} />,
    descriptionKey: 'pageDescriptions.export',
  },
  {
    id: 'transfer',
    labelKey: 'pages.transfer',
    path: '/transfer',
    icon: <Download size={20} />,
    descriptionKey: 'pageDescriptions.transfer',
  },
  {
    id: 'build',
    labelKey: 'pages.build',
    path: '/build',
    icon: <Package size={20} />,
    descriptionKey: 'pageDescriptions.build',
  },
  {
    id: 'security',
    labelKey: 'pages.security',
    path: '/security',
    icon: <Shield size={20} />,
    descriptionKey: 'pageDescriptions.security',
  },
  {
    id: 'server',
    labelKey: 'pages.server',
    path: '/server',
    icon: <Server size={20} />,
    descriptionKey: 'pageDescriptions.server',
  },
  {
    id: 'local-data',
    labelKey: 'pages.localData',
    path: '/local-data',
    icon: <Database size={20} />,
    descriptionKey: 'pageDescriptions.localData',
  },
  {
    id: 'progress-test',
    labelKey: '🧪 进度测试',
    path: '/progress-test',
    icon: <TestTube size={20} />,
    descriptionKey: '测试实时进度组件',
  },
];

function Sidebar({ open, width, collapsedWidth, isMobile, onClose }: SidebarProps) {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { recentProjects, setCurrentProject, currentProject, hasActiveProject, canShowProjectFeatures } = useAppStore();
  const { t: tCommon, currentLanguage, i18n } = useCommonTranslation();

  const languages = [
    { code: 'zh-CN', name: 'Chinese (Simplified)', nativeName: '简体中文' },
    { code: 'en', name: 'English', nativeName: 'English' },
    { code: 'ja-JP', name: 'Japanese', nativeName: '日本語' },
    { code: 'ko-KR', name: 'Korean', nativeName: '한국어' },
    { code: 'fr-FR', name: 'French', nativeName: 'Français' },
    { code: 'de-DE', name: 'German', nativeName: 'Deutsch' },
    { code: 'es-ES', name: 'Spanish', nativeName: 'Español' },
    { code: 'ru-RU', name: 'Russian', nativeName: 'Русский' },
  ];

  const handleLanguageChange = async (languageCode: string) => {
    try {
      await i18n.changeLanguage(languageCode);
    } catch (error) {
      console.error('Failed to change language:', error);
    }
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    if (isMobile) {
      onClose();
    }
  };

  const handleProjectSelect = (project: any) => {
    setCurrentProject(project);
    // Navigate to appropriate page based on project type
    navigate(`/${project.type}`);
    if (isMobile) {
      onClose();
    }
  };

  const drawerContent = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: theme.palette.background.paper,
        borderRight: `1px solid ${theme.palette.divider}`,
      }}
    >
      {/* Logo/Brand */}
      <Box
        sx={{
          height: '64px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'flex-start' : 'center',
          paddingX: open ? 3 : 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              backgroundColor: theme.palette.primary.main,
              borderRadius: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '1.2rem',
            }}
          >
            MC
          </Box>
          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 600,
                    color: theme.palette.text.primary,
                    whiteSpace: 'nowrap',
                  }}
                >
                  TH Suite MC L10n
                </Typography>
              </motion.div>
            )}
          </AnimatePresence>
        </Box>
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <List sx={{ paddingTop: 2 }}>
          {navigationItems.map((item) => {
            // 条件导航：只有在有项目时才显示项目相关功能
            const projectRequiredItems = ['scan', 'extract', 'export', 'transfer', 'build', 'security'];
            const isProjectRequired = projectRequiredItems.includes(item.id);
            
            // 使用新的状态管理函数来控制可见性
            if (isProjectRequired && !canShowProjectFeatures()) {
              return null;
            }
            
            const isActive = location.pathname === item.path;
            
            const listItem = (
              <ListItem key={item.id} disablePadding>
                <ListItemButton
                  onClick={() => handleNavigate(item.path)}
                  sx={{
                    minHeight: 48,
                    justifyContent: open ? 'initial' : 'center',
                    paddingX: open ? 3 : 2,
                    marginX: 1,
                    borderRadius: 1,
                    backgroundColor: isActive
                      ? alpha(theme.palette.primary.main, 0.1)
                      : 'transparent',
                    color: isActive
                      ? theme.palette.primary.main
                      : theme.palette.text.primary,
                    '&:hover': {
                      backgroundColor: isActive
                        ? alpha(theme.palette.primary.main, 0.15)
                        : alpha(theme.palette.action.hover, 0.1),
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 0,
                      marginRight: open ? 3 : 'auto',
                      justifyContent: 'center',
                      color: 'inherit',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <AnimatePresence>
                    {open && (
                      <motion.div
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: 'auto' }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{ overflow: 'hidden' }}
                      >
                        <ListItemText
                          primary={tCommon(item.labelKey)}
                          sx={{
                            '& .MuiListItemText-primary': {
                              fontWeight: isActive ? 600 : 400,
                              fontSize: '0.9rem',
                            },
                          }}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </ListItemButton>
              </ListItem>
            );

            return open ? (
              listItem
            ) : (
              <Tooltip
                key={item.id}
                title={item.descriptionKey ? tCommon(item.descriptionKey) : tCommon(item.labelKey)}
                placement="right"
                arrow
              >
                {listItem}
              </Tooltip>
            );
          })}
        </List>

        {/* Recent Projects */}
        <AnimatePresence>
          {open && recentProjects.length > 0 && hasActiveProject() && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Divider sx={{ marginY: 2 }} />
              <Box sx={{ paddingX: 3, paddingBottom: 1 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: theme.palette.text.secondary,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: 0.5,
                  }}
                >
                  {tCommon('sidebar.recentProjects')}
                </Typography>
              </Box>
              <List dense>
                {recentProjects.slice(0, 5).map((project) => (
                  <ListItem key={project.id} disablePadding>
                    <ListItemButton
                      onClick={() => handleProjectSelect(project)}
                      sx={{
                        paddingX: 3,
                        paddingY: 0.5,
                        '&:hover': {
                          backgroundColor: alpha(theme.palette.action.hover, 0.1),
                        },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <FolderOpen size={16} />
                      </ListItemIcon>
                      <ListItemText
                        primary={project.name}
                        secondary={new Date(project.lastOpened).toLocaleDateString()}
                        sx={{
                          '& .MuiListItemText-primary': {
                            fontSize: '0.8rem',
                            fontWeight: 500,
                          },
                          '& .MuiListItemText-secondary': {
                            fontSize: '0.7rem',
                          },
                        }}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </motion.div>
          )}
        </AnimatePresence>
      </Box>

      {/* Language Switcher */}
      <Box sx={{ padding: open ? 2 : 1, borderTop: `1px solid ${theme.palette.divider}` }}>
        {open ? (
          <Box sx={{ marginBottom: 1 }}>
            <Typography variant="caption" sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1, 
              marginBottom: 1,
              fontSize: '0.8rem',
              color: 'text.secondary'
            }}>
              <Languages size={16} />
              {tCommon('common.language')}
            </Typography>
            <FormControl fullWidth size="small">
            <Select
              value={currentLanguage}
              onChange={(e) => handleLanguageChange(e.target.value)}
              sx={{
                fontSize: '0.85rem',
                '& .MuiSelect-select': {
                  paddingY: 1,
                },
              }}
            >
              {languages.map((lang) => (
                <MenuItem key={lang.code} value={lang.code} sx={{ fontSize: '0.85rem' }}>
                  {lang.nativeName}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Tooltip title={tCommon('common.language')} placement="right" arrow>
              <FormControl size="small" sx={{ minWidth: 40 }}>
                <Select
                  value={currentLanguage}
                  onChange={(e) => handleLanguageChange(e.target.value)}
                  displayEmpty
                  sx={{
                    '& .MuiSelect-select': {
                      paddingY: 1,
                      paddingX: 1,
                      display: 'flex',
                      justifyContent: 'center',
                      fontSize: '0.75rem',
                    },
                    '& .MuiOutlinedInput-notchedOutline': {
                      border: 'none',
                    },
                  }}
                  renderValue={(value) => {
                    const lang = languages.find(l => l.code === value);
                    return <Languages size={16} />;
                  }}
                >
                  {languages.map((lang) => (
                    <MenuItem key={lang.code} value={lang.code} sx={{ fontSize: '0.85rem' }}>
                      {lang.nativeName}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Tooltip>
          </Box>
        )}
      </Box>

      {/* Settings */}
      <Box sx={{ borderTop: `1px solid ${theme.palette.divider}` }}>
        <List>
          <ListItem disablePadding>
            {open ? (
              <ListItemButton
                onClick={() => handleNavigate('/settings')}
                sx={{
                  minHeight: 48,
                  paddingX: 3,
                  color: location.pathname === '/settings'
                    ? theme.palette.primary.main
                    : theme.palette.text.primary,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    marginRight: 3,
                    color: 'inherit',
                  }}
                >
                  <Settings size={20} />
                </ListItemIcon>
                <ListItemText
                  primary={tCommon('pages.settings')}
                  sx={{
                    '& .MuiListItemText-primary': {
                      fontSize: '0.9rem',
                      fontWeight: location.pathname === '/settings' ? 600 : 400,
                    },
                  }}
                />
              </ListItemButton>
            ) : (
              <Tooltip title={tCommon('pages.settings')} placement="right" arrow>
                <ListItemButton
                  onClick={() => handleNavigate('/settings')}
                  sx={{
                    minHeight: 48,
                    justifyContent: 'center',
                    paddingX: 2,
                    color: location.pathname === '/settings'
                      ? theme.palette.primary.main
                      : theme.palette.text.primary,
                  }}
                >
                  <Settings size={20} />
                </ListItemButton>
              </Tooltip>
            )}
          </ListItem>
        </List>
      </Box>
    </Box>
  );

  return (
    <Drawer
      variant={isMobile ? 'temporary' : 'permanent'}
      open={isMobile ? open : true}
      onClose={onClose}
      sx={{
        width: open ? width : collapsedWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: open ? width : collapsedWidth,
          boxSizing: 'border-box',
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          overflowX: 'hidden',
          border: 'none',
        },
      }}
      ModalProps={{
        keepMounted: true, // Better open performance on mobile
      }}
    >
      {drawerContent}
    </Drawer>
  );
}

export default Sidebar;