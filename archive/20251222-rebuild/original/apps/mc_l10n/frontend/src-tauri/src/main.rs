// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;

use tauri::{Manager, Emitter};
use tauri_plugin_dialog::DialogExt;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::path::{Path, PathBuf};
use std::fs;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use config::AppConfig;

const BACKEND_URL: &str = "http://localhost:8000/api/v1";

// 扫描进度结构
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ScanProgress {
    scan_id: String,
    phase: String,
    progress: f64,
    message: String,
    current_file: Option<String>,
    processed_files: u32,
    total_files: u32,
    estimated_remaining: Option<u32>,
    updated_at: String,
}

// 扫描结果结构
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ScanResult {
    scan_id: String,
    project_path: String,
    scan_started_at: String,
    scan_completed_at: Option<String>,
    modpack_manifest: Option<ModpackManifest>,
    mod_jars: Vec<ModJarMetadata>,
    language_resources: Vec<LanguageResource>,
    total_mods: u32,
    total_language_files: u32,
    total_translatable_keys: u32,
    supported_locales: Vec<String>,
    warnings: Vec<String>,
    errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ModpackManifest {
    name: String,
    version: String,
    author: Option<String>,
    description: Option<String>,
    minecraft_version: String,
    loader: String,
    loader_version: String,
    platform: String,
    license: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ModJarMetadata {
    mod_id: String,
    display_name: String,
    version: String,
    loader: String,
    authors: Vec<String>,
    homepage: Option<String>,
    description: Option<String>,
    environment: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct LanguageResource {
    namespace: String,
    locale: String,
    source_path: String,
    source_type: String,
    key_count: u32,
    priority: u32,
}

// 文件信息结构
#[derive(Debug, Clone, Serialize, Deserialize)]
struct FileInfo {
    name: String,
    path: String,
    is_directory: bool,
    size: u64,
    modified_time: String,
}

// 扫描结果结构（简化版）
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SimpleScanResult {
    total_files: u32,
    jar_files: Vec<FileInfo>,
    lang_files: Vec<FileInfo>,
    modpack_files: Vec<FileInfo>,
    errors: Vec<String>,
}

// Mod信息结构
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ModInfo {
    id: String,
    name: String,
    version: String,
    mc_version: String,
    loader: String,
    description: Option<String>,
    authors: Vec<String>,
    dependencies: Vec<String>,
    jar_path: String,
    lang_files: Vec<String>,
}

// 全局扫描状态
type ScanState = Arc<Mutex<HashMap<String, ScanResult>>>;

// Learn more about Tauri commands at https://tauri.app/v1/guides/features/command
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn get_system_info() -> HashMap<String, String> {
    let mut info = HashMap::new();
    info.insert("os".to_string(), std::env::consts::OS.to_string());
    info.insert("arch".to_string(), std::env::consts::ARCH.to_string());
    info.insert("family".to_string(), std::env::consts::FAMILY.to_string());
    info
}

#[tauri::command]
async fn check_backend_connection(url: String) -> Result<bool, String> {
    match reqwest::get(&url).await {
        Ok(response) => Ok(response.status().is_success()),
        Err(e) => Err(format!("Failed to connect to backend: {}", e)),
    }
}

#[tauri::command]
async fn start_backend_server() -> Result<String, String> {
    // 这里应该启动后端服务器
    // 暂时返回模拟的端口
    Ok("8000".to_string())
}

#[tauri::command]
async fn open_external_url(url: String, app: tauri::AppHandle) -> Result<(), String> {
    tauri_plugin_shell::ShellExt::shell(&app)
        .open(&url, None)
        .map_err(|e| format!("Failed to open URL: {}", e))
}

#[tauri::command]
async fn show_notification(title: String, body: String, app: tauri::AppHandle) -> Result<(), String> {
    tauri_plugin_notification::NotificationExt::notification(&app)
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|e| format!("Failed to show notification: {}", e))
}

#[tauri::command]
fn get_config() -> Result<AppConfig, String> {
    AppConfig::load().map_err(|e| e.to_string())
}

#[tauri::command]
fn save_config(config: AppConfig) -> Result<(), String> {
    config.save().map_err(|e| e.to_string())
}

#[tauri::command]
fn get_database_path() -> Result<String, String> {
    let config = AppConfig::load().map_err(|e| e.to_string())?;
    Ok(config.get_database_path().to_string_lossy().to_string())
}

#[tauri::command]
fn get_data_dir() -> Result<String, String> {
    let config = AppConfig::load().map_err(|e| e.to_string())?;
    Ok(config.get_data_dir().to_string_lossy().to_string())
}

#[tauri::command]
async fn start_project_scan(
    project_path: String,
    app: tauri::AppHandle,
    state: tauri::State<'_, ScanState>,
) -> Result<String, String> {
    let scan_id = uuid::Uuid::new_v4().to_string();
    let project_path_buf = PathBuf::from(&project_path);
    
    if !project_path_buf.exists() {
        return Err("Project path does not exist".to_string());
    }
    
    let scan_id_clone = scan_id.clone();
    let app_clone = app.clone();
    let state_clone = state.inner().clone();
    
    // 在后台线程中执行扫描
    tokio::spawn(async move {
        let result = perform_project_scan(scan_id_clone.clone(), project_path, app_clone).await;
        
        // 保存扫描结果
        if let Ok(scan_result) = result {
            let mut scans = state_clone.lock().unwrap();
            scans.insert(scan_id_clone, scan_result);
        }
    });
    
    Ok(scan_id)
}

#[tauri::command]
fn get_scan_result(
    scan_id: String,
    state: tauri::State<'_, ScanState>,
) -> Result<ScanResult, String> {
    let scans = state.lock().unwrap();
    scans.get(&scan_id)
        .cloned()
        .ok_or_else(|| "Scan result not found".to_string())
}

#[tauri::command]
async fn create_project_from_scan(
    scan_id: String,
    state: tauri::State<'_, ScanState>,
) -> Result<String, String> {
    let scan_result = {
        let scans = state.lock().unwrap();
        scans.get(&scan_id).cloned().ok_or("Scan result not found")?
    };

    let client = reqwest::Client::new();
    
    // 构建项目创建请求
    let project_name = scan_result.modpack_manifest
        .as_ref()
        .map(|m| m.name.clone())
        .unwrap_or_else(|| "New Project".to_string());
    
    let mc_version = scan_result.modpack_manifest
        .as_ref()
        .map(|m| m.minecraft_version.clone())
        .unwrap_or_else(|| "1.20.1".to_string());
    
    let loader = scan_result.modpack_manifest
        .as_ref()
        .map(|m| m.loader.clone())
        .unwrap_or_else(|| "fabric".to_string());
    
    let loader_version = scan_result.modpack_manifest
        .as_ref()
        .map(|m| m.loader_version.clone())
        .unwrap_or_else(|| "0.15.0".to_string());
    
    let create_request = serde_json::json!({
        "scan_id": scan_result.scan_id,
        "name": project_name,
        "version": "1.0.0",
        "mc_version": mc_version,
        "loader": loader,
        "loader_version": loader_version,
        "project_type": "modpack",
        "directory": scan_result.project_path
    });
    
    // 调用后端创建项目API
    let response = client
        .post(&format!("{}/projects", BACKEND_URL))
        .json(&create_request)
        .send()
        .await
        .map_err(|e| format!("Failed to call backend API: {}", e))?;
    
    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Backend API returned error: {} - {}", status, error_text));
    }
    
    let response_json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    // 从响应中提取project_id
    let project_id = response_json
        .get("project_id")
        .and_then(|v| v.as_str())
        .ok_or("No project_id in response")?;
    
    Ok(project_id.to_string())
}

// ==================== Local Data Commands ====================

#[tauri::command]
async fn get_local_entries() -> Result<Value, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/local/entries", BACKEND_URL);
    
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to call backend API: {}", e))?;
        
    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Backend API returned error: {} - {}", status, error_text));
    }
    
    let result = response
        .json::<Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
        
    Ok(result)
}

