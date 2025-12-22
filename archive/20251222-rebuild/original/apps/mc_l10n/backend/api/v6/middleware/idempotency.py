"""
V6 幂等性中间件
实现基于X-Idempotency-Key的幂等操作支持
"""
import hashlib
import blake3
import json
import time
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)

# 幂等性缓存 - 实际实现中应该使用Redis或数据库
_idempotency_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 3600  # 1小时幂等窗口


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    幂等性中间件
    
    支持的HTTP方法: POST, PUT, PATCH
    幂等键来源: X-Idempotency-Key 头部
    幂等窗口: 60分钟
    """
    
    def __init__(self, app, ttl_seconds: int = 3600):
        super().__init__(app)
        self.ttl_seconds = ttl_seconds
        
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求的幂等性检查"""
        
        # 只对写操作进行幂等性检查
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)
        
        # 获取幂等键
        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            # 没有幂等键，正常处理
            return await call_next(request)
        
        # 生成缓存键
        cache_key = self._generate_cache_key(request, idempotency_key)
        
        # 检查是否已处理过相同请求
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.info("返回幂等缓存响应", 
                       idempotency_key=idempotency_key, 
                       cache_key=cache_key)
            return self._build_response_from_cache(cached_response)
        
        # 处理新请求
        try:
            response = await call_next(request)
            
            # 缓存成功的响应 (状态码 200-299)
            if 200 <= response.status_code < 300:
                await self._cache_response(cache_key, response)
                
            return response
            
        except Exception as e:
            logger.error("处理幂等请求时发生错误", 
                        idempotency_key=idempotency_key, 
                        error=str(e))
            raise
    
    def _generate_cache_key(self, request: Request, idempotency_key: str) -> str:
        """生成缓存键"""
        # 包含方法、路径和幂等键
        key_data = f"{request.method}:{request.url.path}:{idempotency_key}"
        return blake3.blake3(key_data.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的响应"""
        if cache_key not in _idempotency_cache:
            return None
            
        cached_data = _idempotency_cache[cache_key]
        
        # 检查是否过期
        if time.time() - cached_data["timestamp"] > self.ttl_seconds:
            del _idempotency_cache[cache_key]
            return None
            
        return cached_data
    
    async def _cache_response(self, cache_key: str, response: Response):
        """缓存响应"""
        try:
            # 读取响应体
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
                
            # 尝试解析为JSON
            try:
                response_data = json.loads(response_body.decode())
            except:
                response_data = response_body.decode()
            
            # 缓存响应信息
            _idempotency_cache[cache_key] = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_data,
                "timestamp": time.time()
            }
            
            # 重新创建响应体迭代器
            response.body_iterator = iter([response_body])
            
        except Exception as e:
            logger.warning("缓存响应失败", cache_key=cache_key, error=str(e))
    
    def _build_response_from_cache(self, cached_data: Dict[str, Any]) -> Response:
        """从缓存构建响应"""
        headers = cached_data["headers"].copy()
        
        # 添加幂等性标识头
        headers["X-Idempotency-Cached"] = "true"
        headers["X-Cache-Timestamp"] = str(int(cached_data["timestamp"]))
        
        if isinstance(cached_data["body"], dict):
            return JSONResponse(
                content=cached_data["body"],
                status_code=cached_data["status_code"],
                headers=headers
            )
        else:
            return Response(
                content=cached_data["body"],
                status_code=cached_data["status_code"],
                headers=headers
            )


def cleanup_expired_cache():
    """清理过期的幂等性缓存"""
    current_time = time.time()
    expired_keys = []
    
    for key, data in _idempotency_cache.items():
        if current_time - data["timestamp"] > _cache_ttl:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _idempotency_cache[key]
    
    if expired_keys:
        logger.info(f"清理了 {len(expired_keys)} 个过期的幂等性缓存项")


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    current_time = time.time()
    valid_count = 0
    expired_count = 0
    
    for data in _idempotency_cache.values():
        if current_time - data["timestamp"] <= _cache_ttl:
            valid_count += 1
        else:
            expired_count += 1
    
    return {
        "total_entries": len(_idempotency_cache),
        "valid_entries": valid_count,
        "expired_entries": expired_count,
        "cache_hit_ratio": 0.0  # 需要实际统计
    }