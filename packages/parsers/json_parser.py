"""JSON parser for Minecraft and other JSON-based language files."""

import json
from pathlib import Path
from typing import Any

from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import Segment

from .base import BaseParser, ParseResult


class JsonParser(BaseParser):
    """Parser for JSON language files (primarily Minecraft)."""

    def __init__(self, encoding: str = "utf-8"):
        super().__init__(encoding)
        self.supported_extensions = [".json"]

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions

    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """Parse a JSON language file.

        Args:
            file_path: Path to the JSON file
            **kwargs: Additional options:
                - modid: Mod identifier (extracted from path if not provided)
                - locale: Language locale (extracted from filename if not provided)
                - flatten_nested: Whether to flatten nested objects (default: True)
                - key_separator: Separator for nested keys (default: '.')

        Returns:
            ParseResult with extracted segments
        """
        modid = kwargs.get("modid")
        locale = kwargs.get("locale")
        flatten_nested = kwargs.get("flatten_nested", True)
        key_separator = kwargs.get("key_separator", ".")

        segments = []
        warnings = []
        errors = []

        try:
            content = self.read_file_content(file_path)

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")

            if not isinstance(data, dict):
                raise ValidationError("JSON root must be an object")

            # Extract modid from path if not provided
            if not modid:
                modid = self._extract_modid_from_path(file_path)

            # Extract locale from filename if not provided
            if not locale:
                locale = self._extract_locale_from_filename(file_path)
                if not locale:
                    warnings.append("Could not determine locale from filename")
                    locale = "unknown"

            # Process the JSON data
            if flatten_nested:
                flattened = self._flatten_dict(data, key_separator)
            else:
                flattened = data

            # Create segments
            for key, value in flattened.items():
                if not isinstance(value, str):
                    warnings.append(
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
                        "format": "json",
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
                    "format": "json",
                }
            )

            return ParseResult(
                segments=segments, metadata=metadata, warnings=warnings, errors=errors
            )

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to parse JSON file {file_path}: {e}")

    def write(self, segments: list[Segment], file_path: Path, **kwargs) -> None:
        """Write translation segments to a JSON file.

        Args:
            segments: List of translation segments
            file_path: Output file path
            **kwargs: Additional options:
                - indent: JSON indentation (default: 2)
                - sort_keys: Whether to sort keys (default: True)
                - ensure_ascii: Whether to ensure ASCII output (default: False)
                - unflatten: Whether to unflatten nested keys (default: True)
                - key_separator: Separator for nested keys (default: '.')
        """
        indent = kwargs.get("indent", 2)
        sort_keys = kwargs.get("sort_keys", True)
        ensure_ascii = kwargs.get("ensure_ascii", False)
        unflatten = kwargs.get("unflatten", True)
        key_separator = kwargs.get("key_separator", ".")

        try:
            # Group segments by locale (in case of mixed locales)
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
                data = {}
            else:
                locale_data = next(iter(locale_groups.values()))

                if unflatten:
                    data = self._unflatten_dict(locale_data, key_separator)
                else:
                    data = locale_data

            # Write JSON file
            json_content = json.dumps(
                data,
                indent=indent,
                sort_keys=sort_keys,
                ensure_ascii=ensure_ascii,
                separators=(",", ": ") if indent else (",", ":"),
            )

            self.write_file_content(file_path, json_content)

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to write JSON file {file_path}: {e}")

    def _extract_modid_from_path(self, file_path: Path) -> str:
        """Extract mod ID from file path.

        Looks for patterns like:
        - mods/modname/assets/modname/lang/
        - assets/modname/lang/
        """
        parts = file_path.parts

        # Look for assets/modname/lang pattern
        for i, part in enumerate(parts):
            if part == "assets" and i + 2 < len(parts) and parts[i + 2] == "lang":
                return parts[i + 1]

        # Look for mods/modname pattern
        for i, part in enumerate(parts):
            if part == "mods" and i + 1 < len(parts):
                return parts[i + 1]

        # Fallback: use parent directory name
        return file_path.parent.name if file_path.parent.name != "lang" else "unknown"

    def _extract_locale_from_filename(self, file_path: Path) -> str | None:
        """Extract locale from filename (e.g., en_us.json -> en_us)."""
        name = file_path.stem

        # Check if filename looks like a locale (xx_yy format)
        if "_" in name and len(name) == 5:
            return name.lower()

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
