/**
 * Minecraft 字体和排版系统
 * 基于 Minecraft 的像素字体风格
 */

// 字体配置
export const typography = {
  // 字体族
  fontFamily: {
    // Minecraft 像素字体（需要引入对应字体文件）
    minecraft: '"Minecraft", "MinecraftRegular", monospace',
    // 系统等宽字体作为后备
    mono: '"Courier New", Courier, monospace',
    // UI 字体
    ui: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    // 像素风格字体
    pixel: '"Press Start 2P", "Minecraft", monospace',
  },

  // 字体大小（像素值）
  fontSize: {
    // 基础大小
    tiny: '8px',
    small: '10px',
    normal: '12px',
    medium: '14px',
    large: '16px',
    xlarge: '20px',
    xxlarge: '24px',
    huge: '32px',

    // UI 特定大小
    button: '14px',
    tooltip: '10px',
    title: '20px',
    subtitle: '16px',
    label: '12px',
    caption: '10px',

    // 游戏内文字大小
    chat: '12px',
    scoreboard: '10px',
    nameplate: '8px',
    sign: '14px',
  },

  // 字重
  fontWeight: {
    normal: 400,
    bold: 700,
    // Minecraft 字体通常不支持多种字重
  },

  // 行高
  lineHeight: {
    tight: 1.0,
    normal: 1.2,
    relaxed: 1.4,
    loose: 1.6,
  },

  // 字间距
  letterSpacing: {
    tight: '-0.5px',
    normal: '0px',
    wide: '0.5px',
    wider: '1px',
    widest: '2px',
    pixel: '1px', // 像素字体推荐间距
  },

  // 文字阴影（Minecraft 风格）
  textShadow: {
    // 标准 MC 文字阴影
    normal: '2px 2px 0px rgba(0, 0, 0, 0.5)',
    // 深色阴影
    dark: '2px 2px 0px rgba(0, 0, 0, 0.75)',
    // 轻阴影
    light: '1px 1px 0px rgba(0, 0, 0, 0.25)',
    // 发光效果
    glow: '0 0 5px rgba(255, 255, 255, 0.5)',
    // 附魔效果
    enchanted: '0 0 5px #9C6BFF, 2px 2px 0px rgba(0, 0, 0, 0.5)',
    // 无阴影
    none: 'none',
  },

  // 文字变换
  textTransform: {
    none: 'none',
    uppercase: 'uppercase',
    lowercase: 'lowercase',
    capitalize: 'capitalize',
  },
}

// 文字样式预设
export const textStyles = {
  // 标题样式
  title: {
    fontSize: typography.fontSize.title,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.bold,
    letterSpacing: typography.letterSpacing.wide,
    textShadow: typography.textShadow.normal,
    color: '#FFFFFF',
  },

  // 副标题样式
  subtitle: {
    fontSize: typography.fontSize.subtitle,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.normal,
    textShadow: typography.textShadow.normal,
    color: '#AAAAAA',
  },

  // 正文样式
  body: {
    fontSize: typography.fontSize.normal,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    lineHeight: typography.lineHeight.normal,
    letterSpacing: typography.letterSpacing.pixel,
    textShadow: typography.textShadow.light,
    color: '#404040',
  },

  // 按钮文字
  button: {
    fontSize: typography.fontSize.button,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.wide,
    textShadow: typography.textShadow.dark,
    textTransform: typography.textTransform.none,
    color: '#FFFFFF',
  },

  // 工具提示文字
  tooltip: {
    fontSize: typography.fontSize.tooltip,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    lineHeight: typography.lineHeight.tight,
    letterSpacing: typography.letterSpacing.normal,
    textShadow: 'none',
    color: '#FFFFFF',
  },

  // 标签文字
  label: {
    fontSize: typography.fontSize.label,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.pixel,
    textShadow: typography.textShadow.light,
    color: '#707070',
  },

  // 错误文字
  error: {
    fontSize: typography.fontSize.normal,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.normal,
    textShadow: typography.textShadow.normal,
    color: '#FF5555',
  },

  // 成功文字
  success: {
    fontSize: typography.fontSize.normal,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.normal,
    textShadow: typography.textShadow.normal,
    color: '#55FF55',
  },

  // 警告文字
  warning: {
    fontSize: typography.fontSize.normal,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.normal,
    textShadow: typography.textShadow.normal,
    color: '#FFAA00',
  },

  // 聊天文字
  chat: {
    fontSize: typography.fontSize.chat,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    lineHeight: typography.lineHeight.relaxed,
    letterSpacing: typography.letterSpacing.pixel,
    textShadow: typography.textShadow.normal,
    color: '#FFFFFF',
  },

  // 记分板文字
  scoreboard: {
    fontSize: typography.fontSize.scoreboard,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.wide,
    textShadow: typography.textShadow.dark,
    color: '#FFFFFF',
  },

  // 附魔文字
  enchanted: {
    fontSize: typography.fontSize.normal,
    fontFamily: typography.fontFamily.minecraft,
    fontWeight: typography.fontWeight.normal,
    letterSpacing: typography.letterSpacing.wider,
    textShadow: typography.textShadow.enchanted,
    color: '#9C6BFF',
    animation: 'enchantedGlow 2s ease-in-out infinite',
  },
}

// 创建文字渐变效果
export function createTextGradient(colors: string[]): {
  background: string
  WebkitBackgroundClip: string
  WebkitTextFillColor: string
  backgroundClip: string
} {
  return {
    background: `linear-gradient(90deg, ${colors.join(', ')})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
  }
}

// 创建像素化文字效果
export function createPixelText(size = 12): {
  fontSize: string
  fontFamily: string
  imageRendering: string
  textRendering: string
  WebkitFontSmoothing: string
} {
  return {
    fontSize: `${size}px`,
    fontFamily: typography.fontFamily.pixel,
    imageRendering: 'pixelated',
    textRendering: 'optimizeSpeed',
    WebkitFontSmoothing: 'none',
  }
}

// 创建打字机效果
export function createTypewriterEffect(
  text: string,
  speed = 100,
): {
  animation: string
  overflow: string
  whiteSpace: string
  borderRight: string
} {
  const steps = text.length
  return {
    animation: `typing ${steps * speed}ms steps(${steps}) forwards, blink 1s step-end infinite`,
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    borderRight: '2px solid #FFFFFF',
  }
}

// 创建闪烁文字效果
export function createBlinkingText(interval = 500): {
  animation: string
} {
  return {
    animation: `blink ${interval}ms step-end infinite`,
  }
}

// 创建随机字符效果（Matrix / Enchantment Table 风格）
export class ObfuscatedText {
  private element: HTMLElement
  private originalText: string
  private intervalId?: number
  private chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()'

  constructor(element: HTMLElement) {
    this.element = element
    this.originalText = element.textContent || ''
  }

  start(speed = 50): void {
    this.intervalId = window.setInterval(() => {
      let obfuscated = ''
      for (let i = 0; i < this.originalText.length; i++) {
        if (this.originalText[i] === ' ') {
          obfuscated += ' '
        } else {
          obfuscated += this.chars[Math.floor(Math.random() * this.chars.length)]
        }
      }
      this.element.textContent = obfuscated
    }, speed)
  }

  stop(): void {
    if (this.intervalId) {
      window.clearInterval(this.intervalId)
      this.element.textContent = this.originalText
    }
  }

  reveal(duration = 1000): void {
    const steps = this.originalText.length
    const stepDuration = duration / steps
    let currentStep = 0

    const revealStep = () => {
      if (currentStep <= steps) {
        const revealed = this.originalText.slice(0, currentStep)
        const obfuscated = this.originalText
          .slice(currentStep)
          .split('')
          .map(char =>
            char === ' ' ? ' ' : this.chars[Math.floor(Math.random() * this.chars.length)],
          )
          .join('')
        this.element.textContent = revealed + obfuscated
        currentStep++
        window.setTimeout(revealStep, stepDuration)
      }
    }

    revealStep()
  }
}

// CSS 动画关键帧（需要在全局 CSS 中定义）
export const textAnimations = `
  @keyframes enchantedGlow {
    0%, 100% {
      text-shadow: 0 0 5px #9C6BFF, 2px 2px 0px rgba(0, 0, 0, 0.5);
    }
    50% {
      text-shadow: 0 0 10px #9C6BFF, 0 0 20px #9C6BFF, 2px 2px 0px rgba(0, 0, 0, 0.5);
    }
  }

  @keyframes typing {
    from { width: 0; }
    to { width: 100%; }
  }

  @keyframes blink {
    50% { opacity: 0; }
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-2px); }
    75% { transform: translateX(2px); }
  }

  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }

  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
  }
`

export default typography
