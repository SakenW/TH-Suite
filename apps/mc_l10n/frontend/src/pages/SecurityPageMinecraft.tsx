import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  LinearProgress,
  Alert,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Tooltip,
  Paper,
  Divider,
  Badge,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  InputAdornment,
  Checkbox
} from '@mui/material';
import {
  Shield,
  Lock,
  Key,
  User,
  Users,
  Settings,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  Eye,
  EyeOff,
  Fingerprint,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  UserCheck,
  UserX,
  FileKey,
  Database,
  Activity,
  History,
  Download,
  Upload,
  RefreshCw,
  Trash2,
  Edit,
  Save,
  Copy,
  MoreVertical,
  LogOut,
  UserPlus,
  KeyRound,
  Unlock,
  LockKeyhole,
  ShieldBan,
  ShieldQuestion
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MinecraftButton, 
  MinecraftCard, 
  MinecraftProgress, 
  MinecraftLoader,
  MinecraftBlock
} from '@components/minecraft';
import { minecraftColors } from '../theme/minecraftTheme';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'developer' | 'translator' | 'viewer';
  status: 'active' | 'inactive' | 'suspended';
  lastLogin?: Date;
  permissions: string[];
  twoFactorEnabled: boolean;
}

interface Permission {
  id: string;
  name: string;
  description: string;
  category: 'system' | 'project' | 'translation' | 'data';
  risk: 'low' | 'medium' | 'high';
}

interface SecurityLog {
  id: string;
  timestamp: Date;
  userId: string;
  username: string;
  action: string;
  details: string;
  ipAddress: string;
  result: 'success' | 'failure' | 'warning';
}

interface APIKey {
  id: string;
  name: string;
  key: string;
  createdAt: Date;
  lastUsed?: Date;
  expiresAt?: Date;
  permissions: string[];
  status: 'active' | 'expired' | 'revoked';
}

