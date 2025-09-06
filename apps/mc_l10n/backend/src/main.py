"""
MC L10n 主入口
基于六边形架构的FastAPI应用
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 加载环境变量
load_dotenv()

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入路由
from adapters.api.routes import scan_routes, mod_routes
from adapters.api.dependencies import cleanup_services, check_dependencies_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 Starting MC L10n Service (Hexagonal Architecture)...")
    
    try:
        # 初始化检查
        health = check_dependencies_health()
        logger.info(f"Health check: {health}")
        
        yield
        
    finally:
        # 清理资源
        logger.info("Shutting down services...")
        cleanup_services()
        logger.info("Services shutdown complete")


# 创建FastAPI应用
app = FastAPI(
    title="MC L10n API",
    description="Minecraft Localization Tool - Hexagonal Architecture Edition",
    version="6.0.0",
    lifespan=lifespan
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
app.include_router(scan_routes.router, prefix="/api/v1")
app.include_router(mod_routes.router, prefix="/api/v1")

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    health = check_dependencies_health()
    
    is_healthy = health.get('database', False) and health.get('cache', False)
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": "6.0.0",
        "architecture": "hexagonal",
        "details": health
    }

# 根路径
@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "MC L10n API",
        "version": "6.0.0",
        "architecture": "Hexagonal Architecture",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api": {
            "v1": {
                "scan": "/api/v1/scan",
                "mods": "/api/v1/mods"
            }
        }
    }

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "type": exc.__class__.__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )