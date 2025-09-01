import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Chip,
} from '@mui/material';
import {
  PlayArrow,
  Settings,
  Folder,
  Language,
} from '@mui/icons-material';

export const WelcomeCard: React.FC = () => {
  


  return (
    <Card sx={{ maxWidth: 600, margin: 'auto', mt: 4 }}>
      <CardContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            TH Suite MC L10n
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Minecraft 资源管理工具
          </Typography>
          <Typography variant="body2" color="text.secondary">
            专为 Minecraft 模组和资源包创作者设计的综合工具包，提供资源分析、提取和构建功能。
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
          <Chip
            icon={<Folder />}
            label="模组包处理"
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<Language />}
            label="模组本地化"
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<Settings />}
            label="版本适配"
            variant="outlined"
            size="small"
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            size="large"
          >
            开始使用
          </Button>
          <Button
            variant="outlined"
            startIcon={<Folder />}
            size="large"
          >
            提取资源
          </Button>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            size="large"
          >
            设置
          </Button>
        </Box>

        <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
          <Typography variant="h6" gutterBottom>
            资源提取工作流
          </Typography>
          <Typography variant="body2" color="text.secondary">
            正在扫描项目文件...
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default WelcomeCard;