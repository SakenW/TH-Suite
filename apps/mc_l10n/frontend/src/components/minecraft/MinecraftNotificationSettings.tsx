import React from 'react';
import {
  Box,
  Typography,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  Slider,
  Button,
  Divider,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Bell, Volume2, Sparkles, Monitor, TestTube, Trash2 } from 'lucide-react';
import { MinecraftCard } from './MinecraftCard';
import { MinecraftButton } from './MinecraftButton';
import { useNotification } from '../../hooks/useNotification';
import { minecraftColors } from '../../theme/minecraftTheme';

export const MinecraftNotificationSettings: React.FC = () => {
  const { settings, updateSettings, notify, clear } = useNotification();

  const handleTestNotification = (type: string) => {
    const testMessages = {
      success: { title: '测试成功通知', message: '这是一个成功通知的示例' },
      error: { title: '测试错误通知', message: '这是一个错误通知的示例' },
      warning: { title: '测试警告通知', message: '这是一个警告通知的示例' },
      info: { title: '测试信息通知', message: '这是一个信息通知的示例' },
      achievement: { title: '成就解锁', message: '你已完成测试成就！' },
      system: { title: '系统消息', message: '这是一个系统通知的示例' },
    };

    const msg = testMessages[type as keyof typeof testMessages];
    notify({
      ...msg,
      type: type as any,
      minecraft: type === 'achievement' ? { particle: true, glow: true } : undefined,
    });
  };

  const positionOptions = [
    { value: 'top-right', label: '右上角' },
    { value: 'top-left', label: '左上角' },
    { value: 'bottom-right', label: '右下角' },
    { value: 'bottom-left', label: '左下角' },
    { value: 'top-center', label: '顶部居中' },
    { value: 'bottom-center', label: '底部居中' },
  ];

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
        <Bell size={24} />
        通知设置
      </Typography>

      <MinecraftCard minecraftStyle="stone" sx={{ mb: 3 }}>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Monitor size={20} />
          显示设置
        </Typography>

        <Box sx={{ mb: 3 }}>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>通知位置</InputLabel>
            <Select
              value={settings.position}
              onChange={(e) => updateSettings({ position: e.target.value as any })}
              label="通知位置"
              sx={{
                '& .MuiSelect-select': {
                  fontFamily: '"Minecraft", monospace',
                },
              }}
            >
              {positionOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              最大通知数量: {settings.maxNotifications}
            </Typography>
            <Slider
              value={settings.maxNotifications}
              onChange={(_, value) => updateSettings({ maxNotifications: value as number })}
              min={1}
              max={10}
              marks
              valueLabelDisplay="auto"
              sx={{
                color: minecraftColors.emerald,
                '& .MuiSlider-thumb': {
                  bgcolor: minecraftColors.goldYellow,
                },
              }}
            />
          </Box>

          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              默认显示时长: {settings.defaultDuration / 1000}秒
            </Typography>
            <Slider
              value={settings.defaultDuration / 1000}
              onChange={(_, value) => updateSettings({ defaultDuration: (value as number) * 1000 })}
              min={1}
              max={10}
              step={0.5}
              marks
              valueLabelDisplay="auto"
              sx={{
                color: minecraftColors.diamondBlue,
                '& .MuiSlider-thumb': {
                  bgcolor: minecraftColors.goldYellow,
                },
              }}
            />
          </Box>
        </Box>
      </MinecraftCard>

      <MinecraftCard minecraftStyle="iron" sx={{ mb: 3 }}>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Volume2 size={20} />
          音效设置
        </Typography>

        <FormControlLabel
          control={
            <Switch
              checked={settings.soundEnabled}
              onChange={(e) => updateSettings({ soundEnabled: e.target.checked })}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: minecraftColors.emerald,
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  backgroundColor: minecraftColors.emerald,
                },
              }}
            />
          }
          label="启用通知音效"
          sx={{ mb: 1 }}
        />

        <FormControlLabel
          control={
            <Switch
              checked={settings.achievementEffects}
              onChange={(e) => updateSettings({ achievementEffects: e.target.checked })}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: minecraftColors.goldYellow,
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  backgroundColor: minecraftColors.goldYellow,
                },
              }}
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              成就特效
              <Sparkles size={16} style={{ color: minecraftColors.goldYellow }} />
            </Box>
          }
        />
      </MinecraftCard>

      <MinecraftCard minecraftStyle="gold" sx={{ mb: 3 }}>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Minecraft", monospace',
            color: '#FFFFFF',
            mb: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <TestTube size={20} />
          测试通知
        </Typography>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          <MinecraftButton
            minecraftStyle="emerald"
            size="small"
            onClick={() => handleTestNotification('success')}
          >
            成功
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="redstone"
            size="small"
            onClick={() => handleTestNotification('error')}
          >
            错误
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="gold"
            size="small"
            onClick={() => handleTestNotification('warning')}
          >
            警告
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="diamond"
            size="small"
            onClick={() => handleTestNotification('info')}
          >
            信息
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="gold"
            size="small"
            onClick={() => handleTestNotification('achievement')}
            startIcon={<Sparkles size={16} />}
          >
            成就
          </MinecraftButton>
          <MinecraftButton
            minecraftStyle="iron"
            size="small"
            onClick={() => handleTestNotification('system')}
          >
            系统
          </MinecraftButton>
        </Box>

        <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.1)' }} />

        <MinecraftButton
          minecraftStyle="redstone"
          size="small"
          startIcon={<Trash2 size={16} />}
          onClick={clear}
          sx={{ mt: 1 }}
        >
          清除所有通知
        </MinecraftButton>
      </MinecraftCard>

      <MinecraftCard sx={{ bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)' }}>
        <Typography variant="caption" color="text.secondary">
          提示：通知设置会自动保存到本地存储中
        </Typography>
      </MinecraftCard>
    </Box>
  );
};