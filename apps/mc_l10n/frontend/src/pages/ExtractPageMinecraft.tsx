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
  Checkbox,
  Alert
} from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Package,
  FileArchive,
  FileJson,
  FileText,
  FolderOpen,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Download,
  Eye,
  Filter,
  Layers,
  Archive,
  Zap,
  Clock,
  Hash
} from 'lucide-react';
import toast from 'react-hot-toast';

import { MinecraftButton } from '../components/minecraft/MinecraftButton';
import { MinecraftCard } from '../components/minecraft/MinecraftCard';
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress';
import { MinecraftBlock } from '../components/MinecraftComponents';

interface ExtractItem {
  id: string;
  name: string;
  type: 'jar' | 'zip' | 'folder';
  path: string;
  size: number;
  status: 'pending' | 'extracting' | 'completed' | 'error';
  progress: number;
  langFiles: number;
  keys: number;
  selected: boolean;
  error?: string;
}

const mockExtractItems: ExtractItem[] = [
  {
    id: '1',
    name: 'applied-energistics-2.jar',
    type: 'jar',
    path: 'mods/applied-energistics-2.jar',
    size: 12450000,
    status: 'completed',
    progress: 100,
    langFiles: 12,
    keys: 1250,
    selected: false
  },
  {
    id: '2',
    name: 'create-mod.jar',
    type: 'jar',
    path: 'mods/create-mod.jar',
    size: 8920000,
    status: 'extracting',
    progress: 65,
    langFiles: 8,
    keys: 890,
    selected: true
  },
  {
    id: '3',
    name: 'twilightforest.jar',
    type: 'jar',
    path: 'mods/twilightforest.jar',
    size: 15600000,
    status: 'pending',
    progress: 0,
    langFiles: 0,
    keys: 0,
    selected: true
  },
  {
    id: '4',
    name: 'resourcepacks.zip',
    type: 'zip',
    path: 'resourcepacks/custom-pack.zip',
    size: 3200000,
    status: 'error',
    progress: 0,
    langFiles: 0,
    keys: 0,
    selected: false,
    error: '文件损坏或格式不支持'
  }
];

