// 提取器接口和实现
// 定义核心的 trait Extractor 和相关结构

use std::path::Path;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use anyhow::Result;

/// 提取结果结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractionResult {
    /// 是否成功
    pub success: bool,
    /// 提取的文件类型
    pub file_type: String,
    /// 检测到的语言文件
    pub language_files: Vec<LanguageFile>,
    /// 元数据信息
    pub metadata: FileMetadata,
    /// 错误信息（如果失败）
    pub error: Option<String>,
    /// 警告信息
    pub warnings: Vec<String>,
    /// 处理统计
    pub stats: ExtractionStats,
}

/// 语言文件信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageFile {
    /// 语言代码 (如 en_us, zh_cn)
    pub language_code: String,
    /// 文件路径 (在JAR内的相对路径)
    pub path: String,
    /// 翻译条目数量
    pub entry_count: usize,
    /// 文件格式 (json, properties, lang)
    pub format: String,
    /// 命名空间 (Minecraft中的资源域名)
    pub namespace: Option<String>,
    /// 示例翻译条目
    pub sample_entries: Vec<TranslationEntry>,
}

/// 翻译条目
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationEntry {
    /// 翻译键
    pub key: String,
    /// 翻译值
    pub value: String,
    /// 条目类型 (text, gui, entity等)
    pub category: Option<String>,
}

/// 文件元数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileMetadata {
    /// 文件名
    pub name: String,
    /// 文件大小
    pub size: u64,
    /// 文件哈希 (用于缓存和去重)
    pub hash: String,
    /// 检测到的MOD信息 (如果是MOD)
    pub mod_info: Option<ModInfo>,
    /// 资源包信息 (如果是资源包)
    pub pack_info: Option<PackInfo>,
    /// UIDA兼容性
    pub uida_compatible: bool,
}

/// MOD信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModInfo {
    /// MOD ID
    pub mod_id: String,
    /// 显示名称
    pub name: String,
    /// 版本
    pub version: String,
    /// 作者
    pub authors: Vec<String>,
    /// 描述
    pub description: Option<String>,
    /// 支持的Minecraft版本
    pub minecraft_version: String,
    /// 模组加载器类型 (forge, fabric, quilt, neoforge)
    pub loader_type: String,
    /// 加载器版本
    pub loader_version: Option<String>,
    /// 依赖MOD
    pub dependencies: Vec<String>,
}

/// 资源包信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackInfo {
    /// 资源包格式版本
    pub pack_format: u32,
    /// 描述
    pub description: String,
    /// 支持的Minecraft版本范围
    pub supported_versions: Vec<String>,
}

/// 提取统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractionStats {
    /// 处理时间 (毫秒)
    pub processing_time_ms: u64,
    /// 扫描的文件数量
    pub files_scanned: usize,
    /// 发现的语言文件数量
    pub language_files_found: usize,
    /// 总翻译条目数量
    pub total_entries: usize,
    /// 内存使用量 (字节)
    pub memory_used: usize,
}

/// 核心提取器接口
#[async_trait]
pub trait Extractor {
    /// 检查是否支持指定文件
    async fn supports(&self, file_path: &Path) -> Result<bool>;

    /// 提取文件内容
    async fn extract(&self, file_path: &Path) -> Result<ExtractionResult>;

    /// 获取提取器信息
    fn get_info(&self) -> ExtractorInfo;

    /// 获取支持的文件扩展名
    fn supported_extensions(&self) -> Vec<String>;

    /// 获取UIDA协议版本
    fn uida_protocol_version(&self) -> String {
        "1.0".to_string()
    }

    /// 验证UIDA兼容性
    async fn validate_uida_compatibility(&self, file_path: &Path) -> Result<bool> {
        // 默认实现：检查文件是否包含UIDA标准结构
        let result = self.extract(file_path).await?;
        Ok(result.metadata.uida_compatible)
    }
}

/// 提取器信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractorInfo {
    pub name: String,
    pub version: String,
    pub author: String,
    pub description: String,
    pub supported_formats: Vec<String>,
}

