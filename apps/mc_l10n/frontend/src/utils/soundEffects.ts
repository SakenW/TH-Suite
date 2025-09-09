/**
 * 音效播放工具
 * 提供简单的音效播放功能
 */

// 音效类型定义
export type SoundEffect = 'explosion' | 'click' | 'success' | 'error' | 'notification'

// 音效配置
interface SoundConfig {
  frequency: number
  duration: number
  volume: number
  type: OscillatorType
}

// 预定义音效配置
const SOUND_CONFIGS: Record<SoundEffect, SoundConfig[]> = {
  explosion: [
    // 爆炸音效 - 多层次的低频爆炸声
    { frequency: 60, duration: 0.1, volume: 0.8, type: 'sawtooth' },
    { frequency: 120, duration: 0.15, volume: 0.6, type: 'square' },
    { frequency: 200, duration: 0.2, volume: 0.4, type: 'triangle' },
    { frequency: 80, duration: 0.3, volume: 0.3, type: 'sine' },
  ],
  click: [{ frequency: 800, duration: 0.1, volume: 0.3, type: 'square' }],
  success: [
    { frequency: 523, duration: 0.2, volume: 0.4, type: 'sine' },
    { frequency: 659, duration: 0.2, volume: 0.3, type: 'sine' },
    { frequency: 784, duration: 0.3, volume: 0.2, type: 'sine' },
  ],
  error: [{ frequency: 200, duration: 0.3, volume: 0.5, type: 'sawtooth' }],
  notification: [{ frequency: 440, duration: 0.2, volume: 0.3, type: 'sine' }],
}

/**
 * 播放单个音调
 */
function playTone(config: SoundConfig, delay: number = 0): Promise<void> {
  return new Promise(resolve => {
    setTimeout(() => {
      try {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
        const oscillator = audioContext.createOscillator()
        const gainNode = audioContext.createGain()

        oscillator.connect(gainNode)
        gainNode.connect(audioContext.destination)

        oscillator.frequency.setValueAtTime(config.frequency, audioContext.currentTime)
        oscillator.type = config.type

        // 音量包络 - 快速攻击，慢速衰减
        gainNode.gain.setValueAtTime(0, audioContext.currentTime)
        gainNode.gain.linearRampToValueAtTime(config.volume, audioContext.currentTime + 0.01)
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + config.duration)

        oscillator.start(audioContext.currentTime)
        oscillator.stop(audioContext.currentTime + config.duration)

        oscillator.onended = () => {
          audioContext.close()
          resolve()
        }
      } catch (error) {
        console.warn('音效播放失败:', error)
        resolve()
      }
    }, delay * 1000)
  })
}

/**
 * 播放音效
 * @param effect 音效类型
 * @param volume 音量倍数 (0-1)
 */
export async function playSound(effect: SoundEffect, volume: number = 1): Promise<void> {
  const configs = SOUND_CONFIGS[effect]
  if (!configs) {
    console.warn(`未知的音效类型: ${effect}`)
    return
  }

  // 检查用户是否允许音频播放
  try {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    if (audioContext.state === 'suspended') {
      await audioContext.resume()
    }
    audioContext.close()
  } catch (error) {
    console.warn('音频上下文初始化失败:', error)
    return
  }

  // 播放所有音调（并行播放以创建复合音效）
  const promises = configs.map((config, index) => {
    const adjustedConfig = {
      ...config,
      volume: config.volume * volume,
    }
    return playTone(adjustedConfig, index * 0.02) // 轻微的延迟以增加层次感
  })

  await Promise.all(promises)
}

/**
 * 播放爆炸音效（专门为苦力怕设计）
 */
export function playExplosionSound(): Promise<void> {
  return playSound('explosion', 0.7)
}

/**
 * 播放点击音效
 */
export function playClickSound(): Promise<void> {
  return playSound('click', 0.5)
}

/**
 * 播放成功音效
 */
export function playSuccessSound(): Promise<void> {
  return playSound('success', 0.6)
}

/**
 * 播放错误音效
 */
export function playErrorSound(): Promise<void> {
  return playSound('error', 0.6)
}

/**
 * 播放通知音效
 */
export function playNotificationSound(): Promise<void> {
  return playSound('notification', 0.5)
}

// 导出默认音效播放器
export default {
  playSound,
  playExplosionSound,
  playClickSound,
  playSuccessSound,
  playErrorSound,
  playNotificationSound,
}
