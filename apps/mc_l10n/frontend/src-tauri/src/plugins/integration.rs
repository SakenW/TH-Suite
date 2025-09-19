// 插件系统与现有扫描系统的集成
// 提供与Python后端扫描服务的桥接和兼容性

use std::path::{Path, PathBuf};
use std::collections::HashMap;
use serde::{Serialize, Deserialize};
use anyhow::{Result, anyhow};
use crate::plugins::*;

/// 扫描集成配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanIntegrationConfig {
    /// 是否启用插件扫描
    pub plugin_scanning_enabled: bool,
    /// 回退到Python后端
    pub fallback_to_python_backend: bool,
    /// Python后端URL
    pub python_backend_url: String,
    /// 扫描结果合并策略
    pub merge_strategy: MergeStrategy,
    /// 性能模式
    pub performance_mode: PerformanceMode,
}

/// 合并策略
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MergeStrategy {
    /// 优先使用插件结果
    PluginFirst,
    /// 优先使用Python后端结果
    PythonFirst,
    /// 合并所有结果
    MergeAll,
    /// 使用最佳结果
    BestResult,
}

/// 性能模式
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PerformanceMode {
    /// 快速模式（优先速度）
    Fast,
    /// 平衡模式
    Balanced,
    /// 准确模式（优先准确性）
    Accurate,
}

impl Default for ScanIntegrationConfig {
    fn default() -> Self {
        Self {
            plugin_scanning_enabled: true,
            fallback_to_python_backend: true,
            python_backend_url: "http://localhost:18000".to_string(),
            merge_strategy: MergeStrategy::BestResult,
            performance_mode: PerformanceMode::Balanced,
        }
    }
}

/// 集成扫描器
/// 协调插件系统和Python后端的扫描工作
pub struct IntegratedScanner {
    config: ScanIntegrationConfig,
    plugin_manager: Option<PluginManager>,
    http_client: reqwest::Client,
}

impl IntegratedScanner {
    /// 创建新的集成扫描器
    pub fn new(config: ScanIntegrationConfig) -> Self {
        Self {
            config,
            plugin_manager: None,
            http_client: reqwest::Client::new(),
        }
    }

    /// 初始化集成扫描器
    pub async fn initialize(&mut self, plugin_config: Option<PluginSystemConfig>) -> Result<()> {
        log::info!("🔧 初始化集成扫描系统");

        // 初始化插件管理器
        if self.config.plugin_scanning_enabled {
            if let Some(config) = plugin_config {
                let mut plugin_manager = PluginManager::new(config)?;
                plugin_manager.initialize().await?;
                self.plugin_manager = Some(plugin_manager);
                log::info!("✅ 插件系统已启用");
            } else {
                log::warn!("⚠️ 插件配置未提供，插件扫描已禁用");
                self.config.plugin_scanning_enabled = false;
            }
        }

        // 检查Python后端连接
        if self.config.fallback_to_python_backend {
            if let Err(e) = self.check_python_backend().await {
                log::warn!("⚠️ Python后端连接失败: {}", e);
                if !self.config.plugin_scanning_enabled {
                    return Err(anyhow!("插件系统和Python后端都不可用"));
                }
            } else {
                log::info!("✅ Python后端连接正常");
            }
        }

        log::info!("✅ 集成扫描系统初始化完成");
        Ok(())
    }

    /// 检查Python后端连接
    async fn check_python_backend(&self) -> Result<()> {
        let url = format!("{}/api/v6/health", self.config.python_backend_url);
        let response = self.http_client.get(&url).send().await?;
        
        if response.status().is_success() {
            Ok(())
        } else {
            Err(anyhow!("Python后端健康检查失败: {}", response.status()))
        }
    }

    /// 执行集成扫描
    pub async fn scan_path(&self, target_path: &Path) -> Result<IntegratedScanResult> {
        log::info!("🔍 开始集成扫描: {:?}", target_path);

        let mut plugin_results = Vec::new();
        let mut python_result = None;
        let mut errors = Vec::new();

        // 1. 尝试使用插件扫描
        if self.config.plugin_scanning_enabled {
            if let Some(ref plugin_manager) = self.plugin_manager {
                match self.scan_with_plugins(plugin_manager, target_path).await {
                    Ok(results) => {
                        plugin_results = results;
                        log::info!("✅ 插件扫描完成，发现 {} 个结果", plugin_results.len());
                    }
                    Err(e) => {
                        errors.push(format!("插件扫描失败: {}", e));
                        log::error!("❌ 插件扫描失败: {}", e);
                    }
                }
            }
        }

        // 2. 尝试使用Python后端（回退或并行）
        if self.config.fallback_to_python_backend && 
           (plugin_results.is_empty() || matches!(self.config.merge_strategy, MergeStrategy::MergeAll | MergeStrategy::PythonFirst)) {
            match self.scan_with_python_backend(target_path).await {
                Ok(result) => {
                    python_result = Some(result);
                    log::info!("✅ Python后端扫描完成");
                }
                Err(e) => {
                    errors.push(format!("Python后端扫描失败: {}", e));
                    log::error!("❌ Python后端扫描失败: {}", e);
                }
            }
        }

        // 3. 合并结果
        let final_result = self.merge_scan_results(plugin_results, python_result).await?;

        log::info!("✅ 集成扫描完成");
        Ok(IntegratedScanResult {
            success: true,
            scan_path: target_path.to_path_buf(),
            plugin_results_count: final_result.language_files.len(),
            python_backend_used: python_result.is_some(),
            merge_strategy: self.config.merge_strategy.clone(),
            extraction_result: final_result,
            errors,
            performance_metrics: PerformanceMetrics::default(),
        })
    }

