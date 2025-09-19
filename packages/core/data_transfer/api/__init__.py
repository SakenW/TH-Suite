"""
翻译数据传输API模块

提供RESTful API和WebSocket实时通信接口
"""

from .models import (
    ApplyRequest,
    ApplyResponse,
    BatchRequest,
    BatchResponse,
    ConflictNotificationMessage,
    DiffRequest,
    DiffResponse,
    ErrorMessage,
    ExtractRequest,
    ExtractResponse,
    ProjectStatusMessage,
    StatusResponse,
    SyncProgressMessage,
    SyncRequest,
    SyncResponse,
    TranslationUpdateMessage,
    WebSocketMessage,
    create_conflict_notification_message,
    create_error_message,
    create_sync_progress_message,
    create_translation_update_message,
)
from .routers import router

__all__ = [
    # 路由
    "router",
    
    # 请求响应模型
    "ExtractRequest",
    "ExtractResponse",
    "SyncRequest", 
    "SyncResponse",
    "DiffRequest",
    "DiffResponse",
    "ApplyRequest",
    "ApplyResponse",
    "StatusResponse",
    "BatchRequest",
    "BatchResponse",
    
    # WebSocket消息模型
    "WebSocketMessage",
    "TranslationUpdateMessage",
    "SyncProgressMessage",
    "ConflictNotificationMessage",
    "ProjectStatusMessage",
    "ErrorMessage",
    
    # 工厂函数
    "create_translation_update_message",
    "create_sync_progress_message",
    "create_conflict_notification_message",
    "create_error_message",
]