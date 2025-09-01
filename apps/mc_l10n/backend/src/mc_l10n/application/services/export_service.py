"""Export service for TH Suite MC L10n."""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from packages.core.database import SQLCipherDatabase

from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import ExportRequest, ExportResult
from packages.core.state import State, StateMachine
from packages.parsers.factory import ParserFactory


class ExportService:
    """Service for exporting language packs."""

    def __init__(
        self,
        logger: structlog.BoundLogger,
        state_machine: StateMachine,
        database: Optional["SQLCipherDatabase"] = None,
    ):
        self.logger = logger
        self.state_machine = state_machine
        self.database = database
        self.parser_factory = ParserFactory()

    async def export_language_pack(
        self, job_id: str, request: ExportRequest, context: dict[str, Any]
    ) -> ExportResult:
        """Export language pack from source directory."""
        self.logger.info(
            "Starting language pack export",
            source=request.source_directory,
            output=request.output_directory,
            format=request.export_format,
        )

        try:
            # Update progress
            context["progress"] = 0.1
            context["message"] = "Scanning source directory..."

            # Scan source directory for language files
            language_files = await self._scan_language_files(
                request.source_directory,
                request.include_patterns,
                request.exclude_patterns,
                request.target_locales,
            )

            if not language_files:
                raise ProcessingError("No language files found in source directory")

            self.logger.info(f"Found {len(language_files)} language files")

            # Update progress
            context["progress"] = 0.3
            context["message"] = f"Processing {len(language_files)} language files..."

            # Process language files
            processed_files = await self._process_language_files(language_files)

            # Update progress
            context["progress"] = 0.6
            context["message"] = "Creating export package..."

            # Create export package
            export_result = await self._create_export_package(
                processed_files,
                request.output_directory,
                request.export_format,
                request.compress_level,
            )

            # Update progress
            context["progress"] = 1.0
            context["message"] = "Export completed successfully"
            context["result"] = export_result.dict()

            # Transition to completed state
            self.state_machine.transition(State.COMPLETED, context)

            self.logger.info(
                "Language pack export completed",
                exported_files=export_result.total_files,
                export_path=export_result.export_path,
            )

            return export_result

        except Exception as e:
            self.logger.error("Export failed", error=str(e), exc_info=True)
            context["error"] = str(e)
            context["message"] = f"Export failed: {str(e)}"
            self.state_machine.transition(State.FAILED, context)
            raise

    async def _scan_language_files(
        self,
        source_directory: str,
        include_patterns: list[str],
        exclude_patterns: list[str],
        target_locales: list[str] | None = None,
    ) -> list[Path]:
        """Scan directory for language files."""
        source_path = Path(source_directory)
        if not source_path.exists():
            raise ValidationError(
                f"Source directory does not exist: {source_directory}"
            )

        language_files = []

        # Common language file patterns
        patterns = include_patterns or ["*.json", "*.lang"]

        for pattern in patterns:
            files = list(source_path.rglob(pattern))
            for file_path in files:
                # Skip if matches exclude patterns
                if any(file_path.match(exclude) for exclude in exclude_patterns):
                    continue

                # Filter by target locales if specified
                if target_locales:
                    locale_found = False
                    for locale in target_locales:
                        if locale in str(file_path):
                            locale_found = True
                            break
                    if not locale_found:
                        continue

                language_files.append(file_path)

        return language_files

    async def _process_language_files(
        self, language_files: list[Path]
    ) -> dict[str, dict[str, Any]]:
        """Process language files and extract content."""
        processed_files = {}

        for file_path in language_files:
            try:
                # Determine file type and get appropriate parser
                file_extension = file_path.suffix.lower()
                parser = self.parser_factory.get_parser(file_extension)

                if not parser:
                    self.logger.warning(f"No parser available for file: {file_path}")
                    continue

                # Parse file content
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                parsed_content = parser.parse(content)

                # Extract locale from file path
                locale = self._extract_locale_from_path(file_path)

                processed_files[str(file_path)] = {
                    "locale": locale,
                    "content": parsed_content,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime),
                }

            except Exception as e:
                self.logger.warning(f"Failed to process file {file_path}: {str(e)}")
                continue

        return processed_files

    def _extract_locale_from_path(self, file_path: Path) -> str:
        """Extract locale from file path."""
        # Common patterns for locale extraction
        path_str = str(file_path)

        # Pattern 1: lang/en_us.json
        if "/lang/" in path_str or "\\lang\\" in path_str:
            return file_path.stem

        # Pattern 2: assets/modid/lang/en_us.json
        parts = file_path.parts
        if "lang" in parts:
            lang_index = parts.index("lang")
            if lang_index + 1 < len(parts):
                return Path(parts[lang_index + 1]).stem

        # Pattern 3: en_us/file.json
        for part in parts:
            if "_" in part and len(part) == 5:  # Likely locale format
                return part

        # Fallback: use filename
        return file_path.stem

    async def _create_export_package(
        self,
        processed_files: dict[str, dict[str, Any]],
        output_directory: str,
        export_format: str,
        compress_level: int = 6,
    ) -> ExportResult:
        """Create export package."""
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == "zip":
            export_file = output_path / f"language_pack_{timestamp}.zip"
            return await self._create_zip_export(
                processed_files, export_file, compress_level
            )
        else:
            export_dir = output_path / f"language_pack_{timestamp}"
            return await self._create_directory_export(processed_files, export_dir)

    async def _create_zip_export(
        self,
        processed_files: dict[str, dict[str, Any]],
        export_file: Path,
        compress_level: int,
    ) -> ExportResult:
        """Create ZIP export."""
        exported_files = []
        total_size = 0
        locales = set()

        with zipfile.ZipFile(
            export_file, "w", zipfile.ZIP_DEFLATED, compresslevel=compress_level
        ) as zf:
            # Add metadata file
            metadata = {
                "export_time": datetime.now().isoformat(),
                "total_files": len(processed_files),
                "locales": [],
                "format": "language_pack",
            }

            for file_path, file_data in processed_files.items():
                locale = file_data["locale"]
                locales.add(locale)

                # Create archive path
                archive_path = f"lang/{locale}.json"

                # Convert content to JSON
                json_content = json.dumps(
                    file_data["content"], ensure_ascii=False, indent=2
                )

                # Add to ZIP
                zf.writestr(archive_path, json_content)
                exported_files.append(archive_path)
                total_size += len(json_content.encode("utf-8"))

            # Update and add metadata
            metadata["locales"] = sorted(list(locales))
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))

        return ExportResult(
            exported_files=exported_files,
            total_files=len(exported_files),
            total_size=total_size,
            export_path=str(export_file),
            locales=sorted(list(locales)),
            metadata={
                "format": "zip",
                "compress_level": compress_level,
                "file_size": export_file.stat().st_size,
            },
        )

    async def _create_directory_export(
        self, processed_files: dict[str, dict[str, Any]], export_dir: Path
    ) -> ExportResult:
        """Create directory export."""
        export_dir.mkdir(parents=True, exist_ok=True)

        exported_files = []
        total_size = 0
        locales = set()

        # Create lang directory
        lang_dir = export_dir / "lang"
        lang_dir.mkdir(exist_ok=True)

        for file_path, file_data in processed_files.items():
            locale = file_data["locale"]
            locales.add(locale)

            # Create output file
            output_file = lang_dir / f"{locale}.json"

            # Convert content to JSON
            json_content = json.dumps(
                file_data["content"], ensure_ascii=False, indent=2
            )

            # Write file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json_content)

            exported_files.append(str(output_file.relative_to(export_dir)))
            total_size += len(json_content.encode("utf-8"))

        # Create metadata file
        metadata = {
            "export_time": datetime.now().isoformat(),
            "total_files": len(processed_files),
            "locales": sorted(list(locales)),
            "format": "language_pack",
        }

        metadata_file = export_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return ExportResult(
            exported_files=exported_files,
            total_files=len(exported_files),
            total_size=total_size,
            export_path=str(export_dir),
            locales=sorted(list(locales)),
            metadata={"format": "directory"},
        )