#[tauri::command]
async fn get_mapping_plans() -> Result<Value, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/local/plans", BACKEND_URL);
    
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to call backend API: {}", e))?;
        
    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Backend API returned error: {} - {}", status, error_text));
    }
    
    let result = response
        .json::<Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
        
    Ok(result)
}

#[tauri::command]
async fn get_outbound_queue() -> Result<Value, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/local/queue", BACKEND_URL);
    
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to call backend API: {}", e))?;
        
    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Backend API returned error: {} - {}", status, error_text));
    }
    
    let result = response
        .json::<Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
        
    Ok(result)
}

#[tauri::command]
async fn get_mapping_links() -> Result<Value, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/local/links", BACKEND_URL);
    
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to call backend API: {}", e))?;
        
    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Backend API returned error: {} - {}", status, error_text));
    }
    
    let result = response
        .json::<Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
        
    Ok(result)
}

#[tauri::command]
async fn get_local_data_statistics() -> Result<Value, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/local/entries/statistics", BACKEND_URL);
    
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to call backend API: {}", e))?;
        
    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Backend API returned error: {} - {}", status, error_text));
    }
    
    let result = response
        .json::<Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
        
    Ok(result)
}

#[tauri::command]
async fn import_local_data() -> Result<Value, String> {
    // This is a placeholder. In a real app, you might trigger a background job.
    // For now, we'll just return a success message.
    Ok(serde_json::json!({ "message": "Import started successfully" }))
}


