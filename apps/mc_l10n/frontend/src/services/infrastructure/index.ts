/**
 * 基础设施服务导出
 * 包含系统级别的服务，如文件系统、日志、配置等
 */

export { SystemService } from './systemService';
export { FileService } from './fileService';
export { TauriService } from './tauriService';

// 向后兼容
export { initializeTauri } from './tauriService';