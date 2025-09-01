"""
全局错误处理中间件

统一处理API异常和错误响应格式
"""

import traceback

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from packages.core.framework.logging import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """自定义API错误基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class BusinessError(APIError):
    """业务逻辑错误"""

    def __init__(
        self, message: str, error_code: str = "BUSINESS_ERROR", details: dict = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ValidationError(APIError):
    """验证错误"""

    def __init__(self, message: str, field_errors: dict = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field_errors": field_errors} if field_errors else {},
        )


class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, message: str, resource_type: str = None):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type} if resource_type else {},
        )


class ConflictError(APIError):
    """资源冲突错误"""

    def __init__(self, message: str, conflict_reason: str = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details={"conflict_reason": conflict_reason} if conflict_reason else {},
        )


class AuthenticationError(APIError):
    """认证错误"""

    def __init__(self, message: str = "认证失败"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(APIError):
    """授权错误"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RateLimitError(APIError):
    """请求限流错误"""

    def __init__(self, message: str = "请求过于频繁", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


def create_error_response(
    message: str,
    error_code: str = "UNKNOWN_ERROR",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: dict = None,
    request_id: str = None,
) -> JSONResponse:
    """创建标准错误响应"""
    error_response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
    }

    if details:
        error_response["error"]["details"] = details

    if request_id:
        error_response["request_id"] = request_id

    # 添加响应头
    headers = {"Content-Type": "application/json"}
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=status_code, content=error_response, headers=headers
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """处理自定义API错误"""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        f"API错误: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
        },
    )

    return create_error_response(
        message=exc.message,
        error_code=exc.error_code,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
    )


async def http_exception_handler(
    request: Request, exc: HTTPException | StarletteHTTPException
) -> JSONResponse:
    """处理HTTP异常"""
    request_id = getattr(request.state, "request_id", None)

    # 根据状态码确定错误代码
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if hasattr(exc, "detail") else "HTTP错误"

    # 记录错误日志
    log_level = "warning" if exc.status_code < 500 else "error"
    getattr(logger, log_level)(
        f"HTTP异常: {exc.status_code} - {message}",
        extra={
            "request_id": request_id,
            "error_code": error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return create_error_response(
        message=message,
        error_code=error_code,
        status_code=exc.status_code,
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证错误"""
    request_id = getattr(request.state, "request_id", None)

    # 格式化验证错误信息
    field_errors = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = {
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input"),
        }

    logger.warning(
        f"请求验证失败: {len(field_errors)} 个字段错误",
        extra={
            "request_id": request_id,
            "error_code": "VALIDATION_ERROR",
            "path": request.url.path,
            "method": request.method,
            "field_errors": field_errors,
        },
    )

    return create_error_response(
        message="请求参数验证失败",
        error_code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"field_errors": field_errors},
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常"""
    request_id = getattr(request.state, "request_id", None)

    # 记录详细的异常信息
    logger.error(
        f"未处理的异常: {type(exc).__name__} - {str(exc)}",
        extra={
            "request_id": request_id,
            "error_code": "INTERNAL_SERVER_ERROR",
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )

    # 在开发环境中可以返回详细错误信息
    import os

    is_development = os.getenv("ENVIRONMENT", "production").lower() in (
        "development",
        "dev",
        "local",
    )

    if is_development:
        details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc().split("\n"),
        }
        message = f"服务器内部错误: {str(exc)}"
    else:
        details = None
        message = "服务器内部错误，请稍后重试"

    return create_error_response(
        message=message,
        error_code="INTERNAL_SERVER_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        request_id=request_id,
    )


def setup_error_handlers(app):
    """设置全局错误处理器"""
    # 自定义API错误
    app.add_exception_handler(APIError, api_error_handler)

    # HTTP异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 验证错误
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # 通用异常处理器（必须放在最后）
    app.add_exception_handler(Exception, generic_exception_handler)
