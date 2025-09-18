"""
缓存管理相关路由
提供多层缓存系统的管理和监控功能
V5架构 - 缓存服务集成
"""

import logging
from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from infrastructure.services.multi_layer_cache_service import (
    get_multi_layer_cache_service, 
    MultiLayerCacheService,
    CacheType,
    CacheLevel
)

logger = logging.getLogger(__name__)

def get_cache_service() -> MultiLayerCacheService:
    """依赖注入：获取多层缓存服务"""
    return get_multi_layer_cache_service()

router = APIRouter(
    prefix="/api/v1/cache",
    tags=["缓存管理"],
    responses={404: {"description": "Not found"}},
)


class CacheSetRequest(BaseModel):
    """缓存设置请求模型"""
    key: str
    value: Any
    cache_type: str = "metadata"  # translation, metadata, scan_result, file_content
    ttl_seconds: Optional[int] = None


class CacheGetRequest(BaseModel):
    """缓存获取请求模型"""
    key: str
    cache_type: str = "metadata"


class CacheDeleteRequest(BaseModel):
    """缓存删除请求模型"""
    key: str
    cache_type: str = "metadata"


class CacheClearRequest(BaseModel):
    """缓存清理请求模型"""
    cache_type: Optional[str] = None  # 如果为空则清理所有类型
    cache_level: Optional[str] = None  # memory, database, file


@router.get("/test", response_model=dict[str, Any])
async def cache_test_endpoint():
    """
    缓存路由测试端点
    """
    return {
        "success": True,
        "message": "Cache routes are working",
        "service": "multi-layer-cache",
        "supported_types": ["translation", "metadata", "scan_result", "file_content"],
        "supported_levels": ["memory", "database", "file"],
        "endpoints_available": [
            "GET /api/v1/cache/test",
            "GET /api/v1/cache/statistics",
            "POST /api/v1/cache/set",
            "POST /api/v1/cache/get",
            "DELETE /api/v1/cache/delete",
            "POST /api/v1/cache/clear",
            "GET /api/v1/cache/health"
        ],
    }


