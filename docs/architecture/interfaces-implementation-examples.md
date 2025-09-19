# TH-Suite 配置模板和验证器

## 🎮 游戏配置模板

### Minecraft配置模板

```yaml
# configs/games/minecraft.yml
game:
  id: minecraft
  name: Minecraft
  version: "1.0.0"
  description: "Minecraft mod and resource pack localization tool"
  
file_formats:
  supported:
    - json
    - properties
  primary: json
  encoding: utf-8
  
mod_loaders:
  - id: forge
    name: Forge
    detection:
      files:
        - "META-INF/mods.toml"
        - "mcmod.info"
      jar_manifest_attributes:
        - "FMLCorePlugin"
        - "FMLCorePluginContainsFMLMod"
  
  - id: fabric
    name: Fabric
    detection:
      files:
        - "fabric.mod.json"
      jar_manifest_attributes:
        - "Fabric-Loom-Version"
  
  - id: quilt
    name: Quilt
    detection:
      files:
        - "quilt.mod.json"
      dependencies:
        - "quilt_loader"
  
  - id: neoforge
    name: NeoForge
    detection:
      files:
        - "META-INF/neoforge.mods.toml"
      jar_manifest_attributes:
        - "NeoForge-Version"

project_types:
  - id: mod
    name: MOD项目
    detection:
      priority: 100
      conditions:
        - type: file_exists
          paths:
            - "META-INF/mods.toml"
            - "fabric.mod.json"
            - "quilt.mod.json"
            - "mcmod.info"
        - type: directory_structure
          patterns:
            - "src/main/resources/assets/*/lang/"
            - "assets/*/lang/"
    
    language_file_patterns:
      - "assets/*/lang/*.json"
      - "data/*/lang/*.json"
      - "assets/*/lang/*.properties"
    
    build_targets:
      - jar
      - zip
      - directory
  
  - id: resource_pack
    name: 资源包项目
    detection:
      priority: 90
      conditions:
        - type: file_exists
          paths:
            - "pack.mcmeta"
        - type: directory_structure
          patterns:
            - "assets/*/lang/"
    
    language_file_patterns:
      - "assets/*/lang/*.json"
      - "assets/*/lang/*.properties"
    
    build_targets:
      - zip
      - directory
  
  - id: data_pack
    name: 数据包项目
    detection:
      priority: 80
      conditions:
        - type: file_exists
          paths:
            - "pack.mcmeta"
        - type: directory_structure
          patterns:
            - "data/*/lang/"
    
    language_file_patterns:
      - "data/*/lang/*.json"
    
    build_targets:
      - zip
      - directory

scanning:
  file_patterns:
    include:
      - "**/*.json"
      - "**/*.properties"
      - "**/*.lang"
    exclude:
      - "**/.git/**"
      - "**/node_modules/**"
      - "**/*.jar.tmp"
      - "**/.minecraft/**"
      - "**/logs/**"
      - "**/crash-reports/**"
  
  jar_processing:
    enabled: true
    max_size: "100MB"
    timeout: "30s"
    backup_enabled: true
    backup_directory: ".th-suite/backups"
    
    extraction:
      temp_directory: ".th-suite/temp"
      cleanup_on_exit: true
      preserve_structure: true
    
    validation:
      verify_integrity: true
      check_signatures: false
      scan_malware: true
  
  performance:
    max_concurrent_files: 10
    max_memory_usage: "512MB"
    cache_enabled: true
    cache_ttl: "1h"

build:
  output_formats:
    - id: jar
      name: JAR文件
      extension: ".jar"
      supports_mods: true
      supports_resource_packs: true
      
    - id: zip
      name: ZIP压缩包
      extension: ".zip"
      supports_mods: false
      supports_resource_packs: true
      
    - id: directory
      name: 目录结构
      extension: ""
      supports_mods: true
      supports_resource_packs: true
  
  validation:
    syntax_check: true
    key_consistency: true
    encoding_validation: true
    reference_validation: true
    
    rules:
      - name: json_syntax
        description: "验证JSON语法正确性"
        severity: error
        
      - name: key_format
        description: "验证键名格式规范"
        severity: warning
        pattern: "^[a-z0-9._]+$"
        
      - name: translation_completeness
        description: "检查翻译完整性"
        severity: info
        threshold: 0.8
  
  optimization:
    minify_json: false
    remove_comments: true
    sort_keys: true
    compress_output: false

compression:
  enabled: true
  algorithm: zstd
  level: balanced
  
  dictionary:
    enabled: true
    language_specific: true
    training_samples: 1000
    size: "64KB"
    
  performance:
    chunk_size: "1MB"
    max_memory: "256MB"

localization:
  default_language: "en_us"
  
  supported_languages:
    - code: "en_us"
      name: "English (US)"
      direction: ltr
      
    - code: "zh_cn"
      name: "简体中文"
      direction: ltr
      
    - code: "zh_tw"
      name: "繁體中文"
      direction: ltr
      
    - code: "ja_jp"
      name: "日本語"
      direction: ltr
      
    - code: "ko_kr"
      name: "한국어"
      direction: ltr

integration:
  trans_hub:
    enabled: true
    sync_mode: "bidirectional"
    conflict_resolution: "manual"
    
  version_control:
    git_integration: true
    auto_commit: false
    commit_message_template: "feat: update translations for {language}"
```

