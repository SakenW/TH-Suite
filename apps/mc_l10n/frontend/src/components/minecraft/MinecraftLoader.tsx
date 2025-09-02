import React from 'react';
import { Box, Typography, keyframes } from '@mui/material';
import { motion } from 'framer-motion';

interface MinecraftLoaderProps {
  text?: string;
  variant?: 'blocks' | 'creeper' | 'portal' | 'crafting' | 'chest';
  size?: 'small' | 'medium' | 'large';
  fullScreen?: boolean;
}

// 方块旋转动画
const blockSpin = keyframes`
  0% { transform: rotateY(0deg) rotateX(0deg); }
  50% { transform: rotateY(180deg) rotateX(180deg); }
  100% { transform: rotateY(360deg) rotateX(360deg); }
`;

// 苦力怕脉动动画
const creeperPulse = keyframes`
  0%, 100% { transform: scale(1); filter: brightness(1); }
  25% { transform: scale(1.1); filter: brightness(1.2); }
  50% { transform: scale(0.9); filter: brightness(0.8); }
  75% { transform: scale(1.05); filter: brightness(1.5); }
`;

// 传送门波动动画
const portalWave = keyframes`
  0% { transform: scale(1) rotate(0deg); opacity: 0.8; }
  33% { transform: scale(1.2) rotate(120deg); opacity: 1; }
  66% { transform: scale(0.8) rotate(240deg); opacity: 0.6; }
  100% { transform: scale(1) rotate(360deg); opacity: 0.8; }
`;

// 工作台组装动画
const craftingAssemble = keyframes`
  0% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-10px) rotate(90deg); }
  50% { transform: translateY(0) rotate(180deg); }
  75% { transform: translateY(-10px) rotate(270deg); }
  100% { transform: translateY(0) rotate(360deg); }
`;

// 箱子开合动画
const chestOpen = keyframes`
  0%, 100% { transform: rotateX(0deg); }
  50% { transform: rotateX(-25deg); }
`;

