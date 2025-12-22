"""
Core data models shared across the application.

This module defines common data structures and models that are used
throughout the application for consistent data representation.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


@dataclass
class Segment:
    """Represents a translatable text segment."""

    key: str
    source_text: str
    target_text: str = ""
    context: str = ""
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FileInfo:
    """Basic file information."""

    path: Path
    size: int
    modified_time: datetime
    encoding: str = "utf-8"

    @classmethod
    def from_path(cls, path: Path) -> "FileInfo":
        """Create FileInfo from a file path."""
        stat = path.stat()
        return cls(
            path=path,
            size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
        )


@dataclass
class TranslationProject:
    """Represents a translation project."""

    id: str
    name: str
    source_language: str
    target_languages: list[str]
    project_path: Path
    created_at: datetime
    modified_at: datetime
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationResult:
    """Result of validation operations."""

    is_valid: bool
    errors: list[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)


class JobStatus(Enum):
    """Status of a background job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobInfo:
    """Information about a background job."""

    job_id: str
    status: JobStatus
    progress: float = 0.0
    current_step: str = ""
    error_message: str | None = None
    created_at: datetime = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ExportRequest:
    """Request for exporting project data."""

    project_id: str
    format: str = "zip"  # zip, tar, folder
    include_source: bool = True
    include_translations: bool = True
    target_languages: list[str] = None
    output_path: str | None = None

    def __post_init__(self):
        if self.target_languages is None:
            self.target_languages = []


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    export_path: str | None = None
    file_count: int = 0
    total_size: int = 0  # in bytes
    errors: list[str] = None
    warnings: list[str] = None
    export_time: float = 0.0  # seconds

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
