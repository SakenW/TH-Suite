/**
 * i18n 配置文件
 * 管理多语言系统的初始化和配置
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

// 导入通用语言包
import commonEn from '@th-suite/localization/common/en.json';
import commonZhCN from '@th-suite/localization/common/zh-CN.json';

// 导入 Minecraft 专属语言包
import minecraftEn from '../locales/minecraft/en.json';
import minecraftZhCN from '../locales/minecraft/zh-CN.json';

// 导入应用专属语言包
import mcStudioEn from '../locales/en/mc-studio.json';
import mcStudioZhCN from '../locales/zh-CN/mc-studio.json';

// 支持的语言列表
export const supportedLanguages = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'zh-CN', name: '简体中文', flag: '🇨🇳' },
  { code: 'zh-TW', name: '繁體中文', flag: '🇹🇼' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
  { code: 'ko', name: '한국어', flag: '🇰🇷' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pt-BR', name: 'Português (Brasil)', flag: '🇧🇷' },
] as const;

export type SupportedLanguage = typeof supportedLanguages[number]['code'];

// 默认语言
export const defaultLanguage: SupportedLanguage = 'zh-CN';

// 语言包资源
const resources = {
  en: {
    common: commonEn,
    minecraft: minecraftEn,
    mcStudio: mcStudioEn,
  },
  'zh-CN': {
    common: commonZhCN,
    minecraft: minecraftZhCN,
    mcStudio: mcStudioZhCN,
  },
};

// i18n 配置选项
const i18nConfig = {
  resources,
  fallbackLng: defaultLanguage,
  debug: process.env.NODE_ENV === 'development',
  
  detection: {
    order: ['localStorage', 'navigator', 'htmlTag'],
    caches: ['localStorage'],
    lookupLocalStorage: 'th-suite-language',
  },

  interpolation: {
    escapeValue: false, // React 已经处理了 XSS
  },

  ns: ['common', 'minecraft', 'mcStudio'],
  defaultNS: 'mcStudio',

  react: {
    useSuspense: false,
    bindI18n: 'languageChanged loaded',
    bindI18nStore: 'added removed',
    transEmptyNodeValue: '',
    transSupportBasicHtmlNodes: true,
    transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'p'],
  },
};

// 初始化 i18n
export const initI18n = () => {
  i18n
    .use(Backend)
    .use(LanguageDetector)
    .use(initReactI18next)
    .init(i18nConfig);

  return i18n;
};

// 语言管理器
export class LanguageManager {
  private static instance: LanguageManager;
  private currentLanguage: SupportedLanguage;
  private listeners: Set<(lang: SupportedLanguage) => void> = new Set();

  private constructor() {
    this.currentLanguage = this.getStoredLanguage() || defaultLanguage;
  }

  static getInstance(): LanguageManager {
    if (!LanguageManager.instance) {
      LanguageManager.instance = new LanguageManager();
    }
    return LanguageManager.instance;
  }

  // 获取当前语言
  getCurrentLanguage(): SupportedLanguage {
    return this.currentLanguage;
  }

  // 设置语言
  async setLanguage(language: SupportedLanguage): Promise<void> {
    if (this.currentLanguage === language) return;

    try {
      await i18n.changeLanguage(language);
      this.currentLanguage = language;
      this.storeLanguage(language);
      this.notifyListeners(language);
    } catch (error) {
      console.error('Failed to change language:', error);
      throw error;
    }
  }

  // 获取语言信息
  getLanguageInfo(code: SupportedLanguage) {
    return supportedLanguages.find(lang => lang.code === code);
  }

  // 获取所有支持的语言
  getSupportedLanguages() {
    return supportedLanguages;
  }

  // 添加语言变更监听器
  addListener(callback: (lang: SupportedLanguage) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  // 获取存储的语言
  private getStoredLanguage(): SupportedLanguage | null {
    const stored = localStorage.getItem('th-suite-language');
    if (stored && this.isValidLanguage(stored)) {
      return stored as SupportedLanguage;
    }
    return null;
  }

  // 存储语言设置
  private storeLanguage(language: SupportedLanguage): void {
    localStorage.setItem('th-suite-language', language);
  }

  // 验证语言代码
  private isValidLanguage(code: string): boolean {
    return supportedLanguages.some(lang => lang.code === code);
  }

  // 通知监听器
  private notifyListeners(language: SupportedLanguage): void {
    this.listeners.forEach(callback => callback(language));
  }

  // 获取浏览器语言
  getBrowserLanguage(): SupportedLanguage {
    const browserLang = navigator.language;
    
    // 精确匹配
    if (this.isValidLanguage(browserLang)) {
      return browserLang as SupportedLanguage;
    }
    
    // 语言代码匹配（忽略地区）
    const langCode = browserLang.split('-')[0];
    const matched = supportedLanguages.find(lang => 
      lang.code.startsWith(langCode)
    );
    
    return matched?.code || defaultLanguage;
  }

  // 格式化日期
  formatDate(date: Date, options?: Intl.DateTimeFormatOptions): string {
    return new Intl.DateTimeFormat(this.currentLanguage, options).format(date);
  }

  // 格式化数字
  formatNumber(number: number, options?: Intl.NumberFormatOptions): string {
    return new Intl.NumberFormat(this.currentLanguage, options).format(number);
  }

  // 格式化货币
  formatCurrency(amount: number, currency = 'USD'): string {
    return new Intl.NumberFormat(this.currentLanguage, {
      style: 'currency',
      currency,
    }).format(amount);
  }

  // 格式化相对时间
  formatRelativeTime(date: Date): string {
    const rtf = new Intl.RelativeTimeFormat(this.currentLanguage, {
      numeric: 'auto',
    });
    
    const diff = date.getTime() - Date.now();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (Math.abs(days) >= 1) {
      return rtf.format(days, 'day');
    } else if (Math.abs(hours) >= 1) {
      return rtf.format(hours, 'hour');
    } else if (Math.abs(minutes) >= 1) {
      return rtf.format(minutes, 'minute');
    } else {
      return rtf.format(seconds, 'second');
    }
  }

  // 获取文字方向（LTR/RTL）
  getTextDirection(): 'ltr' | 'rtl' {
    // 阿拉伯语、希伯来语等从右到左的语言
    const rtlLanguages = ['ar', 'he', 'fa', 'ur'];
    const langCode = this.currentLanguage.split('-')[0];
    return rtlLanguages.includes(langCode) ? 'rtl' : 'ltr';
  }
}

// 导出单例实例
export const languageManager = LanguageManager.getInstance();

// 导出 i18n 实例
export default i18n;