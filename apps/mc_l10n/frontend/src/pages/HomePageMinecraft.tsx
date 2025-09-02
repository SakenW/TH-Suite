import React, { useState, useEffect } from 'react';
import { Box, Typography, Grid, IconButton, Tooltip } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Gamepad2, 
  Package, 
  FileSearch, 
  Download, 
  Upload, 
  Settings, 
  Database,
  Sparkles,
  Zap,
  Target,
  Trophy,
  Heart,
  Shield,
  Sword
} from 'lucide-react';

import { MinecraftButton } from '../components/minecraft/MinecraftButton';
import { MinecraftCard } from '../components/minecraft/MinecraftCard';
import { MinecraftProgress } from '../components/minecraft/MinecraftProgress';
import { MinecraftBlock, ParticleEffect, Creeper } from '../components/MinecraftComponents';

// 快捷功能卡片数据
const quickActions = [
  {
    id: 'scan',
    title: '扫描模组',
    description: '扫描并识别模组文件',
    icon: FileSearch,
    color: 'emerald',
    path: '/scan',
    stats: { value: 0, label: '已扫描' }
  },
  {
    id: 'project',
    title: '项目管理',
    description: '管理翻译项目',
    icon: Package,
    color: 'diamond',
    path: '/project',
    stats: { value: 0, label: '活跃项目' }
  },
  {
    id: 'export',
    title: '导出翻译',
    description: '导出翻译文件',
    icon: Download,
    color: 'gold',
    path: '/export',
    stats: { value: 0, label: '已导出' }
  },
  {
    id: 'transfer',
    title: '同步数据',
    description: '与Trans-Hub同步',
    icon: Upload,
    color: 'redstone',
    path: '/transfer',
    stats: { value: 0, label: '待同步' }
  },
];

// 成就数据
const achievements = [
  { id: 1, name: '初次扫描', icon: '🔍', unlocked: true },
  { id: 2, name: '模组收集者', icon: '📦', unlocked: true },
  { id: 3, name: '翻译大师', icon: '🌐', unlocked: false },
  { id: 4, name: '效率专家', icon: '⚡', unlocked: false },
  { id: 5, name: '团队协作', icon: '🤝', unlocked: false },
];

