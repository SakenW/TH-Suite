"""
Universal Scanner Package - 通用扫描引擎

职责：
- 提供与游戏无关的扫描核心功能
- UPSERT数据库操作引擎
- 缓存和实时通信基础设施
- 可被任何游戏本地化项目复用

设计原则：
- 单一职责：每个模块只负责一个核心功能
- 入口单一：统一的扫描器接口
- 通用性：不包含任何游戏特定逻辑
"""

from .core.database_engine import UniversalUpsertEngine
from .core.scanner_engine import UniversalScannerEngine
from .core.scanner_interface import ScannerInterface, ScanRequest, ScanResult

# Import cache and websocket modules if they exist
try:
    from .cache.cache_service import ScanCacheService  # noqa: F401
    from .websocket.progress_broadcaster import ProgressBroadcaster  # noqa: F401

    _optional_imports = ["ScanCacheService", "ProgressBroadcaster"]
except ImportError:
    _optional_imports = []

__all__ = [
    "UniversalScannerEngine",
    "UniversalUpsertEngine",
    "ScannerInterface",
    "ScanRequest",
    "ScanResult",
] + _optional_imports

__version__ = "1.0.0"
