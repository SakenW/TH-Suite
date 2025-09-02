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
  TablePagination,
  Checkbox
} from '@mui/material';
import {
  Database,
  FolderOpen,
  File,
  Download,
  Upload,
  Trash2,
  RefreshCw,
  Search,
  Filter,
  Save,
  Archive,
  HardDrive,
  Activity,
  Zap,
  AlertCircle,
  CheckCircle,
  Info,
  Copy,
  Move,
  Edit,
  Eye,
  Lock,
  Unlock,
  Cloud,
  CloudOff,
  Hash,
  Calendar,
  User,
  Tag,
  BarChart,
  PieChart
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

interface LocalData {
  id: string;
  name: string;
  type: 'translation' | 'project' | 'cache' | 'backup' | 'export';
  size: number;
  created: Date;
  modified: Date;
  accessed: Date;
  path: string;
  synced: boolean;
  encrypted: boolean;
  tags: string[];
}

interface StorageStats {
  totalSize: number;
  usedSize: number;
  translationSize: number;
  cacheSize: number;
  backupSize: number;
  projectCount: number;
  fileCount: number;
  lastCleanup?: Date;
}

interface DataFilter {
  type: string;
  dateRange: string;
  synced: 'all' | 'synced' | 'local';
  searchTerm: string;
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

export default function LocalDataPageMinecraft() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [localData, setLocalData] = useState<LocalData[]>([]);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [storageStats, setStorageStats] = useState<StorageStats>({
    totalSize: 5368709120, // 5GB
    usedSize: 2147483648, // 2GB
    translationSize: 1073741824, // 1GB
    cacheSize: 536870912, // 500MB
    backupSize: 536870912, // 500MB
    projectCount: 12,
    fileCount: 1523
  });
  const [filter, setFilter] = useState<DataFilter>({
    type: 'all',
    dateRange: 'all',
    synced: 'all',
    searchTerm: ''
  });
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedData, setSelectedData] = useState<LocalData | null>(null);
  const [cleanupDialogOpen, setCleanupDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // 模拟数据
  useEffect(() => {
    const mockData: LocalData[] = [
      {
        id: '1',
        name: 'ATM10_translations_v1.0.0.json',
        type: 'translation',
        size: 5242880,
        created: new Date('2024-03-15'),
        modified: new Date('2024-03-20'),
        accessed: new Date('2024-03-21'),
        path: '/data/translations/',
        synced: true,
        encrypted: false,
        tags: ['ATM10', 'v1.0.0', '已完成']
      },
      {
        id: '2',
        name: 'twilightforest_lang_cache.db',
        type: 'cache',
        size: 10485760,
        created: new Date('2024-03-10'),
        modified: new Date('2024-03-19'),
        accessed: new Date('2024-03-21'),
        path: '/data/cache/',
        synced: false,
        encrypted: true,
        tags: ['暮色森林', '缓存']
      },
      {
        id: '3',
        name: 'project_backup_20240320.zip',
        type: 'backup',
        size: 52428800,
        created: new Date('2024-03-20'),
        modified: new Date('2024-03-20'),
        accessed: new Date('2024-03-20'),
        path: '/data/backups/',
        synced: false,
        encrypted: true,
        tags: ['备份', '自动']
      },
      {
        id: '4',
        name: 'mc_project_atm10.proj',
        type: 'project',
        size: 2097152,
        created: new Date('2024-03-01'),
        modified: new Date('2024-03-21'),
        accessed: new Date('2024-03-21'),
        path: '/data/projects/',
        synced: true,
        encrypted: false,
        tags: ['ATM10', '活跃']
      },
      {
        id: '5',
        name: 'export_zh_CN_20240318.zip',
        type: 'export',
        size: 15728640,
        created: new Date('2024-03-18'),
        modified: new Date('2024-03-18'),
        accessed: new Date('2024-03-19'),
        path: '/data/exports/',
        synced: true,
        encrypted: false,
        tags: ['导出', '中文']
      }
    ];

    setLocalData(mockData);
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'translation':
        return <File size={20} style={{ color: minecraftColors.diamondBlue }} />;
      case 'project':
        return <FolderOpen size={20} style={{ color: minecraftColors.goldYellow }} />;
      case 'cache':
        return <Database size={20} style={{ color: minecraftColors.iron }} />;
      case 'backup':
        return <Archive size={20} style={{ color: minecraftColors.emerald }} />;
      case 'export':
        return <Download size={20} style={{ color: minecraftColors.redstoneRed }} />;
      default:
        return <File size={20} />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'translation':
        return minecraftColors.diamondBlue;
      case 'project':
        return minecraftColors.goldYellow;
      case 'cache':
        return minecraftColors.iron;
      case 'backup':
        return minecraftColors.emerald;
      case 'export':
        return minecraftColors.redstoneRed;
      default:
        return '#FFFFFF';
    }
  };

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedItems(localData.map(d => d.id));
    } else {
      setSelectedItems([]);
    }
  };

  const handleSelect = (id: string) => {
    if (selectedItems.includes(id)) {
      setSelectedItems(selectedItems.filter(i => i !== id));
    } else {
      setSelectedItems([...selectedItems, id]);
    }
  };

  const handleDeleteSelected = () => {
    setLocalData(localData.filter(d => !selectedItems.includes(d.id)));
    setSelectedItems([]);
  };

  const handleCleanup = (type: 'cache' | 'backup' | 'all') => {
    // 模拟清理操作
    if (type === 'cache' || type === 'all') {
      setLocalData(data => data.filter(d => d.type !== 'cache'));
    }
    if (type === 'backup' || type === 'all') {
      setLocalData(data => data.filter(d => d.type !== 'backup' || 
        (new Date().getTime() - d.created.getTime()) < 7 * 24 * 60 * 60 * 1000));
    }
    setCleanupDialogOpen(false);
  };

  const filteredData = localData.filter(data => {
    if (filter.type !== 'all' && data.type !== filter.type) return false;
    if (filter.synced === 'synced' && !data.synced) return false;
    if (filter.synced === 'local' && data.synced) return false;
    if (filter.searchTerm && !data.name.toLowerCase().includes(filter.searchTerm.toLowerCase())) return false;
    return true;
  });

  const storageUsagePercent = (storageStats.usedSize / storageStats.totalSize) * 100;

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
          <MinecraftBlock type="stone" size={32} animated />
          本地数据管理
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          管理本地存储的翻译数据、缓存和备份文件
        </Typography>
      </Box>

      {/* 存储统计 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <MinecraftCard variant="chest">
            <CardContent>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                存储使用情况
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">
                    {formatFileSize(storageStats.usedSize)} / {formatFileSize(storageStats.totalSize)}
                  </Typography>
                  <Typography variant="body2">
                    {storageUsagePercent.toFixed(1)}%
                  </Typography>
                </Box>
                <MinecraftProgress
                  variant="experience"
                  value={storageUsagePercent}
                  sx={{ mb: 2 }}
                />
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <File size={16} style={{ color: minecraftColors.diamondBlue }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        翻译文件
                      </Typography>
                      <Typography variant="body2">
                        {formatFileSize(storageStats.translationSize)}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Database size={16} style={{ color: minecraftColors.iron }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        缓存数据
                      </Typography>
                      <Typography variant="body2">
                        {formatFileSize(storageStats.cacheSize)}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Archive size={16} style={{ color: minecraftColors.emerald }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        备份文件
                      </Typography>
                      <Typography variant="body2">
                        {formatFileSize(storageStats.backupSize)}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <FolderOpen size={16} style={{ color: minecraftColors.goldYellow }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        项目文件
                      </Typography>
                      <Typography variant="body2">
                        {storageStats.projectCount} 个
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </MinecraftCard>
        </Grid>

        <Grid item xs={12} md={6}>
          <MinecraftCard variant="crafting">
            <CardContent>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                快速操作
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <MinecraftButton
                    fullWidth
                    minecraftStyle="emerald"
                    startIcon={<Upload size={16} />}
                    onClick={() => setImportDialogOpen(true)}
                  >
                    导入数据
                  </MinecraftButton>
                </Grid>
                <Grid item xs={6}>
                  <MinecraftButton
                    fullWidth
                    minecraftStyle="diamond"
                    startIcon={<Download size={16} />}
                    disabled={selectedItems.length === 0}
                  >
                    导出选中
                  </MinecraftButton>
                </Grid>
                <Grid item xs={6}>
                  <MinecraftButton
                    fullWidth
                    minecraftStyle="gold"
                    startIcon={<RefreshCw size={16} />}
                    onClick={() => setCleanupDialogOpen(true)}
                  >
                    清理空间
                  </MinecraftButton>
                </Grid>
                <Grid item xs={6}>
                  <MinecraftButton
                    fullWidth
                    minecraftStyle="redstone"
                    startIcon={<Trash2 size={16} />}
                    disabled={selectedItems.length === 0}
                    onClick={handleDeleteSelected}
                  >
                    删除选中
                  </MinecraftButton>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    文件总数
                  </Typography>
                  <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                    {storageStats.fileCount}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    上次清理
                  </Typography>
                  <Typography variant="body2">
                    {storageStats.lastCleanup?.toLocaleDateString() || '从未'}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </MinecraftCard>
        </Grid>
      </Grid>

      {/* 数据管理选项卡 */}
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
          <Tab label="数据浏览" icon={<Database size={16} />} iconPosition="start" />
          <Tab label="缓存管理" icon={<Zap size={16} />} iconPosition="start" />
          <Tab label="备份管理" icon={<Archive size={16} />} iconPosition="start" />
          <Tab label="同步状态" icon={<Cloud size={16} />} iconPosition="start" />
        </Tabs>

        {/* 数据浏览 */}
        <TabPanel value={selectedTab} index={0}>
          <Box sx={{ p: 3 }}>
            {/* 过滤器 */}
            <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                size="small"
                placeholder="搜索文件..."
                value={filter.searchTerm}
                onChange={(e) => setFilter({ ...filter, searchTerm: e.target.value })}
                InputProps={{
                  startAdornment: <Search size={16} style={{ marginRight: 8 }} />
                }}
                sx={{ minWidth: 200 }}
              />
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>类型</InputLabel>
                <Select
                  value={filter.type}
                  label="类型"
                  onChange={(e) => setFilter({ ...filter, type: e.target.value })}
                >
                  <MenuItem value="all">全部</MenuItem>
                  <MenuItem value="translation">翻译文件</MenuItem>
                  <MenuItem value="project">项目文件</MenuItem>
                  <MenuItem value="cache">缓存</MenuItem>
                  <MenuItem value="backup">备份</MenuItem>
                  <MenuItem value="export">导出</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>同步状态</InputLabel>
                <Select
                  value={filter.synced}
                  label="同步状态"
                  onChange={(e) => setFilter({ ...filter, synced: e.target.value as any })}
                >
                  <MenuItem value="all">全部</MenuItem>
                  <MenuItem value="synced">已同步</MenuItem>
                  <MenuItem value="local">仅本地</MenuItem>
                </Select>
              </FormControl>
            </Box>

            {/* 数据表格 */}
            <TableContainer component={Paper} sx={{ bgcolor: 'transparent', border: '1px solid #2A2A4E' }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        indeterminate={selectedItems.length > 0 && selectedItems.length < localData.length}
                        checked={localData.length > 0 && selectedItems.length === localData.length}
                        onChange={handleSelectAll}
                      />
                    </TableCell>
                    <TableCell>名称</TableCell>
                    <TableCell>类型</TableCell>
                    <TableCell>大小</TableCell>
                    <TableCell>修改时间</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredData
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((data) => (
                      <TableRow
                        key={data.id}
                        hover
                        selected={selectedItems.includes(data.id)}
                      >
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedItems.includes(data.id)}
                            onChange={() => handleSelect(data.id)}
                          />
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getTypeIcon(data.type)}
                            <Box>
                              <Typography variant="body2">{data.name}</Typography>
                              <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
                                {data.tags.map(tag => (
                                  <Chip
                                    key={tag}
                                    label={tag}
                                    size="small"
                                    sx={{
                                      height: 16,
                                      fontSize: '10px',
                                      bgcolor: 'rgba(255,255,255,0.1)'
                                    }}
                                  />
                                ))}
                              </Box>
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={data.type}
                            size="small"
                            sx={{
                              bgcolor: getTypeColor(data.type),
                              color: '#FFFFFF'
                            }}
                          />
                        </TableCell>
                        <TableCell>{formatFileSize(data.size)}</TableCell>
                        <TableCell>{data.modified.toLocaleDateString()}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            {data.synced ? (
                              <Tooltip title="已同步">
                                <Cloud size={16} style={{ color: minecraftColors.emerald }} />
                              </Tooltip>
                            ) : (
                              <Tooltip title="仅本地">
                                <CloudOff size={16} style={{ color: minecraftColors.iron }} />
                              </Tooltip>
                            )}
                            {data.encrypted && (
                              <Tooltip title="已加密">
                                <Lock size={16} style={{ color: minecraftColors.goldYellow }} />
                              </Tooltip>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <IconButton
                              size="small"
                              onClick={() => {
                                setSelectedData(data);
                                setDetailDialogOpen(true);
                              }}
                            >
                              <Eye size={16} />
                            </IconButton>
                            <IconButton size="small">
                              <Download size={16} />
                            </IconButton>
                            <IconButton size="small" sx={{ color: 'error.main' }}>
                              <Trash2 size={16} />
                            </IconButton>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={filteredData.length}
              page={page}
              onPageChange={(e, p) => setPage(p)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
            />
          </Box>
        </TabPanel>

        {/* 缓存管理 */}
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
              缓存可以加速扫描和翻译操作，但会占用磁盘空间。建议定期清理过期缓存。
            </Alert>

            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Database size={20} style={{ color: minecraftColors.iron }} />
                      <Typography variant="h6">扫描缓存</Typography>
                    </Box>
                    <Typography variant="h4" sx={{ fontFamily: '"Minecraft", monospace', mb: 1 }}>
                      {formatFileSize(268435456)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      432 个文件
                    </Typography>
                    <MinecraftButton
                      fullWidth
                      minecraftStyle="iron"
                      size="small"
                      startIcon={<Trash2 size={14} />}
                    >
                      清理缓存
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>
              <Grid item xs={12} md={4}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <File size={20} style={{ color: minecraftColors.diamondBlue }} />
                      <Typography variant="h6">翻译缓存</Typography>
                    </Box>
                    <Typography variant="h4" sx={{ fontFamily: '"Minecraft", monospace', mb: 1 }}>
                      {formatFileSize(134217728)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      256 个文件
                    </Typography>
                    <MinecraftButton
                      fullWidth
                      minecraftStyle="diamond"
                      size="small"
                      startIcon={<Trash2 size={14} />}
                    >
                      清理缓存
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>
              <Grid item xs={12} md={4}>
                <MinecraftCard variant="inventory">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Zap size={20} style={{ color: minecraftColors.goldYellow }} />
                      <Typography variant="h6">临时文件</Typography>
                    </Box>
                    <Typography variant="h4" sx={{ fontFamily: '"Minecraft", monospace', mb: 1 }}>
                      {formatFileSize(67108864)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      128 个文件
                    </Typography>
                    <MinecraftButton
                      fullWidth
                      minecraftStyle="gold"
                      size="small"
                      startIcon={<Trash2 size={14} />}
                    >
                      清理缓存
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                缓存设置
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch defaultChecked />}
                    label="启用智能缓存"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch defaultChecked />}
                    label="自动清理过期缓存（30天）"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch />}
                    label="压缩缓存文件"
                  />
                </Grid>
              </Grid>
            </Box>
          </Box>
        </TabPanel>

        {/* 备份管理 */}
        <TabPanel value={selectedTab} index={2}>
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace' }}>
                自动备份设置
              </Typography>
              <MinecraftButton
                minecraftStyle="emerald"
                startIcon={<Save size={16} />}
              >
                立即备份
              </MinecraftButton>
            </Box>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <FormControlLabel
                      control={<Switch defaultChecked />}
                      label="启用自动备份"
                      sx={{ mb: 2 }}
                    />
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>备份频率</InputLabel>
                      <Select defaultValue="daily" label="备份频率">
                        <MenuItem value="hourly">每小时</MenuItem>
                        <MenuItem value="daily">每天</MenuItem>
                        <MenuItem value="weekly">每周</MenuItem>
                        <MenuItem value="monthly">每月</MenuItem>
                      </Select>
                    </FormControl>
                    <TextField
                      fullWidth
                      type="number"
                      label="保留备份数量"
                      defaultValue="10"
                      sx={{ mb: 2 }}
                    />
                    <FormControlLabel
                      control={<Switch defaultChecked />}
                      label="备份前验证数据完整性"
                    />
                  </CardContent>
                </MinecraftCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="chest">
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2 }}>
                      备份统计
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">总备份数</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                          15
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">备份总大小</Typography>
                        <Typography variant="body2" sx={{ fontFamily: '"Minecraft", monospace' }}>
                          {formatFileSize(536870912)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">最新备份</Typography>
                        <Typography variant="body2">
                          今天 10:30
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2">下次备份</Typography>
                        <Typography variant="body2">
                          明天 10:30
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                备份历史
              </Typography>
              <List>
                {[1, 2, 3].map((i) => (
                  <ListItem
                    key={i}
                    sx={{
                      bgcolor: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 0,
                      mb: 1
                    }}
                  >
                    <ListItemIcon>
                      <Archive size={20} style={{ color: minecraftColors.emerald }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={`backup_2024032${i}_auto.zip`}
                      secondary={`${formatFileSize(52428800)} - 2024/3/2${i} 10:30`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton edge="end">
                        <Download size={16} />
                      </IconButton>
                      <IconButton edge="end">
                        <RefreshCw size={16} />
                      </IconButton>
                      <IconButton edge="end" sx={{ color: 'error.main' }}>
                        <Trash2 size={16} />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </Box>
          </Box>
        </TabPanel>

        {/* 同步状态 */}
        <TabPanel value={selectedTab} index={3}>
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="enchantment">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Cloud size={20} style={{ color: minecraftColors.diamondBlue }} />
                      <Typography variant="h6">云同步状态</Typography>
                    </Box>
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                        <CheckCircle size={24} style={{ color: minecraftColors.emerald }} />
                        <Typography>已连接到 Trans-Hub</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        上次同步: 5分钟前
                      </Typography>
                    </Box>
                    <MinecraftButton
                      fullWidth
                      minecraftStyle="diamond"
                      startIcon={<RefreshCw size={16} />}
                    >
                      立即同步
                    </MinecraftButton>
                  </CardContent>
                </MinecraftCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <MinecraftCard variant="crafting">
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2 }}>
                      同步队列
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemIcon>
                          <Upload size={16} style={{ color: minecraftColors.emerald }} />
                        </ListItemIcon>
                        <ListItemText
                          primary="ATM10_translations_v1.0.1.json"
                          secondary="等待上传"
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <Download size={16} style={{ color: minecraftColors.diamondBlue }} />
                        </ListItemIcon>
                        <ListItemText
                          primary="twilightforest_lang.json"
                          secondary="正在下载... 45%"
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </MinecraftCard>
              </Grid>
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
                同步设置
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch defaultChecked />}
                    label="自动同步翻译文件"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch defaultChecked />}
                    label="同步项目配置"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch />}
                    label="同步缓存数据"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Switch defaultChecked />}
                    label="冲突时保留本地版本"
                  />
                </Grid>
              </Grid>
            </Box>
          </Box>
        </TabPanel>
      </Paper>

      {/* 详情对话框 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
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
          文件详情
        </DialogTitle>
        <DialogContent>
          {selectedData && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  {getTypeIcon(selectedData.type)}
                  <Typography variant="h6">{selectedData.name}</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">类型</Typography>
                <Typography>{selectedData.type}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">大小</Typography>
                <Typography>{formatFileSize(selectedData.size)}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">创建时间</Typography>
                <Typography>{selectedData.created.toLocaleString()}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">修改时间</Typography>
                <Typography>{selectedData.modified.toLocaleString()}</Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">路径</Typography>
                <Typography sx={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {selectedData.path}{selectedData.name}
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">标签</Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                  {selectedData.tags.map(tag => (
                    <Chip key={tag} label={tag} size="small" />
                  ))}
                </Box>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setDetailDialogOpen(false)}
          >
            关闭
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* 清理对话框 */}
      <Dialog
        open={cleanupDialogOpen}
        onClose={() => setCleanupDialogOpen(false)}
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
          清理存储空间
        </DialogTitle>
        <DialogContent>
          <Alert
            severity="warning"
            sx={{
              mb: 2,
              bgcolor: 'rgba(255, 152, 0, 0.1)',
              border: '1px solid #FF9800'
            }}
          >
            清理操作不可恢复，请确保重要数据已备份
          </Alert>
          <List>
            <ListItem button onClick={() => handleCleanup('cache')}>
              <ListItemIcon>
                <Database size={20} />
              </ListItemIcon>
              <ListItemText
                primary="清理所有缓存"
                secondary={`释放约 ${formatFileSize(storageStats.cacheSize)}`}
              />
            </ListItem>
            <ListItem button onClick={() => handleCleanup('backup')}>
              <ListItemIcon>
                <Archive size={20} />
              </ListItemIcon>
              <ListItemText
                primary="清理旧备份（保留最近7天）"
                secondary={`释放约 ${formatFileSize(storageStats.backupSize / 2)}`}
              />
            </ListItem>
            <ListItem button onClick={() => handleCleanup('all')}>
              <ListItemIcon>
                <Trash2 size={20} />
              </ListItemIcon>
              <ListItemText
                primary="深度清理"
                secondary="清理所有缓存和过期文件"
              />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setCleanupDialogOpen(false)}
          >
            取消
          </MinecraftButton>
        </DialogActions>
      </Dialog>

      {/* 导入对话框 */}
      <Dialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
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
          导入数据
        </DialogTitle>
        <DialogContent>
          <Box
            sx={{
              border: '2px dashed #2A2A4E',
              borderRadius: 0,
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.02)'
              }
            }}
          >
            <Upload size={48} style={{ color: minecraftColors.iron, marginBottom: 16 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>
              拖拽文件到这里
            </Typography>
            <Typography variant="body2" color="text.secondary">
              或点击选择文件
            </Typography>
          </Box>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              支持的格式: JSON, ZIP, 项目文件 (.proj)
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <MinecraftButton
            minecraftStyle="stone"
            onClick={() => setImportDialogOpen(false)}
          >
            取消
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="emerald"
            onClick={() => setImportDialogOpen(false)}
          >
            导入
          </MinecraftButton>
        </DialogActions>
      </Dialog>
    </Box>
  );
}