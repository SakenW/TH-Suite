/**
 * Minecraft 风格进度条组件
 * 模拟 Minecraft 游戏内的经验条、生命值条等
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { minecraftColors } from '../../theme/minecraft/colors';
import { typography } from '../../theme/minecraft/typography';
import { createExperienceBar, createHealthBar, createArmorBar } from '../../theme/minecraft/textures';

export interface MCProgressProps {
  value: number;
  max?: number;
  variant?: 'experience' | 'health' | 'hunger' | 'armor' | 'default' | 'loading';
  size?: 'small' | 'medium' | 'large';
  showLabel?: boolean;
  showPercentage?: boolean;
  animated?: boolean;
  striped?: boolean;
  indeterminate?: boolean;
  label?: string;
  className?: string;
  style?: React.CSSProperties;
}

const MCProgress: React.FC<MCProgressProps> = ({
  value,
  max = 100,
  variant = 'default',
  size = 'medium',
  showLabel = false,
  showPercentage = false,
  animated = true,
  striped = false,
  indeterminate = false,
  label,
  className = '',
  style = {},
}) => {
  const [displayValue, setDisplayValue] = useState(0);
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  // 动画显示数值
  useEffect(() => {
    if (animated && !indeterminate) {
      const timer = setTimeout(() => {
        setDisplayValue(percentage);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setDisplayValue(percentage);
    }
  }, [percentage, animated, indeterminate]);

  // 获取变体颜色
  const getVariantColor = () => {
    switch (variant) {
      case 'experience':
        return minecraftColors.ui.progress.experience;
      case 'health':
        return minecraftColors.ui.progress.health;
      case 'hunger':
        return minecraftColors.ui.progress.hunger;
      case 'armor':
        return minecraftColors.ui.progress.armor;
      case 'loading':
        return minecraftColors.primary.diamond;
      default:
        return minecraftColors.ui.progress.fill;
    }
  };

  // 获取尺寸
  const getSize = () => {
    switch (size) {
      case 'small':
        return { height: '8px', fontSize: typography.fontSize.tiny };
      case 'large':
        return { height: '24px', fontSize: typography.fontSize.medium };
      default:
        return { height: '16px', fontSize: typography.fontSize.small };
    }
  };

  const sizeStyles = getSize();
  const color = getVariantColor();

  // 容器样式
  const containerStyles: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    height: sizeStyles.height,
    backgroundColor: minecraftColors.ui.progress.empty,
    border: `2px solid ${minecraftColors.ui.border.dark}`,
    borderTop: `2px solid ${minecraftColors.ui.border.dark}`,
    borderLeft: `2px solid ${minecraftColors.ui.border.dark}`,
    borderRight: `2px solid ${minecraftColors.ui.border.light}`,
    borderBottom: `2px solid ${minecraftColors.ui.border.light}`,
    imageRendering: 'pixelated',
    overflow: 'hidden',
    ...style,
  };

  // 进度条样式
  const barStyles: React.CSSProperties = {
    height: '100%',
    backgroundColor: color,
    backgroundImage: striped ? `
      repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(255, 255, 255, 0.1) 10px,
        rgba(255, 255, 255, 0.1) 20px
      )
    ` : 'none',
    backgroundSize: striped ? '20px 20px' : 'auto',
    transition: animated && !indeterminate ? 'width 0.3s ease' : 'none',
    position: 'relative',
    overflow: 'hidden',
  };

  // 闪光效果（用于经验条等）
  const glowStyles: React.CSSProperties = variant === 'experience' ? {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `linear-gradient(90deg, 
      transparent 0%, 
      rgba(255, 255, 255, 0.3) 50%, 
      transparent 100%
    )`,
    animation: 'shimmer 2s infinite',
  } : {};

  return (
    <div className={`mc-progress-container ${className}`}>
      {/* 标签 */}
      {(showLabel || label) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '4px',
            fontFamily: typography.fontFamily.minecraft,
            fontSize: sizeStyles.fontSize,
            color: minecraftColors.ui.text.primary,
          }}
        >
          <span>{label || `${Math.round(value)}/${max}`}</span>
          {showPercentage && (
            <span>{Math.round(displayValue)}%</span>
          )}
        </div>
      )}

      {/* 进度条容器 */}
      <div style={containerStyles}>
        {indeterminate ? (
          // 不确定进度动画
          <motion.div
            style={{
              position: 'absolute',
              height: '100%',
              width: '30%',
              backgroundColor: color,
              ...barStyles,
            }}
            animate={{
              x: ['0%', '233%'],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ) : (
          // 确定进度条
          <motion.div
            style={barStyles}
            initial={{ width: 0 }}
            animate={{ width: `${displayValue}%` }}
            transition={animated ? { duration: 0.3, ease: 'easeOut' } : { duration: 0 }}
          >
            {variant === 'experience' && <div style={glowStyles} />}
            
            {/* 条纹动画 */}
            {striped && animated && (
              <motion.div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundImage: `
                    repeating-linear-gradient(
                      45deg,
                      transparent,
                      transparent 10px,
                      rgba(255, 255, 255, 0.1) 10px,
                      rgba(255, 255, 255, 0.1) 20px
                    )
                  `,
                  backgroundSize: '20px 20px',
                }}
                animate={{
                  backgroundPosition: ['0px 0px', '20px 20px'],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  ease: 'linear',
                }}
              />
            )}
          </motion.div>
        )}

        {/* 分段标记（用于生命值等） */}
        {(variant === 'health' || variant === 'armor') && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              pointerEvents: 'none',
            }}
          >
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  borderRight: i < 9 ? `1px solid ${minecraftColors.ui.border.dark}` : 'none',
                  opacity: 0.3,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// 经验等级显示组件
