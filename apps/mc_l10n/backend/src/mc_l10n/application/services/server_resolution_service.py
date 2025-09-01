"""Server resolution service for checking project existence and availability."""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import structlog

from packages.backend_kit.websocket import send_log_message, send_progress_update
from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_models import ContentFingerprint, ProjectKey
from packages.core.errors import NetworkError


@dataclass
class LanguageAvailability:
    """Information about available language for a project."""

    locale: str
    fingerprint: str
    size: int
    last_updated: str
    download_url: str | None = None
    status: str = "available"  # available, processing, failed
    quality_score: float | None = None
    completion_percentage: float | None = None


@dataclass
class ResolutionResult:
    """Result of project resolution."""

    exists: bool
    project_key: str
    content_fingerprint: str
    available_languages: list[LanguageAvailability]
    recommended_downloads: list[str]  # Recommended locale codes
    server_version: str | None = None
    cache_expires_at: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class CacheEntry:
    """Cache entry for resolution results."""

    result: ResolutionResult
    cached_at: datetime
    expires_at: datetime
    etag: str | None = None
    last_modified: str | None = None


class ServerResolutionService:
    """Service for resolving project existence on remote servers."""

    def __init__(
        self,
        database: SQLCipherDatabase,
        logger: structlog.BoundLogger,
        server_base_url: str = "https://api.transhub.example.com",
        cache_ttl_seconds: int = 3600,  # 1 hour default cache
    ):
        self.database = database
        self.logger = logger
        self.server_base_url = server_base_url.rstrip("/")
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "MC-Studio/1.0", "Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def resolve_project(
        self,
        job_id: str,
        project_key: ProjectKey,
        content_fingerprint: ContentFingerprint,
        force_refresh: bool = False,
    ) -> ResolutionResult:
        """Resolve project existence and available languages."""
        logger = self.logger.bind(
            job_id=job_id,
            project_key=project_key.to_string(),
            content_fingerprint=content_fingerprint.aggregate_hash,
        )

        try:
            logger.info("Starting project resolution")
            await send_progress_update(job_id, 0, "Checking server for project...")

            # Generate cache key
            cache_key = self._generate_cache_key(project_key, content_fingerprint)

            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    logger.info("Using cached resolution result")
                    await send_log_message(
                        job_id, "info", "Using cached server response"
                    )
                    return cached_result

            await send_progress_update(job_id, 20, "Querying remote server...")

            # Make resolution request
            result = await self._make_resolution_request(
                job_id, project_key, content_fingerprint
            )

            await send_progress_update(job_id, 80, "Processing server response...")

            # Cache the result
            self._cache_result(cache_key, result)

            # Save resolution to database for audit
            await self._save_resolution_audit(project_key, content_fingerprint, result)

            await send_progress_update(job_id, 100, "Resolution completed")

            logger.info(
                "Project resolution completed",
                exists=result.exists,
                available_languages=len(result.available_languages),
            )

            return result

        except Exception as e:
            logger.error("Project resolution failed", error=str(e), exc_info=True)
            await send_log_message(
                job_id, "error", f"Server resolution failed: {str(e)}"
            )
            raise

    async def _make_resolution_request(
        self,
        job_id: str,
        project_key: ProjectKey,
        content_fingerprint: ContentFingerprint,
    ) -> ResolutionResult:
        """Make the actual resolution request to the server."""

        if not self._session:
            raise NetworkError("HTTP session not initialized")

        # Prepare request payload
        payload = {
            "project_key": {
                "type": project_key.type.value,
                "name": project_key.name,
                "version": project_key.version,
                "mc_version": project_key.mc_version,
                "loader": project_key.loader.value,
                "loader_version": project_key.loader_version,
            },
            "content_fingerprint": {
                "aggregate_hash": content_fingerprint.aggregate_hash,
                "file_count": content_fingerprint.file_count,
                "total_keys": content_fingerprint.total_keys,
                "source_language": content_fingerprint.source_language,
                "pattern_hash": content_fingerprint.pattern_hash,
            },
            "client_info": {
                "version": "1.0",
                "capabilities": ["batch_download", "incremental_update", "compression"],
            },
        }

        url = f"{self.server_base_url}/api/v1/projects/resolve"

        try:
            async with self._session.post(url, json=payload) as response:
                if response.status == 404:
                    # Project not found
                    return ResolutionResult(
                        exists=False,
                        project_key=project_key.to_string(),
                        content_fingerprint=content_fingerprint.aggregate_hash,
                        available_languages=[],
                        recommended_downloads=[],
                        metadata={"reason": "not_found"},
                    )

                elif response.status == 200:
                    # Project found
                    data = await response.json()
                    return self._parse_resolution_response(
                        data, project_key, content_fingerprint
                    )

                elif response.status == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    await send_log_message(
                        job_id,
                        "warning",
                        f"Rate limited, waiting {retry_after} seconds...",
                    )
                    await asyncio.sleep(retry_after)
                    # Retry once
                    return await self._make_resolution_request(
                        job_id, project_key, content_fingerprint
                    )

                else:
                    # Other error
                    error_text = await response.text()
                    raise NetworkError(
                        f"Server returned {response.status}: {error_text}"
                    )

        except aiohttp.ClientError as e:
            raise NetworkError(f"Network request failed: {str(e)}")

        except TimeoutError:
            raise NetworkError("Request timed out")

    def _parse_resolution_response(
        self,
        data: dict[str, Any],
        project_key: ProjectKey,
        content_fingerprint: ContentFingerprint,
    ) -> ResolutionResult:
        """Parse server response into ResolutionResult."""

        # Parse available languages
        available_languages = []
        for lang_data in data.get("available_languages", []):
            availability = LanguageAvailability(
                locale=lang_data["locale"],
                fingerprint=lang_data["fingerprint"],
                size=lang_data["size"],
                last_updated=lang_data["last_updated"],
                download_url=lang_data.get("download_url"),
                status=lang_data.get("status", "available"),
                quality_score=lang_data.get("quality_score"),
                completion_percentage=lang_data.get("completion_percentage"),
            )
            available_languages.append(availability)

        # Parse recommended downloads
        recommended_downloads = data.get("recommended_downloads", [])

        # If no explicit recommendations, use smart defaults
        if not recommended_downloads and available_languages:
            recommended_downloads = self._generate_smart_recommendations(
                available_languages, content_fingerprint.source_language
            )

        return ResolutionResult(
            exists=True,
            project_key=project_key.to_string(),
            content_fingerprint=content_fingerprint.aggregate_hash,
            available_languages=available_languages,
            recommended_downloads=recommended_downloads,
            server_version=data.get("server_version"),
            cache_expires_at=data.get("cache_expires_at"),
            metadata=data.get("metadata", {}),
        )

    def _generate_smart_recommendations(
        self, available_languages: list[LanguageAvailability], source_language: str
    ) -> list[str]:
        """Generate smart download recommendations."""
        recommendations = []

        # Always include source language if available
        source_available = any(
            lang.locale == source_language for lang in available_languages
        )
        if source_available:
            recommendations.append(source_language)

        # Add high-quality, high-completion languages
        quality_languages = [
            lang
            for lang in available_languages
            if lang.quality_score
            and lang.quality_score > 0.8
            and lang.completion_percentage
            and lang.completion_percentage > 90
            and lang.locale != source_language
        ]

        # Sort by quality and completion
        quality_languages.sort(
            key=lambda x: (x.quality_score or 0, x.completion_percentage or 0),
            reverse=True,
        )

        # Add top 3 quality languages
        for lang in quality_languages[:3]:
            if lang.locale not in recommendations:
                recommendations.append(lang.locale)

        # Add common languages if not already included
        common_languages = ["zh_cn", "es_es", "fr_fr", "de_de", "ja_jp", "ko_kr"]
        for locale in common_languages:
            if locale not in recommendations:
                available = any(lang.locale == locale for lang in available_languages)
                if available:
                    recommendations.append(locale)
                    if len(recommendations) >= 5:  # Limit recommendations
                        break

        return recommendations

    def _generate_cache_key(
        self, project_key: ProjectKey, content_fingerprint: ContentFingerprint
    ) -> str:
        """Generate cache key for resolution result."""
        key_data = f"{project_key.to_string()}:{content_fingerprint.aggregate_hash}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_result(self, cache_key: str) -> ResolutionResult | None:
        """Get cached resolution result if valid."""
        entry = self._cache.get(cache_key)
        if not entry:
            return None

        # Check if cache has expired
        if datetime.now() > entry.expires_at:
            del self._cache[cache_key]
            return None

        return entry.result

    def _cache_result(self, cache_key: str, result: ResolutionResult) -> None:
        """Cache resolution result."""
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.cache_ttl_seconds)

        # Use server-provided expiry if available
        if result.cache_expires_at:
            try:
                server_expires = datetime.fromisoformat(
                    result.cache_expires_at.replace("Z", "+00:00")
                )
                if server_expires > now:
                    expires_at = min(expires_at, server_expires)
            except ValueError:
                pass  # Use default expiry

        entry = CacheEntry(result=result, cached_at=now, expires_at=expires_at)

        self._cache[cache_key] = entry

        # Clean up old cache entries (simple LRU)
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].cached_at)
            del self._cache[oldest_key]

    async def _save_resolution_audit(
        self,
        project_key: ProjectKey,
        content_fingerprint: ContentFingerprint,
        result: ResolutionResult,
    ) -> None:
        """Save resolution result to database for audit."""
        try:
            audit_data = {
                "project_key": project_key.to_string(),
                "content_fingerprint": content_fingerprint.aggregate_hash,
                "exists": result.exists,
                "available_languages": len(result.available_languages),
                "recommended_downloads": result.recommended_downloads,
                "server_version": result.server_version,
                "resolved_at": datetime.now().isoformat(),
            }

            self.database.log_audit_event(
                "project_resolution", "server_query", audit_data
            )

        except Exception as e:
            self.logger.warning("Failed to save resolution audit", error=str(e))
            # Non-fatal error

    def clear_cache(self, project_key: ProjectKey | None = None) -> int:
        """Clear resolution cache."""
        if project_key is None:
            # Clear all cache
            count = len(self._cache)
            self._cache.clear()
            return count

        # Clear cache for specific project
        project_key_str = project_key.to_string()
        keys_to_remove = [
            key
            for key, entry in self._cache.items()
            if entry.result.project_key == project_key_str
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        valid_entries = sum(
            1 for entry in self._cache.values() if entry.expires_at > now
        )
        expired_entries = len(self._cache) - valid_entries

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_hit_potential": valid_entries / max(len(self._cache), 1),
        }

    async def batch_resolve_projects(
        self,
        job_id: str,
        projects: list[tuple[ProjectKey, ContentFingerprint]],
        max_concurrent: int = 3,
    ) -> list[ResolutionResult]:
        """Resolve multiple projects concurrently."""
        logger = self.logger.bind(job_id=job_id, project_count=len(projects))

        logger.info("Starting batch project resolution")
        await send_progress_update(job_id, 0, f"Resolving {len(projects)} projects...")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def resolve_single(
            index: int, project_key: ProjectKey, content_fingerprint: ContentFingerprint
        ):
            async with semaphore:
                try:
                    result = await self.resolve_project(
                        f"{job_id}-{index}", project_key, content_fingerprint
                    )
                    progress = int((index + 1) / len(projects) * 100)
                    await send_progress_update(
                        job_id,
                        progress,
                        f"Resolved {index + 1}/{len(projects)} projects",
                    )
                    return result
                except Exception as e:
                    logger.error(f"Failed to resolve project {index}", error=str(e))
                    # Return a failed result instead of raising
                    return ResolutionResult(
                        exists=False,
                        project_key=project_key.to_string(),
                        content_fingerprint=content_fingerprint.aggregate_hash,
                        available_languages=[],
                        recommended_downloads=[],
                        metadata={"error": str(e)},
                    )

        # Execute all resolutions concurrently
        tasks = [
            resolve_single(i, project_key, content_fingerprint)
            for i, (project_key, content_fingerprint) in enumerate(projects)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        await send_progress_update(job_id, 100, "Batch resolution completed")
        logger.info("Batch project resolution completed")

        return results

    async def check_server_health(self) -> dict[str, Any]:
        """Check server health and capabilities."""
        if not self._session:
            raise NetworkError("HTTP session not initialized")

        url = f"{self.server_base_url}/api/v1/health"

        try:
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "server_version": data.get("version"),
                        "capabilities": data.get("capabilities", []),
                        "response_time_ms": response.headers.get("X-Response-Time"),
                        "server_time": data.get("timestamp"),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "http_status": response.status,
                        "error": await response.text(),
                    }

        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
