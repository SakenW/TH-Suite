/**
 * 文件系统操作服务
 * 基于Tauri API实现的文件和目录操作
 */

import { invoke } from '@tauri-apps/api/core'

export interface FileInfo {
  name: string
  path: string
  isDirectory: boolean
  size: number
  modifiedTime: string
}

export interface ScanResult {
  totalFiles: number
  jarFiles: FileInfo[]
  langFiles: FileInfo[]
  modpackFiles: FileInfo[]
  errors: string[]
}

export interface ModInfo {
  id: string
  name: string
  version: string
  mcVersion: string
  loader: 'forge' | 'fabric' | 'quilt' | 'neoforge'
  description?: string
  authors?: string[]
  dependencies?: string[]
  jarPath: string
  langFiles: string[]
}

class FileService {
  /**
   * 选择目录
   */
  async selectDirectory(): Promise<string | null> {
    try {
      // 检查是否在Tauri环境中
      const isTauri = typeof window !== 'undefined' && '__TAURI__' in window

      if (isTauri) {
        console.log('Opening directory selection dialog...')
        const result = await invoke<string | null>('select_directory')
        console.log('Directory selected:', result)
        return result
      } else {
        // Web环境：使用提示框输入路径
        const path = prompt(
          '请输入要扫描的目录路径:\n\n示例:\nC:\\Games\\Minecraft\\mods\nD:\\modpacks\\example-pack',
        )
        console.log('Path entered:', path)
        return path && path.trim() ? path.trim() : null
      }
    } catch (error) {
      console.error('Failed to select directory:', error)
      return null
    }
  }

  /**
   * 扫描目录
   */
  async scanDirectory(dirPath: string): Promise<ScanResult> {
    try {
      console.log('Scanning directory:', dirPath)

      // 检查是否在Tauri环境中
      const isTauri = typeof window !== 'undefined' && '__TAURI__' in window

      if (isTauri) {
        // Tauri环境：使用本地扫描
        const result = await invoke<ScanResult>('scan_directory', { dirPath })
        console.log('Scan completed:', result)
        return result
      } else {
        // Web环境：返回模拟结果
        console.log('Web模式：返回模拟扫描结果')
        const mockResult: ScanResult = {
          totalFiles: 5,
          jarFiles: [
            {
              name: 'example-mod-1.0.0.jar',
              path: dirPath + '/mods/example-mod-1.0.0.jar',
              isDirectory: false,
              size: 1024000,
              modifiedTime: new Date().toISOString(),
            },
          ],
          langFiles: [
            {
              name: 'en_us.json',
              path: dirPath + '/assets/minecraft/lang/en_us.json',
              isDirectory: false,
              size: 2048,
              modifiedTime: new Date().toISOString(),
            },
          ],
          modpackFiles: [],
          errors: [
            'Web模式下的模拟扫描结果 - 请使用 npm run tauri:dev 启动桌面应用获得真实扫描功能',
          ],
        }

        // 模拟扫描延迟
        await new Promise(resolve => setTimeout(resolve, 1000))

        return mockResult
      }
    } catch (error) {
      console.error('Failed to scan directory:', error)
      return {
        totalFiles: 0,
        jarFiles: [],
        langFiles: [],
        modpackFiles: [],
        errors: [`扫描失败: ${error}`],
      }
    }
  }

  /**
   * 解析Mod JAR文件
   */
  async parseModJar(jarPath: string): Promise<ModInfo | null> {
    try {
      console.log('Parsing mod JAR:', jarPath)
      const result = await invoke<ModInfo>('parse_mod_jar', { jarPath })
      console.log('Mod parsed:', result)
      return result
    } catch (error) {
      console.error('Failed to parse mod JAR:', error)
      return null
    }
  }