// 执行项目扫描的主要逻辑
async fn perform_project_scan(
    scan_id: String,
    project_path: String,
    app: tauri::AppHandle,
) -> Result<ScanResult, String> {
    let start_time = chrono::Utc::now();
    let project_path_buf = PathBuf::from(&project_path);
    
    // 发送初始进度
    emit_scan_progress(&app, &scan_id, "detecting_project_type", 0.0, "Detecting project type...", None, 0, 100, None).await;
    
    // 检测项目类型
    let is_modpack = detect_modpack(&project_path_buf);
    
    emit_scan_progress(&app, &scan_id, "scanning_modpack", 10.0, "Scanning modpack manifest...", None, 10, 100, None).await;
    
    // 扫描组合包清单
    let modpack_manifest = if is_modpack {
        scan_modpack_manifest(&project_path_buf)
    } else {
        None
    };
    
    emit_scan_progress(&app, &scan_id, "scanning_mods", 30.0, "Scanning mod JAR files...", None, 30, 100, None).await;
    
    // 扫描模组JAR文件
    let mod_jars = scan_mod_jars(&project_path_buf);
    
    emit_scan_progress(&app, &scan_id, "scanning_language_resources", 60.0, "Scanning language resources...", None, 60, 100, None).await;
    
    // 扫描语言资源
    let language_resources = scan_language_resources(&project_path_buf);
    
    emit_scan_progress(&app, &scan_id, "generating_statistics", 80.0, "Generating statistics...", None, 80, 100, None).await;
    
    // 计算统计信息
    let total_mods = mod_jars.len() as u32;
    let total_language_files = language_resources.len() as u32;
    let total_translatable_keys: u32 = language_resources.iter().map(|r| r.key_count).sum();
    let mut supported_locales: Vec<String> = language_resources.iter()
        .map(|r| r.locale.clone())
        .collect::<std::collections::HashSet<String>>()
        .into_iter()
        .collect();
    supported_locales.sort();
    
    emit_scan_progress(&app, &scan_id, "validation", 95.0, "Validating scan results...", None, 95, 100, None).await;
    
    // 创建扫描结果
    let scan_result = ScanResult {
        scan_id: scan_id.clone(),
        project_path: project_path.clone(),
        scan_started_at: start_time.to_rfc3339(),
        scan_completed_at: Some(chrono::Utc::now().to_rfc3339()),
        modpack_manifest,
        mod_jars,
        language_resources,
        total_mods,
        total_language_files,
        total_translatable_keys,
        supported_locales,
        warnings: vec![], // TODO: Add actual warnings
        errors: vec![], // TODO: Add actual errors
    };
    
    emit_scan_progress(&app, &scan_id, "completed", 100.0, "Scan completed successfully!", None, 100, 100, Some(0)).await;
    
    Ok(scan_result)
}

