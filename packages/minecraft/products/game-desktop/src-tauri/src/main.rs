#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::{Path, PathBuf};
use tauri::{App, Wry};
use rusqlite::Connection;

fn get_portable_dir(app: &App<Wry>, name: &str) -> PathBuf {
    // In production, use the executable's directory.
    // In dev, use the current working directory or a temp dir.
    let exe_path = std::env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
    let exe_dir = exe_path.parent().unwrap_or(&exe_path);
    
    // Check if we are in dev mode (simplistic check)
    // Better: use tauri::api::path functions, but we want strict portability for Prod.
    
    // For MVP: Always look next to exe
    let target_dir = exe_dir.join(name);
    if !target_dir.exists() {
        fs::create_dir_all(&target_dir).expect("Failed to create directory");
    }
    target_dir
}

fn init_db(data_dir: &Path) -> anyhow::Result<()> {
    let db_path = data_dir.join("app.db");
    let needs_init = !db_path.exists();
    
    let conn = Connection::open(&db_path)?;
    
    // Enable encryption (SQLCipher)
    // In a real app, retrieve key from Keychain/Keyring. 
    // Here we simulate or use a default for MVP/Dev if no key found (SECURITY TODO).
    let _key = "default-insecure-key-for-mvp"; 
    
    // PRAGMA key = '...';
    // conn.pragma_update(None, "key", &key)?;
    
    if needs_init {
        conn.execute(
            "CREATE TABLE meta (
                id INTEGER PRIMARY KEY,
                install_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL
            )",
            [],
        )?;
        
        // Generate Install ID
        let install_id = uuid::Uuid::new_v4().to_string();
        conn.execute(
            "INSERT INTO meta (install_id, schema_version) VALUES (?1, 1)",
            [&install_id],
        )?;
    }
    
    Ok(())
}


#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn select_directory() -> Result<String, String> {
    let (tx, rx) = std::sync::mpsc::channel();
    
    tauri::api::dialog::FileDialogBuilder::new()
        .set_title("Select Modpack Root Directory")
        .pick_folder(move |path_buf| {
            match path_buf {
                Some(path) => tx.send(Ok(path.display().to_string())).unwrap(),
                None => tx.send(Err("No directory selected".to_string())).unwrap(),
            }
        });

    rx.recv().unwrap_or(Err("Failed to receive selection".to_string()))
}

mod files;
use tauri::Manager;
use serde::Serialize;

#[derive(Clone, Serialize)]
struct ScanProgress {
    current: usize,
    total: usize,
    file: String,
}

#[tauri::command]
async fn scan_modpack(app_handle: tauri::AppHandle, path: String) -> Result<minecraft_adapters::models::ScanResult, String> {
    let exe_path = std::env::current_exe().map_err(|e| e.to_string())?;
    let exe_dir = exe_path.parent().unwrap_or(&exe_path);
    let cache_dir = exe_dir.join("data").join("cache");
    
    let result = minecraft_adapters::game::scan::scan_and_cache(&path, &cache_dir, |current, total, file| {
        let _ = app_handle.emit_all("scan-progress", ScanProgress {
            current,
            total,
            file,
        });
    });
    
    Ok(result)
}

#[tauri::command]
async fn read_asset(path: String) -> Result<std::collections::HashMap<String, String>, String> {
    files::read_asset_kv(&path)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet, select_directory, scan_modpack, read_asset])
        .setup(|app| {
            let data_dir = get_portable_dir(app, "data");
            let _config_dir = get_portable_dir(app, "config");
            let _logs_dir = get_portable_dir(app, "logs");
            
            // Initialize Database
            if let Err(e) = init_db(&data_dir) {
                eprintln!("Failed to initialize DB: {}", e);
                // Handle error (maybe show a dialog)
            }
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
