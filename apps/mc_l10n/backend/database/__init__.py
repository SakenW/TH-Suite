"""
MC L10n 数据库模块
提供本地数据库的完整功能支持
"""

from .local_database_manager import LocalDatabaseManager
from .scan_service import ScanDatabaseService
from .sync_service import DataSyncService, SyncDirection, ConflictResolution
from .offline_tracker import OfflineChangeTracker, EntityType, ChangeOperation
from .database_api import router as database_router

__all__ = [
    # 管理器
    'LocalDatabaseManager',
    
    # 服务
    'ScanDatabaseService',
    'DataSyncService',
    'OfflineChangeTracker',
    
    # 枚举
    'SyncDirection',
    'ConflictResolution',
    'EntityType',
    'ChangeOperation',
    
    # API路由
    'database_router'
]

# 版本信息
__version__ = '1.0.0'