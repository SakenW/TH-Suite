/**
 * Minecraft 纹理和图案系统
 * 提供各种 Minecraft 风格的背景纹理
 */

// 基础纹理 URL（使用 CSS 模式或 SVG）
export const textures = {
  // 石头纹理（使用 CSS 渐变模拟）
  stone: `
    repeating-linear-gradient(
      0deg,
      #8B8B8B 0px,
      #9A9A9A 2px,
      #8B8B8B 4px,
      #7C7C7C 6px,
      #8B8B8B 8px
    ),
    repeating-linear-gradient(
      90deg,
      #8B8B8B 0px,
      #9A9A9A 2px,
      #8B8B8B 4px,
      #7C7C7C 6px,
      #8B8B8B 8px
    )
  `,

  // 泥土纹理
  dirt: `
    repeating-linear-gradient(
      45deg,
      #8B6F47 0px,
      #9B7F57 2px,
      #8B6F47 4px,
      #7B5F37 6px
    )
  `,

  // 木板纹理
  planks: `
    repeating-linear-gradient(
      90deg,
      #9C7F4E 0px,
      #8B6F3D 4px,
      #9C7F4E 8px,
      #A58F5E 12px,
      #9C7F4E 16px
    )
  `,

  // 圆石纹理
  cobblestone: `
    radial-gradient(circle at 25% 25%, #7C7C7C 0%, transparent 2%),
    radial-gradient(circle at 75% 75%, #6C6C6C 0%, transparent 2%),
    radial-gradient(circle at 50% 50%, #8C8C8C 0%, transparent 3%),
    linear-gradient(0deg, #8B8B8B 0%, #7C7C7C 100%)
  `,

  // 玻璃纹理（半透明）
  glass: `
    linear-gradient(45deg, 
      rgba(255, 255, 255, 0.1) 25%, 
      transparent 25%, 
      transparent 75%, 
      rgba(255, 255, 255, 0.1) 75%
    ),
    linear-gradient(-45deg, 
      rgba(255, 255, 255, 0.1) 25%, 
      transparent 25%, 
      transparent 75%, 
      rgba(255, 255, 255, 0.1) 75%
    )
  `,

  // 格子纹理（物品栏背景）
  inventory: `
    linear-gradient(90deg, #8B8B8B 0%, #8B8B8B 2px, transparent 2px, transparent 18px),
    linear-gradient(0deg, #8B8B8B 0%, #8B8B8B 2px, transparent 2px, transparent 18px)
  `,
};

