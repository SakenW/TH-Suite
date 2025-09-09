/**
 * Minecraft 风格工具提示组件
 * 模拟 Minecraft 游戏内的物品提示框样式
 */

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createPortal } from 'react-dom'
import { minecraftColors, getRarityColor } from '../../theme/minecraft/colors'
import { typography } from '../../theme/minecraft/typography'

export interface MCTooltipProps {
  children: React.ReactNode
  content: React.ReactNode | string
  title?: string
  rarity?: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' | 'mythic'
  enchanted?: boolean
  stats?: Array<{ label: string; value: string | number; color?: string }>
  description?: string
  lore?: string[]
  position?: 'top' | 'bottom' | 'left' | 'right' | 'auto'
  delay?: number
  disabled?: boolean
  interactive?: boolean
  maxWidth?: number
  className?: string
  style?: React.CSSProperties
}

const MCTooltip: React.FC<MCTooltipProps> = ({
  children,
  content,
  title,
  rarity = 'common',
  enchanted = false,
  stats,
  description,
  lore,
  position = 'auto',
  delay = 200,
  disabled = false,
  interactive = false,
  maxWidth = 300,
  className = '',
  style = {},
}) => {
  const [isVisible, setIsVisible] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [actualPosition, setActualPosition] = useState(position)
  const triggerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<number>()

  // 计算工具提示位置
  const calculatePosition = () => {
    if (!triggerRef.current || !tooltipRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()
    const windowWidth = window.innerWidth
    const windowHeight = window.innerHeight

    let x = 0
    let y = 0
    let finalPosition = position

    // 自动定位
    if (position === 'auto') {
      const spaceTop = triggerRect.top
      const spaceBottom = windowHeight - triggerRect.bottom
      const spaceLeft = triggerRect.left
      const spaceRight = windowWidth - triggerRect.right

      if (spaceBottom >= tooltipRect.height + 10) {
        finalPosition = 'bottom'
      } else if (spaceTop >= tooltipRect.height + 10) {
        finalPosition = 'top'
      } else if (spaceRight >= tooltipRect.width + 10) {
        finalPosition = 'right'
      } else if (spaceLeft >= tooltipRect.width + 10) {
        finalPosition = 'left'
      } else {
        finalPosition = 'bottom'
      }
    }

    // 根据位置计算坐标
    switch (finalPosition) {
      case 'top':
        x = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2
        y = triggerRect.top - tooltipRect.height - 8
        break
      case 'bottom':
        x = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2
        y = triggerRect.bottom + 8
        break
      case 'left':
        x = triggerRect.left - tooltipRect.width - 8
        y = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2
        break
      case 'right':
        x = triggerRect.right + 8
        y = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2
        break
    }

    // 边界检查
    x = Math.max(8, Math.min(x, windowWidth - tooltipRect.width - 8))
    y = Math.max(8, Math.min(y, windowHeight - tooltipRect.height - 8))

    setTooltipPosition({ x, y })
    setActualPosition(finalPosition)
  }

  // 显示工具提示
  const showTooltip = () => {
    if (disabled) return

    clearTimeout(timeoutRef.current)
    timeoutRef.current = window.setTimeout(() => {
      setIsVisible(true)
    }, delay)
  }

  // 隐藏工具提示
  const hideTooltip = () => {
    clearTimeout(timeoutRef.current)
    if (!interactive) {
      setIsVisible(false)
    }
  }

  // 更新位置
  useEffect(() => {
    if (isVisible) {
      calculatePosition()

      // 监听滚动和调整大小
      const handleUpdate = () => calculatePosition()
      window.addEventListener('scroll', handleUpdate, true)
      window.addEventListener('resize', handleUpdate)

      return () => {
        window.removeEventListener('scroll', handleUpdate, true)
        window.removeEventListener('resize', handleUpdate)
      }
    }
  }, [isVisible])

  // 清理定时器
  useEffect(() => {
    return () => {
      clearTimeout(timeoutRef.current)
    }
  }, [])

  const rarityColor = getRarityColor(rarity)

  // 工具提示内容样式
  const tooltipStyles: React.CSSProperties = {
    position: 'fixed',
    left: `${tooltipPosition.x}px`,
    top: `${tooltipPosition.y}px`,
    zIndex: 10000,
    maxWidth: `${maxWidth}px`,
    padding: '8px',
    backgroundColor: minecraftColors.ui.background.tooltip,
    border: `2px solid ${minecraftColors.ui.border.dark}`,
    borderTop: `2px solid ${minecraftColors.ui.border.light}`,
    borderLeft: `2px solid ${minecraftColors.ui.border.light}`,
    boxShadow: '4px 4px 0px rgba(0, 0, 0, 0.75)',
    fontFamily: typography.fontFamily.minecraft,
    fontSize: typography.fontSize.tooltip,
    color: minecraftColors.ui.text.secondary,
    imageRendering: 'pixelated',
    pointerEvents: interactive ? 'auto' : 'none',
    ...style,
  }

  // 渲染工具提示内容
  const renderTooltipContent = () => {
    if (typeof content === 'string' && !title && !stats && !description && !lore) {
      // 简单文本提示
      return <div>{content}</div>
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {/* 标题 */}
        {title && (
          <div
            style={{
              color: enchanted ? minecraftColors.ui.text.enchanted : rarityColor,
              fontSize: typography.fontSize.normal,
              fontWeight: typography.fontWeight.bold,
              textShadow: enchanted ? '0 0 5px #9C6BFF' : 'none',
            }}
          >
            {title}
          </div>
        )}

        {/* 内容 */}
        {content && typeof content !== 'string' ? (
          content
        ) : content ? (
          <div style={{ color: minecraftColors.ui.text.secondary }}>{content}</div>
        ) : null}

        {/* 属性统计 */}
        {stats && stats.length > 0 && (
          <div
            style={{
              borderTop: `1px solid ${minecraftColors.ui.border.dark}`,
              paddingTop: '4px',
              marginTop: '4px',
            }}
          >
            {stats.map((stat, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: '16px',
                  color: stat.color || minecraftColors.formatting['§7'],
                  fontSize: typography.fontSize.small,
                }}
              >
                <span>{stat.label}:</span>
                <span style={{ color: stat.color || minecraftColors.formatting['§a'] }}>
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* 描述 */}
        {description && (
          <div
            style={{
              color: minecraftColors.formatting['§7'],
              fontSize: typography.fontSize.small,
              fontStyle: 'italic',
              borderTop: stats ? 'none' : `1px solid ${minecraftColors.ui.border.dark}`,
              paddingTop: stats ? '0' : '4px',
              marginTop: stats ? '0' : '4px',
            }}
          >
            {description}
          </div>
        )}

        {/* 传说文本 */}
        {lore && lore.length > 0 && (
          <div
            style={{
              borderTop: `1px solid ${minecraftColors.ui.border.dark}`,
              paddingTop: '4px',
              marginTop: '4px',
            }}
          >
            {lore.map((line, index) => (
              <div
                key={index}
                style={{
                  color: minecraftColors.formatting['§5'],
                  fontSize: typography.fontSize.small,
                  fontStyle: 'italic',
                }}
              >
                {line}
              </div>
            ))}
          </div>
        )}

        {/* 附魔标记 */}
        {enchanted && (
          <div
            style={{
              color: minecraftColors.ui.text.enchanted,
              fontSize: typography.fontSize.tiny,
              textAlign: 'center',
              marginTop: '4px',
              animation: 'enchantedGlow 2s ease-in-out infinite',
            }}
          >
            ✦ Enchanted ✦
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      {/* 触发器 */}
      <div
        ref={triggerRef}
        className={`mc-tooltip-trigger ${className}`}
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        style={{ display: 'inline-block' }}
      >
        {children}
      </div>

      {/* 工具提示 */}
      <AnimatePresence>
        {isVisible &&
          createPortal(
            <motion.div
              ref={tooltipRef}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.15 }}
              style={tooltipStyles}
              onMouseEnter={() => interactive && setIsVisible(true)}
              onMouseLeave={() => interactive && setIsVisible(false)}
            >
              {renderTooltipContent()}
            </motion.div>,
            document.body,
          )}
      </AnimatePresence>
    </>
  )
}

// 物品提示组件（预设样式）
export interface MCItemTooltipProps {
  children: React.ReactNode
  itemName: string
  itemType?: string
  rarity?: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' | 'mythic'
  enchantments?: Array<{ name: string; level: number }>
  durability?: { current: number; max: number }
  attributes?: Array<{ name: string; value: string }>
  lore?: string[]
  stackSize?: number
  className?: string
}

export const MCItemTooltip: React.FC<MCItemTooltipProps> = ({
  children,
  itemName,
  itemType,
  rarity = 'common',
  enchantments,
  durability,
  attributes,
  lore,
  stackSize,
  className = '',
}) => {
  const stats = []

  // 添加物品类型
  if (itemType) {
    stats.push({ label: 'Type', value: itemType })
  }

  // 添加耐久度
  if (durability) {
    const percentage = Math.round((durability.current / durability.max) * 100)
    const color =
      percentage > 50
        ? minecraftColors.formatting['§a']
        : percentage > 25
          ? minecraftColors.formatting['§e']
          : minecraftColors.formatting['§c']

    stats.push({
      label: 'Durability',
      value: `${durability.current}/${durability.max}`,
      color,
    })
  }

  // 添加堆叠数量
  if (stackSize && stackSize > 1) {
    stats.push({ label: 'Stack Size', value: stackSize })
  }

  // 添加属性
  if (attributes) {
    attributes.forEach(attr => {
      stats.push({ label: attr.name, value: attr.value })
    })
  }

  // 生成附魔描述
  const enchantmentLines = enchantments?.map(ench => {
    const romanNumerals = ['', 'I', 'II', 'III', 'IV', 'V']
    return `${ench.name} ${romanNumerals[ench.level] || ench.level}`
  })

  return (
    <MCTooltip
      title={itemName}
      rarity={rarity}
      enchanted={!!enchantments && enchantments.length > 0}
      stats={stats.length > 0 ? stats : undefined}
      description={enchantmentLines?.join(', ')}
      lore={lore}
      className={className}
    >
      {children}
    </MCTooltip>
  )
}

export default MCTooltip
