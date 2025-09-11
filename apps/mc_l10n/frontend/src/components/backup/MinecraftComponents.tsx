import React, { useState } from 'react'
import { Box, keyframes } from '@mui/material'
import { motion, AnimatePresence } from 'framer-motion'
import { minecraftColors } from '../theme/minecraftTheme'
import { playExplosionSound } from '../utils/soundEffects'

// 方块旋转动画
const blockRotate = keyframes`
  0% { transform: rotateY(0deg); }
  100% { transform: rotateY(360deg); }
`

// 粒子闪烁动画
const particleGlow = keyframes`
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
`

// 经验条填充动画
const xpBarFill = keyframes`
  0% { width: 0%; }
  100% { width: 100%; }
`

// 苦力怕闪烁动画
const creeperBlink = keyframes`
  0%, 90% { opacity: 1; }
  95% { opacity: 0.3; }
  100% { opacity: 1; }
`

// 苦力怕爆炸动画
const creeperExplode = keyframes`
  0% { transform: scale(1); filter: brightness(1); }
  50% { transform: scale(1.2); filter: brightness(2); }
  100% { transform: scale(0); filter: brightness(0); opacity: 0; }
`

// Minecraft方块图标组件
export const MinecraftBlock: React.FC<{
  type?: 'grass' | 'stone' | 'diamond' | 'gold' | 'iron' | 'emerald'
  size?: number
  animated?: boolean
}> = ({ type = 'grass', size = 24, animated = false }) => {
  const getBlockColor = () => {
    switch (type) {
      case 'grass':
        return minecraftColors.grassGreen
      case 'stone':
        return minecraftColors.stoneGray
      case 'diamond':
        return minecraftColors.diamondBlue
      case 'gold':
        return minecraftColors.goldYellow
      case 'iron':
        return minecraftColors.iron
      case 'emerald':
        return '#50C878' // 翠绿色
      default:
        return minecraftColors.grassGreen
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{
        opacity: 1,
        scale: 1,
        rotateY: animated ? 360 : 0,
      }}
      transition={{
        opacity: { duration: 0.3 },
        scale: { duration: 0.3 },
        rotateY: animated ? { duration: 3, repeat: Infinity, ease: 'linear' } : { duration: 0 },
      }}
      whileHover={{ scale: 1.1, rotateY: animated ? undefined : 15 }}
    >
      <Box
        sx={{
          width: size,
          height: size,
          background: `linear-gradient(135deg, ${getBlockColor()}, ${getBlockColor()}dd)`,
          border: '2px solid',
          borderTopColor: '#FFFFFF88',
          borderLeftColor: '#FFFFFF88',
          borderRightColor: '#00000044',
          borderBottomColor: '#00000044',
          borderRadius: '2px',
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: '2px',
            left: '2px',
            right: '2px',
            bottom: '2px',
            background: `linear-gradient(45deg, transparent 30%, ${getBlockColor()}44 50%, transparent 70%)`,
            borderRadius: '1px',
          },
        }}
      />
    </motion.div>
  )
}

// 粒子效果组件
export const ParticleEffect: React.FC<{
  count?: number
  color?: string
}> = ({ count = 5, color = minecraftColors.experienceGreen }) => {
  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      {Array.from({ length: count }).map((_, i) => (
        <Box
          key={i}
          sx={{
            position: 'absolute',
            width: '4px',
            height: '4px',
            backgroundColor: color,
            borderRadius: '50%',
            top: `${Math.random() * 80 + 10}%`,
            left: `${Math.random() * 80 + 10}%`,
            animation: `${particleGlow} ${1 + Math.random() * 2}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 2}s`,
            boxShadow: `0 0 6px ${color}`,
          }}
        />
      ))}
    </Box>
  )
}

