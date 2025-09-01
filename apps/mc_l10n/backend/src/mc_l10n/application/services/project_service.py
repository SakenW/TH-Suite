"""Project creation and management service."""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from packages.backend_kit.websocket import send_log_message, send_progress_update
from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_models import (
    MinecraftLoader,
    Project,
    ProjectKey,
    ProjectSettings,
    ProjectState,
    ProjectType,
)
from packages.core.enhanced_state import ProjectStateMachine
from packages.core.errors import ProcessingError, ValidationError

from .enhanced_scan_service import EnhancedScanService


class ProjectService:
    """Service for project creation and management."""

    def __init__(self, database: SQLCipherDatabase, logger: structlog.BoundLogger):
        self.database = database
        self.logger = logger
        self.scan_service = EnhancedScanService(
            logger, None
        )  # Will set state machine later

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
        settings: dict[str, Any] | None = None,
    ) -> Project:
        """Create a new project with validation and setup."""
        logger = self.logger.bind(job_id=job_id, phase="create_project")

        try:
            logger.info(
                "Starting project creation",
                name=name,
                version=version,
                directory=directory,
            )
            await send_progress_update(job_id, 0, "Validating project parameters...")

            # Validate input parameters
            await self._validate_project_parameters(
                directory,
                project_type,
                name,
                version,
                mc_version,
                loader,
                loader_version,
            )

            # Create project settings
            project_settings = ProjectSettings()
            if settings:
                project_settings.update_from_dict(settings)

            # Create project key and ID
            project_key = ProjectKey(
                type=project_type,
                name=name,
                version=version,
                mc_version=mc_version,
                loader=loader,
                loader_version=loader_version,
            )

            project_id = self._generate_project_id(project_key)

            # Check if project already exists
            existing_project = self.database.load_project(project_id)
            if existing_project:
                logger.warning("Project already exists", project_id=project_id)
                await send_log_message(
                    job_id, "warning", f"Project already exists: {name} v{version}"
                )
                return existing_project

            await send_progress_update(job_id, 20, "Creating project structure...")

            # Create state machine
            state_machine = ProjectStateMachine(ProjectState.NEW, logger)

            # Create project
            project = Project(
                id=project_id,
                key=project_key,
                state=ProjectState.NEW,
                settings=project_settings,
                metadata={
                    "source_directory": directory,
                    "created_at": datetime.now().isoformat(),
                    "created_by": "user",
                },
                state_machine=state_machine,
            )

            await send_progress_update(job_id, 40, "Performing initial validation...")

            # Perform pre-checks
            await self._perform_project_prechecks(project, directory, job_id)

            await send_progress_update(job_id, 60, "Saving project to database...")

            # Save project to database
            self.database.save_project(project)

            await send_progress_update(job_id, 80, "Setting up project workspace...")

            # Setup project workspace
            await self._setup_project_workspace(project, job_id)

            await send_progress_update(job_id, 100, "Project created successfully")

            logger.info(
                "Project created successfully",
                project_id=project_id,
                project_key=project_key.to_string(),
            )

            await send_log_message(
                job_id, "info", f"Project created: {name} v{version} ({project_id[:8]})"
            )

            return project

        except Exception as e:
            logger.error("Project creation failed", error=str(e), exc_info=True)
            await send_log_message(
                job_id, "error", f"Project creation failed: {str(e)}"
            )
            raise

    async def start_recognition(
        self, job_id: str, project: Project, context: dict[str, Any]
    ) -> Project:
        """Start the recognition phase for a project."""
        logger = self.logger.bind(
            job_id=job_id, project_id=project.id, phase="recognition"
        )

        try:
            # Transition to recognition state
            if not project.state_machine.transition_to(
                ProjectState.RECOGNIZED,
                {"recognition_started_at": datetime.now().isoformat()},
                "user",
            ):
                raise ProcessingError("Cannot transition to recognition state")

            # Set up scan service with project's state machine
            self.scan_service.state_machine = project.state_machine

            # Perform detailed recognition
            source_directory = project.metadata.get("source_directory")
            if not source_directory:
                raise ValidationError("Source directory not found in project metadata")

            recognition_report = await self.scan_service.perform_detailed_recognition(
                job_id, project, source_directory, context
            )

            # Update project with recognition results
            project.recognition_report = recognition_report

            # Save updated project
            self.database.save_project(project)

            logger.info("Recognition completed", project_id=project.id)
            return project

        except Exception as e:
            logger.error("Recognition failed", project_id=project.id, error=str(e))
            project.state_machine.transition_to(
                ProjectState.FAILED,
                {"error": str(e), "failed_at": datetime.now().isoformat()},
                "system",
            )
            self.database.save_project(project)
            raise

    async def _validate_project_parameters(
        self,
        directory: str,
        project_type: ProjectType,
        name: str,
        version: str,
        mc_version: str,
        loader: MinecraftLoader,
        loader_version: str,
    ) -> None:
        """Validate project creation parameters."""

        # Validate directory
        directory_path = Path(directory)
        if not directory_path.exists():
            raise ValidationError(f"Directory does not exist: {directory}")

        if not directory_path.is_dir():
            raise ValidationError(f"Path is not a directory: {directory}")

        if not os.access(directory_path, os.R_OK):
            raise ValidationError(f"Directory is not readable: {directory}")

        # Validate name
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty")

        if len(name) > 100:
            raise ValidationError("Project name too long (max 100 characters)")

        # Validate version
        if not version or not version.strip():
            raise ValidationError("Project version cannot be empty")

        if len(version) > 50:
            raise ValidationError("Project version too long (max 50 characters)")

        # Validate MC version
        if not mc_version or not mc_version.strip():
            raise ValidationError("Minecraft version cannot be empty")

        # Basic MC version format check
        if (
            not mc_version.replace(".", "")
            .replace("-", "")
            .replace("_", "")
            .replace("w", "")
            .isalnum()
        ):
            raise ValidationError(f"Invalid Minecraft version format: {mc_version}")

        # Validate loader version
        if not loader_version or not loader_version.strip():
            raise ValidationError("Loader version cannot be empty")

        # Check for basic project structure based on type
        if project_type == ProjectType.MODPACK:
            # Look for modpack indicators
            modpack_indicators = [
                "manifest.json",  # CurseForge
                "modrinth.index.json",  # Modrinth
                "instance.cfg",  # MultiMC
                "mmc-pack.json",  # MultiMC
                "config",  # Config directory
                "mods",  # Mods directory
            ]

            found_indicators = []
            for indicator in modpack_indicators:
                if (directory_path / indicator).exists():
                    found_indicators.append(indicator)

            if not found_indicators:
                self.logger.warning(
                    "No modpack indicators found",
                    directory=directory,
                    expected=modpack_indicators,
                )

        elif project_type == ProjectType.MOD:
            # Look for mod indicators
            mod_indicators = [
                "src/main/java",  # Source code
                "src/main/resources",  # Resources
                "build.gradle",  # Gradle build
                "gradle.properties",  # Gradle properties
                "mods.toml",  # Forge mod info
                "fabric.mod.json",  # Fabric mod info
                "quilt.mod.json",  # Quilt mod info
            ]

            found_indicators = []
            for indicator in mod_indicators:
                if (directory_path / indicator).exists():
                    found_indicators.append(indicator)

            if not found_indicators:
                self.logger.warning(
                    "No mod indicators found",
                    directory=directory,
                    expected=mod_indicators,
                )

    def _generate_project_id(self, project_key: ProjectKey) -> str:
        """Generate a unique project ID from project key."""
        key_string = project_key.to_string()
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    async def _perform_project_prechecks(
        self, project: Project, directory: str, job_id: str
    ) -> None:
        """Perform project pre-checks."""
        directory_path = Path(directory)
        warnings = []

        # Check available disk space
        try:
            if hasattr(os, "statvfs"):  # Unix-like systems
                stat = os.statvfs(directory_path)
                available_bytes = stat.f_bavail * stat.f_frsize
            else:  # Windows
                import shutil

                _, _, available_bytes = shutil.disk_usage(directory_path)

            # Warn if less than 1GB available
            if available_bytes < 1024 * 1024 * 1024:
                warnings.append(
                    f"Low disk space: {available_bytes // (1024 * 1024)} MB available"
                )

        except Exception as e:
            self.logger.warning("Could not check disk space", error=str(e))

        # Check for large directories that might slow processing
        try:
            total_files = sum(1 for _ in directory_path.rglob("*") if _.is_file())
            if total_files > 10000:
                warnings.append(f"Large project detected: {total_files} files")

        except Exception as e:
            self.logger.warning("Could not count files", error=str(e))

        # Check for common problematic patterns
        problematic_patterns = [
            "**/.git/**",  # Git repositories
            "**/node_modules/**",  # Node.js modules
            "**/target/**",  # Maven/Gradle build outputs
            "**/build/**",  # Build outputs
            "**/.gradle/**",  # Gradle cache
            "**/__pycache__/**",  # Python cache
        ]

        for pattern in problematic_patterns:
            matches = list(directory_path.glob(pattern))
            if matches:
                warnings.append(
                    f"Found {len(matches)} files matching pattern: {pattern}"
                )

        # Log warnings
        if warnings:
            for warning in warnings:
                await send_log_message(job_id, "warning", warning)
                self.logger.warning("Project precheck warning", warning=warning)

        # Update project metadata with precheck results
        project.metadata["precheck_warnings"] = warnings
        project.metadata["precheck_completed_at"] = datetime.now().isoformat()

    async def _setup_project_workspace(self, project: Project, job_id: str) -> None:
        """Setup project workspace and initial configuration."""

        # Create project-specific settings if needed
        if not project.settings.workspace_path:
            # Use a workspace directory relative to the source
            source_dir = Path(project.metadata["source_directory"])
            workspace_dir = source_dir / ".transhub"
            workspace_dir.mkdir(exist_ok=True)
            project.settings.workspace_path = str(workspace_dir)

        # Initialize project-specific configuration
        config = {
            "project_id": project.id,
            "project_key": project.key.to_string(),
            "created_at": project.metadata["created_at"],
            "version": "1.0",
        }

        # Save configuration to workspace
        workspace_path = Path(project.settings.workspace_path)
        config_file = workspace_path / "project.json"

        try:
            import json

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            await send_log_message(
                job_id, "info", f"Workspace created: {workspace_path}"
            )

        except Exception as e:
            self.logger.warning("Failed to create workspace config", error=str(e))
            # Non-fatal error, continue

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects in the database."""
        try:
            with self.database._get_connection() as conn:
                rows = conn.execute("""
                    SELECT id, project_key, name, version, mc_version, loader,
                           type, state, created_at, updated_at
                    FROM projects
                    ORDER BY updated_at DESC
                """).fetchall()

                projects = []
                for row in rows:
                    projects.append(
                        {
                            "id": row["id"],
                            "project_key": row["project_key"],
                            "name": row["name"],
                            "version": row["version"],
                            "mc_version": row["mc_version"],
                            "loader": row["loader"],
                            "type": row["type"],
                            "state": row["state"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        }
                    )

                return projects

        except Exception as e:
            self.logger.error("Failed to list projects", error=str(e))
            raise ProcessingError(f"Failed to list projects: {str(e)}")

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and its associated data."""
        try:
            # Load project to get metadata
            project = self.database.load_project(project_id)
            if not project:
                return False

            with self.database._get_connection() as conn:
                # Get all blob IDs associated with this project
                blob_rows = conn.execute(
                    "SELECT DISTINCT blob_id FROM locale_assets WHERE project_id = ?",
                    (project_id,),
                ).fetchall()

                # Release all blobs
                for row in blob_rows:
                    self.database.release_blob(row["blob_id"])

                # Delete project (cascades to related tables)
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                conn.commit()

                # Clean up workspace if it exists
                if project.settings and project.settings.workspace_path:
                    workspace_path = Path(project.settings.workspace_path)
                    if workspace_path.exists():
                        try:
                            import shutil

                            shutil.rmtree(workspace_path)
                        except Exception as e:
                            self.logger.warning(
                                "Failed to clean up workspace", error=str(e)
                            )

                self.logger.info("Project deleted", project_id=project_id)
                return True

        except Exception as e:
            self.logger.error(
                "Failed to delete project", project_id=project_id, error=str(e)
            )
            raise ProcessingError(f"Failed to delete project: {str(e)}")

    def get_project_stats(self, project_id: str) -> dict[str, Any]:
        """Get statistics for a specific project."""
        try:
            with self.database._get_connection() as conn:
                # Basic project info
                project_row = conn.execute(
                    "SELECT * FROM projects WHERE id = ?", (project_id,)
                ).fetchone()

                if not project_row:
                    raise ValidationError(f"Project not found: {project_id}")

                # Asset statistics
                asset_stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_assets,
                        COUNT(DISTINCT modid) as unique_mods,
                        COUNT(DISTINCT locale) as unique_locales,
                        SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_assets
                    FROM locale_assets
                    WHERE project_id = ?
                """,
                    (project_id,),
                ).fetchone()

                # Coverage matrix stats
                coverage_stats = conn.execute(
                    """
                    SELECT
                        status,
                        COUNT(*) as count
                    FROM lang_coverage_matrix
                    WHERE project_id = ?
                    GROUP BY status
                """,
                    (project_id,),
                ).fetchall()

                # State transition count
                transition_count = conn.execute(
                    "SELECT COUNT(*) FROM state_transitions WHERE project_id = ?",
                    (project_id,),
                ).fetchone()[0]

                return {
                    "project_id": project_id,
                    "name": project_row["name"],
                    "version": project_row["version"],
                    "state": project_row["state"],
                    "total_assets": asset_stats["total_assets"] or 0,
                    "unique_mods": asset_stats["unique_mods"] or 0,
                    "unique_locales": asset_stats["unique_locales"] or 0,
                    "active_assets": asset_stats["active_assets"] or 0,
                    "coverage_stats": {
                        row["status"]: row["count"] for row in coverage_stats
                    },
                    "transition_count": transition_count,
                    "created_at": project_row["created_at"],
                    "updated_at": project_row["updated_at"],
                }

        except Exception as e:
            self.logger.error(
                "Failed to get project stats", project_id=project_id, error=str(e)
            )
            raise ProcessingError(f"Failed to get project stats: {str(e)}")