### RimWorld配置模板

```yaml
# configs/games/rimworld.yml
game:
  id: rimworld
  name: RimWorld
  version: "1.0.0"
  description: "RimWorld mod localization tool"

file_formats:
  supported:
    - xml
  primary: xml
  encoding: utf-8

project_types:
  - id: mod
    name: MOD项目
    detection:
      priority: 100
      conditions:
        - type: file_exists
          paths:
            - "About/About.xml"
        - type: directory_structure
          patterns:
            - "Languages/*/DefInjected/"
            - "Languages/*/Keyed/"
    
    language_file_patterns:
      - "Languages/*/DefInjected/**/*.xml"
      - "Languages/*/Keyed/*.xml"
      - "Languages/*/Strings/**/*.txt"
    
    build_targets:
      - directory
      - zip

scanning:
  file_patterns:
    include:
      - "**/*.xml"
      - "**/*.txt"
    exclude:
      - "**/.git/**"
      - "**/Assemblies/**"
      - "**/Textures/**"
      - "**/Sounds/**"
  
  validation:
    xml_syntax: true
    def_reference_check: true
    translation_key_consistency: true

parsing:
  xml_processing:
    preserve_formatting: true
    handle_cdata: true
    validate_structure: true
    
  def_injection:
    supported_types:
      - ThingDef
      - PawnKindDef
      - JobDef
      - WorkGiverDef
      - ThoughtDef
      - TraitDef
      - SkillDef
      - StatDef
      - HediffDef
      - BodyPartDef
      - BiomeDef
      - FactionDef
      - WorldObjectDef
      - IncidentDef
      - RulePackDef
      - ConceptDef
      - DesignationCategoryDef
      - ResearchProjectDef
      - RecipeDef
      
  keyed_strings:
    format_validation: true
    placeholder_check: true
    context_extraction: true

build:
  output_formats:
    - id: directory
      name: 目录结构
      extension: ""
      
    - id: zip
      name: ZIP压缩包
      extension: ".zip"
  
  validation:
    xml_syntax: true
    def_structure: true
    translation_completeness: true
    
localization:
  default_language: "English"
  
  supported_languages:
    - code: "English"
      name: "English"
      direction: ltr
      
    - code: "ChineseSimplified"
      name: "简体中文"
      direction: ltr
      
    - code: "ChineseTraditional"
      name: "繁體中文"
      direction: ltr
      
    - code: "Japanese"
      name: "日本語"
      direction: ltr
      
    - code: "Korean"
      name: "한국어"
      direction: ltr
```

### Factorio配置模板

```yaml
# configs/games/factorio.yml
game:
  id: factorio
  name: Factorio
  version: "1.0.0"
  description: "Factorio mod localization tool"

file_formats:
  supported:
    - cfg
    - json
  primary: cfg
  encoding: utf-8

project_types:
  - id: mod
    name: MOD项目
    detection:
      priority: 100
      conditions:
        - type: file_exists
          paths:
            - "info.json"
        - type: directory_structure
          patterns:
            - "locale/*/LC_MESSAGES/"
            - "locale/*/*.cfg"
    
    language_file_patterns:
      - "locale/*/*.cfg"
      - "locale/*/LC_MESSAGES/*.po"
    
    build_targets:
      - zip
      - directory

scanning:
  file_patterns:
    include:
      - "**/*.cfg"
      - "**/*.json"
      - "**/*.po"
    exclude:
      - "**/.git/**"
      - "**/graphics/**"
      - "**/sounds/**"

parsing:
  cfg_format:
    section_based: true
    key_value_separator: "="
    comment_prefix: ";"
    encoding: utf-8
    
  po_format:
    fuzzy_translations: true
    context_support: true
    plural_forms: true

build:
  output_formats:
    - id: zip
      name: ZIP压缩包 (MOD格式)
      extension: ".zip"
      
    - id: directory
      name: 目录结构
      extension: ""

localization:
  default_language: "en"
  
  supported_languages:
    - code: "en"
      name: "English"
      direction: ltr
      
    - code: "zh-CN"
      name: "简体中文"
      direction: ltr
      
    - code: "zh-TW"
      name: "繁體中文"
      direction: ltr
      
    - code: "ja"
      name: "日本語"
      direction: ltr
      
    - code: "ko"
      name: "한국어"
      direction: ltr
```

