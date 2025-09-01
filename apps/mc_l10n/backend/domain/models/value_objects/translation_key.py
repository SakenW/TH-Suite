"""翻译键值对象"""

from packages.core.data.models import ValueObject


class TranslationKey(ValueObject):
    """翻译键值对象"""

    def __init__(self, value: str):
        if not value:
            raise ValueError("翻译键不能为空")
        self._value = value
        self._parsed = self._parse_key(value)

    def _parse_key(self, key: str) -> dict[str, str]:
        """解析翻译键结构"""
        parts = key.split(".")
        if len(parts) < 2:
            return {"type": "unknown", "identifier": key}

        return {
            "type": parts[0],  # item, block, gui, etc.
            "mod_id": parts[1] if len(parts) > 2 else "minecraft",
            "identifier": ".".join(parts[2:]) if len(parts) > 2 else parts[1],
            "full_key": key,
        }

    @property
    def value(self) -> str:
        return self._value

    @property
    def type(self) -> str:
        """获取翻译键类型 (item, block, gui等)"""
        return self._parsed["type"]

    @property
    def mod_id(self) -> str:
        """获取关联的模组ID"""
        return self._parsed["mod_id"]

    def is_item_key(self) -> bool:
        return self.type == "item"

    def is_block_key(self) -> bool:
        return self.type == "block"

    def is_gui_key(self) -> bool:
        return self.type == "gui"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other) -> bool:
        if not isinstance(other, TranslationKey):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
