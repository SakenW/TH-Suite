"""
API请求日志中间件

记录所有API请求和响应的详细信息
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from packages.core.framework.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """API请求日志中间件"""

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_request_body: bool = True,
        log_response_body: bool = False,
        max_body_size: int = 1024 * 1024,  # 1MB
        exclude_paths: list[str] = None,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求和响应日志"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 检查是否需要跳过日志
        if self._should_skip_logging(request):
            return await call_next(request)

        # 记录请求开始
        start_time = time.time()
        await self._log_request(request, request_id)

        # 处理请求
        try:
            response = await call_next(request)

            # 记录响应
            duration = time.time() - start_time
            await self._log_response(request, response, request_id, duration)

            return response

        except Exception as e:
            # 记录异常
            duration = time.time() - start_time
            await self._log_error(request, e, request_id, duration)
            raise

    def _should_skip_logging(self, request: Request) -> bool:
        """检查是否应该跳过日志记录"""
        path = request.url.path
        return any(excluded in path for excluded in self.exclude_paths)

    async def _log_request(self, request: Request, request_id: str):
        """记录请求信息"""
        try:
            # 基础请求信息
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")

            log_data = {
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": self._sanitize_headers(dict(request.headers)),
                "client_ip": client_ip,
                "user_agent": user_agent,
            }

            # 记录请求体（如果启用且有内容）
            if self.log_request_body and request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await request.body()
                    if body and len(body) <= self.max_body_size:
                        # 尝试解码为文本
                        try:
                            body_text = body.decode("utf-8")
                            # 敏感信息脱敏
                            body_text = self._sanitize_request_body(body_text)
                            log_data["request_body"] = body_text
                        except UnicodeDecodeError:
                            log_data["request_body"] = (
                                f"<binary_data:{len(body)}_bytes>"
                            )
                    elif len(body) > self.max_body_size:
                        log_data["request_body"] = f"<large_body:{len(body)}_bytes>"
                except Exception as e:
                    log_data["request_body_error"] = str(e)

            logger.info(
                f"API请求开始: {request.method} {request.url.path}", extra=log_data
            )

        except Exception as e:
            logger.error(f"记录请求日志失败: {str(e)}")

    async def _log_response(
        self, request: Request, response: Response, request_id: str, duration: float
    ):
        """记录响应信息"""
        try:
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_headers": self._sanitize_headers(dict(response.headers)),
            }

            # 记录响应体（如果启用）
            if self.log_response_body and hasattr(response, "body"):
                try:
                    if hasattr(response.body, "decode"):
                        body_text = response.body.decode("utf-8")
                        if len(body_text) <= self.max_body_size:
                            log_data["response_body"] = body_text
                        else:
                            log_data["response_body"] = (
                                f"<large_response:{len(body_text)}_chars>"
                            )
                except Exception as e:
                    log_data["response_body_error"] = str(e)

            # 根据状态码选择日志级别
            if response.status_code >= 500:
                logger.error(
                    f"API请求完成: {request.method} {request.url.path} - 服务器错误",
                    extra=log_data,
                )
            elif response.status_code >= 400:
                logger.warning(
                    f"API请求完成: {request.method} {request.url.path} - 客户端错误",
                    extra=log_data,
                )
            else:
                logger.info(
                    f"API请求完成: {request.method} {request.url.path} - 成功",
                    extra=log_data,
                )

        except Exception as e:
            logger.error(f"记录响应日志失败: {str(e)}")

    async def _log_error(
        self, request: Request, error: Exception, request_id: str, duration: float
    ):
        """记录错误信息"""
        try:
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "duration_ms": round(duration * 1000, 2),
            }

            logger.error(
                f"API请求异常: {request.method} {request.url.path} - {type(error).__name__}",
                extra=log_data,
            )

        except Exception as e:
            logger.error(f"记录错误日志失败: {str(e)}")

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 优先从代理头中获取真实IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 使用连接IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def _sanitize_headers(self, headers: dict) -> dict:
        """敏感请求头脱敏"""
        sensitive_headers = {
            "authorization",
            "x-api-key",
            "cookie",
            "set-cookie",
            "x-auth-token",
            "x-access-token",
            "x-csrf-token",
        }

        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in sensitive_headers:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_request_body(self, body_text: str) -> str:
        """敏感请求体内容脱敏"""
        import json
        import re

        try:
            # 尝试解析为JSON并脱敏敏感字段
            data = json.loads(body_text)
            if isinstance(data, dict):
                sanitized_data = self._sanitize_json_data(data)
                return json.dumps(sanitized_data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            pass

        # 如果不是JSON，使用正则表达式脱敏
        # 脱敏密码字段
        body_text = re.sub(
            r'("password"\s*:\s*")[^"]*(")',
            r"\1***REDACTED***\2",
            body_text,
            flags=re.IGNORECASE,
        )

        # 脱敏token字段
        body_text = re.sub(
            r'("(?:token|api_?key|secret)"\s*:\s*")[^"]*(")',
            r"\1***REDACTED***\2",
            body_text,
            flags=re.IGNORECASE,
        )

        return body_text

    def _sanitize_json_data(self, data: dict) -> dict:
        """递归脱敏JSON数据中的敏感字段"""
        sensitive_keys = {
            "password",
            "pwd",
            "secret",
            "token",
            "key",
            "api_key",
            "apikey",
            "access_token",
            "refresh_token",
            "auth_token",
            "csrf_token",
        }

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_json_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_json_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized
