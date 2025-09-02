"""Trans-Hub Client Mock Implementation"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ConnectionStatus(Enum):
    """Connection status enum"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


class TransHubConfig:
    """Trans-Hub configuration"""
    def __init__(self, base_url: str = "http://localhost:8000", 
                 api_key: Optional[str] = None,
                 offline_mode: bool = False,
                 auto_sync: bool = True):
        self.base_url = base_url
        self.api_key = api_key
        self.offline_mode = offline_mode
        self.auto_sync = auto_sync


class ScanResult:
    """Scan result model"""
    def __init__(self, project_id: str, scan_id: str, 
                 entries: Dict[str, Dict[str, str]]):
        self.project_id = project_id
        self.scan_id = scan_id
        self.entries = entries
        self.timestamp = datetime.now()


class TransHubClient:
    """Mock Trans-Hub client for development"""
    
    def __init__(self, config: Optional[TransHubConfig] = None):
        self.config = config or TransHubConfig()
        self.status = ConnectionStatus.DISCONNECTED
        self.offline_queue: List[ScanResult] = []
        
    async def connect(self) -> bool:
        """Mock connection to Trans-Hub server"""
        self.status = ConnectionStatus.CONNECTED
        return True
        
    async def disconnect(self) -> bool:
        """Mock disconnection from Trans-Hub server"""
        self.status = ConnectionStatus.DISCONNECTED
        return True
        
    def get_status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self.status
        
    async def upload_scan_result(self, result: ScanResult) -> Dict[str, Any]:
        """Mock upload of scan results"""
        if self.status != ConnectionStatus.CONNECTED:
            self.offline_queue.append(result)
            return {"success": False, "queued": True}
        return {"success": True, "id": result.scan_id}
        
    async def download_patches(self, project_id: str) -> Dict[str, Any]:
        """Mock download of translation patches"""
        return {
            "patches": {},
            "timestamp": datetime.now().isoformat()
        }
        
    def get_offline_queue_size(self) -> int:
        """Get size of offline queue"""
        return len(self.offline_queue)