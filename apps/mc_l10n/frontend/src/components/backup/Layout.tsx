import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
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
  Container,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Home as HomeIcon,
  FolderOpen as ProjectIcon,
  Search as ScanIcon,
  GetApp as ExtractIcon,
  Publish as ExportIcon,
  CloudUpload as TransferIcon,
  Build as BuildIcon,
  Security as SecurityIcon,
  Computer as ServerIcon,
  Settings as SettingsIcon,
  Storage as LocalDataIcon,
} from '@mui/icons-material'

const drawerWidth = 240

interface LayoutProps {
  children: React.ReactNode
}

interface NavItem {
  text: string
  path: string
  icon: React.ReactElement
}

const navItems: NavItem[] = [
  { text: '首页', path: '/', icon: <HomeIcon /> },
  { text: '项目', path: '/project', icon: <ProjectIcon /> },
  { text: '扫描', path: '/scan', icon: <ScanIcon /> },
  { text: '提取', path: '/extract', icon: <ExtractIcon /> },
  { text: '导出', path: '/export', icon: <ExportIcon /> },
  { text: '传输', path: '/transfer', icon: <TransferIcon /> },
  { text: '构建', path: '/build', icon: <BuildIcon /> },
  { text: '安全', path: '/security', icon: <SecurityIcon /> },
  { text: '服务器', path: '/server', icon: <ServerIcon /> },
  { text: '设置', path: '/settings', icon: <SettingsIcon /> },
  { text: '本地数据', path: '/local-data', icon: <LocalDataIcon /> },
]

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant='h6' noWrap component='div'>
          MC L10n
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {navItems.map(item => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              component={Link}
              to={item.path}
              selected={location.pathname === item.path}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position='fixed'
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color='inherit'
            aria-label='open drawer'
            edge='start'
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant='h6' noWrap component='div'>
            TH Suite MC L10n
          </Typography>
        </Toolbar>
      </AppBar>
      <Box component='nav' sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant='temporary'
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant='permanent'
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component='main'
        sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` } }}
      >
        <Toolbar />
        <Container maxWidth='xl'>{children}</Container>
      </Box>
    </Box>
  )
}

export default Layout
