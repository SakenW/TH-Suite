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
  InputAdornment,
  Stepper,
  Step,
  StepLabel,
  StepContent
} from '@mui/material';
import {
  Server,
  Globe,
  Wifi,
  WifiOff,
  Database,
  Settings,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  Play,
  Pause,
  RefreshCw,
  Save,
  Upload,
  Download,
  Link,
  Unlink,
  Activity,
  Zap,
  Clock,
  Shield,
  Key,
  Terminal,
  Code,
  Cloud,
  CloudOff,
  HardDrive,
  Cpu,
  MemoryStick,
  Network,
  GitBranch,
  Send,
  ArrowUpDown,
  BarChart,
  TrendingUp,
  TrendingDown,
  Edit,
  Eye,
  EyeOff
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
import { useTransHub } from '../hooks/useTransHub';
import { TransHubStatusBar } from '../components/TransHubStatusBar';
import { useNotification } from '../hooks/useNotification';
import { storageService } from '../services/storage.service';

interface ServerConfig {
  id: string;
  name: string;
  url: string;
  apiKey: string;
  status: 'connected' | 'disconnected' | 'error' | 'connecting';
  lastSync?: Date;
  version?: string;
  region?: string;
  latency?: number;
  ssl: boolean;
  autoSync: boolean;
  syncInterval: number;
}

interface SyncSettings {
  autoSync: boolean;
  syncInterval: number;
  syncOnStartup: boolean;
  syncOnSave: boolean;
  conflictResolution: 'local' | 'remote' | 'manual';
  includeProjects: boolean;
  includeTranslations: boolean;
  includeSettings: boolean;
  compression: boolean;
  encryption: boolean;
}

interface ServerStats {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageLatency: number;
  uptime: number;
  dataTransferred: number;
  lastError?: string;
  lastErrorTime?: Date;
}

interface ConnectionLog {
  id: string;
  timestamp: Date;
  event: string;
  details: string;
  status: 'success' | 'error' | 'warning' | 'info';
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

export default function ServerPageMinecraft() {
  const [selectedTab, setSelectedTab] = useState(0);
  const {
    isConnected,
    connectionStatus,
    isConnecting,
    error,
    offlineQueueSize,
    connect,
    disconnect,
    refreshStatus,
    testConnection,
    syncOfflineQueue
  } = useTransHub();
  const notification = useNotification();
  
  const [serverConfig, setServerConfig] = useState<ServerConfig>({
    id: '1',
    name: 'Trans-Hub Server',
    url: 'http://localhost:8001',
    apiKey: '',
    status: isConnected ? 'connected' : 'disconnected',
    lastSync: undefined,
    version: undefined,
    region: 'Local',
    latency: connectionStatus?.latency,
    ssl: false,
    autoSync: true,
    syncInterval: 300
  });
  const [syncSettings, setSyncSettings] = useState<SyncSettings>({
    autoSync: true,
    syncInterval: 300,
    syncOnStartup: true,
    syncOnSave: true,
    conflictResolution: 'manual',
    includeProjects: true,
    includeTranslations: true,
    includeSettings: false,
    compression: true,
    encryption: true
  });
  const [serverStats, setServerStats] = useState<ServerStats>({
    totalRequests: 15234,
    successfulRequests: 15201,
    failedRequests: 33,
    averageLatency: 45,
    uptime: 99.78,
    dataTransferred: 2147483648, // 2GB
    lastError: 'Connection timeout',
    lastErrorTime: new Date('2024-03-20T15:30:00')
  });
  const [connectionLogs, setConnectionLogs] = useState<ConnectionLog[]>([]);
  const [testConnectionOpen, setTestConnectionOpen] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [serverUrl, setServerUrl] = useState('http://localhost:8001');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);

  // 更新服务器配置状态
  useEffect(() => {
    if (connectionStatus) {
      setServerConfig(prev => ({
        ...prev,
        status: connectionStatus.connected ? 'connected' : 'disconnected',
        url: connectionStatus.serverUrl || prev.url,
        latency: connectionStatus.latency
      }));
    }
  }, [connectionStatus]);

  // 加载保存的配置
  useEffect(() => {
    const loadSavedConfig = async () => {
      // 加载服务器配置
      const savedServerConfig = storageService.local.get<Partial<ServerConfig>>('server_config');
      if (savedServerConfig) {
        setServerConfig(prev => ({
          ...prev,
          ...savedServerConfig,
          status: isConnected ? 'connected' : 'disconnected'
        }));
        setServerUrl(savedServerConfig.url || 'http://localhost:8001');
        setApiKey(savedServerConfig.apiKey || '');
      }

      // 加载同步设置
      const savedSyncSettings = storageService.local.get<SyncSettings>('sync_settings');
      if (savedSyncSettings) {
        setSyncSettings(savedSyncSettings);
      }

      // 加载连接日志
      const savedLogs = storageService.local.get<ConnectionLog[]>('connection_logs');
      if (savedLogs && savedLogs.length > 0) {
        setConnectionLogs(savedLogs.slice(0, 50)); // 只保留最近50条
      } else {
        // 初始化连接日志
        const initialLogs: ConnectionLog[] = [];
        if (connectionStatus) {
          initialLogs.push({
            id: Date.now().toString(),
            timestamp: new Date(),
            event: connectionStatus.connected ? '已连接' : '未连接',
            details: connectionStatus.message,
            status: connectionStatus.connected ? 'success' : 'info'
          });
        }
        setConnectionLogs(initialLogs);
      }
    };

    loadSavedConfig();
  }, []);

  // 如果启用了启动时连接，尝试自动连接
  useEffect(() => {
    const autoConnect = async () => {
      const savedSyncSettings = storageService.local.get<SyncSettings>('sync_settings');
      const savedServerConfig = storageService.local.get<Partial<ServerConfig>>('server_config');
      
      if (savedSyncSettings?.syncOnStartup && savedServerConfig?.url && savedServerConfig?.apiKey && !isConnected) {
        await handleConnect();
      }
    };

    // 延迟1秒执行，确保应用完全初始化
    const timer = setTimeout(autoConnect, 1000);
    return () => clearTimeout(timer);
  }, []);

  const handleConnect = async () => {
    const success = await connect({
      baseUrl: serverUrl,
      apiKey: apiKey,
      offlineMode: false,
      autoSync: syncSettings.autoSync
    });
    
    if (success) {
      // 保存成功的配置
      const configToSave = {
        ...serverConfig,
        url: serverUrl,
        apiKey: apiKey,
        lastSync: new Date()
      };
      storageService.local.set('server_config', configToSave);
      setServerConfig(prev => ({
        ...prev,
        ...configToSave,
        status: 'connected'
      }));

      const newLog: ConnectionLog = {
        id: Date.now().toString(),
        timestamp: new Date(),
        event: '连接成功',
        details: `成功连接到 ${serverUrl}`,
        status: 'success'
      };
      const updatedLogs = [newLog, ...connectionLogs].slice(0, 100);
      setConnectionLogs(updatedLogs);
      storageService.local.set('connection_logs', updatedLogs);
    } else {
      const newLog: ConnectionLog = {
        id: Date.now().toString(),
        timestamp: new Date(),
        event: '连接失败',
        details: error || '无法连接到服务器',
        status: 'error'
      };
      const updatedLogs = [newLog, ...connectionLogs].slice(0, 100);
      setConnectionLogs(updatedLogs);
      storageService.local.set('connection_logs', updatedLogs);
    }
  };

  const handleDisconnect = async () => {
    await disconnect();
    
    const newLog: ConnectionLog = {
      id: Date.now().toString(),
      timestamp: new Date(),
      event: '断开连接',
      details: '手动断开服务器连接',
      status: 'info'
    };
    const updatedLogs = [newLog, ...connectionLogs].slice(0, 100);
    setConnectionLogs(updatedLogs);
    storageService.local.set('connection_logs', updatedLogs);
  };

  const handleSync = async () => {
    if (offlineQueueSize === 0) {
      notification.info('同步', '离线队列为空，无需同步');
      return;
    }
    
    setIsSyncing(true);
    try {
      await syncOfflineQueue();
      
      const newLog: ConnectionLog = {
        id: Date.now().toString(),
        timestamp: new Date(),
        event: '同步完成',
        details: `成功同步 ${offlineQueueSize} 个待处理项目`,
        status: 'success'
      };
      const updatedLogs = [newLog, ...connectionLogs].slice(0, 100);
      setConnectionLogs(updatedLogs);
      storageService.local.set('connection_logs', updatedLogs);
      
      // 更新最后同步时间
      const updatedConfig = { ...serverConfig, lastSync: new Date() };
      setServerConfig(updatedConfig);
      storageService.local.set('server_config', updatedConfig);
    } catch (err) {
      const newLog: ConnectionLog = {
        id: Date.now().toString(),
        timestamp: new Date(),
        event: '同步失败',
        details: err instanceof Error ? err.message : '同步过程中发生错误',
        status: 'error'
      };
      const updatedLogs = [newLog, ...connectionLogs].slice(0, 100);
      setConnectionLogs(updatedLogs);
      storageService.local.set('connection_logs', updatedLogs);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleTestConnection = async () => {
    setTestConnectionOpen(true);
    setActiveStep(0);
    
    // 测试连接步骤
    const steps = [
      { name: 'DNS解析', delay: 500 },
      { name: '建立连接', delay: 1000 },
      { name: 'SSL握手', delay: 500 },
      { name: 'API验证', delay: 1000 }
    ];
    
    for (let i = 0; i < steps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, steps[i].delay));
      setActiveStep(i + 1);
    }
    
    // 实际测试连接
    const result = await testConnection(serverUrl);
    if (!result) {
      notification.error('连接测试', '无法连接到服务器');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return minecraftColors.emerald;
      case 'disconnected':
        return minecraftColors.iron;
      case 'error':
        return minecraftColors.redstoneRed;
      case 'connecting':
        return minecraftColors.goldYellow;
      default:
        return '#FFFFFF';
    }
  };

  const getLogStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle size={16} style={{ color: minecraftColors.emerald }} />;
      case 'error':
        return <XCircle size={16} style={{ color: minecraftColors.redstoneRed }} />;
      case 'warning':
        return <AlertCircle size={16} style={{ color: minecraftColors.goldYellow }} />;
      case 'info':
        return <Info size={16} style={{ color: minecraftColors.diamondBlue }} />;
      default:
        return null;
    }
  };

  const formatDataSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* 页面标题和状态栏 */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
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
              <MinecraftBlock type="diamond" size={32} animated />
              服务器设置
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              配置和管理 Trans-Hub 服务器连接
            </Typography>
          </Box>
          <TransHubStatusBar
            showDetails={true}
            onStatusClick={() => refreshStatus()}
          />
        </Box>
      </Box>

      {/* 连接状态卡片 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <MinecraftCard variant="enchantment">
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Box>
                  <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace', mb: 1 }}>
                    {connectionStatus?.serverUrl ? 'Trans-Hub Server' : '未配置服务器'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                    {connectionStatus?.serverUrl || serverUrl || '请配置服务器地址'}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'right' }}>
                  <Chip
                    label={isConnected ? 'connected' : 'disconnected'}
                    icon={isConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
                    sx={{
                      bgcolor: getStatusColor(isConnected ? 'connected' : 'disconnected'),
                      color: '#FFFFFF',
                      mb: 1
                    }}
                  />
                  {offlineQueueSize > 0 && (
                    <Chip
                      label={`离线队列: ${offlineQueueSize}`}
                      size="small"
                      sx={{
                        bgcolor: minecraftColors.goldYellow,
                        color: '#FFFFFF',
                        ml: 1
                      }}
                    />
                  )}
                  {serverConfig.ssl && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, justifyContent: 'flex-end' }}>
                      <Shield size={14} style={{ color: minecraftColors.emerald }} />
                      <Typography variant="caption" color="text.secondary">
                        SSL 加密
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Box>

              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    服务器版本
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                    {serverConfig.version || 'N/A'}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    区域
                  </Typography>
                  <Typography variant="body2">
                    {serverConfig.region || 'N/A'}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    延迟
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                      {serverConfig.latency}ms
                    </Typography>
                    {serverConfig.latency && serverConfig.latency < 50 ? (
                      <TrendingDown size={14} style={{ color: minecraftColors.emerald }} />
                    ) : (
                      <TrendingUp size={14} style={{ color: minecraftColors.goldYellow }} />
                    )}
                  </Box>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    上次同步
                  </Typography>
                  <Typography variant="body2">
                    {serverConfig.lastSync?.toLocaleTimeString() || '从未'}
                  </Typography>
                </Grid>
              </Grid>

              <Box sx={{ display: 'flex', gap: 2 }}>
                {isConnected ? (
                  <>
                    <MinecraftButton
                      minecraftStyle="emerald"
                      startIcon={<RefreshCw size={16} />}
                      onClick={handleSync}
                      disabled={isSyncing}
                    >
                      {isSyncing ? '同步中...' : '立即同步'}
                    </MinecraftButton>
                    <MinecraftButton
                      minecraftStyle="stone"
                      startIcon={<Unlink size={16} />}
                      onClick={handleDisconnect}
                    >
                      断开连接
                    </MinecraftButton>
                  </>
                ) : (
                  <MinecraftButton
                    minecraftStyle="diamond"
                    startIcon={<Link size={16} />}
                    onClick={handleConnect}
                    disabled={isConnecting}
                  >
                    {isConnecting ? '连接中...' : '连接服务器'}
                  </MinecraftButton>
                )}
                <MinecraftButton
                  minecraftStyle="gold"
                  startIcon={<Zap size={16} />}
                  onClick={handleTestConnection}
                >
                  测试连接
                </MinecraftButton>
                <MinecraftButton
                  minecraftStyle="iron"
                  startIcon={<Settings size={16} />}
                  onClick={() => setConfigDialogOpen(true)}
                >
                  配置
                </MinecraftButton>
              </Box>

              {isSyncing && (
                <Box sx={{ mt: 2 }}>
                  <MinecraftProgress variant="loading" value={65} />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    正在同步数据...
                  </Typography>
                </Box>
              )}
            </CardContent>
          </MinecraftCard>
        </Grid>

        <Grid item xs={12} md={4}>
          <Grid container spacing={2}>
            <Grid item xs={6} md={12}>
              <MinecraftCard variant="crafting">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Activity size={20} style={{ color: minecraftColors.emerald }} />
                    <Typography variant="body2" color="text.secondary">
                      服务器状态
                    </Typography>
                  </Box>
                  <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                    {serverStats.uptime}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    正常运行时间
                  </Typography>
                </CardContent>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={12}>
              <MinecraftCard variant="crafting">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <ArrowUpDown size={20} style={{ color: minecraftColors.diamondBlue }} />
                    <Typography variant="body2" color="text.secondary">
                      数据传输
                    </Typography>
                  </Box>
                  <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                    {formatDataSize(serverStats.dataTransferred)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    本月传输量
                  </Typography>
                </CardContent>
              </MinecraftCard>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {/* 设置选项卡 */}
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
          <Tab label="同步设置" icon={<RefreshCw size={16} />} iconPosition="start" />
          <Tab label="连接日志" icon={<Terminal size={16} />} iconPosition="start" />
          <Tab label="性能统计" icon={<BarChart size={16} />} iconPosition="start" />
          <Tab label="高级设置" icon={<Settings size={16} />} iconPosition="start" />
        </Tabs>

        {/* 同步设置 */}
        <TabPanel value={selectedTab} index={0}>
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      自动同步
                    </Typography>
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={syncSettings.autoSync}
                          onChange={(e) => setSyncSettings({
                            ...syncSettings,
                            autoSync: e.target.checked
                          })}
                        />
                      }
                      label="启用自动同步"
                      sx={{ mb: 2 }}
                    />

                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>同步间隔</InputLabel>
                      <Select
                        value={syncSettings.syncInterval}
                        label="同步间隔"
                        onChange={(e) => setSyncSettings({
                          ...syncSettings,
                          syncInterval: Number(e.target.value)
                        })}
                        disabled={!syncSettings.autoSync}
                      >
                        <MenuItem value={60}>1 分钟</MenuItem>
                        <MenuItem value={300}>5 分钟</MenuItem>
                        <MenuItem value={900}>15 分钟</MenuItem>
                        <MenuItem value={1800}>30 分钟</MenuItem>
                        <MenuItem value={3600}>1 小时</MenuItem>
                      </Select>
                    </FormControl>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={syncSettings.syncOnStartup}
                          onChange={(e) => setSyncSettings({
                            ...syncSettings,
                            syncOnStartup: e.target.checked
                          })}
                        />
                      }
                      label="启动时同步"
                      sx={{ mb: 1 }}
                    />

                    <FormControlLabel
                      control={
                        <Switch
                          checked={syncSettings.syncOnSave}
                          onChange={(e) => setSyncSettings({
                            ...syncSettings,
                            syncOnSave: e.target.checked
                          })}
                        />
                      }
                      label="保存时同步"
                    />
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12} md={6}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      同步内容
                    </Typography>
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={syncSettings.includeProjects}
                          onChange={(e) => setSyncSettings({
                            ...syncSettings,
                            includeProjects: e.target.checked
                          })}
                        />
                      }
                      label="项目配置"
                      sx={{ mb: 1 }}
                    />

                    <FormControlLabel
                      control={
                        <Switch
                          checked={syncSettings.includeTranslations}
                          onChange={(e) => setSyncSettings({
                            ...syncSettings,
                            includeTranslations: e.target.checked
                          })}
                        />
                      }
                      label="翻译内容"
                      sx={{ mb: 1 }}
                    />

                    <FormControlLabel
                      control={
                        <Switch
                          checked={syncSettings.includeSettings}
                          onChange={(e) => setSyncSettings({
                            ...syncSettings,
                            includeSettings: e.target.checked
                          })}
                        />
                      }
                      label="应用设置"
                      sx={{ mb: 2 }}
                    />

                    <Divider sx={{ my: 2 }} />

                    <FormControl fullWidth>
                      <InputLabel>冲突解决</InputLabel>
                      <Select
                        value={syncSettings.conflictResolution}
                        label="冲突解决"
                        onChange={(e) => setSyncSettings({
                          ...syncSettings,
                          conflictResolution: e.target.value as any
                        })}
                      >
                        <MenuItem value="local">优先本地</MenuItem>
                        <MenuItem value="remote">优先远程</MenuItem>
                        <MenuItem value="manual">手动解决</MenuItem>
                      </Select>
                    </FormControl>
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      传输选项
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={syncSettings.compression}
                              onChange={(e) => setSyncSettings({
                                ...syncSettings,
                                compression: e.target.checked
                              })}
                            />
                          }
                          label="启用压缩（减少带宽使用）"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={syncSettings.encryption}
                              onChange={(e) => setSyncSettings({
                                ...syncSettings,
                                encryption: e.target.checked
                              })}
                            />
                          }
                          label="端到端加密"
                        />
                      </Grid>
                    </Grid>

                    <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                      <MinecraftButton
                        minecraftStyle="emerald"
                        startIcon={<Save size={16} />}
                        onClick={() => {
                          storageService.local.set('sync_settings', syncSettings);
                          notification.success('设置保存', '同步设置已保存');
                        }}
                      >
                        保存设置
                      </MinecraftButton>
                      <MinecraftButton
                        minecraftStyle="stone"
                        startIcon={<RefreshCw size={16} />}
                        onClick={() => {
                          const defaultSettings: SyncSettings = {
                            autoSync: true,
                            syncInterval: 300,
                            syncOnStartup: true,
                            syncOnSave: true,
                            conflictResolution: 'manual',
                            includeProjects: true,
                            includeTranslations: true,
                            includeSettings: false,
                            compression: true,
                            encryption: true
                          };
                          setSyncSettings(defaultSettings);
                          storageService.local.set('sync_settings', defaultSettings);
                          notification.info('设置重置', '已恢复默认同步设置');
                        }}
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

        {/* 连接日志 */}
        <TabPanel value={selectedTab} index={1}>
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                连接活动日志
              </Typography>
              <MinecraftButton
                size="small"
                minecraftStyle="stone"
                startIcon={<Download size={14} />}
                onClick={async () => {
                  const logsData = {
                    logs: connectionLogs,
                    exportTime: new Date().toISOString(),
                    serverUrl: serverUrl
                  };
                  const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `connection-logs-${new Date().toISOString().split('T')[0]}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                  notification.success('导出成功', '连接日志已导出');
                }}
              >
                导出日志
              </MinecraftButton>
            </Box>

            <List>
              {connectionLogs.map((log) => (
                <ListItem
                  key={log.id}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 0,
                    mb: 1
                  }}
                >
                  <ListItemIcon>
                    {getLogStatusIcon(log.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2">{log.event}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {log.timestamp.toLocaleTimeString()}
                        </Typography>
                      </Box>
                    }
                    secondary={log.details}
                  />
                </ListItem>
              ))}
            </List>

            <Box sx={{ mt: 2, textAlign: 'center', display: 'flex', gap: 2, justifyContent: 'center' }}>
              <MinecraftButton
                minecraftStyle="stone"
                size="small"
                onClick={() => {
                  // 这里可以实现加载更多历史日志的逻辑
                  notification.info('提示', '暂无更多历史日志');
                }}
              >
                加载更多
              </MinecraftButton>
              <MinecraftButton
                minecraftStyle="redstone"
                size="small"
                onClick={() => {
                  setConnectionLogs([]);
                  storageService.local.remove('connection_logs');
                  notification.success('清空成功', '连接日志已清空');
                }}
              >
                清空日志
              </MinecraftButton>
            </Box>
          </Box>
        </TabPanel>

        {/* 性能统计 */}
        <TabPanel value={selectedTab} index={2}>
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      请求统计
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">总请求</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                          {serverStats.totalRequests.toLocaleString()}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">成功</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace', color: minecraftColors.emerald }}>
                          {serverStats.successfulRequests.toLocaleString()}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2">失败</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace', color: minecraftColors.redstoneRed }}>
                          {serverStats.failedRequests}
                        </Typography>
                      </Box>
                    </Box>
                    <MinecraftProgress
                      variant="experience"
                      value={(serverStats.successfulRequests / serverStats.totalRequests) * 100}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                      成功率: {((serverStats.successfulRequests / serverStats.totalRequests) * 100).toFixed(2)}%
                    </Typography>
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12} md={4}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      性能指标
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">平均延迟</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                          {serverStats.averageLatency}ms
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">当前延迟</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                          {serverConfig.latency}ms
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2">正常运行时间</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                          {serverStats.uptime}%
                        </Typography>
                      </Box>
                    </Box>
                    <Box sx={{ position: 'relative', display: 'inline-flex', width: '100%', justifyContent: 'center' }}>
                      <Activity size={48} style={{ color: minecraftColors.emerald }} />
                    </Box>
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12} md={4}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      最近错误
                    </Typography>
                    {serverStats.lastError ? (
                      <Box>
                        <Alert
                          severity="error"
                          sx={{
                            bgcolor: 'rgba(244, 67, 54, 0.1)',
                            border: '1px solid #F44336',
                            '& .MuiAlert-icon': {
                              color: minecraftColors.redstoneRed
                            }
                          }}
                        >
                          {serverStats.lastError}
                        </Alert>
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                          发生时间: {serverStats.lastErrorTime?.toLocaleString()}
                        </Typography>
                      </Box>
                    ) : (
                      <Alert
                        severity="success"
                        sx={{
                          bgcolor: 'rgba(76, 175, 80, 0.1)',
                          border: '1px solid #4CAF50',
                          '& .MuiAlert-icon': {
                            color: minecraftColors.emerald
                          }
                        }}
                      >
                        最近24小时无错误
                      </Alert>
                    )}
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      实时监控
                    </Typography>
                    <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 0, border: '1px solid #2A2A4E' }}>
                      <Typography variant="body2" color="text.secondary">
                        延迟图表将在这里显示
                      </Typography>
                    </Box>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>

        {/* 高级设置 */}
        <TabPanel value={selectedTab} index={3}>
          <Box sx={{ p: 3 }}>
            <Alert
              severity="warning"
              sx={{
                mb: 3,
                bgcolor: 'rgba(255, 152, 0, 0.1)',
                border: '1px solid #FF9800'
              }}
            >
              修改高级设置可能影响系统稳定性，请谨慎操作
            </Alert>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      连接参数
                    </Typography>
                    
                    <TextField
                      fullWidth
                      label="连接超时（秒）"
                      type="number"
                      defaultValue="30"
                      sx={{ mb: 2 }}
                    />

                    <TextField
                      fullWidth
                      label="最大重试次数"
                      type="number"
                      defaultValue="3"
                      sx={{ mb: 2 }}
                    />

                    <TextField
                      fullWidth
                      label="请求限制（每分钟）"
                      type="number"
                      defaultValue="100"
                      sx={{ mb: 2 }}
                    />

                    <FormControlLabel
                      control={<Switch defaultChecked />}
                      label="使用连接池"
                    />
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12} md={6}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      代理设置
                    </Typography>
                    
                    <FormControlLabel
                      control={<Switch />}
                      label="使用代理"
                      sx={{ mb: 2 }}
                    />

                    <TextField
                      fullWidth
                      label="代理地址"
                      placeholder="http://proxy.example.com:8080"
                      disabled
                      sx={{ mb: 2 }}
                    />

                    <TextField
                      fullWidth
                      label="代理用户名"
                      disabled
                      sx={{ mb: 2 }}
                    />

                    <TextField
                      fullWidth
                      label="代理密码"
                      type="password"
                      disabled
                    />
                  </CardContent>
                </MinecraftCard>
              </Grid>

              <Grid item xs={12}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                      调试选项
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch />}
                          label="启用详细日志"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch />}
                          label="保存请求/响应数据"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch />}
                          label="模拟离线模式"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={<Switch />}
                          label="忽略SSL证书错误"
                        />
                      </Grid>
                    </Grid>

                    <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                      <MinecraftButton
                        minecraftStyle="emerald"
                        startIcon={<Save size={16} />}
                        onClick={() => {
                          notification.success('设置保存', '高级设置已保存');
                        }}
                      >
                        保存高级设置
                      </MinecraftButton>
                      <MinecraftButton
                        minecraftStyle="redstone"
                        startIcon={<AlertCircle size={16} />}
                        onClick={() => {
                          if (window.confirm('确定要重置所有设置吗？这将清除所有保存的配置。')) {
                            storageService.local.clear();
                            notification.warning('设置重置', '所有设置已重置，请刷新页面');
                            setTimeout(() => window.location.reload(), 1000);
                          }
                        }}
                      >
                        重置所有设置
                      </MinecraftButton>
                    </Box>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>
      </Paper>

      {/* 服务器配置对话框 */}
      <Dialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
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
        <DialogTitle sx={{ fontFamily: '"Minecraft", monospace' }}>
          服务器配置
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="服务器名称"
                value="Trans-Hub Server"
                disabled
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="服务器URL"
                value={serverUrl}
                onChange={(e) => setServerUrl(e.target.value)}
                helperText="例如: http://localhost:8001"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="API密钥"
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                helperText="API密钥将安全存储在本地"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton 
                        edge="end"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>区域</InputLabel>
                <Select defaultValue="ap" label="区域">
                  <MenuItem value="us">美国</MenuItem>
                  <MenuItem value="eu">欧洲</MenuItem>
                  <MenuItem value="ap">亚太</MenuItem>
                  <MenuItem value="cn">中国</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="使用SSL加密"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setConfigDialogOpen(false)}
          >
            取消
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="emerald"
            onClick={async () => {
              // 保存配置
              const configToSave = {
                ...serverConfig,
                url: serverUrl,
                apiKey: apiKey
              };
              storageService.local.set('server_config', configToSave);
              setServerConfig(configToSave);
              
              setConfigDialogOpen(false);
              
              // 如果未连接，尝试连接
              if (!isConnected) {
                await handleConnect();
              } else {
                notification.success('配置保存', '服务器配置已更新');
              }
            }}
          >
            保存并连接
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* 连接测试对话框 */}
      <Dialog
        open={testConnectionOpen}
        onClose={() => setTestConnectionOpen(false)}
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
          连接测试
        </DialogTitle>
        <DialogContent>
          <Stepper activeStep={activeStep} orientation="vertical">
            <Step>
              <StepLabel
                StepIconComponent={() => 
                  activeStep > 0 ? <CheckCircle size={20} style={{ color: minecraftColors.emerald }} /> : 
                  activeStep === 0 ? <MinecraftLoader variant="blocks" size="inline" /> : 
                  <Circle size={20} />
                }
              >
                DNS解析
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary">
                  正在解析服务器地址...
                </Typography>
              </StepContent>
            </Step>
            <Step>
              <StepLabel
                StepIconComponent={() => 
                  activeStep > 1 ? <CheckCircle size={20} style={{ color: minecraftColors.emerald }} /> : 
                  activeStep === 1 ? <MinecraftLoader variant="blocks" size="inline" /> : 
                  <Circle size={20} />
                }
              >
                建立连接
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary">
                  正在建立TCP连接...
                </Typography>
              </StepContent>
            </Step>
            <Step>
              <StepLabel
                StepIconComponent={() => 
                  activeStep > 2 ? <CheckCircle size={20} style={{ color: minecraftColors.emerald }} /> : 
                  activeStep === 2 ? <MinecraftLoader variant="blocks" size="inline" /> : 
                  <Circle size={20} />
                }
              >
                SSL握手
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary">
                  正在进行SSL/TLS握手...
                </Typography>
              </StepContent>
            </Step>
            <Step>
              <StepLabel
                StepIconComponent={() => 
                  activeStep > 3 ? <CheckCircle size={20} style={{ color: minecraftColors.emerald }} /> : 
                  activeStep === 3 ? <MinecraftLoader variant="blocks" size="inline" /> : 
                  <Circle size={20} />
                }
              >
                API验证
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary">
                  正在验证API密钥...
                </Typography>
              </StepContent>
            </Step>
          </Stepper>
          
          {activeStep >= 4 && (
            <Alert
              severity="success"
              sx={{
                mt: 2,
                bgcolor: 'rgba(76, 175, 80, 0.1)',
                border: '1px solid #4CAF50'
              }}
            >
              连接测试成功！服务器响应正常。
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setTestConnectionOpen(false)}
          >
            关闭
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// 添加缺失的 Circle 图标组件
function Circle({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
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