/// Minecraft MOD提取器 (内置)
pub struct MinecraftModExtractor {
    info: ExtractorInfo,
}

impl MinecraftModExtractor {
    pub fn new() -> Self {
        Self {
            info: ExtractorInfo {
                name: "Minecraft MOD Extractor".to_string(),
                version: "1.0.0".to_string(),
                author: "TH-Suite Team".to_string(),
                description: "提取Minecraft MOD中的语言文件 (Forge, Fabric, Quilt, NeoForge)".to_string(),
                supported_formats: vec!["jar".to_string(), "zip".to_string()],
            },
        }
    }

    /// 检测MOD加载器类型
    async fn detect_loader_type(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<String> {
        let file_names: Vec<String> = zip.file_names().map(|s| s.to_string()).collect();

        // Fabric MOD
        if file_names.contains(&"fabric.mod.json".to_string()) {
            return Ok("fabric".to_string());
        }

        // Quilt MOD
        if file_names.contains(&"quilt.mod.json".to_string()) {
            return Ok("quilt".to_string());
        }

        // Forge MOD (新格式)
        if file_names.contains(&"META-INF/mods.toml".to_string()) {
            return Ok("forge".to_string());
        }

        // NeoForge MOD
        if file_names.contains(&"META-INF/neoforge.mods.toml".to_string()) {
            return Ok("neoforge".to_string());
        }

        // Forge MOD (旧格式)
        if file_names.contains(&"mcmod.info".to_string()) {
            return Ok("forge".to_string());
        }

        Ok("unknown".to_string())
    }

    /// 提取MOD元数据
    async fn extract_mod_metadata(&self, zip: &mut zip::ZipArchive<std::fs::File>, loader_type: &str) -> Result<ModInfo> {
        use std::io::Read;

        match loader_type {
            "fabric" => self.extract_fabric_metadata(zip).await,
            "quilt" => self.extract_quilt_metadata(zip).await,
            "forge" => self.extract_forge_metadata(zip).await,
            "neoforge" => self.extract_neoforge_metadata(zip).await,
            _ => Ok(ModInfo {
                mod_id: "unknown".to_string(),
                name: "Unknown MOD".to_string(),
                version: "unknown".to_string(),
                authors: vec![],
                description: None,
                minecraft_version: "unknown".to_string(),
                loader_type: loader_type.to_string(),
                loader_version: None,
                dependencies: vec![],
            }),
        }
    }

    /// 提取Fabric MOD元数据
    async fn extract_fabric_metadata(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<ModInfo> {
        use std::io::Read;

        let mut file = zip.by_name("fabric.mod.json")?;
        let mut content = String::new();
        file.read_to_string(&mut content)?;

        let json: serde_json::Value = serde_json::from_str(&content)?;

        Ok(ModInfo {
            mod_id: json.get("id").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            name: json.get("name").and_then(|v| v.as_str()).unwrap_or("Unknown").to_string(),
            version: json.get("version").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            authors: json.get("authors")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_str()).map(|s| s.to_string()).collect())
                .unwrap_or_default(),
            description: json.get("description").and_then(|v| v.as_str()).map(|s| s.to_string()),
            minecraft_version: json.get("depends")
                .and_then(|v| v.get("minecraft"))
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .to_string(),
            loader_type: "fabric".to_string(),
            loader_version: json.get("depends")
                .and_then(|v| v.get("fabricloader"))
                .and_then(|v| v.as_str())
                .map(|s| s.to_string()),
            dependencies: json.get("depends")
                .and_then(|v| v.as_object())
                .map(|obj| obj.keys().filter(|k| *k != "minecraft" && *k != "fabricloader")
                    .map(|k| k.clone()).collect())
                .unwrap_or_default(),
        })
    }

