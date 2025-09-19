// 插件动态加载器
// 支持dlopen方式加载原生Rust插件

use std::path::Path;
use std::ffi::OsStr;
use std::collections::HashMap;
use anyhow::{Result, anyhow};
use libloading::{Library, Symbol};
use crate::plugins::{Extractor, SandboxConfig};

/// 插件加载器
pub struct PluginLoader {
    /// 已加载的动态库
    loaded_libraries: HashMap<String, Library>,
    /// 沙箱配置
    sandbox_config: SandboxConfig,
}

/// 插件入口点函数签名
/// 每个插件动态库必须导出这个函数
pub type PluginEntryPoint = extern "C" fn() -> *mut dyn Extractor;

/// 插件创建函数签名
pub type CreateExtractorFn = extern "C" fn() -> Box<dyn Extractor + Send + Sync>;

/// 插件释放函数签名
pub type DestroyExtractorFn = extern "C" fn(extractor: *mut dyn Extractor);

impl PluginLoader {
    /// 创建新的插件加载器
    pub fn new(sandbox_config: SandboxConfig) -> Result<Self> {
        Ok(Self {
            loaded_libraries: HashMap::new(),
            sandbox_config,
        })
    }

    /// 加载原生Rust插件
    pub async fn load_native_extractor(&mut self, plugin_path: &Path) -> Result<Box<dyn Extractor + Send + Sync>> {
        log::info!("🔗 加载原生插件: {:?}", plugin_path);

        // 验证文件存在和权限
        self.validate_plugin_file(plugin_path)?;

        // 加载动态库
        let library = unsafe {
            Library::new(plugin_path)
                .map_err(|e| anyhow!("无法加载动态库 {:?}: {}", plugin_path, e))?
        };

        // 获取插件创建函数
        let create_extractor: Symbol<CreateExtractorFn> = unsafe {
            library.get(b"create_extractor")
                .map_err(|e| anyhow!("插件缺少create_extractor函数: {}", e))?
        };

        // 创建提取器实例
        let extractor = create_extractor();

        // 验证提取器
        self.validate_extractor(&*extractor).await?;

        // 存储库引用以防卸载
        let plugin_id = plugin_path.file_stem()
            .and_then(|name| name.to_str())
            .unwrap_or("unknown")
            .to_string();
        
        self.loaded_libraries.insert(plugin_id, library);

        log::info!("✅ 原生插件加载成功: {:?}", plugin_path);
        Ok(extractor)
    }

    /// 卸载插件
    pub fn unload_plugin(&mut self, plugin_id: &str) -> Result<()> {
        if let Some(_library) = self.loaded_libraries.remove(plugin_id) {
            log::info!("🗑️ 卸载插件: {}", plugin_id);
            // library会在被drop时自动卸载
        }
        Ok(())
    }

    /// 验证插件文件
    fn validate_plugin_file(&self, plugin_path: &Path) -> Result<()> {
        // 检查文件存在
        if !plugin_path.exists() {
            return Err(anyhow!("插件文件不存在: {:?}", plugin_path));
        }

        // 检查文件扩展名
        let extension = plugin_path.extension().and_then(OsStr::to_str);
        let valid_extensions = if cfg!(target_os = "windows") {
            vec!["dll"]
        } else if cfg!(target_os = "macos") {
            vec!["dylib"]
        } else {
            vec!["so"]
        };

        if !extension.map_or(false, |ext| valid_extensions.contains(&ext)) {
            return Err(anyhow!("无效的插件文件扩展名: {:?}", extension));
        }

        // 检查文件权限
        let metadata = std::fs::metadata(plugin_path)?;
        if metadata.len() == 0 {
            return Err(anyhow!("插件文件为空: {:?}", plugin_path));
        }

        // 沙箱检查
        if self.sandbox_config.enabled {
            self.validate_plugin_sandbox(plugin_path)?;
        }

        Ok(())
    }

    /// 验证插件沙箱限制
    fn validate_plugin_sandbox(&self, plugin_path: &Path) -> Result<()> {
        // 检查路径白名单
        if !self.sandbox_config.allowed_paths.is_empty() {
            let allowed = self.sandbox_config.allowed_paths.iter()
                .any(|allowed_path| plugin_path.starts_with(allowed_path));
            
            if !allowed {
                return Err(anyhow!("插件路径不在白名单中: {:?}", plugin_path));
            }
        }

        // 检查签名 (如果启用)
        if self.sandbox_config.signature_verification {
            self.verify_plugin_signature(plugin_path)?;
        }

        Ok(())
    }

