"""Response utilities for TransHub Tools FastAPI applications."""

from datetime import datetime
from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from packages.core.models import JobStatus


class THToolsResponse(BaseModel):
    """Standard response format for TransHub Tools APIs."""

    success: bool
    data: Any | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    timestamp: datetime

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProgressResponse(THToolsResponse):
    """Progress update response."""

    def __init__(
        self,
        job_id: str,
        status: JobStatus,
        progress: float,
        message: str,
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(
            success=True,
            data={
                "job_id": job_id,
                "status": status.value,
                "progress": min(max(progress, 0.0), 100.0),  # Clamp between 0-100
                "message": message,
                "details": details or {},
            },
            **kwargs,
        )


class ErrorResponse(THToolsResponse):
    """Error response."""

    def __init__(
        self,
        error_type: str,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(
            success=False,
            error={
                "type": error_type,
                "message": message,
                "code": code or "UNKNOWN_ERROR",
                "details": details or {},
            },
            **kwargs,
        )


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""

    def __init__(
        self, message: str, field_errors: list[dict[str, Any]] | None = None, **kwargs
    ):
        super().__init__(
            error_type="ValidationError",
            message=message,
            code="VALIDATION_ERROR",
            details={"field_errors": field_errors or []},
            **kwargs,
        )


class JobResponse(THToolsResponse):
    """Job-related response."""

    def __init__(
        self,
        job_id: str,
        status: JobStatus,
        result: Any | None = None,
        message: str | None = None,
        **kwargs,
    ):
        super().__init__(
            success=status not in [JobStatus.FAILED, JobStatus.CANCELLED],
            data={
                "job_id": job_id,
                "status": status.value,
                "result": result,
                "message": message,
            },
            **kwargs,
        )


def create_success_response(
    data: Any = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    """Create a successful response.

    Args:
        data: Response data
        message: Optional success message
        metadata: Optional metadata
        status_code: HTTP status code

    Returns:
        JSON response
    """
    response_data = THToolsResponse(success=True, data=data, metadata=metadata or {})

    if message:
        response_data.metadata["message"] = message

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump(mode="json")
    )


def create_error_response(
    error_type: str,
    message: str,
    code: str | None = None,
    details: dict[str, Any] | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """Create an error response.

    Args:
        error_type: Type of error
        message: Error message
        code: Error code
        details: Additional error details
        status_code: HTTP status code

    Returns:
        JSON response
    """
    response_data = ErrorResponse(
        error_type=error_type, message=message, code=code, details=details
    )

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump(mode="json")
    )


def create_validation_error_response(
    message: str,
    field_errors: list[dict[str, Any]] | None = None,
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
) -> JSONResponse:
    """Create a validation error response.

    Args:
        message: Validation error message
        field_errors: List of field-specific errors
        status_code: HTTP status code

    Returns:
        JSON response
    """
    response_data = ValidationErrorResponse(message=message, field_errors=field_errors)

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump(mode="json")
    )


def create_progress_response(
    job_id: str,
    status: JobStatus,
    progress: float,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    """Create a progress update response.

    Args:
        job_id: Job identifier
        status: Current job status
        progress: Progress percentage (0-100)
        message: Progress message
        details: Additional progress details
        status_code: HTTP status code

    Returns:
        JSON response
    """
    response_data = ProgressResponse(
        job_id=job_id,
        status=status,
        progress=progress,
        message=message,
        details=details,
    )

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump(mode="json")
    )


def create_job_response(
    job_id: str,
    job_status: JobStatus,
    result: Any | None = None,
    message: str | None = None,
    status_code: int | None = None,
) -> JSONResponse:
    """Create a job-related response.

    Args:
        job_id: Job identifier
        job_status: Job status
        result: Job result data
        message: Optional message
        status_code: HTTP status code (auto-determined if None)

    Returns:
        JSON response
    """
    if status_code is None:
        if job_status == JobStatus.COMPLETED:
            status_code = status.HTTP_200_OK
        elif job_status == JobStatus.FAILED:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif job_status == JobStatus.CANCELLED:
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_202_ACCEPTED

    response_data = JobResponse(
        job_id=job_id, status=job_status, result=result, message=message
    )

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump(mode="json")
    )


def create_not_found_response(
    resource: str, identifier: str | None = None
) -> JSONResponse:
    """Create a not found response.

    Args:
        resource: Type of resource not found
        identifier: Resource identifier

    Returns:
        JSON response
    """
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"

    return create_error_response(
        error_type="NotFoundError",
        message=message,
        code="NOT_FOUND",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def create_unauthorized_response(
    message: str = "Authentication required",
) -> JSONResponse:
    """Create an unauthorized response.

    Args:
        message: Unauthorized message

    Returns:
        JSON response
    """
    return create_error_response(
        error_type="UnauthorizedError",
        message=message,
        code="UNAUTHORIZED",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def create_forbidden_response(message: str = "Access denied") -> JSONResponse:
    """Create a forbidden response.

    Args:
        message: Forbidden message

    Returns:
        JSON response
    """
    return create_error_response(
        error_type="ForbiddenError",
        message=message,
        code="FORBIDDEN",
        status_code=status.HTTP_403_FORBIDDEN,
    )


def create_conflict_response(
    message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    """Create a conflict response.

    Args:
        message: Conflict message
        details: Additional conflict details

    Returns:
        JSON response
    """
    return create_error_response(
        error_type="ConflictError",
        message=message,
        code="CONFLICT",
        details=details,
        status_code=status.HTTP_409_CONFLICT,
    )


def create_rate_limit_response(
    message: str = "Rate limit exceeded", retry_after: int | None = None
) -> JSONResponse:
    """Create a rate limit response.

    Args:
        message: Rate limit message
        retry_after: Seconds to wait before retrying

    Returns:
        JSON response
    """
    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)

    response = create_error_response(
        error_type="RateLimitError",
        message=message,
        code="RATE_LIMIT_EXCEEDED",
        details={"retry_after": retry_after} if retry_after else None,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )

    # Add headers to response
    for key, value in headers.items():
        response.headers[key] = value

    return response
