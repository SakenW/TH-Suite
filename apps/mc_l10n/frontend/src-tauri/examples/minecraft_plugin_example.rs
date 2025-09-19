// Minecraft MOD插件示例
// 演示如何创建一个Rust-first插件来提取Minecraft MOD的语言文件

use std::path::Path;
use anyhow::Result;
use th_suite_mc_l10n::plugins::*;

/// 示例插件：增强版Minecraft MOD提取器
pub struct EnhancedMinecraftExtractor {
    info: ExtractorInfo,
}

impl EnhancedMinecraftExtractor {
    pub fn new() -> Self {
        Self {
            info: ExtractorInfo {
                name: "Enhanced Minecraft MOD Extractor".to_string(),
                version: "2.0.0".to_string(),
                author: "TH-Suite Plugin Example".to_string(),
                description: "增强版Minecraft MOD提取器，支持更多格式和优化".to_string(),
                supported_formats: vec![
                    "jar".to_string(), 
                    "zip".to_string(), 
                    "mrpack".to_string(),  // Modrinth模组包
                    "ccip".to_string(),    // CurseForge模组包
                ],
            },
        }
    }

    /// 检测模组包类型
    async fn detect_modpack_type(&self, file_path: &Path) -> Result<Option<String>> {
        if let Some(extension) = file_path.extension().and_then(|ext| ext.to_str()) {
            match extension.to_lowercase().as_str() {
                "mrpack" => return Ok(Some("modrinth".to_string())),
                "ccip" => return Ok(Some("curseforge".to_string())),
                _ => {}
            }
        }

        // 检查ZIP内容来判断
        if let Ok(file) = std::fs::File::open(file_path) {
            if let Ok(mut zip) = zip::ZipArchive::new(file) {
                let file_names: Vec<String> = zip.file_names().map(|s| s.to_string()).collect();
                
                if file_names.contains(&"modrinth.index.json".to_string()) {
                    return Ok(Some("modrinth".to_string()));
                }
                
                if file_names.contains(&"manifest.json".to_string()) {
                    return Ok(Some("curseforge".to_string()));
                }
            }
        }

        Ok(None)
    }

    /// 提取模组包中的所有MOD
    async fn extract_modpack_mods(&self, file_path: &Path, pack_type: &str) -> Result<Vec<ExtractionResult>> {
        let mut results = Vec::new();
        
        match pack_type {
            "modrinth" => {
                results.extend(self.extract_modrinth_mods(file_path).await?);
            }
            "curseforge" => {
                results.extend(self.extract_curseforge_mods(file_path).await?);
            }
            _ => {
                log::warn!("未知的模组包类型: {}", pack_type);
            }
        }

        Ok(results)
    }

    /// 提取Modrinth模组包
    async fn extract_modrinth_mods(&self, file_path: &Path) -> Result<Vec<ExtractionResult>> {
        let mut results = Vec::new();
        
        let file = std::fs::File::open(file_path)?;
        let mut zip = zip::ZipArchive::new(file)?;

        // 读取索引文件
        let mut index_file = zip.by_name("modrinth.index.json")?;
        let mut index_content = String::new();
        std::io::Read::read_to_string(&mut index_file, &mut index_content)?;
        
        let index: serde_json::Value = serde_json::from_str(&index_content)?;
        
        // 解析文件列表
        if let Some(files) = index.get("files").and_then(|f| f.as_array()) {
            for file_entry in files {
                if let Some(path) = file_entry.get("path").and_then(|p| p.as_str()) {
                    if path.starts_with("mods/") && path.ends_with(".jar") {
                        // 这里可以进一步处理每个MOD文件
                        log::info!("发现Modrinth MOD: {}", path);
                    }
                }
            }
        }

        Ok(results)
    }