export default function HomePageMinecraft() {
  const navigate = useNavigate();
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [showParticles, setShowParticles] = useState(false);
  const [stats, setStats] = useState({
    totalMods: 156,
    translatedKeys: 12450,
    pendingKeys: 3280,
    completionRate: 79,
    todayProgress: 450,
    weeklyGoal: 2000,
    weeklyProgress: 1650,
  });

  // 模拟统计数据更新
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        todayProgress: Math.min(prev.todayProgress + Math.floor(Math.random() * 5), 500),
        weeklyProgress: Math.min(prev.weeklyProgress + Math.floor(Math.random() * 10), prev.weeklyGoal),
      }));
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleActionClick = (path: string) => {
    setShowParticles(true);
    setTimeout(() => {
      navigate(path);
      setShowParticles(false);
    }, 300);
  };

  return (
    <Box sx={{ position: 'relative', minHeight: '100vh', p: 3 }}>
      {/* 粒子效果 */}
      <AnimatePresence>
        {showParticles && <ParticleEffect count={30} />}
      </AnimatePresence>

      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2, mb: 2 }}>
            <MinecraftBlock type="diamond" size={48} animated />
            <Typography
              variant="h2"
              sx={{
                fontFamily: '"Minecraft", "Press Start 2P", monospace',
                fontSize: { xs: '28px', md: '40px' },
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                background: 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF6347 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                textShadow: '3px 3px 6px rgba(0,0,0,0.5)',
              }}
            >
              TH Suite MC L10n
            </Typography>
            <MinecraftBlock type="emerald" size={48} animated />
          </Box>
          <Typography
            sx={{
              fontFamily: '"Minecraft", monospace',
              fontSize: '16px',
              color: 'text.secondary',
              letterSpacing: '0.02em',
              textShadow: '1px 1px 2px rgba(0,0,0,0.3)',
            }}
          >
            🎮 Minecraft 模组本地化工具套件
          </Typography>
        </Box>
      </motion.div>

      <Grid container spacing={3}>
        {/* 统计概览 */}
        <Grid item xs={12}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <MinecraftCard variant="enchantment" title="今日概览" icon="gold" glowing>
              <Grid container spacing={2}>
                <Grid item xs={12} md={3}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Trophy size={32} color="#FFD700" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '28px',
                        color: '#FFD700',
                        mt: 1,
                      }}
                    >
                      {stats.totalMods}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '12px',
                        color: 'text.secondary',
                      }}
                    >
                      模组总数
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Sparkles size={32} color="#00BCD4" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '28px',
                        color: '#00BCD4',
                        mt: 1,
                      }}
                    >
                      {stats.translatedKeys.toLocaleString()}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '12px',
                        color: 'text.secondary',
                      }}
                    >
                      已翻译
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Target size={32} color="#FF6347" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '28px',
                        color: '#FF6347',
                        mt: 1,
                      }}
                    >
                      {stats.pendingKeys.toLocaleString()}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '12px',
                        color: 'text.secondary',
                      }}
                    >
                      待翻译
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Zap size={32} color="#4CAF50" />
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '28px',
                        color: '#4CAF50',
                        mt: 1,
                      }}
                    >
                      {stats.completionRate}%
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: '"Minecraft", monospace',
                        fontSize: '12px',
                        color: 'text.secondary',
                      }}
                    >
                      完成率
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* 进度条 */}
              <Box sx={{ px: 2, pb: 2 }}>
                <MinecraftProgress
                  value={stats.todayProgress}
                  max={500}
                  variant="experience"
                  label="今日进度"
                  animated
                  size="medium"
                />
                <Box sx={{ mt: 2 }}>
                  <MinecraftProgress
                    value={stats.weeklyProgress}
                    max={stats.weeklyGoal}
                    variant="health"
                    label="本周目标"
                    animated
                    size="medium"
                  />
                </Box>
              </Box>
            </MinecraftCard>
          </motion.div>
        </Grid>

        {/* 快捷操作 */}
        <Grid item xs={12} lg={8}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '18px',
                color: '#FFFFFF',
                mb: 2,
                textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
              }}
            >
              ⚡ 快捷操作
            </Typography>
            <Grid container spacing={2}>
              {quickActions.map((action, index) => (
                <Grid item xs={12} sm={6} key={action.id}>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.1 * index }}
                    whileHover={{ scale: 1.03 }}
                    onHoverStart={() => setSelectedAction(action.id)}
                    onHoverEnd={() => setSelectedAction(null)}
                  >
                    <MinecraftCard
                      variant="inventory"
                      glowing={selectedAction === action.id}
                    >
                      <Box
                        sx={{
                          p: 2,
                          cursor: 'pointer',
                          '&:hover': {
                            background: 'rgba(255,255,255,0.05)',
                          },
                        }}
                        onClick={() => handleActionClick(action.path)}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Box
                            sx={{
                              width: 48,
                              height: 48,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              background: `linear-gradient(135deg, ${
                                action.color === 'emerald' ? '#4CAF50' :
                                action.color === 'diamond' ? '#00BCD4' :
                                action.color === 'gold' ? '#FFD700' :
                                '#FF6347'
                              } 0%, rgba(0,0,0,0.3) 100%)`,
                              border: '2px solid rgba(0,0,0,0.5)',
                              borderRadius: 0,
                            }}
                          >
                            <action.icon size={24} color="#FFFFFF" />
                          </Box>
                          <Box sx={{ flex: 1 }}>
                            <Typography
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '14px',
                                color: '#FFFFFF',
                                fontWeight: 'bold',
                              }}
                            >
                              {action.title}
                            </Typography>
                            <Typography
                              sx={{
                                fontFamily: '"Minecraft", monospace',
                                fontSize: '11px',
                                color: 'text.secondary',
                              }}
                            >
                              {action.description}
                            </Typography>
                          </Box>
                        </Box>
                        <Box
                          sx={{
                            mt: 2,
                            pt: 2,
                            borderTop: '1px solid rgba(255,255,255,0.1)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '10px',
                              color: 'text.secondary',
                            }}
                          >
                            {action.stats.label}
                          </Typography>
                          <Typography
                            sx={{
                              fontFamily: '"Minecraft", monospace',
                              fontSize: '16px',
                              color: '#FFFFFF',
                            }}
                          >
                            {action.stats.value}
                          </Typography>
                        </Box>
                      </Box>
                    </MinecraftCard>
                  </motion.div>
                </Grid>
              ))}
            </Grid>
          </motion.div>
        </Grid>

        {/* 成就系统 */}
        <Grid item xs={12} lg={4}>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Typography
              sx={{
                fontFamily: '"Minecraft", monospace',
                fontSize: '18px',
                color: '#FFFFFF',
                mb: 2,
                textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
              }}
            >
              🏆 成就
            </Typography>
            <MinecraftCard variant="chest" glowing>
              <Box sx={{ p: 2 }}>
                {achievements.map((achievement, index) => (
                  <motion.div
                    key={achievement.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: 0.05 * index }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 2,
                        p: 1,
                        mb: 1,
                        background: achievement.unlocked
                          ? 'linear-gradient(90deg, rgba(255,215,0,0.2) 0%, transparent 100%)'
                          : 'rgba(0,0,0,0.2)',
                        border: `1px solid ${achievement.unlocked ? '#FFD700' : '#333333'}`,
                        borderRadius: 0,
                        opacity: achievement.unlocked ? 1 : 0.5,
                      }}
                    >
                      <Box sx={{ fontSize: 24 }}>{achievement.icon}</Box>
                      <Typography
                        sx={{
                          fontFamily: '"Minecraft", monospace',
                          fontSize: '12px',
                          color: achievement.unlocked ? '#FFD700' : '#888888',
                        }}
                      >
                        {achievement.name}
                      </Typography>
                      {achievement.unlocked && (
                        <Box sx={{ ml: 'auto' }}>
                          <Sparkles size={16} color="#FFD700" />
                        </Box>
                      )}
                    </Box>
                  </motion.div>
                ))}
                <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <Typography
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      fontSize: '11px',
                      color: 'text.secondary',
                      textAlign: 'center',
                    }}
                  >
                    已解锁 {achievements.filter(a => a.unlocked).length}/{achievements.length}
                  </Typography>
                </Box>
              </Box>
            </MinecraftCard>

            {/* 快速操作按钮 */}
            <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <MinecraftButton
                minecraftStyle="diamond"
                onClick={() => navigate('/settings')}
                fullWidth
                startIcon={<Settings size={16} />}
              >
                设置
              </MinecraftButton>
              <MinecraftButton
                minecraftStyle="iron"
                onClick={() => navigate('/local-data')}
                fullWidth
                startIcon={<Database size={16} />}
              >
                本地数据
              </MinecraftButton>
            </Box>
          </motion.div>
        </Grid>

        {/* 底部装饰 */}
        <Grid item xs={12}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Box
              sx={{
                mt: 4,
                p: 2,
                background: 'linear-gradient(135deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 100%)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 0,
                textAlign: 'center',
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3, mb: 1 }}>
                <Heart size={20} color="#FF6B6B" />
                <Shield size={20} color="#4ECDC4" />
                <Sword size={20} color="#FFD93D" />
              </Box>
              <Typography
                sx={{
                  fontFamily: '"Minecraft", monospace',
                  fontSize: '12px',
                  color: 'text.secondary',
                  letterSpacing: '0.05em',
                }}
              >
                Powered by Trans-Hub • Made with ❤️ for Minecraft Community
              </Typography>
            </Box>
          </motion.div>
        </Grid>
      </Grid>
    </Box>
  );
}