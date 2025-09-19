// Rust-first插件系统 - 核心模块
// 支持dlopen动态加载和Python子进程插件

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use anyhow::{Result, anyhow};

pub mod extractor;
pub mod loader;
pub mod python_bridge;
pub mod sandbox;
pub mod registry;
pub mod integration;

pub use extractor::*;
pub use loader::*;
pub use python_bridge::*;
pub use sandbox::*;
pub use registry::*;
pub use integration::*;

/// 插件元数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginMetadata {
    pub id: String,
    pub name: String,
    pub version: String,
    pub author: String,
    pub description: String,
    pub plugin_type: PluginType,
    pub supported_formats: Vec<String>,
    pub uida_protocol_version: String,
    pub minimum_rust_version: Option<String>,
    pub dependencies: Vec<String>,
    pub capabilities: Vec<String>,
}

/// 插件类型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PluginType {
    /// 原生Rust插件 (动态链接库)
    Native,
    /// Python子进程插件
    Python,
    /// WebAssembly插件 (未来扩展)
    Wasm,
}

/// 插件状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PluginStatus {
    NotLoaded,
    Loading,
    Loaded,
    Active,
    Error(String),
    Disabled,
}

/// 插件信息
#[derive(Debug, Clone)]
pub struct PluginInfo {
    pub metadata: PluginMetadata,
    pub status: PluginStatus,
    pub path: PathBuf,
    pub loaded_at: Option<chrono::DateTime<chrono::Utc>>,
    pub last_used: Option<chrono::DateTime<chrono::Utc>>,
}

/// 插件系统配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginSystemConfig {
    /// 插件目录列表
    pub plugin_dirs: Vec<PathBuf>,
    /// 启用的插件ID列表 (白名单)
    pub enabled_plugins: Vec<String>,
    /// 禁用的插件ID列表 (黑名单)
    pub disabled_plugins: Vec<String>,
    /// 是否启用签名验证
    pub signature_verification: bool,
    /// 沙箱模式配置
    pub sandbox_config: SandboxConfig,
    /// Python环境配置
    pub python_config: PythonConfig,
    /// 热重载设置
    pub hot_reload: bool,
    /// 最大并发插件数
    pub max_concurrent_plugins: usize,
}

impl Default for PluginSystemConfig {
    fn default() -> Self {
        Self {
            plugin_dirs: vec![
                PathBuf::from("plugins"),
                PathBuf::from("plugins/native"),
                PathBuf::from("plugins/python"),
            ],
            enabled_plugins: vec![],
            disabled_plugins: vec![],
            signature_verification: true,
            sandbox_config: SandboxConfig::default(),
            python_config: PythonConfig::default(),
            hot_reload: true,
            max_concurrent_plugins: 8,
        }
    }
}

/// 插件管理器
pub struct PluginManager {
    config: PluginSystemConfig,
    plugins: Arc<Mutex<HashMap<String, PluginInfo>>>,
    extractors: Arc<Mutex<HashMap<String, Box<dyn Extractor + Send + Sync>>>>,
    python_bridge: Option<PythonBridge>,
    loader: PluginLoader,
    registry: PluginRegistry,
}

impl PluginManager {
    /// 创建新的插件管理器
    pub fn new(config: PluginSystemConfig) -> Result<Self> {
        let python_bridge = if config.python_config.enabled {
            Some(PythonBridge::new(config.python_config.clone())?)
        } else {
            None
        };

        let loader = PluginLoader::new(config.sandbox_config.clone())?;
        let registry = PluginRegistry::new(config.plugin_dirs.clone())?;

        Ok(Self {
            config,
            plugins: Arc::new(Mutex::new(HashMap::new())),
            extractors: Arc::new(Mutex::new(HashMap::new())),
            python_bridge,
            loader,
            registry,
        })
    }

    /// 初始化插件系统
    pub async fn initialize(&mut self) -> Result<()> {
        log::info!("🔌 初始化Rust-first插件系统");

        // 1. 扫描插件目录
        self.scan_plugins().await?;

        // 2. 加载启用的插件
        self.load_enabled_plugins().await?;

        // 3. 注册内置提取器
        self.register_builtin_extractors().await?;

        // 4. 初始化Python桥接
        if let Some(ref mut python_bridge) = self.python_bridge {
            python_bridge.initialize().await?;
        }

        log::info!("✅ 插件系统初始化完成");
        Ok(())
    }

    /// 扫描插件目录
    async fn scan_plugins(&mut self) -> Result<()> {
        log::info!("📂 扫描插件目录...");

        for plugin_dir in &self.config.plugin_dirs {
            if plugin_dir.exists() {
                self.registry.scan_directory(plugin_dir).await?;
            } else {
                log::warn!("插件目录不存在: {:?}", plugin_dir);
            }
        }

        let discovered = self.registry.get_discovered_plugins();
        log::info!("🔍 发现 {} 个插件", discovered.len());

        Ok(())
    }