// 发送扫描进度事件
async fn emit_scan_progress(
    app: &tauri::AppHandle,
    scan_id: &str,
    phase: &str,
    progress: f64,
    message: &str,
    current_file: Option<String>,
    processed_files: u32,
    total_files: u32,
    estimated_remaining: Option<u32>,
) {
    let progress_data = ScanProgress {
        scan_id: scan_id.to_string(),
        phase: phase.to_string(),
        progress,
        message: message.to_string(),
        current_file,
        processed_files,
        total_files,
        estimated_remaining,
        updated_at: chrono::Utc::now().to_rfc3339(),
    };
    
    let _ = app.emit("scan-progress", progress_data);
}

// 检测是否为组合包
fn detect_modpack(project_path: &PathBuf) -> bool {
    // 检查常见的组合包文件
    let manifest_files = [
        "manifest.json",      // CurseForge
        "modrinth.index.json", // Modrinth
        "pack.toml",          // Packwiz
        "instance.cfg",       // MultiMC
    ];
    
    manifest_files.iter().any(|file| project_path.join(file).exists())
}

// 扫描组合包清单
fn scan_modpack_manifest(project_path: &PathBuf) -> Option<ModpackManifest> {
    // 检查 CurseForge manifest.json
    if let Some(manifest) = read_curseforge_manifest(project_path) {
        return Some(manifest);
    }
    
    // 检查 Modrinth modrinth.index.json
    if let Some(manifest) = read_modrinth_manifest(project_path) {
        return Some(manifest);
    }
    
    // 检查 Packwiz pack.toml
    if let Some(manifest) = read_packwiz_manifest(project_path) {
        return Some(manifest);
    }
    
    // 检查 MultiMC instance.cfg
    if let Some(manifest) = read_multimc_manifest(project_path) {
        return Some(manifest);
    }
    
    None
}

fn read_curseforge_manifest(project_path: &PathBuf) -> Option<ModpackManifest> {
    let manifest_path = project_path.join("manifest.json");
    if !manifest_path.exists() {
        return None;
    }
    
    let content = fs::read_to_string(&manifest_path).ok()?;
    let json: serde_json::Value = serde_json::from_str(&content).ok()?;
    
    Some(ModpackManifest {
        name: json.get("name")?.as_str()?.to_string(),
        version: json.get("version")?.as_str()?.to_string(),
        author: json.get("author")?.as_str().map(|s| s.to_string()),
        description: json.get("description")?.as_str().map(|s| s.to_string()),
        minecraft_version: json.get("minecraft")?.get("version")?.as_str()?.to_string(),
        loader: "Forge".to_string(), // CurseForge 通常使用 Forge
        loader_version: json.get("minecraft")?.get("modLoaders")?.as_array()
            ?.first()?.get("id")?.as_str()?.to_string(),
        platform: "CurseForge".to_string(),
        license: None,
    })
}

fn read_modrinth_manifest(project_path: &PathBuf) -> Option<ModpackManifest> {
    let manifest_path = project_path.join("modrinth.index.json");
    if !manifest_path.exists() {
        return None;
    }
    
    let content = fs::read_to_string(&manifest_path).ok()?;
    let json: serde_json::Value = serde_json::from_str(&content).ok()?;
    
    Some(ModpackManifest {
        name: json.get("name")?.as_str()?.to_string(),
        version: json.get("versionId")?.as_str()?.to_string(),
        author: None,
        description: json.get("summary")?.as_str().map(|s| s.to_string()),
        minecraft_version: json.get("dependencies")?.get("minecraft")?.as_str()?.to_string(),
        loader: json.get("dependencies")?.as_object()?.keys().find(|k| *k != "minecraft")?.clone(),
        loader_version: json.get("dependencies")?.as_object()?.values().nth(1)?.as_str()?.to_string(),
        platform: "Modrinth".to_string(),
        license: None,
    })
}