// Minecraft风格的经验条
export const ExperienceBar: React.FC<{
  progress: number
  level?: number
  animated?: boolean
}> = ({ progress, level, animated = true }) => {
  return (
    <Box sx={{ position: 'relative', width: '100%' }}>
      {/* 经验条背景 */}
      <Box
        sx={{
          width: '100%',
          height: '12px',
          backgroundColor: minecraftColors.inventorySlot,
          border: '1px solid #000000',
          borderRadius: '2px',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)',
        }}
      >
        {/* 经验条填充 */}
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(progress, 100)}%` }}
          transition={{ duration: animated ? 0.8 : 0, ease: 'easeOut' }}
          style={{
            height: '100%',
            background: `linear-gradient(90deg, ${minecraftColors.experienceGreen}, #9AFF9A, ${minecraftColors.experienceGreen})`,
            borderRadius: '1px',
            position: 'relative',
            boxShadow: `0 0 8px ${minecraftColors.experienceGreen}88`,
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '50%',
              background: 'linear-gradient(180deg, rgba(255,255,255,0.3), transparent)',
              borderRadius: '1px 1px 0 0',
            }}
          />
        </motion.div>
      </Box>

      {/* 等级显示 */}
      {level !== undefined && (
        <Box
          sx={{
            position: 'absolute',
            top: '-20px',
            right: 0,
            fontSize: '12px',
            fontWeight: 'bold',
            color: minecraftColors.experienceGreen,
            textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
          }}
        >
          Level {level}
        </Box>
      )}
    </Box>
  )
}

// Minecraft风格的卡片容器
export const MinecraftCard: React.FC<{
  children: React.ReactNode
  variant?: 'default' | 'inventory' | 'crafting'
  glowing?: boolean
}> = ({ children, variant = 'default', glowing = false }) => {
  const getCardStyle = () => {
    switch (variant) {
      case 'inventory':
        return {
          backgroundColor: '#8B8B8B',
          border: '3px solid',
          borderTopColor: '#FFFFFF',
          borderLeftColor: '#FFFFFF',
          borderRightColor: '#373737',
          borderBottomColor: '#373737',
        }
      case 'crafting':
        return {
          backgroundColor: '#A0A0A0',
          border: '2px solid',
          borderTopColor: '#FFFFFF',
          borderLeftColor: '#FFFFFF',
          borderRightColor: '#555555',
          borderBottomColor: '#555555',
        }
      default:
        return {
          backgroundColor: '#F0F0F0',
          border: '2px solid',
          borderTopColor: '#FFFFFF',
          borderLeftColor: '#FFFFFF',
          borderRightColor: '#CCCCCC',
          borderBottomColor: '#CCCCCC',
        }
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <Box
        sx={{
          ...getCardStyle(),
          borderRadius: '4px',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: glowing
            ? `0 0 20px ${minecraftColors.diamondBlue}88, 0 4px 8px rgba(0,0,0,0.3)`
            : '0 4px 8px rgba(0,0,0,0.2)',
          cursor: 'pointer',
          '&::before': glowing
            ? {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `linear-gradient(45deg, transparent, ${minecraftColors.diamondBlue}22, transparent)`,
                pointerEvents: 'none',
              }
            : {},
        }}
      >
        {children}
        {glowing && <ParticleEffect count={3} color={minecraftColors.diamondBlue} />}
      </Box>
    </motion.div>
  )
}

// Minecraft风格的按钮
export const MinecraftButton: React.FC<{
  children: React.ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'danger'
  disabled?: boolean
  size?: 'small' | 'medium' | 'large'
}> = ({ children, onClick, variant = 'primary', disabled = false, size = 'medium' }) => {
  const getButtonColors = () => {
    switch (variant) {
      case 'secondary':
        return {
          bg: minecraftColors.stoneGray,
          bgHover: minecraftColors.cobblestone,
        }
      case 'danger':
        return {
          bg: minecraftColors.redstone,
          bgHover: '#B71C1C',
        }
      default:
        return {
          bg: minecraftColors.grassGreen,
          bgHover: '#689F38',
        }
    }
  }

  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { padding: '6px 12px', fontSize: '0.875rem' }
      case 'large':
        return { padding: '12px 24px', fontSize: '1.125rem' }
      default:
        return { padding: '8px 16px', fontSize: '1rem' }
    }
  }

  const colors = getButtonColors()
  const sizeStyles = getSizeStyles()

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={disabled ? {} : { scale: 1.05, y: -1 }}
      whileTap={disabled ? {} : { scale: 0.95 }}
      transition={{ duration: 0.1, ease: 'easeOut' }}
      style={{
        ...sizeStyles,
        backgroundColor: disabled ? '#CCCCCC' : colors.bg,
        border: '2px solid',
        borderTopColor: disabled ? '#FFFFFF' : '#FFFFFF',
        borderLeftColor: disabled ? '#FFFFFF' : '#FFFFFF',
        borderRightColor: disabled ? '#999999' : colors.bgHover,
        borderBottomColor: disabled ? '#999999' : colors.bgHover,
        borderRadius: '4px',
        color: disabled ? '#666666' : '#FFFFFF',
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        textShadow: disabled ? 'none' : '1px 1px 2px rgba(0,0,0,0.5)',
        fontFamily: 'inherit',
        outline: 'none',
      }}
    >
      {children}
    </motion.button>
  )
}

