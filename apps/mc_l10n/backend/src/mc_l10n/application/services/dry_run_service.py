"""Dry-run validation service for build simulation and verification."""

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import structlog

from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_models import Project, ProjectType
from packages.core.errors import ProcessingError, ValidationError


@dataclass
class FileConflict:
    """Represents a file path conflict."""

    path: str
    conflict_type: str  # case_sensitive, duplicate_key, encoding_mismatch
    sources: list[str]  # Source files causing conflict
    severity: str  # error, warning, info
    description: str
    suggested_resolution: str | None = None


@dataclass
class ValidationIssue:
    """Represents a validation issue found during dry-run."""

    file_path: str
    issue_type: str  # json_syntax, duplicate_keys, encoding, pack_format, size_limit
    severity: str  # error, warning, info
    line_number: int | None = None
    column_number: int | None = None
    message: str
    suggested_fix: str | None = None


@dataclass
class CoverageAnalysis:
    """Analysis of language coverage and priorities."""

    total_keys: int
    covered_keys: int
    missing_keys: int
    coverage_percentage: float
    priority_conflicts: list[str]
    override_summary: dict[str, int]  # source -> count


@dataclass
class DryRunResult:
    """Result of dry-run validation."""

    success: bool
    total_files: int
    total_size: int
    file_tree: dict[str, Any]  # Simulated file structure
    conflicts: list[FileConflict]
    validation_issues: list[ValidationIssue]
    coverage_analysis: dict[str, CoverageAnalysis]  # locale -> analysis
    pack_mcmeta_valid: bool
    pack_format_compatible: bool
    estimated_build_time: float
    warnings_count: int
    errors_count: int
    can_proceed: bool


@dataclass
class BuildConfiguration:
    """Configuration for build validation."""

    target_mc_version: str
    pack_format: int
    max_file_size: int = 1024 * 1024  # 1MB default
    max_total_size: int = 100 * 1024 * 1024  # 100MB default
    strict_json_validation: bool = True
    case_sensitive_paths: bool = False
    allow_duplicate_keys: bool = False
    encoding_validation: bool = True
    validate_pack_mcmeta: bool = True


