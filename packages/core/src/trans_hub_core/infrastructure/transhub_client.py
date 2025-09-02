"""Trans-Hub API Client for TH-Suite

Client for communicating with Trans-Hub translation server.
Handles authentication, data upload/download, and caching.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, AsyncIterator
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json
from pathlib import Path
import hashlib
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status with Trans-Hub server"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    OFFLINE = "offline"  # Working in offline mode


@dataclass
class TransHubConfig:
    """Configuration for Trans-Hub connection"""
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1
    
    # Batch settings
    batch_size: int = 100
    max_concurrent_requests: int = 5
    
    # Cache settings
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None
    cache_ttl: int = 3600  # seconds
    
    # Offline mode
    offline_mode: bool = False
    auto_sync: bool = True


@dataclass
class ScanResult:
    """Result from local scanning to upload"""
    project_id: str
    scan_id: str
    entries: Dict[str, Dict[str, str]]  # namespace -> key -> value
    metadata: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_upload_format(self) -> Dict[str, Any]:
        """Convert to server upload format"""
        return {
            "project_id": self.project_id,
            "scan_id": self.scan_id,
            "entries": self.entries,
            "metadata": {
                **self.metadata,
                "timestamp": self.timestamp.isoformat()
            }
        }


@dataclass
class TranslationPatch:
    """Translation patch from server"""
    patch_id: str
    project_id: str
    items: List[Dict[str, Any]]
    version: str
    signature: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_server_response(cls, data: Dict[str, Any]) -> 'TranslationPatch':
        """Create from server response"""
        return cls(
            patch_id=data['patch_id'],
            project_id=data['project_id'],
            items=data['items'],
            version=data.get('version', '1.0'),
            signature=data.get('signature'),
            created_at=datetime.fromisoformat(data['created_at']) 
                      if 'created_at' in data else None
        )


class TransHubClient:
    """Async client for Trans-Hub API"""
    
    def __init__(self, config: Optional[TransHubConfig] = None):
        self.config = config or TransHubConfig()
        self.status = ConnectionStatus.DISCONNECTED
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cache setup
        if self.config.cache_enabled:
            self.cache_dir = self.config.cache_dir or Path("./cache/transhub")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Offline queue
        self.offline_queue: List[ScanResult] = []
        
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self) -> bool:
        """Establish connection to Trans-Hub server"""
        if self.config.offline_mode:
            self.status = ConnectionStatus.OFFLINE
            logger.info("Running in offline mode")
            return True
        
        try:
            self.status = ConnectionStatus.CONNECTING
            
            # Create session
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f"Bearer {self.config.api_key}"
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
            
            # Test connection
            async with self.session.get(
                urljoin(self.config.base_url, "/health")
            ) as response:
                if response.status == 200:
                    self.status = ConnectionStatus.CONNECTED
                    logger.info(f"Connected to Trans-Hub at {self.config.base_url}")
                    
                    # Process offline queue if any
                    if self.config.auto_sync and self.offline_queue:
                        await self._sync_offline_queue()
                    
                    return True
                else:
                    raise Exception(f"Health check failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to connect to Trans-Hub: {e}")
            self.status = ConnectionStatus.ERROR
            
            # Fall back to offline mode
            if self.config.cache_enabled:
                self.status = ConnectionStatus.OFFLINE
                logger.info("Falling back to offline mode")
            
            return False
    
    async def disconnect(self):
        """Close connection to Trans-Hub"""
        if self.session:
            await self.session.close()
            self.session = None
        self.status = ConnectionStatus.DISCONNECTED
    
    async def upload_scan_results(self, 
                                 scan_result: ScanResult,
                                 batch: bool = True) -> bool:
        """Upload scan results to Trans-Hub"""
        if self.status == ConnectionStatus.OFFLINE:
            # Queue for later sync
            self.offline_queue.append(scan_result)
            self._save_offline_queue()
            logger.info(f"Queued scan {scan_result.scan_id} for offline sync")
            return True
        
        if self.status != ConnectionStatus.CONNECTED:
            logger.error("Not connected to Trans-Hub")
            return False
        
        try:
            data = scan_result.to_upload_format()
            
            if batch and len(data['entries']) > self.config.batch_size:
                # Split into batches
                return await self._upload_in_batches(data)
            else:
                # Single upload
                return await self._upload_single(data)
                
        except Exception as e:
            logger.error(f"Failed to upload scan results: {e}")
            
            # Queue for retry if configured
            if self.config.cache_enabled:
                self.offline_queue.append(scan_result)
                self._save_offline_queue()
            
            return False
    
    async def _upload_single(self, data: Dict[str, Any]) -> bool:
        """Upload single batch of data"""
        url = urljoin(self.config.base_url, "/api/v1/scan/upload")
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Successfully uploaded scan {data['scan_id']}")
                        return True
                    elif response.status == 429:  # Rate limited
                        wait_time = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        error = await response.text()
                        logger.error(f"Upload failed: {response.status} - {error}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Upload timeout, attempt {attempt + 1}/{self.config.max_retries}")
                
            except Exception as e:
                logger.error(f"Upload error: {e}")
            
            # Retry delay
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
        
        return False
    
    async def _upload_in_batches(self, data: Dict[str, Any]) -> bool:
        """Upload data in batches"""
        entries = data['entries']
        namespaces = list(entries.keys())
        
        # Split into batches
        batches = []
        for ns in namespaces:
            ns_entries = entries[ns]
            keys = list(ns_entries.keys())
            
            for i in range(0, len(keys), self.config.batch_size):
                batch_keys = keys[i:i + self.config.batch_size]
                batch_data = {
                    **data,
                    'entries': {ns: {k: ns_entries[k] for k in batch_keys}},
                    'batch_index': len(batches),
                    'total_batches': -1  # Will be updated
                }
                batches.append(batch_data)
        
        # Update total batches
        for batch in batches:
            batch['total_batches'] = len(batches)
        
        # Upload batches concurrently
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        async def upload_with_semaphore(batch):
            async with semaphore:
                return await self._upload_single(batch)
        
        tasks = [upload_with_semaphore(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Uploaded {success_count}/{len(batches)} batches successfully")
        
        return success_count == len(batches)
    
    async def download_patches(self, 
                              project_id: str,
                              since: Optional[datetime] = None) -> List[TranslationPatch]:
        """Download translation patches from Trans-Hub"""
        if self.status == ConnectionStatus.OFFLINE:
            # Load from cache
            return self._load_cached_patches(project_id)
        
        if self.status != ConnectionStatus.CONNECTED:
            logger.error("Not connected to Trans-Hub")
            return []
        
        try:
            params = {'project_id': project_id}
            if since:
                params['since'] = since.isoformat()
            
            url = urljoin(self.config.base_url, "/api/v1/patches/download")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    patches = [
                        TranslationPatch.from_server_response(p) 
                        for p in data['patches']
                    ]
                    
                    # Cache patches
                    if self.config.cache_enabled:
                        for patch in patches:
                            self._cache_patch(patch)
                    
                    logger.info(f"Downloaded {len(patches)} patches for project {project_id}")
                    return patches
                else:
                    error = await response.text()
                    logger.error(f"Failed to download patches: {response.status} - {error}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error downloading patches: {e}")
            # Fall back to cache
            return self._load_cached_patches(project_id)
    
    async def get_translation_status(self, 
                                    project_id: str,
                                    target_language: str) -> Dict[str, Any]:
        """Get translation status from server"""
        if self.status != ConnectionStatus.CONNECTED:
            return {}
        
        try:
            url = urljoin(self.config.base_url, f"/api/v1/projects/{project_id}/status")
            params = {'target_language': target_language}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {}
    
    def _cache_patch(self, patch: TranslationPatch) -> None:
        """Cache a patch locally"""
        cache_file = self.cache_dir / f"patch_{patch.patch_id}.json"
        
        data = {
            'patch_id': patch.patch_id,
            'project_id': patch.project_id,
            'items': patch.items,
            'version': patch.version,
            'signature': patch.signature,
            'created_at': patch.created_at.isoformat() if patch.created_at else None,
            'cached_at': datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_cached_patches(self, project_id: str) -> List[TranslationPatch]:
        """Load cached patches for a project"""
        patches = []
        
        for cache_file in self.cache_dir.glob("patch_*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data['project_id'] == project_id:
                    # Check TTL
                    cached_at = datetime.fromisoformat(data['cached_at'])
                    if datetime.now() - cached_at < timedelta(seconds=self.config.cache_ttl):
                        patches.append(TranslationPatch.from_server_response(data))
                        
            except Exception as e:
                logger.warning(f"Failed to load cached patch {cache_file}: {e}")
        
        return patches
    
    def _save_offline_queue(self) -> None:
        """Save offline queue to disk"""
        queue_file = self.cache_dir / "offline_queue.json"
        
        data = [
            scan.to_upload_format() 
            for scan in self.offline_queue
        ]
        
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_offline_queue(self) -> None:
        """Load offline queue from disk"""
        queue_file = self.cache_dir / "offline_queue.json"
        
        if not queue_file.exists():
            return
        
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.offline_queue = [
                ScanResult(
                    project_id=item['project_id'],
                    scan_id=item['scan_id'],
                    entries=item['entries'],
                    metadata=item['metadata']
                )
                for item in data
            ]
            
        except Exception as e:
            logger.error(f"Failed to load offline queue: {e}")
    
    async def _sync_offline_queue(self) -> None:
        """Sync offline queue when connection is restored"""
        if not self.offline_queue:
            return
        
        logger.info(f"Syncing {len(self.offline_queue)} offline scans")
        
        success_count = 0
        failed = []
        
        for scan in self.offline_queue:
            if await self.upload_scan_results(scan, batch=True):
                success_count += 1
            else:
                failed.append(scan)
        
        self.offline_queue = failed
        self._save_offline_queue()
        
        logger.info(f"Synced {success_count} scans, {len(failed)} failed")
    
    async def test_connection(self) -> bool:
        """Test connection to Trans-Hub"""
        try:
            url = urljoin(self.config.base_url, "/health")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status information"""
        return {
            'connection_status': self.status.value,
            'server_url': self.config.base_url,
            'offline_queue_size': len(self.offline_queue),
            'cache_enabled': self.config.cache_enabled,
            'offline_mode': self.config.offline_mode
        }
