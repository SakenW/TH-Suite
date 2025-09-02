"""TH Suite MC L10n Backend - Main application entry point."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root and backend directory to Python path  
project_root = Path(__file__).parent.parent.parent.parent
backend_dir = project_root / "apps" / "mc_l10n" / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# Import after path modification
from packages.backend_kit import create_app  # noqa: E402

# Application metadata
APP_NAME = "TH Suite MC L10n Backend"
APP_DESCRIPTION = "TransHub Tools - Minecraft Studio Backend API"
APP_VERSION = "1.0.0"

# Environment configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:15173"
).split(",")
LOG_FILE = os.getenv("LOG_FILE", "logs/mc-studio-backend.log")

# Create FastAPI application
thtools_app = create_app(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    debug=DEBUG,
    cors_origins=CORS_ORIGINS,
    log_level=LOG_LEVEL,
    log_file=LOG_FILE,
)
app = thtools_app.app

# Add dependency injection

# Add API routes - imports after app initialization
# from mc_l10n.adapters.api.local_data_routes import router as local_data_router  # noqa: E402
# from mc_l10n.adapters.api.routes import router  # noqa: E402

# Add basic scan endpoints directly to fix the immediate white screen issue
from fastapi import APIRouter
from pydantic import BaseModel

# Create a simple scan router
scan_router = APIRouter(prefix="/api/v1", tags=["scan"])

class ScanRequest(BaseModel):
    path: str

class ScanResponse(BaseModel):
    success: bool
    message: str
    scan_id: str = None

@scan_router.post("/scan-project")
async def start_scan(request: dict):
    """开始扫描项目"""
    directory = request.get("directory", "")
    return {
        "success": True,
        "message": f"扫描已开始: {directory}",
        "scan_id": "temp_scan_123"
    }

@scan_router.get("/scan/{scan_id}")
async def get_scan_status(scan_id: str):
    """获取扫描状态"""
    return {
        "scan_id": scan_id,
        "status": "in_progress",
        "progress": 0.5,
        "message": "正在扫描中..."
    }

@scan_router.get("/scan-results/latest/{path:path}")
async def get_latest_scan_result(path: str):
    """获取最新扫描结果"""
    # 模拟扫描结果
    mock_result = {
        "data": {
            "scan_id": "temp_scan_123",
            "project_path": path,
            "scan_started_at": "2024-01-01T00:00:00Z",
            "scan_completed_at": "2024-01-01T00:01:00Z",
            "modpack_manifest": {
                "name": "测试模组包",
                "version": "1.0.0",
                "author": "测试作者",
                "description": "这是一个测试模组包",
                "minecraft_version": "1.20.1",
                "loader": "fabric",
                "loader_version": "0.15.0",
                "platform": "CurseForge",
                "license": "MIT"
            },
            "mod_jars": [
                {
                    "mod_id": "test_mod",
                    "display_name": "测试模组",
                    "version": "1.0.0",
                    "loader": "fabric",
                    "authors": ["测试作者"],
                    "homepage": None,
                    "description": "这是一个测试模组",
                    "environment": "client"
                }
            ],
            "language_resources": [
                {
                    "namespace": "test_mod",
                    "locale": "en_us",
                    "source_path": "/lang/en_us.json",
                    "source_type": "json",
                    "key_count": 50,
                    "priority": 1
                },
                {
                    "namespace": "test_mod",
                    "locale": "zh_cn",
                    "source_path": "/lang/zh_cn.json",
                    "source_type": "json",
                    "key_count": 25,
                    "priority": 2
                }
            ],
            "total_mods": 1,
            "total_language_files": 2,
            "total_translatable_keys": 75,
            "supported_locales": ["en_us", "zh_cn"],
            "warnings": ["某些模组缺少中文翻译文件"],
            "errors": []
        }
    }
    return mock_result

thtools_app.include_router(scan_router)
print("✅ Basic scan endpoints added")

# Try to load other routers
try:
    from mc_l10n.adapters.api.routes import router
    thtools_app.include_router(router, prefix="/api/v1")
    print("✅ Main API routes loaded")
except Exception as e:
    print(f"❌ Failed to load main routes: {e}")
    
try:
    from mc_l10n.adapters.api.local_data_routes import router as local_data_router
    thtools_app.include_router(local_data_router, prefix="/api/v1")
    print("✅ Local data routes loaded")
except Exception as e:
    print(f"❌ Failed to load local data routes: {e}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host="0.0.0.0", port = 18000, reload=DEBUG, log_level=LOG_LEVEL.lower()
    )