class DryRunService:
    """Service for performing build validation and simulation."""

    def __init__(self, database: SQLCipherDatabase, logger: structlog.BoundLogger):
        self.database = database
        self.logger = logger

        # Pack format compatibility matrix
        self.pack_format_matrix = {
            "1.20.4": 18,
            "1.20.3": 18,
            "1.20.2": 18,
            "1.20.1": 15,
            "1.20": 15,
            "1.19.4": 13,
            "1.19.3": 13,
            "1.19.2": 9,
            "1.19.1": 9,
            "1.19": 9,
            "1.18.2": 8,
            "1.18.1": 8,
            "1.18": 8,
            "1.17.1": 7,
            "1.17": 7,
            "1.16.5": 6,
            "1.16.4": 6,
            "1.16.3": 6,
            "1.16.2": 6,
            "1.16.1": 6,
            "1.16": 6,
        }

    async def validate_build(
        self,
        project: Project,
        build_config: BuildConfiguration,
        selected_locales: list[str] | None = None,
    ) -> DryRunResult:
        """Perform comprehensive build validation."""

        logger = self.logger.bind(
            project_id=project.id, target_mc_version=build_config.target_mc_version
        )

        logger.info("Starting dry-run validation")

        try:
            # Get active language assets
            language_assets = self._get_active_language_assets(
                project.id, selected_locales
            )

            if not language_assets:
                raise ValidationError("No active language assets found")

            # Initialize result
            result = DryRunResult(
                success=True,
                total_files=0,
                total_size=0,
                file_tree={},
                conflicts=[],
                validation_issues=[],
                coverage_analysis={},
                pack_mcmeta_valid=False,
                pack_format_compatible=False,
                estimated_build_time=0.0,
                warnings_count=0,
                errors_count=0,
                can_proceed=True,
            )

            # Step 1: Validate pack format compatibility
            result.pack_format_compatible = self._validate_pack_format(
                build_config, result
            )

            # Step 2: Simulate file tree construction
            file_tree, conflicts = await self._simulate_file_tree(
                project, language_assets, build_config
            )
            result.file_tree = file_tree
            result.conflicts = conflicts

            # Step 3: Validate individual files
            validation_issues = await self._validate_language_files(
                language_assets, build_config
            )
            result.validation_issues = validation_issues

            # Step 4: Analyze coverage and priorities
            coverage_analysis = await self._analyze_coverage(project, language_assets)
            result.coverage_analysis = coverage_analysis

            # Step 5: Validate pack.mcmeta
            result.pack_mcmeta_valid = await self._validate_pack_mcmeta(
                project, build_config, result
            )

            # Step 6: Calculate size and performance metrics
            result.total_files = len(file_tree)
            result.total_size = sum(asset["size"] for asset in language_assets)
            result.estimated_build_time = self._estimate_build_time(
                result.total_files, result.total_size
            )

            # Step 7: Count issues and determine if build can proceed
            result.errors_count = len(
                [
                    issue
                    for issue in result.validation_issues
                    if issue.severity == "error"
                ]
            ) + len(
                [
                    conflict
                    for conflict in result.conflicts
                    if conflict.severity == "error"
                ]
            )

            result.warnings_count = len(
                [
                    issue
                    for issue in result.validation_issues
                    if issue.severity == "warning"
                ]
            ) + len(
                [
                    conflict
                    for conflict in result.conflicts
                    if conflict.severity == "warning"
                ]
            )

            # Determine if build can proceed
            result.can_proceed = (
                result.errors_count == 0
                and result.pack_format_compatible
                and result.total_size <= build_config.max_total_size
            )

            result.success = result.can_proceed

            logger.info(
                "Dry-run validation completed",
                can_proceed=result.can_proceed,
                errors=result.errors_count,
                warnings=result.warnings_count,
                total_files=result.total_files,
                total_size=result.total_size,
            )

            return result

        except Exception as e:
            logger.error("Dry-run validation failed", error=str(e), exc_info=True)
            raise ProcessingError(f"Dry-run validation failed: {str(e)}")

    def _get_active_language_assets(
        self, project_id: str, selected_locales: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Get active language assets for the project."""

        try:
            with self.database._get_connection() as conn:
                query = """
                    SELECT la.*, b.content
                    FROM locale_assets la
                    JOIN blobs b ON la.blob_id = b.id
                    WHERE la.project_id = ? AND la.is_active = 1
                """
                params = [project_id]

                if selected_locales:
                    placeholders = ",".join(["?"] * len(selected_locales))
                    query += f" AND la.locale IN ({placeholders})"
                    params.extend(selected_locales)

                query += " ORDER BY la.locale, la.modid, la.file_path"

                rows = conn.execute(query, params).fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(
                "Failed to get language assets", project_id=project_id, error=str(e)
            )
            return []

    def _validate_pack_format(
        self, build_config: BuildConfiguration, result: DryRunResult
    ) -> bool:
        """Validate pack format compatibility."""

        target_version = build_config.target_mc_version
        required_format = self.pack_format_matrix.get(target_version)

        if not required_format:
            result.validation_issues.append(
                ValidationIssue(
                    file_path="pack.mcmeta",
                    issue_type="pack_format",
                    severity="warning",
                    message=f"Unknown Minecraft version: {target_version}",
                    suggested_fix="Use a known Minecraft version",
                )
            )
            return False

        if build_config.pack_format != required_format:
            result.validation_issues.append(
                ValidationIssue(
                    file_path="pack.mcmeta",
                    issue_type="pack_format",
                    severity="error",
                    message=f"Pack format mismatch: expected {required_format} for MC {target_version}, got {build_config.pack_format}",
                    suggested_fix=f"Update pack format to {required_format}",
                )
            )
            return False

        return True

    async def _simulate_file_tree(
        self,
        project: Project,
        language_assets: list[dict[str, Any]],
        build_config: BuildConfiguration,
    ) -> tuple[dict[str, Any], list[FileConflict]]:
        """Simulate the final file tree and detect conflicts."""

        file_tree = {}
        conflicts = []
        path_registry = {}  # For case-insensitive conflict detection

        # Group assets by target path
        path_groups = defaultdict(list)

        for asset in language_assets:
            # Determine target path in resource pack
            if project.type == ProjectType.MODPACK:
                # For modpacks, organize by mod
                target_path = f"assets/{asset['modid']}/lang/{asset['locale']}.json"
            else:
                # For single mods, direct placement
                target_path = f"assets/{asset['modid']}/lang/{asset['locale']}.json"

            path_groups[target_path].append(asset)

        # Process each path group
        for target_path, assets in path_groups.items():
            # Check for case-sensitive conflicts
            lower_path = target_path.lower()
            if lower_path in path_registry:
                existing_path = path_registry[lower_path]
                if existing_path != target_path:
                    conflicts.append(
                        FileConflict(
                            path=target_path,
                            conflict_type="case_sensitive",
                            sources=[existing_path, target_path],
                            severity="error"
                            if build_config.case_sensitive_paths
                            else "warning",
                            description=f"Case-sensitive path conflict: {existing_path} vs {target_path}",
                            suggested_resolution="Rename one of the conflicting files",
                        )
                    )

            path_registry[lower_path] = target_path

            # Handle multiple assets for same path (priority resolution)
            if len(assets) > 1:
                # Sort by priority (higher priority first)
                assets.sort(key=lambda x: x.get("priority", 0), reverse=True)

                winning_asset = assets[0]
                assets[1:]

                conflicts.append(
                    FileConflict(
                        path=target_path,
                        conflict_type="priority_override",
                        sources=[asset["file_path"] for asset in assets],
                        severity="info",
                        description=f"Multiple sources for {target_path}, using highest priority",
                        suggested_resolution="Review priority settings if unexpected",
                    )
                )

                # Use winning asset
                selected_asset = winning_asset
            else:
                selected_asset = assets[0]

            # Add to file tree
            file_tree[target_path] = {
                "size": selected_asset["size"],
                "source": selected_asset["file_path"],
                "locale": selected_asset["locale"],
                "modid": selected_asset["modid"],
                "priority": selected_asset.get("priority", 0),
                "fingerprint": selected_asset["fingerprint"],
            }

        return file_tree, conflicts

    async def _validate_language_files(
        self, language_assets: list[dict[str, Any]], build_config: BuildConfiguration
    ) -> list[ValidationIssue]:
        """Validate individual language files."""

        issues = []

        for asset in language_assets:
            file_path = asset["file_path"]
            content = asset["content"]

            # Size validation
            if asset["size"] > build_config.max_file_size:
                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        issue_type="size_limit",
                        severity="error",
                        message=f"File size {asset['size']} exceeds limit {build_config.max_file_size}",
                        suggested_fix="Reduce file size or increase limit",
                    )
                )
                continue

            # Encoding validation
            if build_config.encoding_validation:
                try:
                    text_content = content.decode("utf-8")
                except UnicodeDecodeError as e:
                    issues.append(
                        ValidationIssue(
                            file_path=file_path,
                            issue_type="encoding",
                            severity="error",
                            message=f"Invalid UTF-8 encoding: {str(e)}",
                            suggested_fix="Convert file to UTF-8 encoding",
                        )
                    )
                    continue
            else:
                # Try to decode for JSON validation
                try:
                    text_content = content.decode("utf-8")
                except UnicodeDecodeError:
                    # Skip JSON validation if can't decode
                    continue

            # JSON syntax validation
            if build_config.strict_json_validation:
                try:
                    json_data = json.loads(text_content)

                    # Check for duplicate keys
                    if not build_config.allow_duplicate_keys:
                        duplicate_keys = self._find_duplicate_keys(text_content)
                        for key, line_num in duplicate_keys:
                            issues.append(
                                ValidationIssue(
                                    file_path=file_path,
                                    issue_type="duplicate_keys",
                                    severity="error",
                                    line_number=line_num,
                                    message=f"Duplicate key: {key}",
                                    suggested_fix="Remove or rename duplicate key",
                                )
                            )

                    # Validate JSON structure for language files
                    if not isinstance(json_data, dict):
                        issues.append(
                            ValidationIssue(
                                file_path=file_path,
                                issue_type="json_syntax",
                                severity="error",
                                message="Language file must be a JSON object",
                                suggested_fix="Ensure root element is an object {}",
                            )
                        )

                    # Check for empty values
                    empty_keys = [k for k, v in json_data.items() if not v]
                    if empty_keys:
                        issues.append(
                            ValidationIssue(
                                file_path=file_path,
                                issue_type="empty_values",
                                severity="warning",
                                message=f"Empty values for keys: {', '.join(empty_keys[:5])}",
                                suggested_fix="Provide translations for empty keys",
                            )
                        )

                except json.JSONDecodeError as e:
                    issues.append(
                        ValidationIssue(
                            file_path=file_path,
                            issue_type="json_syntax",
                            severity="error",
                            line_number=e.lineno,
                            column_number=e.colno,
                            message=f"JSON syntax error: {e.msg}",
                            suggested_fix="Fix JSON syntax error",
                        )
                    )

        return issues

    def _find_duplicate_keys(self, json_text: str) -> list[tuple[str, int]]:
        """Find duplicate keys in JSON text."""

        duplicates = []
        seen_keys = {}

        # Simple regex-based duplicate detection
        # This is not perfect but catches most cases
        key_pattern = re.compile(r'"([^"]+)"\s*:')

        for line_num, line in enumerate(json_text.split("\n"), 1):
            matches = key_pattern.findall(line)
            for key in matches:
                if key in seen_keys:
                    duplicates.append((key, line_num))
                else:
                    seen_keys[key] = line_num

        return duplicates

    async def _analyze_coverage(
        self, project: Project, language_assets: list[dict[str, Any]]
    ) -> dict[str, CoverageAnalysis]:
        """Analyze language coverage and priority conflicts."""

        coverage_analysis = {}

        # Get source language keys as baseline
        source_keys = set()
        source_lang = project.content_fingerprint.source_language

        if source_lang:
            source_asset = next(
                (asset for asset in language_assets if asset["locale"] == source_lang),
                None,
            )

            if source_asset:
                try:
                    source_content = json.loads(source_asset["content"].decode("utf-8"))
                    source_keys = set(source_content.keys())
                except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                    pass

        # If no source keys found, use union of all keys
        if not source_keys:
            for asset in language_assets:
                try:
                    content = json.loads(asset["content"].decode("utf-8"))
                    source_keys.update(content.keys())
                except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                    continue

        # Analyze each locale
        locale_groups = defaultdict(list)
        for asset in language_assets:
            locale_groups[asset["locale"]].append(asset)

        for locale, assets in locale_groups.items():
            # Merge all assets for this locale
            merged_keys = set()
            override_summary = defaultdict(int)
            priority_conflicts = []

            # Sort by priority
            assets.sort(key=lambda x: x.get("priority", 0), reverse=True)

            for asset in assets:
                try:
                    content = json.loads(asset["content"].decode("utf-8"))
                    asset_keys = set(content.keys())

                    # Check for conflicts with higher priority assets
                    conflicts = merged_keys.intersection(asset_keys)
                    if conflicts:
                        priority_conflicts.extend(list(conflicts))

                    merged_keys.update(asset_keys)
                    override_summary[asset["source"]] += len(asset_keys)

                except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                    continue

            # Calculate coverage
            if source_keys:
                covered_keys = len(merged_keys.intersection(source_keys))
                missing_keys = len(source_keys - merged_keys)
                total_keys = len(source_keys)
                coverage_percentage = (
                    (covered_keys / total_keys) * 100 if total_keys > 0 else 0
                )
            else:
                covered_keys = len(merged_keys)
                missing_keys = 0
                total_keys = covered_keys
                coverage_percentage = 100.0

            coverage_analysis[locale] = CoverageAnalysis(
                total_keys=total_keys,
                covered_keys=covered_keys,
                missing_keys=missing_keys,
                coverage_percentage=coverage_percentage,
                priority_conflicts=priority_conflicts,
                override_summary=dict(override_summary),
            )

        return coverage_analysis

    async def _validate_pack_mcmeta(
        self, project: Project, build_config: BuildConfiguration, result: DryRunResult
    ) -> bool:
        """Validate pack.mcmeta generation."""

        if not build_config.validate_pack_mcmeta:
            return True

        try:
            # Generate pack.mcmeta content
            pack_mcmeta = {
                "pack": {
                    "pack_format": build_config.pack_format,
                    "description": f"Language pack for {project.name} v{project.version}",
                }
            }

            # Validate JSON serialization
            json.dumps(pack_mcmeta, indent=2)

            # Check pack format compatibility
            if build_config.pack_format not in range(1, 20):  # Reasonable range
                result.validation_issues.append(
                    ValidationIssue(
                        file_path="pack.mcmeta",
                        issue_type="pack_format",
                        severity="warning",
                        message=f"Unusual pack format: {build_config.pack_format}",
                        suggested_fix="Verify pack format is correct for target MC version",
                    )
                )

            return True

        except Exception as e:
            result.validation_issues.append(
                ValidationIssue(
                    file_path="pack.mcmeta",
                    issue_type="pack_format",
                    severity="error",
                    message=f"Failed to generate pack.mcmeta: {str(e)}",
                    suggested_fix="Check project configuration",
                )
            )
            return False

    def _estimate_build_time(self, total_files: int, total_size: int) -> float:
        """Estimate build time based on file count and size."""

        # Simple estimation based on empirical data
        # Base time for setup and finalization
        base_time = 0.5

        # Time per file (JSON processing, validation)
        file_time = total_files * 0.01

        # Time per MB (I/O operations)
        size_mb = total_size / (1024 * 1024)
        size_time = size_mb * 0.1

        return base_time + file_time + size_time

    async def generate_validation_report(
        self, result: DryRunResult, include_details: bool = True
    ) -> dict[str, Any]:
        """Generate a comprehensive validation report."""

        report = {
            "summary": {
                "can_proceed": result.can_proceed,
                "total_files": result.total_files,
                "total_size": result.total_size,
                "estimated_build_time": result.estimated_build_time,
                "errors_count": result.errors_count,
                "warnings_count": result.warnings_count,
            },
            "compatibility": {
                "pack_format_compatible": result.pack_format_compatible,
                "pack_mcmeta_valid": result.pack_mcmeta_valid,
            },
            "coverage": {
                locale: {
                    "coverage_percentage": analysis.coverage_percentage,
                    "total_keys": analysis.total_keys,
                    "missing_keys": analysis.missing_keys,
                    "priority_conflicts_count": len(analysis.priority_conflicts),
                }
                for locale, analysis in result.coverage_analysis.items()
            },
        }

        if include_details:
            report["details"] = {
                "conflicts": [
                    {
                        "path": conflict.path,
                        "type": conflict.conflict_type,
                        "severity": conflict.severity,
                        "description": conflict.description,
                        "sources": conflict.sources,
                    }
                    for conflict in result.conflicts
                ],
                "validation_issues": [
                    {
                        "file_path": issue.file_path,
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "message": issue.message,
                        "line_number": issue.line_number,
                        "suggested_fix": issue.suggested_fix,
                    }
                    for issue in result.validation_issues
                ],
                "file_tree": result.file_tree
                if len(result.file_tree) < 100
                else "<truncated>",
            }

        return report