## 🔧 核心服务配置模板

### 文件传输配置

```yaml
# configs/core/file-transfer.yml
file_transfer:
  engine: "default"
  
  chunked_upload:
    enabled: true
    default_chunk_size: "5MB"
    max_chunk_size: "50MB"
    min_chunk_size: "1MB"
    chunk_threshold: "10MB"  # 超过此大小启用分块上传
    
  concurrent_uploads:
    max_parallel: 8
    adaptive_concurrency: true
    bandwidth_detection: true
    
  retry_policy:
    max_retries: 3
    backoff_strategy: "exponential"  # linear, exponential, fixed
    base_delay: "1s"
    max_delay: "30s"
    jitter: true
    
  resume:
    enabled: true
    token_expiry: "24h"
    cleanup_interval: "1h"
    persistence_type: "file"  # file, memory, database
    
  bandwidth:
    throttling_enabled: false
    max_upload_speed: null      # "10MB/s"
    max_download_speed: null    # "50MB/s"
    adaptive_throttling: true
    
  timeout:
    connection_timeout: "30s"
    read_timeout: "60s"
    write_timeout: "60s"
    total_timeout: "10m"
    
  validation:
    checksum_verification: true
    checksum_algorithm: "blake3"  # md5, sha1, sha256, blake3
    integrity_check: true
    
  cache:
    enabled: true
    directory: ".th-suite/cache/transfers"
    max_size: "1GB"
    ttl: "7d"
    
  security:
    encryption_in_transit: true
    encryption_at_rest: false
    certificate_validation: true
    allowed_hosts: []
    blocked_hosts: []

performance:
  memory_limit: "512MB"
  temp_directory: ".th-suite/temp"
  cleanup_on_exit: true
  
  monitoring:
    enabled: true
    metrics_interval: "5s"
    log_level: "info"  # debug, info, warn, error
```

### 压缩服务配置

```yaml
# configs/core/compression.yml
compression:
  default_algorithm: "zstd"
  
  algorithms:
    zstd:
      enabled: true
      levels:
        fast: 1
        balanced: 6
        high: 15
        maximum: 22
      
      dictionary:
        enabled: true
        size: "64KB"
        training_samples: 1000
        language_specific: true
        auto_training: true
        
      performance:
        max_memory: "256MB"
        threads: "auto"  # auto, 1, 2, 4, 8
        
    gzip:
      enabled: true
      levels:
        fast: 1
        balanced: 6
        high: 9
        
    brotli:
      enabled: true
      levels:
        fast: 1
        balanced: 6
        high: 11

file_type_mapping:
  "application/json": "zstd"
  "text/plain": "zstd"
  "text/xml": "zstd"
  "application/xml": "zstd"
  "text/properties": "gzip"
  "application/octet-stream": "brotli"

dictionary_management:
  auto_update: true
  update_threshold: 1000  # 新样本数量
  update_interval: "24h"
  backup_count: 5
  
  language_dictionaries:
    enable_per_language: true
    supported_languages:
      - "en_us"
      - "zh_cn"
      - "zh_tw"
      - "ja_jp"
      - "ko_kr"

cache:
  enabled: true
  compressed_files: true
  dictionaries: true
  max_size: "256MB"
  ttl: "7d"

monitoring:
  statistics: true
  performance_metrics: true
  compression_ratios: true
  log_operations: false
```

### 安全配置

