#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::{Path, PathBuf};
use tauri::{Manager, App, Wry};
use rusqlite::{Connection, Result};
use anyhow::Context;

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
    let key = "default-insecure-key-for-mvp"; 
    
    // PRAGMA key = '...';
    conn.pragma_update(None, "key", &key)?;
    
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

fn main() {
    tauri::Builder::default()
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
