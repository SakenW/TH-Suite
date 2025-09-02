/**
 * 数据导入导出服务
 * 提供项目数据的备份、恢复、导入、导出功能
 */

import { storageService } from './storage.service';

// Check if we're in a Tauri environment
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__;

// Tauri APIs placeholder
let tauriApis: any = {
  invoke: null,
  save: null,
  open: null,
  writeTextFile: null,
  readTextFile: null
};

// Try to load Tauri APIs if available
if (isTauri) {
  try {
    // These will be resolved at runtime by Tauri
    const tauriCore = (window as any).__TAURI__?.tauri;
    const tauriDialog = (window as any).__TAURI__?.dialog;
    const tauriFs = (window as any).__TAURI__?.fs;
    
    if (tauriCore) tauriApis.invoke = tauriCore.invoke;
    if (tauriDialog) {
      tauriApis.save = tauriDialog.save;
      tauriApis.open = tauriDialog.open;
    }
    if (tauriFs) {
      tauriApis.writeTextFile = tauriFs.writeTextFile;
      tauriApis.readTextFile = tauriFs.readTextFile;
    }
  } catch (err) {
    console.warn('Tauri APIs not available');
  }
}

// Compression utilities (fallback implementation if not available)
const compress = async (data: string): Promise<string> => {
  // Simple base64 encoding as fallback
  return btoa(encodeURIComponent(data));
};

const decompress = async (data: string): Promise<string> => {
  // Simple base64 decoding as fallback
  return decodeURIComponent(atob(data));
};

export interface ExportOptions {
  includeProjects?: boolean;
  includeTranslations?: boolean;
  includeSettings?: boolean;
  includeCache?: boolean;
  compressed?: boolean;
  encrypted?: boolean;
  password?: string;
  format?: 'json' | 'zip' | 'thdata';
}

export interface ImportOptions {
  overwrite?: boolean;
  merge?: boolean;
  validateSchema?: boolean;
  password?: string;
}

export interface ExportData {
  version: string;
  timestamp: string;
  metadata: {
    appVersion: string;
    exportedBy: string;
    projectCount: number;
    translationCount: number;
    totalSize: number;
  };
  data: {
    projects?: any[];
    translations?: any[];
    settings?: any;
    cache?: any;
  };
  checksum?: string;
}

export interface ImportResult {
  success: boolean;
  imported: {
    projects: number;
    translations: number;
    settings: boolean;
    cache: boolean;
  };
  errors: string[];
  warnings: string[];
}

class ImportExportService {
  private readonly EXPORT_VERSION = '1.0.0';
  private readonly APP_VERSION = '0.1.0';