```yaml
# configs/core/security.yml
security:
  authentication:
    enabled: true
    providers:
      - name: "local"
        type: "local"
        enabled: true
        
      - name: "trans_hub"
        type: "oauth2"
        enabled: true
        client_id: "${TRANS_HUB_CLIENT_ID}"
        client_secret: "${TRANS_HUB_CLIENT_SECRET}"
        authorization_url: "https://api.trans-hub.net/oauth/authorize"
        token_url: "https://api.trans-hub.net/oauth/token"
        
    token:
      algorithm: "HS256"
      expiry: "24h"
      refresh_enabled: true
      refresh_expiry: "7d"
      
  authorization:
    enabled: true
    model: "rbac"  # rbac, abac
    
    roles:
      - name: "admin"
        permissions:
          - "project:create"
          - "project:read"
          - "project:update"
          - "project:delete"
          - "scan:execute"
          - "build:execute"
          - "settings:manage"
          
      - name: "user"
        permissions:
          - "project:read"
          - "project:update"
          - "scan:execute"
          - "build:execute"
          
      - name: "guest"
        permissions:
          - "project:read"
          
  encryption:
    at_rest:
      enabled: false
      algorithm: "AES-256-GCM"
      key_derivation: "PBKDF2"
      
    in_transit:
      enabled: true
      tls_version: "1.3"
      cipher_suites:
        - "TLS_AES_256_GCM_SHA384"
        - "TLS_CHACHA20_POLY1305_SHA256"
        
  file_validation:
    enabled: true
    max_file_size: "100MB"
    
    allowed_types:
      - "application/json"
      - "text/plain"
      - "text/xml"
      - "application/xml"
      - "application/java-archive"
      - "application/zip"
      
    malware_scanning:
      enabled: true
      engine: "clamav"  # clamav, defender
      quarantine_path: ".th-suite/quarantine"
      
    integrity_check:
      enabled: true
      algorithms:
        - "blake3"
        - "sha256"
        
  audit:
    enabled: true
    log_file: ".th-suite/logs/audit.log"
    log_level: "info"
    
    events:
      - "authentication"
      - "authorization"
      - "file_access"
      - "configuration_change"
      - "security_violation"
      
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    burst_size: 20
    
  cors:
    enabled: true
    allowed_origins:
      - "http://localhost:*"
      - "https://*.trans-hub.net"
    allowed_methods:
      - "GET"
      - "POST"
      - "PUT"
      - "DELETE"
    allowed_headers:
      - "Content-Type"
      - "Authorization"
      - "X-Request-ID"
```

## ✅ 配置验证器

### TypeScript配置验证器

