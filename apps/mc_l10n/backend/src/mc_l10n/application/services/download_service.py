"""Download service for retrieving language packs from remote servers."""

import asyncio
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiofiles
import aiohttp
import structlog

from packages.backend_kit.websocket import send_log_message, send_progress_update
from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_models import Project
from packages.core.enhanced_state import ProjectState
from packages.core.errors import NetworkError, ProcessingError, ValidationError

from .server_resolution_service import LanguageAvailability


@dataclass
class DownloadRequest:
    """Request for downloading specific languages."""

    project_id: str
    selected_languages: list[str]
    download_strategy: str = (
        "recommended"  # recommended, missing_only, all, differential
    )
    force_redownload: bool = False
    verify_integrity: bool = True


@dataclass
class DownloadProgress:
    """Download progress information."""

    total_files: int
    completed_files: int
    failed_files: int
    current_file: str
    current_locale: str
    total_bytes: int
    downloaded_bytes: int
    speed_bps: float
    eta_seconds: int | None = None


@dataclass
class DownloadResult:
    """Result of download operation."""

    success: bool
    downloaded_languages: list[str]
    failed_languages: list[str]
    total_files: int
    total_size: int
    download_time_seconds: float
    integrity_check_passed: bool
    blob_ids: list[str]  # IDs of stored BLOBs
    coverage_matrix_updated: bool = False
    error_messages: list[str] = None


@dataclass
class LanguageDownload:
    """Information about a language download."""

    locale: str
    availability: LanguageAvailability
    download_url: str
    expected_hash: str
    expected_size: int
    priority: int = 0  # Higher priority downloads first


