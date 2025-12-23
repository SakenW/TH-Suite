use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AssetFile {
    pub path: String,          // Path in CACHE
    #[serde(rename = "originalPath")]
    pub original_path: String, // e.g. "mods/Botania.jar!/assets/..."
    #[serde(rename = "modId")]
    pub mod_id: String,
    pub name: String,
    #[serde(rename = "entryCount")]
    pub entry_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanResult {
    #[serde(rename = "appId")]
    pub app_id: String,
    #[serde(rename = "rootPath")]
    pub root_path: String,
    #[serde(rename = "totalFiles")]
    pub total_files: usize,
    #[serde(rename = "totalEntries")]
    pub total_entries: usize,
    pub assets: Vec<AssetFile>,
}