    /// 加载启用的插件
    async fn load_enabled_plugins(&mut self) -> Result<()> {
        let discovered = self.registry.get_discovered_plugins();
        
        for metadata in discovered {
            // 检查是否在白名单中或不在黑名单中
            if self.should_load_plugin(&metadata.id) {
                if let Err(e) = self.load_plugin(&metadata.id).await {
                    log::error!("加载插件失败 {}: {}", metadata.id, e);
                }
            }
        }

        Ok(())
    }

    /// 检查是否应该加载插件
    fn should_load_plugin(&self, plugin_id: &str) -> bool {
        // 如果在禁用列表中，不加载
        if self.config.disabled_plugins.contains(&plugin_id.to_string()) {
            return false;
        }

        // 如果有启用列表且不为空，只加载列表中的插件
        if !self.config.enabled_plugins.is_empty() {
            return self.config.enabled_plugins.contains(&plugin_id.to_string());
        }

        // 默认加载所有非禁用插件
        true
    }

    /// 加载单个插件
    pub async fn load_plugin(&mut self, plugin_id: &str) -> Result<()> {
        log::info!("🔄 加载插件: {}", plugin_id);

        let metadata = self.registry.get_plugin_metadata(plugin_id)
            .ok_or_else(|| anyhow!("插件不存在: {}", plugin_id))?;

        let plugin_path = self.registry.get_plugin_path(plugin_id)
            .ok_or_else(|| anyhow!("插件路径不存在: {}", plugin_id))?;

        // 更新插件状态为加载中
        {
            let mut plugins = self.plugins.lock().unwrap();
            plugins.insert(plugin_id.to_string(), PluginInfo {
                metadata: metadata.clone(),
                status: PluginStatus::Loading,
                path: plugin_path.clone(),
                loaded_at: None,
                last_used: None,
            });
        }

        // 根据插件类型加载
        match metadata.plugin_type {
            PluginType::Native => {
                self.load_native_plugin(plugin_id, &plugin_path).await?;
            }
            PluginType::Python => {
                self.load_python_plugin(plugin_id, &plugin_path).await?;
            }
            PluginType::Wasm => {
                return Err(anyhow!("WebAssembly插件暂未支持"));
            }
        }

        // 更新插件状态为已加载
        {
            let mut plugins = self.plugins.lock().unwrap();
            if let Some(plugin_info) = plugins.get_mut(plugin_id) {
                plugin_info.status = PluginStatus::Loaded;
                plugin_info.loaded_at = Some(chrono::Utc::now());
            }
        }

        log::info!("✅ 插件加载成功: {}", plugin_id);
        Ok(())
    }

    /// 加载原生Rust插件
    async fn load_native_plugin(&mut self, plugin_id: &str, plugin_path: &Path) -> Result<()> {
        let extractor = self.loader.load_native_extractor(plugin_path).await?;
        
        let mut extractors = self.extractors.lock().unwrap();
        extractors.insert(plugin_id.to_string(), extractor);
        
        Ok(())
    }

    /// 加载Python插件
    async fn load_python_plugin(&mut self, plugin_id: &str, plugin_path: &Path) -> Result<()> {
        if let Some(ref mut python_bridge) = self.python_bridge {
            let extractor = python_bridge.load_python_extractor(plugin_id, plugin_path).await?;
            
            let mut extractors = self.extractors.lock().unwrap();
            extractors.insert(plugin_id.to_string(), extractor);
        } else {
            return Err(anyhow!("Python桥接未启用"));
        }
        
        Ok(())
    }

    /// 卸载插件
    pub async fn unload_plugin(&mut self, plugin_id: &str) -> Result<()> {
        log::info!("🔄 卸载插件: {}", plugin_id);

        // 从提取器集合中移除
        {
            let mut extractors = self.extractors.lock().unwrap();
            extractors.remove(plugin_id);
        }

        // 如果是Python插件，通知Python桥接卸载
        if let Some(ref mut python_bridge) = self.python_bridge {
            python_bridge.unload_plugin(plugin_id).await?;
        }

        // 更新插件状态
        {
            let mut plugins = self.plugins.lock().unwrap();
            if let Some(plugin_info) = plugins.get_mut(plugin_id) {
                plugin_info.status = PluginStatus::NotLoaded;
                plugin_info.loaded_at = None;
            }
        }

        log::info!("✅ 插件卸载成功: {}", plugin_id);
        Ok(())
    }

