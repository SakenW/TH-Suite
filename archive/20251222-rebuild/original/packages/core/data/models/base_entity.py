"""
实体基类

DDD中的实体（Entity）基类
"""

import uuid
from abc import ABC
from datetime import datetime
from typing import Any


class BaseEntity(ABC):
    """实体基类"""

    def __init__(self, entity_id: str | None = None):
        self.id = entity_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._domain_events: list = []

    def __eq__(self, other):
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def add_domain_event(self, event: Any) -> None:
        """添加领域事件"""
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        """清除领域事件"""
        self._domain_events.clear()

    def get_domain_events(self) -> list:
        """获取领域事件"""
        return self._domain_events.copy()

    def mark_updated(self) -> None:
        """标记为已更新"""
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
