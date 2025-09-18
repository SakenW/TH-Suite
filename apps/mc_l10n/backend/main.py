"""
MC L10n FastAPI应用主入口点

启动Minecraft本地化工具的后端API服务
基于Clean Architecture和依赖注入模式重构
"""

import os
import sqlite3
import sys
from contextlib import asynccontextmanager
from typing import Any

# 导入依赖注入容器
# 导入中间件和路由
from api.middleware.cors_config import setup_cors
from api.middleware.error_handler import setup_error_handlers
from api.middleware.logging_middleware import LoggingMiddleware
from api.routes import transhub  # TransHub 集成路由
from api.routes.mod_routes import router as mod_router
from api.routes.project_routes import router as project_router
from api.routes.scan_routes import router as scan_router
from api.routes.translation_routes import router as translation_router
# V5架构新增路由
from api.routes.pack_routes import router as pack_router
from api.routes.queue_routes import router as queue_router
from api.routes.sync_routes import router as sync_router
from api.routes.cache_routes import router as cache_router
from api.routes.optimized_scan_routes import router as optimized_scan_router
from api.routes.low_memory_scan_routes import router as low_memory_scan_router
# from api.v6.router import v6_router  # V6 API路由 - 暂时禁用
# from api.v6.middleware.middleware import setup_v6_middlewares, V6MiddlewareConfig  # V6中间件 - 暂时禁用
from core.di_container import (
    get_database_service,
    get_infrastructure_service,
    initialize_container,
)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

# 导入工具类
from utils.process_manager import setup_process_manager
from utils.simple_logging import StructLogFactory

# 旧工作队列处理器已移除，使用新架构的ScanSessionManager

# 导入多层缓存服务
from infrastructure.services.multi_layer_cache_service import initialize_cache_service, cleanup_cache_service

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

logger = StructLogFactory.get_logger(__name__)

# 全局状态管理
active_scans: dict[str, dict[str, Any]] = {}


# 数据模型
class ScanRequest(BaseModel):
    directory: str
    incremental: bool = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 使用依赖注入容器"""
    # 启动时执行
    logger.info("MC L10n API服务启动中...")

    try:
        # 初始化依赖注入容器
        logger.info("初始化依赖注入容器...")
        await initialize_container()

        # 通过容器获取服务并初始化
        logger.info("初始化数据库服务...")
        db_service = get_database_service()
        if db_service:
            await db_service.initialize()

        logger.info("初始化基础设施服务...")
        infra_service = get_infrastructure_service()
        if infra_service:
            await infra_service.initialize()

        # 旧工作队列处理器已移除，新架构使用ScanSessionManager自带的Worker管理
        logger.info("新架构已启用，扫描功能由ScanSessionManager管理")

        # 初始化多层缓存服务
        logger.info("初始化多层缓存服务...")
        await initialize_cache_service()
        logger.info("多层缓存服务已启动")

        logger.info("MC L10n API服务启动完成")

        yield  # 应用运行期间

    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    finally:
        # 关闭时执行
        logger.info("MC L10n API服务关闭中...")

        # 旧工作队列处理器已移除
        logger.info("新架构清理：无需停止旧工作队列处理器")

        # 停止多层缓存服务
        try:
            await cleanup_cache_service()
            logger.info("多层缓存服务已停止")
        except Exception as e:
            logger.warning(f"停止多层缓存服务时出错: {e}")

        # 通过容器清理资源
        infra_service = get_infrastructure_service()
        if infra_service:
            await infra_service.cleanup()

        logger.info("MC L10n API服务关闭完成")


# 创建FastAPI应用实例
def create_app() -> FastAPI:
    """创建并配置FastAPI应用"""

    # 从环境变量获取配置
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "production").lower()

    # 创建应用实例
    app = FastAPI(
        title="MC L10n API",
        description="Minecraft本地化工具后端API服务",
        version="1.0.0",
        debug=debug_mode,
        lifespan=lifespan,
        docs_url=None,  # 自定义文档路径
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )

    # 设置CORS
    setup_cors(app)

    # 设置全局错误处理
    setup_error_handlers(app)

    # 添加V6中间件 - 暂时禁用，V6模块不存在
    # v6_middleware_config = V6MiddlewareConfig(
    #     enable_idempotency=False,  # 暂时禁用
    #     enable_ndjson=False,       # 暂时禁用
    #     enable_etag=False,         # 暂时禁用
    #     enable_compression=False,  # 暂时禁用
    #     idempotency_ttl=3600,
    #     enable_weak_etag=False
    # )
    # setup_v6_middlewares(app, v6_middleware_config)

    # 添加日志中间件
    app.add_middleware(
        LoggingMiddleware,
        log_request_body=False,  # 暂时禁用请求体日志，避免请求体读取冲突
        log_response_body=debug_mode,
        exclude_paths=[
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/openapi.json",
            "/api/v6/",  # V6 API路径也排除详细日志
        ],
    )

    # 注册路由
    # V6 API路由 - 暂时禁用，模块不存在
    # app.include_router(v6_router)
    
    # 现有路由 (兼容性保留)
    app.include_router(project_router)
    app.include_router(mod_router)
    app.include_router(scan_router)
    app.include_router(translation_router)
    app.include_router(transhub.router)  # Trans-Hub集成路由
    
    # V5架构新路由
    app.include_router(pack_router)      # 整合包管理
    app.include_router(queue_router)     # 工作队列管理
    app.include_router(sync_router)      # 同步协议管理
    app.include_router(cache_router)     # 多层缓存管理
    app.include_router(optimized_scan_router)  # 优化扫描功能
    app.include_router(low_memory_scan_router)  # 低内存扫描功能

    # 注册本地数据管理路由 (已移除，待迁移到新结构)

    # 添加数据库统计路由 - 使用应用服务
    @app.get("/api/database/statistics")
    async def get_database_statistics():
        """获取数据库统计信息"""
        from application.services.scan_application_service import ScanApplicationService

        scan_service = ScanApplicationService()
        return await scan_service.get_database_statistics()

    # 添加全局的扫描结果路由 - 使用应用服务
    @app.get("/scan-results/{scan_id}")
    async def get_scan_results_global(scan_id: str):
        """获取扫描结果（全局路由）"""
        from application.services.scan_application_service import ScanApplicationService

        scan_service = ScanApplicationService()
        result = await scan_service.get_scan_results(scan_id)

        if not result["success"]:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND" if "不存在" in result["message"] else "ERROR",
                    "message": result["message"],
                },
            }

        # 转换为兼容格式
        data = result["data"]
        statistics = data.get("statistics", {})
        return {
            "success": True,
            "data": {
                "scan_id": scan_id,
                "status": "completed",
                "statistics": statistics,
                "total_mods": statistics.get("total_mods", 0),
                "total_language_files": statistics.get("total_language_files", 0),
                "total_keys": statistics.get("total_keys", 0),
                "entries": {},
                "errors": [],
                "warnings": [],
            },
        }

    # 数据库初始化已由依赖注入容器处理
    
    # 兼容性路由已移除 - 参见 archive/version_cleanup_20250916/

    # V1兼容性路由已清理完毕 - 已归档至 archive/version_cleanup_20250916/

    # 添加健康检查端点
    @app.get("/health", tags=["系统"], summary="健康检查")
    async def health_check() -> dict[str, Any]:
        """健康检查端点"""
        return {
            "status": "healthy",
            "service": "mc-l10n-api",
            "version": "1.0.0",
            "environment": environment,
            "timestamp": "2024-12-30T12:00:00",  # 简化实现
        }

    # 添加系统信息端点
    @app.get("/info", tags=["系统"], summary="系统信息")
    async def system_info() -> dict[str, Any]:
        """系统信息端点"""
        import platform

        return {
            "service": {
                "name": "MC L10n API",
                "version": "1.0.0",
                "environment": environment,
                "debug_mode": debug_mode,
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
            },
            "api": {
                "total_routes": len(app.routes),
                "cors_enabled": True,
                "error_handling": True,
                "request_logging": True,
            },
        }

    # 自定义OpenAPI文档
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="MC L10n API",
            version="1.0.0",
            description="""
