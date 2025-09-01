"""FastAPI application skeleton for TransHub Tools."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from packages.core.errors import THToolsError
from packages.core.framework.logging import get_logger, setup_logging

from .middleware import setup_middleware
from .websocket import WebSocketManager


class THToolsApp:
    """TransHub Tools FastAPI application wrapper."""

    def __init__(
        self,
        title: str = "TransHub Tools API",
        description: str = "API for TransHub Tools",
        version: str = "1.0.0",
        debug: bool = False,
        cors_origins: list[str] | None = None,
        log_level: str = "INFO",
        log_file: str | None = None,
    ):
        self.title = title
        self.description = description
        self.version = version
        self.debug = debug
        self.cors_origins = cors_origins or ["*"]
        self.log_level = log_level
        self.log_file = log_file

        # Initialize logging
        setup_logging(log_level=log_level, log_format="json" if not debug else "console")
        self.logger = get_logger("thtools.app")

        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager()

        # Create FastAPI app
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan manager."""
            self.logger.info("Starting TransHub Tools API", version=self.version)

            # Startup logic
            app.state.ws_manager = self.ws_manager
            app.state.logger = self.logger

            yield

            # Shutdown logic
            await self.ws_manager.disconnect_all()
            self.logger.info("TransHub Tools API shutdown complete")

        app = FastAPI(
            title=self.title,
            description=self.description,
            version=self.version,
            debug=self.debug,
            lifespan=lifespan,
        )

        # Setup middleware
        setup_middleware(app, cors_origins=self.cors_origins, debug=self.debug)

        # Add global exception handler
        @app.exception_handler(THToolsError)
        async def thtools_exception_handler(request: Request, exc: THToolsError):
            """Handle TransHub Tools specific exceptions."""
            self.logger.error(
                "THTools error occurred",
                error_type=type(exc).__name__,
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
                    },
                    "timestamp": exc.timestamp.isoformat(),
                },
            )

        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle general exceptions."""
            self.logger.error(
                "Unhandled exception occurred",
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
                    },
                },
            )

        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "version": self.version, "service": self.title}

        # WebSocket endpoint for real-time updates
        @app.websocket("/ws")
        async def websocket_endpoint(websocket):
            """WebSocket endpoint for real-time communication."""
            await self.ws_manager.connect(websocket)

        return app

    def include_router(self, router, **kwargs):
        """Include a router in the application."""
        self.app.include_router(router, **kwargs)

    def add_middleware(self, middleware_class, **kwargs):
        """Add middleware to the application."""
        self.app.add_middleware(middleware_class, **kwargs)

    def mount(self, path: str, app, name: str | None = None):
        """Mount a sub-application."""
        self.app.mount(path, app, name)

    def get_openapi_schema(self) -> dict[str, Any]:
        """Get OpenAPI schema for the application."""
        if self.app.openapi_schema:
            return self.app.openapi_schema

        openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            description=self.description,
            routes=self.app.routes,
        )

        # Add custom schema extensions
        openapi_schema["info"]["x-logo"] = {"url": "https://transhub.tools/logo.png"}

        self.app.openapi_schema = openapi_schema
        return openapi_schema

    def run(self, host: str = "127.0.0.1", port: int = 8000, **kwargs):
        """Run the application using uvicorn."""
        import uvicorn

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_config=None,  # Use our custom logging
            **kwargs,
        )


def create_app(
    title: str = "TransHub Tools API",
    description: str = "API for TransHub Tools",
    version: str = "1.0.0",
    debug: bool = False,
    cors_origins: list[str] | None = None,
    log_level: str = "INFO",
    log_file: str | None = None,
) -> THToolsApp:
    """Create a TransHub Tools application instance.

    Args:
        title: Application title
        description: Application description
        version: Application version
        debug: Enable debug mode
        cors_origins: Allowed CORS origins
        log_level: Logging level
        log_file: Log file path

    Returns:
        Configured THToolsApp instance
    """
    return THToolsApp(
        title=title,
        description=description,
        version=version,
        debug=debug,
        cors_origins=cors_origins,
        log_level=log_level,
        log_file=log_file,
    )
