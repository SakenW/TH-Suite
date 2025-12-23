use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub fn read_asset_kv(path: &str) -> Result<HashMap<String, String>, String> {
    let p = Path::new(path);
    if !p.exists() {
        return Err(format!("File not found: {}", path));
    }

    let content = fs::read_to_string(p).map_err(|e| e.to_string())?;
    
    // Naive detection by extension or try json first
    if p.extension().and_then(|s| s.to_str()) == Some("json") {
        if let Ok(json) = serde_json::from_str::<HashMap<String, serde_json::Value>>(&content) {
            let mut map = HashMap::new();
            for (k, v) in json {
                if let Some(s) = v.as_str() {
                    map.insert(k, s.to_string());
                } else {
                    map.insert(k, v.to_string());
                }
            }
            return Ok(map);
        }
    }

    // Fallback or .lang: Line based key=value
    let mut map = HashMap::new();
    for line in content.lines() {
        let line = line.trim();
        if line.starts_with('#') || line.is_empty() { continue; }
        
        if let Some((k, v)) = line.split_once('=') {
            map.insert(k.trim().to_string(), v.trim().to_string());
        }
    }
    
    Ok(map)
}
