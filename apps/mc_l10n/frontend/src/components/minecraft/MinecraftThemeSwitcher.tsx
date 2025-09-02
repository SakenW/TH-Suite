import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
} from '@mui/material';
import { Sun, Moon, Gamepad2, Contrast, Palette, Check } from 'lucide-react';
import { motion } from 'framer-motion';
import { MinecraftCard } from './MinecraftCard';
import { MinecraftButton } from './MinecraftButton';
import { MinecraftBlock } from '../MinecraftComponents';
import { useTheme, ThemeMode, ColorScheme } from '../../contexts/ThemeContext';
import { minecraftColors } from '../../theme/minecraftTheme';
import { useNotification } from '../../hooks/useNotification';

const themeModes: { value: ThemeMode; label: string; icon: React.ReactNode; description: string }[] = [
  {
    value: 'minecraft',
    label: 'Minecraft',
    icon: <Gamepad2 size={24} />,
    description: '经典的 Minecraft 风格主题',
  },
  {
    value: 'dark',
    label: '暗色',
    icon: <Moon size={24} />,
    description: '适合夜间使用的暗色主题',
  },
  {
    value: 'light',
    label: '亮色',
    icon: <Sun size={24} />,
    description: '明亮清爽的亮色主题',
  },
  {
    value: 'highContrast',
    label: '高对比度',
    icon: <Contrast size={24} />,
    description: '提高可读性的高对比度主题',
  },
];

const colorSchemes: { value: ColorScheme; label: string; colors: string[]; block?: string }[] = [
  {
    value: 'emerald',
    label: '绿宝石',
    colors: [minecraftColors.emerald, minecraftColors.diamondBlue, minecraftColors.goldYellow],
    block: 'emerald',
  },
  {
    value: 'diamond',
    label: '钻石',
    colors: [minecraftColors.diamondBlue, minecraftColors.emerald, minecraftColors.goldYellow],
    block: 'diamond',
  },
  {
    value: 'gold',
    label: '金色',
    colors: [minecraftColors.goldYellow, minecraftColors.emerald, minecraftColors.diamondBlue],
    block: 'gold',
  },
  {
    value: 'redstone',
    label: '红石',
    colors: [minecraftColors.redstoneRed, minecraftColors.iron, minecraftColors.goldYellow],
    block: 'redstone',
  },
  {
    value: 'netherite',
    label: '下界合金',
    colors: ['#4A4A4A', minecraftColors.netheriteGray, minecraftColors.goldYellow],
    block: 'iron',
  },
];

