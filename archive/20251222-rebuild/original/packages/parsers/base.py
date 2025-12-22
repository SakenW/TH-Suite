"""Base parser interface and common functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import Segment


@dataclass
class ParseResult:
    """Result of parsing a file."""

    segments: list[Segment]
    metadata: dict[str, Any]
    warnings: list[str]
    errors: list[str]

    @property
    def is_valid(self) -> bool:
        """Check if parsing was successful."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class BaseParser(ABC):
    """Base class for all file parsers."""

    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding
        self.supported_extensions: list[str] = []

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this parser can handle the file
        """
        pass

    @abstractmethod
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """Parse a file and extract translation segments.

        Args:
            file_path: Path to the file to parse
            **kwargs: Additional parser-specific options

        Returns:
            ParseResult containing segments and metadata

        Raises:
            ProcessingError: If parsing fails
            ValidationError: If file format is invalid
        """
        pass

    @abstractmethod
    def write(self, segments: list[Segment], file_path: Path, **kwargs) -> None:
        """Write translation segments to a file.

        Args:
            segments: List of translation segments to write
            file_path: Path where to write the file
            **kwargs: Additional parser-specific options

        Raises:
            ProcessingError: If writing fails
        """
        pass

    def validate_file(self, file_path: Path) -> None:
        """Validate that the file exists and is readable.

        Args:
            file_path: Path to validate

        Raises:
            ValidationError: If file is invalid
        """
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise ValidationError(f"Path is not a file: {file_path}")

        try:
            with open(file_path, encoding=self.encoding):
                pass
        except UnicodeDecodeError as e:
            raise ValidationError(
                f"Cannot decode file with {self.encoding} encoding: {e}"
            )
        except PermissionError as e:
            raise ValidationError(f"Permission denied reading file: {e}")

    def read_file_content(self, file_path: Path) -> str:
        """Read file content with proper error handling.

        Args:
            file_path: Path to read

        Returns:
            File content as string

        Raises:
            ProcessingError: If reading fails
        """
        try:
            self.validate_file(file_path)
            with open(file_path, encoding=self.encoding) as f:
                return f.read()
        except Exception as e:
            raise ProcessingError(f"Failed to read file {file_path}: {e}")

    def write_file_content(self, file_path: Path, content: str) -> None:
        """Write content to file with proper error handling.

        Args:
            file_path: Path to write to
            content: Content to write

        Raises:
            ProcessingError: If writing fails
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding=self.encoding) as f:
                f.write(content)
        except Exception as e:
            raise ProcessingError(f"Failed to write file {file_path}: {e}")

    def create_segment(
        self,
        uida: str,
        locale: str,
        key: str,
        text: str,
        context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Segment:
        """Create a translation segment with validation.

        Args:
            uida: Unique identifier
            locale: Language locale
            key: Translation key
            text: Translation text
            context: Optional context
            metadata: Optional metadata

        Returns:
            Created segment
        """
        return Segment(
            uida=uida,
            locale=locale,
            key=key,
            text=text,
            context=context,
            metadata=metadata or {},
        )

    def get_file_metadata(self, file_path: Path) -> dict[str, Any]:
        """Get metadata about the file.

        Args:
            file_path: Path to analyze

        Returns:
            Dictionary with file metadata
        """
        stat = file_path.stat()
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": stat.st_size,
            "last_modified": stat.st_mtime,
            "extension": file_path.suffix.lower(),
            "parser_type": self.__class__.__name__,
        }