class DownloadService:
    """Service for downloading language packs from remote servers."""

    def __init__(
        self,
        database: SQLCipherDatabase,
        logger: structlog.BoundLogger,
        max_concurrent_downloads: int = 3,
        chunk_size: int = 8192,
        max_retries: int = 3,
        verify_ssl: bool = True,
    ):
        self.database = database
        self.logger = logger
        self.max_concurrent_downloads = max_concurrent_downloads
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = None
        self._download_semaphore = asyncio.Semaphore(max_concurrent_downloads)

    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            limit=20, limit_per_host=10, verify_ssl=self.verify_ssl
        )

        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=300),  # 5 minutes per file
            headers={
                "User-Agent": "MC-Studio/1.0",
                "Accept": "application/octet-stream, application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def download_languages(
        self,
        job_id: str,
        project: Project,
        download_request: DownloadRequest,
        available_languages: list[LanguageAvailability],
    ) -> DownloadResult:
        """Download selected languages for a project."""
        logger = self.logger.bind(
            job_id=job_id,
            project_id=project.id,
            selected_languages=download_request.selected_languages,
        )

        try:
            logger.info("Starting language downloads")
            await send_progress_update(job_id, 0, "Preparing downloads...")

            # Transition to downloading state
            if not project.state_machine.transition_to(
                ProjectState.DOWNLOADING,
                {"download_started_at": datetime.now().isoformat()},
                "user",
            ):
                raise ProcessingError("Cannot transition to downloading state")

            # Prepare download list
            downloads = await self._prepare_download_list(
                job_id, project, download_request, available_languages
            )

            if not downloads:
                await send_log_message(job_id, "info", "No downloads needed")
                return DownloadResult(
                    success=True,
                    downloaded_languages=[],
                    failed_languages=[],
                    total_files=0,
                    total_size=0,
                    download_time_seconds=0,
                    integrity_check_passed=True,
                    blob_ids=[],
                    coverage_matrix_updated=False,
                )

            await send_progress_update(
                job_id, 10, f"Downloading {len(downloads)} language packs..."
            )

            start_time = datetime.now()

            # Execute downloads concurrently
            download_results = await self._execute_downloads(job_id, project, downloads)

            # Process results
            successful_downloads = [r for r in download_results if r["success"]]
            failed_downloads = [r for r in download_results if not r["success"]]

            await send_progress_update(job_id, 80, "Processing downloaded files...")

            # Store successful downloads in database
            blob_ids = []
            for result in successful_downloads:
                blob_id = await self._store_download_in_database(project, result)
                if blob_id:
                    blob_ids.append(blob_id)

            await send_progress_update(job_id, 90, "Updating coverage matrix...")

            # Update coverage matrix
            coverage_updated = await self._update_coverage_matrix(
                project, successful_downloads
            )

            # Calculate totals
            total_size = sum(r["size"] for r in successful_downloads)
            download_time = (datetime.now() - start_time).total_seconds()

            # Transition to appropriate next state
            if failed_downloads:
                # Partial success - stay in current state or transition to failed
                if not successful_downloads:
                    project.state_machine.transition_to(
                        ProjectState.FAILED,
                        {
                            "error": "All downloads failed",
                            "failed_at": datetime.now().isoformat(),
                        },
                        "system",
                    )
                else:
                    # Partial success - log warnings but continue
                    await send_log_message(
                        job_id, "warning", f"{len(failed_downloads)} downloads failed"
                    )
            else:
                # All downloads successful
                project.state_machine.transition_to(
                    ProjectState.READY_TO_BUILD,
                    {
                        "download_completed_at": datetime.now().isoformat(),
                        "downloaded_languages": [
                            r["locale"] for r in successful_downloads
                        ],
                    },
                    "system",
                )

            # Save project state
            self.database.save_project(project)

            await send_progress_update(job_id, 100, "Downloads completed")

            result = DownloadResult(
                success=len(failed_downloads) == 0,
                downloaded_languages=[r["locale"] for r in successful_downloads],
                failed_languages=[r["locale"] for r in failed_downloads],
                total_files=len(downloads),
                total_size=total_size,
                download_time_seconds=download_time,
                integrity_check_passed=all(
                    r.get("integrity_ok", True) for r in successful_downloads
                ),
                blob_ids=blob_ids,
                coverage_matrix_updated=coverage_updated,
                error_messages=[r["error"] for r in failed_downloads if r.get("error")],
            )

            logger.info(
                "Language downloads completed",
                successful=len(successful_downloads),
                failed=len(failed_downloads),
                total_size=total_size,
            )

            return result

        except Exception as e:
            logger.error("Language downloads failed", error=str(e), exc_info=True)

            # Transition to failed state
            project.state_machine.transition_to(
                ProjectState.FAILED,
                {"error": str(e), "failed_at": datetime.now().isoformat()},
                "system",
            )
            self.database.save_project(project)

            await send_log_message(job_id, "error", f"Downloads failed: {str(e)}")
            raise

    async def _prepare_download_list(
        self,
        job_id: str,
        project: Project,
        download_request: DownloadRequest,
        available_languages: list[LanguageAvailability],
    ) -> list[LanguageDownload]:
        """Prepare list of downloads based on strategy and current state."""

        downloads = []

        # Get currently stored languages for this project
        stored_languages = self._get_stored_languages(project.id)

        # Filter available languages based on selection and strategy
        for availability in available_languages:
            locale = availability.locale

            # Check if language is selected
            if locale not in download_request.selected_languages:
                continue

            # Apply download strategy
            should_download = False
            priority = 0

            if download_request.download_strategy == "all":
                should_download = True
                priority = 1

            elif download_request.download_strategy == "missing_only":
                if locale not in stored_languages:
                    should_download = True
                    priority = 2

            elif download_request.download_strategy == "differential":
                stored_fingerprint = stored_languages.get(locale)
                if (
                    not stored_fingerprint
                    or stored_fingerprint != availability.fingerprint
                ):
                    should_download = True
                    priority = 3

            elif download_request.download_strategy == "recommended":
                # Download if missing or if it's a recommended language
                if (
                    locale not in stored_languages
                    or availability.quality_score
                    and availability.quality_score > 0.8
                ):
                    should_download = True
                    priority = 4

            # Force redownload overrides strategy
            if download_request.force_redownload:
                should_download = True
                priority = 5

            if should_download:
                # Validate download URL
                if not availability.download_url:
                    await send_log_message(
                        job_id, "warning", f"No download URL for {locale}"
                    )
                    continue

                download = LanguageDownload(
                    locale=locale,
                    availability=availability,
                    download_url=availability.download_url,
                    expected_hash=availability.fingerprint,
                    expected_size=availability.size,
                    priority=priority,
                )
                downloads.append(download)

        # Sort by priority (higher first)
        downloads.sort(key=lambda x: x.priority, reverse=True)

        self.logger.info(
            "Prepared download list",
            total_downloads=len(downloads),
            strategy=download_request.download_strategy,
        )

        return downloads

    def _get_stored_languages(self, project_id: str) -> dict[str, str]:
        """Get currently stored languages and their fingerprints."""
        try:
            with self.database._get_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT locale, fingerprint
                    FROM locale_assets
                    WHERE project_id = ? AND is_active = 1
                """,
                    (project_id,),
                ).fetchall()

                return {row["locale"]: row["fingerprint"] for row in rows}

        except Exception as e:
            self.logger.warning("Failed to get stored languages", error=str(e))
            return {}

    async def _execute_downloads(
        self, job_id: str, project: Project, downloads: list[LanguageDownload]
    ) -> list[dict[str, Any]]:
        """Execute downloads concurrently with progress tracking."""

        total_downloads = len(downloads)
        completed_downloads = 0
        results = []

        async def download_single(download: LanguageDownload) -> dict[str, Any]:
            nonlocal completed_downloads

            async with self._download_semaphore:
                try:
                    result = await self._download_language_file(job_id, download)

                    completed_downloads += 1
                    progress = int(10 + (completed_downloads / total_downloads) * 70)

                    await send_progress_update(
                        job_id,
                        progress,
                        f"Downloaded {download.locale} ({completed_downloads}/{total_downloads})",
                    )

                    return result

                except Exception as e:
                    self.logger.error(
                        "Download failed", locale=download.locale, error=str(e)
                    )

                    completed_downloads += 1
                    progress = int(10 + (completed_downloads / total_downloads) * 70)

                    await send_progress_update(
                        job_id,
                        progress,
                        f"Failed {download.locale} ({completed_downloads}/{total_downloads})",
                    )

                    return {
                        "success": False,
                        "locale": download.locale,
                        "error": str(e),
                    }

        # Execute all downloads concurrently
        tasks = [download_single(download) for download in downloads]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        return results

    async def _download_language_file(
        self, job_id: str, download: LanguageDownload
    ) -> dict[str, Any]:
        """Download a single language file with retries and verification."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        for attempt in range(self.max_retries):
            try:
                # Create temporary file
                temp_fd, temp_path = tempfile.mkstemp(
                    suffix=".json", prefix=f"mc_studio_download_{download.locale}_"
                )
                os.close(temp_fd)

                try:
                    # Download file
                    downloaded_size = await self._download_to_file(
                        download.download_url, temp_path
                    )

                    # Verify size
                    if downloaded_size != download.expected_size:
                        raise ValidationError(
                            f"Size mismatch: expected {download.expected_size}, got {downloaded_size}"
                        )

                    # Verify hash
                    actual_hash = await self._calculate_file_hash(temp_path)
                    if actual_hash != download.expected_hash:
                        raise ValidationError(
                            f"Hash mismatch: expected {download.expected_hash}, got {actual_hash}"
                        )

                    # Verify JSON format
                    await self._verify_json_format(temp_path)

                    # Read file content for storage
                    async with aiofiles.open(temp_path, "rb") as f:
                        content = await f.read()

                    return {
                        "success": True,
                        "locale": download.locale,
                        "content": content,
                        "size": downloaded_size,
                        "hash": actual_hash,
                        "integrity_ok": True,
                        "availability": download.availability,
                    }

                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass

            except Exception:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    await send_log_message(
                        job_id,
                        "warning",
                        f"Download failed for {download.locale} (attempt {attempt + 1}), retrying in {wait_time}s...",
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

        # Should not reach here
        raise ProcessingError(f"Download failed after {self.max_retries} attempts")

    async def _download_to_file(self, url: str, file_path: str) -> int:
        """Download URL content to file and return size."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        downloaded_size = 0

        async with self._session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise NetworkError(f"Download failed: {response.status} - {error_text}")

            async with aiofiles.open(file_path, "wb") as f:
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    await f.write(chunk)
                    downloaded_size += len(chunk)

        return downloaded_size

    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        hasher = hashlib.sha256()

        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(self.chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)

        return hasher.hexdigest()

    async def _verify_json_format(self, file_path: str) -> None:
        """Verify that file contains valid JSON."""
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            json.loads(content)

        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}")

        except UnicodeDecodeError as e:
            raise ValidationError(f"Invalid UTF-8 encoding: {str(e)}")

    async def _store_download_in_database(
        self, project: Project, download_result: dict[str, Any]
    ) -> str | None:
        """Store downloaded content in database BLOB pool."""

        try:
            content = download_result["content"]
            locale = download_result["locale"]
            availability = download_result["availability"]

            # Store in BLOB pool
            blob_id = self.database.store_blob(content)

            # Create locale asset record
            asset_data = {
                "project_id": project.id,
                "locale": locale,
                "modid": "*",  # Will be updated during processing
                "file_path": f"assets/{locale}/lang/combined.json",
                "blob_id": blob_id,
                "fingerprint": download_result["hash"],
                "size": download_result["size"],
                "is_active": True,
                "source": "remote_download",
                "quality_score": availability.quality_score,
                "completion_percentage": availability.completion_percentage,
                "downloaded_at": datetime.now().isoformat(),
            }

            self.database.save_language_file_asset(asset_data)

            self.logger.info(
                "Stored download in database",
                locale=locale,
                blob_id=blob_id,
                size=download_result["size"],
            )

            return blob_id

        except Exception as e:
            self.logger.error(
                "Failed to store download",
                locale=download_result.get("locale"),
                error=str(e),
            )
            return None

    async def _update_coverage_matrix(
        self, project: Project, successful_downloads: list[dict[str, Any]]
    ) -> bool:
        """Update language coverage matrix after downloads."""

        try:
            with self.database._get_connection() as conn:
                for download in successful_downloads:
                    locale = download["locale"]

                    # Update or insert coverage matrix entry
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO lang_coverage_matrix
                        (project_id, locale, modid, status, priority, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            project.id,
                            locale,
                            "*",  # Will be updated during detailed processing
                            "present",
                            1,  # Downloaded content has high priority
                            datetime.now().isoformat(),
                        ),
                    )

                conn.commit()

            self.logger.info(
                "Updated coverage matrix",
                project_id=project.id,
                updated_locales=[d["locale"] for d in successful_downloads],
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to update coverage matrix", project_id=project.id, error=str(e)
            )
            return False

    async def get_download_recommendations(
        self,
        project: Project,
        available_languages: list[LanguageAvailability],
        user_preferences: dict[str, Any] | None = None,
    ) -> list[str]:
        """Get smart download recommendations based on project and user preferences."""

        recommendations = []
        stored_languages = self._get_stored_languages(project.id)

        # Always recommend source language if available and not stored
        source_lang = project.content_fingerprint.source_language
        if source_lang:
            source_available = any(
                lang.locale == source_lang for lang in available_languages
            )
            if source_available and source_lang not in stored_languages:
                recommendations.append(source_lang)

        # Recommend high-quality languages
        quality_languages = [
            lang
            for lang in available_languages
            if (
                lang.quality_score
                and lang.quality_score > 0.8
                and lang.completion_percentage
                and lang.completion_percentage > 90
                and lang.locale not in stored_languages
                and lang.locale != source_lang
            )
        ]

        # Sort by quality metrics
        quality_languages.sort(
            key=lambda x: (x.quality_score or 0, x.completion_percentage or 0),
            reverse=True,
        )

        # Add top quality languages
        for lang in quality_languages[:3]:
            recommendations.append(lang.locale)

        # Add user preference languages if specified
        if user_preferences and "preferred_languages" in user_preferences:
            for locale in user_preferences["preferred_languages"]:
                if (
                    locale not in recommendations
                    and locale not in stored_languages
                    and any(lang.locale == locale for lang in available_languages)
                ):
                    recommendations.append(locale)

        # Add common languages if not already included
        common_languages = ["zh_cn", "es_es", "fr_fr", "de_de", "ja_jp", "ko_kr"]
        for locale in common_languages:
            if (
                locale not in recommendations
                and locale not in stored_languages
                and any(lang.locale == locale for lang in available_languages)
            ):
                recommendations.append(locale)
                if len(recommendations) >= 8:  # Limit recommendations
                    break

        return recommendations

    async def cleanup_failed_downloads(
        self, project_id: str, max_age_hours: int = 24
    ) -> int:
        """Clean up failed download records older than specified age."""

        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            with self.database._get_connection() as conn:
                # Get failed download blob IDs
                failed_blobs = conn.execute(
                    """
                    SELECT DISTINCT blob_id
                    FROM locale_assets
                    WHERE project_id = ?
                      AND source = 'remote_download'
                      AND is_active = 0
                      AND downloaded_at < ?
                """,
                    (project_id, cutoff_time.isoformat()),
                ).fetchall()

                # Delete failed records
                deleted_count = conn.execute(
                    """
                    DELETE FROM locale_assets
                    WHERE project_id = ?
                      AND source = 'remote_download'
                      AND is_active = 0
                      AND downloaded_at < ?
                """,
                    (project_id, cutoff_time.isoformat()),
                ).rowcount

                # Release associated blobs
                for row in failed_blobs:
                    self.database.release_blob(row["blob_id"])

                conn.commit()

            self.logger.info(
                "Cleaned up failed downloads",
                project_id=project_id,
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "Failed to cleanup downloads", project_id=project_id, error=str(e)
            )
            return 0