fn read_packwiz_manifest(project_path: &PathBuf) -> Option<ModpackManifest> {
    let manifest_path = project_path.join("pack.toml");
    if !manifest_path.exists() {
        return None;
    }
    
    // 简单的 TOML 解析 - 在实际项目中应该使用 toml crate
    let content = fs::read_to_string(&manifest_path).ok()?;
    
    Some(ModpackManifest {
        name: extract_toml_value(&content, "name").unwrap_or_else(|| "Packwiz Modpack".to_string()),
        version: extract_toml_value(&content, "version").unwrap_or_else(|| "1.0.0".to_string()),
        author: extract_toml_value(&content, "author"),
        description: None,
        minecraft_version: extract_toml_value(&content, "mc-version").unwrap_or_else(|| "1.20.1".to_string()),
        loader: extract_toml_value(&content, "mod-loader").unwrap_or_else(|| "fabric".to_string()),
        loader_version: extract_toml_value(&content, "loader-version").unwrap_or_else(|| "latest".to_string()),
        platform: "Packwiz".to_string(),
        license: None,
    })
}

fn read_multimc_manifest(project_path: &PathBuf) -> Option<ModpackManifest> {
    let manifest_path = project_path.join("instance.cfg");
    if !manifest_path.exists() {
        return None;
    }
    
    let content = fs::read_to_string(&manifest_path).ok()?;
    
    Some(ModpackManifest {
        name: extract_cfg_value(&content, "name").unwrap_or_else(|| "MultiMC Instance".to_string()),
        version: "1.0.0".to_string(),
        author: None,
        description: None,
        minecraft_version: extract_cfg_value(&content, "IntendedVersion").unwrap_or_else(|| "1.20.1".to_string()),
        loader: "Forge".to_string(), // MultiMC 实例通常使用 Forge
        loader_version: "latest".to_string(),
        platform: "MultiMC".to_string(),
        license: None,
    })
}

fn extract_toml_value(content: &str, key: &str) -> Option<String> {
    for line in content.lines() {
        if let Some(stripped) = line.trim().strip_prefix(&format!("{} = ", key)) {
            return Some(stripped.trim_matches('"').to_string());
        }
    }
    None
}

fn extract_cfg_value(content: &str, key: &str) -> Option<String> {
    for line in content.lines() {
        if let Some(stripped) = line.trim().strip_prefix(&format!("{}=", key)) {
            return Some(stripped.to_string());
        }
    }
    None
}

// 扫描模组JAR文件
fn scan_mod_jars(project_path: &PathBuf) -> Vec<ModJarMetadata> {
    let mut mod_jars = Vec::new();
    
    // 扫描 mods 目录
    let mods_dir = project_path.join("mods");
    if mods_dir.exists() {
        if let Ok(entries) = fs::read_dir(&mods_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() && path.extension().map_or(false, |ext| ext == "jar") {
                    if let Some(mod_metadata) = extract_mod_metadata(&path) {
                        mod_jars.push(mod_metadata);
                    }
                }
            }
        }
    }
    
    // 如果是单个 JAR 文件项目
    if let Ok(entries) = fs::read_dir(project_path) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |ext| ext == "jar") {
                if let Some(mod_metadata) = extract_mod_metadata(&path) {
                    mod_jars.push(mod_metadata);
                }
            }
        }
    }
    
    mod_jars
}

// 提取 MOD 元数据（简化版本）
fn extract_mod_metadata(jar_path: &Path) -> Option<ModJarMetadata> {
    // 从文件名推断基本信息
    let file_name = jar_path.file_stem()?.to_str()?.to_string();
    
    // 尝试从文件名中提取版本信息
    let (display_name, version) = parse_jar_filename(&file_name);
    
    // 在真实实现中，这里应该解压 JAR 文件并读取 fabric.mod.json 或 META-INF/mods.toml
    Some(ModJarMetadata {
        mod_id: file_name.to_lowercase().replace(' ', "_"),
        display_name,
        version,
        loader: "unknown".to_string(), // 需要通过解析 JAR 内容确定
        authors: vec!["Unknown".to_string()],
        homepage: None,
        description: Some(format!("Mod from {}", file_name)),
        environment: "universal".to_string(),
    })
}

