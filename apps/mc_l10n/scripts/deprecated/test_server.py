"""
简单的测试服务器
用于测试前端功能
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uvicorn

app = FastAPI(title="MC L10n Test API", version="6.0.0-test")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 测试数据
test_mods = [
    {
        "mod_id": "twilightforest",
        "name": "The Twilight Forest",
        "version": "4.7.3196",
        "file_path": "/mods/twilightforest-1.21.1.jar",
        "translation_count": 850,
        "languages": ["en_us", "zh_cn"],
        "last_scanned": "2025-09-06T10:30:00Z"
    },
    {
        "mod_id": "create",
        "name": "Create",
        "version": "0.5.1",
        "file_path": "/mods/create-1.21.1.jar",
        "translation_count": 1200,
        "languages": ["en_us", "zh_cn", "ja_jp"],
        "last_scanned": "2025-09-06T11:00:00Z"
    },
    {
        "mod_id": "ars_nouveau",
        "name": "Ars Nouveau",
        "version": "5.2.0",
        "file_path": "/mods/ars_nouveau-1.21.1.jar",
        "translation_count": 650,
        "languages": ["en_us"],
        "last_scanned": "2025-09-06T09:15:00Z"
    }
]

scan_progress = {
    "scan_id": "scan_12345",
    "status": "idle",
    "progress": 0,
    "current_file": "",
    "processed": 0,
    "total": 0
}

# 请求模型
class ScanRequest(BaseModel):
    path: str
    recursive: bool = True
    auto_extract: bool = True
    include_patterns: List[str] = ["*.jar", "*.zip"]
    exclude_patterns: List[str] = []

class TranslationRequest(BaseModel):
    mod_id: str
    language: str
    translations: Dict[str, str]
    translator: Optional[str] = None
    auto_approve: bool = False

# API端点

@app.get("/")
async def root():
    return {
        "name": "MC L10n Test API",
        "version": "6.0.0-test",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "6.0.0-test",
        "uptime": 3600,
        "checks": {
            "database": "ok",
            "cache": "ok",
            "scanner": "ok"
        }
    }

@app.post("/api/v1/scan")
async def scan_mods(request: ScanRequest):
    """扫描MOD目录"""
    global scan_progress
    
    # 模拟扫描开始
    scan_progress = {
        "scan_id": f"scan_{datetime.now().timestamp()}",
        "status": "scanning",
        "progress": 0,
        "current_file": request.path,
        "processed": 0,
        "total": 3
    }
    
    return {
        "success": True,
        "data": {
            "scan_id": scan_progress["scan_id"],
            "total_files": 3,
            "mods_found": 3,
            "translations_found": 2700,
            "errors": [],
            "duration": 5.2
        }
    }

@app.get("/api/v1/scan/progress/{scan_id}")
async def get_scan_progress(scan_id: str):
    """获取扫描进度"""
    global scan_progress
    
    # 模拟进度更新
    if scan_progress["status"] == "scanning":
        scan_progress["progress"] = min(scan_progress["progress"] + 10, 100)
        scan_progress["processed"] = min(scan_progress["processed"] + 1, scan_progress["total"])
        
        if scan_progress["progress"] >= 100:
            scan_progress["status"] = "completed"
    
    return scan_progress

@app.get("/api/v1/mods")
async def get_mods(page: int = 1, size: int = 20, search: Optional[str] = None):
    """获取MOD列表"""
    filtered_mods = test_mods
    
    if search:
        filtered_mods = [m for m in test_mods if search.lower() in m["name"].lower()]
    
    return {
        "items": filtered_mods,
        "total": len(filtered_mods),
        "page": page,
        "size": size
    }

@app.get("/api/v1/mods/{mod_id}")
async def get_mod(mod_id: str):
    """获取MOD详情"""
    mod = next((m for m in test_mods if m["mod_id"] == mod_id), None)
    
    if not mod:
        raise HTTPException(status_code=404, detail="Mod not found")
    
    return {
        "mod_id": mod["mod_id"],
        "metadata": {
            "name": mod["name"],
            "version": mod["version"],
            "author": "Unknown",
            "description": f"A Minecraft mod: {mod['name']}"
        },
        "statistics": {
            "total_keys": mod["translation_count"],
            "translated": {
                "zh_cn": int(mod["translation_count"] * 0.8),
                "ja_jp": int(mod["translation_count"] * 0.6)
            },
            "approved": {
                "zh_cn": int(mod["translation_count"] * 0.7),
                "ja_jp": int(mod["translation_count"] * 0.5)
            }
        },
        "quality_score": 0.85
    }

@app.post("/api/v1/translations")
async def submit_translation(request: TranslationRequest):
    """提交翻译"""
    return {
        "success": True,
        "data": {
            "mod_id": request.mod_id,
            "language": request.language,
            "translated_count": len(request.translations),
            "failed_count": 0,
            "progress": 85.5,
            "quality_score": 0.92
        }
    }

@app.get("/api/v1/stats")
async def get_stats():
    """获取统计信息"""
    return {
        "performance": {
            "cache_hit_rate": 0.85,
            "avg_scan_time": 0.25,
            "db_connections": {
                "active": 3,
                "idle": 7,
                "total": 10
            }
        },
        "usage": {
            "api_calls_today": 256,
            "translations_today": 89,
            "active_users": 5
        }
    }

if __name__ == "__main__":
    print("🚀 Starting MC L10n Test Server")
    print("📍 Server: http://localhost:18000")
    print("📚 API Docs: http://localhost:18000/docs")
    print("⚠️  This is a TEST server with mock data")
    print("🔧 Press Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=18000, reload=True)