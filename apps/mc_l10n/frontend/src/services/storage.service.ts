/**
 * 数据持久化服务
 * 提供本地存储、会话存储和 IndexedDB 支持
 */

// Check if we're in a Tauri environment
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__

export interface StorageOptions {
  encrypt?: boolean
  compress?: boolean
  ttl?: number // Time to live in milliseconds
}

export interface StorageItem<T = any> {
  data: T
  timestamp: number
  ttl?: number
}

/**
 * 本地存储管理器
 */
class LocalStorageManager {
  private prefix = 'th_suite_'

  /**
   * 保存数据到本地存储
   */
  set(key: string, value: any, options?: StorageOptions): void {
    const fullKey = this.prefix + key
    const item: StorageItem = {
      data: value,
      timestamp: Date.now(),
      ttl: options?.ttl,
    }

    try {
      const serialized = JSON.stringify(item)
      localStorage.setItem(fullKey, serialized)
    } catch (error) {
      console.error('Failed to save to localStorage:', error)
      throw error
    }
  }

  /**
   * 从本地存储获取数据
   */
  get<T>(key: string): T | null {
    const fullKey = this.prefix + key

    try {
      const serialized = localStorage.getItem(fullKey)
      if (!serialized) return null

      const item: StorageItem<T> = JSON.parse(serialized)

      // Check TTL
      if (item.ttl) {
        const age = Date.now() - item.timestamp
        if (age > item.ttl) {
          this.remove(key)
          return null
        }
      }

      return item.data
    } catch (error) {
      console.error('Failed to get from localStorage:', error)
      return null
    }
  }

  /**
   * 删除本地存储数据
   */
  remove(key: string): void {
    const fullKey = this.prefix + key
    localStorage.removeItem(fullKey)
  }

  /**
   * 清空所有本地存储数据
   */
  clear(): void {
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        localStorage.removeItem(key)
      }
    })
  }

  /**
   * 获取所有键
   */
  keys(): string[] {
    const keys = Object.keys(localStorage)
    return keys
      .filter(key => key.startsWith(this.prefix))
      .map(key => key.substring(this.prefix.length))
  }
}

/**
 * 会话存储管理器
 */
class SessionStorageManager {
  private prefix = 'th_suite_session_'

  set(key: string, value: any): void {
    const fullKey = this.prefix + key
    try {
      sessionStorage.setItem(fullKey, JSON.stringify(value))
    } catch (error) {
      console.error('Failed to save to sessionStorage:', error)
      throw error
    }
  }

  get<T>(key: string): T | null {
    const fullKey = this.prefix + key
    try {
      const value = sessionStorage.getItem(fullKey)
      return value ? JSON.parse(value) : null
    } catch (error) {
      console.error('Failed to get from sessionStorage:', error)
      return null
    }
  }

  remove(key: string): void {
    const fullKey = this.prefix + key
    sessionStorage.removeItem(fullKey)
  }

  clear(): void {
    const keys = Object.keys(sessionStorage)
    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        sessionStorage.removeItem(key)
      }
    })
  }
}

/**
 * IndexedDB 管理器
 */
class IndexedDBManager {
  private dbName = 'THSuiteDB'
  private dbVersion = 1
  private db: IDBDatabase | null = null

