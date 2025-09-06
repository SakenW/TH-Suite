"""
日志中间件
记录请求和响应信息
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import logging
import time
import json
from typing import List

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    日志记录中间件
    
    记录HTTP请求和响应的详细信息
    """
    
    def __init__(
        self, 
        app, 
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: List[str] = None
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or []
    
    async def dispatch(self, request: Request, call_next):
        """处理请求和响应"""
        
        # 检查是否需要排除此路径
        if any(path in str(request.url.path) for path in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        
        # 记录请求信息
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client": str(request.client.host) if request.client else "unknown"
        }
        
        # 记录请求体（如果启用）
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_info["body"] = body.decode('utf-8')
            except Exception as e:
                request_info["body_error"] = str(e)
        
        logger.info(f"请求开始: {request.method} {request.url.path}")
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录响应信息
        response_info = {
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2)
        }
        
        # 记录响应体（如果启用且不是流式响应）
        if self.log_response_body and not isinstance(response, StreamingResponse):
            try:
                # 这里需要小心处理，避免消费响应体
                pass  # 为了安全起见，暂时不记录响应体
            except Exception as e:
                response_info["body_error"] = str(e)
        
        # 记录完整的请求-响应日志
        logger.info(
            f"请求完成: {request.method} {request.url.path} - "
            f"状态码: {response.status_code} - "
            f"耗时: {response_info['process_time_ms']}ms"
        )
        
        return response