// 从 JAR 文件名解析模组名和版本
fn parse_jar_filename(filename: &str) -> (String, String) {
    // 尝试不同的分隔符模式来提取版本
    let separators = ["-", "_v", "_"];
    
    for sep in separators {
        if let Some(pos) = filename.rfind(sep) {
            let (name_part, version_part) = filename.split_at(pos);
            let version_candidate = &version_part[sep.len()..];
            
            // 检查版本部分是否像版本号
            if is_version_like(version_candidate) {
                let clean_name = name_part.replace(['_', '-'], " ");
                return (clean_name, version_candidate.to_string());
            }
        }
    }
    
    // 如果无法解析版本，返回文件名和默认版本
    (filename.replace(['_', '-'], " "), "1.0.0".to_string())
}

// 检查字符串是否像版本号
fn is_version_like(s: &str) -> bool {
    if s.is_empty() {
        return false;
    }
    
    // 版本号通常以数字开头
    if !s.chars().next().unwrap_or('a').is_ascii_digit() {
        return false;
    }
    
    // 版本号包含至少一个点
    if !s.contains('.') {
        return false;
    }
    
    // 检查前几个字符是否符合版本格式（数字.数字）
    let chars: Vec<char> = s.chars().take(5).collect();
    if chars.len() >= 3 {
        return chars[0].is_ascii_digit() && 
               chars[1] == '.' && 
               chars[2].is_ascii_digit();
    }
    
    false
}

// 扫描语言资源
fn scan_language_resources(project_path: &PathBuf) -> Vec<LanguageResource> {
    let mut language_resources = Vec::new();
    
    // 扫描资源包语言文件
    scan_resourcepack_lang_files(project_path, &mut language_resources);
    
    // TODO: 扫描 JAR 文件中的语言资源（需要 ZIP 解压功能）
    // scan_jar_lang_files(project_path, &mut language_resources);
    
    language_resources
}

// 扫描资源包语言文件
fn scan_resourcepack_lang_files(project_path: &PathBuf, language_resources: &mut Vec<LanguageResource>) {
    // 扫描 assets 目录结构
    let assets_dir = project_path.join("assets");
    if !assets_dir.exists() {
        return;
    }
    
    // 遍历 namespace 目录
    if let Ok(namespace_entries) = fs::read_dir(&assets_dir) {
        for namespace_entry in namespace_entries.flatten() {
            if !namespace_entry.path().is_dir() {
                continue;
            }
            
            let namespace = namespace_entry.file_name().to_string_lossy().to_string();
            let lang_dir = namespace_entry.path().join("lang");
            
            if lang_dir.exists() {
                if let Ok(lang_entries) = fs::read_dir(&lang_dir) {
                    for lang_entry in lang_entries.flatten() {
                        let lang_path = lang_entry.path();
                        if lang_path.is_file() && is_language_file(&lang_path) {
                            if let Some(lang_resource) = create_language_resource(&lang_path, &namespace, "resourcepack") {
                                language_resources.push(lang_resource);
                            }
                        }
                    }
                }
            }
        }
    }
}

// 创建语言资源对象
fn create_language_resource(lang_path: &Path, namespace: &str, source_type: &str) -> Option<LanguageResource> {
    let file_name = lang_path.file_stem()?.to_str()?;
    let locale = file_name.to_string();
    
    // 统计语言文件中的键数量
    let key_count = count_language_keys(lang_path);
    
    Some(LanguageResource {
        namespace: namespace.to_string(),
        locale,
        source_path: lang_path.to_string_lossy().to_string(),
        source_type: source_type.to_string(),
        key_count,
        priority: 1,
    })
}

// 统计语言文件中的键数量
fn count_language_keys(lang_path: &Path) -> u32 {
    if let Ok(content) = fs::read_to_string(lang_path) {
        if lang_path.extension().map_or(false, |ext| ext == "json") {
            // JSON 格式
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(obj) = json.as_object() {
                    return obj.len() as u32;
                }
            }
        } else if lang_path.extension().map_or(false, |ext| ext == "lang") {
            // .lang 格式 (key=value)
            return content.lines().filter(|line| {
                let trimmed = line.trim();
                !trimmed.is_empty() && !trimmed.starts_with('#') && trimmed.contains('=')
            }).count() as u32;
        }
    }
    0
}

// 新增的文件系统操作命令