export const MinecraftLoader: React.FC<MinecraftLoaderProps> = ({
  text = '加载中...',
  variant = 'blocks',
  size = 'medium',
  fullScreen = false
}) => {
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { blockSize: 20, fontSize: '12px', gap: 8 };
      case 'large':
        return { blockSize: 60, fontSize: '18px', gap: 20 };
      case 'medium':
      default:
        return { blockSize: 40, fontSize: '14px', gap: 12 };
    }
  };

  const sizeStyles = getSizeStyles();

  const renderLoader = () => {
    switch (variant) {
      case 'blocks':
        return (
          <Box sx={{ display: 'flex', gap: `${sizeStyles.gap}px` }}>
            {['#7DB037', '#2EAFCC', '#FFA000', '#DC2B2B'].map((color, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
              >
                <Box
                  sx={{
                    width: sizeStyles.blockSize,
                    height: sizeStyles.blockSize,
                    background: `linear-gradient(135deg, ${color} 0%, ${color}CC 50%, ${color}88 100%)`,
                    border: '2px solid',
                    borderTopColor: '#FFFFFF66',
                    borderLeftColor: '#FFFFFF66',
                    borderRightColor: '#00000066',
                    borderBottomColor: '#00000066',
                    borderRadius: '2px',
                    animation: `${blockSpin} 2s ease-in-out infinite`,
                    animationDelay: `${index * 0.2}s`,
                    boxShadow: '2px 2px 8px rgba(0,0,0,0.4)',
                    position: 'relative',
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: '2px',
                      left: '2px',
                      right: '2px',
                      bottom: '2px',
                      background: `linear-gradient(45deg, transparent 30%, ${color}44 50%, transparent 70%)`,
                      borderRadius: '1px',
                    },
                  }}
                />
              </motion.div>
            ))}
          </Box>
        );

      case 'creeper':
        return (
          <Box
            sx={{
              width: sizeStyles.blockSize * 1.5,
              height: sizeStyles.blockSize * 2,
              position: 'relative',
              animation: `${creeperPulse} 1.5s ease-in-out infinite`,
            }}
          >
            {/* 苦力怕头部 */}
            <Box
              sx={{
                width: '100%',
                height: '50%',
                background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)',
                border: '2px solid #1B5E20',
                borderRadius: '2px',
                position: 'relative',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            >
              {/* 眼睛 */}
              <Box
                sx={{
                  position: 'absolute',
                  top: '30%',
                  left: '20%',
                  width: '20%',
                  height: '25%',
                  background: '#000000',
                  borderRadius: '1px',
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  top: '30%',
                  right: '20%',
                  width: '20%',
                  height: '25%',
                  background: '#000000',
                  borderRadius: '1px',
                }}
              />
              {/* 嘴巴 */}
              <Box
                sx={{
                  position: 'absolute',
                  bottom: '20%',
                  left: '30%',
                  width: '40%',
                  height: '15%',
                  background: '#000000',
                  borderRadius: '1px',
                }}
              />
            </Box>
            {/* 苦力怕身体 */}
            <Box
              sx={{
                width: '100%',
                height: '50%',
                background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)',
                border: '2px solid #1B5E20',
                borderRadius: '2px',
                marginTop: '2px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            />
          </Box>
        );

      case 'portal':
        return (
          <Box sx={{ position: 'relative', width: sizeStyles.blockSize * 2, height: sizeStyles.blockSize * 2 }}>
            {[0, 1, 2].map(ring => (
              <Box
                key={ring}
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  width: `${100 - ring * 20}%`,
                  height: `${100 - ring * 20}%`,
                  transform: 'translate(-50%, -50%)',
                  border: '3px solid',
                  borderColor: ring === 0 ? '#9B59B6' : ring === 1 ? '#8E44AD' : '#7D3C98',
                  borderRadius: '50%',
                  animation: `${portalWave} ${2 + ring * 0.5}s ease-in-out infinite`,
                  animationDelay: `${ring * 0.2}s`,
                  boxShadow: `0 0 20px ${ring === 0 ? '#9B59B6' : ring === 1 ? '#8E44AD' : '#7D3C98'}`,
                }}
              />
            ))}
            {/* 中心粒子 */}
            <Box
              sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '10px',
                height: '10px',
                background: '#FFFFFF',
                borderRadius: '50%',
                boxShadow: '0 0 20px #FFFFFF',
                animation: `${creeperPulse} 1s ease-in-out infinite`,
              }}
            />
          </Box>
        );

      case 'crafting':
        return (
          <Box sx={{ position: 'relative', width: sizeStyles.blockSize * 2, height: sizeStyles.blockSize * 2 }}>
            {/* 3x3 工作台网格 */}
            {[0, 1, 2, 3, 4, 5, 6, 7, 8].map(index => {
              const row = Math.floor(index / 3);
              const col = index % 3;
              const colors = ['#8B6239', '#C6A57A', '#D7CCC8'];
              const color = colors[index % 3];
              
              return (
                <Box
                  key={index}
                  sx={{
                    position: 'absolute',
                    left: `${col * 33.33}%`,
                    top: `${row * 33.33}%`,
                    width: '30%',
                    height: '30%',
                    background: `linear-gradient(135deg, ${color} 0%, ${color}BB 100%)`,
                    border: '1px solid #4B2909',
                    borderRadius: '1px',
                    animation: `${craftingAssemble} 3s ease-in-out infinite`,
                    animationDelay: `${index * 0.1}s`,
                    boxShadow: '1px 1px 4px rgba(0,0,0,0.3)',
                  }}
                />
              );
            })}
          </Box>
        );

      case 'chest':
        return (
          <Box sx={{ position: 'relative', width: sizeStyles.blockSize * 2, height: sizeStyles.blockSize * 1.5 }}>
            {/* 箱子盖子 */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '40%',
                background: 'linear-gradient(180deg, #8B6239 0%, #6B4929 100%)',
                border: '2px solid #4B2909',
                borderBottom: 'none',
                borderRadius: '2px 2px 0 0',
                transformOrigin: 'bottom',
                animation: `${chestOpen} 2s ease-in-out infinite`,
                boxShadow: '0 -2px 8px rgba(0,0,0,0.4)',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: '30%',
                  height: '4px',
                  background: '#FFD700',
                  borderRadius: '2px',
                  boxShadow: '0 0 10px #FFD700',
                },
              }}
            />
            {/* 箱子主体 */}
            <Box
              sx={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: '60%',
                background: 'linear-gradient(180deg, #6B4929 0%, #5B3919 100%)',
                border: '2px solid #4B2909',
                borderTop: '1px solid #4B2909',
                borderRadius: '0 0 2px 2px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: '2px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: '20%',
                  height: '40%',
                  background: '#2B2B2B',
                  borderRadius: '1px',
                },
              }}
            />
          </Box>
        );

      default:
        return null;
    }
  };

  const content = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 3,
        p: 4,
      }}
    >
      {renderLoader()}
      <Typography
        sx={{
          fontFamily: '"Minecraft", "Press Start 2P", monospace',
          fontSize: sizeStyles.fontSize,
          color: '#FFFFFF',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
        }}
      >
        {text}
      </Typography>
      {/* 加载提示点 */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        {[0, 1, 2].map(index => (
          <motion.div
            key={index}
            animate={{
              opacity: [0.3, 1, 0.3],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay: index * 0.2,
            }}
          >
            <Box
              sx={{
                width: 8,
                height: 8,
                background: '#FFFFFF',
                borderRadius: '50%',
                boxShadow: '0 0 8px rgba(255,255,255,0.8)',
              }}
            />
          </motion.div>
        ))}
      </Box>
    </Box>
  );

  if (fullScreen) {
    return (
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'linear-gradient(135deg, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.85) 100%)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
        }}
      >
        {content}
      </Box>
    );
  }

  return content;
};

export default MinecraftLoader;