interface EncryptionSettings {
  algorithm: string;
  keyLength: number;
  autoEncrypt: boolean;
  encryptExports: boolean;
  encryptBackups: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function SecurityPageMinecraft() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [users, setUsers] = useState<User[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [securityLogs, setSecurityLogs] = useState<SecurityLog[]>([]);
  const [apiKeys, setAPIKeys] = useState<APIKey[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [apiKeyDialogOpen, setApiKeyDialogOpen] = useState(false);
  const [showApiKey, setShowApiKey] = useState<string | null>(null);
  const [encryptionSettings, setEncryptionSettings] = useState<EncryptionSettings>({
    algorithm: 'AES-256',
    keyLength: 256,
    autoEncrypt: true,
    encryptExports: true,
    encryptBackups: true
  });
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // 模拟数据
  useEffect(() => {
    const mockUsers: User[] = [
      {
        id: '1',
        username: 'admin',
        email: 'admin@th-suite.com',
        role: 'admin',
        status: 'active',
        lastLogin: new Date('2024-03-21T10:30:00'),
        permissions: ['all'],
        twoFactorEnabled: true
      },
      {
        id: '2',
        username: 'translator1',
        email: 'translator1@th-suite.com',
        role: 'translator',
        status: 'active',
        lastLogin: new Date('2024-03-21T09:15:00'),
        permissions: ['translate', 'export', 'view'],
        twoFactorEnabled: false
      },
      {
        id: '3',
        username: 'viewer1',
        email: 'viewer@th-suite.com',
        role: 'viewer',
        status: 'inactive',
        lastLogin: new Date('2024-03-15T14:20:00'),
        permissions: ['view'],
        twoFactorEnabled: false
      }
    ];

    const mockPermissions: Permission[] = [
      {
        id: 'p1',
        name: '系统管理',
        description: '完全控制系统设置和配置',
        category: 'system',
        risk: 'high'
      },
      {
        id: 'p2',
        name: '项目管理',
        description: '创建、编辑和删除项目',
        category: 'project',
        risk: 'medium'
      },
      {
        id: 'p3',
        name: '翻译编辑',
        description: '编辑和提交翻译内容',
        category: 'translation',
        risk: 'low'
      },
      {
        id: 'p4',
        name: '数据导出',
        description: '导出翻译数据和报告',
        category: 'data',
        risk: 'medium'
      },
      {
        id: 'p5',
        name: '数据删除',
        description: '永久删除数据和备份',
        category: 'data',
        risk: 'high'
      }
    ];

    const mockLogs: SecurityLog[] = [
      {
        id: 'l1',
        timestamp: new Date('2024-03-21T10:30:00'),
        userId: '1',
        username: 'admin',
        action: '用户登录',
        details: '成功登录系统',
        ipAddress: '192.168.1.100',
        result: 'success'
      },
      {
        id: 'l2',
        timestamp: new Date('2024-03-21T10:25:00'),
        userId: '2',
        username: 'translator1',
        action: '导出数据',
        details: '导出ATM10翻译包',
        ipAddress: '192.168.1.101',
        result: 'success'
      },
      {
        id: 'l3',
        timestamp: new Date('2024-03-21T10:20:00'),
        userId: '0',
        username: 'unknown',
        action: '登录失败',
        details: '密码错误，尝试登录用户 admin',
        ipAddress: '203.0.113.45',
        result: 'failure'
      }
    ];

    const mockApiKeys: APIKey[] = [
      {
        id: 'k1',
        name: 'CI/CD Pipeline',
        key: 'sk_live_xxxxxxxxxxxxxxxxxxx',
        createdAt: new Date('2024-03-01'),
        lastUsed: new Date('2024-03-21T08:00:00'),
        permissions: ['read', 'export'],
        status: 'active'
      },
      {
        id: 'k2',
        name: 'Mobile App',
        key: 'sk_test_yyyyyyyyyyyyyyyyyyy',
        createdAt: new Date('2024-02-15'),
        expiresAt: new Date('2024-04-15'),
        permissions: ['read', 'write', 'export'],
        status: 'active'
      }
    ];

    setUsers(mockUsers);
    setPermissions(mockPermissions);
    setSecurityLogs(mockLogs);
    setAPIKeys(mockApiKeys);
  }, []);

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return minecraftColors.redstoneRed;
      case 'developer':
        return minecraftColors.diamondBlue;
      case 'translator':
        return minecraftColors.emerald;
      case 'viewer':
        return minecraftColors.iron;
      default:
        return '#FFFFFF';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return minecraftColors.redstoneRed;
      case 'medium':
        return minecraftColors.goldYellow;
      case 'low':
        return minecraftColors.emerald;
      default:
        return '#FFFFFF';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return minecraftColors.emerald;
      case 'inactive':
        return minecraftColors.iron;
      case 'suspended':
      case 'expired':
      case 'revoked':
        return minecraftColors.redstoneRed;
      default:
        return '#FFFFFF';
    }
  };

