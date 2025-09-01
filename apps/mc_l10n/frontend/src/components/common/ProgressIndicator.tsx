/**
 * 进度指示器组件
 * 多样化的进度展示组件，支持线性、圆形、步骤等形式
 */

import React from 'react';
import {
  Box,
  LinearProgress,
  CircularProgress,
  Typography,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  StepConnector,
  Chip,
} from '@mui/material';
import { useTheme, alpha, styled } from '@mui/material/styles';
import {
  CheckCircle,
  Circle,
  Clock,
  Zap,
  TrendingUp,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ProgressIndicatorProps {
  // 基础属性
  value: number; // 0-100
  variant?: 'linear' | 'circular' | 'card' | 'stepper' | 'mini' | 'dashboard';
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  
  // 显示选项
  showValue?: boolean;
  showLabel?: boolean;
  label?: string;
  buffer?: number; // 缓冲进度 (仅限linear)
  
  // 步骤进度 (仅限stepper)
  steps?: Array<{
    label: string;
    description?: string;
    completed?: boolean;
    active?: boolean;
  }>;
  
  // 卡片样式属性
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  animated?: boolean;
  
  // 仪表板样式属性
  segments?: Array<{
    label: string;
    value: number;
    color: string;
  }>;
}

// 自定义步骤连接器
const CustomStepConnector = styled(StepConnector)(({ theme }) => ({
  '&.Mui-active': {
    '& .MuiStepConnector-line': {
      borderColor: theme.palette.primary.main,
    },
  },
  '&.Mui-completed': {
    '& .MuiStepConnector-line': {
      borderColor: theme.palette.success.main,
    },
  },
}));

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  value,
  variant = 'linear',
  size = 'medium',
  color = 'primary',
  showValue = true,
  showLabel = true,
  label,
  buffer,
  steps = [],
  title,
  subtitle,
  icon,
  animated = false,
  segments = [],
}) => {
  const theme = useTheme();

  const getColorValue = (colorName: string) => {
    switch (colorName) {
      case 'secondary': return theme.palette.secondary.main;
      case 'success': return theme.palette.success.main;
      case 'warning': return theme.palette.warning.main;
      case 'error': return theme.palette.error.main;
      case 'info': return theme.palette.info.main;
      case 'primary':
      default: return theme.palette.primary.main;
    }
  };

  const getSize = () => {
    switch (size) {
      case 'small': return { width: 100, height: 4, circular: 32 };
      case 'large': return { width: 300, height: 8, circular: 80 };
      case 'medium':
      default: return { width: 200, height: 6, circular: 56 };
    }
  };

  const sizeConfig = getSize();
  const colorValue = getColorValue(color);

  const formatValue = (val: number) => `${Math.round(val)}%`;

  const renderLinearProgress = () => (
    <Box sx={{ width: '100%' }}>
      {(showLabel && label) && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
          {showValue && (
            <Typography variant="body2" color="text.secondary">
              {formatValue(value)}
            </Typography>
          )}
        </Box>
      )}
      
      <LinearProgress
        variant={buffer !== undefined ? 'buffer' : 'determinate'}
        value={value}
        valueBuffer={buffer}
        sx={{
          height: sizeConfig.height,
          borderRadius: sizeConfig.height / 2,
          backgroundColor: alpha(colorValue, 0.1),
          '& .MuiLinearProgress-bar': {
            backgroundColor: colorValue,
            borderRadius: sizeConfig.height / 2,
            transition: animated ? 'transform 1s ease-in-out' : 'none',
          },
          ...(buffer !== undefined && {
            '& .MuiLinearProgress-bar2Buffer': {
              backgroundColor: alpha(colorValue, 0.3),
            },
          }),
        }}
      />
      
      {showValue && !label && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            {formatValue(value)}
          </Typography>
        </Box>
      )}
    </Box>
  );

  const renderCircularProgress = () => (
    <Box sx={{ position: 'relative', display: 'inline-flex' }}>
      <CircularProgress
        variant="determinate"
        value={100}
        size={sizeConfig.circular}
        sx={{
          color: alpha(colorValue, 0.1),
          position: 'absolute',
        }}
        thickness={size === 'small' ? 3 : size === 'large' ? 6 : 4}
      />
      <CircularProgress
        variant="determinate"
        value={value}
        size={sizeConfig.circular}
        sx={{
          color: colorValue,
          transition: animated ? 'stroke-dashoffset 1s ease-in-out' : 'none',
        }}
        thickness={size === 'small' ? 3 : size === 'large' ? 6 : 4}
      />
      {showValue && (
        <Box
          sx={{
            top: 0,
            left: 0,
            bottom: 0,
            right: 0,
            position: 'absolute',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
          }}
        >
          <Typography
            variant={size === 'small' ? 'caption' : size === 'large' ? 'h6' : 'body2'}
            component="div"
            color="text.secondary"
            sx={{ fontWeight: 600 }}
          >
            {formatValue(value)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: size === 'small' ? '0.6rem' : '0.7rem' }}
            >
              {label}
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );

  const renderCardProgress = () => (
    <Card
      sx={{
        background: `linear-gradient(135deg, ${alpha(colorValue, 0.1)}, ${alpha(colorValue, 0.05)})`,
        border: `1px solid ${alpha(colorValue, 0.2)}`,
        borderRadius: 3,
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          {icon && (
            <Box
              sx={{
                mr: 2,
                p: 1,
                borderRadius: 2,
                backgroundColor: alpha(colorValue, 0.1),
                color: colorValue,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {icon}
            </Box>
          )}
          <Box sx={{ flexGrow: 1 }}>
            {title && (
              <Typography variant="h6" sx={{ fontWeight: 700, color: colorValue, mb: 0.5 }}>
                {title}
              </Typography>
            )}
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          {showValue && (
            <Chip
              label={formatValue(value)}
              size="small"
              sx={{
                backgroundColor: alpha(colorValue, 0.1),
                color: colorValue,
                fontWeight: 600,
              }}
            />
          )}
        </Box>
        
        <LinearProgress
          variant="determinate"
          value={value}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: alpha(colorValue, 0.1),
            '& .MuiLinearProgress-bar': {
              backgroundColor: colorValue,
              borderRadius: 4,
              transition: animated ? 'transform 1s ease-in-out' : 'none',
            },
          }}
        />
      </CardContent>
    </Card>
  );

  const renderStepperProgress = () => {
    const activeStep = steps.findIndex(step => step.active);
    const completedSteps = steps.filter(step => step.completed).length;
    const progressValue = (completedSteps / steps.length) * 100;

    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {title || '进度步骤'}
          </Typography>
          <Chip
            label={`${completedSteps}/${steps.length}`}
            size="small"
            color={completedSteps === steps.length ? 'success' : 'primary'}
            variant="outlined"
          />
        </Box>

        <LinearProgress
          variant="determinate"
          value={progressValue}
          sx={{
            mb: 3,
            height: 6,
            borderRadius: 3,
            backgroundColor: alpha(theme.palette.primary.main, 0.1),
            '& .MuiLinearProgress-bar': {
              backgroundColor: theme.palette.primary.main,
              borderRadius: 3,
            },
          }}
        />

        <Stepper activeStep={activeStep} connector={<CustomStepConnector />}>
          {steps.map((step, index) => (
            <Step key={index} completed={step.completed}>
              <StepLabel
                StepIconComponent={({ active, completed }) => (
                  <Box
                    sx={{
                      width: 24,
                      height: 24,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: completed
                        ? theme.palette.success.main
                        : active
                        ? theme.palette.primary.main
                        : theme.palette.grey[300],
                      color: 'white',
                    }}
                  >
                    {completed ? (
                      <CheckCircle size={14} />
                    ) : active ? (
                      <Circle size={14} />
                    ) : (
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>
                        {index + 1}
                      </Typography>
                    )}
                  </Box>
                )}
              >
                <Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: step.completed
                        ? theme.palette.success.main
                        : step.active
                        ? theme.palette.primary.main
                        : theme.palette.text.secondary,
                    }}
                  >
                    {step.label}
                  </Typography>
                  {step.description && (
                    <Typography variant="caption" color="text.secondary">
                      {step.description}
                    </Typography>
                  )}
                </Box>
              </StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>
    );
  };

  const renderMiniProgress = () => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box sx={{ flexGrow: 1, minWidth: 60 }}>
        <LinearProgress
          variant="determinate"
          value={value}
          sx={{
            height: 4,
            borderRadius: 2,
            backgroundColor: alpha(colorValue, 0.1),
            '& .MuiLinearProgress-bar': {
              backgroundColor: colorValue,
              borderRadius: 2,
            },
          }}
        />
      </Box>
      {showValue && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontWeight: 600, minWidth: 35, textAlign: 'right' }}
        >
          {formatValue(value)}
        </Typography>
      )}
    </Box>
  );

  const renderDashboardProgress = () => (
    <Card sx={{ borderRadius: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {icon || <TrendingUp size={24} color={colorValue} />}
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {title || '总体进度'}
              </Typography>
              {subtitle && (
                <Typography variant="body2" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </Box>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: colorValue }}>
            {formatValue(value)}
          </Typography>
        </Box>

        <LinearProgress
          variant="determinate"
          value={value}
          sx={{
            height: 12,
            borderRadius: 6,
            backgroundColor: alpha(colorValue, 0.1),
            mb: 3,
            '& .MuiLinearProgress-bar': {
              backgroundColor: colorValue,
              borderRadius: 6,
              transition: animated ? 'transform 1s ease-in-out' : 'none',
            },
          }}
        />

        {segments.length > 0 && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
              详细分布
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <AnimatePresence>
                {segments.map((segment, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2" color="text.secondary">
                        {segment.label}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, color: segment.color }}>
                        {formatValue(segment.value)}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={segment.value}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: alpha(segment.color, 0.1),
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: segment.color,
                          borderRadius: 3,
                        },
                      }}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );

  switch (variant) {
    case 'circular':
      return renderCircularProgress();
    case 'card':
      return renderCardProgress();
    case 'stepper':
      return renderStepperProgress();
    case 'mini':
      return renderMiniProgress();
    case 'dashboard':
      return renderDashboardProgress();
    case 'linear':
    default:
      return renderLinearProgress();
  }
};