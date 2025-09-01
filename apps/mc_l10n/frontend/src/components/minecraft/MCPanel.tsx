/**
 * Minecraft 风格面板组件
 * 模拟 Minecraft 游戏内的窗口和面板样式
 */

import React from 'react';
import { motion } from 'framer-motion';
import { minecraftColors, get3DBorder } from '../../theme/minecraft/colors';
import { typography } from '../../theme/minecraft/typography';
import { textures, createBorderTexture } from '../../theme/minecraft/textures';

export interface MCPanelProps {
  children: React.ReactNode;
  title?: string;
  variant?: 'stone' | 'dirt' | 'planks' | 'glass' | 'obsidian' | 'inventory';
  padding?: 'none' | 'small' | 'medium' | 'large';
  border?: boolean;
  raised?: boolean;
  shadow?: boolean;
  closable?: boolean;
  onClose?: () => void;
  width?: string | number;
  height?: string | number;
  className?: string;
  style?: React.CSSProperties;
}

const MCPanel: React.FC<MCPanelProps> = ({
  children,
  title,
  variant = 'stone',
  padding = 'medium',
  border = true,
  raised = true,
  shadow = true,
  closable = false,
  onClose,
  width,
  height,
  className = '',
  style = {},
}) => {
  // 获取背景纹理
  const getBackgroundTexture = () => {
    switch (variant) {
      case 'dirt':
        return textures.dirt;
      case 'planks':
        return textures.planks;
      case 'glass':
        return textures.glass;
      case 'obsidian':
        return `linear-gradient(0deg, #1a0033 0%, #0d001a 100%)`;
      case 'inventory':
        return textures.inventory;
      default:
        return textures.stone;
    }
  };

  // 获取内边距
  const getPadding = () => {
    switch (padding) {
      case 'none':
        return '0';
      case 'small':
        return '8px';
      case 'large':
        return '24px';
      default:
        return '16px';
    }
  };

  const borderStyles = border ? get3DBorder(raised) : {};
  const backgroundTexture = getBackgroundTexture();

  const panelStyles: React.CSSProperties = {
    position: 'relative',
    width: width || 'auto',
    height: height || 'auto',
    backgroundColor: variant === 'glass' 
      ? 'rgba(139, 139, 139, 0.3)' 
      : minecraftColors.ui.background.primary,
    backgroundImage: backgroundTexture,
    backgroundSize: variant === 'inventory' ? '36px 36px' : '16px 16px',
    backgroundRepeat: 'repeat',
    ...borderStyles,
    padding: getPadding(),
    boxShadow: shadow ? '4px 4px 0px rgba(0, 0, 0, 0.5)' : 'none',
    imageRendering: 'pixelated',
    ...style,
  };

  return (
    <motion.div
      className={`mc-panel mc-panel-${variant} ${className}`}
      style={panelStyles}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      {/* 标题栏 */}
      {title && (
        <div
          style={{
            position: 'relative',
            margin: padding === 'none' ? '0' : `-${getPadding()} -${getPadding()} ${getPadding()} -${getPadding()}`,
            padding: '8px 12px',
            backgroundColor: minecraftColors.ui.background.secondary,
            borderBottom: `2px solid ${minecraftColors.ui.border.dark}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span
            style={{
              color: minecraftColors.ui.text.secondary,
              fontSize: typography.fontSize.subtitle,
              fontFamily: typography.fontFamily.minecraft,
              textShadow: '2px 2px 0px rgba(0, 0, 0, 0.5)',
            }}
          >
            {title}
          </span>
          
          {closable && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: minecraftColors.ui.text.secondary,
                fontSize: typography.fontSize.large,
                fontFamily: typography.fontFamily.minecraft,
                cursor: 'pointer',
                padding: '0 4px',
                opacity: 0.7,
                transition: 'opacity 0.2s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* 内容区 */}
      {children}
    </motion.div>
  );
};

// 物品栏格子组件
export interface MCInventorySlotProps {
  item?: React.ReactNode;
  count?: number;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  size?: number;
  tooltip?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const MCInventorySlot: React.FC<MCInventorySlotProps> = ({
  item,
  count,
  selected = false,
  disabled = false,
  onClick,
  size = 36,
  tooltip,
  className = '',
  style = {},
}) => {
  const [hovered, setHovered] = React.useState(false);

  const slotStyles: React.CSSProperties = {
    position: 'relative',
    width: `${size}px`,
    height: `${size}px`,
    backgroundColor: disabled ? '#2A2A2A' : '#8B8B8B',
    border: selected 
      ? `2px solid ${minecraftColors.ui.border.selected}`
      : `1px solid ${minecraftColors.ui.border.slot}`,
    ...get3DBorder(false),
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'not-allowed' : onClick ? 'pointer' : 'default',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.1s',
    imageRendering: 'pixelated',
    ...style,
  };

  return (
    <>
      <div
        className={`mc-inventory-slot ${className}`}
        style={slotStyles}
        onClick={!disabled ? onClick : undefined}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* 物品内容 */}
        {item && (
          <div style={{ position: 'relative', width: '80%', height: '80%' }}>
            {item}
          </div>
        )}

        {/* 数量显示 */}
        {count && count > 1 && (
          <span
            style={{
              position: 'absolute',
              bottom: '0',
              right: '2px',
              color: minecraftColors.ui.text.secondary,
              fontSize: typography.fontSize.tiny,
              fontFamily: typography.fontFamily.minecraft,
              textShadow: '1px 1px 0px rgba(0, 0, 0, 0.75)',
            }}
          >
            {count > 99 ? '99+' : count}
          </span>
        )}

        {/* 选中高亮 */}
        {selected && (
          <div
            style={{
              position: 'absolute',
              inset: '-2px',
              border: `2px solid ${minecraftColors.ui.text.highlight}`,
              pointerEvents: 'none',
              animation: 'pulse 1s infinite',
            }}
          />
        )}
      </div>

      {/* 工具提示 */}
      {tooltip && hovered && (
        <div
          style={{
            position: 'absolute',
            zIndex: 1000,
            padding: '4px 8px',
            backgroundColor: minecraftColors.ui.background.tooltip,
            color: minecraftColors.ui.text.secondary,
            border: `1px solid ${minecraftColors.ui.border.dark}`,
            fontSize: typography.fontSize.tooltip,
            fontFamily: typography.fontFamily.minecraft,
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            transform: 'translate(-50%, -100%)',
            marginTop: '-8px',
          }}
        >
          {tooltip}
        </div>
      )}
    </>
  );
};

// 物品栏网格组件
export interface MCInventoryGridProps {
  rows: number;
  columns: number;
  items?: (React.ReactNode | null)[];
  selectedIndex?: number;
  onSlotClick?: (index: number) => void;
  slotSize?: number;
  gap?: number;
  className?: string;
  style?: React.CSSProperties;
}

export const MCInventoryGrid: React.FC<MCInventoryGridProps> = ({
  rows,
  columns,
  items = [],
  selectedIndex,
  onSlotClick,
  slotSize = 36,
  gap = 2,
  className = '',
  style = {},
}) => {
  const totalSlots = rows * columns;

  const gridStyles: React.CSSProperties = {
    display: 'grid',
    gridTemplateRows: `repeat(${rows}, ${slotSize}px)`,
    gridTemplateColumns: `repeat(${columns}, ${slotSize}px)`,
    gap: `${gap}px`,
    padding: '8px',
    backgroundColor: minecraftColors.ui.background.tertiary,
    ...get3DBorder(false),
    ...style,
  };

  return (
    <div className={`mc-inventory-grid ${className}`} style={gridStyles}>
      {Array.from({ length: totalSlots }).map((_, index) => (
        <MCInventorySlot
          key={index}
          item={items[index]}
          selected={selectedIndex === index}
          onClick={() => onSlotClick?.(index)}
          size={slotSize}
        />
      ))}
    </div>
  );
};

// 选项卡面板组件
export interface MCTabPanelProps {
  tabs: Array<{
    id: string;
    label: string;
    icon?: React.ReactNode;
    content: React.ReactNode;
  }>;
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
  variant?: 'stone' | 'planks';
  className?: string;
  style?: React.CSSProperties;
}

export const MCTabPanel: React.FC<MCTabPanelProps> = ({
  tabs,
  activeTab,
  onTabChange,
  variant = 'stone',
  className = '',
  style = {},
}) => {
  const [currentTab, setCurrentTab] = React.useState(activeTab || tabs[0]?.id);

  const handleTabChange = (tabId: string) => {
    setCurrentTab(tabId);
    onTabChange?.(tabId);
  };

  const activeTabContent = tabs.find(tab => tab.id === currentTab)?.content;

  return (
    <div className={`mc-tab-panel ${className}`} style={style}>
      {/* 选项卡头部 */}
      <div
        style={{
          display: 'flex',
          gap: '2px',
          marginBottom: '-2px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {tabs.map(tab => {
          const isActive = tab.id === currentTab;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              style={{
                padding: '8px 16px',
                backgroundColor: isActive 
                  ? minecraftColors.ui.background.primary 
                  : minecraftColors.ui.background.secondary,
                color: isActive 
                  ? minecraftColors.ui.text.secondary 
                  : minecraftColors.ui.text.disabled,
                border: 'none',
                ...get3DBorder(isActive),
                borderBottom: isActive ? 'none' : `2px solid ${minecraftColors.ui.border.dark}`,
                fontFamily: typography.fontFamily.minecraft,
                fontSize: typography.fontSize.normal,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s',
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* 选项卡内容 */}
      <MCPanel variant={variant} border={true} raised={true}>
        <motion.div
          key={currentTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {activeTabContent}
        </motion.div>
      </MCPanel>
    </div>
  );
};

export default MCPanel;