    /// 重新加载插件 (热重载)
    pub async fn reload_plugin(&mut self, plugin_id: &str) -> Result<()> {
        if !self.config.hot_reload {
            return Err(anyhow!("热重载功能未启用"));
        }

        log::info!("🔄 热重载插件: {}", plugin_id);

        // 先卸载
        self.unload_plugin(plugin_id).await?;

        // 重新扫描插件定义
        self.registry.rescan_plugin(plugin_id).await?;

        // 重新加载
        self.load_plugin(plugin_id).await?;

        Ok(())
    }

    /// 获取支持指定文件格式的提取器
    pub fn get_extractors_for_format(&self, format: &str) -> Vec<String> {
        let plugins = self.plugins.lock().unwrap();
        
        plugins.iter()
            .filter(|(_, info)| {
                matches!(info.status, PluginStatus::Loaded | PluginStatus::Active) &&
                info.metadata.supported_formats.iter().any(|f| f == format)
            })
            .map(|(id, _)| id.clone())
            .collect()
    }

    /// 执行文件提取
    pub async fn extract_file(&self, plugin_id: &str, file_path: &Path) -> Result<ExtractionResult> {
        let extractors = self.extractors.lock().unwrap();
        
        if let Some(extractor) = extractors.get(plugin_id) {
            // 更新最后使用时间
            {
                let mut plugins = self.plugins.lock().unwrap();
                if let Some(plugin_info) = plugins.get_mut(plugin_id) {
                    plugin_info.last_used = Some(chrono::Utc::now());
                    plugin_info.status = PluginStatus::Active;
                }
            }

            // 执行提取
            extractor.extract(file_path).await
        } else {
            Err(anyhow!("提取器不存在: {}", plugin_id))
        }
    }

    /// 注册内置提取器
    async fn register_builtin_extractors(&mut self) -> Result<()> {
        log::info!("📦 注册内置提取器...");

        // 注册Minecraft MOD提取器
        let minecraft_extractor = MinecraftModExtractor::new();
        self.register_extractor("builtin.minecraft_mod", Box::new(minecraft_extractor));

        // 注册资源包提取器
        let resourcepack_extractor = MinecraftResourcePackExtractor::new();
        self.register_extractor("builtin.minecraft_resourcepack", Box::new(resourcepack_extractor));

        log::info!("✅ 内置提取器注册完成");
        Ok(())
    }

    /// 注册提取器
    fn register_extractor(&self, id: &str, extractor: Box<dyn Extractor + Send + Sync>) {
        let mut extractors = self.extractors.lock().unwrap();
        extractors.insert(id.to_string(), extractor);
    }

    /// 获取插件列表
    pub fn get_plugins(&self) -> Vec<PluginInfo> {
        let plugins = self.plugins.lock().unwrap();
        plugins.values().cloned().collect()
    }

    /// 获取插件状态
    pub fn get_plugin_status(&self, plugin_id: &str) -> Option<PluginStatus> {
        let plugins = self.plugins.lock().unwrap();
        plugins.get(plugin_id).map(|info| info.status.clone())
    }

    /// 关闭插件系统
    pub async fn shutdown(&mut self) -> Result<()> {
        log::info!("🔌 关闭插件系统...");

        // 卸载所有插件
        let plugin_ids: Vec<String> = {
            let plugins = self.plugins.lock().unwrap();
            plugins.keys().cloned().collect()
        };

        for plugin_id in plugin_ids {
            if let Err(e) = self.unload_plugin(&plugin_id).await {
                log::error!("卸载插件失败 {}: {}", plugin_id, e);
            }
        }

        // 关闭Python桥接
        if let Some(ref mut python_bridge) = self.python_bridge {
            python_bridge.shutdown().await?;
        }

        log::info!("✅ 插件系统已关闭");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_plugin_manager_initialization() {
        let temp_dir = TempDir::new().unwrap();
        let config = PluginSystemConfig {
            plugin_dirs: vec![temp_dir.path().to_path_buf()],
            ..Default::default()
        };

        let mut manager = PluginManager::new(config).unwrap();
        assert!(manager.initialize().await.is_ok());
        assert!(manager.shutdown().await.is_ok());
    }

    #[test]
    fn test_plugin_metadata_serialization() {
        let metadata = PluginMetadata {
            id: "test.plugin".to_string(),
            name: "Test Plugin".to_string(),
            version: "1.0.0".to_string(),
            author: "Test Author".to_string(),
            description: "A test plugin".to_string(),
            plugin_type: PluginType::Native,
            supported_formats: vec!["jar".to_string(), "zip".to_string()],
            uida_protocol_version: "1.0".to_string(),
            minimum_rust_version: Some("1.70.0".to_string()),
            dependencies: vec![],
            capabilities: vec!["extract".to_string()],
        };

        let json = serde_json::to_string(&metadata).unwrap();
        let deserialized: PluginMetadata = serde_json::from_str(&json).unwrap();
        assert_eq!(metadata.id, deserialized.id);
    }
}