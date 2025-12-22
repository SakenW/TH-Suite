"""Parser for .lang files (legacy Minecraft format)."""

import re
from pathlib import Path

from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import Segment

from .base import BaseParser, ParseResult


class LangParser(BaseParser):
    """Parser for .lang language files (legacy Minecraft format)."""

    def __init__(self, encoding: str = "utf-8"):
        super().__init__(encoding)
        self.supported_extensions = [".lang"]
        # Pattern for key=value lines
        self.key_value_pattern = re.compile(r"^([^=]+)=(.*)$")
        # Pattern for comments
        self.comment_pattern = re.compile(r"^\s*#")

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions

    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """Parse a .lang language file.

        Args:
            file_path: Path to the .lang file
            **kwargs: Additional options:
                - modid: Mod identifier (extracted from path if not provided)
                - locale: Language locale (extracted from filename if not provided)
                - preserve_comments: Whether to preserve comments as metadata (default: False)
                - strict_format: Whether to enforce strict format validation (default: False)

        Returns:
            ParseResult with extracted segments
        """
        modid = kwargs.get("modid")
        locale = kwargs.get("locale")
        preserve_comments = kwargs.get("preserve_comments", False)
        strict_format = kwargs.get("strict_format", False)

        segments = []
        warnings = []
        errors = []
        comments = []

        try:
            content = self.read_file_content(file_path)
            lines = content.splitlines()

            # Extract modid from path if not provided
            if not modid:
                modid = self._extract_modid_from_path(file_path)

            # Extract locale from filename if not provided
            if not locale:
                locale = self._extract_locale_from_filename(file_path)
                if not locale:
                    warnings.append("Could not determine locale from filename")
                    locale = "unknown"

            # Process each line
            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Handle comments
                if self.comment_pattern.match(line):
                    if preserve_comments:
                        comments.append({"line": line_num, "content": line})
                    continue

                # Parse key=value lines
                match = self.key_value_pattern.match(line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    # Validate key
                    if not key:
                        warning_msg = f"Empty key on line {line_num}"
                        if strict_format:
                            errors.append(warning_msg)
                        else:
                            warnings.append(warning_msg)
                        continue

                    # Handle escaped characters in value
                    value = self._unescape_value(value)

                    uida = f"{modid}.{key}" if modid != "unknown" else key

                    segment = self.create_segment(
                        uida=uida,
                        locale=locale,
                        key=key,
                        text=value,
                        metadata={
                            "source_file": str(file_path),
                            "line_number": line_num,
                            "modid": modid,
                            "format": "lang",
                        },
                    )
                    segments.append(segment)
                else:
                    # Invalid line format
                    warning_msg = f"Invalid line format on line {line_num}: {line}"
                    if strict_format:
                        errors.append(warning_msg)
                    else:
                        warnings.append(warning_msg)

            metadata = self.get_file_metadata(file_path)
            metadata.update(
                {
                    "modid": modid,
                    "locale": locale,
                    "total_lines": len(lines),
                    "valid_segments": len(segments),
                    "format": "lang",
                }
            )

            if preserve_comments:
                metadata["comments"] = comments

            return ParseResult(
                segments=segments, metadata=metadata, warnings=warnings, errors=errors
            )

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to parse .lang file {file_path}: {e}")

    def write(self, segments: list[Segment], file_path: Path, **kwargs) -> None:
        """Write translation segments to a .lang file.

        Args:
            segments: List of translation segments
            file_path: Output file path
            **kwargs: Additional options:
                - header_comment: Header comment to add (default: None)
                - sort_keys: Whether to sort keys (default: True)
                - preserve_comments: Whether to preserve original comments (default: False)
        """
        header_comment = kwargs.get("header_comment")
        sort_keys = kwargs.get("sort_keys", True)
        kwargs.get("preserve_comments", False)

        try:
            lines = []

            # Add header comment if provided
            if header_comment:
                for comment_line in header_comment.split("\n"):
                    lines.append(f"# {comment_line.strip()}")
                lines.append("")  # Empty line after header

            # Group segments by locale
            locale_groups = {}
            for segment in segments:
                if segment.locale not in locale_groups:
                    locale_groups[segment.locale] = []
                locale_groups[segment.locale].append(segment)

            # If multiple locales, write only the first one or raise error
            if len(locale_groups) > 1:
                raise ValidationError(
                    f"Cannot write multiple locales to single file: {list(locale_groups.keys())}"
                )

            if locale_groups:
                locale_segments = next(iter(locale_groups.values()))

                # Sort segments if requested
                if sort_keys:
                    locale_segments.sort(key=lambda s: s.key)

                # Write key=value pairs
                for segment in locale_segments:
                    escaped_value = self._escape_value(segment.text)
                    lines.append(f"{segment.key}={escaped_value}")

            # Write file
            content = "\n".join(lines)
            if content and not content.endswith("\n"):
                content += "\n"

            self.write_file_content(file_path, content)

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to write .lang file {file_path}: {e}")

    def _extract_modid_from_path(self, file_path: Path) -> str:
        """Extract mod ID from file path."""
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
        """Extract locale from filename (e.g., en_US.lang -> en_us)."""
        name = file_path.stem

        # Check if filename looks like a locale (xx_YY format)
        if "_" in name and len(name) == 5:
            return name.lower()

        return None

    def _unescape_value(self, value: str) -> str:
        """Unescape special characters in .lang values."""
        # Common escape sequences in .lang files
        replacements = {
            "\\n": "\n",
            "\\t": "\t",
            "\\r": "\r",
            "\\\\": "\\",
            "\\'": "'",
            '\\"': '"',
        }

        result = value
        for escaped, unescaped in replacements.items():
            result = result.replace(escaped, unescaped)

        return result

    def _escape_value(self, value: str) -> str:
        """Escape special characters for .lang values."""
        # Escape sequences for .lang files
        replacements = {
            "\\": "\\\\",
            "\n": "\\n",
            "\t": "\\t",
            "\r": "\\r",
            "'": "\\'",
            '"': '\\"',
        }

        result = value
        for unescaped, escaped in replacements.items():
            result = result.replace(unescaped, escaped)

        return result
