/**
 * 页面容器组件
 * 提供统一的页面内容布局和间距
 */

import React from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Breadcrumbs,
  Link,
  Chip,
  Stack,
  Fade,
  useMediaQuery,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import { ChevronRight, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';

interface PageAction {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'outlined';
  disabled?: boolean;
  icon?: React.ReactNode;
}

interface PageBreadcrumb {
  label: string;
  path?: string;
  onClick?: () => void;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  description?: string;
  breadcrumbs?: PageBreadcrumb[];
  actions?: PageAction[];
  tags?: string[];
  backAction?: {
    label?: string;
    onClick: () => void;
  };
}

interface PageContainerProps {
  children: React.ReactNode;
  header?: PageHeaderProps;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
  disableGutters?: boolean;
  background?: 'default' | 'paper' | 'transparent';
  padding?: number | string;
  animate?: boolean;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  description,
  breadcrumbs,
  actions,
  tags,
  backAction,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <Box sx={{ mb: 4 }}>
      {/* 面包屑导航 */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumbs
          separator={<ChevronRight size={16} />}
          sx={{ mb: 2 }}
        >
          {breadcrumbs.map((breadcrumb, index) => (
            <Link
              key={index}
              component="button"
              variant="body2"
              onClick={breadcrumb.onClick}
              sx={{
                textDecoration: 'none',
                color: index === breadcrumbs.length - 1 ? 'text.primary' : 'text.secondary',
                fontWeight: index === breadcrumbs.length - 1 ? 600 : 400,
                '&:hover': {
                  color: 'primary.main',
                  textDecoration: breadcrumb.onClick ? 'underline' : 'none',
                },
                cursor: breadcrumb.onClick ? 'pointer' : 'default',
              }}
            >
              {breadcrumb.label}
            </Link>
          ))}
        </Breadcrumbs>
      )}

      {/* 返回按钮 */}
      {backAction && (
        <Box sx={{ mb: 2 }}>
          <Link
            component="button"
            variant="body2"
            onClick={backAction.onClick}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              textDecoration: 'none',
              color: 'text.secondary',
              '&:hover': {
                color: 'primary.main',
                textDecoration: 'underline',
              },
            }}
          >
            <ArrowLeft size={16} />
            {backAction.label || '返回'}
          </Link>
        </Box>
      )}

      {/* 页面标题区域 */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          alignItems: isMobile ? 'flex-start' : 'flex-end',
          justifyContent: 'space-between',
          gap: 2,
          mb: 2,
        }}
      >
        <Box sx={{ flex: 1 }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Typography
              variant="h4"
              sx={{
                fontWeight: 700,
                mb: subtitle ? 0.5 : 0,
                background: `linear-gradient(135deg, ${theme.palette.text.primary}, ${alpha(theme.palette.text.primary, 0.7)})`,
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {title}
            </Typography>
            {subtitle && (
              <Typography
                variant="h6"
                color="text.secondary"
                sx={{ fontWeight: 400, mb: 1 }}
              >
                {subtitle}
              </Typography>
            )}
            {description && (
              <Typography
                variant="body1"
                color="text.secondary"
                sx={{ maxWidth: 600 }}
              >
                {description}
              </Typography>
            )}
          </motion.div>
        </Box>

        {/* 操作按钮组 */}
        {actions && actions.length > 0 && (
          <Stack
            direction={isMobile ? 'column' : 'row'}
            spacing={1}
            sx={{ minWidth: isMobile ? '100%' : 'auto' }}
          >
            {actions.map((action, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Box
                  component="button"
                  onClick={action.onClick}
                  disabled={action.disabled}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    px: 3,
                    py: 1.5,
                    border: 'none',
                    borderRadius: 2,
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    cursor: action.disabled ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease-in-out',
                    minWidth: isMobile ? '100%' : 'auto',
                    justifyContent: isMobile ? 'center' : 'flex-start',
                    ...(action.variant === 'primary' && {
                      backgroundColor: theme.palette.primary.main,
                      color: theme.palette.primary.contrastText,
                      '&:hover': {
                        backgroundColor: theme.palette.primary.dark,
                        transform: 'translateY(-1px)',
                        boxShadow: theme.shadows[4],
                      },
                    }),
                    ...(action.variant === 'secondary' && {
                      backgroundColor: theme.palette.secondary.main,
                      color: theme.palette.secondary.contrastText,
                      '&:hover': {
                        backgroundColor: theme.palette.secondary.dark,
                        transform: 'translateY(-1px)',
                        boxShadow: theme.shadows[4],
                      },
                    }),
                    ...(action.variant === 'outlined' && {
                      backgroundColor: 'transparent',
                      color: theme.palette.primary.main,
                      border: `1px solid ${theme.palette.primary.main}`,
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.primary.main, 0.05),
                        transform: 'translateY(-1px)',
                        boxShadow: theme.shadows[2],
                      },
                    }),
                    ...(!action.variant && {
                      backgroundColor: alpha(theme.palette.action.hover, 0.5),
                      color: theme.palette.text.primary,
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.action.hover, 0.8),
                        transform: 'translateY(-1px)',
                        boxShadow: theme.shadows[2],
                      },
                    }),
                    ...(action.disabled && {
                      opacity: 0.5,
                      '&:hover': {
                        transform: 'none',
                        boxShadow: 'none',
                      },
                    }),
                  }}
                >
                  {action.icon}
                  {action.label}
                </Box>
              </motion.div>
            ))}
          </Stack>
        )}
      </Box>

      {/* 标签 */}
      {tags && tags.length > 0 && (
        <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
          {tags.map((tag, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <Chip
                label={tag}
                size="small"
                variant="outlined"
                sx={{
                  backgroundColor: alpha(theme.palette.primary.main, 0.05),
                  borderColor: alpha(theme.palette.primary.main, 0.2),
                  color: theme.palette.primary.main,
                }}
              />
            </motion.div>
          ))}
        </Stack>
      )}
    </Box>
  );
};

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  header,
  maxWidth = 'xl',
  disableGutters = false,
  background = 'default',
  padding,
  animate = true,
}) => {
  const theme = useTheme();

  const getBackgroundColor = () => {
    switch (background) {
      case 'paper':
        return theme.palette.background.paper;
      case 'transparent':
        return 'transparent';
      case 'default':
      default:
        return theme.palette.background.default;
    }
  };

  const containerContent = (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: getBackgroundColor(),
        py: padding || 3,
      }}
    >
      <Container
        maxWidth={maxWidth}
        disableGutters={disableGutters}
        sx={{
          px: disableGutters ? 0 : { xs: 2, sm: 3 },
        }}
      >
        {header && <PageHeader {...header} />}
        
        <Box sx={{ position: 'relative' }}>
          {animate ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              {children}
            </motion.div>
          ) : (
            children
          )}
        </Box>
      </Container>
    </Box>
  );

  return background === 'paper' ? (
    <Paper elevation={0} sx={{ minHeight: '100vh' }}>
      {containerContent}
    </Paper>
  ) : (
    containerContent
  );
};