#[tauri::command]
async fn select_directory(app: tauri::AppHandle) -> Result<Option<String>, String> {
    use std::sync::{Arc, Mutex};
    use std::sync::mpsc;
    
    let (sender, receiver) = mpsc::channel();
    let sender = Arc::new(Mutex::new(Some(sender)));
    
    app.dialog()
        .file()
        .set_title("Select Minecraft Directory")
        .pick_folder(move |folder_path| {
            if let Ok(sender_guard) = sender.lock() {
                if let Some(sender) = sender_guard.as_ref() {
                    let _ = sender.send(folder_path);
                }
            }
        });
    
    match receiver.recv() {
        Ok(Some(path)) => Ok(Some(path.to_string())),
        Ok(None) => Ok(None),
        Err(_) => Err("Dialog operation failed".to_string()),
    }
}

#[tauri::command]
async fn scan_directory(dir_path: String) -> Result<SimpleScanResult, String> {
    let path = Path::new(&dir_path);
    
    if !path.exists() {
        return Err("Directory does not exist".to_string());
    }
    
    let mut jar_files = Vec::new();
    let mut lang_files = Vec::new();
    let mut modpack_files = Vec::new();
    let mut errors = Vec::new();
    let mut total_files = 0;
    
    // 递归扫描目录
    if let Err(e) = scan_directory_recursive(path, &mut jar_files, &mut lang_files, &mut modpack_files, &mut total_files, &mut errors) {
        errors.push(format!("Scan error: {}", e));
    }
    
    Ok(SimpleScanResult {
        total_files,
        jar_files,
        lang_files,
        modpack_files,
        errors,
    })
}

fn scan_directory_recursive(
    dir: &Path,
    jar_files: &mut Vec<FileInfo>,
    lang_files: &mut Vec<FileInfo>,
    modpack_files: &mut Vec<FileInfo>,
    total_files: &mut u32,
    errors: &mut Vec<String>
) -> Result<(), Box<dyn std::error::Error>> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        *total_files += 1;
        
        if path.is_file() {
            let file_name = path.file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("")
                .to_string();
            
            let metadata = fs::metadata(&path)?;
            let modified_time = metadata.modified()
                .map(|t| format!("{:?}", t))
                .unwrap_or_else(|_| "Unknown".to_string());
            
            let file_info = FileInfo {
                name: file_name.clone(),
                path: path.to_string_lossy().to_string(),
                is_directory: false,
                size: metadata.len(),
                modified_time,
            };
            
            // 分类文件
            if file_name.ends_with(".jar") {
                jar_files.push(file_info);
            } else if is_language_file(&path) {
                lang_files.push(file_info);
            } else if is_modpack_file(&path) {
                modpack_files.push(file_info);
            }
        } else if path.is_dir() {
            // 递归扫描子目录，但限制深度避免无限递归
            if let Err(e) = scan_directory_recursive(&path, jar_files, lang_files, modpack_files, total_files, errors) {
                errors.push(format!("Error scanning {}: {}", path.display(), e));
            }
        }
    }
    
    Ok(())
}

fn is_language_file(path: &Path) -> bool {
    if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
        if ext == "json" || ext == "lang" {
            if let Some(path_str) = path.to_str() {
                return path_str.contains("lang") || path_str.contains("i18n");
            }
        }
    }
    false
}

fn is_modpack_file(path: &Path) -> bool {
    if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
        matches!(name.to_lowercase().as_str(),
            "manifest.json" | "modrinth.index.json" | "pack.toml" | 
            "instance.cfg" | "mmc-pack.json" | "modlist.html"
        )
    } else {
        false
    }
}

#[tauri::command]
async fn parse_mod_jar(jar_path: String) -> Result<ModInfo, String> {
    // 这里应该实际解析JAR文件
    // 暂时返回模拟数据
    let path = Path::new(&jar_path);
    let file_name = path.file_stem()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown");
    
    Ok(ModInfo {
        id: format!("{}_mod", file_name.to_lowercase()),
        name: file_name.to_string(),
        version: "1.0.0".to_string(),
        mc_version: "1.20.1".to_string(),
        loader: "forge".to_string(),
        description: Some(format!("Mod parsed from {}", file_name)),
        authors: vec!["Unknown Author".to_string()],
        dependencies: vec![],
        jar_path,
        lang_files: vec![],
    })
}

