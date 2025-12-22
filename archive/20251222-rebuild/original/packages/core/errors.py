"""
Common error types for the core package.

This module provides standardized error types that can be used across
the application for consistent error handling.
"""

from typing import Any, Optional


class ProcessingError(Exception):
    """Error that occurs during file or data processing."""

    def __init__(
        self, message: str, file_path: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.details = details or {}


class ValidationError(Exception):
    """Error that occurs during data validation."""

    def __init__(self, message: str, field_errors: Optional[dict[str, list[str]]] = None):
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or {}


class ConfigurationError(Exception):
    """Error related to application configuration."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.config_key = config_key


class ModParsingError(ProcessingError):
    """Error that occurs during MOD file parsing."""

    pass


class ProjectError(Exception):
    """General project-related error."""

    def __init__(self, message: str, project_path: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.project_path = project_path


class UnsupportedProjectTypeError(ProjectError):
    """Error raised when project type is not supported."""

    pass


class ProjectAlreadyExistsError(ProjectError):
    """Error raised when trying to create a project that already exists."""

    pass


class ScanError(Exception):
    """Error that occurs during scanning operations."""

    def __init__(self, message: str, scan_path: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.scan_path = scan_path


class FileParsingError(ProcessingError):
    """Error that occurs during file parsing operations."""

    pass


class UnsupportedFileFormatError(FileParsingError):
    """Error raised when file format is not supported."""

    pass


class EntityNotFoundError(Exception):
    """Error raised when an entity is not found."""

    def __init__(self, message: str, entity_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.entity_id = entity_id


class RepositoryError(Exception):
    """Error that occurs in repository operations."""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.operation = operation


class ProjectScanError(ScanError):
    """Error that occurs during project scanning operations."""

    pass


class THToolsError(Exception):
    """Base error class for TH Tools."""

    def __init__(
        self, message: str, error_code: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
