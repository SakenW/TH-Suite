# TH-Suite 核心接口实现示例

## 🎮 游戏适配器接口实现

### Minecraft适配器实现

```typescript
// packages/protocols/game-adapter/MinecraftAdapter.ts
import { GameAdapter, GameProject, LanguageFile, TranslationEntry } from './interfaces';
import { MinecraftProjectDetector } from './detectors/MinecraftProjectDetector';
import { MinecraftFileParser } from './parsers/MinecraftFileParser';
import { MinecraftBuilder } from './builders/MinecraftBuilder';

export class MinecraftAdapter implements GameAdapter {
  readonly gameId = 'minecraft';
  readonly name = 'Minecraft';
  readonly version = '1.0.0';
  readonly supportedFormats = ['json', 'properties'];

  private detector: MinecraftProjectDetector;
  private parser: MinecraftFileParser;
  private builder: MinecraftBuilder;
  private config: MinecraftConfig;

  constructor() {
    this.detector = new MinecraftProjectDetector();
    this.parser = new MinecraftFileParser();
    this.builder = new MinecraftBuilder();
  }

  async initialize(config: MinecraftConfig): Promise<void> {
    this.config = config;
    await this.detector.initialize(config);
    await this.parser.initialize(config);
    await this.builder.initialize(config);
  }

  async detectProjects(directory: string): Promise<GameProject[]> {
    const projects: GameProject[] = [];
    
    // 检测MOD项目
    const modProjects = await this.detector.detectModProjects(directory);
    projects.push(...modProjects);
    
    // 检测资源包项目
    const resourcePackProjects = await this.detector.detectResourcePackProjects(directory);
    projects.push(...resourcePackProjects);
    
    // 检测数据包项目
    const dataPackProjects = await this.detector.detectDataPackProjects(directory);
    projects.push(...dataPackProjects);

    return projects;
  }

  async validateProject(project: GameProject): Promise<ValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 验证项目结构
    if (project.type === 'mod') {
      const hasModFile = await this.detector.hasModLoaderFile(project.path);
      if (!hasModFile) {
        errors.push('No mod loader configuration file found');
      }
    }

    // 验证语言文件
    const languageFiles = await this.extractLanguageFiles(project);
    for (const file of languageFiles) {
      try {
        await this.parser.parseLanguageFile(file);
      } catch (error) {
        errors.push(`Invalid language file ${file.path}: ${error.message}`);
      }
    }

    // 验证资源完整性
    if (project.type === 'resource_pack') {
      const hasPackMcmeta = await fs.pathExists(path.join(project.path, 'pack.mcmeta'));
      if (!hasPackMcmeta) {
        errors.push('pack.mcmeta file not found');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  async extractLanguageFiles(project: GameProject): Promise<LanguageFile[]> {
    const files: LanguageFile[] = [];
    const patterns = this.getLanguageFilePatterns(project.type);

    for (const pattern of patterns) {
      const matches = await glob(pattern, { cwd: project.path });
      
      for (const match of matches) {
        const filePath = path.join(project.path, match);
        const content = await fs.readFile(filePath, 'utf8');
        
        const languageFile: LanguageFile = {
          id: `${project.id}:${match}`,
          path: filePath,
          format: this.detectFileFormat(match),
          language: this.extractLanguageCode(match),
          content,
          metadata: {
            size: content.length,
            lastModified: (await fs.stat(filePath)).mtime,
            encoding: 'utf-8',
            checksum: await this.calculateChecksum(content)
          }
        };

        files.push(languageFile);
      }
    }

    return files;
  }

  async parseLanguageFile(file: LanguageFile): Promise<TranslationEntry[]> {
    return await this.parser.parseLanguageFile(file);
  }

  async buildProject(project: GameProject, options: BuildOptions): Promise<BuildResult> {
    return await this.builder.buildProject(project, options);
  }

  async exportTranslations(project: GameProject, format: ExportFormat): Promise<ExportResult> {
    return await this.builder.exportTranslations(project, format);
  }

  async dispose(): Promise<void> {
    await this.detector.dispose();
    await this.parser.dispose();
    await this.builder.dispose();
  }

  private getLanguageFilePatterns(projectType: string): string[] {
    const config = this.config.project_types.find(pt => pt.id === projectType);
    return config?.language_file_patterns || [];
  }

  private detectFileFormat(filePath: string): FileFormat {
    const extension = path.extname(filePath).toLowerCase();
    switch (extension) {
      case '.json': return 'json';
      case '.properties': return 'properties';
      case '.lang': return 'properties';
      default: return 'unknown';
    }
  }

  private extractLanguageCode(filePath: string): string {
    // 从路径中提取语言代码，如 assets/minecraft/lang/en_us.json -> en_us
    const matches = filePath.match(/\/lang\/([^\/]+)\.[^.]+$/);
    return matches ? matches[1] : 'unknown';
  }

  private async calculateChecksum(content: string): Promise<string> {
    const hasher = createHash('blake3');
    hasher.update(content, 'utf8');
    return hasher.digest('hex');
  }
}
```