  const handleChangePassword = () => {
    if (newPassword === confirmPassword && newPassword.length >= 8) {
      // 保存新密码逻辑
      setPasswordDialogOpen(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    }
  };

  const handleRevokeApiKey = (keyId: string) => {
    setAPIKeys(keys => 
      keys.map(k => k.id === keyId ? { ...k, status: 'revoked' } : k)
    );
  };

  const handleToggle2FA = (userId: string) => {
    setUsers(users => 
      users.map(u => u.id === userId ? { ...u, twoFactorEnabled: !u.twoFactorEnabled } : u)
    );
  };

  const passwordStrength = (password: string): number => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    return (strength / 5) * 100;
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* 页面标题 */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 2
          }}
        >
          <MinecraftBlock type="gold" size={32} animated />
          安全设置
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          管理用户权限、数据加密和系统安全策略
        </Typography>
      </Box>

      {/* 安全状态概览 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="enchantment">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <ShieldCheck size={20} style={{ color: minecraftColors.emerald }} />
                <Typography variant="body2" color="text.secondary">
                  安全等级
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace', color: minecraftColors.emerald }}>
                高
              </Typography>
              <Typography variant="caption" color="text.secondary">
                所有安全功能已启用
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="enchantment">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Users size={20} style={{ color: minecraftColors.diamondBlue }} />
                <Typography variant="body2" color="text.secondary">
                  活跃用户
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {users.filter(u => u.status === 'active').length} / {users.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {users.filter(u => u.twoFactorEnabled).length} 人启用双因素
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="enchantment">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Key size={20} style={{ color: minecraftColors.goldYellow }} />
                <Typography variant="body2" color="text.secondary">
                  API 密钥
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {apiKeys.filter(k => k.status === 'active').length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                活跃密钥
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="enchantment">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Activity size={20} style={{ color: minecraftColors.redstoneRed }} />
                <Typography variant="body2" color="text.secondary">
                  安全事件
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {securityLogs.filter(l => l.result === 'failure').length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                最近24小时
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
      </Grid>

      {/* 安全管理选项卡 */}
      <Paper
        sx={{
          bgcolor: 'rgba(15, 23, 42, 0.8)',
          border: '2px solid #2A2A4E',
          borderRadius: 0
        }}
      >
        <Tabs
          value={selectedTab}
          onChange={(e, v) => setSelectedTab(v)}
          sx={{
            borderBottom: '2px solid #2A2A4E',
            '& .MuiTab-root': {
              fontFamily: '"Minecraft", monospace',
              fontSize: '12px'
            }
          }}
        >
          <Tab label="用户管理" icon={<Users size={16} />} iconPosition="start" />
          <Tab label="权限控制" icon={<Shield size={16} />} iconPosition="start" />
          <Tab label="数据加密" icon={<Lock size={16} />} iconPosition="start" />
          <Tab label="API密钥" icon={<Key size={16} />} iconPosition="start" />
          <Tab label="审计日志" icon={<History size={16} />} iconPosition="start" />
          <Tab label="安全策略" icon={<Settings size={16} />} iconPosition="start" />
        </Tabs>

        {/* 用户管理 */}
        <TabPanel value={selectedTab} index={0}>
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                用户列表
              </Typography>
              <MinecraftButton
                minecraftStyle="emerald"
                startIcon={<UserPlus size={16} />}
                onClick={() => setUserDialogOpen(true)}
              >
                添加用户
              </MinecraftButton>
            </Box>

            <TableContainer component={Paper} sx={{ bgcolor: 'transparent', border: '1px solid #2A2A4E' }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>用户名</TableCell>
                    <TableCell>邮箱</TableCell>
                    <TableCell>角色</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>双因素认证</TableCell>
                    <TableCell>最后登录</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <User size={16} />
                          {user.username}
                        </Box>
                      </TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Chip
                          label={user.role}
                          size="small"
                          sx={{
                            bgcolor: getRoleColor(user.role),
                            color: '#FFFFFF'
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={user.status}
                          size="small"
                          sx={{
                            bgcolor: getStatusColor(user.status),
                            color: '#FFFFFF'
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={user.twoFactorEnabled}
                          onChange={() => handleToggle2FA(user.id)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {user.lastLogin?.toLocaleString() || '从未'}
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedUser(user);
                              setUserDialogOpen(true);
                            }}
                          >
                            <Edit size={16} />
                          </IconButton>
                          <IconButton size="small">
                            <Key size={16} />
                          </IconButton>
                          <IconButton size="small" sx={{ color: 'error.main' }}>
                            <UserX size={16} />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </TabPanel>

        {/* 权限控制 */}
        <TabPanel value={selectedTab} index={1}>
          <Box sx={{ p: 3 }}>
            <Alert
              severity="info"
              sx={{
                mb: 3,
                bgcolor: 'rgba(33, 150, 243, 0.1)',
                border: '1px solid #2196F3'
              }}
            >
              权限控制基于角色的访问控制（RBAC）模型，确保用户只能访问其职责所需的功能
            </Alert>

            <Grid container spacing={3}>
              {permissions.map((permission) => (
                <Grid item xs={12} md={6} key={permission.id}>
                  <MinecraftCard variant="inventory">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Box>
                          <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                            {permission.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {permission.description}
                          </Typography>
                        </Box>
                        <Chip
                          label={permission.risk}
                          size="small"
                          sx={{
                            bgcolor: getRiskColor(permission.risk),
                            color: '#FFFFFF'
                          }}
                        />
                      </Box>

                      <Divider sx={{ my: 2 }} />

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        分配给角色:
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {permission.risk === 'high' && (
                          <Chip label="Admin" size="small" sx={{ bgcolor: getRoleColor('admin'), color: '#FFF' }} />
                        )}
                        {(permission.risk === 'high' || permission.risk === 'medium') && (
                          <Chip label="Developer" size="small" sx={{ bgcolor: getRoleColor('developer'), color: '#FFF' }} />
                        )}
                        {permission.category === 'translation' && (
                          <Chip label="Translator" size="small" sx={{ bgcolor: getRoleColor('translator'), color: '#FFF' }} />
                        )}
                        {permission.risk === 'low' && (
                          <Chip label="Viewer" size="small" sx={{ bgcolor: getRoleColor('viewer'), color: '#FFF' }} />
                        )}
                      </Box>
                    </CardContent>
                  </MinecraftCard>
                </Grid>
              ))}
            </Grid>
          </Box>
        </TabPanel>

        {/* 数据加密 */}
        <TabPanel value={selectedTab} index={2}>
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      加密设置
                    </Typography>
                    
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>加密算法</InputLabel>
                      <Select
                        value={encryptionSettings.algorithm}
                        label="加密算法"
                        onChange={(e) => setEncryptionSettings({
                          ...encryptionSettings,
                          algorithm: e.target.value
                        })}
                      >
                        <MenuItem value="AES-256">AES-256-GCM</MenuItem>
                        <MenuItem value="AES-128">AES-128-GCM</MenuItem>
                        <MenuItem value="ChaCha20">ChaCha20-Poly1305</MenuItem>
                      </Select>
                    </FormControl>

                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>密钥长度</InputLabel>
                      <Select
                        value={encryptionSettings.keyLength}
                        label="密钥长度"
                        onChange={(e) => setEncryptionSettings({
                          ...encryptionSettings,
                          keyLength: Number(e.target.value)
                        })}
                      >
                        <MenuItem value={128}>128 位</MenuItem>
                        <MenuItem value={256}>256 位</MenuItem>
                        <MenuItem value={512}>512 位</MenuItem>
                      </Select>
                    </FormControl>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={encryptionSettings.autoEncrypt}
                          onChange={(e) => setEncryptionSettings({
                            ...encryptionSettings,
                            autoEncrypt: e.target.checked
                          })}
                        />
                      }
                      label="自动加密新数据"
                      sx={{ mb: 1 }}
                    />

                    <FormControlLabel
                      control={
                        <Switch
                          checked={encryptionSettings.encryptExports}
                          onChange={(e) => setEncryptionSettings({
                            ...encryptionSettings,
                            encryptExports: e.target.checked
                          })}
                        />
                      }
                      label="加密导出文件"
                      sx={{ mb: 1 }}
                    />

                    <FormControlLabel
                      control={
                        <Switch
                          checked={encryptionSettings.encryptBackups}
                          onChange={(e) => setEncryptionSettings({
                            ...encryptionSettings,
                            encryptBackups: e.target.checked
                          })}
                        />
                      }
                      label="加密备份文件"
                    />
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12} md={6}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      密钥管理
                    </Typography>
                    
                    <List>
                      <ListItem>
                        <ListItemIcon>
                          <FileKey size={20} style={{ color: minecraftColors.goldYellow }} />
                        </ListItemIcon>
                        <ListItemText
                          primary="主密钥"
                          secondary="最后更新: 2024-03-01"
                        />
                        <ListItemSecondaryAction>
                          <MinecraftButton
                            size="small"
                            minecraftStyle="gold"
                            startIcon={<RefreshCw size={14} />}
                          >
                            轮换
                          </MinecraftButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                      
                      <ListItem>
                        <ListItemIcon>
                          <Database size={20} style={{ color: minecraftColors.iron }} />
                        </ListItemIcon>
                        <ListItemText
                          primary="数据库密钥"
                          secondary="AES-256 加密"
                        />
                        <ListItemSecondaryAction>
                          <IconButton edge="end">
                            <Settings size={16} />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>

                      <ListItem>
                        <ListItemIcon>
                          <Shield size={20} style={{ color: minecraftColors.emerald }} />
                        </ListItemIcon>
                        <ListItemText
                          primary="传输加密"
                          secondary="TLS 1.3 已启用"
                        />
                        <ListItemSecondaryAction>
                          <CheckCircle size={20} style={{ color: minecraftColors.emerald }} />
                        </ListItemSecondaryAction>
                      </ListItem>
                    </List>

                    <Divider sx={{ my: 2 }} />

                    <MinecraftButton
                      fullWidth
                      minecraftStyle="diamond"
                      startIcon={<Download size={16} />}
                    >
                      导出密钥备份
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Alert
                severity="warning"
                sx={{
                  bgcolor: 'rgba(255, 152, 0, 0.1)',
                  border: '1px solid #FF9800'
                }}
              >
                <strong>重要：</strong> 密钥轮换将影响所有加密数据的访问。请确保在执行此操作前备份所有重要数据。
              </Alert>
            </Box>
          </Box>
        </TabPanel>

        {/* API密钥 */}
        <TabPanel value={selectedTab} index={3}>
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                API 密钥管理
              </Typography>
              <MinecraftButton
                minecraftStyle="emerald"
                startIcon={<Key size={16} />}
                onClick={() => setApiKeyDialogOpen(true)}
              >
                创建新密钥
              </MinecraftButton>
            </Box>

            <Grid container spacing={2}>
              {apiKeys.map((apiKey) => (
                <Grid item xs={12} key={apiKey.id}>
                  <MinecraftCard variant="inventory">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Box>
                          <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                            {apiKey.name}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                            <TextField
                              size="small"
                              value={showApiKey === apiKey.id ? apiKey.key : '••••••••••••••••••••'}
                              InputProps={{
                                readOnly: true,
                                endAdornment: (
                                  <InputAdornment position="end">
                                    <IconButton
                                      edge="end"
                                      onClick={() => setShowApiKey(
                                        showApiKey === apiKey.id ? null : apiKey.id
                                      )}
                                    >
                                      {showApiKey === apiKey.id ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </IconButton>
                                  </InputAdornment>
                                ),
                                sx: { fontFamily: 'monospace', fontSize: '12px' }
                              }}
                              sx={{ width: 300 }}
                            />
                            <IconButton size="small">
                              <Copy size={16} />
                            </IconButton>
                          </Box>
                        </Box>
                        <Chip
                          label={apiKey.status}
                          size="small"
                          sx={{
                            bgcolor: getStatusColor(apiKey.status),
                            color: '#FFFFFF'
                          }}
                        />
                      </Box>

                      <Grid container spacing={2}>
                        <Grid item xs={12} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            创建时间
                          </Typography>
                          <Typography variant="body2">
                            {apiKey.createdAt.toLocaleDateString()}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            最后使用
                          </Typography>
                          <Typography variant="body2">
                            {apiKey.lastUsed?.toLocaleString() || '从未'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            过期时间
                          </Typography>
                          <Typography variant="body2">
                            {apiKey.expiresAt?.toLocaleDateString() || '永不过期'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            权限
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {apiKey.permissions.map(p => (
                              <Chip key={p} label={p} size="small" />
                            ))}
                          </Box>
                        </Grid>
                      </Grid>

                      <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                        <MinecraftButton
                          size="small"
                          minecraftStyle="stone"
                          startIcon={<Edit size={14} />}
                        >
                          编辑
                        </MinecraftButton>
                        <MinecraftButton
                          size="small"
                          minecraftStyle="redstone"
                          startIcon={<ShieldBan size={14} />}
                          onClick={() => handleRevokeApiKey(apiKey.id)}
                          disabled={apiKey.status !== 'active'}
                        >
                          撤销
                        </MinecraftButton>
                      </Box>
                    </CardContent>
                  </MinecraftCard>
                </Grid>
              ))}
            </Grid>
          </Box>
        </TabPanel>

        {/* 审计日志 */}
        <TabPanel value={selectedTab} index={4}>
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                安全审计日志
              </Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  size="small"
                  placeholder="搜索日志..."
                  InputProps={{
                    startAdornment: <Search size={16} style={{ marginRight: 8 }} />
                  }}
                />
                <MinecraftButton
                  minecraftStyle="stone"
                  startIcon={<Download size={16} />}
                >
                  导出日志
                </MinecraftButton>
              </Box>
            </Box>

            <TableContainer component={Paper} sx={{ bgcolor: 'transparent', border: '1px solid #2A2A4E' }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>时间</TableCell>
                    <TableCell>用户</TableCell>
                    <TableCell>操作</TableCell>
                    <TableCell>详情</TableCell>
                    <TableCell>IP地址</TableCell>
                    <TableCell>结果</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {securityLogs.map((log) => (
                    <TableRow key={log.id} hover>
                      <TableCell>
                        <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                          {log.timestamp.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>{log.username}</TableCell>
                      <TableCell>{log.action}</TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {log.details}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                          {log.ipAddress}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={log.result}
                          size="small"
                          icon={
                            log.result === 'success' ? <CheckCircle size={14} /> :
                            log.result === 'failure' ? <XCircle size={14} /> :
                            <AlertCircle size={14} />
                          }
                          sx={{
                            bgcolor: log.result === 'success' ? minecraftColors.emerald :
                                    log.result === 'failure' ? minecraftColors.redstoneRed :
                                    minecraftColors.goldYellow,
                            color: '#FFFFFF'
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </TabPanel>

        {/* 安全策略 */}
        <TabPanel value={selectedTab} index={5}>
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      密码策略
                    </Typography>
                    
                    <List>
                      <ListItem>
                        <ListItemText primary="最小密码长度" />
                        <TextField
                          size="small"
                          type="number"
                          defaultValue="8"
                          sx={{ width: 80 }}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="需要大小写字母" />
                        <Switch defaultChecked />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="需要数字" />
                        <Switch defaultChecked />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="需要特殊字符" />
                        <Switch defaultChecked />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="密码过期时间（天）" />
                        <TextField
                          size="small"
                          type="number"
                          defaultValue="90"
                          sx={{ width: 80 }}
                        />
                      </ListItem>
                    </List>

                    <Divider sx={{ my: 2 }} />

                    <MinecraftButton
                      fullWidth
                      minecraftStyle="diamond"
                      startIcon={<Lock size={16} />}
                      onClick={() => setPasswordDialogOpen(true)}
                    >
                      修改我的密码
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12} md={6}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      会话管理
                    </Typography>
                    
                    <List>
                      <ListItem>
                        <ListItemText primary="会话超时（分钟）" />
                        <TextField
                          size="small"
                          type="number"
                          defaultValue="30"
                          sx={{ width: 80 }}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="记住登录状态" />
                        <Switch defaultChecked />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="单设备登录" />
                        <Switch />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="登录失败锁定" />
                        <Switch defaultChecked />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary="最大失败次数" />
                        <TextField
                          size="small"
                          type="number"
                          defaultValue="5"
                          sx={{ width: 80 }}
                        />
                      </ListItem>
                    </List>

                    <Divider sx={{ my: 2 }} />

                    <MinecraftButton
                      fullWidth
                      minecraftStyle="redstone"
                      startIcon={<LogOut size={16} />}
                    >
                      登出所有设备
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      其他安全设置
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch defaultChecked />}
                          label="启用双因素认证"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch defaultChecked />}
                          label="IP白名单"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch defaultChecked />}
                          label="异常登录检测"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch />}
                          label="开发者模式"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch defaultChecked />}
                          label="自动安全更新"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch defaultChecked />}
                          label="安全邮件通知"
                        />
                      </Grid>
                    </Grid>

                    <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                      <MinecraftButton
                        minecraftStyle="emerald"
                        startIcon={<Save size={16} />}
                      >
                        保存设置
                      </MinecraftButton>
                      <MinecraftButton
                        minecraftStyle="stone"
                        startIcon={<RefreshCw size={16} />}
                      >
                        重置默认
                      </MinecraftButton>
                    </Box>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>
      </Paper>

      {/* 用户对话框 */}
      <Dialog
        open={userDialogOpen}
        onClose={() => {
          setUserDialogOpen(false);
          setSelectedUser(null);
        }}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#0F172A',
            border: '2px solid #2A2A4E',
            borderRadius: 0
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: '"Minecraft", monospace' }}>
          {selectedUser ? '编辑用户' : '添加新用户'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="用户名"
                defaultValue={selectedUser?.username}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="邮箱"
                type="email"
                defaultValue={selectedUser?.email}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>角色</InputLabel>
                <Select
                  defaultValue={selectedUser?.role || 'viewer'}
                  label="角色"
                >
                  <MenuItem value="admin">管理员</MenuItem>
                  <MenuItem value="developer">开发者</MenuItem>
                  <MenuItem value="translator">翻译员</MenuItem>
                  <MenuItem value="viewer">查看者</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            {!selectedUser && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="初始密码"
                  type="password"
                />
              </Grid>
            )}
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked={selectedUser?.twoFactorEnabled} />}
                label="启用双因素认证"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => {
              setUserDialogOpen(false);
              setSelectedUser(null);
            }}
          >
            取消
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="emerald"
            onClick={() => {
              setUserDialogOpen(false);
              setSelectedUser(null);
            }}
          >
            保存
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* API密钥对话框 */}
      <Dialog
        open={apiKeyDialogOpen}
        onClose={() => setApiKeyDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#0F172A',
            border: '2px solid #2A2A4E',
            borderRadius: 0
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: '"Minecraft", monospace' }}>
          创建新的API密钥
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="密钥名称"
                placeholder="例如: CI/CD Pipeline"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>过期时间</InputLabel>
                <Select defaultValue="never" label="过期时间">
                  <MenuItem value="never">永不过期</MenuItem>
                  <MenuItem value="30">30天</MenuItem>
                  <MenuItem value="90">90天</MenuItem>
                  <MenuItem value="365">1年</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="body2" sx={{ mb: 1 }}>
                权限设置
              </Typography>
              <FormControlLabel
                control={<Checkbox defaultChecked />}
                label="读取权限"
              />
              <FormControlLabel
                control={<Checkbox />}
                label="写入权限"
              />
              <FormControlLabel
                control={<Checkbox />}
                label="删除权限"
              />
              <FormControlLabel
                control={<Checkbox defaultChecked />}
                label="导出权限"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setApiKeyDialogOpen(false)}
          >
            取消
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="emerald"
            onClick={() => setApiKeyDialogOpen(false)}
          >
            创建
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* 修改密码对话框 */}
      <Dialog
        open={passwordDialogOpen}
        onClose={() => setPasswordDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#0F172A',
            border: '2px solid #2A2A4E',
            borderRadius: 0
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: '"Minecraft", monospace' }}>
          修改密码
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="当前密码"
                type={showPassword ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        edge="end"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="新密码"
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                helperText="至少8个字符，包含大小写字母、数字和特殊字符"
              />
              {newPassword && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    密码强度
                  </Typography>
                  <MinecraftProgress
                    variant="experience"
                    value={passwordStrength(newPassword)}
                    sx={{ mt: 0.5 }}
                  />
                </Box>
              )}
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="确认新密码"
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={confirmPassword !== '' && confirmPassword !== newPassword}
                helperText={confirmPassword !== '' && confirmPassword !== newPassword ? '密码不匹配' : ''}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => {
              setPasswordDialogOpen(false);
              setCurrentPassword('');
              setNewPassword('');
              setConfirmPassword('');
            }}
          >
            取消
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="emerald"
            onClick={handleChangePassword}
            disabled={!currentPassword || !newPassword || newPassword !== confirmPassword}
          >
            确认修改
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// 添加缺失的 Search 图标组件
function Search({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}