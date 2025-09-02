import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Tabs,
  Tab
} from '@mui/material';
import { Keyboard, X, Command, Info } from 'lucide-react';
import { MinecraftButton, MinecraftCard } from '@components/minecraft';
import { formatShortcut, getModifierKey, useGlobalShortcuts } from '@hooks/useKeyboardShortcuts';
import { minecraftColors } from '../theme/minecraftTheme';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

export function ShortcutHelp() {
  const [open, setOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState(0);
  const globalShortcuts = useGlobalShortcuts();
  const modKey = getModifierKey();

  // 按类别分组快捷键
  const navigationShortcuts = globalShortcuts.filter(s => 
    ['返回首页', '扫描页面', '项目管理', '导出管理', '传输管理', '构建管理', '设置'].includes(s.description)
  );

  const actionShortcuts = globalShortcuts.filter(s => 
    ['新建项目', '打开文件', '刷新', '搜索'].includes(s.description)
  );

  const uiShortcuts = globalShortcuts.filter(s => 
    ['切换侧边栏', '关闭对话框/返回'].includes(s.description)
  );

  const tableShortcuts = [
    { key: 'a', ctrl: true, description: '全选表格项' },
    { key: 'd', ctrl: true, description: '取消选择' },
    { key: 'Delete', description: '删除选中项' },
    { key: 'Enter', description: '编辑选中项' },
    { key: '↑↓', description: '上下导航' },
    { key: 'Space', description: '选择/取消当前项' }
  ];

  const dialogShortcuts = [
    { key: 'Escape', description: '关闭对话框' },
    { key: 'Enter', ctrl: true, description: '确认操作' },
    { key: 'Tab', description: '切换焦点' },
    { key: 'Tab', shift: true, description: '反向切换焦点' }
  ];

  const renderShortcutTable = (shortcuts: any[]) => (
    <TableContainer 
      component={Paper} 
      sx={{ 
        bgcolor: 'transparent', 
        border: '2px solid #2A2A4E',
        borderRadius: 0
      }}
    >
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontFamily: '"Minecraft", monospace', color: minecraftColors.goldYellow }}>
              快捷键
            </TableCell>
            <TableCell sx={{ fontFamily: '"Minecraft", monospace', color: minecraftColors.goldYellow }}>
              功能
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {shortcuts.map((shortcut, index) => (
            <TableRow key={index} hover>
              <TableCell>
                <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                  {renderKeys(shortcut)}
                </Box>
              </TableCell>
              <TableCell sx={{ color: 'text.secondary' }}>
                {shortcut.description}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderKeys = (shortcut: any) => {
    const keys = [];
    
    if (shortcut.ctrl) {
      keys.push(
        <Chip
          key="ctrl"
          label={modKey}
          size="small"
          sx={{
            bgcolor: minecraftColors.stone,
            color: '#FFFFFF',
            fontFamily: 'monospace',
            height: 20
          }}
        />
      );
    }
    
    if (shortcut.shift) {
      keys.push(
        <Chip
          key="shift"
          label="Shift"
          size="small"
          sx={{
            bgcolor: minecraftColors.stone,
            color: '#FFFFFF',
            fontFamily: 'monospace',
            height: 20
          }}
        />
      );
    }
    
    if (shortcut.alt) {
      keys.push(
        <Chip
          key="alt"
          label="Alt"
          size="small"
          sx={{
            bgcolor: minecraftColors.stone,
            color: '#FFFFFF',
            fontFamily: 'monospace',
            height: 20
          }}
        />
      );
    }

    keys.push(
      <Typography key="plus" variant="caption" sx={{ mx: 0.5 }}>
        +
      </Typography>
    );
    
    keys.push(
      <Chip
        key="key"
        label={shortcut.key.toUpperCase()}
        size="small"
        sx={{
          bgcolor: minecraftColors.diamondBlue,
          color: '#FFFFFF',
          fontFamily: 'monospace',
          fontWeight: 'bold',
          height: 20
        }}
      />
    );
    
    return keys;
  };

  return (
    <>
      {/* 快捷键帮助按钮 */}
      <Tooltip title="快捷键帮助 (Ctrl+?)">
        <IconButton
          onClick={() => setOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            bgcolor: 'rgba(15, 23, 42, 0.9)',
            border: '2px solid #2A2A4E',
            borderRadius: 0,
            '&:hover': {
              bgcolor: 'rgba(15, 23, 42, 1)',
              transform: 'scale(1.1)'
            }
          }}
        >
          <Keyboard size={24} style={{ color: minecraftColors.goldYellow }} />
        </IconButton>
      </Tooltip>

      {/* 快捷键帮助对话框 */}
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#0F172A',
            border: '2px solid #2A2A4E',
            borderRadius: 0
          }
        }}
      >
        <DialogTitle 
          sx={{ 
            fontFamily: '"Minecraft", monospace',
            display: 'flex',
            alignItems: 'center',
            gap: 1
          }}
        >
          <Keyboard size={24} style={{ color: minecraftColors.goldYellow }} />
          键盘快捷键
          <Box sx={{ flex: 1 }} />
          <IconButton onClick={() => setOpen(false)} size="small">
            <X size={20} />
          </IconButton>
        </DialogTitle>

        <DialogContent>
          <Tabs
            value={selectedTab}
            onChange={(e, v) => setSelectedTab(v)}
            sx={{
              borderBottom: '2px solid #2A2A4E',
              mb: 2,
              '& .MuiTab-root': {
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px'
              }
            }}
          >
            <Tab label="全局快捷键" />
            <Tab label="表格操作" />
            <Tab label="对话框" />
          </Tabs>

          <TabPanel value={selectedTab} index={0}>
            <Box sx={{ mb: 3 }}>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontFamily: '"Minecraft", monospace',
                  color: minecraftColors.emerald,
                  mb: 2
                }}
              >
                导航
              </Typography>
              {renderShortcutTable(navigationShortcuts)}
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontFamily: '"Minecraft", monospace',
                  color: minecraftColors.emerald,
                  mb: 2
                }}
              >
                操作
              </Typography>
              {renderShortcutTable(actionShortcuts)}
            </Box>

            <Box>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontFamily: '"Minecraft", monospace',
                  color: minecraftColors.emerald,
                  mb: 2
                }}
              >
                界面控制
              </Typography>
              {renderShortcutTable(uiShortcuts)}
            </Box>
          </TabPanel>

          <TabPanel value={selectedTab} index={1}>
            {renderShortcutTable(tableShortcuts)}
          </TabPanel>

          <TabPanel value={selectedTab} index={2}>
            {renderShortcutTable(dialogShortcuts)}
          </TabPanel>

          <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid #2A2A4E', borderRadius: 0 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Info size={16} style={{ color: minecraftColors.goldYellow }} />
              <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                提示
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              • 在输入框中，大部分全局快捷键会被禁用以避免冲突
            </Typography>
            <br />
            <Typography variant="caption" color="text.secondary">
              • 某些快捷键可能因操作系统或浏览器限制而无法使用
            </Typography>
            <br />
            <Typography variant="caption" color="text.secondary">
              • 使用 {modKey}+? 可以随时打开此帮助对话框
            </Typography>
          </Box>
        </DialogContent>

        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setOpen(false)}
          >
            关闭
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </>
  );
}

// 导出快捷键提示组件
export function ShortcutHint({ shortcut, description }: { shortcut: string; description: string }) {
  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
      <Chip
        label={shortcut}
        size="small"
        sx={{
          bgcolor: 'rgba(255,255,255,0.1)',
          color: 'text.secondary',
          fontFamily: 'monospace',
          fontSize: '10px',
          height: 16
        }}
      />
      <Typography variant="caption" color="text.secondary">
        {description}
      </Typography>
    </Box>
  );
}