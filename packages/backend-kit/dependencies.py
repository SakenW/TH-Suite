"""Dependency injection utilities for TransHub Tools FastAPI applications."""

import os
import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from packages.core.database import SQLCipherDatabase
from packages.core.framework.logging import get_logger as core_get_logger
from packages.core.models import JobStatus
from packages.core.state import State, StateMachine

from .websocket import WebSocketManager, get_websocket_manager


class JobContext(BaseModel):
    """Context for a job execution."""

    job_id: str
    request_id: str
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = {}
    created_at: datetime

    def __init__(self, **data):
        if "job_id" not in data:
            data["job_id"] = str(uuid.uuid4())
        if "request_id" not in data:
            data["request_id"] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow()
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True


# Global state machines cache
_state_machines: dict[str, StateMachine] = {}

# Global job contexts cache
_job_contexts: dict[str, JobContext] = {}


def get_logger_dependency(name: str = "thtools.api"):
    """Create a logger dependency.

    Args:
        name: Logger name

    Returns:
        Logger dependency function
    """

    def _get_logger() -> structlog.BoundLogger:
        return core_get_logger(name)

    return _get_logger


# Default logger dependency
get_logger = get_logger_dependency()


def get_request_id(request: Request) -> str:
    """Get or generate request ID from request.

    Args:
        request: FastAPI request object

    Returns:
        Request ID
    """
    # Try to get from request state (set by middleware)
    if hasattr(request.state, "request_id"):
        return request.state.request_id

    # Try to get from headers
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        return request_id

    # Generate new one
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


def get_user_id(request: Request) -> str | None:
    """Get user ID from request (placeholder for authentication).

    Args:
        request: FastAPI request object

    Returns:
        User ID if authenticated, None otherwise
    """
    # This is a placeholder - implement actual authentication logic
    # For now, try to get from headers or return None
    return request.headers.get("X-User-ID")


def get_session_id(request: Request) -> str | None:
    """Get session ID from request.

    Args:
        request: FastAPI request object

    Returns:
        Session ID if available
    """
    # Try to get from headers
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        return session_id

    # Try to get from cookies
    return request.cookies.get("session_id")


