use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::fs;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppConfig {
    pub database_path: String,
    pub data_dir: String,
    pub theme: String,
    pub language: String,
    pub auto_save: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            database_path: "./data/app.db".to_string(),
            data_dir: "./data".to_string(),
            theme: "light".to_string(),
            language: "zh-CN".to_string(),
            auto_save: true,
        }
    }
}

impl AppConfig {
    pub fn load() -> Result<Self, Box<dyn std::error::Error>> {
        let config_path = Self::get_config_path()?;
        
        if config_path.exists() {
            let content = fs::read_to_string(&config_path)?;
            let config: AppConfig = serde_json::from_str(&content)?;
            Ok(config)
        } else {
            let config = Self::default();
            config.save()?;
            Ok(config)
        }
    }
    
    pub fn save(&self) -> Result<(), Box<dyn std::error::Error>> {
        let config_path = Self::get_config_path()?;
        
        // 确保配置目录存在
        if let Some(parent) = config_path.parent() {
            fs::create_dir_all(parent)?;
        }
        
        let content = serde_json::to_string_pretty(self)?;
        fs::write(&config_path, content)?;
        Ok(())
    }
    
    fn get_config_path() -> Result<PathBuf, Box<dyn std::error::Error>> {
        // 获取可执行文件所在目录
        let exe_dir = std::env::current_exe()?
            .parent()
            .ok_or("Cannot get executable directory")?
            .to_path_buf();
        
        Ok(exe_dir.join("config.json"))
    }
    
    pub fn get_database_path(&self) -> PathBuf {
        let path = PathBuf::from(&self.database_path);
        if path.is_absolute() {
            path
        } else {
            // 相对于可执行文件目录
            std::env::current_exe()
                .unwrap()
                .parent()
                .unwrap()
                .join(&self.database_path)
        }
    }
    
    pub fn get_data_dir(&self) -> PathBuf {
        let path = PathBuf::from(&self.data_dir);
        if path.is_absolute() {
            path
        } else {
            // 相对于可执行文件目录
            std::env::current_exe()
                .unwrap()
                .parent()
                .unwrap()
                .join(&self.data_dir)
        }
    }
    
    pub fn ensure_directories(&self) -> Result<(), Box<dyn std::error::Error>> {
        let data_dir = self.get_data_dir();
        fs::create_dir_all(&data_dir)?;
        
        // 确保数据库目录存在
        let db_path = self.get_database_path();
        if let Some(parent) = db_path.parent() {
            fs::create_dir_all(parent)?;
        }
        
        Ok(())
    }
}