### Minecraft项目检测器

```typescript
// packages/protocols/game-adapter/detectors/MinecraftProjectDetector.ts
export class MinecraftProjectDetector {
  private config: MinecraftConfig;

  async initialize(config: MinecraftConfig): Promise<void> {
    this.config = config;
  }

  async detectModProjects(directory: string): Promise<GameProject[]> {
    const projects: GameProject[] = [];
    
    // 检测每种MOD加载器
    for (const loader of this.config.mod_loaders) {
      const modProjects = await this.detectModProjectsForLoader(directory, loader);
      projects.push(...modProjects);
    }

    return projects;
  }

  async detectResourcePackProjects(directory: string): Promise<GameProject[]> {
    const projects: GameProject[] = [];
    const packMcmetaFiles = await glob('**/pack.mcmeta', { cwd: directory });

    for (const packFile of packMcmetaFiles) {
      const projectPath = path.dirname(path.join(directory, packFile));
      
      // 检查是否为资源包（有assets目录）
      const hasAssetsDir = await fs.pathExists(path.join(projectPath, 'assets'));
      if (hasAssetsDir) {
        const project = await this.createResourcePackProject(projectPath);
        projects.push(project);
      }
    }

    return projects;
  }

  async detectDataPackProjects(directory: string): Promise<GameProject[]> {
    const projects: GameProject[] = [];
    const packMcmetaFiles = await glob('**/pack.mcmeta', { cwd: directory });

    for (const packFile of packMcmetaFiles) {
      const projectPath = path.dirname(path.join(directory, packFile));
      
      // 检查是否为数据包（有data目录）
      const hasDataDir = await fs.pathExists(path.join(projectPath, 'data'));
      if (hasDataDir) {
        const project = await this.createDataPackProject(projectPath);
        projects.push(project);
      }
    }

    return projects;
  }

  private async detectModProjectsForLoader(directory: string, loader: ModLoaderConfig): Promise<GameProject[]> {
    const projects: GameProject[] = [];

    // 基于文件检测
    if (loader.detection.files) {
      for (const file of loader.detection.files) {
        const matches = await glob(`**/${file}`, { cwd: directory });
        
        for (const match of matches) {
          const projectPath = path.dirname(path.join(directory, match));
          const project = await this.createModProject(projectPath, loader);
          projects.push(project);
        }
      }
    }

    // 基于JAR文件检测
    const jarFiles = await glob('**/*.jar', { cwd: directory });
    for (const jarFile of jarFiles) {
      const jarPath = path.join(directory, jarFile);
      const isModJar = await this.isModJarForLoader(jarPath, loader);
      
      if (isModJar) {
        const projectPath = path.dirname(jarPath);
        const project = await this.createModProject(projectPath, loader, jarPath);
        projects.push(project);
      }
    }

    return projects;
  }

  private async isModJarForLoader(jarPath: string, loader: ModLoaderConfig): Promise<boolean> {
    try {
      const zip = new AdmZip(jarPath);
      const entries = zip.getEntries();

      // 检查JAR内部文件
      if (loader.detection.files) {
        for (const file of loader.detection.files) {
          if (entries.some(entry => entry.entryName === file)) {
            return true;
          }
        }
      }

      // 检查manifest属性
      if (loader.detection.jar_manifest_attributes) {
        const manifestEntry = entries.find(entry => entry.entryName === 'META-INF/MANIFEST.MF');
        if (manifestEntry) {
          const manifestContent = manifestEntry.getData().toString('utf8');
          
          for (const attr of loader.detection.jar_manifest_attributes) {
            if (manifestContent.includes(attr)) {
              return true;
            }
          }
        }
      }

      return false;
    } catch (error) {
      this.logger.warn(`Failed to analyze JAR file ${jarPath}:`, error);
      return false;
    }
  }

  private async createModProject(projectPath: string, loader: ModLoaderConfig, jarPath?: string): Promise<GameProject> {
    const projectName = path.basename(projectPath);
    const metadata = await this.extractModMetadata(projectPath, loader, jarPath);

    return {
      id: `mod-${projectName}-${Date.now()}`,
      name: metadata.name || projectName,
      type: 'mod',
      path: projectPath,
      metadata: {
        description: metadata.description,
        version: metadata.version,
        authors: metadata.authors,
        dependencies: metadata.dependencies,
        gameVersions: metadata.gameVersions
      },
      gameSpecificData: {
        modLoader: loader.id,
        jarPath,
        modId: metadata.modId
      }
    };
  }

  private async extractModMetadata(projectPath: string, loader: ModLoaderConfig, jarPath?: string): Promise<ModMetadata> {
    const metadata: ModMetadata = {};

    try {
      switch (loader.id) {
        case 'forge':
          metadata = await this.extractForgeMetadata(projectPath, jarPath);
          break;
        case 'fabric':
          metadata = await this.extractFabricMetadata(projectPath, jarPath);
          break;
        case 'quilt':
          metadata = await this.extractQuiltMetadata(projectPath, jarPath);
          break;
        case 'neoforge':
          metadata = await this.extractNeoForgeMetadata(projectPath, jarPath);
          break;
      }
    } catch (error) {
      this.logger.warn(`Failed to extract metadata for ${loader.id} mod:`, error);
    }

    return metadata;
  }

  private async extractForgeMetadata(projectPath: string, jarPath?: string): Promise<ModMetadata> {
    // 尝试读取mods.toml
    const modsTomlPath = path.join(projectPath, 'META-INF/mods.toml');
    if (await fs.pathExists(modsTomlPath)) {
      const tomlContent = await fs.readFile(modsTomlPath, 'utf8');
      return this.parseForgeToml(tomlContent);
    }

    // 如果有JAR文件，从JAR中读取
    if (jarPath) {
      const zip = new AdmZip(jarPath);
      const modsTomlEntry = zip.getEntry('META-INF/mods.toml');
      if (modsTomlEntry) {
        const tomlContent = modsTomlEntry.getData().toString('utf8');
        return this.parseForgeToml(tomlContent);
      }

      // 尝试旧格式mcmod.info
      const mcmodInfoEntry = zip.getEntry('mcmod.info');
      if (mcmodInfoEntry) {
        const jsonContent = mcmodInfoEntry.getData().toString('utf8');
        return this.parseMcmodInfo(jsonContent);
      }
    }

    return {};
  }

  private async extractFabricMetadata(projectPath: string, jarPath?: string): Promise<ModMetadata> {
    const fabricModJsonPath = path.join(projectPath, 'fabric.mod.json');
    if (await fs.pathExists(fabricModJsonPath)) {
      const jsonContent = await fs.readFile(fabricModJsonPath, 'utf8');
      return this.parseFabricModJson(jsonContent);
    }

    if (jarPath) {
      const zip = new AdmZip(jarPath);
      const fabricModEntry = zip.getEntry('fabric.mod.json');
      if (fabricModEntry) {
        const jsonContent = fabricModEntry.getData().toString('utf8');
        return this.parseFabricModJson(jsonContent);
      }
    }

    return {};
  }

  async hasModLoaderFile(projectPath: string): Promise<boolean> {
    for (const loader of this.config.mod_loaders) {
      if (loader.detection.files) {
        for (const file of loader.detection.files) {
          const filePath = path.join(projectPath, file);
          if (await fs.pathExists(filePath)) {
            return true;
          }
        }
      }
    }
    return false;
  }

  async dispose(): Promise<void> {
    // 清理资源
  }
}
```

