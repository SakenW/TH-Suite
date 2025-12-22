import React from 'react'
import { Box, Typography } from '@mui/material'
import { motion } from 'framer-motion'

interface MinecraftProgressProps {
  value: number
  max?: number
  label?: string
  variant?: 'experience' | 'health' | 'hunger' | 'armor' | 'loading'
  showValue?: boolean
  animated?: boolean
  size?: 'small' | 'medium' | 'large'
}

export const MinecraftProgress: React.FC<MinecraftProgressProps> = ({
  value,
  max = 100,
  label,
  variant = 'experience',
  showValue = true,
  animated = true,
  size = 'medium',
}) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))

  const getVariantStyles = () => {
    switch (variant) {
      case 'health':
        return {
          barColor: 'linear-gradient(180deg, #FF6B6B 0%, #DC143C 50%, #8B0000 100%)',
          backgroundColor: '#4A0E0E',
          borderColor: '#2A0505',
          glowColor: '#FF0000',
          icon: '❤️',
        }
      case 'hunger':
        return {
          barColor: 'linear-gradient(180deg, #D2691E 0%, #A0522D 50%, #8B4513 100%)',
          backgroundColor: '#3E2723',
          borderColor: '#2E1A17',
          glowColor: '#D2691E',
          icon: '🍖',
        }
      case 'armor':
        return {
          barColor: 'linear-gradient(180deg, #C0C0C0 0%, #808080 50%, #696969 100%)',
          backgroundColor: '#2B2B2B',
          borderColor: '#1B1B1B',
          glowColor: '#C0C0C0',
          icon: '🛡️',
        }
      case 'loading':
        return {
          barColor: 'linear-gradient(180deg, #4FC3F7 0%, #29B6F6 50%, #039BE5 100%)',
          backgroundColor: '#01579B',
          borderColor: '#014A8F',
          glowColor: '#29B6F6',
          icon: '⚙️',
        }
      case 'experience':
      default:
        return {
          barColor: 'linear-gradient(180deg, #8BC34A 0%, #7CB342 50%, #689F38 100%)',
          backgroundColor: '#1B5E20',
          borderColor: '#0D3E10',
          glowColor: '#7CB342',
          icon: '⭐',
        }
    }
  }

  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { height: 8, fontSize: '10px', padding: '2px 4px' }
      case 'large':
        return { height: 24, fontSize: '16px', padding: '4px 12px' }
      case 'medium':
      default:
        return { height: 16, fontSize: '12px', padding: '3px 8px' }
    }
  }

  const styles = getVariantStyles()
  const sizeStyles = getSizeStyles()

  return (
    <Box sx={{ width: '100%', position: 'relative' }}>
      {label && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 1,
          }}
        >
          <Typography
            sx={{
              fontFamily: '"Minecraft", "Press Start 2P", monospace',
              fontSize: sizeStyles.fontSize,
              color: '#FFFFFF',
              textShadow: '1px 1px 0 rgba(0,0,0,0.8)',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}
          >
            {styles.icon} {label}
          </Typography>
          {showValue && (
            <Typography
              sx={{
                fontFamily: '"Minecraft", "Press Start 2P", monospace',
                fontSize: sizeStyles.fontSize,
                color: '#FFFFFF',
                textShadow: '1px 1px 0 rgba(0,0,0,0.8)',
              }}
            >
              {typeof value === 'number' ? Math.round(value) : value}/{max}
            </Typography>
          )}
        </Box>
      )}

      <Box
        sx={{
          position: 'relative',
          height: sizeStyles.height,
          background: styles.backgroundColor,
          border: `2px solid ${styles.borderColor}`,
          borderRadius: 0,
          overflow: 'hidden',
          boxShadow: `
            inset 0 2px 4px rgba(0,0,0,0.5),
            0 0 0 1px #000000
          `,
        }}
      >
        {/* 背景纹理 */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            opacity: 0.3,
            background: `
              repeating-linear-gradient(
                90deg,
                transparent,
                transparent 2px,
                rgba(0,0,0,0.1) 2px,
                rgba(0,0,0,0.1) 4px
              )
            `,
          }}
        />

        {/* 进度条 */}
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{
            duration: animated ? 0.5 : 0,
            ease: 'easeOut',
          }}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '100%',
            background: styles.barColor,
            boxShadow: `
              inset 0 2px 0 rgba(255,255,255,0.3),
              inset 0 -2px 0 rgba(0,0,0,0.3),
              ${animated ? `0 0 10px ${styles.glowColor}66` : 'none'}
            `,
          }}
        >
          {/* 闪光效果 */}
          {animated && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `
                  linear-gradient(
                    90deg,
                    transparent 0%,
                    rgba(255,255,255,0.4) 50%,
                    transparent 100%
                  )
                `,
                animation: 'minecraft-progress-shine 2s linear infinite',
                '@keyframes minecraft-progress-shine': {
                  '0%': { transform: 'translateX(-100%)' },
                  '100%': { transform: 'translateX(200%)' },
                },
              }}
            />
          )}

          {/* 像素化边缘 */}
          <Box
            sx={{
              position: 'absolute',
              right: 0,
              top: 0,
              bottom: 0,
              width: '4px',
              background: `
                repeating-linear-gradient(
                  0deg,
                  ${styles.glowColor} 0px,
                  ${styles.glowColor} 2px,
                  transparent 2px,
                  transparent 4px
                )
              `,
            }}
          />
        </motion.div>

        {/* 分段标记（用于某些进度条类型） */}
        {(variant === 'health' || variant === 'hunger' || variant === 'armor') && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              pointerEvents: 'none',
              background: `
                repeating-linear-gradient(
                  90deg,
                  transparent,
                  transparent calc(100% / 20 - 1px),
                  ${styles.borderColor} calc(100% / 20 - 1px),
                  ${styles.borderColor} calc(100% / 20)
                )
              `,
            }}
          />
        )}
      </Box>

      {/* 进度文本（覆盖在进度条上） */}
      {showValue && !label && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontFamily: '"Minecraft", "Press Start 2P", monospace',
            fontSize: sizeStyles.fontSize,
            color: '#FFFFFF',
            textShadow: `
              1px 1px 0 #000000,
              -1px -1px 0 #000000,
              1px -1px 0 #000000,
              -1px 1px 0 #000000
            `,
            fontWeight: 'bold',
            pointerEvents: 'none',
          }}
        >
          {Math.round(percentage)}%
        </Box>
      )}
    </Box>
  )
}

export default MinecraftProgress