#[tauri::command]
async fn detect_project_type(dir_path: String) -> Result<String, String> {
    let path = Path::new(&dir_path);
    
    // 检查是否为modpack
    if detect_modpack(&PathBuf::from(&dir_path)) {
        return Ok("modpack".to_string());
    }
    
    // 检查mods目录
    if path.join("mods").exists() {
        return Ok("mods".to_string());
    }
    
    // 检查assets目录（资源包）
    if path.join("assets").exists() || path.join("pack.mcmeta").exists() {
        return Ok("resourcepack".to_string());
    }
    
    Ok("unknown".to_string())
}

#[tauri::command]
async fn read_text_file(file_path: String) -> Result<String, String> {
    fs::read_to_string(&file_path)
        .map_err(|e| format!("Failed to read file: {}", e))
}

#[tauri::command]
async fn file_exists(file_path: String) -> Result<bool, String> {
    Ok(Path::new(&file_path).exists())
}

#[tauri::command]
async fn list_directory(dir_path: String) -> Result<Vec<FileInfo>, String> {
    let path = Path::new(&dir_path);
    
    if !path.exists() {
        return Err("Directory does not exist".to_string());
    }
    
    let mut files = Vec::new();
    
    for entry in fs::read_dir(path).map_err(|e| format!("Failed to read directory: {}", e))? {
        let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
        let entry_path = entry.path();
        
        let metadata = fs::metadata(&entry_path)
            .map_err(|e| format!("Failed to read metadata: {}", e))?;
        
        let file_info = FileInfo {
            name: entry_path.file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("")
                .to_string(),
            path: entry_path.to_string_lossy().to_string(),
            is_directory: metadata.is_dir(),
            size: metadata.len(),
            modified_time: metadata.modified()
                .map(|t| format!("{:?}", t))
                .unwrap_or_else(|_| "Unknown".to_string()),
        };
        
        files.push(file_info);
    }
    
    Ok(files)
}

#[tauri::command]
async fn create_directory(dir_path: String) -> Result<(), String> {
    fs::create_dir_all(&dir_path)
        .map_err(|e| format!("Failed to create directory: {}", e))
}

#[tauri::command]
async fn copy_file(source_path: String, dest_path: String) -> Result<(), String> {
    fs::copy(&source_path, &dest_path)
        .map(|_| ())
        .map_err(|e| format!("Failed to copy file: {}", e))
}

#[tauri::command]
async fn delete_file(file_path: String) -> Result<(), String> {
    let path = Path::new(&file_path);
    
    if path.is_dir() {
        fs::remove_dir_all(path)
            .map_err(|e| format!("Failed to delete directory: {}", e))
    } else {
        fs::remove_file(path)
            .map_err(|e| format!("Failed to delete file: {}", e))
    }
}

fn main() {
    // 初始化扫描状态
    let scan_state: ScanState = Arc::new(Mutex::new(HashMap::new()));
    
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .manage(scan_state)
        .setup(|app| {
            // 应用启动时的初始化逻辑
            let window = app.get_webview_window("main").unwrap();
            
            // 设置窗口标题
            window.set_title("TH Suite MC L10n").unwrap();
            
            // 初始化配置和数据目录
            if let Err(e) = AppConfig::load().and_then(|config| {
                config.ensure_directories().map_err(|e| e.into())
            }) {
                eprintln!("Failed to initialize app config: {}", e);
            }
            
            // 在开发模式下打开开发者工具
            #[cfg(debug_assertions)]
            window.open_devtools();
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_app_version,
            get_system_info,
            check_backend_connection,
            start_backend_server,
            open_external_url,
            show_notification,
            get_config,
            save_config,
            get_database_path,
            get_data_dir,
            start_project_scan,
            get_scan_result,
            create_project_from_scan,
            get_local_entries,
            get_mapping_plans,
            get_outbound_queue,
            get_mapping_links,
            get_local_data_statistics,
            import_local_data,
            // 新增的文件系统操作命令
            select_directory,
            scan_directory,
            parse_mod_jar,
            detect_project_type,
            read_text_file,
            file_exists,
            list_directory,
            create_directory,
            copy_file,
            delete_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
