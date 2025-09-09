"""
V6中间件聚合模块
统一管理和配置所有V6中间件
"""
from typing import List
from fastapi import FastAPI
from .idempotency import IdempotencyMiddleware
from .ndjson import NDJSONMiddleware
from .etag import ETagMiddleware
from .compression import CompressionMiddleware
import structlog

logger = structlog.get_logger(__name__)


class V6MiddlewareConfig:
    """V6中间件配置"""
    
    def __init__(
        self,
        enable_idempotency: bool = True,
        enable_ndjson: bool = True,
        enable_etag: bool = True,
        enable_compression: bool = True,
        idempotency_ttl: int = 3600,
        enable_weak_etag: bool = True,
        compression_level: int = 6,
        min_compression_size: int = 1024
    ):
        self.enable_idempotency = enable_idempotency
        self.enable_ndjson = enable_ndjson
        self.enable_etag = enable_etag
        self.enable_compression = enable_compression
        self.idempotency_ttl = idempotency_ttl
        self.enable_weak_etag = enable_weak_etag
        self.compression_level = compression_level
        self.min_compression_size = min_compression_size


def setup_v6_middlewares(app: FastAPI, config: V6MiddlewareConfig = None):
    """
    为FastAPI应用设置V6中间件
    
    Args:
        app: FastAPI应用实例
        config: 中间件配置，None时使用默认配置
    """
    if config is None:
        config = V6MiddlewareConfig()
    
    middlewares_added = []
    
    # 压缩中间件 (最外层 - 最后执行)
    if config.enable_compression:
        app.add_middleware(
            CompressionMiddleware,
            min_response_size=config.min_compression_size,
            compression_level=config.compression_level,
            enable_dictionary=True
        )
        middlewares_added.append("Compression")
        logger.info("已启用压缩中间件", 
                   level=config.compression_level,
                   min_size=config.min_compression_size)
    
    # ETag中间件 
    if config.enable_etag:
        app.add_middleware(
            ETagMiddleware,
            enable_weak_etag=config.enable_weak_etag
        )
        middlewares_added.append("ETag")
        logger.info("已启用ETag版本控制中间件", weak_etag=config.enable_weak_etag)
    
    # NDJSON中间件
    if config.enable_ndjson:
        app.add_middleware(NDJSONMiddleware)
        middlewares_added.append("NDJSON")
        logger.info("已启用NDJSON流处理中间件")
    
    # 幂等性中间件 (最内层 - 最先执行)
    if config.enable_idempotency:
        app.add_middleware(
            IdempotencyMiddleware,
            ttl_seconds=config.idempotency_ttl
        )
        middlewares_added.append("Idempotency")
        logger.info("已启用幂等性中间件", ttl_seconds=config.idempotency_ttl)
    
    logger.info(f"V6中间件设置完成，已启用: {', '.join(middlewares_added)}")
    
    return middlewares_added


# 中间件状态监控
def get_middleware_stats() -> dict:
    """获取中间件统计信息"""
    from .idempotency import get_cache_stats
    
    return {
        "idempotency": get_cache_stats(),
        "ndjson": {
            "status": "active"
        },
        "etag": {
            "status": "active"
        }
    }


# 清理函数
def cleanup_middleware_resources():
    """清理中间件资源"""
    from .idempotency import cleanup_expired_cache
    
    try:
        cleanup_expired_cache()
        logger.info("中间件资源清理完成")
    except Exception as e:
        logger.error("中间件资源清理失败", error=str(e))


# 中间件健康检查
def check_middleware_health() -> dict:
    """检查中间件健康状态"""
    health = {
        "status": "healthy",
        "middlewares": {
            "idempotency": "active",
            "ndjson": "active", 
            "etag": "active"
        },
        "issues": []
    }
    
    try:
        # 检查幂等性缓存
        cache_stats = get_cache_stats()
        if cache_stats["expired_entries"] > cache_stats["valid_entries"]:
            health["issues"].append("幂等性缓存中过期条目过多")
    except Exception as e:
        health["issues"].append(f"幂等性中间件检查失败: {str(e)}")
        health["middlewares"]["idempotency"] = "degraded"
    
    if health["issues"]:
        health["status"] = "degraded"
    
    return health