    /// 提取CurseForge模组包
    async fn extract_curseforge_mods(&self, file_path: &Path) -> Result<Vec<ExtractionResult>> {
        let mut results = Vec::new();
        
        let file = std::fs::File::open(file_path)?;
        let mut zip = zip::ZipArchive::new(file)?;

        // 读取清单文件
        let mut manifest_file = zip.by_name("manifest.json")?;
        let mut manifest_content = String::new();
        std::io::Read::read_to_string(&mut manifest_file, &mut manifest_content)?;
        
        let manifest: serde_json::Value = serde_json::from_str(&manifest_content)?;
        
        // 解析文件列表
        if let Some(files) = manifest.get("files").and_then(|f| f.as_array()) {
            for file_entry in files {
                if let Some(file_id) = file_entry.get("fileID").and_then(|f| f.as_u64()) {
                    log::info!("发现CurseForge MOD ID: {}", file_id);
                    // 这里可以通过CurseForge API获取更多信息
                }
            }
        }

        Ok(results)
    }

    /// 智能语言文件检测
    async fn smart_language_detection(&self, zip: &mut zip::ZipArchive<std::fs::File>) -> Result<Vec<LanguageFile>> {
        let mut language_files = Vec::new();
        
        for i in 0..zip.len() {
            let file = zip.by_index(i)?;
            let file_path = file.name();

            // 检测各种语言文件模式
            if self.is_language_file_path(file_path) {
                if let Ok(lang_file) = self.parse_language_file(file).await {
                    language_files.push(lang_file);
                }
            }
        }

        // 去重和排序
        language_files.sort_by(|a, b| a.language_code.cmp(&b.language_code));
        language_files.dedup_by(|a, b| a.path == b.path);

        Ok(language_files)
    }

    /// 检查是否为语言文件路径
    fn is_language_file_path(&self, path: &str) -> bool {
        // 标准Minecraft路径
        if path.starts_with("assets/") && path.contains("/lang/") {
            return true;
        }

        // 其他可能的语言文件路径
        let lang_patterns = [
            "/lang/",
            "/i18n/",
            "/localization/",
            "/locale/",
            "_lang/",
            ".lang",
            "_i18n.",
        ];

        lang_patterns.iter().any(|pattern| path.contains(pattern))
    }

    /// 解析语言文件
    async fn parse_language_file(&self, mut file: zip::read::ZipFile) -> Result<LanguageFile> {
        let file_path = file.name().to_string();
        let mut content = String::new();
        std::io::Read::read_to_string(&mut file, &mut content)?;

        // 智能检测语言代码
        let language_code = self.extract_language_code(&file_path);
        
        // 智能检测格式
        let format = self.detect_file_format(&file_path, &content);
        
        // 解析条目
        let (entries, entry_count) = self.parse_entries(&content, &format).await?;

        // 提取命名空间
        let namespace = self.extract_namespace(&file_path);

        Ok(LanguageFile {
            language_code,
            path: file_path,
            entry_count,
            format,
            namespace,
            sample_entries: entries.into_iter().take(5).collect(),
        })
    }

    /// 提取语言代码
    fn extract_language_code(&self, path: &str) -> String {
        // 从文件名提取语言代码
        if let Some(file_name) = path.split('/').last() {
            if let Some(name_part) = file_name.split('.').next() {
                // 标准语言代码模式
                if name_part.len() >= 2 {
                    return name_part.to_string();
                }
            }
        }

        // 从路径中提取
        if path.contains("/lang/") {
            if let Some(lang_part) = path.split("/lang/").nth(1) {
                if let Some(lang_code) = lang_part.split('/').next() {
                    return lang_code.to_string();
                }
            }
        }

        "unknown".to_string()
    }

    /// 检测文件格式
    fn detect_file_format(&self, path: &str, content: &str) -> String {
        // 从扩展名检测
        if path.ends_with(".json") {
            return "json".to_string();
        }
        if path.ends_with(".lang") || path.ends_with(".properties") {
            return "properties".to_string();
        }

        // 从内容检测
        if content.trim_start().starts_with('{') {
            return "json".to_string();
        }

        if content.lines().any(|line| line.contains('=') && !line.trim_start().starts_with('#')) {
            return "properties".to_string();
        }

        "unknown".to_string()
    }

