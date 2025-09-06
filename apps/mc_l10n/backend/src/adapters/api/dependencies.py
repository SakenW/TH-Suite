"""
FastAPI依赖注入
提供依赖注入函数
"""

from typing import Generator, Any
from functools import lru_cache
import logging

from container import get_container, get_service, get_repository
from application.services.scan_service import ScanService
from domain.repositories import (
    ModRepository,
    TranslationProjectRepository,
    TranslationRepository,
    EventRepository,
    ScanResultRepository,
    CacheRepository
)

logger = logging.getLogger(__name__)


def get_mod_repository() -> ModRepository:
    """获取Mod仓储实例"""
    return get_repository('mod')


def get_project_repository() -> TranslationProjectRepository:
    """获取项目仓储实例"""
    return get_repository('project')


def get_translation_repository() -> TranslationRepository:
    """获取翻译仓储实例"""
    return get_repository('translation')


def get_event_repository() -> EventRepository:
    """获取事件仓储实例"""
    return get_repository('event')


def get_scan_result_repository() -> ScanResultRepository:
    """获取扫描结果仓储实例"""
    return get_repository('scan_result')


def get_cache_repository() -> CacheRepository:
    """获取缓存仓储实例"""
    return get_repository('cache')


def get_scan_service() -> ScanService:
    """获取扫描服务实例"""
    return get_service('scan')


def get_translation_service():
    """获取翻译服务实例"""
    return get_service('translation_service')


def get_project_service():
    """获取项目服务实例"""
    # TODO: 当ProjectService实现后更新
    # return get_service('project')
    return None


def get_sync_service():
    """获取同步服务实例"""
    # TODO: 当SyncService实现后更新
    # return get_service('sync')
    return None


def get_query_service():
    """获取查询服务实例"""
    # TODO: 当QueryService实现后更新
    # return get_service('query')
    return None


def get_mod_service():
    """获取模组服务实例（用于命令处理）"""
    # TODO: 当ModService实现后更新
    # return get_service('mod')
    return None


# 清理函数
def cleanup_services():
    """清理所有服务实例"""
    container = get_container()
    container.cleanup()
    logger.info("All services cleaned up")


# 健康检查
def check_dependencies_health() -> dict:
    """检查所有依赖的健康状态"""
    container = get_container()
    stats = container.get_stats()
    
    health = {
        'database': False,
        'cache': False,
        'services': {},
        'container': stats
    }
    
    try:
        # 检查数据库
        mod_repo = get_mod_repository()
        health['database'] = mod_repo.count() >= 0
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    try:
        # 检查缓存
        cache = get_cache_repository()
        cache.set("health_check", "ok", ttl=1)
        health['cache'] = cache.get("health_check") == "ok"
        
        if 'cache_stats' in stats:
            health['cache_stats'] = stats['cache_stats']
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
    
    # 检查服务状态
    health['services'] = {
        'initialized': len(stats.get('services', [])) > 0,
        'available': stats.get('services', [])
    }
    
    return health