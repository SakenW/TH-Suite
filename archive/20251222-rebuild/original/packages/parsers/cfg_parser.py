"""CFG parser for RimWorld and other configuration-based language files."""

import re
from pathlib import Path

from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import Segment

from .base import BaseParser, ParseResult


class CfgParser(BaseParser):
    """Parser for CFG/configuration language files (RimWorld format)."""

    def __init__(self, encoding: str = "utf-8"):
        super().__init__(encoding)
        self.supported_extensions = [".cfg", ".txt"]
        # Patterns for parsing CFG format
        self.section_pattern = re.compile(r"^\s*\[([^\]]+)\]\s*$")
        self.key_value_pattern = re.compile(r"^\s*([^=]+?)\s*=\s*(.*)$")
        self.comment_pattern = re.compile(r"^\s*[#;]")
        self.xml_tag_pattern = re.compile(r"^\s*<([^>]+)>\s*(.*)\s*</\1>\s*$")

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions

    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """Parse a CFG language file.

        Args:
            file_path: Path to the CFG file
            **kwargs: Additional options:
                - modid: Mod identifier (extracted from path if not provided)
                - locale: Language locale (extracted from filename if not provided)
                - preserve_sections: Whether to preserve section structure (default: True)
                - xml_mode: Whether to parse XML-style tags (default: True)
                - case_sensitive: Whether keys are case sensitive (default: False)

        Returns:
            ParseResult with extracted segments
        """
        modid = kwargs.get("modid")
        locale = kwargs.get("locale")
        preserve_sections = kwargs.get("preserve_sections", True)
        xml_mode = kwargs.get("xml_mode", True)
        case_sensitive = kwargs.get("case_sensitive", False)

        segments = []
        warnings = []
        errors = []
        current_section = None

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
                original_line = line
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Handle comments
                if self.comment_pattern.match(line):
                    continue

                # Handle sections
                section_match = self.section_pattern.match(line)
                if section_match:
                    current_section = section_match.group(1).strip()
                    continue

                # Handle XML-style tags if enabled
                if xml_mode:
                    xml_match = self.xml_tag_pattern.match(line)
                    if xml_match:
                        key = xml_match.group(1).strip()
                        value = xml_match.group(2).strip()

                        if not case_sensitive:
                            key = key.lower()

                        self._add_segment(
                            segments,
                            modid,
                            locale,
                            key,
                            value,
                            current_section,
                            preserve_sections,
                            file_path,
                            line_num,
                            "xml",
                        )
                        continue

                # Handle key=value pairs
                kv_match = self.key_value_pattern.match(line)
                if kv_match:
                    key = kv_match.group(1).strip()
                    value = kv_match.group(2).strip()

                    if not case_sensitive:
                        key = key.lower()

                    # Remove quotes from value if present
                    value = self._unquote_value(value)

                    self._add_segment(
                        segments,
                        modid,
                        locale,
                        key,
                        value,
                        current_section,
                        preserve_sections,
                        file_path,
                        line_num,
                        "keyvalue",
                    )
                else:
                    # Try to parse as simple key-only line (some CFG formats)
                    if line and not line.startswith("["):
                        warnings.append(
                            f"Could not parse line {line_num}: {original_line}"
                        )

            metadata = self.get_file_metadata(file_path)
            metadata.update(
                {
                    "modid": modid,
                    "locale": locale,
                    "total_lines": len(lines),
                    "valid_segments": len(segments),
                    "format": "cfg",
                    "sections_found": len(
                        set(
                            s.metadata.get("section")
                            for s in segments
                            if s.metadata.get("section")
                        )
                    ),
                }
            )

            return ParseResult(
                segments=segments, metadata=metadata, warnings=warnings, errors=errors
            )

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to parse CFG file {file_path}: {e}")

    def write(self, segments: list[Segment], file_path: Path, **kwargs) -> None:
        """Write translation segments to a CFG file.

        Args:
            segments: List of translation segments
            file_path: Output file path
            **kwargs: Additional options:
                - preserve_sections: Whether to group by sections (default: True)
                - xml_mode: Whether to use XML-style tags (default: False)
                - quote_values: Whether to quote values (default: False)
                - sort_keys: Whether to sort keys within sections (default: True)
                - header_comment: Header comment to add (default: None)
        """
        preserve_sections = kwargs.get("preserve_sections", True)
        xml_mode = kwargs.get("xml_mode", False)
        quote_values = kwargs.get("quote_values", False)
        sort_keys = kwargs.get("sort_keys", True)
        header_comment = kwargs.get("header_comment")

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

                if preserve_sections:
                    # Group by sections
                    sections = {}
                    no_section = []

                    for segment in locale_segments:
                        section = segment.metadata.get("section")
                        if section:
                            if section not in sections:
                                sections[section] = []
                            sections[section].append(segment)
                        else:
                            no_section.append(segment)

                    # Write segments without section first
                    if no_section:
                        if sort_keys:
                            no_section.sort(key=lambda s: s.key)

                        for segment in no_section:
                            line = self._format_segment(segment, xml_mode, quote_values)
                            lines.append(line)

                        if sections:
                            lines.append("")  # Empty line before sections

                    # Write sections
                    for section_name in sorted(sections.keys()):
                        lines.append(f"[{section_name}]")

                        section_segments = sections[section_name]
                        if sort_keys:
                            section_segments.sort(key=lambda s: s.key)

                        for segment in section_segments:
                            line = self._format_segment(segment, xml_mode, quote_values)
                            lines.append(line)

                        lines.append("")  # Empty line after section
                else:
                    # Write all segments without sections
                    if sort_keys:
                        locale_segments.sort(key=lambda s: s.key)

                    for segment in locale_segments:
                        line = self._format_segment(segment, xml_mode, quote_values)
                        lines.append(line)

            # Write file
            content = "\n".join(lines)
            if content and not content.endswith("\n"):
                content += "\n"

            self.write_file_content(file_path, content)

        except Exception as e:
            if isinstance(e, ValidationError | ProcessingError):
                raise
            raise ProcessingError(f"Failed to write CFG file {file_path}: {e}")

    def _add_segment(
        self,
        segments: list[Segment],
        modid: str,
        locale: str,
        key: str,
        value: str,
        section: str | None,
        preserve_sections: bool,
        file_path: Path,
        line_num: int,
        format_type: str,
    ) -> None:
        """Add a segment to the list."""
        # Build full key with section if preserving sections
        if preserve_sections and section:
            full_key = f"{section}.{key}"
        else:
            full_key = key

        uida = f"{modid}.{full_key}" if modid != "unknown" else full_key

        segment = self.create_segment(
            uida=uida,
            locale=locale,
            key=full_key,
            text=value,
            metadata={
                "source_file": str(file_path),
                "line_number": line_num,
                "modid": modid,
                "format": "cfg",
                "section": section,
                "original_key": key,
                "format_type": format_type,
            },
        )
        segments.append(segment)

    def _format_segment(
        self, segment: Segment, xml_mode: bool, quote_values: bool
    ) -> str:
        """Format a segment for output."""
        key = segment.metadata.get("original_key", segment.key)
        value = segment.text

        if quote_values and not (value.startswith('"') and value.endswith('"')):
            value = f'"{value}"'

        if xml_mode:
            return f"<{key}>{value}</{key}>"
        else:
            return f"{key}={value}"

    def _unquote_value(self, value: str) -> str:
        """Remove quotes from value if present."""
        if len(value) >= 2:
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                return value[1:-1]
        return value

    def _extract_modid_from_path(self, file_path: Path) -> str:
        """Extract mod ID from file path."""
        parts = file_path.parts

        # Look for RimWorld mod patterns
        for i, part in enumerate(parts):
            if part.lower() in ["mods", "languages", "lang"] and i + 1 < len(parts):
                return parts[i + 1]

        # Look for common patterns
        for i, part in enumerate(parts):
            if part.lower() in ["data", "config", "localization"] and i + 1 < len(
                parts
            ):
                return parts[i + 1]

        # Fallback: use parent directory name
        return (
            file_path.parent.name
            if file_path.parent.name.lower() not in ["lang", "languages"]
            else "unknown"
        )

    def _extract_locale_from_filename(self, file_path: Path) -> str | None:
        """Extract locale from filename."""
        name = file_path.stem.lower()

        # Common RimWorld language mappings
        rimworld_locales = {
            "english": "en_us",
            "chinese": "zh_cn",
            "chinesesimplified": "zh_cn",
            "chinesetraditional": "zh_tw",
            "japanese": "ja_jp",
            "korean": "ko_kr",
            "french": "fr_fr",
            "german": "de_de",
            "spanish": "es_es",
            "russian": "ru_ru",
            "portuguese": "pt_br",
            "italian": "it_it",
            "dutch": "nl_nl",
            "polish": "pl_pl",
            "czech": "cs_cz",
            "finnish": "fi_fi",
            "norwegian": "no_no",
            "swedish": "sv_se",
            "danish": "da_dk",
            "hungarian": "hu_hu",
            "turkish": "tr_tr",
            "arabic": "ar_sa",
            "ukrainian": "uk_ua",
        }

        # Check for exact matches
        if name in rimworld_locales:
            return rimworld_locales[name]

        # Check for partial matches
        for locale_name, locale_code in rimworld_locales.items():
            if locale_name in name:
                return locale_code

        # Check for standard locale format
        if "_" in name and len(name) == 5:
            return name

        return None