## 📁 文件传输引擎实现

```typescript
// packages/core/file-transfer/FileTransferEngine.ts
import { FileTransferEngine, UploadOptions, DownloadOptions, TransferProgress } from './interfaces';
import { ChunkedUploadManager } from './ChunkedUploadManager';
import { ProgressTracker } from './ProgressTracker';
import { RetryManager } from './RetryManager';

export class DefaultFileTransferEngine implements FileTransferEngine {
  private chunkedUploadManager: ChunkedUploadManager;
  private progressTracker: ProgressTracker;
  private retryManager: RetryManager;
  private activeTransfers = new Map<string, AbortController>();
  private config: FileTransferConfig;

  constructor(config: FileTransferConfig) {
    this.config = config;
    this.chunkedUploadManager = new ChunkedUploadManager(config.chunked_upload);
    this.progressTracker = new ProgressTracker();
    this.retryManager = new RetryManager(config.retry_policy);
  }

  async uploadFile(file: File, options: UploadOptions = {}): Promise<UploadResult> {
    const transferId = this.generateTransferId();
    const abortController = new AbortController();
    this.activeTransfers.set(transferId, abortController);

    try {
      // 决定是否使用分块上传
      const useChunkedUpload = file.size > this.parseSize(this.config.chunked_upload.chunk_threshold);
      
      if (useChunkedUpload) {
        return await this.uploadFileChunked(transferId, file, options, abortController.signal);
      } else {
        return await this.uploadFileWhole(transferId, file, options, abortController.signal);
      }
    } finally {
      this.activeTransfers.delete(transferId);
    }
  }

  async uploadChunked(file: File, options: ChunkedUploadOptions = {}): Promise<UploadResult> {
    const transferId = this.generateTransferId();
    const abortController = new AbortController();
    this.activeTransfers.set(transferId, abortController);

    try {
      return await this.uploadFileChunked(transferId, file, options, abortController.signal);
    } finally {
      this.activeTransfers.delete(transferId);
    }
  }

  async resumeUpload(uploadId: string): Promise<UploadResult> {
    const uploadState = await this.chunkedUploadManager.getUploadState(uploadId);
    if (!uploadState) {
      throw new Error(`Upload ${uploadId} not found or expired`);
    }

    const abortController = new AbortController();
    this.activeTransfers.set(uploadId, abortController);

    try {
      return await this.chunkedUploadManager.resumeUpload(uploadState, abortController.signal);
    } finally {
      this.activeTransfers.delete(uploadId);
    }
  }

  async downloadFile(url: string, options: DownloadOptions = {}): Promise<DownloadResult> {
    const transferId = this.generateTransferId();
    const abortController = new AbortController();
    this.activeTransfers.set(transferId, abortController);

    try {
      return await this.retryManager.executeWithRetry(async () => {
        const response = await fetch(url, {
          signal: abortController.signal,
          headers: options.headers
        });

        if (!response.ok) {
          throw new Error(`Download failed: ${response.status} ${response.statusText}`);
        }

        const contentLength = parseInt(response.headers.get('content-length') || '0');
        const reader = response.body?.getReader();
        
        if (!reader) {
          throw new Error('Response body is not readable');
        }

        const chunks: Uint8Array[] = [];
        let downloadedBytes = 0;

        // 开始进度跟踪
        this.progressTracker.startTransfer(transferId, contentLength);

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            chunks.push(value);
            downloadedBytes += value.length;

            // 更新进度
            this.progressTracker.updateProgress(transferId, downloadedBytes);
          }

          // 合并所有chunks
          const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
          const result = new Uint8Array(totalLength);
          let offset = 0;
          
          for (const chunk of chunks) {
            result.set(chunk, offset);
            offset += chunk.length;
          }

          return {
            transferId,
            data: result,
            size: downloadedBytes,
            contentType: response.headers.get('content-type') || 'application/octet-stream'
          };
        } finally {
          reader.releaseLock();
          this.progressTracker.completeTransfer(transferId);
        }
      });
    } finally {
      this.activeTransfers.delete(transferId);
    }
  }

  async *downloadStream(url: string, options: StreamOptions = {}): AsyncIterable<Uint8Array> {
    const response = await fetch(url, {
      headers: options.headers
    });

    if (!response.ok) {
      throw new Error(`Download failed: ${response.status} ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        yield value;
      }
    } finally {
      reader.releaseLock();
    }
  }

  onProgress(callback: ProgressCallback): void {
    this.progressTracker.onProgress(callback);
  }

  async getProgress(transferId: string): Promise<TransferProgress> {
    return this.progressTracker.getProgress(transferId);
  }

  async pauseTransfer(transferId: string): Promise<void> {
    const controller = this.activeTransfers.get(transferId);
    if (controller) {
      // 对于分块上传，保存状态以便恢复
      if (this.chunkedUploadManager.hasActiveUpload(transferId)) {
        await this.chunkedUploadManager.pauseUpload(transferId);
      }
      
      controller.abort();
      this.activeTransfers.delete(transferId);
    }
  }

  async resumeTransfer(transferId: string): Promise<void> {
    // 分块上传的恢复通过resumeUpload处理
    if (this.chunkedUploadManager.hasUploadState(transferId)) {
      await this.resumeUpload(transferId);
    } else {
      throw new Error(`Transfer ${transferId} cannot be resumed`);
    }
  }

  async cancelTransfer(transferId: string): Promise<void> {
    const controller = this.activeTransfers.get(transferId);
    if (controller) {
      controller.abort();
    }

    // 清理分块上传状态
    await this.chunkedUploadManager.cancelUpload(transferId);
    this.progressTracker.cancelTransfer(transferId);
    this.activeTransfers.delete(transferId);
  }

  private async uploadFileWhole(
    transferId: string, 
    file: File, 
    options: UploadOptions,
    signal: AbortSignal
  ): Promise<UploadResult> {
    return await this.retryManager.executeWithRetry(async () => {
      const formData = new FormData();
      formData.append('file', file);
      
      if (options.metadata) {
        formData.append('metadata', JSON.stringify(options.metadata));
      }

      // 开始进度跟踪
      this.progressTracker.startTransfer(transferId, file.size);

      const response = await fetch(options.url || '/api/upload', {
        method: 'POST',
        body: formData,
        signal,
        headers: options.headers
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      this.progressTracker.completeTransfer(transferId);

      return {
        transferId,
        uploadId: result.uploadId,
        url: result.url,
        size: file.size
      };
    });
  }

  private async uploadFileChunked(
    transferId: string,
    file: File,
    options: UploadOptions,
    signal: AbortSignal
  ): Promise<UploadResult> {
    return await this.chunkedUploadManager.uploadFile(transferId, file, options, signal);
  }

  private generateTransferId(): string {
    return `transfer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private parseSize(sizeStr: string): number {
    const units = { B: 1, KB: 1024, MB: 1024 * 1024, GB: 1024 * 1024 * 1024 };
    const match = sizeStr.match(/^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)?$/i);
    
    if (!match) {
      throw new Error(`Invalid size format: ${sizeStr}`);
    }

    const value = parseFloat(match[1]);
    const unit = (match[2] || 'B').toUpperCase() as keyof typeof units;
    
    return value * units[unit];
  }
}
```

## 🗜️ 压缩服务实现

```typescript
// packages/core/compression/ZstdCompressionService.ts
import { CompressionService, CompressionOptions, CompressionStatistics } from './interfaces';
import * as zstd from 'zstandard';
import { Transform } from 'stream';

export class ZstdCompressionService implements CompressionService {
  private dictionaries = new Map<string, Buffer>();
  private statistics: CompressionStatistics = {
    totalCompressions: 0,
    totalDecompressions: 0,
    totalBytesCompressed: 0,
    totalBytesDecompressed: 0,
    averageCompressionRatio: 0,
    averageCompressionTime: 0,
    averageDecompressionTime: 0
  };

  async compress(data: Buffer, options: CompressionOptions = {}): Promise<Buffer> {
    const startTime = Date.now();
    
    try {
      const level = this.getCompressionLevel(options.level);
      const compressOptions: any = { level };

      // 使用字典压缩
      if (options.dictionary) {
        compressOptions.dict = options.dictionary;
      }

      const compressed = await zstd.compress(data, compressOptions);
      
      // 更新统计信息
      this.updateCompressionStats(data.length, compressed.length, Date.now() - startTime);
      
      return compressed;
    } catch (error) {
      throw new Error(`Compression failed: ${error.message}`);
    }
  }

  async decompress(data: Buffer, options: DecompressionOptions = {}): Promise<Buffer> {
    const startTime = Date.now();
    
    try {
      const decompressOptions: any = {};

      // 使用字典解压
      if (options.dictionary) {
        decompressOptions.dict = options.dictionary;
      }

      const decompressed = await zstd.decompress(data, decompressOptions);
      
      // 更新统计信息
      this.updateDecompressionStats(data.length, decompressed.length, Date.now() - startTime);
      
      return decompressed;
    } catch (error) {
      throw new Error(`Decompression failed: ${error.message}`);
    }
  }

  createCompressionStream(options: CompressionOptions = {}): Transform {
    const level = this.getCompressionLevel(options.level);
    const compressOptions: any = { level };

    if (options.dictionary) {
      compressOptions.dict = options.dictionary;
    }

    return new Transform({
      transform(chunk: Buffer, encoding, callback) {
        zstd.compress(chunk, compressOptions)
          .then(compressed => callback(null, compressed))
          .catch(error => callback(error));
      }
    });
  }

  createDecompressionStream(options: DecompressionOptions = {}): Transform {
    const decompressOptions: any = {};

    if (options.dictionary) {
      decompressOptions.dict = options.dictionary;
    }

    return new Transform({
      transform(chunk: Buffer, encoding, callback) {
        zstd.decompress(chunk, decompressOptions)
          .then(decompressed => callback(null, decompressed))
          .catch(error => callback(error));
      }
    });
  }

  async createDictionary(samples: Buffer[], options: DictionaryOptions = {}): Promise<Buffer> {
    try {
      const dictSize = options.size || 64 * 1024; // 默认64KB
      
      // 合并所有样本
      const totalSize = samples.reduce((acc, sample) => acc + sample.length, 0);
      const combinedSamples = Buffer.alloc(totalSize);
      let offset = 0;
      
      for (const sample of samples) {
        sample.copy(combinedSamples, offset);
        offset += sample.length;
      }

      // 训练字典
      const dictionary = await zstd.trainDict(combinedSamples, dictSize);
      
      return dictionary;
    } catch (error) {
      throw new Error(`Dictionary creation failed: ${error.message}`);
    }
  }

  async loadDictionary(dictionary: Buffer): Promise<void> {
    // 验证字典格式
    if (!this.isValidDictionary(dictionary)) {
      throw new Error('Invalid dictionary format');
    }

    // 生成字典ID（基于内容的哈希）
    const dictId = this.generateDictionaryId(dictionary);
    this.dictionaries.set(dictId, dictionary);
  }

  getCompressionRatio(originalSize: number, compressedSize: number): number {
    if (originalSize === 0) return 0;
    return compressedSize / originalSize;
  }

  getStatistics(): CompressionStatistics {
    return { ...this.statistics };
  }

  private getCompressionLevel(level?: CompressionLevel): number {
    switch (level) {
      case CompressionLevel.Fast: return 1;
      case CompressionLevel.Balanced: return 6;
      case CompressionLevel.High: return 15;
      case CompressionLevel.Maximum: return 22;
      default: return 6; // 默认平衡级别
    }
  }

  private updateCompressionStats(originalSize: number, compressedSize: number, timeMs: number): void {
    this.statistics.totalCompressions++;
    this.statistics.totalBytesCompressed += originalSize;
    
    // 更新平均压缩比
    const ratio = this.getCompressionRatio(originalSize, compressedSize);
    this.statistics.averageCompressionRatio = (
      (this.statistics.averageCompressionRatio * (this.statistics.totalCompressions - 1) + ratio) 
      / this.statistics.totalCompressions
    );
    
    // 更新平均压缩时间
    this.statistics.averageCompressionTime = (
      (this.statistics.averageCompressionTime * (this.statistics.totalCompressions - 1) + timeMs)
      / this.statistics.totalCompressions
    );
  }

  private updateDecompressionStats(compressedSize: number, decompressedSize: number, timeMs: number): void {
    this.statistics.totalDecompressions++;
    this.statistics.totalBytesDecompressed += decompressedSize;
    
    // 更新平均解压时间
    this.statistics.averageDecompressionTime = (
      (this.statistics.averageDecompressionTime * (this.statistics.totalDecompressions - 1) + timeMs)
      / this.statistics.totalDecompressions
    );
  }

  private isValidDictionary(dictionary: Buffer): boolean {
    // Zstandard字典的魔数是0xEC30A437
    if (dictionary.length < 8) return false;
    
    const magic = dictionary.readUInt32LE(0);
    return magic === 0x37A430EC;
  }

  private generateDictionaryId(dictionary: Buffer): string {
    const crypto = require('crypto');
    return crypto.createHash('blake3').update(dictionary).digest('hex').substring(0, 16);
  }
}
```

## 🔒 安全管理器实现

```typescript
// packages/core/security/SecurityManager.ts
import { SecurityManager, AuthenticationResult, AuthorizationResult } from './interfaces';
import { TokenManager } from './TokenManager';
import { PermissionManager } from './PermissionManager';
import { FileValidator } from './FileValidator';

export class DefaultSecurityManager implements SecurityManager {
  private tokenManager: TokenManager;
  private permissionManager: PermissionManager;
  private fileValidator: FileValidator;
  private config: SecurityConfig;

  constructor(config: SecurityConfig) {
    this.config = config;
    this.tokenManager = new TokenManager(config.authentication);
    this.permissionManager = new PermissionManager(config.authorization);
    this.fileValidator = new FileValidator(config.file_validation);
  }

  async authenticate(credentials: AuthCredentials): Promise<AuthenticationResult> {
    try {
      switch (credentials.type) {
        case 'local':
          return await this.authenticateLocal(credentials);
        case 'oauth2':
          return await this.authenticateOAuth2(credentials);
        case 'token':
          return await this.authenticateToken(credentials);
        default:
          return {
            success: false,
            error: 'Unsupported authentication type'
          };
      }
    } catch (error) {
      this.auditLog('authentication_failure', {
        type: credentials.type,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }

  async authorize(user: User, resource: string, action: string): Promise<AuthorizationResult> {
    try {
      const hasPermission = await this.permissionManager.checkPermission(
        user, 
        resource, 
        action
      );

      if (hasPermission) {
        this.auditLog('authorization_success', {
          userId: user.id,
          resource,
          action
        });
        
        return { authorized: true };
      } else {
        this.auditLog('authorization_failure', {
          userId: user.id,
          resource,
          action,
          reason: 'Insufficient permissions'
        });
        
        return {
          authorized: false,
          reason: 'Insufficient permissions'
        };
      }
    } catch (error) {
      this.auditLog('authorization_error', {
        userId: user.id,
        resource,
        action,
        error: error.message
      });
      
      return {
        authorized: false,
        reason: error.message
      };
    }
  }

  async validateFile(file: File | Buffer, metadata?: FileMetadata): Promise<ValidationResult> {
    return await this.fileValidator.validateFile(file, metadata);
  }

  async encryptData(data: Buffer, key?: Buffer): Promise<Buffer> {
    if (!this.config.encryption.at_rest.enabled) {
      return data;
    }

    const crypto = require('crypto');
    const algorithm = this.config.encryption.at_rest.algorithm;
    const encryptionKey = key || await this.deriveKey();
    
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher(algorithm, encryptionKey);
    
    const encrypted = Buffer.concat([
      cipher.update(data),
      cipher.final()
    ]);

    // 返回IV + 加密数据
    return Buffer.concat([iv, encrypted]);
  }

  async decryptData(encryptedData: Buffer, key?: Buffer): Promise<Buffer> {
    if (!this.config.encryption.at_rest.enabled) {
      return encryptedData;
    }

    const crypto = require('crypto');
    const algorithm = this.config.encryption.at_rest.algorithm;
    const decryptionKey = key || await this.deriveKey();
    
    // 提取IV和加密数据
    const iv = encryptedData.slice(0, 16);
    const encrypted = encryptedData.slice(16);
    
    const decipher = crypto.createDecipher(algorithm, decryptionKey);
    
    const decrypted = Buffer.concat([
      decipher.update(encrypted),
      decipher.final()
    ]);

    return decrypted;
  }

  async createToken(payload: TokenPayload): Promise<string> {
    return await this.tokenManager.createToken(payload);
  }

  async verifyToken(token: string): Promise<TokenPayload | null> {
    return await this.tokenManager.verifyToken(token);
  }

  async refreshToken(refreshToken: string): Promise<TokenPair | null> {
    return await this.tokenManager.refreshToken(refreshToken);
  }

  private async authenticateLocal(credentials: LocalCredentials): Promise<AuthenticationResult> {
    // 本地用户认证逻辑
    const user = await this.findUserByUsername(credentials.username);
    if (!user) {
      return {
        success: false,
        error: 'User not found'
      };
    }

    const passwordValid = await this.verifyPassword(credentials.password, user.passwordHash);
    if (!passwordValid) {
      return {
        success: false,
        error: 'Invalid password'
      };
    }

    const tokenPair = await this.tokenManager.createTokenPair({
      userId: user.id,
      username: user.username,
      roles: user.roles
    });

    this.auditLog('authentication_success', {
      userId: user.id,
      username: user.username,
      type: 'local'
    });

    return {
      success: true,
      user,
      tokens: tokenPair
    };
  }

  private async authenticateOAuth2(credentials: OAuth2Credentials): Promise<AuthenticationResult> {
    // OAuth2认证逻辑
    const tokenResponse = await this.exchangeCodeForToken(credentials.code);
    const userInfo = await this.fetchUserInfo(tokenResponse.access_token);
    
    const user = await this.findOrCreateUser(userInfo);
    const tokenPair = await this.tokenManager.createTokenPair({
      userId: user.id,
      username: user.username,
      roles: user.roles
    });

    this.auditLog('authentication_success', {
      userId: user.id,
      username: user.username,
      type: 'oauth2'
    });

    return {
      success: true,
      user,
      tokens: tokenPair
    };
  }

  private async authenticateToken(credentials: TokenCredentials): Promise<AuthenticationResult> {
    const payload = await this.tokenManager.verifyToken(credentials.token);
    if (!payload) {
      return {
        success: false,
        error: 'Invalid token'
      };
    }

    const user = await this.findUserById(payload.userId);
    if (!user) {
      return {
        success: false,
        error: 'User not found'
      };
    }

    return {
      success: true,
      user
    };
  }

  private async deriveKey(): Promise<Buffer> {
    const crypto = require('crypto');
    const masterKey = process.env.MASTER_ENCRYPTION_KEY || 'default-key';
    const salt = 'th-suite-salt';
    
    return crypto.pbkdf2Sync(masterKey, salt, 100000, 32, 'sha256');
  }

  private auditLog(event: string, data: any): void {
    if (this.config.audit.enabled) {
      const logEntry = {
        timestamp: new Date().toISOString(),
        event,
        data,
        source: 'SecurityManager'
      };
      
      // 写入审计日志
      console.log('AUDIT:', JSON.stringify(logEntry));
    }
  }
}
```

这些具体的接口实现示例展示了：

1. **游戏适配器**: 如何实现Minecraft特定的项目检测、文件解析和构建逻辑
2. **文件传输引擎**: 完整的上传下载功能，包括分块传输、进度跟踪和断点续传
3. **压缩服务**: Zstd压缩算法的实现，包括字典训练和统计信息收集
4. **安全管理器**: 认证、授权、文件验证和数据加密的完整实现

这些实现为模块化架构提供了坚实的技术基础，确保各组件能够独立工作并有效协同。