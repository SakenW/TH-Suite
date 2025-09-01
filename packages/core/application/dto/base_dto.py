"""
数据传输对象基类

提供通用的数据传输对象功能
"""

import json
from typing import Any


class BaseDTO:
    """数据传输对象基类"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                if hasattr(value, "to_dict"):
                    result[key] = value.to_dict()
                elif hasattr(value, "isoformat"):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseDTO":
        """从字典创建"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "BaseDTO":
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        attrs = self.to_dict()
        attr_str = ", ".join(f"{k}={repr(v)}" for k, v in attrs.items())
        return f"{self.__class__.__name__}({attr_str})"