    /// 提取Quilt MOD元数据
    async fn extract_quilt_metadata(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<ModInfo> {
        use std::io::Read;

        let mut file = zip.by_name("quilt.mod.json")?;
        let mut content = String::new();
        file.read_to_string(&mut content)?;

        let json: serde_json::Value = serde_json::from_str(&content)?;
        let loader_info = json.get("quilt_loader").unwrap_or(&json);

        Ok(ModInfo {
            mod_id: loader_info.get("id").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            name: loader_info.get("metadata")
                .and_then(|v| v.get("name"))
                .and_then(|v| v.as_str())
                .unwrap_or("Unknown")
                .to_string(),
            version: loader_info.get("version").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            authors: vec![], // Quilt的作者信息更复杂，这里简化处理
            description: loader_info.get("metadata")
                .and_then(|v| v.get("description"))
                .and_then(|v| v.as_str())
                .map(|s| s.to_string()),
            minecraft_version: "unknown".to_string(), // 需要从depends中解析
            loader_type: "quilt".to_string(),
            loader_version: None,
            dependencies: vec![],
        })
    }

    /// 提取Forge MOD元数据
    async fn extract_forge_metadata(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<ModInfo> {
        use std::io::Read;

        // 尝试新格式
        if let Ok(mut file) = zip.by_name("META-INF/mods.toml") {
            let mut content = String::new();
            file.read_to_string(&mut content)?;
            return self.parse_forge_toml(&content).await;
        }

        // 尝试旧格式
        if let Ok(mut file) = zip.by_name("mcmod.info") {
            let mut content = String::new();
            file.read_to_string(&mut content)?;
            return self.parse_mcmod_info(&content).await;
        }

        Err(anyhow::anyhow!("无法找到Forge MOD元数据文件"))
    }

    /// 解析Forge TOML格式
    async fn parse_forge_toml(&self, content: &str) -> Result<ModInfo> {
        // 简单的TOML解析（实际项目中应该使用toml crate）
        use regex::Regex;

        let mod_id_re = Regex::new(r#"modId\s*=\s*"([^"]+)""#)?;
        let version_re = Regex::new(r#"version\s*=\s*"([^"]+)""#)?;
        let display_name_re = Regex::new(r#"displayName\s*=\s*"([^"]+)""#)?;
        let authors_re = Regex::new(r#"authors\s*=\s*"([^"]+)""#)?;
        let description_re = Regex::new(r#"description\s*=\s*"([^"]+)""#)?;

        Ok(ModInfo {
            mod_id: mod_id_re.captures(content)
                .and_then(|cap| cap.get(1))
                .map(|m| m.as_str().to_string())
                .unwrap_or("unknown".to_string()),
            name: display_name_re.captures(content)
                .and_then(|cap| cap.get(1))
                .map(|m| m.as_str().to_string())
                .unwrap_or("Unknown".to_string()),
            version: version_re.captures(content)
                .and_then(|cap| cap.get(1))
                .map(|m| m.as_str().to_string())
                .unwrap_or("unknown".to_string()),
            authors: authors_re.captures(content)
                .and_then(|cap| cap.get(1))
                .map(|m| vec![m.as_str().to_string()])
                .unwrap_or_default(),
            description: description_re.captures(content)
                .and_then(|cap| cap.get(1))
                .map(|m| m.as_str().to_string()),
            minecraft_version: "unknown".to_string(),
            loader_type: "forge".to_string(),
            loader_version: None,
            dependencies: vec![],
        })
    }

    /// 解析mcmod.info格式
    async fn parse_mcmod_info(&self, content: &str) -> Result<ModInfo> {
        let json: serde_json::Value = serde_json::from_str(content)?;
        
        let mod_data = if let Some(array) = json.as_array() {
            array.first().unwrap_or(&json)
        } else {
            &json
        };

        Ok(ModInfo {
            mod_id: mod_data.get("modid").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            name: mod_data.get("name").and_then(|v| v.as_str()).unwrap_or("Unknown").to_string(),
            version: mod_data.get("version").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            authors: mod_data.get("authorList")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_str()).map(|s| s.to_string()).collect())
                .unwrap_or_default(),
            description: mod_data.get("description").and_then(|v| v.as_str()).map(|s| s.to_string()),
            minecraft_version: mod_data.get("mcversion").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
            loader_type: "forge".to_string(),
            loader_version: None,
            dependencies: vec![],
        })
    }

    /// 提取NeoForge MOD元数据
    async fn extract_neoforge_metadata(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<ModInfo> {
        use std::io::Read;

        let mut file = zip.by_name("META-INF/neoforge.mods.toml")?;
        let mut content = String::new();
        file.read_to_string(&mut content)?;

        // NeoForge使用类似Forge的TOML格式
        let mut mod_info = self.parse_forge_toml(&content).await?;
        mod_info.loader_type = "neoforge".to_string();
        Ok(mod_info)
    }

    /// 提取语言文件
    async fn extract_language_files(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<Vec<LanguageFile>> {
        use std::io::Read;

        let mut language_files = Vec::new();

        for i in 0..zip.len() {
            let mut file = zip.by_index(i)?;
            let file_path = file.name().to_string();

            // 检查是否是语言文件路径
            if file_path.starts_with("assets/") && file_path.contains("/lang/") && 
               (file_path.ends_with(".json") || file_path.ends_with(".lang")) {
                
                let mut content = String::new();
                file.read_to_string(&mut content)?;

                // 解析路径信息
                let path_parts: Vec<&str> = file_path.split('/').collect();
                let namespace = if path_parts.len() > 1 { Some(path_parts[1].to_string()) } else { None };
                let filename = path_parts.last().unwrap_or(&"unknown");
                let language_code = filename.split('.').next().unwrap_or("unknown").to_string();
                let format = if file_path.ends_with(".json") { "json" } else { "lang" };

                // 解析翻译条目
                let (entries, entry_count) = self.parse_language_content(&content, format).await?;

                language_files.push(LanguageFile {
                    language_code,
                    path: file_path,
                    entry_count,
                    format: format.to_string(),
                    namespace,
                    sample_entries: entries.into_iter().take(10).collect(),
                });
            }
        }

        Ok(language_files)
    }

    /// 解析语言文件内容
    async fn parse_language_content(&self, content: &str, format: &str) -> Result<(Vec<TranslationEntry>, usize)> {
        match format {
            "json" => {
                let json: serde_json::Value = serde_json::from_str(content)?;
                if let Some(obj) = json.as_object() {
                    let entries: Vec<TranslationEntry> = obj.iter()
                        .map(|(key, value)| TranslationEntry {
                            key: key.clone(),
                            value: value.as_str().unwrap_or("").to_string(),
                            category: self.categorize_translation_key(key),
                        })
                        .collect();
                    Ok((entries.clone(), entries.len()))
                } else {
                    Ok((vec![], 0))
                }
            }
            "lang" => {
                let entries: Vec<TranslationEntry> = content.lines()
                    .filter(|line| !line.trim().is_empty() && !line.starts_with('#') && line.contains('='))
                    .map(|line| {
                        let parts: Vec<&str> = line.splitn(2, '=').collect();
                        if parts.len() == 2 {
                            TranslationEntry {
                                key: parts[0].trim().to_string(),
                                value: parts[1].trim().to_string(),
                                category: self.categorize_translation_key(parts[0].trim()),
                            }
                        } else {
                            TranslationEntry {
                                key: line.to_string(),
                                value: "".to_string(),
                                category: None,
                            }
                        }
                    })
                    .collect();
                Ok((entries.clone(), entries.len()))
            }
            _ => Ok((vec![], 0))
        }
    }

    /// 分类翻译键
    fn categorize_translation_key(&self, key: &str) -> Option<String> {
        if key.starts_with("item.") {
            Some("item".to_string())
        } else if key.starts_with("block.") {
            Some("block".to_string())
        } else if key.starts_with("gui.") {
            Some("gui".to_string())
        } else if key.starts_with("entity.") {
            Some("entity".to_string())
        } else if key.starts_with("enchantment.") {
            Some("enchantment".to_string())
        } else if key.starts_with("effect.") {
            Some("effect".to_string())
        } else {
            Some("other".to_string())
        }
    }
}

#[async_trait]
impl Extractor for MinecraftModExtractor {
    async fn supports(&self, file_path: &Path) -> Result<bool> {
        // 检查文件扩展名
        if let Some(extension) = file_path.extension().and_then(|ext| ext.to_str()) {
            if !matches!(extension.to_lowercase().as_str(), "jar" | "zip") {
                return Ok(false);
            }
        } else {
            return Ok(false);
        }

        // 检查文件是否可以作为ZIP打开
        match std::fs::File::open(file_path) {
            Ok(file) => {
                match zip::ZipArchive::new(file) {
                    Ok(mut zip) => {
                        // 检查是否包含MOD标识文件
                        let file_names: Vec<String> = zip.file_names().map(|s| s.to_string()).collect();
                        
                        let mod_indicators = [
                            "fabric.mod.json",
                            "quilt.mod.json", 
                            "META-INF/mods.toml",
                            "META-INF/neoforge.mods.toml",
                            "mcmod.info"
                        ];

                        Ok(mod_indicators.iter().any(|&indicator| file_names.contains(&indicator.to_string())))
                    }
                    Err(_) => Ok(false),
                }
            }
            Err(_) => Ok(false),
        }
    }

    async fn extract(&self, file_path: &Path) -> Result<ExtractionResult> {
        let start_time = std::time::Instant::now();
        
        let file = std::fs::File::open(file_path)?;
        let mut zip = zip::ZipArchive::new(file)?;

        // 检测加载器类型
        let loader_type = self.detect_loader_type(&mut zip).await?;

        // 提取MOD元数据
        let mod_info = self.extract_mod_metadata(&mut zip, &loader_type).await?;

        // 提取语言文件
        let language_files = self.extract_language_files(&mut zip).await?;

        // 计算文件哈希
        let file_content = std::fs::read(file_path)?;
        let hash = format!("{:x}", sha2::Sha256::digest(&file_content));

        // 统计信息
        let total_entries: usize = language_files.iter().map(|lf| lf.entry_count).sum();
        let processing_time = start_time.elapsed();

        Ok(ExtractionResult {
            success: true,
            file_type: "minecraft_mod".to_string(),
            language_files,
            metadata: FileMetadata {
                name: file_path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                size: file_content.len() as u64,
                hash,
                mod_info: Some(mod_info),
                pack_info: None,
                uida_compatible: true, // Minecraft MOD通常兼容UIDA
            },
            error: None,
            warnings: vec![],
            stats: ExtractionStats {
                processing_time_ms: processing_time.as_millis() as u64,
                files_scanned: zip.len(),
                language_files_found: language_files.len(),
                total_entries,
                memory_used: file_content.len(),
            },
        })
    }

    fn get_info(&self) -> ExtractorInfo {
        self.info.clone()
    }

    fn supported_extensions(&self) -> Vec<String> {
        vec!["jar".to_string(), "zip".to_string()]
    }
}

/// Minecraft资源包提取器 (内置)
pub struct MinecraftResourcePackExtractor {
    info: ExtractorInfo,
}

impl MinecraftResourcePackExtractor {
    pub fn new() -> Self {
        Self {
            info: ExtractorInfo {
                name: "Minecraft Resource Pack Extractor".to_string(),
                version: "1.0.0".to_string(),
                author: "TH-Suite Team".to_string(),
                description: "提取Minecraft资源包中的语言文件".to_string(),
                supported_formats: vec!["zip".to_string()],
            },
        }
    }
}

#[async_trait]
impl Extractor for MinecraftResourcePackExtractor {
    async fn supports(&self, file_path: &Path) -> Result<bool> {
        // 检查是否是ZIP文件
        if let Some(extension) = file_path.extension().and_then(|ext| ext.to_str()) {
            if extension.to_lowercase() != "zip" {
                return Ok(false);
            }
        } else {
            return Ok(false);
        }

        // 检查是否包含pack.mcmeta文件
        match std::fs::File::open(file_path) {
            Ok(file) => {
                match zip::ZipArchive::new(file) {
                    Ok(zip) => {
                        let file_names: Vec<String> = zip.file_names().map(|s| s.to_string()).collect();
                        Ok(file_names.contains(&"pack.mcmeta".to_string()))
                    }
                    Err(_) => Ok(false),
                }
            }
            Err(_) => Ok(false),
        }
    }

    async fn extract(&self, file_path: &Path) -> Result<ExtractionResult> {
        let start_time = std::time::Instant::now();
        
        let file = std::fs::File::open(file_path)?;
        let mut zip = zip::ZipArchive::new(file)?;

        // 读取pack.mcmeta
        let pack_info = self.extract_pack_info(&mut zip).await?;

        // 提取语言文件
        let language_files = self.extract_language_files(&mut zip).await?;

        // 计算文件哈希
        let file_content = std::fs::read(file_path)?;
        let hash = format!("{:x}", sha2::Sha256::digest(&file_content));

        // 统计信息
        let total_entries: usize = language_files.iter().map(|lf| lf.entry_count).sum();
        let processing_time = start_time.elapsed();

        Ok(ExtractionResult {
            success: true,
            file_type: "minecraft_resourcepack".to_string(),
            language_files,
            metadata: FileMetadata {
                name: file_path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                size: file_content.len() as u64,
                hash,
                mod_info: None,
                pack_info: Some(pack_info),
                uida_compatible: true,
            },
            error: None,
            warnings: vec![],
            stats: ExtractionStats {
                processing_time_ms: processing_time.as_millis() as u64,
                files_scanned: zip.len(),
                language_files_found: language_files.len(),
                total_entries,
                memory_used: file_content.len(),
            },
        })
    }

    fn get_info(&self) -> ExtractorInfo {
        self.info.clone()
    }

    fn supported_extensions(&self) -> Vec<String> {
        vec!["zip".to_string()]
    }
}

impl MinecraftResourcePackExtractor {
    /// 提取资源包信息
    async fn extract_pack_info(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<PackInfo> {
        use std::io::Read;

        let mut file = zip.by_name("pack.mcmeta")?;
        let mut content = String::new();
        file.read_to_string(&mut content)?;

        let json: serde_json::Value = serde_json::from_str(&content)?;
        let pack_data = json.get("pack").unwrap_or(&json);

        Ok(PackInfo {
            pack_format: pack_data.get("pack_format")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as u32,
            description: pack_data.get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("Unknown")
                .to_string(),
            supported_versions: vec![], // 需要根据pack_format推断
        })
    }

    /// 提取语言文件
    async fn extract_language_files(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<Vec<LanguageFile>> {
        use std::io::Read;

        let mut language_files = Vec::new();

        for i in 0..zip.len() {
            let mut file = zip.by_index(i)?;
            let file_path = file.name().to_string();

            // 检查是否是语言文件路径
            if file_path.starts_with("assets/") && file_path.contains("/lang/") && 
               file_path.ends_with(".json") {
                
                let mut content = String::new();
                file.read_to_string(&mut content)?;

                // 解析路径信息
                let path_parts: Vec<&str> = file_path.split('/').collect();
                let namespace = if path_parts.len() > 1 { Some(path_parts[1].to_string()) } else { None };
                let filename = path_parts.last().unwrap_or(&"unknown");
                let language_code = filename.split('.').next().unwrap_or("unknown").to_string();

                // 解析JSON内容
                let json: serde_json::Value = serde_json::from_str(&content)?;
                if let Some(obj) = json.as_object() {
                    let entries: Vec<TranslationEntry> = obj.iter()
                        .map(|(key, value)| TranslationEntry {
                            key: key.clone(),
                            value: value.as_str().unwrap_or("").to_string(),
                            category: self.categorize_translation_key(key),
                        })
                        .collect();

                    language_files.push(LanguageFile {
                        language_code,
                        path: file_path,
                        entry_count: entries.len(),
                        format: "json".to_string(),
                        namespace,
                        sample_entries: entries.into_iter().take(10).collect(),
                    });
                }
            }
        }

        Ok(language_files)
    }

    /// 分类翻译键
    fn categorize_translation_key(&self, key: &str) -> Option<String> {
        if key.starts_with("item.") {
            Some("item".to_string())
        } else if key.starts_with("block.") {
            Some("block".to_string())
        } else if key.starts_with("gui.") {
            Some("gui".to_string())
        } else {
            Some("other".to_string())
        }
    }
}