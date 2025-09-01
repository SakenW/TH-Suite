/**
 * 导出页面 - 最优化版本
 * 使用新的服务架构
 */

import React from 'react';
import { Box, Typography, Alert } from '@mui/material';
import { Download } from 'lucide-react';

export default function ExportPageOptimal() {
  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Download size={32} />
        导出管理 - 最优架构
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        导出翻译文件到各种格式。
      </Typography>

      <Alert severity="info">
        <strong>导出功能正在使用最优架构重构中...</strong>
        <br />
        • 统一的服务调用模式
        <br />
        • 类型安全的API访问
        <br />
        • 现代化的状态管理
        <br />
        • 完整的错误处理机制
      </Alert>
    </Box>
  );
}