"""TransHub Tools backend kit package.

Provides FastAPI skeleton, WebSocket middleware, and common backend utilities.
"""

from .app import THToolsApp, create_app
from .dependencies import JobContext, get_job_context, get_logger, get_state_machine
from .middleware import (
    CORSMiddleware,
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    setup_middleware,
)
from .responses import (
    THToolsResponse,
    create_error_response,
    create_progress_response,
    create_success_response,
)
from .websocket import (
    WebSocketConnection,
    WebSocketManager,
    broadcast_message,
    send_progress_update,
)

__all__ = [
    "create_app",
    "THToolsApp",
    "CORSMiddleware",
    "LoggingMiddleware",
    "ErrorHandlingMiddleware",
    "setup_middleware",
    "WebSocketManager",
    "WebSocketConnection",
    "broadcast_message",
    "send_progress_update",
    "get_logger",
    "get_state_machine",
    "get_job_context",
    "JobContext",
    "create_success_response",
    "create_error_response",
    "create_progress_response",
    "THToolsResponse",
]