    /// 解析条目
    async fn parse_entries(&self, content: &str, format: &str) -> Result<(Vec<TranslationEntry>, usize)> {
        match format {
            "json" => self.parse_json_entries(content).await,
            "properties" => self.parse_properties_entries(content).await,
            _ => Ok((vec![], 0)),
        }
    }

    /// 解析JSON格式条目
    async fn parse_json_entries(&self, content: &str) -> Result<(Vec<TranslationEntry>, usize)> {
        let json: serde_json::Value = serde_json::from_str(content)?;
        
        if let Some(obj) = json.as_object() {
            let entries: Vec<TranslationEntry> = obj.iter()
                .map(|(key, value)| TranslationEntry {
                    key: key.clone(),
                    value: value.as_str().unwrap_or("").to_string(),
                    category: self.categorize_key(key),
                })
                .collect();
            
            Ok((entries.clone(), entries.len()))
        } else {
            Ok((vec![], 0))
        }
    }

    /// 解析Properties格式条目
    async fn parse_properties_entries(&self, content: &str) -> Result<(Vec<TranslationEntry>, usize)> {
        let entries: Vec<TranslationEntry> = content.lines()
            .filter_map(|line| {
                let line = line.trim();
                if line.is_empty() || line.starts_with('#') || line.starts_with('!') {
                    return None;
                }

                if let Some(eq_pos) = line.find('=') {
                    let key = line[..eq_pos].trim().to_string();
                    let value = line[eq_pos + 1..].trim().to_string();
                    
                    Some(TranslationEntry {
                        key: key.clone(),
                        value,
                        category: self.categorize_key(&key),
                    })
                } else {
                    None
                }
            })
            .collect();

        Ok((entries.clone(), entries.len()))
    }

    /// 分类翻译键
    fn categorize_key(&self, key: &str) -> Option<String> {
        let categories = [
            ("item.", "item"),
            ("block.", "block"),
            ("gui.", "gui"),
            ("entity.", "entity"),
            ("enchantment.", "enchantment"),
            ("effect.", "effect"),
            ("biome.", "biome"),
            ("advancement.", "advancement"),
            ("command.", "command"),
            ("death.", "death"),
            ("menu.", "menu"),
        ];

        for (prefix, category) in &categories {
            if key.starts_with(prefix) {
                return Some(category.to_string());
            }
        }

        Some("other".to_string())
    }

    /// 提取命名空间
    fn extract_namespace(&self, path: &str) -> Option<String> {
        if path.starts_with("assets/") {
            let parts: Vec<&str> = path.split('/').collect();
            if parts.len() > 1 {
                return Some(parts[1].to_string());
            }
        }
        None
    }
}

#[async_trait::async_trait]
impl Extractor for EnhancedMinecraftExtractor {
    async fn supports(&self, file_path: &Path) -> Result<bool> {
        // 检查文件扩展名
        if let Some(extension) = file_path.extension().and_then(|ext| ext.to_str()) {
            let supported_extensions = ["jar", "zip", "mrpack", "ccip"];
            if !supported_extensions.contains(&extension.to_lowercase().as_str()) {
                return Ok(false);
            }
        } else {
            return Ok(false);
        }

        // 检查是否为有效的ZIP文件
        match std::fs::File::open(file_path) {
            Ok(file) => {
                match zip::ZipArchive::new(file) {
                    Ok(_) => Ok(true),
                    Err(_) => Ok(false),
                }
            }
            Err(_) => Ok(false),
        }
    }

