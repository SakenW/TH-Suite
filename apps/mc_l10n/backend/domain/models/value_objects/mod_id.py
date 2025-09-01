"""模组ID值对象"""

import re

from packages.core.data.models import ValueObject


class ModId(ValueObject):
    """模组ID值对象"""

    def __init__(self, value: str):
        if not value or not self._is_valid_mod_id(value):
            raise ValueError(f"无效的模组ID: {value}")
        self._value = value.lower()  # 模组ID通常是小写

    @staticmethod
    def _is_valid_mod_id(value: str) -> bool:
        """验证模组ID格式"""
        # 模组ID只能包含字母、数字、下划线和连字符
        pattern = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
        return bool(re.match(pattern, value)) and len(value) <= 64

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other) -> bool:
        if not isinstance(other, ModId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
