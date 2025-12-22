#!/usr/bin/env python3
"""
RW Studio Backend Application

RimWorld 模组管理工具的后端服务
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.backend_kit import create_app, setup_logging
from packages.core.logging import get_logger
from packages.protocol.websocket import WebSocketManager

from .api import router as api_router
from .services import (
    ConfigService,
    ModService,
    SaveGameService,
    WorkshopService,
)
from .websocket import websocket_router

# 配置日志
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting RW Studio Backend...")

    # 初始化服务
    try:
        # 初始化各种服务
        mod_service = ModService()
        workshop_service = WorkshopService()
        save_game_service = SaveGameService()
        config_service = ConfigService()

        # 将服务添加到应用状态
        app.state.mod_service = mod_service
        app.state.workshop_service = workshop_service
        app.state.save_game_service = save_game_service
        app.state.config_service = config_service

        # 初始化 WebSocket 管理器
        app.state.websocket_manager = WebSocketManager()

        logger.info("RW Studio Backend started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start RW Studio Backend: {e}")
        raise
    finally:
        logger.info("Shutting down RW Studio Backend...")
        # 清理资源
        if hasattr(app.state, "websocket_manager"):
            await app.state.websocket_manager.disconnect_all()


def create_rw_studio_app() -> FastAPI:
    """创建 RW Studio 应用实例"""

    app = create_app(
        title="RW Studio API",
        description="RimWorld 模组管理工具 API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生产环境中应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/ws")

    return app


app = create_rw_studio_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True, log_level="info")
