import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  TextField,
  InputAdornment,
  FormControl,
  Select,
  MenuItem,
  Alert,
  Divider,
  Badge
} from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  Download,
  RefreshCw,
  Wifi,
  WifiOff,
  Cloud,
  CloudOff,
  Server,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Zap,
  GitBranch,
  GitCommit,
  GitMerge,
  ArrowUp,
  ArrowDown,
  Pause,
  Play,
  Search,
  Filter,
  MoreVert,
  Eye,
  Hash,
  Package,
  Globe
} from 'lucide-react';
import toast from 'react-hot-toast';

import { MinecraftButton } from '../components/minecraft/MinecraftButton';
import { MinecraftCard } from '../components/minecraft/MinecraftCard';
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress';
import { MinecraftBlock } from '../components/MinecraftComponents';

interface TransferTask {
  id: string;
  type: 'upload' | 'download' | 'sync';
  name: string;
  project: string;
  status: 'pending' | 'transferring' | 'completed' | 'error' | 'paused';
  progress: number;
  speed: number; // KB/s
  size: number; // bytes
  transferred: number; // bytes
  remainingTime: number; // seconds
  error?: string;
  conflicts?: number;
  direction?: 'local_to_server' | 'server_to_local' | 'bidirectional';
  createdAt: string;
}

interface ServerStatus {
  connected: boolean;
  latency: number;
  bandwidth: number;
  activeConnections: number;
  queuedTasks: number;
}

const mockTasks: TransferTask[] = [
  {
    id: '1',
    type: 'upload',
    name: 'ATM9 完整翻译包',
    project: 'All The Mods 9',
    status: 'transferring',
    progress: 65,
    speed: 1024,
    size: 25600000,
    transferred: 16640000,
    remainingTime: 8,
    direction: 'local_to_server',
    createdAt: '2025-01-01 14:30'
  },
  {
    id: '2',
    type: 'download',
    name: 'Create 模组更新',
    project: 'Create: Above and Beyond',
    status: 'completed',
    progress: 100,
    speed: 0,
    size: 8400000,
    transferred: 8400000,
    remainingTime: 0,
    direction: 'server_to_local',
    createdAt: '2025-01-01 14:25'
  },
  {
    id: '3',
    type: 'sync',
    name: 'Twilight Forest 同步',
    project: 'Twilight Forest',
    status: 'pending',
    progress: 0,
    speed: 0,
    size: 12000000,
    transferred: 0,
    remainingTime: 0,
    conflicts: 3,
    direction: 'bidirectional',
    createdAt: '2025-01-01 14:35'
  }
];