export default function ExtractPageMinecraft() {
  const [items, setItems] = useState<ExtractItem[]>(mockExtractItems);
  const [isExtracting, setIsExtracting] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed' | 'error'>('all');
  const [selectedCount, setSelectedCount] = useState(2);

  const handleSelectAll = (checked: boolean) => {
    setItems(prev => prev.map(item => ({ ...item, selected: checked })));
    setSelectedCount(checked ? items.length : 0);
  };

  const handleSelectItem = (id: string) => {
    setItems(prev => prev.map(item =>
      item.id === id ? { ...item, selected: !item.selected } : item
    ));
    const newSelected = items.filter(item => 
      item.id === id ? !item.selected : item.selected
    ).length;
    setSelectedCount(newSelected);
  };

  const handleStartExtraction = () => {
    if (selectedCount === 0) {
      toast.error('请选择要提取的文件', { icon: '⚠️' });
      return;
    }
    setIsExtracting(true);
    toast.success(`开始提取 ${selectedCount} 个文件`, { icon: '🚀' });
    
    // 模拟提取进度
    const interval = setInterval(() => {
      setItems(prev => prev.map(item => {
        if (item.selected && item.status === 'pending') {
          return { ...item, status: 'extracting', progress: 0 };
        }
        if (item.status === 'extracting' && item.progress < 100) {
          const newProgress = Math.min(100, item.progress + Math.random() * 20);
          if (newProgress >= 100) {
            return {
              ...item,
              status: 'completed',
              progress: 100,
              langFiles: Math.floor(Math.random() * 20) + 5,
              keys: Math.floor(Math.random() * 2000) + 500
            };
          }
          return { ...item, progress: newProgress };
        }
        return item;
      }));
    }, 500);

    setTimeout(() => {
      clearInterval(interval);
      setIsExtracting(false);
      toast.success('提取完成！', { icon: '✅' });
    }, 5000);
  };

  const handleStopExtraction = () => {
    setIsExtracting(false);
    toast.success('已停止提取', { icon: '⏹️' });
  };

  const handleAddFiles = () => {
    toast.info('选择要提取的文件...', { icon: '📁' });
  };

  const handleViewDetails = (item: ExtractItem) => {
    toast.info(`查看 ${item.name} 详情`, { icon: '👁️' });
  };

  const formatSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} color="#4CAF50" />;
      case 'extracting': return <Clock size={16} color="#2196F3" />;
      case 'error': return <XCircle size={16} color="#F44336" />;
      default: return <AlertTriangle size={16} color="#FF9800" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'jar': return <Package size={20} color="#FFD700" />;
      case 'zip': return <FileArchive size={20} color="#9C27B0" />;
      case 'folder': return <FolderOpen size={20} color="#2196F3" />;
      default: return <FileText size={20} />;
    }
  };

  const filteredItems = items.filter(item => {
    if (filter === 'all') return true;
    return item.status === filter;
  });

  const stats = {
    total: items.length,
    completed: items.filter(i => i.status === 'completed').length,
    extracting: items.filter(i => i.status === 'extracting').length,
    error: items.filter(i => i.status === 'error').length,
    totalLangFiles: items.reduce((sum, i) => sum + i.langFiles, 0),
    totalKeys: items.reduce((sum, i) => sum + i.keys, 0)
  };

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
              background: 'linear-gradient(135deg, #FF6347 0%, #FFD700 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              mb: 1,
            }}
          >
            📦 提取管理
          </Typography>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '14px',
              color: 'text.secondary',
            }}
          >
            从JAR文件和资源包中提取语言文件
          </Typography>
        </Box>
      </motion.div>

      <Grid container spacing={3}>
        {/* 统计信息 */}
        <Grid item xs={12}>
          <Grid container spacing={2}>
            <Grid item xs={6} md={2}>
              <MinecraftCard variant="inventory">
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <Archive size={24} />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#FFFFFF',
                      mt: 1,
                    }}
                  >
                    {stats.total}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    总文件数
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={2}>
              <MinecraftCard variant="inventory">
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <CheckCircle size={24} color="#4CAF50" />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#4CAF50',
                      mt: 1,
                    }}
                  >
                    {stats.completed}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    已完成
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={2}>
              <MinecraftCard variant="inventory">
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <Clock size={24} color="#2196F3" />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#2196F3',
                      mt: 1,
                    }}
                  >
                    {stats.extracting}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    提取中
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={2}>
              <MinecraftCard variant="inventory">
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <XCircle size={24} color="#F44336" />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#F44336',
                      mt: 1,
                    }}
                  >
                    {stats.error}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    错误
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={2}>
              <MinecraftCard variant="inventory">
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <FileText size={24} color="#FFD700" />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#FFD700',
                      mt: 1,
                    }}
                  >
                    {stats.totalLangFiles}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    语言文件
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
            <Grid item xs={6} md={2}>
              <MinecraftCard variant="inventory">
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <Hash size={24} color="#9C27B0" />
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '20px',
                      color: '#9C27B0',
                      mt: 1,
                    }}
                  >
                    {stats.totalKeys.toLocaleString()}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '10px',
                      color: 'text.secondary',
                    }}
                  >
                    翻译键
                  </Typography>
                </Box>
              </MinecraftCard>
            </Grid>
          </Grid>
        </Grid>

        {/* 工具栏 */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <MinecraftButton
              minecraftStyle="gold"
              onClick={handleAddFiles}
              startIcon={<Plus size={16} />}
            >
              添加文件
            </MinecraftButton>
            {!isExtracting ? (
              <MinecraftButton
                minecraftStyle="emerald"
                onClick={handleStartExtraction}
                startIcon={<Play size={16} />}
                disabled={selectedCount === 0}
                glowing
              >
                开始提取 ({selectedCount})
              </MinecraftButton>
            ) : (
              <MinecraftButton
                minecraftStyle="redstone"
                onClick={handleStopExtraction}
                startIcon={<Pause size={16} />}
              >
                停止提取
              </MinecraftButton>
            )}
            <Box sx={{ flex: 1 }} />
            <MinecraftButton
              minecraftStyle={filter === 'all' ? 'diamond' : 'stone'}
              onClick={() => setFilter('all')}
              variant={filter === 'all' ? 'minecraft' : 'outlined'}
            >
              全部
            </MinecraftButton>
            <MinecraftButton
              minecraftStyle={filter === 'completed' ? 'emerald' : 'stone'}
              onClick={() => setFilter('completed')}
              variant={filter === 'completed' ? 'minecraft' : 'outlined'}
            >
              已完成
            </MinecraftButton>
            <MinecraftButton
              minecraftStyle={filter === 'error' ? 'redstone' : 'stone'}
              onClick={() => setFilter('error')}
              variant={filter === 'error' ? 'minecraft' : 'outlined'}
            >
              错误
            </MinecraftButton>
          </Box>
        </Grid>

        {/* 文件列表 */}
        <Grid item xs={12}>
          <MinecraftCard variant="chest" title="文件列表" icon="gold">
            <Box sx={{ p: 2 }}>
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectedCount === items.length}
                      indeterminate={selectedCount > 0 && selectedCount < items.length}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                      sx={{ color: '#FFD700' }}
                    />
                  }
                  label={
                    <Typography sx={{ fontFamily: '"Minecraft", monospace', fontSize: '12px' }}>
                      全选
                    </Typography>
                  }
                />
              </Box>
              <List>
                <AnimatePresence>
                  {filteredItems.map((item, index) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                    >
                      <ListItem
                        sx={{
                          mb: 1,
                          background: item.selected
                            ? 'linear-gradient(90deg, rgba(255,215,0,0.1) 0%, transparent 100%)'
                            : 'rgba(0,0,0,0.2)',
                          border: `1px solid ${item.selected ? '#FFD700' : '#4A4A4A'}`,
                          borderRadius: 0,
                          '&:hover': {
                            background: 'rgba(255,255,255,0.05)',
                          },
                        }}
                      >
                        <ListItemIcon>
                          <Checkbox
                            checked={item.selected}
                            onChange={() => handleSelectItem(item.id)}
                            sx={{ color: '#FFD700' }}
                          />
                        </ListItemIcon>
                        <ListItemIcon>
                          {getTypeIcon(item.type)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography
                                sx={{
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '14px',
                                  color: '#FFFFFF',
                                }}
                              >
                                {item.name}
                              </Typography>
                              {getStatusIcon(item.status)}
                              <Chip
                                label={formatSize(item.size)}
                                size="small"
                                sx={{
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '10px',
                                  height: 20,
                                  background: 'rgba(0,0,0,0.3)',
                                  borderRadius: 0,
                                }}
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography
                                sx={{
                                  fontFamily: '"Minecraft", monospace',
                                  fontSize: '11px',
                                  color: 'text.secondary',
                                }}
                              >
                                {item.path}
                              </Typography>
                              {item.status === 'extracting' && (
                                <Box sx={{ mt: 1 }}>
                                  <MinecraftProgress
                                    value={item.progress}
                                    variant="loading"
                                    size="small"
                                    animated
                                  />
                                </Box>
                              )}
                              {item.status === 'completed' && (
                                <Box sx={{ mt: 1, display: 'flex', gap: 2 }}>
                                  <Typography
                                    sx={{
                                      fontFamily: '"Minecraft", monospace',
                                      fontSize: '10px',
                                      color: '#4CAF50',
                                    }}
                                  >
                                    {item.langFiles} 语言文件
                                  </Typography>
                                  <Typography
                                    sx={{
                                      fontFamily: '"Minecraft", monospace',
                                      fontSize: '10px',
                                      color: '#2196F3',
                                    }}
                                  >
                                    {item.keys} 翻译键
                                  </Typography>
                                </Box>
                              )}
                              {item.error && (
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
                                  {item.error}
                                </Alert>
                              )}
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Tooltip title="查看详情">
                            <IconButton
                              size="small"
                              onClick={() => handleViewDetails(item)}
                            >
                              <Eye size={16} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="下载结果">
                            <IconButton
                              size="small"
                              disabled={item.status !== 'completed'}
                            >
                              <Download size={16} />
                            </IconButton>
                          </Tooltip>
                        </ListItemSecondaryAction>
                      </ListItem>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </List>
            </Box>
          </MinecraftCard>
        </Grid>

        {/* 操作提示 */}
        {isExtracting && (
          <Grid item xs={12}>
            <Alert
              severity="info"
              icon={<Zap size={20} />}
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '12px',
                background: 'linear-gradient(135deg, rgba(33,150,243,0.2) 0%, rgba(0,0,0,0.2) 100%)',
                border: '2px solid #2196F3',
                borderRadius: 0,
              }}
            >
              正在提取文件，请稍候...处理速度取决于文件大小和数量
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}