  /**
   * 初始化数据库
   */
  async init(): Promise<void> {
    if (this.db) return

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = event => {
        const db = (event.target as IDBOpenDBRequest).result

        // 创建对象存储
        if (!db.objectStoreNames.contains('storage')) {
          db.createObjectStore('storage', { keyPath: 'id' })
        }

        if (!db.objectStoreNames.contains('cache')) {
          const cacheStore = db.createObjectStore('cache', { keyPath: 'id' })
          cacheStore.createIndex('timestamp', 'timestamp', { unique: false })
        }

        if (!db.objectStoreNames.contains('projects')) {
          db.createObjectStore('projects', { keyPath: 'id' })
        }
      }
    })
  }

  /**
   * 保存数据到 IndexedDB
   */
  async save(storeName: string, data: any): Promise<void> {
    await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.put(data)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 从 IndexedDB 获取数据
   */
  async get<T>(storeName: string, id: string): Promise<T | null> {
    await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.get(id)

      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 获取所有数据
   */
  async getAll<T>(storeName: string): Promise<T[]> {
    await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.getAll()

      request.onsuccess = () => resolve(request.result || [])
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 删除数据
   */
  async delete(storeName: string, id: string): Promise<void> {
    await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.delete(id)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 清空存储
   */
  async clear(storeName: string): Promise<void> {
    await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.clear()

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }
}

/**
 * 文件存储管理器（Tauri）
 */
class FileStorageManager {
  private dataDir: string | null = null

  /**
   * 初始化存储目录
   */
  async init(): Promise<void> {
    // Skip file system initialization for now to avoid permission issues
    // Will use localStorage fallback instead
    console.log('FileStorageManager: Using localStorage fallback')
  }

  /**
   * 保存数据到文件
   */
  async saveToFile(filename: string, data: any): Promise<void> {
    // Always use localStorage for now to avoid permission issues
    localStorage.setItem(`file_${filename}`, JSON.stringify(data))
  }

  /**
   * 从文件读取数据
   */
  async readFromFile<T>(filename: string): Promise<T | null> {
    // Always use localStorage for now to avoid permission issues
    const data = localStorage.getItem(`file_${filename}`)
    return data ? JSON.parse(data) : null
  }

  /**
   * 检查文件是否存在
   */
  async fileExists(filename: string): Promise<boolean> {
    // Always use localStorage for now to avoid permission issues
    return localStorage.getItem(`file_${filename}`) !== null
  }

  /**
   * 调用 Tauri 后端存储 API
   */
  async saveToBackend(key: string, value: any): Promise<void> {
    if (!isTauri || !tauriApis.invoke) {
      console.warn('Tauri invoke not available')
      return
    }

    try {
      await tauriApis.invoke('save_data', { key, value })
    } catch (error) {
      console.error('Failed to save to backend:', error)
      throw error
    }
  }

  /**
   * 从 Tauri 后端读取数据
   */
  async loadFromBackend<T>(key: string): Promise<T | null> {
    if (!isTauri || !tauriApis.invoke) {
      console.warn('Tauri invoke not available')
      return null
    }

    try {
      return await tauriApis.invoke('load_data', { key })
    } catch (error) {
      console.error('Failed to load from backend:', error)
      return null
    }
  }
}

/**
 * 统一的存储服务
 */
export class StorageService {
  public local: LocalStorageManager
  public session: SessionStorageManager
  public indexedDB: IndexedDBManager
  public file: FileStorageManager

  constructor() {
    this.local = new LocalStorageManager()
    this.session = new SessionStorageManager()
    this.indexedDB = new IndexedDBManager()
    this.file = new FileStorageManager()
  }

  /**
   * 初始化所有存储
   */
  async init(): Promise<void> {
    await Promise.all([this.indexedDB.init(), this.file.init()])
  }

  /**
   * 保存应用设置
   */
  async saveSettings(settings: any): Promise<void> {
    this.local.set('settings', settings)
    await this.file.saveToFile('settings.json', settings)
  }

  /**
   * 加载应用设置
   */
  async loadSettings(): Promise<any> {
    // 优先从文件加载
    const fileSettings = await this.file.readFromFile('settings.json')
    if (fileSettings) return fileSettings

    // 其次从本地存储加载
    return this.local.get('settings')
  }

  /**
   * 保存项目数据
   */
  async saveProject(project: any): Promise<void> {
    await this.indexedDB.save('projects', project)
    await this.file.saveToFile(`project_${project.id}.json`, project)
  }

  /**
   * 加载项目数据
   */
  async loadProject(projectId: string): Promise<any> {
    // 优先从 IndexedDB 加载
    const dbProject = await this.indexedDB.get('projects', projectId)
    if (dbProject) return dbProject

    // 其次从文件加载
    return await this.file.readFromFile(`project_${projectId}.json`)
  }

  /**
   * 获取所有项目
   */
  async getAllProjects(): Promise<any[]> {
    return await this.indexedDB.getAll('projects')
  }

  /**
   * 清理过期缓存
   */
  async cleanupCache(): Promise<void> {
    const cacheItems = await this.indexedDB.getAll<any>('cache')
    const now = Date.now()
    const expired = cacheItems.filter(item => {
      return item.ttl && now - item.timestamp > item.ttl
    })

    for (const item of expired) {
      await this.indexedDB.delete('cache', item.id)
    }
  }

  /**
   * 导出所有数据
   */
  async exportData(): Promise<any> {
    const settings = await this.loadSettings()
    const projects = await this.getAllProjects()
    const localKeys = this.local.keys()
    const localData: any = {}

    for (const key of localKeys) {
      localData[key] = this.local.get(key)
    }

    return {
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      settings,
      projects,
      localStorage: localData,
    }
  }

  /**
   * 导入数据
   */
  async importData(data: any): Promise<void> {
    if (data.settings) {
      await this.saveSettings(data.settings)
    }

    if (data.projects) {
      for (const project of data.projects) {
        await this.saveProject(project)
      }
    }

    if (data.localStorage) {
      for (const [key, value] of Object.entries(data.localStorage)) {
        this.local.set(key, value)
      }
    }
  }
}

// 导出单例实例
export const storageService = new StorageService()

// 初始化存储服务
if (typeof window !== 'undefined') {
  storageService.init().catch(console.error)
}
