"""Upload service for sending language packs to remote servers."""

import asyncio
import hashlib
import json
import os
import tempfile
import zipfile
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiofiles
import aiohttp
import structlog

from packages.backend_kit.websocket import send_log_message, send_progress_update
from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_models import (
    ContentFingerprint,
    LanguageFileInfo,
    Project,
    ProjectKey,
)
from packages.core.enhanced_state import ProjectState
from packages.core.errors import NetworkError, ProcessingError, ValidationError


@dataclass
class UploadTicket:
    """Upload ticket from server."""

    ticket_id: str
    upload_url: str
    expires_at: str
    max_file_size: int
    allowed_formats: list[str]
    idempotency_key: str
    metadata: dict[str, Any] | None = None


@dataclass
class UploadProgress:
    """Upload progress information."""

    total_bytes: int
    uploaded_bytes: int
    current_file: str
    files_completed: int
    total_files: int
    speed_bps: float
    eta_seconds: int | None = None


@dataclass
class UploadResult:
    """Result of upload operation."""

    success: bool
    ticket_id: str
    uploaded_files: list[str]
    total_size: int
    upload_time_seconds: float
    server_reference: str | None = None
    processing_status: str = "pending"  # pending, processing, completed, failed
    error_message: str | None = None


@dataclass
class ProcessingStatus:
    """Server-side processing status."""

    status: str  # pending, processing, completed, failed
    progress_percentage: float
    estimated_completion: str | None = None
    queue_position: int | None = None
    available_languages: list[str] = None
    error_message: str | None = None
    last_updated: str | None = None