```typescript
// packages/core/config/ConfigValidator.ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { ConfigValidationError } from './errors';

export class ConfigValidator {
  private ajv: Ajv;
  private schemas = new Map<string, object>();

  constructor() {
    this.ajv = new Ajv({ allErrors: true, strict: false });
    addFormats(this.ajv);
    this.loadSchemas();
  }

  async validateGameConfig(gameId: string, config: any): Promise<ValidationResult> {
    const schema = this.schemas.get(`game-${gameId}`);
    if (!schema) {
      return {
        isValid: false,
        errors: [`No schema found for game: ${gameId}`]
      };
    }

    const validate = this.ajv.compile(schema);
    const isValid = validate(config);

    if (!isValid) {
      return {
        isValid: false,
        errors: validate.errors?.map(err => 
          `${err.instancePath}: ${err.message}`
        ) || []
      };
    }

    // 业务逻辑验证
    const businessValidation = await this.validateGameBusinessRules(gameId, config);
    
    return {
      isValid: businessValidation.isValid,
      errors: businessValidation.errors,
      warnings: businessValidation.warnings
    };
  }

  async validateCoreConfig(configType: string, config: any): Promise<ValidationResult> {
    const schema = this.schemas.get(`core-${configType}`);
    if (!schema) {
      return {
        isValid: false,
        errors: [`No schema found for core config: ${configType}`]
      };
    }

    const validate = this.ajv.compile(schema);
    const isValid = validate(config);

    if (!isValid) {
      return {
        isValid: false,
        errors: validate.errors?.map(err => 
          `${err.instancePath}: ${err.message}`
        ) || []
      };
    }

    return { isValid: true, errors: [] };
  }

  private loadSchemas(): void {
    // Minecraft游戏配置Schema
    this.schemas.set('game-minecraft', {
      type: 'object',
      required: ['game', 'file_formats', 'mod_loaders', 'project_types'],
      properties: {
        game: {
          type: 'object',
          required: ['id', 'name', 'version'],
          properties: {
            id: { type: 'string', pattern: '^[a-z_]+$' },
            name: { type: 'string', minLength: 1 },
            version: { type: 'string', pattern: '^\\d+\\.\\d+\\.\\d+$' },
            description: { type: 'string' }
          }
        },
        file_formats: {
          type: 'object',
          required: ['supported', 'primary'],
          properties: {
            supported: { 
              type: 'array', 
              items: { type: 'string' },
              minItems: 1
            },
            primary: { type: 'string' },
            encoding: { type: 'string', default: 'utf-8' }
          }
        },
        mod_loaders: {
          type: 'array',
          items: {
            type: 'object',
            required: ['id', 'name', 'detection'],
            properties: {
              id: { type: 'string' },
              name: { type: 'string' },
              detection: {
                type: 'object',
                properties: {
                  files: { type: 'array', items: { type: 'string' } },
                  jar_manifest_attributes: { type: 'array', items: { type: 'string' } }
                }
              }
            }
          }
        },
        // ... 其他属性schema定义
      }
    });

    // 文件传输配置Schema
    this.schemas.set('core-file-transfer', {
      type: 'object',
      required: ['file_transfer'],
      properties: {
        file_transfer: {
          type: 'object',
          properties: {
            engine: { type: 'string', default: 'default' },
            chunked_upload: {
              type: 'object',
              properties: {
                enabled: { type: 'boolean', default: true },
                default_chunk_size: { type: 'string', pattern: '^\\d+[KMGT]?B$' },
                max_chunk_size: { type: 'string', pattern: '^\\d+[KMGT]?B$' },
                min_chunk_size: { type: 'string', pattern: '^\\d+[KMGT]?B$' }
              }
            },
            // ... 其他配置schema
          }
        }
      }
    });

    // 压缩配置Schema
    this.schemas.set('core-compression', {
      type: 'object',
      required: ['compression'],
      properties: {
        compression: {
          type: 'object',
          properties: {
            default_algorithm: { 
              type: 'string', 
              enum: ['zstd', 'gzip', 'brotli'],
              default: 'zstd'
            },
            algorithms: {
              type: 'object',
              properties: {
                zstd: {
                  type: 'object',
                  properties: {
                    enabled: { type: 'boolean', default: true },
                    levels: {
                      type: 'object',
                      properties: {
                        fast: { type: 'integer', minimum: 1, maximum: 22 },
                        balanced: { type: 'integer', minimum: 1, maximum: 22 },
                        high: { type: 'integer', minimum: 1, maximum: 22 },
                        maximum: { type: 'integer', minimum: 1, maximum: 22 }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    });
  }

  private async validateGameBusinessRules(gameId: string, config: any): Promise<ValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (gameId) {
      case 'minecraft':
        // 验证MOD加载器配置
        if (config.mod_loaders) {
          const loaderIds = new Set();
          for (const loader of config.mod_loaders) {
            if (loaderIds.has(loader.id)) {
              errors.push(`Duplicate mod loader ID: ${loader.id}`);
            }
            loaderIds.add(loader.id);

            // 验证检测条件
            if (!loader.detection.files?.length && !loader.detection.jar_manifest_attributes?.length) {
              warnings.push(`Mod loader ${loader.id} has no detection criteria`);
            }
          }
        }

        // 验证项目类型优先级
        if (config.project_types) {
          const priorities = config.project_types.map(pt => pt.detection.priority);
          const uniquePriorities = new Set(priorities);
          if (priorities.length !== uniquePriorities.size) {
            warnings.push('Some project types have duplicate priorities');
          }
        }

        // 验证语言文件模式
        if (config.scanning?.file_patterns?.include) {
          for (const pattern of config.scanning.file_patterns.include) {
            if (!this.isValidGlobPattern(pattern)) {
              errors.push(`Invalid glob pattern: ${pattern}`);
            }
          }
        }
        break;

      case 'rimworld':
        // RimWorld特定验证
        if (config.parsing?.def_injection?.supported_types) {
          const supportedTypes = config.parsing.def_injection.supported_types;
          if (!Array.isArray(supportedTypes) || supportedTypes.length === 0) {
            warnings.push('No supported DefInjection types defined');
          }
        }
        break;

      case 'factorio':
        // Factorio特定验证
        if (config.file_formats?.supported?.includes('cfg')) {
          if (!config.parsing?.cfg_format) {
            errors.push('CFG format support enabled but no parsing configuration provided');
          }
        }
        break;
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  private isValidGlobPattern(pattern: string): boolean {
    try {
      // 简单的glob模式验证
      return /^[^<>:"|?*]*$/.test(pattern);
    } catch {
      return false;
    }
  }
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings?: string[];
}
```