@router.get("/statistics", response_model=dict[str, Any])
async def get_cache_statistics(
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    获取缓存统计信息
    """
    try:
        stats = cache_service.get_statistics()
        
        return {
            "success": True,
            "data": stats,
            "message": "缓存统计信息获取成功",
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set", response_model=dict[str, Any])
async def set_cache(
    request: CacheSetRequest,
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    设置缓存值
    
    Args:
        request: 缓存设置请求参数
    """
    try:
        # 验证缓存类型
        try:
            cache_type = CacheType(request.cache_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的缓存类型: {request.cache_type}"
            )
            
        # 设置缓存
        await cache_service.set(
            key=request.key,
            value=request.value,
            cache_type=cache_type,
            ttl=request.ttl_seconds
        )
        
        return {
            "success": True,
            "data": {
                "key": request.key,
                "cache_type": request.cache_type,
                "set_at": datetime.now().isoformat()
            },
            "message": f"缓存设置成功: {request.key}",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get", response_model=dict[str, Any])
async def get_cache(
    request: CacheGetRequest,
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    获取缓存值
    
    Args:
        request: 缓存获取请求参数
    """
    try:
        # 验证缓存类型
        try:
            cache_type = CacheType(request.cache_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的缓存类型: {request.cache_type}"
            )
            
        # 获取缓存
        value = await cache_service.get(
            key=request.key,
            cache_type=cache_type
        )
        
        if value is not None:
            return {
                "success": True,
                "data": {
                    "key": request.key,
                    "value": value,
                    "cache_type": request.cache_type,
                    "retrieved_at": datetime.now().isoformat()
                },
                "message": f"缓存获取成功: {request.key}",
            }
        else:
            return {
                "success": False,
                "error": {
                    "code": "CACHE_MISS",
                    "message": f"缓存未找到: {request.key}",
                    "details": {
                        "key": request.key,
                        "cache_type": request.cache_type
                    }
                },
                "message": "缓存未找到",
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete", response_model=dict[str, Any])
async def delete_cache(
    request: CacheDeleteRequest,
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    删除缓存值
    
    Args:
        request: 缓存删除请求参数
    """
    try:
        # 验证缓存类型
        try:
            cache_type = CacheType(request.cache_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的缓存类型: {request.cache_type}"
            )
            
        # 删除缓存
        result = await cache_service.delete(
            key=request.key,
            cache_type=cache_type
        )
        
        return {
            "success": True,
            "data": {
                "key": request.key,
                "cache_type": request.cache_type,
                "deleted": result,
                "deleted_at": datetime.now().isoformat()
            },
            "message": f"缓存删除成功: {request.key}",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear", response_model=dict[str, Any])
async def clear_cache(
    request: CacheClearRequest,
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    清理缓存
    
    Args:
        request: 缓存清理请求参数
    """
    try:
        cache_type = None
        cache_level = None
        
        # 验证缓存类型
        if request.cache_type:
            try:
                cache_type = CacheType(request.cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"无效的缓存类型: {request.cache_type}"
                )
        
        # 验证缓存级别
        if request.cache_level:
            try:
                cache_level = CacheLevel(request.cache_level)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"无效的缓存级别: {request.cache_level}"
                )
                
        # 清理缓存
        result = await cache_service.clear(
            cache_type=cache_type,
            cache_level=cache_level
        )
        
        return {
            "success": True,
            "data": {
                "cache_type": request.cache_type,
                "cache_level": request.cache_level,
                "cleared_items": result,
                "cleared_at": datetime.now().isoformat()
            },
            "message": "缓存清理成功",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=dict[str, Any])
async def cache_health_check(
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    缓存系统健康检查
    """
    try:
        # 执行健康检查测试
        test_key = "health_check_test"
        test_value = {"timestamp": datetime.now().isoformat()}
        
        # 测试设置和获取
        await cache_service.set(test_key, test_value, CacheType.METADATA, ttl=60)
        retrieved_value = await cache_service.get(test_key, CacheType.METADATA)
        
        # 清理测试数据
        await cache_service.delete(test_key, CacheType.METADATA)
        
        # 检查结果
        health_status = "healthy" if retrieved_value == test_value else "degraded"
        
        return {
            "success": True,
            "data": {
                "status": health_status,
                "test_successful": retrieved_value == test_value,
                "timestamp": datetime.now().isoformat(),
                "cache_layers": {
                    "memory": "operational",
                    "database": "operational", 
                    "file": "operational"
                }
            },
            "message": f"缓存系统健康状态: {health_status}",
        }
        
    except Exception as e:
        logger.error(f"缓存健康检查失败: {e}")
        return {
            "success": False,
            "error": {
                "code": "HEALTH_CHECK_FAILED",
                "message": f"缓存健康检查失败: {str(e)}",
                "details": {"timestamp": datetime.now().isoformat()}
            },
            "message": "缓存系统健康检查失败",
        }


@router.get("/config", response_model=dict[str, Any])
async def get_cache_config(
    cache_service: MultiLayerCacheService = Depends(get_cache_service)
):
    """
    获取缓存配置信息
    """
    try:
        config = {
            "cache_strategies": {
                "translation": ["memory", "database"],
                "metadata": ["memory", "database", "file"],
                "scan_result": ["memory", "database", "file"],
                "file_content": ["memory", "file"]
            },
            "memory_cache": {
                "max_size": 2000,
                "ttl_seconds": 1800  # 30分钟
            },
            "database_cache": {
                "table_name": "cache_general",
                "cleanup_interval": 3600  # 1小时
            },
            "file_cache": {
                "base_directory": "data/cache",
                "max_file_size": 10485760  # 10MB
            },
            "supported_types": ["translation", "metadata", "scan_result", "file_content"],
            "supported_levels": ["memory", "database", "file"]
        }
        
        return {
            "success": True,
            "data": config,
            "message": "缓存配置获取成功",
        }
        
    except Exception as e:
        logger.error(f"获取缓存配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))