export default function TransferPageMinecraft() {
  const [tasks, setTasks] = useState<TransferTask[]>(mockTasks);
  const [serverStatus, setServerStatus] = useState<ServerStatus>({
    connected: true,
    latency: 45,
    bandwidth: 2048,
    activeConnections: 3,
    queuedTasks: 5
  });
  const [filterType, setFilterType] = useState<'all' | 'upload' | 'download' | 'sync'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTask, setSelectedTask] = useState<TransferTask | null>(null);

  const handleStartTransfer = (taskId: string) => {
    setTasks(prev => prev.map(task => {
      if (task.id === taskId) {
        return { ...task, status: 'transferring', progress: 0 };
      }
      return task;
    }));

    // 模拟传输进度
    const interval = setInterval(() => {
      setTasks(prev => prev.map(task => {
        if (task.id === taskId && task.status === 'transferring') {
          const newProgress = Math.min(100, task.progress + Math.random() * 10);
          const newTransferred = (task.size * newProgress) / 100;
          const remainingBytes = task.size - newTransferred;
          const remainingTime = Math.max(0, Math.floor(remainingBytes / (task.speed * 1024)));
          
          if (newProgress >= 100) {
            clearInterval(interval);
            toast.success(`${task.name} 传输完成！`, { icon: '✅' });
            return { 
              ...task, 
              status: 'completed', 
              progress: 100,
              transferred: task.size,
              remainingTime: 0,
              speed: 0
            };
          }
          
          return { 
            ...task, 
            progress: newProgress,
            transferred: newTransferred,
            remainingTime,
            speed: 800 + Math.random() * 500
          };
        }
        return task;
      }));
    }, 500);
  };

  const handlePauseTransfer = (taskId: string) => {
    setTasks(prev => prev.map(task => {
      if (task.id === taskId) {
        return { ...task, status: 'paused', speed: 0 };
      }
      return task;
    }));
    toast.success('传输已暂停', { icon: '⏸️' });
  };

  const handleResumeTransfer = (taskId: string) => {
    handleStartTransfer(taskId);
    toast.success('继续传输', { icon: '▶️' });
  };

  const handleCancelTransfer = (taskId: string) => {
    setTasks(prev => prev.filter(task => task.id !== taskId));
    toast.success('传输已取消', { icon: '❌' });
  };

  const handleRetryTransfer = (taskId: string) => {
    setTasks(prev => prev.map(task => {
      if (task.id === taskId) {
        return { ...task, status: 'pending', progress: 0, transferred: 0, error: undefined };
      }
      return task;
    }));
    setTimeout(() => handleStartTransfer(taskId), 500);
  };

  const handleResolveConflicts = (task: TransferTask) => {
    toast.info(`解决 ${task.conflicts} 个冲突...`, { icon: '🔧' });
    setSelectedTask(task);
  };

  const formatSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(2)} MB` : `${(bytes / 1024).toFixed(2)} KB`;
  };

  const formatSpeed = (kbps: number) => {
    return kbps >= 1024 ? `${(kbps / 1024).toFixed(1)} MB/s` : `${kbps.toFixed(0)} KB/s`;
  };

  const formatTime = (seconds: number) => {
    if (seconds <= 0) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} color="#4CAF50" />;
      case 'transferring': return <Clock size={16} color="#2196F3" />;
      case 'error': return <XCircle size={16} color="#F44336" />;
      case 'paused': return <Pause size={16} color="#FF9800" />;
      default: return <AlertTriangle size={16} color="#9E9E9E" />;
    }
  };

  const getTypeIcon = (type: string, direction?: string) => {
    if (type === 'sync') return <RefreshCw size={20} color="#9C27B0" />;
    if (type === 'upload' || direction === 'local_to_server') 
      return <Upload size={20} color="#4CAF50" />;
    return <Download size={20} color="#2196F3" />;
  };

  const filteredTasks = tasks.filter(task => {
    const matchesFilter = filterType === 'all' || task.type === filterType;
    const matchesSearch = task.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         task.project.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <Box sx={{ p: 3 }}>
      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ mb: 4 }}>
          <Typography
            variant="h3"
            sx={{
              fontFamily: '"Minecraft", "Press Start 2P", monospace',
              fontSize: { xs: '24px', md: '32px' },
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              background: 'linear-gradient(135deg, #9C27B0 0%, #673AB7 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              mb: 1,
            }}
          >
            🔄 传输管理
          </Typography>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '14px',
              color: 'text.secondary',
            }}
          >
            与 Trans-Hub 平台同步数据
          </Typography>
        </Box>
      </motion.div>

      {/* 服务器状态 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <MinecraftCard 
            variant="enchantment" 
            title="服务器状态" 
            icon="diamond"
            glowing={serverStatus.connected}
          >
            <Box sx={{ p: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={2}>
                  <Box sx={{ textAlign: 'center' }}>
                    {serverStatus.connected ? (
                      <Wifi size={24} color="#4CAF50" />
                    ) : (
                      <WifiOff size={24} color="#F44336" />
                    )}
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '12px',
                        color: serverStatus.connected ? '#4CAF50' : '#F44336',
                        mt: 1,
                      }}
                    >
                      {serverStatus.connected ? '已连接' : '未连接'}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={2}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Zap size={24} color="#FFD700" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '16px',
                        color: '#FFFFFF',
                        mt: 1,
                      }}
                    >
                      {serverStatus.latency} ms
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '10px',
                        color: 'text.secondary',
                      }}
                    >
                      延迟
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={2}>
                  <Box sx={{ textAlign: 'center' }}>
                    <ArrowUp size={24} color="#2196F3" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '16px',
                        color: '#FFFFFF',
                        mt: 1,
                      }}
                    >
                      {formatSpeed(serverStatus.bandwidth)}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '10px',
                        color: 'text.secondary',
                      }}
                    >
                      带宽
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={2}>
                  <Box sx={{ textAlign: 'center' }}>
                    <GitBranch size={24} color="#9C27B0" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '16px',
                        color: '#FFFFFF',
                        mt: 1,
                      }}
                    >
                      {serverStatus.activeConnections}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '10px',
                        color: 'text.secondary',
                      }}
                    >
                      活跃连接
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={2}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Clock size={24} color="#FF9800" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '16px',
                        color: '#FFFFFF',
                        mt: 1,
                      }}
                    >
                      {serverStatus.queuedTasks}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '10px',
                        color: 'text.secondary',
                      }}
                    >
                      队列任务
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={2}>
                  <Box sx={{ textAlign: 'center' }}>
                    <MinecraftButton
                      minecraftStyle="emerald"
                      size="small"
                      onClick={() => {
                        setServerStatus(prev => ({ ...prev, connected: !prev.connected }));
                        toast.success(serverStatus.connected ? '已断开连接' : '已连接到服务器');
                      }}
                    >
                      {serverStatus.connected ? '断开' : '连接'}
                    </MinecraftButton>
                  </Box>
                </Grid>
              </Grid>
            </Box>
          </MinecraftCard>
        </Grid>
      </Grid>

      {/* 工具栏 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            placeholder="搜索任务..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={20} />
                </InputAdornment>
              ),
              sx: {
                fontFamily: '"Minecraft", monospace',
                fontSize: '14px',
                background: 'rgba(0,0,0,0.3)',
                border: '2px solid #4A4A4A',
                borderRadius: 0,
                '& fieldset': { border: 'none' },
              }
            }}
          />
        </Grid>
        <Grid item xs={6} md={2}>
          <FormControl fullWidth>
            <Select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '14px',
                background: 'rgba(0,0,0,0.3)',
                border: '2px solid #4A4A4A',
                borderRadius: 0,
                '& fieldset': { border: 'none' },
              }}
            >
              <MenuItem value="all">全部</MenuItem>
              <MenuItem value="upload">上传</MenuItem>
              <MenuItem value="download">下载</MenuItem>
              <MenuItem value="sync">同步</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={6} md={2}>
          <MinecraftButton
            fullWidth
            minecraftStyle="diamond"
            onClick={() => toast.info('检查更新...')}
            startIcon={<RefreshCw size={16} />}
          >
            检查更新
          </MinecraftButton>
        </Grid>
        <Grid item xs={6} md={2}>
          <MinecraftButton
            fullWidth
            minecraftStyle="gold"
            onClick={() => toast.info('创建新任务...')}
            startIcon={<Upload size={16} />}
          >
            上传
          </MinecraftButton>
        </Grid>
        <Grid item xs={6} md={2}>
          <MinecraftButton
            fullWidth
            minecraftStyle="emerald"
            onClick={() => toast.info('同步所有...')}
            startIcon={<GitMerge size={16} />}
            glowing
          >
            全部同步
          </MinecraftButton>
        </Grid>
      </Grid>

      {/* 任务列表 */}
      <MinecraftCard variant="chest" title="传输任务" icon="gold">
        <Box sx={{ p: 2 }}>
          <List>
            <AnimatePresence>
              {filteredTasks.map((task, index) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <ListItem
                    sx={{
                      mb: 2,
                      p: 2,
                      background: 'rgba(0,0,0,0.3)',
                      border: `2px solid ${
                        task.status === 'completed' ? '#4CAF50' :
                        task.status === 'transferring' ? '#2196F3' :
                        task.status === 'error' ? '#F44336' :
                        '#4A4A4A'
                      }`,
                      borderRadius: 0,
                    }}
                  >
                    <ListItemIcon>
                      {getTypeIcon(task.type, task.direction)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Typography
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '14px',
                                color: '#FFFFFF',
                                fontWeight: 'bold',
                              }}
                            >
                              {task.name}
                            </Typography>
                            {getStatusIcon(task.status)}
                            {task.conflicts && task.conflicts > 0 && (
                              <Chip
                                label={`${task.conflicts} 冲突`}
                                size="small"
                                sx={{
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '10px',
                                  background: '#FF9800',
                                  color: '#000000',
                                  height: 20,
                                  borderRadius: 0,
                                }}
                                onClick={() => handleResolveConflicts(task)}
                              />
                            )}
                          </Box>
                          <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
                            <Typography
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '11px',
                                color: 'text.secondary',
                              }}
                            >
                              {task.project}
                            </Typography>
                            <Typography
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '11px',
                                color: 'text.secondary',
                              }}
                            >
                              {task.createdAt}
                            </Typography>
                          </Box>
                        </Box>
                      }
                      secondary={
                        <Box>
                          {(task.status === 'transferring' || task.status === 'paused') && (
                            <>
                              <MinecraftProgress
                                value={task.progress}
                                variant="loading"
                                size="small"
                                animated={task.status === 'transferring'}
                              />
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography
                                    sx={{
                                      fontFamily: '"Minecraft", monospace',
                                      fontSize: '10px',
                                      color: '#4CAF50',
                                    }}
                                  >
                                    {formatSize(task.transferred)} / {formatSize(task.size)}
                                  </Typography>
                                  {task.speed > 0 && (
                                    <Typography
                                      sx={{
                                        fontFamily: '"Minecraft", monospace',
                                        fontSize: '10px',
                                        color: '#2196F3',
                                      }}
                                    >
                                      {formatSpeed(task.speed)}
                                    </Typography>
                                  )}
                                </Box>
                                <Typography
                                  sx={{
                                    fontFamily: '"Minecraft", monospace',
                                    fontSize: '10px',
                                    color: '#FF9800',
                                  }}
                                >
                                  剩余: {formatTime(task.remainingTime)}
                                </Typography>
                              </Box>
                            </>
                          )}
                          {task.status === 'completed' && (
                            <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                              <Chip
                                icon={<CheckCircle size={14} />}
                                label="已完成"
                                size="small"
                                sx={{
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '10px',
                                  background: 'rgba(76,175,80,0.2)',
                                  color: '#4CAF50',
                                  border: '1px solid #4CAF50',
                                  borderRadius: 0,
                                }}
                              />
                              <Typography
                                sx={{
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '10px',
                                  color: 'text.secondary',
                                }}
                              >
                                {formatSize(task.size)}
                              </Typography>
                            </Box>
                          )}
                          {task.error && (
                            <Alert
                              severity="error"
                              sx={{
                                mt: 1,
                                py: 0.5,
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '10px',
                                background: 'rgba(244,67,54,0.1)',
                                border: '1px solid #F44336',
                                borderRadius: 0,
                              }}
                            >
                              {task.error}
                            </Alert>
                          )}
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {task.status === 'pending' && (
                          <Tooltip title="开始">
                            <IconButton
                              size="small"
                              onClick={() => handleStartTransfer(task.id)}
                            >
                              <Play size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {task.status === 'transferring' && (
                          <Tooltip title="暂停">
                            <IconButton
                              size="small"
                              onClick={() => handlePauseTransfer(task.id)}
                            >
                              <Pause size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {task.status === 'paused' && (
                          <Tooltip title="继续">
                            <IconButton
                              size="small"
                              onClick={() => handleResumeTransfer(task.id)}
                            >
                              <Play size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {task.status === 'error' && (
                          <Tooltip title="重试">
                            <IconButton
                              size="small"
                              onClick={() => handleRetryTransfer(task.id)}
                            >
                              <RefreshCw size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title="详情">
                          <IconButton size="small">
                            <Eye size={16} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="取消">
                          <IconButton
                            size="small"
                            onClick={() => handleCancelTransfer(task.id)}
                          >
                            <XCircle size={16} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </ListItemSecondaryAction>
                  </ListItem>
                </motion.div>
              ))}
            </AnimatePresence>
          </List>

          {filteredTasks.length === 0 && (
            <Box sx={{ py: 8, textAlign: 'center', opacity: 0.6 }}>
              <Cloud size={64} />
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '16px',
                  color: 'text.secondary',
                  mt: 2,
                }}
              >
                暂无传输任务
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '12px',
                  color: 'text.secondary',
                  mt: 1,
                }}
              >
                点击上传或同步按钮开始
              </Typography>
            </Box>
          )}
        </Box>
      </MinecraftCard>

      {/* 传输统计 */}
      <Grid container spacing={2} sx={{ mt: 3 }}>
        <Grid item xs={6} md={3}>
          <MinecraftCard variant="inventory">
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Upload size={24} color="#4CAF50" />
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '20px',
                  color: '#4CAF50',
                  mt: 1,
                }}
              >
                {tasks.filter(t => t.type === 'upload').length}
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '10px',
                  color: 'text.secondary',
                }}
              >
                上传任务
              </Typography>
            </Box>
          </MinecraftCard>
        </Grid>
        <Grid item xs={6} md={3}>
          <MinecraftCard variant="inventory">
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Download size={24} color="#2196F3" />
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '20px',
                  color: '#2196F3',
                  mt: 1,
                }}
              >
                {tasks.filter(t => t.type === 'download').length}
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '10px',
                  color: 'text.secondary',
                }}
              >
                下载任务
              </Typography>
            </Box>
          </MinecraftCard>
        </Grid>
        <Grid item xs={6} md={3}>
          <MinecraftCard variant="inventory">
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <RefreshCw size={24} color="#9C27B0" />
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '20px',
                  color: '#9C27B0',
                  mt: 1,
                }}
              >
                {tasks.filter(t => t.type === 'sync').length}
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '10px',
                  color: 'text.secondary',
                }}
              >
                同步任务
              </Typography>
            </Box>
          </MinecraftCard>
        </Grid>
        <Grid item xs={6} md={3}>
          <MinecraftCard variant="inventory">
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Package size={24} color="#FFD700" />
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '20px',
                  color: '#FFD700',
                  mt: 1,
                }}
              >
                {formatSize(tasks.reduce((sum, t) => sum + t.size, 0))}
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '10px',
                  color: 'text.secondary',
                }}
              >
                总数据量
              </Typography>
            </Box>
          </MinecraftCard>
        </Grid>
      </Grid>
    </Box>
  );
}