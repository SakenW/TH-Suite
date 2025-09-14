import React from 'react'
import { Card, CardContent, CardProps, Box, Typography } from '@mui/material'
import { motion } from 'framer-motion'
import { MinecraftBlock } from '../MinecraftComponents'

interface MinecraftCardProps extends Omit<CardProps, 'variant'> {
  variant?: 'inventory' | 'chest' | 'crafting' | 'enchantment'
  title?: string
  icon?: 'grass' | 'stone' | 'diamond' | 'gold' | 'iron' | 'emerald'
  glowing?: boolean
  pixelated?: boolean
  children: React.ReactNode
}

export const MinecraftCard: React.FC<MinecraftCardProps> = ({
  variant = 'inventory',
  title,
  icon,
  glowing = false,
  pixelated = true,
  children,
  ...props
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'chest':
        return {
          background: 'linear-gradient(180deg, #8B6239 0%, #6B4929 50%, #5B3919 100%)',
          borderColor: '#4B2909',
          borderWidth: 3,
          innerBorder: '#AB8259',
          shadowColor: '#3B1909',
        }
      case 'crafting':
        return {
          background: 'linear-gradient(180deg, #C6A57A 0%, #A68A5A 50%, #86704A 100%)',
          borderColor: '#665040',
          borderWidth: 3,
          innerBorder: '#D6B58A',
          shadowColor: '#463030',
        }
      case 'enchantment':
        return {
          background: 'linear-gradient(180deg, #4A3C6E 0%, #3A2C5E 50%, #2A1C4E 100%)',
          borderColor: '#1A0C3E',
          borderWidth: 3,
          innerBorder: '#6A5C8E',
          shadowColor: '#0A0020',
          glowColor: '#9B59B6',
        }
      case 'inventory':
      default:
        return {
          background: 'linear-gradient(180deg, #C6C6C6 0%, #8B8B8B 50%, #6B6B6B 100%)',
          borderColor: '#2B2B2B',
          borderWidth: 3,
          innerBorder: '#D6D6D6',
          shadowColor: '#1B1B1B',
        }
    }
  }

  const styles = getVariantStyles()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
    >
      <Card
        {...props}
        sx={{
          position: 'relative',
          background: styles.background,
          border: `${styles.borderWidth}px solid ${styles.borderColor}`,
          borderRadius: 0,
          boxShadow: `
            inset 2px 2px 0 ${styles.innerBorder},
            inset -2px -2px 0 ${styles.shadowColor},
            4px 4px 0 rgba(0,0,0,0.5)
          `,
          overflow: 'visible',
          imageRendering: pixelated ? 'pixelated' : 'auto',
          ...(glowing && {
            animation: 'minecraft-card-glow 3s ease-in-out infinite',
            '@keyframes minecraft-card-glow': {
              '0%, 100%': {
                boxShadow: `
                  inset 2px 2px 0 ${styles.innerBorder},
                  inset -2px -2px 0 ${styles.shadowColor},
                  4px 4px 0 rgba(0,0,0,0.5),
                  0 0 20px ${styles.glowColor || styles.innerBorder}66
                `,
              },
              '50%': {
                boxShadow: `
                  inset 2px 2px 0 ${styles.innerBorder},
                  inset -2px -2px 0 ${styles.shadowColor},
                  4px 4px 0 rgba(0,0,0,0.5),
                  0 0 40px ${styles.glowColor || styles.innerBorder}aa
                `,
              },
            },
          }),
          '&::before': {
            content: '""',
            position: 'absolute',
            top: -1,
            left: -1,
            right: -1,
            bottom: -1,
            background: `
              repeating-linear-gradient(
                45deg,
                transparent,
                transparent 10px,
                ${styles.innerBorder}11 10px,
                ${styles.innerBorder}11 20px
              )
            `,
            pointerEvents: 'none',
            borderRadius: 'inherit',
          },
          ...props.sx,
        }}
      >
        {title && (
          <Box
            sx={{
              position: 'relative',
              padding: '12px 16px',
              background: 'linear-gradient(180deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.6) 100%)',
              borderBottom: `2px solid ${styles.borderColor}`,
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            {icon && <MinecraftBlock type={icon} size={24} animated={glowing} />}
            <Typography
              variant='h6'
              sx={{
                color: '#FFFFFF',
                fontFamily: pixelated ? '"Minecraft", "Press Start 2P", monospace' : 'inherit',
                fontSize: pixelated ? '14px' : '18px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                textShadow: '2px 2px 0 rgba(0,0,0,0.8)',
              }}
            >
              {title}
            </Typography>
          </Box>
        )}
        <CardContent
          sx={{
            position: 'relative',
            '&:last-child': {
              paddingBottom: 2,
            },
          }}
        >
          {children}
        </CardContent>

        {/* 角落装饰 */}
        <Box
          sx={{
            position: 'absolute',
            top: -6,
            left: -6,
            width: 12,
            height: 12,
            background: styles.innerBorder,
            border: `2px solid ${styles.borderColor}`,
            borderRadius: 0,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            top: -6,
            right: -6,
            width: 12,
            height: 12,
            background: styles.innerBorder,
            border: `2px solid ${styles.borderColor}`,
            borderRadius: 0,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: -6,
            left: -6,
            width: 12,
            height: 12,
            background: styles.innerBorder,
            border: `2px solid ${styles.borderColor}`,
            borderRadius: 0,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: -6,
            right: -6,
            width: 12,
            height: 12,
            background: styles.innerBorder,
            border: `2px solid ${styles.borderColor}`,
            borderRadius: 0,
          }}
        />
      </Card>
    </motion.div>
  )
}

export default MinecraftCard