export interface MCExperienceLevelProps {
  level: number;
  experience: number;
  maxExperience: number;
  size?: 'small' | 'medium' | 'large';
  className?: string;
  style?: React.CSSProperties;
}

export const MCExperienceLevel: React.FC<MCExperienceLevelProps> = ({
  level,
  experience,
  maxExperience,
  size = 'medium',
  className = '',
  style = {},
}) => {
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { fontSize: '16px', orbSize: '32px' };
      case 'large':
        return { fontSize: '32px', orbSize: '64px' };
      default:
        return { fontSize: '24px', orbSize: '48px' };
    }
  };

  const sizeStyles = getSizeStyles();

  return (
    <div
      className={`mc-experience-level ${className}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        ...style,
      }}
    >
      {/* 等级球 */}
      <motion.div
        style={{
          width: sizeStyles.orbSize,
          height: sizeStyles.orbSize,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${minecraftColors.ui.progress.experience} 0%, ${minecraftColors.primary.emerald} 100%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: `0 0 10px ${minecraftColors.ui.progress.experience}`,
          border: `2px solid ${minecraftColors.ui.border.dark}`,
        }}
        animate={{
          boxShadow: [
            `0 0 10px ${minecraftColors.ui.progress.experience}`,
            `0 0 20px ${minecraftColors.ui.progress.experience}`,
            `0 0 10px ${minecraftColors.ui.progress.experience}`,
          ],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <span
          style={{
            color: minecraftColors.ui.text.secondary,
            fontSize: sizeStyles.fontSize,
            fontFamily: typography.fontFamily.minecraft,
            fontWeight: typography.fontWeight.bold,
            textShadow: '2px 2px 0px rgba(0, 0, 0, 0.5)',
          }}
        >
          {level}
        </span>
      </motion.div>

      {/* 经验条 */}
      <div style={{ flex: 1 }}>
        <MCProgress
          value={experience}
          max={maxExperience}
          variant="experience"
          size={size}
          showLabel={true}
          animated={true}
        />
      </div>
    </div>
  );
};

// 状态条组（生命值、饥饿值、护甲值）
export interface MCStatusBarsProps {
  health: number;
  maxHealth?: number;
  hunger: number;
  maxHunger?: number;
  armor?: number;
  maxArmor?: number;
  showLabels?: boolean;
  vertical?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export const MCStatusBars: React.FC<MCStatusBarsProps> = ({
  health,
  maxHealth = 20,
  hunger,
  maxHunger = 20,
  armor = 0,
  maxArmor = 20,
  showLabels = true,
  vertical = false,
  className = '',
  style = {},
}) => {
  const containerStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: vertical ? 'column' : 'row',
    gap: '12px',
    padding: '8px',
    backgroundColor: minecraftColors.ui.background.overlay,
    borderRadius: '4px',
    ...style,
  };

  return (
    <div className={`mc-status-bars ${className}`} style={containerStyles}>
      {/* 生命值 */}
      <div style={{ flex: 1 }}>
        {showLabels && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginBottom: '4px',
              fontSize: typography.fontSize.small,
              fontFamily: typography.fontFamily.minecraft,
              color: minecraftColors.ui.text.secondary,
            }}
          >
            <span style={{ color: minecraftColors.ui.progress.health }}>❤</span>
            <span>Health</span>
          </div>
        )}
        <MCProgress
          value={health}
          max={maxHealth}
          variant="health"
          size="small"
          showPercentage={false}
        />
      </div>

      {/* 饥饿值 */}
      <div style={{ flex: 1 }}>
        {showLabels && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginBottom: '4px',
              fontSize: typography.fontSize.small,
              fontFamily: typography.fontFamily.minecraft,
              color: minecraftColors.ui.text.secondary,
            }}
          >
            <span style={{ color: minecraftColors.ui.progress.hunger }}>🍖</span>
            <span>Hunger</span>
          </div>
        )}
        <MCProgress
          value={hunger}
          max={maxHunger}
          variant="hunger"
          size="small"
          showPercentage={false}
        />
      </div>

      {/* 护甲值 */}
      {armor > 0 && (
        <div style={{ flex: 1 }}>
          {showLabels && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                marginBottom: '4px',
                fontSize: typography.fontSize.small,
                fontFamily: typography.fontFamily.minecraft,
                color: minecraftColors.ui.text.secondary,
              }}
            >
              <span style={{ color: minecraftColors.ui.progress.armor }}>🛡</span>
              <span>Armor</span>
            </div>
          )}
          <MCProgress
            value={armor}
            max={maxArmor}
            variant="armor"
            size="small"
            showPercentage={false}
          />
        </div>
      )}
    </div>
  );
};

export default MCProgress;