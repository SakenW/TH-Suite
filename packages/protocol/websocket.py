"""TransHub Tools WebSocket Protocol.

WebSocket message types and handlers for real-time communication.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .schemas import (
    ErrorMessageSchema,
    JobStatus,
    LogLevel,
    LogMessageSchema,
    ProgressMessageSchema,
    WebSocketMessageSchema,
)


class WebSocketEventType(str, Enum):
    """WebSocket event types."""

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PROGRESS = "progress"
    LOG = "log"
    ERROR = "error"
    JOB_STATUS = "job_status"
    HEARTBEAT = "heartbeat"


class SubscriptionType(str, Enum):
    """WebSocket subscription types."""

    JOB = "job"
    LOGS = "logs"
    PROGRESS = "progress"
    ALL = "all"


class WebSocketCommandSchema(BaseModel):
    """Base schema for WebSocket commands."""

    command: str = Field(..., description="Command type")
    data: dict[str, Any] | None = Field(None, description="Command data")
    request_id: str | None = Field(None, description="Request identifier")


class SubscribeCommandSchema(WebSocketCommandSchema):
    """Schema for subscription commands."""

    command: str = Field("subscribe", description="Command type")
    subscription_type: SubscriptionType = Field(..., description="Subscription type")
    job_id: str | None = Field(
        None, description="Job ID for job-specific subscriptions"
    )
    filters: dict[str, Any] | None = Field(None, description="Subscription filters")


class JobStatusMessageSchema(WebSocketMessageSchema):
    """Schema for job status update messages."""

    type: str = Field("job_status", description="Message type")
    status: JobStatus = Field(..., description="Job status")
    progress: int | None = Field(None, description="Progress percentage")
    current_step: str | None = Field(None, description="Current operation step")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    result: dict[str, Any] | None = Field(None, description="Job result data")
    error: str | None = Field(None, description="Error message if failed")


def create_progress_message(
    job_id: str, progress: int, message: str, timestamp: datetime | None = None
) -> ProgressMessageSchema:
    """Create a progress update message."""
    return ProgressMessageSchema(
        job_id=job_id,
        progress=progress,
        message=message,
        timestamp=timestamp or datetime.now(),
    )


def create_log_message(
    level: LogLevel,
    message: str,
    job_id: str | None = None,
    logger_name: str | None = None,
    extra: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> LogMessageSchema:
    """Create a log message."""
    return LogMessageSchema(
        job_id=job_id,
        level=level,
        message=message,
        logger_name=logger_name,
        extra=extra,
        timestamp=timestamp or datetime.now(),
    )


def create_error_message(
    error_type: str,
    error_code: str,
    message: str,
    job_id: str | None = None,
    details: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> ErrorMessageSchema:
    """Create an error message."""
    return ErrorMessageSchema(
        job_id=job_id,
        error_type=error_type,
        error_code=error_code,
        message=message,
        details=details,
        timestamp=timestamp or datetime.now(),
    )


class WebSocketProtocol:
    """WebSocket protocol constants and utilities."""

    VERSION = "1.0"
    HEARTBEAT_INTERVAL = 30
    CONNECTION_TIMEOUT = 300
    MAX_MESSAGE_SIZE = 1024 * 1024

    MESSAGE_TYPES = {
        "progress": ProgressMessageSchema,
        "log": LogMessageSchema,
        "error": ErrorMessageSchema,
        "job_status": JobStatusMessageSchema,
    }
