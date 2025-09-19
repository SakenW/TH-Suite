// 插件注册表和发现机制
// 负责插件的扫描、注册、版本管理和热重载

use std::path::{Path, PathBuf};
use std::collections::HashMap;
use std::fs;
use serde::{Deserialize, Serialize};
use anyhow::{Result, anyhow};
use crate::plugins::{PluginMetadata, PluginType};

/// 插件注册表
pub struct PluginRegistry {
    /// 插件目录列表
    plugin_dirs: Vec<PathBuf>,
    /// 已发现的插件
    discovered_plugins: HashMap<String, PluginRegistryEntry>,
    /// 插件依赖图
    dependency_graph: DependencyGraph,
}

/// 插件注册表条目
#[derive(Debug, Clone)]
pub struct PluginRegistryEntry {
    pub metadata: PluginMetadata,
    pub path: PathBuf,
    pub manifest_path: PathBuf,
    pub discovered_at: chrono::DateTime<chrono::Utc>,
    pub last_modified: chrono::DateTime<chrono::Utc>,
    pub hash: String,
    pub dependencies_resolved: bool,
}

/// 插件清单文件
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginManifest {
    pub plugin: PluginMetadata,
    /// 构建信息
    pub build: Option<BuildInfo>,
    /// 配置架构
    pub config_schema: Option<serde_json::Value>,
}

/// 构建信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildInfo {
    pub target: String,
    pub features: Vec<String>,
    pub build_time: String,
    pub git_commit: Option<String>,
    pub compiler_version: String,
}

/// 依赖图
pub struct DependencyGraph {
    /// 节点（插件ID -> 依赖列表）
    dependencies: HashMap<String, Vec<String>>,
    /// 反向依赖（插件ID -> 依赖它的插件列表）
    dependents: HashMap<String, Vec<String>>,
}

impl PluginRegistry {
    /// 创建新的插件注册表
    pub fn new(plugin_dirs: Vec<PathBuf>) -> Result<Self> {
        Ok(Self {
            plugin_dirs,
            discovered_plugins: HashMap::new(),
            dependency_graph: DependencyGraph::new(),
        })
    }

    /// 扫描目录发现插件
    pub async fn scan_directory(&mut self, dir: &Path) -> Result<()> {
        log::info!("🔍 扫描插件目录: {:?}", dir);

        if !dir.exists() {
            return Err(anyhow!("插件目录不存在: {:?}", dir));
        }

        let mut discovered_count = 0;

        // 递归扫描目录
        self.scan_directory_recursive(dir, &mut discovered_count).await?;

        log::info!("✅ 在目录 {:?} 中发现 {} 个插件", dir, discovered_count);
        Ok(())
    }

    /// 递归扫描目录
    async fn scan_directory_recursive(&mut self, dir: &Path, discovered_count: &mut usize) -> Result<()> {
        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_dir() {
                // 检查是否是插件目录（包含manifest文件）
                if self.is_plugin_directory(&path)? {
                    if let Ok(()) = self.register_plugin_from_directory(&path).await {
                        *discovered_count += 1;
                    }
                } else {
                    // 继续递归扫描子目录
                    self.scan_directory_recursive(&path, discovered_count).await?;
                }
            } else if self.is_plugin_file(&path) {
                // 单文件插件（如.dll, .so, .dylib）
                if let Ok(()) = self.register_plugin_from_file(&path).await {
                    *discovered_count += 1;
                }
            }
        }

        Ok(())
    }

    /// 检查是否是插件目录
    fn is_plugin_directory(&self, dir: &Path) -> Result<bool> {
        let manifest_files = [
            "plugin.toml",
            "plugin.json", 
            "manifest.toml",
            "manifest.json",
        ];

        for manifest_file in &manifest_files {
            if dir.join(manifest_file).exists() {
                return Ok(true);
            }
        }

        Ok(false)
    }

    /// 检查是否是插件文件
    fn is_plugin_file(&self, file: &Path) -> bool {
        if let Some(extension) = file.extension().and_then(|ext| ext.to_str()) {
            matches!(extension.to_lowercase().as_str(), "dll" | "so" | "dylib" | "py")
        } else {
            false
        }
    }

    /// 从目录注册插件
    async fn register_plugin_from_directory(&mut self, dir: &Path) -> Result<()> {
        log::debug!("📦 注册插件目录: {:?}", dir);

        // 查找清单文件
        let manifest_path = self.find_manifest_file(dir)?;
        
        // 解析清单文件
        let manifest = self.parse_manifest(&manifest_path)?;

        // 确定插件主文件路径
        let plugin_path = self.determine_plugin_path(dir, &manifest)?;

        // 计算文件哈希
        let hash = self.calculate_plugin_hash(&plugin_path)?;

        // 获取文件修改时间
        let metadata = fs::metadata(&plugin_path)?;
        let last_modified = metadata.modified()
            .map(|time| chrono::DateTime::from(time))
            .unwrap_or_else(|_| chrono::Utc::now());

        // 创建注册表条目
        let entry = PluginRegistryEntry {
            metadata: manifest.plugin,
            path: plugin_path,
            manifest_path,
            discovered_at: chrono::Utc::now(),
            last_modified,
            hash,
            dependencies_resolved: false,
        };

        // 检查是否已存在
        if let Some(existing) = self.discovered_plugins.get(&entry.metadata.id) {
            if existing.hash == entry.hash {
                log::debug!("插件已存在且未变更: {}", entry.metadata.id);
                return Ok(());
            }
            log::info!("🔄 更新插件: {}", entry.metadata.id);
        } else {
            log::info!("➕ 发现新插件: {} v{}", entry.metadata.name, entry.metadata.version);
        }

        // 注册插件
        self.discovered_plugins.insert(entry.metadata.id.clone(), entry);

        Ok(())
    }

    /// 从文件注册插件
    async fn register_plugin_from_file(&mut self, file: &Path) -> Result<()> {
        log::debug!("📄 注册插件文件: {:?}", file);

        // 对于单文件插件，尝试找到相邻的清单文件
        let manifest_path = self.find_adjacent_manifest(file)?;
        
        let manifest = if manifest_path.exists() {
            self.parse_manifest(&manifest_path)?
        } else {
            // 生成默认清单
            self.generate_default_manifest(file)?
        };

        // 计算文件哈希
        let hash = self.calculate_plugin_hash(file)?;

        // 获取文件修改时间
        let metadata = fs::metadata(file)?;
        let last_modified = metadata.modified()
            .map(|time| chrono::DateTime::from(time))
            .unwrap_or_else(|_| chrono::Utc::now());

        // 创建注册表条目
        let entry = PluginRegistryEntry {
            metadata: manifest.plugin,
            path: file.to_path_buf(),
            manifest_path,
            discovered_at: chrono::Utc::now(),
            last_modified,
            hash,
            dependencies_resolved: false,
        };

        log::info!("➕ 发现单文件插件: {} v{}", entry.metadata.name, entry.metadata.version);

        // 注册插件
        self.discovered_plugins.insert(entry.metadata.id.clone(), entry);

        Ok(())
    }

    /// 查找清单文件
    fn find_manifest_file(&self, dir: &Path) -> Result<PathBuf> {
        let manifest_files = [
            "plugin.toml",
            "plugin.json", 
            "manifest.toml",
            "manifest.json",
        ];

        for manifest_file in &manifest_files {
            let path = dir.join(manifest_file);
            if path.exists() {
                return Ok(path);
            }
        }

        Err(anyhow!("未找到清单文件在目录: {:?}", dir))
    }

    /// 查找相邻的清单文件
    fn find_adjacent_manifest(&self, file: &Path) -> Result<PathBuf> {
        if let Some(parent) = file.parent() {
            let file_stem = file.file_stem().and_then(|s| s.to_str()).unwrap_or("plugin");
            
            let manifest_files = [
                format!("{}.toml", file_stem),
                format!("{}.json", file_stem),
                "plugin.toml".to_string(),
                "plugin.json".to_string(),
            ];

            for manifest_file in &manifest_files {
                let path = parent.join(manifest_file);
                if path.exists() {
                    return Ok(path);
                }
            }
        }

        // 返回默认路径（即使不存在）
        Ok(file.with_extension("toml"))
    }

    /// 解析清单文件
    fn parse_manifest(&self, manifest_path: &Path) -> Result<PluginManifest> {
        let content = fs::read_to_string(manifest_path)?;
        
        let extension = manifest_path.extension()
            .and_then(|ext| ext.to_str())
            .unwrap_or("toml");

        match extension.to_lowercase().as_str() {
            "toml" => {
                toml::from_str(&content)
                    .map_err(|e| anyhow!("TOML解析错误: {}", e))
            }
            "json" => {
                serde_json::from_str(&content)
                    .map_err(|e| anyhow!("JSON解析错误: {}", e))
            }
            _ => Err(anyhow!("不支持的清单文件格式: {}", extension))
        }
    }

    /// 生成默认清单
    fn generate_default_manifest(&self, file: &Path) -> Result<PluginManifest> {
        let file_stem = file.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown");

        let plugin_type = if file.extension().and_then(|ext| ext.to_str()) == Some("py") {
            PluginType::Python
        } else {
            PluginType::Native
        };

        let supported_formats = match plugin_type {
            PluginType::Python => vec!["jar".to_string(), "zip".to_string(), "json".to_string()],
            PluginType::Native => vec!["jar".to_string(), "zip".to_string()],
            PluginType::Wasm => vec!["jar".to_string()],
        };

        let metadata = PluginMetadata {
            id: format!("auto.{}", file_stem.to_lowercase()),
            name: file_stem.to_string(),
            version: "1.0.0".to_string(),
            author: "Unknown".to_string(),
            description: format!("自动发现的插件: {}", file.display()),
            plugin_type,
            supported_formats,
            uida_protocol_version: "1.0".to_string(),
            minimum_rust_version: None,
            dependencies: vec![],
            capabilities: vec!["extract".to_string()],
        };

        Ok(PluginManifest {
            plugin: metadata,
            build: None,
            config_schema: None,
        })
    }

    /// 确定插件主文件路径
    fn determine_plugin_path(&self, dir: &Path, manifest: &PluginManifest) -> Result<PathBuf> {
        // 首先检查清单中是否指定了主文件
        // 这里简化处理，实际应该支持在清单中指定main字段

        match manifest.plugin.plugin_type {
            PluginType::Native => {
                // 查找动态库文件
                let extensions = if cfg!(target_os = "windows") {
                    vec!["dll"]
                } else if cfg!(target_os = "macos") {
                    vec!["dylib"]
                } else {
                    vec!["so"]
                };

                for extension in extensions {
                    for entry in fs::read_dir(dir)? {
                        let entry = entry?;
                        let path = entry.path();
                        if path.is_file() && 
                           path.extension().and_then(|ext| ext.to_str()) == Some(extension) {
                            return Ok(path);
                        }
                    }
                }

                Err(anyhow!("未找到原生库文件在目录: {:?}", dir))
            }
            PluginType::Python => {
                // 查找Python主文件
                let main_files = ["main.py", "plugin.py", "__init__.py"];
                
                for main_file in &main_files {
                    let path = dir.join(main_file);
                    if path.exists() {
                        return Ok(path);
                    }
                }

                Err(anyhow!("未找到Python主文件在目录: {:?}", dir))
            }
            PluginType::Wasm => {
                // 查找WebAssembly文件
                for entry in fs::read_dir(dir)? {
                    let entry = entry?;
                    let path = entry.path();
                    if path.is_file() && 
                       path.extension().and_then(|ext| ext.to_str()) == Some("wasm") {
                        return Ok(path);
                    }
                }

                Err(anyhow!("未找到WebAssembly文件在目录: {:?}", dir))
            }
        }
    }

    /// 计算插件哈希
    fn calculate_plugin_hash(&self, file: &Path) -> Result<String> {
        let content = fs::read(file)?;
        let hash = sha2::Sha256::digest(&content);
        Ok(format!("{:x}", hash))
    }

    /// 重新扫描单个插件
    pub async fn rescan_plugin(&mut self, plugin_id: &str) -> Result<()> {
        if let Some(entry) = self.discovered_plugins.get(plugin_id) {
            let manifest_dir = entry.manifest_path.parent()
                .ok_or_else(|| anyhow!("无法获取插件目录"))?;
            
            // 重新注册插件
            self.register_plugin_from_directory(manifest_dir).await?;
            
            log::info!("🔄 重新扫描插件: {}", plugin_id);
        } else {
            return Err(anyhow!("插件不存在: {}", plugin_id));
        }

        Ok(())
    }

    /// 解析依赖关系
    pub fn resolve_dependencies(&mut self) -> Result<()> {
        log::info!("🔗 解析插件依赖关系...");

        // 重置依赖图
        self.dependency_graph = DependencyGraph::new();

        // 构建依赖图
        for (plugin_id, entry) in &self.discovered_plugins {
            for dependency in &entry.metadata.dependencies {
                self.dependency_graph.add_dependency(plugin_id.clone(), dependency.clone());
            }
        }

        // 检查循环依赖
        if let Some(cycle) = self.dependency_graph.detect_cycles() {
            return Err(anyhow!("检测到循环依赖: {:?}", cycle));
        }

        // 标记所有插件为依赖已解析
        for entry in self.discovered_plugins.values_mut() {
            entry.dependencies_resolved = true;
        }

        log::info!("✅ 插件依赖关系解析完成");
        Ok(())
    }

    /// 获取加载顺序
    pub fn get_load_order(&self) -> Result<Vec<String>> {
        self.dependency_graph.topological_sort()
    }

    /// 获取已发现的插件列表
    pub fn get_discovered_plugins(&self) -> Vec<PluginMetadata> {
        self.discovered_plugins.values()
            .map(|entry| entry.metadata.clone())
            .collect()
    }

    /// 获取插件元数据
    pub fn get_plugin_metadata(&self, plugin_id: &str) -> Option<PluginMetadata> {
        self.discovered_plugins.get(plugin_id)
            .map(|entry| entry.metadata.clone())
    }

    /// 获取插件路径
    pub fn get_plugin_path(&self, plugin_id: &str) -> Option<PathBuf> {
        self.discovered_plugins.get(plugin_id)
            .map(|entry| entry.path.clone())
    }

    /// 检查插件是否有更新
    pub fn check_plugin_updates(&self, plugin_id: &str) -> Result<bool> {
        if let Some(entry) = self.discovered_plugins.get(plugin_id) {
            let current_hash = self.calculate_plugin_hash(&entry.path)?;
            Ok(current_hash != entry.hash)
        } else {
            Err(anyhow!("插件不存在: {}", plugin_id))
        }
    }

    /// 获取插件统计信息
    pub fn get_registry_stats(&self) -> RegistryStats {
        let mut stats = RegistryStats {
            total_plugins: self.discovered_plugins.len(),
            native_plugins: 0,
            python_plugins: 0,
            wasm_plugins: 0,
            plugins_with_dependencies: 0,
            total_dependencies: 0,
        };

        for entry in self.discovered_plugins.values() {
            match entry.metadata.plugin_type {
                PluginType::Native => stats.native_plugins += 1,
                PluginType::Python => stats.python_plugins += 1,
                PluginType::Wasm => stats.wasm_plugins += 1,
            }

            if !entry.metadata.dependencies.is_empty() {
                stats.plugins_with_dependencies += 1;
                stats.total_dependencies += entry.metadata.dependencies.len();
            }
        }

        stats
    }
}

