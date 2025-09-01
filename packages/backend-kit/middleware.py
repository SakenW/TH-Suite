"""Middleware components for TransHub Tools FastAPI applications."""

import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from packages.core.errors import THToolsError
from packages.core.framework.logging import get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    def __init__(self, app, logger_name: str = "thtools.middleware"):
        super().__init__(app)
        self.logger = get_logger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            self.logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                process_time=round(process_time, 4),
                response_size=response.headers.get("content-length"),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))

            return response

        except Exception as exc:
            # Calculate processing time for errors
            process_time = time.time() - start_time

            # Log error
            self.logger.error(
                "Request failed",
                request_id=request_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                process_time=round(process_time, 4),
                exc_info=True,
            )

            # Re-raise the exception to be handled by error handlers
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""

    def __init__(self, app, logger_name: str = "thtools.errors"):
        super().__init__(app)
        self.logger = get_logger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors and provide consistent error responses."""
        try:
            return await call_next(request)

        except THToolsError as exc:
            # Handle TransHub Tools specific errors
            request_id = getattr(request.state, "request_id", "unknown")

            self.logger.warning(
                "THTools error occurred",
                request_id=request_id,
                error_type=type(exc).__name__,
                error_code=exc.error_code,
                error_message=str(exc),
                path=request.url.path,
                method=request.method,
            )

            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "code": exc.error_code,
                        "request_id": request_id,
                    },
                    "timestamp": exc.timestamp.isoformat(),
                },
                headers={"X-Request-ID": request_id},
            )

        except Exception as exc:
            # Handle unexpected errors
            request_id = getattr(request.state, "request_id", "unknown")

            self.logger.error(
                "Unhandled exception occurred",
                request_id=request_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                path=request.url.path,
                method=request.method,
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "type": "InternalServerError",
                        "message": "An internal server error occurred",
                        "code": "INTERNAL_ERROR",
                        "request_id": request_id,
                    },
                },
                headers={"X-Request-ID": request_id},
            )


class CORSMiddleware:
    """CORS middleware wrapper with sensible defaults."""

    @staticmethod
    def setup(
        app: FastAPI,
        origins: list[str] = None,
        allow_credentials: bool = True,
        allow_methods: list[str] = None,
        allow_headers: list[str] = None,
    ):
        """Setup CORS middleware with defaults."""
        if origins is None:
            origins = ["*"]

        if allow_methods is None:
            allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

        if allow_headers is None:
            allow_headers = [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Request-ID",
                "X-Requested-With",
            ]

        app.add_middleware(
            FastAPICORSMiddleware,
            allow_origins=origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            expose_headers=["X-Request-ID", "X-Process-Time"],
        )


class SecurityMiddleware:
    """Security middleware for common security headers."""

    @staticmethod
    def setup(
        app: FastAPI, trusted_hosts: list[str] | None = None, force_https: bool = False
    ):
        """Setup security middleware."""
        # Add trusted host middleware if hosts are specified
        if trusted_hosts:
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

        # Add security headers middleware
        @app.middleware("http")
        async def add_security_headers(request: Request, call_next):
            response = await call_next(request)

            # Security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            if force_https:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )

            return response


def setup_middleware(
    app: FastAPI,
    cors_origins: list[str] | None = None,
    trusted_hosts: list[str] | None = None,
    debug: bool = False,
    enable_logging: bool = True,
    enable_error_handling: bool = True,
    enable_security: bool = True,
):
    """Setup all middleware for a TransHub Tools application.

    Args:
        app: FastAPI application instance
        cors_origins: Allowed CORS origins
        trusted_hosts: Trusted host names
        debug: Enable debug mode
        enable_logging: Enable request logging middleware
        enable_error_handling: Enable error handling middleware
        enable_security: Enable security middleware
    """
    # Setup middleware in reverse order (last added = first executed)

    # 1. Security middleware (outermost)
    if enable_security:
        SecurityMiddleware.setup(
            app, trusted_hosts=trusted_hosts, force_https=not debug
        )

    # 2. CORS middleware
    CORSMiddleware.setup(app, origins=cors_origins or ["*"])

    # 3. Error handling middleware
    if enable_error_handling:
        app.add_middleware(ErrorHandlingMiddleware)

    # 4. Logging middleware (innermost, closest to application)
    if enable_logging:
        app.add_middleware(LoggingMiddleware)
