"""Parser factory for automatic parser selection based on file type."""

from pathlib import Path

from packages.core.errors import ValidationError

from .base import BaseParser
from .cfg_parser import CfgParser
from .json_parser import JsonParser
from .lang_parser import LangParser
from .toml_parser import TomlParser


class ParserFactory:
    """Factory for creating appropriate parsers based on file type."""

    def __init__(self):
        self._parsers: dict[str, type[BaseParser]] = {
            ".json": JsonParser,
            ".lang": LangParser,
            ".toml": TomlParser,
            ".tml": TomlParser,  # Alternative TOML extension
            ".cfg": CfgParser,
            ".txt": CfgParser,  # Many config files use .txt
            ".ini": CfgParser,  # INI files are similar to CFG
        }

        # Parser instances cache
        self._parser_instances: dict[type[BaseParser], BaseParser] = {}

    def register_parser(self, extension: str, parser_class: type[BaseParser]) -> None:
        """Register a new parser for a file extension.

        Args:
            extension: File extension (with dot, e.g., '.xml')
            parser_class: Parser class to handle this extension
        """
        if not extension.startswith("."):
            extension = f".{extension}"

        self._parsers[extension.lower()] = parser_class

        # Clear cached instance if it exists
        if parser_class in self._parser_instances:
            del self._parser_instances[parser_class]

    def get_parser(self, file_path: str | Path, encoding: str = "utf-8") -> BaseParser:
        """Get appropriate parser for the given file.

        Args:
            file_path: Path to the file
            encoding: File encoding (default: utf-8)

        Returns:
            Parser instance that can handle the file

        Raises:
            ValidationError: If no suitable parser is found
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        extension = file_path.suffix.lower()

        if extension not in self._parsers:
            raise ValidationError(
                f"No parser available for file extension: {extension}"
            )

        parser_class = self._parsers[extension]

        # Use cached instance or create new one
        if parser_class not in self._parser_instances:
            self._parser_instances[parser_class] = parser_class(encoding=encoding)

        parser = self._parser_instances[parser_class]

        # Double-check that parser can handle this file
        if not parser.can_parse(file_path):
            raise ValidationError(
                f"Parser {parser_class.__name__} cannot handle file: {file_path}"
            )

        return parser

    def get_supported_extensions(self) -> list[str]:
        """Get list of all supported file extensions.

        Returns:
            List of supported extensions (with dots)
        """
        return list(self._parsers.keys())

    def can_parse(self, file_path: str | Path) -> bool:
        """Check if any parser can handle the given file.

        Args:
            file_path: Path to the file

        Returns:
            True if a parser is available for this file
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        extension = file_path.suffix.lower()
        return extension in self._parsers

    def get_parser_info(self) -> dict[str, str]:
        """Get information about registered parsers.

        Returns:
            Dictionary mapping extensions to parser class names
        """
        return {
            ext: parser_class.__name__ for ext, parser_class in self._parsers.items()
        }

    def clear_cache(self) -> None:
        """Clear the parser instances cache."""
        self._parser_instances.clear()


# Global factory instance
_factory = ParserFactory()


def get_parser_for_file(file_path: str | Path, encoding: str = "utf-8") -> BaseParser:
    """Convenience function to get a parser for a file.

    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        Parser instance that can handle the file

    Raises:
        ValidationError: If no suitable parser is found
    """
    return _factory.get_parser(file_path, encoding)


def register_parser(extension: str, parser_class: type[BaseParser]) -> None:
    """Register a new parser globally.

    Args:
        extension: File extension (with or without dot)
        parser_class: Parser class to handle this extension
    """
    _factory.register_parser(extension, parser_class)


def get_supported_extensions() -> list[str]:
    """Get list of all supported file extensions.

    Returns:
        List of supported extensions (with dots)
    """
    return _factory.get_supported_extensions()


def can_parse_file(file_path: str | Path) -> bool:
    """Check if any parser can handle the given file.

    Args:
        file_path: Path to the file

    Returns:
        True if a parser is available for this file
    """
    return _factory.can_parse(file_path)


def get_parser_info() -> dict[str, str]:
    """Get information about registered parsers.

    Returns:
        Dictionary mapping extensions to parser class names
    """
    return _factory.get_parser_info()


def clear_parser_cache() -> None:
    """Clear the global parser instances cache."""
    _factory.clear_cache()