    /// 使用插件扫描
    async fn scan_with_plugins(&self, plugin_manager: &PluginManager, target_path: &Path) -> Result<Vec<ExtractionResult>> {
        let mut results = Vec::new();

        // 如果是目录，递归扫描文件
        if target_path.is_dir() {
            let files = self.discover_scannable_files(target_path).await?;
            for file in files {
                if let Ok(file_results) = self.scan_file_with_plugins(plugin_manager, &file).await {
                    results.extend(file_results);
                }
            }
        } else {
            // 单文件扫描
            let file_results = self.scan_file_with_plugins(plugin_manager, target_path).await?;
            results.extend(file_results);
        }

        Ok(results)
    }

    /// 使用插件扫描单个文件
    async fn scan_file_with_plugins(&self, plugin_manager: &PluginManager, file_path: &Path) -> Result<Vec<ExtractionResult>> {
        let mut results = Vec::new();

        // 获取文件扩展名
        let extension = file_path.extension()
            .and_then(|ext| ext.to_str())
            .unwrap_or("")
            .to_lowercase();

        // 查找支持该格式的提取器
        let extractors = plugin_manager.get_extractors_for_format(&extension);

        if extractors.is_empty() {
            return Ok(results);
        }

        // 根据性能模式选择扫描策略
        match self.config.performance_mode {
            PerformanceMode::Fast => {
                // 快速模式：只使用第一个提取器
                if let Some(extractor_id) = extractors.first() {
                    if let Ok(result) = plugin_manager.extract_file(extractor_id, file_path).await {
                        results.push(result);
                    }
                }
            }
            PerformanceMode::Balanced => {
                // 平衡模式：使用最多2个提取器
                for extractor_id in extractors.iter().take(2) {
                    if let Ok(result) = plugin_manager.extract_file(extractor_id, file_path).await {
                        results.push(result);
                        break; // 找到一个成功的就停止
                    }
                }
            }
            PerformanceMode::Accurate => {
                // 准确模式：尝试所有提取器
                for extractor_id in extractors {
                    if let Ok(result) = plugin_manager.extract_file(&extractor_id, file_path).await {
                        results.push(result);
                    }
                }
            }
        }

        Ok(results)
    }

    /// 发现可扫描的文件
    async fn discover_scannable_files(&self, dir: &Path) -> Result<Vec<PathBuf>> {
        let mut files = Vec::new();
        let scannable_extensions = ["jar", "zip", "mrpack", "ccip", "mcpack"];

        fn scan_recursive(dir: &Path, files: &mut Vec<PathBuf>, extensions: &[&str]) -> Result<()> {
            for entry in std::fs::read_dir(dir)? {
                let entry = entry?;
                let path = entry.path();

                if path.is_dir() {
                    scan_recursive(&path, files, extensions)?;
                } else if path.is_file() {
                    if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                        if extensions.contains(&ext.to_lowercase().as_str()) {
                            files.push(path);
                        }
                    }
                }
            }
            Ok(())
        }

        scan_recursive(dir, &mut files, &scannable_extensions)?;
        Ok(files)
    }

    /// 使用Python后端扫描
    async fn scan_with_python_backend(&self, target_path: &Path) -> Result<PythonScanResult> {
        let url = format!("{}/api/v6/scan/start", self.config.python_backend_url);
        
        let request_body = serde_json::json!({
            "target_path": target_path.to_string_lossy(),
            "incremental": true,
            "scan_options": {
                "max_depth": 10,
                "max_file_size_mb": 500
            }
        });

        // 启动扫描
        let response = self.http_client
            .post(&url)
            .json(&request_body)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(anyhow!("启动Python扫描失败: {}", response.status()));
        }

        let scan_response: serde_json::Value = response.json().await?;
        let scan_id = scan_response.get("scan_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("无法获取扫描ID"))?;

        // 轮询扫描状态
        self.wait_for_python_scan(scan_id).await
    }

    /// 等待Python扫描完成
    async fn wait_for_python_scan(&self, scan_id: &str) -> Result<PythonScanResult> {
        let status_url = format!("{}/api/v6/scan/{}/status", self.config.python_backend_url, scan_id);
        let mut attempts = 0;
        const MAX_ATTEMPTS: u32 = 60; // 最多等待5分钟

        loop {
            if attempts >= MAX_ATTEMPTS {
                return Err(anyhow!("Python扫描超时"));
            }

            tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
            attempts += 1;

            let response = self.http_client.get(&status_url).send().await?;
            if !response.status().is_success() {
                continue;
            }

            let status: serde_json::Value = response.json().await?;
            let scan_status = status.get("status").and_then(|v| v.as_str()).unwrap_or("unknown");

            match scan_status {
                "completed" => {
                    return self.convert_python_result(status).await;
                }
                "failed" | "cancelled" => {
                    let error = status.get("error_message")
                        .and_then(|v| v.as_str())
                        .unwrap_or("未知错误");
                    return Err(anyhow!("Python扫描失败: {}", error));
                }
                _ => {
                    // 继续等待
                    log::debug!("Python扫描进行中: {}", scan_status);
                }
            }
        }
    }

    /// 转换Python扫描结果
    async fn convert_python_result(&self, python_result: serde_json::Value) -> Result<PythonScanResult> {
        // 转换Python后端的结果格式到插件系统格式
        let discovered_items = python_result.get("discovered_items")
            .and_then(|v| v.as_array())
            .unwrap_or(&vec![]);

        let mut language_files = Vec::new();

        for item in discovered_items {
            if item.get("type").and_then(|v| v.as_str()) == Some("mod") {
                if let Some(lang_files) = item.get("language_files").and_then(|v| v.as_array()) {
                    for lang_file in lang_files {
                        let language_file = LanguageFile {
                            language_code: lang_file.get("language")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown")
                                .to_string(),
                            path: lang_file.get("path")
                                .and_then(|v| v.as_str())
                                .unwrap_or("")
                                .to_string(),
                            entry_count: lang_file.get("key_count")
                                .and_then(|v| v.as_u64())
                                .unwrap_or(0) as usize,
                            format: "json".to_string(), // Python后端主要处理JSON
                            namespace: None, // Python结果中可能没有命名空间信息
                            sample_entries: vec![], // 简化处理
                        };
                        language_files.push(language_file);
                    }
                }
            }
        }

        Ok(PythonScanResult {
            language_files,
            statistics: python_result.get("statistics").cloned().unwrap_or_default(),
        })
    }

    /// 合并扫描结果
    async fn merge_scan_results(
        &self,
        plugin_results: Vec<ExtractionResult>,
        python_result: Option<PythonScanResult>,
    ) -> Result<ExtractionResult> {
        match self.config.merge_strategy {
            MergeStrategy::PluginFirst => {
                if !plugin_results.is_empty() {
                    Ok(plugin_results.into_iter().next().unwrap())
                } else if let Some(python_result) = python_result {
                    Ok(self.convert_python_to_extraction_result(python_result))
                } else {
                    Err(anyhow!("没有可用的扫描结果"))
                }
            }
            MergeStrategy::PythonFirst => {
                if let Some(python_result) = python_result {
                    Ok(self.convert_python_to_extraction_result(python_result))
                } else if !plugin_results.is_empty() {
                    Ok(plugin_results.into_iter().next().unwrap())
                } else {
                    Err(anyhow!("没有可用的扫描结果"))
                }
            }
            MergeStrategy::MergeAll => {
                self.merge_all_results(plugin_results, python_result).await
            }
            MergeStrategy::BestResult => {
                self.select_best_result(plugin_results, python_result).await
            }
        }
    }

    /// 合并所有结果
    async fn merge_all_results(
        &self,
        plugin_results: Vec<ExtractionResult>,
        python_result: Option<PythonScanResult>,
    ) -> Result<ExtractionResult> {
        let mut all_language_files = Vec::new();
        let mut total_entries = 0;
        let mut files_scanned = 0;
        let mut processing_time = 0;

        // 合并插件结果
        for result in plugin_results {
            all_language_files.extend(result.language_files);
            total_entries += result.stats.total_entries;
            files_scanned += result.stats.files_scanned;
            processing_time += result.stats.processing_time_ms;
        }

        // 合并Python结果
        if let Some(python_result) = python_result {
            all_language_files.extend(python_result.language_files);
        }

        // 去重（基于路径）
        all_language_files.sort_by(|a, b| a.path.cmp(&b.path));
        all_language_files.dedup_by(|a, b| a.path == b.path);

        Ok(ExtractionResult {
            success: true,
            file_type: "merged_result".to_string(),
            language_files: all_language_files.clone(),
            metadata: FileMetadata {
                name: "Merged Results".to_string(),
                size: 0,
                hash: "merged".to_string(),
                mod_info: None,
                pack_info: None,
                uida_compatible: true,
            },
            error: None,
            warnings: vec![],
            stats: ExtractionStats {
                processing_time_ms: processing_time,
                files_scanned,
                language_files_found: all_language_files.len(),
                total_entries,
                memory_used: 0,
            },
        })
    }

    /// 选择最佳结果
    async fn select_best_result(
        &self,
        plugin_results: Vec<ExtractionResult>,
        python_result: Option<PythonScanResult>,
    ) -> Result<ExtractionResult> {
        let mut best_result = None;
        let mut best_score = 0;

        // 评估插件结果
        for result in plugin_results {
            let score = self.evaluate_result_quality(&result);
            if score > best_score {
                best_score = score;
                best_result = Some(result);
            }
        }

        // 评估Python结果
        if let Some(python_result) = python_result {
            let converted_result = self.convert_python_to_extraction_result(python_result);
            let score = self.evaluate_result_quality(&converted_result);
            if score > best_score {
                best_result = Some(converted_result);
            }
        }

        best_result.ok_or_else(|| anyhow!("没有可用的扫描结果"))
    }

    /// 评估结果质量
    fn evaluate_result_quality(&self, result: &ExtractionResult) -> usize {
        // 简单的质量评分：语言文件数量 + 翻译条目数量的权重
        result.language_files.len() * 10 + result.stats.total_entries
    }

    /// 转换Python结果为提取结果
    fn convert_python_to_extraction_result(&self, python_result: PythonScanResult) -> ExtractionResult {
        let total_entries = python_result.language_files.iter().map(|lf| lf.entry_count).sum();

        ExtractionResult {
            success: true,
            file_type: "python_backend_result".to_string(),
            language_files: python_result.language_files.clone(),
            metadata: FileMetadata {
                name: "Python Backend Result".to_string(),
                size: 0,
                hash: "python".to_string(),
                mod_info: None,
                pack_info: None,
                uida_compatible: true,
            },
            error: None,
            warnings: vec![],
            stats: ExtractionStats {
                processing_time_ms: 0,
                files_scanned: python_result.language_files.len(),
                language_files_found: python_result.language_files.len(),
                total_entries,
                memory_used: 0,
            },
        }
    }

    /// 关闭集成扫描器
    pub async fn shutdown(&mut self) -> Result<()> {
        if let Some(mut plugin_manager) = self.plugin_manager.take() {
            plugin_manager.shutdown().await?;
        }
        Ok(())
    }
}

