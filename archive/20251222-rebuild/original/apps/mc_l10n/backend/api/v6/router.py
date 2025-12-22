"""
V6 API路由聚合模块
统一注册所有V6 API端点
"""
from fastapi import APIRouter

# 导入所有V6 API模块
from .database.statistics import router as database_router
from .entities.packs import router as packs_router
from .entities.mods import router as mods_router
from .entities.language_files import router as language_files_router
from .entities.translations import router as translations_router
from .queue.tasks import router as queue_router
from .settings.config import router as settings_router
from .cache.management import router as cache_router
from .sync.sync_endpoints import router as sync_router

# 创建V6 API主路由器
v6_router = APIRouter(prefix="/api/v6", tags=["V6 API"])

# 注册所有子路由
v6_router.include_router(database_router)
v6_router.include_router(packs_router)
v6_router.include_router(mods_router)  
v6_router.include_router(language_files_router)
v6_router.include_router(translations_router)
v6_router.include_router(queue_router)
v6_router.include_router(settings_router)
v6_router.include_router(cache_router)
v6_router.include_router(sync_router)


@v6_router.get("/")
async def v6_api_info():
    """V6 API信息"""
    return {
        "name": "MC L10n V6 API",
        "version": "6.0.0",
        "description": "基于V6架构的Minecraft本地化工具API",
        "features": [
            "键级差量同步",
            "内容寻址存储", 
            "工作队列管理",
            "实体管理(Pack、MOD、语言文件、翻译条目)",
            "缓存和性能优化",
            "统计和监控",
            "Bloom过滤器同步协议",
            "UIDA统一标识符"
        ],
        "endpoints": {
            "database": "/api/v6/database",
            "packs": "/api/v6/packs",
            "mods": "/api/v6/mods", 
            "language_files": "/api/v6/language-files",
            "translations": "/api/v6/translations",
            "queue": "/api/v6/queue",
            "settings": "/api/v6/settings",
            "cache": "/api/v6/cache",
            "sync": "/api/v6/sync"
        },
        "documentation": "/docs"
    }


@v6_router.get("/health")
async def v6_health_check():
    """V6 API健康检查"""
    return {
        "status": "healthy",
        "version": "6.0.0",
        "timestamp": "2025-09-10T02:40:00Z",
        "components": {
            "database": "operational",
            "cache": "operational", 
            "queue": "operational"
        }
    }