export const MinecraftThemeSwitcher: React.FC = () => {
  const { themeMode, colorScheme, setThemeMode, setColorScheme } = useTheme();
  const notification = useNotification();

  const handleThemeModeChange = (mode: ThemeMode) => {
    setThemeMode(mode);
    notification.success('主题已切换', `已切换到${themeModes.find(t => t.value === mode)?.label}主题`);
  };

  const handleColorSchemeChange = (scheme: ColorScheme) => {
    setColorScheme(scheme);
    notification.info('配色方案已更改', `已切换到${colorSchemes.find(c => c.value === scheme)?.label}配色`);
  };

  return (
    <Box>
      <Typography
        variant="h5"
        sx={{
          fontFamily: '"Minecraft", monospace',
          color: minecraftColors.goldYellow,
          mb: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <Palette size={24} />
        主题设置
      </Typography>

      {/* 主题模式选择 */}
      <MinecraftCard minecraftStyle="stone" sx={{ mb: 3 }}>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 2,
          }}
        >
          主题模式
        </Typography>
        
        <Grid container spacing={2}>
          {themeModes.map((mode) => (
            <Grid item xs={12} sm={6} md={3} key={mode.value}>
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Card
                  sx={{
                    bgcolor: themeMode === mode.value ? 'rgba(255,255,255,0.1)' : 'transparent',
                    border: themeMode === mode.value ? `2px solid ${minecraftColors.emerald}` : '2px solid transparent',
                    borderRadius: 0,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.05)',
                      borderColor: 'rgba(255,255,255,0.2)',
                    },
                  }}
                  onClick={() => handleThemeModeChange(mode.value)}
                >
                  <CardActionArea>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                        <Box sx={{ color: themeMode === mode.value ? minecraftColors.emerald : '#FFFFFF' }}>
                          {mode.icon}
                        </Box>
                        {themeMode === mode.value && (
                          <Check size={20} style={{ color: minecraftColors.emerald }} />
                        )}
                      </Box>
                      <Typography
                        variant="subtitle1"
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          color: '#FFFFFF',
                          mb: 0.5,
                        }}
                      >
                        {mode.label}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'rgba(255,255,255,0.6)',
                          fontSize: '11px',
                        }}
                      >
                        {mode.description}
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </MinecraftCard>

      {/* 配色方案选择 */}
      <MinecraftCard minecraftStyle="iron" sx={{ mb: 3 }}>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 2,
          }}
        >
          配色方案
        </Typography>
        
        <Grid container spacing={2}>
          {colorSchemes.map((scheme) => (
            <Grid item xs={6} sm={4} md={2.4} key={scheme.value}>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Box
                  sx={{
                    p: 2,
                    border: colorScheme === scheme.value ? `2px solid ${scheme.colors[0]}` : '2px solid rgba(255,255,255,0.1)',
                    borderRadius: 0,
                    cursor: 'pointer',
                    bgcolor: colorScheme === scheme.value ? 'rgba(255,255,255,0.05)' : 'transparent',
                    transition: 'all 0.2s',
                    textAlign: 'center',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.02)',
                      borderColor: scheme.colors[0],
                    },
                  }}
                  onClick={() => handleColorSchemeChange(scheme.value)}
                >
                  {/* 方块图标 */}
                  {scheme.block && (
                    <Box sx={{ mb: 1, display: 'flex', justifyContent: 'center' }}>
                      <MinecraftBlock type={scheme.block as any} size={32} animated={colorScheme === scheme.value} />
                    </Box>
                  )}
                  
                  {/* 颜色展示 */}
                  <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                    {scheme.colors.map((color, index) => (
                      <Box
                        key={index}
                        sx={{
                          width: 16,
                          height: 16,
                          bgcolor: color,
                          border: '1px solid rgba(0,0,0,0.3)',
                        }}
                      />
                    ))}
                  </Box>
                  
                  {/* 名称 */}
                  <Typography
                    variant="caption"
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      color: colorScheme === scheme.value ? scheme.colors[0] : '#FFFFFF',
                      fontSize: '12px',
                    }}
                  >
                    {scheme.label}
                  </Typography>
                  
                  {/* 选中标记 */}
                  {colorScheme === scheme.value && (
                    <Box sx={{ mt: 0.5 }}>
                      <Check size={16} style={{ color: scheme.colors[0] }} />
                    </Box>
                  )}
                </Box>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </MinecraftCard>

      {/* 预览区域 */}
      <MinecraftCard minecraftStyle="gold">
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 2,
          }}
        >
          主题预览
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <MinecraftButton minecraftStyle="emerald" fullWidth sx={{ mb: 1 }}>
              主要按钮
            </MinecraftButton>
            <MinecraftButton minecraftStyle="stone" fullWidth sx={{ mb: 1 }}>
              次要按钮
            </MinecraftButton>
            <MinecraftButton minecraftStyle="gold" fullWidth disabled>
              禁用按钮
            </MinecraftButton>
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 0, mb: 1 }}>
              <Typography variant="body2" color="text.primary">
                主要文本颜色
              </Typography>
            </Box>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 0 }}>
              <Typography variant="body2" color="text.secondary">
                次要文本颜色
              </Typography>
            </Box>
          </Grid>
        </Grid>
        
        <Box sx={{ mt: 2, p: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)' }}>
          <Typography variant="caption" color="text.secondary">
            当前主题: <Chip label={`${themeModes.find(t => t.value === themeMode)?.label} + ${colorSchemes.find(c => c.value === colorScheme)?.label}`} size="small" />
          </Typography>
        </Box>
      </MinecraftCard>
    </Box>
  );
};