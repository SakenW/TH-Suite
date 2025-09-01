"""Core types and data structures."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LanguageEntry:
    """A single language entry."""
    key: str
    value: str
    context: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ParseResult:
    """Result of parsing a file."""
    entries: list[LanguageEntry]
    metadata: dict[str, Any]
    warnings: list[str] | None = None
    errors: list[str] | None = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

    @property
    def is_valid(self) -> bool:
        """Check if parsing was successful."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


@dataclass
class LanguageFileInfo:
    """Information about a language file."""
    path: Path
    locale: str
    format: str
    entries_count: int
    last_modified: float


@dataclass
class ModInfo:
    """Information about a mod."""
    name: str
    version: str
    mod_id: str
    description: str | None = None
    authors: list[str] | None = None


@dataclass
class ProjectInfo:
    """Information about a project."""
    name: str
    path: Path | str
    project_type: str
    game_type: str | None = None
    loader_type: str | None = None
    minecraft_versions: list[str] | None = None
    total_mods: int | None = None
    total_language_files: int | None = None
    supported_languages: list[str] | None = None
    metadata: dict[str, Any] | None = None
    mod_info: ModInfo | None = None
    language_files: list[LanguageFileInfo] | None = None


@dataclass
class ProjectScanResult:
    """Result of scanning a project directory."""
    projects: list[ProjectInfo]
    warnings: list[str] | None = None
    errors: list[str] | None = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []