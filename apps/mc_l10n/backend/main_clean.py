#!/usr/bin/env python
"""
MC L10n FastAPI应用主入口
清理版本 - 使用统一的数据库模块
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.staticfiles import StaticFiles

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入数据库模块
from database import (
    database_router,
    ScanDatabaseService,
    LocalDatabaseManager,
    DataSyncService,
    OfflineChangeTracker
)

# 全局服务实例
services = {
    'scan': None,
    'database': None,
    'sync': None,
    'tracker': None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在启动 MC L10n 服务...")
    
    try:
        # 初始化服务
        db_path = os.getenv("DATABASE_PATH", "mc_l10n_local.db")
        
        # 初始化数据库管理器
        services['database'] = LocalDatabaseManager(db_path)
        services['database'].initialize_database()
        
        # 初始化扫描服务
        services['scan'] = ScanDatabaseService(db_path)
        
        # 初始化同步服务
        services['sync'] = DataSyncService(db_path)
        await services['sync'].initialize()
        
        # 初始化离线跟踪器
        services['tracker'] = OfflineChangeTracker(db_path)
        
        logger.info("✅ 所有服务初始化完成")
        
        yield
        
    finally:
        # 清理资源
        logger.info("正在关闭服务...")
        
        if services['scan']:
            services['scan'].close()
            
        if services['sync']:
            await services['sync'].close()
            
        logger.info("服务已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="MC L10n API",
    description="Minecraft本地化工具API - 清理版",
    version="6.0.0",
    lifespan=lifespan,
    docs_url=None,  # 自定义文档路径
    redoc_url=None
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(database_router, prefix="/api")

# 自定义文档端点
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义Swagger UI"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc文档"""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js",
    )

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "6.0.0",
        "services": {
            "scan": services['scan'] is not None,
            "database": services['database'] is not None,
            "sync": services['sync'] is not None,
            "tracker": services['tracker'] is not None
        }
    }

# 根路径
@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "MC L10n API",
        "version": "6.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

# 获取服务实例（供其他模块使用）
def get_scan_service():
    """获取扫描服务实例"""
    if not services['scan']:
        raise HTTPException(status_code=503, detail="Scan service not available")
    return services['scan']

def get_database_service():
    """获取数据库服务实例"""
    if not services['database']:
        raise HTTPException(status_code=503, detail="Database service not available")
    return services['database']

def get_sync_service():
    """获取同步服务实例"""
    if not services['sync']:
        raise HTTPException(status_code=503, detail="Sync service not available")
    return services['sync']

def get_tracker_service():
    """获取离线跟踪服务实例"""
    if not services['tracker']:
        raise HTTPException(status_code=503, detail="Tracker service not available")
    return services['tracker']

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main_clean:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )