"""Core interfaces for file parsing and processing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .types import ParseResult


class FileParser(ABC):
    """Interface for file parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        pass

    @abstractmethod
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """Parse a file and return parse result."""
        pass

    @abstractmethod
    def write(self, file_path: Path, content: Any, **kwargs) -> None:
        """Write parsed content to a file."""
        pass


class ParserFactory(ABC):
    """Interface for parser factories."""

    @abstractmethod
    def create_parser(self, file_path: Path) -> FileParser | None:
        """Create appropriate parser for the given file."""
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        pass


class ProjectRepository(ABC):
    """Interface for project data repositories."""

    @abstractmethod
    def save_project(self, project: Any) -> None:
        """Save project to repository."""
        pass

    @abstractmethod
    def load_project(self, project_id: str) -> Any:
        """Load project from repository."""
        pass

    @abstractmethod
    def delete_project(self, project_id: str) -> None:
        """Delete project from repository."""
        pass


class ProjectScanner(ABC):
    """Interface for project scanners."""

    @abstractmethod
    def scan_directory(self, directory: Path) -> list[Path]:
        """Scan directory for relevant files."""
        pass

    @abstractmethod
    def is_valid_project(self, directory: Path) -> bool:
        """Check if directory contains a valid project."""
        pass