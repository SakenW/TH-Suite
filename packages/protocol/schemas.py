"""TransHub Tools Protocol Schemas.

Pydantic schemas for API requests, responses, and data models.
These schemas define the contract between frontend and backend.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class LogLevel(str, Enum):
    """Log message levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BuildMode(str, Enum):
    """Resource pack build modes."""

    RESOURCE_PACK = "resource_pack"
    OVERRIDES = "overrides"


# Request Schemas


class ScanRequestSchema(BaseModel):
    """Schema for directory scan requests."""

    directory: str = Field(..., description="Directory path to scan")
    recursive: bool = Field(True, description="Whether to scan recursively")
    include_patterns: list[str] | None = Field(
        None, description="File patterns to include (regex)"
    )
    exclude_patterns: list[str] | None = Field(
        None, description="File patterns to exclude (regex)"
    )
    output_file: str | None = Field(
        None, description="Output file path for inventory (optional)"
    )

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v):
        if not v or not v.strip():
            raise ValueError("Directory path cannot be empty")
        return v.strip()


class ExtractRequestSchema(BaseModel):
    """Schema for translation extraction requests."""

    inventory_file: str = Field(..., description="Path to inventory JSON file")
    output_file: str | None = Field(
        None, description="Output file path for segments (optional)"
    )
    locales: list[str] | None = Field(
        None, description="Target locales to extract (all if not specified)"
    )
    validate_keys: bool = Field(
        True, description="Whether to validate translation keys for consistency"
    )

    @field_validator("inventory_file")
    @classmethod
    def validate_inventory_file(cls, v):
        if not v or not v.strip():
            raise ValueError("Inventory file path cannot be empty")
        return v.strip()


class BuildRequestSchema(BaseModel):
    """Schema for resource pack build requests."""

    segments_file: str = Field(..., description="Path to segments JSON file")
    output_path: str = Field(..., description="Output directory path")
    mode: BuildMode = Field(..., description="Build mode")
    target_locales: list[str] | None = Field(
        None, description="Target locales to build (all if not specified)"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Additional metadata for the build"
    )

    @field_validator("segments_file")
    @classmethod
    def validate_segments_file(cls, v):
        if not v or not v.strip():
            raise ValueError("Segments file path cannot be empty")
        return v.strip()

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v):
        if not v or not v.strip():
            raise ValueError("Output path cannot be empty")
        return v.strip()


# Response Schemas


class BaseResponseSchema(BaseModel):
    """Base response schema."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


class ErrorResponseSchema(BaseResponseSchema):
    """Schema for error responses."""

    success: bool = Field(False, description="Always false for errors")
    error_type: str = Field(..., description="Type of error")
    error_code: str = Field(..., description="Machine-readable error code")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class JobResponseSchema(BaseResponseSchema):
    """Schema for job-related responses."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    result: dict[str, Any] | None = Field(None, description="Job result data")


class ScanResponseSchema(JobResponseSchema):
    """Schema for scan operation responses."""

    pass


class ExtractResponseSchema(JobResponseSchema):
    """Schema for extract operation responses."""

    pass


class BuildResponseSchema(JobResponseSchema):
    """Schema for build operation responses."""

    pass


class JobStatusResponseSchema(JobResponseSchema):
    """Schema for job status query responses."""

    progress: int | None = Field(None, description="Progress percentage (0-100)")
    current_step: str | None = Field(None, description="Current operation step")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    error: str | None = Field(None, description="Error message if failed")


# Data Schemas


class InventoryItemSchema(BaseModel):
    """Schema for inventory items."""

    modid: str = Field(..., description="Mod identifier")
    locale: str = Field(..., description="Language locale code")
    path: str = Field(..., description="File path")
    hash: str = Field(..., description="File content hash")
    format: str = Field(..., description="File format (json, lang, etc.)")
    size: int = Field(..., description="File size in bytes")

    @field_validator("modid")
    @classmethod
    def validate_modid(cls, v):
        if not v or not v.strip():
            raise ValueError("Mod ID cannot be empty")
        return v.strip().lower()

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v):
        if not v or not v.strip():
            raise ValueError("Locale cannot be empty")
        return v.strip().lower()


class InventorySchema(BaseModel):
    """Schema for file inventory."""

    version: str = Field("1.0", description="Inventory format version")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    total_files: int = Field(..., description="Total number of files")
    items: list[InventoryItemSchema] = Field(..., description="Inventory items")

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError("Inventory must contain at least one item")
        return v


class SegmentSchema(BaseModel):
    """Schema for translation segments."""

    modid: str = Field(..., description="Mod identifier")
    locale: str = Field(..., description="Language locale code")
    key: str = Field(..., description="Translation key")
    value: str = Field(..., description="Translation value")
    context: str | None = Field(None, description="Additional context")
    file_path: str | None = Field(None, description="Source file path")
    line_number: int | None = Field(None, description="Line number in source file")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v):
        if not v or not v.strip():
            raise ValueError("Translation key cannot be empty")
        return v.strip()


class BuildArtifactSchema(BaseModel):
    """Schema for build artifacts."""

    type: str = Field(..., description="Artifact type")
    path: str = Field(..., description="Artifact file path")
    size: int = Field(..., description="Artifact size in bytes")
    modid: str | None = Field(None, description="Associated mod ID")
    locale: str | None = Field(None, description="Associated locale")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


# WebSocket Message Schemas


class WebSocketMessageSchema(BaseModel):
    """Base schema for WebSocket messages."""

    type: str = Field(..., description="Message type")
    job_id: str | None = Field(None, description="Associated job ID")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )


class ProgressMessageSchema(WebSocketMessageSchema):
    """Schema for progress update messages."""

    type: str = Field("progress", description="Message type")
    progress: int = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Progress message")

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Progress must be between 0 and 100")
        return v


class LogMessageSchema(WebSocketMessageSchema):
    """Schema for log messages."""

    type: str = Field("log", description="Message type")
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    logger_name: str | None = Field(None, description="Logger name")
    extra: dict[str, Any] | None = Field(None, description="Additional log data")


class ErrorMessageSchema(WebSocketMessageSchema):
    """Schema for error messages."""

    type: str = Field("error", description="Message type")
    error_type: str = Field(..., description="Error type")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Error details")


# Health Check Schema


class HealthCheckSchema(BaseModel):
    """Schema for health check responses."""

    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str | None = Field(None, description="Service version")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Check timestamp"
    )
    details: dict[str, Any] | None = Field(
        None, description="Additional health details"
    )


# Configuration Schemas


class AppConfigSchema(BaseModel):
    """Schema for application configuration."""

    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")
    cors_origins: list[str] = Field(
        default_factory=list, description="CORS allowed origins"
    )
    max_file_size: int = Field(
        100 * 1024 * 1024, description="Maximum file size in bytes"
    )
    temp_dir: str | None = Field(None, description="Temporary directory path")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