  /**
   * 批量解析Mod文件
   */
  async batchParseMods(jarPaths: string[]): Promise<ModInfo[]> {
    console.log('Batch parsing', jarPaths.length, 'mod files...')
    const results: ModInfo[] = []

    for (let i = 0; i < jarPaths.length; i++) {
      const jarPath = jarPaths[i]
      console.log(`Parsing mod ${i + 1}/${jarPaths.length}: ${jarPath}`)

      const modInfo = await this.parseModJar(jarPath)
      if (modInfo) {
        results.push(modInfo)
      }

      // 添加小延迟避免过度占用资源
      if (i < jarPaths.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 10))
      }
    }

    console.log('Batch parsing completed:', results.length, 'mods parsed')
    return results
  }

  /**
   * 检测项目类型
   */
  async detectProjectType(
    dirPath: string,
  ): Promise<'modpack' | 'mods' | 'resourcepack' | 'unknown'> {
    try {
      const result = await invoke<string>('detect_project_type', { dirPath })
      return result as 'modpack' | 'mods' | 'resourcepack' | 'unknown'
    } catch (error) {
      console.error('Failed to detect project type:', error)
      return 'unknown'
    }
  }

  /**
   * 获取文件内容（用于读取配置文件等）
   */
  async readTextFile(filePath: string): Promise<string | null> {
    try {
      const content = await invoke<string>('read_text_file', { filePath })
      return content
    } catch (error) {
      console.error('Failed to read text file:', error)
      return null
    }
  }

  /**
   * 检查文件是否存在
   */
  async fileExists(filePath: string): Promise<boolean> {
    try {
      return await invoke<boolean>('file_exists', { filePath })
    } catch (error) {
      console.error('Failed to check file existence:', error)
      return false
    }
  }

  /**
   * 获取目录下的文件列表
   */
  async listDirectory(dirPath: string): Promise<FileInfo[]> {
    try {
      return await invoke<FileInfo[]>('list_directory', { dirPath })
    } catch (error) {
      console.error('Failed to list directory:', error)
      return []
    }
  }

  /**
   * 创建目录
   */
  async createDirectory(dirPath: string): Promise<boolean> {
    try {
      await invoke('create_directory', { dirPath })
      return true
    } catch (error) {
      console.error('Failed to create directory:', error)
      return false
    }
  }

  /**
   * 复制文件
   */
  async copyFile(sourcePath: string, destPath: string): Promise<boolean> {
    try {
      await invoke('copy_file', { sourcePath, destPath })
      return true
    } catch (error) {
      console.error('Failed to copy file:', error)
      return false
    }
  }

  /**
   * 删除文件或目录
   */
  async deleteFile(filePath: string): Promise<boolean> {
    try {
      await invoke('delete_file', { filePath })
      return true
    } catch (error) {
      console.error('Failed to delete file:', error)
      return false
    }
  }

  /**
   * 获取文件大小（以人类可读的格式）
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B'

    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  /**
   * 从路径获取文件名
   */
  getFileName(filePath: string): string {
    return filePath.split(/[\\/]/).pop() || ''
  }

  /**
   * 从路径获取目录名
   */
  getDirName(filePath: string): string {
    const parts = filePath.split(/[\\/]/)
    parts.pop() // 移除文件名部分
    return parts.join('/')
  }

  /**
   * 获取文件扩展名
   */
  getFileExtension(filePath: string): string {
    const fileName = this.getFileName(filePath)
    const lastDotIndex = fileName.lastIndexOf('.')
    return lastDotIndex > 0 ? fileName.substring(lastDotIndex + 1).toLowerCase() : ''
  }

  /**
   * 检查是否为JAR文件
   */
  isJarFile(filePath: string): boolean {
    return this.getFileExtension(filePath) === 'jar'
  }

  /**
   * 检查是否为语言文件
   */
  isLangFile(filePath: string): boolean {
    const ext = this.getFileExtension(filePath)
    return ['json', 'lang'].includes(ext) && filePath.includes('lang')
  }

  /**
   * 检查是否为Modpack配置文件
   */
  isModpackFile(filePath: string): boolean {
    const fileName = this.getFileName(filePath).toLowerCase()
    return ['manifest.json', 'modlist.html', 'instance.cfg', 'mmc-pack.json', 'pack.toml'].includes(
      fileName,
    )
  }
}

// 导出类和单例实例
export { FileService }

// 创建单例实例
export const fileService = new FileService()
export default fileService
