/**
 * 提取页面 - 最优化版本
 * 使用新的服务架构
 */

import React from 'react'
import { Box, Typography, Alert } from '@mui/material'
import { Package } from 'lucide-react'

export default function ExtractPageOptimal() {
  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Typography variant='h4' gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Package size={32} />
        提取管理 - 最优架构
      </Typography>

      <Typography variant='body1' color='text.secondary' sx={{ mb: 4 }}>
        从JAR文件和资源包中提取翻译内容。
      </Typography>

      <Alert severity='info'>
        <strong>提取功能正在使用最优架构重构中...</strong>
        <br />
        • 统一的文件处理服务
        <br />
        • 类型安全的解析器
        <br />
        • 现代化的React Hooks
        <br />• 完整的进度跟踪
      </Alert>
    </Box>
  )
}