/// 注册表统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegistryStats {
    pub total_plugins: usize,
    pub native_plugins: usize,
    pub python_plugins: usize,
    pub wasm_plugins: usize,
    pub plugins_with_dependencies: usize,
    pub total_dependencies: usize,
}

impl DependencyGraph {
    /// 创建新的依赖图
    pub fn new() -> Self {
        Self {
            dependencies: HashMap::new(),
            dependents: HashMap::new(),
        }
    }

    /// 添加依赖关系
    pub fn add_dependency(&mut self, plugin: String, dependency: String) {
        self.dependencies.entry(plugin.clone())
            .or_insert_with(Vec::new)
            .push(dependency.clone());
        
        self.dependents.entry(dependency)
            .or_insert_with(Vec::new)
            .push(plugin);
    }

    /// 检测循环依赖
    pub fn detect_cycles(&self) -> Option<Vec<String>> {
        let mut visited = HashMap::new();
        let mut rec_stack = HashMap::new();

        for plugin in self.dependencies.keys() {
            if self.has_cycle_dfs(plugin, &mut visited, &mut rec_stack) {
                // 重构路径
                let mut cycle = Vec::new();
                let mut current = plugin;
                loop {
                    cycle.push(current.clone());
                    if let Some(deps) = self.dependencies.get(current) {
                        if let Some(next) = deps.iter().find(|dep| rec_stack.get(*dep) == Some(&true)) {
                            if next == plugin {
                                cycle.push(next.clone());
                                break;
                            }
                            current = next;
                        } else {
                            break;
                        }
                    } else {
                        break;
                    }
                }
                return Some(cycle);
            }
        }

        None
    }