    /// 验证插件签名
    fn verify_plugin_signature(&self, plugin_path: &Path) -> Result<()> {
        // TODO: 实现插件签名验证
        // 这里应该检查插件的数字签名
        
        log::debug!("验证插件签名: {:?}", plugin_path);
        
        // 暂时跳过签名验证
        if self.sandbox_config.allow_unsigned {
            log::warn!("跳过插件签名验证 (allow_unsigned=true): {:?}", plugin_path);
            return Ok(());
        }

        // 在实际实现中，这里应该：
        // 1. 读取插件的签名信息
        // 2. 验证签名的有效性
        // 3. 检查签名是否来自可信的证书
        
        Err(anyhow!("插件签名验证功能尚未实现"))
    }

    /// 验证提取器接口
    async fn validate_extractor(&self, extractor: &dyn Extractor) -> Result<()> {
        // 检查提取器信息
        let info = extractor.get_info();
        if info.name.is_empty() {
            return Err(anyhow!("提取器名称不能为空"));
        }

        // 检查支持的扩展名
        let extensions = extractor.supported_extensions();
        if extensions.is_empty() {
            return Err(anyhow!("提取器必须支持至少一种文件扩展名"));
        }

        // 检查UIDA协议版本
        let uida_version = extractor.uida_protocol_version();
        if !self.is_supported_uida_version(&uida_version) {
            return Err(anyhow!("不支持的UIDA协议版本: {}", uida_version));
        }

        log::debug!("✅ 提取器验证通过: {}", info.name);
        Ok(())
    }

    /// 检查UIDA协议版本是否支持
    fn is_supported_uida_version(&self, version: &str) -> bool {
        // 支持的UIDA协议版本列表
        let supported_versions = vec!["1.0", "1.1", "2.0"];
        supported_versions.contains(&version)
    }

    /// 获取已加载的插件数量
    pub fn loaded_plugin_count(&self) -> usize {
        self.loaded_libraries.len()
    }

    /// 获取已加载的插件ID列表
    pub fn loaded_plugin_ids(&self) -> Vec<String> {
        self.loaded_libraries.keys().cloned().collect()
    }

    /// 检查插件是否已加载
    pub fn is_plugin_loaded(&self, plugin_id: &str) -> bool {
        self.loaded_libraries.contains_key(plugin_id)
    }

    /// 卸载所有插件
    pub fn unload_all(&mut self) {
        log::info!("🗑️ 卸载所有插件...");
        self.loaded_libraries.clear();
        log::info!("✅ 所有插件已卸载");
    }
}

impl Drop for PluginLoader {
    fn drop(&mut self) {
        self.unload_all();
    }
}

/// 插件构建辅助宏
/// 用于在插件动态库中导出标准接口
#[macro_export]
macro_rules! export_plugin {
    ($extractor_type:ty) => {
        #[no_mangle]
        pub extern "C" fn create_extractor() -> Box<dyn $crate::plugins::Extractor + Send + Sync> {
            Box::new(<$extractor_type>::new())
        }

        #[no_mangle]
        pub extern "C" fn destroy_extractor(_extractor: *mut dyn $crate::plugins::Extractor) {
            // 由Box自动释放
        }

        #[no_mangle]
        pub extern "C" fn plugin_api_version() -> *const std::os::raw::c_char {
            b"1.0\0".as_ptr() as *const std::os::raw::c_char
        }
    };
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    #[test]
    fn test_plugin_loader_creation() {
        let sandbox_config = SandboxConfig::default();
        let loader = PluginLoader::new(sandbox_config);
        assert!(loader.is_ok());
    }

    #[test]
    fn test_validate_plugin_file_not_exists() {
        let sandbox_config = SandboxConfig::default();
        let loader = PluginLoader::new(sandbox_config).unwrap();
        
        let non_existent_path = Path::new("non_existent_plugin.so");
        let result = loader.validate_plugin_file(non_existent_path);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("插件文件不存在"));
    }

    #[test]
    fn test_validate_plugin_file_empty() {
        let sandbox_config = SandboxConfig::default();
        let loader = PluginLoader::new(sandbox_config).unwrap();
        
        let temp_dir = TempDir::new().unwrap();
        let plugin_path = temp_dir.path().join("empty_plugin.so");
        fs::write(&plugin_path, "").unwrap();
        
        let result = loader.validate_plugin_file(&plugin_path);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("插件文件为空"));
    }

    #[test]
    fn test_uida_version_support() {
        let sandbox_config = SandboxConfig::default();
        let loader = PluginLoader::new(sandbox_config).unwrap();
        
        assert!(loader.is_supported_uida_version("1.0"));
        assert!(loader.is_supported_uida_version("1.1"));
        assert!(loader.is_supported_uida_version("2.0"));
        assert!(!loader.is_supported_uida_version("3.0"));
        assert!(!loader.is_supported_uida_version("invalid"));
    }

    #[test]
    fn test_plugin_id_management() {
        let sandbox_config = SandboxConfig::default();
        let mut loader = PluginLoader::new(sandbox_config).unwrap();
        
        assert_eq!(loader.loaded_plugin_count(), 0);
        assert!(loader.loaded_plugin_ids().is_empty());
        assert!(!loader.is_plugin_loaded("test_plugin"));
    }
}