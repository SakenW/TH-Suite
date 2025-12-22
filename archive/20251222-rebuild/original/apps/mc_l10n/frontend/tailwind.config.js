/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    './src/**/*.{css,scss}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Minecraft 主题色彩
        mc: {
          // 主要色彩
          'emerald': '#4CAF50',
          'grass': '#8BC34A', 
          'gold': '#FFC107',
          'redstone': '#F44336',
          'lapis': '#2196F3',
          
          // 方块色彩
          'stone': '#7F7F7F',
          'cobblestone': '#6B6B6B',
          'wood': '#8B4513',
          'dirt': '#8B6914',
          'bedrock': '#2C2C2C',
          
          // 特殊材质
          'glass': 'rgba(255,255,255,0.2)',
          'obsidian': '#1A1A2E',
          'diamond': '#B3E5FC',
          'iron': '#D7D7D7',
          'netherrack': '#8B0000',
          
          // 生物群系
          'forest': '#7CB342',
          'desert': '#F4E7B7',
          'snow': '#F0F8FF',
          'ocean': '#1976D2',
        },
        // 渐变色停靠点
        gradient: {
          'start': '#4CAF50',
          'middle': '#8BC34A', 
          'end': '#2196F3',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        'pixel': '2px',  // 像素化圆角
        'block': '4px',  // 方块圆角
      },
      fontFamily: {
        minecraft: ['Minecraft', 'monospace'],
        mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', 'monospace'],
      },
      fontSize: {
        'pixel': ['12px', { lineHeight: '16px', fontWeight: '500' }],
        'block': ['14px', { lineHeight: '20px', fontWeight: '600' }],
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-subtle': 'bounce 2s infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'shimmer': 'shimmer 2s linear infinite',
        'exp-fill': 'exp-fill 1.5s ease-out',
        'block-drop': 'block-drop 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'pixel-fade': 'pixel-fade 0.3s ease-in-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(76, 175, 80, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(76, 175, 80, 0.8), 0 0 30px rgba(76, 175, 80, 0.6)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'exp-fill': {
          '0%': { width: '0%' },
          '100%': { width: 'var(--progress, 0%)' },
        },
        'block-drop': {
          '0%': { 
            transform: 'translateY(-20px) scale(0.8)',
            opacity: '0',
          },
          '100%': { 
            transform: 'translateY(0) scale(1)',
            opacity: '1',
          },
        },
        'pixel-fade': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      backdropBlur: {
        xs: '2px',
        'glass': '20px',
      },
      boxShadow: {
        'pixel': '2px 2px 0 rgba(0,0,0,0.3)',
        'block': '4px 4px 0 rgba(0,0,0,0.2), 8px 8px 0 rgba(0,0,0,0.1)',
        'glow-emerald': '0 0 20px rgba(76, 175, 80, 0.3)',
        'glow-gold': '0 0 20px rgba(255, 193, 7, 0.3)',
        'glow-redstone': '0 0 20px rgba(244, 67, 54, 0.3)',
        'glow-lapis': '0 0 20px rgba(33, 150, 243, 0.3)',
        'inner-pixel': 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.1)',
        'minecraft-card': '0 4px 16px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.1)',
        'depth': '0 8px 32px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.08)',
      },
      backgroundImage: {
        'grid-pattern': `
          linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px),
          linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px)
        `,
        'noise-pattern': 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' /%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\' opacity=\'0.05\'/%3E%3C/svg%3E")',
        'minecraft-gradient': 'linear-gradient(135deg, #4CAF50 0%, #8BC34A 50%, #2196F3 100%)',
        'shimmer-gradient': 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
      },
      backgroundSize: {
        'grid': '16px 16px',
        'noise': '256px 256px',
        'shimmer': '200% 100%',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
      screens: {
        '3xl': '1600px',
      },
    },
  },
  plugins: [
    // 自定义插件：Minecraft 装饰类
    function({ addUtilities, theme }) {
      const newUtilities = {
        '.pixel-perfect': {
          imageRendering: 'pixelated',
          imageRendering: '-moz-crisp-edges',
          imageRendering: 'crisp-edges',
        },
        '.text-pixel': {
          fontFamily: theme('fontFamily.minecraft'),
          textShadow: '1px 1px 0 rgba(0,0,0,0.3)',
        },
        '.bg-grid': {
          backgroundImage: theme('backgroundImage.grid-pattern'),
          backgroundSize: theme('backgroundSize.grid'),
        },
        '.bg-noise': {
          backgroundImage: theme('backgroundImage.noise-pattern'),
          backgroundSize: theme('backgroundSize.noise'),
        },
        '.glass-effect': {
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
        },
        '.block-shadow': {
          boxShadow: theme('boxShadow.block'),
        },
        '.pixel-shadow': {
          boxShadow: theme('boxShadow.pixel'),
        },
        '.minecraft-card': {
          background: 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.05) 100%)',
          border: '1px solid rgba(0,0,0,0.1)',
          boxShadow: theme('boxShadow.minecraft-card'),
        },
        '.exp-bar': {
          background: 'linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%)',
          border: '1px solid rgba(0,0,0,0.2)',
          boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.2)',
          height: '4px',
        },
        '.shimmer': {
          backgroundImage: theme('backgroundImage.shimmer-gradient'),
          backgroundSize: theme('backgroundSize.shimmer'),
          animation: theme('animation.shimmer'),
        },
      }
      addUtilities(newUtilities)
    },
  ],
  corePlugins: {
    preflight: true,
  },
}
