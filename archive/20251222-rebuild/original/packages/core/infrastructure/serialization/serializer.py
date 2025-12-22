"""
序列化器

提供数据序列化功能
"""

import json
from abc import ABC, abstractmethod
from typing import Any


class ISerializer(ABC):
    """序列化器接口"""

    @abstractmethod
    def serialize(self, obj: Any) -> str:
        """序列化"""
        pass

    @abstractmethod
    def deserialize(self, data: str) -> Any:
        """反序列化"""
        pass


class JsonSerializer(ISerializer):
    """JSON序列化器"""

    def serialize(self, obj: Any) -> str:
        """序列化为JSON"""
        return json.dumps(obj, ensure_ascii=False, default=str)

    def deserialize(self, data: str) -> Any:
        """从JSON反序列化"""
        return json.loads(data)
