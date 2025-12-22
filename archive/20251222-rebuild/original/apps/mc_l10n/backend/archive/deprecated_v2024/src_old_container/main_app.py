"""
MC L10n 主应用
集成所有组件的FastAPI应用
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from adapters.api.routes import facade_routes
from container import get_container
from infrastructure.event_bus import get_event_bus
from infrastructure.event_handlers import EventHandlerRegistry

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting MC L10n application...")

    # 启动时初始化
    container = get_container()

    # 启动事件总线
    event_bus = get_event_bus()
    event_bus.start()

    # 注册事件处理器
    event_registry = EventHandlerRegistry(
        mod_repository=container.get_repository("mod"),
        project_repository=container.get_repository("project"),
    )
    event_registry.start()

    logger.info("Application started successfully")

    yield

    # 关闭时清理
    logger.info("Shutting down MC L10n application...")

    event_bus.stop()
    container.cleanup()

    logger.info("Application shutdown complete")


# 创建FastAPI应用
app = FastAPI(
    title="MC L10n API",
    description="Minecraft Mod Localization Service",
    version="6.0.0",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An error occurred",
        },
    )


# 注册路由
app.include_router(facade_routes.router)


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        container = get_container()
        stats = container.get_stats()

        return {
            "status": "healthy",
            "services": len(stats.get("services", [])),
            "repositories": len(stats.get("repositories", [])),
            "initialized": stats.get("initialized", False),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "MC L10n API",
        "version": "6.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }


# API文档配置
app.openapi_tags = [
    {
        "name": "Facade API",
        "description": "Simplified unified interface for all operations",
    },
    {"name": "Scan", "description": "Mod scanning operations"},
    {"name": "Translation", "description": "Translation management"},
    {"name": "Project", "description": "Project management"},
    {"name": "Sync", "description": "Synchronization with server"},
    {"name": "Quality", "description": "Quality management"},
]


if __name__ == "__main__":
    import uvicorn

    # 开发服务器配置
    uvicorn.run(
        "main_app:app", host="0.0.0.0", port=18000, reload=True, log_level="info"
    )
