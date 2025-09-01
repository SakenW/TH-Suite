"""TransHub Tools Protocol Package.

OpenAPI Schema contracts for TransHub Tools.
Defines request/response schemas, data models, and WebSocket message types.
"""

# Request Schemas
# Response Schemas
# Data Schemas
# WebSocket Schemas
# Enums
from .schemas import (
    AppConfigSchema,
    BaseResponseSchema,
    BuildArtifactSchema,
    BuildMode,
    BuildRequestSchema,
    BuildResponseSchema,
    ErrorMessageSchema,
    ErrorResponseSchema,
    ExtractRequestSchema,
    ExtractResponseSchema,
    HealthCheckSchema,
    InventoryItemSchema,
    InventorySchema,
    JobResponseSchema,
    JobStatus,
    JobStatusResponseSchema,
    LogLevel,
    LogMessageSchema,
    ProgressMessageSchema,
    ScanRequestSchema,
    ScanResponseSchema,
    SegmentSchema,
    WebSocketMessageSchema,
)

# Validation
from .validation import (
    DataConverter,
    ProtocolConstants,
    ProtocolValidator,
    ValidationResult,
    normalize_data,
    validate_request,
)

# WebSocket Protocol
from .websocket import (
    JobStatusMessageSchema,
    SubscribeCommandSchema,
    SubscriptionType,
    WebSocketCommandSchema,
    WebSocketEventType,
    WebSocketProtocol,
    create_error_message,
    create_log_message,
    create_progress_message,
)


# Convenience validation functions
def validate_scan_request(data: dict) -> ValidationResult:
    """Validate scan request data."""
    return ProtocolValidator.validate_scan_request(data)


def validate_extract_request(data: dict) -> ValidationResult:
    """Validate extract request data."""
    return ProtocolValidator.validate_extract_request(data)


def validate_build_request(data: dict) -> ValidationResult:
    """Validate build request data."""
    return ProtocolValidator.validate_build_request(data)


# Data conversion utilities
def to_dict(schema_instance) -> dict:
    """Convert schema instance to dictionary."""
    return DataConverter.to_dict(schema_instance)


def from_dict(schema_class, data: dict):
    """Create schema instance from dictionary."""
    return DataConverter.from_dict(schema_class, data)


def to_json(schema_instance, **kwargs) -> str:
    """Convert schema instance to JSON string."""
    return DataConverter.to_json(schema_instance, **kwargs)


def from_json(schema_class, json_str: str):
    """Create schema instance from JSON string."""
    return DataConverter.from_json(schema_class, json_str)


__all__ = [
    # Request Schemas
    "ScanRequestSchema",
    "ExtractRequestSchema",
    "BuildRequestSchema",
    # Response Schemas
    "BaseResponseSchema",
    "ErrorResponseSchema",
    "JobResponseSchema",
    "ScanResponseSchema",
    "ExtractResponseSchema",
    "BuildResponseSchema",
    "JobStatusResponseSchema",
    "HealthCheckSchema",
    # Data Schemas
    "InventoryItemSchema",
    "InventorySchema",
    "SegmentSchema",
    "BuildArtifactSchema",
    "AppConfigSchema",
    # WebSocket Schemas
    "WebSocketMessageSchema",
    "ProgressMessageSchema",
    "LogMessageSchema",
    "ErrorMessageSchema",
    # WebSocket Protocol
    "WebSocketEventType",
    "SubscriptionType",
    "WebSocketCommandSchema",
    "SubscribeCommandSchema",
    "JobStatusMessageSchema",
    "WebSocketProtocol",
    "create_progress_message",
    "create_log_message",
    "create_error_message",
    # Validation
    "ValidationResult",
    "ProtocolValidator",
    "DataConverter",
    "ProtocolConstants",
    "validate_request",
    "normalize_data",
    # Enums
    "JobStatus",
    "LogLevel",
    "BuildMode",
    # Utilities
    "validate_scan_request",
    "validate_extract_request",
    "validate_build_request",
    "to_dict",
    "from_dict",
    "to_json",
    "from_json",
]
