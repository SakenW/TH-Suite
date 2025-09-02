"""Trans-Hub integration routes for MC L10n

Provides endpoints for connecting to Trans-Hub server,
uploading scan results, and downloading patches.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging

from trans_hub_core.infrastructure.transhub_client import (
    TransHubClient,
    TransHubConfig,
    ScanResult,
    ConnectionStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/transhub", tags=["Trans-Hub"])

# Global client instance
transhub_client: Optional[TransHubClient] = None


class ServerConfig(BaseModel):
    """Trans-Hub server configuration"""
    base_url: str = Field(default="http://localhost:18000", description="Trans-Hub server URL")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    offline_mode: bool = Field(default=False, description="Enable offline mode")
    auto_sync: bool = Field(default=True, description="Auto sync when connection restored")


class ConnectionStatusResponse(BaseModel):
    """Connection status response"""
    connected: bool
    status: str
    server_url: str
    offline_queue_size: int
    message: str


class UploadRequest(BaseModel):
    """Request to upload scan results"""
    project_id: str
    scan_id: str
    entries: Dict[str, Dict[str, str]]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PatchDownloadRequest(BaseModel):
    """Request to download patches"""
    project_id: str
    since: Optional[str] = Field(default=None, description="ISO datetime to get patches since")


class PatchApplyRequest(BaseModel):
    """Request to apply a patch"""
    patch_id: str
    strategy: str = Field(default="overlay", description="Writeback strategy: overlay or jar_inplace")
    dry_run: bool = Field(default=False, description="Test run without applying changes")


async def get_client() -> TransHubClient:
    """Get or create Trans-Hub client instance"""
    global transhub_client
    if not transhub_client:
        transhub_client = TransHubClient()
    return transhub_client


@router.post("/connect")
async def connect_to_server(
    config: ServerConfig,
    background_tasks: BackgroundTasks
) -> ConnectionStatusResponse:
    """Connect to Trans-Hub server"""
    global transhub_client
    
    try:
        # Create new client with config
        client_config = TransHubConfig(
            base_url=config.base_url,
            api_key=config.api_key,
            offline_mode=config.offline_mode,
            auto_sync=config.auto_sync
        )
        
        # Close existing client if any
        if transhub_client:
            await transhub_client.disconnect()
        
        transhub_client = TransHubClient(client_config)
        
        # Connect
        connected = await transhub_client.connect()
        
        status = transhub_client.get_status()
        
        return ConnectionStatusResponse(
            connected=connected,
            status=status.value,
            server_url=transhub_client.config.base_url,
            offline_queue_size=transhub_client.get_offline_queue_size() if hasattr(transhub_client, 'get_offline_queue_size') else 0,
            message="Connected successfully" if connected else "Connection failed, running in offline mode"
        )
        
    except Exception as e:
        logger.error(f"Failed to connect to Trans-Hub: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_connection_status() -> ConnectionStatusResponse:
    """Get current connection status"""
    client = await get_client()
    status = client.get_status()
    
    return ConnectionStatusResponse(
        connected=status == ConnectionStatus.CONNECTED,
        status=status.value,
        server_url=client.config.base_url if client.config else "",
        offline_queue_size=client.get_offline_queue_size() if hasattr(client, 'get_offline_queue_size') else 0,
        message=f"Status: {status.value}"
    )


@router.post("/disconnect")
async def disconnect_from_server() -> Dict[str, str]:
    """Disconnect from Trans-Hub server"""
    client = await get_client()
    await client.disconnect()
    return {"message": "Disconnected from Trans-Hub"}


@router.post("/upload")
async def upload_scan_results(
    request: UploadRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Upload scan results to Trans-Hub"""
    client = await get_client()
    
    if client.status == ConnectionStatus.DISCONNECTED:
        raise HTTPException(status_code=503, detail="Not connected to Trans-Hub")
    
    try:
        # Create scan result
        scan_result = ScanResult(
            project_id=request.project_id,
            scan_id=request.scan_id,
            entries=request.entries,
            metadata=request.metadata or {}
        )
        
        # Upload (will queue if offline)
        success = await client.upload_scan_results(scan_result)
        
        if client.status == ConnectionStatus.OFFLINE:
            return {
                "success": True,
                "message": "Scan queued for offline sync",
                "queued": True,
                "scan_id": request.scan_id
            }
        else:
            return {
                "success": success,
                "message": "Upload successful" if success else "Upload failed",
                "queued": False,
                "scan_id": request.scan_id
            }
            
    except Exception as e:
        logger.error(f"Failed to upload scan results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-patches")
async def download_patches(request: PatchDownloadRequest) -> Dict[str, Any]:
    """Download patches from Trans-Hub"""
    client = await get_client()
    
    if client.status not in [ConnectionStatus.CONNECTED, ConnectionStatus.OFFLINE]:
        raise HTTPException(status_code=503, detail="Not connected to Trans-Hub")
    
    try:
        # Parse since date if provided
        since = None
        if request.since:
            since = datetime.fromisoformat(request.since)
        
        # Download patches
        patches = await client.download_patches(request.project_id, since)
        
        return {
            "success": True,
            "patch_count": len(patches),
            "patches": [
                {
                    "patch_id": p.patch_id,
                    "version": p.version,
                    "item_count": len(p.items),
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in patches
            ],
            "from_cache": client.status == ConnectionStatus.OFFLINE
        }
        
    except Exception as e:
        logger.error(f"Failed to download patches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-patch")
async def apply_patch(request: PatchApplyRequest) -> Dict[str, Any]:
    """Apply a downloaded patch"""
    # This would integrate with the patch_client module
    # For now, return a placeholder
    return {
        "success": False,
        "message": "Patch application not yet implemented",
        "patch_id": request.patch_id
    }


@router.get("/translation-status/{project_id}")
async def get_translation_status(
    project_id: str,
    target_language: str = "zh_cn"
) -> Dict[str, Any]:
    """Get translation status from Trans-Hub"""
    client = await get_client()
    
    if client.status != ConnectionStatus.CONNECTED:
        return {
            "available": False,
            "message": "Status only available when connected"
        }
    
    try:
        status = await client.get_translation_status(project_id, target_language)
        return {
            "available": True,
            **status
        }
    except Exception as e:
        logger.error(f"Failed to get translation status: {e}")
        return {
            "available": False,
            "error": str(e)
        }


@router.post("/sync-offline")
async def sync_offline_queue() -> Dict[str, Any]:
    """Manually trigger offline queue sync"""
    client = await get_client()
    
    if client.status != ConnectionStatus.CONNECTED:
        raise HTTPException(status_code=503, detail="Must be connected to sync")
    
    try:
        # Trigger sync
        await client._sync_offline_queue()
        
        return {
            "success": True,
            "message": "Offline queue sync completed",
            "remaining_queue_size": len(client.offline_queue)
        }
    except Exception as e:
        logger.error(f"Failed to sync offline queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection")
async def test_connection(server_url: str = "http://localhost:18000") -> Dict[str, Any]:
    """Test connection to a Trans-Hub server"""
    try:
        # Create temporary client
        config = TransHubConfig(base_url=server_url)
        test_client = TransHubClient(config)
        
        # Test connection
        reachable = await test_client.test_connection()
        
        return {
            "reachable": reachable,
            "server_url": server_url,
            "message": "Server is reachable" if reachable else "Server is not reachable"
        }
        
    except Exception as e:
        return {
            "reachable": False,
            "server_url": server_url,
            "error": str(e)
        }