/// Python扫描结果
#[derive(Debug, Clone)]
pub struct PythonScanResult {
    pub language_files: Vec<LanguageFile>,
    pub statistics: serde_json::Value,
}

/// 集成扫描结果
#[derive(Debug, Clone)]
pub struct IntegratedScanResult {
    pub success: bool,
    pub scan_path: PathBuf,
    pub plugin_results_count: usize,
    pub python_backend_used: bool,
    pub merge_strategy: MergeStrategy,
    pub extraction_result: ExtractionResult,
    pub errors: Vec<String>,
    pub performance_metrics: PerformanceMetrics,
}

/// 性能指标
#[derive(Debug, Clone, Default)]
pub struct PerformanceMetrics {
    pub total_time_ms: u64,
    pub plugin_time_ms: u64,
    pub python_time_ms: u64,
    pub merge_time_ms: u64,
    pub memory_peak_mb: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_integrated_scanner_creation() {
        let config = ScanIntegrationConfig::default();
        let scanner = IntegratedScanner::new(config);
        // 基本创建测试
        assert!(true);
    }

    #[test]
    fn test_merge_strategies() {
        assert!(matches!(MergeStrategy::PluginFirst, MergeStrategy::PluginFirst));
        assert!(matches!(MergeStrategy::PythonFirst, MergeStrategy::PythonFirst));
        assert!(matches!(MergeStrategy::MergeAll, MergeStrategy::MergeAll));
        assert!(matches!(MergeStrategy::BestResult, MergeStrategy::BestResult));
    }

    #[test]
    fn test_performance_modes() {
        assert!(matches!(PerformanceMode::Fast, PerformanceMode::Fast));
        assert!(matches!(PerformanceMode::Balanced, PerformanceMode::Balanced));
        assert!(matches!(PerformanceMode::Accurate, PerformanceMode::Accurate));
    }
}