  /**
   * 导出数据到文件
   */
  async exportData(options: ExportOptions = {}): Promise<void> {
    const {
      includeProjects = true,
      includeTranslations = true,
      includeSettings = true,
      includeCache = false,
      compressed = true,
      encrypted = false,
      password,
      format = 'thdata'
    } = options;

    try {
      // 收集要导出的数据
      const exportData: ExportData = {
        version: this.EXPORT_VERSION,
        timestamp: new Date().toISOString(),
        metadata: {
          appVersion: this.APP_VERSION,
          exportedBy: 'TH Suite MC L10n',
          projectCount: 0,
          translationCount: 0,
          totalSize: 0
        },
        data: {}
      };

      // 收集项目数据
      if (includeProjects) {
        const projects = await storageService.getAllProjects();
        exportData.data.projects = projects;
        exportData.metadata.projectCount = projects.length;
      }

      // 收集翻译数据
      if (includeTranslations) {
        const translations = await this.getAllTranslations();
        exportData.data.translations = translations;
        exportData.metadata.translationCount = translations.length;
      }

      // 收集设置
      if (includeSettings) {
        const settings = await storageService.getSettings();
        exportData.data.settings = settings;
      }

      // 收集缓存（可选）
      if (includeCache) {
        const cache = await this.getCacheData();
        exportData.data.cache = cache;
      }

      // 生成校验和
      exportData.checksum = await this.generateChecksum(exportData);

      // 序列化数据
      let dataString = JSON.stringify(exportData, null, 2);
      exportData.metadata.totalSize = dataString.length;

      // 压缩（如果需要）
      if (compressed) {
        dataString = await compress(dataString);
      }

      // 加密（如果需要）
      if (encrypted && password) {
        dataString = await this.encryptData(dataString, password);
      }

      // 选择保存位置
      if (isTauri && tauriApis.save && tauriApis.writeTextFile) {
        const filePath = await tauriApis.save({
          defaultPath: `th-suite-backup-${Date.now()}.${format}`,
          filters: [
            { name: 'TH Suite Data', extensions: [format] },
            { name: 'JSON', extensions: ['json'] },
            { name: 'All Files', extensions: ['*'] }
          ]
        });

        if (filePath) {
          // 写入文件
          await tauriApis.writeTextFile(filePath, dataString);
          console.log('Data exported successfully to:', filePath);
        }
      } else {
        // Fallback: 下载文件到浏览器
        const blob = new Blob([dataString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `th-suite-backup-${Date.now()}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
        console.log('Data exported as download');
      }
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  }

  /**
   * 从文件导入数据
   */
  async importData(options: ImportOptions = {}): Promise<ImportResult> {
    const {
      overwrite = false,
      merge = true,
      validateSchema = true,
      password
    } = options;

    const result: ImportResult = {
      success: false,
      imported: {
        projects: 0,
        translations: 0,
        settings: false,
        cache: false
      },
      errors: [],
      warnings: []
    };

    try {
      // 选择要导入的文件
      let dataString: string;
      
      if (isTauri && tauriApis.open && tauriApis.readTextFile) {
        const selected = await tauriApis.open({
          multiple: false,
          filters: [
            { name: 'TH Suite Data', extensions: ['thdata', 'json', 'zip'] },
            { name: 'All Files', extensions: ['*'] }
          ]
        });

        if (!selected || Array.isArray(selected)) {
          throw new Error('No file selected');
        }

        // 读取文件
        dataString = await tauriApis.readTextFile(selected);
      } else {
        // Fallback: 使用文件选择器
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json,.thdata,.zip';
        
        dataString = await new Promise((resolve, reject) => {
          input.onchange = (e: any) => {
            const file = e.target.files[0];
            if (!file) {
              reject(new Error('No file selected'));
              return;
            }
            
            const reader = new FileReader();
            reader.onload = (event) => {
              resolve(event.target?.result as string);
            };
            reader.onerror = reject;
            reader.readAsText(file);
          };
          input.click();
        });
      }

      // 检测并处理加密
      if (this.isEncrypted(dataString)) {
        if (!password) {
          throw new Error('Password required for encrypted file');
        }
        dataString = await this.decryptData(dataString, password);
      }

      // 检测并处理压缩
      if (this.isCompressed(dataString)) {
        dataString = await decompress(dataString);
      }

      // 解析数据
      const importData: ExportData = JSON.parse(dataString);

      // 验证架构
      if (validateSchema) {
        this.validateImportData(importData);
      }

      // 验证校验和
      if (importData.checksum) {
        const expectedChecksum = await this.generateChecksum({
          ...importData,
          checksum: undefined
        });
        if (expectedChecksum !== importData.checksum) {
          result.warnings.push('Checksum mismatch - data may be corrupted');
        }
      }

      // 导入项目
      if (importData.data.projects) {
        const importedProjects = await this.importProjects(
          importData.data.projects,
          { overwrite, merge }
        );
        result.imported.projects = importedProjects;
      }

      // 导入翻译
      if (importData.data.translations) {
        const importedTranslations = await this.importTranslations(
          importData.data.translations,
          { overwrite, merge }
        );
        result.imported.translations = importedTranslations;
      }

      // 导入设置
      if (importData.data.settings) {
        await storageService.saveSettings(importData.data.settings);
        result.imported.settings = true;
      }

      // 导入缓存
      if (importData.data.cache) {
        await this.importCache(importData.data.cache);
        result.imported.cache = true;
      }

      result.success = true;
    } catch (error) {
      console.error('Import failed:', error);
      result.errors.push(error instanceof Error ? error.message : String(error));
    }

    return result;
  }

  /**
   * 导出为不同格式
   */
  async exportToFormat(format: 'csv' | 'excel' | 'json' | 'xml', data: any): Promise<void> {
    let formatted: string;

    switch (format) {
      case 'csv':
        formatted = await this.convertToCSV(data);
        break;
      case 'json':
        formatted = JSON.stringify(data, null, 2);
        break;
      case 'xml':
        formatted = await this.convertToXML(data);
        break;
      case 'excel':
        // 需要特殊处理，可能需要使用第三方库
        throw new Error('Excel export not yet implemented');
      default:
        throw new Error(`Unsupported format: ${format}`);
    }

    if (isTauri && tauriApis.save && tauriApis.writeTextFile) {
      const filePath = await tauriApis.save({
        defaultPath: `export-${Date.now()}.${format}`,
        filters: [
          { name: format.toUpperCase(), extensions: [format] },
          { name: 'All Files', extensions: ['*'] }
        ]
      });

      if (filePath) {
        await tauriApis.writeTextFile(filePath, formatted);
      }
    } else {
      // Fallback: download file to browser
      const blob = new Blob([formatted], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `export-${Date.now()}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  /**
   * 批量导出项目
   */
  async exportProjects(projectIds: string[], options?: ExportOptions): Promise<void> {
    const projects = await Promise.all(
      projectIds.map(id => storageService.getProject(id))
    );

    await this.exportData({
      ...options,
      includeProjects: true,
      includeTranslations: false,
      includeSettings: false,
      includeCache: false
    });
  }

  /**
   * 创建备份
   */
  async createBackup(name?: string): Promise<string> {
    const backupName = name || `backup-${Date.now()}`;
    const backupData = await storageService.exportData();
    
    // 保存到 Tauri 后端
    if (isTauri && tauriApis.invoke) {
      await tauriApis.invoke('create_backup', { name: backupName, data: backupData });
    } else {
      // Fallback: 保存到 localStorage
      const backups = JSON.parse(localStorage.getItem('th_suite_backups') || '[]');
      backups.push({ name: backupName, data: backupData, timestamp: Date.now() });
      localStorage.setItem('th_suite_backups', JSON.stringify(backups));
    }
    
    return backupName;
  }

  /**
   * 恢复备份
   */
  async restoreBackup(backupName: string): Promise<void> {
    if (isTauri && tauriApis.invoke) {
      const backupData = await tauriApis.invoke<any>('restore_backup', { name: backupName });
      await storageService.importData(backupData);
    } else {
      // Fallback: restore from localStorage
      const backups = JSON.parse(localStorage.getItem('th_suite_backups') || '[]');
      const backup = backups.find((b: any) => b.name === backupName);
      if (backup) {
        await storageService.importData(backup.data);
      }
    }
  }

  /**
   * 列出所有备份
   */
  async listBackups(): Promise<Array<{ name: string; date: string; size: number }>> {
    if (isTauri && tauriApis.invoke) {
      return await tauriApis.invoke('list_backups');
    } else {
      // Fallback: 从 localStorage 获取
      const backups = JSON.parse(localStorage.getItem('th_suite_backups') || '[]');
      return backups.map((b: any) => ({ name: b.name, timestamp: b.timestamp }));
    }
  }

  // 私有辅助方法

  private async getAllTranslations(): Promise<any[]> {
    // 从 IndexedDB 获取所有翻译
    // 这里需要实现具体的逻辑
    return [];
  }

  private async getCacheData(): Promise<any> {
    // 获取缓存数据
    return {};
  }

  private async generateChecksum(data: any): Promise<string> {
    const str = JSON.stringify(data);
    // 简单的校验和实现，实际应用中可以使用更强的算法
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString(16);
  }

  private async encryptData(data: string, password: string): Promise<string> {
    // 简单的XOR加密，实际应用中应使用更强的加密算法
    const encrypted = data.split('').map((char, i) => {
      return String.fromCharCode(char.charCodeAt(0) ^ password.charCodeAt(i % password.length));
    }).join('');
    return btoa(encrypted);
  }

  private async decryptData(data: string, password: string): Promise<string> {
    const decoded = atob(data);
    return decoded.split('').map((char, i) => {
      return String.fromCharCode(char.charCodeAt(0) ^ password.charCodeAt(i % password.length));
    }).join('');
  }

  private isEncrypted(data: string): boolean {
    // 检查是否为Base64编码
    try {
      return btoa(atob(data)) === data;
    } catch {
      return false;
    }
  }

  private isCompressed(data: string): boolean {
    // 检查压缩标识
    return data.startsWith('COMPRESSED:');
  }

  private validateImportData(data: ExportData): void {
    if (!data.version || !data.timestamp || !data.data) {
      throw new Error('Invalid import data structure');
    }
    
    // 版本兼容性检查
    const [major] = data.version.split('.').map(Number);
    const [currentMajor] = this.EXPORT_VERSION.split('.').map(Number);
    
    if (major > currentMajor) {
      throw new Error(`Incompatible version: ${data.version}`);
    }
  }

  private async importProjects(projects: any[], options: any): Promise<number> {
    let imported = 0;
    for (const project of projects) {
      try {
        if (options.overwrite || !(await storageService.getProject(project.id))) {
          await storageService.saveProject(project);
          imported++;
        }
      } catch (error) {
        console.error('Failed to import project:', project.id, error);
      }
    }
    return imported;
  }

  private async importTranslations(translations: any[], options: any): Promise<number> {
    // 实现翻译导入逻辑
    return translations.length;
  }

  private async importCache(cache: any): Promise<void> {
    // 实现缓存导入逻辑
  }

  private async convertToCSV(data: any[]): Promise<string> {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');
    const csvRows = data.map(row => 
      headers.map(header => {
        const value = row[header];
        return typeof value === 'string' && value.includes(',') 
          ? `"${value}"` 
          : value;
      }).join(',')
    );
    
    return [csvHeaders, ...csvRows].join('\n');
  }

  private async convertToXML(data: any): Promise<string> {
    const xmlDoc = new DOMParser().parseFromString('<root></root>', 'text/xml');
    const root = xmlDoc.documentElement;
    
    const appendElement = (parent: Element, obj: any, name: string) => {
      const elem = xmlDoc.createElement(name);
      
      if (typeof obj === 'object' && obj !== null) {
        Object.entries(obj).forEach(([key, value]) => {
          if (Array.isArray(value)) {
            value.forEach(item => appendElement(elem, item, key));
          } else {
            appendElement(elem, value, key);
          }
        });
      } else {
        elem.textContent = String(obj);
      }
      
      parent.appendChild(elem);
    };
    
    appendElement(root, data, 'data');
    return new XMLSerializer().serializeToString(xmlDoc);
  }
}

export const importExportService = new ImportExportService();