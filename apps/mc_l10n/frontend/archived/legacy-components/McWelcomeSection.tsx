import React from 'react'
import { Box, Typography, Grid, Card, CardContent, Button, useTheme, alpha } from '@mui/material'
import { motion } from 'framer-motion'
import { Creeper } from './MinecraftComponents'

export interface McQuickAction {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  color: string
  onClick: () => void
}

export interface McWelcomeSectionProps {
  title: string
  subtitle?: string
  description?: string
  quickActions?: McQuickAction[]
  quickActionsTitle?: string
  primaryButton?: {
    text: string
    icon?: React.ReactNode
    onClick: () => void
  }
  secondaryButtons?: {
    text: string
    icon?: React.ReactNode
    onClick: () => void
    variant?: 'outlined' | 'text'
  }[]
  headerAction?: React.ReactNode
  enableAnimation?: boolean
  animationDelay?: number
}

const McWelcomeSection: React.FC<McWelcomeSectionProps> = ({
  title,
  subtitle,
  description,
  quickActions = [],
  quickActionsTitle = '快速操作',
  primaryButton,
  secondaryButtons = [],
  headerAction,
  enableAnimation = true,
  animationDelay = 0,
}) => {
  const theme = useTheme()

  return (
    <Box sx={{ width: '100%' }}>
      {/* 标题区域 */}
      <motion.div
        initial={enableAnimation ? { opacity: 0, y: 20 } : {}}
        animate={enableAnimation ? { opacity: 1, y: 0 } : {}}
        transition={enableAnimation ? { duration: 0.5, delay: animationDelay } : {}}
      >
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'flex-start', sm: 'flex-start' },
            gap: { xs: 2, sm: 0 },
            mb: 3,
          }}
        >
          <Box sx={{ flex: 1 }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: { xs: 1, sm: 2 },
                mb: 1,
                flexWrap: 'wrap',
              }}
            >
              <Creeper />
              <Typography
                variant='h3'
                sx={{
                  fontWeight: 700,
                  color: theme.palette.text.primary,
                  fontFamily: 'Minecraft, "Microsoft YaHei", "Noto Sans SC", sans-serif',
                }}
              >
                {title}
              </Typography>
              <Creeper />
            </Box>
            {subtitle && (
              <Typography
                variant='h6'
                sx={{
                  color: theme.palette.text.secondary,
                  fontWeight: 400,
                  marginBottom: description ? 1 : 2,
                  fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
                }}
              >
                {subtitle}
              </Typography>
            )}
            {description && (
              <Typography
                variant='body1'
                sx={{
                  color: theme.palette.text.secondary,
                  lineHeight: 1.6,
                  marginBottom: 2,
                  fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
                }}
              >
                {description}
              </Typography>
            )}
          </Box>
          {headerAction && <Box sx={{ ml: 2 }}>{headerAction}</Box>}
        </Box>
      </motion.div>

      {/* 按钮区域 */}
      {(primaryButton || secondaryButtons.length > 0) && (
        <motion.div
          initial={enableAnimation ? { opacity: 0, y: 20 } : {}}
          animate={enableAnimation ? { opacity: 1, y: 0 } : {}}
          transition={enableAnimation ? { duration: 0.5, delay: animationDelay + 0.1 } : {}}
        >
          <Box
            sx={{
              display: 'flex',
              gap: { xs: 1, sm: 2 },
              mb: 4,
              flexWrap: 'wrap',
              flexDirection: { xs: 'column', sm: 'row' },
              alignItems: { xs: 'stretch', sm: 'flex-start' },
            }}
          >
            {primaryButton && (
              <Button
                variant='contained'
                size='large'
                startIcon={primaryButton.icon}
                onClick={primaryButton.onClick}
                sx={{
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
                  '&:hover': {
                    backgroundColor: '#45a049',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 4px 8px rgba(76, 175, 80, 0.3)',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                {primaryButton.text}
              </Button>
            )}
            {secondaryButtons.map((button, index) => (
              <Button
                key={index}
                variant={button.variant || 'outlined'}
                size='large'
                startIcon={button.icon}
                onClick={button.onClick}
                sx={{
                  fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                {button.text}
              </Button>
            ))}
          </Box>
        </motion.div>
      )}

      {/* 快速操作区域 */}
      {quickActions.length > 0 && (
        <motion.div
          initial={enableAnimation ? { opacity: 0, y: 20 } : {}}
          animate={enableAnimation ? { opacity: 1, y: 0 } : {}}
          transition={enableAnimation ? { duration: 0.5, delay: animationDelay + 0.2 } : {}}
        >
          <Typography
            variant='h5'
            sx={{
              fontWeight: 600,
              marginBottom: 2,
              color: theme.palette.text.primary,
              fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
            }}
          >
            {quickActionsTitle}
          </Typography>
          <Grid container spacing={{ xs: 2, sm: 3 }}>
            {quickActions.map((action, index) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={action.id}>
                <motion.div
                  initial={enableAnimation ? { opacity: 0, y: 20 } : {}}
                  animate={enableAnimation ? { opacity: 1, y: 0 } : {}}
                  transition={
                    enableAnimation
                      ? { duration: 0.5, delay: animationDelay + 0.3 + index * 0.1 }
                      : {}
                  }
                  whileHover={{ y: -4, scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card
                    sx={{
                      cursor: 'pointer',
                      height: '100%',
                      background: `linear-gradient(135deg, ${alpha(action.color, 0.1)} 0%, ${alpha(action.color, 0.05)} 100%)`,
                      border: `2px solid ${alpha(action.color, 0.2)}`,
                      borderRadius: '12px',
                      transition: 'all 0.3s ease-in-out',
                      '&:hover': {
                        borderColor: action.color,
                        boxShadow: `0 8px 25px ${alpha(action.color, 0.3)}`,
                        transform: 'translateY(-4px)',
                      },
                    }}
                    onClick={action.onClick}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 48,
                            height: 48,
                            borderRadius: '12px',
                            backgroundColor: alpha(action.color, 0.1),
                            color: action.color,
                            marginRight: 2,
                          }}
                        >
                          {action.icon}
                        </Box>
                      </Box>
                      <Typography
                        variant='h6'
                        sx={{
                          fontWeight: 600,
                          marginBottom: 1,
                          color: theme.palette.text.primary,
                          fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
                        }}
                      >
                        {action.title}
                      </Typography>
                      <Typography
                        variant='body2'
                        sx={{
                          color: theme.palette.text.secondary,
                          lineHeight: 1.5,
                          fontFamily: '"Microsoft YaHei", "Noto Sans SC", sans-serif',
                        }}
                      >
                        {action.description}
                      </Typography>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
            ))}
          </Grid>
        </motion.div>
      )}
    </Box>
  )
}

export default McWelcomeSection
export { McWelcomeSection }