# Minecraft本地化工具API

这是一个用于Minecraft模组和资源包本地化的完整API服务。

## 功能特性

### 🎯 项目管理
- 创建和管理翻译项目
- 项目配置和设置
- 项目进度统计

### 📦 模组管理
- 扫描和分析JAR/文件夹
- 解析模组元数据
- 依赖关系管理

### 🌐 翻译管理
- 翻译条目提取
- 多格式导入/导出
- 批量翻译操作
- 翻译进度跟踪

### 🔍 搜索功能
- 项目搜索
- 模组搜索
- 翻译内容搜索

## API版本

当前版本: **v1.0.0**

所有API端点都以 `/api/v1/` 开头。

## 认证

目前API处于开发阶段，暂不需要认证。生产环境将使用JWT token认证。

## 响应格式

所有API响应都遵循统一格式：

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "request_id": "req_12345678"
}
```

错误响应格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  },
  "request_id": "req_12345678"
}
```
            """,
            routes=app.routes,
        )

        # 添加自定义信息
        openapi_schema["info"]["x-logo"] = {
            "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # 自定义文档页面
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.0/bundles/redoc.standalone.js",
        )

    return app


# 创建应用实例
app = create_app()


# 启动配置
if __name__ == "__main__":
    import uvicorn

    # 设置进程管理器，自动清理旧进程
    try:
        # 检查是否有--kill-all参数
        kill_all = "--kill-all" in sys.argv
        if kill_all:
            sys.argv.remove("--kill-all")
        setup_process_manager(kill_all=kill_all)
        logger.info("进程管理器已启动")
    except Exception as e:
        logger.warning(f"进程管理器启动失败: {e}")

    # 从环境变量获取配置，使用不常见的端口避免冲突
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "18000"))  # 使用18000端口，避免与其他服务冲突
    debug = os.getenv("DEBUG", "false").lower() == "true"
    reload = os.getenv("RELOAD", "true" if debug else "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))

    logger.info(f"启动MC L10n API服务: http://{host}:{port}")
    logger.info(f"调试模式: {debug}, 自动重载: {reload}, 工作进程: {workers}")
    logger.info(f"API文档: http://{host}:{port}/docs")
    logger.info(f"ReDoc文档: http://{host}:{port}/redoc")

    # 启动服务器
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not debug else 1,  # 调试模式下只使用1个工作进程
        access_log=True,
        use_colors=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(asctime)s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["default"],
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": "INFO",
                    "handlers": ["default"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": "INFO",
                    "handlers": ["access"],
                    "propagate": False,
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        },
    )
