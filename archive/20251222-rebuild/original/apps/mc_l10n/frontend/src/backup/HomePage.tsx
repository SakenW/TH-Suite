import React from 'react'
import { Box, Typography, Grid, Card, CardContent, Button, useTheme, alpha } from '@mui/material'
import { ExternalLink, Users, Sparkles, Heart } from 'lucide-react'
import { motion } from 'framer-motion'
import { Creeper, MinecraftBlock, ParticleEffect } from '@components/MinecraftComponents'

export const HomePage: React.FC = () => {
  const theme = useTheme()

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        padding: { xs: 2, sm: 3, md: 4 },
        backgroundColor: theme.palette.background.default,
      }}
    >
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Card
          sx={{
            marginBottom: { xs: 2, sm: 3, lg: 4 },
            backgroundColor: theme.palette.background.paper,
            boxShadow: theme.shadows[2],
            borderRadius: 3,
            border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.02)} 0%, ${alpha(theme.palette.secondary.main, 0.02)} 100%)`,
          }}
        >
          <CardContent sx={{ padding: { xs: 3, sm: 4, lg: 5 } }}>
            {/* Title Section with Minecraft Elements */}
            <Box sx={{ marginBottom: 4, position: 'relative' }}>
              {/* Decorative Particles */}
              <Box
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  pointerEvents: 'none',
                }}
              >
                <ParticleEffect count={8} color={theme.palette.primary.main} />
              </Box>

              {/* Main Title Row with Creepers */}
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  marginBottom: 3,
                  flexWrap: { xs: 'wrap', md: 'nowrap' },
                  gap: { xs: 2, md: 3 },
                  position: 'relative',
                  zIndex: 1,
                }}
              >
                <motion.div
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.8, delay: 0.3 }}
                >
                  <Creeper
                    size={48}
                    shouldBlink={false}
                    onExplode={() => console.log('左侧苦力怕爆炸了！💥')}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                >
                  <Typography
                    variant='h2'
                    sx={{
                      fontWeight: 800,
                      background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      fontSize: { xs: '2rem', sm: '2.8rem', lg: '3.5rem' },
                      textAlign: 'center',
                      fontFamily: 'Minecraft, "Microsoft YaHei", sans-serif',
                      textShadow: '2px 2px 4px rgba(0,0,0,0.1)',
                      letterSpacing: '0.02em',
                    }}
                  >
                    TH Suite MC L10n
                  </Typography>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.8, delay: 0.5 }}
                >
                  <Creeper
                    size={48}
                    shouldBlink={true}
                    blinkInterval={2000}
                    onExplode={() => console.log('右侧苦力怕爆炸了！💥')}
                  />
                </motion.div>
              </Box>

              {/* Subtitle with Minecraft Blocks */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.7 }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    gap: 2,
                    flexWrap: 'wrap',
                    marginBottom: 2,
                  }}
                >
                  <MinecraftBlock type='diamond' size={20} animated />
                  <Typography
                    variant='h6'
                    sx={{
                      color: theme.palette.text.primary,
                      fontSize: { xs: '1.1rem', sm: '1.3rem', lg: '1.5rem' },
                      fontWeight: 600,
                      textAlign: 'center',
                      fontFamily: '"Microsoft YaHei", sans-serif',
                    }}
                  >
                    专业的 Minecraft 模组本地化管理工具
                  </Typography>
                  <MinecraftBlock type='emerald' size={20} animated />
                </Box>

                <Typography
                  variant='body1'
                  sx={{
                    color: theme.palette.text.secondary,
                    fontSize: { xs: '0.95rem', sm: '1.05rem', lg: '1.1rem' },
                    lineHeight: 1.6,
                    maxWidth: '600px',
                    margin: '0 auto',
                    textAlign: 'center',
                    fontFamily: '"Microsoft YaHei", sans-serif',
                  }}
                >
                  让模组本地化工作变得简单高效 ✨
                </Typography>
              </motion.div>
            </Box>

            {/* 社区支持 */}
            <Grid container spacing={3} sx={{ justifyContent: 'center', marginTop: 2 }}>
              <Grid item xs={12} sx={{ textAlign: 'center' }}>
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.9 }}
                >
                  <Box sx={{ marginBottom: 3 }}>
                    <Typography
                      variant='h5'
                      sx={{
                        fontWeight: 700,
                        color: theme.palette.primary.main,
                        marginBottom: 2,
                        fontFamily: '"Microsoft YaHei", sans-serif',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 1,
                      }}
                    >
                      <Heart size={24} color={theme.palette.error.main} />
                      语枢 Trans-Hub
                      <Sparkles size={24} color={theme.palette.warning.main} />
                    </Typography>
                    <Typography
                      variant='body1'
                      sx={{
                        color: theme.palette.text.secondary,
                        lineHeight: 1.6,
                        maxWidth: '500px',
                        margin: '0 auto 3rem',
                        fontFamily: '"Microsoft YaHei", sans-serif',
                      }}
                    >
                      全球本地化语言平台，TH Suite MC L10n 是其中的专业工具之一 🌍
                    </Typography>
                  </Box>

                  <Button
                    variant='contained'
                    size='large'
                    startIcon={<Users size={20} />}
                    endIcon={<ExternalLink size={20} />}
                    onClick={() => window.open('https://discord.gg/BWn6E94PbS', '_blank')}
                    sx={{
                      borderRadius: 3,
                      padding: '16px 32px',
                      fontSize: '1.1rem',
                      fontWeight: 700,
                      textTransform: 'none',
                      background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                      boxShadow: theme.shadows[6],
                      '&:hover': {
                        background: `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.secondary.dark})`,
                        transform: 'translateY(-3px)',
                        boxShadow: theme.shadows[12],
                      },
                      transition: 'all 0.3s ease',
                      fontFamily: '"Microsoft YaHei", sans-serif',
                    }}
                  >
                    加入 Discord 群组
                  </Button>

                  <Typography
                    variant='body2'
                    sx={{
                      color: theme.palette.text.secondary,
                      marginTop: 2,
                      lineHeight: 1.6,
                      fontFamily: '"Microsoft YaHei", sans-serif',
                    }}
                  >
                    与全球本地化专家交流，获取最新资讯和技术支持 💬
                  </Typography>
                </motion.div>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </motion.div>

      {/* 页面底部 - 作者署名创意设计 */}
      <Box
        sx={{
          position: 'relative',
          marginTop: 'auto',
          padding: '2rem 0 1rem',
          borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          background: `linear-gradient(180deg, transparent 0%, ${alpha(theme.palette.background.paper, 0.8)} 100%)`,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.2 }}
        >
          <Box
            sx={{
              display: 'flex',
              flexDirection: { xs: 'column', md: 'row' },
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
              maxWidth: '1200px',
              margin: '0 auto',
              padding: '0 2rem',
            }}
          >
            {/* 左侧 - 项目信息 */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                opacity: 0.8,
              }}
            >
              <MinecraftBlock type='grass' size={20} animated />
              <Box>
                <Typography
                  variant='caption'
                  sx={{
                    color: theme.palette.text.secondary,
                    fontSize: '0.75rem',
                    fontFamily: 'monospace',
                  }}
                >
                  TH Suite MC L10n
                </Typography>
                <Typography
                  variant='caption'
                  sx={{
                    display: 'block',
                    color: theme.palette.text.disabled,
                    fontSize: '0.7rem',
                  }}
                >
                  Part of Trans-Hub Ecosystem
                </Typography>
              </Box>
            </Box>

            {/* 中间 - 创意作者署名 */}
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  padding: '6px 12px',
                  borderRadius: '20px',
                  background: `linear-gradient(45deg, ${alpha('#4CAF50', 0.1)}, ${alpha('#2196F3', 0.1)})`,
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    background: `linear-gradient(45deg, ${alpha('#4CAF50', 0.2)}, ${alpha('#2196F3', 0.2)})`,
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.4)}`,
                    boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.2)}`,
                  },
                }}
              >
                <Typography
                  sx={{
                    fontSize: '0.75rem',
                    color: theme.palette.text.secondary,
                    fontFamily: 'monospace',
                  }}
                >
                  🛠️
                </Typography>
                <Typography
                  sx={{
                    fontSize: '0.8rem',
                    color: theme.palette.text.primary,
                    fontWeight: 500,
                    fontFamily: 'Minecraft, monospace',
                    letterSpacing: '0.5px',
                  }}
                >
                  @Saken
                </Typography>
                <Typography
                  sx={{
                    fontSize: '0.75rem',
                    color: theme.palette.text.secondary,
                    fontFamily: 'monospace',
                  }}
                >
                  ⚡
                </Typography>
              </Box>
            </motion.div>

            {/* 右侧 - 版本信息 */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                opacity: 0.8,
              }}
            >
              <Box sx={{ textAlign: 'right' }}>
                <Typography
                  variant='caption'
                  sx={{
                    color: theme.palette.text.secondary,
                    fontSize: '0.75rem',
                    fontFamily: 'monospace',
                  }}
                >
                  v1.0.0-beta
                </Typography>
                <Typography
                  variant='caption'
                  sx={{
                    display: 'block',
                    color: theme.palette.text.disabled,
                    fontSize: '0.7rem',
                  }}
                >
                  Open Source
                </Typography>
              </Box>
              <MinecraftBlock type='redstone' size={20} animated />
            </Box>
          </Box>
        </motion.div>
      </Box>
    </Box>
  )
}

export default HomePage
