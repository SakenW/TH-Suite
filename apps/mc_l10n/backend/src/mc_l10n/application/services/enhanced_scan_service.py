"""Enhanced scan service implementing the new Trans-Hub architecture."""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

import structlog

from packages.backend_kit.websocket import send_log_message, send_progress_update
from packages.core.enhanced_models import (
    ContentFingerprint,
    FileFingerprint,
    LanguageFileInfo,
    MinecraftLoader,
    Project,
    ProjectKey,
    ProjectSettings,
    ProjectState,
    ProjectType,
    RecognitionReport,
)
from packages.core.enhanced_state import ProjectStateMachine
from packages.core.errors import ProcessingError, ValidationError
from packages.parsers.factory import ParserFactory


class EnhancedScanService:
    """Enhanced scan service with detailed recognition and fingerprinting."""

    def __init__(
        self, logger: structlog.BoundLogger, state_machine: ProjectStateMachine
    ):
        self.logger = logger
        self.state_machine = state_machine
        self.parser_factory = ParserFactory()

        # Placeholder pattern detection
        self.placeholder_patterns = [
            r"%[sd%]",  # Java format strings
            r"\{\d+\}",  # Numbered placeholders
            r"\{[a-zA-Z_][a-zA-Z0-9_]*\}",  # Named placeholders
            r"\$\{[^}]+\}",  # Variable placeholders
            r"<[^>]+>",  # XML-style placeholders
            r"\[\w+\]",  # Bracket placeholders
        ]

    async def create_project(
        self,
        job_id: str,
        directory: str,
        project_type: ProjectType,
        name: str,
        version: str,
        mc_version: str,
        loader: MinecraftLoader,
        loader_version: str,
        settings: ProjectSettings | None = None,
    ) -> Project:
        """Create a new project with normalized identifier."""
        logger = self.logger.bind(job_id=job_id, phase="create_project")

        try:
            # Create project key
            project_key = ProjectKey(
                type=project_type,
                name=name,
                version=version,
                mc_version=mc_version,
                loader=loader,
                loader_version=loader_version,
            )

            # Generate project ID
            project_id = hashlib.sha256(project_key.to_string().encode()).hexdigest()[
                :16
            ]

            # Create project
            project = Project(
                id=project_id,
                key=project_key,
                settings=settings or ProjectSettings(),
                metadata={"source_directory": directory},
            )

            logger.info(
                "Project created",
                project_id=project_id,
                project_key=project_key.to_string(),
            )
            await send_log_message(
                job_id, "info", f"Created project: {name} v{version}"
            )

            return project

        except Exception as e:
            logger.error("Failed to create project", error=str(e))
            raise ProcessingError(f"Failed to create project: {str(e)}")

    async def perform_detailed_recognition(
        self, job_id: str, project: Project, directory: str, context: dict
    ) -> RecognitionReport:
        """Perform detailed recognition with fingerprinting."""
        logger = self.logger.bind(
            job_id=job_id, project_id=project.id, phase="recognition"
        )

        try:
            logger.info("Starting detailed recognition", directory=directory)
            await send_progress_update(job_id, 0, "Starting detailed recognition...")

            # Pre-check: validate directory and permissions
            await self._perform_precheck(directory, job_id)

            # Discover language files
            language_files = await self._discover_language_files(
                directory, project, job_id
            )

            # Generate file fingerprints
            await self._generate_file_fingerprints(language_files, job_id)

            # Analyze content and detect patterns
            await self._analyze_content_patterns(language_files, job_id)

            # Determine override priorities
            override_priorities = await self._determine_override_priorities(
                language_files
            )

            # Generate content fingerprint
            content_fingerprint = ContentFingerprint.generate(
                project.key, language_files
            )

            # Create recognition report
            report = RecognitionReport(
                project_key=project.key,
                content_fingerprint=content_fingerprint,
                language_files=language_files,
                source_locale="",  # Will be set below
                override_priorities=override_priorities,
            )

            # Select source locale
            report.source_locale = report.select_source_locale(
                preferred=project.settings.preferred_source_lang,
                fallbacks=project.settings.source_fallbacks,
            )
            report.source_fallbacks = project.settings.source_fallbacks

            # Generate coverage matrix
            report.coverage_matrix = await self._generate_coverage_matrix(
                language_files
            )

            # Validate report
            await self._validate_recognition_report(report, project.settings)

            # Update project
            project.recognition_report = report
            project.transition_to(
                ProjectState.RECOGNIZED,
                {
                    "recognition_completed_at": datetime.now().isoformat(),
                    "total_files": len(language_files),
                    "total_locales": len(content_fingerprint.locales),
                    "content_hash": content_fingerprint.content_hash,
                },
            )

            context.update(
                {
                    "result": {
                        "project_id": project.id,
                        "content_fingerprint": content_fingerprint.content_hash,
                        "total_files": len(language_files),
                        "total_locales": len(content_fingerprint.locales),
                        "source_locale": report.source_locale,
                        "validation_warnings": len(report.validation_warnings),
                        "validation_errors": len(report.validation_errors),
                    },
                    "message": "Recognition completed successfully",
                }
            )

            await send_progress_update(
                job_id, 100, "Recognition completed successfully"
            )
            logger.info(
                "Recognition completed",
                total_files=len(language_files),
                content_hash=content_fingerprint.content_hash[:16],
                source_locale=report.source_locale,
            )

            return report

        except Exception as e:
            logger.error("Recognition failed", error=str(e), exc_info=True)
            project.transition_to(ProjectState.FAILED, {"error": str(e)})
            context.update(
                {"error": str(e), "message": f"Recognition failed: {str(e)}"}
            )
            raise

    async def _perform_precheck(self, directory: str, job_id: str) -> None:
        """Perform pre-check validation."""
        await send_progress_update(job_id, 5, "Performing pre-checks...")

        directory_path = Path(directory)

        # Check directory exists and is readable
        if not directory_path.exists():
            raise ValidationError(f"Directory does not exist: {directory}")

        if not directory_path.is_dir():
            raise ValidationError(f"Path is not a directory: {directory}")

        # Check permissions
        if not os.access(directory_path, os.R_OK):
            raise ValidationError(f"Directory is not readable: {directory}")

        # Check available space (at least 100MB for processing)
        try:
            stat = os.statvfs(directory_path) if hasattr(os, "statvfs") else None
            if stat and stat.f_bavail * stat.f_frsize < 100 * 1024 * 1024:
                self.logger.warning(
                    "Low disk space detected",
                    available_mb=stat.f_bavail * stat.f_frsize // (1024 * 1024),
                )
        except (OSError, AttributeError):
            pass  # Skip space check on Windows or if unavailable

    async def _discover_language_files(
        self, directory: str, project: Project, job_id: str
    ) -> list[LanguageFileInfo]:
        """Discover language files in the directory."""
        await send_progress_update(job_id, 10, "Discovering language files...")

        directory_path = Path(directory)
        language_files = []

        # Define search patterns based on project type
        if project.key.type == ProjectType.MODPACK:
            search_patterns = [
                "**/assets/*/lang/*.json",
                "**/assets/*/lang/*.lang",
                "**/lang/*.json",
                "**/lang/*.lang",
            ]
        else:
            search_patterns = [
                "assets/*/lang/*.json",
                "assets/*/lang/*.lang",
                "lang/*.json",
                "lang/*.lang",
                "src/main/resources/assets/*/lang/*.json",
            ]

        found_files = set()
        for pattern in search_patterns:
            for file_path in directory_path.glob(pattern):
                if file_path.is_file() and file_path not in found_files:
                    found_files.add(file_path)

        total_files = len(found_files)
        processed = 0

        for file_path in found_files:
            try:
                # Extract mod ID and locale from path
                modid, locale = self._extract_modid_and_locale(
                    file_path, directory_path
                )

                if not modid or not locale:
                    self.logger.warning(
                        "Could not extract mod ID or locale", file_path=str(file_path)
                    )
                    continue

                # Determine file format
                file_format = file_path.suffix.lower().lstrip(".")

                # Determine source priority
                source_priority = self._calculate_source_priority(
                    file_path, directory_path
                )

                # Create language file info (fingerprint will be added later)
                lang_file = LanguageFileInfo(
                    modid=modid,
                    locale=locale,
                    path=str(file_path.relative_to(directory_path)),
                    format=file_format,
                    fingerprint=FileFingerprint(
                        path=str(file_path.relative_to(directory_path)),
                        sha256="",  # Will be calculated later
                        size=file_path.stat().st_size,
                        last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                    ),
                    source_priority=source_priority,
                )

                language_files.append(lang_file)

                processed += 1
                if processed % 10 == 0 or processed == total_files:
                    progress = 10 + (processed / total_files) * 30
                    await send_progress_update(
                        job_id,
                        int(progress),
                        f"Discovered {processed}/{total_files} language files",
                    )

            except Exception as e:
                self.logger.warning(
                    "Failed to process file", file_path=str(file_path), error=str(e)
                )
                continue

        self.logger.info(
            "Language file discovery completed", total_files=len(language_files)
        )
        return language_files

    def _extract_modid_and_locale(
        self, file_path: Path, base_path: Path
    ) -> tuple[str, str]:
        """Extract mod ID and locale from file path."""
        relative_path = file_path.relative_to(base_path)
        parts = relative_path.parts

        # Try to find assets/modid/lang/locale.ext pattern
        for i, part in enumerate(parts):
            if part == "assets" and i + 3 < len(parts) and parts[i + 2] == "lang":
                modid = parts[i + 1]
                locale_file = parts[i + 3]
                locale = locale_file.split(".")[0]
                return modid, locale
            elif part == "lang" and i + 1 < len(parts):
                # Direct lang/locale.ext pattern
                locale_file = parts[i + 1]
                locale = locale_file.split(".")[0]
                # Try to infer mod ID from parent directories
                if i > 0:
                    modid = parts[i - 1]
                else:
                    modid = "unknown"
                return modid, locale

        # Fallback: use filename as locale and parent as mod ID
        locale = file_path.stem
        modid = file_path.parent.name if file_path.parent.name != "lang" else "unknown"
        return modid, locale

    def _calculate_source_priority(self, file_path: Path, base_path: Path) -> int:
        """Calculate source priority for override resolution."""
        relative_path = str(file_path.relative_to(base_path))

        # Resource pack files have higher priority
        if "resourcepacks" in relative_path or "resource_packs" in relative_path:
            return 100

        # Mod files in mods directory
        if "mods" in relative_path:
            return 50

        # Source files (development)
        if "src/main/resources" in relative_path:
            return 75

        # Default priority
        return 25

    async def _generate_file_fingerprints(
        self, language_files: list[LanguageFileInfo], job_id: str
    ) -> None:
        """Generate SHA-256 fingerprints for all files."""
        await send_progress_update(job_id, 40, "Generating file fingerprints...")

        total_files = len(language_files)
        processed = 0

        for lang_file in language_files:
            try:
                file_path = Path(lang_file.path)

                # Calculate SHA-256 hash
                hasher = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hasher.update(chunk)

                lang_file.fingerprint.sha256 = hasher.hexdigest()

                # Detect encoding and line endings
                try:
                    with open(file_path, "rb") as f:
                        raw_data = f.read(1024)  # Sample first 1KB

                    # Simple encoding detection
                    try:
                        raw_data.decode("utf-8")
                        lang_file.fingerprint.encoding = "utf-8"
                    except UnicodeDecodeError:
                        try:
                            raw_data.decode("latin-1")
                            lang_file.fingerprint.encoding = "latin-1"
                        except UnicodeDecodeError:
                            lang_file.fingerprint.encoding = "unknown"

                    # Line ending detection
                    if b"\r\n" in raw_data:
                        lang_file.fingerprint.line_endings = "crlf"
                    elif b"\n" in raw_data:
                        lang_file.fingerprint.line_endings = "lf"
                    elif b"\r" in raw_data:
                        lang_file.fingerprint.line_endings = "cr"
                    else:
                        lang_file.fingerprint.line_endings = "unknown"

                except Exception as e:
                    self.logger.warning(
                        "Failed to detect encoding",
                        file_path=str(file_path),
                        error=str(e),
                    )

                processed += 1
                if processed % 20 == 0 or processed == total_files:
                    progress = 40 + (processed / total_files) * 20
                    await send_progress_update(
                        job_id,
                        int(progress),
                        f"Generated fingerprints for {processed}/{total_files} files",
                    )

            except Exception as e:
                self.logger.error(
                    "Failed to generate fingerprint",
                    file_path=lang_file.path,
                    error=str(e),
                )
                lang_file.fingerprint.sha256 = "error"

    async def _analyze_content_patterns(
        self, language_files: list[LanguageFileInfo], job_id: str
    ) -> None:
        """Analyze content patterns and count keys."""
        await send_progress_update(job_id, 60, "Analyzing content patterns...")

        total_files = len(language_files)
        processed = 0

        for lang_file in language_files:
            try:
                file_path = Path(lang_file.path)

                # Get appropriate parser
                parser = self.parser_factory.get_parser(file_path)

                # Parse file content
                content = await parser.parse_file(str(file_path))

                # Count keys
                lang_file.key_count = len(content) if isinstance(content, dict) else 0

                # Detect placeholder patterns
                patterns = set()
                if isinstance(content, dict):
                    for value in content.values():
                        if isinstance(value, str):
                            for pattern_regex in self.placeholder_patterns:
                                if re.search(pattern_regex, value):
                                    patterns.add(pattern_regex)

                lang_file.placeholder_patterns = patterns

                processed += 1
                if processed % 15 == 0 or processed == total_files:
                    progress = 60 + (processed / total_files) * 20
                    await send_progress_update(
                        job_id,
                        int(progress),
                        f"Analyzed {processed}/{total_files} files",
                    )

            except Exception as e:
                self.logger.warning(
                    "Failed to analyze content", file_path=lang_file.path, error=str(e)
                )
                lang_file.key_count = 0
                lang_file.placeholder_patterns = set()

    async def _determine_override_priorities(
        self, language_files: list[LanguageFileInfo]
    ) -> dict[str, list[str]]:
        """Determine file override priorities."""
        priorities = {}

        # Group files by normalized path
        path_groups = {}
        for lang_file in language_files:
            normalized_path = f"{lang_file.modid}/lang/{lang_file.locale}.json"
            if normalized_path not in path_groups:
                path_groups[normalized_path] = []
            path_groups[normalized_path].append(lang_file.path)

        # Sort by priority for each path
        for normalized_path, file_paths in path_groups.items():
            if len(file_paths) > 1:
                # Sort by source priority (higher first)
                file_priorities = [
                    (
                        path,
                        next(
                            f.source_priority for f in language_files if f.path == path
                        ),
                    )
                    for path in file_paths
                ]
                sorted_paths = [
                    path
                    for path, _ in sorted(
                        file_priorities, key=lambda x: x[1], reverse=True
                    )
                ]
                priorities[normalized_path] = sorted_paths

        return priorities

    async def _generate_coverage_matrix(
        self, language_files: list[LanguageFileInfo]
    ) -> dict[str, dict[str, str]]:
        """Generate mod x locale coverage matrix."""
        matrix = {}

        # Get all unique mod IDs and locales
        modids = {f.modid for f in language_files}
        locales = {f.locale for f in language_files}

        # Initialize matrix
        for modid in modids:
            matrix[modid] = {}
            for locale in locales:
                matrix[modid][locale] = "missing"

        # Fill matrix with actual data
        for lang_file in language_files:
            if lang_file.key_count > 0:
                matrix[lang_file.modid][lang_file.locale] = "present"

        # Mark conflicts (multiple files for same mod/locale)
        path_counts = {}
        for lang_file in language_files:
            key = (lang_file.modid, lang_file.locale)
            path_counts[key] = path_counts.get(key, 0) + 1

        for (modid, locale), count in path_counts.items():
            if count > 1:
                matrix[modid][locale] = "conflict"

        return matrix

    async def _validate_recognition_report(
        self, report: RecognitionReport, settings: ProjectSettings
    ) -> None:
        """Validate recognition report and add warnings/errors."""
        warnings = []
        errors = []

        # Check for missing source locale
        if not any(f.locale == report.source_locale for f in report.language_files):
            errors.append(
                f"Source locale '{report.source_locale}' not found in any files"
            )

        # Check for encoding inconsistencies
        encodings = {
            f.fingerprint.encoding
            for f in report.language_files
            if f.fingerprint.encoding
        }
        if len(encodings) > 1:
            warnings.append(f"Multiple file encodings detected: {', '.join(encodings)}")

        # Check for line ending inconsistencies
        line_endings = {
            f.fingerprint.line_endings
            for f in report.language_files
            if f.fingerprint.line_endings
        }
        if len(line_endings) > 1:
            warnings.append(
                f"Multiple line ending styles detected: {', '.join(line_endings)}"
            )

        # Check for conflicts in coverage matrix
        conflicts = []
        for modid, locales in report.coverage_matrix.items():
            for locale, status in locales.items():
                if status == "conflict":
                    conflicts.append(f"{modid}/{locale}")

        if conflicts:
            if settings.validation_mode == "strict":
                errors.append(f"File conflicts detected: {', '.join(conflicts)}")
            else:
                warnings.append(f"File conflicts detected: {', '.join(conflicts)}")

        # Check for empty files
        empty_files = [f.path for f in report.language_files if f.key_count == 0]
        if empty_files:
            warnings.append(f"Empty language files detected: {len(empty_files)} files")

        report.validation_warnings = warnings
        report.validation_errors = errors

        if errors and settings.validation_mode == "strict":
            raise ValidationError(f"Validation failed: {'; '.join(errors)}")