// 苦力怕组件
export const Creeper: React.FC<{
  size?: number
  exploding?: boolean
  onExplode?: () => void
  shouldBlink?: boolean
  blinkInterval?: number
}> = ({ size = 48, exploding = false, onExplode, shouldBlink = true, blinkInterval = 3000 }) => {
  const [isBlinking, setIsBlinking] = useState(false)
  const [hasExploded, setHasExploded] = useState(false)
  const [autoBlinking, setAutoBlinking] = useState(false)

  // 自动闪烁效果
  React.useEffect(() => {
    if (!shouldBlink) return

    const interval = setInterval(() => {
      if (!hasExploded && !isBlinking) {
        setAutoBlinking(true)
        setTimeout(() => setAutoBlinking(false), 300)
      }
    }, blinkInterval)

    return () => clearInterval(interval)
  }, [shouldBlink, blinkInterval, hasExploded, isBlinking])

  const handleClick = () => {
    if (!exploding && !hasExploded) {
      setIsBlinking(true)
      setTimeout(async () => {
        setHasExploded(true)
        // 播放爆炸音效
        try {
          await playExplosionSound()
        } catch (error) {
          console.warn('爆炸音效播放失败:', error)
        }
        onExplode?.()
        // 重置状态以便重新使用
        setTimeout(() => {
          setHasExploded(false)
          setIsBlinking(false)
        }, 1000)
      }, 1500)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: hasExploded ? 0 : 1, y: 0 }}
      whileHover={{ scale: 1.1, y: -2 }}
      whileTap={{ scale: 0.95 }}
      onClick={handleClick}
      style={{
        cursor: 'pointer',
        display: 'inline-block',
      }}
    >
      <Box
        sx={{
          width: size,
          height: size * 1.5,
          background: hasExploded
            ? 'radial-gradient(circle, #ff6b35 0%, #4a5d23 70%)'
            : 'linear-gradient(135deg, #4a5d23 0%, #5a6d33 50%, #3a4d13 100%)',
          border: '2px solid #2d3d15',
          borderRadius: '2px',
          position: 'relative',
          cursor: 'pointer',
          animation: isBlinking || autoBlinking ? `${creeperBlink} 0.3s infinite` : 'none',
          transform: hasExploded ? 'scale(0)' : 'scale(1)',
          transition: hasExploded ? 'none' : 'transform 0.2s ease',
          boxShadow: hasExploded
            ? '0 0 20px #ff6b35, 0 0 40px #ff6b35, inset 0 0 10px rgba(255,107,53,0.3)'
            : '2px 2px 4px rgba(0,0,0,0.3), inset 1px 1px 2px rgba(255,255,255,0.1)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* 苦力怕的脸 */}
        <Box
          sx={{
            width: '80%',
            height: '60%',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gridTemplateRows: '1fr 1fr 1fr',
            gap: '1px',
          }}
        >
          {/* 眼睛 */}
          <Box sx={{ backgroundColor: '#000', gridColumn: '1', gridRow: '1' }} />
          <Box />
          <Box sx={{ backgroundColor: '#000', gridColumn: '3', gridRow: '1' }} />

          {/* 鼻子 */}
          <Box />
          <Box sx={{ backgroundColor: '#000', gridColumn: '2', gridRow: '2' }} />
          <Box />

          {/* 嘴巴 */}
          <Box sx={{ backgroundColor: '#000', gridColumn: '1', gridRow: '3' }} />
          <Box sx={{ backgroundColor: '#000', gridColumn: '2', gridRow: '3' }} />
          <Box sx={{ backgroundColor: '#000', gridColumn: '3', gridRow: '3' }} />
        </Box>

        {/* 爆炸效果 */}
        {hasExploded && (
          <motion.div
            initial={{ scale: 0, opacity: 1 }}
            animate={{ scale: 3, opacity: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: size,
              height: size,
              background:
                'radial-gradient(circle, #FF6B35 0%, #F7931E 30%, #FFD23F 60%, transparent 100%)',
              borderRadius: '50%',
              pointerEvents: 'none',
              fontSize: size * 0.8,
            }}
          >
            💥
          </motion.div>
        )}
      </Box>
    </motion.div>
  )
}

export default {
  MinecraftBlock,
  ParticleEffect,
  ExperienceBar,
  MinecraftCard,
  MinecraftButton,
  Creeper,
}