def create_job_context(
    request: Request,
    request_id: str = Depends(get_request_id),
    user_id: str | None = Depends(get_user_id),
    session_id: str | None = Depends(get_session_id),
) -> JobContext:
    """Create a job context for the current request.

    Args:
        request: FastAPI request object
        request_id: Request ID
        user_id: User ID (if authenticated)
        session_id: Session ID (if available)

    Returns:
        Job context
    """
    context = JobContext(
        request_id=request_id,
        user_id=user_id,
        session_id=session_id,
        metadata={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )

    # Cache the context
    _job_contexts[context.job_id] = context

    return context


def get_job_context(job_id: str) -> JobContext | None:
    """Get a cached job context by ID.

    Args:
        job_id: Job ID

    Returns:
        Job context if found, None otherwise
    """
    return _job_contexts.get(job_id)


def cleanup_job_context(job_id: str):
    """Clean up a job context from cache.

    Args:
        job_id: Job ID to clean up
    """
    _job_contexts.pop(job_id, None)
    _state_machines.pop(job_id, None)


def get_state_machine(job_id: str | None = None) -> StateMachine:
    """Get or create a state machine for a job.

    Args:
        job_id: Job ID (if None, creates a new state machine)

    Returns:
        State machine instance
    """
    if job_id is None:
        # Create a new state machine
        return StateMachine()

    # Get or create cached state machine
    if job_id not in _state_machines:
        state_machine = StateMachine()

        # Setup common transitions for job processing
        state_machine.add_transition(
            State.IDLE,
            State.SCANNING,
            condition=lambda ctx: True,
            action=lambda ctx: ctx.update({"status": JobStatus.RUNNING}),
        )

        state_machine.add_transition(
            State.SCANNING,
            State.EXTRACTING,
            condition=lambda ctx: ctx.get("scan_complete", False),
            action=lambda ctx: ctx.update({"scan_complete": True}),
        )

        state_machine.add_transition(
            State.EXTRACTING,
            State.VALIDATING,
            condition=lambda ctx: ctx.get("extract_complete", False),
            action=lambda ctx: ctx.update({"extract_complete": True}),
        )

        state_machine.add_transition(
            State.VALIDATING,
            State.BUILDING,
            condition=lambda ctx: ctx.get("validation_complete", False),
            action=lambda ctx: ctx.update({"validation_complete": True}),
        )

        state_machine.add_transition(
            State.BUILDING,
            State.COMPLETED,
            condition=lambda ctx: ctx.get("build_complete", False),
            action=lambda ctx: ctx.update(
                {"build_complete": True, "status": JobStatus.COMPLETED}
            ),
        )

        # Error transitions from any state
        for state in [
            State.SCANNING,
            State.EXTRACTING,
            State.VALIDATING,
            State.BUILDING,
        ]:
            state_machine.add_transition(
                state,
                State.FAILED,
                condition=lambda ctx: ctx.get("error") is not None,
                action=lambda ctx: ctx.update({"status": JobStatus.FAILED}),
            )

        # Cancel transitions from any state
        for state in [
            State.SCANNING,
            State.EXTRACTING,
            State.VALIDATING,
            State.BUILDING,
        ]:
            state_machine.add_transition(
                state,
                State.CANCELLED,
                condition=lambda ctx: ctx.get("cancelled", False),
                action=lambda ctx: ctx.update({"status": JobStatus.CANCELLED}),
            )

        _state_machines[job_id] = state_machine

    return _state_machines[job_id]


def get_websocket_manager_dependency() -> WebSocketManager:
    """Get WebSocket manager dependency.

    Returns:
        WebSocket manager instance
    """
    return get_websocket_manager()


def require_job_context(job_id: str) -> JobContext:
    """Require a job context to exist.

    Args:
        job_id: Job ID

    Returns:
        Job context

    Raises:
        HTTPException: If job context not found
    """
    context = get_job_context(job_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"Job context not found: {job_id}")
    return context


def validate_job_ownership(
    job_id: str, current_user_id: str | None = Depends(get_user_id)
) -> JobContext:
    """Validate that the current user owns the job.

    Args:
        job_id: Job ID
        current_user_id: Current user ID

    Returns:
        Job context

    Raises:
        HTTPException: If job not found or access denied
    """
    context = require_job_context(job_id)

    # If no authentication is required, allow access
    if current_user_id is None and context.user_id is None:
        return context

    # Check ownership
    if context.user_id != current_user_id:
        raise HTTPException(
            status_code=403, detail="Access denied: You don't own this job"
        )

    return context


# Global database instance
_database: SQLCipherDatabase | None = None


def get_database() -> SQLCipherDatabase:
    """Get SQLCipher database instance.

    Returns:
        SQLCipher database instance
    """
    global _database

    if _database is None:
        # Get database configuration from environment
        db_path = os.getenv("DATABASE_PATH", "./data/app.db")
        db_password = os.getenv(
            "DATABASE_PASSWORD", "default_secure_password_change_in_production"
        )

        # Create database instance
        logger = core_get_logger("database")
        _database = SQLCipherDatabase(db_path, db_password, logger)

        logger.info("SQLCipher database initialized", db_path=db_path)

    return _database


def get_database_dependency() -> SQLCipherDatabase:
    """Database dependency for FastAPI.

    Returns:
        SQLCipher database instance
    """
    return get_database()


# Convenience dependencies
JobContextDep = Depends(create_job_context)
LoggerDep = Depends(get_logger)
DatabaseDep = Depends(get_database_dependency)
StateMachineDep = Depends(get_state_machine)
WebSocketManagerDep = Depends(get_websocket_manager_dependency)