class UploadService:
    """Service for uploading language packs to remote servers."""

    def __init__(
        self,
        database: SQLCipherDatabase,
        logger: structlog.BoundLogger,
        server_base_url: str = "https://api.transhub.example.com",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        chunk_size: int = 8192,
        max_retries: int = 3,
    ):
        self.database = database
        self.logger = logger
        self.server_base_url = server_base_url.rstrip("/")
        self.max_file_size = max_file_size
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),  # 5 minutes for uploads
            headers={"User-Agent": "MC-Studio/1.0", "Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def upload_project(
        self,
        job_id: str,
        project: Project,
        language_files: list[LanguageFileInfo],
        source_language: str = "en_us",
    ) -> UploadResult:
        """Upload project language files to server."""
        logger = self.logger.bind(
            job_id=job_id, project_id=project.id, file_count=len(language_files)
        )

        try:
            logger.info("Starting project upload")
            await send_progress_update(job_id, 0, "Preparing upload...")

            # Transition to uploading state
            if not project.state_machine.transition_to(
                ProjectState.UPLOADING,
                {"upload_started_at": datetime.now().isoformat()},
                "user",
            ):
                raise ProcessingError("Cannot transition to uploading state")

            # Generate idempotency key
            idempotency_key = self._generate_idempotency_key(
                project.key, project.content_fingerprint
            )

            await send_progress_update(job_id, 10, "Requesting upload ticket...")

            # Request upload ticket
            ticket = await self._request_upload_ticket(job_id, project, idempotency_key)

            await send_progress_update(job_id, 20, "Preparing language pack...")

            # Create upload package
            package_path = await self._create_upload_package(
                job_id, project, language_files, source_language
            )

            try:
                await send_progress_update(job_id, 40, "Uploading language pack...")

                # Upload package
                upload_result = await self._upload_package(job_id, ticket, package_path)

                await send_progress_update(job_id, 80, "Confirming upload...")

                # Confirm upload with server
                await self._confirm_upload(job_id, ticket, upload_result)

                # Transition to waiting state
                project.state_machine.transition_to(
                    ProjectState.WAITING_REMOTE,
                    {
                        "upload_completed_at": datetime.now().isoformat(),
                        "ticket_id": ticket.ticket_id,
                        "server_reference": upload_result.server_reference,
                    },
                    "system",
                )

                # Save project state
                self.database.save_project(project)

                await send_progress_update(job_id, 100, "Upload completed")

                logger.info(
                    "Project upload completed",
                    ticket_id=ticket.ticket_id,
                    uploaded_size=upload_result.total_size,
                )

                await send_log_message(
                    job_id,
                    "info",
                    f"Upload completed: {upload_result.total_size} bytes",
                )

                return upload_result

            finally:
                # Clean up temporary package
                try:
                    os.unlink(package_path)
                except Exception as e:
                    logger.warning("Failed to clean up package", error=str(e))

        except Exception as e:
            logger.error("Project upload failed", error=str(e), exc_info=True)

            # Transition to failed state
            project.state_machine.transition_to(
                ProjectState.FAILED,
                {"error": str(e), "failed_at": datetime.now().isoformat()},
                "system",
            )
            self.database.save_project(project)

            await send_log_message(job_id, "error", f"Upload failed: {str(e)}")
            raise

    async def _request_upload_ticket(
        self, job_id: str, project: Project, idempotency_key: str
    ) -> UploadTicket:
        """Request upload ticket from server."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        payload = {
            "project_key": {
                "type": project.key.type.value,
                "name": project.key.name,
                "version": project.key.version,
                "mc_version": project.key.mc_version,
                "loader": project.key.loader.value,
                "loader_version": project.key.loader_version,
            },
            "content_fingerprint": {
                "aggregate_hash": project.content_fingerprint.aggregate_hash,
                "file_count": project.content_fingerprint.file_count,
                "total_keys": project.content_fingerprint.total_keys,
                "source_language": project.content_fingerprint.source_language,
            },
            "idempotency_key": idempotency_key,
            "client_info": {
                "version": "1.0",
                "max_file_size": self.max_file_size,
                "supported_formats": ["zip", "tar.gz"],
            },
        }

        url = f"{self.server_base_url}/api/v1/projects/upload-ticket"

        try:
            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return UploadTicket(
                        ticket_id=data["ticket_id"],
                        upload_url=data["upload_url"],
                        expires_at=data["expires_at"],
                        max_file_size=data["max_file_size"],
                        allowed_formats=data["allowed_formats"],
                        idempotency_key=idempotency_key,
                        metadata=data.get("metadata"),
                    )

                elif response.status == 409:
                    # Conflict - upload already exists
                    data = await response.json()
                    existing_ticket = data.get("existing_ticket")
                    if existing_ticket:
                        await send_log_message(
                            job_id,
                            "info",
                            "Upload already exists, using existing ticket",
                        )
                        return UploadTicket(
                            ticket_id=existing_ticket["ticket_id"],
                            upload_url=existing_ticket["upload_url"],
                            expires_at=existing_ticket["expires_at"],
                            max_file_size=existing_ticket["max_file_size"],
                            allowed_formats=existing_ticket["allowed_formats"],
                            idempotency_key=idempotency_key,
                            metadata=existing_ticket.get("metadata"),
                        )
                    else:
                        raise ProcessingError(
                            "Upload conflict but no existing ticket provided"
                        )

                else:
                    error_text = await response.text()
                    raise NetworkError(
                        f"Failed to get upload ticket: {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            raise NetworkError(f"Network request failed: {str(e)}")

    async def _create_upload_package(
        self,
        job_id: str,
        project: Project,
        language_files: list[LanguageFileInfo],
        source_language: str,
    ) -> str:
        """Create ZIP package for upload."""

        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".zip", prefix="mc_studio_upload_")
        os.close(temp_fd)

        try:
            total_files = len(language_files)
            processed_files = 0

            with zipfile.ZipFile(
                temp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
            ) as zf:
                # Add metadata file
                metadata = {
                    "project_key": project.key.to_string(),
                    "content_fingerprint": project.content_fingerprint.aggregate_hash,
                    "source_language": source_language,
                    "created_at": datetime.now().isoformat(),
                    "client_version": "1.0",
                    "file_count": total_files,
                }

                zf.writestr("metadata.json", json.dumps(metadata, indent=2))

                # Group files by priority (source language first)
                source_files = [
                    f for f in language_files if f.locale == source_language
                ]
                other_files = [f for f in language_files if f.locale != source_language]

                # Process source files first
                for file_info in source_files:
                    await self._add_file_to_zip(zf, file_info, "source")
                    processed_files += 1

                    progress = int(20 + (processed_files / total_files) * 60)
                    await send_progress_update(
                        job_id,
                        progress,
                        f"Packaging {file_info.locale}/{file_info.modid}...",
                    )

                # Process other language files
                for file_info in other_files:
                    await self._add_file_to_zip(zf, file_info, "translation")
                    processed_files += 1

                    progress = int(20 + (processed_files / total_files) * 60)
                    await send_progress_update(
                        job_id,
                        progress,
                        f"Packaging {file_info.locale}/{file_info.modid}...",
                    )

            # Verify package size
            package_size = os.path.getsize(temp_path)
            if package_size > self.max_file_size:
                raise ValidationError(
                    f"Package too large: {package_size} bytes (max: {self.max_file_size})"
                )

            self.logger.info(
                "Upload package created",
                package_size=package_size,
                file_count=total_files,
            )

            return temp_path

        except Exception:
            # Clean up on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    async def _add_file_to_zip(
        self, zf: zipfile.ZipFile, file_info: LanguageFileInfo, category: str
    ) -> None:
        """Add a language file to the ZIP archive."""

        # Create archive path
        archive_path = f"{category}/{file_info.locale}/{file_info.modid}.json"

        # Read file content
        try:
            async with aiofiles.open(file_info.file_path, encoding="utf-8") as f:
                content = await f.read()

            # Validate JSON
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.warning(
                    "Invalid JSON file", file_path=file_info.file_path, error=str(e)
                )
                # Skip invalid files
                return

            # Add to ZIP
            zf.writestr(archive_path, content)

        except Exception as e:
            self.logger.warning(
                "Failed to add file to package",
                file_path=file_info.file_path,
                error=str(e),
            )
            # Continue with other files

    async def _upload_package(
        self, job_id: str, ticket: UploadTicket, package_path: str
    ) -> UploadResult:
        """Upload package to server."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        package_size = os.path.getsize(package_path)
        start_time = datetime.now()

        # Prepare upload with progress tracking
        async def upload_with_progress() -> UploadResult:
            uploaded_bytes = 0
            last_progress_time = start_time

            async def progress_callback(chunk: bytes) -> None:
                nonlocal uploaded_bytes, last_progress_time
                uploaded_bytes += len(chunk)

                now = datetime.now()
                if (
                    now - last_progress_time
                ).total_seconds() >= 1.0:  # Update every second
                    progress = int(40 + (uploaded_bytes / package_size) * 40)
                    speed_bps = uploaded_bytes / (now - start_time).total_seconds()
                    (
                        package_size - uploaded_bytes
                    ) / speed_bps if speed_bps > 0 else None

                    await send_progress_update(
                        job_id,
                        progress,
                        f"Uploading... {uploaded_bytes}/{package_size} bytes",
                    )

                    last_progress_time = now

            # Create file reader with progress
            async def file_reader() -> AsyncGenerator[bytes, None]:
                async with aiofiles.open(package_path, "rb") as f:
                    while True:
                        chunk = await f.read(self.chunk_size)
                        if not chunk:
                            break
                        await progress_callback(chunk)
                        yield chunk

            # Prepare form data
            data = aiohttp.FormData()
            data.add_field(
                "file",
                file_reader(),
                filename="language_pack.zip",
                content_type="application/zip",
            )
            data.add_field("ticket_id", ticket.ticket_id)
            data.add_field("idempotency_key", ticket.idempotency_key)

            # Upload with retries
            for attempt in range(self.max_retries):
                try:
                    async with self._session.post(
                        ticket.upload_url, data=data
                    ) as response:
                        if response.status == 200:
                            result_data = await response.json()

                            upload_time = (datetime.now() - start_time).total_seconds()

                            return UploadResult(
                                success=True,
                                ticket_id=ticket.ticket_id,
                                uploaded_files=["language_pack.zip"],
                                total_size=package_size,
                                upload_time_seconds=upload_time,
                                server_reference=result_data.get("reference"),
                                processing_status=result_data.get("status", "pending"),
                            )

                        elif response.status == 409:
                            # Already uploaded (idempotent)
                            result_data = await response.json()
                            upload_time = (datetime.now() - start_time).total_seconds()

                            await send_log_message(
                                job_id, "info", "Upload already completed (idempotent)"
                            )

                            return UploadResult(
                                success=True,
                                ticket_id=ticket.ticket_id,
                                uploaded_files=["language_pack.zip"],
                                total_size=package_size,
                                upload_time_seconds=upload_time,
                                server_reference=result_data.get("reference"),
                                processing_status=result_data.get(
                                    "status", "completed"
                                ),
                            )

                        else:
                            error_text = await response.text()
                            if attempt < self.max_retries - 1:
                                wait_time = 2**attempt  # Exponential backoff
                                await send_log_message(
                                    job_id,
                                    "warning",
                                    f"Upload failed (attempt {attempt + 1}), retrying in {wait_time}s...",
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise NetworkError(
                                    f"Upload failed: {response.status} - {error_text}"
                                )

                except aiohttp.ClientError as e:
                    if attempt < self.max_retries - 1:
                        wait_time = 2**attempt
                        await send_log_message(
                            job_id,
                            "warning",
                            f"Network error (attempt {attempt + 1}), retrying in {wait_time}s...",
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise NetworkError(
                            f"Upload failed after {self.max_retries} attempts: {str(e)}"
                        )

            # Should not reach here
            raise ProcessingError("Upload failed after all retries")

        return await upload_with_progress()

    async def _confirm_upload(
        self, job_id: str, ticket: UploadTicket, upload_result: UploadResult
    ) -> None:
        """Confirm upload completion with server."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        payload = {
            "ticket_id": ticket.ticket_id,
            "idempotency_key": ticket.idempotency_key,
            "upload_result": {
                "total_size": upload_result.total_size,
                "upload_time_seconds": upload_result.upload_time_seconds,
                "client_checksum": upload_result.server_reference,
            },
        }

        url = f"{self.server_base_url}/api/v1/projects/upload-confirm"

        try:
            async with self._session.post(url, json=payload) as response:
                if response.status in [200, 202]:  # OK or Accepted
                    await send_log_message(job_id, "info", "Upload confirmed")
                else:
                    error_text = await response.text()
                    self.logger.warning(
                        "Upload confirmation failed",
                        status=response.status,
                        error=error_text,
                    )
                    # Non-fatal - upload was successful

        except Exception as e:
            self.logger.warning("Upload confirmation failed", error=str(e))
            # Non-fatal - upload was successful

    def _generate_idempotency_key(
        self, project_key: ProjectKey, content_fingerprint: ContentFingerprint
    ) -> str:
        """Generate idempotency key for upload."""
        key_data = f"{project_key.to_string()}:{content_fingerprint.aggregate_hash}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def poll_processing_status(
        self,
        job_id: str,
        ticket_id: str,
        max_poll_time_seconds: int = 3600,  # 1 hour
        initial_delay: int = 30,
        max_delay: int = 300,  # 5 minutes
    ) -> ProcessingStatus:
        """Poll server for processing status with exponential backoff."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        url = f"{self.server_base_url}/api/v1/projects/processing-status/{ticket_id}"

        start_time = datetime.now()
        delay = initial_delay

        while True:
            try:
                # Check if we've exceeded max poll time
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > max_poll_time_seconds:
                    raise ProcessingError("Processing timeout exceeded")

                async with self._session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = ProcessingStatus(
                            status=data["status"],
                            progress_percentage=data.get("progress_percentage", 0),
                            estimated_completion=data.get("estimated_completion"),
                            queue_position=data.get("queue_position"),
                            available_languages=data.get("available_languages", []),
                            error_message=data.get("error_message"),
                            last_updated=data.get("last_updated"),
                        )

                        # Update progress
                        await send_progress_update(
                            job_id,
                            int(status.progress_percentage),
                            f"Processing... {status.status}",
                        )

                        # Check if processing is complete
                        if status.status in ["completed", "failed"]:
                            return status

                        # Log status updates
                        if status.queue_position:
                            await send_log_message(
                                job_id,
                                "info",
                                f"Queue position: {status.queue_position}",
                            )

                        if status.estimated_completion:
                            await send_log_message(
                                job_id,
                                "info",
                                f"Estimated completion: {status.estimated_completion}",
                            )

                    elif response.status == 404:
                        raise ProcessingError("Processing ticket not found")

                    else:
                        error_text = await response.text()
                        self.logger.warning(
                            "Status check failed",
                            status=response.status,
                            error=error_text,
                        )

                # Wait before next poll (exponential backoff)
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, max_delay)

            except aiohttp.ClientError as e:
                self.logger.warning("Status check network error", error=str(e))
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, max_delay)

            except Exception as e:
                self.logger.error("Status check failed", error=str(e))
                raise

    async def cancel_upload(self, job_id: str, ticket_id: str) -> bool:
        """Cancel an ongoing upload or processing."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        url = f"{self.server_base_url}/api/v1/projects/cancel/{ticket_id}"

        try:
            async with self._session.delete(url) as response:
                if response.status in [200, 204]:
                    await send_log_message(job_id, "info", "Upload cancelled")
                    return True
                elif response.status == 404:
                    await send_log_message(job_id, "warning", "Upload not found")
                    return False
                else:
                    error_text = await response.text()
                    await send_log_message(
                        job_id,
                        "error",
                        f"Cancel failed: {response.status} - {error_text}",
                    )
                    return False

        except Exception as e:
            self.logger.error("Cancel request failed", error=str(e))
            await send_log_message(job_id, "error", f"Cancel failed: {str(e)}")
            return False
