/**
 * 占位页面组件
 * 用于正在重构的页面
 */

import React from 'react';
import { Box, Typography, Alert } from '@mui/material';
import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description: string;
  features?: string[];
}

export default function PlaceholderPage({ title, description, features = [] }: PlaceholderPageProps) {
  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Construction size={32} />
        {title} - 最优架构
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        {description}
      </Typography>

      <Alert severity="info">
        <strong>该功能正在使用最优架构重构中...</strong>
        {features.length > 0 && (
          <>
            <br />
            {features.map((feature, index) => (
              <React.Fragment key={index}>
                • {feature}
                <br />
              </React.Fragment>
            ))}
          </>
        )}
      </Alert>
    </Box>
  );
}