## 🔧 配置管理器

```typescript
// packages/core/config/ConfigManager.ts
export class ConfigManager {
  private configs = new Map<string, any>();
  private validator: ConfigValidator;
  private watchers = new Map<string, FSWatcher>();

  constructor() {
    this.validator = new ConfigValidator();
  }

  async loadGameConfig(gameId: string): Promise<GameConfig> {
    const configPath = this.getGameConfigPath(gameId);
    const config = await this.loadYamlFile(configPath);
    
    // 验证配置
    const validation = await this.validator.validateGameConfig(gameId, config);
    if (!validation.isValid) {
      throw new ConfigValidationError(
        `Invalid ${gameId} configuration: ${validation.errors.join(', ')}`
      );
    }

    // 警告日志
    if (validation.warnings?.length) {
      this.logger.warn(`Config warnings for ${gameId}:`, validation.warnings);
    }

    this.configs.set(`game-${gameId}`, config);
    this.startWatching(configPath, () => this.reloadGameConfig(gameId));
    
    return config;
  }

  async loadCoreConfig(configType: string): Promise<any> {
    const configPath = this.getCoreConfigPath(configType);
    const config = await this.loadYamlFile(configPath);
    
    // 验证配置
    const validation = await this.validator.validateCoreConfig(configType, config);
    if (!validation.isValid) {
      throw new ConfigValidationError(
        `Invalid ${configType} configuration: ${validation.errors.join(', ')}`
      );
    }

    this.configs.set(`core-${configType}`, config);
    this.startWatching(configPath, () => this.reloadCoreConfig(configType));
    
    return config;
  }

  getGameConfig(gameId: string): GameConfig | undefined {
    return this.configs.get(`game-${gameId}`);
  }

  getCoreConfig(configType: string): any {
    return this.configs.get(`core-${configType}`);
  }

  async reloadAllConfigs(): Promise<void> {
    // 重新加载所有配置
    const gameConfigs = Array.from(this.configs.keys())
      .filter(key => key.startsWith('game-'))
      .map(key => key.replace('game-', ''));
    
    const coreConfigs = Array.from(this.configs.keys())
      .filter(key => key.startsWith('core-'))
      .map(key => key.replace('core-', ''));

    for (const gameId of gameConfigs) {
      await this.reloadGameConfig(gameId);
    }

    for (const configType of coreConfigs) {
      await this.reloadCoreConfig(configType);
    }
  }

  private async reloadGameConfig(gameId: string): Promise<void> {
    try {
      await this.loadGameConfig(gameId);
      this.emit('config:reloaded', { type: 'game', id: gameId });
    } catch (error) {
      this.logger.error(`Failed to reload ${gameId} config:`, error);
      this.emit('config:error', { type: 'game', id: gameId, error });
    }
  }

  private async reloadCoreConfig(configType: string): Promise<void> {
    try {
      await this.loadCoreConfig(configType);
      this.emit('config:reloaded', { type: 'core', id: configType });
    } catch (error) {
      this.logger.error(`Failed to reload ${configType} config:`, error);
      this.emit('config:error', { type: 'core', id: configType, error });
    }
  }

  private startWatching(filePath: string, callback: () => void): void {
    if (this.watchers.has(filePath)) {
      return; // 已经在监听
    }

    const watcher = fs.watch(filePath, { persistent: false }, (eventType) => {
      if (eventType === 'change') {
        // 延迟执行，避免重复触发
        setTimeout(callback, 100);
      }
    });

    this.watchers.set(filePath, watcher);
  }

  async dispose(): Promise<void> {
    // 停止所有文件监听
    for (const watcher of this.watchers.values()) {
      watcher.close();
    }
    this.watchers.clear();
    this.configs.clear();
  }
}
```

这些配置模板和验证器提供了：

1. **标准化配置**: 为不同游戏和核心服务定义了统一的配置格式
2. **完整验证**: JSON Schema验证加上业务逻辑验证
3. **热重载**: 配置文件变更时自动重新加载
4. **错误处理**: 详细的错误信息和警告提示
5. **扩展性**: 易于添加新游戏和配置类型的支持

这为模块化架构提供了坚实的配置管理基础。