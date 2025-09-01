/**
 * 项目卡片组件
 * 重构后的项目展示组件，使用新的 API 架构
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  IconButton,
  Chip,
  Box,
  Collapse,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  LinearProgress,
} from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import { motion } from 'framer-motion';
import {
  FolderOpen,
  MoreVertical,
  Edit,
  Archive,
  Trash2,
  Download,
  Copy,
  ChevronDown,
  ChevronUp,
  Package,
  FileText,
  Settings,
} from 'lucide-react';
import { Project } from '../../types/api';
import { useApi } from '../../hooks/useApi';
import { projectService } from '../../services';
import toast from 'react-hot-toast';

interface ProjectCardProps {
  project: Project;
  isSelected?: boolean;
  onSelect?: (project: Project) => void;
  onEdit?: (project: Project) => void;
  onDelete?: (project: Project) => void;
  onRefresh?: () => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  isSelected = false,
  onSelect,
  onEdit,
  onDelete,
  onRefresh,
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // API hooks
  const { execute: archiveProject, loading: archiving } = useApi(
    () => projectService.archiveProject(project.id),
    false
  );

  const { execute: duplicateProject, loading: duplicating } = useApi(
    () => projectService.duplicateProject(project.id),
    false
  );

  const { execute: getStatistics, data: statistics, loading: loadingStats } = useApi(
    () => projectService.getProjectStatistics(project.id),
    false
  );

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleCardClick = () => {
    if (onSelect) {
      onSelect(project);
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    handleMenuClose();
    if (onEdit) {
      onEdit(project);
    }
  };

  const handleArchive = async (e: React.MouseEvent) => {
    e.stopPropagation();
    handleMenuClose();
    
    try {
      const result = await archiveProject();
      if (result) {
        toast.success(project.status === 'active' ? '项目已归档' : '项目已恢复');
        if (onRefresh) onRefresh();
      }
    } catch (error) {
      toast.error('操作失败');
    }
  };

  const handleDuplicate = async (e: React.MouseEvent) => {
    e.stopPropagation();
    handleMenuClose();
    
    try {
      const result = await duplicateProject();
      if (result) {
        toast.success('项目复制成功');
        if (onRefresh) onRefresh();
      }
    } catch (error) {
      toast.error('复制失败');
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    handleMenuClose();
    if (onDelete) {
      onDelete(project);
    }
  };

  const handleToggleExpanded = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
    
    // 首次展开时加载统计数据
    if (!expanded && !statistics) {
      getStatistics();
    }
  };

  const getProjectTypeColor = (type: string) => {
    switch (type) {
      case 'mod':
        return theme.palette.secondary.main;
      case 'resource_pack':
        return theme.palette.warning.main;
      case 'mixed':
        return theme.palette.info.main;
      default:
        return theme.palette.primary.main;
    }
  };

  const getProjectTypeLabel = (type: string) => {
    switch (type) {
      case 'mod':
        return '模组';
      case 'resource_pack':
        return '资源包';
      case 'mixed':
        return '混合';
      default:
        return type;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'archived':
        return 'default';
      case 'paused':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return '活跃';
      case 'archived':
        return '已归档';
      case 'paused':
        return '暂停';
      default:
        return status;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          border: isSelected 
            ? `2px solid ${getProjectTypeColor(project.project_type)}` 
            : `1px solid ${alpha(theme.palette.divider, 0.2)}`,
          borderRadius: 3,
          background: project.status === 'archived' 
            ? alpha(theme.palette.action.disabled, 0.05)
            : 'transparent',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: theme.shadows[8],
            borderColor: getProjectTypeColor(project.project_type),
          },
        }}
        onClick={handleCardClick}
      >
        {/* 加载指示器 */}
        {(archiving || duplicating) && (
          <LinearProgress 
            sx={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0, 
              borderRadius: '12px 12px 0 0' 
            }} 
          />
        )}

        <CardContent sx={{ flexGrow: 1, pb: 1 }}>
          {/* 头部信息 */}
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                label={getProjectTypeLabel(project.project_type)}
                size="small"
                sx={{
                  backgroundColor: alpha(getProjectTypeColor(project.project_type), 0.1),
                  color: getProjectTypeColor(project.project_type),
                  fontWeight: 600,
                }}
              />
              <Chip
                label={getStatusLabel(project.status)}
                size="small"
                color={getStatusColor(project.status) as any}
                variant={project.status === 'active' ? 'filled' : 'outlined'}
              />
            </Box>
            
            <IconButton
              size="small"
              onClick={handleMenuClick}
              sx={{ opacity: 0.7, '&:hover': { opacity: 1 } }}
            >
              <MoreVertical size={16} />
            </IconButton>
          </Box>

          {/* 项目名称和描述 */}
          <Typography 
            variant="h6" 
            sx={{ 
              mb: 1, 
              fontWeight: 700, 
              fontSize: '1.1rem',
              color: project.status === 'archived' ? 'text.secondary' : 'text.primary',
            }}
          >
            {project.name}
          </Typography>
          
          <Typography 
            variant="body2" 
            color="text.secondary" 
            sx={{ 
              mb: 2, 
              lineHeight: 1.5,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {project.description || '暂无描述'}
          </Typography>

          {/* 语言支持 */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
            {project.supported_languages?.slice(0, 3).map((lang) => (
              <Chip
                key={lang}
                label={lang}
                size="small"
                variant="outlined"
                sx={{ 
                  fontSize: '0.7rem', 
                  height: 20,
                  '& .MuiChip-label': { px: 1 }
                }}
              />
            ))}
            {project.supported_languages && project.supported_languages.length > 3 && (
              <Chip
                label={`+${project.supported_languages.length - 3}`}
                size="small"
                variant="outlined"
                sx={{ 
                  fontSize: '0.7rem', 
                  height: 20,
                  '& .MuiChip-label': { px: 1 }
                }}
              />
            )}
          </Box>

          {/* 时间信息 */}
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
            更新时间: {new Date(project.updated_at).toLocaleDateString('zh-CN')}
          </Typography>
        </CardContent>

        <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
          <IconButton
            size="small"
            color="primary"
            onClick={(e) => {
              e.stopPropagation();
              if (onSelect) onSelect(project);
            }}
            title="打开项目"
            disabled={project.status === 'archived'}
          >
            <FolderOpen size={16} />
          </IconButton>

          <IconButton
            size="small"
            onClick={handleToggleExpanded}
            title={expanded ? "收起详情" : "展开详情"}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </IconButton>
        </CardActions>

        {/* 展开内容 */}
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Box sx={{ px: 2, pb: 2 }}>
            <Divider sx={{ mb: 2 }} />
            
            {/* 项目路径 */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                项目路径
              </Typography>
              <Typography 
                variant="body2" 
                sx={{ 
                  fontFamily: 'monospace', 
                  fontSize: '0.8rem',
                  wordBreak: 'break-all',
                  color: 'text.secondary',
                  backgroundColor: alpha(theme.palette.divider, 0.1),
                  padding: '4px 8px',
                  borderRadius: 1,
                }}
              >
                {project.source_path}
              </Typography>
            </Box>

            {/* 统计信息 */}
            {loadingStats ? (
              <Box sx={{ py: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  加载统计信息...
                </Typography>
              </Box>
            ) : statistics?.data && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
                  项目统计
                </Typography>
                <List dense sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0, py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Package size={14} />
                    </ListItemIcon>
                    <ListItemText
                      primary={`总条目: ${statistics.data.total_entries || 0}`}
                      primaryTypographyProps={{ variant: 'body2', fontSize: '0.85rem' }}
                    />
                  </ListItem>
                  <ListItem sx={{ px: 0, py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <FileText size={14} />
                    </ListItemIcon>
                    <ListItemText
                      primary={`已翻译: ${statistics.data.translated_entries || 0}`}
                      primaryTypographyProps={{ variant: 'body2', fontSize: '0.85rem' }}
                    />
                  </ListItem>
                  <ListItem sx={{ px: 0, py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Settings size={14} />
                    </ListItemIcon>
                    <ListItemText
                      primary={`进度: ${Math.round(statistics.data.translation_progress || 0)}%`}
                      primaryTypographyProps={{ variant: 'body2', fontSize: '0.85rem' }}
                    />
                  </ListItem>
                </List>
              </Box>
            )}
          </Box>
        </Collapse>

        {/* 菜单 */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <MenuItem onClick={handleEdit} disabled={project.status === 'archived'}>
            <Edit size={16} style={{ marginRight: 8 }} />
            编辑
          </MenuItem>
          <MenuItem onClick={handleDuplicate} disabled={duplicating}>
            <Copy size={16} style={{ marginRight: 8 }} />
            复制
          </MenuItem>
          <MenuItem onClick={handleArchive} disabled={archiving}>
            <Archive size={16} style={{ marginRight: 8 }} />
            {project.status === 'active' ? '归档' : '恢复'}
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
            <Trash2 size={16} style={{ marginRight: 8 }} />
            删除
          </MenuItem>
        </Menu>
      </Card>
    </motion.div>
  );
};