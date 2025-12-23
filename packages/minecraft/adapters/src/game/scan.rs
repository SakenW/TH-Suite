use crate::models::{AssetFile, ScanResult};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;
use zip::ZipArchive;

pub fn scan_and_cache<F>(root_path: &str, cache_root: &Path, mut on_progress: F) -> ScanResult 
where F: FnMut(usize, usize, String) {
    println!("--- STARTED SCANNING (Adapter): {} ---", root_path);
    let mut assets = Vec::new();
    let root = Path::new(root_path);

    // Ensure cache exist
    if !cache_root.exists() {
        let _ = fs::create_dir_all(cache_root);
    }

    // Phase 1: Pre-scan (Count potential archives)
    let mut total_mods = 0;
    let walker = WalkDir::new(root).into_iter().filter_map(|e| e.ok());
    let mut candidates = Vec::new();

    for entry in walker {
        let path = entry.path().to_path_buf();
        let ext = path.extension().and_then(|s| s.to_str()).map(|s| s.to_lowercase());
        if ext == Some("jar".to_string()) || ext == Some("zip".to_string()) {
            candidates.push(path);
            total_mods += 1;
        }
    }
    
    // Initial Progress
    on_progress(0, total_mods, "Starting scan...".to_string());

    // Phase 2: Process
    let mut current_mod = 0;
    for path in candidates {
        current_mod += 1;
        let file_name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
        
        // Emit Progress
        on_progress(current_mod, total_mods, file_name.clone());

        println!("Scanning archive [{}/{}]: {:?}", current_mod, total_mods, path);
        
        if let Ok(mut extracted_assets) = process_archive(root, &path, cache_root) {
            assets.append(&mut extracted_assets);
        } else {
            println!("Failed to process archive: {:?}", path);
        }
    }

    let total_files = assets.len();
    let total_entries = assets.iter().map(|a| a.entry_count).sum();

    // Final Emit
    on_progress(total_mods, total_mods, "Done".to_string());

    ScanResult {
        app_id: "Minecraft".to_string(),
        root_path: root_path.to_string(),
        total_files,
        total_entries,
        assets,
    }
}

fn process_archive(root: &Path, archive_path: &Path, cache_root: &Path) -> anyhow::Result<Vec<AssetFile>> {
    let file = fs::File::open(archive_path)?;
    let mut archive = ZipArchive::new(file)?;
    let mut assets = Vec::new();

    let archive_name = archive_path.file_name().unwrap().to_string_lossy().to_string();
    
    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;
        let raw_path = file.name().to_string();
        let internal_path = raw_path.replace("\\", "/"); 
        
        let clean_path = internal_path.trim_start_matches('/');
        let is_json = clean_path.ends_with(".json");
        let is_lang = clean_path.ends_with(".lang");

        if !clean_path.starts_with("assets/") || (!is_json && !is_lang) || !clean_path.contains("/lang/") {
            continue;
        }

        let parts: Vec<&str> = clean_path.split('/').collect();
        if parts.len() < 4 { continue; }
        
        let mod_id = parts[1];
        
        let safe_archive_name = sanitize_filename::sanitize(&archive_name);
        let dest_path = cache_root.join(&safe_archive_name).join(&internal_path);
        
        if let Some(parent) = dest_path.parent() {
            fs::create_dir_all(parent)?;
        }
        let mut outfile = fs::File::create(&dest_path)?;
        io::copy(&mut file, &mut outfile)?;

        let content = fs::read_to_string(&dest_path).unwrap_or_default();
        let entry_count = if is_json {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                json.as_object().map(|m| m.len()).unwrap_or(0)
            } else {
                0
            }
        } else {
            content.lines()
                .filter(|line| !line.trim().starts_with('#') && line.contains('='))
                .count()
        };

        assets.push(AssetFile {
            path: dest_path.to_string_lossy().replace("\\", "/"),
            original_path: format!("{}!/{}", archive_name, internal_path),
            mod_id: mod_id.to_string(),
            name: parts.last().unwrap().to_string(),
            entry_count
        });
    }

    Ok(assets)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs; // Import fs
    use std::fs::File;
    use std::io::Write;
    use zip::write::FileOptions;
    
    // ... rest of test


    #[test]
    fn test_scan_and_cache_zip() -> anyhow::Result<()> {
        let temp_dir = std::env::temp_dir().join(format!("th_test_scan_{}", uuid::Uuid::new_v4()));
        let root = temp_dir.join("root");
        let cache = temp_dir.join("cache");
        
        fs::create_dir_all(&root)?;
        
        // Create a Mock Jar
        let jar_path = root.join("test_mod.jar");
        let file = File::create(&jar_path)?;
        let mut zip = zip::ZipWriter::new(file);
        
        let options = FileOptions::default().compression_method(zip::CompressionMethod::Stored);
        
        // Add valid asset
        zip.start_file("assets/testmod/lang/en_us.json", options)?;
        zip.write_all(b"{ \"key\": \"value\" }")?;
        
        // Add invalid asset
        zip.start_file("assets/testmod/textures/test.png", options)?;
        zip.write_all(b"fake image")?;
        
        zip.finish()?;
        
        // Run Scan
        let mut progress_count = 0;
        let result = scan_and_cache(root.to_str().unwrap(), &cache, |curr, total, name| {
            println!("Progress: {}/{} - {}", curr, total, name);
            if name == "test_mod.jar" {
                progress_count += 1;
            }
        });
        
        // Verify
        assert_eq!(result.total_files, 1);
        assert_eq!(result.assets.len(), 1);
        let asset = &result.assets[0];
        assert_eq!(asset.mod_id, "testmod");
        assert_eq!(asset.name, "en_us.json");
        assert_eq!(asset.entry_count, 1);
        
        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
        
        Ok(())
    }
}
