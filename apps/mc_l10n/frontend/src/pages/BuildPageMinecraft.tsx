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
  Badge
} from '@mui/material';
import {
  Package,
  Settings,
  Play,
  Pause,
  Square,
  Check,
  X,
  AlertCircle,
  Download,
  Upload,
  FolderOpen,
  FileText,
  Zap,
  Shield,
  Clock,
  TrendingUp,
  Hash,
  GitBranch,
  Archive,
  CheckCircle,
  XCircle,
  Info,
  Trash2,
  Edit,
  Save,
  RefreshCw,
  Terminal,
  Code,
  Layers,
  Target,
  Activity
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

interface BuildConfig {
  id: string;
  name: string;
  type: 'modpack' | 'resourcepack' | 'mixed';
  version: string;
  minecraftVersion: string;
  loader: 'forge' | 'fabric' | 'quilt' | 'neoforge' | 'vanilla';
  outputFormat: 'zip' | 'jar' | 'folder';
  includeDocs: boolean;
  validateTranslations: boolean;
  optimizeAssets: boolean;
  lastBuilt?: Date;
  status: 'ready' | 'building' | 'success' | 'error';
}

interface BuildTask {
  id: string;
  configId: string;
  configName: string;
  startTime: Date;
  endTime?: Date;
  status: 'queued' | 'preparing' | 'building' | 'validating' | 'packaging' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  logs: string[];
  errors: string[];
  warnings: string[];
  outputPath?: string;
  outputSize?: number;
}

interface BuildStats {
  totalBuilds: number;
  successfulBuilds: number;
  failedBuilds: number;
  averageBuildTime: number;
  totalOutputSize: number;
  lastBuildDate?: Date;
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

export default function BuildPageMinecraft() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [buildConfigs, setBuildConfigs] = useState<BuildConfig[]>([]);
  const [buildTasks, setBuildTasks] = useState<BuildTask[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<BuildConfig | null>(null);
  const [activeBuild, setActiveBuild] = useState<BuildTask | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<BuildConfig | null>(null);
  const [buildStats, setBuildStats] = useState<BuildStats>({
    totalBuilds: 0,
    successfulBuilds: 0,
    failedBuilds: 0,
    averageBuildTime: 0,
    totalOutputSize: 0
  });
  const [logViewerOpen, setLogViewerOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<BuildTask | null>(null);

  // 模拟数据
  useEffect(() => {
    const mockConfigs: BuildConfig[] = [
      {
        id: '1',
        name: 'ATM10 本地化包',
        type: 'modpack',
        version: '1.0.0',
        minecraftVersion: '1.21.1',
        loader: 'neoforge',
        outputFormat: 'zip',
        includeDocs: true,
        validateTranslations: true,
        optimizeAssets: true,
        lastBuilt: new Date('2024-03-20'),
        status: 'success'
      },
      {
        id: '2',
        name: '暮色森林资源包',
        type: 'resourcepack',
        version: '2.1.0',
        minecraftVersion: '1.21.1',
        loader: 'vanilla',
        outputFormat: 'zip',
        includeDocs: false,
        validateTranslations: true,
        optimizeAssets: false,
        status: 'ready'
      }
    ];

    const mockTasks: BuildTask[] = [
      {
        id: 't1',
        configId: '1',
        configName: 'ATM10 本地化包',
        startTime: new Date('2024-03-20T10:00:00'),
        endTime: new Date('2024-03-20T10:05:00'),
        status: 'completed',
        progress: 100,
        currentStep: '构建完成',
        logs: ['开始构建...', '验证翻译...', '打包文件...', '构建成功！'],
        errors: [],
        warnings: ['发现 3 个未翻译条目'],
        outputPath: '/builds/atm10_1.0.0.zip',
        outputSize: 15728640
      }
    ];

    setBuildConfigs(mockConfigs);
    setBuildTasks(mockTasks);
    setBuildStats({
      totalBuilds: 25,
      successfulBuilds: 23,
      failedBuilds: 2,
      averageBuildTime: 180,
      totalOutputSize: 524288000,
      lastBuildDate: new Date('2024-03-20')
    });
  }, []);

  const handleStartBuild = (config: BuildConfig) => {
    const newTask: BuildTask = {
      id: `t${Date.now()}`,
      configId: config.id,
      configName: config.name,
      startTime: new Date(),
      status: 'queued',
      progress: 0,
      currentStep: '等待构建...',
      logs: ['构建任务已创建'],
      errors: [],
      warnings: []
    };
    setBuildTasks([newTask, ...buildTasks]);
    setActiveBuild(newTask);
    
    // 模拟构建进度
    simulateBuildProgress(newTask);
  };

  const simulateBuildProgress = (task: BuildTask) => {
    const steps = [
      { status: 'preparing', progress: 10, step: '准备构建环境...' },
      { status: 'building', progress: 30, step: '收集翻译文件...' },
      { status: 'building', progress: 50, step: '合并翻译内容...' },
      { status: 'validating', progress: 70, step: '验证翻译完整性...' },
      { status: 'packaging', progress: 90, step: '打包输出文件...' },
      { status: 'completed', progress: 100, step: '构建完成！' }
    ];

    steps.forEach((step, index) => {
      setTimeout(() => {
        setBuildTasks(tasks => 
          tasks.map(t => t.id === task.id ? {
            ...t,
            status: step.status as any,
            progress: step.progress,
            currentStep: step.step,
            logs: [...t.logs, step.step]
          } : t)
        );
        
        if (step.status === 'completed') {
          setActiveBuild(null);
        }
      }, (index + 1) * 2000);
    });
  };

  const handleSaveConfig = (config: BuildConfig) => {
    if (editingConfig) {
      setBuildConfigs(configs => 
        configs.map(c => c.id === config.id ? config : c)
      );
    } else {
      setBuildConfigs([...buildConfigs, { ...config, id: `c${Date.now()}` }]);
    }
    setConfigDialogOpen(false);
    setEditingConfig(null);
  };

  const handleDeleteConfig = (configId: string) => {
    setBuildConfigs(configs => configs.filter(c => c.id !== configId));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
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
          <MinecraftBlock type="iron" size={32} animated />
          构建管理
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          配置和执行本地化包构建任务，生成最终的分发文件
        </Typography>
      </Box>

      {/* 统计信息 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="crafting">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Package size={20} style={{ color: minecraftColors.diamondBlue }} />
                <Typography variant="body2" color="text.secondary">
                  总构建次数
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {buildStats.totalBuilds}
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="crafting">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <CheckCircle size={20} style={{ color: minecraftColors.emerald }} />
                <Typography variant="body2" color="text.secondary">
                  成功率
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {buildStats.totalBuilds > 0 
                  ? `${Math.round(buildStats.successfulBuilds / buildStats.totalBuilds * 100)}%`
                  : '0%'}
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="crafting">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Clock size={20} style={{ color: minecraftColors.goldYellow }} />
                <Typography variant="body2" color="text.secondary">
                  平均耗时
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {formatDuration(buildStats.averageBuildTime)}
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
        <Grid item xs={12} md={3}>
          <MinecraftCard variant="crafting">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Archive size={20} style={{ color: minecraftColors.iron }} />
                <Typography variant="body2" color="text.secondary">
                  总输出大小
                </Typography>
              </Box>
              <Typography variant="h5" sx={{ fontFamily: '"Minecraft", monospace' }}>
                {formatFileSize(buildStats.totalOutputSize)}
              </Typography>
            </CardContent>
          </MinecraftCard>
        </Grid>
      </Grid>

      {/* 选项卡 */}
      <Paper
        sx={{
          bgcolor: 'rgba(15, 23, 42, 0.8)',
          border: '2px solid #2A2A4E',
          borderRadius: 0,
          mb: 3
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
          <Tab label="构建配置" icon={<Settings size={16} />} iconPosition="start" />
          <Tab label="构建任务" icon={<Activity size={16} />} iconPosition="start" />
          <Tab label="构建历史" icon={<Clock size={16} />} iconPosition="start" />
          <Tab label="输出管理" icon={<Archive size={16} />} iconPosition="start" />
        </Tabs>

        {/* 构建配置 */}
        <TabPanel value={selectedTab} index={0}>
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                构建配置列表
              </Typography>
              <MinecraftButton
                minecraftStyle="emerald"
                onClick={() => {
                  setEditingConfig(null);
                  setConfigDialogOpen(true);
                }}
                startIcon={<Plus size={16} />}
              >
                新建配置
              </MinecraftButton>
            </Box>

            <Grid container spacing={2}>
              {buildConfigs.map((config) => (
                <Grid item xs={12} md={6} key={config.id}>
                  <MinecraftCard variant="chest">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Box>
                          <Typography
                            variant="h6"
                            sx={{ fontFamily: '"Minecraft", monospace', mb: 1 }}
                          >
                            {config.name}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                              label={config.type}
                              size="small"
                              sx={{
                                bgcolor: config.type === 'modpack' 
                                  ? minecraftColors.diamondBlue 
                                  : minecraftColors.goldYellow,
                                color: '#FFFFFF'
                              }}
                            />
                            <Chip
                              label={config.loader}
                              size="small"
                              sx={{ bgcolor: 'rgba(255,255,255,0.1)' }}
                            />
                            <Chip
                              label={`MC ${config.minecraftVersion}`}
                              size="small"
                              sx={{ bgcolor: 'rgba(255,255,255,0.1)' }}
                            />
                          </Box>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            onClick={() => {
                              setEditingConfig(config);
                              setConfigDialogOpen(true);
                            }}
                          >
                            <Edit size={16} />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteConfig(config.id)}
                            sx={{ color: 'error.main' }}
                          >
                            <Trash2 size={16} />
                          </IconButton>
                        </Box>
                      </Box>

                      <Divider sx={{ my: 2 }} />

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          构建选项
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          {config.includeDocs && (
                            <Chip
                              icon={<FileText size={14} />}
                              label="包含文档"
                              size="small"
                              variant="outlined"
                            />
                          )}
                          {config.validateTranslations && (
                            <Chip
                              icon={<Check size={14} />}
                              label="验证翻译"
                              size="small"
                              variant="outlined"
                            />
                          )}
                          {config.optimizeAssets && (
                            <Chip
                              icon={<Zap size={14} />}
                              label="优化资源"
                              size="small"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </Box>

                      {config.lastBuilt && (
                        <Typography variant="caption" color="text.secondary">
                          上次构建: {config.lastBuilt.toLocaleDateString()}
                        </Typography>
                      )}

                      <Box sx={{ mt: 2 }}>
                        <MinecraftButton
                          fullWidth
                          minecraftStyle="grass"
                          onClick={() => handleStartBuild(config)}
                          disabled={activeBuild !== null}
                          startIcon={<Play size={16} />}
                        >
                          开始构建
                        </MinecraftButton>
                      </Box>
                    </CardContent>
                  </MinecraftCard>
                </Grid>
              ))}
            </Grid>
          </Box>
        </TabPanel>

        {/* 构建任务 */}
        <TabPanel value={selectedTab} index={1}>
          <Box sx={{ p: 3 }}>
            {activeBuild ? (
              <MinecraftCard variant="enchantment">
                <CardContent>
                  <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                    正在构建: {activeBuild.configName}
                  </Typography>
                  
                  <MinecraftProgress
                    variant="loading"
                    value={activeBuild.progress}
                    sx={{ mb: 2 }}
                  />
                  
                  <Typography variant="body2" sx={{ mb: 3 }}>
                    {activeBuild.currentStep}
                  </Typography>

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <MinecraftButton
                      minecraftStyle="redstone"
                      startIcon={<Square size={16} />}
                      onClick={() => setActiveBuild(null)}
                    >
                      停止构建
                    </MinecraftButton>
                    <MinecraftButton
                      minecraftStyle="stone"
                      startIcon={<Terminal size={16} />}
                      onClick={() => {
                        setSelectedTask(activeBuild);
                        setLogViewerOpen(true);
                      }}
                    >
                      查看日志
                    </MinecraftButton>
                  </Box>
                </CardContent>
              </MinecraftCard>
            ) : (
              <Alert
                severity="info"
                sx={{
                  bgcolor: 'rgba(33, 150, 243, 0.1)',
                  border: '1px solid #2196F3'
                }}
              >
                当前没有正在进行的构建任务
              </Alert>
            )}

            {buildTasks.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                  任务队列
                </Typography>
                <List>
                  {buildTasks.slice(0, 5).map((task) => (
                    <ListItem
                      key={task.id}
                      sx={{
                        bgcolor: 'rgba(255,255,255,0.02)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 0,
                        mb: 1
                      }}
                    >
                      <ListItemIcon>
                        {task.status === 'completed' ? (
                          <CheckCircle size={20} style={{ color: minecraftColors.emerald }} />
                        ) : task.status === 'failed' ? (
                          <XCircle size={20} style={{ color: minecraftColors.redstoneRed }} />
                        ) : (
                          <Clock size={20} style={{ color: minecraftColors.goldYellow }} />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={task.configName}
                        secondary={`${task.currentStep} - ${task.progress}%`}
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => {
                            setSelectedTask(task);
                            setLogViewerOpen(true);
                          }}
                        >
                          <Info size={16} />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Box>
        </TabPanel>

        {/* 构建历史 */}
        <TabPanel value={selectedTab} index={2}>
          <Box sx={{ p: 3 }}>
            <List>
              {buildTasks.filter(t => t.status === 'completed' || t.status === 'failed').map((task) => (
                <ListItem
                  key={task.id}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 0,
                    mb: 1
                  }}
                >
                  <ListItemIcon>
                    {task.status === 'completed' ? (
                      <CheckCircle size={20} style={{ color: minecraftColors.emerald }} />
                    ) : (
                      <XCircle size={20} style={{ color: minecraftColors.redstoneRed }} />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography>{task.configName}</Typography>
                        {task.warnings.length > 0 && (
                          <Chip
                            icon={<AlertCircle size={14} />}
                            label={`${task.warnings.length} 警告`}
                            size="small"
                            sx={{ bgcolor: 'rgba(255, 152, 0, 0.2)' }}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption">
                          {task.startTime.toLocaleString()}
                        </Typography>
                        {task.outputSize && (
                          <Typography variant="caption" sx={{ ml: 2 }}>
                            输出大小: {formatFileSize(task.outputSize)}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {task.outputPath && (
                        <IconButton edge="end">
                          <Download size={16} />
                        </IconButton>
                      )}
                      <IconButton
                        edge="end"
                        onClick={() => {
                          setSelectedTask(task);
                          setLogViewerOpen(true);
                        }}
                      >
                        <Info size={16} />
                      </IconButton>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </Box>
        </TabPanel>

        {/* 输出管理 */}
        <TabPanel value={selectedTab} index={3}>
          <Box sx={{ p: 3 }}>
            <Alert
              severity="info"
              sx={{
                mb: 3,
                bgcolor: 'rgba(33, 150, 243, 0.1)',
                border: '1px solid #2196F3'
              }}
            >
              构建输出文件保存在本地，可以导出到指定位置或上传到服务器
            </Alert>

            <Grid container spacing={2}>
              {buildTasks
                .filter(t => t.status === 'completed' && t.outputPath)
                .map((task) => (
                  <Grid item xs={12} md={6} key={task.id}>
                    <MinecraftCard variant="inventory">
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                          <Box>
                            <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                              {task.configName}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {task.endTime?.toLocaleString()}
                            </Typography>
                          </Box>
                          <Chip
                            label={formatFileSize(task.outputSize || 0)}
                            size="small"
                            sx={{ bgcolor: minecraftColors.iron }}
                          />
                        </Box>

                        <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                          {task.outputPath}
                        </Typography>

                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <MinecraftButton
                            size="small"
                            minecraftStyle="grass"
                            startIcon={<FolderOpen size={14} />}
                          >
                            打开位置
                          </MinecraftButton>
                          <MinecraftButton
                            size="small"
                            minecraftStyle="diamond"
                            startIcon={<Upload size={14} />}
                          >
                            上传
                          </MinecraftButton>
                          <MinecraftButton
                            size="small"
                            minecraftStyle="redstone"
                            startIcon={<Trash2 size={14} />}
                          >
                            删除
                          </MinecraftButton>
                        </Box>
                      </CardContent>
                    </MinecraftCard>
                  </Grid>
                ))}
            </Grid>
          </Box>
        </TabPanel>
      </Paper>

      {/* 配置对话框 */}
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
          {editingConfig ? '编辑构建配置' : '新建构建配置'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="配置名称"
                defaultValue={editingConfig?.name}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>类型</InputLabel>
                <Select
                  defaultValue={editingConfig?.type || 'modpack'}
                  label="类型"
                >
                  <MenuItem value="modpack">整合包</MenuItem>
                  <MenuItem value="resourcepack">资源包</MenuItem>
                  <MenuItem value="mixed">混合</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>加载器</InputLabel>
                <Select
                  defaultValue={editingConfig?.loader || 'forge'}
                  label="加载器"
                >
                  <MenuItem value="forge">Forge</MenuItem>
                  <MenuItem value="fabric">Fabric</MenuItem>
                  <MenuItem value="quilt">Quilt</MenuItem>
                  <MenuItem value="neoforge">NeoForge</MenuItem>
                  <MenuItem value="vanilla">原版</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="版本号"
                defaultValue={editingConfig?.version || '1.0.0'}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Minecraft 版本"
                defaultValue={editingConfig?.minecraftVersion || '1.21.1'}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>输出格式</InputLabel>
                <Select
                  defaultValue={editingConfig?.outputFormat || 'zip'}
                  label="输出格式"
                >
                  <MenuItem value="zip">ZIP 压缩包</MenuItem>
                  <MenuItem value="jar">JAR 文件</MenuItem>
                  <MenuItem value="folder">文件夹</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch defaultChecked={editingConfig?.includeDocs ?? true} />
                }
                label="包含文档"
              />
              <FormControlLabel
                control={
                  <Switch defaultChecked={editingConfig?.validateTranslations ?? true} />
                }
                label="验证翻译"
              />
              <FormControlLabel
                control={
                  <Switch defaultChecked={editingConfig?.optimizeAssets ?? false} />
                }
                label="优化资源"
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
            onClick={() => {
              // 保存配置逻辑
              setConfigDialogOpen(false);
            }}
          >
            保存
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* 日志查看器 */}
      <Dialog
        open={logViewerOpen}
        onClose={() => setLogViewerOpen(false)}
        maxWidth="lg"
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
          构建日志 - {selectedTask?.configName}
        </DialogTitle>
        <DialogContent>
          <Paper
            sx={{
              p: 2,
              bgcolor: '#000000',
              border: '1px solid #2A2A4E',
              borderRadius: 0,
              fontFamily: 'monospace',
              fontSize: '12px',
              maxHeight: '400px',
              overflowY: 'auto'
            }}
          >
            {selectedTask?.logs.map((log, index) => (
              <Box key={index} sx={{ mb: 0.5 }}>
                <span style={{ color: '#00FF00' }}>[{new Date().toLocaleTimeString()}]</span>{' '}
                {log}
              </Box>
            ))}
            {selectedTask?.warnings.map((warning, index) => (
              <Box key={`w${index}`} sx={{ mb: 0.5, color: '#FFA500' }}>
                <span>[警告]</span> {warning}
              </Box>
            ))}
            {selectedTask?.errors.map((error, index) => (
              <Box key={`e${index}`} sx={{ mb: 0.5, color: '#FF0000' }}>
                <span>[错误]</span> {error}
              </Box>
            ))}
          </Paper>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setLogViewerOpen(false)}
          >
            关闭
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// 添加 Plus 图标组件
function Plus({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}