// SVG 纹理生成器
export function generateSVGTexture(type: 'dots' | 'grid' | 'noise', color = '#8B8B8B'): string {
  const svgPatterns = {
    dots: `
      <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="10" cy="10" r="2" fill="${color}" opacity="0.3"/>
          </pattern>
        </defs>
        <rect width="20" height="20" fill="url(#dots)"/>
      </svg>
    `,
    grid: `
      <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="${color}" stroke-width="1" opacity="0.2"/>
          </pattern>
        </defs>
        <rect width="20" height="20" fill="url(#grid)"/>
      </svg>
    `,
    noise: `
      <svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
        <filter id="noise">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4"/>
          <feColorMatrix type="saturate" values="0"/>
        </filter>
        <rect width="100" height="100" filter="url(#noise)" opacity="0.1"/>
      </svg>
    `,
  };

  const svg = svgPatterns[type];
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

// 创建像素化背景
export function createPixelatedBackground(
  baseColor: string,
  pixelSize = 4,
  variation = 0.1
): string {
  const generatePixelGrid = () => {
    const pixels = [];
    for (let i = 0; i < 10; i++) {
      for (let j = 0; j < 10; j++) {
        const opacity = 1 - Math.random() * variation;
        pixels.push(
          `radial-gradient(circle at ${i * 10 + 5}% ${j * 10 + 5}%, 
           ${baseColor}${Math.floor(opacity * 255).toString(16)} 0%, 
           transparent ${pixelSize}%)`
        );
      }
    }
    return pixels.join(',');
  };

  return generatePixelGrid();
}

// 创建 Minecraft 式边框纹理
export function createBorderTexture(raised = true): {
  backgroundImage: string;
  backgroundSize: string;
  backgroundPosition: string;
} {
  const lightColor = raised ? '#FFFFFF' : '#373737';
  const darkColor = raised ? '#373737' : '#FFFFFF';

  return {
    backgroundImage: `
      linear-gradient(to right, ${lightColor} 0%, ${lightColor} 2px, transparent 2px),
      linear-gradient(to bottom, ${lightColor} 0%, ${lightColor} 2px, transparent 2px),
      linear-gradient(to left, ${darkColor} 0%, ${darkColor} 2px, transparent 2px),
      linear-gradient(to top, ${darkColor} 0%, ${darkColor} 2px, transparent 2px)
    `,
    backgroundSize: '100% 100%, 100% 100%, 100% 100%, 100% 100%',
    backgroundPosition: 'left, top, right, bottom',
  };
}

// 创建物品栏格子
export function createInventorySlot(size = 36): {
  width: string;
  height: string;
  backgroundImage: string;
  backgroundSize: string;
} {
  return {
    width: `${size}px`,
    height: `${size}px`,
    backgroundImage: textures.inventory,
    backgroundSize: '18px 18px',
  };
}

// 生成附魔闪光效果
export function createEnchantmentGlint(): string {
  return `
    linear-gradient(
      135deg,
      transparent 0%,
      rgba(156, 107, 255, 0.3) 20%,
      rgba(156, 107, 255, 0.5) 40%,
      rgba(156, 107, 255, 0.3) 60%,
      transparent 100%
    )
  `;
}

// 创建经验条纹理
export function createExperienceBar(progress: number): {
  background: string;
  backgroundSize: string;
} {
  return {
    background: `
      linear-gradient(90deg, 
        #80FF20 0%, 
        #80FF20 ${progress}%, 
        #2A2A2A ${progress}%, 
        #2A2A2A 100%
      ),
      ${textures.stone}
    `,
    backgroundSize: `100% 100%, 8px 8px`,
  };
}

// 创建生命值条纹理
export function createHealthBar(health: number, maxHealth: number): {
  background: string;
} {
  const percentage = (health / maxHealth) * 100;
  return {
    background: `
      linear-gradient(90deg,
        #FF0000 0%,
        #FF0000 ${percentage}%,
        #3C0000 ${percentage}%,
        #3C0000 100%
      )
    `,
  };
}

// 创建护甲条纹理
export function createArmorBar(armor: number, maxArmor = 20): {
  background: string;
} {
  const percentage = (armor / maxArmor) * 100;
  return {
    background: `
      linear-gradient(90deg,
        #A0A0A0 0%,
        #A0A0A0 ${percentage}%,
        #3C3C3C ${percentage}%,
        #3C3C3C 100%
      )
    `,
  };
}

// 动画纹理类
export class AnimatedTexture {
  private frames: string[];
  private currentFrame: number;
  private interval: number;
  private animationId?: number;

  constructor(frames: string[], interval = 100) {
    this.frames = frames;
    this.currentFrame = 0;
    this.interval = interval;
  }

  start(callback: (frame: string) => void): void {
    const animate = () => {
      callback(this.frames[this.currentFrame]);
      this.currentFrame = (this.currentFrame + 1) % this.frames.length;
      this.animationId = window.setTimeout(animate, this.interval);
    };
    animate();
  }

  stop(): void {
    if (this.animationId) {
      window.clearTimeout(this.animationId);
    }
  }
}

// 创建传送门效果
export function createPortalEffect(): AnimatedTexture {
  const frames = [];
  for (let i = 0; i < 8; i++) {
    frames.push(`
      radial-gradient(
        ellipse at center,
        rgba(128, 0, 128, ${0.5 + Math.sin(i * Math.PI / 4) * 0.3}) 0%,
        rgba(75, 0, 130, ${0.3 + Math.sin(i * Math.PI / 4) * 0.2}) 50%,
        transparent 100%
      )
    `);
  }
  return new AnimatedTexture(frames, 125);
}

export default textures;