    async fn extract(&self, file_path: &Path) -> Result<ExtractionResult> {
        let start_time = std::time::Instant::now();
        
        // 检测是否为模组包
        if let Some(pack_type) = self.detect_modpack_type(file_path).await? {
            log::info!("检测到模组包类型: {}", pack_type);
            
            // 提取模组包内容
            let modpack_results = self.extract_modpack_mods(file_path, &pack_type).await?;
            
            if !modpack_results.is_empty() {
                // 返回第一个结果作为示例（实际应该合并所有结果）
                return Ok(modpack_results.into_iter().next().unwrap());
            }
        }

        // 按照标准MOD处理
        let file = std::fs::File::open(file_path)?;
        let mut zip = zip::ZipArchive::new(file)?;

        // 智能语言文件检测
        let language_files = self.smart_language_detection(&mut zip).await?;

        // 计算文件哈希
        let file_content = std::fs::read(file_path)?;
        let hash = format!("{:x}", sha2::Sha256::digest(&file_content));

        // 统计信息
        let total_entries: usize = language_files.iter().map(|lf| lf.entry_count).sum();
        let processing_time = start_time.elapsed();

        Ok(ExtractionResult {
            success: true,
            file_type: "enhanced_minecraft_mod".to_string(),
            language_files,
            metadata: FileMetadata {
                name: file_path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                size: file_content.len() as u64,
                hash,
                mod_info: None, // 可以添加更详细的MOD信息提取
                pack_info: None,
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
        vec!["jar".to_string(), "zip".to_string(), "mrpack".to_string(), "ccip".to_string()]
    }

    fn uida_protocol_version(&self) -> String {
        "2.0".to_string()
    }
}

/// 插件入口点 - 导出函数供动态加载
#[no_mangle]
pub extern "C" fn create_extractor() -> Box<dyn Extractor + Send + Sync> {
    Box::new(EnhancedMinecraftExtractor::new())
}

#[no_mangle]
pub extern "C" fn plugin_api_version() -> *const std::os::raw::c_char {
    b"2.0\0".as_ptr() as *const std::os::raw::c_char
}

/// 演示如何使用插件系统
async fn demo_plugin_system() -> Result<()> {
    println!("🚀 Rust-first插件系统演示");

    // 创建插件配置
    let plugin_config = PluginSystemConfig {
        plugin_dirs: vec![
            std::path::PathBuf::from("plugins"),
            std::path::PathBuf::from("examples/plugins"),
        ],
        enabled_plugins: vec!["enhanced_minecraft".to_string()],
        signature_verification: false, // 演示时关闭签名验证
        sandbox_config: SandboxConfig {
            enabled: true,
            allow_file_write: false,
            allow_network: false,
            ..Default::default()
        },
        ..Default::default()
    };

    // 创建插件管理器
    let mut plugin_manager = PluginManager::new(plugin_config)?;

    // 初始化插件系统
    plugin_manager.initialize().await?;

    // 演示文件提取
    let test_file = std::path::Path::new("test_mod.jar");
    if test_file.exists() {
        println!("📦 测试文件: {:?}", test_file);

        // 查找支持的提取器
        let extractors = plugin_manager.get_extractors_for_format("jar");
        println!("🔍 找到 {} 个支持jar格式的提取器", extractors.len());

        for extractor_id in extractors {
            println!("🔄 使用提取器: {}", extractor_id);
            
            match plugin_manager.extract_file(&extractor_id, test_file).await {
                Ok(result) => {
                    println!("✅ 提取成功:");
                    println!("  - 文件类型: {}", result.file_type);
                    println!("  - 语言文件数: {}", result.language_files.len());
                    println!("  - 总翻译条目: {}", result.stats.total_entries);
                    println!("  - 处理时间: {}ms", result.stats.processing_time_ms);
                }
                Err(e) => {
                    println!("❌ 提取失败: {}", e);
                }
            }
        }
    } else {
        println!("⚠️ 测试文件不存在: {:?}", test_file);
    }

    // 显示插件状态
    let plugins = plugin_manager.get_plugins();
    println!("\n📋 已加载插件:");
    for plugin in plugins {
        println!("  - {} v{} ({})", 
            plugin.metadata.name,
            plugin.metadata.version,
            match plugin.status {
                PluginStatus::Loaded => "已加载",
                PluginStatus::Active => "活跃",
                PluginStatus::Error(ref e) => &format!("错误: {}", e),
                _ => "其他",
            }
        );
    }

    // 关闭插件系统
    plugin_manager.shutdown().await?;

    println!("✅ 插件系统演示完成");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // 初始化日志
    env_logger::init();

    // 运行演示
    if let Err(e) = demo_plugin_system().await {
        eprintln!("❌ 演示失败: {}", e);
        std::process::exit(1);
    }

    Ok(())
}