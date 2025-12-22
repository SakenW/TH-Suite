import React from 'react'
import { Button, ButtonProps, Box } from '@mui/material'
import { motion } from 'framer-motion'
import { minecraftColors } from '../../theme/minecraftTheme'

interface MinecraftButtonProps extends Omit<ButtonProps, 'variant'> {
  variant?: 'contained' | 'outlined' | 'text' | 'minecraft'
  minecraftStyle?: 'grass' | 'stone' | 'diamond' | 'gold' | 'iron' | 'emerald' | 'redstone'
  pixelated?: boolean
  glowing?: boolean
}

export const MinecraftButton = React.forwardRef<HTMLButtonElement, MinecraftButtonProps>(
  (
    {
      children,
      variant = 'minecraft',
      minecraftStyle = 'stone',
      pixelated = true,
      glowing = false,
      disabled = false,
      onClick,
      startIcon,
      endIcon,
      fullWidth,
      size,
      color,
      ...props
    },
    ref,
  ) => {
    const getStyleColors = () => {
      if (disabled) {
        return {
          primary: '#808080',
          secondary: '#606060',
          highlight: '#909090',
          shadow: '#404040',
          text: '#A0A0A0',
        }
      }

      switch (minecraftStyle) {
        case 'grass':
          return {
            primary: '#7DB037',
            secondary: '#5D8A2A',
            highlight: '#9BC653',
            shadow: '#3E5A1B',
            text: '#FFFFFF',
          }
        case 'diamond':
          return {
            primary: '#2EAFCC',
            secondary: '#2391A9',
            highlight: '#5FC7DB',
            shadow: '#1A6B7F',
            text: '#FFFFFF',
          }
        case 'gold':
          return {
            primary: '#FFA000',
            secondary: '#F57C00',
            highlight: '#FFB74D',
            shadow: '#E65100',
            text: '#000000',
          }
        case 'iron':
          return {
            primary: '#D8D8D8',
            secondary: '#A8A8A8',
            highlight: '#ECECEC',
            shadow: '#686868',
            text: '#000000',
          }
        case 'emerald':
          return {
            primary: '#17C35C',
            secondary: '#0F9442',
            highlight: '#41D775',
            shadow: '#0A5E2A',
            text: '#FFFFFF',
          }
        case 'redstone':
          return {
            primary: '#DC2B2B',
            secondary: '#AA1E1E',
            highlight: '#E85454',
            shadow: '#7A1010',
            text: '#FFFFFF',
          }
        case 'stone':
        default:
          return {
            primary: '#8B8B8B',
            secondary: '#686868',
            highlight: '#A8A8A8',
            shadow: '#4A4A4A',
            text: '#FFFFFF',
          }
      }
    }

    const colors = getStyleColors()

    if (variant === 'minecraft') {
      return (
        <motion.div
          whileHover={!disabled ? { scale: 1.05 } : {}}
          whileTap={!disabled ? { scale: 0.98 } : {}}
          style={{ display: 'inline-block' }}
        >
          <Box
            component='button'
            ref={ref}
            onClick={disabled ? undefined : onClick}
            disabled={disabled}
            sx={{
              position: 'relative',
              padding: '12px 24px',
              fontSize: pixelated ? '14px' : '16px',
              fontFamily: pixelated ? '"Minecraft", "Press Start 2P", monospace' : 'inherit',
              fontWeight: 'bold',
              color: colors.text,
              background: `linear-gradient(180deg, ${colors.highlight} 0%, ${colors.primary} 50%, ${colors.secondary} 100%)`,
              border: 'none',
              borderRadius: 0,
              cursor: disabled ? 'not-allowed' : 'pointer',
              textTransform: 'uppercase',
              letterSpacing: pixelated ? '0.05em' : '0.02em',
              imageRendering: pixelated ? 'pixelated' : 'auto',
              transition: 'all 0.1s ease',
              boxShadow: `
              inset -2px -4px 0 ${colors.shadow},
              inset 2px 2px 0 ${colors.highlight},
              0 0 0 2px #000000
            `,
              '&:hover:not(:disabled)': {
                background: `linear-gradient(180deg, ${colors.highlight}dd 0%, ${colors.primary}dd 50%, ${colors.secondary}dd 100%)`,
                transform: 'translateY(-1px)',
                boxShadow: `
                inset -2px -4px 0 ${colors.shadow},
                inset 2px 2px 0 ${colors.highlight},
                0 0 0 2px #000000,
                ${glowing ? `0 0 20px ${colors.primary}88` : '0 2px 8px rgba(0,0,0,0.3)'}
              `,
              },
              '&:active:not(:disabled)': {
                transform: 'translateY(1px)',
                boxShadow: `
                inset -1px -2px 0 ${colors.shadow},
                inset 1px 1px 0 ${colors.highlight},
                0 0 0 2px #000000
              `,
              },
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `
                repeating-linear-gradient(
                  0deg,
                  transparent,
                  transparent 2px,
                  ${colors.highlight}11 2px,
                  ${colors.highlight}11 4px
                )
              `,
                pointerEvents: 'none',
              },
              ...(glowing &&
                !disabled && {
                  animation: 'minecraft-glow 2s ease-in-out infinite',
                  '@keyframes minecraft-glow': {
                    '0%, 100%': {
                      filter: 'brightness(1)',
                      boxShadow: `
                    inset -2px -4px 0 ${colors.shadow},
                    inset 2px 2px 0 ${colors.highlight},
                    0 0 0 2px #000000,
                    0 0 10px ${colors.primary}66
                  `,
                    },
                    '50%': {
                      filter: 'brightness(1.1)',
                      boxShadow: `
                    inset -2px -4px 0 ${colors.shadow},
                    inset 2px 2px 0 ${colors.highlight},
                    0 0 0 2px #000000,
                    0 0 20px ${colors.primary}aa
                  `,
                    },
                  },
                }),
              ...props.sx,
            }}
            {...props}
          >
            {children}
          </Box>
        </motion.div>
      )
    }

    // 标准Material-UI按钮样式
    return (
      <Button
        ref={ref}
        variant={variant as ButtonProps['variant']}
        disabled={disabled}
        onClick={onClick}
        startIcon={startIcon}
        endIcon={endIcon}
        fullWidth={fullWidth}
        size={size}
        color={color}
        {...props}
      >
        {children}
      </Button>
    )
  },
)

MinecraftButton.displayName = 'MinecraftButton'

export default MinecraftButton