    /// DFS检测循环
    fn has_cycle_dfs(
        &self,
        plugin: &str,
        visited: &mut HashMap<String, bool>,
        rec_stack: &mut HashMap<String, bool>,
    ) -> bool {
        visited.insert(plugin.to_string(), true);
        rec_stack.insert(plugin.to_string(), true);

        if let Some(deps) = self.dependencies.get(plugin) {
            for dep in deps {
                if !visited.get(dep).unwrap_or(&false) {
                    if self.has_cycle_dfs(dep, visited, rec_stack) {
                        return true;
                    }
                } else if rec_stack.get(dep).unwrap_or(&false) {
                    return true;
                }
            }
        }

        rec_stack.insert(plugin.to_string(), false);
        false
    }

    /// 拓扑排序
    pub fn topological_sort(&self) -> Result<Vec<String>> {
        let mut in_degree: HashMap<String, usize> = HashMap::new();
        let mut queue = Vec::new();
        let mut result = Vec::new();

        // 计算入度
        for plugin in self.dependencies.keys() {
            in_degree.insert(plugin.clone(), 0);
        }

        for deps in self.dependencies.values() {
            for dep in deps {
                *in_degree.entry(dep.clone()).or_insert(0) += 1;
            }
        }

        // 找到所有入度为0的节点
        for (plugin, degree) in &in_degree {
            if *degree == 0 {
                queue.push(plugin.clone());
            }
        }

        // 拓扑排序
        while let Some(plugin) = queue.pop() {
            result.push(plugin.clone());

            if let Some(deps) = self.dependencies.get(&plugin) {
                for dep in deps {
                    if let Some(degree) = in_degree.get_mut(dep) {
                        *degree -= 1;
                        if *degree == 0 {
                            queue.push(dep.clone());
                        }
                    }
                }
            }
        }

        // 检查是否所有节点都被处理
        if result.len() != in_degree.len() {
            return Err(anyhow!("依赖图中存在循环依赖"));
        }

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    #[test]
    fn test_dependency_graph() {
        let mut graph = DependencyGraph::new();
        
        graph.add_dependency("A".to_string(), "B".to_string());
        graph.add_dependency("B".to_string(), "C".to_string());
        graph.add_dependency("D".to_string(), "B".to_string());

        // 正常的拓扑排序
        let order = graph.topological_sort().unwrap();
        let c_pos = order.iter().position(|x| x == "C").unwrap();
        let b_pos = order.iter().position(|x| x == "B").unwrap();
        let a_pos = order.iter().position(|x| x == "A").unwrap();
        
        assert!(c_pos < b_pos);
        assert!(b_pos < a_pos);
    }

    #[test]
    fn test_cycle_detection() {
        let mut graph = DependencyGraph::new();
        
        graph.add_dependency("A".to_string(), "B".to_string());
        graph.add_dependency("B".to_string(), "C".to_string());
        graph.add_dependency("C".to_string(), "A".to_string()); // 循环

        assert!(graph.detect_cycles().is_some());
    }

    #[tokio::test]
    async fn test_plugin_registry() {
        let temp_dir = TempDir::new().unwrap();
        let mut registry = PluginRegistry::new(vec![temp_dir.path().to_path_buf()]).unwrap();

        // 创建一个模拟插件
        let plugin_dir = temp_dir.path().join("test_plugin");
        fs::create_dir_all(&plugin_dir).unwrap();

        let manifest_content = r#"
[plugin]
id = "test.plugin"
name = "Test Plugin"
version = "1.0.0"
author = "Test"
description = "A test plugin"
plugin_type = "Native"
supported_formats = ["jar", "zip"]
uida_protocol_version = "1.0"
dependencies = []
capabilities = ["extract"]
"#;
        fs::write(plugin_dir.join("plugin.toml"), manifest_content).unwrap();

        // 创建一个模拟的动态库文件
        fs::write(plugin_dir.join("libtest.so"), "fake library content").unwrap();

        // 扫描目录
        assert!(registry.scan_directory(&temp_dir.path()).await.is_ok());

        // 验证插件被发现
        let discovered = registry.get_discovered_plugins();
        assert_eq!(discovered.len(), 1);
        assert_eq!(discovered[0].id, "test.plugin");
    }
}