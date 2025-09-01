"""TOML parser for configuration files and some game formats."""

from pathlib import Path
from typing import Any

import toml

from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import Segment

from .base import BaseParser, ParseResult


class TomlParser(BaseParser):
    """Parser for TOML configuration and language files."""

    def __init__(self, encoding: str = "utf-8"):
        super().__init__(encoding)
        self.supported_extensions = [".toml"]

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions

    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """Parse a TOML file.

        Args:
            file_path: Path to the TOML file
            **kwargs: Additional options:
                - modid: Mod identifier (extracted from path if not provided)
                - locale: Language locale (extracted from filename if not provided)
                - flatten_nested: Whether to flatten nested objects (default: True)
                - key_separator: Separator for nested keys (default: '.')
                - translation_section: Specific section containing translations (default: None)

        Returns:
            ParseResult with extracted segments
        """
        modid = kwargs.get("modid")
        locale = kwargs.get("locale")
        flatten_nested = kwargs.get("flatten_nested", True)
        key_separator = kwargs.get("key_separator", ".")
        translation_section = kwargs.get("translation_section")

        segments = []
        warnings_list = []
        errors = []

        try:
            content = self.read_file_content(file_path)

            # Parse TOML
            try:
                data = toml.loads(content)
            except toml.TomlDecodeError as e:
                raise ValidationError(f"Invalid TOML format: {e}")

            if not isinstance(data, dict):
                raise ValidationError("TOML root must be a table")

            # Extract modid from path if not provided
            if not modid:
                modid = self._extract_modid_from_path(file_path)

            # Extract locale from filename if not provided
            if not locale:
                locale = self._extract_locale_from_filename(file_path)
                if not locale:
                    warnings_list.append("Could not determine locale from filename")
                    locale = "unknown"

            # Get translation data
            if translation_section:
                if translation_section not in data:
                    warnings_list.append(
                        f"Translation section '{translation_section}' not found"
                    )
                    translation_data = {}
                else:
                    translation_data = data[translation_section]
            else:
                translation_data = data

            # Process the TOML data
            if flatten_nested:
                flattened = self._flatten_dict(translation_data, key_separator)
            else:
                flattened = translation_data

            # Create segments
            for key, value in flattened.items():
                if not isinstance(value, str):
                    warnings_list.append(
                        f"Skipping non-string value for key '{key}': {type(value).__name__}"
                    )
                    continue

                uida = f"{modid}.{key}" if modid != "unknown" else key

                segment = self.create_segment(
                    uida=uida,
                    locale=locale,
                    key=key,
                    text=value,
                    metadata={
                        "source_file": str(file_path),
                        "modid": modid,
                        "format": "toml",
                        "section": translation_section,
                    },
                )
                segments.append(segment)

            metadata = self.get_file_metadata(file_path)
            metadata.update(
                {
                    "modid": modid,
                    "locale": locale,
                    "total_keys": len(flattened),
                    "valid_segments": len(segments),
                    "format": "toml",
                    "translation_section": translation_section,
                    "all_sections": list(data.keys()) if isinstance(data, dict) else [],
                }
            )

            return ParseResult(
                segments=segments,
                metadata=metadata,
                warnings=warnings_list,
                errors=errors,
            )

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to parse TOML file {file_path}: {e}")

    def write(self, segments: list[Segment], file_path: Path, **kwargs) -> None:
        """Write translation segments to a TOML file.

        Args:
            segments: List of translation segments
            file_path: Output file path
            **kwargs: Additional options:
                - unflatten: Whether to unflatten nested keys (default: True)
                - key_separator: Separator for nested keys (default: '.')
                - translation_section: Section name for translations (default: None)
                - preserve_structure: Whether to preserve original file structure (default: False)
        """
        unflatten = kwargs.get("unflatten", True)
        key_separator = kwargs.get("key_separator", ".")
        translation_section = kwargs.get("translation_section")
        preserve_structure = kwargs.get("preserve_structure", False)

        try:
            warnings_list = []
            # Group segments by locale
            locale_groups = {}
            for segment in segments:
                if segment.locale not in locale_groups:
                    locale_groups[segment.locale] = {}
                locale_groups[segment.locale][segment.key] = segment.text

            # If multiple locales, write only the first one or raise error
            if len(locale_groups) > 1:
                raise ValidationError(
                    f"Cannot write multiple locales to single file: {list(locale_groups.keys())}"
                )

            if not locale_groups:
                translation_data = {}
            else:
                locale_data = next(iter(locale_groups.values()))

                if unflatten:
                    translation_data = self._unflatten_dict(locale_data, key_separator)
                else:
                    translation_data = locale_data

            # Structure the final data
            if translation_section:
                data = {translation_section: translation_data}
            else:
                data = translation_data

            # If preserving structure, try to merge with existing file
            if preserve_structure and file_path.exists():
                try:
                    existing_content = self.read_file_content(file_path)
                    existing_data = toml.loads(existing_content)

                    if translation_section:
                        existing_data[translation_section] = translation_data
                    else:
                        existing_data.update(translation_data)

                    data = existing_data
                except Exception as e:
                    warnings_list.append(f"Could not preserve existing structure: {e}")

            # Write TOML file
            toml_content = toml.dumps(data)
            self.write_file_content(file_path, toml_content)

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to write TOML file {file_path}: {e}")

    def _extract_modid_from_path(self, file_path: Path) -> str:
        """Extract mod ID from file path."""
        parts = file_path.parts

        # Look for common patterns
        for i, part in enumerate(parts):
            if part in ["config", "configs", "data"] and i + 1 < len(parts):
                return parts[i + 1]

        # Fallback: use parent directory name
        return file_path.parent.name if file_path.parent.name != "config" else "unknown"

    def _extract_locale_from_filename(self, file_path: Path) -> str | None:
        """Extract locale from filename."""
        name = file_path.stem

        # Check for locale patterns in filename
        if "_" in name:
            parts = name.split("_")
            if len(parts) >= 2 and len(parts[-2]) == 2 and len(parts[-1]) == 2:
                return f"{parts[-2]}_{parts[-1]}".lower()

        # Check for common locale names
        common_locales = {
            "english": "en_us",
            "chinese": "zh_cn",
            "japanese": "ja_jp",
            "korean": "ko_kr",
            "french": "fr_fr",
            "german": "de_de",
            "spanish": "es_es",
            "russian": "ru_ru",
        }

        name_lower = name.lower()
        for locale_name, locale_code in common_locales.items():
            if locale_name in name_lower:
                return locale_code

        return None

    def _flatten_dict(
        self, data: dict[str, Any], separator: str = "."
    ) -> dict[str, Any]:
        """Flatten nested dictionary."""

        def _flatten(obj: Any, parent_key: str = "") -> dict[str, Any]:
            items = []

            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    items.extend(_flatten(value, new_key).items())
            else:
                return {parent_key: obj}

            return dict(items)

        return _flatten(data)

    def _unflatten_dict(
        self, data: dict[str, Any], separator: str = "."
    ) -> dict[str, Any]:
        """Unflatten dictionary with nested keys."""
        result = {}

        for key, value in data.items():
            parts = key.split(separator)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result
