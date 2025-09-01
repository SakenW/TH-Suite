import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';
import { readTextFile, writeTextFile, exists, mkdir } from '@tauri-apps/plugin-fs';
import { join, dirname } from '@tauri-apps/api/path';
import { sendNotification } from '@tauri-apps/plugin-notification';
import { listen } from '@tauri-apps/api/event';
import { WebviewWindow } from '@tauri-apps/api/webviewWindow';

export interface TauriFileFilter {
  name: string;
  extensions: string[];
}

export interface TauriDialogOptions {
  title?: string;
  defaultPath?: string;
  filters?: TauriFileFilter[];
  multiple?: boolean;
}

export interface TauriNotificationOptions {
  title: string;
  body?: string;
  icon?: string;
}

export class TauriService {
  private initialized = false;

  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      console.log('Initializing Tauri service...');
      
      if (typeof window !== 'undefined' && window.__TAURI__) {
        console.log('Running in Tauri environment, setting up...');
        
        await this.setupEventListeners();
        await this.requestNotificationPermission();
        
        console.log('Tauri service initialized successfully');
      } else {
        console.warn('Not running in Tauri environment - this appears to be a web browser');
      }
      
      this.initialized = true;
    } catch (error) {
      console.error('Failed to initialize Tauri service:', error);
      throw error;
    }
  }

  // Check if running in Tauri environment
  isTauri(): boolean {
    const isInTauri = typeof window !== 'undefined' && !!window.__TAURI__;
    console.log('isTauri check:', {
      windowExists: typeof window !== 'undefined',
      tauriExists: typeof window !== 'undefined' ? !!window.__TAURI__ : false,
      tauriValue: typeof window !== 'undefined' ? window.__TAURI__ : 'undefined',
      result: isInTauri
    });
    return isInTauri;
  }

  private async setupEventListeners(): Promise<void> {
    // Listen for window events
    await listen('tauri://close-requested', () => {
      console.log('Window close requested');
    });

    await listen('tauri://window-created', (event) => {
      console.log('Window created:', event.payload);
    });

    // Listen for file drop events
    await listen('tauri://file-drop', (event) => {
      console.log('Files dropped:', event.payload);
      // Emit custom event for components to handle
      window.dispatchEvent(new CustomEvent('tauri-file-drop', {
        detail: event.payload
      }));
    });
  }

  private async requestNotificationPermission(): Promise<void> {
    try {
      // Tauri handles notification permissions automatically
      console.log('Notification permission requested');
    } catch (error) {
      console.warn('Failed to request notification permission:', error);
    }
  }

  // File system operations
  async selectFile(options: TauriDialogOptions = {}): Promise<string | null> {
    if (!this.isTauri()) {
      console.warn('selectFile called in non-Tauri environment');
      alert('此功能需要在桌面应用中使用，请下载并安装桌面版本');
      return null;
    }
    
    try {
      console.log('Calling Tauri open dialog for file selection...');
      const result = await open({
        title: options.title || 'Select File',
        defaultPath: options.defaultPath,
        filters: options.filters,
        multiple: false,
      });
      console.log('File selection result:', result);
      return Array.isArray(result) ? result[0] : result;
    } catch (error) {
      console.error('Failed to select file:', error);
      alert('选择文件失败: ' + (error as Error).message);
      return null;
    }
  }

  async selectFiles(options: TauriDialogOptions = {}): Promise<string[]> {
    try {
      const result = await open({
        title: options.title || 'Select Files',
        defaultPath: options.defaultPath,
        filters: options.filters,
        multiple: true,
      });
      return Array.isArray(result) ? result : result ? [result] : [];
    } catch (error) {
      console.error('Failed to select files:', error);
      return [];
    }
  }

  async selectDirectory(options: Omit<TauriDialogOptions, 'filters' | 'multiple'> = {}): Promise<string | null> {
    if (!this.isTauri()) {
      console.warn('selectDirectory called in non-Tauri environment');
      alert('此功能需要在桌面应用中使用，请下载并安装桌面版本');
      return null;
    }
    
    try {
      console.log('Calling Tauri open dialog for directory selection...');
      const result = await open({
        title: options.title || 'Select Directory',
        defaultPath: options.defaultPath,
        directory: true,
      });
      console.log('Directory selection result:', result);
      return Array.isArray(result) ? result[0] : result;
    } catch (error) {
      console.error('Failed to select directory:', error);
      alert('选择文件夹失败: ' + (error as Error).message);
      return null;
    }
  }

  async saveFile(options: TauriDialogOptions = {}): Promise<string | null> {
    try {
      const result = await save({
        title: options.title || 'Save File',
        defaultPath: options.defaultPath,
        filters: options.filters,
      });
      return result;
    } catch (error) {
      console.error('Failed to save file:', error);
      return null;
    }
  }

  async readFile(filePath: string): Promise<string | null> {
    try {
      const content = await readTextFile(filePath);
      return content;
    } catch (error) {
      console.error('Failed to read file:', error);
      return null;
    }
  }

  async writeFile(filePath: string, content: string): Promise<boolean> {
    try {
      // Ensure directory exists
      const dir = await dirname(filePath);
      if (!(await exists(dir))) {
        await mkdir(dir, { recursive: true });
      }
      
      await writeTextFile(filePath, content);
      return true;
    } catch (error) {
      console.error('Failed to write file:', error);
      return false;
    }
  }

  async fileExists(filePath: string): Promise<boolean> {
    try {
      return await exists(filePath);
    } catch (error) {
      console.error('Failed to check file existence:', error);
      return false;
    }
  }

  async joinPath(...paths: string[]): Promise<string> {
    try {
      return await join(...paths);
    } catch (error) {
      console.error('Failed to join paths:', error);
      return paths.join('/');
    }
  }

  // Notification operations
  async showNotification(options: TauriNotificationOptions): Promise<void> {
    try {
      await sendNotification({
        title: options.title,
        body: options.body,
        icon: options.icon,
      });
    } catch (error) {
      console.error('Failed to show notification:', error);
    }
  }

  // Window operations
  async createWindow(label: string, url: string, options: any = {}): Promise<WebviewWindow | null> {
    try {
      const window = new WebviewWindow(label, {
        url,
        title: options.title || 'MC Studio',
        width: options.width || 800,
        height: options.height || 600,
        resizable: options.resizable !== false,
        ...options,
      });
      
      await window.once('tauri://created', () => {
        console.log('Window created successfully');
      });
      
      return window;
    } catch (error) {
      console.error('Failed to create window:', error);
      return null;
    }
  }

  // Backend communication
  async invokeBackend<T = any>(command: string, args: any = {}): Promise<T> {
    try {
      const result = await invoke<T>(command, args);
      return result;
    } catch (error) {
      console.error(`Failed to invoke backend command '${command}':`, error);
      throw error;
    }
  }

  // System operations
  async openPath(path: string): Promise<void> {
    try {
      if (this.isRunningInTauri()) {
        await invoke('open_path', { path });
      } else {
        // In browser environment, just log the action
        console.log('Would open path:', path);
        alert(`Would open: ${path}`);
      }
    } catch (error) {
      console.error('Failed to open path:', error);
      // Fallback: try using shell command only in Tauri
      if (this.isRunningInTauri()) {
        try {
          const { Command } = await import('@tauri-apps/plugin-shell');
          const command = new Command('explorer', [path]);
          await command.execute();
        } catch (fallbackError) {
          console.error('Fallback open path also failed:', fallbackError);
        }
      }
    }
  }

  // Utility methods
  isRunningInTauri(): boolean {
    return typeof window !== 'undefined' && !!window.__TAURI__;
  }

  getVersion(): string {
    return (window as any).__TAURI_METADATA__?.version || 'unknown';
  }
}

// Create singleton instance
const tauriService = new TauriService();

// Export service instance and initialization function
export { tauriService };
export const initializeTauri = () => tauriService.initialize();

// Export commonly used file filters
export const FILE_FILTERS = {
  JSON: { name: 'JSON Files', extensions: ['json'] },
  LANG: { name: 'Language Files', extensions: ['lang'] },
  TOML: { name: 'TOML Files', extensions: ['toml'] },
  CFG: { name: 'Config Files', extensions: ['cfg'] },
  JAR: { name: 'JAR Files', extensions: ['jar'] },
  ZIP: { name: 'ZIP Files', extensions: ['zip'] },
  ALL: { name: 'All Files', extensions: ['*'] },
} as const;