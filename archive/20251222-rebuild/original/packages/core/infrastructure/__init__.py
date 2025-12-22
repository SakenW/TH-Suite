"""
基础设施层

提供与外部系统的集成接口：
- 存储服务
- HTTP通信
- 序列化
- 加密服务
- 压缩服务
"""

from .crypto.encryptor import Encryptor
from .http.http_client import HttpClient
from .serialization.serializer import ISerializer, JsonSerializer
from .storage.storage_manager import IStorageProvider, StorageManager

__all__ = [
    "StorageManager",
    "IStorageProvider",
    "HttpClient",
    "ISerializer",
    "JsonSerializer",
    "Encryptor",
]
