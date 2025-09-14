/**
 * 全局类型定义文件
 * 用于解决TypeScript类型检查问题
 */

// Tauri API 全局类型定义
declare global {
  interface Window {
    __TAURI__?: {
      tauri: {
        invoke: (cmd: string, args?: Record<string, any>) => Promise<any>
        convertFileSrc: (filePath: string, protocol?: string) => string
      }
      dialog: {
        open: (options?: any) => Promise<string | string[] | null>
        save: (options?: any) => Promise<string | null>
        message: (message: string, options?: any) => Promise<void>
        ask: (message: string, options?: any) => Promise<boolean>
        confirm: (message: string, options?: any) => Promise<boolean>
      }
      fs: {
        readTextFile: (path: string) => Promise<string>
        writeTextFile: (path: string, content: string) => Promise<void>
        exists: (path: string) => Promise<boolean>
        createDir: (path: string, options?: any) => Promise<void>
      }
      path: {
        join: (...paths: string[]) => Promise<string>
        dirname: (path: string) => Promise<string>
        basename: (path: string) => Promise<string>
        extname: (path: string) => Promise<string>
      }
      os: {
        platform: () => Promise<string>
        arch: () => Promise<string>
        version: () => Promise<string>
      }
    }
  }

  // NodeJS 命名空间（用于某些工具类型）
  namespace NodeJS {
    interface Timeout {
      ref(): this
      unref(): this
    }
  }
}

// Tauri Command 类构造器类型
declare class Command<T = any> {
  constructor(command: string, payload?: Record<string, any>)
  execute(): Promise<T>
}

// 导出空对象确保此文件被识别为模块
export {}