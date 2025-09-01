/**
 * Minecraft 风格色彩系统
 * 基于 Minecraft 游戏内 UI 的经典配色
 */

export const minecraftColors = {
  // 基础色
  primary: {
    grass: '#5EBA3A',           // 草方块绿
    dirt: '#8B6F47',            // 泥土棕
    stone: '#8B8B8B',           // 石头灰
    water: '#3F76E4',           // 水蓝
    lava: '#D5632C',            // 岩浆橙
    diamond: '#5ECFCF',         // 钻石青
    emerald: '#17DD62',         // 绿宝石绿
    gold: '#FDD835',            // 金色
    iron: '#D8D8D8',            // 铁灰
    redstone: '#AA0000',        // 红石红
    netherite: '#4D494D',       // 下界合金黑
    endstone: '#F9F3A9',        // 末地石黄
  },

  // UI 颜色
  ui: {
    // 背景色
    background: {
      primary: '#C6C6C6',       // 主背景（石头材质色）
      secondary: '#8B8B8B',     // 次背景（深石头色）
      tertiary: '#373737',      // 第三背景（暗色）
      overlay: 'rgba(0, 0, 0, 0.75)', // 覆盖层
      tooltip: '#100010',       // 工具提示背景（紫黑色）
    },
    
    // 边框色
    border: {
      light: '#FFFFFF',         // 亮边框（顶部/左侧）
      dark: '#373737',          // 暗边框（底部/右侧）
      slot: '#8B8B8B',          // 物品栏边框
      selected: '#FFFFFF',       // 选中边框
    },
    
    // 文字色
    text: {
      primary: '#404040',       // 主文字（深灰）
      secondary: '#FFFFFF',     // 次文字（白色）
      disabled: '#A0A0A0',      // 禁用文字
      highlight: '#FFFF00',     // 高亮文字（黄色）
      shadow: '#3F3F3F',        // 文字阴影
      enchanted: '#9C6BFF',     // 附魔紫
    },
    
    // 按钮色
    button: {
      default: '#7D7D7D',       // 默认按钮
      hover: '#9D9D9D',         // 悬停按钮
      active: '#5D5D5D',        // 激活按钮
      disabled: '#4D4D4D',      // 禁用按钮
      success: '#5EBA3A',       // 成功按钮（草绿）
      danger: '#C84C44',        // 危险按钮（TNT红）
    },
    
    // 进度条色
    progress: {
      empty: '#8B8B8B',         // 空进度条
      fill: '#5EBA3A',          // 填充进度条（经验绿）
      experience: '#80FF20',    // 经验条绿
      health: '#FF0000',        // 生命值红
      hunger: '#D99420',        // 饥饿值棕
      armor: '#A0A0A0',         // 护甲灰
    },
  },

  // 稀有度颜色（基于 Minecraft 物品稀有度）
  rarity: {
    common: '#FFFFFF',          // 普通（白色）
    uncommon: '#FFFF55',        // 罕见（黄色）
    rare: '#55FFFF',            // 稀有（青色）
    epic: '#FF55FF',            // 史诗（紫色）
    legendary: '#FF5555',       // 传奇（红色）
    mythic: '#55FF55',          // 神话（绿色）
  },

  // 状态颜色
  status: {
    online: '#5EBA3A',          // 在线（绿）
    offline: '#AA0000',         // 离线（红）
    idle: '#FFAA00',            // 空闲（黄）
    busy: '#FF5555',            // 忙碌（亮红）
    away: '#AAAAAA',            // 离开（灰）
  },

  // 聊天颜色代码（Minecraft 格式化代码）
  formatting: {
    '§0': '#000000',            // 黑色
    '§1': '#0000AA',            // 深蓝
    '§2': '#00AA00',            // 深绿
    '§3': '#00AAAA',            // 深青
    '§4': '#AA0000',            // 深红
    '§5': '#AA00AA',            // 深紫
    '§6': '#FFAA00',            // 金色
    '§7': '#AAAAAA',            // 灰色
    '§8': '#555555',            // 深灰
    '§9': '#5555FF',            // 蓝色
    '§a': '#55FF55',            // 绿色
    '§b': '#55FFFF',            // 青色
    '§c': '#FF5555',            // 红色
    '§d': '#FF55FF',            // 粉色
    '§e': '#FFFF55',            // 黄色
    '§f': '#FFFFFF',            // 白色
  },

  // 生物群系颜色
  biome: {
    plains: '#8DB360',          // 平原
    desert: '#FA9418',          // 沙漠
    forest: '#056621',          // 森林
    taiga: '#0B6659',           // 针叶林
    swamp: '#07F9B2',           // 沼泽
    ocean: '#000080',           // 海洋
    snow: '#FFFFFF',            // 雪地
    nether: '#700000',          // 下界
    end: '#4A374A',             // 末地
  },

  // 半透明遮罩
  overlay: {
    light: 'rgba(255, 255, 255, 0.1)',
    medium: 'rgba(0, 0, 0, 0.5)',
    heavy: 'rgba(0, 0, 0, 0.75)',
    full: 'rgba(0, 0, 0, 0.9)',
  },
} as const;

// 获取 Minecraft 格式化颜色
export function getFormattingColor(code: string): string {
  return minecraftColors.formatting[code as keyof typeof minecraftColors.formatting] || '#FFFFFF';
}

// 获取稀有度颜色
export function getRarityColor(rarity: keyof typeof minecraftColors.rarity): string {
  return minecraftColors.rarity[rarity];
}

// 获取渐变色（用于进度条等）
export function getGradient(from: string, to: string): string {
  return `linear-gradient(90deg, ${from} 0%, ${to} 100%)`;
}

// 像素化阴影效果
export function getPixelShadow(color = '#000000'): string {
  return `2px 2px 0px ${color}`;
}

// 获取 3D 边框效果（Minecraft UI 风格）
export function get3DBorder(raised = true): {
  borderTop: string;
  borderLeft: string;
  borderBottom: string;
  borderRight: string;
} {
  if (raised) {
    return {
      borderTop: `2px solid ${minecraftColors.ui.border.light}`,
      borderLeft: `2px solid ${minecraftColors.ui.border.light}`,
      borderBottom: `2px solid ${minecraftColors.ui.border.dark}`,
      borderRight: `2px solid ${minecraftColors.ui.border.dark}`,
    };
  } else {
    return {
      borderTop: `2px solid ${minecraftColors.ui.border.dark}`,
      borderLeft: `2px solid ${minecraftColors.ui.border.dark}`,
      borderBottom: `2px solid ${minecraftColors.ui.border.light}`,
      borderRight: `2px solid ${minecraftColors.ui.border.light}`,
    };
  }
}

export default minecraftColors;